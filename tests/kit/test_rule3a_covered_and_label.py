"""A rule 3a acceptance counts for `Covered-by:`, and its head is routed `agk:merge-ready` (#601).

ADR-0293, citing ADR-0271 (`Covered-by:`) and ADR-0277 (SPEC-0021 rule 3a). An ADR accepted by a
covered `Final:` keeps `Proposed` in its file until the release flips it; its record on the merge
base, verified by its Final comment (`--comments FILE`, as the workflow's `Record comments` step
saves them), counts as Accepted for `Covered-by:`, and without the comments, while a record of
that ADR exists, the check fails closed and names the option. The router reads a covered fix list
on the full head whose every `Final:` line accepts an ADR the pull request changes as cleared, as
`merge_cleared.py` does, so a pull request merged on it ends with `agk:merge-ready`. Saved
responses, invented logins, no network.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import route  # noqa: E402

ADR = "docs/adr/0009-intake-of-an-invented-requirement.md"
CONFIG = "version: 1\nverdict_authors: [reviewer]\n"
CLASSES = "constitution/ config/ .github/ docs/requirements.md scripts/agk/ kit/"
RECORD = "Example (#7)\n\nADR-0009 Accepted (Final 42)\nMerged-by: merge_cleared.py\n"
ACCEPT = f"Final: {ADR} Proposed -> Accepted"


def adr(status: str = "Proposed") -> str:
    return (
        "# ADR-0009: Intake of an invented requirement\n\n"
        f"- Status: {status}\n- Date: 2026-01-01\n- Deciders: maintainers\n- Related: none\n"
        "- Requirements: REQ-028\n\n## Decision\n\nThe build changes `config/` `scripts/agk/`.\n"
    )


def fix_list(sha: str, *lines: str) -> str:
    return "\n".join([f"Verdict: fix list {sha}", "", "reviewed.", "", *lines]) + "\n"


def final_comment(pr: int = 7, login: str = "reviewer", cid: int = 42) -> dict:
    return {
        "id": cid,
        "issue_url": f"https://api.example.com/repos/example-owner/example-repo/issues/{pr}",
        "user": {"login": login},
        "body": fix_list("a1b2c3d", ACCEPT),
    }


def base(repo, status: str = "Proposed", record: str | None = RECORD):
    """A base with ADR-0009 in STATUS, and (by default) a rule 3a record of it on main."""
    repo.commit(
        {
            "config/protected-paths.txt": "# c\n" + "\n".join(CLASSES.split()) + "\n",
            "config/reviewers.yaml": CONFIG,
            "config/x.txt": "x\n",
            ADR: adr(status),
        },
        "base",
    )
    if record is not None:
        repo.commit({"README.md": "x\n"}, record)
    repo.branch()
    repo.commit({"config/x.txt": "y\n"})
    return repo


def check(repo, tmp_path: Path, comments: list[dict] | str | None):
    body = tmp_path / "pr-body.md"
    body.write_text("Advances: REQ-028\nCovered-by: ADR-0009\n", encoding="utf-8")
    args = ["--base", "main", "--body", str(body)]
    if comments is not None:
        saved = tmp_path / "record-comments.json"
        text = comments if isinstance(comments, str) else json.dumps(comments)
        saved.write_text(text, encoding="utf-8")
        args += ["--comments", str(saved)]
    return repo.run("check_protected_changes.py", *args)


# --- item 1: Covered-by an ADR that a rule 3a Final accepted ----------------------------------


def test_req028_a_verified_rule_3a_record_counts_as_accepted_for_covered_by(repo, tmp_path):
    """REQ-028: brief #601 item 1 (the record and its verifying comment)."""
    proc = check(base(repo), tmp_path, [final_comment()])
    assert proc.returncode == 0, proc.stdout
    assert "Covered-by" in proc.stdout


def test_req028_without_the_comments_a_recorded_adr_fails_closed(repo, tmp_path):
    """REQ-028: brief #601 item 1 (fail closed: name rule 3a and the option, never a value)."""
    proc = check(base(repo), tmp_path, None)
    assert proc.returncode == 1
    assert "rule 3a" in proc.stdout and "--comments" in proc.stdout


@pytest.mark.parametrize(
    "comments",
    [
        [final_comment(login="someone-else")],  # not a listed author
        [final_comment(pr=8)],  # not on the record's pull request
        [final_comment(cid=43)],  # not the record's comment
        [],  # the workflow could not read it
        "",  # an empty file
    ],
)
def test_req028_an_unverified_record_does_not_count(repo, tmp_path, comments):
    """REQ-028: brief #601 item 1 (a copied squash message accepts nothing)."""
    proc = check(base(repo), tmp_path, comments)
    assert proc.returncode == 1
    assert "Accepted" in proc.stdout


