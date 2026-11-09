"""session.py plan names each brief refused for a brief-check rule (brief #770; REQ-037; ADR-0357).

One line `MALFORMED: #<n> <rule> (fix: <filer>)` for each, nothing for a brief that is only taken;
with `[flow] plan_issue` a brief without a wave of the plan is refused the same way. A `gh` stub
serves saved JSON copies; invented data, no network."""

from __future__ import annotations

import json

import pytest
from test_session import ISSUES, REPO, Stub, comment, issue, listing
from test_session_flow import brief, flow
from test_session_plan import free, plan

MILESTONES = f"repos/{REPO}/milestones"
LONG = 'Sentence: "' + "x" * 301 + '"\n'
RULE = "rule 4: the Sentence is not 1 to 300 characters"
NO_WAVE = "rule 4: exactly one line Wave: n (setting: plan_issue)"


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    repo.write("config/protected-paths.txt", "config/\nscripts/agk/\n")
    return repo


def filed(number: int, body: str, login: str = "filer") -> dict:
    return {**issue(number, body), "user": {"login": login}}


def malformed(out: str) -> list[str]:
    return [x for x in out.splitlines() if x.startswith("MALFORMED:")]


def long_sentence() -> str:
    body = brief()
    return "\n".join(LONG.strip() if x.startswith("Sentence:") else x for x in body.splitlines())


def test_a_refused_brief_gets_its_own_line_naming_the_rule_and_the_filer(proj, stub):
    listing(stub, [filed(5, long_sentence())])
    out = plan(proj, stub).stdout
    assert malformed(out) == [f"MALFORMED: #5 {RULE} (fix: filer)"]
    assert "xxx" not in out
    assert not any(x.startswith("Skipped:") and "#5" in x for x in out.splitlines())


def test_a_taken_brief_prints_no_malformed_line(proj, stub):
    listing(stub, [filed(6, brief())])
    stub.serve(f"{ISSUES}/6/comments", [comment(1, "other", "taken: b2 2099-01-01")])
    assert malformed(plan(proj, stub).stdout) == []


def test_a_good_brief_prints_no_malformed_line(proj, stub):
    listing(stub, [filed(7, brief())])
    free(stub, 7)
    assert malformed(plan(proj, stub).stdout) == []


def test_json_carries_the_same_rows(proj, stub):
    listing(stub, [filed(5, long_sentence())])
    data = json.loads(plan(proj, stub, "--json").stdout)
    assert data["malformed"] == [{"brief": 5, "why": RULE, "filer": "filer"}]
    assert all(row["brief"] != 5 for row in data["skipped"])


def test_with_a_plan_issue_a_brief_without_a_wave_is_refused(proj, stub):
    flow(proj, "plan_issue = 9")
    stub.serve(MILESTONES, [{"title": "Wave 1: first"}, {"title": "v1 acceptance run"}])
    listing(stub, [filed(5, brief())])
    assert malformed(plan(proj, stub).stdout) == [f"MALFORMED: #5 {NO_WAVE} (fix: filer)"]


def test_with_a_plan_issue_a_wave_of_the_plan_passes_and_another_is_refused(proj, stub):
    flow(proj, "plan_issue = 9")
    stub.serve(MILESTONES, [{"title": "Wave 1: first"}])
    listing(stub, [filed(5, brief() + "Wave: 1\n"), filed(6, brief() + "Wave: 7\n")])
    free(stub, 5)
    assert malformed(plan(proj, stub).stdout) == [
        "MALFORMED: #6 rule 4: the Wave line names a wave the plan does not have (fix: filer)"
    ]


def test_with_no_plan_issue_no_wave_is_needed_and_no_milestone_is_read(proj, stub):
    listing(stub, [filed(7, brief())])
    free(stub, 7)
    assert malformed(plan(proj, stub).stdout) == []
    assert not any("milestones" in " ".join(map(str, call)) for call in stub.calls())
