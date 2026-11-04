"""Tests of the `Covered-by:` line of scripts/agk/check_protected_changes.py (brief #545, ADR-0271).

A build of an Approved spec covers its protected change by naming its requirement's Accepted ADR
in one `Covered-by: ADR-nnnn` line of the pull request body (owner ruling D1 on plan #542). The
body is read from `--body FILE` or from the file that `AGK_PR_BODY` names. Invented data only.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

REQS = "# Requirements\n\n### REQ-001 — A\n\n- Acceptance: AC1\n- Status: planned\n"
CLASSES = "constitution/ config/ .github/ docs/requirements.md scripts/agk/"


def adr(status: str = "Accepted", names: str = "config/ scripts/agk/", reqs: str = "REQ-001"):
    return (
        "# ADR-0009: Intake of an invented requirement\n\n"
        f"- Status: {status}\n- Date: 2026-01-01\n- Deciders: maintainers\n- Related: none\n"
        f"- Requirements: {reqs}\n\n## Decision\n\nThe build changes {names}.\n"
    )


def body(*covered: str, advances: str = "REQ-001") -> str:
    lines = [f"Advances: {advances}", "Build-state row: 2026-01-02 | x | REQ-001"]
    lines += [f"Covered-by: {c}" for c in covered]
    return "\n".join(lines) + "\n"


def make_base(repo, adr_text: str | None = None):
    files = {
        "config/protected-paths.txt": "# c\n" + "\n".join(CLASSES.split()) + "\n",
        "docs/requirements.md": REQS,
        "constitution/principles.md": "1. p\n",
        "config/x.txt": "x\n",
        "src/app.py": "x = 1\n",
    }
    if adr_text is not None:
        files["docs/adr/0009-intake-of-an-invented-requirement.md"] = adr_text
    repo.commit(files, "base")
    repo.branch()
    return repo


def check(repo, text: str | None, tmp_path: Path, via_env: bool = False):
    if text is None:
        return repo.run("check_protected_changes.py", "--base", "main")
    path = tmp_path / "pr-body.md"
    path.write_text(text, encoding="utf-8")
    if via_env:
        return repo.run("check_protected_changes.py", "--base", "main", AGK_PR_BODY=str(path))
    return repo.run("check_protected_changes.py", "--base", "main", "--body", str(path))


@pytest.fixture
def accepted(repo):
    return make_base(repo, adr())


def test_req001_accepted_adr_naming_the_class_passes(accepted, tmp_path):
    """REQ-001 AC1: an Accepted ADR on the base, naming the class, with its REQ in Advances."""
    accepted.commit({"config/x.txt": "y\n"})
    proc = check(accepted, body("ADR-0009"), tmp_path)
    assert proc.returncode == 0, proc.stdout
    assert "Covered-by" in proc.stdout


def test_req001_body_from_the_environment_passes(accepted, tmp_path):
    """REQ-001 AC1: prepush passes the body through AGK_PR_BODY."""
    accepted.commit({"config/x.txt": "y\n"})
    proc = check(accepted, body("ADR-0009"), tmp_path, via_env=True)
    assert proc.returncode == 0, proc.stdout


def test_req001_without_a_body_it_fails_as_today(accepted, tmp_path):
    """REQ-001 AC1: no body, no covering ADR: the old failure."""
    accepted.commit({"config/x.txt": "y\n"})
    proc = check(accepted, None, tmp_path)
    assert proc.returncode == 1
    assert "'config/'" in proc.stdout


def test_req001_proposed_adr_fails(repo, tmp_path):
    """REQ-001 AC1: a Proposed ADR never covers."""
    make_base(repo, adr(status="Proposed"))
    repo.commit({"config/x.txt": "y\n"})
    proc = check(repo, body("ADR-0009"), tmp_path)
    assert proc.returncode == 1
    assert "Accepted" in proc.stdout


def test_req001_accepted_adr_not_naming_the_class_fails(repo, tmp_path):
    """REQ-001 AC1 AC3: the ADR must name every changed class; the message names the class."""
    make_base(repo, adr(names="scripts/agk/"))
    repo.commit({"config/x.txt": "y\n"})
    proc = check(repo, body("ADR-0009"), tmp_path)
    assert proc.returncode == 1
    assert "'config/'" in proc.stdout


def test_req001_requirement_not_in_advances_fails(accepted, tmp_path):
    """REQ-001 AC1: the ADR's requirement must be one the body advances."""
    accepted.commit({"config/x.txt": "y\n"})
    proc = check(accepted, body("ADR-0009", advances="REQ-002"), tmp_path)
    assert proc.returncode == 1
    assert "Advances" in proc.stdout


def test_req001_two_covered_by_lines_fail(accepted, tmp_path):
    """REQ-001 AC1: exactly one `Covered-by:` line."""
    accepted.commit({"config/x.txt": "y\n"})
    proc = check(accepted, body("ADR-0009", "ADR-0009"), tmp_path)
    assert proc.returncode == 1
    assert "exactly one" in proc.stdout


