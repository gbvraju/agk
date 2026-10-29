"""Tests of a `Depends-on` line that names a brief issue (REQ-039, brief #282, ADR-0166).

`check_pr_mode.py` rule 5 accepts `#n` when it is a merged pull request or an issue closed as
completed. An open issue, an issue closed as not planned (or for any other reason) and an unmerged
pull request still fail, each with its own message. The workflow reads the issues endpoint, which
answers for a pull request and for an issue alike. Files only: no network, no model.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "governance.yml"
RULES = ROOT / "config" / "session-rules.md"


def flow(repo) -> None:
    repo.write("agk.toml", 'version = "0.0.1"\npr_mode = "flow"\n')


def issue(n: int, state: str, reason: str | None = None) -> dict:
    return {
        "number": n,
        "pull_request": False,
        "merged": False,
        "state": state,
        "state_reason": reason,
    }


def pull(n: int, merged: bool) -> dict:
    state = "closed" if merged else "open"
    return {
        "number": n,
        "pull_request": True,
        "merged": merged,
        "state": state,
        "state_reason": None,
    }


def check(repo, tmp_path: Path, numbers: list[int], states: list[dict]):
    body = tmp_path / "body.md"
    body.write_text(
        "Advances: REQ-039\n" + "".join(f"Depends-on: #{n}\n" for n in numbers), encoding="utf-8"
    )
    lines = tmp_path / "states.json"
    lines.write_text("".join(json.dumps(s) + "\n" for s in states), encoding="utf-8")
    return repo.run("check_pr_mode.py", "--body", str(body), "--states", str(lines))


def test_req039_the_pilot_case_a_brief_closed_as_completed_passes(repo, tmp_path):
    """REQ-039: brief #282 answer 1 (the pilot: brief #29, closed by its merged pull request)."""
    flow(repo)
    proc = check(repo, tmp_path, [29], [issue(29, "closed", "completed")])
    assert (proc.returncode, proc.stdout) == (0, "skipped (no open pull requests file)\n"), (
        proc.stdout
    )


def test_req039_a_merged_pull_request_still_passes_in_the_new_shape(repo, tmp_path):
    """REQ-039: brief #282 answer 1 (a merged pull request, as today)."""
    flow(repo)
    proc = check(repo, tmp_path, [49, 29], [pull(49, True), issue(29, "closed", "completed")])
    assert proc.returncode == 0, proc.stdout


def test_req039_an_open_brief_fails_naming_an_open_issue(repo, tmp_path):
    """REQ-039: brief #282 answer 1."""
    flow(repo)
    proc = check(repo, tmp_path, [29], [issue(29, "open")])
    assert proc.returncode == 1, proc.stdout
    assert proc.stdout == "FAIL pr-mode: rule 5: #29 is an open issue\n", proc.stdout


def test_req039_a_brief_closed_as_not_planned_fails_naming_it(repo, tmp_path):
    """REQ-039: brief #282 answer 1."""
    flow(repo)
    proc = check(repo, tmp_path, [29], [issue(29, "closed", "not_planned")])
    assert proc.stdout == "FAIL pr-mode: rule 5: #29 is an issue closed as not planned\n", (
        proc.stdout
    )


def test_req039_a_brief_closed_for_another_reason_or_none_fails(repo, tmp_path):
    """REQ-039: brief #282 answer 1 (only `completed` counts: a duplicate or no reason fails)."""
    flow(repo)
    for reason in ("duplicate", None):
        proc = check(repo, tmp_path, [29], [issue(29, "closed", reason)])
        assert proc.stdout == "FAIL pr-mode: rule 5: #29 is an issue not closed as completed\n", (
            proc.stdout
        )


def test_req039_an_unmerged_pull_request_fails_naming_a_pull_request(repo, tmp_path):
    """REQ-039: brief #282 answer 1 (open or closed without a merge)."""
    flow(repo)
    for state in ("open", "closed"):
        record = {**pull(49, False), "state": state}
        proc = check(repo, tmp_path, [49], [record])
        assert proc.stdout == "FAIL pr-mode: rule 5: #49 is a pull request that is not merged\n", (
            proc.stdout
        )


def test_req039_each_failing_case_gives_its_own_message_in_one_run(repo, tmp_path):
    """REQ-039: brief #282 answer 3 (one message a number, in the order of the body)."""
    flow(repo)
    states = [
        issue(1, "open"),
        issue(2, "closed", "not_planned"),
        pull(3, False),
        issue(4, "closed", "completed"),
    ]
    proc = check(repo, tmp_path, [1, 2, 3, 4, 5], states)
    assert proc.returncode == 1
    assert proc.stdout == (
        "FAIL pr-mode: rule 5: #1 is an open issue; rule 5: #2 is an issue closed as not planned; "
        "rule 5: #3 is a pull request that is not merged; rule 5: #5 is not merged\n"
    ), proc.stdout


def test_req039_a_record_of_unknown_kind_is_read_as_before(repo, tmp_path):
    """REQ-039: brief #282 (a record without `pull_request`, the fallback, is not merged)."""
    flow(repo)
    proc = check(repo, tmp_path, [29], [{"number": 29, "merged": False}])
    assert proc.stdout == "FAIL pr-mode: rule 5: #29 is not merged\n", proc.stdout
    proc = check(
        repo,
        tmp_path,
        [29],
        [{"number": 29, "merged": False, "state": "closed", "state_reason": "completed"}],
    )
    assert proc.returncode == 1, "an issue is told by `pull_request: false`, never guessed"


def test_req039_strict_mode_still_fails_any_depends_on_line(repo, tmp_path):
    """REQ-039: brief #282 (rule 6 is unchanged: a closed brief does not open strict mode)."""
    repo.write("agk.toml", 'version = "0.0.1"\n')
    proc = check(repo, tmp_path, [29], [issue(29, "closed", "completed")])
    assert proc.returncode == 1 and proc.stdout.startswith("FAIL pr-mode: rule 6"), proc.stdout


def test_req039_the_workflow_reads_the_issues_endpoint_for_each_named_number():
    """REQ-039: brief #282 answer 1 (one GET a number, answered for a pull request or an issue)."""
    text = WORKFLOW.read_text(encoding="utf-8")
    step = text.split("      - name: PR states and open pull requests\n", 1)[1].split(
        "      - name:", 1
    )[0]
    fetch = [
        c
        for c in re.findall(r"gh api [^\n]*", step)
        if "--list-depends" not in c and "/issues/$n" in c
    ]
    assert len(fetch) == 1, step
    call = fetch[0]
    assert '"repos/${{ github.repository }}/issues/$n"' in call and "--method GET" in call
    for field in (
        "number: .number",
        "pull_request: (.pull_request != null)",
        "merged: (.pull_request.merged_at != null)",
        "state: .state",
        "state_reason: .state_reason",
    ):
        assert field in call, field
    assert "/pulls/$n" not in step


def test_req039_the_session_rules_say_what_a_depends_on_line_names():
    """REQ-039: brief #282 answer 2 (what must merge first; a merged one needs no line)."""
    rule = next(ln for ln in RULES.read_text(encoding="utf-8").splitlines() if ln.startswith("3. "))
    assert "`Depends-on: #n`" in rule
    assert "names what must merge first" in rule
    assert "already on the default branch needs no `Depends-on` line" in rule
    assert "closed as completed" in rule
