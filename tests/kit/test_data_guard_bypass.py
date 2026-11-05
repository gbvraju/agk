"""Adversarial tests of the data guard's layer 1 on commands (SPEC-0042 rules 4 to 6, brief #589).

The brief's Answer 2: path tricks, shell indirection, encoded names and an `allow_paths` entry
naming a built-in secret file must each be denied, with a line naming the rule, never the value.
Every value is invented; no network, no gh.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK_FILE = ROOT / ".claude" / "hooks" / "data_guard.py"
LINE = re.compile(r"data guard: (secret-file|raw-log|cannot-judge) \([a-z ]+\): \S.*")
ALTERNATIVES = {
    "ask the person for the one value you need, or for a cleaned copy",
    "read it through `agk logs <file>` (python3 scripts/agk/guard_logs.py)",
    "ask the person to run it and give you a cleaned copy",
}


@pytest.fixture
def hook(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home" / ".ssh").mkdir(parents=True)
    spec = importlib.util.spec_from_file_location("data_guard", HOOK_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bash(hook, folder: Path, command: str, tool: str = "Bash") -> str | None:
    payload = {"tool_name": tool, "tool_input": {"command": command}, "cwd": str(folder)}
    return hook.judge(payload)


def holding(tmp_path: Path, *names: str) -> Path:
    for name in ("README.md", "src/a.py", *names):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x = 1\n", encoding="utf-8")
    return tmp_path


DENIED = [
    "cat .env", "cat '.env'", 'cat ".e"nv', "cat .e\\nv", "FOO=1 cat .env", "env -i cat .env",
    "sudo cat .env", "sudo -u root cat .env", "timeout 5 cat .env", "nice -n 5 cat .env",
    "echo x | xargs -I{} cat .env", "true && cat .env", "false || cat .env", "ls; cat app.log",
    "cat app.log | head", "(cat .env)", "{ cat .env; }", "bash -c 'cat .env'", "sh -c 'cat .env'",
    "bash -lc 'cat .env'", "eval cat .env", "eval 'cat .env'",
    "bash -c \"sh -c 'eval cat .env'\"", "bash -c \"sh -c 'bash -c \\\"eval cat .env\\\"'\"",
    "python -c \"open('.env').read()\"", "python3 -c 'print(open(\".env\").read())'",
    "node -e \"require('fs').readFileSync('.env')\"", "perl -e 'open(F, \".env\")'",
    "cat .en*", "cat *.log", "cat .[e]nv", "cat .?nv", "cat .{e,x}nv", "head < .env",
    "head 0<.env", "cat > .env", "echo A=1 >> .env", "echo $(cat .env)", "echo `cat .env`",
    "cat .ENV", "CAT .env", "head APP.LOG", "cat ./.env", "cat sub/../.env", "cat ././.env",
    "cat ~/.ssh/id_rsa", "cat ~/.aws/credentials", "base64 .env", "xxd .env", "head -c 64 .env",
    "od -c .env", "strings .env", "cp .env /tmp/x",
    "awk '{ while ((getline l < \".env\") > 0) print l }'",
    "sed -n '1r .env' /dev/null", "awk '{ print }' app.log", "jq . secrets.json",
    "git show HEAD:.env", "git cat-file -p HEAD:.env", "git show main:logs/a.txt",
    "cat $'\\x2eenv'", "cat $'\\056env'", "cat $(echo LmVudg== | base64 -d)",
    "echo LmVudg== | base64 -d | xargs cat", "echo LmVudg== | base64 --decode | sh",
    "printf '\\x2eenv' | xargs cat", "cat <(cat .env)", "cat <<EOF\n$(cat .env)\nEOF",
    "journalctl -u web", "dmesg", "sudo dmesg", "kubectl logs pod-1", "kubectl -n x logs pod-1",
    "docker logs web", "docker compose logs", "docker-compose logs web", "podman logs web",
    "heroku logs --tail", "aws logs tail g", "gcloud logging read x", "az monitor log-analytics",
    "ln -s .env notes.txt", "source .env", ". .env", "cat logs/today.txt",
]


@pytest.mark.parametrize("command", DENIED)
def test_ac2_each_bypass_form_is_denied_with_the_line_of_rule_9(hook, tmp_path, command):
    """REQ-049 AC2: rules 4 to 6 (quotes, prefixes, wrappers, chains, pipes, subshells, nested
    shells, inline interpreters, globs, redirections, substitutions, case, encoded names)."""
    folder = holding(tmp_path, ".env", "app.log", "secrets.json", "home/.ssh/id_rsa")
    line = bash(hook, folder, command)
    assert line is not None and LINE.fullmatch(line), command
    assert line.split(": ", 2)[2] in ALTERNATIVES  # a fixed text: never a path or a value


def test_ac2_a_link_to_a_secret_file_is_denied_by_its_resolved_path(hook, tmp_path):
    """REQ-049 AC2: rule 3 (symlinks)."""
    folder = holding(tmp_path, ".env")
    (folder / "notes.txt").symlink_to(folder / ".env")
    assert bash(hook, folder, "cat notes.txt").startswith("data guard: secret-file (env file)")
    (folder / "d").symlink_to(folder, target_is_directory=True)
    assert bash(hook, folder, "head d/.ENV").startswith("data guard: secret-file (env file)")


def test_ac2_powershell_commands_are_judged_alike(hook, tmp_path):
    """REQ-049 AC2: rules 2 and 4 (the PowerShell tool beside Bash)."""
    folder = holding(tmp_path, ".env")
    line = bash(hook, folder, "Get-Content .env", "PowerShell")
    assert line.startswith("data guard: secret-file")
    assert bash(hook, folder, "Get-ChildItem src", "PowerShell") is None


def test_ac2_nesting_past_depth_3_is_denied_even_without_a_name(hook, tmp_path):
    """REQ-049 AC2: rule 4 (judged again to a depth of 3, denied past it)."""
    folder = holding(tmp_path)
    four = "bash -c \"sh -c 'bash -c \\\"eval ls\\\"'\""
    assert bash(hook, folder, four).startswith("data guard: cannot-judge (nested shell)")
    assert bash(hook, folder, "bash -c \"sh -c 'eval ls'\"") is None


SEARCHES = [
    "grep -r foo .", "grep -R foo", "grep -rn foo src .", "grep --recursive foo",
    "grep -d recurse foo .", "egrep -r foo", "rg foo", "ag foo", "ack foo", "git grep foo",
    "find . -type f -exec cat {} +", "find . -name '*.py' -execdir head {} \\;",
    "find . | xargs cat",
    "find | xargs grep foo",
]


@pytest.mark.parametrize("command", SEARCHES)
@pytest.mark.parametrize("held", [".env", "app.log", "config/logs/x.txt", "deep/id_ed25519"])
def test_ac2_a_recursive_search_over_a_folder_holding_a_denied_file_is_denied(
    hook, tmp_path, command, held
):
    """REQ-049 AC2: rules 4 and 5 (the folder check; Q-S0042-11)."""
    folder = holding(tmp_path, held)
    line = bash(hook, folder, command)
    assert line is not None and "(folder search)" in line, command


@pytest.mark.parametrize("command", SEARCHES)
def test_ac2_the_same_searches_over_a_clean_folder_are_allowed(hook, tmp_path, command):
    """REQ-049 AC2: rule 4 (the folder check denies only what it finds)."""
    assert bash(hook, holding(tmp_path, ".env.example"), command) is None


ALLOWED = [
    "cat .envrc", "ls catalog.json", "git log -1", "git status && make lint", "ls docs | wc -l",
    "cat README.md 2>&1 | head", "env FOO=1 make test", "python3 -m pytest -q tests",
    "grep foo src/a.py", "echo done", "cat .env.example", "git diff --stat origin/main",
    "printf '%s\\n' hello", "make governance && git commit -m 'checkpoint: tests'",
]


@pytest.mark.parametrize("command", ALLOWED)
def test_ac2_ordinary_commands_are_allowed(hook, tmp_path, command):
    """REQ-049 AC2: rule 4 (a deny-list on an ordinary builder's commands)."""
    folder = holding(tmp_path, ".env", "app.log", ".env.example")
    assert bash(hook, folder, command) is None, command


def test_ac2_the_project_log_reader_is_the_one_allowed_reader(hook, tmp_path):
    """REQ-049 AC2: rule 6 (`python3 scripts/agk/guard_logs.py <file>`, piped onward)."""
    reader = "scripts/agk/guard_logs.py"
    folder = holding(tmp_path, "app.log", reader, "other/guard_logs.py", ".env")
    assert bash(hook, folder, f"python3 {reader} app.log") is None
    assert bash(hook, folder, f"python3 {reader} --max-lines 9 app.log | head") is None
    line = bash(hook, folder, "python3 other/guard_logs.py app.log")
    assert line.startswith("data guard: raw-log")
    assert bash(hook, folder, "python3 scripts/agk/guard_logs.py .env").startswith(
        "data guard: secret-file"
    )
    assert bash(hook, folder, "python3 scripts/agk/guard_logs.py app.log; cat app.log").startswith(
        "data guard: raw-log"
    )


def test_ac1_an_allow_paths_entry_naming_a_built_in_secret_file_is_refused(hook, tmp_path, capsys):
    """REQ-049 AC1: rule 1 and Q-S0042-10 (an escape never names a built-in secret file)."""
    folder = holding(tmp_path, ".env", "id_rsa")
    for name in (".env", "id_rsa", "deep/.ENV.local"):
        text = f'[guard]\nallow_paths = [{{ path = "{name}", reason = "fixture" }}]\n'
        (folder / "agk.toml").write_text(text, encoding="utf-8")
        assert bash(hook, folder, "cat .env").startswith("data guard: secret-file (env file)")
        assert bash(hook, folder, "cat id_rsa").startswith("data guard: secret-file (key file)")
        assert "(setting: [guard] allow_paths)" in capsys.readouterr().err


def test_ac2_deny_commands_add_a_log_command(hook, tmp_path):
    """REQ-049 AC1 AC2: rules 1 and 6 (`deny_commands` adds to the log commands)."""
    folder = holding(tmp_path)
    (folder / "agk.toml").write_text('[guard]\ndeny_commands = ["tail-prod"]\n', encoding="utf-8")
    assert bash(hook, folder, "sudo tail-prod -f").startswith("data guard: raw-log (log command)")
    assert bash(hook, folder, "tail README.md") is None
