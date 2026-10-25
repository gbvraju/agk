"""session.py watch and next against a `gh` stub (SPEC-0030 rules 2, 3 and 5; REQ-037 AC2, AC3)."""

from __future__ import annotations

import json
import os
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

STUB = '''#!/usr/bin/env python3
"""A gh stub: serves fixtures/<endpoint>.json (or .N.json for the Nth call), logs every call."""
import json, os, sys
args = sys.argv[1:]
root = os.environ["GH_STUB_DIR"]
method = args[args.index("--method") + 1]
endpoint = args[args.index("--method") + 2]
with open(os.path.join(root, "calls.log"), "a") as log:
    log.write(json.dumps([method, endpoint, args[args.index("--method") + 3:]]) + "\\n")
name = endpoint.split("?")[0].replace("/", "__")
count_file = os.path.join(root, "count." + method + "." + name)
n = int(open(count_file).read()) + 1 if os.path.exists(count_file) else 1
open(count_file, "w").write(str(n))
if method == "POST" and not any(f.startswith(name + ".POST") for f in os.listdir(root)):
    print("{}")
    sys.exit(0)
for candidate in (name + "." + method + "." + str(n), name + "." + method):
    path = os.path.join(root, candidate + ".json")
    if os.path.exists(path):
        text = open(path).read()
        if text.strip() == "FAIL":
            sys.exit(1)
        sys.stdout.write(text)
        sys.exit(0)
sys.exit(1)
'''

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"


def clean_env() -> dict[str, str]:
    drop = ("GITHUB_BASE_REF", "AGK_BASE", "CI", "AGK_KIT_TESTS")
    return {k: v for k, v in os.environ.items() if k not in drop}


REPO = "acme/widgets"
SHA = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"


def iso(delta: timedelta = timedelta(0)) -> str:
    return (datetime.now(UTC) + delta).strftime("%Y-%m-%dT%H:%M:%SZ")


class Stub:
    def __init__(self, tmp: Path) -> None:
        self.dir = tmp / "stub"
        self.dir.mkdir()
        self.bin = tmp / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(STUB, encoding="utf-8")
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)

    def serve(self, endpoint: str, data: object, method: str = "GET", nth: int | None = None):
        name = endpoint.replace("/", "__") + "." + method + (f".{nth}" if nth else "")
        text = data if isinstance(data, str) else json.dumps(data)
        (self.dir / f"{name}.json").write_text(text, encoding="utf-8")

    def calls(self) -> list[list]:
        log = self.dir / "calls.log"
        return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []


@pytest.fixture
def stub(tmp_path: Path) -> Stub:
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    return repo


def session(proj, stub, *args: str):
    env = clean_env()
    env.update(PATH=f"{stub.bin}{os.pathsep}{os.environ['PATH']}", GH_STUB_DIR=str(stub.dir))
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "session.py"), *args],
        cwd=proj.root,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def comment(cid: int, login: str, body: str, when: str | None = None) -> dict:
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": when or iso()}


def pull(
    state: str = "open",
    merged: str | None = None,
    author: str = "builder",
    mergeable: str = "clean",
) -> dict:
    return {
        "mergeable_state": mergeable,
        "state": state,
        "merged_at": merged,
        "user": {"login": author},
        "head": {"sha": SHA},
    }


PR = f"repos/{REPO}/pulls/7"
PR_COMMENTS = f"repos/{REPO}/issues/7/comments"
WATCH = ("watch", "--pr", "7", "--interval", "0", "--timeout", "5")


def watching(stub: Stub, polls: list[tuple[dict | str, list | str]], base: list | None = None):
    """The first comments read is the baseline; each poll is a pulls read and a comments read."""
    stub.serve(PR_COMMENTS, base or [], nth=1)
    for i, (p, c) in enumerate(polls, start=1):
        stub.serve(PR, p, nth=i)
        stub.serve(PR_COMMENTS, c, nth=i + 1)


# --- watch (rules 2 and 5; AC2) -----------------------------------------------------------------


def test_ac2_watch_ends_on_a_verdict_of_a_listed_author_naming_the_head(proj, stub):
    """REQ-037 AC2"""
    old = comment(1, "boss", f"Verdict: cleared {SHA[:7]}")
    new = comment(9, "Boss", f"Verdict: fix list {SHA[:9]}\n\n1. a thing")
    watching(stub, [(pull(), [old, new])], base=[old])
    out = session(proj, stub, *WATCH)
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.strip() == f"verdict fix list {SHA[:9]} (comment 9)"


