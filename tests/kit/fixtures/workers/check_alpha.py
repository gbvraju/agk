"""An invented fixture test file: one pass and one failure (SPEC-0044 rule 6)."""


def test_adds():
    assert 1 + 1 == 2


def test_fails_on_purpose():
    assert "example.com".upper() == "example.com"
