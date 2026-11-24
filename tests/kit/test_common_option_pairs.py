"""Tests of `common.option_pairs`: a command line's options read two by two (brief #1886, ADR-0780).

REQ-014: the shipped kit scripts read `--flag value` pairs through one helper instead of a slice
that steps by two, which the data guard reads as an address, so the plugin snapshot passes the
unchanged guard. The helper gives what `zip(args[::2], args[1::2], strict=...)` gave: with
`strict=True` an odd count raises `ValueError`, with `strict=False` the last item is dropped.
Pure functions only: no files, no network.
"""

from __future__ import annotations

import itertools
import re

import common
import pytest

# Every form the replaced call sites used, as (the list, where the pairs start, strict).
FORMS = [
    (["--pr", "12", "--sha", "abc"], 0, True),
    (["--pr", "12", "--sha", "abc"], 0, False),
    (["--pr", "12", "--sha"], 0, False),
    (["cmd", "--pr", "12", "--session", "s1"], 1, False),
    (["cmd", "--pr", "12", "--session"], 1, False),
    (["cmd", "sub", "--a", "1", "--b", "2"], 2, True),
]


def old(args: list[str], start: int, strict: bool) -> list[tuple[str, str]]:
    """The replaced form, built by islice so this file holds no stepped slice either."""
    rest = args[start:]
    firsts = list(itertools.islice(rest, 0, None, 2))
    seconds = list(itertools.islice(rest, 1, None, 2))
    return list(zip(firsts, seconds, strict=strict))


def test_req014_pairs_read_two_by_two():
    """REQ-014 brief #1886 answer 3a: pairs `args[0], args[1]`, `args[2], args[3]`, ..."""
    pairs = common.option_pairs(["--a", "1", "--b", "2"], strict=True)
    assert pairs == [("--a", "1"), ("--b", "2")]
    assert dict(pairs) == {"--a": "1", "--b": "2"}


def test_req014_an_odd_count_raises_when_strict():
    """REQ-014 brief #1886 answer 6: `strict=True` raises on an odd count, as zip does."""
    with pytest.raises(ValueError):
        common.option_pairs(["--a", "1", "--b"], strict=True)


def test_req014_an_odd_count_drops_the_last_when_not_strict():
    """REQ-014 brief #1886 answer 6: `strict=False` drops the last item."""
    assert common.option_pairs(["--a", "1", "--b"], strict=False) == [("--a", "1")]


def test_req014_an_empty_list_gives_no_pairs():
    """REQ-014 brief #1886 answer 6: an empty list gives `{}`."""
    assert dict(common.option_pairs([], strict=True)) == {}
    assert dict(common.option_pairs([], strict=False)) == {}


@pytest.mark.parametrize("args,start,strict", FORMS)
def test_req014_every_call_site_form_gives_what_the_slice_gave(args, start, strict):
    """REQ-014 brief #1886 answer 3a: the forms of the call sites, the same pairs as before."""
    assert common.option_pairs(args[start:], strict=strict) == old(args, start, strict)


def test_req014_the_strict_odd_form_raises_like_the_slice():
    """REQ-014 brief #1886 answer 6: the strict odd case raises in both forms."""
    with pytest.raises(ValueError):
        old(["--a", "1", "--b"], 0, True)
    with pytest.raises(ValueError):
        common.option_pairs(["--a", "1", "--b"], strict=True)


def test_req014_strict_is_a_keyword():
    """REQ-014 brief #1886 answer 3a: a call names `strict`, so no site reads as the other."""
    with pytest.raises(TypeError):
        common.option_pairs(["--a", "1"], True)


def test_req014_no_shipped_script_steps_a_slice_by_two():
    """REQ-014 brief #1886 answer 3a: no `x[::2]`-style slice is left in the kit's scripts."""
    from pathlib import Path

    root = Path(common.__file__).resolve().parent
    stepped = re.compile(r"\[\d*::2\]")
    found = [p.name for p in sorted(root.glob("*.py")) if stepped.search(p.read_text("utf-8"))]
    assert found == []
