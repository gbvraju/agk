"""Tests of `architect_guard.py --review`, the guard of the read-only review agent (SPEC-0023).


The hook runs as Claude Code runs it: JSON on stdin, a denial as JSON on stdout. In review mode no
write is ever allowed, not even under docs/; Bash is judged as for the deciding architect.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from test_architect_guard import (
    BASH_NO,
    BASH_OK,
    HOOK,
    RULE9_MARK,
    WRITE_NO,
    WRITE_OK,
    denied,
)
from test_architect_guard import (
    project as base_project,  # noqa: F401  (the fixture of test_architect_guard)
)

TOOLS = ["Edit", "Write", "MultiEdit", "NotebookEdit"]


@pytest.fixture
def project(request):
    return request.getfixturevalue("base_project")


def review(payload, project_dir, *flags):
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK), *(flags or ("--review",))],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(project_dir)},
    )


@pytest.mark.parametrize("tool", TOOLS)
@pytest.mark.parametrize("path", [*WRITE_OK, *WRITE_NO])
def test_ac1_review_mode_denies_every_write_even_under_docs(project, tool, path):
    """REQ-030 AC1: rule 2 (no path is allowed; the message names the rule, never the path)."""
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    proc = review({"tool_name": tool, "tool_input": {key: path}}, project)
    verdict = denied(proc.stdout)
    assert proc.returncode == 0 and verdict["permissionDecision"] == "deny"
    assert RULE9_MARK in verdict["permissionDecisionReason"]
    assert "review agent" in verdict["permissionDecisionReason"]
    assert not path or path not in proc.stdout


@pytest.mark.parametrize("command", BASH_OK)
def test_ac1_review_mode_allows_the_same_commands_as_the_deciding_architect(project, command):
    """REQ-030 AC1: rule 2 (read-only git, gh api GET, the comment POST, date -u, governance)."""
    proc = review({"tool_name": "Bash", "tool_input": {"command": command}}, project)
    assert proc.returncode == 0 and proc.stdout == "", command


@pytest.mark.parametrize("command", BASH_NO)
def test_ac1_review_mode_denies_every_other_command_without_echoing_it(project, command):
    """REQ-030 AC1: rule 2 (a merge, a push, a write, an operator, a substitution)."""
    proc = review({"tool_name": "Bash", "tool_input": {"command": command}}, project)
    verdict = denied(proc.stdout)
    assert verdict and verdict["permissionDecision"] == "deny", command
    assert not command or command not in proc.stdout


def test_ac1_review_mode_leaves_reads_alone_and_denies_a_broken_payload(project):
    """REQ-030 AC1: rule 2."""
    for tool in ("Read", "Grep", "Glob"):
        payload = {"tool_name": tool, "tool_input": {"file_path": "docs/a.md"}}
        assert review(payload, project).stdout == ""
    assert denied(review("not json", project).stdout)["permissionDecision"] == "deny"


def test_ac1_without_the_flag_the_guard_is_the_deciding_architects_and_unchanged(project):
    """REQ-030 AC2: rule 1 (the deciding architect still writes under docs/ and the vision)."""
    for path in WRITE_OK:
        payload = {"tool_name": "Write", "tool_input": {"file_path": path}}
        assert (
            subprocess.run(  # nosec B603 - fixed argument list, no shell
                [sys.executable, str(HOOK)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(project)},
            ).stdout
            == ""
        )


# --- brief #982 answer 4: the review agent re-runs the evidence check --------------------------

EVIDENCE_OK = [
    "python3 scripts/agk/evidence.py check .agk/evidence.json",
    "python3 scripts/agk/evidence.py check rec.json --head " + "a" * 40,
    "python3 scripts/agk/evidence.py check rec.json --sample 2 --json",
    "python3 ./scripts/agk/evidence.py check --json rec.json",
]
EVIDENCE_NO = [
    "python3 scripts/agk/evidence.py",
    "python3 scripts/agk/evidence.py check",
    "python3 scripts/agk/evidence.py record rec.json",
    "python3 scripts/agk/evidence.py check rec.json --write",
    "python3 scripts/agk/evidence.py check rec.json --out x.json",
    "python3 scripts/agk/evidence.py check a.json b.json",
    "python3 scripts/agk/evidence.py check rec.json > out.txt",
    "python3 scripts/agk/evidence.py check rec.json --head",
]


@pytest.mark.parametrize("command", EVIDENCE_OK)
def test_review_mode_allows_the_evidence_check_with_its_read_only_arguments(project, command):
    """REQ-013: brief #982 answer 4 (`check` writes nothing in the repository; the worktree it
    adds is in a temporary folder and removed)."""
    proc = review({"tool_name": "Bash", "tool_input": {"command": command}}, project)
    assert proc.returncode == 0 and proc.stdout == "", command


@pytest.mark.parametrize("command", EVIDENCE_NO)
def test_review_mode_denies_any_other_evidence_command(project, command):
    """REQ-013: brief #982 answer 4"""
    proc = review({"tool_name": "Bash", "tool_input": {"command": command}}, project)
    verdict = denied(proc.stdout)
    assert verdict and verdict["permissionDecision"] == "deny", command


