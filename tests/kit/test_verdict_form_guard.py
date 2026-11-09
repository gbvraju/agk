"""A conductor line in the wrong form is refused before and after posting (brief #854).

REQ-039. Answer 1: `conductor_guard.py` refuses a comment whose first line starts `Verdict:`,
`Final:` or `Correction:` unless `conductor.py check-verdict` accepts it, naming the failed rule.
Answer 2: the router reads the same lines, and one it cannot read puts the pull request in
`agk:review` with one comment `Unreadable: <rule>`. Answer 9: `sweep` prints `HELD VERDICT #<n>`.
The saved bodies keep the form of the three blocked merges with invented shas and paths. A `gh`
stub serves saved JSON; no network.
"""

from __future__ import annotations

import base64
import json
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_conductor_commands import proj, run, stub  # noqa: F401 - fixtures
from test_route import facts, route, said
from test_session import REPO

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "conductor_guard.py"
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import common  # noqa: E402
import conductor  # noqa: E402

HEAD = "a1b2c3d4e5f6" + "0" * 28
ADR = "docs/adr/0001-the-adr.md"
DOUBLED = f"Verdict: fix list {HEAD}\n\nFinal: docs/adr/{ADR} Proposed -> Accepted\n"  # as on #800
GOOD = f"Verdict: fix list {HEAD}\n\nFinal: {ADR} Proposed -> Accepted\n"
NO_ITEMS = f"Verdict: fix list {HEAD}\nRead: all files.\nRules:\n- Rule 8: holds.\n"  # as on #810
ITEMS = f"Verdict: fix list {HEAD}\n\n1. Fix it. (rule: none)\n"
CLEARED = f"Verdict: cleared {HEAD}\nRead: all files.\n"
OLD_HEAD = f"Verdict: cleared {'b' * 40}\nRead: all files.\n"
MARK = "conductor guard rule 6"
PULL = {"number": 7, "head": {"sha": HEAD}, "state": "open"}
TREE = {"truncated": False, "tree": [{"path": ADR, "type": "blob"}]}


def text_of(words: str) -> dict:
    return {"content": base64.b64encode(words.encode()).decode()}


def serve(stub_, files: list | None = None, repo: str = REPO) -> None:
    stub_.serve(f"repos/{repo}/pulls/7", PULL)
    stub_.serve(f"repos/{repo}/git/trees/{HEAD}", TREE)
    stub_.serve(f"repos/{repo}/pulls/7/files", files if files is not None else [])
    stub_.serve(f"repos/{repo}/contents/{ADR}", text_of("# A\n\n- Status: Proposed\n"))


def check(proj_, stub_, text: str, *extra: str):
    path = proj_.root / "line.md"
    path.write_text(text, encoding="utf-8")
    return run(proj_, stub_, "check-verdict", str(path), *extra)


# --- answer 1: check-verdict -----------------------------------------------------------------


def test_the_doubled_final_path_of_800_is_refused_by_name(proj, stub):  # noqa: F811
    serve(stub)
    out = check(proj, stub, DOUBLED, "--pr", "7")
    assert out.returncode == 1 and out.stdout.strip() == conductor.FINAL_PATH
    assert "0001" not in out.stdout  # the rule, never the value


def test_a_fix_list_with_no_items_on_a_covered_pull_request_must_be_cleared(proj, stub):  # noqa: F811
    serve(stub, [{"filename": "scripts/agk/x.py", "status": "modified"}])
    out = check(proj, stub, NO_ITEMS, "--pr", "7")
    assert out.returncode == 1 and out.stdout.strip() == conductor.NO_ITEMS


def test_a_fix_list_with_no_items_is_allowed_beside_a_proposed_adr(proj, stub):  # noqa: F811
    serve(stub, [{"filename": ADR, "status": "added"}])
    assert check(proj, stub, NO_ITEMS, "--pr", "7").stdout.strip() == "ok"


def test_a_fix_list_beside_an_accepted_adr_only_must_be_cleared(proj, stub):  # noqa: F811
    serve(stub, [{"filename": ADR, "status": "modified"}])
    stub.serve(f"repos/{REPO}/contents/{ADR}", text_of("# A\n\n- Status: Accepted\n"))
    assert check(proj, stub, NO_ITEMS, "--pr", "7").stdout.strip() == conductor.NO_ITEMS


def test_a_verdict_on_another_head_is_refused(proj, stub):  # noqa: F811
    serve(stub)
    out = check(proj, stub, OLD_HEAD, "--pr", "7")
    assert out.returncode == 1 and out.stdout.strip() == conductor.OTHER_HEAD


@pytest.mark.parametrize("text", [GOOD, ITEMS, CLEARED, CLEARED.replace(HEAD, HEAD[:7])])
def test_a_good_verdict_passes(proj, stub, text):  # noqa: F811
    serve(stub)
    out = check(proj, stub, text, "--pr", "7")
    assert out.returncode == 0 and out.stdout.strip() == "ok", out.stdout + out.stderr


