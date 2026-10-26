# ruff: noqa: F811 - the fixtures and helpers of test_route are imported by name
"""A person's approval never counts when an agent posted it (brief 242; SPEC-0032 rule 5; REQ-039).

`agent_apps` in `agk.toml` (default `["claude"]`) lists the GitHub Apps an agent posts through. A
comment whose `performed_via_github_app.slug` is listed never counts as a person's approval, in the
router, in `check_specs.py` and in the final-clearance check; the router answers it once with a
`Correction needed:` comment. The same rule holds with one account or several. Saved responses; no
network."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from test_route import HEAD, OLD, REPO_INFO, approved_spec, facts, run_router, said
from test_route import proj as route_proj  # noqa: F401  (the fixtures of test_route)
from test_route import stub as route_stub  # noqa: F401

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import reviewers  # noqa: E402
import route  # noqa: E402

APPS = ["claude"]
EVENT = {"pull_request": {"number": 7}, "repository": REPO_INFO}
SHORT = "Approve: SPEC-0032"
LONG = f"Approve: {OLD[:7]} SPEC-0032"
CLEARED = f"Verdict: cleared {HEAD[:7]}"


@pytest.fixture
def stub(request):
    return request.getfixturevalue("route_stub")


@pytest.fixture
def proj(request):
    return request.getfixturevalue("route_proj")


def via(comment: dict, slug: str = "claude") -> dict:
    return {**comment, "performed_via_github_app": {"slug": slug, "id": 1236702}}


# --- the setting (answer 1) ---------------------------------------------------------------------


def test_the_default_is_the_claude_app(tmp_path):
    assert common.agent_apps(tmp_path) == ["claude"]


def test_the_setting_is_read_lowercased_and_may_be_empty(tmp_path):
    (tmp_path / "agk.toml").write_text('agent_apps = ["Claude", "my-bot"]\n')
    assert common.agent_apps(tmp_path) == ["claude", "my-bot"]
    (tmp_path / "agk.toml").write_text("agent_apps = []\n")
    assert common.agent_apps(tmp_path) == []


@pytest.mark.parametrize("value", ['"claude"', "[1]", '[""]', '["a", ""]', '[["a"]]', "true"])
def test_an_invalid_setting_is_refused_naming_the_setting(tmp_path, value):
    (tmp_path / "agk.toml").write_text(f"agent_apps = {value}\n")
    with pytest.raises(common.CheckError) as err:
        common.agent_apps(tmp_path)
    assert str(err.value).startswith("agent_apps must be a list of app slugs")
    assert "agent_apps" in str(err.value) and "agk.toml" in str(err.value)


# --- the rule (answer 2) ------------------------------------------------------------------------


def shas(comments, reviews=(), apps=APPS) -> dict:
    return reviewers.approval_shas(list(comments), list(reviews), ["maintainer"], [], (), apps)


def test_a_comment_through_a_listed_app_never_counts_whether_the_login_is_listed_or_not():
    sent = said(2, "maintainer", LONG)
    assert shas([sent]) == {"SPEC-0032": [OLD[:7]]}
    assert shas([via(sent)]) == {}
    assert shas([via(sent, "Claude")]) == {}  # the slug is read case-blind
    assert shas([via(sent, "some-other-app")]) == {"SPEC-0032": [OLD[:7]]}


def test_an_unlisted_login_never_counts_with_or_without_the_marker():
    assert shas([said(2, "stranger", LONG)]) == {}
    assert shas([via(said(2, "stranger", LONG))]) == {}


def test_the_short_line_follows_the_same_rule():
    assert reviewers.person_approvals([said(2, "maintainer", SHORT)], [], ["maintainer"]) == {
        "SPEC-0032"
    }
    people = reviewers.person_approvals(
        [via(said(2, "maintainer", SHORT))], [], ["maintainer"], (), APPS
    )
    assert people == set()
    people = reviewers.person_approvals(
        [said(2, "maintainer", SHORT)], [], ["maintainer"], (), APPS
    )
    assert people == {"SPEC-0032"}


def test_the_rule_is_the_same_with_the_app_list_empty_for_a_project_that_clears_it():
    sent = via(said(2, "maintainer", LONG))
    assert shas([sent], apps=[]) == {"SPEC-0032": [OLD[:7]]}


def test_a_review_shows_no_app_so_it_counts_for_nothing_while_apps_are_listed():
    """Q-242-1 (b): the review record has no `performed_via_github_app`."""
    review = {"user": {"login": "maintainer"}, "body": LONG, "state": "COMMENTED"}
    assert shas([], [review], apps=APPS) == {}
    assert shas([], [review], apps=[]) == {"SPEC-0032": [OLD[:7]]}


def test_the_router_keeps_waiting_for_a_person_when_an_agent_posted_the_approval():
    cleared = said(1, "boss", CLEARED)
    sent = said(2, "maintainer", LONG)
    base = {"files": approved_spec(), "approvers": ["maintainer"], "agent_apps": APPS}
    assert route.decide(facts(comments=[cleared, sent], **base)) == "agk:ready"
    assert route.decide(facts(comments=[cleared, via(sent)], **base)) == "agk:approve"


# --- the reply (answer 3) -----------------------------------------------------------------------


def replies(stub) -> list[list]:
    return [w for w in stub.writes() if w[0] == "POST" and w[1].endswith("/issues/7/comments")]


def routed(proj, stub, tmp_path, comments: list):
    stub.pull(7)
    stub.serve("issues/7/comments", comments)
    return run_router(proj, stub, tmp_path, "pull_request", EVENT)


def test_an_approval_through_the_app_gets_one_correction_and_none_a_second_time(
    proj, stub, tmp_path
):
    sent = via(said(11, "maintainer", SHORT))
    assert routed(proj, stub, tmp_path, [sent]).returncode == 0
    (reply,) = replies(stub)
    body = next(a for a in reply[2] if a.startswith("body="))
    assert body.startswith(
        "body=Correction needed: an approval posted through an agent's app does not count; "
        "the person posts it themselves"
    )
    assert "(approval comment 11)" in body
    again = {"id": 12, "user": {"login": "x"}, "body": body[len("body=") :]}
    stub.serve("issues/7/comments", [sent, again])
    run_router(proj, stub, tmp_path, "pull_request", EVENT)
    assert len(replies(stub)) == 1


def test_no_reply_for_a_person_a_stranger_another_app_or_a_line_that_is_not_an_approval(
    proj, stub, tmp_path
):
    comments = [
        said(11, "maintainer", SHORT),
        via(said(12, "stranger", SHORT)),
        via(said(13, "maintainer", SHORT), "some-other-app"),
        via(said(14, "maintainer", "I approve SPEC-0032")),
        via(said(15, "boss", f"Approval: SPEC-0032 docs/specs/0032-x.md {CLEARED}")),
    ]
    assert routed(proj, stub, tmp_path, comments).returncode == 0
    assert replies(stub) == []


def test_an_invalid_setting_stops_the_router_naming_the_setting(proj, stub, tmp_path):
    (proj / "agk.toml").write_text('agent_apps = "claude"\n')
    proc = routed(proj, stub, tmp_path, [])
    assert proc.returncode == 1 and "agent_apps" in proc.stdout
    assert stub.writes() == []


# --- a review (answer 2, the ruling on Q-242-1) -------------------------------------------------


def a_review(rid: int, who: str = "maintainer", body: str = LONG, state: str = "COMMENTED") -> dict:
    return {"id": rid, "user": {"login": who}, "body": body, "state": state}


def test_a_review_that_would_have_counted_gets_one_correction_asking_for_the_comment(
    proj, stub, tmp_path
):
    stub.pull(7)
    stub.serve("issues/7/comments", [])
    stub.serve("pulls/7/reviews", [a_review(31)])
    assert run_router(proj, stub, tmp_path, "pull_request", EVENT).returncode == 0
    (reply,) = replies(stub)
    body = next(a for a in reply[2] if a.startswith("body="))
    assert body.startswith("body=Correction needed: a review does not count as an approval")
    assert "Approve: SPEC-<n>" in body and "own account" in body
    assert "(approval review 31)" in body
    again = {"id": 40, "user": {"login": "x"}, "body": body[len("body=") :]}
    stub.serve("issues/7/comments", [again])
    run_router(proj, stub, tmp_path, "pull_request", EVENT)
    assert len(replies(stub)) == 1


def test_a_review_that_would_not_have_counted_gets_no_reply(proj, stub, tmp_path):
    stub.pull(7)
    stub.serve("issues/7/comments", [])
    reviews = [
        a_review(31, who="stranger"),
        a_review(32, body="looks fine"),
        a_review(33, body="", state="APPROVED"),  # names no spec and no spec is flipped
    ]
    stub.serve("pulls/7/reviews", reviews)
    assert run_router(proj, stub, tmp_path, "pull_request", EVENT).returncode == 0
    assert replies(stub) == []


def test_with_the_list_empty_reviews_count_as_before_and_get_no_reply(proj, stub, tmp_path):
    (proj / "agk.toml").write_text("agent_apps = []\n")
    stub.pull(7)
    stub.serve("issues/7/comments", [via(said(11, "maintainer", SHORT))])
    stub.serve("pulls/7/reviews", [a_review(31)])
    assert run_router(proj, stub, tmp_path, "pull_request", EVENT).returncode == 0
    assert replies(stub) == []
