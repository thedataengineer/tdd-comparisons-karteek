"""Inter-rater reliability metrics (weighted Cohen's kappa) and severity calibration."""

from __future__ import annotations

from typing import Sequence

from tdd_ablation.contracts import ContractError

SEVERITY_LEVELS = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def weighted_kappa(left: Sequence[int], right: Sequence[int], num_categories: int = 4) -> float:
    """Calculate quadratic-weighted Cohen's kappa for ordinal ratings in 0..num_categories-1."""
    if len(left) != len(right):
        raise ContractError(f"length mismatch: {len(left)} vs {len(right)}")
    if len(left) == 0:
        raise ContractError("rating arrays must not be empty")

    n = len(left)
    k = num_categories

    # Observed matrix O
    o_matrix = [[0.0] * k for _ in range(k)]
    for r1, r2 in zip(left, right):
        if not (0 <= r1 < k) or not (0 <= r2 < k):
            raise ContractError(f"ratings must be integers in range [0, {k-1}]")
        o_matrix[r1][r2] += 1.0

    # Marginals
    r_margin = [sum(o_matrix[i][j] for j in range(k)) for i in range(k)]
    c_margin = [sum(o_matrix[i][j] for i in range(k)) for j in range(k)]

    # Expected matrix E
    e_matrix = [[(r_margin[i] * c_margin[j]) / n for j in range(k)] for i in range(k)]

    # Quadratic weight matrix W: w_ij = (i - j)^2 / (k - 1)^2
    denom_weight = (k - 1) ** 2 if k > 1 else 1.0
    w_matrix = [[((i - j) ** 2) / denom_weight for j in range(k)] for i in range(k)]

    po_weighted = sum(w_matrix[i][j] * o_matrix[i][j] for i in range(k) for j in range(k)) / n
    pe_weighted = sum(w_matrix[i][j] * e_matrix[i][j] for i in range(k) for j in range(k)) / n

    if pe_weighted == 0.0:
        return 1.0

    kappa = 1.0 - (po_weighted / pe_weighted)
    return kappa


def validate_severity_calibration(ratings: dict[str, list[int]]) -> float:
    """Validate severity calibration between two reviewers.

    Requires weighted kappa >= 0.80.
    """
    if len(ratings) != 2:
        raise ContractError(
            f"severity calibration must contain exactly two reviewers, found {len(ratings)}"
        )

    keys = list(ratings.keys())
    left, right = ratings[keys[0]], ratings[keys[1]]

    kappa = weighted_kappa(left, right)
    if kappa < 0.80:
        raise ContractError(
            f"severity calibration reliability below 0.80 threshold: {kappa:.3f}"
        )

    return kappa
