"""The merger records the owner's spec approval in the merge (brief #1520, ADR-0642, REQ-039).

With `[flow] auto_merge = true` a spec the owner approved for the head's text that still reads
`Draft` merges with one squash line `SPEC-nnnn Approved (Approve <comment id>)`;
`common.approval_records` reads it back only from a squash commit the merger made, and
`check_specs.py` and `route.py` count the spec as Approved. Saved answers, temporary git
repositories and invented logins only; no network.
"""

from __future__ import annotations

import base64
import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tempfile
from pathlib import Path

from test_merge_cleared_verdict import HEAD, ON, calls, cleared, comment, fake_gh, repo, run, toml
from test_route import facts, said

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import merge_cleared  # noqa: E402
import route  # noqa: E402

APPROVER = "owner-example-1"
YAML = f'version: 1\nspec_approvers: ["@{APPROVER}"]\nconductor_accounts: ["@conductor-two"]\n'
SPEC_A, SPEC_B = "docs/specs/0052-an-example.md", "docs/specs/0053-another.md"
RECORD = "Intake (#1511)\n\nSPEC-0070 Approved (Approve 6970385486)\nMerged-by: merge_cleared.py\n"
SPEC70 = "docs/specs/0070-locked-releases.md"


def contents(*pairs: tuple[str, str]) -> dict:
    found = {}
    for path, word in pairs:
        text = base64.b64encode(f"# SPEC-x: Example\n\n- Status: {word}\n".encode()).decode()
        found[path] = {"type": "file", "encoding": "base64", "content": text}
    return found


def merged(tmp_path, notes, paths=(SPEC_A,), word="Draft", flow=ON, **saved):
    root = repo(tmp_path, toml(flow), reviewers_yaml=YAML)
    files = [{"filename": p, "status": "modified", "patch": "+a"} for p in paths]
    found = contents(*[(p, word) for p in paths])
    bin_dir, log = fake_gh(
        tmp_path,
        comments=[cleared(login="conductor-two"), *notes],
        files=files,
        contents=found,
        **saved,
    )
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    puts = [c for c in calls(log) if "PUT" in c]
    return proc, [a for c in puts for a in c if a.startswith("commit_message=")]


def test_an_approved_draft_spec_merges_with_its_record(tmp_path):
    """REQ-039: brief #1520 answer 1 (the record line beside Merged-by, no hold)."""
    proc, message = merged(tmp_path, [comment(f"Approve: {HEAD} SPEC-0052", APPROVER, 6)])
    assert "merged" in proc.stdout, proc.stdout + proc.stderr
    assert message == [
        "commit_message=SPEC-0052 Approved (Approve 1006)\nMerged-by: merge_cleared.py"
    ]


def test_two_specs_approved_in_one_pull_request_give_two_lines(tmp_path):
    """REQ-039: brief #1520 answer 6 (two specs, two lines)."""
    notes = [
        comment(f"Approve: {HEAD} SPEC-0052", APPROVER, 6),
        comment(f"Approve: {HEAD} SPEC-0053", APPROVER, 7),
    ]
    _, message = merged(tmp_path, notes, (SPEC_A, SPEC_B))
    lines = message[0].removeprefix("commit_message=").splitlines()
    assert lines == [
        "SPEC-0052 Approved (Approve 1006)",
        "SPEC-0053 Approved (Approve 1007)",
        "Merged-by: merge_cleared.py",
    ]


def test_a_spec_already_approved_or_approved_by_a_stranger_gives_no_line(tmp_path):
    """REQ-039: brief #1520 answer 6 (Approved at the head, or a stranger's line: no line)."""
    _, message = merged(
        tmp_path / "a", [comment(f"Approve: {HEAD} SPEC-0052", APPROVER, 6)], word="Approved"
    )
    assert message == ["commit_message=Merged-by: merge_cleared.py"]
    _, message = merged(tmp_path / "b", [comment(f"Approve: {HEAD} SPEC-0052", "a-stranger", 6)])
    assert message == ["commit_message=Merged-by: merge_cleared.py"]


