"""The day's model spend by session, role, brief and model from local usage records (brief #1283).

REQ-050 AC5, ADR-0544. `metrics.py --cost [--day YYYY-MM-DD] [--days N] [--records DIR] [--save]`
reads only the usage fields of the local session records of this clone (model, the four token
counts, time, working folder, branch, session id), groups each reply by session, role, brief and
model, prices it from `[cost] prices` in agk.toml when given, and prints one table per day. Invented
record files in `tmp_path` (no real transcript, example.com only), no network. Written first.
"""

from __future__ import annotations

import json
from pathlib import Path

import metrics as metrics_mod
import pytest

DAY = "2026-11-14"
MARKER = "kiwi-marker-9c1 https://example.com/secret-text"  # text that must never reach the output
S1 = "0a1b2c3d-0000-4000-8000-000000000001"
S2 = "0a1b2c3d-0000-4000-8000-000000000002"
S3 = "0a1b2c3d-0000-4000-8000-000000000003"


def reply(
    cwd: str,
    session: str,
    mid: str,
    *,
    model: str = "model-a",
    branch: str = "claude/brief-1283",
    at: str = f"{DAY}T10:00:00Z",
    inp: object = 10,
    out: object = 20,
    write: object = 30,
    read: object = 40,
    agent: str | None = None,
) -> dict:
    usage = {
        "input_tokens": inp,
        "output_tokens": out,
        "cache_creation_input_tokens": write,
        "cache_read_input_tokens": read,
    }
    entry = {
        "type": "assistant",
        "cwd": cwd,
        "sessionId": session,
        "gitBranch": branch,
        "timestamp": at,
        "message": {
            "id": mid,
            "model": model,
            "role": "assistant",
            "content": [{"type": "text", "text": MARKER}],
            "usage": {k: v for k, v in usage.items() if v is not None},
        },
    }
    if agent:
        entry["agentName"] = agent
    return entry


def user_line(cwd: str, session: str) -> dict:
    return {
        "type": "user",
        "cwd": cwd,
        "sessionId": session,
        "timestamp": f"{DAY}T09:59:00Z",
        "message": {"role": "user", "content": MARKER},
    }


def records(tmp_path: Path, files: dict[str, list]) -> Path:
    top = tmp_path / "records" / "projects"
    for name, lines in files.items():
        path = top / name
        path.parent.mkdir(parents=True, exist_ok=True)
        text = "\n".join(x if isinstance(x, str) else json.dumps(x) for x in lines)
        path.write_text(text + "\n", encoding="utf-8")
    return top


def run_cost(repo, top: Path, *args: str):
    return repo.run("metrics.py", "--cost", "--day", DAY, "--records", str(top), *args)


def rows(out: str) -> list[dict[str, str]]:
    lines = [ln for ln in out.splitlines() if ln.startswith("|")]
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    return [
        dict(zip(header, [c.strip() for c in ln.strip("|").split("|")], strict=True))
        for ln in lines[2:]
    ]


def test_groups_by_session_role_brief_and_model(repo, tmp_path) -> None:
    """REQ-050 AC5: answers 1 and 2, test (a) (one row per session, role, brief and model)."""
    here = str(repo.root)
    top = records(
        tmp_path,
        {
            "p/one.jsonl": [
                user_line(here, S1),
                reply(here, S1, "m1"),
                reply(here, S1, "m1"),  # a reply written in parts counts once
                reply(here, S1, "m2", model="model-b"),
            ],
            "p/two.jsonl": [
                reply(
                    here, S2, "m3", branch="main", agent="conductor", inp=1, out=2, write=3, read=4
                ),
                reply(here, S2, "m4", branch="main", at="2026-11-13T23:59:59Z"),  # the day before
            ],
            "p/three.jsonl": [reply(f"{here}/sub", S3, "m5", branch="claude/brief-77")],
        },
    )
    proc = run_cost(repo, top)
    assert proc.returncode == 0, proc.stderr
    got = {(r["session"], r["role"], r["brief"], r["model"]): r for r in rows(proc.stdout)}
    assert set(got) == {
        (S1, "builder", "#1283", "model-a"),
        (S1, "builder", "#1283", "model-b"),
        (S2, "conductor", "unknown", "model-a"),
        (S3, "builder", "#77", "model-a"),
    }
    one = got[(S1, "builder", "#1283", "model-a")]
    assert (one["replies"], one["input"], one["output"]) == ("1", "10", "20")
    assert (one["cache_write"], one["cache_read"], one["total"]) == ("30", "40", "100")
    assert got[(S2, "conductor", "unknown", "model-a")]["total"] == "10"
    assert f"Spend {DAY}" in proc.stdout
    assert "Total: replies 4, input 31, output 62, cache write 93, cache read 124, total 310" in (
        proc.stdout
    )
    assert f"Top sessions: {S1} 200, {S3} 100, {S2} 10" in proc.stdout
    assert "Top briefs: #1283 200, #77 100, unknown 10" in proc.stdout
    # cache reads 124 of 248 input-side tokens; fresh input (input + cache write) 124
    assert "Cache reads: 50.0% of input-side tokens; fresh input 50.0%" in proc.stdout