@pytest.mark.parametrize("comments", [None, [final_comment()]])
def test_req028_a_proposed_adr_without_a_record_still_fails(repo, tmp_path, comments):
    """REQ-028: brief #601 item 1 (no record: as before, with or without the comments)."""
    proc = check(base(repo, record=None), tmp_path, comments)
    assert proc.returncode == 1
    assert "not '- Status: Accepted'" in proc.stdout


def test_req028_an_accepted_file_needs_no_comments(repo, tmp_path):
    """REQ-028: brief #601 item 1 (the file's own Accepted is read first, as before)."""
    proc = check(base(repo, status="Accepted"), tmp_path, None)
    assert proc.returncode == 0, proc.stdout


def test_req028_a_record_made_on_the_branch_does_not_count(repo, tmp_path):
    """REQ-028: brief #601 item 1 (only the merge base's history holds a record)."""
    base(repo, record=None)
    repo.commit({"README.md": "y\n"}, RECORD)
    proc = check(repo, tmp_path, [final_comment()])
    assert proc.returncode == 1


# --- item 2: the label of a head cleared by a rule 3a Final -----------------------------------

HEAD = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"


def ok(name: str) -> dict:
    return {"name": name, "status": "completed", "conclusion": "success"}


def said(cid: int, body: str, login: str = "boss") -> dict:
    return {
        "id": cid,
        "user": {"login": login},
        "body": body,
        "created_at": f"2026-10-25T10:{cid:02d}:00Z",
    }


def facts(comments: list[dict], files: list[dict] | None = None, **kw) -> dict:
    found = {
        "head": HEAD,
        "mergeable_state": "clean",
        "checks": [ok("governance"), ok("proof")],
        "statuses": [],
        "comments": comments,
        "reviews": [],
        "authors": ["boss"],
        "approvers": ["maintainer"],
        "author": "builder",
        "files": [{"filename": ADR, "status": "added"}] if files is None else files,
        "commit": {},
    }
    found.update(kw)
    return found


def test_req028_a_rule_3a_final_on_the_full_head_is_ready():
    """REQ-028: brief #601 item 2 (cleared for the label, as merge_cleared.py clears it)."""
    accept = said(1, fix_list(HEAD, ACCEPT))
    assert route.decide(facts([accept])) == "agk:merge-ready"
    changed = [{"filename": ADR, "status": "modified"}]
    assert route.decide(facts([accept], files=changed)) == "agk:merge-ready"


@pytest.mark.parametrize(
    ("body", "files"),
    [
        (fix_list(HEAD[:7], ACCEPT), None),  # merge_cleared.py needs the full head
        (fix_list(HEAD, ACCEPT), []),  # an ADR the pull request does not change
        (fix_list(HEAD, ACCEPT), [{"filename": ADR, "status": "removed"}]),
        (fix_list(HEAD, "Final: docs/specs/0001-x.md Draft -> Approved"), None),  # not rule 3a
        (fix_list(HEAD, "1. fix this", ACCEPT), None),  # items: no covered fix list
    ],
)
def test_req028_any_other_fix_list_on_the_head_stays_fix(body, files):
    """REQ-028: brief #601 item 2 (only what merge_cleared.py clears counts)."""
    assert route.decide(facts([said(1, body)], files=files)) == "agk:fix"


def test_req028_a_newer_fix_list_or_an_unlisted_author_hides_the_accept():
    """REQ-028: brief #601 item 2 (the latest verdict by a listed author decides)."""
    accept = said(1, fix_list(HEAD, ACCEPT))
    newer = said(2, fix_list(HEAD, "1. one more thing"))
    assert route.decide(facts([accept, newer])) == "agk:fix"
    assert route.decide(facts([said(1, fix_list(HEAD, ACCEPT), login="stranger")])) == (
        "agk:review"
    )


def test_req028_a_rule_3a_final_does_not_hide_a_red_check():
    """REQ-028: brief #601 item 2 (the order of the labels is unchanged)."""
    red = {"name": "proof", "status": "completed", "conclusion": "failure"}
    accept = said(1, fix_list(HEAD, ACCEPT))
    assert route.decide(facts([accept], checks=[ok("governance"), red])) == "agk:ci-red"
