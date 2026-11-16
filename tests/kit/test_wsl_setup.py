"""One command, /agk:wsl, moves a Windows machine's workforce into WSL 2 and back (brief #1376,
ADR-0577; REQ-050).

Answer 6: `scripts/agk/wsl_setup.ps1` is read as text, without Windows: it is ASCII, its embedded
Linux scripts pass `bash -n`, it never handles a token or password, every step has its skip check,
and its `-Json` table carries the keys `wsl.py` reads; when `pwsh` is on the runner it is parsed by
PowerShell's parser too. The skill's plan, the adapter pull request and the status lines of
`scripts/agk/wsl.py` run against a recorded `gh` double. Answer 5: the doctor's WSL lines, with the
platform and the paths simulated. Invented names of example.com; no network, no model.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import conductor  # noqa: E402
import doctor  # noqa: E402
import wsl  # noqa: E402

PS1 = SCRIPTS / "wsl_setup.ps1"
SKILL = ROOT / "skills" / "wsl" / "SKILL.md"
REPO = "example-org/example-project"
WINDOWS = 'launch_adapter = "pwsh -NoProfile -File scripts/start-session-windows.ps1"'
LOCAL = 'launch_adapter = "bash scripts/start-session-local.sh"'

FAKE = r"""#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ["FAKE_GH_CALLS"], "a", encoding="utf-8") as f:
    f.write(json.dumps(args) + "\n")
if args[:1] == ["api"] and any(a.startswith("repos/") and "/contents/agk.toml" in a for a in args):
    sys.stdout.write(open(os.environ["FAKE_GH_TOML"], encoding="utf-8").read())
    sys.exit(0)
if args[:1] == ["api"] and "POST" in args:
    print(json.dumps({"number": 41, "html_url": "https://example.com/pull/41"}))
    sys.exit(0)
sys.stderr.write("fake gh: unknown command\n")
sys.exit(1)
"""


def ps1_text() -> str:
    return PS1.read_text(encoding="utf-8")


def bash_blocks(text: str) -> dict[str, str]:
    """{variable: body} of each single-quoted here-string that holds a bash script."""
    found = re.findall(r"\$(\w+)\s*=\s*@'\r?\n(.*?)\r?\n'@", text, flags=re.S)
    return {name: body for name, body in found if body.startswith("#!/usr/bin/env bash")}


def project(tmp: Path, adapter: str | None = WINDOWS, auto: bool = True) -> Path:
    root = tmp / "proj"
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "docs" / "adr" / "0001-adopt-agk.md").write_text("# ADR-0001: Adopt\n", "utf-8")
    (root / "docs" / "adr" / "0007-something.md").write_text("# ADR-0007: Other\n", "utf-8")
    flow = ["[flow]", f"auto_start = {'true' if auto else 'false'}"]
    flow += [adapter] if adapter else []
    text = 'version = "6.0.0"\n\n' + "\n".join(flow) + "\nplan_issue = 3\n\n[plan]\nx = 1\n"
    (root / "agk.toml").write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607 - fixed args
    subprocess.run(  # nosec B603 B607 - fixed argument list
        ["git", "-C", str(root), "remote", "add", "origin", f"https://github.com/{REPO}.git"],
        check=True,
    )
    return root


class Gh:
    def __init__(self, tmp: Path, default_toml: str) -> None:
        self.bin = tmp / "bin"
        self.bin.mkdir()
        exe = self.bin / "gh"
        exe.write_text(FAKE.replace("#!/usr/bin/env python3", f"#!{sys.executable}"), "utf-8")
        exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
        self.calls_path = tmp / "gh-calls.jsonl"
        self.toml = tmp / "default-agk.toml"
        self.toml.write_text(default_toml, encoding="utf-8")

    def calls(self) -> list[list[str]]:
        if not self.calls_path.exists():
            return []
        return [json.loads(x) for x in self.calls_path.read_text("utf-8").splitlines()]

    def run(self, root: Path, *args: str) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env.update(
            PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            FAKE_GH_CALLS=str(self.calls_path),
            FAKE_GH_TOML=str(self.toml),
        )
        return subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(SCRIPTS / "wsl.py"), *args, "--root", str(root)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=60,
        )


def state(**changes) -> dict:
    steps = [{"step": s, "result": "done", "note": ""} for s in wsl.STEP_IDS]
    data = {
        "steps": steps,
        "pending": [],
        "project_dir": "/home/sam/work/example-project",
        "distro": "Ubuntu-24.04",
        "memory_gb": 11,
        "watchdog": "windows",
        "doctor": "summary: 30 ok, 0 fail, 0 cannot-check",
    }
    data.update(changes)
    return data


def write_state(tmp: Path, data: dict) -> Path:
    path = tmp / "state.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# --- the script, read as text (answer 6) ---------------------------------------------------------


def test_script_is_ascii():
    """REQ-050: brief #1376 answer 6: Windows PowerShell 5.1 reads a file without a BOM as ANSI."""
    PS1.read_bytes().decode("ascii")


