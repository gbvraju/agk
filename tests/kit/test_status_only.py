"""The status-only final commit: proof may report success without running the suite (brief #216).

`status_only.py` decides from git and one value the workflow passes in (the conclusion of `proof` on
the parent commit, read with one GET there, never here). It says `skip` only when all of these
hold: the head is one commit after its parent; that commit changes only `- Status:` lines (the shape
`check_final_clearance.py` recognises); proof passed on the parent; the merge base with the default
branch is the same as the parent's. Otherwise `run (<reason>)`. Fixture commits in `tmp_path`; no
network.
"""

from __future__ import annotations

import pytest

ADR = "docs/adr/0001-x.md"
SPEC = "docs/specs/0001-x.md"
REQS = "docs/requirements.md"
ADR_TEXT = "# ADR-0001: x\n\n- Status: Proposed\n- Date: 2026-10-25\n"
SPEC_TEXT = "# SPEC-0001: x\n\n- Status: Draft\n- Owner: o\n"
REQ_TEXT = "# Requirements\n\n### REQ-001 — One\n\n- Acceptance: AC1 g, w, t\n- Status: planned\n"


def adr(status: str, extra: str = "") -> str:
    return ADR_TEXT.replace("Proposed", status) + extra


@pytest.fixture
def work(repo):
    """main with three files; a feature branch with one code commit P; returns P's sha."""
    repo.commit({"a.txt": "one\n", ADR: ADR_TEXT, SPEC: SPEC_TEXT, REQS: REQ_TEXT}, "base")
    repo.git("branch", "-M", "main")
    repo.branch("feature")
    repo.commit({"a.txt": "two\n"}, "code")
    return repo.git("rev-parse", "HEAD").strip()


def decide(repo, parent_proof: str = "success", base: str = "main", head: str = "HEAD"):
    out = repo.run("status_only.py", "--head", head, "--parent-proof", parent_proof, "--base", base)
    assert out.returncode == 0, out.stdout + out.stderr
    return out.stdout.strip()


def test_one_status_line_after_a_proven_parent_is_skipped(repo, work):
    """Brief #216 answer 4: the four conditions hold."""
    repo.commit({ADR: adr("Accepted")}, "Final: ADR-0001 Proposed -> Accepted")
    assert decide(repo) == "skip"


def test_two_files_with_one_status_line_each_are_still_status_only(repo, work):
    """Brief #216 answer 4: the shape of a covered fix list with several `Final:` lines."""
    repo.commit({ADR: adr("Accepted"), REQS: REQ_TEXT.replace("planned", "done")}, "final")
    assert decide(repo) == "skip"


def test_a_spec_flip_to_approved_is_a_status_line_too(repo, work):
    """Brief #216 answer 4: governance still decides whether it may be made."""
    repo.commit({SPEC: SPEC_TEXT.replace("Draft", "Approved")}, "final")
    assert decide(repo) == "skip"


@pytest.mark.parametrize(
    "files",
    [
        {ADR: adr("Accepted", "- Extra: x\n")},
        {ADR: adr("Accepted").replace("2026-10-25", "2026-10-26")},
        {ADR: adr("Accepted"), "a.txt": "three\n"},
        {"a.txt": "three\n"},
        {ADR: adr("Accepted"), "docs/new.md": "x\n"},
        {ADR: ADR_TEXT.replace("- Status: Proposed", "Status: Accepted")},
        {ADR: ADR_TEXT.replace("- Status: Proposed", "- Status:Accepted")},
    ],
)
def test_a_commit_that_changes_more_than_a_status_line_runs_in_full(repo, work, files):
    """Brief #216 answer 4: anything but `- Status:` lines runs the suite."""
    repo.commit(files, "change")
    assert decide(repo).startswith("run (")


def test_a_deleted_file_or_a_mode_change_runs_in_full(repo, work):
    """Brief #216 answer 4: only modified files, mode unchanged."""
    repo.commit({"a.txt": None}, "delete")
    assert decide(repo).startswith("run (")


def test_a_mode_change_with_the_status_line_runs_in_full(repo, work):
    """Brief #216 answer 4."""
    (repo.root / ADR).write_text(adr("Accepted"), encoding="utf-8")
    (repo.root / ADR).chmod(0o755)
    repo.git("add", "-A")
    repo.git("commit", "-q", "-m", "mode")
    assert decide(repo).startswith("run (")


