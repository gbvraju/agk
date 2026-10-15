"""Tests of .github/workflows/governance.yml shape."""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "governance.yml"


def test_ac2_pr_workflow_reruns_on_body_edit():
    """REQ-008 AC2: pull_request types include edited so a PR body fix re-runs the check."""
    text = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(r"pull_request:\s*\n\s*types:\s*\[([^\]]*)\]", text)
    assert match, "pull_request must list types"
    types = {t.strip() for t in match.group(1).split(",")}
    assert {"opened", "synchronize", "reopened", "edited"} <= types


def test_ac2_pr_body_step_reads_event_body_via_env_not_inline():
    """REQ-008 AC2: the PR body reaches the check through an env var."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "PR_BODY: ${{ github.event.pull_request.body }}" in text
    assert "printf '%s\\n' \"$PR_BODY\"" in text


def test_ac2_every_action_is_pinned_to_a_full_commit_sha():
    """REQ-009 AC2: each `uses:` line is pinned to a 40-character SHA with the tag in a comment."""
    text = WORKFLOW.read_text(encoding="utf-8")
    uses = re.findall(r"^\s*-?\s*uses:\s*(.+)$", text, flags=re.M)
    assert uses, "the workflow uses at least one action"
    for line in uses:
        assert re.fullmatch(r"\S+@[0-9a-f]{40}\s+# v\d+(\.\d+){1,2}", line.strip()), line


def test_ac2_workflow_has_no_branch_name_and_gates_on_the_default_branch():
    """REQ-010 AC1 (SPEC-0002 rule 8): push runs everywhere; the job gates on the default branch."""
    text = WORKFLOW.read_text(encoding="utf-8")
    on_block = text.split("permissions:")[0]
    assert "branches:" not in on_block
    assert re.search(r"^\s*push:\s*$", on_block, flags=re.M)
    assert (
        "github.event_name == 'pull_request' || "
        "github.ref_name == github.event.repository.default_branch"
    ) in text
    assert re.search(r"^\s*if:\s*\$\{\{", text, flags=re.M)


def step_blocks(text: str) -> dict[str, str]:
    """Step name -> its block of lines."""
    parts = re.split(r"^      - ", text, flags=re.M)[1:]
    out = {}
    for part in parts:
        match = re.match(r"name:\s*(.+)", part)
        if match:
            out[match.group(1).strip()] = part
    return out


def test_ac2_governance_is_one_step_per_check_named_by_its_check_id():
    """REQ-012 AC1 (SPEC-0007 rule 13): the steps equal the commands of agk-governance, in order."""
    text = WORKFLOW.read_text(encoding="utf-8")
    mk = (WORKFLOW.parents[2] / "agk.mk").read_text(encoding="utf-8")
    recipe = mk.split("agk-governance:\n", 1)[1].split("\n\n", 1)[0]
    commands = [ln.strip().removeprefix("$(PY) ") for ln in recipe.splitlines()]
    blocks = step_blocks(text)
    names = list(blocks)
    for command in commands:
        script, _, flag = command.removeprefix("scripts/agk/").partition(".py")
        check_id = script if script.startswith("check_") else f"reviewers{flag}"
        assert check_id in blocks, check_id
        assert f"run: python {command}" in blocks[check_id], check_id
    ids = [n for n in names if n.startswith(("check_", "reviewers"))]
    assert len(ids) == len(commands) == 9
    assert names.index(ids[0]) < names.index("PR body shape")
    assert "Governance checks" not in names


def test_ac2_every_check_step_runs_unless_cancelled():
    """REQ-012 AC1 (SPEC-0007 rule 13): each failure shows on its own step; the job still fails."""
    text = WORKFLOW.read_text(encoding="utf-8")
    checks = {n: b for n, b in step_blocks(text).items() if n.startswith(("check_", "reviewers"))}
    assert len(checks) == 9
    for name, block in checks.items():
        assert "        if: ${{ !cancelled() }}\n" in block, name
    # the job is not marked to continue on error, so one failing step fails the job
    assert "continue-on-error" not in text


def test_ac2_the_job_is_still_named_governance():
    """REQ-012 AC1 (SPEC-0007 rule 13): the required status check does not change."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert re.search(r"^jobs:\n  governance:\n", text, flags=re.M)
    assert re.search(r"^name: governance$", text, flags=re.M)


def test_ac2_pull_request_base_reaches_the_checks_through_the_job_environment():
    """REQ-012 AC1: AGK_BASE is set for every step, so each check sees the base."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "    env:\n      AGK_BASE: ${{ github.event.pull_request.base.sha }}" in text


def test_ac2_workflow_calls_the_agk_mk_form_for_lint_and_tests():
    """REQ-010 AC1 (SPEC-0002 rule 5): lint and tests are called through agk.mk."""
    text = WORKFLOW.read_text(encoding="utf-8")
    for target in ("agk-lint", "agk-test"):
        assert f"run: make -f agk.mk {target}" in text
    assert not re.search(r"run: make (governance|lint|test)\b", text)


def test_ac2_project_tests_step_follows_the_tests_of_the_checks():
    """REQ-010 AC1 (SPEC-0002 rule 5): CI runs the project's own tests after the kit tests."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "run: make -f agk.mk agk-project-test" in text
    assert text.index("name: Tests of the checks") < text.index("name: Project tests")
    assert text.index("agk-test") < text.index("agk-project-test")
