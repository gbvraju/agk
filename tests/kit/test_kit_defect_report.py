"""A kit defect is reported in one labelled form and the steward keeps its reads (brief #1411,
ADR-0594; part 2 of 2, part 1 is #1410).

Answer 1: `steward_owner.py defect` drafts one report (kit version, operating system and shell,
reason codes, the redacted refusal lines of part 1, what should happen instead), checked by the
outbound data guard, and `--post` opens it labelled `agk-kit-defect`, never `agk-brief`; the plan
never offers it; `defects` lists the open ones one line each. Answer 2: a refused `gh api
rate_limit` gives one line naming the setting and the step that restores it, once per session, and
`doctor.py` changes no permission mode. A recorded `gh` double stands in for GitHub; every name
and value is invented (example.com); no network.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import itertools
import json
import os
import string
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import guard_logs  # noqa: E402
import session_plan  # noqa: E402
import steward_owner  # noqa: E402

SEED = itertools.count(1411)
LABEL = "agk-kit-defect"
HOOK = ROOT / ".claude" / "hooks" / "steward_guard.py"


def guard(root: Path, command: str) -> str | None:
    """The steward guard's denial reason for COMMAND, or None when it allows it."""
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(root)}
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK)], input=json.dumps(payload), capture_output=True, text=True,
        encoding="utf-8", env={**os.environ, "CLAUDE_PROJECT_DIR": str(root)}, check=False,
    )  # fmt: skip
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)["hookSpecificOutput"] if proc.stdout.strip() else None
    return out["permissionDecisionReason"] if out else None


def made(n: int) -> str:
    """n letters and digits from SHA-256 of a counter: invented, belonging to no one."""
    alphabet, out = string.ascii_letters + string.digits, ""
    while len(out) < n:
        digest = hashlib.sha256(str(next(SEED)).encode()).digest()
        out += "".join(alphabet[b % len(alphabet)] for b in digest)
    return out[:n]


def git(root: Path, *args: str) -> None:
    subprocess.run(  # nosec B603 B607 - fixed git argument list, no shell
        ["git", *args], cwd=root, check=True, capture_output=True
    )


@pytest.fixture
def project(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "remote", "add", "origin", "https://github.com/example-org/example-app.git")
    (root / "agk.toml").write_text('version = "0.64.5"\ndefault_branch = "main"\n', "utf-8")
    (root / "config").mkdir()
    (root / "config" / "neutrality.txt").write_text("# invented\nzorblaxcorp\n", "utf-8")
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setattr(steward_owner.session, "repo_name", lambda r: "example-org/example-app")
    return root


def refusal(root: Path, text: str, reason: str = "cannot-judge (hook error)") -> None:
    payload = {"tool_name": "Bash", "tool_input": {"command": text}, "cwd": str(root)}
    error = {"type": "IndexError", "place": "judge:212"}
    assert guard_logs.record_refusal(payload, "data guard", reason, "builder", error)


class GitHub:
    def __init__(self, issues: list | None = None) -> None:
        self.calls: list = []
        self.issues = issues or []

    def __call__(self, endpoint: str, *extra: str, method: str = "GET"):
        self.calls.append((method, endpoint, extra))
        if method == "POST" and endpoint.endswith("/issues"):
            return {"number": 41}
        raise AssertionError((method, endpoint))

    def pages(self, endpoint: str):
        self.calls.append(("GET", endpoint, ()))
        return self.issues


def run(root: Path, monkeypatch, *argv: str) -> tuple[int, str]:
    monkeypatch.chdir(root)
    monkeypatch.setattr(steward_owner, "repo_root", lambda: root)
    return steward_owner.main(list(argv)), ""


def expected(root: Path, text: str = "a seed run against a throwaway database is allowed") -> Path:
    path = root.parent / "expected.txt"
    path.write_text(text + "\n", encoding="utf-8")
    return path


def fields(call: tuple) -> dict[str, str]:
    extra = call[2]
    return dict(extra[i + 1].split("=", 1) for i in range(0, len(extra), 2) if extra[i] == "-f")


# --- answer 1: one labelled form --------------------------------------------------------------


def test_req050_a_kit_defect_is_posted_with_its_label_and_never_agk_brief(
    project, monkeypatch, capsys
):
    """REQ-050: brief #1411 answer 1 (one issue labelled `agk-kit-defect`, never `agk-brief`)."""
    refusal(project, "psql -h db.example.com -f seed.sql")
    hub = GitHub()
    monkeypatch.setattr(steward_owner.session, "gh", hub)
    code, _ = run(project, monkeypatch, "defect", "--title", "the guard refuses a seed run",
                  "--file", str(expected(project)), "--post")  # fmt: skip
    assert code == 0, capsys.readouterr()
    [call] = hub.calls
    assert call[0] == "POST" and call[1] == "repos/example-org/example-app/issues"
    labels = [v for i, v in enumerate(call[2]) if call[2][i - 1] == "-f" and v.startswith("labels")]
    assert labels == [f"labels[]={LABEL}"]
    assert "agk-brief" not in " ".join(call[2])
    assert f"kit defect filed: #41 ({LABEL})" in capsys.readouterr().out


