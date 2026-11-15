"""The data guard judges substitution, here-documents and PowerShell lines (brief #1360, ADR-0572).

Answer 1: (a) a `$(...)`, `<(...)`, `>(...)` or backquote command is judged as a nested shell
within the depth of 3, the outer line with a placeholder word; (b) a here-document body is data,
searched for a denied name and never expanded as a glob, and the command before it is judged as
usual; (c) a PowerShell line is split at `;`, `|`, `&&` and `||`, with the backquote read as its
escape and line continuation. A form it still cannot judge denies, and the line adds `split it
into single commands`. The rules of what is denied do not change. Every name is invented; no
network, no gh.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK_FILE = ROOT / ".claude" / "hooks" / "data_guard.py"
HINT = "split it into single commands, or ask the person to run it and give you a cleaned copy"


@pytest.fixture
def hook(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("SHELL", raising=False)
    spec = importlib.util.spec_from_file_location("data_guard", HOOK_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def folder(tmp_path) -> Path:
    """A project holding a secret file and a raw log beside clean files."""
    for name in ("README.md", "src/a.py", ".env", "app.log"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x = 1\n", encoding="utf-8")
    return tmp_path


def judge(hook, folder: Path, command: str, tool: str = "Bash") -> str | None:
    return hook.judge({"tool_name": tool, "tool_input": {"command": command}, "cwd": str(folder)})


PLANTED = [
    "echo $(cat .env)", "git log --grep=$(cat app.log)", "diff <(cat .env) README.md",
    "tee >(cat > .env) < README.md", "echo `cat .env`", 'echo "$(head -1 .env)"',
    "cat .e$(echo nv)", "cat $(echo LmVudg== | base64 -d)",
    "git commit -F - <<'EOF'\nfix: read .env first\nEOF",
    "cat <<EOF\n$(cat .env)\nEOF", "cat <<-EOF\n\tsee app.log\n\tEOF",
    'git commit -m "$(cat <<\'EOF\'\nfix: the ~/.ssh/id_rsa path\nEOF\n)"',
    "pwsh -Command 'Get-Content `.env'", "echo $(date); grep -r foo .",
]


@pytest.mark.parametrize("command", PLANTED)
def test_answer1_a_planted_name_inside_each_form_is_still_denied(hook, folder, command):
    """REQ-050: brief #1360 answers 1a, 1b and 4 (inside a substitution, a here-document body)."""
    line = judge(hook, folder, command)
    assert line is not None and line.startswith("data guard: "), command
    assert ".env" not in line and "app.log" not in line  # the line names no path (rule 9)


CLEAN = [
    "echo $(date)", "git log -1 $(git merge-base HEAD origin/main)", "ls `pwd`",
    "diff <(git show HEAD:README.md) README.md", 'git tag -l "v$(cat VERSION)"',
    "git commit -F - <<'EOF'\nfix: the guard\n\n* one bullet\n- another\nEOF",
    'git commit -m "$(cat <<\'EOF\'\nfix: don\'t split it\n\nCo-Authored-By: A <a@example.com>\n'
    'EOF\n)"',
    "gh api repos/o/r/issues/1/comments -F body=@- <<EOF\nDone at $(date -u).\nEOF",
    "cat <<< 'one line'", "pwsh -Command 'Get-ChildItem src `\n -Name'",
]


@pytest.mark.parametrize("command", CLEAN)
def test_answer1_the_same_forms_with_clean_names_are_allowed(hook, folder, command):
    """REQ-050: brief #1360 answers 1a, 1b and 4 (a `*` bullet of a body is not a glob)."""
    assert judge(hook, folder, command) is None, command


def test_answer1_git_commit_with_a_here_document_message_is_allowed(hook, folder):
    """REQ-050: brief #1360 answer 4 (`git commit -F - <<'EOF'` with a clean message)."""
    assert judge(hook, folder, "git commit -F - <<'EOF'\ncheckpoint: tests\nEOF") is None


POWERSHELL_PLANTED = [
    "Get-ChildItem src; Get-Content `\n  .env", "Get-Content `.env",
    "Get-Content .env | Select -First 1",
    'Write-Output "$(Get-Content .env)"', "git status && Get-Content app.log",
    "Get-ChildItem -Recurse | Select-String foo", "Get-ChildItem `\n -Recurse | Select-String foo",
    "& cat .env", "bash -c 'cat .env'",
]


