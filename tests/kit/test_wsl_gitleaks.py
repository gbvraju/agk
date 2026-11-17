"""The WSL setup installs the pinned gitleaks, so a new machine's first local push can run its
secret scan (brief #1450, ADR-0608; REQ-049).

The `gitleaks` step of `scripts/agk/wsl_setup.ps1`'s root script runs under bash with stubs on the
PATH only: a `curl` stub that serves a saved release archive and its checksum file (or refuses),
a `uname` stub for the architecture and an installed `gitleaks` stub. The PowerShell side is read
as text. Invented data only; no network, no model, nothing installed outside the test's folder.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import doctor  # noqa: E402
import wsl  # noqa: E402
from common import GITLEAKS_PIN  # noqa: E402

PS1 = SCRIPTS / "wsl_setup.ps1"
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="bash is not on this runner")

CURL = r"""#!/usr/bin/env python3
import json, os, shutil, sys
args = sys.argv[1:]
with open(os.environ["FAKE_CURL_CALLS"], "a", encoding="utf-8") as f:
    f.write(json.dumps(args) + "\n")
if os.environ.get("FAKE_CURL_BLOCK") == "1":
    sys.exit(22)
out = args[args.index("-o") + 1]
src = os.path.join(os.environ["FAKE_CURL_FILES"], args[-1].rsplit("/", 1)[-1])
if not os.path.isfile(src):
    sys.exit(22)
shutil.copyfile(src, out)
"""


def tool(text: str) -> bytes:
    return text.encode("utf-8")


def stub(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def root_script() -> str:
    text = PS1.read_text(encoding="utf-8")
    return re.search(r"\$rootScript\s*=\s*@'\r?\n(.*?)\r?\n'@", text, flags=re.S).group(1)


def harness() -> str:
    """The root script's `step` function and its gitleaks block, then the one step."""
    body = root_script()
    step = re.search(r"^step\(\) \{.*?^\}$", body, flags=re.S | re.M).group(0)
    block = re.search(r"^# --- gitleaks.*?^# --- end gitleaks ---$", body, flags=re.S | re.M)
    assert block, "the gitleaks functions sit between their two marker lines"
    return f"set -uo pipefail\n{step}\n{block.group(0)}\nstep gitleaks has_gitleaks set_gitleaks\n"


class Machine:
    def __init__(self, tmp: Path, arch: str = "x86_64", installed: str | None = None) -> None:
        self.tmp = tmp
        self.bin = tmp / "stubs"
        self.dest = tmp / "local-bin"
        self.files = tmp / "release"
        for d in (self.bin, self.dest, self.files):
            d.mkdir()
        self.calls = tmp / "curl-calls.jsonl"
        stub(self.bin / "curl", CURL.replace("#!/usr/bin/env python3", f"#!{sys.executable}"))
        stub(self.bin / "uname", f"#!/bin/sh\necho {arch}\n")
        if installed:
            stub(self.dest / "gitleaks", f"#!/bin/sh\necho {installed}\n")
        name = {"x86_64": "x64", "aarch64": "arm64"}.get(arch, arch)
        self.archive = f"gitleaks_{GITLEAKS_PIN}_linux_{name}.tar.gz"
        self.release(self.archive)

    def release(self, archive: str, digest: str | None = None) -> None:
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w:gz") as tar:
            payload = tool(f"#!/bin/sh\necho {GITLEAKS_PIN}\n")
            info = tarfile.TarInfo("gitleaks")
            info.size, info.mode = len(payload), 0o755
            tar.addfile(info, io.BytesIO(payload))
        (self.files / archive).write_bytes(data.getvalue())
        sums = f"{digest or hashlib.sha256(data.getvalue()).hexdigest()}  {archive}\n"
        sums += f"{'0' * 64}  gitleaks_{GITLEAKS_PIN}_darwin_x64.tar.gz\n"
        (self.files / f"gitleaks_{GITLEAKS_PIN}_checksums.txt").write_text(sums, encoding="utf-8")

    def run(self, check_only: bool = False, block: bool = False, pin: str = GITLEAKS_PIN):
        script = self.tmp / "harness.sh"
        script.write_text(harness(), encoding="utf-8")
        env = {
            "PATH": f"{self.dest}:{self.bin}:/usr/bin:/bin",
            "AGK_GITLEAKS": pin,
            "AGK_GITLEAKS_DIR": str(self.dest),
            "AGK_CHECK_ONLY": "1" if check_only else "0",
            "FAKE_CURL_CALLS": str(self.calls),
            "FAKE_CURL_FILES": str(self.files),
            "FAKE_CURL_BLOCK": "1" if block else "0",
        }
        done = subprocess.run(  # nosec B603 - fixed argument list, no shell
            [BASH, str(script)], capture_output=True, text=True, env=env, timeout=60
        )
        lines = [x for x in done.stdout.splitlines() if x.startswith("AGK_STEP=gitleaks|")]
        assert len(lines) == 1, done.stdout + done.stderr
        return lines[0].split("|", 2)[1:]

    def curl_calls(self) -> list[list[str]]:
        if not self.calls.exists():
            return []
        return [json.loads(x) for x in self.calls.read_text("utf-8").splitlines()]

    def installed(self) -> str | None:
        exe = self.dest / "gitleaks"
        if not exe.exists():
            return None
        return subprocess.run(  # nosec B603 - fixed argument list, no shell
            [str(exe)], capture_output=True, text=True, timeout=30
        ).stdout.strip()


