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


# --- `--pending` reads the records a merge of main brought in (brief #1370, ADR-0575) ----------

PENDING_ADR = "docs/adr/0002-second.md"
REVIEWERS = "version: 1\nverdict_authors: [reviewer]\n"


def final_record(pr: int, cid: int, number: str = "0002") -> str:
    from common import MERGED_BY  # the merger's squash message line

    return f"Example (#{pr})\n\nADR-{number} Accepted (Final {cid})\n{MERGED_BY}\n"


def final_comment(pr: int, cid: int, path: str = PENDING_ADR) -> dict:
    return {
        "id": cid,
        "issue_url": f"https://api.example.com/repos/example-owner/example-repo/issues/{pr}",
        "user": {"login": "reviewer"},
        "body": f"Verdict: fix list a1b2c3d\n\nreviewed.\n\nFinal: {path} Proposed -> Accepted\n",
    }


def comments_at(repo, *items: dict) -> str:
    import json

    path = repo.root.parent / "final-comments.json"
    path.write_text(json.dumps(list(items)), encoding="utf-8")
    return str(path)


def release_branch(repo) -> None:
    """main holds two Proposed ADRs; a release branch starts from it."""
    repo.commit(
        {
            "config/reviewers.yaml": REVIEWERS,
            "docs/adr/0001-first.md": adr(),
            PENDING_ADR: adr("0002", status="Proposed"),
            "docs/adr/0003-third.md": adr("0003", status="Proposed"),
        },
        "base",
    )
    repo.branch("release")
    repo.commit({"CHANGELOG.md": "release\n"}, "release notes")


def pending(repo, saved: str):
    return repo.run("check_adrs.py", "--pending", "--comments", saved, "--base", "main")


def test_pending_lists_an_adr_whose_record_a_merge_of_main_brought_in(repo):
    """REQ-050: brief #1370 answer 1 (bug #1266: the record is on the second parent)."""
    release_branch(repo)
    repo.git("checkout", "-q", "main")
    repo.commit({"README.md": "x\n"}, final_record(7, 42))
    repo.git("checkout", "-q", "release")
    repo.git("merge", "-q", "--no-ff", "-m", "Merge main", "main")
    proc = pending(repo, comments_at(repo, final_comment(7, 42)))
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.splitlines() == [PENDING_ADR]


def test_pending_without_a_merge_of_main_lists_as_before(repo):
    """REQ-050: brief #1370 answer 2 (a record in HEAD's own history; none elsewhere)."""
    release_branch(repo)
    saved = comments_at(repo, final_comment(7, 42))
    assert pending(repo, saved).stdout == ""
    repo.commit({"README.md": "x\n"}, final_record(7, 42))
    proc = pending(repo, saved)
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.splitlines() == [PENDING_ADR]


def test_pending_lists_an_adr_once_when_head_and_the_merge_base_both_record_it(repo):
    """REQ-050: brief #1370 answer 1 (each ADR once)."""
    release_branch(repo)
    repo.git("checkout", "-q", "main")
    repo.commit({"README.md": "x\n"}, final_record(7, 42))
    repo.commit({"README.md": "y\n"}, final_record(8, 43, "0003"))
    repo.git("checkout", "-q", "-b", "later", "main")
    proc = pending(
        repo,
        comments_at(repo, final_comment(7, 42), final_comment(8, 43, "docs/adr/0003-third.md")),
    )
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.splitlines() == [PENDING_ADR, "docs/adr/0003-third.md"]


def test_pending_fails_closed_on_a_record_of_the_merge_base_without_the_comments(repo):
    """REQ-050: brief #1370 answer 1 (a record of the merge base is read like one of HEAD's)."""
    release_branch(repo)
    repo.git("checkout", "-q", "main")
    repo.commit({"README.md": "x\n"}, final_record(7, 42))
    repo.git("checkout", "-q", "release")
    repo.git("merge", "-q", "--no-ff", "-m", "Merge main", "main")
    proc = repo.run("check_adrs.py", "--pending", "--base", "main")
    assert proc.returncode == 1
    assert proc.stdout.startswith("FAIL adrs: rule 3a")
