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
    """REQ-052: fix list 2 item 1, the top-level builder's `Report:` runs `usage.py --helpers`."""
    text = (KIT / "kit" / "templates" / "runtime" / "builder.txt").read_text(encoding="utf-8")
    assert "usage.py --helpers --since <the time of your previous Report:>" in text


# --- Q-2020-1 (a): the sums of answer 4 over `Report:` lines, priced at `[cost] prices` -------


def comment(cid: int, at: str, first: str, login: str = "b") -> dict:
    return {"id": cid, "created_at": at, "body": f"{first}\n\nmore text", "user": {"login": login}}


SUM_COMMENTS = {
    7: [
        comment(1, "2026-11-10T08:00:00Z", "Started: s1 by the conductor"),
        comment(2, "2026-11-10T09:00:00Z", f"Report: abc1234 ready for review; {SPLIT}"),
        comment(3, "2026-11-10T10:00:00Z", "Verdict: fix list " + "a" * 40, "c"),
        comment(4, "2026-11-10T11:00:00Z", "Report: abd1234 fix list applied; " + SPLIT),
    ],
    8: [
        comment(5, "2026-11-11T09:00:00Z", "Report: bcd1234 ready for review; Usage: 500 tokens"),
        comment(6, "2026-11-12T09:00:00Z", "Report: bce1234 handing over: done"),
    ],
    9: [comment(7, "2026-11-20T09:00:00Z", "Report: cde1234 ready; Usage: not shown (no-transcript)")],
}


def sums_setup(tmp_path, monkeypatch, toml: str = "") -> tuple[Path, Path]:
    api = tmp_path / "api"
    api.mkdir()
    for number, items in SUM_COMMENTS.items():
        (api / f"comments-{number}.json").write_text(json.dumps(items), encoding="utf-8")
    pulls = [{"number": 7, "brief": 70}, {"number": 8, "brief": 70}, {"number": 9, "brief": 90}]
    facts = tmp_path / "facts.json"
    facts.write_text(json.dumps({"pull_requests": pulls}), encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    monkeypatch.setattr(metrics, "repo_root", lambda: root)
    return facts, api


def sums(capsys, facts: Path, api: Path, *more: str) -> str:
    assert metrics.main(["--report-sums", str(facts), "--api-dir", str(api), *more]) == 0
    return capsys.readouterr().out


def test_req052_report_sums_by_pull_request_brief_and_role(tmp_path, monkeypatch, capsys):
    """REQ-052: answer 4 under Q-2020-1 (a), the sums by pull request, brief and role from the
    `Report:` lines; a missing figure is counted as not reported, never as 0."""
    facts, api = sums_setup(tmp_path, monkeypatch)
    out = sums(capsys, facts, api)
    assert "usage reported: 3 of 5 reports" in out
    assert "| #7 | #70 | 2 | 0 | 4 | 600 | 2000 | 80 | 2684 | - |" in out
    assert "| #8 | #70 | 1 | 1 | unknown | unknown | unknown | unknown | 500 | - |" in out
    assert "| #9 | #90 | 0 | 1 | unknown | unknown | unknown | unknown | unknown | - |" in out
    assert "By brief: #70 3184 (1 not reported), #90 unknown (1 not reported)" in out
    assert "By role: builder 3184 (2 not reported); conductor, reviewer, steward: not read" in out
    assert "usd: not priced (setting: [cost] prices)" in out
    assert "Total: reports 5, reported 3, total 3184 (2 not reported)" in out


def test_req052_report_sums_for_one_week(tmp_path, monkeypatch, capsys):
    """REQ-052: answer 4, `--after DAY` sums the `Report:` lines of the 7 days from that day."""
    facts, api = sums_setup(tmp_path, monkeypatch)
    out = sums(capsys, facts, api, "--after", "2026-11-11")
    assert "week 2026-11-11 to 2026-11-17" in out
    assert "usage reported: 1 of 2 reports" in out
    assert "#7 |" not in out and "#9 |" not in out


def test_req052_report_sums_are_priced_at_the_cost_prices_table(tmp_path, monkeypatch, capsys):
    """REQ-052: answer 3 under Q-2020-1 (a), the money comes from `[cost.prices.<model>]` by kind
    (ADR-0544), named with `--model`; a figure without its split is not priced, never 0."""
    toml = (
        "[cost.prices.model-a]\ninput = 1000000\ncache_write = 100000\ncache_read = 10000\n"
        "output = 2000000\n"
    )
    facts, api = sums_setup(tmp_path, monkeypatch, toml)
    out = sums(capsys, facts, api, "--model", "model-a")
    # #7: input 4 * 1 + cache write 600 * 0.1 + cache read 2000 * 0.01 + output 80 * 2 = 244.00
    assert "| #7 | #70 | 2 | 0 | 4 | 600 | 2000 | 80 | 2684 | 244.00 |" in out
    assert "| #8 | #70 | 1 | 1 | unknown | unknown | unknown | unknown | 500 | unknown |" in out
    assert "usd priced at [cost] prices for the named model" in out
    no_model = sums(capsys, facts, api)
    assert "usd: not priced (option: --model)" in no_model
    other = sums(capsys, facts, api, "--model", "model-z")
    assert "usd: not priced (setting: [cost] prices has no row for the named model)" in other
    assert "model-z" not in other


def test_req052_report_sums_refuse_a_bad_price_and_bad_options(tmp_path, monkeypatch, capsys):
    """REQ-052: answer 6, a bad kind or price is refused naming the setting, never the value;
    `[models.prices]` is not read by the sums (Q-2020-1 (a)); bad options print the usage."""
    facts, api = sums_setup(tmp_path, monkeypatch, '[cost.prices.model-a]\nfresh = 3\n')
    with pytest.raises(metrics.CheckError, match=r"setting: cost\.prices\)"):
        metrics.main(["--report-sums", str(facts), "--api-dir", str(api)])
    (tmp_path / "root" / "agk.toml").write_text("[models.prices]\nstrongest = 9\n", "utf-8")
    assert "usd: not priced (setting: [cost] prices)" in sums(capsys, facts, api)
    for bad in (["--model", "m"], ["--report-sums", str(facts), "--cost"]):
        assert metrics.main(bad) == 2
    assert metrics.main(["--report-sums", str(facts), "--after", "11-11"]) == 2


def test_req052_report_sums_say_when_comments_cannot_be_read(tmp_path, monkeypatch, capsys):
    """REQ-052: a pull request whose comments cannot be read is `unknown`, never 0."""
    facts, api = sums_setup(tmp_path, monkeypatch)
    (api / "comments-8.json").unlink()
    out = sums(capsys, facts, api)
    assert "| #8 | #70 | unknown | unknown |" in out
    assert "usage reported: 2 of 3 reports (1 pull requests unread)" in out


def test_req052_the_weekly_report_says_how_many_reports_carry_a_figure():
    """REQ-052: answer 4's coverage line of the weekly issue."""

    class Src:
        def get(self, name, endpoint, until=None):
            return {f"comments-{n}": items for n, items in SUM_COMMENTS.items()}.get(name)

    details = [{"number": 7}, {"number": 8}, {"number": 9}]
    assert metrics.coverage_line(Src(), details) == "usage reported: 3 of 5 reports"
    assert metrics.coverage_line(Src(), [*details, {"number": 4}]) == (
        "usage reported: 3 of 5 reports (1 pull requests unread)"
    )
