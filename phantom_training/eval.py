"""Dependency-free held-out eval for an instruction-tuning JSONL dataset.

This is a *lightweight proxy* metric, NOT a public benchmark and NOT a model
evaluation — no GPU, no model download, no finetune. It answers a concrete,
honest question: "given the training split, how well does a trivial retrieval
baseline reproduce the held-out gold outputs?"

Method
------
1. Load alpaca rows ``{instruction, input, output}`` from JSONL.
2. Deterministically split into train / held-out (default 20% held out).
3. Baseline: for each held-out instruction, retrieve the *train* example whose
   instruction has the highest token-overlap (Jaccard) and predict its output.
4. Score the predicted output against the held-out gold output with:
     * exact_match  (string equality after whitespace normalisation)
     * token_f1     (mean token-level F1, the SQuAD-style overlap metric)

The number is real and computed from the data. It is deliberately a floor:
a trivial retriever, so any future finetune must beat it to be worth shipping.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_WORD = re.compile(r"\w+")


def _tokens(text: str) -> list[str]:
    return _WORD.findall((text or "").lower())


def load_jsonl(path: Path | str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as fp:
        for lineno, line in enumerate(fp, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"malformed JSON on line {lineno}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(
                    f"line {lineno}: expected a JSON object, got {type(row).__name__}"
                )
            rows.append(row)
    return rows


def _split(rows: list[dict[str, Any]], holdout_fraction: float) -> tuple[list, list]:
    """Deterministic interleaved split (no RNG → reproducible numbers)."""
    n = len(rows)
    k = max(1, round(n * holdout_fraction)) if n else 0
    if n and k >= n:
        k = n - 1  # always keep at least one train row to retrieve from
    # take every (n//k)-th row as held-out for an even, deterministic spread
    step = max(1, n // k) if k else 1
    held, train = [], []
    for i, r in enumerate(rows):
        (held if (k and i % step == 0 and len(held) < k) else train).append(r)
    if not train:  # pragma: no cover - defensive; unreachable given the k=n-1 clamp
        train = held[:1]
        held = held[1:]
    return train, held


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _exact_match(pred: str, gold: str) -> bool:
    return " ".join((pred or "").split()) == " ".join((gold or "").split())


def _token_f1(pred: str, gold: str) -> float:
    pt, gt = _tokens(pred), _tokens(gold)
    if not pt and not gt:
        return 1.0
    if not pt or not gt:
        return 0.0
    gt_counts: dict[str, int] = {}
    for t in gt:
        gt_counts[t] = gt_counts.get(t, 0) + 1
    overlap = 0
    seen: dict[str, int] = {}
    for t in pt:
        seen[t] = seen.get(t, 0) + 1
        if seen[t] <= gt_counts.get(t, 0):
            overlap += 1
    if overlap == 0:
        return 0.0
    precision = overlap / len(pt)
    recall = overlap / len(gt)
    return 2 * precision * recall / (precision + recall)


def _retrieve(instruction: str, train: list[dict[str, Any]]) -> dict[str, Any]:
    q = set(_tokens(instruction))
    best, best_score = train[0], -1.0
    for r in train:
        s = _jaccard(q, set(_tokens(r.get("instruction", ""))))
        if s > best_score:
            best, best_score = r, s
    return best


def evaluate(path: Path | str, *, holdout_fraction: float = 0.2) -> dict[str, Any]:
    if not (0.0 < holdout_fraction < 1.0):
        return {
            "n_rows": 0,
            "error": f"holdout_fraction must satisfy 0.0 < x < 1.0, got {holdout_fraction}",
        }
    try:
        rows = load_jsonl(path)
    except (ValueError, OSError) as exc:
        # Corrupt / unreadable dataset: report cleanly via the same structured
        # error path as the "too few rows" case rather than crashing the CLI.
        return {"n_rows": 0, "error": str(exc)}
    if len(rows) < 2:
        return {
            "n_rows": len(rows),
            "error": "need >=2 rows to form a held-out split",
        }
    train, held = _split(rows, holdout_fraction)

    em_hits = 0
    f1_sum = 0.0
    samples: list[dict[str, Any]] = []
    for r in held:
        pred = _retrieve(r.get("instruction", ""), train)
        pred_out = pred.get("output", "")
        gold_out = r.get("output", "")
        em = _exact_match(pred_out, gold_out)
        f1 = _token_f1(pred_out, gold_out)
        em_hits += int(em)
        f1_sum += f1
        if len(samples) < 3:
            samples.append(
                {
                    "instruction": r.get("instruction", "")[:80],
                    "exact_match": em,
                    "token_f1": round(f1, 4),
                }
            )

    n_held = len(held)
    return {
        "n_rows": len(rows),
        "n_train": len(train),
        "n_holdout": n_held,
        "baseline": "nearest-instruction retrieval (token Jaccard)",
        "exact_match": round(em_hits / n_held, 4) if n_held else 0.0,
        "token_f1": round(f1_sum / n_held, 4) if n_held else 0.0,
        "holdout_fraction": holdout_fraction,
        "samples": samples,
    }