def test_two_status_lines_in_one_file_run_in_full(repo, work):
    """Brief #216 answer 4: one named status line per file, as the clearance check reads it."""
    two = ADR_TEXT + "- Status: Proposed\n"
    repo.commit({ADR: two}, "two lines")
    repo.commit({ADR: two.replace("Proposed", "Accepted")}, "both")
    assert decide(repo).startswith("run (")


@pytest.mark.parametrize("value", ["failure", "cancelled", "", "skipped", "neutral", "SUCCESS"])
def test_a_parent_whose_proof_did_not_pass_runs_in_full(repo, work, value):
    """Brief #216 answer 4: proof passed on the parent, or the suite runs."""
    repo.commit({ADR: adr("Accepted")}, "final")
    assert decide(repo, parent_proof=value).startswith("run (")


def test_a_merge_commit_runs_in_full(repo, work):
    """Brief #216 answer 4: the head is one commit after its parent, not a merge."""
    repo.git("checkout", "-q", "main")
    repo.commit({"b.txt": "x\n"}, "main moves")
    repo.git("checkout", "-q", "feature")
    repo.git("merge", "-q", "--no-ff", "main", "-m", "merge main")
    assert decide(repo).startswith("run (")


def test_a_main_that_moved_past_the_parent_runs_in_full(repo, work):
    """Brief #216 answer 4 (the verdict on 460dab3): the parent's run tested the parent with main
    as it was; the new run would test the head with main as it is now, so the suite runs."""
    repo.commit({ADR: adr("Accepted")}, "final")
    repo.git("checkout", "-q", "main")
    repo.commit({"b.txt": "x\n"}, "main moves")
    repo.git("checkout", "-q", "feature")
    assert decide(repo).startswith("run (")


def test_a_main_that_moved_and_was_merged_into_the_parent_is_skipped(repo, work):
    """Brief #216 answer 4: nothing from main is untested when the tip is in the parent."""
    repo.git("checkout", "-q", "main")
    repo.commit({"b.txt": "x\n"}, "main moves")
    repo.git("checkout", "-q", "feature")
    repo.git("merge", "-q", "--no-ff", "main", "-m", "merge main")
    repo.commit({ADR: adr("Accepted")}, "final")
    assert decide(repo) == "skip"


def test_a_main_that_did_not_move_and_is_in_the_parent_is_skipped(repo, work):
    """Brief #216 answer 4: main unchanged and contained in the parent."""
    repo.commit({ADR: adr("Accepted")}, "final")
    assert decide(repo, base="main") == "skip"


def test_a_head_already_in_the_default_branch_runs_in_full(repo, work):
    """Brief #216 answer 4: the tip of the default branch is not in the parent; run."""
    repo.commit({ADR: adr("Accepted")}, "final")
    repo.git("branch", "-f", "main", "HEAD")
    assert decide(repo).startswith("run (")


def test_the_root_commit_and_an_unknown_head_run_in_full(repo):
    """Brief #216 answer 4: nothing can be said about them."""
    repo.commit({"a.txt": "one\n"}, "root")
    assert decide(repo).startswith("run (")
    assert decide(repo, head="0" * 40).startswith("run (")


def test_the_reasons_name_the_condition_and_never_a_value(repo, work):
    """CLAUDE.md rule 6: no file name, no line, no sha in a reason."""
    repo.commit({ADR: adr("Accepted", "- Secret: hunter2\n")}, "change")
    out = decide(repo)
    assert out.startswith("run (") and "hunter2" not in out and "0001" not in out
    assert "Accepted" not in out


def test_usage(repo, work):
    """Brief #216: --head is required, the proof value is one word."""
    assert repo.run("status_only.py").returncode == 2
    assert repo.run("status_only.py", "--head", "HEAD", "--bogus", "x").returncode == 2


def test_it_reads_git_only_and_never_the_network(repo):
    """Brief #216 answer 6: no check calls the network."""
    import ast
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts" / "agk" / "status_only.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = {
        a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    names |= {
        n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module
    }
    assert not names & {"socket", "urllib", "http", "requests", "ssl"}
