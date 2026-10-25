"""`watch --pr` ends at once on a verdict or a correction it would otherwise miss (brief #210 (b)).

A verdict that names the current head, or a `Correction:`, posted after the last `Report:` of the
pull request's author and before the watch started, was never seen: the watch only ends on comments
newer than the newest one it sees at start, and a session waited silently. At start it now ends at
once, printing the same line, when the latest verdict by a listed author names the current head
(an older verdict on a previous head never does). `--since <comment id>` marks what the session has
already acted on. A `gh` stub on `PATH`, saved responses, no network.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_session import (
    BRIEF,
    PR,
    PR_COMMENTS,
    SHA,
    comment,
    fresh,
    pull,
    session,
    watching,
    with_brief,
)
from test_session import (
    proj as session_proj,  # noqa: F401  (the fixtures of test_session)
)
from test_session import (
    stub as session_stub,  # noqa: F401
)

ROOT = Path(__file__).resolve().parents[2]
OLD = "0123456789abcdef0123456789abcdef01234567"
WATCH = ("watch", "--pr", "7", "--interval", "0", "--timeout", "0")


@pytest.fixture
def stub(request):
    return request.getfixturevalue("session_stub")


@pytest.fixture
def proj(request):
    return request.getfixturevalue("session_proj")


def report(cid: int = 1, login: str = "builder") -> dict:
    return comment(cid, login, "Report: abc1234 pushed; CI pending")


def verdict(cid: int, sha: str = SHA, login: str = "boss", kind: str = "cleared") -> dict:
    return comment(cid, login, f"Verdict: {kind} {sha[:7]}")


def start(stub, comments: list, p: dict | None = None) -> None:
    """The watch starts with `comments` already on the pull request."""
    watching(stub, [(p or pull(), comments)], base=comments)


def run(proj, stub, *extra: str):
    return session(proj, stub, *WATCH, *extra)


def test_ac_a_verdict_naming_the_head_posted_before_the_watch_ends_it_at_once(proj, stub):
    """Brief #210 (b): the verdict landed between the push and the start of the watch."""
    start(stub, [report(), verdict(2)])
    out = run(proj, stub)
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.strip() == f"verdict cleared {SHA[:7]} (comment 2)"


def test_ac_a_fix_list_is_printed_the_same_way(proj, stub):
    """Brief #210 (b): the line is the one the watch prints for a verdict it sees later."""
    start(stub, [report(), verdict(2, kind="fix list")])
    assert run(proj, stub).stdout.strip() == f"verdict fix list {SHA[:7]} (comment 2)"


def test_ac_an_older_verdict_on_a_previous_head_does_not_end_the_watch(proj, stub):
    """Brief #210 (b): a verdict that names another head is not about the current head."""
    start(stub, [report(), verdict(2, OLD)])
    out = run(proj, stub)
    assert out.returncode == 3 and out.stdout.strip() == "timeout"


def test_ac_only_the_latest_verdict_counts(proj, stub):
    """Brief #210 (b): the latest verdict by a listed author decides."""
    start(stub, [report(), verdict(2), verdict(3, OLD)])
    assert run(proj, stub).returncode == 3
    fresh(stub)
    start(stub, [report(), verdict(2, OLD), verdict(3)])
    assert run(proj, stub).stdout.strip() == f"verdict cleared {SHA[:7]} (comment 3)"


def test_ac_a_verdict_before_the_last_report_was_already_acted_on(proj, stub):
    """Brief #210 (b): the session pushed and reported after it; the report is the floor."""
    start(stub, [verdict(1), report(2)])
    assert run(proj, stub).returncode == 3


def test_ac_the_report_of_another_account_is_not_the_floor(proj, stub):
    """Brief #210 (b): only the Report: of the pull request's author sets it."""
    start(stub, [verdict(1), report(2, "stranger")])
    assert run(proj, stub).stdout.strip() == f"verdict cleared {SHA[:7]} (comment 1)"


def test_ac_a_verdict_of_an_unlisted_author_does_not_end_it(proj, stub):
    """Brief #210 (b): only a listed verdict author counts."""
    start(stub, [report(), verdict(2, login="stranger")])
    assert run(proj, stub).returncode == 3


