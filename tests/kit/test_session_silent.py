"""A wait of session.py never goes silent (REQ-041, brief #210; SPEC-0034 rules 11 and 12).

Every wait (`watch --pr`, `--merged`, `--assign`) ends with `error: <what> cannot be read` and
exit 4 when GitHub cannot be read for 5 polls in a row; one failure is retried; `--assign` says
what it waits for when it starts. A blocked session posts a `Question:` where the conductor
reads. A `gh` stub on `PATH`, saved responses (a call with no fixture fails), no network.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_session import (
    PR,
    PR_COMMENTS,
    WATCH,
    pull,
    session,
)
from test_session import (
    proj as session_proj,  # noqa: F401  (the fixtures of test_session)
)
from test_session import (
    stub as session_stub,  # noqa: F401
)
from test_session_assign import COMMENTS, CONDUCTOR, CONDUCTOR_ISSUE, assign, comment, request

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "config" / "session-rules.md"
CONDUCTOR_ROLE = ROOT / ".claude" / "agents" / "conductor.md"


@pytest.fixture
def stub(request):
    return request.getfixturevalue("session_stub")


@pytest.fixture
def proj(request):
    return request.getfixturevalue("session_proj")


MERGE = ("watch", "--merged", "7", "--interval", "0", "--timeout", "5")


# --- watch --pr and --merged (answer 1) ---------------------------------------------------------


def test_ac_five_failed_reads_of_the_pull_request_end_the_wait_with_an_error(proj, stub):
    """Brief #210 answer 1: the wait ends with one line and exit 4, never silently."""
    stub.serve(PR_COMMENTS, [], nth=1)
    out = session(proj, stub, *WATCH)
    assert out.returncode == 4, out.stdout + out.stderr
    assert out.stdout.strip() == "error: pull request #7 cannot be read"
    gets = [c for c in stub.calls() if c[1] == PR]
    assert len(gets) == 5


def test_ac_four_failures_then_a_good_read_do_not_end_the_wait(proj, stub):
    """Brief #210 answer 1: a single failure (or four) is retried."""
    stub.serve(PR_COMMENTS, [], nth=1)
    stub.serve(PR, pull("closed"), nth=5)
    out = session(proj, stub, *WATCH)
    assert out.returncode == 0 and out.stdout.strip() == "closed #7"


def test_ac_a_good_read_resets_the_count_of_failures(proj, stub):
    """Brief #210 answer 1: 5 in a row, not 5 in all."""
    stub.serve(PR_COMMENTS, [], nth=1)
    stub.serve(PR, pull(), nth=5)
    stub.serve(PR_COMMENTS, [], nth=2)
    stub.serve(PR, pull("closed"), nth=10)
    out = session(proj, stub, *WATCH)
    assert out.returncode == 0 and out.stdout.strip() == "closed #7", out.stdout


def test_ac_five_failed_reads_of_the_comments_end_the_wait_with_an_error(proj, stub):
    """Brief #210 answer 1: the comments of the pull request, after a good first read."""
    stub.serve(PR_COMMENTS, [], nth=1)
    stub.serve(PR, pull())
    out = session(proj, stub, *WATCH)
    assert out.returncode == 4 and out.stdout.strip() == "error: the comments of #7 cannot be read"


def test_ac_a_baseline_that_cannot_be_read_five_times_is_an_error_too(proj, stub):
    """Brief #210 answer 1: the first read of the comments is part of the wait."""
    out = session(proj, stub, *WATCH)
    assert out.returncode == 4 and out.stdout.strip() == "error: the comments of #7 cannot be read"


def test_ac_watch_merged_ends_with_an_error_after_five_failed_reads(proj, stub):
    """Brief #210 answer 1: --merged waits on the pull request alone."""
    out = session(proj, stub, *MERGE)
    assert out.returncode == 4 and out.stdout.strip() == "error: pull request #7 cannot be read"


def test_ac_watch_merged_retries_one_failure(proj, stub):
    """Brief #210 answer 1."""
    stub.serve(PR, pull(merged="2026-10-25T10:00:00Z"), nth=2)
    out = session(proj, stub, *MERGE)
    assert out.returncode == 0 and out.stdout.strip() == "merged #7"


def test_ac_the_error_line_names_what_and_never_a_value(proj, stub):
    """Brief #210 answer 1 and CLAUDE.md rule 6."""
    out = session(proj, stub, *MERGE)
    assert out.stdout.count("\n") == 1 and "token" not in out.stdout.lower()


# --- watch --assign (answers 1 and 2) ------------------------------------------------------------


