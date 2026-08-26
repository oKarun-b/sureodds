# SureOdds — Daily 1X2 Accumulator Bot

Daily-pick accumulator bot: scans all football fixtures worldwide, scores every 1X2 outcome with a Dixon–Coles Poisson engine blended with 33-bookmaker market consensus, builds one `~2.00` acca, and sends it to Telegram for your validation. After validation the placer fills the `1X2 2UP` market on BetPawa (with Win-Bonus awareness and bonus-adjusted EV). Stake is calibration-governed Kelly with Growth/Security modes.

## Architecture (inspired by `xai-org/grok-build`)

| SureOdds package | Grok-build analog | Role |
|---|---|---|
| `cli.py` | `-bin` crate | Composition root — thin wiring |
| `core/` | `xai-grok-shell` | Pure domain, zero I/O |
| `providers/` | `xai-grok-tools` | Adapters at the edge |
| `storage/` | `xai-grok-workspace` | SQLite repos + migrations |
| `config.py` | leaf crate | Shared settings loader |
| `notify/` `placement/` | tool impls | Telegram, Playwright stubs |

Rule: core never imports I/O. Adapters push data in, sinks take slips out.

## Quickstart (Windows / PowerShell)

```powershell
Copy-Item .env.example .env          # set API_FOOTBALL_KEY, TELEGRAM_*, BETPAWA_*
python -m uv sync --python 3.12
python -m uv run sureodds init       # migrates data/sureodds.db
python -m uv run sureodds bankroll --set 10000   # starting bankroll in FCFA
python -m uv run sureodds fetch      # today's fixtures + 1X2 odds
python -m uv run sureodds pick       # builds slip, prints card, records in DB
python -m uv run sureodds validate --slip 1 --yes   # or --no to skip today
python -m uv run sureodds settle --date 2026-08-25  # settles yesterday; handles 2UP
python -m uv run sureodds report --window 60
python -m uv run sureodds run        # blocking scheduler (pick 09:00, settle 08:00 Africa/Douala)
```

Run Telegram validation listener in a second session by extending `notify/telegram.py` (calls `Telegram.poll_validations`).

## BetPawa features wired in

* **1X2 2UP | Full Time** — a separate market: any leg whose team goes 2 goals up at any point is settled WIN instantly, even if the final score draws/loses. The engine computes `P(ever 2 up)` via a minute-step Poisson path DP and boosts qualifying legs; settlement checks the merged goal timeline and marks `via_2up`.
* **Win Bonus** (`pct_by_legs` in `config.yaml`, min leg odds 1.20) counted into `eff_total_odds` and EV; optimizer maximizes bonus-adjusted joint probability.
* **Cashout** hardcoded OFF — it voids 2UP eligibility and carries margin; a manual override path exists but is disabled by default.
* **Pawa6 free jackpot** auto-entry after the 7-day activity check (phase 9).

## Config

`config.yaml` is the single tuning surface: target odds band `[1.95,2.05]`, leg band `[1.20,1.60]`, `blend.w_model=0.35`, `ratings.half_life_days=120`, `staking.growth.cap_pct=0.20` with auto-demote after 2 straight losses or −40% drawdown, security tiers `[0.125,0.25,0.5]` gated on rolling 60-slip Brier score. `SUREODDS_DB` and secrets come from `.env`.

## Staking modes

```
bankroll < 10k                       → PAPER_FLOOR: flat 50 FCFA (min stake)
bankroll < 100k  (Growth Mode)       → 20% (demoted → 5% until recovery to ~98% watermark)
bankroll ≥ 100k  (Security Mode)     → fractional Kelly × tier (Brier-gated ⅛→¼→½, hard cap 10%)
```

## Paper-trade gate (phase 9)

The Playwright placer (`placement/betpawa_pw.py`) stays `NotImplementedError`-gated until `≥150` slips, calibration inside bands, and ROI CI clear of breakeven. That prevents automating money movement before the edge is proven.

## Tests

```
python -m uv run pytest
```

37 tests: Poisson ratings, 2UP path simulator, accumulator band/constraint logic, staking governor state machine, 2UP settlement rules, storage smoke.