def test_ac_without_any_report_a_verdict_for_the_head_ends_it(proj, stub):
    """Brief #210 (b): a pull request with no Report: yet has no floor."""
    start(stub, [verdict(1)])
    assert run(proj, stub).stdout.strip() == f"verdict cleared {SHA[:7]} (comment 1)"


def test_ac_since_marks_what_the_session_has_already_acted_on(proj, stub):
    """Brief #210 (b): `--since <id>` so that a restart does not report the same verdict again."""
    start(stub, [report(), verdict(2)])
    assert run(proj, stub, "--since", "2").returncode == 3
    fresh(stub)
    start(stub, [report(), verdict(2)])
    assert run(proj, stub, "--since", "1").stdout.startswith("verdict cleared")


@pytest.mark.parametrize("value", ["x", "-1", "1.5", ""])
def test_ac_since_needs_a_comment_id(proj, stub, value):
    """Brief #210 (b): usage."""
    assert run(proj, stub, "--since", value).returncode == 2


def test_ac_since_belongs_to_watch_pr_only(proj, stub):
    """Brief #210 (b): `--merged` ignores comments, so it takes no `--since`."""
    out = session(proj, stub, "watch", "--merged", "7", "--since", "3")
    assert out.returncode == 2


def test_ac_a_correction_newer_than_the_report_ends_it_at_once(proj, stub):
    """Brief #210 (b): a Correction: it would otherwise miss."""
    fix = comment(5, "boss", "Correction: the cause was a cache; the check stands")
    start(stub, [report(), fix])
    out = run(proj, stub)
    assert (
        out.stdout.strip()
        == "correction #7 (comment 5): Correction: the cause was a cache; the check stands"
    )


def test_ac_a_correction_of_an_unlisted_author_or_before_the_report_does_not(proj, stub):
    """Brief #210 (b): only a listed author, only after the report."""
    start(stub, [report(), comment(5, "stranger", "Correction: no")])
    assert run(proj, stub).returncode == 3
    start(stub, [comment(1, "boss", "Correction: old"), report(2)])
    assert run(proj, stub).returncode == 3


def test_ac_the_verdict_comes_before_the_correction(proj, stub):
    """Brief #210 (b): one event, the verdict first."""
    start(stub, [report(), comment(3, "boss", "Correction: x; y"), verdict(4)])
    assert run(proj, stub).stdout.startswith("verdict cleared")


def test_ac_a_correction_on_the_brief_newer_than_the_report_ends_it_at_once(proj, stub):
    """Brief #210 (b): the brief named by the `Brief: #n` line."""
    fix = comment(9, "boss", "Correction: the cause was another; the order stands")
    stub.serve(PR_COMMENTS, [report()], nth=1)
    stub.serve(PR, with_brief(), nth=1)
    stub.serve(PR_COMMENTS, [report()], nth=2)
    stub.serve(BRIEF, [comment(3, "boss", "an old note"), fix], nth=1)
    out = run(proj, stub)
    assert out.stdout.strip().startswith("correction #5 (comment 9): Correction: the cause")


def test_ac_an_old_correction_on_the_brief_does_not_end_it(proj, stub):
    """Brief #210 (b): older than the last report."""
    stub.serve(PR_COMMENTS, [report(10)], nth=1)
    stub.serve(PR, with_brief(), nth=1)
    stub.serve(PR_COMMENTS, [report(10)], nth=2)
    stub.serve(BRIEF, [comment(9, "boss", "Correction: before the push")], nth=1)
    assert run(proj, stub).returncode == 3


def test_ac_the_check_only_gets(proj, stub):
    """Brief #210 (b): GET only."""
    start(stub, [report(), verdict(2)])
    run(proj, stub)
    assert stub.calls() and all(call[0] == "GET" for call in stub.calls())


def test_ac_the_rules_and_the_guide_say_how_to_wait_after_a_verdict():
    """Brief #210 (b): a restart after a verdict names it with --since."""
    rules = " ".join((ROOT / "config" / "session-rules.md").read_text(encoding="utf-8").split())
    assert "ends at once" in rules and "`--since <comment id>`" in rules
    assert "already acted on" in rules
    guide = (ROOT / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")
    assert "--since" in guide