def test_req001_malformed_covered_by_line_fails(accepted, tmp_path):
    """REQ-001 AC1: the line is `Covered-by: ADR-nnnn` and nothing else."""
    accepted.commit({"config/x.txt": "y\n"})
    proc = check(accepted, body("ADR-9 and more"), tmp_path)
    assert proc.returncode == 1


def test_req001_adr_added_in_the_same_change_set_fails(repo, tmp_path):
    """REQ-001 AC1: a `Covered-by:` ADR must already be on the merge base."""
    make_base(repo)
    repo.commit({"config/x.txt": "y\n", "docs/adr/0009-intake-of-an-invented-requirement.md": ""})
    # An empty added ADR names no class, so only the Covered-by path could pass it.
    proc = check(repo, body("ADR-0009"), tmp_path)
    assert proc.returncode == 1
    assert "merge base" in proc.stdout


def test_req001_status_raised_in_the_change_set_does_not_count(repo, tmp_path):
    """REQ-001 AC1: the status is read on the merge base, not in the change set."""
    make_base(repo, adr(status="Proposed"))
    path = "docs/adr/0009-intake-of-an-invented-requirement.md"
    repo.commit({"config/x.txt": "y\n", path: adr()})
    proc = check(repo, body("ADR-0009"), tmp_path)
    assert proc.returncode == 1


def test_req001_constitution_change_with_only_covered_by_fails(repo, tmp_path):
    """REQ-001 AC1: `Covered-by:` never covers `constitution/`."""
    make_base(repo, adr(names="constitution/ config/"))
    repo.commit({"constitution/principles.md": "1. q\n"})
    proc = check(repo, body("ADR-0009"), tmp_path)
    assert proc.returncode == 1
    assert "'constitution/'" in proc.stdout


@pytest.mark.parametrize("path", ["config/reviewers.yaml", ".github/workflows/governance.yml"])
def test_req001_reviewers_and_workflows_need_an_adr_of_their_own(repo, tmp_path, path):
    """REQ-001 AC1: brief #545 answer 3 (the reviewers file and the workflows keep their ADR)."""
    make_base(repo, adr(names="config/ .github/"))
    repo.commit({path: "changed\n"})
    proc = check(repo, body("ADR-0009"), tmp_path)
    assert proc.returncode == 1


def test_req001_adr_in_the_change_set_passes_as_before(repo, tmp_path):
    """REQ-001 AC1: an ADR in the change set naming the class still covers, body or not."""
    make_base(repo)
    repo.commit({"config/x.txt": "y\n", "docs/adr/0010-x.md": adr(status="Proposed")})
    assert check(repo, None, tmp_path).returncode == 0
    assert check(repo, body(), tmp_path).returncode == 0


def test_req001_unknown_adr_fails(accepted, tmp_path):
    """REQ-001 AC1: a `Covered-by:` ADR that is not on the merge base fails, naming the rule."""
    accepted.commit({"config/x.txt": "y\n"})
    proc = check(accepted, body("ADR-0042"), tmp_path)
    assert proc.returncode == 1
    assert "merge base" in proc.stdout


# --- the one sentence in principle 1 and in CLAUDE.md item 3 ------------------------------------

PRINCIPLE_1 = (
    "1. A protected change requires an ADR in the same PR, or, for a build of an Approved spec, "
    "a `Covered-by:` line naming that spec's Accepted ADR, which names the class."
)
OLD_PRINCIPLES = (
    "# Principles\n\nThe twelve rules. Briefs cite them by number.\n\n"
    "1. A protected change requires an ADR in the same PR.\n"
)
ITEM_3 = (
    "Protected paths (`config/protected-paths.txt`) change only with an ADR in the same PR that "
    "names each changed path class, or, for a build of an Approved spec, a `Covered-by:` line "
    "naming that spec's Accepted ADR, which names the class."
)


def flat(text: str) -> str:
    return " ".join(text.split())


def test_req001_principle_1_changed_by_exactly_the_one_sentence():
    """REQ-001: brief #545 answer 1 (principle 1 is the one sentence; the rest is unchanged)."""
    text = (ROOT / "constitution" / "principles.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert PRINCIPLE_1 in lines
    old = OLD_PRINCIPLES.splitlines()
    assert lines[: len(old) - 1] == old[:-1]
    assert lines[len(old) - 1] == PRINCIPLE_1
    rest = lines[len(old) :]
    assert [int(m.group(1)) for x in rest if (m := re.match(r"^(\d+)\. ", x))] == list(
        range(2, 13)
    )


def test_req001_claude_md_item_3_changed_by_exactly_the_one_sentence():
    """REQ-001: brief #545 answer 1 (item 3 of the core rules page carries the clause)."""
    page = (ROOT / "config" / "core-rules.md").read_text(encoding="utf-8")
    m = re.search(r"(?ms)^3\. (.*?)\n(?=\S)", page)
    assert m
    assert flat(m.group(1)) == flat(ITEM_3)
    assert page.count("`Covered-by:`") == 1
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Covered-by" not in claude
