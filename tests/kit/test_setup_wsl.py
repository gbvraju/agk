"""/agk:setup build (d): on Windows with WSL 2 chosen, the setup calls `/agk:wsl`'s script and
helper unchanged, then the scheduler through that script's own watchdog step, so one command and
one yes set up the WSL workforce (brief #1463, SPEC-0065 rules 7 and 17, ADR-0621; REQ-072 AC4
and AC8).

A fake machine read, saved GitHub answers and a stub runtime that records every command and answers
`wsl_setup.ps1 -Json` and `wsl.py` as they print; no Windows, no WSL, no network, no model. Invented
names of example.com only.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location("agk_setup_wsl", SCRIPTS / "setup.py")
setup = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(setup)

PS1 = str(SCRIPTS / "wsl_setup.ps1")
HELPER = str(SCRIPTS / "wsl.py")
MACHINE_STEPS = ("wsl", "distro", "packages", "gh_cli", "nodejs", "podman", "github_signin",
                 "clone", "claude_signin", "terminal")  # fmt: skip
ON = "watchdog: the WSL task on, the Windows task disabled (never deleted)"
LATER = "watchdog: moved on the next /agk:wsl after that pull request merges"
TOKEN = re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_|password\s*[:=]", re.I)


class Runtime:
    """The stub runtime: `wsl_setup.ps1` answers its `-Json` table, each step `skipped` once a
    setup pass made it `done` (FAIL names a step that fails, SIGNIN leaves the sign-ins waiting);
    `wsl.py plan` prints WATCHDOG as its watchdog line. Every call is kept."""

    def __init__(self, monkeypatch, watchdog=ON, fail=None, signin=False, code=0):
        self.calls: list[list[str]] = []
        self.made: set[str] = set()
        self.watchdog, self.fail, self.signin, self.code = watchdog, fail, signin, code
        monkeypatch.setattr(setup, "run_out", self.run)

    def run(self, args, cwd):
        self.calls.append(list(args))
        if args[:3] == ["pwsh", "-NoProfile", "-File"]:
            return self.ps1(args)
        if args[1:2] == [HELPER]:
            if args[2] == "plan":
                return 0, f"machine: WSL 2 with Ubuntu-24.04\nadapter: WSL\n{self.watchdog}\n"
            return 0, "wsl: on\nwatchdog: the WSL task\n"
        return 1, ""

    def ps1(self, args):
        if self.code:
            return self.code, ""
        check = "-Status" in args
        steps = []
        names = (*MACHINE_STEPS, *(["watchdog"] if "-InstallWatchdog" in args else []))
        for name in names:
            if name == self.fail and not check:
                steps.append({"step": name, "result": "failed", "note": "apt-get failed"})
                break
            if self.signin and name.endswith("_signin"):
                steps.append({"step": name, "result": "waiting", "note": "sign in in your browser"})
            elif name in self.made:
                steps.append({"step": name, "result": "skipped", "note": ""})
            elif check:
                steps.append({"step": name, "result": "waiting", "note": "to set up"})
            else:
                self.made.add(name)
                steps.append({"step": name, "result": "done", "note": "set up"})
        pending = [f"{s['step']}: {s['note']}" for s in steps if s["result"] == "waiting"]
        state = {"steps": steps, "pending": pending, "distro": "Ubuntu-24.04", "engine": "podman"}
        return 0, json.dumps(state)

    def passes(self):
        return [c for c in self.calls if c[:3] == ["pwsh", "-NoProfile", "-File"]]


def machine(**over) -> dict:
    found = {
        "os": "Windows", "os_version": "10.0.22631", "wsl": "present", "memory_total_gb": 16,
        "memory_available_gb": 12, "cores": 8, "disk_free_gb": 100, "admin": True,
        "tools": dict.fromkeys(setup.MINIMUM) | {"python": "3.13.1"}, "winget": "allowed",
        "proxy": "configured", "remote": "example-org/example-project",
    }  # fmt: skip
    return found | over


LOCAL = 'review_mode = "solo"\nexecution = "local"\n'


def run(tmp_path, capsys, fake=None, yes=True, answers=("windows=wsl",), toml=LOCAL):
    root = tmp_path / "project"
    root.mkdir(exist_ok=True)
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    m, g = tmp_path / "machine.json", tmp_path / "github.json"
    m.write_text(json.dumps(fake or machine()), encoding="utf-8")
    g.write_text(json.dumps({"lease": "free", "running": 0}), encoding="utf-8")
    args = ["wsl", "--machine", str(m), "--github", str(g), "--root", str(root), "--json"]
    args += [f"--answer={a}" for a in answers] + (["--yes"] if yes else [])
    code = setup.main(args)
    out = capsys.readouterr().out
    return code, json.loads(out), out


def test_ac8_the_wsl_path_runs_the_wsl_script_and_helper_unchanged(tmp_path, capsys, monkeypatch):
    """REQ-072 AC8: rule 17: wsl_setup.ps1 and wsl.py are called from the plugin, never copied."""
    rt = Runtime(monkeypatch)
    code, table, _ = run(tmp_path, capsys)
    assert code == 0
    assert all(c[3] == PS1 and c[-1] == "-Json" for c in rt.passes())
    helpers = [c for c in rt.calls if c not in rt.passes()]
    assert helpers and all(c[:2] == [sys.executable, HELPER] for c in helpers)
    assert {c[2] for c in helpers} == {"plan", "status"}
    source = (SCRIPTS / "setup.py").read_text(encoding="utf-8")
    assert "Set-WslWatchdog" not in source and "AGK_STEP=" not in source  # nothing of it copied
    copies = [p for p in SCRIPTS.iterdir() if p.is_file() and p.name != "wsl_setup.ps1"
              and "function Set-WslWatchdog" in p.read_text(encoding="utf-8", errors="ignore")]
    assert copies == []


def test_ac4_one_yes_sets_up_a_machine_with_nothing_installed(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: a check pass, then one setup pass after the yes; the final table passes."""
    rt = Runtime(monkeypatch)
    code, table, _ = run(tmp_path, capsys)
    assert code == 0 and table["stop"] is None and table["pending"] == []
    assert [("-Status" in c) for c in rt.passes()] == [True, False]
    results = {r["step"]: r["result"] for r in table["steps"]}
    assert set(results.values()) == {"done"} and set(MACHINE_STEPS) <= set(results)
    assert table["plan"][-1] == ON and table["status"]


