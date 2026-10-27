"""Tests of the covered final commit and its check (SPEC-0021 rules 1 to 4 and 8 to 10).

A fix list whose first line is `Verdict: fix list <sha>`, with `Final: <path> <old> -> <new>` lines
and no numbered item, clears in advance the one commit after <sha> that changes exactly those
status lines. `check_final_clearance.py` reads the comments from a file and git. No network.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ADR = "docs/adr/0001-x.md"
REQS = "docs/requirements.md"
CONFIG = "version: 1\nverdict_authors: [reviewer]\n"
REQ_TEXT = (
    "# Requirements\n\n### REQ-001 — One\n\n- Acceptance: AC1 g, w, t\n- Status: planned\n\n"
    "### REQ-002 — Two\n\n- Acceptance: AC1 g, w, t\n- Status: planned\n"
)


def req_done(number: int) -> str:
    """REQ_TEXT with the status of one requirement changed to `done`."""
    head, one, two = REQ_TEXT.partition("### REQ-002")
    return (
        (head.replace("planned", "done") + one + two)
        if number == 1
        else head + one + two.replace("planned", "done")
    )


def adr(status: str) -> str:
    return f"# ADR-0001: x\n\n- Status: {status}\n- Date: 2026-10-22\n"


def scenario(repo) -> str:
    """The reviewed head: an ADR `Proposed` and two requirements `planned`."""
    repo.commit({"config/reviewers.yaml": CONFIG, ADR: adr("Proposed"), REQS: REQ_TEXT}, "reviewed")
    return repo.git("rev-parse", "HEAD").strip()


def comments_file(tmp_path: Path, body: str, login: str = "reviewer", at: int = 0) -> Path:
    path = tmp_path / "comments.json"
    found = [{"body": body, "created_at": f"2026-10-22T10:{at:02d}:00Z", "user": {"login": login}}]
    path.write_text(json.dumps(found), encoding="utf-8")
    return path


def fix_list(reviewed: str, *finals: str, extra: str = "") -> str:
    lines = [f"Verdict: fix list {reviewed[:7]}", "", "reviewed.", extra, *finals]
    return "\n".join(lines) + "\n"


def check(repo, comments: Path, *extra: str):
    return repo.run("check_final_clearance.py", "--comments", str(comments), *extra)


def accept_adr(repo) -> None:
    repo.commit({ADR: adr("Accepted")}, "final")


# --- the covered fix list (rules 1 and 2) --------------------------------------------------------


def test_ac1_a_covered_fix_list_is_read_with_its_sha_and_final_lines():
    """REQ-028 AC1: rules 1 and 2."""
    from common import covered_fix_list

    body = (
        "Verdict: fix list 0066abc\n\nreviewed.\n\nFinal: docs/adr/0001-x.md Proposed -> Accepted\n"
        "Final: docs/requirements.md REQ-002 planned -> done\n"
    )
    assert covered_fix_list(body) == (
        "0066abc",
        [(ADR, None, "Proposed", "Accepted"), (REQS, "REQ-002", "planned", "done")],
    )


@pytest.mark.parametrize(
    "body",
    [
        "Verdict: fix list 0066abc\n\n1. an item\n\nFinal: docs/adr/0001-x.md A -> B\n",
        "Verdict: fix list 0066abc\n\n  2. an item\nFinal: docs/adr/0001-x.md A -> B\n",
        "Verdict: fix list 0066abc\n\nno final line\n",
        "Verdict: fix list\n\nFinal: docs/adr/0001-x.md Proposed -> Accepted\n",
        "Verdict: fix list 066\n\nFinal: docs/adr/0001-x.md Proposed -> Accepted\n",
        "Verdict: cleared 0066abc\n\nFinal: docs/adr/0001-x.md Proposed -> Accepted\n",
        "Verdict: fix list 0066abc now\n\nFinal: docs/adr/0001-x.md Proposed -> Accepted\n",
        "Verdict: fix list 0066abc\n\nFinal: docs/adr/0001-x.md Proposed => Accepted\n",
        "Verdict: fix list 0066abc\n\nFinal: docs/adr/0001-x.md REQ-001 Proposed -> Accepted\n",
        "Verdict: fix list 0066abc\n\nFinal: docs/requirements.md planned -> done\n",
        "Verdict: fix list 0066abc\n\nFinal: docs/adr/0001-x.md A -> B\nFinal: nope\n",
        "",
    ],
)
def test_ac3_a_fix_list_that_is_not_covered_clears_nothing(body):
    """REQ-028 AC3: rule 1 (a numbered item, no Final line, no or short sha, other first lines)."""
    from common import covered_fix_list

    assert covered_fix_list(body) is None


def test_ac1_status_edit_changes_the_one_status_line_or_nothing():
    """REQ-028 AC1: rule 2 (the file's own line; in `docs/requirements.md` the named section)."""
    from common import status_edit

    assert status_edit(adr("Proposed"), "Proposed", "Accepted") == adr("Accepted")
    assert status_edit(adr("Proposed"), "Draft", "Approved") is None
    assert status_edit(adr("Proposed") + "- Status: Proposed\n", "Proposed", "Accepted") is None
    assert status_edit(REQ_TEXT, "planned", "done", "REQ-002") == req_done(2)
    assert status_edit(REQ_TEXT, "planned", "done", "REQ-001") == req_done(1)
    assert status_edit(REQ_TEXT, "planned", "done", "REQ-009") is None


# --- the check (rules 3 and 4) -------------------------------------------------------------------


def test_ac1_the_commit_that_changes_exactly_the_named_line_passes(repo, tmp_path):
    """REQ-028 AC1: rules 3 and 4."""
    reviewed = scenario(repo)
    accept_adr(repo)
    final = f"Final: {ADR} Proposed -> Accepted"
    proc = check(repo, comments_file(tmp_path, fix_list(reviewed, final)))
    assert (proc.returncode, proc.stdout) == (0, "ok final-clearance\n"), proc.stdout


def test_ac1_two_files_one_in_the_named_section_of_the_requirements_pass(repo, tmp_path):
    """REQ-028 AC1: rules 2 and 3 (a `Final:` line with the requirement id)."""
    reviewed = scenario(repo)
    repo.commit({ADR: adr("Accepted"), REQS: req_done(2)}, "final")
    finals = (f"Final: {ADR} Proposed -> Accepted", f"Final: {REQS} REQ-002 planned -> done")
    assert check(repo, comments_file(tmp_path, fix_list(reviewed, *finals))).returncode == 0


def commit_variant(repo, variant: str) -> None:
    changes = {
        "extra line": {ADR: adr("Accepted") + "- Extra: x\n"},
        "other file": {ADR: adr("Accepted"), "docs/other.md": "x\n"},
        "other value": {ADR: adr("Superseded")},
        "no change": {"unrelated.txt": "x\n"},
    }
    repo.commit(changes[variant], "final")


@pytest.mark.parametrize("variant", ["extra line", "other file", "other value", "no change"])
def test_ac2_a_commit_that_changes_more_than_the_named_lines_fails(repo, tmp_path, variant):
    """REQ-028 AC2: rule 3 (the message names the rule and never a value)."""
    reviewed = scenario(repo)
    commit_variant(repo, variant)
    final = f"Final: {ADR} Proposed -> Accepted"
    proc = check(repo, comments_file(tmp_path, fix_list(reviewed, final)))
    assert proc.returncode == 1, proc.stdout
    assert proc.stdout.startswith("FAIL final-clearance: rule 3")
    assert "Accepted" not in proc.stdout and "Superseded" not in proc.stdout


STACK = "docs/adr/0002-stack-options.md"


def stack(status: str, chosen: str) -> str:
    return (
        f"# ADR-0002: stack options\n\n- Status: {status}\n- Date: 2026-10-26\n\n## Decision\n\n"
        "1. **Options**\n   - Option A — a. Trade-offs: t. Practices: p.\n"
        f"3. **Chosen**: {chosen}\n"
    )


def test_ac2_a_final_commit_that_sets_a_stack_chosen_line_names_the_cause(repo, tmp_path):
    """REQ-028 AC2: brief 274 answer 3 (Chosen is set by an ordinary commit, not a Final one)."""
    repo.commit({"config/reviewers.yaml": CONFIG, STACK: stack("Proposed", "none yet")}, "reviewed")
    reviewed = repo.git("rev-parse", "HEAD").strip()
    repo.commit({STACK: stack("Accepted", "Option A — only one fits.")}, "final")
    final = f"Final: {STACK} Proposed -> Accepted"
    proc = check(repo, comments_file(tmp_path, fix_list(reviewed, final)))
    assert proc.returncode == 1, proc.stdout
    assert proc.stdout == (
        "FAIL final-clearance: rule 3: a stack's Chosen line is set by an ordinary commit, "
        "not a Final commit\n"
    )


def test_ac2_a_final_commit_that_changes_another_line_of_a_stack_adr_keeps_the_rule_3_message(
    repo, tmp_path
):
    """REQ-028 AC2: rule 3 (only a change of the Chosen line gets the new message)."""
    repo.commit({"config/reviewers.yaml": CONFIG, STACK: stack("Proposed", "none yet")}, "reviewed")
    reviewed = repo.git("rev-parse", "HEAD").strip()
    repo.commit({STACK: stack("Accepted", "none yet") + "x\n"}, "final")
    final = f"Final: {STACK} Proposed -> Accepted"
    proc = check(repo, comments_file(tmp_path, fix_list(reviewed, final)))
    assert proc.returncode == 1 and "not exactly the named status lines" in proc.stdout
    assert "Chosen" not in proc.stdout


def test_ac2_a_status_line_of_another_requirement_fails(repo, tmp_path):
    """REQ-028 AC2: rules 2 and 3 (REQ-001 is named, REQ-002 changes)."""
    reviewed = scenario(repo)
    repo.commit({REQS: req_done(2)}, "final")
    final = f"Final: {REQS} REQ-001 planned -> done"
    assert check(repo, comments_file(tmp_path, fix_list(reviewed, final))).returncode == 1


def test_ac2_a_mode_change_with_the_status_fails(repo, tmp_path):
    """REQ-028 AC2: rule 3 (no mode change)."""
    reviewed = scenario(repo)
    (repo.root / ADR).write_text(adr("Accepted"), encoding="utf-8")
    (repo.root / ADR).chmod(0o755)
    repo.git("add", "-A")
    repo.git("commit", "-q", "-m", "final")
    final = f"Final: {ADR} Proposed -> Accepted"
    assert check(repo, comments_file(tmp_path, fix_list(reviewed, final))).returncode == 1


def test_ac3_nothing_is_checked_without_a_covered_fix_list_or_for_other_shapes(repo, tmp_path):
    """REQ-028 AC3: rule 4 (the head is the reviewed sha; numbered; an unknown sha)."""
    reviewed = scenario(repo)
    final = f"Final: {ADR} Proposed -> Accepted"
    ok = "ok final-clearance\n"
    covered = comments_file(tmp_path, fix_list(reviewed, final))
    assert check(repo, covered).stdout == ok  # the head is the reviewed sha
    repo.commit({"a.txt": "1\n"}, "one")
    repo.commit({"b.txt": "2\n"}, "two")
    late = check(repo, covered)  # two commits after: the clearance is late (SPEC-0030 rule 7)
    assert late.returncode == 1 and "rule 7" in late.stdout
    numbered = comments_file(tmp_path, fix_list(reviewed, final, extra="1. an item"))
    assert check(repo, numbered).stdout == ok
    stale = comments_file(tmp_path, fix_list("0" * 40, final))
    assert check(repo, stale).stdout == ok  # the sha is not in the history of the head


def test_ac3_a_later_verdict_replaces_the_covered_fix_list(repo, tmp_path):
    """REQ-028 AC3: rule 3 (the covered fix list must be the latest verdict by a listed author)."""
    reviewed = scenario(repo)
    repo.commit({ADR: adr("Superseded")}, "not the named line")
    final = f"Final: {ADR} Proposed -> Accepted"
    path = tmp_path / "comments.json"
    found = [
        {
            "body": fix_list(reviewed, final),
            "created_at": "2026-10-22T10:00:00Z",
            "user": {"login": "reviewer"},
        },
        {
            "body": "Verdict: fix list 0066abc\n",
            "created_at": "2026-10-22T10:01:00Z",
            "user": {"login": "reviewer"},
        },
    ]
    path.write_text(json.dumps(found), encoding="utf-8")
    assert check(repo, path).returncode == 0


def test_ac4_a_covered_fix_list_by_anyone_else_is_ignored(repo, tmp_path):
    """REQ-028 AC4: rule 5 (a stranger's Final lines clear nothing, so nothing is checked)."""
    reviewed = scenario(repo)
    repo.commit({ADR: adr("Superseded")}, "not the named line")
    final = f"Final: {ADR} Proposed -> Accepted"
    path = comments_file(tmp_path, fix_list(reviewed, final), login="stranger")
    assert check(repo, path).stdout == "ok final-clearance\n"


def test_ac6_without_a_comments_file_the_check_is_skipped(repo):
    """REQ-028 AC6: rule 4 (a local `make governance` never fails for want of the comments)."""
    scenario(repo)
    proc = repo.run("check_final_clearance.py")
    assert (proc.returncode, proc.stdout) == (0, "skipped (no comments file)\n")


def test_ac6_the_comments_file_is_an_array_lines_or_pages_and_a_bad_one_fails(repo, tmp_path):
    """REQ-028 AC6: rule 4 (`gh api --paginate` writes lines or pages)."""
    reviewed = scenario(repo)
    accept_adr(repo)
    one = {
        "body": fix_list(reviewed, f"Final: {ADR} Proposed -> Accepted"),
        "created_at": "2026-10-22T10:00:00Z",
        "user": {"login": "reviewer"},
    }
    for name, text in (
        ("lines", json.dumps(one) + "\n"),
        ("pages", json.dumps([[one], []])),
        ("array", json.dumps([one])),
    ):
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        assert check(repo, path).stdout == "ok final-clearance\n", name
    bad = tmp_path / "bad"
    bad.write_text("not json", encoding="utf-8")
    assert check(repo, bad).returncode == 1
    assert check(repo, tmp_path / "missing").returncode == 1


def test_ac6_the_head_can_be_named_for_a_merge_checkout(repo, tmp_path):
    """REQ-028 AC6: rule 4 (`--head`, the pull request head; CI checks out a merge commit)."""
    reviewed = scenario(repo)
    accept_adr(repo)
    head = repo.git("rev-parse", "HEAD").strip()
    repo.git("checkout", "-q", "-b", "other", reviewed)
    repo.commit({"side.txt": "x\n"}, "side")
    repo.git("merge", "-q", "--no-ff", "-m", "merge", head)
    path = comments_file(tmp_path, fix_list(reviewed, f"Final: {ADR} Proposed -> Accepted"))
    assert check(repo, path, "--head", head).stdout == "ok final-clearance\n"


# --- the workflow, the script and the texts (rules 8 to 10) --------------------------------------


def test_ac8_the_workflow_only_reads_and_the_script_reaches_no_network_or_model():
    """REQ-028 AC8: rules 4 and 8."""
    text = (ROOT / ".github" / "workflows" / "governance.yml").read_text(encoding="utf-8")
    block = text.split("permissions:", 1)[1].split("jobs:", 1)[0]
    assert re.findall(r"^\s+([a-z-]+): (read|write)$", block, re.M) == [
        ("contents", "read"),
        ("pull-requests", "read"),
        ("issues", "read"),
        ("actions", "read"),  # brief #216: the partial run reads the workflow runs of the head
    ]
    assert "write" not in block
    assert "gh api --paginate --method GET" in text
    assert "check_final_clearance.py --comments" in text and "--head" in text
    for write in ("--method POST", "--method PATCH", "--method PUT", "--method DELETE"):
        assert write not in text
    for verb in ("gh pr comment", "gh issue comment", "gh pr review", "gh pr edit"):
        assert verb not in text
    source = (ROOT / "scripts" / "agk" / "check_final_clearance.py").read_text(encoding="utf-8")
    imports = set(re.findall(r"(?m)^(?:import|from) ([a-z_]+)", source))
    assert not imports & {"urllib", "socket", "http", "requests", "ssl", "anthropic"}, imports


def test_ac6_make_governance_runs_the_step_after_the_other_checks():
    """REQ-028 AC6: rule 4 (a step of `make governance`)."""
    text = (ROOT / "agk.mk").read_text(encoding="utf-8")
    recipe = text.split("agk-governance:\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert recipe[-1].strip() == "$(PY) scripts/agk/check_final_clearance.py"


def test_ac1_the_verdict_template_and_the_architect_describe_the_form():
    """REQ-028 AC1: rule 9."""
    for rel in ("kit/templates/playbook/verdict.md", ".claude/agents/architect.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "Verdict: fix list <reviewed sha>" in text, rel
        assert "Final: <path> <old> -> <new>" in text, rel


def test_ac1_intake_reads_its_status_lines_through_the_shared_function():
    """REQ-028 AC1: rule 10 (the final-commit mode of SPEC-0020 reuses it)."""
    source = (ROOT / "scripts" / "agk" / "intake.py").read_text(encoding="utf-8")
    assert "final_commit_problems" in source and "def hunk_lines" not in source
