"""Kit tests: pinned versions and licences in the stack record, and the stack's own build and lock
files (brief #1592, ADR-0672, amendments 200 and 201; REQ-036 AC4, REQ-079).

A Proposed stack record names each option's `Parts:`, each `<name> <exact version> <licence id>`;
`engines.py stack-files` writes the chosen stack's build file from `kit/templates/stacks/` and
never rewrites one a project already holds; `gates/pins.py` (the `pins` step) fails on a direct
dependency not pinned exactly or not in the lock, on a missing lock and on a part of the Accepted
record whose version differs from the lock's, naming the rule and the component class, never a
name or a version. Invented package names under a temporary root (example.com); no network.
"""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
ENGINES = KIT_ROOT / "scripts" / "agk" / "engines.py"
PINS = KIT_ROOT / "scripts" / "agk" / "gates" / "pins.py"
STACK = "docs/adr/0002-stack-options.md"
EFFECTS = (
    "Cost: one small server; Build speed: quick, one program; "
    "Security: one sign-in in front of the data; Uptime: a short pause on a restart."
)
PY_PARTS = "Parts: python 3.12.7 PSF-2.0, examplelib 1.2.3 MIT (verify)."
NODE_PARTS = "Parts: node 22.11.0 MIT, example-web 4.21.1 MIT (verify)."
HASH = "--hash=sha256:" + "0" * 64
SECRET_WORDS = ("examplelib", "example-web", "1.2.3", "1.2.4", "4.21.1")


def option(letter: str, parts: str, recommended: bool) -> str:
    mark = " (recommended)" if recommended else ""
    why = " Why: the busiest hour is small." if recommended else ""
    return (
        f"   - Option {letter} — one web application at example.com{mark}. Trade-offs: {EFFECTS}"
        f"{why} {parts} Practices: pinned actions.\n"
    )


def record(a_parts: str = PY_PARTS, status: str = "Proposed", chosen: str = "none yet") -> str:
    options = option("A", a_parts, True) + option("B", NODE_PARTS, False)
    return f"""# ADR-0002: stack options

- Status: {status}
- Date: 2026-11-20
- Deciders: maintainers
- Related: ADR-0001
- Requirements: REQ-001

## Context

A reading list for readers at example.com.

## Decision

1. **Options**
{options}2. **Practices**
   - pinned actions: check (step: the workflow lint of the adopting build)
3. **Chosen**: {chosen}

## Consequences

The architect accepts one option; the ADR then locks it.

## Residual

None.
"""


def project(tmp: Path, text: str | None, toml: str = '[delivery]\nwork_type = "web-app"\n') -> Path:
    (tmp / "docs" / "adr").mkdir(parents=True)
    (tmp / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
    shutil.copytree(KIT_ROOT / "config" / "playbooks", tmp / "config" / "playbooks")
    (tmp / "agk.toml").write_text('default_branch = "main"\n' + toml, encoding="utf-8")
    if text is not None:
        (tmp / STACK).write_text(text, encoding="utf-8")
    return tmp


def run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(script), *args], capture_output=True, text=True, check=False
    )


def check(root: Path) -> subprocess.CompletedProcess:
    return run(PINS, "--root", str(root))


def python_project(tmp: Path, dep: str = "examplelib==1.2.3", lock: str | None = None) -> Path:
    root = project(tmp, record(status="Accepted", chosen="Option A"))
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "sample"\nversion = "0.0.0"\ndependencies = ["{dep}"]\n',
        encoding="utf-8",
    )
    if lock is None:
        lock = f"examplelib==1.2.3 \\\n    {HASH}\n"
    if lock:
        (root / "requirements.lock").write_text(lock, encoding="utf-8")
    return root


