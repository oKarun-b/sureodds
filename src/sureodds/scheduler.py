from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler

from . import orchestrator


def _parse_hhmm(raw: str) -> tuple[int, int]:
    hh, mm = raw.split(":")
    return int(hh), int(mm)


def start(cfg, conn) -> None:
    sched = BlockingScheduler(timezone=cfg.timezone)

    ph, pm = _parse_hhmm(cfg.schedule.pick)
    sh, sm = _parse_hhmm(cfg.schedule.settle)

    def job_morning():
        orchestrator.fetch(cfg, conn)
        result, err = orchestrator.pick(cfg, conn)
        if err:
            print(f"[scheduler] no slip: {err}")
            return
        print(result["card"])

    def job_settlement():
        summary = orchestrator.settle(cfg, conn)
        for s in summary:
            flag = " (2UP)" if s["via_2up"] else ""
            print(f"[scheduler] #{s['slip_id']} {s['result']}{flag} bankroll={s['bankroll']}")

    sched.add_job(job_morning, "cron", hour=ph, minute=pm, id="pick")
    sched.add_job(job_settlement, "cron", hour=sh, minute=sm, id="settle")

    print(
        f"scheduler started ({cfg.timezone}): pick {cfg.schedule.pick}, settle {cfg.schedule.settle}"
    )
    sched.start()
