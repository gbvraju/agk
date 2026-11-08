"""The pinned CI test tools (brief #698, ADR-0328, REQ-051).

`config/ci-tools.txt` holds one exact `<name>==<version>` pin per line; the governance workflow's
`Install tooling` step installs that file and nothing else, so a tool update touches the pin file
only. `ci_tools.py check` prints the pins with no network; `--upstream` reads the package index's
JSON once per pin (a `curl` stub here, or saved responses with `--responses`) and prints which are
behind. Invented data only; no network.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "agk" / "ci_tools.py"
PINS = ROOT / "config" / "ci-tools.txt"
GOVERNANCE = ROOT / ".github" / "workflows" / "governance.yml"
LINE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([0-9][0-9A-Za-z.+!-]*)$")


def governance_step(name: str) -> str:
    body = GOVERNANCE.read_text(encoding="utf-8").split("    steps:\n", 1)[1]
    parts = re.split(r"(?m)^      - (?=name: |uses: )", body)[1:]
    found = {m.group(1).strip(): p for p in parts if (m := re.match(r"name: (.+)", p))}
    assert name in found, f"governance has no step {name!r}"
    return found[name]


def pin_lines(text: str) -> list[str]:
    return [
        ln.strip() for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")
    ]


def run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 - fixed argument list from sys.executable, no shell
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        env=env,
    )


def project(tmp_path: Path, text: str) -> Path:
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "config" / "ci-tools.txt").write_text(text, encoding="utf-8")
    return tmp_path


def response(newest: str, dates: dict[str, str]) -> str:
    releases = {v: [{"upload_time_iso_8601": f"{d}T10:00:00.000000Z"}] for v, d in dates.items()}
    return json.dumps({"info": {"version": newest}, "releases": releases})


GOOD = "# invented pins\nalpha-tool==1.0.0\nbeta==2.1.0\ngamma==0.3.0\n"


def saved(tmp_path: Path) -> Path:
    folder = tmp_path / "responses"
    folder.mkdir()
    (folder / "alpha-tool.json").write_text(
        response("1.2.0", {"1.0.0": "2026-01-01", "1.1.0": "2026-02-01", "1.2.0": "2026-03-02"}),
        encoding="utf-8",
    )
    (folder / "beta.json").write_text(response("2.1.0", {"2.1.0": "2026-05-01"}), encoding="utf-8")
    return folder  # gamma has no saved response: the upstream cannot be read


# --- the pin file and the workflow (answers 1 and 3) ----------------------------------------------


def test_pin_file_has_one_exact_pin_per_line_sorted_and_unique():
    """REQ-051: brief #698 answer 1. Every line is `<name>==<version>`; names sorted, no repeats."""
    lines = pin_lines(PINS.read_text(encoding="utf-8"))
    assert lines, "config/ci-tools.txt has no pin"
    bad = [ln for ln in lines if not LINE.match(ln)]
    assert not bad, f"not an exact pin: {bad}"
    names = [ln.split("==", 1)[0].lower() for ln in lines]
    assert names == sorted(names) and len(names) == len(set(names))


def test_pin_file_pins_the_four_ci_tools_and_the_measured_xdist():
    """REQ-051: brief #698 answer 1. pytest, pytest-xdist (3.8.0, #642 measured), ruff, bandit."""
    pins = dict(ln.split("==", 1) for ln in pin_lines(PINS.read_text(encoding="utf-8")))
    assert {"bandit", "pytest", "pytest-xdist", "ruff"} <= set(pins)
    assert pins["pytest-xdist"] == "3.8.0"


def test_install_tooling_installs_the_pin_file_and_nothing_else():
    """REQ-051: brief #698 answers 1 and 4. One `pip install -r config/ci-tools.txt`, no other."""
    run_text = governance_step("Install tooling").split("run:", 1)[1]
    installs = re.findall(r"pip install ([^\n|]+)", run_text)
    assert [i.strip() for i in installs] == ["-r config/ci-tools.txt"]
    whole = GOVERNANCE.read_text(encoding="utf-8")
    job, merger = whole.split("\n  merger:\n", 1)  # the merger job installs its own (brief #765)
    assert len(re.findall(r"pip install", job)) == 1, "a tool is installed outside the pin file"
    found = re.findall(r"pip install ([^\n|]+)", merger)
    assert [i.strip() for i in found] == ["-q -r config/ci-tools.txt"], "the merger's one install"


def test_the_workflow_reads_the_pin_file_that_exists():
    """REQ-051: brief #698 answer 3. The workflow's `-r` path and the pin file agree."""
    run_text = governance_step("Install tooling").split("run:", 1)[1]
    found = re.search(r"pip install -r (\S+)", run_text)
    assert found and (ROOT / found.group(1)) == PINS and PINS.is_file()


def test_install_tooling_fails_by_name_when_xdist_is_missing():
    """REQ-051: brief #698 answer 2. xdist has no `--version`; the step imports it by name."""
    run_text = governance_step("Install tooling").split("run:", 1)[1]
    assert re.search(
        r'python -c "import xdist" [^\n]*\|\| \{ echo "[^"]*pytest-xdist[^"]*"; exit 1; \}',
        run_text,
    )


# --- ci_tools.py check (answer 3) -----------------------------------------------------------------


