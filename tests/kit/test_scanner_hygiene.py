"""Kit source under a project's own scanners: justified suppressions and clean types (ADR-0010).

Pure checks of the source text; bandit and mypy are run only where they are installed. Governance
installs bandit with its other tooling, so the bandit test runs in CI (brief #338, ADR-0192).
"""

from __future__ import annotations

import ast
import importlib.metadata
import importlib.util
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE = ROOT / ".github" / "workflows" / "governance.yml"
MYPY_BASELINE = ROOT / "config" / "mypy-baseline.txt"
KIT_SOURCE = ("scripts/agk", ".claude/hooks", "tests/kit")
SPAWNERS = {"run", "Popen", "call", "check_call", "check_output"}
# Built from parts so that this file carries no suppression comment of its own.
MARK = "# " + "nosec"
WITH_REASON = re.compile(re.escape(MARK) + r" (B\d{3}(?: B\d{3})*) - \S")
IGNORE = "type" + ": ignore"


def sources() -> list[Path]:
    found = []
    for rel in KIT_SOURCE:
        base = ROOT / rel
        if base.is_dir():
            found.extend(sorted(base.glob("*.py")))
    return found


def codes_on(line: str) -> set[str]:
    match = WITH_REASON.search(line)
    return set(match.group(1).split()) if match else set()


def partial_path_executable(call: ast.Call) -> bool:
    """True when the first argument is a list whose first item is a bare program name."""
    if not call.args or not isinstance(call.args[0], (ast.List, ast.Tuple)):
        return False
    elements = call.args[0].elts
    first = elements[0] if elements else None
    return (
        isinstance(first, ast.Constant)
        and isinstance(first.value, str)
        and not first.value.startswith("/")
    )


def test_kit_source_is_found():
    """REQ-010: the scan below is not vacuous."""
    names = {p.name for p in sources()}
    assert {"common.py", "stop_check.py", "conftest.py"} <= names


def test_every_subprocess_import_and_call_has_a_justified_suppression():
    """REQ-010: ADR-0010 decision 1. Each import and each call names its codes and a reason."""
    problems = []
    for path in sources():
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Import) and any(a.name == "subprocess" for a in node.names):
                if "B404" not in codes_on(lines[node.lineno - 1]):
                    problems.append(f"{path.name}:{node.lineno} import needs B404 and a reason")
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "subprocess"
                and node.func.attr in SPAWNERS
            ):
                want = {"B603"} | ({"B607"} if partial_path_executable(node) else set())
                have = codes_on(lines[node.lineno - 1])
                if have != want:
                    where = f"{path.name}:{node.lineno}"
                    problems.append(f"{where} needs exactly {sorted(want)}, has {sorted(have)}")
    assert not problems, "\n".join(problems)


def test_no_blanket_suppression_and_no_type_ignore():
    """REQ-010: ADR-0010 decisions 1 and 2. Every suppression has codes and a reason."""
    problems = []
    for path in sources():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if MARK in line and not WITH_REASON.search(line):
                problems.append(f"{path.name}:{number} suppression without codes and a reason")
            if IGNORE in line:
                problems.append(f"{path.name}:{number} type comment instead of a fix")
    assert not problems, "\n".join(problems)