def node_project(tmp: Path, spec: str = "4.21.1", locked: str = "4.21.1") -> Path:
    root = project(tmp, record(a_parts=NODE_PARTS, status="Accepted", chosen="Option A"))
    pkg = {"name": "sample", "version": "0.0.0", "dependencies": {"example-web": spec}}
    (root / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    lock = {
        "lockfileVersion": 3,
        "packages": {"": {"name": "sample"}, "node_modules/example-web": {"version": locked}},
    }
    (root / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
    return root


def with_lock(root: Path, runtime: str = "python") -> Path:
    """Brief #1776: the chosen stack's lock with no dependency, so `pins` passes on a sample of
    another step that had no lock before (its build file must exist)."""
    name, text = (
        ("package-lock.json", '{"lockfileVersion": 3}\n')
        if runtime == "node"
        else ("requirements.lock", "# no dependency yet\n")
    )
    (root / name).write_text(text, encoding="utf-8")
    return root


def no_values(text: str) -> None:
    for word in SECRET_WORDS:
        assert word not in text, word


# REQ-036 AC4: the record names each part's exact version and licence.


def test_req036_ac4_a_record_with_exact_parts_passes(tmp_path: Path) -> None:
    result = run(ENGINES, "stack-check", "--root", str(project(tmp_path, record())))
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("parts", "says"),
    [
        ("Parts: python 3.12.7 PSF-2.0, examplelib ^1.2.3 MIT.", "option A part 2 has a range"),
        ("Parts: python 3.12.7 PSF-2.0, examplelib 1.x MIT.", "option A part 2 has a range"),
        ("Parts: python 3.12.7 PSF-2.0, examplelib MIT.", "option A part 2 has a range"),
        ("Parts: python 3.12.7 PSF-2.0, examplelib 1.2.3.", "option A part 2 has no licence id"),
        ("Parts: python 3.12.7, examplelib 1.2.3 MIT.", "option A part 1 has no licence id"),
        ("", "option A names no Parts"),
    ],
)
def test_req036_ac4_a_record_with_a_range_or_no_licence_is_refused(
    tmp_path: Path, parts: str, says: str
) -> None:
    result = run(ENGINES, "stack-check", "--root", str(project(tmp_path, record(a_parts=parts))))
    assert result.returncode == 1
    assert f"rule 5: {says}" in result.stdout + result.stderr
    no_values(result.stdout + result.stderr)


def test_req036_ac4_an_accepted_record_without_parts_still_passes(tmp_path: Path) -> None:
    root = project(tmp_path, record(a_parts="", status="Accepted", chosen="Option A"))
    result = run(ENGINES, "stack-check", "--root", str(root))
    assert "names no Parts" not in result.stdout + result.stderr


def test_req036_ac4_the_skeleton_asks_for_parts() -> None:
    text = (KIT_ROOT / "kit" / "templates" / "stack-adr.md").read_text(encoding="utf-8")
    assert text.count("Parts: TODO(architect).") == 2


# REQ-079: the foundation writes the chosen stack's build file; the pins step checks it.


def test_req079_a_node_sample_gets_package_json_and_no_pyproject(tmp_path: Path) -> None:
    root = project(tmp_path, record(a_parts=NODE_PARTS, status="Accepted", chosen="Option A"))
    result = run(ENGINES, "stack-files", "--root", str(root))
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads((root / "package.json").read_text(encoding="utf-8"))
    assert data["dependencies"] == {} and data["private"] is True
    assert not (root / "pyproject.toml").exists()


def test_req079_a_python_sample_gets_exact_pins_over_the_init_file(tmp_path: Path) -> None:
    root = project(tmp_path, record(status="Accepted", chosen="Option A"))
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    from init import slug  # noqa: PLC0415 - the kit's own slug

    init_text = (KIT_ROOT / "kit" / "templates" / "pyproject.toml").read_text(encoding="utf-8")
    (root / "pyproject.toml").write_text(
        init_text.replace("{{project}}", slug(root.name)), encoding="utf-8"
    )
    assert run(ENGINES, "stack-files", "--root", str(root)).returncode == 0
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "setuptools==" in text and ">=61" not in text


def test_req079_an_adopted_build_file_is_untouched(tmp_path: Path) -> None:
    root = project(
        tmp_path,
        record(a_parts=NODE_PARTS, status="Accepted", chosen="Option A"),
        toml='mode = "adopt"\n[delivery]\nwork_type = "web-app"\n',
    )
    own = '{"name": "theirs", "dependencies": {"example-web": "^4.0.0"}}\n'
    (root / "package.json").write_text(own, encoding="utf-8")
    result = run(ENGINES, "stack-files", "--root", str(root))
    assert result.returncode == 0 and "kept package.json" in result.stdout
    assert (root / "package.json").read_text(encoding="utf-8") == own


def test_req079_no_work_type_is_not_run(tmp_path: Path) -> None:
    result = check(project(tmp_path, record(), toml=""))
    assert result.returncode == 0 and "not run: no stack chosen" in result.stdout


def test_req079_a_pinned_python_sample_passes(tmp_path: Path) -> None:
    result = check(python_project(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ok pins" in result.stdout


def test_req079_crlf_lock_lines_are_normalised(tmp_path: Path) -> None:
    lock = f"examplelib==1.2.3 \\\r\n    {HASH}\r\n"
    assert check(python_project(tmp_path, lock=lock)).returncode == 0


@pytest.mark.parametrize(
    ("dep", "lock", "says"),
    [
        ("examplelib>=1.2", None, "a direct dependency is not pinned exactly"),
        ("examplelib==1.2.3", "", "the lock file is missing"),
        ("examplelib==1.2.3", f"otherlib==0.1.0 \\\n    {HASH}\n", "is not in the lock"),
        ("examplelib==1.2.3", f"examplelib==1.2.4 \\\n    {HASH}\n", "differs from the lock"),
    ],
)
def test_req079_an_unpinned_or_unlocked_python_sample_is_red(
    tmp_path: Path, dep: str, lock: str | None, says: str
) -> None:
    result = check(python_project(tmp_path, dep=dep, lock=lock))
    assert result.returncode == 1
    assert says in result.stdout and "component class:" in result.stdout
    no_values(result.stdout + result.stderr)


def test_req079_a_pinned_node_sample_passes(tmp_path: Path) -> None:
    result = check(node_project(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("spec", "locked", "says"),
    [
        ("^4.21.1", "4.21.1", "a direct dependency is not pinned exactly"),
        ("4.21.1", "4.21.2", "differs from the lock"),
    ],
)
def test_req079_an_unpinned_or_stale_node_sample_is_red(
    tmp_path: Path, spec: str, locked: str, says: str
) -> None:
    result = check(node_project(tmp_path, spec=spec, locked=locked))
    assert result.returncode == 1 and says in result.stdout
    no_values(result.stdout + result.stderr)


def test_req079_the_step_follows_the_runner_interface(tmp_path: Path) -> None:
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    from gates import pins  # noqa: PLC0415 - the step module itself

    assert isinstance(pins.RULE, str) and pins.RULE
    assert pins.check(python_project(tmp_path), {}) == []


@pytest.mark.parametrize("args", [["--root"], ["--other"], ["--root", ".", "extra"]])
def test_req079_a_malformed_command_line_prints_usage(args: list[str]) -> None:
    result = run(PINS, *args)
    assert result.returncode == 2 and "Traceback" not in result.stderr
    assert result.stderr.startswith("usage: python3 scripts/agk/gates/pins.py")


# Brief #1776 (ADR-0742): the gate runner runs the pins step; governance fails an unpinned product.


def gate_rows(root: Path) -> list[tuple[object, str]]:
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import run_gates  # noqa: PLC0415 - the gate runner itself

    return [row for row in run_gates.results(root) if row[1].startswith(("pins", "baseline pins"))]


def test_req079_the_runner_fails_an_unpinned_sample(tmp_path: Path) -> None:
    rows = gate_rows(node_project(tmp_path, spec="^4.21.1"))
    assert rows and all(passed is False for passed, _ in rows), rows
    assert any("not pinned exactly (component class: dependency)" in line for _, line in rows)
    no_values(repr(rows))


def test_req079_the_runner_fails_a_missing_lock(tmp_path: Path) -> None:
    rows = gate_rows(python_project(tmp_path, lock=""))
    assert [p for p, _ in rows] == [False]
    assert "the lock file is missing (component class: lock file)" in rows[0][1]


def test_req079_the_runner_passes_a_pinned_and_locked_sample(tmp_path: Path) -> None:
    assert gate_rows(python_project(tmp_path)) == [(True, "pins")]


def test_req079_no_stack_chosen_is_a_not_run_row(tmp_path: Path) -> None:
    assert gate_rows(project(tmp_path, record())) == [(None, "pins: no stack chosen")]


def test_req079_no_work_type_leaves_the_runner_unchanged(tmp_path: Path) -> None:
    assert gate_rows(project(tmp_path, record(), toml="")) == []


def test_req079_an_adopted_sample_writes_its_baseline_then_fails_on_a_new_range(
    tmp_path: Path,
) -> None:
    root = node_project(tmp_path, spec="^4.21.1")
    text = (root / "agk.toml").read_text(encoding="utf-8")
    (root / "agk.toml").write_text('mode = "adopt"\n' + text, encoding="utf-8")
    rows = gate_rows(root)
    assert (True, "pins (baseline)") in rows, rows
    assert any(line.startswith("baseline pins: written") for _, line in rows)
    assert (root / "config" / "agk-baseline" / "pins.txt").is_file()
    assert gate_rows(root) == [(True, "pins (baseline)")]
    pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
    pkg["dependencies"]["example-api"] = "~3.23.8"
    (root / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    rows = gate_rows(root)
    assert any(p is False and "SPEC-0072 rule 7" in line for p, line in rows), rows


# REQ-079, brief #1778 (ADR-0744): a runtime written with a capital, as people write it, is read.


def picked(parts: str) -> object:
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    from gates import pins  # noqa: PLC0415 - the step module itself

    found = pins.pick([record(a_parts=parts, status="Accepted", chosen="Option A")])
    return found[0] if found else None


@pytest.mark.parametrize(
    ("parts", "runtime"),
    [
        ("Parts: Node 22.11.0 MIT (verify), example-web 4.21.1 MIT (verify).", "node"),
        ("Parts: Python 3.13.1 PSF-2.0, examplelib 1.2.3 MIT.", "python"),
        ("Parts: PYTHON 3.13.1 PSF-2.0, examplelib 1.2.3 MIT.", "python"),
    ],
)
def test_req079_a_capitalised_runtime_is_chosen_as_that_runtime(parts: str, runtime: str) -> None:
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    from gates import pins  # noqa: PLC0415 - the step module itself

    assert picked(parts) == pins.STACKS[runtime]


# REQ-079, brief #1843 (ADR-0771, superseding ADR-0744 decision 2): the common spellings of a
# runtime are that runtime, through one table, for every reader.

SPELLINGS = [
    ("Node.js", "node"),
    ("NodeJS", "node"),
    ("nodejs", "node"),
    ("NODE.JS", "node"),
    ("Node", "node"),
    ("python3", "python"),
    ("CPython", "python"),
    ("Python", "python"),
]


def pins_module() -> object:
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    from gates import pins  # noqa: PLC0415 - the step module itself

    return pins


@pytest.mark.parametrize(("name", "runtime"), SPELLINGS)
def test_req079_a_common_spelling_of_a_runtime_is_that_runtime(name: str, runtime: str) -> None:
    """Brief #1843 answer 3: `option_parts`, `pick` and so `chosen` read the runtime."""
    pins = pins_module()
    parts = f"Parts: {name} 22.11.0 MIT, example-web 4.21.1 MIT."
    assert pins.option_parts(parts)[0] == (runtime, "22.11.0", "MIT")
    assert picked(parts) == pins.STACKS[runtime]


@pytest.mark.parametrize(("name", "runtime"), SPELLINGS)
def test_req079_the_tests_floor_reads_every_spelling(
    tmp_path: Path, name: str, runtime: str
) -> None:
    """Brief #1843 answers 3 and 5: `tests_floor.runtime` on one Accepted record per spelling."""
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    from gates import tests_floor  # noqa: PLC0415 - the step module itself

    parts = f"Parts: {name} 22.11.0 MIT, example-web 4.21.1 MIT."
    root = project(tmp_path, record(a_parts=parts, status="Accepted", chosen="Option A"))
    assert tests_floor.runtime(root) == runtime


def test_req079_a_two_word_runtime_stays_two_words() -> None:
    """Brief #1843 answer 3: `Node JS 22.11.0` is the name `node` and the version `JS`."""
    pins = pins_module()
    assert pins.option_parts("Parts: Node JS 22.11.0 MIT.")[0] == ("node", "JS", "22.11.0 MIT")


@pytest.mark.parametrize("name", ["Deno", "examplelib", "Node-RED"])
def test_req079_another_name_stays_as_written(name: str) -> None:
    """Brief #1843 answer 3: every other name is kept as written, and is no runtime."""
    pins = pins_module()
    assert pins.option_parts(f"Parts: {name} 1.0.0 MIT.")[0][0] == name
    assert picked(f"Parts: {name} 22.11.0 MIT, example-web 4.21.1 MIT.") is None


def test_req079_the_runtime_table_and_the_stacks_are_one_class() -> None:
    """Brief #1843 answer 5: every spelling names a `STACKS` key, every key has its row, and
    each key spells itself, so a runtime added without its spellings fails here."""
    pins = pins_module()
    assert set(pins.RUNTIME_NAMES.values()) == set(pins.STACKS)
    for key in pins.STACKS:
        assert pins.RUNTIME_NAMES[key] == key
    assert all(k == k.lower() for k in pins.RUNTIME_NAMES)


def test_req079_an_accepted_node_js_record_gets_package_json(tmp_path: Path) -> None:
    """Brief #1843 answer 8 (Q-HI-2): `stack-files` on an Accepted `Node.js` record."""
    parts = NODE_PARTS.replace("Parts: node ", "Parts: Node.js ")
    root = project(tmp_path, record(a_parts=parts, status="Accepted", chosen="Option A"))
    result = run(ENGINES, "stack-files", "--root", str(root))
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / "package.json").is_file() and not (root / "pyproject.toml").exists()


def test_req079_a_capitalised_node_sample_runs_the_pins_step(tmp_path: Path) -> None:
    root = node_project(tmp_path)
    text = (root / STACK).read_text(encoding="utf-8")
    (root / STACK).write_text(text.replace("Parts: node ", "Parts: Node "), encoding="utf-8")
    result = check(root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ok pins" in result.stdout and "not run" not in result.stdout


# REQ-079, brief #1909 (ADR-0791, amendment 234): in a new project, from the stack's acceptance to
# the foundation, the step waits: `not run: no foundation yet`, never a failure and never `ok`.

INIT = 'mode = "init"\n[delivery]\nwork_type = "web-app"\n'
FOUNDATION = "not run: no foundation yet"


def init_build_file(root: Path) -> None:
    """`init`'s own `pyproject.toml`, which declares no dependency."""
    text = (KIT_ROOT / "kit" / "templates" / "pyproject.toml").read_text(encoding="utf-8")
    (root / "pyproject.toml").write_text(text.replace("{{project}}", "sample"), encoding="utf-8")


def init_python(tmp: Path, toml: str = INIT) -> Path:
    """An init project with an Accepted Python record, `init`'s build file, no lock, no record."""
    root = project(tmp, record(status="Accepted", chosen="Option A"), toml=toml)
    init_build_file(root)
    return root


def init_node(tmp: Path) -> Path:
    return project(tmp, record(a_parts=NODE_PARTS, status="Accepted", chosen="Option A"), INIT)


def add_dependency(root: Path) -> None:
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    text = text.replace("dependencies = []", 'dependencies = ["examplelib==1.2.3"]')
    (root / "pyproject.toml").write_text(text, encoding="utf-8")


def test_req079_an_init_project_before_the_foundation_waits(tmp_path: Path) -> None:
    pins = pins_module()
    root = init_python(tmp_path)
    assert pins.waiting(root) is True
    assert pins.skipped(root) == "no foundation yet"
    assert pins.findings(root) is None and pins.counts(root, {}) == {}
    result = check(root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == f"pins: {FOUNDATION}"
    assert gate_rows(root) == [(None, "pins: no foundation yet")]


def test_req079_the_stack_files_template_still_waits(tmp_path: Path) -> None:
    root = project(tmp_path, record(status="Accepted", chosen="Option A"), toml=INIT)
    assert run(ENGINES, "stack-files", "--root", str(root)).returncode == 0
    assert (root / "pyproject.toml").is_file()
    result = check(root)
    assert result.returncode == 0 and FOUNDATION in result.stdout, result.stdout


def end_by_dependency(root: Path) -> None:
    add_dependency(root)


def end_by_requirements(root: Path) -> None:
    (root / "requirements.txt").write_text("examplelib==1.2.3\n", encoding="utf-8")


def end_by_architecture(root: Path) -> None:
    (root / "docs" / "architecture.md").write_text("# Architecture\n", encoding="utf-8")


def end_by_adopt(root: Path) -> None:
    text = (root / "agk.toml").read_text(encoding="utf-8")
    (root / "agk.toml").write_text(text.replace('mode = "init"', 'mode = "adopt"'), "utf-8")


@pytest.mark.parametrize(
    "end", [end_by_dependency, end_by_requirements, end_by_architecture, end_by_adopt]
)
def test_req079_each_condition_alone_ends_the_wait(tmp_path: Path, end) -> None:
    """Brief #1909 answer 9: each of the four conditions alone makes the step strict again."""
    pins = pins_module()
    root = init_python(tmp_path)
    end(root)
    assert pins.waiting(root) is False and pins.skipped(root) is None
    result = check(root)
    assert result.returncode == 1
    assert "the lock file is missing (component class: lock file)" in result.stdout
    no_values(result.stdout + result.stderr)


def test_req079_an_adopted_sample_holds_the_missing_lock_in_its_baseline(tmp_path: Path) -> None:
    root = init_python(tmp_path)
    end_by_adopt(root)
    rows = gate_rows(root)
    assert (True, "pins (baseline)") in rows, rows
    assert (root / "config" / "agk-baseline" / "pins.txt").is_file()


def test_req079_a_committed_lock_ends_the_wait_and_is_read_in_full(tmp_path: Path) -> None:
    pins = pins_module()
    root = init_python(tmp_path)
    with_lock(root)
    assert pins.waiting(root) is False
    assert check(root).returncode == 0 and "ok pins" in check(root).stdout
    add_dependency(root)
    (root / "requirements.lock").write_text(f"examplelib==1.2.4 \\\n    {HASH}\n", "utf-8")
    result = check(root)
    assert result.returncode == 1 and "differs from the lock" in result.stdout


def test_req079_a_malformed_build_file_never_waits(tmp_path: Path) -> None:
    pins = pins_module()
    root = init_python(tmp_path)
    (root / "pyproject.toml").write_text("[project\nname = \n", encoding="utf-8")
    assert pins.waiting(root) is False
    result = check(root)
    assert result.returncode == 1 and "the build file is missing or unreadable" in result.stdout


def test_req079_a_missing_requirements_include_never_waits(tmp_path: Path) -> None:
    root = init_python(tmp_path)
    (root / "requirements.txt").write_text("-r missing.txt\n", encoding="utf-8")
    result = check(root)
    assert result.returncode == 1 and "the build file is missing or unreadable" in result.stdout


def test_req079_a_node_record_with_no_package_json_waits(tmp_path: Path) -> None:
    result = check(init_node(tmp_path))
    assert result.returncode == 0 and FOUNDATION in result.stdout, result.stdout


@pytest.mark.parametrize("groups", [{}, {"dependencies": {}, "devDependencies": {}}])
def test_req079_a_node_build_file_with_no_dependency_waits(tmp_path: Path, groups: dict) -> None:
    root = init_node(tmp_path)
    (root / "package.json").write_text(json.dumps({"name": "sample", **groups}), "utf-8")
    assert check(root).returncode == 0 and FOUNDATION in check(root).stdout


@pytest.mark.parametrize("group", ["dependencies", "devDependencies", "optionalDependencies"])
def test_req079_a_node_dependency_with_no_lock_fails(tmp_path: Path, group: str) -> None:
    root = init_node(tmp_path)
    pkg = {"name": "sample", group: {"example-web": "4.21.1"}}
    (root / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    result = check(root)
    assert result.returncode == 1 and "the lock file is missing" in result.stdout
    no_values(result.stdout + result.stderr)


def test_req079_a_malformed_package_json_never_waits(tmp_path: Path) -> None:
    root = init_node(tmp_path)
    (root / "package.json").write_text("{not json", encoding="utf-8")
    result = check(root)
    assert result.returncode == 1 and "the build file is missing or unreadable" in result.stdout


def test_req079_no_stack_chosen_still_wins_over_the_wait(tmp_path: Path) -> None:
    pins = pins_module()
    root = project(tmp_path, record(), toml=INIT)
    assert pins.skipped(root) == "no stack chosen"
    assert check(root).stdout.strip() == "pins: not run: no stack chosen"


def test_req079_the_wait_reads_the_record_path_of_the_layers_step() -> None:
    """Brief #1909 answer 9: one architecture record for the wait and the foundation's steps."""
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    from gates import layers  # noqa: PLC0415 - the step module itself

    assert pins_module().ARCHITECTURE == layers.RECORD


def test_req079_the_runner_passes_an_init_project_with_pins_not_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import run_gates  # noqa: PLC0415 - the gate runner itself

    root = init_python(tmp_path)
    assert run_gates.main(["--root", str(root)]) == 0
    out = capsys.readouterr().out
    last = out.strip().splitlines()[-1]
    assert "not run: " in last and "pins" in last.split("not run: ", 1)[1].split(", "), out
    assert "FAIL" not in out


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout


def accept_record() -> str:
    """The Proposed record with what `stack-accept` reads: a test selection and its classes."""
    lint = "   - pinned actions: check (step: the workflow lint of the adopting build)\n"
    selection = (
        "   - test selection: judgement (Option A: profile fast, always_full `app/auth/**`; "
        "Option B: profile thorough, always_full `src/**`)\n"
    )
    practices = "Practices: pinned actions"
    text = record().replace(f"{practices}.", f"{practices}, test selection.")
    text = text.replace(lint, lint + selection)
    return text.replace("## Context", "Protected classes: `agk.toml`\n\n## Context", 1)


def test_req079_after_stack_accept_the_runner_holds_no_failed_pins_row(tmp_path: Path) -> None:
    """Brief #1909 answer 8: the accepting change of an init project leaves governance green."""
    remote = tmp_path / "remote.git"
    root = tmp_path / "web"
    root.mkdir()
    project(root, accept_record(), toml=INIT + '\n[testing]\nprofile = "balanced"\n')
    shutil.copy(
        KIT_ROOT / "kit" / "templates" / "protected-paths.txt",
        root / "config" / "protected-paths.txt",
    )
    init_build_file(root)
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "init", "-q", "--bare", str(remote)], check=True
    )
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "builder@example.com")
    git(root, "config", "user.name", "Builder")
    git(root, "remote", "add", "origin", str(remote))
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "start")
    git(root, "push", "-q", "origin", "main")
    git(root, "checkout", "-q", "-b", "stack/accept")
    args = ("stack-accept", "--option", "A", "--reason", "smallest", "--root", str(root))
    accept = run(ENGINES, *args)
    assert accept.returncode == 0, accept.stdout + accept.stderr
    assert "Accepted" in (root / STACK).read_text(encoding="utf-8")
    rows = gate_rows(root)
    assert rows == [(None, "pins: no foundation yet")], rows


# REQ-079 AC5, brief #1932 (ADR-0800, amendment 247): a chosen option with two runtimes (Node at
# the root, Python in `service/`) is read per runtime, each build file and lock in its own folder.

TWO_PARTS = (
    "Parts: Node.js 22.11.0 MIT, example-web 4.21.1 MIT, "
    "Python 3.12.7 PSF-2.0, examplelib 1.2.3 MIT (verify)."
)
PY_LOCK = f"examplelib==1.2.3 \\\n    {HASH}\n"


def node_files(base: Path, spec: str = "4.21.1", extra: dict | None = None) -> None:
    base.mkdir(parents=True, exist_ok=True)
    pkg = {"name": "sample", "version": "0.0.0", "dependencies": {"example-web": spec}}
    (base / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    packages = {"": {"name": "sample"}, "node_modules/example-web": {"version": "4.21.1"}}
    packages.update(extra or {})
    lock = {"lockfileVersion": 3, "packages": packages}
    (base / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")


def py_files(base: Path, req: str = "examplelib==1.2.3\n", lock: str | None = PY_LOCK) -> None:
    base.mkdir(parents=True, exist_ok=True)
    (base / "requirements.txt").write_text(req, encoding="utf-8")
    if lock is not None:
        (base / "requirements.lock").write_text(lock, encoding="utf-8")


def two_runtimes(tmp: Path, parts: str = TWO_PARTS, toml: str | None = None) -> Path:
    text = record(a_parts=parts, status="Accepted", chosen="Option A")
    root = project(tmp, text) if toml is None else project(tmp, text, toml=toml)
    node_files(root)
    py_files(root / "service")
    return root


def test_req079_ac5_two_pinned_runtimes_pass(tmp_path: Path) -> None:
    pins = pins_module()
    root = two_runtimes(tmp_path)
    result = check(root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "ok pins\n"
    found = pins.runtimes([(root / STACK).read_text(encoding="utf-8")], lambda: pins.tracked(root))
    assert [(r.row[0], r.folder) for r in found] == [("node", ""), ("python-pyproject", "service")]


def test_req079_ac5_pick_still_reads_two_runtimes_as_none(tmp_path: Path) -> None:
    """Answer 1: the single-runtime readers (ADR-0800's list) stay `not run`, never moved."""
    pins = pins_module()
    root = two_runtimes(tmp_path)
    assert pins.pick([(root / STACK).read_text(encoding="utf-8")]) is None
    assert pins.chosen(root) is None
    assert pins.skipped(root) is None


def test_req079_ac5_an_unpinned_dependency_of_each_runtime_fails_in_its_file(
    tmp_path: Path,
) -> None:
    pins = pins_module()
    root = two_runtimes(tmp_path)
    node_files(root, spec="^4.21.1")
    py_files(root / "service", req="examplelib>=1\n")
    result = check(root)
    assert result.returncode == 1, result.stdout
    assert "not pinned exactly (component class: dependency)" in result.stdout
    assert pins.counts(root, {}) == {"package.json": 1, "service/requirements.txt": 1}
    no_values(result.stdout + result.stderr)
    assert "service" not in result.stdout


def test_req079_ac5_a_missing_lock_of_one_runtime_is_that_lock_only(tmp_path: Path) -> None:
    pins = pins_module()
    root = two_runtimes(tmp_path)
    (root / "service" / "requirements.lock").unlink()
    node_files(root, spec="^4")
    assert pins.counts(root, {}) == {"package.json": 1, "service/requirements.lock": 1}
    assert "the lock file is missing (component class: lock file)" in check(root).stdout


def test_req079_ac5_a_runtime_in_two_folders_is_one_finding(tmp_path: Path) -> None:
    pins = pins_module()
    root = two_runtimes(tmp_path)
    py_files(root / "worker", req="examplelib>=1\n")
    node_files(root, spec="^4")
    result = check(root)
    assert result.returncode == 1
    assert (
        "a runtime's build file is in more than one folder (component class: build file)"
        in result.stdout
    )
    assert pins.counts(root, {}) == {"package.json": 1, "service/requirements.txt": 1}


def test_req079_ac5_both_runtimes_at_the_root_are_both_read(tmp_path: Path) -> None:
    pins = pins_module()
    root = project(tmp_path, record(a_parts=TWO_PARTS, status="Accepted", chosen="Option A"))
    node_files(root)
    py_files(root, req="examplelib\n")
    assert pins.counts(root, {}) == {"requirements.txt": 1}
    py_files(root)
    assert check(root).stdout == "ok pins\n"


def test_req079_ac5_a_tracked_node_modules_build_file_is_ignored(tmp_path: Path) -> None:
    root = two_runtimes(tmp_path)
    node_files(root / "node_modules" / "example-dep", spec="^1")
    assert check(root).stdout == "ok pins\n"


def test_req079_ac5_only_tracked_files_place_a_runtime(tmp_path: Path) -> None:
    root = two_runtimes(tmp_path)
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    py_files(root / "worker", req="examplelib>=1\n")  # not tracked: not a second folder
    assert check(root).stdout == "ok pins\n"


def test_req079_ac5_a_part_is_compared_with_its_own_runtimes_lock(tmp_path: Path) -> None:
    pins = pins_module()
    root = two_runtimes(tmp_path)
    node_files(root, extra={"node_modules/examplelib": {"version": "9.9.9"}})
    assert check(root).stdout == "ok pins\n"
    py_files(root / "service", lock=f"examplelib==1.2.4 \\\n    {HASH}\n")
    assert {f for _, f in pins.check(root, {})} == {"service/requirements.lock"}


def test_req079_ac5_a_third_runtime_with_no_reader_is_not_checked(tmp_path: Path) -> None:
    root = two_runtimes(tmp_path, parts=TWO_PARTS.replace(" (verify)", ", Go 1.23.2 BSD-3-Clause"))
    assert check(root).stdout == "ok pins\n"


@pytest.mark.parametrize(("status", "chosen"), [("Proposed", "none yet"), ("Accepted", "none yet")])
def test_req079_ac5_a_record_not_accepted_is_still_no_stack(
    tmp_path: Path, status: str, chosen: str
) -> None:
    root = project(tmp_path, record(a_parts=TWO_PARTS, status=status, chosen=chosen))
    node_files(root)
    assert check(root).stdout == "pins: not run: no stack chosen\n"


def test_req079_ac5_no_work_type_is_still_no_stack(tmp_path: Path) -> None:
    assert check(two_runtimes(tmp_path, toml="")).stdout == "pins: not run: no stack chosen\n"


def test_req079_ac5_the_wait_holds_only_while_every_runtime_waits(tmp_path: Path) -> None:
    pins = pins_module()
    root = project(tmp_path, record(a_parts=TWO_PARTS, status="Accepted", chosen="Option A"), INIT)
    (root / "package.json").write_text('{"name": "sample"}', encoding="utf-8")
    assert pins.waiting(root) is True
    node_files(root, spec="4.21.1")
    assert pins.waiting(root) is False
    assert "the build file is missing or unreadable" in check(root).stdout


def test_req079_ac5_the_runner_runs_pins_for_two_runtimes(tmp_path: Path) -> None:
    root = two_runtimes(tmp_path)
    node_files(root, spec="^4")
    rows = gate_rows(root)
    assert (None, "pins: no stack chosen") not in rows, rows
    assert any(ok is False and "pins" in str(name) for ok, name in rows), rows


def test_req079_ac5_every_single_runtime_reader_is_named_in_its_adr() -> None:
    """Answer 9: a module that reads `pins.chosen` or `pins.pick` is named in ADR-0800's list."""
    import re  # noqa: PLC0415

    adr = next((KIT_ROOT / "docs" / "adr").glob("0800-*.md")).read_text(encoding="utf-8")
    listed = adr.split("Single-runtime readers:", 1)[1].split("\n\n", 1)[0]
    reads = re.compile(r"\bpins\.(chosen|pick)\(|from gates\.pins import [^\n]*\b(chosen|pick)\b")
    found = sorted(
        p.relative_to(KIT_ROOT).as_posix()
        for p in (KIT_ROOT / "scripts" / "agk").rglob("*.py")
        if p.name != "pins.py" and reads.search(p.read_text(encoding="utf-8"))
    )
    assert found, "no reader found: the pattern no longer matches"
    assert [f for f in found if f"`{f}`" not in listed] == []


def test_req079_ac5_a_baseline_without_the_new_paths_counts_them_as_new(tmp_path: Path) -> None:
    """Answer 6: an adopted gate file that lacks a runtime's paths counts them as new findings;
    `--baseline` lowers a line it holds and never adds or raises one."""
    root = two_runtimes(tmp_path, toml='mode = "adopt"\n[delivery]\nwork_type = "web-app"\n')
    node_files(root, spec="^4")
    py_files(root / "service", req="examplelib>=1\n")
    gate = root / "config" / "agk-baseline" / "pins.txt"
    gate.parent.mkdir(parents=True)
    gate.write_text("package.json 1\n", encoding="utf-8")
    rows = gate_rows(root)
    assert any(p is False and "SPEC-0072 rule 7" in line for p, line in rows), rows
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import run_gates  # noqa: PLC0415 - the gate runner itself

    run_gates.results(root, write=True)
    assert gate.read_text(encoding="utf-8") == "package.json 1\n"
    assert any(p is False for p, _ in gate_rows(root))
    node_files(root)
    run_gates.results(root, write=True)
    assert "package.json 1" not in gate.read_text(encoding="utf-8")


def test_req079_ac5_the_plugin_layout_reads_the_same_files(tmp_path: Path) -> None:
    """Answer 6: `[kit] layout` installed or `plugin`, the steps read `--root`'s files alike."""
    pins = pins_module()
    plugin = (
        '[kit]\nlayout = "plugin"\nplugin_version = "0.1.0"\n[delivery]\nwork_type = "web-app"\n'
    )
    roots = [two_runtimes(tmp_path / "a"), two_runtimes(tmp_path / "b", toml=plugin)]
    for root in roots:
        node_files(root, spec="^4")
        py_files(root / "service", req="examplelib>=1\n")
    assert check(roots[0]).stdout == check(roots[1]).stdout
    assert pins.counts(roots[1], {}) == {"package.json": 1, "service/requirements.txt": 1}
