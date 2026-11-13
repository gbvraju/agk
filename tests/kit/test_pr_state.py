"""A surviving governance run reads the draft state at run time (brief #1174, ADR-0499).

A builder pushes and marks its pull request ready within a second: the `synchronize` run carries
`draft: true`, the `ready_for_review` run `draft: false`, and the later one cancels the other. The
job reads the pull request with one GET when it runs and `pr_state.py` decides from that read, so a
surviving run of a pull request that is ready by then runs in full. A read that fails counts as not
a draft (fail closed: the heavy steps run). Stubbed reads are files in `tmp_path` with invented
data; the workflow is read as text; no network.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "agk" / "pr_state.py"
GOVERNANCE = ROOT / ".github" / "workflows" / "governance.yml"

sys.path.insert(0, str(ROOT / "scripts" / "agk"))


def pull(draft: object) -> str:
    """An invented `GET repos/{owner}/{repo}/pulls/<n>` answer."""
    return json.dumps(
        {"number": 7, "html_url": "https://example.com/o/r/pull/7", "state": "open", "draft": draft}
    )


def run(tmp_path: Path, text: str | None, *extra: str) -> subprocess.CompletedProcess:
    args = [sys.executable, str(SCRIPT)]
    if text is not None:
        path = tmp_path / "pull.json"
        path.write_text(text, encoding="utf-8")
        args += ["--pull", str(path)]
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [*args, *extra], capture_output=True, text=True, check=False
    )


def decide(tmp_path: Path, text: str | None, *extra: str) -> str:
    out = run(tmp_path, text, *extra)
    assert out.returncode == 0, out.stdout + out.stderr
    return out.stdout.strip()


# --- (a) to (c): the decision ---------------------------------------------------------------------


def test_a_payload_draft_and_read_ready_runs_the_heavy_steps(tmp_path):
    """REQ-051: brief #1174 answer 3 (a): payload draft, read ready: run in full."""
    assert decide(tmp_path, pull(False), "--event-draft", "true") == "false"


def test_b_both_draft_skips_as_today(tmp_path):
    """REQ-051: brief #1174 answer 3 (b): both say draft: the heavy steps are skipped as today."""
    assert decide(tmp_path, pull(True), "--event-draft", "true") == "true"
    assert decide(tmp_path, pull(True)) == "true"


@pytest.mark.parametrize(
    "text",
    ["", "not json", "[]", json.dumps({"message": "Not Found"}), pull("true"), pull(None)],
    ids=["empty", "not-json", "not-an-object", "error-answer", "string-draft", "null-draft"],
)
def test_c_a_failed_read_runs_the_heavy_steps(tmp_path, text):
    """REQ-051: brief #1174 answer 2 and 3 (c): a read that fails counts as not a draft."""
    assert decide(tmp_path, text, "--event-draft", "true") == "false"


def test_c_a_missing_file_runs_the_heavy_steps(tmp_path):
    """REQ-051: brief #1174 answer 3 (c): the GET wrote nothing at all: not a draft."""
    missing = tmp_path / "absent.json"
    assert decide(tmp_path, None, "--pull", str(missing), "--event-draft", "true") == "false"


def test_a_ready_payload_and_a_draft_read_still_runs_in_full(tmp_path):
    """REQ-051: brief #1174 answer 2: a draft only when nothing says ready."""
    assert decide(tmp_path, pull(True), "--event-draft", "false") == "false"


def test_the_function_answers_as_the_command(tmp_path):
    """REQ-051: brief #1174 answer 2: a kit function a test can call, returning true or false."""
    import pr_state

    assert pr_state.is_draft(pull(True), "true") is True
    assert pr_state.is_draft(pull(False), "true") is False
    assert pr_state.is_draft("", "true") is False
    assert pr_state.is_draft(pull(True), None) is True


def test_usage_errors_exit_2(tmp_path):
    """REQ-051: brief #1174 answer 2: --pull is required; --event-draft is true, false or empty."""
    assert run(tmp_path, None).returncode == 2
    assert run(tmp_path, pull(True), "--event-draft", "maybe").returncode == 2
    assert decide(tmp_path, pull(True), "--event-draft", "") == "true"


def test_the_script_calls_no_network():
    """REQ-051: brief #1174 answer 3: the workflow does the GET; the script reads a file only."""
    text = SCRIPT.read_text(encoding="utf-8")
    names = set(re.findall(r"^\s*(?:import|from)\s+(\w+)", text, re.M))
    assert not names & {"socket", "urllib", "http", "requests", "ssl", "subprocess"}


# --- (d): the workflow sets PR_DRAFT from the read ------------------------------------------------


def steps() -> list[str]:
    """The text of each step of the governance job, in order."""
    text = GOVERNANCE.read_text(encoding="utf-8")
    return re.split(r"\n      - (?=name:|uses:)", text)[1:]


def test_d_the_workflow_sets_pr_draft_from_the_read():
    """REQ-051: brief #1174 answer 1 and 3 (d): every PR_DRAFT comes from the run-time read."""
    text = GOVERNANCE.read_text(encoding="utf-8")
    values = re.findall(r"^\s*PR_DRAFT:\s*(.+?)\s*$", text, re.M)
    assert values, "governance sets no PR_DRAFT"
    assert all(v == "${{ steps.draft.outputs.draft }}" for v in values), values


def test_d_one_get_of_the_pull_request_feeds_pr_state_before_the_draft_is_used():
    """REQ-051: brief #1174 answer 1: one GET, read by pr_state.py, first."""
    all_steps = steps()
    draft = [i for i, s in enumerate(all_steps) if re.search(r"^\s*id: draft\s*$", s, re.M)]
    assert len(draft) == 1, "one step with id `draft`"
    step = all_steps[draft[0]]
    get = r'gh api --method GET "repos/\$\{\{ github\.repository \}\}/pulls/\$PR_NUMBER"'
    assert re.search(get, step)
    assert "scripts/agk/pr_state.py" in step
    assert "EVENT_DRAFT: ${{ github.event.pull_request.draft }}" in step
    assert "github.event_name == 'pull_request'" in step
    first_use = min(i for i, s in enumerate(all_steps) if "PR_DRAFT:" in s)
    assert draft[0] < first_use