def test_the_deciding_architect_is_not_given_the_evidence_check(project):
    """REQ-013: brief #982 answer 4 (the allowance is for `--review` only)."""
    command = EVIDENCE_OK[0]
    proc = review({"tool_name": "Bash", "tool_input": {"command": command}}, project, "--x")
    assert denied(proc.stdout)["permissionDecision"] == "deny"


def test_review_mode_allows_the_review_bundle_and_no_redirect_of_it(project):
    """REQ-046: brief #1013 answer 3 (ADR-0431): the bundle is a read-only script of the guard."""
    command = "python3 scripts/agk/review_bundle.py --pr 7 --sha " + "a" * 40
    proc = review({"tool_name": "Bash", "tool_input": {"command": command}}, project)
    assert proc.returncode == 0 and proc.stdout == ""
    proc = review({"tool_name": "Bash", "tool_input": {"command": command + " > b.md"}}, project)
    assert denied(proc.stdout)["permissionDecision"] == "deny"


# --- brief #1050 (Q-1013-3, ADR-0444): the reviewer slot's steps run under the guard ----------

# The hook's own text, read when a test runs: a module-level import fails the collection of a copied
# kit that has no `.claude/hooks/` (test_agk_mk.py AC1).
REVIEW_RULE_LINE = re.compile(r'^REVIEW_RULE = "([^"]+)"$', re.M)


def review_rule() -> str:
    found = REVIEW_RULE_LINE.search(HOOK.read_text(encoding="utf-8"))
    assert found, HOOK
    return found.group(1)


class Slot:
    """A real checkout `work` whose `feature` commit is on a branch of origin and whose `fork` is on
    none, beside a system temp directory `tmp` with one review scratch directory."""

    def __init__(self, root: Path) -> None:
        self.root = root / "work"
        self.tmp = root / "tmp"
        self.root.mkdir()
        self.tmp.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        self.git("remote", "add", "origin", "https://github.com/o/r.git")
        (self.root / "a.txt").write_text("a\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "one")
        self.feature = self.git("rev-parse", "HEAD").strip()
        self.git("update-ref", "refs/remotes/origin/feature", self.feature)
        tree = self.git("rev-parse", "HEAD^{tree}").strip()
        self.fork = self.git("commit-tree", tree, "-m", "fork").strip()
        self.scratch = self.tmp / "agk-review-x"
        self.scratch.mkdir()
        self.verdict = self.file("v.md", "Verdict: cleared abc1234\n\nRead: all\n")

    def git(self, *args: str) -> str:
        return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", *args], cwd=self.root, capture_output=True, text=True, check=True
        ).stdout

    def file(self, name: str, text: str) -> Path:
        path = self.tmp / name if "/" in name else self.scratch / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run(self, payload: dict, *flags: str):
        return subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(HOOK), *flags],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={
                "PATH": "/usr/bin:/bin",
                "CLAUDE_PROJECT_DIR": str(self.root),
                "TMPDIR": str(self.tmp),
            },
        )

    def bash(self, command: str, *flags: str) -> dict | None:
        payload = {"tool_name": "Bash", "tool_input": {"command": command}}
        return denied(self.run(payload, *(flags or ("--review",))).stdout)

    def write(self, path: object, tool: str = "Write", *flags: str) -> dict | None:
        key = "notebook_path" if tool == "NotebookEdit" else "file_path"
        payload = {"tool_name": tool, "tool_input": {key: str(path)}}
        return denied(self.run(payload, *(flags or ("--review",))).stdout)


