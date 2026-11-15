"""Tests of .claude/hooks/steward_guard.py (SPEC-0059 rule 11, brief #1320, ADR-0557; REQ-066 AC5).

The guard denies the steward's reserved first lines, an owner answer without the owner's quote, a
merge, a push to the default branch, a force push, a tag, a workflow, ruleset, required check or
secret change, a filing above `[steward] auto_file` with no owner line and any other label write;
each denial names the rule and never the value. No test uses the network; data is invented.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "steward_guard.py"
RULE = "SPEC-0059 rule 11"
POST = "gh api --method POST repos/o/r/issues/9/comments"
QUOTE = 'Owner said (2026-11-15T10:20Z): "Ship it on Friday."'


def project(tmp_path: Path, toml: str = 'default_branch = "main"\n') -> Path:
    (tmp_path / "agk.toml").write_text(toml, encoding="utf-8")
    return tmp_path


def run_hook(root: Path, tool: str, tool_input: dict) -> dict | None:
    payload = {"tool_name": tool, "tool_input": tool_input, "cwd": str(root)}
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(root)},
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["hookSpecificOutput"] if proc.stdout.strip() else None


def bash(root: Path, command: str) -> dict | None:
    return run_hook(root, "Bash", {"command": command})


def body_file(root: Path, text: str) -> str:
    path = root / "body.md"
    path.write_text(text, encoding="utf-8")
    return f"{POST} -F body=@{path}"


@pytest.mark.parametrize("first", ["Approve:", "Confirmed:", "Verdict:", "Final:", "Correction:"])
def test_req066_each_reserved_first_line_is_denied(tmp_path, first):
    """REQ-066 AC5: rule 11, a comment whose first line starts a reserved word is denied."""
    root = project(tmp_path)
    for command in (
        f"{POST} -f body='{first} cleared abc1234'",
        body_file(root, f"{first} cleared abc1234\n\nWho: AGK steward\n"),
        f"gh pr comment 9 --body '{first} x'",
    ):
        found = bash(root, command)
        assert found is not None and found["permissionDecision"] == "deny", command
        assert RULE in found["permissionDecisionReason"]
        assert "abc1234" not in found["permissionDecisionReason"]


def test_req066_an_owner_answer_needs_the_quote_line(tmp_path):
    """REQ-066 AC5: rule 11, `Maintainer answer:` with no or a malformed `Owner said` line."""
    root = project(tmp_path)
    for second in ("", "The owner agreed.", 'Owner said (yesterday): "Ship it."', "Owner said: x"):
        text = f"Maintainer answer: Q-1-1 Friday\n{second}\nWho: ProductOwner\n"
        assert bash(root, body_file(root, text))["permissionDecision"] == "deny", second
    good = f"Maintainer answer: Q-1-1 Friday\n{QUOTE}\nWho: ProductOwner\n"
    assert bash(root, body_file(root, good)) is None


@pytest.mark.parametrize(
    "command",
    [
        "gh pr merge 9 --squash",
        "gh pr merge 9 --auto",
        "gh api --method PUT repos/o/r/pulls/9/merge",
        "python3 scripts/agk/merge_cleared.py --pr 9",
        "git merge origin/claude/x",
        "git push origin main",
        "git push origin HEAD:main",
        "git push origin HEAD:refs/heads/main",
        "git push",
        "git push --force origin claude/x",
        "git push origin +claude/x",
        "git push --force-with-lease origin claude/x",
        "git tag v1.0.0",
        "git push origin --tags",
        "gh release create v1.0.0",
        "gh api --method POST repos/o/r/git/refs -f ref=refs/tags/v1",
        "gh api --method PUT repos/o/r/contents/.github/workflows/ci.yml -f message=x",
        "cp notes.txt .github/workflows/ci.yml",
        "gh workflow run ci.yml",
        "gh api --method POST repos/o/r/rulesets -f name=x",
        "gh api -X PUT repos/o/r/branches/main/protection/required_status_checks -f strict=1",
        "gh secret set TOKEN --body x",
        "gh api --method PUT repos/o/r/actions/secrets/TOKEN -f encrypted_value=x",
        "gh api graphql -f query='mutation { x }'",
        "gh label create agk:fast",
        "gh pr edit 9 --add-label agk:ready",
        "gh pr edit 9 --add-label agk-steward",
        "gh issue edit 9 --remove-label agk-brief",
        "gh api --method POST repos/o/r/issues/9/labels -f 'labels[]=agk:ready'",
        "gh api --method DELETE repos/o/r/issues/9/labels/agk-brief",
        "gh api repos/o/r/issues/9/comments -F body=@-",
        'gh api repos/o/r/issues/9/comments -f body="$(cat x)"',
    ],
)
def test_req066_the_listed_actions_are_denied_naming_the_rule(tmp_path, command):
    """REQ-066 AC5: rule 11, merge, push, tag, workflow, ruleset, secret, label, unreadable body."""
    found = bash(project(tmp_path), command)
    assert found is not None and found["permissionDecision"] == "deny", command
    reason = found["permissionDecisionReason"]
    assert RULE in reason or "CLAUDE.md item 10" in reason
    assert "TOKEN" not in reason and "v1.0.0" not in reason and "agk:ready" not in reason


def test_req066_a_workflow_file_edit_is_denied(tmp_path):
    """REQ-066 AC5: rule 11, an Edit or Write of a file under `.github/` (path class)."""
    root = project(tmp_path)
    for tool in ("Edit", "Write", "MultiEdit"):
        found = run_hook(root, tool, {"file_path": str(root / ".github" / "workflows" / "ci.yml")})
        assert found["permissionDecision"] == "deny"
        assert "`.github/`" in found["permissionDecisionReason"]
    assert run_hook(root, "Write", {"file_path": str(root / "docs" / "notes.md")}) is None


def filing(root: Path, priority: int, owner: bool = False) -> str:
    text = f"Sentence: a fix.\nPriority: {priority}\n"
    if owner:
        text += f"{QUOTE}\n"
    path = root / "brief.md"
    path.write_text(text, encoding="utf-8")
    return f"gh issue create --title 'A fix' --body-file {path} --label agk-steward"


def test_req066_a_filing_above_auto_file_needs_the_owner_line(tmp_path):
    """REQ-066 AC5: rules 11 and 12, `Priority: 0` passes at the default, `1` needs the owner."""
    root = project(tmp_path)
    assert bash(root, filing(root, 0)) is None
    found = bash(root, filing(root, 1))
    assert found["permissionDecision"] == "deny"
    assert "steward.auto_file" in found["permissionDecisionReason"]
    assert bash(root, filing(root, 1, owner=True)) is None
    raised = project(tmp_path, 'default_branch = "main"\n[steward]\nauto_file = 2\n')
    assert bash(raised, filing(raised, 2)) is None
    none = project(tmp_path, 'default_branch = "main"\n[steward]\nauto_file = false\n')
    assert bash(none, filing(none, 0))["permissionDecision"] == "deny"
    bad = project(tmp_path, 'default_branch = "main"\n[steward]\nauto_file = 9\n')
    found = bash(bad, filing(bad, 0))
    assert (
        found["permissionDecision"] == "deny"
        and "setting: steward.auto_file" in found["permissionDecisionReason"]
    )


@pytest.mark.parametrize(
    "command",
    [
        "gh api repos/o/r/issues/9/comments",
        "gh api repos/o/r/pulls/9",
        "gh pr edit 9 --add-label agk:parked",
        "gh api --method POST repos/o/r/issues/9/labels -f 'labels[]=agk:parked'",
        "gh issue create --title 'AGK steward memory' --body 'Notes.' --label agk-steward",
        "git push origin claude/steward-notes",
        "git fetch origin main",
        "git tag --list",
        "python3 scripts/agk/steward.py start --session s1",
        f"{POST} -f body='Answer: Q-1-1 Friday (evidence: docs/sources/a.md:3; rule: 3)'",
    ],
)
def test_req066_an_answer_parked_label_and_reads_are_allowed(tmp_path, command):
    """REQ-066 AC5: rule 11 allows an `Answer:`, the `agk:parked` label and every read."""
    assert bash(project(tmp_path), command) is None, command


def test_req066_the_steward_setting_is_read_and_a_bad_value_refused(tmp_path):
    """REQ-066 AC5: rule 12, `auto_file` is `false` or 0 to 3, 0 when unset; else refused."""
    sys.path.insert(0, str(HOOK.parents[2] / "scripts" / "agk"))
    from config import StewardSettingError, steward_settings

    assert steward_settings(project(tmp_path, "")) == {"auto_file": 0}
    for value, want in (("false", False), ("3", 3), ("0", 0)):
        root = project(tmp_path, f"[steward]\nauto_file = {value}\n")
        assert steward_settings(root) == {"auto_file": want}
    for table in ("auto_file = 4", "auto_file = true", "auto_file = '1'", "other = 1", "x = -1"):
        root = project(tmp_path, f"[steward]\n{table}\n")
        with pytest.raises(StewardSettingError) as caught:
            steward_settings(root)
        assert "setting: steward." in str(caught.value)
        assert "'1'" not in str(caught.value) and "-1" not in str(caught.value)


@pytest.mark.parametrize(
    "command",
    [
        "env gh pr merge 5",
        "env -u HOME A=1 gh pr merge 5",
        "timeout 60 gh pr merge 5",
        "command git push --force origin x",
        "nohup nice -n 5 git push origin main",
        "sudo -u ci gh pr merge 5",
        'python3 -c "import os; os.system(\\"gh pr merge 5\\")"',
        "node -e \"require('child_process').execSync('git push origin main')\"",
        "echo 5 | xargs gh pr merge",
        "find . -name x -exec gh pr merge 5 ;",
    ],
)
def test_req066_a_wrapper_or_inline_code_does_not_pass_the_guard(tmp_path, command):
    """REQ-066 AC5: rule 11, the command behind a wrapper, `xargs` or `find -exec` is read, and an
    interpreter's inline code that runs `gh` or `git` is denied (the fix list on f34f420)."""
    found = bash(project(tmp_path), command)
    assert found is not None and found["permissionDecision"] == "deny", command
    assert RULE in found["permissionDecisionReason"]


def test_req066_a_wrapper_of_a_read_is_still_allowed(tmp_path):
    """REQ-066 AC5: rule 11, a wrapper does not deny what it runs when that is allowed."""
    root = project(tmp_path)
    for command in ("timeout 60 gh api repos/o/r/pulls/9", "env A=1 git fetch origin main"):
        assert bash(root, command) is None, command