def test_missing_gitleaks_is_installed_at_the_pin(tmp_path):
    """REQ-049: brief #1450 answers 1 and 2: downloaded, checked against its checksum, installed."""
    m = Machine(tmp_path)
    assert m.run() == ["done", ""]
    assert m.installed() == GITLEAKS_PIN
    urls = [c[-1] for c in m.curl_calls()]
    assert any(u.endswith(f"/v{GITLEAKS_PIN}/{m.archive}") for u in urls)
    assert any(u.endswith("_checksums.txt") for u in urls)


def test_the_pinned_version_already_installed_is_skipped(tmp_path):
    """REQ-049: brief #1450 answer 6: already at the pinned version."""
    m = Machine(tmp_path, installed=f"v{GITLEAKS_PIN}")
    assert m.run() == ["skipped", ""]
    assert m.curl_calls() == []


def test_an_older_version_is_replaced(tmp_path):
    """REQ-049: brief #1450 answer 6: an older version."""
    m = Machine(tmp_path, installed="8.0.0")
    assert m.run() == ["done", ""]
    assert m.installed() == GITLEAKS_PIN


def test_a_checksum_mismatch_installs_nothing(tmp_path):
    """REQ-049: brief #1450 answers 2 and 6: a mismatch stops the step `failed`."""
    m = Machine(tmp_path)
    m.release(m.archive, digest="f" * 64)
    result, note = m.run()
    assert result == "failed" and "checksum" in note and "nothing was installed" in note
    assert m.installed() is None


def test_a_blocked_download_names_what_to_allow(tmp_path):
    """REQ-049: brief #1450 answers 2, 3 and 6: a blocked download names what to allow."""
    m = Machine(tmp_path, installed="8.0.0")
    result, note = m.run(block=True)
    assert result == "failed" and "github.com" in note and "-CorpCaFile" in note
    assert "nothing was installed" in note
    assert m.installed() == "8.0.0"


def test_status_checks_only(tmp_path):
    """REQ-049: brief #1450 answer 6: `-Status` changes nothing and downloads nothing."""
    m = Machine(tmp_path)
    assert m.run(check_only=True) == ["waiting", "to do"]
    assert m.curl_calls() == [] and m.installed() is None


def test_an_arm64_machine_gets_the_arm64_release(tmp_path):
    """REQ-049: brief #1450 answer 6: an arm64 machine."""
    m = Machine(tmp_path, arch="aarch64")
    assert m.run() == ["done", ""]
    assert any(c[-1].endswith("_linux_arm64.tar.gz") for c in m.curl_calls())


def test_an_unknown_architecture_fails_plainly(tmp_path):
    """REQ-049: brief #1450 answer 6: no release for the machine, nothing downloaded."""
    m = Machine(tmp_path, arch="riscv64")
    result, note = m.run()
    assert result == "failed" and "architecture" in note
    assert m.curl_calls() == []


def test_a_pin_not_read_fails_plainly(tmp_path):
    """REQ-049: brief #1450 answer 1: no version typed twice, so an unread pin is a failure."""
    m = Machine(tmp_path)
    result, note = m.run(pin="")
    assert result == "failed" and "pinned" in note
    assert m.curl_calls() == []


# --- the PowerShell side, read as text --------------------------------------------------------


def test_the_step_follows_packages_and_reads_the_one_pin():
    """REQ-049: brief #1450 answer 1: after `packages`, the pin read from `common.py`."""
    body = root_script()
    steps = re.findall(r"^step (\w+) ", body, flags=re.M)
    assert steps.index("gitleaks") == steps.index("packages") + 1
    assert wsl.STEP_IDS.index("gitleaks") == wsl.STEP_IDS.index("packages") + 1
    text = PS1.read_text(encoding="utf-8")
    pattern = re.search(r"-Pattern '([^']+)'", text[text.index("GITLEAKS_PIN") - 300 :]).group(1)
    pin = re.search(pattern, (SCRIPTS / "common.py").read_text("utf-8"), flags=re.M)
    assert pin and pin.group(1) == GITLEAKS_PIN
    assert '"AGK_GITLEAKS=$gitleaksPin"' in text
    assert not re.search(r"8\.\d+\.\d+", text), "the version is never typed in the script"


# --- the doctor (answer 4) ------------------------------------------------------------------------


def test_the_doctor_names_the_step_inside_wsl(monkeypatch):
    """REQ-049: brief #1450 answer 4: missing gitleaks inside WSL names /agk:wsl."""
    monkeypatch.setattr(doctor.shutil, "which", lambda _name: None)
    line = doctor.secret_scan_line(in_wsl=True)
    assert line.startswith("secret scan: gitleaks is not installed; prepush fails until it is")
    assert line.endswith(f"run /agk:wsl again; it installs gitleaks {GITLEAKS_PIN}")
    outside = doctor.secret_scan_line(in_wsl=False)
    assert "/agk:wsl" not in outside and f"install gitleaks {GITLEAKS_PIN}" in outside
