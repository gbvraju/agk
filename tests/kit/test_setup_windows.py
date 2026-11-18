"""/agk:setup build (c): the native Windows path installs each missing tool through winget at its
minimum version and stops before the first install with one line naming what IT must allow
(brief #1462, SPEC-0065 rule 7, ADR-0620; REQ-072 AC4).

A fake machine read, a stub package manager (a recorder of the winget and installer calls) and a
stub version read after each install; no network, no model, no real install. The PowerShell
bootstrap is read as text, without Windows. Invented names of example.com only.
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
_spec = importlib.util.spec_from_file_location("agk_setup_windows", SCRIPTS / "setup.py")
setup = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(setup)

PS1 = SCRIPTS / "setup_windows.ps1"
NOTHING = dict.fromkeys(setup.MINIMUM)  # a Windows machine with nothing installed


def machine(tools=None, **over) -> dict:
    found = {
        "os": "Windows", "os_version": "10.0.22631", "wsl": "absent", "memory_total_gb": 16,
        "memory_available_gb": 12, "cores": 8, "disk_free_gb": 100, "admin": True,
        "tools": dict(NOTHING if tools is None else tools), "winget": "allowed",
        "proxy": "none", "remote": "example-org/example-project",
    }  # fmt: skip
    return found | over


class Stub:
    """The stub package manager: records each call; an install makes its tool read back at the
    minimum version (or at AFTER's version), and FAIL names a tool whose install exits 1."""

    def __init__(self, monkeypatch, fail=None, download=0, after=None):
        self.calls: list[list[str]] = []
        self.installed: dict[str, str] = {}
        self.fail, self.download, self.after = fail, download, after or {}
        monkeypatch.setattr(setup, "run_cmd", self.run)
        monkeypatch.setattr(setup, "installed_version", lambda name: self.installed.get(name))

    def run(self, args, cwd):
        self.calls.append(list(args))
        if args[:2] == ["winget", "show"]:
            return self.download
        tool = setup.tool_of(args)
        if tool is None or tool == self.fail:
            return 1
        self.installed[tool] = self.after.get(tool, setup.MINIMUM[tool] or "1.0")
        return 0

    def installs(self):
        return [c for c in self.calls if c[:2] != ["winget", "show"]]


def project(tmp_path: Path, engines=False) -> Path:
    (tmp_path / "agk.toml").write_text('review_mode = "solo"\n', encoding="utf-8")
    if engines:
        (tmp_path / "compose.yaml").write_text("services: {}\n", encoding="utf-8")
    return tmp_path


def run(tmp_path, capsys, fake, yes=True, engines=False):
    root = project(tmp_path, engines)
    m = tmp_path.parent / "machine.json"
    m.write_text(json.dumps(fake), encoding="utf-8")
    args = ["install", "--machine", str(m), "--github", str(github(tmp_path)), "--root", str(root)]
    code = setup.main([*args, "--json", *(["--yes"] if yes else [])])
    return code, json.loads(capsys.readouterr().out)


def github(tmp_path: Path) -> Path:
    g = tmp_path.parent / "github.json"
    g.write_text(json.dumps({"lease": "free", "running": 0}), encoding="utf-8")
    return g


def test_ac4_the_table_names_every_tool_of_the_brief_with_a_minimum():
    """REQ-072 AC4: rule 7: one table in setup.py; each Windows tool has its winget package."""
    wanted = {"git", "gh", "python", "node", "wt", "pwsh", "gitleaks", "podman"}
    assert wanted <= set(setup.WINGET) and set(setup.WINGET) <= set(setup.MINIMUM)
    assert all(setup.MINIMUM[t] for t in wanted | {"claude"})
    assert setup.MINIMUM["python"] == "3.11" and setup.MINIMUM["node"] == "20"
    assert setup.MINIMUM["gitleaks"] == setup.common.GITLEAKS_PIN
    assert "claude" not in setup.WINGET and setup.CLAUDE_INSTALL[0] == "powershell"


def test_ac4_nothing_installed_gets_one_install_per_missing_tool(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: one install per missing tool at its minimum, checked after, table passes."""
    stub = Stub(monkeypatch)
    code, table = run(tmp_path, capsys, machine(), engines=True)
    installs = stub.installs()
    tools = [setup.tool_of(c) for c in installs]
    assert code == 0 and sorted(tools) == sorted({*setup.WINGET, "claude"} - {"docker"})
    assert len(tools) == len(set(tools))
    for call in installs:
        if call[0] == "winget":
            tool = setup.tool_of(call)
            assert call[:4] == ["winget", "install", "--id", setup.WINGET[tool]]
            assert "--exact" in call and "--source" in call and "--disable-interactivity" in call
    rows = {r["step"]: r for r in table["steps"]}
    assert all(rows[t]["result"] == "done" for t in tools)
    assert all(setup.MINIMUM[t] is None or setup.MINIMUM[t] in rows[t]["note"] for t in tools)
    assert table["pending"] == []


def test_ac4_a_second_run_installs_nothing(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4 (AC1): a set-up machine skips every install."""
    stub = Stub(monkeypatch)
    have = {t: setup.MINIMUM[t] or "1.0" for t in setup.MINIMUM}
    code, table = run(tmp_path, capsys, machine(have), engines=True)
    assert code == 0 and stub.calls == []
    assert {r["result"] for r in table["steps"]} == {"skipped"}


def test_ac4_an_older_tool_is_updated_and_a_newer_one_kept(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: checked before: older than the minimum is installed, newer is left alone."""
    stub = Stub(monkeypatch)
    have = {t: "99.0" for t in setup.MINIMUM} | {"git": "2.30.1"}
    code, _ = run(tmp_path, capsys, machine(have))
    assert code == 0 and [setup.tool_of(c) for c in stub.installs()] == ["git"]


def test_ac4_no_container_engine_without_containers(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: the engine only when the project uses containers (rule 7, stacks)."""
    stub = Stub(monkeypatch)
    run(tmp_path, capsys, machine())
    assert "podman" not in [setup.tool_of(c) for c in stub.installs()]


@pytest.mark.parametrize(
    ("over", "download", "allow"),
    [
        ({"winget": "absent"}, 0, "allow winget"),
        ({"winget": "refused by policy"}, 0, "allow winget"),
        ({"admin": False}, 0, "administrator"),
        ({}, 1, "allow downloads"),
    ],
)
def test_ac4_a_stop_comes_before_the_first_install(
    tmp_path, capsys, monkeypatch, over, download, allow
):
    """REQ-072 AC4: winget missing or refused, no administrator right or a blocked download
    stops before the first install with one line naming what IT must allow."""
    stub = Stub(monkeypatch, download=download)
    code, table = run(tmp_path, capsys, machine(**over))
    assert code == 1 and stub.installs() == []
    stop = table["stop"]
    assert "\n" not in stop and allow in stop and "then run /agk:setup again" in stop
    assert "by hand" in stop and "git" in stop  # the hand route names the tools
    assert all(r["result"] == "waiting" for r in table["steps"] if r["step"] != "stop")


def test_ac4_anything_but_a_yes_installs_nothing(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4 (AC2): rule 5: without the yes the install form refuses and calls nothing."""
    stub = Stub(monkeypatch)
    code, table = run(tmp_path, capsys, machine(), yes=False)
    assert code == 1 and stub.calls == [] and "--yes" in table["stop"]


def test_ac4_a_failure_mid_way_stops_and_leaves_the_rest_untouched(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: a failed step is reported, the tool stays as it was (winget's own
    transaction), and no later install runs."""
    stub = Stub(monkeypatch, fail="gh")
    code, table = run(tmp_path, capsys, machine())
    tools = [setup.tool_of(c) for c in stub.installs()]
    assert code == 1 and tools[-1] == "gh" and "gh" not in stub.installed
    rows = {r["step"]: r for r in table["steps"]}
    assert rows["gh"]["result"] == "failed" and "as it was" in rows["gh"]["note"]
    later = [t for t in setup.install_order(machine()["tools"], False) if t not in tools]
    assert later and all(rows[t]["result"] == "waiting" for t in later)


def test_ac4_an_install_below_the_minimum_after_is_failed(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: checked after: a version still below the minimum is not done."""
    Stub(monkeypatch, after={"git": "2.1.0"})
    code, table = run(tmp_path, capsys, machine())
    rows = {r["step"]: r for r in table["steps"]}
    assert code == 1 and rows["git"]["result"] == "failed"


def test_ac4_only_native_windows_takes_this_path(tmp_path, capsys, monkeypatch):
    """REQ-072 AC4: a platform with no path of its own (Linux has build (e)'s, macOS its line) is
    refused by name and nothing is called."""
    stub = Stub(monkeypatch)
    code, table = run(tmp_path, capsys, machine(os="FreeBSD"))
    assert code == 1 and stub.calls == [] and "native Windows" in table["stop"]


def test_ac4_no_output_holds_a_proxy_or_a_credential(tmp_path, capsys, monkeypatch):
    """REQ-072 AC5: the proxy is `configured`, never its address; no token-shaped value."""
    Stub(monkeypatch, download=1)
    _, table = run(tmp_path, capsys, machine(proxy="configured"))
    text = json.dumps(table)
    assert "://" not in text.replace("https://claude.ai", "")
    assert not re.search(r"(gh[pousr]_|github_pat_)[A-Za-z0-9_]{8,}", text)


def ps1() -> str:
    return PS1.read_text(encoding="utf-8")


def test_ac4_the_bootstrap_reads_the_table_from_setup_py():
    """REQ-072 AC4: rule 7: the PowerShell bootstrap holds no version or package of its own."""
    text = ps1()
    assert text.isascii() and "setup.py" in text and "MINIMUM" in text and "WINGET" in text
    assert not re.search(r"\b3\.11\b|Python\.Python\.\d", text)
    line = re.search(r'"python":\s*"([^"]+)"', setup.Path(SCRIPTS / "setup.py").read_text())
    assert line and line[1] == setup.MINIMUM["python"]  # the shape the bootstrap's regex reads


def test_ac4_the_bootstrap_stops_before_its_first_install():
    """REQ-072 AC4: winget, its policy, the administrator right and the test download are read
    before the bootstrap's one install; each stop names what to allow."""
    text = ps1()
    first = text.index("winget install")
    for check in ("Get-Command winget", "EnableAppInstaller", "IsInRole", "winget show"):
        assert -1 < text.index(check) < first, check
    assert "then run /agk:setup again" in text and text.count(", $Hand\"") >= 4
    assert re.search(r"setup\.py.{0,40}\binstall\b", text)
    assert not re.search(r"-Force\b|Set-ExecutionPolicy|Remove-Item", text)


def test_ac4_the_bootstrap_is_kit_only_and_mapped():
    """REQ-072 AC4: kit-only, named in the kit-only list, with its testing map entry."""
    manifest = (ROOT / "tests" / "kit_dev" / "test_kit_manifest.py").read_text(encoding="utf-8")
    assert '"scripts/agk/setup_windows.ps1"' in manifest
    toml = (ROOT / "agk.toml").read_text(encoding="utf-8")
    assert re.search(r'code = "scripts/agk/setup_windows\.ps1"\ntests = \[[^\]]*test_setup_windows',
                     toml)  # fmt: skip


WINGET_LIST = """Name                Id        Version   Available Source
----------------------------------------------------------
Git                 Git.Git   2.40.0    2.55.0    winget
"""


def test_ac4_the_after_check_reads_winget_list(monkeypatch):
    """REQ-072 AC4: the installed version, not the available one, from a recorded `winget list`."""
    seen: list[list[str]] = []
    monkeypatch.setattr(setup, "capture", lambda args, cwd=None: seen.append(args) or WINGET_LIST)
    assert setup.installed_version("git") == "2.40.0"
    assert seen[0][:4] == ["winget", "list", "--id", "Git.Git"]
    monkeypatch.setattr(setup, "capture", lambda args, cwd=None: "No installed package found.\n")
    assert setup.installed_version("git") is None


def test_ac4_claude_is_read_on_the_path_an_install_leaves(tmp_path, monkeypatch):
    """REQ-072 AC4: Claude Code's after-check reads the machine's and the user's PATH again,
    not this process's, which an install does not refresh."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    tool = bin_dir / "claude"
    tool.write_text("#!/bin/sh\necho '2.1.5 (Claude Code)'\n", encoding="utf-8")
    tool.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(setup, "fresh_path", lambda: str(bin_dir))
    assert setup.installed_version("claude") == "2.1.5"


@pytest.mark.parametrize(
    ("listed", "installs"), [("1.20.1", True), ("1.24.3", False), (None, True)]
)
def test_ac4_a_tool_read_only_as_present_is_read_through_winget(
    tmp_path, capsys, monkeypatch, listed, installs
):
    """REQ-072 AC4: a tool with a floor whose version was not read is read through winget's list;
    below the floor, or still unread, it is installed."""
    stub = Stub(monkeypatch)
    stub.installed["wt"] = listed
    have = {t: setup.MINIMUM[t] or "1.0" for t in setup.MINIMUM} | {"wt": "present"}
    run(tmp_path, capsys, machine(have))
    assert ("wt" in [setup.tool_of(c) for c in stub.installs()]) is installs


def test_ac4_the_bootstrap_passes_the_projects_folder():
    """REQ-072 AC4: the project's folder, not the plugin's, decides the container engine."""
    assert re.search(r"'install', '--root', \$Root", ps1())
