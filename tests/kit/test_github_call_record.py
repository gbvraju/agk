"""Each GitHub job of the kit records the calls it made and the hourly limit left.

Brief #1877, ADR-0776; REQ-039. `session.call_record()`, registered with `atexit` beside the read
cache's save, prints to the log and appends to `$GITHUB_STEP_SUMMARY` one line when the process runs
in GitHub Actions (`GITHUB_ACTIONS=true`) and made at least one call:
`github calls: <workflow> / <job>: <n> calls (<c> cached, <w> writes, <k> waits, <s> s waited);
limit <r> of <l> left, resets <HH:MM>Z`. The limit figures are the last `x-ratelimit-*` headers a
call saw, else one free `GET rate_limit`, else `unknown`. The router's own writes and searches and
the merger's direct `gh api` calls are counted through `session.count_call`. A double of `gh`
(`subprocess.run` or `session.RUN`) answers with invented headers and bodies: no network."""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - only the double's CompletedProcess and one python child
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import merge_cleared  # noqa: E402
import route  # noqa: E402
import session  # noqa: E402

EP = "repos/acme/widgets/issues/7"
RESET = 1_900_000_000  # 2030-03-17T17:46:40Z
REFUSED = "github calls: the job summary cannot be written (setting: GITHUB_STEP_SUMMARY)"


def head(status: str, headers: dict[str, str], body: str = "") -> str:
    lines = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
    return f"HTTP/2.0 {status}\r\n{lines}\r\n{body}"


def limits(left: int, of: int = 5000) -> dict[str, str]:
    return {"X-Ratelimit-Remaining": str(left), "X-Ratelimit-Limit": str(of),
            "X-Ratelimit-Reset": str(RESET)}  # fmt: skip


class Double:
    def __init__(self, *answers: tuple) -> None:
        self.answers = list(answers)
        self.calls: list[list[str]] = []

    def __call__(self, args, **_kw):
        self.calls.append(list(args))
        out, err, code = self.answers.pop(0)
        return subprocess.CompletedProcess(args, code, out, err)


@pytest.fixture
def fresh(monkeypatch, tmp_path):
    """Counters at zero, a private read cache in tmp_path, the gh transport, in Actions."""
    cache = session.ReadCache()
    cache.place = tmp_path / "cache"
    cache.place.mkdir()
    monkeypatch.setattr(session, "CACHE", cache)
    monkeypatch.setattr(session, "MEMO", None)
    monkeypatch.setattr(session, "RUN", None)
    for name, value in (("CALLS", 0), ("CACHED", 0), ("WRITES", 0), ("WAITS", 0),
                        ("WAITED", 0.0), ("LAST_WRITE", None)):  # fmt: skip
        monkeypatch.setattr(session, name, value)
    monkeypatch.setattr(session, "LIMIT_SEEN", {})
    monkeypatch.setattr(session.DIRECT, "mode", "gh")
    monkeypatch.setattr(session, "time", SimpleNamespace(
        time=lambda: RESET - 600, monotonic=lambda: 0.0, sleep=lambda s: None))  # fmt: skip
    monkeypatch.setattr(session, "rate_state", lambda limit=False: None)
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("GITHUB_WORKFLOW", "agk-route")
    monkeypatch.setenv("GITHUB_JOB", "route")
    return summary


def test_two_gets_one_304_and_one_post_write_one_line(monkeypatch, fresh, capsys):
    """REQ-039"""
    double = Double(
        (head("200 OK", {"ETag": '"e1"', **limits(4000)}, '{"n": 1}'), "", 0),
        (head("304 Not Modified", {"ETag": '"e1"', **limits(3999)}), "gh: HTTP 304\n", 1),
        ('{"id": 9}', "", 0),
    )
    monkeypatch.setattr(session.subprocess, "run", double)
    assert session.gh(EP) == {"n": 1}
    assert session.gh(EP) == {"n": 1}
    assert session.gh(EP + "/comments", "-f", "body=hi", method="POST") == {"id": 9}
    session.call_record()
    line = ("github calls: agk-route / route: 3 calls (1 cached, 1 writes, 0 waits, 0 s waited);"
            " limit 3999 of 5000 left, resets 17:46Z")  # fmt: skip
    assert fresh.read_text(encoding="utf-8") == line + "\n"
    assert line in capsys.readouterr().err
    assert EP not in line and "body" not in line and "body=hi" not in line


def test_the_routers_writes_and_searches_and_the_mergers_calls_count(monkeypatch, fresh):
    """REQ-039"""
    double = Double(("", "", 0), ('{"items": []}', "", 0), ("{}", "", 0), ("{}", "", 0))
    monkeypatch.setattr(subprocess, "run", double)
    route.write(EP + "/labels", "-f", "labels[]=x", method="POST")
    assert route.search_once("search/issues?q=x") == {"items": []}
    merge_cleared.gh_api(["--method", "PUT", EP + "/merge"])
    merge_cleared.gh_api([EP])
    assert (session.CALLS, session.WRITES) == (4, 2)