def test_ac2_watch_ignores_unlisted_authors_other_heads_and_other_comments(proj, stub):
    """REQ-037 AC2"""
    ignored = [
        comment(2, "stranger", f"Verdict: cleared {SHA[:7]}"),
        comment(3, "boss", "Verdict: cleared 1234567"),
        comment(4, "boss", f"please merge {SHA[:7]}"),
        comment(5, "boss", f"note\nVerdict: cleared {SHA[:7]}"),
        comment(6, "boss", "Verdict: fix list"),
    ]
    watching(stub, [(pull(), ignored)], base=[])
    out = session(proj, stub, "watch", "--pr", "7", "--interval", "0", "--timeout", "0")
    assert out.returncode == 3 and out.stdout.strip() == "timeout"


def test_ac2_watch_does_not_end_on_a_verdict_older_than_the_start(proj, stub):
    """REQ-037 AC2"""
    old = comment(2, "boss", f"Verdict: cleared {SHA[:7]}")
    watching(stub, [(pull(), [old])], base=[old])
    out = session(proj, stub, "watch", "--pr", "7", "--interval", "0", "--timeout", "0")
    assert out.returncode == 3


def test_ac2_watch_drops_the_pull_requests_own_author_when_two_are_listed(proj, stub):
    """REQ-037 AC2"""
    own = comment(3, "second", f"Verdict: cleared {SHA[:7]}")
    watching(stub, [(pull(author="second"), [own])], base=[])
    out = session(proj, stub, "watch", "--pr", "7", "--interval", "0", "--timeout", "0")
    assert out.returncode == 3


@pytest.mark.parametrize(
    ("state", "line"),
    [
        (pull(merged="2026-10-24T10:00:00Z", state="closed"), "merged #7"),
        (pull("closed"), "closed #7"),
    ],
)
def test_ac2_watch_ends_on_a_merge_and_on_a_close(proj, stub, state, line):
    """REQ-037 AC2"""
    watching(stub, [(state, [])])
    out = session(proj, stub, *WATCH)
    assert out.returncode == 0 and out.stdout.strip() == line


def test_ac2_watch_retries_a_failed_get_on_the_next_poll(proj, stub):
    """REQ-037 AC2"""
    watching(stub, [("FAIL", "FAIL"), (pull(merged="2026-10-24T10:00:00Z", state="closed"), [])])
    out = session(proj, stub, *WATCH)
    assert out.returncode == 0 and out.stdout.strip() == "merged #7"


def test_ac2_watch_ends_with_one_line_when_the_pull_request_has_a_conflict(proj, stub):
    """REQ-037 AC2 (the verdict on #169: a conflict is seen without a person noticing)"""
    watching(stub, [(pull(mergeable="dirty"), [])])
    out = session(proj, stub, *WATCH)
    assert out.returncode == 0 and out.stdout.strip() == "conflict #7"


@pytest.mark.parametrize("mergeable", ["clean", "blocked", "unknown", "behind", "unstable"])
def test_ac2_watch_goes_on_for_every_other_mergeable_state(proj, stub, mergeable):
    """REQ-037 AC2"""
    watching(stub, [(pull(mergeable=mergeable), [])])
    out = session(proj, stub, "watch", "--pr", "7", "--interval", "0", "--timeout", "0")
    assert out.returncode == 3


def test_ac2_watch_merged_ignores_a_conflict(proj, stub):
    """REQ-037 AC2"""
    other = f"repos/{REPO}/pulls/12"
    stub.serve(other, pull(mergeable="dirty"))
    out = session(proj, stub, "watch", "--merged", "12", "--interval", "0", "--timeout", "0")
    assert out.returncode == 3


def test_ac2_watch_with_a_timeout_and_no_event_exits_3(proj, stub):
    """REQ-037 AC2"""
    watching(stub, [(pull(), [])] * 3)
    out = session(proj, stub, "watch", "--pr", "7", "--interval", "0", "--timeout", "0")
    assert out.returncode == 3 and out.stdout.strip() == "timeout"


def test_ac2_watch_merged_waits_on_another_pull_request_and_ignores_verdicts(proj, stub):
    """REQ-037 AC2 (the `--merged N` mode of the verdict on #167)"""
    other = f"repos/{REPO}/pulls/12"
    stub.serve(other, pull(), nth=1)
    stub.serve(other, pull(merged="2026-10-24T10:00:00Z", state="closed"), nth=2)
    out = session(proj, stub, "watch", "--merged", "12", "--interval", "0", "--timeout", "5")
    assert out.returncode == 0 and out.stdout.strip() == "merged #12"
    assert not any("comments" in call[1] for call in stub.calls())


