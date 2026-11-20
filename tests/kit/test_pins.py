"""Kit tests: pinned versions and licences in the stack record, and the stack's own build and lock
files (brief #1592, ADR-0672, amendments 200 and 201; REQ-036 AC4, REQ-079).

A Proposed stack record names each option's `Parts:`, each `<name> <exact version> <licence id>`;
`gates/pins.py write` writes the chosen stack's build file from `kit/templates/stacks/<stack>/` and
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
    result = run(PINS, "write", "--root", str(root))
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
    assert run(PINS, "write", "--root", str(root)).returncode == 0
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
    result = run(PINS, "write", "--root", str(root))
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