def test_days_prints_one_table_per_day(repo, tmp_path) -> None:
    """REQ-050 AC5: answer 2 (`--days N` ends at `--day`, one table per day, oldest first)."""
    here = str(repo.root)
    top = records(
        tmp_path,
        {"p/a.jsonl": [reply(here, S1, "m1"), reply(here, S1, "m2", at="2026-11-13T08:00:00Z")]},
    )
    proc = run_cost(repo, top, "--days", "2")
    assert proc.returncode == 0, proc.stderr
    first = proc.stdout.index("Spend 2026-11-13")
    assert first < proc.stdout.index(f"Spend {DAY}")


def test_usd_from_the_price_table(repo, tmp_path) -> None:
    """REQ-050 AC5: answer 2, test (b) (USD per model and token kind, per million tokens)."""
    repo.write(
        "agk.toml",
        "[cost.prices.model-a]\ninput = 1000000\noutput = 2000000\n"
        "cache_write = 100000\ncache_read = 10000\n",
    )
    here = str(repo.root)
    top = records(
        tmp_path,
        {"p/a.jsonl": [reply(here, S1, "m1"), reply(here, S2, "m2", model="model-z")]},
    )
    proc = run_cost(repo, top)
    assert proc.returncode == 0, proc.stderr
    got = {r["model"]: r for r in rows(proc.stdout)}
    # 10 * 1 + 20 * 2 + 30 * 0.1 + 40 * 0.01 = 53.40
    assert got["model-a"]["usd"] == "53.40"
    assert got["model-z"]["usd"] == "unknown"  # a model with no price is unknown, never 0
    assert "~usd unknown" in proc.stdout


def test_tokens_only_without_a_price_table(repo, tmp_path) -> None:
    """REQ-050 AC5: answer 2, test (b) (no `[cost] prices`: tokens only, no USD figure)."""
    here = str(repo.root)
    top = records(tmp_path, {"p/a.jsonl": [reply(here, S1, "m1")]})
    proc = run_cost(repo, top)
    assert proc.returncode == 0, proc.stderr
    assert rows(proc.stdout)[0]["usd"] == "-"
    assert "usd: not priced (setting: [cost] prices)" in proc.stdout
    assert "~usd" not in proc.stdout


def test_a_bad_price_table_is_refused_naming_the_setting(repo, tmp_path) -> None:
    """REQ-050 AC5: answer 2 (a price that is not a number of 0 or more names the setting only)."""
    repo.write("agk.toml", '[cost.prices.model-a]\ninput = "cheap"\n')
    top = records(tmp_path, {"p/a.jsonl": [reply(str(repo.root), S1, "m1")]})
    proc = run_cost(repo, top)
    assert proc.returncode == 1
    assert "(setting: cost.prices.input)" in proc.stdout
    assert "cheap" not in proc.stdout + proc.stderr


def test_no_content_field_is_read_or_printed(repo, tmp_path) -> None:
    """REQ-050 AC5: answer 1, test (c) (record text holding a marker never prints, nor is saved)."""
    here = str(repo.root)
    top = records(tmp_path, {"p/a.jsonl": [user_line(here, S1), reply(here, S1, "m1")]})
    proc = run_cost(repo, top, "--save")
    assert proc.returncode == 0, proc.stderr
    saved = (repo.root / "docs" / "runs" / "cost" / f"{DAY}.json").read_text(encoding="utf-8")
    for text in (proc.stdout, proc.stderr, saved):
        assert "kiwi-marker" not in text
        assert "example.com" not in text


class Guarded(dict):
    """An entry whose content fields raise when read: the reader takes only its usage fields."""

    CONTENT = frozenset({"content", "text", "toolUseResult", "summary"})

    def __getitem__(self, key):
        if key in self.CONTENT:
            raise AssertionError(f"content field read: {key}")
        return super().__getitem__(key)

    def get(self, key, default=None):
        if key in self.CONTENT:
            raise AssertionError(f"content field read: {key}")
        return super().get(key, default)

    def items(self):
        raise AssertionError("the whole entry was walked")

    def values(self):
        raise AssertionError("the whole entry was walked")


def test_the_reader_never_touches_a_content_field() -> None:
    """REQ-050 AC5: answer 1, test (c) (only named usage fields of an entry are read)."""
    raw = reply("/w/example", S1, "m1")
    entry = Guarded(raw, message=Guarded(raw["message"]))
    got = metrics_mod.cost_reply(entry)
    assert got is not None
    assert got["model"] == "model-a"
    assert got["tokens"] == {"input": 10, "output": 20, "cache_write": 30, "cache_read": 40}


