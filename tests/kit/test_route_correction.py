"""The router tells the reviewer when it cannot read a `Final:` line (brief 238; REQ-039).

On a `Verdict:` comment of a listed author with a problem (`common.verdict_problem`) the router
posts one reply on the pull request, beginning `Correction needed:` and giving the message, at
most once for each verdict comment. The label stays as the router decides it. The reply goes
through the router's write path with the permissions it has. A `gh` stub on `PATH`, saved
responses, no network.
"""

from __future__ import annotations

import pytest
from test_route import (
    HEAD,
    REPO,
    REPO_INFO,
    run_router,
    said,
)
from test_route import (
    proj as route_proj,  # noqa: F401  (the fixtures of test_route)
)
from test_route import (
    stub as route_stub,  # noqa: F401
)

BAD = (
    f"Verdict: cleared {HEAD[:7]}\nFinal: flip ADR-0146 to Accepted in one commit, pushed alone.\n"
)
GOOD = f"Verdict: fix list {HEAD[:7]}\nFinal: docs/adr/0001-x.md Proposed -> Accepted\n"
NOT_FIX = "a Final: line is read only under 'Verdict: fix list <sha>'"
EVENT = {"pull_request": {"number": 7}, "repository": REPO_INFO}


@pytest.fixture
def stub(request):
    return request.getfixturevalue("route_stub")


@pytest.fixture
def proj(request):
    return request.getfixturevalue("route_proj")


def replies(stub) -> list[list]:
    return [w for w in stub.writes() if w[0] == "POST" and w[1].endswith("/issues/7/comments")]


def route(proj, stub, tmp_path, comments: list, *args: str, **extra: str):
    stub.pull(7)
    stub.serve("issues/7/comments", comments)
    return run_router(proj, stub, tmp_path, "pull_request", EVENT, *args, **extra)


def test_a_verdict_with_a_final_line_the_router_cannot_read_gets_one_correction(
    proj, stub, tmp_path
):
    """Brief 238 answer 2 and 4: the router posts one reply beginning `Correction needed:`."""
    proc = route(proj, stub, tmp_path, [said(11, "boss", BAD)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    posted = replies(stub)
    assert len(posted) == 1
    body = posted[0][2][posted[0][2].index("-f") + 1]
    assert body.startswith("body=Correction needed: SPEC-0021 rule 1: ")
    assert NOT_FIX in body and "(verdict comment 11)" in body
    assert "flip ADR-0146" not in body and HEAD[:7] not in body


def test_the_label_stays_as_the_router_decides_it_today(proj, stub, tmp_path):
    """Brief 238 answer 2: the reply changes no label."""
    route(proj, stub, tmp_path, [said(11, "boss", BAD)])
    labels = [w for w in stub.writes() if w[1].endswith("/issues/7/labels")]
    assert labels and labels[0][2] == ["-f", "labels[]=agk:ready"]


def test_a_rerun_posts_nothing_new_for_a_verdict_it_has_answered(proj, stub, tmp_path):
    """Brief 238 answer 2 and 4: at most once for each verdict comment."""
    first = route(proj, stub, tmp_path, [said(11, "boss", BAD)])
    assert first.returncode == 0 and len(replies(stub)) == 1
    body = replies(stub)[0][2][1][len("body=") :]
    answered = [said(11, "boss", BAD), said(12, "github-actions[bot]", body)]
    (tmp_path / "again").mkdir()
    stub.pull(7)
    stub.serve("issues/7/comments", answered)
    before = len(replies(stub))
    run_router(proj, stub, tmp_path / "again", "pull_request", EVENT)
    assert len(replies(stub)) == before


def test_a_new_malformed_verdict_gets_its_own_correction(proj, stub, tmp_path):
    """Brief 238 answer 2: one reply for each verdict comment, not one for the pull request."""
    route(proj, stub, tmp_path, [said(11, "boss", BAD)])
    body = replies(stub)[0][2][1][len("body=") :]
    again = [said(11, "boss", BAD), said(12, "github-actions[bot]", body), said(13, "boss", BAD)]
    stub.pull(7)
    stub.serve("issues/7/comments", again)
    (tmp_path / "second").mkdir()
    run_router(proj, stub, tmp_path / "second", "pull_request", EVENT)
    assert len(replies(stub)) == 2 and "(verdict comment 13)" in replies(stub)[1][2][1]


def test_a_well_formed_verdict_and_a_comment_that_is_no_verdict_get_no_reply(proj, stub, tmp_path):
    """Brief 238 answer 4: a well-formed verdict has no problem."""
    quiet = [said(11, "boss", GOOD), said(12, "boss", "Report: abc\nFinal: plain words\n")]
    route(proj, stub, tmp_path, quiet)
    assert replies(stub) == []


def test_a_malformed_verdict_of_an_unlisted_author_gets_no_reply(proj, stub, tmp_path):
    """Brief 238: only a listed verdict author's comment is a verdict, so no one else can make the
    router post."""
    route(proj, stub, tmp_path, [said(11, "stranger", BAD)])
    assert replies(stub) == []


def test_the_dry_run_and_a_read_only_token_post_nothing_and_fail_nothing(proj, stub, tmp_path):
    """Brief 238 answer 2: the existing write path; a 403 is skipped; a dry run writes nothing."""
    dry = route(proj, stub, tmp_path, [said(11, "boss", BAD)], "--pr", "7", "--dry-run")
    assert dry.returncode == 0 and stub.writes() == []
    (tmp_path / "ro").mkdir()
    stub.pull(7)
    stub.serve("issues/7/comments", [said(11, "boss", BAD)])
    ro = run_router(proj, stub, tmp_path / "ro", "pull_request", EVENT, GH_STUB_FORBID="1")
    assert ro.returncode == 0 and "read-only" in ro.stdout


def test_a_failed_reply_does_not_stop_the_label(proj, stub, tmp_path):
    """Brief 238: the label is set first; the reply is the last write of the routing."""
    route(proj, stub, tmp_path, [said(11, "boss", BAD)])
    writes = [w[1] for w in stub.writes() if "/issues/7/" in w[1]]
    assert writes.index(f"repos/{REPO}/issues/7/labels") < writes.index(
        f"repos/{REPO}/issues/7/comments"
    )


def test_the_workflow_gains_no_permission():
    """Brief 238 answer 2: the router's five permissions stay."""
    from pathlib import Path

    text = (
        Path(__file__).resolve().parents[2] / ".github" / "workflows" / "agk-route.yml"
    ).read_text(encoding="utf-8")
    perms = text.split("\npermissions:\n", 1)[1].split("\n\n", 1)[0].split("\n")
    held = {line.split(":")[0].strip(): line.split(":")[1].strip() for line in perms if ":" in line}
    assert held == {
        "contents": "read",
        "pull-requests": "write",
        "issues": "write",
        "checks": "read",
        "statuses": "read",
    }


def test_a_final_line_beside_numbered_items_gets_a_correction_too(proj, stub, tmp_path):
    """Verdict on 90e5749: the silent case; the router replies to it."""
    final = "Final: docs/adr/0001-x.md Proposed -> Accepted"
    body = f"Verdict: fix list {HEAD[:7]}\n\n1. Fix x.\n\n{final}\n"
    route(proj, stub, tmp_path, [said(11, "boss", body)])
    posted = replies(stub)
    assert len(posted) == 1
    assert "read only in a fix list with no numbered items" in posted[0][2][1]
