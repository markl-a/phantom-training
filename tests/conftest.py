"""Shared test fixtures for the phantom-training suite.

Hermeticity guard: ``extract_from_recall`` shells out to the ``phantom`` binary
when one is found on ``PATH`` (``dataset.shutil.which("phantom")``). On a clean
CI runner there is no ``phantom`` so the call degrades to ``[]`` and the suite is
offline. But on a developer machine where ``phantom`` IS on ``PATH`` (common
here), the planner/entrypoint tests that drive ``cli.main()`` with a missing DB
would issue a REAL ``phantom recall`` subprocess against live, nondeterministic
local timeline state — contradicting the suite's "fully hermetic, no subprocess"
contract.

This autouse fixture forces ``which("phantom")`` to ``None`` by default, so every
test is hermetic regardless of ``PATH``. Tests that specifically exercise the
recall subprocess path (``test_dataset_recall.py``) re-monkeypatch
``dataset.shutil.which`` themselves; their explicit per-test ``setattr`` runs
after this fixture and therefore wins. Lookups for any binary other than
``phantom`` are delegated to the real ``shutil.which`` so unrelated logic is
unaffected.
"""

import pytest

from phantom_training import dataset


@pytest.fixture(autouse=True)
def _offline_phantom_recall_by_default(monkeypatch):
    real_which = dataset.shutil.which

    def _which(name, *args, **kwargs):
        if name == "phantom":
            return None
        return real_which(name, *args, **kwargs)

    monkeypatch.setattr(dataset.shutil, "which", _which)