def test_ac2_watch_usage_is_checked(proj, stub):
    """REQ-037 AC2"""
    assert session(proj, stub, "watch").returncode == 2
    assert session(proj, stub, "watch", "--pr", "7", "--merged", "8").returncode == 2
    assert session(proj, stub, "watch", "--pr", "x").returncode == 2


def test_ac2_watch_writes_nothing_and_only_gets(proj, stub):
    """REQ-037 AC2 and rule 5"""
    watching(stub, [(pull("closed"), [])])
    session(proj, stub, *WATCH)
    assert stub.calls() and all(call[0] == "GET" for call in stub.calls())


# --- next (rule 3; AC3) --------------------------------------------------------------------------

ISSUES = f"repos/{REPO}/issues"
GOOD = (
    'Sentence: "A thing works."\n'
    "Answers (the maintainers'):\n1. one\n2. two\n"
    "Depends-on: #3\nSize: M\n"
)


FREE = GOOD.replace("Depends-on: #3\n", "")


def issue(number: int, body: str = GOOD, title: str = "t") -> dict:
    url = f"https://github.com/{REPO}/issues/{number}"
    return {"number": number, "title": f"{title}{number}", "body": body, "html_url": url}


def listing(stub: Stub, issues: list[dict]) -> None:
    stub.serve(ISSUES, issues)


def state(stub: Stub, number: int, name: str) -> None:
    stub.serve(f"{ISSUES}/{number}", {"number": number, "state": name})


def take(cid: int, who: str, when: str | None = None, login: str = "someone") -> dict:
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    return comment(cid, login, f"taken: {who} {day}", when)


def nxt(proj, stub, who: str = "s-me"):
    return session(proj, stub, "next", "--session", who)


def posts(stub: Stub) -> list[list]:
    return [call for call in stub.calls() if call[0] == "POST"]


def test_ac3_next_takes_the_first_free_brief_with_the_one_post(proj, stub):
    """REQ-037 AC3"""
    listing(stub, [issue(9), issue(5)])
    state(stub, 3, "closed")
    stub.serve(f"{ISSUES}/5/comments", [], nth=1)
    stub.serve(f"{ISSUES}/5/comments", [take(1, "s-me", login="me")], nth=2)
    stub.serve(f"{ISSUES}/5/comments", {"id": 1}, method="POST")
    out = nxt(proj, stub)
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.startswith("brief #5\n")
    assert "t5" in out.stdout and f"https://github.com/{REPO}/issues/5" in out.stdout
    assert 'Sentence: "A thing works."' in out.stdout
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    assert posts(stub) == [["POST", f"{ISSUES}/5/comments", ["-f", f"body=taken: s-me {day}"]]]


def test_ac3_next_skips_a_bad_shape_an_open_dependence_and_a_live_take_with_reasons(proj, stub):
    """REQ-037 AC3"""
    listing(
        stub,
        [issue(4, "no shape here"), issue(5), issue(6, GOOD.replace("#3", "#2")), issue(8, FREE)],
    )
    state(stub, 3, "open")
    state(stub, 2, "closed")
    stub.serve(f"{ISSUES}/6/comments", [take(1, "s-other")], nth=1)
    stub.serve(f"{ISSUES}/8/comments", [], nth=1)
    stub.serve(f"{ISSUES}/8/comments", [take(2, "s-me", login="me")], nth=2)
    out = nxt(proj, stub)
    lines = out.stdout.splitlines()
    assert lines[0].startswith("skip #4: rule 4") and "no shape here" not in out.stdout
    assert "skip #5: depends on #3, which is open" in lines
    assert "skip #6: taken by s-other" in lines
    assert any(line == "brief #8" for line in lines) and out.returncode == 0


def test_ac3_next_does_not_post_when_the_brief_is_already_taken_by_this_session(proj, stub):
    """REQ-037 AC3"""
    listing(stub, [issue(5, FREE)])
    stub.serve(f"{ISSUES}/5/comments", [take(1, "s-me", login="me")])
    out = nxt(proj, stub)
    assert out.returncode == 0 and out.stdout.startswith("brief #5") and posts(stub) == []


