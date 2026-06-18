"""Curator-style success judge.

When a row carries reference tests or a reference answer, this module now
performs real deterministic evaluation: code is judged by sandboxed subprocess
pass-rate, while QA is judged by normalized answer match. Rows without ground
truth still use the original permissive Tier 1 column-check fallback.

In Tier 2 this becomes a real LLM judge call into phantom-mesh's Hermes
Curator (or an embedded distilled judge model). For Tier 1 we expose the
right interface so downstream code (``cli.py``, ``dataset.py``) doesn't
need to change later.

The judge is intentionally permissive in Tier 1: if a row already carries
``judged_success == 1`` or a ``hermes_score >= threshold`` it passes; if
those columns are absent we let it through too (the dataset extractor will
have already filtered to ``judged_success = 1`` when the schema supports
it). The point of this module is to be the single chokepoint where a real
Curator can be plugged in later.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

DEFAULT_SCORE_THRESHOLD = 0.6


def is_success(row: dict[str, Any], *, threshold: float = DEFAULT_SCORE_THRESHOLD) -> bool:
    """Tier 1 heuristic: success unless we have evidence otherwise."""
    if row.get("tests") or row.get("reference"):
        from phantom_training.hermetic_judge import judge_task

        return judge_task(row, threshold=threshold)["accepted"]

    judged = row.get("judged_success")
    if judged is not None:
        try:
            if int(judged) != 1:
                return False
        except (TypeError, ValueError):
            return False
    score = row.get("hermes_score")
    if score is not None:
        try:
            return float(score) >= threshold
        except (TypeError, ValueError):
            return True
    return True


def filter_success_cases(
    rows: Iterable[dict[str, Any]],
    *,
    threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> Iterator[dict[str, Any]]:
    """Yield only rows the Curator considers successful."""
    for r in rows:
        if is_success(r, threshold=threshold):
            yield r
