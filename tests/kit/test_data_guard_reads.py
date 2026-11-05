"""Tests of the data guard's layer 1 on tool paths (SPEC-0042 rules 1 to 3, 5, 6 and 9, brief #589).

Every value is invented: key-shaped strings are built here at run time from a fixed seed, so no
secret-like constant sits in this file. Files live in tmp_path; no network, no gh.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK_FILE = ROOT / ".claude" / "hooks" / "data_guard.py"
LINE = re.compile(r"data guard: (secret-file|raw-log|cannot-judge) \([a-z ]+\): \S.*")
SECRET = "data guard: secret-file ({}): ask the person for the one value you need, or for a cleaned copy"
LOG = "data guard: raw-log ({}): read it through `agk logs <file>` (python3 scripts/agk/guard_logs.py)"


def load_hook():
    spec = importlib.util.spec_from_file_location("data_guard", HOOK_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def hook(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    return load_hook()


def fake_value(n: int = 1) -> str:
    """A key-shaped line built at run time: a hex digest next to a key-like name (rule 10)."""
    return "api_key = " + hashlib.sha256(f"brief-589-{n}".encode()).hexdigest()[:40] + "\n"


def call(hook, tmp_path, tool: str, **tool_input) -> str | None:
    payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input}
    return hook.judge({**payload, "cwd": str(tmp_path)})


def run_hook(tmp_path: Path, stdin: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "HOME": str(tmp_path)}
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK_FILE)], input=stdin, capture_output=True, text=True, env=env
    )


def reason(proc: subprocess.CompletedProcess) -> str:
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse" and out["permissionDecision"] == "deny"
    return out["permissionDecisionReason"]


# --- rule 2: registration and failing closed -----------------------------------------------------


def test_ac2_the_settings_register_layer_1_with_its_matcher_on_failure_and_timeout():
    """REQ-049 AC2: rule 2 (the PreToolUse registration in .claude/settings.json)."""
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    entries = settings["hooks"]["PreToolUse"]
    ours = [e for e in entries if any("data_guard.py" in h["command"] for h in e["hooks"])]
    assert len(ours) == 1
    assert ours[0]["matcher"] == "Read|Grep|Glob|Bash|PowerShell|Edit|Write|MultiEdit|NotebookEdit"
    (h,) = ours[0]["hooks"]
    assert h["type"] == "command" and h["onFailure"] == "block" and h["timeout"] == 10
    assert h["command"] == 'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/data_guard.py'
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert ".claude/hooks/data_guard.py" in manifest["verbatim"]


def test_ac2_the_settings_deny_reads_of_the_built_in_secret_files_with_carve_outs_after():
    """REQ-049 AC2: Q-S0042-13 (Read deny rules, then the `!` carve-outs, same list)."""
    deny = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    deny = deny["permissions"]["deny"]
    for rule in ("Read(**/.env)", "Read(**/.env.*)", "Read(**/*.pem)", "Read(**/*.key)",
                 "Read(**/*.tfstate)", "Read(**/secrets.*)", "Read(~/.ssh/**)", "Read(~/.aws/**)",
                 "Read(~/.netrc)", "Read(~/.git-credentials)", "Read(~/.config/gh/**)"):
        assert rule in deny
    first_carve = min(i for i, r in enumerate(deny) if r.startswith("Read(!"))
    last_rule = max(i for i, r in enumerate(deny) if r.startswith("Read(") and "!" not in r)
    assert last_rule < first_carve
    assert "Read(!**/.env.example)" in deny and "Read(!**/tests/**)" in deny
    assert not [r for r in deny if r.startswith("Read(") and r.endswith("/**)") and "!" not in r
                and not r.startswith("Read(~/")]  # no whole-folder rule under a carve-out


def test_ac2_input_that_is_not_json_denies_with_cannot_judge(tmp_path):
    """REQ-049 AC2: rule 2 (fails closed)."""
    proc = run_hook(tmp_path, "not json")
    assert proc.returncode == 0
    assert reason(proc).startswith("data guard: cannot-judge (")


@pytest.mark.parametrize(
    "payload",
    [
        [1, 2],
        {"tool_name": "Read", "tool_input": ["x"]},
        {"tool_name": "Read", "tool_input": {"file_path": 7}},
        {"tool_name": "Bash", "tool_input": {"command": None}},
        {"tool_name": "Grep", "tool_input": {"pattern": "x", "path": ["."]}},
    ],
)
def test_ac2_a_tool_input_of_the_wrong_shape_denies_with_cannot_judge(tmp_path, payload):
    """REQ-049 AC2: rule 2 (a tool input of the wrong type)."""
    proc = run_hook(tmp_path, json.dumps(payload))
    assert reason(proc).startswith("data guard: cannot-judge (")


def test_ac2_a_setting_that_raises_denies_with_cannot_judge(hook, tmp_path, monkeypatch):
    """REQ-049 AC2: rule 2 (an exception inside the hook denies; it never allows)."""

    def boom(root):
        raise RuntimeError("unreadable")

    monkeypatch.setattr(hook, "load_settings", boom)
    line = call(hook, tmp_path, "Read", file_path="README.md")
    assert line is not None and line.startswith("data guard: cannot-judge (hook error)")


def test_ac2_an_allowed_call_prints_nothing_and_exits_0(tmp_path):
    """REQ-049 AC2: rule 2 (an allowed call prints nothing)."""
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    payload = {"tool_name": "Read", "tool_input": {"file_path": "README.md"}, "cwd": str(tmp_path)}
    proc = run_hook(tmp_path, json.dumps(payload))
    assert proc.returncode == 0 and proc.stdout == ""


def test_ac2_a_denial_end_to_end_is_the_json_of_rule_2_with_the_line_of_rule_9(tmp_path):
    """REQ-049 AC2: rules 2 and 9."""
    payload = {"tool_name": "Read", "tool_input": {"file_path": ".env"}, "cwd": str(tmp_path)}
    proc = run_hook(tmp_path, json.dumps(payload))
    assert proc.returncode == 0 and reason(proc) == SECRET.format("env file")


# --- rules 3, 5 and 9: secret files by every tool and every path form ---------------------------

NAMES = {
    ".env": "env file", ".env.local": "env file", "server.pem": "key file", "tls.key": "key file",
    "cert.p12": "key file", "cert.pfx": "key file", "id_rsa": "key file",
    "id_ed25519_sk": "key file", "prod.tfstate": "state file", "prod.tfstate.backup": "state file",
    "secrets.yaml": "secrets file",
}
TOOLS = [("Read", "file_path"), ("Edit", "file_path"), ("Write", "file_path"),
         ("MultiEdit", "file_path"), ("NotebookEdit", "notebook_path")]


@pytest.mark.parametrize("name", sorted(NAMES))
@pytest.mark.parametrize("tool,field", TOOLS)
def test_ac2_each_tool_on_each_built_in_secret_file_is_denied_with_the_line(
    hook, tmp_path, name, tool, field
):
    """REQ-049 AC2: rules 3, 5 and 9 (a read and an edit are judged alike)."""
    line = call(hook, tmp_path, tool, **{field: f"config/{name}"})
    assert line == SECRET.format(NAMES[name])
    assert name not in line and "config" not in line


@pytest.mark.parametrize("form", ["ABS", "./.env", "sub/../.env", "~/../.env", "././.env"])
def test_ac2_relative_absolute_home_and_dotdot_paths_are_denied(hook, tmp_path, form):
    """REQ-049 AC2: rule 3 (each path resolved against cwd and with realpath)."""
    path = str(tmp_path / ".env") if form == "ABS" else form
    assert call(hook, tmp_path, "Read", file_path=path) == SECRET.format("env file")


def test_ac2_a_link_to_a_secret_file_is_judged_by_the_resolved_path(hook, tmp_path):
    """REQ-049 AC2: rule 3 (a link that points to a denied file)."""
    (tmp_path / ".env").write_text("A=1\n", encoding="utf-8")
    (tmp_path / "notes.txt").symlink_to(tmp_path / ".env")
    assert call(hook, tmp_path, "Read", file_path="notes.txt") == SECRET.format("env file")


@pytest.mark.parametrize(
    "rel",
    [".ssh/config", ".aws/credentials", ".azure/x.json", ".config/gcloud/a.db", ".kube/config",
     ".netrc", ".git-credentials", ".docker/config.json", ".config/gh/hosts.yml"],
)
def test_ac2_the_credential_stores_of_the_home_folder_are_denied(hook, tmp_path, rel):
    """REQ-049 AC2: rule 5 (everything under ~/.ssh/ and the like, Q-S0042-18)."""
    expected = SECRET.format("credential store")
    assert call(hook, tmp_path, "Read", file_path=f"~/{rel}") == expected
    assert call(hook, tmp_path, "Read", file_path=str(tmp_path / "home" / rel)) == expected


@pytest.mark.parametrize("name", [".ENV", ".Env.local", "ID_RSA", "Server.PEM", "Secrets.Json"])
def test_ac2_case_variants_of_secret_files_are_denied_on_every_platform(hook, tmp_path, name):
    """REQ-049 AC2: rule 5 (case-insensitive on every platform)."""
    line = call(hook, tmp_path, "Read", file_path=name)
    assert line is not None and line.startswith("data guard: secret-file (")


@pytest.mark.parametrize("name", ["id_map.py", "id_rsa.pub", ".envrc", "catalog.json", "key.md"])
def test_ac2_look_alike_names_are_allowed(hook, tmp_path, name):
    """REQ-049 AC2: rule 5 (a source file such as id_map.py is not a key file)."""
    assert call(hook, tmp_path, "Read", file_path=name) is None


def test_ac2_grep_and_glob_naming_a_secret_file_are_denied(hook, tmp_path):
    """REQ-049 AC2: rule 3 (the paths and globs Grep and Glob search with)."""
    assert call(hook, tmp_path, "Grep", pattern="x", path=".env") == SECRET.format("env file")
    assert call(hook, tmp_path, "Grep", pattern="x", path="src", glob="*.pem") == SECRET.format(
        "key file"
    )
    assert call(hook, tmp_path, "Glob", pattern="**/.env") == SECRET.format("env file")
    assert call(hook, tmp_path, "Glob", pattern="**/*.py") is None


def test_ac2_env_example_and_a_fixture_are_allowed_clean_and_denied_with_a_finding(hook, tmp_path):
    """REQ-049 AC2: rule 5 and Q-S0042-8 (the hook reads the file itself first)."""
    fixture = tmp_path / "tests" / "fixtures" / ".env"
    fixture.parent.mkdir(parents=True)
    for path in (tmp_path / ".env.example", fixture):
        path.write_text("PORT=8080\n", encoding="utf-8")
        assert call(hook, tmp_path, "Read", file_path=str(path)) is None
        path.write_text(fake_value(), encoding="utf-8")
        assert call(hook, tmp_path, "Read", file_path=str(path)) == SECRET.format("env file")


def test_ac2_npmrc_is_denied_only_with_a_token_line(hook, tmp_path):
    """REQ-049 AC2: rule 5 (.npmrc and .pypirc when the file holds a token line)."""
    npmrc = tmp_path / ".npmrc"
    npmrc.write_text("registry=https://registry.example.com/\n", encoding="utf-8")
    assert call(hook, tmp_path, "Read", file_path=".npmrc") is None
    built = hashlib.sha256(b"npm-589").hexdigest()
    npmrc.write_text(f"//registry.example.com/:_authToken={built}\n", encoding="utf-8")
    assert call(hook, tmp_path, "Read", file_path=".npmrc") == SECRET.format("token file")


# --- rule 5's folder check and rule 6's logs -----------------------------------------------------


def test_ac2_grep_over_a_folder_holding_a_secret_file_is_denied_ignored_or_not(hook, tmp_path):
    """REQ-049 AC2: rule 5 (the folder check) and Q-S0042-11 (an ignored file still counts)."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / ".env").write_text("A=1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(".env\n", encoding="utf-8")
    expected = SECRET.format("folder search")
    assert call(hook, tmp_path, "Grep", pattern="x", path="app") == expected
    assert call(hook, tmp_path, "Grep", pattern="x") == expected