def installed(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


@pytest.mark.skipif(not installed("bandit"), reason="bandit is not installed")
def test_bandit_finds_only_asserts_in_kit_source():
    """REQ-010: ADR-0010. Without the bare-assert rule B101, bandit is quiet on kit source."""
    proc = subprocess.run(  # nosec B603 - fixed argument list from sys.executable, no shell
        [sys.executable, "-m", "bandit", "-q", "-r", *KIT_SOURCE, "--skip", "B101"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout[-800:]


# --- the type check ratchet (brief #633, ADR-0307) ------------------------------------------------

def mypy_counts(output: str) -> dict[tuple[str, str], int]:
    raise NotImplementedError


def read_baseline(text: str) -> tuple[str, dict[tuple[str, str], int]]:
    raise NotImplementedError


def ratchet_problems(
    current: dict[tuple[str, str], int], baseline: dict[tuple[str, str], int]
) -> list[str]:
    raise NotImplementedError


def baseline_text(version: str, counts: dict[tuple[str, str], int]) -> str:
    raise NotImplementedError


SAMPLE = """\
scripts/agk/a.py:3: error: Value of type "int | str" is not indexable  [index]
scripts/agk/a.py:9: note: Right operand is of type "int | None"
scripts/agk/a.py:12: error: Item "None" of "str | None" has no attribute "x"  [union-attr]
scripts/agk/a.py:40: error: Item "None" of "str | None" has no attribute "y"  [union-attr]
scripts/agk/b.py:7:5: error: Need type annotation for "found"  [var-annotated]
Found 4 errors in 2 files (checked 3 source files)
"""


def test_mypy_counts_errors_by_file_and_code_without_line_numbers():
    """REQ-016: brief #633 answer 1. Notes are not errors; lines and columns are dropped."""
    assert mypy_counts(SAMPLE) == {
        ("scripts/agk/a.py", "index"): 1,
        ("scripts/agk/a.py", "union-attr"): 2,
        ("scripts/agk/b.py", "var-annotated"): 1,
    }
    assert mypy_counts("Success: no issues found in 3 source files\n") == {}


def test_mypy_counts_refuses_output_it_cannot_read_whole():
    """REQ-016: brief #633 answer 1. An error line it cannot parse is never silently dropped."""
    no_code = "scripts/agk/a.py:3: error: Something\nFound 1 error in 1 file\n"
    with pytest.raises(ValueError, match="error code"):
        mypy_counts(no_code)
    short = SAMPLE.replace("Found 4 errors", "Found 5 errors")
    with pytest.raises(ValueError, match="summary"):
        mypy_counts(short)
    with pytest.raises(ValueError, match="summary"):
        mypy_counts("scripts/agk/a.py:3: error: X  [index]\n")


BASELINE = """\
# comment lines and blank lines are ignored

mypy 2.3.1
scripts/agk/a.py index 1
scripts/agk/a.py union-attr 2
"""


def test_read_baseline_returns_the_pinned_version_and_the_counts():
    """REQ-016: brief #633 answers 1 and 2. One `mypy` line pins the version; one line per code."""
    version, counts = read_baseline(BASELINE)
    assert version == "2.3.1"
    assert counts == {("scripts/agk/a.py", "index"): 1, ("scripts/agk/a.py", "union-attr"): 2}


@pytest.mark.parametrize(
    "text, words",
    [
        ("scripts/agk/a.py index 1\n", "mypy"),
        ("mypy 2.3\nscripts/agk/a.py index 1\n", "exact"),
        ("mypy >=2.3.1\n", "exact"),
        ("mypy 2.3.1\nmypy 2.3.1\n", "mypy"),
        ("mypy 2.3.1\nscripts/agk/a.py index 0\n", "count"),
        ("mypy 2.3.1\nscripts/agk/a.py index x\n", "count"),
        ("mypy 2.3.1\nscripts/agk/a.py:3 index 1\n", "line"),
        ("mypy 2.3.1\nscripts/agk/a.py index\n", "line"),
        ("mypy 2.3.1\na.py index 1\na.py index 2\n", "twice"),
    ],
)
def test_read_baseline_refuses_a_malformed_file(text, words):
    """REQ-016: brief #633 answers 1 and 2. A baseline it cannot read exactly fails, naming why."""
    with pytest.raises(ValueError, match=words):
        read_baseline(text)


def test_ratchet_fails_when_a_file_gains_an_error_of_a_code():
    """REQ-016: brief #633 answer 1. More errors of a code in a file than its baseline fails."""
    _, baseline = read_baseline(BASELINE)
    more = dict(baseline) | {("scripts/agk/a.py", "union-attr"): 3}
    new_code = dict(baseline) | {("scripts/agk/a.py", "arg-type"): 1}
    new_file = dict(baseline) | {("scripts/agk/c.py", "index"): 1}
    for current in (more, new_code, new_file):
        problems = ratchet_problems(current, baseline)
        assert len(problems) == 1 and "added" in problems[0], problems


def test_ratchet_fails_when_the_baseline_lists_errors_that_are_gone():
    """REQ-016: brief #633 answer 1. The baseline only shrinks, in the same pull request."""
    _, baseline = read_baseline(BASELINE)
    fewer = dict(baseline) | {("scripts/agk/a.py", "union-attr"): 1}
    gone = {("scripts/agk/a.py", "union-attr"): 2}
    assert ["lower" in p for p in ratchet_problems(fewer, baseline)] == [True]
    assert ["lower" in p for p in ratchet_problems(gone, baseline)] == [True]
    assert ratchet_problems(dict(baseline), baseline) == []


def test_baseline_text_reads_back_to_the_same_counts():
    """REQ-016: brief #633 answer 1. The text a failure prints is a baseline the reader accepts."""
    counts = mypy_counts(SAMPLE)
    assert read_baseline(baseline_text("2.3.1", counts)) == ("2.3.1", counts)


def test_the_baseline_pins_mypy_and_names_only_files_that_exist():
    """REQ-016: brief #633 answer 2. Runs without mypy too, so CI reads the baseline file."""
    version, counts = read_baseline(MYPY_BASELINE.read_text(encoding="utf-8"))
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    missing = sorted({f for f, _ in counts if not (ROOT / f).is_file()})
    assert not missing, f"the baseline names files that are gone: {missing}"


@pytest.mark.skipif(not installed("mypy"), reason="mypy is not installed")
def test_mypy_errors_on_scripts_match_the_baseline():
    """REQ-016: brief #633 answers 1 and 2 (was REQ-010, ADR-0010 decision 2: mypy clean)."""
    version, baseline = read_baseline(MYPY_BASELINE.read_text(encoding="utf-8"))
    if importlib.metadata.version("mypy") != version:
        pytest.skip("installed mypy is not the version the mypy line of the baseline pins")
    proc = subprocess.run(  # nosec B603 - fixed argument list from sys.executable, no shell
        [sys.executable, "-m", "mypy", "scripts/agk"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    current = mypy_counts(proc.stdout)
    problems = ratchet_problems(current, baseline)
    rel = MYPY_BASELINE.relative_to(ROOT)
    assert not problems, "\n".join(problems) + f"\n\n{rel} now reads:\n" + baseline_text(
        version, current
    )


# --- governance installs bandit (brief #338, ADR-0192) --------------------------------------------


def governance_step(name: str) -> str:
    """The text of one step of the governance job, read when a test runs."""
    body = GOVERNANCE.read_text(encoding="utf-8").split("    steps:\n", 1)[1]
    parts = re.split(r"(?m)^      - (?=name: |uses: )", body)[1:]
    found = {m.group(1).strip(): p for p in parts if (m := re.match(r"name: (.+)", p))}
    assert name in found, f"governance has no step {name!r}"
    return found[name]


def test_governance_installs_bandit_with_its_other_tooling():
    """REQ-001: brief #338 answer 2. The step that installs pytest and ruff installs bandit too."""
    run = governance_step("Install tooling").split("run:", 1)[1]
    install = re.search(r"python -m pip install ([^\n|]+)", run)
    assert install, "Install tooling has no pip install line"
    assert {"pytest", "ruff", "bandit"} <= set(install.group(1).split())


def test_governance_fails_naming_a_tool_it_could_not_install():
    """REQ-001: brief #338 answer 2. A missing tool fails the step by name; nothing skips."""
    run = governance_step("Install tooling").split("run:", 1)[1]
    loop = re.search(r"for tool in ([^;\n]+);", run)
    assert loop, "Install tooling does not check each tool after the install"
    assert {"pytest", "ruff", "bandit"} <= set(loop.group(1).split())
    assert 'python -m "$tool" --version' in run
    named = re.search(r'echo "[^"]*\$tool[^"]*"; exit 1', run)
    assert named, "a missing tool must fail the step by name"
