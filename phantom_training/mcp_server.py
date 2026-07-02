"""MCP server: honest training-eval tool for phantom-mesh.

Exposes a single ``training_eval`` function (no MCP protocol bindings here —
just the business logic that an MCP tool call would dispatch to).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import eval as _eval

METRIC_KIND = "retrieval-floor"
DISCLAIMER = (
    "Retrieval floor over held-out rows: a trivial Jaccard-nearest-instruction "
    "baseline with exact_match + token_f1. A finetune must beat this before it "
    "is worth shipping. No model was trained for this evaluation."
)


def training_eval(path: str | Path, **kwargs: Any) -> dict[str, Any]:
    """Evaluate a JSONL dataset and return an honest assessment.

    Wraps :func:`eval.evaluate` with structured metadata fields
    (``metric_kind``, ``trained_model``, ``disclaimer``) so consumers see
    at a glance what the number means and does *not* mean.

    Never raises — returns the same envelope even on a corrupt or too-small
    dataset.
    """
    result = _eval.evaluate(path, **kwargs)
    result["metric_kind"] = METRIC_KIND
    result["trained_model"] = False
    result["disclaimer"] = DISCLAIMER
    return result