def test_ac2_grep_over_a_folder_holding_only_a_clean_env_example_is_allowed(hook, tmp_path):
    """REQ-049 AC2: rule 5 (the folder check's exceptions)."""
    (tmp_path / ".env.example").write_text("PORT=8080\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("print(1)\n", encoding="utf-8")
    assert call(hook, tmp_path, "Grep", pattern="x", path=".") is None


@pytest.mark.parametrize("log", ["app.log", "logs/output.txt", "deep/Logs/x.txt", "APP.LOG"])
def test_ac2_grep_over_a_project_holding_a_log_is_denied(hook, tmp_path, log):
    """REQ-049 AC2: rules 5 and 6 (Grep with path "." and with no path)."""
    target = tmp_path / log
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("line\n", encoding="utf-8")
    expected = LOG.format("folder search")
    assert call(hook, tmp_path, "Grep", pattern="x", path=".") == expected
    assert call(hook, tmp_path, "Grep", pattern="x") == expected


def test_ac2_a_log_only_under_tests_is_allowed_clean_and_a_fixture_key_denies(hook, tmp_path):
    """REQ-049 AC2: rule 5 (a fixture is scanned before a search over it is allowed)."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "run.log").write_text("ok\n", encoding="utf-8")
    assert call(hook, tmp_path, "Grep", pattern="x") is None
    (tmp_path / "tests" / ".env").write_text(fake_value(2), encoding="utf-8")
    assert call(hook, tmp_path, "Grep", pattern="x", path="tests") == SECRET.format(
        "folder search"
    )
    assert call(hook, tmp_path, "Read", file_path="tests/.env") == SECRET.format("env file")


@pytest.mark.parametrize("path", ["app.log", "app.log.1", "logs/output.txt", "APP.LOG", "Logs/a"])
@pytest.mark.parametrize("tool,field", TOOLS)
def test_ac2_each_tool_on_a_raw_log_is_denied(hook, tmp_path, path, tool, field):
    """REQ-049 AC2: rule 6 (a path ending .log or .log.<n>, or with a component logs)."""
    assert call(hook, tmp_path, tool, **{field: path}) == LOG.format("log file")


def test_ac2_ordinary_files_are_allowed(hook, tmp_path):
    """REQ-049 AC2: the guard denies only what rules 5 and 6 name."""
    assert call(hook, tmp_path, "Read", file_path="README.md") is None
    assert call(hook, tmp_path, "Edit", file_path="src/app.py") is None
    assert call(hook, tmp_path, "Glob", pattern="docs/*.md") is None


# --- rule 1: the [guard] table only adds, and an escape counts only on the default branch -------


def git(root: Path, *args: str) -> None:
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=root, check=True, capture_output=True,
    )


def project(tmp_path: Path, default_toml: str, branch_toml: str) -> None:
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "agk.toml").write_text(default_toml, encoding="utf-8")
    git(tmp_path, "add", "agk.toml")
    git(tmp_path, "commit", "-q", "-m", "default")
    git(tmp_path, "update-ref", "refs/remotes/origin/main", "HEAD")
    (tmp_path / "agk.toml").write_text(branch_toml, encoding="utf-8")


ALLOW = '[guard]\nallow_paths = [{ path = "logs/notes.md", reason = "a source file" }]\n'


def test_ac1_an_allow_paths_entry_on_both_lifts_the_log_denial_for_one_clean_file(hook, tmp_path):
    """REQ-049 AC1: rule 1 (the one documented escape, layer 1 only)."""
    project(tmp_path, ALLOW, ALLOW)
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "notes.md").write_text("notes\n", encoding="utf-8")
    assert call(hook, tmp_path, "Read", file_path="logs/notes.md") is None
    assert call(hook, tmp_path, "Read", file_path="logs/other.md") == LOG.format("log file")
    (tmp_path / "logs" / "notes.md").write_text(fake_value(3), encoding="utf-8")
    assert call(hook, tmp_path, "Read", file_path="logs/notes.md") == LOG.format("log file")


def test_ac1_an_allow_paths_entry_only_on_the_branch_does_not_count(hook, tmp_path):
    """REQ-049 AC1: rule 1 (a branch cannot loosen its own guard)."""
    project(tmp_path, "", ALLOW)
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "notes.md").write_text("notes\n", encoding="utf-8")
    assert call(hook, tmp_path, "Read", file_path="logs/notes.md") == LOG.format("log file")


def test_ac1_deny_paths_add_a_custom_secret_path(hook, tmp_path):
    """REQ-049 AC1: rule 1 (`deny_paths` adds to rule 5, case-insensitively)."""
    (tmp_path / "agk.toml").write_text('[guard]\ndeny_paths = ["*.sqlite"]\n', encoding="utf-8")
    assert call(hook, tmp_path, "Read", file_path="data/Main.SQLITE") == SECRET.format(
        "custom path"
    )
    assert call(hook, tmp_path, "Read", file_path="data/main.db") is None


@pytest.mark.parametrize(
    "table",
    ["enabled = false", "off = true", 'allow_paths = [{ path = "app.log" }]',
     'patterns = [{ name = "x", regex = "(" }]'],
)
def test_ac1_a_refused_table_keeps_the_built_in_rules_and_counts_no_addition(
    hook, tmp_path, table, capsys
):
    """REQ-049 AC1: rule 1 (refused, naming the setting; the built-in rules alone apply)."""
    text = f'[guard]\ndeny_paths = ["*.sqlite"]\n{table}\n'
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    assert call(hook, tmp_path, "Read", file_path=".env") == SECRET.format("env file")
    assert call(hook, tmp_path, "Read", file_path="app.log") == LOG.format("log file")
    assert call(hook, tmp_path, "Read", file_path="a.sqlite") is None
    err = capsys.readouterr().err
    assert "(setting: [guard] " in err and "app.log" not in err and "false" not in err


def test_ac2_every_denial_matches_the_line_of_rule_9_and_holds_no_path(hook, tmp_path):
    """REQ-049 AC2: rule 9 (one line, never the path, the command or a value)."""
    for path in (".env", "deep/server.pem", "~/.aws/credentials", "x/app.log"):
        line = call(hook, tmp_path, "Read", file_path=path)
        assert LINE.fullmatch(line) and "\n" not in line
        assert Path(path).name not in line
