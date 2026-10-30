"""A local check run leaves a record of what ran (brief #374, ADR-0208).

`scripts/agk/prepush.py --record FILE` writes one JSON record of the run: `schema: 1`, the head
and base shas, when it started, whether the work tree was clean, and for each step its name,
argument list, folder, exit code, seconds and a digest of its output (never the output text), with
the versions of python3, git, make and gitleaks where found. It prints one `Evidence:` line for the
pull request body. Without `--record` nothing changes; a failed step still writes the record and
the exit code stays 1.

The fixture repositories are those of `test_prepush.py`: a stand-in `agk.mk`, `Makefile` and
`gitleaks`, so each step can be made to pass or fail on its own.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest
from test_prepush import MK_FAIL, TOML, path_with, project, scanner, steps

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
EVIDENCE = re.compile(
    r"^Evidence: prepush schema 1, head ([0-9a-f]{12}), (\d+) steps ok, record ([0-9a-f]{12})$",
    re.M,
)
SECRET = "s3cr3t-value-that-must-not-leak"
OUTPUT_MARK = "TEST_OUTPUT_TEXT_MARK"


@pytest.fixture
def outside(tmp_path_factory) -> Path:
    """A folder outside the fixture repository, so the record and its files keep the tree clean."""
    return tmp_path_factory.mktemp("outside")


def run(repo, *args: str, scan: Path | None = None, **env: str):
    return repo.run("prepush.py", *args, PATH=path_with(scan), **env)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_an_all_ok_run_writes_the_record_and_the_evidence_line(repo, outside):
    """REQ-039: brief #374 answers 1, 2 and 5 (an all-ok run)."""
    project(repo)
    record = outside / "record.json"
    proc = run(repo, "--record", str(record), scan=scanner(outside / "bin", 0))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = load(record)
    assert data["schema"] == 1
    assert data["head"] == repo.git("rev-parse", "HEAD").strip()
    assert data["base"] == repo.git("rev-parse", "main").strip()
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", data["started"])
    assert data["tree_clean"] is True
    names = [s["name"] for s in data["steps"]]
    assert names == ["pr-body", "lint", "governance", "secret-scan", "tests"]
    for step in data["steps"]:
        assert set(step) >= {"name", "argv", "cwd", "exit", "seconds", "output_sha256"}
        assert "output_bytes" in step
        assert isinstance(step["argv"], list)
        assert isinstance(step["seconds"], float | int) and step["seconds"] >= 0
    lint = next(s for s in data["steps"] if s["name"] == "lint")
    assert lint["argv"] == ["make", "lint"] and lint["cwd"] == "." and lint["exit"] == 0
    out = "LINT_RAN".encode()
    assert lint["output_sha256"] == hashlib.sha256(out).hexdigest()
    assert lint["output_bytes"] == len(out)
    body = next(s for s in data["steps"] if s["name"] == "pr-body")
    assert body["outcome"] == "skipped" and body["exit"] is None
    assert data["versions"]["python3"] == ".".join(map(str, sys.version_info[:3]))
    assert data["versions"]["git"] and "gitleaks" in data["versions"]
    found = EVIDENCE.search(proc.stdout)
    assert found, proc.stdout
    assert found.group(1) == data["head"][:12]
    ok = sum(1 for s in data["steps"] if s["outcome"] == "ok")
    assert int(found.group(2)) == ok == 4
    assert found.group(3) == hashlib.sha256(record.read_bytes()).hexdigest()[:12]
    assert "prepush: all steps passed" in proc.stdout


def test_the_tests_step_records_each_run_it_made(repo, outside):
    """REQ-039: brief #374 answer 1 (the tests step: the command of each run, with its digest)."""
    project(repo)
    record = outside / "record.json"
    proc = run(repo, "--record", str(record), scan=scanner(outside / "bin", 0))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    tests = next(s for s in load(record)["steps"] if s["name"] == "tests")
    assert tests["exit"] == 0
    assert [r["command"] for r in tests["runs"]] == ["echo RAN_PROJECT_TESTS"]
    run_one = tests["runs"][0]
    assert run_one["exit"] == 0 and run_one["cwd"] == "."
    want = hashlib.sha256(b"RAN_PROJECT_TESTS\n").hexdigest()
    assert run_one["output_sha256"] == want


