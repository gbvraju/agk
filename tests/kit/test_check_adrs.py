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


# --- a decision cleared on a pull request merged by hand (brief #1738, ADR-0724) ---------------
# `--pending --pulls FILE` also lists an ADR of a squash commit the merger did not make,
# only when the latest verdict's Final verifies and the payload says that the head it named merged
# as that commit. Commits come from a temporary repository; comments and payloads are fixtures.

HEAD_A = "a" * 40
HEAD_B = "b" * 40


def hand_verdict(pr: int, cid: int, head: str = HEAD_A, path: str = PENDING_ADR, **extra) -> dict:
    return {
        "id": cid,
        "issue_url": f"https://api.example.com/repos/example-owner/example-repo/issues/{pr}",
        "user": {"login": "reviewer"},
        "created_at": extra.get("at", "2026-11-20T10:00:00Z"),
        "body": extra.get(
            "body", f"Verdict: fix list {head}\n\nreviewed.\n\nFinal: {path} Proposed -> Accepted\n"
        ),
    }


def pull_payload(pr: int, sha: str, head: str = HEAD_A, merged: bool = True) -> dict:
    return {"number": pr, "merged": merged, "merge_commit_sha": sha, "head": {"sha": head}}


def pulls_at(repo, *items) -> str:
    import json

    path = repo.root.parent / "pulls.json"
    path.write_text(json.dumps(list(items)), encoding="utf-8")
    return str(path)


def hand_world(repo, message: str = "Add the second decision (#7)", status: str = "Proposed"):
    """main: a base, then a squash commit `(#7)` that adds ADR-0002; a release branch from it."""
    repo.commit({"config/reviewers.yaml": REVIEWERS, "docs/adr/0001-first.md": adr()}, "base")
    repo.commit({PENDING_ADR: adr("0002", status=status)}, message)
    sha = repo.git("rev-parse", "HEAD").strip()
    repo.branch("release")
    repo.commit({"CHANGELOG.md": "release\n"}, "release notes")
    return sha


def pending_pulls(repo, comments: str, pulls: str):
    args = ("--pending", "--comments", comments, "--pulls", pulls, "--base", "main")
    return repo.run("check_adrs.py", *args)


def test_1738_a_hand_merged_decision_is_listed_with_pulls_only(repo):
    """REQ-035: brief #1738 answer 2 and edge case 5(a) (#1719's facts)."""
    sha = hand_world(repo)
    saved = comments_at(repo, hand_verdict(7, 42))
    assert pending(repo, saved).stdout == ""  # without --pulls nothing changes
    proc = pending_pulls(repo, saved, pulls_at(repo, pull_payload(7, sha)))
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.splitlines() == [PENDING_ADR]


def test_1738_a_verdict_on_an_older_head_is_never_accepted(repo):
    """REQ-035: brief #1738 edge case 5(c)."""
    sha = hand_world(repo)
    saved = comments_at(repo, hand_verdict(7, 42, head=HEAD_A))
    proc = pending_pulls(repo, saved, pulls_at(repo, pull_payload(7, sha, head=HEAD_B)))
    assert (proc.returncode, proc.stdout) == (0, "")


def test_1738_a_payload_naming_another_merge_commit_or_not_merged_is_not_accepted(repo):
    """REQ-035: brief #1738 edge case 5(h) and answer 2 (`merged: true`)."""
    sha = hand_world(repo)
    saved = comments_at(repo, hand_verdict(7, 42))
    other = pending_pulls(repo, saved, pulls_at(repo, pull_payload(7, "c" * 40)))
    assert (other.returncode, other.stdout) == (0, "")
    unmerged = pending_pulls(repo, saved, pulls_at(repo, pull_payload(7, sha, merged=False)))
    assert (unmerged.returncode, unmerged.stdout) == (0, "")
    absent = pending_pulls(repo, saved, pulls_at(repo, pull_payload(8, sha)))
    assert (absent.returncode, absent.stdout) == (0, "")


def test_1738_a_later_numbered_fix_list_or_rejection_is_the_latest_verdict(repo):
    """REQ-035: brief #1738 edge case 5(d) (the latest verdict by a record author decides)."""
    sha = hand_world(repo)
    pulls = pulls_at(repo, pull_payload(7, sha))
    for body in (
        f"Verdict: fix list {HEAD_A}\n\n1. fix it (rule: none).\n",
        f"Verdict: rejected {HEAD_A}\n",
    ):
        later = hand_verdict(7, 43, at="2026-11-21T10:00:00Z", body=body)
        proc = pending_pulls(repo, comments_at(repo, hand_verdict(7, 42), later), pulls)
        assert (proc.returncode, proc.stdout) == (0, ""), body


