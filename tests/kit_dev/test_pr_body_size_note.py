"""Kit-only tests of the size note of a printed pull request body (brief #1270 answer 2; REQ-050).

`pr_body.print_body` prints one information line when the body passes 1,500 characters outside its
`Verified:` lines, and nothing more: the exit, the fields and the check are unchanged. Invented text
only; no network, no model.
"""

from __future__ import annotations

import sys

from conftest import KIT_ROOT

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import pr_body  # noqa: E402

HEAD = "Summary: Reviews read a short body first.\nAdvances: REQ-050\n"
VERIFIED = "Verified:\n- python3 -m pytest -q tests/kit/test_example.py: 3 passed\n"


def test_a_a_short_body_gets_no_note(tmp_path, capsys):
    """REQ-050: brief #1270 answer 4 (a), under the limit."""
    text = HEAD + VERIFIED
    assert pr_body.outside_verified(text) < pr_body.BODY_NOTE_LIMIT
    assert pr_body.size_note(text) is None
    path = tmp_path / "pr-body.md"
    pr_body.print_body(path, text)
    assert "characters; the summary-first form" not in capsys.readouterr().out


def test_a_a_long_body_prints_one_information_line(tmp_path, capsys):
    """REQ-050: brief #1270 answer 4 (a), over the limit outside `Verified:`."""
    text = HEAD + "Decisions taken:\n" + "- a decision written at length\n" * 60 + VERIFIED
    n = pr_body.outside_verified(text)
    assert n > 1500
    note = f"pr body: {n} characters; the summary-first form keeps it under 1,500"
    assert pr_body.size_note(text) == note
    pr_body.print_body(tmp_path / "pr-body.md", text)
    out = capsys.readouterr().out
    assert out.count(note) == 1 and text in out


def test_a_the_verified_lines_do_not_count(tmp_path, capsys):
    """REQ-050: brief #1270 answer 4 (a), a long `Verified:` alone gives no note."""
    long_verified = "Verified:\n" + "- python3 -m pytest -q tests/kit/test_x.py: 9 passed\n" * 80
    text = HEAD + long_verified + "Questions:\n- none\n"
    assert len(text) > 1500
    assert pr_body.outside_verified(text) == len(HEAD + "Questions:\n- none\n")
    assert pr_body.size_note(text) is None
    pr_body.print_body(tmp_path / "pr-body.md", text)
    assert "pr body:" not in capsys.readouterr().out
