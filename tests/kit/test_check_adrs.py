"""Tests of scripts/agk/check_adrs.py."""

from __future__ import annotations


def adr(num="0001", status="Accepted", extra="", date="2026-01-02", sections=True):
    text = (
        f"# ADR-{num}: Title\n\n- Status: {status}\n- Date: {date}\n- Deciders: maintainers\n"
        f"- Related: none\n- Requirements: REQ-004\n{extra}\n"
    )
    if sections:
        text += "## Context\n\nc\n\n## Decision\n\nd\n\n## Consequences\n\nq\n\n## Residual\n\nr\n"
    return text


def check(repo):
    return repo.run("check_adrs.py", "--base", "main")


def start(repo, **files):
    repo.commit({"docs/adr/0001-first.md": adr(), **files}, "base")
    repo.branch()


def test_valid_adr_passes(repo):
    """REQ-004"""
    start(repo)
    assert check(repo).returncode == 0


def test_missing_header_field_fails(repo):
    """REQ-004"""
    start(repo)
    repo.commit({"docs/adr/0002-x.md": adr("0002").replace("- Deciders: maintainers\n", "")})
    proc = check(repo)
    assert proc.returncode == 1
    assert "0002-x.md" in proc.stdout


def test_missing_section_fails(repo):
    """REQ-004"""
    start(repo)
    repo.commit({"docs/adr/0002-x.md": adr("0002", sections=False)})
    assert check(repo).returncode == 1


def test_bad_status_and_date_fail(repo):
    """REQ-004"""
    start(repo)
    repo.commit({"docs/adr/0002-x.md": adr("0002", status="Maybe")})
    assert check(repo).returncode == 1
    repo.commit({"docs/adr/0002-x.md": adr("0002", date="02/01/2026")})
    assert check(repo).returncode == 1


def test_filename_number_must_match_title_and_be_unique(repo):
    """REQ-004"""
    start(repo)
    repo.commit({"docs/adr/0002-x.md": adr("0001")})
    assert check(repo).returncode == 1


def test_template_is_not_checked(repo):
    """REQ-004"""
    start(repo)
    repo.commit({"docs/adr/TEMPLATE.md": "# ADR-NNNN: Title\n"})
    assert check(repo).returncode == 0


def test_ac1_accepted_adr_body_change_fails(repo):
    """REQ-004 AC1"""
    start(repo)
    repo.commit({"docs/adr/0001-first.md": adr().replace("\nd\n", "\nchanged\n")})
    proc = check(repo)
    assert proc.returncode == 1
    assert "0001-first.md" in proc.stdout


def test_ac1_accepted_adr_status_only_change_passes(repo):
    """REQ-004 AC1"""
    start(repo)
    repo.commit({"docs/adr/0001-first.md": adr(status="Superseded")})
    assert check(repo).returncode == 0


def test_ac1_accepted_adr_deleted_fails(repo):
    """REQ-004 AC1"""
    start(repo)
    repo.commit({"docs/adr/0001-first.md": None})
    assert check(repo).returncode == 1


def test_proposed_adr_may_change(repo):
    """REQ-004 AC1"""
    repo.commit({"docs/adr/0001-first.md": adr(status="Proposed")}, "base")
    repo.branch()
    repo.commit({"docs/adr/0001-first.md": adr(status="Proposed").replace("\nd\n", "\nz\n")})
    assert check(repo).returncode == 0


def test_ac2_amends_must_reference_existing_adr(repo):
    """REQ-004 AC2"""
    start(repo)
    repo.commit({"docs/adr/0002-x.md": adr("0002", extra="- Amends: ADR-0001\n")})
    assert check(repo).returncode == 0
    repo.commit({"docs/adr/0003-y.md": adr("0003", extra="- Amends: ADR-0042\n")})
    assert check(repo).returncode == 1


def test_no_base_locally_still_checks_format(repo):
    """REQ-004"""
    repo.commit({"docs/adr/0001-first.md": adr().replace("- Date: 2026-01-02\n", "")})
    repo.git("branch", "-m", "trunk")
    proc = repo.run("check_adrs.py")
    assert proc.returncode == 1
