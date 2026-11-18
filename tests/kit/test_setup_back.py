"""/agk:setup build (g): the steward hands a plain-words ask to `/agk:setup`, and `/agk:setup back`
removes only the scheduler tasks this command added and prepares the reverse settings change
(brief #1466, SPEC-0065 rules 2, 13 and 17, ADR-0624; REQ-072 AC8).

A fake machine read, saved GitHub answers, a stub runtime that records every command and a scratch
git repository whose `origin` is a bare repository beside it; no network, no Windows, no model.
Invented names of example.com only.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess  # nosec B404 - the tests' own scratch repository, fixed argument lists
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location("agk_setup_g", SCRIPTS / "setup.py")
setup = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(setup)
import steward_evidence  # noqa: E402

AGENT = ROOT / ".claude" / "agents" / "steward.md"
SKILL = ROOT / "skills" / "setup" / "SKILL.md"
WSL_TASK = "AGK conductor watchdog (WSL)"
AUTO_TASK = "agk-autopilot (WSL)"
SECRET = re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}|github_pat_|password\s*[=:]", re.IGNORECASE)
WHO = ("-c", "user.email=member-example-1@example.com", "-c", "user.name=member-example-1")
TOOLS = {"python": "3.12.1", "git": "2.43.0", "gh": "2.50.0", "claude": "2.1.0", "node": "20.11.0"}


def git(root: Path, *args: str) -> str:
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, the scratch repository
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def project(tmp_path: Path, toml: str) -> Path:
    root = tmp_path / "project"
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    (root / "docs" / "adr" / "0001-example.md").write_text("# ADR-0001\n", encoding="utf-8")
    (root / "notes.txt").write_text("the person's own data\n", encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, *WHO, "add", ".")
    git(root, *WHO, "commit", "-q", "-m", "example")
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", str(origin))
    git(root, "remote", "add", "origin", str(origin))
    git(root, "push", "-q", "origin", "main")
    git(root, "fetch", "-q", "origin")
    return root


def machine(**over) -> dict:
    found = {
        "os": "Linux", "os_version": "6.1", "wsl": "absent", "memory_total_gb": 16,
        "memory_available_gb": 12, "cores": 8, "disk_free_gb": 100, "admin": False,
        "tools": dict(TOOLS, podman="4.9.3", docker=None), "winget": "absent",
        "proxy": "none", "remote": "example-org/example-project",
    }  # fmt: skip
    return found | over


class Runtime:
    """Every command setup runs is kept; `schtasks /Delete` answers CODE, the WSL script its
    table (the watchdog row `done` on its setup pass), and `wsl.py plan` the task-on line."""

    def __init__(self, monkeypatch, code=0):
        self.calls: list[list[str]] = []
        self.code = code
        monkeypatch.setattr(setup, "run_cmd", self.cmd)
        monkeypatch.setattr(setup, "run_out", self.out)

    def cmd(self, args, cwd):
        self.calls.append(list(args))
        return self.code if args[:2] == ["schtasks", "/Delete"] else 1

    def out(self, args, cwd):
        self.calls.append(list(args))
        if args[:3] == ["pwsh", "-NoProfile", "-File"]:
            check = "-Status" in args
            rows = [{"step": "wsl", "result": "skipped", "note": ""}]
            if "-InstallWatchdog" in args:
                rows.append({"step": "watchdog", "result": "waiting" if check else "done",
                             "note": "set up"})  # fmt: skip
            return 0, json.dumps({"steps": rows, "pending": []})
        if args[2:3] == ["plan"]:
            return 0, "watchdog: the WSL task on, the Windows task disabled (never deleted)\n"
        return 0, "wsl: on\n"


def run(root, capsys, form, *extra, fake=None):
    m, g = root.parent / "machine.json", root.parent / "github.json"
    m.write_text(json.dumps(fake or machine()), encoding="utf-8")
    g.write_text(json.dumps({"lease": "free", "running": 0}), encoding="utf-8")
    code = setup.main([form, "--machine", str(m), "--github", str(g), "--root", str(root), *extra])
    return code, capsys.readouterr().out


def record_of(root: Path) -> dict:
    path = Path(git(root, "rev-parse", "--absolute-git-dir")) / "agk" / "setup.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def write_record(root: Path, record: dict) -> None:
    path = Path(git(root, "rev-parse", "--absolute-git-dir")) / "agk" / "setup.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")


def files_of(root: Path) -> dict:
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}


def test_ac8_the_wsl_path_records_the_task_it_added(tmp_path, capsys, monkeypatch):
    """REQ-072 AC8: rule 13: a task the setup pass added is recorded by name in setup.json."""
    root = project(tmp_path, 'review_mode = "solo"\nexecution = "local"\n')
    Runtime(monkeypatch)
    fake = machine(os="Windows", wsl="present")
    code, out = run(root, capsys, "wsl", "--yes", "--answer", "windows=wsl", fake=fake)
    assert code == 0, out
    assert record_of(root)["tasks"] == [WSL_TASK]
    run(root, capsys, "wsl", "--yes", "--answer", "windows=wsl", fake=fake)
    assert record_of(root)["tasks"] == [WSL_TASK]  # a second run records nothing twice


def test_ac8_with_autopilot_the_recorded_task_is_autopilots(tmp_path, capsys, monkeypatch):
    """REQ-072 AC8: rule 17: with `[autopilot]` set the WSL script's task is autopilot's."""
    root = project(tmp_path, 'execution = "local"\n[autopilot]\nmode = "assist"\n')
    Runtime(monkeypatch)
    fake = machine(os="Windows", wsl="present")
    assert run(root, capsys, "wsl", "--yes", "--answer", "windows=wsl", fake=fake)[0] == 0
    assert record_of(root)["tasks"] == [AUTO_TASK]


def test_ac8_back_without_a_yes_changes_nothing(tmp_path, capsys, monkeypatch):
    """REQ-072 AC8: back names what it would do and, without the yes, runs nothing."""
    root = project(tmp_path, "")
    write_record(root, {"tasks": [WSL_TASK]})
    rt = Runtime(monkeypatch)
    code, out = run(root, capsys, "back")
    assert code == 1 and rt.calls == [] and WSL_TASK in out and "yes" in out
    assert record_of(root)["tasks"] == [WSL_TASK]


def test_ac8_back_removes_only_the_recorded_tasks_and_uninstalls_nothing(
    tmp_path, capsys, monkeypatch
):
    """REQ-072 AC8: rule 13: one delete per recorded task by name, and no other command."""
    root = project(tmp_path, "")
    before = files_of(root)
    write_record(root, {"tasks": [WSL_TASK]})
    rt = Runtime(monkeypatch)
    code, out = run(root, capsys, "back", "--yes", "--json")
    assert code == 0, out
    assert rt.calls == [["schtasks", "/Delete", "/TN", WSL_TASK, "/F"]]
    table = json.loads(out)
    assert {r["step"]: r["result"] for r in table["steps"]}["tasks"] == "done"
    assert set(table) >= {"steps", "pending", "roles", "builders"}
    assert record_of(root)["tasks"] == []
    assert files_of(root) == before  # no data deleted, no file written
    rt.calls.clear()
    assert run(root, capsys, "back", "--yes")[0] == 0 and rt.calls == []  # a second run: nothing


def test_ac8_a_task_not_removed_stays_recorded(tmp_path, capsys, monkeypatch):
    """REQ-072 AC8: a refused delete is `failed`, names the task and keeps it for the next run."""
    root = project(tmp_path, "")
    write_record(root, {"tasks": [WSL_TASK]})
    Runtime(monkeypatch, code=1)
    code, out = run(root, capsys, "back", "--yes")
    assert code == 1 and "failed" in out and WSL_TASK in out
    assert record_of(root)["tasks"] == [WSL_TASK]


def test_ac8_nothing_recorded_is_nothing_to_undo(tmp_path, capsys, monkeypatch):
    """REQ-072 AC8: no record on this machine: one line, no command, no file."""
    root = project(tmp_path, "")
    rt = Runtime(monkeypatch)
    code, out = run(root, capsys, "back", "--yes")
    assert code == 0 and rt.calls == [] and "nothing to undo" in out
    assert git(root, "branch", "--show-current") == "main"


def test_ac8_an_unreadable_record_is_refused(tmp_path, capsys, monkeypatch):
    """REQ-072 AC8: a record that cannot be read is refused by its setting; nothing removed."""
    root = project(tmp_path, "")
    path = Path(git(root, "rev-parse", "--absolute-git-dir")) / "agk" / "setup.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    rt = Runtime(monkeypatch)
    code, out = run(root, capsys, "back", "--yes")
    assert code == 1 and rt.calls == [] and "setup.json" in out


def proposed_and_merged(root: Path, capsys) -> None:
    extra = ("--yes", "--date", "2026-11-17", "--answer", "where=local", "--answer", "team=solo",
             "--answer", "autopilot=assist")  # fmt: skip
    code, out = run(root, capsys, "settings", *extra)
    assert code == 0, out
    git(root, *WHO, "add", "-A")
    git(root, *WHO, "commit", "-q", "-m", "the settings chosen in setup")
    git(root, "push", "-q", "origin", "HEAD:main")
    git(root, "fetch", "-q", "origin")


def test_ac8_back_prepares_the_reverse_change_with_its_adr(tmp_path, capsys, monkeypatch):
    """REQ-072 AC8: rule 13: the merged settings are reversed on a new branch with an ADR, a key
    setup added is removed and a changed one restored; nothing committed or pushed."""
    root = project(tmp_path, 'review_mode = "team"\n[flow]\nmax_builders = 2\n')
    proposed_and_merged(root, capsys)
    recorded = record_of(root)["settings"]
    assert {"table": None, "key": "review_mode", "value": "solo", "before": "team"} in recorded
    head = git(root, "rev-parse", "HEAD")
    Runtime(monkeypatch)
    code, out = run(root, capsys, "back", "--yes", "--date", "2026-11-18")
    assert code == 0, out
    assert git(root, "branch", "--show-current") == "agk/setup-back-2026-11-18"
    assert git(root, "rev-parse", "HEAD") == head
    config = setup.tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
    assert config["review_mode"] == "team" and "execution" not in config
    assert config["flow"] == {"max_builders": 2}
    assert "autopilot" not in config  # a table setup added goes with its last key
    adr = sorted((root / "docs" / "adr").glob("0003-*.md"))
    assert len(adr) == 1
    text = adr[0].read_text(encoding="utf-8")
    assert "- Status: Proposed" in text and "`agk.toml`" in text and "back" in text
    assert "prepush.py --record" in out and "git push" in out
    assert "uninstalled" in out and not SECRET.search(out)
    assert (root / "notes.txt").read_text(encoding="utf-8") == "the person's own data\n"


def test_ac8_a_setting_changed_since_is_not_reversed(tmp_path, capsys, monkeypatch):
    """REQ-072 AC8: back reverses only what still holds setup's value; none: no branch."""
    root = project(tmp_path, 'review_mode = "team"\n')
    extra = ("--yes", "--date", "2026-11-17", "--answer", "where=local", "--answer", "team=solo")
    assert run(root, capsys, "settings", *extra)[0] == 0
    git(root, "checkout", "-q", "-f", "main")  # the proposal was never merged
    git(root, "clean", "-q", "-fd")
    Runtime(monkeypatch)
    code, out = run(root, capsys, "back", "--yes", "--date", "2026-11-18")
    assert code == 0, out
    assert "nothing to reverse" in out and git(root, "branch", "--show-current") == "main"


def test_ac8_the_steward_hands_a_plain_ask_to_setup():
    """REQ-072 AC8: rules 2 and 17: the steward uses the `setup` skill when asked in plain words to
    set up or to undo, on the person's yes; its table names the skill."""
    text = AGENT.read_text(encoding="utf-8")
    assert "plain words" in text and "the `setup` skill" in text and "undo" in text
    assert "/agk:" not in text  # a law file never names the plugin's command
    assert re.search(r"^\| [^|]*set[^|]* \| `setup` \|$", text, re.M)
    assert steward_evidence.skill_line(ROOT, "setting up a machine") == "skill: `setup`"


def test_ac8_the_skill_names_the_back_form():
    """REQ-072 AC8: the skill's back form asks for the yes and never runs the printed commands."""
    text = SKILL.read_text(encoding="utf-8")
    assert "## /agk:setup back" in text and "setup.py\" back" in text
    part = text.split("## /agk:setup back", 1)[1]
    assert "--yes" in part and "never" in part and "uninstall" in part
