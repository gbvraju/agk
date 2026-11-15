"""A GitHub limit is waited out as GitHub asks, and the kit paces and counts its own writes.

Brief #1335, ADR-0565; REQ-050. `session.gh()` decides the wait of a limited call in this order:
the `retry-after` seconds when the response carries them; else the `x-ratelimit-reset` time when
`x-ratelimit-remaining` is 0 (the primary limit); else 60 seconds, doubled on each further try of
the same call. With no header to read, `GET rate_limit` stays the fallback. A secondary wait is
capped at 15 minutes, after which the call counts as failed; a primary one is taken as given.
Two mutating calls of one process are at least one second apart; reads are not delayed. A run
counts its writes and the plan's `reads:` line ends `writes: <n>`. A recorded double of `gh`
(`subprocess.run`) and a fake clock: no network, no real sleep."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - only the double's CompletedProcess is built
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import checklist  # noqa: E402
import session  # noqa: E402
import session_plan  # noqa: E402

EP = "repos/acme/widgets/issues/7"
SECONDARY = "gh: You have exceeded a secondary rate limit. (HTTP 403)\n"
PRIMARY = "gh: API rate limit exceeded for user ID 1. (HTTP 403)\n"


class Clock:
    def __init__(self) -> None:
        self.now = 1_000_000.0
        self.slept: list[float] = []

    def time(self) -> float:
        return self.now

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def limited(headers: dict[str, str] | None, stderr: str = SECONDARY) -> tuple:
    if headers is None:
        return ("", stderr, 1)
    head = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
    return (f"HTTP/2.0 403 Forbidden\r\n{head}\r\n" + '{"message": "limited"}', stderr, 1)


def ok(body: object = None, headers: bool = True) -> tuple:
    text = json.dumps({"ok": True} if body is None else body)
    return (f"HTTP/2.0 200 OK\r\nContent-Type: application/json\r\n\r\n{text}" if headers else text,
            "", 0)  # fmt: skip


class Double:
    """`gh`: each call answers with the next queued response; `rate_limit` with its own."""

    def __init__(self, *answers: tuple, rate: dict | None = None) -> None:
        self.answers = list(answers)
        self.rate = rate
        self.calls: list[list[str]] = []

    def __call__(self, args, **_kw):
        self.calls.append(list(args))
        if "rate_limit" in args:
            text = json.dumps({"resources": {"core": self.rate}}) if self.rate else ""
            return subprocess.CompletedProcess(args, 0 if self.rate else 1, text, "")
        out, err, code = self.answers.pop(0)
        return subprocess.CompletedProcess(args, code, out, err)


@pytest.fixture
def clock(monkeypatch):
    found = Clock()
    monkeypatch.setattr(session, "time", SimpleNamespace(
        time=found.time, monotonic=found.monotonic, sleep=found.sleep))  # fmt: skip
    monkeypatch.setattr(session.CACHE, "place", None)
    monkeypatch.setattr(session, "MEMO", None)
    monkeypatch.setattr(session, "WRITES", 0)
    monkeypatch.setattr(session, "LAST_WRITE", None)
    return found


def run(monkeypatch, double: Double, *extra: str, method: str = "GET"):
    monkeypatch.setattr(session.subprocess, "run", double)
    return session.gh(EP, *extra, method=method)


def test_the_wait_is_the_retry_after_seconds(monkeypatch, clock, capsys):
    """REQ-050"""
    double = Double(limited({"Retry-After": "30", "X-Ratelimit-Remaining": "4000"}), ok())
    assert run(monkeypatch, double) == {"ok": True}
    assert clock.slept == [30.0]
    assert "github: limited, waiting 30 s (secondary)" in capsys.readouterr().err
    assert not any("rate_limit" in c for c in double.calls)  # no extra request


def test_a_spent_primary_limit_waits_until_the_reset_time(monkeypatch, clock, capsys):
    """REQ-050"""
    reset = str(int(clock.now) + 100)
    double = Double(limited({"X-Ratelimit-Remaining": "0", "X-Ratelimit-Reset": reset}, PRIMARY),
                    ok())  # fmt: skip
    assert run(monkeypatch, double) == {"ok": True}
    assert clock.slept == [100.0 + session.RESET_SLACK]
    assert "waiting 101 s (primary)" in capsys.readouterr().err


def test_otherwise_sixty_seconds_doubled_on_each_further_try(monkeypatch, clock):
    """REQ-050"""
    head = {"X-Ratelimit-Remaining": "4000"}
    double = Double(limited(head), limited(head), limited(head), ok())
    assert run(monkeypatch, double) == {"ok": True}
    assert clock.slept == [60.0, 120.0, 240.0]


def test_with_no_header_rate_limit_is_the_fallback(monkeypatch, clock):
    """REQ-050"""
    reset = int(clock.now) + 50
    double = Double(limited(None, PRIMARY), ok(), rate={"remaining": 0, "reset": reset})
    assert run(monkeypatch, double) == {"ok": True}
    assert clock.slept == [50.0 + session.RESET_SLACK]
    double = Double(limited(None), ok(), rate={"remaining": 4000, "reset": reset + 3000})
    clock.slept.clear()
    assert run(monkeypatch, double) == {"ok": True}
    assert clock.slept == [60.0]  # a secondary limit never sleeps to the core reset
    double = Double(limited(None))  # rate_limit unreadable too: the call fails, as before
    assert run(monkeypatch, double) is None


@pytest.mark.parametrize("value", ["0", "soon", "-5"])
def test_a_retry_after_of_zero_or_unreadable_falls_to_the_next_rule(monkeypatch, clock, value):
    """REQ-050"""
    double = Double(limited({"Retry-After": value, "X-Ratelimit-Remaining": "12"}), ok())
    assert run(monkeypatch, double) == {"ok": True}
    assert clock.slept == [60.0]


def test_a_long_primary_wait_is_taken_and_a_long_secondary_one_capped(monkeypatch, clock):
    """REQ-050"""
    reset = str(int(clock.now) + 3600)
    double = Double(limited({"X-Ratelimit-Remaining": "0", "X-Ratelimit-Reset": reset}), ok())
    assert run(monkeypatch, double) == {"ok": True}
    assert clock.slept == [3600.0 + session.RESET_SLACK]
    clock.slept.clear()
    double = Double(limited({"Retry-After": "2000", "X-Ratelimit-Remaining": "9"}), ok())
    assert run(monkeypatch, double) is None  # counted as failed after the capped wait
    assert clock.slept == [session.SECONDARY_CAP]
    assert len(double.answers) == 1  # never retried


def test_a_304_never_waits(monkeypatch, clock, tmp_path):
    """REQ-050"""
    folder = tmp_path / "cache"
    folder.mkdir(mode=0o700)
    monkeypatch.setattr(session.CACHE, "place", folder)
    session.CACHE.keep(EP, '"e1"', {"kept": 1})
    double = Double(("HTTP/2.0 304 Not Modified\r\nEtag: \"e1\"\r\n\r\n", "gh: HTTP 304\n", 1))
    assert run(monkeypatch, double) == {"kept": 1}
    assert clock.slept == []


def test_a_cached_read_during_a_wait_is_answered_from_the_cache(monkeypatch, clock):
    """REQ-050"""
    monkeypatch.setattr(session, "MEMO", {(EP,): {"held": True}})
    double = Double()
    assert run(monkeypatch, double) == {"held": True}
    assert double.calls == [] and clock.slept == []


def test_two_writes_are_one_second_apart_and_reads_are_not_delayed(monkeypatch, clock):
    """REQ-050"""
    double = Double(ok({}, headers=False), ok(), ok({}, headers=False))
    run(monkeypatch, double, "-f", "body=a", method="POST")
    clock.now += 0.25
    run(monkeypatch, double)  # a read between them: no pause
    assert clock.slept == []
    run(monkeypatch, double, "-f", "body=b", method="PATCH")
    assert clock.slept == [pytest.approx(0.75)]
    clock.now += 5
    clock.slept.clear()
    double.answers.append(ok({}, headers=False))
    run(monkeypatch, double, method="DELETE")
    assert clock.slept == []


def test_a_limited_write_waits_as_rate_limit_reports(monkeypatch, clock):
    """REQ-050: a write carries no `-i`, so its limit's kind comes from `GET rate_limit`."""
    double = Double(limited(None), ok({"id": 1}, headers=False), rate={"remaining": 9, "reset": 1})
    assert run(monkeypatch, double, "-f", "body=a", method="POST") == {"id": 1}
    assert clock.slept == [60.0]
    assert "-i" not in double.calls[0]


def test_a_run_counts_its_writes_and_the_reads_line_ends_with_them(monkeypatch, clock, tmp_path):
    """REQ-050"""
    double = Double(ok({}, headers=False), ok(), ok({}, headers=False))
    run(monkeypatch, double, "-f", "body=a", method="POST")
    run(monkeypatch, double)
    run(monkeypatch, double, method="PUT")
    assert session.WRITES == 2
    figures = {"calls": 3, "cached": 0, "seconds": 0.5}
    assert session_plan.reads_line(figures) == "reads: 3 calls (0 from cache), 0.5 s"
    assert session_plan.reads_line({**figures, "writes": 2}).endswith(", writes: 2")
    saved = tmp_path / "agk-plan-reads.json"
    saved.write_text(json.dumps({**figures, "writes": 2}), encoding="utf-8")
    assert checklist.plan_reads(saved) == "plan reads 3 calls (0 from cache), 0.5 s, writes 2"