def test_a_forged_record_line_in_a_branch_commit_is_held(tmp_path):
    """REQ-039: brief #1520 answer 1 (a commit already holding the line is held, as for the ADR)."""
    forged = [{"sha": HEAD, "commit": {"message": "x\n\nSPEC-0052 Approved (Approve 1)\n"}}]
    proc, message = merged(
        tmp_path, [comment(f"Approve: {HEAD} SPEC-0052", APPROVER, 6)], commits=forged
    )
    assert "already holds a record line" in proc.stdout and message == []


def test_a_short_approval_with_no_run_to_pin_it_still_holds(tmp_path):
    """REQ-039: brief #1520 answer 1 (an approval that pins no text holds as before)."""
    proc, message = merged(tmp_path, [comment("Approve: SPEC-0052", APPROVER, 6)])
    assert merge_cleared.DRAFT_HOLD in proc.stdout and message == []


def test_the_record_needs_auto_merge_on_and_no_merge_queue():
    """REQ-039: brief #1520 answer 5 (auto_merge off or the merge queue: the holds stay)."""
    on = {"flow": {"auto_merge": True, "auto_merge_method": "squash"}}
    assert merge_cleared.records_specs(on)
    assert not merge_cleared.records_specs({"flow": {"auto_merge": False}})
    assert not merge_cleared.records_specs({})
    assert not merge_cleared.records_specs({"flow": {**on["flow"], "merge_queue": True}})


# --- the #1511 case: a short approval, then a merge of main -------------------------------------


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def history(repo, spec_text: str = "- Status: Draft\nrules\n") -> tuple[str, str]:
    repo.commit({SPEC70: f"# SPEC-0070: Locked\n\n{spec_text}"}, "intake")
    approved = git(repo.root, "rev-parse", "HEAD")
    repo.commit({"other.txt": "main\n"}, "merge of main")
    return approved, git(repo.root, "rev-parse", "HEAD")


def approval_of(repo, approved, head, line="Approve: SPEC-0070", login=APPROVER, approvers=None):
    runs = [{"event": "pull_request", "head_sha": approved, "created_at": "2026-11-18T03:42:30Z"}]
    note = {
        "id": 6970385486,
        "user": {"login": login},
        "body": line,
        "created_at": "2026-11-18T05:52:16Z",
    }
    return merge_cleared.spec_approval_id(
        "SPEC-0070", [note], approvers or [f"@{APPROVER}"], runs, head, repo.root, 1511
    )


def test_the_1511_case_a_short_approval_is_pinned_and_kept_over_a_merge_of_main(repo):
    """REQ-039: brief #1520 Correction (#1511: `Approve: SPEC-0070`, then a merge of main)."""
    approved, head = history(repo)
    assert approval_of(repo, approved, head) == 6970385486
    labelled = facts(
        comments=[
            said(1, "boss", f"Verdict: cleared {facts()['head']}"),
            said(2, "maintainer", "Approve: SPEC-0070"),
        ],
        files=[{"filename": SPEC70, "status": "modified", "patch": "+a"}],
        draft_specs={"SPEC-0070"},
    )
    assert route.decide({**labelled, "merger": True}) == "agk:merge-ready"
    assert route.decide(labelled) == "agk:approve"  # auto_merge off: as today


def test_no_record_for_a_changed_text_a_stranger_a_confirmation_or_replace_me(repo):
    """REQ-039: brief #1520 answers 5 and 6 (solo `Confirmed:`, `@REPLACE-ME`, a stranger)."""
    approved, _ = history(repo)
    repo.commit({SPEC70: "# SPEC-0070: Locked\n\n- Status: Draft\nchanged\n"}, "edit")
    changed = git(repo.root, "rev-parse", "HEAD")
    assert approval_of(repo, approved, changed) is None
    assert approval_of(repo, approved, approved, login="a-stranger") is None
    solo = f"Confirmed: {approved}\nVerdict: cleared {approved}\nApprove: {approved} SPEC-0070"
    assert approval_of(repo, approved, approved, line=solo) is None
    assert approval_of(repo, approved, approved, approvers=["@REPLACE-ME"]) is None