def test_a_failed_step_still_writes_the_record_and_exits_1(repo, outside):
    """REQ-039: brief #374 answers 3 and 5 (a failed step)."""
    project(repo, mk=MK_FAIL)
    record = outside / "record.json"
    proc = run(repo, "--record", str(record), scan=scanner(outside / "bin", 0))
    assert proc.returncode == 1
    assert steps(proc.stdout)["governance"] == "FAIL"
    data = load(record)
    assert [s["name"] for s in data["steps"]] == ["pr-body", "lint", "governance"]
    gov = data["steps"][-1]
    assert gov["outcome"] == "FAIL" and gov["exit"] == 1
    assert gov["argv"] == ["make", "-f", "agk.mk", "agk-governance"]
    assert data["result"] == "failed"
    found = EVIDENCE.search(proc.stdout)
    assert found and int(found.group(2)) == 1


def test_a_dirty_tree_is_recorded(repo, outside):
    """REQ-039: brief #374 answers 1 and 5 (a dirty tree is recorded, never hidden)."""
    project(repo)
    repo.write("src/code.txt", "uncommitted\n")
    record = outside / "record.json"
    proc = run(repo, "--quick", "--record", str(record), scan=scanner(outside / "bin", 0))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert load(record)["tree_clean"] is False


def test_gitleaks_missing_is_recorded_without_a_version(repo, outside):
    """REQ-039: brief #374 answers 1 and 5 (gitleaks missing)."""
    project(repo)
    record = outside / "record.json"
    proc = run(repo, "--quick", "--record", str(record), scan=None)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = load(record)
    assert "gitleaks" not in data["versions"]
    scan = next(s for s in data["steps"] if s["name"] == "secret-scan")
    assert scan["outcome"] == "skipped" and scan["not_run"] is True and scan["exit"] is None
    assert data["not_run"] == ["secret-scan"]
    assert EVIDENCE.search(proc.stdout)


def test_no_output_text_environment_value_or_outside_path_is_written(repo, outside):
    """REQ-039: brief #374 answers 1 and 5 (no output text and no environment value in the file)."""
    toml = TOML.replace("echo RAN_PROJECT_TESTS", f"echo {OUTPUT_MARK}; echo $AGK_TEST_SECRET")
    project(repo, toml=toml)
    body = outside / "body.md"
    body.write_text("Advances: REQ-001\n", encoding="utf-8")  # fails: the body step's own output
    record = outside / "record.json"
    proc = run(
        repo,
        "--body",
        str(body),
        "--record",
        str(record),
        scan=scanner(outside / "bin", 0),
        AGK_TEST_SECRET=SECRET,
    )
    assert proc.returncode == 1
    text = record.read_text(encoding="utf-8")
    assert "Summary" not in text  # the failing body check's message is not copied
    for value in (SECRET, str(outside), str(SCRIPTS), sys.executable, str(repo.root)):
        assert value not in text
    argv = load(record)["steps"][0]["argv"]
    assert argv[0] == "python3"
    assert "scripts/agk/check_pr_body.py" in argv and "<outside>/body.md" in argv

    # Without the bad body the tests run: their output (the mark and the secret) is digested only.
    proc = run(
        repo, "--record", str(record), scan=scanner(outside / "bin", 0), AGK_TEST_SECRET=SECRET
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    tests = next(s for s in load(record)["steps"] if s["name"] == "tests")
    out = f"{OUTPUT_MARK}\n{SECRET}\n".encode()
    assert tests["runs"][0]["output_sha256"] == hashlib.sha256(out).hexdigest()
    text = record.read_text(encoding="utf-8")
    assert OUTPUT_MARK not in text and SECRET not in text and "AGK_TEST_SECRET" not in text


def test_without_record_nothing_changes(repo, outside):
    """REQ-039: brief #374 answer 3 (without `--record`, prepush behaves exactly as before)."""
    project(repo)
    proc = run(repo, scan=scanner(outside / "bin", 0))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Evidence:" not in proc.stdout
    assert not list(repo.root.glob("*.json"))


def test_a_record_file_that_cannot_be_written_is_a_usage_error(repo, outside):
    """REQ-039: brief #374 answer 1 (the refusal names the option, never the value)."""
    project(repo)
    target = outside / "no-such-folder" / "record.json"
    proc = run(repo, "--quick", "--record", str(target), scan=scanner(outside / "bin", 0))
    assert proc.returncode == 2
    assert "--record" in proc.stdout + proc.stderr
    assert str(target) not in proc.stdout + proc.stderr


def test_record_without_a_file_is_a_usage_error(repo):
    """REQ-039: brief #374 answer 1 (`--record` takes a file)."""
    project(repo)
    proc = repo.run("prepush.py", "--record")
    assert proc.returncode == 2
