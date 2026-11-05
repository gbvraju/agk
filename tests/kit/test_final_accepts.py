"""A covered `Final:` accepting an ADR on the reviewed head is the acceptance (brief #557 item 1).

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
    cleared,
    comment,
    fake_gh,
    merge_call,
    merge_cleared_run,
    one_line,
    repo,
    run,
    toml,
    world,
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
    repo.commit({"config/reviewers.yaml": CONFIG}, "base")
    repo.branch()
    repo.commit({ADR: adr_text("Proposed")}, "reviewed")
    body = fix_list(head_of(repo)[:7], ACCEPT)
    proc = repo.run("check_final_clearance.py", "--comments", str(comments_file(tmp_path, body)))
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.parametrize("files", [{ADR: None}, {ADR: "x"}])
def test_a_final_accept_of_an_adr_that_is_not_proposed_at_the_head_fails(repo, tmp_path, files):
    """REQ-028: rule 3a (the ADR must be Proposed at the head; gone or other status fails)."""
    repo.commit({"config/reviewers.yaml": CONFIG, "README.md": "x\n"}, "base")
    repo.branch()
    repo.commit({ADR: adr_text("Proposed")}, "added")
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


RECORD = "Example (#7)\n\nADR-0001 Accepted (Final 42)\nMerged-by: merge_cleared.py\n"


def accepted_on_main(repo_, message: str = RECORD) -> None:
    repo_.commit({"config/reviewers.yaml": CONFIG, ADR: adr_text("Proposed")}, "base")
    repo_.commit({"README.md": "x\n"}, message)
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
    saved = remote_file(repo.root.parent, [remote_comment()])
    proc = repo.run("check_adrs.py", "--pending", "--comments", saved)
    assert proc.returncode == 0
    assert proc.stdout.splitlines() == [ADR]
    repo.commit({ADR: adr_text("Accepted")})
    assert repo.run("check_adrs.py", "--pending", "--comments", saved).stdout == ""


# --- merge_cleared.py --------------------------------------------------------------------------

CONDUCTOR = "conductor-two"
PEOPLE = f"version: 1\nconductor_accounts: [{CONDUCTOR}]\n"


def contents(status: str) -> dict:
    import base64

    raw = base64.b64encode(adr_text(status).encode()).decode()
    return {"type": "file", "encoding": "base64", "content": raw}


ADR_FILE = {"filename": ADR, "status": "added", "patch": "+x"}


def merge_run(tmp_path, body: str, status: str = "Proposed", files=None, later=()):
    root = repo(tmp_path, toml(ON), None, PEOPLE)
    verdict = comment(body, CONDUCTOR, at=5, cid=6649)
    saved = {"contents": {ADR: contents(status)}, "files": files or [ADR_FILE]}
    bin_dir, log = fake_gh(tmp_path, comments=[verdict, *later], **saved)
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    return proc, calls(log)


def test_a_final_accept_on_the_head_merges_with_the_acceptance_in_the_squash_message(tmp_path):
    """REQ-046: SPEC-0039 rule 3 as amended (a Final accept on the head clears it)."""
    proc, made = merge_run(tmp_path, fix_list(HEAD, ACCEPT))
    assert one_line(proc) == f"merge-cleared #7 {SHA12}: merged {MERGE12}"
    put = [c for c in made if "PUT" in c]
    message = "ADR-0001 Accepted (Final 6649)\nMerged-by: merge_cleared.py"
    assert put == [merge_call(message=message)]
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


# --- fix list of 2026-11-05 on f623a77 (brief #557) --------------------------------------------
# Item 1: a Final accepts only an ADR the pull request adds or changes, never a stack-options ADR,
# and a newer fix list hides an older accept. Item 2: the facts, the drift audit and the release
# read the acceptance. Item 4: the record line counts only in a first-parent squash commit that
# merge_cleared.py made, and the facts check its comment id against the pull request's comment.


def test_a_stack_options_adr_is_never_accepted_by_a_final_line_alone():
    """REQ-028: rule 3a (a stack ADR needs Chosen and Accepted in one commit, rule 3)."""
    from common import final_accepts

    stack = "docs/adr/0001-stack-options.md"
    assert final_accepts([(stack, None, "Proposed", "Accepted")]) is None
    both = [(ADR, None, "Proposed", "Accepted"), (stack, None, "Proposed", "Accepted")]
    assert final_accepts(both) is None


def test_a_final_accepting_an_adr_the_pull_request_does_not_change_fails(repo, tmp_path):
    """REQ-028: rule 3a (another pull request's Proposed ADR, waiting on main, is not accepted)."""
    repo.commit({"config/reviewers.yaml": CONFIG, ADR: adr_text("Proposed")}, "base")
    repo.branch()
    repo.commit({"README.md": "unrelated\n"}, "reviewed")
    body = fix_list(head_of(repo)[:7], ACCEPT)
    proc = repo.run("check_final_clearance.py", "--comments", str(comments_file(tmp_path, body)))
    assert proc.returncode == 1
    assert "rule 3a" in proc.stdout and "does not change" in proc.stdout


def test_merge_cleared_holds_a_final_accepting_an_adr_the_pull_request_does_not_change(tmp_path):
    """REQ-046: SPEC-0039 rule 3 as amended (each Final path is among the pull request's files)."""
    other = [{"filename": "docs/runs/notes.md", "status": "modified", "patch": "+x"}]
    proc, made = merge_run(tmp_path, fix_list(HEAD, ACCEPT), files=other)
    line = one_line(proc)
    assert line.startswith(f"merge-cleared #7 {SHA12}: held: "), line
    assert "rule 3" in line
    assert [c for c in made if "PUT" in c] == []


def test_a_newer_fix_list_after_an_accept_holds_and_does_not_count_as_cleared(tmp_path):
    """REQ-046: rule 3 (the latest verdict decides; an older accept is hidden by a newer list)."""
    newer = comment(f"Verdict: fix list {HEAD}\n\n1. one more item\n", CONDUCTOR, at=9, cid=6650)
    proc, made = merge_run(tmp_path, fix_list(HEAD, ACCEPT), later=[newer])
    assert one_line(proc).startswith(f"merge-cleared #7 {SHA12}: held: ")
    assert [c for c in made if "PUT" in c] == []
    from metrics import merged_head_cleared

    accept = {"body": fix_list(HEAD, ACCEPT), "created_at": "t1", "user": {"login": "reviewer"}}
    later = {**accept, "body": newer["body"], "created_at": "t2"}
    assert merged_head_cleared(_NoRecord(), HEAD, [accept, later], ["reviewer"]) != "yes"


# --- item 4: the record line ------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "Example (#7)\n\nADR-0001 Accepted (Final 42)\n",  # no line of merge_cleared.py
        "Example\n\nADR-0001 Accepted (Final 42)\nMerged-by: merge_cleared.py\n",  # no (#n)
    ],
)
def test_a_record_line_outside_a_merge_cleared_squash_commit_is_not_read(repo, message):
    """REQ-028: rule 3a (only merge_cleared.py's squash commit carries the record)."""
    accepted_on_main(repo, message)
    assert repo.run("check_adrs.py", "--pending").stdout == ""
    repo.commit({ADR: adr_text("Proposed", body="changed")})
    assert repo.run("check_adrs.py", "--base", "main").returncode == 0