def test_a_read_that_fails_is_not_an_accepted_verdict(proj, stub):  # noqa: F811
    out = check(proj, stub, CLEARED, "--pr", "7")
    assert out.returncode == 1 and "cannot be read" in out.stderr


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        ("Final: docs/adr/0001-x.md Proposed -> Accepted\n", common.NOT_FIX_LIST),
        ("Correction:\n", conductor.CORRECTION_EMPTY),
        ("Verdict: cleared\nRead: all.\n", conductor.VERDICT_SHAPE),
        (f"{CLEARED}Approval: please approve the spec\n", conductor.APPROVAL_SHAPE),
    ],
)
def test_the_shape_of_a_line_is_read_with_no_read_of_github(proj, stub, text, rule):  # noqa: F811
    out = check(proj, stub, text)
    assert out.returncode == 1 and out.stdout.strip() == rule
    assert stub.calls() == []


def test_a_correction_with_text_and_a_good_approval_line_pass(proj, stub):  # noqa: F811
    assert check(proj, stub, "Correction: the cause was x; y stands\n").stdout.strip() == "ok"
    ask = 'Approval: SPEC-0001 docs/specs/0001-x.md Draft -> Approved, waiting for a person: post "Approve: SPEC-0001"\n'  # noqa: E501
    assert check(proj, stub, CLEARED + ask).stdout.strip() == "ok"


# --- answer 1: the guard ---------------------------------------------------------------------

STUB = """#!/bin/sh
case "$4" in
  repos/o/r/pulls/7) echo '{pull}' ;;
  repos/o/r/git/trees/*) echo '{tree}' ;;
  repos/o/r/pulls/7/files*) echo '[]' ;;
  *) exit 1 ;;
esac
"""


def hook(project: Path, tmpdir: Path, text: str, endpoint: str = "repos/o/r/issues/7/comments"):
    (tmpdir / "bin").mkdir(exist_ok=True)
    gh = tmpdir / "bin" / "gh"
    gh.write_text(STUB.format(pull=json.dumps(PULL), tree=json.dumps(TREE)), encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    scratch = tmpdir / "agk-conductor-1"
    scratch.mkdir(exist_ok=True)
    (scratch / "v.md").write_text(text, encoding="utf-8")
    command = f"gh api --method POST {endpoint} -F body=@{scratch / 'v.md'}"
    env = {
        "PATH": f"{tmpdir / 'bin'}:/usr/bin:/bin",
        "CLAUDE_PROJECT_DIR": str(project),
        "TMPDIR": str(tmpdir),
    }
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)["hookSpecificOutput"] if out.stdout.strip() else None


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True)
    (root / ".git" / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/o/r.git\n', encoding="utf-8"
    )
    return root


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        (DOUBLED, conductor.FINAL_PATH),
        (NO_ITEMS, conductor.NO_ITEMS),
        (OLD_HEAD, conductor.OTHER_HEAD),
        ("Final: docs/adr/0001-x.md Proposed -> Accepted\n", common.NOT_FIX_LIST),
        ("Correction:\n", conductor.CORRECTION_EMPTY),
    ],
)
def test_the_guard_refuses_each_wrong_form_by_name(project, tmp_path, text, rule):
    found = hook(project, tmp_path, text)
    assert found is not None and found["permissionDecision"] == "deny"
    assert found["permissionDecisionReason"] == f"{MARK}: {rule}"


def test_the_guard_allows_a_good_verdict_and_other_comments(project, tmp_path):
    for text in (GOOD, ITEMS, CLEARED, "Correction: x; y stands\n", "Question: Q-1 why\n"):
        assert hook(project, tmp_path, text) is None, text


def test_the_guard_refuses_a_verdict_it_cannot_check(project, tmp_path):
    """A pull request the stub cannot serve: the check did not accept it."""
    found = hook(project, tmp_path, CLEARED, "repos/o/r/issues/8/comments")
    assert found is not None and "cannot be read" in found["permissionDecisionReason"]


def test_a_correction_on_a_brief_needs_no_pull_request(project, tmp_path):
    assert hook(project, tmp_path, "Correction: x; y\n", "repos/o/r/issues/8/comments") is None


# --- answer 2: the router --------------------------------------------------------------------


def test_a_line_it_cannot_read_puts_the_pull_request_in_review():
    fix = said(1, "boss", f"Verdict: fix list {HEAD}\n\n1. Fix it.\n")
    assert route.decide(facts(head=HEAD, comments=[fix])) == "agk:fix"
    assert route.decide(facts(head=HEAD, comments=[fix], unreadable=True)) == "agk:review"


def test_the_router_reads_the_newest_line_with_the_same_check(monkeypatch):
    monkeypatch.setattr(route, "head_check", lambda *a: None)
    bad = said(1, "boss", "Final: docs/adr/0001-x.md Proposed -> Accepted\n")
    good = said(2, "boss", f"Verdict: cleared {HEAD}\n")
    other = said(3, "builder", "Correction:\n")
    f = facts(head=HEAD, comments=[bad, good, other])
    assert route.unreadable_lines("o/r", 7, f) == [(bad, common.NOT_FIX_LIST)]
    assert (
        route.newest_is_unreadable(f["comments"], f["authors"], route.unreadable_lines("o/r", 7, f))
        is False
    )
    bad = said(4, "boss", bad["body"])
    f = facts(head=HEAD, comments=[good, bad])
    found = route.unreadable_lines("o/r", 7, f)
    assert route.newest_is_unreadable(f["comments"], f["authors"], found) is True


