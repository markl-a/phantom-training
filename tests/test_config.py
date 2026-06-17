from __future__ import annotations

import pytest

from phantom_training.config import RecipeError, assert_valid_recipe, validate_recipe


def test_valid_full_rust_coder_recipe_returns_empty_list():
    recipe = {
        "skill_name": "rust-coder",
        "base_model": "qwen2.5-coder-7b",
        "backend": "unsloth",
        "lora_rank": 32,
        "lora_alpha": 64,
        "lora_dropout": 0.05,
        "target_modules": ["q_proj", "k_proj", "v_proj"],
        "lr": 2.0e-4,
        "epochs": 3,
        "batch_size": 4,
        "grad_accum": 4,
        "warmup_steps": 20,
        "weight_decay": 0.01,
        "holdout_fraction": 0.1,
        "max_seq_len": 4096,
        "min_response_len": 32,
        "benchmarks": ["HumanEval", "MBPP", "RustBench"],
        "pass_threshold": 0.55,
        "prefer_node": "local-mac",
        "fallback_node": "mesh-gpu",
        "publish_skill_as": "rust-coder-v2",
        "require_commit_signoff": True,
    }

    assert validate_recipe(recipe) == []


@pytest.mark.parametrize(
    ("recipe", "expected"),
    [
        ({"lora_rank": 0}, "lora_rank must be an integer >= 1, got 0"),
        ({"lora_rank": True}, "lora_rank must be an integer >= 1, got True"),
        ({"lora_alpha": 0}, "lora_alpha must be an integer >= 1, got 0"),
        ({"lora_dropout": 1.0}, "lora_dropout must be a number in [0.0, 1.0), got 1.0"),
        ({"lr": 0}, "lr must be a number with 0 < lr < 1.0, got 0"),
        ({"lr": 1.5}, "lr must be a number with 0 < lr < 1.0, got 1.5"),
        ({"epochs": 0}, "epochs must be an integer >= 1, got 0"),
        ({"batch_size": 0}, "batch_size must be an integer >= 1, got 0"),
        ({"grad_accum": 0}, "grad_accum must be an integer >= 1, got 0"),
        ({"holdout_fraction": 0.0}, "holdout_fraction must be a number with 0.0 < x < 1.0, got 0.0"),
        ({"holdout_fraction": 1.0}, "holdout_fraction must be a number with 0.0 < x < 1.0, got 1.0"),
        ({"warmup_steps": -1}, "warmup_steps must be an integer >= 0, got -1"),
        ({"weight_decay": -0.1}, "weight_decay must be a number >= 0.0, got -0.1"),
        ({"max_seq_len": 0}, "max_seq_len must be an integer >= 1, got 0"),
        ({"pass_threshold": -0.1}, "pass_threshold must be a number in [0.0, 1.0], got -0.1"),
        ({"pass_threshold": 1.1}, "pass_threshold must be a number in [0.0, 1.0], got 1.1"),
        ({"benchmarks": [""]}, "benchmarks[0] must be a non-empty string, got ''"),
    ],
)
def test_invalid_recipe_values_are_reported(recipe, expected):
    assert validate_recipe(recipe) == [expected]


def test_string_numeric_field_is_reported_not_raised():
    assert validate_recipe({"lr": "fast"}) == ["lr must be a number with 0 < lr < 1.0, got 'fast'"]


def test_benchmarks_must_be_a_list():
    # a bare string is not a list of benchmark names -> reported, not crashed
    problems = validate_recipe({"benchmarks": "HumanEval"})
    assert problems == ["benchmarks must be a list of non-empty strings, got 'HumanEval'"]


def test_benchmarks_non_string_item_reported():
    problems = validate_recipe({"benchmarks": ["HumanEval", 7]})
    assert problems == ["benchmarks[1] must be a non-empty string, got 7"]


def test_unknown_keys_are_ignored():
    assert validate_recipe({"future_knob": object()}) == []


def test_empty_recipe_is_valid():
    assert validate_recipe({}) == []


def test_assert_valid_recipe_raises_recipe_error_on_bad_recipe():
    with pytest.raises(RecipeError) as exc:
        assert_valid_recipe({"lora_rank": 0, "lr": 1.5})

    assert str(exc.value) == (
        "lora_rank must be an integer >= 1, got 0; "
        "lr must be a number with 0 < lr < 1.0, got 1.5"
    )


def test_assert_valid_recipe_is_silent_on_good_recipe():
    assert_valid_recipe({"lora_rank": 1, "lr": 0.001})