def test_a_record_line_off_the_first_parent_line_is_not_read(repo):
    """REQ-028: rule 3a (a commit merged in from a side branch, or a merge commit, is not one)."""
    repo.commit({ADR: adr_text("Proposed")}, "base")
    repo.branch("side")
    repo.commit({"README.md": "x\n"}, RECORD)
    repo.git("checkout", "-q", "main")
    repo.commit({"other.md": "y\n"}, "main moves")
    repo.git("merge", "-q", "--no-ff", "-m", RECORD, "side")
    from common import accepted_by_final

    assert accepted_by_final(repo.root, "HEAD") == set()


def test_the_record_names_its_pull_request_and_comment(repo):
    """REQ-028: rule 3a (`final_records` gives the pull request and the Final comment id)."""
    accepted_on_main(repo)
    from common import final_records

    assert final_records(repo.root, "HEAD") == {"0001": (7, 42)}


def remote_comment(pr: int = 7, login: str = "reviewer", body: str | None = None) -> dict:
    return {
        "id": 42,
        "issue_url": f"https://api.example.com/repos/example-owner/example-repo/issues/{pr}",
        "user": {"login": login},
        "body": fix_list("a1b2c3d", ACCEPT) if body is None else body,
    }


def test_the_record_is_verified_against_the_comment_on_its_pull_request():
    """REQ-028: rule 3a (a copied message cannot accept an ADR)."""
    from check_adrs import final_record_verified

    record = (7, 42)
    assert final_record_verified(ADR, record, remote_comment(), ["reviewer"])
    assert not final_record_verified(ADR, record, remote_comment(pr=8), ["reviewer"])
    assert not final_record_verified(ADR, record, remote_comment(login="other"), ["reviewer"])
    other_adr = fix_list("a1b2c3d", "Final: docs/adr/0002-y.md Proposed -> Accepted")
    assert not final_record_verified(ADR, record, remote_comment(body=other_adr), ["reviewer"])
    assert not final_record_verified(ADR, record, None, ["reviewer"])
    assert not final_record_verified(ADR, record, {**remote_comment(), "id": 43}, ["reviewer"])


