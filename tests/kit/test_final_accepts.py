"""A covered `Final:` that accepts an ADR on the reviewed head is the acceptance (brief #557 item 1).

ADR-0277, amendment 118 (SPEC-0021 rule 3a, SPEC-0039 rule 3). When the latest covered fix list by
a listed author names the head itself and every `Final:` line is `docs/adr/<file> Proposed ->
Accepted`, no status commit follows: `check_final_clearance.py` passes when each named ADR is
`Proposed` at the head, `merge_cleared.py` merges with the squash message line
`ADR-nnnn Accepted (Final <comment id>)`, `check_adrs.py` treats an ADR so recorded on the base as
Accepted (only its Status line may change) and lists it with `--pending` for the release PR, and
the metrics count the head as cleared. No network; invented logins.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_merge_cleared_verdict import (
    HEAD,
    MERGE12,
    ON,
    REPO,
    SHA12,
    calls,
    comment,
    fake_gh,
    merge_call,
    one_line,
    repo,
    run,
    toml,
)

ADR = "docs/adr/0001-x.md"
CONFIG = "version: 1\nverdict_authors: [reviewer]\n"
ACCEPT = f"Final: {ADR} Proposed -> Accepted"


def adr_text(status: str, body: str = "d") -> str:
    return (
        f"# ADR-0001: x\n\n- Status: {status}\n- Date: 2026-11-05\n- Deciders: maintainers\n"
        f"- Related: none\n- Requirements: REQ-028\n\n## Context\n\nc\n\n## Decision\n\n{body}\n\n"
        "## Consequences\n\nq\n\n## Residual\n\nr\n"
    )


def fix_list(sha: str, *finals: str) -> str:
    return "\n".join([f"Verdict: fix list {sha}", "", "reviewed.", "", *finals]) + "\n"


# --- the reading -------------------------------------------------------------------------------


def test_final_accepts_reads_only_adr_proposed_to_accepted_lines():
    """REQ-028: rule 3a names the ADRs of a fix list whose every Final line accepts an ADR."""
    from common import final_accepts

    one = [(ADR, None, "Proposed", "Accepted")]
    assert final_accepts(one) == [ADR]
    assert final_accepts(one + [("docs/adr/0002-y.md", None, "Proposed", "Accepted")]) == [
        ADR,
        "docs/adr/0002-y.md",
    ]
    for other in (
        [("docs/specs/0001-x.md", None, "Draft", "Approved")],
        [("docs/requirements.md", "REQ-001", "planned", "done")],
        [(ADR, None, "Proposed", "Rejected")],
        [(ADR, None, "Accepted", "Superseded")],
        [("docs/adr/sub/0001-x.md", None, "Proposed", "Accepted")],
        one + [("docs/requirements.md", "REQ-001", "planned", "done")],
        [],
    ):
        assert final_accepts(other) is None, other


# --- check_final_clearance.py ------------------------------------------------------------------


def comments_file(tmp_path: Path, body: str, login: str = "reviewer") -> Path:
    path = tmp_path / "comments.json"
    item = {"id": 42, "body": body, "created_at": "2026-11-05T10:00:00Z", "user": {"login": login}}
    path.write_text(json.dumps([item]), encoding="utf-8")
    return path


def head_of(repo_) -> str:
    return repo_.git("rev-parse", "HEAD").strip()


def test_a_final_accept_on_the_head_with_a_proposed_adr_passes(repo, tmp_path):
    """REQ-028: rule 3a (no status commit follows)."""
    repo.commit({"config/reviewers.yaml": CONFIG, ADR: adr_text("Proposed")}, "reviewed")
    body = fix_list(head_of(repo)[:7], ACCEPT)
    proc = repo.run("check_final_clearance.py", "--comments", str(comments_file(tmp_path, body)))
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.parametrize("files", [{ADR: None}, {ADR: "x"}])
def test_a_final_accept_of_an_adr_that_is_not_proposed_at_the_head_fails(repo, tmp_path, files):
    """REQ-028: rule 3a (the ADR must be Proposed at the head; gone or other status fails)."""
    repo.commit({"config/reviewers.yaml": CONFIG, ADR: adr_text("Proposed")}, "base")
    accepted = {k: (adr_text("Accepted") if v == "x" else v) for k, v in files.items()}
    repo.commit(accepted, "reviewed")
    body = fix_list(head_of(repo)[:7], ACCEPT)
    proc = repo.run("check_final_clearance.py", "--comments", str(comments_file(tmp_path, body)))
    assert proc.returncode == 1
    assert "rule 3a" in proc.stdout and "Accepted\n" not in proc.stdout


def test_a_final_accept_by_an_unlisted_author_is_not_read(repo, tmp_path):
    """REQ-028: rule 5 (an unlisted author's Final line is ignored, so nothing is checked)."""
    repo.commit({"config/reviewers.yaml": CONFIG, ADR: adr_text("Accepted")}, "reviewed")
    body = fix_list(head_of(repo)[:7], ACCEPT)
    path = comments_file(tmp_path, body, login="someone-else")
    assert repo.run("check_final_clearance.py", "--comments", str(path)).returncode == 0


# --- check_adrs.py -----------------------------------------------------------------------------


def accepted_on_main(repo_) -> None:
    repo_.commit({ADR: adr_text("Proposed")}, "base")
    repo_.commit({"README.md": "x\n"}, "Example (#7)\n\nADR-0001 Accepted (Final 42)\n")
    repo_.branch()


def test_an_adr_accepted_by_a_final_on_the_base_changes_only_its_status_line(repo):
    """REQ-028: rule 3a (the squash message line is the record; the ADR is then immutable)."""
    accepted_on_main(repo)
    repo.commit({ADR: adr_text("Proposed", body="changed")})
    proc = repo.run("check_adrs.py", "--base", "main")
    assert proc.returncode == 1
    assert "may change only its Status line" in proc.stdout


def test_the_release_flip_of_an_adr_accepted_by_a_final_passes(repo):
    """REQ-028: rule 3a (the one-line flip of the release PR)."""
    accepted_on_main(repo)
    repo.commit({ADR: adr_text("Accepted")})
    proc = repo.run("check_adrs.py", "--base", "main")
    assert proc.returncode == 0, proc.stdout


def test_pending_lists_the_adrs_accepted_by_a_final_that_still_say_proposed(repo):
    """REQ-028: rule 3a (`--pending` is what the release PR flips)."""
    accepted_on_main(repo)
    repo.commit({"docs/adr/0002-y.md": adr_text("Proposed").replace("0001", "0002")})
    proc = repo.run("check_adrs.py", "--pending")
    assert proc.returncode == 0
    assert proc.stdout.splitlines() == [ADR]
    repo.commit({ADR: adr_text("Accepted")})
    assert repo.run("check_adrs.py", "--pending").stdout == ""


# --- merge_cleared.py --------------------------------------------------------------------------

CONDUCTOR = "conductor-two"
PEOPLE = f"version: 1\nconductor_accounts: [{CONDUCTOR}]\n"


def contents(status: str) -> dict:
    import base64

    raw = base64.b64encode(adr_text(status).encode()).decode()
    return {"type": "file", "encoding": "base64", "content": raw}


def merge_run(tmp_path, body: str, status: str = "Proposed"):
    root = repo(tmp_path, toml(ON), None, PEOPLE)
    verdict = comment(body, CONDUCTOR, at=5, cid=6649)
    bin_dir, log = fake_gh(tmp_path, comments=[verdict], contents={ADR: contents(status)})
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    return proc, calls(log)


def test_a_final_accept_on_the_head_merges_with_the_acceptance_in_the_squash_message(tmp_path):
    """REQ-046: SPEC-0039 rule 3 as amended (a Final accept on the head clears it)."""
    proc, made = merge_run(tmp_path, fix_list(HEAD, ACCEPT))
    assert one_line(proc) == f"merge-cleared #7 {SHA12}: merged {MERGE12}"
    put = [c for c in made if "PUT" in c]
    assert put == [merge_call() + ["-f", "commit_message=ADR-0001 Accepted (Final 6649)"]]
    assert [f"repos/{REPO}/contents/{ADR}?ref={HEAD}" in c for c in made].count(True) == 1


@pytest.mark.parametrize(
    ("body", "status"),
    [
        (fix_list(HEAD, ACCEPT), "Accepted"),  # the ADR is not Proposed at the head
        (fix_list(HEAD[:7], ACCEPT), "Proposed"),  # a short sha: the pinned head is 40 characters
        (fix_list("0f9e8d7c6b" * 4, ACCEPT), "Proposed"),  # another head
        (fix_list(HEAD, ACCEPT, "Final: docs/requirements.md REQ-001 planned -> done"), "Proposed"),
        (fix_list(HEAD, ACCEPT) + "\n1. an item\n", "Proposed"),
    ],
)
def test_any_other_final_holds_and_merges_nothing(tmp_path, body, status):
    """REQ-046: SPEC-0039 rule 3 as amended (only ADR accepts on the exact head clear)."""
    proc, made = merge_run(tmp_path, body, status)
    line = one_line(proc)
    assert line.startswith(f"merge-cleared #7 {SHA12}: held: "), line
    assert "rule 3" in line
    assert [c for c in made if "PUT" in c] == []


# --- the metrics -------------------------------------------------------------------------------


def test_a_head_merged_under_a_final_accept_counts_as_cleared():
    """REQ-028: SPEC-0021 rule 7 with rule 3a (merged_head_cleared)."""
    from metrics import merged_head_cleared

    verdict = {"body": fix_list(HEAD, ACCEPT), "created_at": "t", "user": {"login": "reviewer"}}
    assert merged_head_cleared({}, HEAD, [verdict], ["reviewer"]) == "yes"
    other = {**verdict, "body": fix_list("0f9e8d7c6b" * 4, ACCEPT)}
    assert merged_head_cleared(_NoRecord(), HEAD, [other], ["reviewer"]) != "yes"


class _NoRecord(dict):
    def get(self, *_args, **_kwargs):  # the commit record of SPEC-0021 rule 7 is unreadable
        return None