@pytest.fixture
def slot(tmp_path: Path) -> Slot:
    return Slot(tmp_path)


POST_TO = "gh api --method POST repos/o/r/issues/9/comments"


def steps(s: Slot) -> list[str]:
    """The slot steps of `architect-review.md` in their exact forms (brief #1050 answer 2)."""
    return [
        "git fetch origin",
        f"git checkout --detach {s.feature}",
        f"git checkout --detach {s.feature[:7]}",
        f"python3 scripts/agk/conductor.py check-verdict {s.verdict} --pr 7",
        f"{POST_TO} -F body=@{s.verdict}",
        "python3 scripts/agk/session.py slot --next r1",
        "python3 scripts/agk/session.py slot --release r12",
    ]


def test_brief_1050_a_write_to_a_review_scratch_file_is_allowed(slot):
    """REQ-046: brief #1050 answer 1 and 5(a)."""
    assert slot.write(slot.scratch / "v.md") is None
    assert slot.write(slot.scratch / "new.md") is None
    assert slot.write(slot.scratch / "deep" / "b.md") is None


def test_brief_1050_a_write_anywhere_else_is_denied_with_the_review_rule(slot):
    """REQ-046: brief #1050 answer 1 and 5(b) (the project, another temp folder, a link, `..`)."""
    (slot.tmp / "other").mkdir()
    (slot.scratch / "out").symlink_to(slot.tmp / "other")
    (slot.scratch / "far.md").symlink_to(slot.tmp / "other" / "far.md")
    for path in (
        slot.root / "docs" / "v.md",
        "docs/v.md",
        slot.tmp / "other" / "v.md",
        slot.tmp / "agk-conductor-1" / "v.md",
        slot.scratch / "out" / "v.md",
        slot.scratch / "far.md",
        f"{slot.scratch}/../other/v.md",
        f"{slot.scratch}/../agk-review-y/v.md",
        slot.scratch,
        slot.tmp / "v.md",
        "agk-review-x/v.md",
        "",
    ):
        found = slot.write(path)
        assert found is not None and found["permissionDecisionReason"] == review_rule(), path
    (slot.root / "agk-review-in").mkdir()
    found = slot.write(slot.root / "agk-review-in" / "v.md")
    assert found is not None and found["permissionDecisionReason"] == review_rule()


@pytest.mark.parametrize("tool", ["Edit", "MultiEdit", "NotebookEdit"])
def test_brief_1050_an_edit_of_a_scratch_file_is_denied(slot, tool):
    """REQ-046: brief #1050 answer 1 and 5(c)."""
    found = slot.write(slot.verdict, tool)
    assert found is not None and found["permissionDecisionReason"] == review_rule()


def test_brief_1050_each_slot_step_is_allowed_in_its_exact_form(slot):
    """REQ-046: brief #1050 answer 2 and 5(d)."""
    for command in steps(slot):
        assert slot.bash(command) is None, command


