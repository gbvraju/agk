"""Retired requirements and untagged tests (brief 244 build a; SPEC-0004 rule 24, SPEC-0010 26).

`retired` joins the requirement statuses. A retired requirement's `REQ-nnn` markers fail
`check_requirements`, naming the requirement and the file and never the test's text, so the pull
request that retires a requirement removes its tests or retags them. The weekly drift audit lists
the test files that carry no marker (D8, never blocking), and `traceability.py` shows both."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import drift_fixtures as fx
import pytest
from test_check_requirements import check, reqs
from test_drift_audit import SUMMARY, audit, findings

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

ROOT = Path(__file__).resolve().parents[2]


# --- the status and the block (answer 1) --------------------------------------------------------


def test_retired_is_an_allowed_status(repo):
    repo.commit({"docs/requirements.md": reqs(("REQ-001", "retired"), ("REQ-002", "planned"))})
    assert check(repo).returncode == 0


def test_an_unknown_status_still_fails_and_the_message_lists_retired(repo):
    repo.commit({"docs/requirements.md": reqs(("REQ-001", "gone"))})
    proc = check(repo)
    assert proc.returncode == 1
    assert "planned, in-progress, done, retired" in proc.stdout and "gone" not in proc.stdout


def test_retiring_with_the_markers_left_fails_naming_the_requirement_and_the_file(repo):
    secret = "THE-TEXT-OF-THE-TEST-NOT-TO-BE-ECHOED"
    repo.commit(
        {
            "docs/requirements.md": reqs(("REQ-001", "retired")),
            "tests/test_old.py": f"# REQ-001\ndef test_old():\n    assert '{secret}'\n",
            "tests/test_other.py": "# REQ-001 AC1\n",
        }
    )
    proc = check(repo)
    assert proc.returncode == 1
    assert "REQ-001" in proc.stdout and "retired" in proc.stdout
    assert "tests/test_old.py" in proc.stdout and "tests/test_other.py" in proc.stdout
    assert secret not in proc.stdout


def test_retiring_with_the_markers_removed_or_retagged_passes(repo):
    repo.commit(
        {
            "docs/requirements.md": reqs(("REQ-001", "retired"), ("REQ-002", "done")),
            "tests/test_old.py": "# REQ-002\n",  # retagged to a requirement it still proves
        }
    )
    assert check(repo).returncode == 0


def test_a_retired_requirement_needs_no_marker_and_no_criteria(repo):
    repo.commit({"docs/requirements.md": reqs(("REQ-001", "retired"))})
    proc = check(repo)
    assert proc.returncode == 0 and "warn" not in proc.stdout


def test_the_block_falls_only_on_a_retired_requirement(repo):
    repo.commit(
        {
            "docs/requirements.md": reqs(("REQ-001", "done"), ("REQ-002", "planned")),
            "tests/test_a.py": "# REQ-001\n# REQ-002\n",
        }
    )
    assert check(repo).returncode == 0


# --- the audit (answer 2) -----------------------------------------------------------------------


def commit_tests(repo, files: dict[str, str]) -> None:
    for rel, text in files.items():
        repo.write(rel, text)
    repo.commit(1)


def d8(root) -> list[tuple[str, str, str, str]]:
    return [f for f in findings(root) if f[0] == "D8"]


def test_untagged_test_files_are_listed_with_a_count_and_never_block(tmp_path):
    repo = fx.base(tmp_path / "repo")
    commit_tests(
        repo,
        {
            "tests/test_tagged.py": "# REQ-001\n",
            "tests/test_a.py": "def test_a():\n    assert 1\n",
            "tests/sub/test_b.py": "def test_b():\n    assert 2\n",
            "tests/helper.py": "x = 1\n",  # not a test file by the configured pattern
        },
    )
    found = d8(repo.root)
    assert len(found) == 1
    code, subject, rule, sentence = found[0]
    assert subject == "tests" and rule == "SPEC-0004 rule 24"
    assert sentence.startswith("2 test files carry no requirement marker")
    assert "tests/test_a.py" in sentence and "tests/sub/test_b.py" in sentence
    assert "test_tagged" not in sentence and "helper.py" not in sentence
    assert audit(repo.root).returncode == 0
    summary = SUMMARY.match(audit(repo.root).stdout.splitlines()[0])
    assert summary and summary.group(12) == "1"


def test_a_project_with_every_test_tagged_gets_no_finding(tmp_path):
    repo = fx.base(tmp_path / "repo")
    commit_tests(repo, {"tests/test_tagged.py": "# REQ-001\n", "tests/test_two.py": "# REQ-099\n"})
    assert d8(repo.root) == []


def test_the_listing_is_capped_and_says_how_many_more(tmp_path):
    repo = fx.base(tmp_path / "repo")
    commit_tests(repo, {f"tests/test_{i:02d}.py": "x = 1\n" for i in range(25)})
    (finding,) = d8(repo.root)
    assert finding[3].startswith("25 test files carry no requirement marker")
    assert "and 5 more" in finding[3] and "tests/test_19.py" in finding[3]
    assert "tests/test_20.py" not in finding[3]


def test_the_finding_never_quotes_file_content(tmp_path):
    repo = fx.base(tmp_path / "repo")
    mark = "UNIQUE-CONTENT-WORDS-NOT-TO-BE-ECHOED"
    commit_tests(repo, {"tests/test_a.py": f"# {mark}\n"})
    assert mark not in audit(repo.root).stdout


# --- traceability (answer 3) --------------------------------------------------------------------


def trace(repo):
    proc = repo.run("traceability.py")
    assert proc.returncode == 0, proc.stdout
    return proc.stdout


def test_traceability_ends_with_the_retired_requirements_and_the_untagged_test_files(repo):
    repo.commit(
        {
            "docs/requirements.md": reqs(
                ("REQ-001", "done"), ("REQ-002", "retired"), ("REQ-003", "retired")
            ),
            "tests/test_tagged.py": "# REQ-001\n",
            "tests/test_loose.py": "def test_x():\n    assert 1\n",
        }
    )
    out = trace(repo).splitlines()
    assert "| REQ-002 | retired | - |" in out
    assert out[-3:] == [
        "",
        "Retired: REQ-002, REQ-003",
        "Untagged test files (1): tests/test_loose.py",
    ]


def test_traceability_is_unchanged_when_nothing_is_retired_or_untagged(repo):
    repo.commit(
        {"docs/requirements.md": reqs(("REQ-001", "done")), "tests/test_t.py": "# REQ-001\n"}
    )
    out = trace(repo)
    assert out.splitlines()[-1] == "| REQ-001 | done | tests/test_t.py |"
    assert "Retired" not in out and "Untagged" not in out


# --- the words (answers 1 and 3) ----------------------------------------------------------------


@pytest.mark.parametrize("rel", ["docs/requirements.md", "kit/templates/requirements.md"])
def test_the_requirements_file_header_lists_the_four_statuses(rel):
    text = (ROOT / rel).read_text(encoding="utf-8")
    assert re.search(r"\(planned \| in-progress \| done \| retired\)", text)


def test_the_facts_read_a_retired_requirement_as_unknown_and_do_not_fail(repo):
    """ADR-0151 reading: schema 6 and 7 do not list the status yet (a later brief may)."""
    import facts

    repo.commit({"docs/requirements.md": reqs(("REQ-001", "retired"))})
    (found,) = facts.requirements_section(repo.root)
    assert found["id"] == "REQ-001" and found["status"] == "unknown"