def test_1738_a_verdict_by_an_unlisted_author_does_not_count(repo):
    """REQ-035: brief #1738 answer 1 (a record author, `check_adrs.record_authors`)."""
    sha = hand_world(repo)
    verdict = hand_verdict(7, 42)
    verdict["user"] = {"login": "someone-else"}
    proc = pending_pulls(repo, comments_at(repo, verdict), pulls_at(repo, pull_payload(7, sha)))
    assert (proc.returncode, proc.stdout) == (0, "")


def test_1738_a_merger_made_squash_is_read_as_today(repo):
    """REQ-035: brief #1738 edge case 5(b)."""
    sha = hand_world(repo, message=final_record(7, 42))
    saved = comments_at(repo, final_comment(7, 42))
    import check_adrs

    assert check_adrs.hand_merges(repo.root, "main") == []
    for proc in (
        pending(repo, saved),
        pending_pulls(repo, saved, pulls_at(repo, pull_payload(7, sha))),
    ):
        assert proc.stdout.splitlines() == [PENDING_ADR], proc.stdout


def test_1738_an_adr_the_default_branch_reads_accepted_is_not_read(repo):
    """REQ-035: brief #1738 edge case 5(e)."""
    import check_adrs

    sha = hand_world(repo, status="Accepted")
    assert check_adrs.hand_merges(repo.root, "main") == []
    proc = pending_pulls(
        repo, comments_at(repo, hand_verdict(7, 42)), pulls_at(repo, pull_payload(7, sha))
    )
    assert (proc.returncode, proc.stdout) == (0, "")


def test_1738_a_two_parent_merge_or_a_commit_off_the_first_parent_line_is_not_read(repo):
    """REQ-035: brief #1738 edge case 5(f)."""
    import check_adrs

    repo.commit({"config/reviewers.yaml": REVIEWERS, "docs/adr/0001-first.md": adr()}, "base")
    repo.branch("side")
    repo.commit({PENDING_ADR: adr("0002", status="Proposed")}, "Add the second decision (#7)")
    repo.git("checkout", "-q", "main")
    repo.git("merge", "-q", "--no-ff", "-m", "Merge the side (#8)", "side")
    assert check_adrs.hand_merges(repo.root, "main") == []


def test_1738_a_copied_record_line_in_a_hand_merge_is_still_not_a_record(repo):
    """REQ-035: brief #1738 edge case 5(g)."""
    import check_adrs

    sha = hand_world(repo, message="Add the second decision (#7)\n\nADR-0002 Accepted (Final 42)\n")
    assert check_adrs.final_records(repo.root, "main") == {}
    assert check_adrs.hand_merges(repo.root, "main") == [(7, sha)]
    assert pending(repo, comments_at(repo, hand_verdict(7, 42))).stdout == ""


def test_1738_a_pulls_file_that_is_not_a_list_of_pull_requests_is_refused(repo):
    """REQ-035: brief #1738 answer 2 (refused naming the option, never a value)."""
    hand_world(repo)
    saved = comments_at(repo, hand_verdict(7, 42))
    bad = repo.root.parent / "bad-pulls.json"
    for text in ("not json at all", '{"title": "secret-value"}', "[]"):
        bad.write_text(text, encoding="utf-8")
        proc = pending_pulls(repo, saved, str(bad))
        assert proc.returncode == 1, text
        assert "option --pulls" in proc.stdout and "secret-value" not in proc.stdout


def test_1738_payloads_one_after_another_are_read_like_a_list(repo):
    """REQ-035: brief #1738 answer 2 (GET pulls/<n> payloads appended to one file)."""
    import json

    sha = hand_world(repo)
    path = repo.root.parent / "pulls-stream.json"
    path.write_text(
        json.dumps(pull_payload(9, "d" * 40)) + "\n" + json.dumps(pull_payload(7, sha)) + "\n",
        encoding="utf-8",
    )
    proc = pending_pulls(repo, comments_at(repo, hand_verdict(7, 42)), str(path))
    assert proc.stdout.splitlines() == [PENDING_ADR], proc.stdout
