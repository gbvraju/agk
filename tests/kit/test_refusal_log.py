"""Every hook refusal is kept on the machine, redacted (brief #1410, ADR-0593).

Answer 1: each of the four hooks appends one JSON line per denial to `<git common dir>/agk/refusals.log`
(time, session, role, hook, reason code, the command or path redacted by `guard.scan_text` and cut at
500 characters); it rolls over at 1 MB keeping one older file, and a failed write never changes the
decision. Answer 2: a `hook error` line adds the exception's type and the hook's function and line,
never a value, and the denial adds `see agk logs --refusals`. Answer 3: `agk logs --refusals` and the
`agk status` count. Answer 4: Windows-shaped seed runs against a throwaway database. Every name and
value is invented (example.com); no network, no gh.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import itertools
import json
import os
import re
import string
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime
from pathlib import Path

import guard_logs
import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".claude" / "hooks"
SEED = itertools.count(1410)


def made(n: int) -> str:
    """n letters and digits from SHA-256 of a counter: invented, belonging to no one."""
    alphabet, out = string.ascii_letters + string.digits, ""
    while len(out) < n:
        digest = hashlib.sha256(str(next(SEED)).encode()).digest()
        out += "".join(alphabet[b % len(alphabet)] for b in digest)
    return out[:n]


def project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / ".git").mkdir(parents=True)
    (root / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    return root


def run_hook(name: str, root: Path, tool: str, tool_input: dict, *args: str) -> dict | None:
    payload = {"tool_name": tool, "tool_input": tool_input, "cwd": str(root), "session_id": "s-1"}
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "CLAUDE_PROJECT_DIR": str(root),
           "HOME": str(root.parent / "home"), "AGK_SESSION": "cb-example-1"}
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOKS / f"{name}.py"), *args], input=json.dumps(payload),
        capture_output=True, text=True, env=env, check=False, cwd=root,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["hookSpecificOutput"] if proc.stdout.strip() else None


def lines(root: Path, name: str = "refusals.log") -> list[dict]:
    path = root / ".git" / "agk" / name
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


DENIALS = [
    ("data_guard", "Read", {"file_path": ".env"}, (), "secret-file (env file)", "unknown"),
    ("conductor_guard", "Bash", {"command": "rm -rf build"}, (), "bash", "conductor"),
    ("architect_guard", "Write", {"file_path": "src/app.py"}, (), "path", "architect"),
    ("architect_guard", "Bash", {"command": "rm -rf build"}, ("--review",), "bash", "review"),
    ("steward_guard", "Bash", {"command": "gh pr merge 7"}, (), None, "steward"),
]


@pytest.mark.parametrize("hook, tool, tool_input, args, code, role", DENIALS)
def test_req050_a_denial_in_each_hook_appends_one_redacted_line(
    tmp_path, hook, tool, tool_input, args, code, role
):
    """REQ-050: brief #1410 answer 1 (one line per denial: time, session, role, hook, reason)."""
    root = project(tmp_path)
    out = run_hook(hook, root, tool, tool_input, *args)
    assert out and out["permissionDecision"] == "deny"
    [line] = lines(root)
    assert line["hook"] == hook.replace("_", " ")
    assert line["session"] == "cb-example-1" and line["role"] == role
    assert line["reason"] == code if code else line["reason"]
    assert line["text"] == next(iter(tool_input.values()))
    assert datetime.strptime(line["at"], "%Y-%m-%dT%H:%M:%SZ")
    assert "error" not in line


def test_req050_an_allowed_call_writes_nothing(tmp_path):
    """REQ-050: brief #1410 answer 1 (only a denial is kept)."""
    root = project(tmp_path)
    assert run_hook("data_guard", root, "Read", {"file_path": "README.md"}) is None
    assert run_hook("conductor_guard", root, "Bash", {"command": "date -u"}) is None
    assert lines(root) == []