def test_the_live_check_reads_only_the_newest_verdict_on_the_head(monkeypatch):
    calls = []
    monkeypatch.setattr(route, "head_check", lambda *a: calls.append(a[2]) or conductor.NO_ITEMS)
    older = said(1, "boss", f"Verdict: cleared {'b' * 40}\n")
    newest = said(2, "boss", f"Verdict: fix list {HEAD}\nRules: holds.\n")
    f = facts(head=HEAD, comments=[older, newest])
    assert route.unreadable_lines("o/r", 7, f) == [(newest, conductor.NO_ITEMS)]
    assert len(calls) == 1
    calls.clear()
    older = said(3, "boss", older["body"])
    f = facts(head=HEAD, comments=[newest, older])  # the newest names an older head: not read
    assert route.unreadable_lines("o/r", 7, f) == []
    assert calls == []


def test_a_read_that_fails_after_posting_does_not_flag_the_line(monkeypatch):
    def fails(*_):
        raise common.CheckError("cannot be read")

    monkeypatch.setattr(route, "head_check", fails)
    f = facts(head=HEAD, comments=[said(1, "boss", NO_ITEMS)])
    assert route.unreadable_lines("o/r", 7, f) == []


def test_one_router_comment_names_the_rule_once(monkeypatch):
    posted: list[str] = []
    monkeypatch.setattr(route, "write", lambda _e, *x, **_k: posted.append(x[1]))
    line = said(5, "boss", "Final: docs/adr/0001-x.md Proposed -> Accepted\n")
    route.report_unreadable("o/r", 7, [line], [(line, common.NOT_FIX_LIST)])
    assert posted == [f"body=Unreadable: {common.NOT_FIX_LIST} (comment 5)"]
    posted.clear()
    answer = said(6, "github-actions[bot]", f"Unreadable: {common.NOT_FIX_LIST} (comment 5)")
    route.report_unreadable("o/r", 7, [line, answer], [(line, common.NOT_FIX_LIST)])
    assert posted == []


def test_a_final_shape_problem_keeps_its_correction_and_gets_no_second_comment(monkeypatch):
    posted: list[str] = []
    monkeypatch.setattr(route, "write", lambda _e, *x, **_k: posted.append(x[1]))
    line = said(5, "boss", f"Verdict: fix list {HEAD}\nFinal: flip the ADR\n")
    route.report_unreadable("o/r", 7, [line], [(line, common.FINAL_SHAPE)])
    assert posted == []


# --- answer 9: a verdict held back -----------------------------------------------------------


def ago(minutes: int) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def note(cid: int, login: str, body: str, minutes: int) -> dict:
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": ago(minutes)}


def pull(draft: bool = False) -> dict:
    return {"number": 9, "draft": draft, "user": {"login": "b"}, "head": {"sha": HEAD}}


@pytest.fixture
def green(monkeypatch):
    monkeypatch.setattr(conductor.session, "check_state", lambda *_: ("green", []))


def held(monkeypatch, comments: list, draft: bool = False):
    monkeypatch.setattr(conductor, "read", lambda *_: comments)
    return conductor.held_verdict_line(None, "o/r", pull(draft), ["boss"], datetime.now(UTC))


READY = f"Report: {HEAD[:7]} ready for review"


def test_a_green_ready_head_with_no_verdict_is_a_held_verdict(monkeypatch, green):
    comments = [note(1, "boss", "Reviewed the plan", 40), note(2, "b", READY, 30)]
    assert held(monkeypatch, comments) == "HELD VERDICT #9"


def test_a_recent_review_or_report_is_not_held(monkeypatch, green):
    assert held(monkeypatch, [note(1, "boss", "Looking", 5), note(2, "b", READY, 30)]) is None
    assert held(monkeypatch, [note(1, "boss", "Looked", 40), note(2, "b", READY, 5)]) is None


def test_a_verdict_on_the_head_or_a_draft_is_not_held(monkeypatch, green):
    verdict = note(3, "boss", f"Verdict: cleared {HEAD}", 20)
    assert held(monkeypatch, [note(2, "b", READY, 30), verdict]) is None
    assert held(monkeypatch, [note(2, "b", READY, 30)], draft=True) is None


def test_a_report_that_is_not_ready_or_red_checks_is_not_held(monkeypatch):
    monkeypatch.setattr(conductor.session, "check_state", lambda *_: ("red", []))
    assert held(monkeypatch, [note(2, "b", READY, 30)]) is None
    monkeypatch.setattr(conductor.session, "check_state", lambda *_: ("green", []))
    assert held(monkeypatch, [note(2, "b", f"Report: {HEAD[:7]} escalate why", 30)]) is None


def test_the_conductors_role_says_a_refused_merge_never_holds_a_verdict():
    text = (ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    assert "A refused session merge never holds a verdict" in text
    assert "HELD VERDICT" in text
