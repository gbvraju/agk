"""Tests of the facts artifact of .github/workflows/product-report.yml (SPEC-0019, REQ-026).

The workflow file is read as text and its shell body is run against a stub `gh` and a fixture; no
network and no model.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists, and a stub `gh`
from pathlib import Path

from test_product_report_workflow import ALLOWED_GH, FIXTURE, ROOT, body_with_facts, script, text

SECURITY = ROOT / "docs" / "guides" / "security.md"


def upload_step() -> str:
    """The text of the step that uses the upload action (one step, from its `- name:` line)."""
    steps = re.split(r"(?m)^      - ", text())
    found = [s for s in steps if "upload-artifact" in s]
    assert len(found) == 1, "the workflow has exactly one upload step"
    return found[0]


def with_value(step: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s+{re.escape(key)}:\s*(.*?)\s*$", step)
    return match.group(1) if match else None


def test_ac1_the_workflow_has_one_upload_step_named_from_the_week_label():
    """REQ-026 AC1: SPEC-0019 rules 1 and 3 (`agk-facts-<week>`, the week the report step wrote)."""
    step = upload_step()
    assert with_value(step, "name") == "agk-facts-${{ steps.report.outputs.week }}"
    assert re.search(r"(?m)^      - name: .*\n(?:        .*\n)*?        id: report\b", text()), (
        "the report step has the id `report`"
    )
    assert 'echo "week=$week" >> "$GITHUB_OUTPUT"' in script()


def test_ac2_the_artifact_is_the_file_the_report_was_rendered_from():
    """REQ-026 AC2: SPEC-0019 rules 2 and 3 (the path facts.py wrote and product_report.py read)."""
    run = script()
    assert 'facts="$RUNNER_TEMP/facts.json"' in run
    assert 'scripts/agk/facts.py --today "$today" --repo "$GITHUB_REPOSITORY" > "$facts"' in run
    assert 'scripts/agk/product_report.py --facts "$facts"' in run
    assert with_value(upload_step(), "path") == "${{ runner.temp }}/facts.json"


def run_body(tmp_path: Path, facts_text: str | None = None):
    """The shell body run with facts.py replaced by a copy of the fixture (or of `facts_text`)."""
    script_file = body_with_facts(tmp_path, [])
    if facts_text is not None:
        (tmp_path / "source.json").write_text(facts_text, encoding="utf-8")
    (tmp_path / "scripts").symlink_to(ROOT / "scripts")
    github_output = tmp_path / "github-output"
    env = {
        "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "RUNNER_TEMP": str(tmp_path),
        "INPUT_TODAY": "2026-10-14",
        "GITHUB_REPOSITORY": "demo-org/demo-repo",
        "GH_TOKEN": "unused",
        "GITHUB_OUTPUT": str(github_output),
    }
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell string
        [shutil.which("bash") or "bash", "-eo", "pipefail", str(script_file)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    log = tmp_path / "gh-calls"
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    out = github_output.read_text(encoding="utf-8") if github_output.exists() else ""
    return proc, calls, out


def test_ac2_the_file_at_the_upload_path_is_the_fixture_byte_for_byte(tmp_path):
    """REQ-026 AC2: SPEC-0019 rule 2 (run against a stub `gh`: nothing filtered or added)."""
    proc, _, out = run_body(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "week=2026-W41" in out.splitlines()
    uploaded = (tmp_path / "facts.json").read_bytes()
    assert uploaded != b"" and uploaded == (tmp_path / "source.json").read_bytes()


def test_ac3_the_upload_step_follows_the_issue_step_and_is_pinned_and_strict():
    """REQ-026 AC3: SPEC-0019 rule 3 (order, one file, 90 days, error when missing, full SHA)."""
    body = text()
    assert body.index("gh issue edit") < body.index("upload-artifact")
    step = upload_step()
    uses = re.search(r"uses:\s*(\S+)@([0-9a-f]{40})\s+# (v\d+\.\d+\.\d+)\s*$", step, re.M)
    assert uses and uses.group(1) == "actions/upload-artifact", step
    assert with_value(step, "retention-days") == "90"
    assert with_value(step, "if-no-files-found") == "error"
    assert with_value(step, "archive") in (None, "true")
    path = with_value(step, "path") or ""
    assert path.endswith("/facts.json") and not re.search(r"[*?\[\]]", path)


def test_ac4_an_empty_facts_file_fails_the_run_before_anything_is_written(tmp_path):
    """REQ-026 AC4: SPEC-0019 rule 4 (an empty file never reaches an issue or an upload)."""
    proc, calls, out = run_body(tmp_path, facts_text="")
    assert proc.returncode != 0
    assert calls == [] and out == ""
    assert "nothing written" in proc.stdout + proc.stderr


def test_ac4_a_failure_after_the_issue_leaves_the_issue_as_written():
    """REQ-026 AC4: SPEC-0019 rule 4 (no step closes, deletes or rolls back an issue)."""
    code = "\n".join(ln for ln in text().splitlines() if not ln.lstrip().startswith("#"))
    for forbidden in (
        "issue close",
        "issue delete",
        "issue comment",
        "gh api",
        "continue-on-error",
    ):
        assert forbidden not in code, forbidden
    assert (
        re.search(r"(?m)^        if:", upload_step()) is None
    )  # it runs once the issue is written


def test_ac5_a_rerun_replaces_the_artifact_of_the_same_name_and_nothing_else_is_deleted():
    """REQ-026 AC5: SPEC-0019 rule 5 (Q-S0019-1: the upload sets the overwrite option)."""
    assert with_value(upload_step(), "overwrite") == "true"
    code = "\n".join(ln for ln in text().splitlines() if not ln.lstrip().startswith("#"))
    for forbidden in ("delete-artifact", "artifacts/", "gh run delete", "gh api"):
        assert forbidden not in code, forbidden


def test_ac6_the_permissions_and_the_writes_are_those_of_before():
    """REQ-026 AC6: SPEC-0019 rule 7 (no new permission; no commit, no push, the same gh verbs)."""
    block = re.search(r"(?m)^permissions:\s*\n((?:[ \t]+.*\n)+)", text()).group(1)
    assert sorted(ln.strip() for ln in block.splitlines()) == [
        "actions: read",
        "checks: read",
        "contents: read",
        "issues: write",
        "pull-requests: read",
    ]
    code = "\n".join(ln for ln in text().splitlines() if not ln.lstrip().startswith("#"))
    assert "git push" not in code and "git commit" not in code
    verbs = set(re.findall(r"\bgh ((?:issue|label|pr|release|gist|api) \w+)", code))
    assert verbs <= ALLOWED_GH, verbs


def test_ac6_ac7_the_file_is_published_nowhere_but_as_a_workflow_artifact():
    """REQ-026 AC6, AC7: SPEC-0019 rules 6 and 7 (no release, page, gist, link or other upload)."""
    uses = re.findall(r"(?m)^\s*-?\s*uses:\s*(\S+)@", text())
    assert sorted(uses) == ["actions/checkout", "actions/upload-artifact"]
    code = "\n".join(ln for ln in text().splitlines() if not ln.lstrip().startswith("#"))
    for forbidden in ("gh release", "gh gist", "pages", "curl", "wget", "aws ", "gsutil", "scp "):
        assert forbidden not in code, forbidden


def test_ac7_the_security_guide_says_who_can_read_the_artifact():
    """REQ-026 AC7: SPEC-0019 rules 6 and 9 (a line in the guide's account of what is written)."""
    row = next(
        ln
        for ln in SECURITY.read_text(encoding="utf-8").splitlines()
        if "`product-report.yml`" in ln
    )
    assert "agk-facts-<week>" in row and "workflow artifact" in row
    assert "90 days" in row and "read the repository" in row


def test_ac8_the_metrics_workflow_and_the_issue_commands_are_unchanged():
    """REQ-026 AC8: SPEC-0019 rule 8 (metrics uploads nothing; the same two issue commands)."""
    metrics = (ROOT / ".github" / "workflows" / "metrics.yml").read_text(encoding="utf-8")
    assert "upload-artifact" not in metrics
    assert (
        'gh issue create --title "$title" --label agk-product-report --body-file "$report"'
        in text()
    )
    assert 'gh issue edit "${action#update }" --title "$title" --body-file "$report"' in text()
    assert FIXTURE.is_file()