def test_ac3_next_frees_a_take_older_than_24_hours_without_a_pull_request(proj, stub):
    """REQ-037 AC3"""
    old = iso(-timedelta(hours=30))
    listing(stub, [issue(5, FREE)])
    stub.serve(f"repos/{REPO}/pulls", [])
    stub.serve(f"{ISSUES}/5/comments", [take(1, "s-other", old)], nth=1)
    stub.serve(
        f"{ISSUES}/5/comments", [take(1, "s-other", old), take(2, "s-me", login="me")], nth=2
    )
    out = nxt(proj, stub)
    assert out.returncode == 0 and out.stdout.startswith("brief #5") and len(posts(stub)) == 1


def test_ac3_next_keeps_an_old_take_while_a_later_pull_request_by_the_taker_mentions_it(proj, stub):
    """REQ-037 AC3"""
    old = iso(-timedelta(hours=30))
    listing(stub, [issue(5, FREE)])
    mine = {
        "user": {"login": "someone"},
        "created_at": iso(-timedelta(hours=20)),
        "body": "Fixes #5",
    }
    other = {"user": {"login": "else"}, "created_at": iso(-timedelta(hours=20)), "body": "#5"}
    before = {"user": {"login": "someone"}, "created_at": iso(-timedelta(hours=40)), "body": "#5"}
    stub.serve(f"repos/{REPO}/pulls", [other, before, mine])
    stub.serve(f"{ISSUES}/5/comments", [take(1, "s-other", old)])
    out = nxt(proj, stub)
    assert out.returncode == 1 and "skip #5: taken by s-other" in out.stdout
    assert out.stdout.splitlines()[-1] == "no brief" and posts(stub) == []


def test_ac3_next_goes_on_when_two_takes_are_made_at_once_and_the_other_is_older(proj, stub):
    """REQ-037 AC3"""
    listing(stub, [issue(5, FREE), issue(6, FREE)])
    first, second = iso(-timedelta(seconds=5)), iso()
    stub.serve(f"{ISSUES}/5/comments", [], nth=1)
    stub.serve(
        f"{ISSUES}/5/comments",
        [take(1, "s-other", first, "x"), take(2, "s-me", second, "me")],
        nth=2,
    )
    stub.serve(f"{ISSUES}/6/comments", [], nth=1)
    stub.serve(f"{ISSUES}/6/comments", [take(3, "s-me", login="me")], nth=2)
    out = nxt(proj, stub)
    assert "skip #5: lost the take to s-other" in out.stdout.splitlines()
    assert out.stdout.splitlines()[-1].startswith("Sentence") or "brief #6" in out.stdout
    assert out.returncode == 0 and len(posts(stub)) == 2


def test_ac3_next_with_no_brief_left_says_so_and_exits_1(proj, stub):
    """REQ-037 AC3"""
    listing(stub, [{**issue(5), "pull_request": {}}])
    out = nxt(proj, stub)
    assert out.returncode == 1 and out.stdout.strip() == "no brief" and posts(stub) == []


def test_ac3_next_treats_an_unreadable_dependence_as_open_and_a_failed_list_as_a_failure(
    proj, stub
):
    """REQ-037 AC3"""
    listing(stub, [issue(5)])
    out = nxt(proj, stub)
    assert "skip #5: depends on #3, which cannot be read" in out.stdout and out.returncode == 1
    listing(stub, "FAIL")
    out = nxt(proj, stub)
    assert out.returncode == 2 and out.stdout.startswith("FAIL session: ")


def test_ac3_next_needs_a_session_id_that_is_a_plain_word(proj, stub):
    """REQ-037 AC3"""
    assert session(proj, stub, "next").returncode == 2
    assert session(proj, stub, "next", "--session", "a b").returncode == 2


def test_rule5_session_posts_only_its_two_take_comments_and_the_checks_do_not_call_gh():
    """REQ-037 AC2 and rule 5 (the take of SPEC-0030 and the takeover of SPEC-0033 rule 5)"""
    text = (SCRIPTS / "session.py").read_text(encoding="utf-8")
    assert text.count('method="POST"') == 2
    assert text.count('f"body=taken: ') == 1 and text.count('f"body=taken over: ') == 1
    for name in ("check_final_clearance.py", "check_brief.py", "facts.py"):
        path = SCRIPTS / name
        if path.exists() and name != "facts.py":
            assert '"gh"' not in path.read_text(encoding="utf-8")