def test_embedded_linux_scripts_pass_bash_n(tmp_path):
    """REQ-050: brief #1376 answer 6: the root and the user scripts pass `bash -n`."""
    blocks = bash_blocks(ps1_text())
    assert set(blocks) == {"rootScript", "userScript"}
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is not on this runner")
    for name, body in blocks.items():
        path = tmp_path / f"{name}.sh"
        path.write_text(body + "\n", encoding="utf-8")
        done = subprocess.run(  # nosec B603 - fixed argument list, no shell
            [bash, "-n", str(path)], capture_output=True, text=True
        )
        assert done.returncode == 0, f"{name}: {done.stderr}"


@pytest.mark.parametrize(
    "pattern",
    [
        r"gh\s+auth\s+token",
        r"--with-token",
        r"Read-Host",
        r"AsSecureString",
        r"ConvertTo-SecureString",
        r"Get-Credential",
        r"\bGH_TOKEN\b",
        r"\bGITHUB_TOKEN\b",
        r"(?i)\$\w*(password|passwd|token)\w*\s*=",
    ],
)
def test_script_never_handles_a_token_or_password(pattern):
    """REQ-050: brief #1376 answer 2: the sign-ins are the normal browser sign-ins."""
    assert not re.search(pattern, ps1_text()), pattern


def test_every_powershell_step_has_its_skip_check():
    """REQ-050: brief #1376 answer 2: every step checks first and skips what is done."""
    text = ps1_text()
    calls = re.findall(r"(?<!function )\bInvoke-Step\s+(-Name.*)$", text, flags=re.M)
    assert len(calls) >= 8
    for call in calls:
        assert "-Name" in call and "-Done" in call and "-Do" in call, call


def test_every_linux_step_has_its_skip_check():
    """REQ-050: brief #1376 answer 2: each `step ID CHECK DO` of the Linux scripts names a check
    and an action that the same script defines."""
    for name, body in bash_blocks(ps1_text()).items():
        calls = re.findall(r"^\s*step\s+(\w+)\s+(\w+)\s+(\w+)", body, flags=re.M)
        assert calls, name
        defined = set(re.findall(r"^(\w+)\(\)\s*\{", body, flags=re.M))
        for step_id, check, action in calls:
            assert check in defined and action in defined, f"{name}: {step_id}"
            assert check.startswith("has_"), f"{name}: {step_id}"


def test_every_step_id_is_known_to_the_helper():
    """REQ-050: brief #1376 answer 2: the step names the script reports are those `wsl.py` reads."""
    text = ps1_text()
    ids = set(re.findall(r"Invoke-Step\s+-Name\s+'(\w+)'", text))
    for body in bash_blocks(text).values():
        ids |= {m for m, _c, _a in re.findall(r"^\s*step\s+(\w+)\s+(\w+)\s+(\w+)", body, re.M)}
    assert ids == set(wsl.STEP_IDS)


def test_json_table_keys_match_what_the_skill_reads():
    """REQ-050: brief #1376 answer 2: the `-Json` table's keys and result words."""
    text = ps1_text()
    block = re.search(r"\$state\s*=\s*\[ordered\]@\{(.*?)\n\}", text, flags=re.S)
    assert block, "the -Json table is one [ordered] hashtable named $state"
    keys = re.findall(r"^\s*(\w+)\s*=", block.group(1), flags=re.M)
    assert keys == list(wsl.STATE_KEYS)
    for word in wsl.RESULTS:
        assert f"'{word}'" in text, word
    assert re.search(r"\[switch\]\s*\$Json", text)