def test_ac4_podman_is_the_engine_unless_the_person_chose_docker(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: Podman by default (ADR-0579); the engine answer of rule 4 decides otherwise."""
    rt = Runtime(monkeypatch)
    run(tmp_path, capsys)
    assert all(c[c.index("-Engine") + 1] == "podman" for c in rt.passes())
    rt.calls.clear()
    run(tmp_path, capsys, answers=("windows=wsl", "engine=docker"))
    assert all(c[c.index("-Engine") + 1] == "docker" for c in rt.passes())


def test_ac4_anything_but_a_yes_sets_up_nothing(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: without the yes only the check pass runs; nothing is set up."""
    rt = Runtime(monkeypatch)
    code, table, _ = run(tmp_path, capsys, yes=False)
    assert code == 1 and "--yes" in table["stop"]
    assert len(rt.passes()) == 1 and "-Status" in rt.passes()[0]
    assert "-InstallWatchdog" not in rt.passes()[0] and rt.made == set()


def test_ac4_a_second_run_changes_nothing(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: rule 2: a second run reports every step skipped."""
    Runtime(monkeypatch)
    run(tmp_path, capsys)
    code, table, _ = run(tmp_path, capsys)
    assert code == 0 and {r["result"] for r in table["steps"]} == {"skipped"}


def test_ac4_a_failed_step_stops_and_the_next_run_resumes(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: a failure stops with one line; the next run skips what was done."""
    rt = Runtime(monkeypatch, fail="nodejs")
    code, table, _ = run(tmp_path, capsys)
    assert code == 1 and table["stop"].startswith("stop: nodejs") and "nodejs" in table["pending"]
    assert "podman" not in {r["step"] for r in table["steps"]}
    rt.fail = None
    code, table, _ = run(tmp_path, capsys)
    results = {r["step"]: r["result"] for r in table["steps"]}
    assert code == 0 and results["packages"] == "skipped" and results["nodejs"] == "done"


def test_ac4_sign_ins_wait_with_their_line_and_pass(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: rule 11: a sign-in that needs the person is `waiting` with its line."""
    Runtime(monkeypatch, signin=True)
    code, table, _ = run(tmp_path, capsys)
    assert code == 0 and table["stop"] is None
    assert table["pending"] == ["github_signin", "claude_signin"]
    assert all(r["note"] for r in table["steps"] if r["result"] == "waiting")


def test_ac8_the_scheduler_is_the_wsl_scripts_one_task(tmp_path, capsys, monkeypatch):
    """REQ-072 AC8: brief answer 1: after the adapter change merged, the one setup pass carries
    `-InstallWatchdog` (`autopilot.py on` inside WSL when `[autopilot]` is set), no second task."""
    rt = Runtime(monkeypatch, watchdog=ON)
    code, table, _ = run(tmp_path, capsys)
    assert code == 0 and ["-InstallWatchdog" in c for c in rt.passes()] == [False, True]
    assert {r["step"]: r["result"] for r in table["steps"]}["watchdog"] == "done"
    said = " ".join(" ".join(c) for c in rt.calls)
    assert "autopilot.py" not in said and "conductor.py" not in said and "schtasks" not in said


def test_ac8_no_scheduler_before_the_adapter_change_merges(tmp_path, capsys, monkeypatch):
    """REQ-072 AC8: the adapter not yet merged: no task; the row waits with /agk:wsl's own line."""
    rt = Runtime(monkeypatch, watchdog=LATER)
    code, table, _ = run(tmp_path, capsys)
    assert code == 0 and not any("-InstallWatchdog" in c for c in rt.passes())
    found = {r["step"]: r for r in table["steps"]}["scheduler"]
    assert found["result"] == "waiting" and "merges" in found["note"]


def test_ac8_personal_mode_adds_no_scheduler(tmp_path, capsys, monkeypatch):
    """REQ-072 AC8: rule 16: for me only, the same installs and no scheduler task."""
    rt = Runtime(monkeypatch, watchdog=ON)
    code, table, _ = run(tmp_path, capsys, answers=("windows=wsl", "where=personal"))
    assert code == 0 and not any("-InstallWatchdog" in c for c in rt.passes())
    assert {r["step"]: r["result"] for r in table["steps"]}["scheduler"] == "skipped"


@pytest.mark.parametrize(
    ("fake", "answers", "toml", "said"),
    [
        (machine(os="Linux"), ("windows=wsl",), LOCAL, "the platform"),
        (machine(), ("windows=native",), LOCAL, "windows"),
        (machine(), ("windows=wsl", "where=hosted"), LOCAL, "execution"),
        (machine(), ("windows=wsl",), 'review_mode = "solo"\n', "execution"),  # hosted by default
    ],
)
def test_ac4_only_windows_with_wsl_chosen_takes_this_path(
    tmp_path, capsys, monkeypatch, fake, answers, toml, said
):
    """REQ-072 AC4: another platform, Windows itself or CI mode is refused naming its setting,
    and nothing is called."""
    rt = Runtime(monkeypatch)
    code, table, _ = run(tmp_path, capsys, fake=fake, answers=answers, toml=toml)
    assert code == 1 and f"(setting: {said})" in table["stop"] and rt.calls == []


def test_ac4_a_script_that_gives_no_table_stops_with_one_line(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: PowerShell 7 missing or the script failing stops before any setup pass."""
    rt = Runtime(monkeypatch, code=127)
    code, table, _ = run(tmp_path, capsys)
    assert code == 1 and "wsl_setup.ps1" in table["stop"] and len(rt.passes()) == 1


def test_ac4_no_output_holds_a_proxy_or_a_credential(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: a configured proxy and the sign-ins leave no credential in the output."""
    monkeypatch.setenv("HTTPS_PROXY", "http://user-example:pw-example@proxy.example.com:8080")
    Runtime(monkeypatch, signin=True)
    _, _, out = run(tmp_path, capsys)
    assert "pw-example" not in out and "proxy.example.com" not in out and not TOKEN.search(out)


def test_ac8_the_skill_names_the_wsl_form():
    """REQ-072 AC8: the skill runs the WSL form after the yes, when WSL 2 was chosen."""
    text = (ROOT / "skills" / "setup" / "SKILL.md").read_text(encoding="utf-8")
    assert "setup.py\" wsl --yes" in text and "windows=wsl" in text
