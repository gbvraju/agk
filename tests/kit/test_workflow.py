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


def test_ac2_workflow_calls_the_agk_mk_form():
    """REQ-010 AC1 (SPEC-0002 rule 5): governance, lint and tests are called through agk.mk."""
    text = WORKFLOW.read_text(encoding="utf-8")
    for target in ("agk-governance", "agk-lint", "agk-test"):
        assert f"run: make -f agk.mk {target}" in text
    assert not re.search(r"run: make (governance|lint|test)\b", text)


def test_ac2_project_tests_step_follows_the_tests_of_the_checks():
    """REQ-010 AC1 (SPEC-0002 rule 5): CI runs the project's own tests after the kit tests."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "run: make -f agk.mk agk-project-test" in text
    assert text.index("name: Tests of the checks") < text.index("name: Project tests")
    assert text.index("agk-test") < text.index("agk-project-test")