def test_the_windows_watchdog_task_is_the_kits():
    """REQ-050: brief #1376 answer 3: the task disabled (never deleted) is `conductor.py`'s."""
    text = ps1_text()
    assert f"'{conductor.WATCHDOG_TASK}'" in text
    assert "Unregister-ScheduledTask" not in text
    assert "Disable-ScheduledTask" in text and "Enable-ScheduledTask" in text


def test_script_forms():
    """REQ-050: brief #1376 answer 1: set up, `-Status` (checks only) and `-Back`."""
    text = ps1_text()
    for switch in ("Status", "Back", "InstallWatchdog", "Json"):
        assert re.search(rf"\[switch\]\s*\${switch}\b", text), switch


def test_powershell_parses_the_script():
    """REQ-050: brief #1376 answer 6: PowerShell's own parser, when `pwsh` is on the runner."""
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        print("skipped: pwsh is not on this runner; the text tests above still ran")
        pytest.skip("pwsh is not on this runner")
    command = (
        "$e=$null; [System.Management.Automation.Language.Parser]::ParseFile("
        f"'{PS1}', [ref]$null, [ref]$e) | Out-Null; $e.Count"
    )
    done = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [pwsh, "-NoProfile", "-Command", command], capture_output=True, text=True, timeout=120
    )
    assert done.stdout.strip() == "0", done.stdout + done.stderr


# --- the helper: plan, pull request, status (answers 1, 3 and 4) --------------------------------


def test_adapters_are_the_doctors():
    """REQ-050: brief #1376 answer 3: one table of the kit's two adapter lines."""
    assert wsl.ADAPTERS == {
        "windows": doctor.ADAPTERS["win32"][1].split(" = ", 1)[1].strip('"'),
        "wsl": doctor.ADAPTERS["posix"][1].split(" = ", 1)[1].strip('"'),
    }


def test_plan_before_the_move(tmp_path):
    """REQ-050: brief #1376 answer 1: five lines or fewer; the pull request comes first."""
    root = project(tmp_path)
    gh = Gh(tmp_path, (root / "agk.toml").read_text("utf-8"))
    done = gh.run(root, "plan")
    assert done.returncode == 0, done.stderr
    lines = done.stdout.strip().splitlines()
    assert 1 <= len(lines) <= 5
    text = done.stdout
    assert "pull request" in text and "never merges" in text
    assert "after that pull request merges" in text
    assert REPO in text
    calls = gh.calls()
    assert calls and all("POST" not in c for c in calls)
    assert any(f"repos/{REPO}/contents/agk.toml" in " ".join(c) for c in calls)


def test_plan_after_the_merge(tmp_path):
    """REQ-050: brief #1376 answer 3: with the WSL adapter merged, the watchdog moves."""
    root = project(tmp_path)
    gh = Gh(tmp_path, (root / "agk.toml").read_text("utf-8").replace(WINDOWS, LOCAL))
    path = write_state(tmp_path, state())
    done = gh.run(root, "plan", "--state", str(path))
    assert done.returncode == 0, done.stderr
    assert len(done.stdout.strip().splitlines()) <= 5
    assert "already the WSL adapter" in done.stdout
    assert "Windows task disabled (never deleted)" in done.stdout
    assert "machine: already set up" in done.stdout


def test_plan_without_a_conductor_has_no_watchdog(tmp_path):
    """REQ-050: brief #1376 contexts: personal mode and auto_start off have no watchdog step."""
    root = project(tmp_path, auto=False)
    gh = Gh(tmp_path, (root / "agk.toml").read_text("utf-8"))
    done = gh.run(root, "plan")
    assert done.returncode == 0, done.stderr
    assert "watchdog: none" in done.stdout


def test_plan_back(tmp_path):
    """REQ-050: brief #1376 answer 3: `back` makes the reverse pull request."""
    root = project(tmp_path, adapter=LOCAL)
    gh = Gh(tmp_path, (root / "agk.toml").read_text("utf-8"))
    done = gh.run(root, "plan", "--back")
    assert done.returncode == 0, done.stderr
    assert "Windows adapter" in done.stdout and "re-enabled" in done.stdout
    assert len(done.stdout.strip().splitlines()) <= 5


