"""The flow in the facts (SPEC-0034 rule 10, SPEC-0033 rule 5 and SPEC-0032 rule 11; build (d)).

The `flow` case of `fixtures/facts/` holds saved GitHub copies of four briefs' pull requests: the
`Brief: #n` line, the `taken:` comments of the briefs, `conflict needs a person:` comments, commits
that renumber, `Correction:` comments and the labels of open pull requests. A figure that cannot be
read is `unknown`, never 0. No network, no model. REQ-041 AC8, REQ-040 AC5, REQ-039.
"""

from __future__ import annotations

from test_facts import document


def pulls(doc: dict) -> dict:
    return {p["number"]: p for p in doc["pull_requests"]}


def test_ac8_a_pull_request_carries_its_brief_and_the_hours_between_its_steps(tmp_path):
    """REQ-041 AC8: rule 10 (taken to pull request, to first verdict, to cleared, to merge)."""
    doc = document("flow", tmp_path)
    first, second = pulls(doc)[20], pulls(doc)[21]
    assert first["brief"] == 30 and second["brief"] == 31
    assert first["flow"] == {
        "taken_to_pull_request": "2.0",
        "to_first_verdict": "24.0",
        "verdict_to_cleared": "48.0",
        "cleared_to_merge": "24.0",
    }
    # the brief was taken twice: the take that counts is the latest one before the pull request
    assert second["flow"] == {
        "taken_to_pull_request": "4.0",
        "to_first_verdict": "6.0",
        "verdict_to_cleared": "0.0",
        "cleared_to_merge": "36.0",
    }


def test_ac8_a_step_that_did_not_happen_is_null(tmp_path):
    """REQ-041 AC8: rule 10 (never 0 for what is not known)."""
    doc = document("flow", tmp_path)
    assert pulls(doc)[22]["flow"] == {
        "taken_to_pull_request": None,
        "to_first_verdict": None,
        "verdict_to_cleared": None,
        "cleared_to_merge": None,
    }
    assert pulls(doc)[24]["brief"] is None


def test_ac8_conflicts_renumbers_and_corrections_are_counted_from_comments_and_commits(tmp_path):
    """REQ-041 AC8: rule 10 (conflicts, renumbers); REQ-039: rule 11 (corrections)."""
    doc = document("flow", tmp_path)
    first = pulls(doc)[20]
    assert (first["conflicts"], first["renumbers"]) == (1, 1)
    assert first["corrections"] == ["2026-10-11T11:00:00Z"]
    assert (pulls(doc)[21]["conflicts"], pulls(doc)[21]["renumbers"]) == (0, 0)
    assert doc["flow"]["corrections"] == ["2026-10-11T11:00:00Z", "2026-10-13T08:00:00Z"]


def test_ac8_retakes_and_the_open_briefs_are_listed_with_what_they_advance(tmp_path):
    """REQ-041 AC8: rule 10 (retakes, briefs with no pull request, requirements with no brief)."""
    flow = document("flow", tmp_path)["flow"]
    assert flow["retakes"] == ["2026-10-12T08:00:00Z"]
    assert [(b["number"], b["advances"]) for b in flow["briefs"]] == [
        (30, ["REQ-001"]),
        (31, ["REQ-001"]),
        (32, ["REQ-001"]),
        (33, "new"),
        (34, "new"),
    ]
    assert flow["briefs"][3]["created_at"] == "2026-10-02T09:00:00Z"
    assert (flow["max_builders"], flow["stall_hours"]) == (2, 4)


def test_ac5_only_work_that_waits_on_its_builder_stalls(tmp_path):
    """REQ-040 AC5: rule 5 (a label or draft unchanged for stall_hours; never a person's wait)."""
    doc = document("flow", tmp_path)
    assert [pulls(doc)[n]["stalled"] for n in (22, 23, 24)] == [True, False, False]
    assert pulls(doc)[20]["stalled"] is None  # a merged pull request cannot stall


def test_ac8_without_the_saved_copies_the_figures_are_unknown_and_never_zero(tmp_path):
    """REQ-041 AC8: rule 10."""
    doc = document("ok", tmp_path, api=False)
    assert doc["pull_requests"] == "unknown"
    assert (
        doc["flow"]["briefs"] == doc["flow"]["retakes"] == doc["flow"]["corrections"] == "unknown"
    )
    assert doc["flow"]["max_builders"] == 3 and doc["flow"]["stall_hours"] == 4


def test_ac8_a_pull_request_with_no_brief_no_conflict_and_no_flow_is_plain(tmp_path):
    """REQ-041 AC8"""
    doc = document("ok", tmp_path)
    first = pulls(doc)[5]
    assert first["brief"] is None and first["conflicts"] == 0 and first["stalled"] is None
    assert doc["flow"]["briefs"] == [] and doc["flow"]["retakes"] == []


def test_ac8_an_invalid_flow_value_is_unknown_in_the_facts_and_never_a_default(tmp_path):
    """REQ-041 AC8"""
    from test_facts import build_repo, run_facts

    root = build_repo("ok", tmp_path)
    (root / "agk.toml").write_text(
        (root / "agk.toml").read_text(encoding="utf-8")
        + '[flow]\nmax_builders = "x"\nstall_hours = 0\n',
        encoding="utf-8",
    )
    import json

    flow = json.loads(run_facts(root, "ok", tmp_path).stdout)["flow"]
    assert (flow["max_builders"], flow["stall_hours"]) == ("unknown", "unknown")