def test_brief_1050_any_other_form_of_a_slot_step_is_denied_without_echoing_it(slot):
    """REQ-046: brief #1050 answer 2 and 5(e)."""
    outside = slot.file("other/v.md", "Verdict: cleared abc1234\n")
    report = slot.file("r.md", "Report: abc1234 done\n")
    late = slot.file("late.md", "\nVerdict: cleared abc1234\n")
    (slot.scratch / "link.md").symlink_to(outside)
    v = slot.verdict
    for command in (
        "git fetch origin main",
        "git fetch --all",
        "git fetch origin; id",
        "git checkout --detach",
        "git checkout main",
        f"git checkout {slot.feature}",
        f"git checkout --detach --force {slot.feature}",
        f"git checkout --detach {slot.fork}",
        "git checkout --detach deadbeefdeadbeef",
        f"git checkout --detach {slot.feature[:6]}",
        f"git checkout --detach {slot.feature} && id",
        f"python3 scripts/agk/conductor.py check-verdict {v}",
        f"python3 scripts/agk/conductor.py check-verdict {v} --pr 7 --x",
        f"python3 scripts/agk/conductor.py check-verdict {outside} --pr 7",
        f"python3 scripts/agk/conductor.py check-verdict {slot.scratch}/link.md --pr 7",
        f"python3 scripts/agk/conductor.py check-verdict {v} --pr x",
        "python3 scripts/agk/conductor.py check-verdict v.md --pr 7",
        f"python3 scripts/agk/conductor.py sweep {v}",
        f"{POST_TO} -F body=@{outside}",
        f"{POST_TO} -F body=@{report}",
        f"{POST_TO} -F body=@{late}",
        f"{POST_TO} -F body=@{slot.scratch}/link.md",
        f"{POST_TO} -F body=@{slot.scratch}/none.md",
        f"{POST_TO} -F body=@{v} -f x=y",
        f"{POST_TO} -F body=@{v} --input {v}",
        f"{POST_TO} -F body=@{v} --jq .id",
        f"{POST_TO} -F title=@{v}",
        f"gh api --method POST repos/x/y/issues/9/comments -F body=@{v}",
        f"gh api --method POST repos/o/r/pulls/9/comments -F body=@{v}",
        f"gh api --method PATCH repos/o/r/issues/comments/9 -F body=@{v}",
        f"{POST_TO} -F body=@{v} | sh",
        "python3 scripts/agk/session.py slot --next s1",
        "python3 scripts/agk/session.py slot --release s-shadow",
        "python3 scripts/agk/session.py slot --take r1",
        "python3 scripts/agk/session.py slot --renew r1",
        "python3 scripts/agk/session.py slot --next r0",
        "python3 scripts/agk/session.py slot --next r1 --x",
        "python3 scripts/agk/session.py slot --next r1; id",
        "python3 scripts/agk/session.py plan --json",
        "python3 scripts/agk/session.py watch --pr 7",
    ):
        found = slot.bash(command)
        assert found is not None and found["permissionDecision"] == "deny", command
        assert RULE9_MARK in found["permissionDecisionReason"]
        assert command not in found["permissionDecisionReason"]


def test_brief_1050_without_review_the_architect_guard_is_unchanged(slot):
    """REQ-046: brief #1050 answer 2 and 5(f) (the deciding architect gets none of it)."""
    found = slot.write(slot.scratch / "v.md", "Write", "--x")
    assert found is not None and "docs/" in found["permissionDecisionReason"]
    payload = {"tool_name": "Write", "tool_input": {"file_path": "docs/a.md"}}
    assert slot.run(payload).stdout == ""
    for command in steps(slot):
        found = slot.bash(command, "--x")
        assert found is not None and found["permissionDecision"] == "deny", command


def test_brief_1050_the_reviewer_slot_name_is_sessions_own():
    """REQ-046: brief #1050 answer 2(e) (the guard's slot name is `session.REVIEWER_NAME`)."""
    sys.path.insert(0, str(HOOK.parents[2] / "scripts" / "agk"))
    sys.path.insert(0, str(HOOK.parent))
    import architect_guard
    import session

    assert architect_guard.REVIEWER_NAME.pattern == session.REVIEWER_NAME.pattern