def test_check_prints_the_pins_with_no_network(tmp_path):
    """REQ-051: brief #698 answer 3. `check` reads the file only; a `curl` on PATH never runs."""
    root = project(tmp_path, GOOD)
    bin_dir, calls = curl_stub(tmp_path, saved(tmp_path))
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"}
    proc = run("check", "--root", str(root), env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines() == [
        "pin alpha-tool 1.0.0",
        "pin beta 2.1.0",
        "pin gamma 0.3.0",
        "ok ci-tools: 3 pins",
    ]
    assert not calls.exists()


def test_check_passes_on_the_repository_pin_file():
    """REQ-051: brief #698 answer 3. The kit's own file passes its own check."""
    proc = run("check", "--root", str(ROOT))
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.splitlines()[-1].startswith("ok ci-tools: ")


def test_check_refuses_a_line_that_is_not_an_exact_pin_without_quoting_it(tmp_path):
    """REQ-051: brief #698 answer 3; principle 8: a range pin fails naming the path only."""
    root = project(tmp_path, "alpha-tool==1.0.0\nbeta>=2.1.0\n")
    proc = run("check", "--root", str(root))
    assert proc.returncode == 1
    assert (
        "FAIL ci-tools: line 2 is not <name>==<version> (path: config/ci-tools.txt)" in proc.stdout
    )
    assert "2.1.0" not in proc.stdout


def test_check_refuses_a_repeated_or_unsorted_name(tmp_path):
    """REQ-051: brief #698 answer 3. One pin per tool, in name order, so an update is one line."""
    repeated = run("check", "--root", str(project(tmp_path / "a", "beta==1.0.0\nbeta==1.1.0\n")))
    assert repeated.returncode == 1 and "line 2 repeats a tool" in repeated.stdout
    unsorted = run("check", "--root", str(project(tmp_path / "b", "beta==1.0.0\nalpha==1.0.0\n")))
    assert unsorted.returncode == 1 and "line 2 is out of name order" in unsorted.stdout


def test_check_refuses_a_missing_or_empty_pin_file(tmp_path):
    """REQ-051: brief #698 answer 3. No file, or no pin in it, fails naming the path."""
    missing = run("check", "--root", str(tmp_path))
    assert missing.returncode == 1
    assert "FAIL ci-tools: no pin file (path: config/ci-tools.txt)" in missing.stdout
    empty = run("check", "--root", str(project(tmp_path / "e", "# nothing pinned\n")))
    assert empty.returncode == 1 and "no pin (path: config/ci-tools.txt)" in empty.stdout


def test_upstream_from_saved_responses_names_behind_current_and_unknown(tmp_path):
    """REQ-051: brief #698 answer 3; SPEC-0047 rule 8. Behind with its gap, current, and unknown
    for an upstream that cannot be read (never `0 behind`)."""
    root = project(tmp_path, GOOD)
    proc = run("check", "--root", str(root), "--upstream", "--responses", str(saved(tmp_path)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines() == [
        "behind alpha-tool 1.0.0 newest 1.2.0 gap 60 days",
        "current beta 2.1.0",
        "unknown gamma 0.3.0",
        "pins_behind 1",
        "pins_oldest_gap_days 60",
        "ok ci-tools: 3 pins, 1 behind, 1 unknown",
    ]


def test_upstream_with_every_upstream_unreadable_is_unknown_not_zero(tmp_path):
    """REQ-051: brief #698 answer 3; SPEC-0047 rule 8. Nothing read is `unknown`, never `0`."""
    root = project(tmp_path, "gamma==0.3.0\n")
    empty = tmp_path / "none"
    empty.mkdir()
    proc = run("check", "--root", str(root), "--upstream", "--responses", str(empty))
    assert proc.returncode == 0
    assert "pins_behind unknown" in proc.stdout.splitlines()
    assert "pins_oldest_gap_days unknown" in proc.stdout.splitlines()


def curl_stub(tmp_path: Path, folder: Path) -> tuple[Path, Path]:
    """A `curl` that serves the saved response named by the URL's package and logs each call."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    calls = tmp_path / "curl-calls.txt"
    stub = bin_dir / "curl"
    stub.write_text(
        f"#!{sys.executable}\n"
        "import sys, pathlib\n"
        "url = sys.argv[-1]\n"
        f"pathlib.Path({str(calls)!r}).open('a').write(url + '\\n')\n"
        "name = url.rstrip('/').split('/')[-2]\n"
        f"saved = pathlib.Path({str(folder)!r}) / (name + '.json')\n"
        "if not saved.is_file():\n"
        "    sys.exit(22)\n"
        "sys.stdout.write(saved.read_text())\n",
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    return bin_dir, calls


def test_upstream_reads_the_package_index_once_per_pin(tmp_path):
    """REQ-051: brief #698 answer 3; SPEC-0047 rule 8. One GET per pin, of the index JSON."""
    root = project(tmp_path, GOOD)
    bin_dir, calls = curl_stub(tmp_path, saved(tmp_path))
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"}
    proc = run("check", "--root", str(root), "--upstream", env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert calls.read_text(encoding="utf-8").splitlines() == [
        "https://pypi.org/pypi/alpha-tool/json",
        "https://pypi.org/pypi/beta/json",
        "https://pypi.org/pypi/gamma/json",
    ]
    assert "pins_behind 1" in proc.stdout.splitlines()


def test_unknown_command_or_option_prints_the_usage(tmp_path):
    """REQ-051: brief #698 answer 3. Anything but `check` and its options: the usage, exit 2."""
    for args in ([], ["update"], ["check", "--network"], ["check", "--responses"]):
        proc = run(*args)
        assert proc.returncode == 2, args
        assert proc.stdout.startswith("usage: ci_tools.py check")
