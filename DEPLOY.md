# Deploy — so you don't run Python locally

You have 2 options. Pick one.

## Option A — 24/7 worker (recommended for Telegram Place/Skip)

Any free host that runs a Docker worker will do. Example with **Render**:

1. Push this repo to GitHub (see below).
2. On render.com → New → Background Worker → connect your GitHub repo.
3. Build: `docker` (uses `Dockerfile:1`). Start: `python -m sureodds run` is already the CMD.
4. Add Environment Variables (Render → Environment):
   `API_FOOTBALL_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SUREODDS_DB=data/sureodds.db`
5. Add a second service **or** run `python -m sureodds listen` as a separate worker so Telegram buttons work 24/7. On Render you can add a second Background Worker with start `python -m sureodds listen`.

Free alternatives: Railway, Fly.io (`fly launch` + `fly deploy`), or a €5 VPS (Hetzner/Contabo) with `systemd` + `git pull`.

## Option B — GitHub Actions only (no server, cron pick)

`.github/workflows/daily.yml:1` already runs `fetch → pick` daily at 08:00 UTC (09:00 WAT) and sends the card to Telegram. Settlement still needs a manual `workflow_dispatch` or a second cron.

Add repo Secrets: GitHub → Settings → Secrets → Actions → `API_FOOTBALL_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

## Push to GitHub

```powershell
# from C:\Users\PC\sureodds
git remote add origin https://github.com/<you>/sureodds.git
git branch -M main
git push -u origin main
```

Replace `<you>` with your GitHub username. If you don't have a repo yet: github.com → New repository → `sureodds` (empty, no README) → copy the HTTPS URL.

After pushing, the Actions workflow will appear under GitHub → Actions.

## 09:00 window

`src/sureodds/orchestrator.py:14` `window_for_day` enforces `09:00 Africa/Douala → next day 09:00` (UTC conversion inside). `fetch` now pulls both calendar dates and `pick` filters by `kickoff` timestamp, so a pick at 09:00 never includes matches that already kicked off or that belong to the next day's window.
