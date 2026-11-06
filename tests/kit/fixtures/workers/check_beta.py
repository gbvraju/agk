"""An invented fixture test file: one pass and one skip (SPEC-0044 rule 6)."""

import pytest


def test_joins():
    assert "-".join(["a", "b"]) == "a-b"


@pytest.mark.skip(reason="skipped on purpose")
def test_skipped():
    raise AssertionError("never runs")
