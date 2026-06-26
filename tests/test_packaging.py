"""Packaging / shipped-artifact regression tests.

These guard the two things a fresh `pip install -e .` user actually touches
first: the console entry point declared in ``pyproject.toml`` and the example
recipe shipped in ``examples/``. Both are easy to break silently — a bad
default in the example recipe would make the CLI ``sys.exit(2)`` for anyone
who copies it, and a renamed ``main`` would break the ``phantom-train`` script.

Fully hermetic: no install step, no network, no subprocess to the real binary.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from phantom_training import cli
from phantom_training.config import validate_recipe

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
EXAMPLES_DIR = REPO_ROOT / "examples"


def test_shipped_example_recipes_are_valid():
    """Every recipe under examples/ must pass validate_recipe with no problems,
    so a user who copies one isn't met with a hard exit(2)."""
    recipes = sorted(EXAMPLES_DIR.glob("*.toml"))
    assert recipes, "expected at least one example recipe to ship"
    for recipe_path in recipes:
        with recipe_path.open("rb") as fp:
            recipe = tomllib.load(fp)
        problems = validate_recipe(recipe)
        assert problems == [], f"{recipe_path.name} is invalid: {problems}"


def test_console_entrypoint_target_is_importable_and_callable():
    """pyproject declares `phantom-train = "phantom_training.cli:main"`. The
    setuptools console-script wrapper does `sys.exit(load_entry_point()())`,
    so the target must (a) exist at that dotted path and (b) be callable and
    return an int exit code."""
    with PYPROJECT.open("rb") as fp:
        pyproject = tomllib.load(fp)
    target = pyproject["project"]["scripts"]["phantom-train"]
    assert target == "phantom_training.cli:main"

    module_path, _, attr = target.partition(":")
    import importlib

    mod = importlib.import_module(module_path)
    entry = getattr(mod, attr)
    assert callable(entry)
    assert entry is cli.main


def test_demo_loop_entrypoint_target_is_importable_and_callable():
    with PYPROJECT.open("rb") as fp:
        pyproject = tomllib.load(fp)
    target = pyproject["project"]["scripts"]["phantom-training-demo-loop"]
    assert target == "phantom_training.demo_loop:main"

    module_path, _, attr = target.partition(":")
    import importlib

    mod = importlib.import_module(module_path)
    entry = getattr(mod, attr)
    assert callable(entry)


def test_console_entrypoint_returns_int_exit_code(tmp_path):
    """The entry point must return an int (not None) so the wrapper's
    `sys.exit(rc)` yields a meaningful process exit status."""
    rc = cli.main(
        [
            "--skill",
            "rust-coder",
            "--base",
            "qwen2.5-coder-7b",
            "--dry-run",
            "--db",
            str(tmp_path / "missing.db"),
        ]
    )
    assert isinstance(rc, int)
    assert rc == 0