# --- item 2: the facts, the drift audit and the release ----------------------------------------


def api_dir(tmp_path: Path, item: dict | None) -> Path:
    folder = tmp_path / "api"
    folder.mkdir()
    if item is not None:
        (folder / "comment-42.json").write_text(json.dumps(item), encoding="utf-8")
    return folder


@pytest.mark.parametrize(
    ("item", "status"),
    [
        (remote_comment(), "Accepted"),
        (remote_comment(pr=8), "Proposed"),  # a copied message: the comment is on another PR
        (None, "Proposed"),  # the comment cannot be read: fail closed
    ],
)
def test_facts_take_an_adrs_status_from_its_verified_final_record(repo, tmp_path, item, status):
    """REQ-028: rule 3a (the owner's inbox and the questions read the acceptance)."""
    import facts
    import metrics

    accepted_on_main(repo)
    src = metrics.ApiDir(api_dir(tmp_path, item))
    accepted = facts.final_accepted(repo.root, src, ["reviewer"])
    records = facts.adr_records(repo.root, accepted)
    assert [r["status"] for r in records if r["id"] == "ADR-0001"] == [status]


def test_facts_without_a_source_keep_the_files_status(repo):
    """REQ-028: rule 3a (no GitHub, nothing verified: the file's status stands)."""
    import facts

    accepted_on_main(repo)
    assert facts.final_accepted(repo.root, None, ["reviewer"]) == set()


def test_the_drift_audit_raises_no_stale_proposed_finding_for_a_recorded_adr(repo):
    """REQ-028: rule 3a (D3 does not report an ADR the default branch records as accepted)."""
    from datetime import date

    import drift_audit

    accepted_on_main(repo)
    late = date(2027, 1, 1)
    assert [f for f in drift_audit.d3(repo.root, "HEAD", late) if f.subject == ADR] == []
    repo.git("checkout", "-q", "main")
    repo.commit({"docs/adr/0002-y.md": adr_text("Proposed").replace("0001", "0002")})
    paths = [f.subject for f in drift_audit.d3(repo.root, "HEAD", late)]
    assert "docs/adr/0002-y.md" in paths and ADR not in paths


