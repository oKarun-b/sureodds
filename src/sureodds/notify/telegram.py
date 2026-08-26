from __future__ import annotations

import httpx


class Telegram:
    def __init__(self, token: str, chat_id: str) -> None:
        self._token = token
        self._chat_id = chat_id
        self._base = f"https://api.telegram.org/bot{token}" if token else None

    @property
    def enabled(self) -> bool:
        return bool(self._token and self._chat_id)

    def send(self, text: str, buttons: list[list[dict]] | None = None) -> None:
        if not self.enabled:
            print("[telegram disabled] message would be:\n" + text)
            return
        payload: dict = {"chat_id": self._chat_id, "text": text}
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        resp = httpx.post(f"{self._base}/sendMessage", json=payload, timeout=30)
        resp.raise_for_status()

    def send_pick(self, card: str, slip_id: int) -> None:
        buttons = [
            [{"text": "✅ PLACE", "callback_data": f"validate:{slip_id}"}],
            [{"text": "❌ SKIP", "callback_data": f"reject:{slip_id}"}],
        ]
        self.send(card, buttons)

    def poll_validations(self, handler, once: bool = True, timeout: int = 55) -> str | None:
        if not self.enabled:
            raise RuntimeError("telegram not configured")
        offset = 0
        while True:
            resp = httpx.get(
                f"{self._base}/getUpdates",
                params={"timeout": timeout, "offset": offset},
                timeout=timeout + 10,
            )
            resp.raise_for_status()
            updates = resp.json().get("result", [])
            for upd in updates:
                offset = max(offset, upd["update_id"] + 1)
                cb = upd.get("callback_query")
                if not cb:
                    continue
                data = cb.get("data", "")
                if data.startswith(("validate:", "reject:")):
                    handler(data)
                    httpx.post(
                        f"{self._base}/answerCallbackQuery",
                        json={"callback_query_id": cb["id"]},
                        timeout=15,
                    )
                    if once:
                        return data
            if not updates and once:
                continue