def test_req050_the_body_holds_version_machine_codes_refusals_and_what_should_happen(
    project, monkeypatch, capsys
):
    """REQ-050: brief #1411 answer 1 (the body's fields) and part 1's redacted refusal lines."""
    token = "ghp_" + made(36)
    refusal(project, f"curl -H 'Authorization: token {token}' https://api.example.com/seed")
    refusal(project, "rm -rf build", "bash")
    hub = GitHub()
    monkeypatch.setattr(steward_owner.session, "gh", hub)
    code, _ = run(project, monkeypatch, "defect", "--title", "the guard refuses a seed run",
                  "--file", str(expected(project)), "--post")  # fmt: skip
    assert code == 0, capsys.readouterr()
    body = fields(hub.calls[0])["body"]
    assert "Kit version: 0.64.5" in body
    assert "shell: bash" in body and "Machine: " in body
    assert "Reason codes: bash, cannot-judge (hook error)" in body
    assert "IndexError" in body and "judge:212" in body
    assert "[TOKEN-1]" in body and token not in body and token[4:20] not in body
    assert "What should happen instead: a seed run against a throwaway database" in body
    assert body.rstrip().endswith("Who: AGK steward")


def test_req050_no_refusal_recorded_says_so(project, monkeypatch, capsys):
    """REQ-050: brief #1411 answer 1 (the refusal lines of part 1 only when they exist)."""
    monkeypatch.setattr(steward_owner.session, "gh", GitHub())
    code, _ = run(project, monkeypatch, "defect", "--title", "the guard refuses a seed run",
                  "--file", str(expected(project)))  # fmt: skip
    out = capsys.readouterr().out
    assert code == 0
    assert "Reason codes: none recorded" in out and "    none recorded" in out
    assert "not posted: run again with --post" in out


@pytest.mark.parametrize(
    "planted",
    [
        "send it to ops@example-app.example.com and ghp_PLACEHOLDER",
        "see https://github.com/example-org/example-app/issues/3",
    ],
)
def test_req050_the_outbound_guard_checks_the_body_before_it_is_posted(
    project, monkeypatch, capsys, planted
):
    """REQ-050: brief #1411 answer 1 (the outbound data guard checks the body; fail closed)."""
    planted = planted.replace("PLACEHOLDER", made(36))
    hub = GitHub()
    monkeypatch.setattr(steward_owner.session, "gh", hub)
    code, _ = run(project, monkeypatch, "defect", "--title", "the guard refuses a seed run",
                  "--file", str(expected(project, planted)), "--post")  # fmt: skip
    out = capsys.readouterr().out
    assert code == 2 and hub.calls == []
    assert "outbound guard:" in out and planted not in out


def test_req050_personal_mode_drafts_and_posts_nothing(project, monkeypatch, capsys):
    """REQ-050: brief #1411 contexts (personal: drafted for the person, posted on their word)."""
    hub = GitHub()
    monkeypatch.setattr(steward_owner.session, "gh", hub)
    monkeypatch.setattr(steward_owner, "personal_table", lambda root: {"forge": "files"})
    code, _ = run(project, monkeypatch, "defect", "--title", "the guard refuses a seed run",
                  "--file", str(expected(project)), "--post")  # fmt: skip
    out = capsys.readouterr().out
    assert code == 0 and hub.calls == []
    assert "personal mode: nothing is posted" in out and "Kit version: 0.64.5" in out


def test_req050_the_plan_never_offers_a_kit_defect():
    """REQ-050: brief #1411 answer 3 (a kit defect is never offered by the plan)."""
    brief = {"number": 7, "labels": [{"name": "agk-brief"}], "body": "Priority: 1"}
    defect = {"number": 8, "labels": [{"name": LABEL}], "body": "Priority: 1"}
    both = {"number": 9, "labels": [{"name": "agk-brief"}, {"name": LABEL}], "body": ""}
    assert session_plan.plan_briefs([brief, defect, both]) == [brief]
    assert "plan_briefs(issues)" in inspect.getsource(session_plan.plan_pass)
    assert session_plan.KIT_DEFECT_LABEL == steward_owner.KIT_DEFECT_LABEL == LABEL