def test_req050_a_planted_secret_never_reaches_the_log_in_clear(tmp_path):
    """REQ-050: brief #1410 answer 1 (redacted by guard.scan_text, cut at 500 characters)."""
    root = project(tmp_path)
    token = "ghp_" + made(36)
    command = f"curl -H 'Authorization: token {token}' https://api.example.com/x && cat .env "
    out = run_hook("data_guard", root, "Bash", {"command": command + "x" * 900})
    assert out["permissionDecision"] == "deny"
    raw = (root / ".git" / "agk" / "refusals.log").read_text(encoding="utf-8")
    assert token not in raw and token[4:20] not in raw
    [line] = lines(root)
    assert "[TOKEN-1]" in line["text"] and len(line["text"]) == 500


def test_req050_a_worktree_keeps_its_refusals_in_the_common_dir(tmp_path):
    """REQ-050: brief #1410 answer 1 (`<git common dir>/agk/refusals.log`, one per clone)."""
    root = project(tmp_path)
    tree = tmp_path / "tree"
    gitdir = root / ".git" / "worktrees" / "tree"
    gitdir.mkdir(parents=True)
    (gitdir / "commondir").write_text("../..\n", encoding="utf-8")
    tree.mkdir()
    (tree / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")
    assert run_hook("data_guard", tree, "Read", {"file_path": ".env"})
    assert len(lines(root)) == 1 and not (tree / "agk").exists()


def load_data_guard(monkeypatch, root: Path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.setenv("AGK_SESSION", "cb-example-2")
    monkeypatch.delenv("SHELL", raising=False)
    spec = importlib.util.spec_from_file_location("data_guard_1410", HOOKS / "data_guard.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def call_main(module, monkeypatch, capsys, payload: dict) -> dict:
    stdin = io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode("utf-8")), encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", stdin)
    assert module.main() == 0
    return json.loads(capsys.readouterr().out)["hookSpecificOutput"]


def test_req050_a_hook_error_still_denies_and_names_its_type_and_place(tmp_path, monkeypatch, capsys):
    """REQ-050: brief #1410 answer 2 (the exception's type and the function and line, no value)."""
    root = project(tmp_path)
    guard = load_data_guard(monkeypatch, root)

    def broken(self, command, ps=False):
        raise ValueError("planted-value-1410")

    monkeypatch.setattr(guard.Guard, "command", broken)
    payload = {"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": str(root)}
    out = call_main(guard, monkeypatch, capsys, payload)
    assert out["permissionDecision"] == "deny"
    assert out["permissionDecisionReason"].startswith("data guard: cannot-judge (hook error)")
    assert "see agk logs --refusals" in out["permissionDecisionReason"]
    [line] = lines(root)
    assert line["reason"] == "cannot-judge (hook error)"
    assert line["error"]["type"] == "ValueError"
    assert line["error"]["place"].startswith("decide:") and line["error"]["place"][7:].isdigit()
    assert "planted-value-1410" not in json.dumps(line)


def test_req050_an_ordinary_denial_does_not_point_at_the_refusal_log(tmp_path, monkeypatch, capsys):
    """REQ-050: brief #1410 answer 2 (only a hook error adds the pointer)."""
    root = project(tmp_path)
    guard = load_data_guard(monkeypatch, root)
    payload = {"tool_name": "Read", "tool_input": {"file_path": ".env"}, "cwd": str(root)}
    out = call_main(guard, monkeypatch, capsys, payload)
    assert "agk logs --refusals" not in out["permissionDecisionReason"]


def test_req050_a_log_that_cannot_be_written_leaves_the_denial_unchanged(tmp_path):
    """REQ-050: brief #1410 answer 1 (a failed write never changes a decision)."""
    root = project(tmp_path)
    (root / ".git" / "agk").write_text("a file where the folder would be\n", encoding="utf-8")
    out = run_hook("data_guard", root, "Read", {"file_path": ".env"})
    assert out["permissionDecision"] == "deny"
    assert out["permissionDecisionReason"].startswith("data guard: secret-file (env file)")
    no_git = tmp_path / "loose"
    no_git.mkdir()
    assert run_hook("conductor_guard", no_git, "Bash", {"command": "rm -rf build"})


def test_req050_the_log_rolls_over_at_one_megabyte_keeping_one_older_file(tmp_path):
    """REQ-050: brief #1410 answer 1 (rollover at 1 MB, one older file)."""
    root = project(tmp_path)
    folder = root / ".git" / "agk"
    folder.mkdir()
    (folder / "refusals.log.1").write_text("oldest\n", encoding="utf-8")
    (folder / "refusals.log").write_text("x" * guard_logs.ROLL_BYTES + "\n", encoding="utf-8")
    assert run_hook("data_guard", root, "Read", {"file_path": ".env"})
    assert len(lines(root)) == 1
    older = (folder / "refusals.log.1").read_text(encoding="utf-8")
    assert older.startswith("x" * 100) and "oldest" not in older
    assert sorted(p.name for p in folder.iterdir()) == ["refusals.log", "refusals.log.1"]


def test_req050_agk_logs_refusals_prints_the_file_redacted(tmp_path, monkeypatch, capsys):
    """REQ-050: brief #1410 answer 3 (`agk logs --refusals`, the older file first)."""
    root = project(tmp_path)
    folder = root / ".git" / "agk"
    folder.mkdir()
    (folder / "refusals.log.1").write_text('{"reason": "older"}\n', encoding="utf-8")
    planted = "ana@mail.example.io"  # example.com is not flagged
    (folder / "refusals.log").write_text(f'{{"reason": "newer", "text": "{planted}"}}\n',
                                         encoding="utf-8")
    monkeypatch.chdir(root)
    assert guard_logs.main(["--refusals"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == '{"reason": "older"}'
    assert out[1] == '{"reason": "newer", "text": "[EMAIL-1]"}'
    assert out[-1] == "agk logs: EMAIL 1"


def test_req050_agk_logs_refusals_with_no_log_says_so(tmp_path, monkeypatch, capsys):
    """REQ-050: brief #1410 answer 3 (no refusals yet, or no git folder)."""
    root = project(tmp_path)
    monkeypatch.chdir(root)
    assert guard_logs.main(["--refusals"]) == 0
    assert capsys.readouterr().out == "agk logs: no refusals recorded\n"
    assert guard_logs.main(["--refusals", "app.log"]) == 2


def test_req050_the_data_guard_allows_agk_logs_refusals(tmp_path):
    """REQ-050: brief #1410 answer 3 (the reader is the allowed way to read the log)."""
    root = project(tmp_path)
    command = "python3 scripts/agk/guard_logs.py --refusals"
    assert run_hook("data_guard", root, "Bash", {"command": command}) is None
    denied = run_hook("data_guard", root, "Bash", {"command": "cat .git/agk/refusals.log"})
    assert denied["permissionDecisionReason"].startswith("data guard: raw-log")


def test_req050_agk_status_counts_todays_refusals_by_reason(tmp_path, monkeypatch, capsys):
    """REQ-050: brief #1410 answer 3 (`agk status` shows today's count by reason code)."""
    import autopilot

    root = project(tmp_path)
    folder = root / ".git" / "agk"
    folder.mkdir()
    rows = [("2026-11-16T08:00:00Z", "bash"), ("2026-11-16T09:00:00Z", "secret-file (env file)"),
            ("2026-11-16T09:30:00Z", "bash"), ("2026-11-15T23:59:59Z", "bash")]
    text = "".join(json.dumps({"at": at, "reason": r}) + "\n" for at, r in rows)
    (folder / "refusals.log").write_text(text + "not json\n", encoding="utf-8")
    now = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)
    assert guard_logs.today_line(root, now) == "refusals today: 3 (bash 2, secret-file (env file) 1)"
    assert guard_logs.today_line(tmp_path / "loose", now) == "refusals today: none"
    monkeypatch.setattr(autopilot, "job_lines", lambda r: ([], []))
    monkeypatch.setattr(autopilot, "claude_processes", lambda: [])
    monkeypatch.setattr(autopilot, "github_lines", lambda r: (["queue: none"], True))
    assert autopilot.status(root, now) == 0
    assert "refusals today: 3 (bash 2, secret-file (env file) 1)" in capsys.readouterr().out


# --- answer 4: Windows-shaped seed runs against a throwaway database --------------------------

SEEDS = [
    ("PowerShell", r"psql -h localhost -U seed -d scratch -f db\seed\001_init.sql"),
    ("PowerShell", r"Get-Content db\seed\001_init.sql | docker exec -i scratch-db psql -U seed scratch"),
    ("PowerShell", "foreach ($f in Get-ChildItem db\\seed\\*.sql) { psql -U seed -d scratch -f $f }\r\n"),
    ("PowerShell", 'psql -U seed -d scratch -c "select 1" `\r\n  -v ON_ERROR_STOP=1\r\n'),
    ("PowerShell", 'psql -U seed -d scratch -c "$(Get-Content db\\seed\\001_init.sql -Raw)"'),
    ("PowerShell", '& "C:\\Program Files\\PostgreSQL\\16\\bin\\psql.exe" -d scratch -f db\\seed\\002.sql'),
    ("Bash", "for f in db/seed/*.sql; do psql -U seed -d scratch -f \"$f\"; done\r\n"),
    ("Bash", "psql -U seed -d scratch <<'SQL'\r\nINSERT INTO users VALUES (1, 'a@example.com');\r\nSQL\r\n"),
    ("Bash", "cat <<EOF | psql -U seed -d scratch\r\nselect 1;\r\nEOF\r\necho seeded\r\n"),
    ("Bash", 'python -c "import sqlite3; sqlite3.connect(\'scratch.db\').execute(\'select 1\')"\r\n'),
]


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    root = project(tmp_path)
    for name in ("db/seed/001_init.sql", "db/seed/002.sql", ".env"):
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text("select 1;\n", encoding="utf-8")
    guard = load_data_guard(monkeypatch, root)
    monkeypatch.setenv("SHELL", "C:\\Program Files\\PowerShell\\7\\pwsh.exe")
    return guard, root


@pytest.mark.parametrize("tool, command", SEEDS)
def test_req050_a_windows_seed_run_is_allowed_clean_and_denied_with_a_planted_name(
    seeded, tool, command
):
    """REQ-050: brief #1410 answer 4 (a PowerShell session, backslash paths, CRLF line ends)."""
    guard, root = seeded
    payload = {"tool_name": tool, "tool_input": {"command": command}, "cwd": str(root)}
    assert guard.judge(payload) is None
    planted = re.sub(r"scratch(?![-.\w])", "scratch .env", command, count=1)
    planted = planted if planted != command else command.rstrip() + " .env"
    payload["tool_input"]["command"] = planted
    assert guard.judge(payload).startswith("data guard: secret-file"), planted


def test_req050_a_crlf_here_document_still_ends_at_its_delimiter(seeded):
    """REQ-050: brief #1410 answer 4 (a `SQL\\r` line closes `<<'SQL'`; the body stays data)."""
    guard, root = seeded
    body = "psql -d scratch <<'SQL'\r\n\\i other.sql\r\nSQL\r\ncat .env\r\n"
    payload = {"tool_name": "Bash", "tool_input": {"command": body}, "cwd": str(root)}
    assert guard.judge(payload).startswith("data guard: secret-file")
    payload["tool_input"]["command"] = "psql -d scratch <<'SQL'\r\n\\i .env\r\nSQL\r\n"
    assert guard.judge(payload).startswith("data guard: secret-file")
