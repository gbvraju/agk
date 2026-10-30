"""The conductor's guard refuses a `Confirmed:` comment (brief #277, verdict on f58803a; REQ-039).

In solo mode a comment whose first line is `Confirmed: <head>` counts as the person's one yes. Only
the person posts it, from the browser or the GitHub app; a session never does, because GitHub cannot
tell a comment the person typed from one a session posted under the same account. The guard
refuses such a body by name, inline or from a scratch file. No network.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_conductor_guard import COMMENT, denial, run_hook
from test_conductor_guard import project as guard_project  # noqa: F401  (the fixture)

SHA = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
POST = "gh api --method POST repos/o/r/issues/7/comments"
RULE = "conductor guard rule 6: a session never posts a Confirmed: comment"


@pytest.fixture
def project(request):
    return request.getfixturevalue("guard_project")


def bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


@pytest.mark.parametrize(
    "body",
    [
        f"Confirmed: {SHA}",
        f"Confirmed: {SHA} and more",
        "Confirmed:",
        f"  Confirmed: {SHA}",
    ],
)
def test_an_inline_confirmed_body_is_refused_by_name(project, body):
    """REQ-039: brief #277 (a session never posts the person's confirmation)."""
    found = denial(run_hook(bash(f"{POST} -f 'body={body}'"), project).stdout)
    assert found is not None and found["permissionDecisionReason"].startswith(RULE)
    assert SHA not in found["permissionDecisionReason"]


def test_a_confirmed_body_from_a_scratch_file_is_refused_by_name(project, tmp_path_factory):
    """REQ-039: brief #277 (the file form of the comment POST)."""
    tmp_path = tmp_path_factory.mktemp("temp")
    scratch = tmp_path / "agk-conductor-1"
    scratch.mkdir()
    note = scratch / "note.md"
    note.write_text(f"Confirmed: {SHA}\nVerdict: cleared {SHA}\n", encoding="utf-8")
    found = denial(run_hook(bash(f"{POST} -F body=@{note}"), project, tmp_path).stdout)
    assert found is not None and found["permissionDecisionReason"].startswith(RULE)


def test_other_comments_are_unchanged(project, tmp_path_factory):
    """REQ-039: brief #277 (only a first line `Confirmed:` is refused)."""
    tmp_path = tmp_path_factory.mktemp("temp")
    assert denial(run_hook(bash(COMMENT), project).stdout) is None
    scratch = tmp_path / "agk-conductor-2"
    scratch.mkdir()
    note = scratch / "note.md"
    note.write_text("A note.\nConfirmed: not the first line\n", encoding="utf-8")
    assert denial(run_hook(bash(f"{POST} -F body=@{note}"), project, tmp_path).stdout) is None
    assert not Path(note).read_text(encoding="utf-8").startswith("Confirmed:")
