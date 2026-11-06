"""The secret scan is mandatory in every mode (brief #632, ADR-0306, REQ-049).

The secret scan never passes by being skipped: in every mode, a run that needs it fails, naming
the missing tool, when gitleaks is not installed. `prepush.py` stops at `secret-scan` with one line
naming the tool and the version the governance workflow pins, `--quick` does not skip the scan,
the record of such a run says `FAIL`, and `doctor.py` prints one line saying whether gitleaks is
installed and at which version. Every gitleaks here is a stand-in shell script; nothing is
downloaded and no network is used.
"""

from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path

from test_doctor import doctor, run_case
from test_prepush import path_with, project, scanner, steps

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "governance.yml"


def pinned() -> str:
    """The gitleaks version the governance workflow pins (`GITLEAKS_VERSION`)."""
    found = set(re.findall(r"GITLEAKS_VERSION: ([0-9.]+)", WORKFLOW.read_text(encoding="utf-8")))
    assert len(found) == 1, found
    return found.pop()


def versioned(folder: Path, version: str) -> Path:
    """A stand-in `gitleaks` that answers `gitleaks version` with `version`."""
    folder.mkdir(parents=True, exist_ok=True)
    tool = folder / "gitleaks"
    tool.write_text(f'#!/bin/sh\n[ "$1" = version ] && echo "{version}"\nexit 0\n', encoding="utf-8")
    tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    return folder


def prepush(repo, *args: str, scan: Path | None = None):
    return repo.run("prepush.py", *args, PATH=path_with(scan))


def test_the_kit_pin_is_the_workflow_pin():
    """REQ-049: brief #632 answer 1 (the version named is the one the workflow pins)."""
    from common import GITLEAKS_PIN

    assert GITLEAKS_PIN == pinned()


def test_a_missing_gitleaks_fails_prepush_naming_the_tool(repo):
    """REQ-049: brief #632 answer 1 (a missing gitleaks is a FAIL, never `not run`)."""
    project(repo)
    proc = prepush(repo, scan=None)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert steps(proc.stdout)["secret-scan"] == "FAIL"
    assert "tests" not in steps(proc.stdout)  # nothing after it ran
    assert "gitleaks is not installed" in proc.stdout
    assert f"install gitleaks {pinned()}" in proc.stdout
    assert "(tool: gitleaks)" in proc.stdout
    assert "secret scan: not run" not in proc.stdout
    assert "not run: secret-scan" not in proc.stdout
    assert "prepush: stopped at secret-scan; nothing after it ran" in proc.stdout


def test_quick_never_skips_the_scan(repo, tmp_path):
    """REQ-049: brief #632 answer 1 (`--quick` skips the tests only, never the scan)."""
    project(repo)
    missing = prepush(repo, "--quick", scan=None)
    assert missing.returncode == 1, missing.stdout + missing.stderr
    assert steps(missing.stdout)["secret-scan"] == "FAIL"
    folder = scanner(tmp_path / "bin", 0)
    present = prepush(repo, "--quick", scan=folder)
    assert present.returncode == 0, present.stdout + present.stderr
    assert steps(present.stdout)["secret-scan"] == "ok"
    assert (folder / "args.txt").is_file()  # the scan ran under --quick


def test_a_missing_gitleaks_is_recorded_as_a_failure(repo, tmp_path):
    """REQ-049: brief #632 answer 1 (the record says FAIL, so evidence cannot read it as a pass)."""
    project(repo)
    outside = tmp_path / "outside"
    outside.mkdir()
    record = outside / "record.json"
    proc = prepush(repo, "--quick", "--record", str(record), scan=None)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    data = json.loads(record.read_text(encoding="utf-8"))
    scan = next(s for s in data["steps"] if s["name"] == "secret-scan")
    assert scan["outcome"] == "FAIL" and scan["not_run"] is False
    assert data["result"] == "failed" and data["not_run"] == []
    assert "gitleaks" not in data["versions"]


def test_no_kit_script_passes_a_scan_that_did_not_run():
    """REQ-049: brief #632 answer 2 (no other command says `secret scan: not run` and passes)."""
    scripts = sorted((ROOT / "scripts" / "agk").glob("*.py"))
    assert scripts
    for path in scripts:
        text = path.read_text(encoding="utf-8")
        assert "secret scan: not run" not in text, path.name
        assert 'gitleaks is not installed; secret scan' not in text, path.name


def doctor_line(stdout: str) -> str:
    lines = [ln for ln in stdout.splitlines() if ln.startswith("secret scan: ")]
    assert len(lines) == 1, stdout
    return lines[0]


def test_doctor_names_the_installed_gitleaks_and_its_version(tmp_path):
    """REQ-049: brief #632 answer 3 (installed, at which version)."""
    proc, _, dirs = run_case("ok", tmp_path)
    plain = proc.returncode
    stub = versioned(tmp_path / "leaks", pinned())
    args = ["--api-dir", str(dirs["api"]), "--repo", "example-owner/example-repo"]
    args += ["--kit-root", str(dirs["kit"]), str(dirs["root"])]
    found = doctor(*args, path=path_with(stub) + os.pathsep + str(tmp_path / "bin"))
    line = doctor_line(found.stdout)
    assert line == f"secret scan: gitleaks {pinned()} is installed"
    assert found.returncode == plain  # an information line; the exit code does not change
    assert found.stdout.index(line) < found.stdout.index("summary: ")


def test_doctor_names_a_version_other_than_the_pin(tmp_path):
    """REQ-049: brief #632 answer 3 (a version that is not the workflow's pin is said)."""
    dirs = run_case("ok", tmp_path)[2]
    stub = versioned(tmp_path / "leaks", "8.0.0")
    args = ["--api-dir", str(dirs["api"]), "--repo", "example-owner/example-repo", str(dirs["root"])]
    line = doctor_line(doctor(*args, path=path_with(stub) + os.pathsep + str(tmp_path / "bin")).stdout)
    assert line.startswith("secret scan: gitleaks 8.0.0 is installed")
    assert f"the governance workflow pins {pinned()}" in line


def test_doctor_says_when_gitleaks_is_missing(tmp_path):
    """REQ-049: brief #632 answer 3 (missing: the line names the tool and how to install it)."""
    proc, _, dirs = run_case("ok", tmp_path)
    plain = proc.returncode
    args = ["--api-dir", str(dirs["api"]), "--repo", "example-owner/example-repo"]
    args += ["--kit-root", str(dirs["kit"]), str(dirs["root"])]
    found = doctor(*args, path=path_with(None) + os.pathsep + str(tmp_path / "bin"))
    line = doctor_line(found.stdout)
    assert line.startswith("secret scan: gitleaks is not installed")
    assert "prepush fails" in line and f"install gitleaks {pinned()}" in line
    assert found.returncode == plain


def test_doctor_json_carries_the_line(tmp_path):
    """REQ-049: brief #632 answer 3 (the same line in `--json`)."""
    dirs = run_case("ok", tmp_path)[2]
    stub = versioned(tmp_path / "leaks", pinned())
    args = ["--api-dir", str(dirs["api"]), "--repo", "example-owner/example-repo", "--json"]
    args += [str(dirs["root"])]
    found = doctor(*args, path=path_with(stub) + os.pathsep + str(tmp_path / "bin"))
    data = json.loads(found.stdout)
    assert data["secret_scan"] == f"secret scan: gitleaks {pinned()} is installed"
