"""/agk:setup build (e): Linux and cloud virtual machines install each missing tool through apt or
dnf, and Node.js, gitleaks and Claude Code by the path `wsl_setup.ps1`'s embedded steps use, at the
minimum versions of the one table; macOS prints one line and changes nothing (brief #1464,
SPEC-0065 rule 7, ADR-0622; REQ-072 AC4).

A fake machine read, a stub package manager (a recorder of the apt, dnf and step calls) and a stub
version read after each install; no network, no model, no real install. The bash bootstrap is read
as text. Invented names of example.com only.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess  # nosec B404 - bash -n only, on the kit's own file
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location("agk_setup_linux", SCRIPTS / "setup.py")
setup = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(setup)

SH = SCRIPTS / "setup_linux.sh"
NOTHING = dict.fromkeys(setup.MINIMUM) | {"python": "3.12.3"}  # setup.py runs: Python is there
LINUX_TOOLS = {"git", "gh", "node", "gitleaks", "claude"}


def machine(tools=None, **over) -> dict:
    found = {
        "os": "Linux", "os_version": "6.8.0", "wsl": "absent", "memory_total_gb": 16,
        "memory_available_gb": 12, "cores": 8, "disk_free_gb": 100, "admin": True,
        "tools": dict(NOTHING if tools is None else tools), "winget": "absent",
        "package_manager": "apt", "sudo": True, "proxy": "none",
        "remote": "example-org/example-project",
    }  # fmt: skip
    return found | over


class Stub:
    """The stub package manager: records each call; an install makes its tool read back at the
    minimum version (or AFTER's), FAIL names a tool whose install exits 1, and REFRESH is the exit
    of the package lists' test download."""

    def __init__(self, monkeypatch, fail=None, refresh=0, after=None):
        self.calls: list[list[str]] = []
        self.installed: dict[str, str] = {}
        self.fail, self.refresh, self.after = fail, refresh, after or {}
        monkeypatch.setattr(setup, "run_cmd", self.run)
        monkeypatch.setattr(setup, "linux_version", lambda name: self.installed.get(name))

    def run(self, args, cwd):
        self.calls.append(list(args))
        if setup.is_refresh(args):
            return self.refresh
        tool = setup.linux_tool_of(args)
        if tool is None or tool == self.fail:
            return 1
        self.installed[tool] = self.after.get(tool, setup.MINIMUM[tool] or "1.0")
        return 0

    def installs(self):
        return [c for c in self.calls if not setup.is_refresh(c)]


def run(tmp_path, capsys, fake, yes=True, engines=False, as_json=True):
    root = tmp_path / "project"
    root.mkdir(exist_ok=True)
    (root / "agk.toml").write_text('review_mode = "solo"\n', encoding="utf-8")
    if engines:
        (root / "compose.yaml").write_text("services: {}\n", encoding="utf-8")
    m, g = tmp_path / "machine.json", tmp_path / "github.json"
    m.write_text(json.dumps(fake), encoding="utf-8")
    g.write_text(json.dumps({"lease": "free", "running": 0}), encoding="utf-8")
    args = ["install", "--machine", str(m), "--github", str(g), "--root", str(root)]
    code = setup.main([*args, *(["--json"] if as_json else []), *(["--yes"] if yes else [])])
    out = capsys.readouterr().out
    return code, (json.loads(out) if as_json else out)


def test_ac4_the_linux_table_reads_the_one_minimum_table():
    """REQ-072 AC4: rule 7: every Linux tool has a minimum in the one table; apt and dnf each
    name a package for the distribution's tools; no version is held twice."""
    assert set(setup.LINUX_PACKAGES) == {"apt", "dnf"}
    for packages in setup.LINUX_PACKAGES.values():
        assert {"git", "gh", "podman"} == set(packages)
    assert all(setup.MINIMUM[t] for t in LINUX_TOOLS | {"podman"})
    assert set(setup.NODE_SETUP) == {"apt", "dnf"}
    urls = setup.NODE_SETUP.values()
    assert all(u.startswith("https://") and "nodesource.com" in u for u in urls)
    assert setup.CLAUDE_LINUX == "https://claude.ai/install.sh"
    ps1 = (SCRIPTS / "wsl_setup.ps1").read_text(encoding="utf-8")
    assert setup.CLAUDE_LINUX in ps1 and setup.NODE_SETUP["apt"] in ps1  # the same path


@pytest.mark.parametrize("manager", ["apt", "dnf"])
def test_ac4_nothing_installed_gets_one_install_per_missing_tool(
    tmp_path, capsys, monkeypatch, manager
):
    """REQ-072 AC4: on apt and on dnf, one install per missing tool, checked after; it passes."""
    stub = Stub(monkeypatch)
    code, table = run(tmp_path, capsys, machine(package_manager=manager), engines=True)
    tools = [setup.linux_tool_of(c) for c in stub.installs()]
    assert code == 0 and sorted(tools) == sorted(LINUX_TOOLS | {"podman"})
    assert len(tools) == len(set(tools))
    for call in stub.installs():
        tool = setup.linux_tool_of(call)
        if tool in setup.LINUX_PACKAGES[manager]:
            assert call[-1] == setup.LINUX_PACKAGES[manager][tool] and "-y" in call
            assert (manager == "apt") == ("apt-get" in call)
            assert (manager == "dnf") == ("dnf" in call)
        else:
            assert call[:2] == ["bash", str(SH)]
    node = next(c for c in stub.installs() if setup.linux_tool_of(c) == "node")
    assert node[2:] == ["node", manager, setup.NODE_SETUP[manager]]
    gitleaks = next(c for c in stub.installs() if setup.linux_tool_of(c) == "gitleaks")
    assert gitleaks[2:] == ["gitleaks", setup.common.GITLEAKS_PIN]
    rows = {r["step"]: r for r in table["steps"]}
    assert all(rows[t]["result"] == "done" and setup.MINIMUM[t] in rows[t]["note"] for t in tools)
    assert rows["python"]["result"] == "skipped" and table["pending"] == []


def test_ac4_without_root_the_package_installs_go_through_sudo(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: an account that is not root installs through sudo, which asks its own."""
    stub = Stub(monkeypatch)
    code, _ = run(tmp_path, capsys, machine(admin=False))
    packages = [c for c in stub.installs() if c[0] == "sudo"]
    assert code == 0 and packages and all(c[1] == "apt-get" for c in packages)


def test_ac4_a_second_run_installs_nothing(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4 (AC1): a set-up machine skips every install and downloads nothing."""
    stub = Stub(monkeypatch)
    have = {t: setup.MINIMUM[t] for t in LINUX_TOOLS} | {"python": "3.12.3"}
    code, table = run(tmp_path, capsys, machine(tools=have))
    assert code == 0 and stub.calls == []
    assert all(r["result"] == "skipped" for r in table["steps"])


def test_ac4_docker_present_means_no_podman(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: the engine is installed only when the project uses containers and none is."""
    stub = Stub(monkeypatch)
    have = {t: setup.MINIMUM[t] for t in LINUX_TOOLS} | {"python": "3.12.3", "docker": "27.1.0"}
    code, _ = run(tmp_path, capsys, machine(tools=have), engines=True)
    assert code == 0 and stub.calls == []
    (tmp_path / "project" / "compose.yaml").unlink()
    run(tmp_path, capsys, machine(tools={**have, "docker": None}))  # no containers: no engine
    assert stub.calls == []


def test_ac4_without_a_yes_nothing_installs(tmp_path, capsys, monkeypatch):
    """REQ-072 AC2 and AC4: anything but a yes installs nothing and downloads nothing."""
    stub = Stub(monkeypatch)
    code, table = run(tmp_path, capsys, machine(), yes=False)
    assert code == 1 and stub.calls == [] and "--yes" in table["stop"]
    assert {"git", "gh", "node", "gitleaks", "claude"} <= set(table["pending"])


@pytest.mark.parametrize(
    ("over", "refresh", "allow"),
    [
        ({"package_manager": "absent"}, 0, "apt or dnf"),
        ({"admin": False, "sudo": False}, 0, "sudo"),
        ({}, 100, "the distribution's package mirrors"),
    ],
)
def test_ac4_a_stop_names_what_to_allow_before_the_first_install(
    tmp_path, capsys, monkeypatch, over, refresh, allow
):
    """REQ-072 AC4: no apt or dnf, no root nor sudo, or a refused test download stops before the
    first install with one line naming what to allow and the tools to install by hand."""
    stub = Stub(monkeypatch, refresh=refresh)
    code, out = run(tmp_path, capsys, machine(**over), as_json=False)
    stops = [ln for ln in out.splitlines() if ln.startswith("stop:")]
    assert code == 1 and len(stops) == 1 and allow in stops[0] and "by hand" in stops[0]
    assert stub.installs() == []


def test_ac4_a_failed_install_stops_and_runs_nothing_after(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: a failed install is `failed`, left as it was, and nothing after it runs."""
    stub = Stub(monkeypatch, fail="gh")
    code, table = run(tmp_path, capsys, machine())
    rows = {r["step"]: r for r in table["steps"]}
    assert code == 1 and rows["gh"]["result"] == "failed" and "as it was" in rows["gh"]["note"]
    assert [setup.linux_tool_of(c) for c in stub.installs()] == ["git", "gh"]
    assert rows["node"]["result"] == "waiting" and "gh" in table["stop"]


def test_ac4_a_version_below_the_minimum_after_its_install_fails(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: an older distribution's package that reads below the floor is `failed`."""
    Stub(monkeypatch, after={"git": "2.39.5"})
    code, table = run(tmp_path, capsys, machine())
    rows = {r["step"]: r for r in table["steps"]}
    assert code == 1 and rows["git"]["result"] == "failed" and "2.39.5" in rows["git"]["note"]


def test_ac4_macos_prints_one_line_and_changes_nothing(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: macOS is not covered in the first release (Q-S0065-3): one line, no call."""
    stub = Stub(monkeypatch)
    code, out = run(tmp_path, capsys, machine(os="Darwin"), as_json=False)
    assert code == 1 and out.strip() == setup.MAC_LINE and stub.calls == []
    assert not list((tmp_path / "project").glob(".git*"))
    assert setup.MAC_LINE in SH.read_text(encoding="utf-8")


def test_ac4_the_local_linux_plan_proposes_the_background_adapter():
    """REQ-072 AC5 (rule 10): local mode on Linux proposes `bash scripts/start-session-local.sh`."""
    config = {"execution": "local", "review_mode": "solo"}
    builders = {"figure": 1, "per_builder_gb": 3}
    found = setup.proposals(config, {}, builders, machine())
    assert ("flow", "launch_adapter", "bash scripts/start-session-local.sh") in found


def test_ac4_the_bootstrap_holds_no_version_or_url_of_its_own():
    """REQ-072 AC4: setup_linux.sh reads Python's floor from setup.py's table, takes each URL and
    version from setup.py's call, stops before its one install, and never reads a secret."""
    text = SH.read_text(encoding="utf-8")
    assert subprocess.run(["bash", "-n", str(SH)], check=False).returncode == 0  # nosec B603 B607 - bash -n of the kit file
    assert "MINIMUM" in text and "setup.py" in text and 'REST=(install --root' in text
    assert not re.search(r"\b\d+\.\d+\.\d+\b", text)  # no version of its own
    assert "nodesource" not in text and "claude.ai" not in text  # setup.py names each URL
    assert "sha256sum" in text  # gitleaks is checked against its published checksum file
    assert not re.search(r"(?i)password|token|read -s", text)


def test_ac4_the_bootstrap_on_macos_prints_the_one_line(tmp_path):
    """REQ-072 AC4: the bash bootstrap run on a stub macOS (`uname -s` says Darwin) prints
    setup.py's line and exits 1 before any install; the stub folder is all it touches."""
    stubs = tmp_path / "bin"
    stubs.mkdir()
    (stubs / "uname").write_text("#!/bin/sh\necho Darwin\n", encoding="utf-8")
    (stubs / "uname").chmod(0o755)
    env = {"PATH": f"{stubs}:/usr/bin:/bin", "HOME": str(tmp_path)}
    done = subprocess.run(  # nosec B603 B607 - the kit's own script, fixed arguments
        ["bash", str(SH), "--yes"], cwd=tmp_path, env=env, capture_output=True, text=True,
        check=False, timeout=30,
    )  # fmt: skip
    assert done.returncode == 1 and done.stdout.strip() == setup.MAC_LINE
    assert sorted(p.name for p in tmp_path.iterdir()) == ["bin"]


def test_ac4_sudo_counts_only_when_it_runs_without_a_prompt(monkeypatch):
    """REQ-072 AC4: the machine read probes `sudo -n true`; sudo present but refused, or asking
    for its sign-in with no terminal, reads as not ready."""
    calls = []
    monkeypatch.setattr(setup.shutil, "which", lambda name, path=None: f"/usr/bin/{name}")
    monkeypatch.setattr(setup, "capture", lambda args, cwd=None: calls.append(args))
    assert setup.sudo_ready() is False and calls == [["sudo", "-n", "true"]]
    monkeypatch.setattr(setup, "capture", lambda args, cwd=None: "")
    assert setup.sudo_ready() is True


def test_ac4_sudo_not_ready_stops_naming_sudo(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: an account with sudo that cannot use it here stops naming sudo, not the
    package mirrors, and nothing is downloaded."""
    stub = Stub(monkeypatch)
    code, out = run(tmp_path, capsys, machine(admin=False, sudo=False), as_json=False)
    assert code == 1 and "sudo -v" in out and "mirrors" not in out and stub.calls == []


def test_ac4_claude_code_alone_needs_no_root_and_no_refresh(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: a machine that lacks only Claude Code (a user install) is not stopped for
    sudo or apt, and refreshes no package list."""
    stub = Stub(monkeypatch)
    have = {t: setup.MINIMUM[t] for t in LINUX_TOOLS - {"claude"}} | {"python": "3.12.3"}
    fake = machine(tools=have, admin=False, sudo=False, package_manager="absent")
    code, table = run(tmp_path, capsys, fake)
    assert code == 0 and [setup.linux_tool_of(c) for c in stub.calls] == ["claude"]
    assert stub.calls[0] == ["bash", str(SH), "claude", setup.CLAUDE_LINUX]


def test_ac4_a_failed_node_install_says_its_package_source_stays(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: NodeSource's script adds a package source before `nodejs`; when `nodejs`
    fails the row says that source stays (ADR-0622's residual)."""
    Stub(monkeypatch, fail="node")
    code, table = run(tmp_path, capsys, machine())
    rows = {r["step"]: r for r in table["steps"]}
    assert code == 1 and rows["node"]["result"] == "failed"
    assert "NodeSource's package source it added stays" in rows["node"]["note"]


def test_ac4_linux_version_reads_a_stub_tool(tmp_path, monkeypatch):
    """REQ-072 AC4: the after-check reads each tool's real output: `gitleaks version`, else
    `--version`; a tool nowhere on the PATH or the installers' folders is None."""
    stubs = tmp_path / "bin"
    stubs.mkdir()
    for name, text in (("gitleaks", '[ "$1" = version ] && echo 8.30.1'),
                       ("git", '[ "$1" = --version ] && echo "git version 2.43.0"')):  # fmt: skip
        (stubs / name).write_text(f"#!/bin/sh\n{text}\n", encoding="utf-8")
        (stubs / name).chmod(0o755)
    monkeypatch.setenv("PATH", str(stubs))
    monkeypatch.setenv("HOME", str(tmp_path))
    assert setup.linux_version("gitleaks") == "8.30.1"
    assert setup.linux_version("git") == "2.43.0"
    assert setup.linux_version("example-tool-absent") is None


def bootstrap(tmp_path: Path, *flags: str):
    """setup_linux.sh on a stub machine: uid 1000, apt-get, sudo and a Python too old, no curl;
    each stub call is logged."""
    stubs, log = tmp_path / "bin", tmp_path / "calls.log"
    stubs.mkdir(exist_ok=True)
    for real in ("awk", "sed", "dirname", "uname"):
        target = stubs / real
        if not target.exists():
            target.symlink_to(shutil.which(real))
    fakes = {
        "id": "echo 1000",
        "apt-get": f'echo "apt-get $*" >> "{log}"',
        "sudo": f'echo "sudo $*" >> "{log}"; [ "$1" = -n ] && exit 0; "$@"',
        "python3": f'echo "python3 $*" >> "{log}"; exit 1',
    }
    for name, body in fakes.items():
        (stubs / name).write_text(f"#!/bin/bash\n{body}\n", encoding="utf-8")
        (stubs / name).chmod(0o755)
    env = {"PATH": str(stubs), "HOME": str(tmp_path)}
    done = subprocess.run(  # nosec B603 - the kit's own script, fixed arguments
        ["/bin/bash", str(SH), *flags], cwd=tmp_path, env=env, capture_output=True, text=True,
        check=False, timeout=30,
    )  # fmt: skip
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return done, [c for c in calls if not c.startswith("python3")]


def test_ac4_the_bootstrap_installs_nothing_without_a_yes(tmp_path):
    """REQ-072 AC2 and AC4: a bare machine without --yes gets one stop line and no apt call."""
    done, calls = bootstrap(tmp_path)
    assert done.returncode == 1 and "--yes" in done.stdout
    assert not [c for c in calls if "apt-get" in c]


def test_ac4_the_bootstrap_refreshes_then_installs_python_and_curl_on_a_yes(tmp_path):
    """REQ-072 AC4: on a yes, the package lists' refresh, then one install of Python and curl
    through sudo; a Python still below the table's floor stops with one line naming it."""
    done, calls = bootstrap(tmp_path, "--yes")
    apt = [c for c in calls if c.startswith("apt-get")]
    assert apt == ["apt-get update -q", "apt-get install -y -q python3 curl ca-certificates"]
    assert "sudo apt-get update -q" in calls
    stops = [ln for ln in done.stdout.splitlines() if ln.startswith("stop:")]
    assert done.returncode == 1 and len(stops) == 1 and setup.MINIMUM["python"] in stops[0]
