"""Governance skips its heavy steps on a status-only final commit (brief #234, #216 build c).

`status_only.py` makes the one decision for proof and for governance: the head is one commit after
its parent, the commit changes only `- Status:` lines, the check passed on the parent (for
governance: the full run of governance, `--parent-governance`) and the default branch has not
moved past the parent. The workflow skips the steps whose inputs a status line cannot change and
keeps every other one. Fixture commits in `tmp_path` and the workflow file as text; no network.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE = ROOT / ".github" / "workflows" / "governance.yml"
ADR = "docs/adr/0001-x.md"
SPEC = "docs/specs/0001-x.md"
ADR_TEXT = "# ADR-0001: x\n\n- Status: Proposed\n- Date: 2026-10-25\n"
SPEC_TEXT = "# SPEC-0001: x\n\n- Status: Draft\n- Owner: o\n"


def adr(status: str, extra: str = "") -> str:
    return ADR_TEXT.replace("Proposed", status) + extra


@pytest.fixture
def work(repo):
    repo.commit({"a.txt": "one\n", ADR: ADR_TEXT, SPEC: SPEC_TEXT}, "base")
    repo.git("branch", "-M", "main")
    repo.branch("feature")
    repo.commit({"a.txt": "two\n"}, "code")
    return repo.git("rev-parse", "HEAD").strip()


def decide(repo, kind: str, value: str = "success", base: str = "main", head: str = "HEAD"):
    flag = {"proof": "--parent-proof", "governance": "--parent-governance"}[kind]
    out = repo.run("status_only.py", "--head", head, flag, value, "--base", base)
    assert out.returncode == 0, out.stdout + out.stderr
    return out.stdout.strip()


def test_a_status_only_commit_with_an_unchanged_base_and_a_full_parent_run_skips(repo, work):
    """Brief #234 answer 5: status-only with an unchanged base (skips)."""
    repo.commit({ADR: adr("Accepted")}, "Final: ADR-0001 Proposed -> Accepted")
    assert decide(repo, "governance") == "skip"


def test_a_moved_base_runs_in_full(repo, work):
    """Brief #234 answer 3 and 5: main moved past the parent, so the code checked is new."""
    repo.commit({ADR: adr("Accepted")}, "final")
    repo.git("checkout", "-q", "main")
    repo.commit({"b.txt": "x\n"}, "main moves")
    repo.git("checkout", "-q", "feature")
    assert decide(repo, "governance").startswith("run (")


@pytest.mark.parametrize("value", ["failure", "cancelled", "", "skipped", "neutral", "SUCCESS"])
def test_a_parent_whose_full_governance_run_did_not_pass_runs_in_full(repo, work, value):
    """Brief #234 answer 1 and 5: the parent's governance red (or unknown) runs in full."""
    repo.commit({ADR: adr("Accepted")}, "final")
    out = decide(repo, "governance", value)
    assert out.startswith("run (") and "governance" in out


@pytest.mark.parametrize(
    "files",
    [
        {"a.txt": "three\n"},
        {ADR: adr("Accepted", "- Extra: x\n")},
        {ADR: adr("Accepted"), "a.txt": "three\n"},
        {ADR: adr("Accepted"), "docs/new.md": "x\n"},
    ],
)
def test_a_commit_that_changes_more_than_a_status_line_runs_in_full(repo, work, files):
    """Brief #234 answer 5: a non-status change runs in full."""
    repo.commit(files, "change")
    assert decide(repo, "governance").startswith("run (")


def test_a_merge_commit_and_a_root_commit_run_in_full(repo, work):
    """Brief #234 answer 1: one commit after its parent."""
    repo.git("checkout", "-q", "main")
    repo.commit({"b.txt": "x\n"}, "main moves")
    repo.git("checkout", "-q", "feature")
    repo.git("merge", "-q", "--no-ff", "main", "-m", "merge main")
    assert decide(repo, "governance").startswith("run (")


