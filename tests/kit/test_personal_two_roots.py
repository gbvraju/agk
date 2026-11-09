"""SPEC-0041 build (e): the private test map and the sidecar's own checks (brief #900, REQ-048).

Rule 16: in a sidecar the marker readers read `test-map.toml` and scan no test file. Rule 2: the
five file checks run unchanged with a sidecar as their working directory. Principle 10 becomes true
of the reader, and nothing is written into the product tree. Invented data only; no network.
"""

from __future__ import annotations

import hashlib
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import personal_state as ps  # noqa: E402

PERSON = "demo-dev"
RULE = "SPEC-0041 rule 16"
MAP = """
"REQ-101 AC1" = ["tests/test_cart.py::test_adds", "tests/test_cart.py::test_removes"]
"REQ-101 AC2" = ["tests/test_pay.py::TestPay::test_refund"]
"REQ-102 AC1" = ["src/shop/test_ship.py::test_label"]
"""
# A value no refusal may repeat (principle 8).
SENTINEL = "secret-looking-value.example.com"
REQ_101 = """
### REQ-101 — A customer can empty the cart

- Acceptance: AC1 the cart empties
- Status: done
"""
SPEC = """# SPEC-0001: A customer can empty the cart

- Status: Draft
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-101

Observed in code at example.com/cart.

## Contexts

- personal: the sidecar holds this spec
- kit, github, local, stacks: not applicable: an invented fixture
"""
ADR = """# ADR-0001: The cart empties in one step

- Status: Proposed
- Date: 2026-11-09
- Deciders: maintainers
- Related: SPEC-0001
- Requirements: REQ-101

## Context

Invented.

## Decision

Invented.

## Consequences

Invented.

## Residual

None.
"""
BRIEF = """Sentence: "A customer can empty the cart."

Answers:
1. The cart empties.

Advances: {req}
Size: S
Touches: docs/requirements.md
Contexts: personal (the sidecar); kit, github, local, stacks (not applicable: invented)
"""
CHECKS = ("check_requirements", "check_specs", "check_adrs", "check_numbers")


def sidecar(path: Path) -> Path:
    ps.make_sidecar(path, PERSON)
    return path


def write_map(root: Path, text: str) -> None:
    (root / "test-map.toml").write_text(text, encoding="utf-8")


def holding(path: Path) -> Path:
    """A sidecar with one requirement, one spec and one ADR of its own, and its map."""
    root = sidecar(path)
    requirements = root / "docs" / "requirements.md"
    requirements.write_text(requirements.read_text(encoding="utf-8") + REQ_101, encoding="utf-8")
    (root / "docs" / "specs" / "0001-empty-cart.md").write_text(SPEC, encoding="utf-8")
    (root / "docs" / "adr" / "0001-empty-cart.md").write_text(ADR, encoding="utf-8")
    write_map(root, '"REQ-101 AC1" = ["tests/test_cart.py::test_empties"]\n')
    return root


def run_check(root: Path, name: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / f"{name}.py"), *args],
        cwd=root,
        capture_output=True,
        text=True,
        env={k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")},
    )


