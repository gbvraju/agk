"""One state label per pull request, naming who acts next (brief #846 build (a); REQ-039, ADR-0385).

Amendment 150 items 1 to 4 and 8: `route.pr_state` gives one of eleven labels and its actor from
saved facts, the old `agk:ready` is read as `agk:merge-ready` and removed, the queues list the new
labels by role, and `doctor.py` warns when a state label is missing or does not name its actor.
Saved responses and invented data only; no network.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from test_doctor import checks_of, doctor, prepare
from test_route import HEAD, OLD, facts, ok, said

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import merge_cleared  # noqa: E402
import route  # noqa: E402
import session  # noqa: E402
import session_plan  # noqa: E402
import uninstall  # noqa: E402

ORDER = [
    "agk:parked",
    "agk:build",
    "agk:ci-running",
    "agk:ci-red",
    "agk:conflict",
    "agk:review",
    "agk:fix",
    "agk:question",
    "agk:approve",
    "agk:owner-merge",
    "agk:merge-ready",
    "agk:handover",
]
ACTORS = {"builder", "checks", "conductor", "owner", "merger", "launcher"}
BRIEF = "Brief: #5\nSummary: A person sees who acts next.\n"
RED = {"name": "proof", "status": "completed", "conclusion": "failure"}


def state(**kw) -> tuple[str, str]:
    return route.pr_state(facts(**kw))


def ready(line: str = "ready for review", login: str = "builder", sha: str = HEAD) -> dict:
    return said(3, login, f"Report: {sha[:12]} {line}. Usage: not shown")


def cleared(cid: int = 1) -> dict:
    return said(cid, "boss", f"Verdict: cleared {HEAD[:7]}")


# --- item 1: the eleven states and their actors -------------------------------------------------


def test_eleven_states_each_naming_its_actor_in_its_description():
    """REQ-039: amendment 150 item 1 (the labels, the order, `AGK: <actor> acts next: <what>`)."""
    assert [label for label, _, _ in route.STATES] == ORDER
    for label, actor, _ in route.STATES:
        assert actor in ACTORS
        assert route.description_of(label).startswith(f"AGK: {actor} acts next: "), label
        assert len(route.description_of(label)) <= 100  # GitHub's limit for a description
    assert "agk:ready" not in route.ACTOR


def test_decide_is_the_label_of_pr_state():
    """REQ-039: amendment 150 item 3 (one function; `decide` is its label)."""
    f = facts(comments=[cleared()])
    assert route.pr_state(f) == ("agk:merge-ready", "merger")
    assert route.decide(f) == "agk:merge-ready"


def test_a_draft_is_build_whatever_its_checks_or_verdicts():
    """REQ-039: amendment 150 item 1 (`agk:build`; a draft never carries `agk:review`)."""
    assert state(draft=True) == ("agk:build", "builder")
    assert state(draft=True, checks=[ok("governance"), RED]) == ("agk:build", "builder")
    assert state(draft=True, comments=[ready()]) == ("agk:build", "builder")


def test_a_brief_pull_request_without_a_ready_report_on_its_head_is_build():
    """REQ-039: amendment 150 item 1 and Q-846-3 (the `Report:` test needs a `Brief:` line)."""
    assert state(body=BRIEF) == ("agk:build", "builder")
    assert state(body=BRIEF, comments=[ready(sha=OLD)])[0] == "agk:build"
    assert state(body=BRIEF, comments=[ready(login="someone")])[0] == "agk:build"
    assert (
        state(body=BRIEF, comments=[said(3, "builder", f"Report: {HEAD[:12]} over cap")])[0]
        == "agk:build"
    )
    for line in ("ready for review", "fix list applied", "merge of main"):
        assert state(body=BRIEF, comments=[ready(line)]) == ("agk:review", "conductor"), line
    assert state(body="Summary: a person opened it.") == ("agk:review", "conductor")


def test_a_head_a_verdict_names_is_past_build():
    """REQ-039: Q-846-7 (a verdict on the head means the builder reported; no `Report:` needed)."""
    assert state(body=BRIEF, comments=[cleared()]) == ("agk:merge-ready", "merger")
    fix = said(1, "boss", f"Verdict: fix list {HEAD[:7]}\n\n1. do this")
    assert state(body=BRIEF, comments=[fix]) == ("agk:fix", "builder")


def test_a_conflict_still_comes_before_the_checks():
    """REQ-039: Q-846-8 (a dirty head starts no workflow, so it never waits at `agk:ci-running`)."""
    assert state(mergeable_state="dirty", checks=[]) == ("agk:conflict", "builder")
    assert state(mergeable_state="dirty", checks=[RED]) == ("agk:conflict", "builder")
    assert state(draft=True, mergeable_state="dirty") == ("agk:build", "builder")


def test_the_parked_label_wins_and_is_never_set_or_removed():
    """REQ-039: amendment 150 item 1 and Q-846-1 (`agk:parked` first; the router leaves it)."""
    parked = ["agk:parked", "agk:review"]
    assert state(labels=parked, comments=[cleared()]) == ("agk:parked", "owner")
    assert state(labels=parked, draft=True, checks=[RED]) == ("agk:parked", "owner")
    assert "agk:parked" not in route.LABELS


def test_a_cleared_head_that_changes_an_owner_path_is_owner_merge():
    """REQ-039: amendment 150 item 1 (`agk:owner-merge`: the list `merge_cleared.py` refuses)."""
    assert route.OWNER_PATHS is merge_cleared.PROTECTED
    for path in (".github/workflows/x.yml", "constitution/principles.md", "config/reviewers.yaml"):
        files = [{"filename": path, "status": "modified"}]
        assert state(comments=[cleared()], files=files) == ("agk:owner-merge", "owner"), path
    other = [{"filename": "scripts/agk/x.py", "status": "modified"}]
    assert state(comments=[cleared()], files=other) == ("agk:merge-ready", "merger")


def test_an_open_owner_needed_line_is_question_until_answered():
    """REQ-039: amendment 150 item 1, Q-846-4 and amendment 172 (`agk:question`, closed by an answer;
    a later head no longer closes it, brief #1168, ADR-0497)."""
    asked = said(4, "boss", "Owner needed: may this change the workflow?")
    commit = {"commit": {"committer": {"date": "2026-10-25T09:00:00Z"}}}
    assert state(comments=[cleared(), asked], commit=commit) == ("agk:question", "owner")
    answer = said(5, "maintainer", "Maintainer answer: yes")
    assert state(comments=[cleared(), asked, answer], commit=commit)[0] == "agk:merge-ready"
    stranger = said(5, "stranger", "Maintainer answer: yes")
    assert state(comments=[cleared(), asked, stranger], commit=commit)[0] == "agk:question"
    later = {"commit": {"committer": {"date": "2026-10-25T11:00:00Z"}}}
    assert state(comments=[cleared(), asked], commit=later)[0] == "agk:question"
    unlisted = said(4, "stranger", "Owner needed: anything")
    assert state(comments=[cleared(), unlisted], commit=commit)[0] == "agk:merge-ready"


def test_question_comes_before_fix_and_fix_before_approve():
    """REQ-039: amendment 150 item 1 (fix before approve), brief #1101 answer 1 and ADR-0471
    (an open owner ask before fix)."""
    body = (
        f"Verdict: fix list {HEAD[:7]}\n\n1. do this\n\n"
        "Approval: SPEC-0032 docs/specs/0032-the-spec.md Draft -> Approved, waiting for a person"
    )
    asked = said(4, "boss", "Owner needed: a line")
    assert state(comments=[said(1, "boss", body), asked]) == ("agk:question", "owner")
    assert state(comments=[said(1, "boss", body)]) == ("agk:fix", "builder")


# --- item 2: the rename without a gap -----------------------------------------------------------


def test_the_router_removes_the_old_ready_label_and_never_sets_it(monkeypatch):
    """REQ-039: amendment 150 item 2 (`agk:ready` is one of the labels removed)."""
    calls = []
    monkeypatch.setattr(
        route, "write", lambda endpoint, *a, method, **k: calls.append((method, endpoint))
    )
    labels = route.Labels("acme/widgets")
    labels.known = set(route.LABELS)
    route.apply("acme/widgets", 7, ["agk:ready"], "agk:merge-ready", labels)
    assert ("DELETE", "repos/acme/widgets/issues/7/labels/agk%3Aready") in calls
    assert "agk:ready" in route.LABELS


def test_the_readers_take_the_old_ready_label_as_merge_ready():
    """REQ-039: amendment 150 item 2 (plan, queue, uninstall read both names)."""
    assert {"agk:merge-ready", "agk:owner-merge", "agk:ready"} <= session_plan.READY_LABELS
    assert {"agk:merge-ready", "agk:ready"} <= set(session.ROLES["merger"])
    assert set(route.ACTOR) | {"agk:ready"} <= set(uninstall.LABELS)


def test_merge_cleared_holds_a_parked_pull_request_and_sees_a_stale_build_label():
    """REQ-039: Q-846-1 (`agk:parked` holds as `agk:hold` does); item 1 (`agk:build` is stale)."""
    assert merge_cleared.held_label({"labels": [{"name": "agk:parked"}]}) == "agk:parked"
    assert merge_cleared.held_label({"labels": [{"name": "agk:hold"}]}) == "agk:hold"
    assert merge_cleared.held_label({"labels": [{"name": "agk:merge-ready"}]}) is None
    assert "agk:build" in merge_cleared.STALE_LABELS


# --- item 4: the queues -------------------------------------------------------------------------


def test_each_role_lists_its_own_labels():
    """REQ-039: amendment 150 item 4 (builder, conductor, person and the new merger role) and
    amendment 162 item 4 (`agk:handover` is the builder's, listed first)."""
    assert set(session.ROLES["builder"]) == {
        "agk:handover",
        "agk:build",
        "agk:ci-red",
        "agk:conflict",
        "agk:fix",
    }
    assert set(session.ROLES["conductor"]) == {"agk:review", "agk:ci-red"}
    assert set(session.ROLES["person"]) == {
        "agk:question",
        "agk:approve",
        "agk:owner-merge",
        "agk:parked",
    }
    assert set(session.ROLES["merger"]) == {"agk:merge-ready", "agk:ready"}


# --- item 8: the doctor row ---------------------------------------------------------------------


def _row(tmp_path, labels, router: bool = True, toml: str = ""):
    dirs = prepare("ok", tmp_path)
    if router:
        workflow = dirs["root"] / ".github" / "workflows" / "agk-route.yml"
        workflow.write_text("name: agk-route\n", encoding="utf-8")
    if toml:
        config = dirs["root"] / "agk.toml"
        config.write_text(toml + "\n" + config.read_text(encoding="utf-8"), encoding="utf-8")
    if labels is not None:
        (dirs["api"] / "labels.json").write_text(json.dumps(labels), encoding="utf-8")
    proc = doctor("--api-dir", str(dirs["api"]), "--kit-root", str(dirs["kit"]), "--json",
                  str(dirs["root"]))  # fmt: skip
    return checks_of(proc.stdout)["state-labels"]


def good() -> list[dict]:
    return [{"name": n, "description": route.description_of(n)} for n in route.ACTOR]


def test_the_doctor_fixture_holds_the_labels_the_router_creates():
    """REQ-039: amendment 150 item 8 (the saved labels of the `ok` case are the router's own)."""
    root = Path(__file__).resolve().parents[2]
    saved = root / "tests/kit/fixtures/doctor/ok/api/labels.json"
    assert json.loads(saved.read_text(encoding="utf-8")) == good()


def test_doctor_is_ok_when_every_state_label_names_its_actor(tmp_path):
    """REQ-039: amendment 150 item 8 (`state-labels`, a warning, ok here)."""
    row = _row(tmp_path, good())
    assert (row["status"], row["severity"]) == ("ok", "warn")


@pytest.mark.parametrize("broken", ["missing", "old description"])
def test_doctor_warns_about_a_missing_or_unnamed_state_label(tmp_path, broken):
    """REQ-039: amendment 150 item 8 (it lists the label, never fails the run)."""
    labels = good()
    if broken == "missing":
        labels = [x for x in labels if x["name"] != "agk:question"]
    else:
        labels = [
            {**x, "description": "AGK: the state of a pull request"}
            if x["name"] == "agk:question"
            else x
            for x in labels
        ]
    row = _row(tmp_path, labels)
    assert (row["status"], row["severity"]) == ("fail", "warn")
    assert "agk:question" in row["message"]


def test_doctor_reads_nothing_without_a_router_or_in_local_mode(tmp_path):
    """REQ-039: amendment 150 item 8 (`not applicable` with no router and in local mode)."""
    for name, kw in (("a", {"router": False}), ("b", {"toml": 'execution = "local"'})):
        row = _row(tmp_path / name, None, **kw)
        assert row["status"] == "ok" and "not applicable" in row["message"], name


def test_doctor_cannot_check_unreadable_labels(tmp_path):
    """REQ-039: amendment 150 item 8 (a failed read is `cannot-check`, never ok)."""
    assert _row(tmp_path, {"message": "Server Error"})["status"] == "cannot-check"