def served(stub, first=None):
    stub.serve(CONDUCTOR, [CONDUCTOR_ISSUE])
    if first is not None:
        stub.serve(COMMENTS, first, nth=1)


def test_ac_assign_says_what_it_waits_for_when_it_starts(proj, stub):
    """Brief #210 answer 2: one line `waiting on #<issue> since <request id>`."""
    served(stub, [request(3)])
    out = assign(proj, stub, timeout="0")
    lines = out.stdout.splitlines()
    assert lines[0] == "waiting on #204 since 3" and lines[-1] == "assign-timeout"


def test_ac_assign_without_a_request_waits_since_the_newest_comment(proj, stub):
    """Brief #210 answer 2."""
    served(stub, [comment(8, "boss", "a note")])
    out = assign(proj, stub, timeout="0")
    assert out.stdout.splitlines()[0] == "waiting on #204 since 8"


def test_ac_assign_prints_nothing_more_while_it_waits(proj, stub):
    """Brief #210 answer 2: the polls that do not end it write nothing."""
    served(stub, [request(3)])
    for n in range(2, 6):
        stub.serve(COMMENTS, [request(3)], nth=n)
    stub.serve(COMMENTS, [request(3), comment(9, "boss", "Assign: s-me #7")], nth=6)
    out = assign(proj, stub)
    assert out.stdout.splitlines() == ["waiting on #204 since 3", "assign #7"]


def test_ac_assign_ends_with_an_error_after_five_failed_reads(proj, stub):
    """Brief #210 answer 1: the observed case, a failed read looped silently for 30 minutes."""
    served(stub, [request(3)])
    out = assign(proj, stub)
    assert out.returncode == 4, out.stdout + out.stderr
    assert out.stdout.splitlines()[-1] == "error: the comments of #204 cannot be read"


def test_ac_assign_retries_one_failed_read_and_still_sees_the_answer(proj, stub):
    """Brief #210 answer 1."""
    served(stub, [request(3)])
    stub.serve(COMMENTS, [request(3), comment(9, "boss", "Assign: s-me #7")], nth=3)
    out = assign(proj, stub)
    assert out.returncode == 0 and out.stdout.splitlines()[-1] == "assign #7"


def test_ac_assign_does_not_start_from_an_unread_baseline(proj, stub):
    """Brief #210 answer 1: a failed first read must not make an old Assign line look new."""
    old = comment(1, "boss", "Assign: s-me #3")
    served(stub)
    stub.serve(COMMENTS, [old, request(2)], nth=3)
    out = assign(proj, stub, timeout="0")
    assert out.stdout.splitlines()[0] == "waiting on #204 since 2"
    assert out.stdout.splitlines()[-1] == "assign-timeout"


# --- the rules and the role file (answers 3 and 4) ------------------------------------------------


def test_ac_the_rules_say_a_blocked_session_asks_on_github_never_only_in_its_chat():
    """Brief #210 answer 3."""
    text = " ".join(RULES.read_text(encoding="utf-8").split())
    assert "is blocked for any reason" in text
    assert "`Question: Q-<id> <text>`" in text
    assert "on its brief when it has none" in text
    assert "never asks only in its own chat" in text


def test_ac_the_rules_name_the_designated_branch_case():
    """Brief #210 answer 4."""
    text = " ".join(RULES.read_text(encoding="utf-8").split())
    assert "pushes only the branch its runtime gives it" in text
    assert "opens its pull request from that branch" in text


def test_ac_the_rule_numbers_stay_without_a_gap():
    """Brief #210 answers 3 and 4: the file stays numbered 1, 2, ..."""
    lines = RULES.read_text(encoding="utf-8").splitlines()
    numbers = [int(x.split(".")[0]) for x in lines if x[:1].isdigit()]
    assert numbers == list(range(1, len(numbers) + 1))


def test_ac_the_conductor_reads_question_comments_on_briefs_as_on_pull_requests():
    """Brief #210 answer 3: the role file."""
    text = " ".join(CONDUCTOR_ROLE.read_text(encoding="utf-8").split())
    assert "`Question:` comments on briefs as on pull requests" in text


# --- when GitHub cannot be reached at all (answer 6) -------------------------------------------

LINE = (
    r"github-unreachable: {what} cannot be read; local head [0-9a-f]{{7}} not pushed; "
    r"next: push, then post the Report:/Question:"
)


def unreachable(stub, text: str = "error connecting to api.github.com") -> None:
    (stub.dir / "error.txt").write_text(text + "\n", encoding="utf-8")


def committed(proj) -> None:
    proj.commit({"a.txt": "x\n"}, "local work")