def snapshot(root: Path) -> dict[str, tuple[str, int]]:
    return {
        path.relative_to(root).as_posix(): (
            hashlib.sha256(path.read_bytes()).hexdigest(),
            path.stat().st_mtime_ns,
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_the_map_gives_requirements_and_criteria(tmp_path):  # REQ-048
    root = sidecar(tmp_path / "state")
    write_map(root, MAP)
    want = {
        "REQ-101": ["tests/test_cart.py", "tests/test_pay.py"],
        "REQ-102": ["src/shop/test_ship.py"],
    }
    assert common.find_markers(root, ["tests"]) == want
    assert common.markers_for(root) == want
    assert common.find_ac_markers(root, ["tests"]) == [
        {"req": "REQ-102", "ac": "AC1", "file": "src/shop/test_ship.py", "line": 0},
        {"req": "REQ-101", "ac": "AC1", "file": "tests/test_cart.py", "line": 0},
        {"req": "REQ-101", "ac": "AC2", "file": "tests/test_pay.py", "line": 0},
    ]
    assert common.ac_markers_for(root) == common.find_ac_markers(root, ["tests"])


def test_a_sidecar_scans_no_test_file(tmp_path):  # REQ-048
    root = sidecar(tmp_path / "state")
    write_map(root, MAP)
    (root / "tests").mkdir()
    (root / "tests" / "test_stray.py").write_text("# REQ-777 AC9\n", encoding="utf-8")
    assert "REQ-777" not in common.find_markers(root, ["tests"])
    assert all(m["req"] != "REQ-777" for m in common.find_ac_markers(root, ["tests"]))


def test_no_map_file_gives_none_and_no_error(tmp_path):  # REQ-048
    root = sidecar(tmp_path / "state")
    (root / "test-map.toml").unlink()
    assert common.find_markers(root, ["tests"]) == {}
    assert common.find_ac_markers(root, ["tests"]) == []
    assert common.markers_for(root) == {}
    assert common.ac_markers_for(root) == []


def test_the_fresh_map_holds_no_entry(tmp_path):  # REQ-048
    root = sidecar(tmp_path / "state")
    assert common.find_markers(root, ["tests"]) == {}
    assert common.find_ac_markers(root, ["tests"]) == []


def test_a_repository_without_the_table_reads_as_today(tmp_path):  # REQ-048
    root = tmp_path / "repo"
    (root / "tests").mkdir(parents=True)
    (root / "agk.toml").write_text('test_dirs = ["tests"]\n', encoding="utf-8")
    (root / "tests" / "test_a.py").write_text(
        "# REQ-001 AC2\n\n# REQ-003, REQ-002 AC1\n", encoding="utf-8"
    )
    (root / "tests" / "test_b.py").write_text("# REQ-001\n", encoding="utf-8")
    (root / "tests" / "other.py").write_text("# REQ-009\n", encoding="utf-8")
    # A map file means nothing outside a sidecar.
    write_map(root, MAP)
    assert common.find_markers(root, ["tests"]) == {
        "REQ-001": ["tests/test_a.py", "tests/test_b.py"],
        "REQ-002": ["tests/test_a.py"],
        "REQ-003": ["tests/test_a.py"],
    }
    assert common.find_ac_markers(root, ["tests"]) == [
        {"req": "REQ-001", "ac": "AC2", "file": "tests/test_a.py", "line": 1},
        {"req": "REQ-002", "ac": "AC1", "file": "tests/test_a.py", "line": 3},
        {"req": "REQ-003", "ac": "AC1", "file": "tests/test_a.py", "line": 3},
        {"req": "REQ-001", "ac": None, "file": "tests/test_b.py", "line": 1},
    ]


@pytest.mark.parametrize(
    "text",
    [
        f'"REQ-101 AC1" = [ "{SENTINEL}::t"',  # not TOML
        f'"{SENTINEL}" = ["tests/test_a.py::t"]',  # a key that is not `REQ-nnn ACm`
        '"REQ-101" = ["tests/test_a.py::t"]',  # no criterion
        '"REQ-1 AC1" = ["tests/test_a.py::t"]',  # not a requirement id
        f'"REQ-101 AC1" = "{SENTINEL}::t"',  # not a list
        '"REQ-101 AC1" = []',  # no test id
        '"REQ-101 AC1" = [1]',  # not a string
        f'"REQ-101 AC1" = ["{SENTINEL}"]',  # not `path::name`
        '"REQ-101 AC1" = ["::t"]',  # no path
        '"REQ-101 AC1" = ["tests/test_a.py::"]',  # no name
        'REQ.AC1 = ["tests/test_a.py::t"]',  # a table, not a key
    ],
)
def test_a_malformed_map_is_refused_naming_the_rule(tmp_path, text):  # REQ-048
    root = sidecar(tmp_path / "state")
    write_map(root, text + "\n")
    for read in (common.find_markers, common.find_ac_markers):
        with pytest.raises(common.CheckError) as err:
            read(root, ["tests"])
        message = str(err.value)
        assert RULE in message and "test-map.toml" in message
        assert SENTINEL not in message


def test_a_map_that_is_not_text_is_refused(tmp_path):  # REQ-048
    root = sidecar(tmp_path / "state")
    (root / "test-map.toml").write_bytes(b'"REQ-101 AC1" = ["\xff::t"]\n')
    with pytest.raises(common.CheckError, match=RULE):
        common.find_markers(root, ["tests"])


def test_a_repeated_key_is_refused_naming_the_rule(tmp_path):  # REQ-048
    root = sidecar(tmp_path / "state")
    line = f'"REQ-101 AC1" = ["{SENTINEL}::t"]\n'
    write_map(root, line + line)
    with pytest.raises(common.CheckError) as err:
        common.find_markers(root, ["tests"])
    assert RULE in str(err.value) and "test-map.toml" in str(err.value)
    assert SENTINEL not in str(err.value)


@pytest.mark.parametrize("name", CHECKS)
@pytest.mark.parametrize("make", [sidecar, holding], ids=["fresh", "holding"])
def test_the_checks_pass_on_a_sidecar(tmp_path, make, name):  # REQ-048
    root = make(tmp_path / "state")
    done = run_check(root, name)
    assert done.returncode == 0, done.stdout + done.stderr


@pytest.mark.parametrize(
    ("make", "req"), [(sidecar, "REQ-001"), (holding, "REQ-101")], ids=["fresh", "holding"]
)
def test_check_brief_passes_on_a_sidecar(tmp_path, make, req):  # REQ-048
    root = make(tmp_path / "state")
    brief = tmp_path / "brief.md"
    brief.write_text(BRIEF.format(req=req), encoding="utf-8")
    done = run_check(root, "check_brief", str(brief), "--root", ".")
    assert done.returncode == 0, done.stdout + done.stderr


def test_a_done_requirement_needs_its_map_entry(tmp_path):  # REQ-048
    root = holding(tmp_path / "state")
    assert run_check(root, "check_requirements").returncode == 0
    write_map(root, "")
    done = run_check(root, "check_requirements")
    assert done.returncode == 1
    assert "REQ-101" in done.stdout


def test_the_product_tree_is_untouched(tmp_path):  # REQ-048
    clone = tmp_path / "clone"
    (clone / "tests").mkdir(parents=True)
    (clone / "tests" / "test_cart.py").write_text("def test_empties(): ...\n", encoding="utf-8")
    git = ("git", "-C", str(clone))
    who = ("-c", f"user.name={PERSON}", "-c", f"user.email={PERSON}@example.com")
    for args in (("init", "-q", "-b", "main"), ("add", "-A"), (*who, "commit", "-q", "-m", "one")):
        subprocess.run([*git, *args], check=True)  # nosec B603 - fixed argument list, no shell
    before = snapshot(clone)
    root = holding(tmp_path / "state")
    common.find_markers(root, ["tests"])
    common.find_ac_markers(root, ["tests"])
    for name in CHECKS:
        assert run_check(root, name).returncode == 0
    assert snapshot(clone) == before