def test_another_clones_records_are_skipped(repo, tmp_path) -> None:
    """REQ-050 AC5: answer 4, test (d) (a record of another folder, or none, never counts)."""
    here = str(repo.root)
    other = str(tmp_path.parent / f"{tmp_path.name}-other" / "clone")
    sibling = f"{here}-copy"  # a folder whose name starts with the clone's is not the clone
    no_cwd = reply(here, S3, "m4")
    del no_cwd["cwd"]
    top = records(
        tmp_path,
        {
            "p/a.jsonl": [reply(here, S1, "m1")],
            "q/b.jsonl": [reply(other, S2, "m2"), reply(sibling, S2, "m3"), no_cwd],
        },
    )
    proc = run_cost(repo, top)
    assert proc.returncode == 0, proc.stderr
    assert [r["session"] for r in rows(proc.stdout)] == [S1]
    assert "Skipped: 3 replies of other folders, 0 unreadable lines" in proc.stdout


def test_a_worktree_of_the_clone_is_counted(repo, tmp_path) -> None:
    """REQ-050 AC5: answer 1 (a reply whose folder is a worktree of the clone is counted)."""
    repo.commit({"README.md": "x\n"})
    tree = tmp_path.parent / f"{tmp_path.name}-wt" / "brief-1283"  # outside the clone folder
    repo.git("worktree", "add", "-q", "-b", "claude/brief-1283", str(tree))
    top = records(tmp_path, {"p/a.jsonl": [reply(str(tree), S1, "m1", branch="")]})
    proc = run_cost(repo, top)
    assert proc.returncode == 0, proc.stderr
    got = rows(proc.stdout)
    assert [(r["session"], r["brief"]) for r in got] == [(S1, "#1283")]


def test_a_malformed_record_is_unknown_not_zero(repo, tmp_path) -> None:
    """REQ-050 AC5: answer 4, test (e) (a figure that cannot be read is `unknown`, never 0)."""
    here = str(repo.root)
    top = records(
        tmp_path,
        {
            "p/a.jsonl": [
                reply(here, S1, "m1"),
                reply(here, S1, "m2", out="many"),  # a count that is not a number
                reply(here, S1, "m3", read=None),  # a count that is missing
                "{not json",
            ],
            "p/b.jsonl": [reply(here, S2, "m4", model=12, branch=None)],
        },
    )
    proc = run_cost(repo, top)
    assert proc.returncode == 0, proc.stderr
    got = {r["session"]: r for r in rows(proc.stdout)}
    one = got[S1]
    assert one["replies"] == "3"
    assert one["input"] == "30"
    assert one["output"] == "unknown"
    assert one["cache_read"] == "unknown"
    assert one["total"] == "unknown"
    assert got[S2]["model"] == "unknown"
    assert got[S2]["brief"] == "unknown"
    assert "1 unreadable lines" in proc.stdout
    assert "output unknown" in proc.stdout


def test_no_record_prints_unknown_never_zero(repo, tmp_path) -> None:
    """REQ-050 AC5: answer 4 (no records folder, or no reply that day: `unknown`, never 0)."""
    proc = run_cost(repo, tmp_path / "absent")
    assert proc.returncode == 0, proc.stderr
    assert "Total: unknown (no usage record of this clone)" in proc.stdout


def test_save_writes_the_days_figures(repo, tmp_path) -> None:
    """REQ-050 AC5: answer 3 (`--save` writes `docs/runs/cost/<date>.json`, figures only)."""
    here = str(repo.root)
    top = records(tmp_path, {"p/a.jsonl": [reply(here, S1, "m1"), reply(here, S1, "m2")]})
    proc = run_cost(repo, top, "--save")
    assert proc.returncode == 0, proc.stderr
    path = repo.root / "docs" / "runs" / "cost" / f"{DAY}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["day"] == DAY
    assert data["total"] == {
        "replies": 2,
        "input": 20,
        "output": 40,
        "cache_write": 60,
        "cache_read": 80,
        "total": 200,
        "usd": None,
    }
    assert data["rows"][0]["session"] == S1
    assert data["rows"][0]["brief"] == "#1283"
    assert f"saved docs/runs/cost/{DAY}.json" in proc.stdout


@pytest.mark.parametrize(
    "args",
    [
        ("--cost", "--day", "2026-13-01"),
        ("--cost", "--days", "0"),
        ("--cost", "--days", "x"),
        ("--day", DAY),
        ("--cost", "--today", DAY),
        ("--cost", "--usage-by-kind", "f.json"),
    ],
)
def test_bad_arguments_print_the_usage(repo, args) -> None:
    """REQ-050 AC5: answer 1 (the options of `--cost` go with it alone)."""
    proc = repo.run("metrics.py", *args)
    assert proc.returncode == 2
    assert "metrics.py --cost" in proc.stderr
