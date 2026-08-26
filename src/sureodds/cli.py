from __future__ import annotations

import argparse
import json

from .config import apply_dotenv, load_config
from .storage import db as dbmod
from .storage import repo


def _open():
    apply_dotenv()
    cfg = load_config()
    conn = dbmod.connect(cfg.db_path)
    dbmod.migrate(conn)
    return cfg, conn


def cmd_init(_args) -> None:
    cfg, _conn = _open()
    print(f"db ready at {cfg.db_path}")


def cmd_fetch(args) -> None:
    from . import orchestrator

    cfg, conn = _open()
    out = orchestrator.fetch(cfg, conn, args.date)
    print(json.dumps(out))


def cmd_pick(args) -> None:
    from . import orchestrator

    cfg, conn = _open()
    result, err = orchestrator.pick(cfg, conn, args.date)
    if err:
        print(f"NO SLIP: {err}")
        raise SystemExit(2)
    print(result["card"])


def cmd_validate(args) -> None:
    from . import orchestrator

    _cfg, conn = _open()

    status = orchestrator.validate_slip(conn, args.slip, accept=args.yes)
    print(f"slip #{args.slip} -> {status}")


def cmd_settle(args) -> None:
    from . import orchestrator

    cfg, conn = _open()
    summary = orchestrator.settle(cfg, conn, args.date)
    if not summary:
        print("nothing to settle")
        return
    for s in summary:
        flag = " (2UP)" if s["via_2up"] else ""
        print(
            f"#{s['slip_id']}: {s['result']}{flag} payout={s['payout']:.2f} bankroll={s['bankroll']:.2f}"
        )


def cmd_report(args) -> None:
    from . import orchestrator

    cfg, conn = _open()
    r = orchestrator.report(cfg, conn, args.window)
    print(json.dumps(r, indent=2))


def cmd_bankroll(args) -> None:
    cfg, conn = _open()
    if args.set is not None:
        before = repo.get_bankroll(conn, 0.0)
        after = repo.ledger_record(conn, "manual_adjustment", before, args.set - before, ref="cli")
        print(f"bankroll set to {after}")
    else:
        print(repo.get_bankroll(conn, float(cfg.staking.paper_floor_bankroll)))


def cmd_listen(args) -> None:
    import time

    import httpx

    from . import orchestrator

    cfg, conn = _open()
    tok = cfg.env.get("TELEGRAM_BOT_TOKEN", "")
    if not tok:
        raise SystemExit("TELEGRAM_BOT_TOKEN not set")
    cid = cfg.env.get("TELEGRAM_CHAT_ID", "")
    print(f"listening for Telegram Place/Skip on @{cfg.env.get('TELEGRAM_BOT_TOKEN','')[:8]}... (Ctrl+C to stop)")
    offset = None
    # ack existing
    with httpx.Client(timeout=15) as c:
        r = c.get(f"https://api.telegram.org/bot{tok}/getUpdates", params={"timeout": 1})
        if r.json().get("result"):
            offset = max(u["update_id"] for u in r.json()["result"]) + 1
    while True:
        try:
            with httpx.Client(timeout=35) as c:
                params = {"timeout": 30}
                if offset is not None:
                    params["offset"] = offset
                r = c.get(f"https://api.telegram.org/bot{tok}/getUpdates", params=params)
                j = r.json()
                for u in j.get("result", []):
                    offset = u["update_id"] + 1
                    if "callback_query" in u:
                        cb = u["callback_query"]
                        data = cb.get("data", "")
                        sid = None
                        accept = None
                        if data.startswith("validate:"):
                            sid = int(data.split(":")[1]); accept = True
                        elif data.startswith("reject:"):
                            sid = int(data.split(":")[1]); accept = False
                        if sid is not None:
                            status = orchestrator.validate_slip(conn, sid, accept)
                            c.post(f"https://api.telegram.org/bot{tok}/answerCallbackQuery", json={"callback_query_id": cb["id"], "text": status})
                            if cid:
                                c.post(f"https://api.telegram.org/bot{tok}/sendMessage", json={"chat_id": cid, "text": f"Slip #{sid} -> {status}"})
                            print(f"callback {data} -> {status}")
                    elif "message" in u:
                        text = (u["message"].get("text") or "").lower()
                        row = conn.execute("SELECT id FROM slips WHERE status='PENDING' ORDER BY id DESC LIMIT 1").fetchone()
                        if row and any(k in text for k in ["validate", "place", "yes"]):
                            status = orchestrator.validate_slip(conn, row["id"], True)
                            if cid:
                                c.post(f"https://api.telegram.org/bot{tok}/sendMessage", json={"chat_id": cid, "text": f"Slip #{row['id']} -> {status}"})
                        elif row and any(k in text for k in ["skip", "reject", "no"]):
                            status = orchestrator.validate_slip(conn, row["id"], False)
                            if cid:
                                c.post(f"https://api.telegram.org/bot{tok}/sendMessage", json={"chat_id": cid, "text": f"Slip #{row['id']} -> {status}"})
        except KeyboardInterrupt:
            break
        except (RuntimeError, OSError) as e:
            print(f"listen error: {e}")
            time.sleep(2)


def cmd_run(_args) -> None:
    from .scheduler import start

    cfg, conn = _open()
    start(cfg, conn)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sureodds", description="Daily 1X2 accumulator bot")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init").set_defaults(func=cmd_init)

    sp = sub.add_parser("fetch")
    sp.add_argument("--date", default=None)
    sp.set_defaults(func=cmd_fetch)

    sp = sub.add_parser("pick")
    sp.add_argument("--date", default=None)
    sp.set_defaults(func=cmd_pick)

    sp = sub.add_parser("validate")
    sp.add_argument("--slip", type=int, required=True)
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--yes", action="store_true")
    g.add_argument("--no", action="store_true")
    sp.set_defaults(func=cmd_validate)

    sp = sub.add_parser("settle")
    sp.add_argument("--date", default=None)
    sp.set_defaults(func=cmd_settle)

    sp = sub.add_parser("report")
    sp.add_argument("--window", type=int, default=60)
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("bankroll")
    sp.add_argument("--set", type=float, default=None)
    sp.set_defaults(func=cmd_bankroll)

    sub.add_parser("run").set_defaults(func=cmd_run)
    lp = sub.add_parser("listen", help="poll Telegram for Place/Skip buttons")
    lp.set_defaults(func=cmd_listen)
    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
