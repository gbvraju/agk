"""The conductor's guard refuses a verdict whose `Final:` line the router cannot read (brief 238).

A comment `POST` whose body starts with `Verdict:` is read with `common.verdict_problem` and denied,
with the same message the router would reply with, before it is posted. The body comes from `-f
body=...` or from `-F body=@<file>` where the file is in a scratch directory (a verdict has several
lines, which a command line cannot carry). Hook run as Claude Code runs it; no network.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "conductor_guard.py"
sys.path.insert(0, str(ROOT / "scripts" / "agk"))
import common  # noqa: E402

MARK = "conductor guard rule 6"
POST = "gh api --method POST repos/o/r/issues/7/comments"
SHA = "a1b2c3d4e5f6"
GOOD = f"Verdict: fix list {SHA}\n\nFinal: docs/adr/0001-x.md Proposed -> Accepted\n"
CLEARED = f"Verdict: cleared {SHA}\n\nAll fine.\n"
BAD = f"Verdict: cleared {SHA}\nFinal: flip ADR-0146 to Accepted in one commit.\n"
SHAPE = f"Verdict: fix list {SHA}\nFinal: flip the ADR\n"
REQ = f"Verdict: fix list {SHA}\nFinal: docs/requirements.md planned -> done\n"


def run_hook(command: str, project: Path, tmpdir: Path, *args: str):
    env = {"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(project), "TMPDIR": str(tmpdir)}
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK), *args],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def denial(out) -> dict | None:
    return json.loads(out.stdout)["hookSpecificOutput"] if out.stdout.strip() else None


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True)
    (root / ".git" / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/o/r.git\n', encoding="utf-8"
    )
    return root


@pytest.fixture
def tmp(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("systmp")
    (root / "agk-conductor-1").mkdir()
    return root


def body_file(tmp: Path, text: str, name: str = "agk-conductor-1/v.md") -> Path:
    path = tmp / name
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def by_file(path: object, flag: str = "-F", endpoint: str = "repos/o/r/issues/7/comments") -> str:
    return f"gh api --method POST {endpoint} {flag} body=@{path}"


def test_a_well_formed_verdict_from_a_scratch_file_is_allowed(project, tmp):
    """Brief 238 answer 3 and 4: by file, a well-formed verdict."""
    for text in (GOOD, CLEARED, "Question: Q-1 something\nFinal: plain words\n"):
        out = run_hook(by_file(body_file(tmp, text)), project, tmp)
        assert out.returncode == 0 and denial(out) is None, text
    assert denial(run_hook(by_file(body_file(tmp, GOOD), "--field"), project, tmp)) is None


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (BAD, common.NOT_FIX_LIST),
        (SHAPE, common.FINAL_SHAPE),
        (REQ, common.FINAL_REQUIREMENT),
    ],
)
def test_a_malformed_verdict_from_a_scratch_file_is_denied_with_the_same_message(
    project, tmp, text, message
):
    """Brief 238 answer 3 and 4: by file, the message of the router."""
    path = body_file(tmp, text)
    found = denial(run_hook(by_file(path), project, tmp))
    assert found is not None and found["permissionDecision"] == "deny"
    assert found["permissionDecisionReason"] == f"{MARK}: {message}"
    assert (
        str(path) not in found["permissionDecisionReason"]
        and SHA not in found["permissionDecisionReason"]
    )


def test_the_message_is_the_one_the_router_replies_with():
    """Brief 238 answer 1 and 3: one function, one text."""
    assert common.verdict_problem(BAD) == common.NOT_FIX_LIST
    assert common.verdict_problem(SHAPE) == common.FINAL_SHAPE
    assert common.verdict_problem(REQ) == common.FINAL_REQUIREMENT


def test_a_one_line_verdict_in_a_field_is_allowed_and_a_multi_line_one_is_refused(project, tmp):
    """Brief 238 answer 3: by field. A command line carries one line, so a Final: line cannot be in
    a field; a body with a newline is refused as an unsafe command, not read."""
    assert denial(run_hook(f"{POST} -f 'body=Verdict: cleared {SHA}'", project, tmp)) is None
    multi = f"{POST} -f 'body=Verdict: cleared {SHA}\nFinal: plain words'"
    found = denial(run_hook(multi, project, tmp))
    assert found is not None and MARK in found["permissionDecisionReason"]


def test_the_field_body_is_read_with_the_same_function(tmp):
    """Brief 238 answer 3: by field. The hook reads the value of `body=` with `verdict_problem`."""
    sys.path.insert(0, str(HOOK.parent))
    import conductor_guard

    words = ["gh", "api", "--method", "POST", "repos/o/r/issues/7/comments", "-f", f"body={BAD}"]
    assert conductor_guard.comment_body(words) == BAD
    words = ["gh", "api", "--method", "POST", "repos/o/r/issues/7/comments", "-f", "x=y"]
    assert conductor_guard.comment_body(words) is None


@pytest.mark.parametrize(
    "shape",
    ["outside", "other-dir", "dotdot", "missing", "link", "stdin", "relative", "second-field"],
)
def test_a_file_that_is_not_a_regular_file_of_a_scratch_directory_is_denied(
    project, tmp, tmp_path, shape
):
    """Brief 238 answer 3: only a file of a scratch directory is read; anything else is denied."""
    scratch = tmp / "agk-conductor-1"
    outside = body_file(tmp, GOOD, "notes.md")
    (scratch / "link.md").symlink_to(outside)
    command = {
        "outside": by_file(outside),
        "other-dir": by_file(body_file(tmp, GOOD, "other-dir/v.md")),
        "dotdot": by_file(scratch / ".." / "notes.md"),
        "missing": by_file(scratch / "none.md"),
        "link": by_file(scratch / "link.md"),
        "stdin": by_file("-"),
        "relative": by_file("v.md"),
        "second-field": by_file(body_file(tmp, GOOD)) + " -f x=y",
    }[shape]
    found = denial(run_hook(command, project, tmp))
    assert found is not None and MARK in found["permissionDecisionReason"]


def test_another_repository_a_pull_request_endpoint_and_input_are_denied(project, tmp):
    """Brief 238: the comment target stays the origin repository's issue comments."""
    path = body_file(tmp, GOOD)
    for endpoint in ("repos/x/y/issues/7/comments", "repos/o/r/pulls/7/comments"):
        assert denial(run_hook(by_file(path, endpoint=endpoint), project, tmp)) is not None
    assert denial(run_hook(f"{POST} --input {path}", project, tmp)) is not None


def test_shadow_mode_is_unchanged_and_reads_no_verdict(project, tmp):
    """Brief 238: the shadow's file post still needs a Shadow: first line; a verdict is denied."""
    shadow = body_file(tmp, "Shadow: #7 abc1234 fix list\n\nS1. a.py line 1: x\n")
    assert denial(run_hook(by_file(shadow), project, tmp, "--shadow")) is None
    assert denial(run_hook(by_file(body_file(tmp, GOOD)), project, tmp, "--shadow")) is not None
