"""Recipe validation for phantom-training (Tier 1, stdlib-only).

A "recipe" is the TOML dict loaded by ``cli.py`` (see ``examples/rust-coder.toml``).
Every key is optional — the planner fills sane defaults — but when a key *is*
present we want to catch obviously-broken values (``lora_rank=0``,
``lr=1.5``, ``holdout_fraction=1.0``) instead of silently emitting a nonsense
plan. This module is the single chokepoint for that check.

Design notes
------------
* Pure / dependency-free / never crashes on a malformed dict: ``validate_recipe``
  always returns a list of human-readable problem strings (empty == valid).
* Unknown keys are allowed (forward-compat) and are *not* validated.
* ``bool`` is a subclass of ``int`` in Python, so ``True``/``False`` are
  rejected where a real integer is expected.

Public surface:

* ``validate_recipe(recipe) -> list[str]``
* ``assert_valid_recipe(recipe) -> None``  (raises :class:`RecipeError`)
"""

from __future__ import annotations

from typing import Any


class RecipeError(ValueError):
    """Raised by :func:`assert_valid_recipe` when a recipe is out of range."""


def _is_real_int(value: Any) -> bool:
    """True only for genuine ints (``bool`` is rejected on purpose)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    """True for int/float but not bool (a number for range checks)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_int_min(recipe: dict[str, Any], key: str, minimum: int, problems: list[str]) -> None:
    if key not in recipe:
        return
    v = recipe[key]
    if not _is_real_int(v) or v < minimum:
        problems.append(f"{key} must be an integer >= {minimum}, got {v!r}")


def validate_recipe(recipe: dict[str, Any]) -> list[str]:
    """Return a list of problem strings for ``recipe`` (empty == valid).

    Only keys that are *present* are checked; every key is optional. Never
    raises — non-numeric values where a number is expected are reported, not
    propagated.
    """
    problems: list[str] = []

    # --- integer fields, >= 1 ---
    for key in ("lora_rank", "lora_alpha", "epochs", "batch_size", "grad_accum", "max_seq_len"):
        _check_int_min(recipe, key, 1, problems)

    # --- integer fields, >= 0 ---
    _check_int_min(recipe, "warmup_steps", 0, problems)

    # --- lora_dropout: float in [0.0, 1.0) ---
    if "lora_dropout" in recipe:
        v = recipe["lora_dropout"]
        if not _is_number(v) or not (0.0 <= v < 1.0):
            problems.append(f"lora_dropout must be a number in [0.0, 1.0), got {v!r}")

    # --- lr: 0 < lr < 1.0 ---
    if "lr" in recipe:
        v = recipe["lr"]
        if not _is_number(v) or not (0 < v < 1.0):
            problems.append(f"lr must be a number with 0 < lr < 1.0, got {v!r}")

    # --- holdout_fraction: 0.0 < x < 1.0 ---
    if "holdout_fraction" in recipe:
        v = recipe["holdout_fraction"]
        if not _is_number(v) or not (0.0 < v < 1.0):
            problems.append(f"holdout_fraction must be a number with 0.0 < x < 1.0, got {v!r}")

    # --- weight_decay: >= 0.0 ---
    if "weight_decay" in recipe:
        v = recipe["weight_decay"]
        if not _is_number(v) or v < 0.0:
            problems.append(f"weight_decay must be a number >= 0.0, got {v!r}")

    # --- pass_threshold: [0.0, 1.0] ---
    if "pass_threshold" in recipe:
        v = recipe["pass_threshold"]
        if not _is_number(v) or not (0.0 <= v <= 1.0):
            problems.append(f"pass_threshold must be a number in [0.0, 1.0], got {v!r}")

    # --- benchmarks: list of non-empty strings ---
    if "benchmarks" in recipe:
        v = recipe["benchmarks"]
        if not isinstance(v, list):
            problems.append(f"benchmarks must be a list of non-empty strings, got {v!r}")
        else:
            for i, item in enumerate(v):
                if not isinstance(item, str) or not item:
                    problems.append(f"benchmarks[{i}] must be a non-empty string, got {item!r}")

    return problems


def assert_valid_recipe(recipe: dict[str, Any]) -> None:
    """Raise :class:`RecipeError` joining all problems, or return silently."""
    problems = validate_recipe(recipe)
    if problems:
        raise RecipeError("; ".join(problems))