def test_a_shared_get_through_the_merger_counts_once(monkeypatch, fresh):
    """REQ-039"""
    double = Double((head("200 OK", limits(10)), "", 0))
    monkeypatch.setattr(subprocess, "run", double)
    merge_cleared.shared_get(EP)
    assert (session.CALLS, session.WRITES) == (1, 0)
    assert session.LIMIT_SEEN["x-ratelimit-remaining"] == "10"


def test_a_primary_wait_counts_one_wait_and_its_seconds(monkeypatch, fresh):
    """REQ-039"""
    spent = {"X-Ratelimit-Remaining": "0", "X-Ratelimit-Limit": "5000",
             "X-Ratelimit-Reset": str(RESET - 600 + 99)}  # fmt: skip
    double = Double(
        (head("403 Forbidden", spent, '{"message": "x"}'), "gh: API rate limit exceeded\n", 1),
        (head("200 OK", limits(4999), "{}"), "", 0),
    )
    monkeypatch.setattr(session.subprocess, "run", double)
    assert session.gh(EP) == {}
    assert (session.CALLS, session.WAITS, session.WAITED) == (2, 1, 99.0 + session.RESET_SLACK)
    session.call_record()
    assert "2 calls (0 cached, 0 writes, 1 waits, 100 s waited); limit 4999 of 5000" in (
        fresh.read_text(encoding="utf-8")
    )


def test_no_headers_reads_rate_limit_once(monkeypatch, fresh):
    """REQ-039"""
    asked = []
    monkeypatch.setattr(
        session, "rate_state", lambda limit=False: asked.append(limit) or (12.0, 60.0, float(RESET))
    )
    session.count_call("GET")
    session.call_record()
    assert asked == [True]
    assert fresh.read_text(encoding="utf-8").endswith(
        "1 calls (0 cached, 0 writes, 0 waits, 0 s waited); limit 12 of 60 left, resets 17:46Z\n"
    )


def test_a_figure_that_cannot_be_read_is_unknown_never_zero(fresh):
    """REQ-039"""
    session.count_call("POST")
    session.call_record()
    assert fresh.read_text(encoding="utf-8").endswith(
        "1 calls (0 cached, 1 writes, 0 waits, 0 s waited);"
        " limit unknown of unknown left, resets unknown\n"
    )


def test_rate_state_returns_the_limit_when_asked(monkeypatch):
    """REQ-039"""
    core = {"resources": {"core": {"remaining": 7, "limit": 60, "reset": RESET}}}
    monkeypatch.setattr(session.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(
        a, 0, json.dumps(core), ""))  # fmt: skip
    assert session.rate_state() == (7.0, float(RESET))
    assert session.rate_state(limit=True) == (7.0, 60.0, float(RESET))


@pytest.mark.parametrize("unset", ["GITHUB_ACTIONS", "calls"])
def test_outside_actions_or_with_no_call_nothing_is_written(monkeypatch, fresh, capsys, unset):
    """REQ-039"""
    if unset == "GITHUB_ACTIONS":
        monkeypatch.delenv("GITHUB_ACTIONS")
        session.count_call("GET")
    session.call_record()
    assert not fresh.exists()
    assert "github calls" not in capsys.readouterr().err


def test_an_unwritable_summary_prints_the_refusal(monkeypatch, fresh, tmp_path, capsys):
    """REQ-039"""
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "no" / "such" / "summary.md"))
    session.count_call("GET")
    assert session.call_record() is None
    err = capsys.readouterr().err
    assert err.count(REFUSED) == 1 and "github calls: agk-route / route: 1 calls" in err


def test_a_paused_router_makes_no_call_and_writes_no_line(monkeypatch, fresh, tmp_path):
    """REQ-039"""
    (tmp_path / "agk.toml").write_text("paused = true\n", encoding="utf-8")
    monkeypatch.setattr(route, "repo_root", lambda: tmp_path)
    assert route.main([]) == 0
    session.call_record()
    assert session.CALLS == 0 and not fresh.exists()


def test_atexit_writes_the_line_and_keeps_the_exit_code(tmp_path):
    """REQ-039"""
    summary = tmp_path / "summary.md"
    child = (
        "import subprocess, sys\n"
        f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
        "import session\n"
        "session.RUN = lambda argv: subprocess.CompletedProcess(argv, 0, '{}', '')\n"
        "session.gh('repos/acme/widgets/issues/7', '-f', 'x=1', method='PATCH')\n"
        "sys.exit(3)\n"
    )
    env = {**os.environ, "GITHUB_ACTIONS": "true", "GITHUB_STEP_SUMMARY": str(summary),
           "GITHUB_WORKFLOW": "merger", "GITHUB_JOB": "merge", "AGK_READ_CACHE": "off",
           "PATH": ""}  # fmt: skip
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-c", child], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert proc.returncode == 3
    text = summary.read_text(encoding="utf-8")
    assert text.startswith("github calls: merger / merge: 1 calls (0 cached, 1 writes, 0 waits")
    assert "limit unknown of unknown left, resets unknown" in text
