"""A verdict with nothing to fix is posted as `Verdict: cleared <head>` (brief #2001, ADR-0827).

REQ-028. Answer 1: a verdict with no numbered item is cleared, and on the full head it carries the
`Final: docs/adr/<file> Proposed -> Accepted` lines of SPEC-0021 rule 3a. Answer 2: the readers
read both forms. Answer 3: other `Final:` lines under a cleared verdict, or a short sha, are
unreadable, and a cleared verdict naming an ADR outside the diff fails the head check. Answer 4:
the old forms are refused before a post only. Answer 5: `watch` prints no label line for a cleared
head. Answer 6: the texts say the form. A `gh` stub serves saved JSON; invented data; no network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from test_conductor_commands import proj, run, stub  # noqa: F401 - fixtures
from test_route import facts, route, said
from test_session import REPO, SHA, comment, pull, session, watching
from test_verdict_form_guard import ADR, HEAD, hook, project, serve, text_of  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import common  # noqa: E402
import conductor  # noqa: E402
import merge_cleared  # noqa: E402
import reviewers  # noqa: E402
import session as session_py  # noqa: E402

ACCEPT = f"Final: {ADR} Proposed -> Accepted"
SPEC_FINAL = "Final: docs/specs/0001-the-spec.md Draft -> Approved"
REQ_FINAL = "Final: docs/requirements.md REQ-001 planned -> built"
NEW = f"Verdict: cleared {HEAD}\nRead: all files.\n\n{ACCEPT}\n"
OLD = f"Verdict: fix list {HEAD}\nRead: all files.\n\n{ACCEPT}\n"
EMPTY = f"Verdict: fix list {HEAD}\nRead: all files.\nRules:\n- Rule 8: holds.\n"
ADDED = [{"filename": ADR, "status": "added"}]


def check(proj_, stub_, text: str):
    path = proj_.root / "line.md"
    path.write_text(text, encoding="utf-8")
    return run(proj_, stub_, "check-verdict", str(path), "--pr", "7")


# --- answers 1 and 2: the form and the one reader --------------------------------------------


def test_the_reader_reads_the_cleared_form_and_the_old_one():
    edits = [(ADR, None, "Proposed", "Accepted")]
    assert common.covered_fix_list(NEW) == (HEAD, edits)
    assert common.covered_fix_list(OLD) == (HEAD, edits)
    fallback = NEW.replace(HEAD, f"{HEAD} (conductor fallback)", 1)
    assert common.covered_fix_list(fallback) == (HEAD, edits)


@pytest.mark.parametrize(
    "body",
    [
        NEW.replace(HEAD, HEAD[:12]),  # a short sha: rule 3a needs the full head
        f"Verdict: cleared {HEAD}\n\n{REQ_FINAL}\n",  # needs the builder's status commit
        f"Verdict: cleared {HEAD}\n\n{SPEC_FINAL}\n",
        f"Verdict: cleared {HEAD}\nRead: all files.\n",  # no Final: line: cleared, nothing to read
    ],
)
def test_a_cleared_verdict_with_another_final_line_is_not_covered(body):
    assert common.covered_fix_list(body) is None


def test_the_merger_accepts_both_forms_with_the_same_lines(monkeypatch):
    monkeypatch.setattr(merge_cleared, "adr_status", lambda *_a: "Proposed")
    new, old = {"id": 11, "body": NEW}, {"id": 11, "body": OLD}
    assert merge_cleared.accepted_adrs(new, HEAD) == merge_cleared.accepted_adrs(old, HEAD) == [ADR]
    lines = merge_cleared.acceptance_lines(REPO, HEAD, new)
    assert lines == merge_cleared.acceptance_lines(REPO, HEAD, old)
    assert lines == ["ADR-0001 Accepted (Final 11)", common.MERGED_BY]
    assert merge_cleared.clears_head(new, HEAD) and merge_cleared.no_builder_event(new, HEAD)


@pytest.mark.parametrize(
    "body",
    [
        f"Verdict: cleared {HEAD}\n\n{SPEC_FINAL}\n",  # a spec Final: the builder's status commit
        f"Verdict: cleared {HEAD}\n\n1. Fix it.\n\n{ACCEPT}\n",  # numbered items beside it
    ],
)
def test_the_merger_holds_a_cleared_verdict_whose_final_line_it_cannot_read(body):
    """The fix list on 8d2042a, item 4: such a verdict never merges without its acceptance."""
    verdict = {"id": 3, "user": {"login": "boss"}, "body": body, "created_at": "2026-11-26T12:00Z"}
    assert not merge_cleared.clears_head(verdict, HEAD)
    held = ("held", merge_cleared.UNREADABLE_FINAL)
    assert merge_cleared.judge([verdict], HEAD, ["boss"]) == held
    for good in (NEW, f"Verdict: cleared {HEAD}\nRead: all files.\n"):
        verdict["body"] = good
        assert merge_cleared.judge([verdict], HEAD, ["boss"]) == ("cleared", "")


def test_the_record_check_and_a_light_re_prove_read_the_cleared_form(monkeypatch):
    """The two points the verdict on 8d2042a left unproven: `check_adrs` verifies a squash record
    whose Final is the cleared form, and a cleared acceptance carries over a light re-prove."""
    import check_adrs  # noqa: PLC0415 - only this test reads it

    url = f"https://api.github.com/repos/{REPO}/issues/7"
    verdict = {"id": 11, "user": {"login": "boss"}, "body": NEW, "issue_url": url}
    assert check_adrs.final_record_verified(ADR, (7, 11), verdict, ["boss"])
    monkeypatch.setattr(merge_cleared.session_plan, "light_merge", lambda *_a: True)
    merged = "c" * 40
    verdict["created_at"] = "2026-11-26T12:00Z"
    assert merge_cleared.carried_from(ROOT, [verdict], merged, ["boss"], "main", []) == HEAD
    monkeypatch.setattr(merge_cleared, "adr_status", lambda *_a: "Proposed")
    lines = merge_cleared.acceptance_lines(REPO, merged, verdict, HEAD)
    assert lines == ["ADR-0001 Accepted (Final 11)", common.MERGED_BY]


def test_the_router_labels_the_cleared_acceptance_merge_ready():
    f = facts(head=HEAD, comments=[said(1, "boss", NEW)], files=ADDED)
    assert route.decide(f) == "agk:merge-ready"
    assert route.final_accept_clears(NEW, HEAD, ADDED)


def test_the_solo_confirmation_derives_the_same_body():
    shown = "Shown:\none\ntwo\nthree\n"
    by = "confirmed by person in a session at 2026-11-26T12:00:00Z"
    body = f"Confirmed: {HEAD}\n{NEW}{shown}{by}"
    item = {"id": 5, "user": {"login": "person"}, "body": body, "created_at": "2026-11-26T12:00Z"}
    found = reviewers.confirmed_comments([item], person="person")
    derived = [c for c in found if c is not item]
    assert derived and common.covered_fix_list(str(derived[0]["body"])) is not None


# --- answer 3: readable lines ----------------------------------------------------------------


def test_the_router_reads_the_cleared_acceptance_and_both_old_forms():
    assert common.verdict_problem(NEW) is None
    assert common.verdict_problem(OLD) is None  # posted before the upgrade: no correction
    assert common.verdict_problem(EMPTY) is None
    assert conductor.line_problem(OLD) is None and conductor.line_problem(EMPTY) is None


@pytest.mark.parametrize(
    "body",
    [
        NEW.replace(HEAD, HEAD[:12]),
        f"Verdict: cleared {HEAD}\n\n{REQ_FINAL}\n",
        f"Verdict: cleared {HEAD}\n\n{SPEC_FINAL}\n",
        f"Verdict: rejected {HEAD}\n\n{ACCEPT}\n",
    ],
)
def test_another_final_line_under_a_cleared_verdict_is_unreadable(body):
    assert common.verdict_problem(body) == common.NOT_FIX_LIST


def test_a_cleared_verdict_naming_an_adr_outside_the_diff_fails_the_head_check(proj, stub):  # noqa: F811
    serve(stub, [{"filename": "scripts/agk/x.py", "status": "modified"}])
    out = check(proj, stub, NEW)
    assert out.returncode == 1 and out.stdout.strip() == conductor.FINAL_OUTSIDE
    assert "0001" not in out.stdout  # the rule, never the value


# --- answer 4: the refusal before posting ----------------------------------------------------


def test_a_fix_list_with_nothing_to_fix_is_refused_before_posting(proj, stub):  # noqa: F811
    serve(stub, ADDED)  # beside a Proposed ADR, which head_problem allowed
    out = check(proj, stub, EMPTY)
    assert out.returncode == 1 and out.stdout.strip() == conductor.FIX_LIST_EMPTY
    out = check(proj, stub, OLD)
    assert out.returncode == 1 and out.stdout.strip() == conductor.FIX_LIST_ACCEPTS


def test_the_cleared_acceptance_and_a_status_commit_fix_list_pass(proj, stub):  # noqa: F811
    serve(stub, ADDED)
    assert check(proj, stub, NEW).stdout.strip() == "ok"
    spec = "docs/specs/0001-the-spec.md"
    tree = {"truncated": False, "tree": [{"path": spec, "type": "blob"}]}
    stub.serve(f"repos/{REPO}/git/trees/{HEAD}", tree)
    out = check(proj, stub, f"Verdict: fix list {HEAD}\n\n{SPEC_FINAL}\n")
    assert out.stdout.strip() == "ok", out.stdout + out.stderr


def test_the_guard_refuses_the_old_acceptance_form(project, tmp_path):  # noqa: F811
    found = hook(project, tmp_path, OLD)
    assert found is not None and found["permissionDecision"] == "deny"
    assert found["permissionDecisionReason"].endswith(conductor.FIX_LIST_ACCEPTS)


def test_the_router_posts_no_reply_on_an_old_form_verdict(monkeypatch):
    monkeypatch.setattr(route, "head_check", lambda *a: None)
    posted: list = []
    monkeypatch.setattr(route, "write", lambda *a, **k: posted.append(a))
    f = facts(head=HEAD, comments=[said(1, "boss", OLD)], files=ADDED)
    assert route.unreadable_lines(REPO, 7, f) == []
    route.correct_verdicts(REPO, 7, f["comments"], f["authors"])
    assert posted == []


# --- answer 5: the watch ---------------------------------------------------------------------

CLEARED_ON_SHA = f"Verdict: cleared {SHA}\n\nFinal: {ADR} Proposed -> Accepted\n"
WATCH_SINCE = ("watch", "--pr", "7", "--interval", "0", "--since", "9", "--timeout")


def test_the_cleared_verdict_still_ends_the_watch():
    verdict = comment(9, "boss", CLEARED_ON_SHA)
    assert session_py.builder_verdicts([verdict], SHA, ["boss"]) == [verdict]


def test_watch_prints_no_label_line_after_a_clearing_verdict(proj, stub):  # noqa: F811
    """`agk:owner-merge` ends the watch by its own owner-wait line, as today."""
    label = "agk:merge-ready"
    verdict = [comment(9, "boss", CLEARED_ON_SHA)]
    watching(
        stub,
        [(pull(labels=("agk:review",)), verdict), (pull(labels=(label,)), verdict)],
        base=verdict,
    )
    stub.serve(f"repos/{REPO}/pulls/7", pull(labels=(label,)))
    stub.serve(f"repos/{REPO}/issues/7/comments", verdict)
    out = session(proj, stub, *WATCH_SINCE, "1")
    assert out.returncode == 3 and out.stdout.strip() == "timeout", out.stdout + out.stderr


def test_watch_still_prints_reprove_after_a_clearing_verdict(proj, stub):  # noqa: F811
    verdict = [comment(9, "boss", CLEARED_ON_SHA)]
    watching(
        stub,
        [(pull(labels=("agk:merge-ready",)), verdict), (pull(labels=("agk:reprove",)), verdict)],
        base=verdict,
    )
    out = session(proj, stub, *WATCH_SINCE, "5")
    assert out.stdout.strip() == "label agk:reprove", out.stdout + out.stderr


def test_review_queue_lists_nothing_on_a_cleared_head_without_a_report(monkeypatch):
    verdict = comment(9, "boss", CLEARED_ON_SHA)
    monkeypatch.setattr(session_py, "pages", lambda *_a: [verdict])
    monkeypatch.setattr(session_py, "check_state", lambda *_a: ("green", []))
    pr = {"number": 7, "head": {"sha": SHA}, "user": {"login": "builder"}, "labels": []}
    verb, reasons, _ = session_py.review_line(REPO, ROOT, pr, ["boss"])
    assert verb == "skip" and reasons == ["verdict on this head (comment 9)"]


# --- answer 6: the texts ---------------------------------------------------------------------


def test_the_texts_say_the_cleared_form():
    conductor_md = (ROOT / ".claude/agents/conductor.md").read_text(encoding="utf-8")
    builder = (ROOT / "kit/templates/runtime/builder.txt").read_text(encoding="utf-8")
    assert "a fix list has numbered items or a status-commit `Final:` line" in conductor_md
    form = "`Verdict: cleared <sha>` with the full 40-character head and its ADR `Final:` lines"
    assert form in conductor_md
    final = next(ln for ln in builder.splitlines() if ln.startswith("FINAL LINES:"))
    assert "A `Verdict: cleared` on your head is no work" in final
    assert "nothing to change" in final and "older form" in final
    merge = next(ln for ln in conductor_md.splitlines() if ln.startswith("The guarded merge"))
    assert "or an older fix list of only those" in merge  # the merger still merges one (answer 9)
