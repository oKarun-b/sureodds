from __future__ import annotations


def p_ever_two_up(
    lam_h: float,
    lam_a: float,
    minutes: int = 90,
    max_goals: int = 8,
) -> dict[str, float]:
    ph = min(lam_h / minutes, 0.25)
    pa = min(lam_a / minutes, 0.25)

    mg = max_goals
    dist = [[0.0] * (mg + 1) for _ in range(mg + 1)]
    dist[0][0] = 1.0
    ever_h = 0.0
    ever_a = 0.0

    for _ in range(minutes):
        nxt = [[0.0] * (mg + 1) for _ in range(mg + 1)]
        for i in range(mg + 1):
            row = dist[i]
            for j in range(mg + 1):
                p = row[j]
                if p <= 0.0:
                    continue
                stay = p * (1.0 - ph - pa)
                gh = p * ph
                ga = p * pa

                nxt[i][j] += stay

                ni = i + 1 if i < mg else i
                if gh > 0.0:
                    if ni - j >= 2:
                        ever_h += gh
                    else:
                        nxt[ni][j] += gh

                nj = j + 1 if j < mg else j
                if ga > 0.0:
                    if nj - i >= 2:
                        ever_a += ga
                    else:
                        nxt[i][nj] += ga
        dist = nxt

    return {"HOME": ever_h, "AWAY": ever_a}