def test_pull_request_to_wsl(tmp_path):
    """REQ-050: brief #1376 answer 3: one change of `launch_adapter` with its Proposed ADR."""
    root = project(tmp_path)
    gh = Gh(tmp_path, (root / "agk.toml").read_text("utf-8"))
    done = gh.run(root, "pr", "--to", "wsl", "--brief", "none", "--date", "2026-11-15")
    assert done.returncode == 0, done.stderr
    toml = (root / "agk.toml").read_text("utf-8")
    assert LOCAL in toml and WINDOWS not in toml
    assert toml.index(LOCAL) > toml.index("[flow]") and toml.index(LOCAL) < toml.index("[plan]")
    adr = root / "docs" / "adr" / "0008-the-workforce-runs-in-wsl-2.md"
    text = adr.read_text("utf-8")
    assert "- Status: Proposed" in text and "`agk.toml`" in text
    for section in ("## Context", "## Decision", "## Consequences", "## Residual"):
        assert section in text
    body = Path(re.search(r"^body: (.+)$", done.stdout, flags=re.M).group(1)).read_text("utf-8")
    assert "Brief:" not in body  # `--brief none`: the repository has no open brief
    for field in (
        "Advances:",
        "Summary:",
        "Build-state row: 2026-11-15",
        "Decisions taken:",
        "Questions: none",
        "Verified:",
    ):
        assert field in body, field
    assert "ADR-0008" in body
    assert all("POST" not in c for c in gh.calls())


def test_pull_request_back_and_refusals(tmp_path):
    """REQ-050: brief #1376 answer 3: the reverse change, and nothing written when already set."""
    root = project(tmp_path, adapter=LOCAL)
    gh = Gh(tmp_path, "")
    again = gh.run(root, "pr", "--to", "wsl", "--brief", "none", "--date", "2026-11-15")
    assert again.returncode == 1
    assert "already" in again.stdout and "launch_adapter" in again.stdout
    assert not (root / "docs" / "adr" / "0008-the-workforce-runs-in-wsl-2.md").exists()
    back = gh.run(root, "pr", "--to", "windows", "--brief", "none", "--date", "2026-11-15")
    assert back.returncode == 0, back.stderr
    assert WINDOWS in (root / "agk.toml").read_text("utf-8")
    assert (root / "docs" / "adr" / "0008-the-workforce-runs-on-windows-again.md").is_file()


def test_pull_request_names_its_brief(tmp_path):
    """REQ-050: brief #1376 answer 3: `--brief N` gives the body its `Brief: #N` line."""
    root = project(tmp_path)
    gh = Gh(tmp_path, "")
    done = gh.run(root, "pr", "--to", "wsl", "--brief", "12", "--date", "2026-11-15")
    assert done.returncode == 0, done.stderr
    assert "\nBrief: #12\n" in "\n" + done.stdout + "\n"
    bad = gh.run(root, "pr", "--to", "linux", "--date", "2026-11-15")
    assert bad.returncode == 2


def test_pull_request_adds_an_unset_adapter(tmp_path):
    """REQ-050: brief #1376 answer 3: an unset adapter is added to the `[flow]` table."""
    root = project(tmp_path, adapter=None)
    gh = Gh(tmp_path, "")
    done = gh.run(root, "pr", "--to", "wsl", "--brief", "none", "--date", "2026-11-15")
    assert done.returncode == 0, done.stderr
    toml = (root / "agk.toml").read_text("utf-8")
    assert toml.index("[flow]") < toml.index(LOCAL) < toml.index("[plan]")


def test_open_posts_one_draft_and_never_merges(tmp_path):
    """REQ-050: brief #1376 answer 3: one REST POST of a draft; no merge, no auto-merge."""
    root = project(tmp_path)
    gh = Gh(tmp_path, "")
    body = tmp_path / "body.md"
    body.write_text("Brief: none\n", encoding="utf-8")
    done = gh.run(root, "open", "--body", str(body), "--branch", "agk/wsl-adapter")
    assert done.returncode == 0, done.stderr
    assert "https://example.com/pull/41" in done.stdout
    calls = gh.calls()
    assert len(calls) == 1
    call = calls[0]
    assert call[:4] == ["api", "-X", "POST", f"repos/{REPO}/pulls"]
    assert "draft=true" in call and "head=agk/wsl-adapter" in call and "base=main" in call
    assert not any("merge" in a for a in call)