# --- the reader and check_specs.py ---------------------------------------------------------------

SPEC_TEXT = (
    "# SPEC-0070: Locked\n\n- Status: {}\n- Requirements: REQ-077\n\n## Rules\n\n1. {}\n"
    "\n## Contexts\n\nkit, github, local, personal and stacks: as written\n"
)


def recorded(repo, message: str = RECORD) -> None:
    repo.commit({SPEC70: SPEC_TEXT.format("Draft", "rules")}, "intake")
    repo.commit({"notes.txt": "merged\n"}, message)
    repo.branch()


def test_records_are_read_only_from_a_squash_commit_the_merger_made(repo):
    """REQ-039: brief #1520 answers 2 and 5 (no `Merged-by` line, or two parents: never read)."""
    recorded(repo)
    assert common.approval_records(repo.root, "HEAD") == {"0070": (1511, 6970385486)}
    assert common.approved_specs(repo.root, "HEAD") == {"SPEC-0070"}
    repo.commit({"x.txt": "1\n"}, RECORD.replace("Merged-by: merge_cleared.py\n", ""))
    repo.git("checkout", "-q", "-b", "side", "HEAD~1")
    repo.commit({"y.txt": "1\n"}, "side")
    repo.git("checkout", "-q", "feature")
    repo.git("merge", "-q", "--no-ff", "-m", RECORD.replace("0070", "0071"), "side")
    assert common.approval_records(repo.root, "HEAD") == {"0070": (1511, 6970385486)}


def check(repo, body: str = "Advances: REQ-077\n", *extra: str):
    path = Path(tempfile.mkdtemp()) / "body.md"
    path.write_text(body, encoding="utf-8")
    return repo.run("check_specs.py", "--base", "main", "--body", str(path), *extra)


def test_rule_a_counts_a_recorded_spec_as_approved(repo):
    """REQ-039: brief #1520 answer 3 and Measured (a build advancing REQ-077 passes rule a)."""
    recorded(repo)
    repo.commit({"src/a.py": "1\n"})
    assert check(repo).returncode == 0, check(repo).stdout


def test_rule_a_still_fails_a_draft_spec_with_no_record(repo):
    """REQ-039: brief #1520 answer 3 (a Draft spec with no record is unchanged)."""
    recorded(repo, "plain commit (#1511)\n")
    repo.commit({"src/a.py": "1\n"})
    assert "REQ-077: no Approved spec names it" in check(repo).stdout


def test_a_recorded_spec_amended_later_needs_an_amendment_but_its_flip_does_not(repo):
    """REQ-039: brief #1520 answers 4 and 6 (rule (1) reads it as Approved; the release flip)."""
    recorded(repo)
    repo.commit({SPEC70: SPEC_TEXT.format("Draft", "changed")})
    assert f"approved spec '{SPEC70}' changed" in check(repo).stdout
    repo.git("reset", "-q", "--hard", "main")
    repo.git("checkout", "-q", "-B", "release")
    assert repo.run("check_specs.py", "--pending", "--base", "main").stdout.split() == [SPEC70]
    repo.commit({SPEC70: SPEC_TEXT.format("Approved", "rules")})
    saved = Path(tempfile.mkdtemp()) / "comments.json"
    saved.write_text(json.dumps([]), encoding="utf-8")
    proc = check(repo, "Advances: REQ-077\n", "--comments", str(saved))
    assert proc.returncode == 0, proc.stdout
    assert repo.run("check_specs.py", "--pending", "--base", "main").stdout.split() == []
