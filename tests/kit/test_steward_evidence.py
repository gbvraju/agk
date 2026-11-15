"""Tests of scripts/agk/steward_evidence.py: the evidence rule, the stage and the answer form
(SPEC-0059 rules 2, 3, 4 and 18; brief #1321, ADR-0558; REQ-066).

Invented data only (example.com); no network, no model: the `gh` double of test_steward_memory.py
counts every call.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts" / "agk"))
sys.path.insert(0, str(HERE))

import steward  # noqa: E402
import steward_evidence as ev  # noqa: E402
from test_steward_memory import NOW, GitHub  # noqa: E402

TODAY = date(2026, 11, 15)
SPEC = {"source": 2, "answer": "weekly", "place": "docs/specs/0001-report.md rule 3", "rule": "3"}
RULE = {"source": 5, "answer": "make lint", "place": "Makefile:12", "rule": "session rule 31"}


def question(cls="technical", findings=(RULE,), **more) -> dict:
    return {"id": "Q-7-1", "class": cls, "findings": list(findings), **more}


# --- the stage (rule 2, Q-S0059-10) --------------------------------------------------------------


@pytest.mark.parametrize(
    ("files", "conductor", "stage"),
    [
        ((), False, "start"),
        (("docs/discovery/report.md",), False, "vision and discovery"),
        (("docs/plan/scope.md",), False, "scope"),
        (("docs/adr/0002-stack-options.md",), False, "stack and technical design"),
        (("docs/plan/milestones.md",), False, "plan"),
        (("docs/plan/scope-lock.md", "docs/adr/0002-stack-options.md"), False, "plan"),
        ((), True, "build"),
    ],
)
def test_req066_the_stage_is_read_on_the_guided_path(tmp_path, files, conductor, stage):
    """REQ-066: rule 2, the stage in the owner's words, from the files and the conductor's issue."""
    for rel in files:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("# invented\n", encoding="utf-8")
    assert ev.stage_of(tmp_path, TODAY, conductor) == stage
    assert ev.building(stage) is (stage == "build")


# --- rule 3 by stage (a) planning, (b) building, (c) every stage --------------------------------


def test_req066_a_planning_technical_question_is_answered_in_the_form():
    """REQ-066: rules 3(a) and 4, a technical question the kit's rules settle is the steward's."""
    found = ev.settle(question(), "plan")
    assert found["to"] == "answer"
    assert found["line"] == (
        "Answer: Q-7-1 make lint (evidence: AGK rule or code Makefile:12; rule: session rule 31)"
    )
    body = ev.answer_body(found)
    assert body.splitlines()[0] == found["line"]
    assert body.rstrip().endswith("Who: AGK steward")


def test_req066_a_planning_requirement_question_goes_to_the_owner_with_a_recommendation():
    """REQ-066: rule 3(a), even when a source settles it."""
    found = ev.settle(question("requirement", [SPEC]), "vision and discovery")
    assert found["to"] == "owner" and found["line"] is None
    assert "weekly" in found["recommendation"] and "docs/specs/0001-report.md" in found["evidence"]
    assert not found["gap"]


def test_req066_a_building_requirement_answer_waits_for_the_recheck():
    """REQ-066: rules 3(b), 4 and 13, settled in building, but posted only with the re-check."""
    found = ev.settle(question("requirement", [SPEC]), "build")
    assert found["to"] == "owner" and "re-check" in found["reason"]
    assert "weekly" in found["recommendation"]


def test_req066_a_question_the_plan_never_decided_is_a_planning_gap():
    """REQ-066: rule 3, a planning gap in building goes to the owner and records a `Gap:`."""
    found = ev.settle(question("requirement", [RULE]), "build")
    assert found["to"] == "owner" and found["gap"]
    assert found["record"].startswith("Gap: Q-7-1 ")
    assert not ev.settle(question("requirement", [RULE]), "plan")["gap"]


@pytest.mark.parametrize("stage", ev.STAGES)
@pytest.mark.parametrize("cls", sorted(ev.OWNER_CLASSES))
def test_req066_business_scope_date_cost_and_signoff_go_to_the_owner_in_every_stage(stage, cls):
    """REQ-066: rule 3(c)."""
    assert ev.settle(question(cls), stage)["to"] == "owner"


@pytest.mark.parametrize(
    "more",
    [{"changes": ["date"]}, {"changes": ["cost"]}, {"reverses": True}, {"findings": []}],
)
def test_req066_the_negative_cases_go_to_the_owner(more):
    """REQ-066: rule 3, a changed date or cost, a reversed decision, no source."""
    assert ev.settle(question(**more), "build")["to"] == "owner"


def test_req066_the_first_source_wins_and_a_disagreement_needs_a_ranking():
    """REQ-066: rule 3, the order of the sources; two answers with no ranking go to the owner."""
    owner = {"source": 1, "answer": "make lint", "place": "comment 6800000001", "rule": "1"}
    found = ev.settle(question(findings=[RULE, owner]), "build")
    assert "owner decision comment 6800000001" in found["line"]
    other = {**RULE, "source": 4, "answer": "make check", "place": "docs/sources/a.md:4"}
    assert ev.settle(question(findings=[RULE, other]), "build")["to"] == "owner"
    ranked = question(findings=[RULE, other], ranking={"source": 5, "place": "comment 6800000002"})
    found = ev.settle(ranked, "build")
    assert found["to"] == "answer" and "make lint" in found["line"]
    assert "ranking comment 6800000002" in found["line"]


def test_req066_a_question_that_cannot_be_read_is_refused(tmp_path, capsys):
    """REQ-066: a malformed question file is refused naming the field, never the value."""
    path = tmp_path / "q.json"
    path.write_text(json.dumps({"id": "Q-7-1", "class": "secretive", "findings": []}))
    assert ev.main(["settle", "--question", str(path), "--stage", "build"]) == 2
    assert "class" in capsys.readouterr().err


# --- rule 18: one mechanical answer, at most 15 counted calls and one comment --------------------


class Pass(GitHub):
    def __call__(self, method, endpoint, fields=None):
        if "labels=agk-conductor" in endpoint:
            self.calls.append((method, endpoint))
            return [{"number": 9}]
        return super().__call__(method, endpoint, fields)


def test_req066_one_mechanical_answer_costs_at_most_15_calls_and_posts_one_comment(
    tmp_path, monkeypatch
):
    """REQ-066 AC1: rule 18's measured budget for one steward pass."""
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(tmp_path / "cache.json"))
    (tmp_path / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    gh = Pass()
    pr = gh.add_issue(labels=())
    gh.comment(pr, "Question: Q-7-1 which target lints the kit?")
    steward.start(tmp_path, "s1", gh, NOW)
    gh.calls.append(("GET", f"repos/{{owner}}/{{repo}}/issues/{pr}/comments"))  # the read
    code, lines = ev.answer(tmp_path, question(), pr, gh, TODAY)
    steward.end(tmp_path, "s1", gh, NOW)
    assert code == 0, lines
    assert gh.counted() <= 15
    answers = [c for c in gh.issues[pr]["c"] if c["body"].startswith("Answer:")]
    assert len(answers) == 1 and answers[0]["body"].startswith("Answer: Q-7-1 make lint")


def test_req066_an_owner_question_posts_no_answer(tmp_path):
    """REQ-066: rule 4, no `Answer:` on a question that rule 3 sends to the owner."""
    gh = Pass()
    pr = gh.add_issue(labels=())
    code, lines = ev.answer(tmp_path, question("cost"), pr, gh, TODAY)
    assert code == 3 and lines[0].startswith("owner: ")
    assert not gh.issues[pr]["c"]
