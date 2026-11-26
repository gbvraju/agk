"""Tests of scripts/agk/test_audit.py, the read-only report of a test suite (brief #2007, ADR-0831).

A fixture suite in a temporary repository: two equal tests, one wording-only test, one
brief-pinned name, one file no map entry names, a file that does not parse and a prepush record
with per-file timing. Invented data only (example.com); no network.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys

import pytest

PROOF = '[proof.kit]\ndirs = ["tests"]\npatterns = ["test_*.py"]\ncommand = "pytest {files}"\n'
MAP = (
    '[testing]\nwhole_tests = ["tests/test_whole.py"]\n'
    '[[testing.map]]\ncode = "app/*.py"\ntests = ["tests/test_a.py", "tests/test_b.py"]\n'
)
A = '''import app_mod

def test_one():
    """First copy."""
    x = 1
    assert x == 1

def test_brief_1234_rule():
    assert app_mod.run() == 2
'''
B = '''from pathlib import Path

GUIDE = "docs/guide.md"

def test_two():
    """Second copy, other words."""
    x = 1
    assert x == 1

def read(name):
    return Path(name).read_text()

def test_guide_names_the_site():
    text = read(GUIDE)
    assert "example.com" in text and "site" in text

class TestKind:
    def test_method(self):
        assert 3 == 3

@pytest.mark.parametrize("n", [1, 2])
def test_many(n):
    assert n
'''
FILES = {
    "agk.toml": PROOF + MAP,
    "app/app_mod.py": "def run():\n    return 2\n",
    "docs/guide.md": "example.com site\n",
    "tests/test_a.py": A,
    "tests/test_b.py": B,
    "tests/test_whole.py": "def test_whole():\n    assert True\n",
    "tests/test_lonely.py": "def test_lonely():\n    assert 1\n",
    "tests/test_broken.py": "def test_x(:\n",
}


def start(repo, toml: str | None = None) -> None:
    repo.commit({**FILES, **({"agk.toml": toml} if toml is not None else {})}, "base")


def audit(repo, *args: str):
    return repo.run("test_audit.py", *args)


def data(repo, *args: str) -> dict:
    proc = audit(repo, "--json", *args)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_the_counts_and_every_list(repo):
    """REQ-051: brief #2007 answers 1 and 2 (sizes, equal, wording-only, pinned, unselected)."""
    start(repo)
    got = data(repo)
    assert got["files"] == 5 and got["functions"] == 8
    assert got["not_read"] == ["tests/test_broken.py"]
    assert got["code_lines"] == 2 and got["test_lines"] > 20
    assert got["equal"]["count"] == 1 and got["equal"]["extra"] == 1
    assert got["equal"]["groups"] == [["tests/test_a.py::test_one", "tests/test_b.py::test_two"]]
    assert got["wording"]["names"] == ["tests/test_b.py::test_guide_names_the_site"]
    assert got["pinned"]["names"] == ["tests/test_a.py::test_brief_1234_rule"]
    assert got["unselected"]["names"] == ["tests/test_broken.py", "tests/test_lonely.py"]
    assert got["slowest"]["note"] == "per-file timing: unknown"


def test_the_text_report_says_the_lists_are_candidates(repo):
    """REQ-051: brief #2007 answers 1 and 2 (the text form; a list, never a verdict)."""
    start(repo)
    proc = audit(repo)
    assert proc.returncode == 0
    out = proc.stdout
    assert "test audit: 5 test files, 8 test functions" in out
    assert "not read: tests/test_broken.py" in out and out.count("tests/test_broken.py") == 2
    assert "equal tests: 1 groups, 1 extra copies" in out
    assert "never a ruling" in out


def test_slowest_files_come_from_the_newest_prepush_record(repo):
    """REQ-051: brief #2007 answer 2 (e) (the record's per-file timing, slowest first)."""
    start(repo)
    common = repo.git("rev-parse", "--git-common-dir").strip()
    folder = repo.root / common / "agk-evidence"
    folder.mkdir(parents=True)
    files = [{"path": "tests/test_a.py", "seconds": 1.5}, {"path": "tests/test_b.py", "seconds": 4}]
    run = {"timing": {"source": "durations", "total_seconds": 5.5, "files": files}}
    (folder / "x.json").write_text(json.dumps({"steps": [{"name": "tests", "runs": [run]}]}))
    got = data(repo, "--limit", "1")
    assert got["slowest"]["count"] == 2
    assert got["slowest"]["files"] == [{"path": "tests/test_b.py", "seconds": 4}]


def test_since_counts_added_and_removed_test_lines(repo):
    """REQ-051: brief #2007 answer 1 (`--since`, from local git)."""
    start(repo)
    repo.commit({"tests/test_lonely.py": None}, "drop")
    got = data(repo, "--since", "2000-01-01")
    assert got["since"] == {"day": "2000-01-01", "added": 9, "removed": 1}
    assert data(repo, "--since", "2099-01-01")["since"]["added"] == 0


def test_no_testing_table_says_no_testing_map(repo):
    """REQ-051: brief #2007 answer 6 (no `[testing]`: list (d) says so, the rest print)."""
    start(repo, toml=PROOF)
    got = data(repo)
    assert got["unselected"] == {"note": "no testing map"}
    assert got["equal"]["count"] == 1
    assert "unselected files: no testing map" in audit(repo).stdout


def test_no_proof_table_reads_tests_by_default(repo):
    """REQ-051: brief #2007 answer 6 (`[proof]` absent: `tests/` with `test_*.py`)."""
    start(repo, toml=MAP)
    assert data(repo)["files"] == 5


def test_a_malformed_map_is_refused_naming_the_setting(repo):
    """REQ-051: brief #2007 answer 6 (a malformed table, named by its setting)."""
    start(repo, toml=PROOF + '[testing]\nmap = "app/secret-value"\n')
    proc = audit(repo)
    assert proc.returncode == 2
    assert "setting: testing.map" in proc.stderr and "secret-value" not in proc.stderr


@pytest.mark.parametrize(
    "args", [("--limit", "0"), ("--limit", "x"), ("--limit",), ("--since", "26-11"), ("--nope",)]
)
def test_a_bad_option_exits_2_naming_it(repo, args):
    """REQ-051: brief #2007 answer 1 (a malformed argument exits 2 naming the option)."""
    start(repo)
    proc = audit(repo, *args)
    assert proc.returncode == 2
    assert args[0] in proc.stderr


def test_it_writes_nothing_and_imports_no_network_module(repo):
    """REQ-051: brief #2007 answers 1 and 9 (reads only; the standing import ruling's set)."""
    start(repo)
    before = sorted(p.relative_to(repo.root) for p in repo.root.rglob("*"))
    assert audit(repo, "--since", "2000-01-01").returncode == 0
    assert sorted(p.relative_to(repo.root) for p in repo.root.rglob("*")) == before
    kit = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "rev-parse", "--show-toplevel"],
        cwd=__file__.rsplit("/", 1)[0],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "scripts/agk/rules.py", "imports", "scripts/agk/test_audit.py"],
        cwd=kit,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
