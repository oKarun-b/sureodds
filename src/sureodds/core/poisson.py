from __future__ import annotations

import math


def pois_pmf(lam: float, k: int) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * lam**k / math.factorial(k)


def score_matrix(lam_h: float, lam_a: float, max_goals: int = 8) -> list[list[float]]:
    row = [pois_pmf(lam_h, i) for i in range(max_goals + 1)]
    col = [pois_pmf(lam_a, j) for j in range(max_goals + 1)]
    m = [[row[i] * col[j] for j in range(max_goals + 1)] for i in range(max_goals + 1)]
    total = sum(sum(r) for r in m)
    return [[v / total for v in r] for r in m] if total > 0 else m


def dc_adjust(
    matrix: list[list[float]], lam_h: float, lam_a: float, rho: float = -0.05
) -> list[list[float]]:
    m = [row[:] for row in matrix]
    m[0][0] *= 1.0 - lam_h * lam_a * rho
    m[0][1] *= 1.0 + lam_h * rho
    m[1][0] *= 1.0 + lam_a * rho
    m[1][1] *= 1.0 - rho
    total = sum(sum(r) for r in m)
    return [[v / total for v in row] for row in m]


def outcome_probs(matrix: list[list[float]]) -> dict[str, float]:
    n = len(matrix)
    home = sum(matrix[i][j] for i in range(n) for j in range(n) if i > j)
    draw = sum(matrix[i][i] for i in range(n))
    away = sum(matrix[i][j] for i in range(n) for j in range(n) if i < j)
    return {"HOME": home, "DRAW": draw, "AWAY": away}


def top_scorelines(matrix: list[list[float]], k: int = 3) -> list[tuple[int, int, float]]:
    cells = [(i, j, matrix[i][j]) for i in range(len(matrix)) for j in range(len(matrix[i]))]
    cells.sort(key=lambda t: t[2], reverse=True)
    return cells[:k]


def predict_match(
    lam_h: float,
    lam_a: float,
    rho: float = -0.05,
    max_goals: int = 8,
) -> tuple[list[list[float]], dict[str, float]]:
    m = dc_adjust(score_matrix(lam_h, lam_a, max_goals), lam_h, lam_a, rho)
    return m, outcome_probs(m)
