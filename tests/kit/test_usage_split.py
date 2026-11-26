"""The usage line split by kind, with a reason when it is not shown (brief #2020, ADR-0835).

REQ-052: `usage.py` prints `Usage: <n> tokens (input <a>, cache write <b>, cache read <c>, output <d>)`,
`<n>` still the sum; a count of a kind it does not know is summed in `<n>` and named `other`; a
sub-agent's transcript beside the session's file is read with it, each message id counted once; and
`Usage: not shown (<class>)` names why, never a path or an id. The readers of `Report:` and
`Progress:` lines read the new form as they read today's. Invented transcripts in `tmp_path`, no
network. The tests were written first.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists, no shell
import sys
from pathlib import Path

import pytest

import metrics
import session

KIT = Path(__file__).resolve().parents[2]
SCRIPT = KIT / "scripts" / "agk" / "usage.py"
SESSION = "0a1b2c3d-0000-4000-8000-00000000abcd"
SPLIT = "Usage: 1342 tokens (input 2, cache write 300, cache read 1000, output 40)"


def entry(mid: str, at: str, inp=2, made=300, read=1000, out=40, **more) -> dict:
    used = {
        "input_tokens": inp,
        "cache_creation_input_tokens": made,
        "cache_read_input_tokens": read,
        "output_tokens": out,
        "output_tokens_details": {"thinking_tokens": 5},
        "service_tier": "standard",
        **more,
    }
    return {"type": "assistant", "timestamp": at, "message": {"id": mid, "usage": used}}


def write(path: Path, entries: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
    return path


def usage(*args: str, env: dict | None = None, cwd: Path | None = None) -> str:
    full = {"PATH": "/usr/bin:/bin", "HOME": str(cwd or KIT), **(env or {})}
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=full,
        cwd=cwd or KIT,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout


def test_req052_the_line_splits_the_four_kinds_and_keeps_the_sum(tmp_path):
    """REQ-052: answer 2, the sum first, then each kind."""
    path = write(tmp_path / "t.jsonl", [entry("m1", "2026-11-10T08:00:00Z")])
    assert usage("--transcript", str(path)) == SPLIT + "\n"


def test_req052_a_kind_it_does_not_know_is_summed_and_named_other(tmp_path):
    """REQ-052: answer 7, an unknown `*_tokens` count is in `<n>` and named `other`."""
    path = write(tmp_path / "t.jsonl", [entry("m1", "2026-11-10T08:00:00Z", new_kind_tokens=8)])
    assert usage("--transcript", str(path)) == (
        "Usage: 1350 tokens (input 2, cache write 300, cache read 1000, output 40, other 8)\n"
    )


def test_req052_a_sub_agent_transcript_beside_the_session_is_read(tmp_path):
    """REQ-052: answer 1, `<id>/subagents/*.jsonl` beside `<id>.jsonl` (measured, Q-CM-1)."""
    home = tmp_path / "rt"
    folder = home / "projects" / "-work-x"
    write(folder / f"{SESSION}.jsonl", [entry("m1", "2026-11-10T08:00:00Z")])
    helper = [entry("m2", "2026-11-10T08:01:00Z", 1, 0, 10, 1), entry("m1", "2026-11-10T08:02:00Z")]
    write(folder / SESSION / "subagents" / "agent-a1.jsonl", helper)
    env = {"CLAUDE_CONFIG_DIR": str(home), "CLAUDE_CODE_SESSION_ID": SESSION}
    expected = "Usage: 1354 tokens (input 3, cache write 300, cache read 1010, output 41)\n"
    assert usage(env=env, cwd=tmp_path) == expected
    assert usage("--transcript", str(folder / f"{SESSION}.jsonl")) == expected


def test_req052_two_transcripts_of_a_resumed_session_count_a_message_once(tmp_path):
    """REQ-052: answer 7, `--transcript` twice; a message id in both is counted once."""
    one = write(tmp_path / "a.jsonl", [entry("m1", "2026-11-10T08:00:00Z")])
    two = write(tmp_path / "b.jsonl", [entry("m1", "2026-11-10T09:00:00Z"), entry("m2", "2026-11-10T09:00:00Z")])
    assert usage("--transcript", str(one), "--transcript", str(two)).startswith("Usage: 2684 tokens (")
    assert usage("--transcript", str(two), "--since", "2026-11-10T08:30:00Z").startswith(
        "Usage: 2684 tokens ("
    )


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("no-id", "no-session-id"),
        ("bad-id", "no-session-id"),
        ("no-file", "no-transcript"),
        ("missing", "no-transcript"),
        ("folder", "unreadable"),
        ("not-utf8", "unreadable"),
        ("no-usage", "no-usage-record"),
        ("all-before-since", "no-usage-record"),
    ],
)
def test_req052_not_shown_names_its_class_never_a_path_or_an_id(tmp_path, case, reason):
    """REQ-052: answer 1, `Usage: not shown (<class>)`; no path, id or text is printed."""
    home = tmp_path / "rt"
    (home / "projects" / "-work-x").mkdir(parents=True)
    env = {"CLAUDE_CONFIG_DIR": str(home), "CLAUDE_CODE_SESSION_ID": SESSION}
    args: list[str] = []
    path = tmp_path / "t.jsonl"
    if case == "no-id":
        env.pop("CLAUDE_CODE_SESSION_ID")
    elif case == "bad-id":
        env["CLAUDE_CODE_SESSION_ID"] = "../x"
    elif case == "missing":
        args = ["--transcript", str(path)]
    elif case == "folder":
        path.mkdir()
        args = ["--transcript", str(path)]
    elif case == "not-utf8":
        path.write_bytes(b"\xff\xfe\x00{")
        args = ["--transcript", str(path)]
    elif case == "no-usage":
        path.write_text('{"message": {"id": "m1"}}\nnot json\n', encoding="utf-8")
        args = ["--transcript", str(path)]
    elif case == "all-before-since":
        write(path, [entry("m1", "2026-11-10T08:00:00Z")])
        args = ["--transcript", str(path), "--since", "2026-11-11T00:00:00Z"]
    out = usage(*args, env=env, cwd=tmp_path)
    assert out == f"Usage: not shown ({reason})\n"
    assert str(tmp_path) not in out and SESSION not in out


def test_req052_the_readers_read_the_split_and_the_reason_as_today():
    """REQ-052: answer 2, `<n>` stays the sum every reader of today's form reads."""
    split = f"Report: abc1234 ready for review; {SPLIT}"
    reason = "Report: abc1234 ready for review; Usage: not shown (no-transcript)"
    comments = [{"body": split, "user": {"login": "b"}}, {"body": reason, "user": {"login": "b"}}]
    assert metrics.usage_of(comments, "b") == 1342
    assert metrics.usage_of(comments[1:], "b") == "not-reported"
    for ending in (SPLIT, "Usage: not shown (no-session-id)", "Usage: 5 tokens", "Usage: not shown"):
        match = session.PROGRESS.fullmatch(f"Progress: abc1234 done 2/4; next: 3; {ending}")
        assert match and match.group(4) == "3", ending
