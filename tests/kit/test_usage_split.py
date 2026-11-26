"""The usage line split by kind, with a reason when it is not shown (brief #2020, ADR-0835).

REQ-052: `usage.py` prints `Usage: <n> tokens (input <a>, cache write <b>, cache read <c>, output
<d>)`, `<n>` still the sum; a count of a kind it does not know is summed in `<n>` and named `other`;
a sub-agent's transcript beside the session's file is read with it, each message id counted once;
and `Usage: not shown (<class>)` names why, never a path or an id. The readers of `Report:` and
`Progress:` lines read the new form as they read today's. Invented transcripts in `tmp_path`, no
network. The tests were written first.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists, no shell
import sys
from pathlib import Path

import metrics
import pytest
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
    flat = {"ephemeral_5m_cache_input_tokens": 300}  # a flattened cache write is not counted twice
    rows = [entry("m1", "2026-11-10T08:00:00Z", new_kind_tokens=8, **flat)]
    path = write(tmp_path / "t.jsonl", rows)
    assert usage("--transcript", str(path)) == (
        "Usage: 1350 tokens (input 2, cache write 300, cache read 1000, output 40, other 8)\n"
    )


def test_req052_helpers_add_only_the_session_s_own_sub_agents_each_once(tmp_path):
    """REQ-052: answer 1 and fix list item 2, `<id>/subagents/*.jsonl` beside `<id>.jsonl`
    (measured, Q-CM-1) only with `--helpers`; no sibling's tokens enter another's line."""
    home = tmp_path / "rt"
    folder = home / "projects" / "-work-x"
    parent = write(folder / f"{SESSION}.jsonl", [entry("m1", "2026-11-10T08:00:00Z")])
    one = [entry("m2", "2026-11-10T08:01:00Z", 1, 0, 10, 1), entry("m1", "2026-11-10T08:02:00Z")]
    two = [entry("m3", "2026-11-10T08:03:00Z", 0, 0, 100, 0)]
    sib_a = write(folder / SESSION / "subagents" / "agent-a1.jsonl", one)
    sib_b = write(folder / SESSION / "subagents" / "agent-b2.jsonl", two)
    env = {"CLAUDE_CONFIG_DIR": str(home), "CLAUDE_CODE_SESSION_ID": SESSION}
    assert usage(env=env, cwd=tmp_path) == SPLIT + "\n"  # a sub-agent sees this same id
    assert usage("--transcript", str(sib_a)).startswith("Usage: 1354 tokens (")
    assert usage("--transcript", str(sib_b)) == (
        "Usage: 100 tokens (input 0, cache write 0, cache read 100, output 0)\n"
    )
    helped = "Usage: 1454 tokens (input 3, cache write 300, cache read 1110, output 41)\n"
    assert usage("--helpers", env=env, cwd=tmp_path) == helped
    assert usage("--transcript", str(parent), "--helpers") == helped


def test_req052_two_transcripts_of_a_resumed_session_count_a_message_once(tmp_path):
    """REQ-052: answer 7, `--transcript` twice; a message id in both is counted once."""
    one = write(tmp_path / "a.jsonl", [entry("m1", "2026-11-10T08:00:00Z")])
    two = write(
        tmp_path / "b.jsonl",
        [entry("m1", "2026-11-10T09:00:00Z"), entry("m2", "2026-11-10T09:00:00Z")],
    )
    assert usage("--transcript", str(one), "--transcript", str(two)).startswith(
        "Usage: 2684 tokens ("
    )
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
    for ending in (
        SPLIT,
        "Usage: not shown (no-session-id)",
        "Usage: 5 tokens",
        "Usage: not shown",
    ):
        match = session.PROGRESS.fullmatch(f"Progress: abc1234 done 2/4; next: 3; {ending}")
        assert match and match.group(4) == "3", ending


def test_req052_the_progress_figure_of_the_over_cap_count_reads_the_split():
    """REQ-052: fix list item 1, `caps.PROGRESS_USAGE` reads `<n>` of the split ending."""
    import caps

    for ending, figure in ((SPLIT, "1342"), ("Usage: 5 tokens", "5")):
        found = caps.PROGRESS_USAGE.fullmatch(f"Progress: abc1234 done 2/4; next: 3; {ending}")
        assert found and found.group(1) == figure, ending


def test_req052_the_steward_end_reads_the_usage_line_when_no_figure_is_typed(tmp_path, monkeypatch):
    """REQ-052: answer 5 and fix list item 4, `steward.py end` without `--tokens` passes the
    reader's figure to the `Ended:` note; a typed `--tokens` is passed as before."""
    import steward
    import steward_daily
    import usage as reader

    home = tmp_path / "rt"
    write(home / "projects" / "-w" / f"{SESSION}.jsonl", [entry("m1", "2026-11-10T08:00:00Z")])
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(home))
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", SESSION)
    seen: list = []
    monkeypatch.setattr(steward, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(steward, "no_start", lambda root: None)
    monkeypatch.setattr(steward, "end", lambda *a: (seen.append(a[-1]), (0, ["ok"]))[1])
    assert steward.main(["end", "--session", "s1", "--calls", "9"]) == 0
    assert steward.main(["end", "--session", "s1", "--tokens", "77"]) == 0
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID")
    assert steward.main(["end", "--session", "s1"]) == 0
    split = "1342 (input 2, cache write 300, cache read 1000, output 40)"
    assert seen == [split, 77, "not shown (no-session-id)"]
    helper = [entry("m9", "2026-11-10T08:05:00Z", 0, 0, 8, 0)]
    write(home / "projects" / "-w" / SESSION / "subagents" / "agent-c3.jsonl", helper)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", SESSION)
    assert steward.main(["end", "--session", "s1"]) == 0  # fix list 2 item 1: the steward's helpers
    assert seen[-1] == "1350 (input 2, cache write 300, cache read 1008, output 40)"
    line = f"Ended: steward s1 calls 9; tokens {split}"
    assert steward_daily.ENDED.fullmatch(line).group(3) == split
    assert reader.tokens_figure({}) == "not shown (no-session-id)"


def test_req052_the_builder_report_text_passes_helpers():
    """REQ-052: fix list 2 item 1, the top-level builder's `Report:` text runs `usage.py --helpers`."""
    text = (KIT / "kit" / "templates" / "runtime" / "builder.txt").read_text(encoding="utf-8")
    assert "usage.py --helpers --since <the time of your previous Report:>" in text