def test_governance_makes_the_same_decision_as_proof_on_every_case(repo, work):
    """Brief #234 answer 1: one copy of the decision, so proof and governance cannot differ."""
    cases = []
    repo.commit({ADR: adr("Accepted")}, "final")
    cases.append(decide(repo, "proof") == decide(repo, "governance"))
    repo.commit({"a.txt": "three\n"}, "code")
    cases.append(decide(repo, "proof") == decide(repo, "governance"))
    repo.git("checkout", "-q", "main")
    repo.commit({"b.txt": "x\n"}, "main moves")
    repo.git("checkout", "-q", "feature")
    repo.commit({SPEC: SPEC_TEXT.replace("Draft", "Approved")}, "final 2")
    cases.append(decide(repo, "proof") == decide(repo, "governance"))
    assert all(cases)


def test_the_reasons_name_the_condition_and_never_a_value(repo, work):
    """CLAUDE.md rule 6"""
    repo.commit({ADR: adr("Accepted", "- Secret: hunter2\n")}, "change")
    out = decide(repo, "governance")
    assert "hunter2" not in out and "0001" not in out and "Accepted" not in out


def test_the_two_parent_conclusions_are_not_given_together(repo, work):
    """Brief #234 answer 1: one check at a time."""
    both = repo.run(
        "status_only.py", "--head", "HEAD", "--parent-proof", "success", "--parent-governance", "x"
    )
    assert both.returncode == 2


# --- the workflow --------------------------------------------------------------------------------

SKIPPED = ("Install tooling", "check_kit_tests", "Lint", "Tests of the checks", "Project tests")
KEPT_FOR_A_REASON = ("Secret scan",)


def steps() -> dict[str, str]:
    body = GOVERNANCE.read_text(encoding="utf-8").split("    steps:\n", 1)[1]
    parts = re.split(r"(?m)^      - (?=name: |uses: )", body)[1:]
    return {m.group(1).strip(): p for p in parts if (m := re.match(r"name: (.+)", p))}


def head_of(part: str) -> str:
    """The step up to its `run:` or `uses:` (the conditions and the environment)."""
    return part.split("run:", 1)[0]


def test_the_status_step_decides_with_the_one_script_and_the_parents_full_run():
    """Brief #234 answers 1 and 4: status_only.py, the parent's full run, the summary."""
    part = steps()["Status-only final commit"]
    assert "scripts/agk/status_only.py" in part and "--parent-governance" in part
    assert 'display_title == "governance full"' in part
    assert "$GITHUB_STEP_SUMMARY" in part
    assert (
        "github.event_name == 'pull_request'" in part and "github.event.action != 'edited'" in part
    )
    assert "git diff" not in part and "Status:" not in part.replace("Status-only", "")


def test_the_status_step_runs_before_every_step_it_can_skip():
    """Brief #234 answer 2"""
    names = list(steps())
    for name in SKIPPED:
        assert names.index("Status-only final commit") < names.index(name), name


def test_exactly_the_named_steps_are_skipped_on_a_status_only_commit():
    """Brief #234 answer 2: the list of the ADR, pinned to the workflow."""
    found = {
        name
        for name, part in steps().items()
        if "steps.status.outputs.skip != 'true'" in head_of(part)
    }
    assert found == set(SKIPPED)


def test_every_step_that_reads_statuses_numbers_specs_or_the_body_keeps_running():
    """Brief #234 answer 2: check_final_clearance above all; when unsure, keep the step."""
    for name in (
        "check_protected_changes",
        "check_requirements",
        "check_adrs",
        "check_numbers",
        "check_specs",
        "check_neutrality",
        "check_build_state",
        "check_design",
        "check_pr_mode",
        "check_final_clearance",
        "PR body shape",
        *KEPT_FOR_A_REASON,
    ):
        assert "outputs.skip" not in steps()[name], name
    assert "check_final_clearance" in steps()


def test_a_skipped_run_names_the_parent_run_it_relies_on():
    """Brief #234 answer 4: one line in the job summary."""
    part = steps()["Status-only final commit"]
    assert re.search(r"echo .*GITHUB_STEP_SUMMARY", part)
    assert "parent" in part and "run" in part.split("GITHUB_STEP_SUMMARY", 1)[0].lower()


def test_the_job_and_its_name_stay_and_nothing_is_added_to_the_permissions():
    """Brief #234 principles: the required check still reports; no write permission."""
    text = GOVERNANCE.read_text(encoding="utf-8")
    assert "\njobs:\n  governance:\n" in text
    perms = text.split("\npermissions:\n", 1)[1].split("\n\n", 1)[0]
    assert "write" not in perms