def test_req050_the_steward_lists_open_kit_defects_one_line_each(project, monkeypatch, capsys):
    """REQ-050: brief #1411 answer 1 (the steward lists open kit defects in one line each)."""
    issues = [
        {"number": 12, "title": "the guard refuses a heredoc", "created_at": "2026-11-15T08:00Z"},
        {"number": 5, "title": "status prints twice\nsecond line", "created_at": "2026-11-01T08Z"},
        {"number": 13, "title": "a pull request", "pull_request": {}},
    ]
    hub = GitHub(issues)
    monkeypatch.setattr(steward_owner.session, "pages", hub.pages)
    code, _ = run(project, monkeypatch, "defects")
    out = capsys.readouterr().out.splitlines()
    assert code == 0
    assert out == [
        "kit defect #5: status prints twice second line (opened 2026-11-01)",
        "kit defect #12: the guard refuses a heredoc (opened 2026-11-15)",
    ]
    assert hub.calls[0][1].endswith(f"issues?state=open&labels={LABEL}")
    hub.issues = []
    run(project, monkeypatch, "defects")
    assert capsys.readouterr().out.strip() == "kit defects: none open"


def test_req050_unreadable_kit_defects_exit_4(project, monkeypatch, capsys):
    """REQ-050: brief #1411 answer 1 (an unread list is never `none open`)."""
    monkeypatch.setattr(steward_owner.session, "pages", lambda endpoint: None)
    code, _ = run(project, monkeypatch, "defects")
    assert code == 4 and "none open" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "command",
    [
        f"gh issue create --title x --body-file b.md --label {LABEL}",
        f"gh api repos/example-org/example-app/issues -f title=x -F body=@b.md -f labels[]={LABEL}",
    ],
)
def test_req050_the_steward_guard_allows_a_kit_defect_filing(tmp_path, command):
    """REQ-050: brief #1411 answer 1 (the steward may open the labelled issue)."""
    (tmp_path / "b.md").write_text("Kit defect: x\n\nWho: AGK steward\n", encoding="utf-8")
    assert guard(tmp_path, command) is None


@pytest.mark.parametrize(
    "command",
    [
        "gh issue create --title x --body-file b.md --label agk-brief",
        f"gh issue edit 4 --add-label {LABEL}",
        f"gh api repos/example-org/example-app/issues/4/labels -f labels[]={LABEL}",
    ],
)
def test_req050_the_steward_guard_still_denies_other_labels(tmp_path, command):
    """REQ-050: brief #1411 answer 1 (never `agk-brief`; the label only on a new issue)."""
    (tmp_path / "b.md").write_text("Kit defect: x\n", encoding="utf-8")
    assert "label" in (guard(tmp_path, command) or "")


# --- answer 2: the steward keeps its GitHub reads ---------------------------------------------


def gh_proc(code: int, err: str = ""):
    def fake(args, **kwargs):
        assert args[:3] == ["gh", "api", "rate_limit"]
        return subprocess.CompletedProcess(args, code, "4999\n" if code == 0 else "", err)

    return fake


def test_req050_a_read_that_answers_is_ok(project, monkeypatch, capsys):
    """REQ-050: brief #1411 answer 2 (one read, `gh api rate_limit`, checked at start)."""
    monkeypatch.setattr(steward_owner.subprocess, "run", gh_proc(0))
    code, _ = run(project, monkeypatch, "reads", "--session", "st-example-1")
    assert code == 0 and capsys.readouterr().out.strip() == "reads: ok"


@pytest.mark.parametrize(
    "fake, setting",
    [
        (gh_proc(4, "To get started with GitHub CLI, please run:  gh auth login"), "gh auth"),
        (gh_proc(1, "HTTP 403: Resource not accessible"), "the token's access"),
    ],
)
def test_req050_a_refused_read_names_its_setting_and_step_once(
    project, monkeypatch, capsys, fake, setting
):
    """REQ-050: brief #1411 answer 2 (said once, with the step; the steward goes on)."""
    monkeypatch.setattr(steward_owner.subprocess, "run", fake)
    code, _ = run(project, monkeypatch, "reads", "--session", "st-example-1")
    [line] = capsys.readouterr().out.splitlines()
    assert code == 1
    assert line.startswith("reads: gh api refused (setting: " + setting)
    assert "restore: run gh auth status" in line
    assert line.endswith("meanwhile the steward reads through the kit's scripts")
    code, _ = run(project, monkeypatch, "reads", "--session", "st-example-1")
    assert code == 1 and capsys.readouterr().out == ""  # once per session
    run(project, monkeypatch, "reads", "--session", "st-example-2")
    assert capsys.readouterr().out.strip() == line  # another session says it again