def test_status_lines(tmp_path):
    """REQ-050: brief #1376 answer 4: one plain line per part, in order."""
    root = project(tmp_path)
    gh = Gh(tmp_path, (root / "agk.toml").read_text("utf-8").replace(WINDOWS, LOCAL))
    data = state(watchdog="wsl")
    for item in data["steps"]:
        if item["step"] == "claude_signin":
            item["result"] = "waiting"
    done = gh.run(root, "status", "--state", str(write_state(tmp_path, data)))
    assert done.returncode == 0, done.stderr
    heads = [line.split(":", 1)[0] for line in done.stdout.strip().splitlines()]
    assert heads == [
        "wsl",
        "sign-ins",
        "clone",
        "adapter",
        "watchdog",
        "podman",
        "playwright",
        "doctor",
    ]
    assert "Ubuntu-24.04" in done.stdout and "11 GB" in done.stdout
    assert "GitHub done, Claude waiting" in done.stdout
    assert "adapter: the WSL adapter on main" in done.stdout
    assert "watchdog: the WSL task" in done.stdout
    assert "summary: 30 ok" in done.stdout


def test_status_without_a_state(tmp_path):
    """REQ-050: brief #1376 answer 4: before any run, the parts are `not read` and the adapter is
    still read from the default branch."""
    root = project(tmp_path)
    gh = Gh(tmp_path, (root / "agk.toml").read_text("utf-8"))
    done = gh.run(root, "status")
    assert done.returncode == 0, done.stderr
    assert "adapter: the Windows adapter on main" in done.stdout
    assert "wsl: not read" in done.stdout


def test_skill_names_its_forms_and_the_helper():
    """REQ-050: brief #1376 answers 1 and 3: the skill runs the script and the helper from the
    plugin root, shows the plan, and never merges."""
    text = SKILL.read_text("utf-8")
    assert text.startswith("---\nname: wsl\n")
    for form in ("/agk:wsl status", "/agk:wsl back"):
        assert form in text
    assert "${CLAUDE_PLUGIN_ROOT}/scripts/agk/wsl_setup.ps1" in text
    assert "${CLAUDE_PLUGIN_ROOT}/scripts/agk/wsl.py" in text
    assert "prepush.py --record" in text
    assert "Never merge" in text


# --- the doctor (answer 5) -----------------------------------------------------------------------


def test_doctor_inside_wsl_on_a_windows_drive():
    """REQ-050: brief #1376 answer 5."""
    lines = doctor.wsl_lines(Path("/mnt/c/Users/sam/example-project"), "linux", True, None, None)
    assert lines == ["wsl: the project is on a Windows drive; move it inside WSL (/agk:wsl)"]
    assert doctor.wsl_lines(Path("/home/sam/work/example-project"), "linux", True, None, None) == []
    assert doctor.wsl_lines(Path("/mnt/c/x"), "linux", False, None, None) == []


def test_doctor_on_windows_with_wsl_present():
    """REQ-050: brief #1376 answer 5: the Windows adapter set and `wsl` found: one line."""
    adapter = wsl.ADAPTERS["windows"]
    found = doctor.wsl_lines(Path("C:/x"), "win32", False, adapter, r"C:\Windows\wsl.exe")
    assert len(found) == 1 and "/agk:wsl" in found[0] and found[0].startswith("wsl: ")
    assert doctor.wsl_lines(Path("C:/x"), "win32", False, adapter, None) == []
    assert doctor.wsl_lines(Path("C:/x"), "win32", False, wsl.ADAPTERS["wsl"], "wsl.exe") == []


def test_doctor_reads_wsl_from_the_kernel(tmp_path):
    """REQ-050: brief #1376 answer 5: WSL is read from the kernel's version text."""
    version = tmp_path / "version"
    version.write_text("Linux version 5.15.0-microsoft-standard-WSL2 (example)\n", "utf-8")
    assert doctor.inside_wsl(version) is True
    version.write_text("Linux version 6.1.0-generic (example)\n", "utf-8")
    assert doctor.inside_wsl(version) is False
    assert doctor.inside_wsl(tmp_path / "absent") is False
