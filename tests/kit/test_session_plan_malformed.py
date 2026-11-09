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


# --- reservation clashes (amendment 141 item 5; REQ-057 AC11) ----------------------------------

CLASH = "rule 4 of SPEC-0050: Reserved {} is also held by #{}"


def reserving(line: str) -> str:
    return brief() + f"Reserved: {line}\n"


def open_pr(stub, number: int, brief_no: int, *files: dict) -> dict:
    stub.serve(f"repos/{REPO}/pulls/{number}/files", list(files))
    return {
        "number": number,
        "state": "open",
        "body": f"Brief: #{brief_no}\n",
        "labels": [],
        "head": {"ref": f"claude/brief-{brief_no}", "sha": "a" * 40},
        "updated_at": "2099-01-01T00:00:00Z",
        "created_at": "2099-01-01T00:00:00Z",
        "merged_at": None,
        "user": {"login": "x"},
    }


def served(proj, stub, issues, prs=()) -> str:
    stub.serve(f"repos/{REPO}/pulls", list(prs))
    listing(stub, issues)
    free(stub, *[i["number"] for i in issues])
    out = plan(proj, stub)
    assert out.returncode == 0, out.stdout + out.stderr
    return out.stdout


def test_ac11_of_two_briefs_the_later_one_is_refused_naming_both(proj, stub):
    """REQ-057 AC11: two open briefs reserve one number."""
    out = served(proj, stub, [filed(5, reserving("ADR-0900")), filed(6, reserving("ADR-0900"))])
    assert malformed(out) == [f"MALFORMED: #6 {CLASH.format('ADR-0900', 5)} (fix: filer)"]


def test_ac11_an_amendment_number_is_a_reservation(proj, stub):
    """REQ-057 AC11: `amendment n` counts."""
    out = served(
        proj, stub, [filed(5, reserving("amendment 139")), filed(6, reserving("amendment 139"))]
    )
    assert malformed(out) == [f"MALFORMED: #6 {CLASH.format('amendment 139', 5)} (fix: filer)"]


def test_ac11_a_brief_yields_to_a_pull_request_of_another_brief(proj, stub):
    """REQ-057 AC11: the brief is refused and the pull request is named."""
    added = {"filename": "docs/adr/0900-a.md", "status": "added"}
    pr = open_pr(stub, 40, 9, added)
    out = served(proj, stub, [filed(5, reserving("ADR-0900"))], [pr])
    assert malformed(out) == [f"MALFORMED: #5 {CLASH.format('ADR-0900', 40)} (fix: filer)"]


def test_ac11_a_brief_s_own_pull_request_is_excepted(proj, stub):
    """REQ-057 AC11: the pull request of that brief (its `Brief: #n` line) holds nothing."""
    added = {"filename": "docs/runs/proposed-spec-amendments-139.md", "status": "added"}
    pr = open_pr(stub, 40, 5, added)
    assert malformed(served(proj, stub, [filed(5, reserving("amendment 139"))], [pr])) == []


def test_ac11_a_requirement_added_by_a_pull_request_is_a_clash(proj, stub):
    """REQ-057 AC11: `REQ-nnn` is read from the added section of the requirements."""
    changed = {
        "filename": "docs/requirements.md",
        "status": "modified",
        "patch": "@@ -1 +1,2 @@\n+### REQ-900 — x\n",
    }
    pr = open_pr(stub, 40, 9, changed)
    out = served(proj, stub, [filed(5, reserving("REQ-900"))], [pr])
    assert malformed(out) == [f"MALFORMED: #5 {CLASH.format('REQ-900', 40)} (fix: filer)"]


def test_ac11_a_modified_adr_is_not_a_reservation_clash(proj, stub):
    """REQ-057 AC11: a pull request that only edits an ADR adds no number."""
    changed = {"filename": "docs/adr/0900-a.md", "status": "modified"}
    pr = open_pr(stub, 40, 9, changed)
    assert malformed(served(proj, stub, [filed(5, reserving("ADR-0900"))], [pr])) == []


def test_ac11_text_in_brackets_is_not_a_reservation(proj, stub):
    """REQ-057 AC11, Q-772-9: only the text before the first `(`."""
    one = filed(5, reserving("none (Covered-by: ADR-0303)"))
    two = filed(6, reserving("ADR-0304 (not ADR-0303)"))
    three = filed(7, reserving("ADR-0303"))
    assert malformed(served(proj, stub, [one, two, three])) == []


def test_ac11_a_refused_brief_does_not_start(proj, stub):
    """REQ-057 AC11: a refused brief is not planned."""
    listing(stub, [filed(5, reserving("ADR-0900")), filed(6, reserving("ADR-0900"))])
    free(stub, 5, 6)
    out = json.loads(plan(proj, stub, "--json").stdout)
    assert [row["brief"] for row in out["start"]] == [5]


def test_q_772_9_the_reserved_numbers_of_a_take_stop_at_the_bracket():
    """Q-772-9: `session.reserved_numbers` reads the same way."""
    import session

    body = "Reserved: ADR-0304 (Covered-by: ADR-0303)\n"
    assert session.reserved_numbers(body, []) == ["ADR-0304"]
    assert session.reservations(
        "Reserved: REQ-901, SPEC-0901, ADR-0901, amendment 7 (x ADR-1)\n"
    ) == [
        "REQ-901",
        "SPEC-0901",
        "ADR-0901",
        "amendment 7",
    ]