@pytest.mark.parametrize("command", POWERSHELL_PLANTED)
def test_answer1_powershell_lines_with_a_planted_name_are_denied(hook, folder, command):
    """REQ-050: brief #1360 answers 1c and 4 (after a backquote continuation, in `$(...)`)."""
    line = judge(hook, folder, command, "PowerShell")
    assert line is not None and line.startswith("data guard: "), command


POWERSHELL_CLEAN = [
    "Get-ChildItem -Path src `\n  -Name", "git log -1; git status", 'Write-Output "$(Get-Date)"',
    "git commit -m 'it''s done'", "Get-ChildItem src -Recurse | Select-String foo",
    "Write-Output \"a`tb\" | Out-Null", "git status || exit 1",
]


@pytest.mark.parametrize("command", POWERSHELL_CLEAN)
def test_answer1_powershell_lines_with_clean_names_are_allowed(hook, folder, command):
    """REQ-050: brief #1360 answer 1c (the backquote is PowerShell's escape and continuation)."""
    assert judge(hook, folder, command, "PowerShell") is None, command


def test_answer1_a_powershell_session_judges_a_bash_tool_line_by_both_readers(
    hook, folder, monkeypatch
):
    """REQ-050: brief #1360 answer 1c and the fix list on 609cea6: the Bash tool runs bash whatever
    `SHELL` says, so its line is judged as bash and, in a `pwsh` session, also as PowerShell."""
    monkeypatch.setenv("SHELL", "/usr/bin/pwsh")
    assert judge(hook, folder, "cat $'\\x2eenv'").startswith("data guard: secret-file")
    assert judge(hook, folder, "Get-Content `.env").startswith("data guard: ")
    line = judge(hook, folder, "Get-Content `.env", "PowerShell")
    assert line.startswith("data guard: secret-file")
    assert judge(hook, folder, "Get-ChildItem src | Select-Object -First 1") is None


ESCAPED = ['Get-Content "`u{2e}env"', "Get-Content `u{2E}env", 'Get-Content "app`u{2e}log"']


@pytest.mark.parametrize("command", ESCAPED)
def test_answer1_powershell_escapes_are_decoded_before_judging(hook, folder, command):
    """REQ-050: brief #1360 answer 1c and the fix list on 609cea6 (the `u{...} escape)."""
    line = judge(hook, folder, command, "PowerShell")
    assert line is not None and line.startswith("data guard: "), command


def test_answer1_a_bad_code_point_escape_denies_with_the_hint(hook, folder):
    """REQ-050: brief #1360 answer 1c (an escape it cannot decode is a form it cannot judge)."""
    for command in ('Get-Content "`u{zz}"', 'Get-Content "`u{110000}"'):
        line = judge(hook, folder, command, "PowerShell")
        assert line == f"data guard: cannot-judge (compound form): {HINT}", command


NESTED_TOO_DEEP = [
    "bash -c \"sh -c 'bash -c \\\"eval ls\\\"'\"", "echo $(echo $(echo $(echo $(ls))))",
]


@pytest.mark.parametrize("command", NESTED_TOO_DEEP)
def test_answer1_nesting_past_depth_3_denies_with_the_hint(hook, folder, command):
    """REQ-050: brief #1360 answer 4 (deeper than 3 still denies, now with what to do)."""
    assert judge(hook, folder, command) == f"data guard: cannot-judge (nested shell): {HINT}"


UNJUDGEABLE = ["cat <<EOF\nnever closed", "echo $(ls", "echo `ls \\` x`", "Get-Content `"]


@pytest.mark.parametrize("command", UNJUDGEABLE)
def test_answer1_a_form_it_cannot_take_apart_denies_with_the_hint(hook, folder, command):
    """REQ-050: brief #1360 answer 1 (a form it still cannot judge denies, adding the hint)."""
    tool = "PowerShell" if command.startswith("Get-") else "Bash"
    assert judge(hook, folder, command, tool) == f"data guard: cannot-judge (compound form): {HINT}"


def test_answer1_other_denials_keep_their_line(hook, folder):
    """REQ-050: brief #1360 answer 1 (the hint is added only where splitting helps)."""
    line = judge(hook, folder, "cat $(echo LmVudg== | base64 -d)")
    alternative = "ask the person to run it and give you a cleaned copy"
    assert line == f"data guard: cannot-judge (decoded name): {alternative}"