def test_ac6_an_unreachable_github_ends_a_wait_with_the_one_line_of_the_outage(proj, stub):
    """Brief #210 answer 6: the only channel left is the session's own output."""
    import re

    committed(proj)
    unreachable(stub)
    out = session(proj, stub, *MERGE)
    assert out.returncode == 4
    assert re.fullmatch(LINE.format(what="pull request #7") + "\n", out.stdout), out.stdout


@pytest.mark.parametrize(
    "text",
    [
        "Post https://api.github.com/x: dial tcp: lookup api.github.com: no such host",
        "Could not resolve host: api.github.com",
        "dial tcp 140.82.112.5:443: i/o timeout",
        "connection refused",
        "net/http: TLS handshake timeout",
    ],
)
def test_ac6_the_messages_of_a_network_failure_are_an_outage(proj, stub, text):
    """Brief #210 answer 6: what gh says when it cannot connect."""
    committed(proj)
    unreachable(stub, text)
    assert session(proj, stub, *MERGE).stdout.startswith("github-unreachable: ")


@pytest.mark.parametrize("text", ["gh: Not Found (HTTP 404)", "gh: Forbidden (HTTP 403)", ""])
def test_ac6_a_refused_call_or_an_error_response_is_not_an_outage(proj, stub, text):
    """Brief #210 answer 6: GitHub answered, so the read ends with `error:` as in answer 1."""
    committed(proj)
    unreachable(stub, text)
    out = session(proj, stub, *MERGE)
    assert out.stdout.strip() == "error: pull request #7 cannot be read"


def test_ac6_the_outage_line_of_a_wait_on_the_assignment_names_the_comments_read(proj, stub):
    """Brief #210 answer 6: --assign ends the same way."""
    import re

    committed(proj)
    served(stub, [request(3)])
    unreachable(stub)
    out = assign(proj, stub)
    assert out.returncode == 4
    assert re.fullmatch(
        r"waiting on #204 since 3\n" + LINE.format(what="the comments of #204") + "\n", out.stdout
    ), out.stdout


def test_ac6_a_pushed_head_is_said_so_and_no_commit_is_none(proj, stub):
    """Brief #210 answer 6: the line says only what is true of the local head."""
    unreachable(stub)
    assert "local head none" in session(proj, stub, *MERGE).stdout
    committed(proj)
    proj.git("update-ref", "refs/remotes/origin/main", "HEAD")
    proj.git("branch", "--set-upstream-to=origin/main")
    assert "pushed; next:" in session(proj, stub, *MERGE).stdout
    assert "not pushed" not in session(proj, stub, *MERGE).stdout


def test_ac6_a_rate_limit_is_waited_out_to_the_reset_time_and_does_not_end_the_wait(proj, stub):
    """Brief #210 answer 6: the reset time is read from GET rate_limit; the wait goes on."""
    import time

    reset = int(time.time()) + 2
    stub.serve("rate_limit", {"resources": {"core": {"reset": reset, "remaining": 0}}})
    stub.serve(PR, "RATELIMIT", nth=1)
    stub.serve(PR, pull(merged="2026-10-25T10:00:00Z"), nth=2)
    started = time.time()
    out = session(proj, stub, *MERGE)
    assert out.returncode == 0 and out.stdout.strip() == "merged #7", out.stdout
    assert time.time() >= reset, "the wait ended before the reset time"
    assert any(call[1] == "rate_limit" for call in stub.calls())
    assert time.time() - started < 30


def test_ac6_a_rate_limit_is_not_counted_as_a_failed_poll(proj, stub):
    """Brief #210 answer 6: waiting out five limits in a row ends nothing."""
    import time

    stub.serve("rate_limit", {"resources": {"core": {"reset": int(time.time()), "remaining": 0}}})
    for n in range(1, 4):
        stub.serve(PR, "RATELIMIT", nth=n)
    stub.serve(PR, pull(merged="2026-10-25T10:00:00Z"), nth=4)
    out = session(proj, stub, *MERGE)
    assert out.returncode == 0 and out.stdout.strip() == "merged #7"


def test_ac6_the_rules_name_the_outage_line_the_restart_order_and_what_is_not_an_outage():
    """Brief #210 answer 6: the session rules."""
    text = " ".join(RULES.read_text(encoding="utf-8").split())
    assert (
        "github-unreachable: <what failed>; local head <sha> not pushed; next: push, then" in text
    )
    assert "post the `Report:`/`Question:`" in text
    assert "runs `python3 scripts/agk/session.py push-check`" in text
    assert "pushes its local commits" in text
    assert "before anything else" in text
    assert "A refused push or a 403 on one action is not an outage" in text
    assert "A rate limit is not an outage" in text
    assert "keeps committing locally" in text
