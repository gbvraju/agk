"""session.py resume and the takeover of a stalled pull request (SPEC-0033 rules 4 and 5; REQ-040).

`resume --pr N` prints where the work stands from GitHub and git only and writes nothing. `next`
offers a stalled pull request (one that waits on its builder and has not changed for `stall_hours`)
before any brief and takes it over with the one comment `taken over: <id> <date>`. A `gh` stub on
`PATH`, saved responses, no network.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from test_session import (
    FREE,
    ISSUES,
    REPO,
    SHA,
    comment,
    iso,
    issue,
    listing,
    posts,
    session,
)
from test_session import (
    proj as session_proj,  # noqa: F401  (the fixtures of test_session)
)
from test_session import (
    stub as session_stub,  # noqa: F401
)


@pytest.fixture
def stub(request):
    return request.getfixturevalue("session_stub")


@pytest.fixture
def proj(request):
    return request.getfixturevalue("session_proj")


PRS = f"repos/{REPO}/pulls"
HEAD = SHA
OLD = timedelta(hours=-9)
RESUME = ("resume", "--pr", "7")
DAY = datetime.now(UTC).strftime("%Y-%m-%d")


def pr_object(number: int = 7, **fields) -> dict:
    base = {
        "number": number,
        "title": f"build {number}",
        "html_url": f"https://github.com/{REPO}/pull/{number}",
        "state": "open",
        "draft": False,
        "labels": [],
        "user": {"login": "builder"},
        "head": {"sha": HEAD, "ref": "feature/x"},
        "body": "Advances: REQ-001\n",
    }
    return base | fields


def label(*names: str) -> list[dict]:
    return [{"name": n} for n in names]


# --- resume (rule 4; AC4) ------------------------------------------------------------------------


def serve_resume(stub, *, comments=None, body="Advances: REQ-001\nBrief: #5\n", labels=None):
    stub.serve(f"{PRS}/7", pr_object(body=body, labels=labels or []))
    stub.serve(f"{ISSUES}/7/comments", comments if comments is not None else [])
    stub.serve(f"{ISSUES}/5", {**issue(5, title="the brief"), "labels": label("agk-brief")})


def test_ac4_resume_prints_each_part_from_github_and_git(proj, stub):
    """REQ-040 AC4"""
    progress = comment(3, "builder", "Progress: abc1234 done 2/5; next: the report lines")
    verdict = comment(4, "boss", f"Verdict: fix list {HEAD[:9]}\n\n1. an item\n")
    serve_resume(stub, comments=[progress, verdict], labels=label("agk:fix", "other"))
    out = session(proj, stub, *RESUME)
    assert out.returncode == 0, out.stdout + out.stderr
    text = out.stdout
    assert text.startswith('pull request #7 "build 7" (open) head ' + HEAD)
    assert "state: agk:fix" in text
    assert 'brief #5 "the brief5"' in text and 'Sentence: "A thing works."' in text
    assert "progress: abc1234 done 2/5; next: the report lines" in text
    assert "continue from: the report lines" in text
    assert f"verdict: fix list {HEAD[:9]} (comment 4) names the head" in text
    assert "git fetch origin feature/x" in text
    assert f"git checkout -B feature/x {HEAD}" in text
    assert "python3 scripts/agk/session.py watch --pr 7" in text


def test_ac4_resume_says_none_for_each_missing_part(proj, stub):
    """REQ-040 AC4"""
    serve_resume(stub, body="Advances: REQ-001\n")
    text = session(proj, stub, *RESUME).stdout
    assert "state: none" in text and "progress: none" in text and "verdict: none" in text
    assert "brief: none" in text and "continue from" not in text


def test_ac4_resume_says_when_the_verdict_names_another_head(proj, stub):
    """REQ-040 AC4"""
    old = comment(4, "boss", "Verdict: cleared 1234567")
    serve_resume(stub, comments=[old])
    assert (
        "verdict: cleared 1234567 (comment 4) does not name the head"
        in session(proj, stub, *RESUME).stdout
    )


def test_ac4_resume_ignores_an_unlisted_verdict_and_a_progress_line_of_another_author(proj, stub):
    """REQ-040 AC4"""
    others = [
        comment(3, "stranger", "Progress: abc1234 done 1/2; next: x"),
        comment(4, "stranger", f"Verdict: cleared {HEAD[:7]}"),
    ]
    serve_resume(stub, comments=others)
    text = session(proj, stub, *RESUME).stdout
    assert "progress: none" in text and "verdict: none" in text


def test_ac4_resume_reports_an_unreadable_progress_line_by_rule(proj, stub):
    """REQ-040 AC4"""
    twice = [
        comment(3, "builder", "Progress: abc1234 done 1/2; next: x"),
        comment(4, "builder", "Progress: abc1234 done 2/2; next: y"),
    ]
    serve_resume(stub, comments=twice)
    text = session(proj, stub, *RESUME).stdout
    assert "progress: unreadable (rule 3: " in text and "abc1234" not in text.split("progress:")[1]


def test_ac4_resume_takes_the_brief_only_from_an_agk_brief_issue(proj, stub):
    """REQ-040 AC4"""
    stub.serve(f"{PRS}/7", pr_object(body="See #9 and #5\n"))
    stub.serve(f"{ISSUES}/7/comments", [])
    stub.serve(f"{ISSUES}/9", {**issue(9, title="not a brief"), "labels": label("bug")})
    stub.serve(f"{ISSUES}/5", {**issue(5, title="the brief"), "labels": label("agk-brief")})
    text = session(proj, stub, *RESUME).stdout
    assert 'brief #5 "the brief5"' in text and "not a brief" not in text


def test_ac4_resume_writes_nothing_and_only_gets(proj, stub):
    """REQ-040 AC4 and rule 9"""
    serve_resume(stub)
    session(proj, stub, *RESUME)
    assert stub.calls() and all(call[0] == "GET" for call in stub.calls())


def test_ac4_resume_fails_naming_the_rule_when_the_pull_request_cannot_be_read(proj, stub):
    """REQ-040 AC4"""
    stub.serve(f"{PRS}/7", "FAIL")
    out = session(proj, stub, *RESUME)
    assert out.returncode == 2 and out.stdout.startswith("FAIL session: ")


def test_ac4_resume_usage_is_checked(proj, stub):
    """REQ-040 AC4"""
    for args in (("resume",), ("resume", "--pr", "x"), ("resume", "--pr", "7", "--x", "1")):
        assert session(proj, stub, *args).returncode == 2, args


# --- the takeover of a stalled pull request (rule 5; AC5) ---------------------------------------


def commit_at(when: str) -> dict:
    return {"commit": {"committer": {"date": when}}}


def serve_list(stub, items: list[tuple[dict, list, timedelta]]) -> None:
    stub.serve(PRS, [p for p, _, _ in items])
    for p, comments, age in items:
        stub.serve(f"{ISSUES}/{p['number']}/comments", comments)
        stub.serve(f"{REPO and 'repos/' + REPO}/commits/{p['head']['sha']}", commit_at(iso(age)))


def nxt(proj, stub, *extra: str):
    return session(proj, stub, "next", "--session", "s-me", "--take", *extra)


def offered(out) -> bool:
    return out.stdout.startswith("stalled #")


def test_ac5_a_stalled_draft_is_offered_before_a_brief_and_taken_over_with_one_comment(proj, stub):
    """REQ-040 AC5"""
    serve_list(stub, [(pr_object(7, draft=True), [], OLD)])
    listing(stub, [issue(5, FREE)])
    out = nxt(proj, stub)
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.startswith("stalled #7\n") and "title: build 7" in out.stdout
    assert "python3 scripts/agk/session.py resume --pr 7" in out.stdout
    assert posts(stub) == [["POST", f"{ISSUES}/7/comments", ["-f", f"body=taken over: s-me {DAY}"]]]
    assert not any("issues/5" in call[1] for call in stub.calls())  # no brief was taken


@pytest.mark.parametrize("name", ["agk:fix", "agk:conflict", "agk:ci-red"])
def test_ac5_work_that_waits_on_its_builder_stalls(proj, stub, name):
    """REQ-040 AC5"""
    serve_list(stub, [(pr_object(7, labels=label(name)), [], OLD)])
    assert offered(nxt(proj, stub))


@pytest.mark.parametrize("name", ["agk:ready", "agk:approve", "agk:review", "other"])
def test_ac5_work_that_waits_for_a_person_or_has_no_builder_label_is_never_offered(
    proj, stub, name
):
    """REQ-040 AC5"""
    serve_list(stub, [(pr_object(7, labels=label(name)), [], OLD)])
    listing(stub, [])
    out = nxt(proj, stub)
    assert not offered(out) and out.stdout.strip() == "no brief" and posts(stub) == []


def test_ac5_a_pull_request_that_is_neither_a_draft_nor_labelled_is_not_offered(proj, stub):
    """REQ-040 AC5"""
    serve_list(stub, [(pr_object(7), [], OLD)])
    listing(stub, [])
    assert nxt(proj, stub).stdout.strip() == "no brief"


def test_ac5_a_pull_request_younger_than_stall_hours_is_not_offered(proj, stub):
    """REQ-040 AC5"""
    serve_list(stub, [(pr_object(7, draft=True), [], timedelta(hours=-3))])
    listing(stub, [])
    assert nxt(proj, stub).stdout.strip() == "no brief"


def test_ac5_a_recent_comment_keeps_an_old_pull_request_from_stalling(proj, stub):
    """REQ-040 AC5"""
    fresh = comment(3, "builder", "note", when=iso(timedelta(hours=-1)))
    serve_list(stub, [(pr_object(7, draft=True), [fresh], OLD)])
    listing(stub, [])
    assert nxt(proj, stub).stdout.strip() == "no brief"


def test_ac5_an_edited_progress_line_counts_as_a_change(proj, stub):
    """REQ-040 AC5"""
    line = comment(3, "builder", "Progress: abc1234 done 1/2; next: x", when=iso(OLD))
    line["updated_at"] = iso(timedelta(hours=-1))
    serve_list(stub, [(pr_object(7, draft=True), [line], OLD)])
    listing(stub, [])
    assert nxt(proj, stub).stdout.strip() == "no brief"


@pytest.mark.parametrize(
    "body",
    [
        f"Verdict: cleared {HEAD[:7]}\n",
        f"Verdict: fix list {HEAD[:7]}\n\nFinal: docs/a.md A -> B\n",
    ],
)
def test_ac5_a_verdict_that_clears_or_covers_the_head_means_it_waits_for_a_person(proj, stub, body):
    """REQ-040 AC5"""
    verdict = comment(3, "boss", body, when=iso(OLD))
    serve_list(stub, [(pr_object(7, labels=label("agk:fix")), [verdict], OLD)])
    listing(stub, [])
    assert nxt(proj, stub).stdout.strip() == "no brief"


def test_ac5_a_fix_list_with_numbered_items_does_not_exempt_the_pull_request(proj, stub):
    """REQ-040 AC5"""
    verdict = comment(3, "boss", f"Verdict: fix list {HEAD[:7]}\n\n1. an item\n", when=iso(OLD))
    serve_list(stub, [(pr_object(7, labels=label("agk:fix")), [verdict], OLD)])
    assert offered(nxt(proj, stub))


def test_ac5_a_recent_takeover_comment_resets_the_clock(proj, stub):
    """REQ-040 AC5"""
    taken = comment(3, "other", f"taken over: s-other {DAY}", when=iso(timedelta(hours=-1)))
    serve_list(stub, [(pr_object(7, draft=True), [taken], OLD)])
    listing(stub, [])
    assert nxt(proj, stub).stdout.strip() == "no brief"


def test_ac5_stall_hours_comes_from_the_flow_table_and_defaults_to_4(proj, stub):
    """REQ-040 AC5"""
    three = timedelta(hours=-3)
    serve_list(stub, [(pr_object(7, draft=True), [], three)])
    listing(stub, [])
    assert not offered(nxt(proj, stub))
    proj.write("agk.toml", "[flow]\nstall_hours = 2\n")
    assert offered(nxt(proj, stub))


@pytest.mark.parametrize("value", ["0", "-1", '"x"', "true", "2.5"])
def test_ac5_a_bad_stall_hours_fails_naming_the_setting_not_the_value(proj, stub, value):
    """REQ-040 AC5"""
    proj.write("agk.toml", f"[flow]\nstall_hours = {value}\n")
    serve_list(stub, [(pr_object(7, draft=True), [], OLD)])
    out = nxt(proj, stub)
    assert (
        out.returncode == 2
        and "stall_hours" in out.stdout
        and value not in out.stdout.split("stall_hours")[1]
    )


def test_ac5_the_lowest_numbered_stalled_pull_request_is_offered_first(proj, stub):
    """REQ-040 AC5"""
    serve_list(stub, [(pr_object(9, draft=True), [], OLD), (pr_object(4, draft=True), [], OLD)])
    assert nxt(proj, stub).stdout.startswith("stalled #4\n")


def test_ac5_when_two_sessions_take_over_at_once_the_older_comment_wins(proj, stub):
    """REQ-040 AC5"""
    other = comment(8, "x", f"taken over: s-other {DAY}", when=iso(timedelta(seconds=-5)))
    mine = comment(9, "me", f"taken over: s-me {DAY}", when=iso())
    stub.serve(PRS, [pr_object(7, draft=True)])
    stub.serve(f"{ISSUES}/7/comments", [], nth=1)
    stub.serve(f"{ISSUES}/7/comments", [other, mine], nth=2)
    stub.serve(f"repos/{REPO}/commits/{HEAD}", commit_at(iso(OLD)))
    listing(stub, [])
    out = nxt(proj, stub)
    assert "skip #7: lost the takeover to s-other" in out.stdout.splitlines()
    assert out.stdout.splitlines()[-1] == "no brief" and len(posts(stub)) == 1


def test_ac5_the_pull_requests_are_read_by_get_and_the_takeover_is_the_only_post(proj, stub):
    """REQ-040 AC5 and rule 9"""
    serve_list(stub, [(pr_object(7, draft=True), [], OLD)])
    nxt(proj, stub)
    assert [c[0] for c in stub.calls()].count("POST") == 1
    assert all(c[0] in ("GET", "POST") for c in stub.calls())


def test_ac4_the_rules_file_says_a_session_on_a_stalled_pull_request_resumes_first():
    """REQ-040 AC4"""
    from pathlib import Path

    text = (Path(__file__).resolve().parents[2] / "config" / "session-rules.md").read_text("utf-8")
    for phrase in (
        "session.py resume --pr N",
        "continues from its `next:` step",
        "on the same branch and the same pull request",
        "never opens a second pull request",
        "unless a verdict says so",
    ):
        assert phrase in text, phrase
