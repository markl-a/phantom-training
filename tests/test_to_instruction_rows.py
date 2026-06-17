from phantom_training.dataset import dedupe_instruction_rows, to_instruction_rows


def test_strips_whitespace():
    rows = [{"prompt": "  p  ", "response": "  r  "}]

    assert to_instruction_rows(rows) == [{"instruction": "p", "input": "", "output": "r"}]


def test_drops_none_and_blank():
    rows = [
        {"prompt": None, "response": "r"},
        {"prompt": "   ", "response": "r"},
        {"prompt": "p", "response": None},
        {"prompt": "p", "response": ""},
        {},
    ]

    assert to_instruction_rows(rows) == []


def test_coerces_int_without_crashing():
    rows = [{"prompt": 5, "response": "r"}]

    assert to_instruction_rows(rows) == [{"instruction": "5", "input": "", "output": "r"}]


def test_coerces_both_numeric():
    rows = [{"prompt": 1, "response": 2}]

    assert to_instruction_rows(rows) == [{"instruction": "1", "input": "", "output": "2"}]


def test_missing_keys_skipped():
    assert to_instruction_rows([{}]) == []


def test_falsy_values_are_dropped():
    # Original (value or "").strip() semantics: falsy non-None values collapse
    # to empty and are dropped — we preserve that, we just don't crash.
    assert to_instruction_rows([{"prompt": 0, "response": "r"}]) == []
    assert to_instruction_rows([{"prompt": "p", "response": 0}]) == []
    assert to_instruction_rows([{"prompt": False, "response": "r"}]) == []
    assert to_instruction_rows([{"prompt": "p", "response": 0.0}]) == []


def test_decodes_bytes_leniently():
    rows = [{"prompt": b"hello", "response": "r"}]

    assert to_instruction_rows(rows) == [{"instruction": "hello", "input": "", "output": "r"}]


def test_pathological_object_does_not_crash():
    class _Bad:
        def __bool__(self):
            raise RuntimeError("boom-bool")

        def __str__(self):
            raise RuntimeError("boom-str")

    # Must never crash the planner — the bad value is treated as no usable
    # text and the row is dropped.
    assert to_instruction_rows([{"prompt": _Bad(), "response": "r"}]) == []


def test_dedupe_drops_exact_duplicates_preserving_order():
    rows = [
        {"instruction": "a", "input": "", "output": "1"},
        {"instruction": "b", "input": "", "output": "2"},
        {"instruction": "a", "input": "", "output": "1"},  # exact dup of #1
        {"instruction": "c", "input": "", "output": "3"},
    ]
    deduped = dedupe_instruction_rows(rows)
    assert [r["instruction"] for r in deduped] == ["a", "b", "c"]


def test_dedupe_keeps_rows_differing_only_in_output():
    # same instruction but a different output is a distinct training example
    rows = [
        {"instruction": "a", "input": "", "output": "1"},
        {"instruction": "a", "input": "", "output": "2"},
    ]
    assert dedupe_instruction_rows(rows) == rows


def test_dedupe_keeps_rows_differing_only_in_input():
    rows = [
        {"instruction": "a", "input": "ctx1", "output": "1"},
        {"instruction": "a", "input": "ctx2", "output": "1"},
    ]
    assert dedupe_instruction_rows(rows) == rows


def test_dedupe_empty_and_singleton():
    assert dedupe_instruction_rows([]) == []
    one = [{"instruction": "a", "input": "", "output": "1"}]
    assert dedupe_instruction_rows(one) == one


def test_dedupe_is_idempotent():
    rows = [
        {"instruction": "a", "input": "", "output": "1"},
        {"instruction": "a", "input": "", "output": "1"},
    ]
    once = dedupe_instruction_rows(rows)
    assert dedupe_instruction_rows(once) == once