# --- fix list of 2026-11-05 on e5e45d5 (brief #557): a copied record line accepts nothing -----
# merge_cleared.py always writes its own squash message and holds a pull request whose commits or
# body already hold a record line; the release check and `--pending` count a record only when its
# comment, given with `--comments`, verifies it, and fail closed without that input.

FORGED = (  # GitHub's default squash message copies the commit bodies of the pull request
    "Example (#7)\n\n* an ordinary change\n\nADR-0001 Accepted (Final 42)\n"
    "Merged-by: merge_cleared.py\n"
)


def remote_file(folder: Path, items: list[dict]) -> str:
    path = folder / "final-comments.json"
    path.write_text(json.dumps(items), encoding="utf-8")
    return str(path)


def test_merge_cleared_always_writes_its_own_squash_message(tmp_path):
    """REQ-046: SPEC-0039 rule 6 as amended (never GitHub's default message)."""
    proc, made = merge_cleared_run(tmp_path, toml(ON), [cleared()])
    assert proc.returncode == 0, proc.stdout
    assert [c for c in made if "PUT" in c] == [merge_call(message="Merged-by: merge_cleared.py")]


@pytest.mark.parametrize(
    ("where", "line"),
    [
        ("commit", "ADR-0001 Accepted (Final 42)"),
        ("commit", "Merged-by: merge_cleared.py"),
        ("body", "  ADR-0002 Accepted (Final 7)  "),
        ("body", "Merged-by: merge_cleared.py"),
    ],
)
def test_merge_cleared_holds_a_pull_request_that_already_holds_a_record_line(tmp_path, where, line):
    """REQ-046: SPEC-0039 rule 3 as amended (an author cannot carry a record into the squash)."""
    pull = {**world()["pull"]}
    commits = list(world()["commits"])
    if where == "body":
        pull["body"] = f"{pull['body']}\n{line}\n"
    else:
        commits.append({"sha": "b" * 40, "commit": {"message": f"Change\n\n{line}\n"}})
    proc, made = merge_cleared_run(tmp_path, toml(ON), [cleared()], pull=pull, commits=commits)
    out = one_line(proc)
    assert out.startswith(f"merge-cleared #7 {SHA12}: held: "), out
    assert "record line" in out and "rule 3" in out
    assert [c for c in made if "PUT" in c] == []


def test_merge_cleared_holds_when_the_commits_are_not_all_read(tmp_path):
    """REQ-046: SPEC-0039 rule 5 (GitHub lists at most 250 commits: an unread one may hold it)."""
    pull = {**world()["pull"], "commits": 251}
    proc, made = merge_cleared_run(tmp_path, toml(ON), [cleared()], pull=pull)
    assert "held: commits not all read" in one_line(proc)
    assert [c for c in made if "PUT" in c] == []


def test_pending_fails_closed_without_the_comments(repo):
    """REQ-028: rule 3a (a record is counted only once its comment verifies it)."""
    accepted_on_main(repo)
    proc = repo.run("check_adrs.py", "--pending")
    assert proc.returncode == 1
    assert proc.stdout.startswith("FAIL adrs: rule 3a") and "--comments" in proc.stdout


@pytest.mark.parametrize(
    "items",
    [
        [],  # the comment is not given
        [remote_comment(pr=8)],  # the id names a comment on another pull request
        [remote_comment(login="someone-else")],  # not a listed verdict author
        [{**remote_comment(), "id": 43}],  # another comment
    ],
)
def test_a_default_message_squash_with_a_forged_record_is_not_pending(repo, items):
    """REQ-028: rule 3a (a forged record line asks no flip)."""
    accepted_on_main(repo, FORGED)
    saved = remote_file(repo.root.parent, items)
    proc = repo.run("check_adrs.py", "--pending", "--comments", saved)
    assert (proc.returncode, proc.stdout) == (0, ""), proc.stdout
    verified = remote_file(repo.root.parent, [remote_comment()])
    assert repo.run("check_adrs.py", "--pending", "--comments", verified).stdout == f"{ADR}\n"