def test_req050_a_missing_gh_names_the_path(project, monkeypatch, capsys):
    """REQ-050: brief #1411 answer 2 (the one step that restores it)."""

    def missing(args, **kwargs):
        raise FileNotFoundError(args[0])

    monkeypatch.setattr(steward_owner.subprocess, "run", missing)
    run(project, monkeypatch, "reads")
    assert "setting: gh on PATH); restore: install gh" in capsys.readouterr().out


@pytest.mark.parametrize(
    "settings, name, setting, step",
    [
        ({"permissions": {"deny": ["Bash(gh api*)"]}}, "settings.local.json",
         "permissions.deny of .claude/settings.local.json", "remove that entry, then restart"),
        ({"permissions": {"allow": ["Bash(python3 scripts/agk/*)"]}}, "settings.json",
         "the session's permission mode, with no permissions.allow entry for gh api (verify)",
         "restart the steward session (claude --agent steward), or approve"),
        ({"permissions": {"allow": ["Bash(gh api *)"]}}, "settings.json",
         "the session's permission mode (verify)", "restart the steward session"),
    ],
)  # fmt: skip
def test_req050_a_read_the_runtime_refused_names_the_permission_setting(
    project, monkeypatch, capsys, settings, name, setting, step
):
    """REQ-050: brief #1411 answer 2 (a refused read in a steward session gives its one line)."""
    (project / ".claude").mkdir()
    (project / ".claude" / name).write_text(json.dumps(settings), encoding="utf-8")
    monkeypatch.setattr(steward_owner.subprocess, "run", gh_proc(0))  # never asked
    code, _ = run(project, monkeypatch, "reads", "--refused", "--session", "st-example-3")
    [line] = capsys.readouterr().out.splitlines()
    assert code == 1
    assert f"(setting: {setting}); restore: {step}" in line
    assert "Bash(gh" not in line  # names the setting, never the value


def test_req050_the_steward_is_told_to_check_its_reads_and_list_kit_defects():
    """REQ-050: brief #1411 answers 1 and 2 (the steward's instructions name both steps)."""
    text = (ROOT / ".claude" / "agents" / "steward.md").read_text(encoding="utf-8")
    assert "docs/guides/local-mode.md` (ADR-0594)" in text and "/doctor" in text and LABEL in text
    guide = (ROOT / "docs" / "guides" / "local-mode.md").read_text(encoding="utf-8")
    guide = guide.split("## Reporting a defect of the kit", 1)[1].split("\n## ", 1)[0]
    assert "steward_owner.py reads" in guide and "/doctor" in guide
    assert "steward_owner.py defects" in guide and "steward_owner.py defect " in guide
    assert LABEL in guide and "never `agk-brief`" in guide


def test_req050_doctor_changes_no_permission_mode():
    """REQ-050: brief #1411 answer 2 (the kit's `doctor.py` never changes a permission mode)."""
    source = (ROOT / "scripts" / "agk" / "doctor.py").read_text(encoding="utf-8")
    assert "defaultMode" not in source and "permission_mode" not in source
    tree = ast.parse(source)
    writes = {"write_text", "write_bytes", "unlink", "mkdir", "dump", "touch"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in writes, node.lineno
            moved = node.func.attr in ("replace", "rename", "remove")
            assert not (moved and getattr(node.func.value, "id", "") == "os"), node.lineno
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "open":
            modes = [a.value for a in node.args[1:] if isinstance(a, ast.Constant)]
            assert not any(set(str(m)) & set("wax+") for m in modes), node.lineno


def test_req050_doctor_leaves_the_settings_files_as_they_were(tmp_path):
    """REQ-050: brief #1411 answer 2 (a run of `doctor.py` leaves `.claude/settings*.json`)."""
    root = tmp_path / "proj"
    (root / ".claude").mkdir(parents=True)
    git(root, "init", "-q")
    (root / "agk.toml").write_text('version = "0.64.5"\n', encoding="utf-8")
    before = {"permissions": {"defaultMode": "default", "allow": ["Bash(gh api *)"]}}
    for name in ("settings.json", "settings.local.json"):
        (root / ".claude" / name).write_text(json.dumps(before), encoding="utf-8")
    env = {"HOME": str(tmp_path), "NO_COLOR": "1", "PATH": os.path.dirname(sys.executable)}
    subprocess.run(  # nosec B603 - fixed argument list, no shell; gh absent from a bare PATH
        [sys.executable, str(ROOT / "scripts" / "agk" / "doctor.py")],
        cwd=root, env=env,
        capture_output=True, text=True, timeout=120, check=False,
    )  # fmt: skip
    for name in ("settings.json", "settings.local.json"):
        assert json.loads((root / ".claude" / name).read_text(encoding="utf-8")) == before
