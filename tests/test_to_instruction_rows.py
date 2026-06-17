from phantom_training.dataset import to_instruction_rows


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
