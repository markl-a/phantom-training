from __future__ import annotations

import json

import pytest

from phantom_training import cli


def _write_dataset(path) -> None:
    rows = [
        {"instruction": "first task", "input": "", "output": "first answer"},
        {"instruction": "second task", "input": "", "output": "second answer"},
        {"instruction": "third task", "input": "", "output": "third answer"},
    ]
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_invalid_recipe_rejected_exit_2(tmp_path, capsys):
    recipe = tmp_path / "bad.toml"
    recipe.write_text("lora_rank = 0\nlr = 1.5\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "--skill",
                "rust-coder",
                "--base",
                "m",
                "--dry-run",
                "--recipe",
                str(recipe),
                "--db",
                str(tmp_path / "missing.db"),
            ]
        )

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "invalid recipe" in err
    assert "lora_rank" in err


def test_malformed_toml_recipe_exit_2(tmp_path, capsys):
    recipe = tmp_path / "malformed.toml"
    recipe.write_text("this is = = not toml", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "--skill",
                "rust-coder",
                "--base",
                "m",
                "--dry-run",
                "--recipe",
                str(recipe),
                "--db",
                str(tmp_path / "missing.db"),
            ]
        )

    assert exc.value.code == 2
    assert "not valid TOML" in capsys.readouterr().err


def test_valid_recipe_accepted(tmp_path, capsys):
    recipe = tmp_path / "valid.toml"
    recipe.write_text("lora_rank = 16\nlr = 0.0002\nepochs = 3\n", encoding="utf-8")

    rc = cli.main(
        [
            "--skill",
            "rust-coder",
            "--base",
            "m",
            "--recipe",
            str(recipe),
            "--json",
            "--db",
            str(tmp_path / "missing.db"),
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["lora"]["rank"] == 16


def test_eval_invalid_holdout_fraction_exit_2(tmp_path, capsys):
    dataset = tmp_path / "dataset.jsonl"
    _write_dataset(dataset)

    rc = cli.main(["eval", "--dataset", str(dataset), "--holdout-fraction", "1.5"])

    assert rc == 2
    assert "holdout-fraction" in capsys.readouterr().err


def test_evaluate_function_rejects_bad_holdout(tmp_path):
    from phantom_training.eval import evaluate

    dataset = tmp_path / "dataset.jsonl"
    _write_dataset(dataset)

    too_high = evaluate(dataset, holdout_fraction=1.5)
    assert "error" in too_high
    assert "holdout_fraction" in too_high["error"]

    too_low = evaluate(dataset, holdout_fraction=0.0)
    assert "error" in too_low
    assert "holdout_fraction" in too_low["error"]

    valid = evaluate(dataset, holdout_fraction=0.3)
    assert "error" not in valid
