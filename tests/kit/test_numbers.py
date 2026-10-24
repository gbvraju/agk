"""Tests of scripts/agk/check_numbers.py (SPEC-0025 rule 1; REQ-032 AC1).

Two requirements, two specs or two ADRs with the same number fail; the message names the rule and
the id, never a title. The check reads files only.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REQS = (
    "# Requirements\n\n### REQ-001 — Secret title one\n\n- Status: planned\n\n### REQ-002 — Two\n"
)


def start(repo, **files):
    base = {"docs/requirements.md": REQS, "docs/specs/0001-a.md": "# SPEC-0001: a\n"}
    base["docs/adr/0001-a.md"] = "# ADR-0001: a\n"
    repo.commit({**base, **files}, "base")


def check(repo):
    return repo.run("check_numbers.py")


def test_ac1_unique_numbers_pass_and_the_templates_are_not_numbers(repo):
    """REQ-032 AC1: rule 1 (a tree with no duplicate passes)."""
    start(
        repo, **{"docs/adr/TEMPLATE.md": "# ADR-NNNN\n", "docs/specs/TEMPLATE.md": "# SPEC-NNN\n"}
    )
    proc = check(repo)
    assert (proc.returncode, proc.stdout) == (0, "ok numbers\n")


def test_ac1_a_tree_without_the_docs_passes(repo):
    """REQ-032 AC1: rule 1 (nothing to compare is not a failure)."""
    repo.commit({"a.txt": "x\n"}, "base")
    assert check(repo).returncode == 0


@pytest.mark.parametrize(
    ("files", "needle"),
    [
        ({"docs/specs/0001-b.md": "# SPEC-0001: b\n"}, "SPEC-0001"),
        ({"docs/adr/0001-b.md": "# ADR-0001: b\n"}, "ADR-0001"),
        (
            {"docs/requirements.md": REQS + "\n### REQ-001 — Again\n\n- Status: planned\n"},
            "REQ-001",
        ),
    ],
    ids=["spec", "adr", "requirement"],
)
def test_ac1_two_with_the_same_number_fail_naming_the_rule_and_the_id(repo, files, needle):
    """REQ-032 AC1: rule 1 (the id is named, the title never)."""
    start(repo, **files)
    proc = check(repo)
    assert proc.returncode == 1
    assert proc.stdout.startswith("FAIL numbers: rule 1") and needle in proc.stdout
    assert "Secret title" not in proc.stdout


def test_ac1_it_reads_files_only_and_imports_no_network_module():
    """REQ-032 AC1: rule 7 (no network call in a check)."""
    root = Path(__file__).resolve().parents[2]
    tree = ast.parse((root / "scripts" / "agk" / "check_numbers.py").read_text(encoding="utf-8"))
    names = {
        a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    names |= {
        n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module
    }
    assert not names & {"socket", "urllib", "http", "requests", "ssl", "subprocess"}
