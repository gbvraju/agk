"""A brief that running work depends on is never held back by that work (brief #1432, ADR-0600).

REQ-050. `session_plan.running_conflict`, the wait judgement `plan`, `next` and `claim` share,
lifts the overlap of a holder that waits on the brief by `Depends-on:` (directly or down a chain of
open briefs), prints why, and reports a true cycle to the owner. The survey is built in memory from
recorded issue and pull request lists; `gh` fails if called, so no extra GitHub read is made.
Invented data only; no network."""

from __future__ import annotations

import pytest
import session_plan
from session_plan import Survey, ahead_lines, running_conflict, wait_text, waves

REPO = "example/project"


@pytest.fixture(autouse=True)
def no_github(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError(f"no GitHub call is allowed: {args}")

    monkeypatch.setattr(session_plan, "gh", refuse)
    monkeypatch.setattr(session_plan, "pages", refuse)


def issue(number: int, touches: str, *deps: object, state: str = "open") -> dict:
    lines = [f"Brief {number}.", f"Touches: {touches}", "Priority: 1"]
    lines += [f"Depends-on: #{d}" for d in deps]
    return {"number": number, "state": state, "title": f"brief {number}", "body": "\n".join(lines)}


def pull(number: int, brief: int, *deps: object) -> dict:
    body = "\n".join([f"Brief: #{brief}", *(f"Depends-on: #{d}" for d in deps)])
    return {"number": number, "state": "open", "body": body, "head": {"sha": "a" * 40}}


def scene(briefs: list[dict], held: list[int] = (), pulls: dict | None = None) -> Survey:
    """Open briefs; `held` are taken with no pull request; `pulls` maps a pull request to the
    one file it changes."""
    pulls = pulls or {}
    prs = [p for p, _ in pulls.values()]
    s = Survey(REPO, "cb1", 4, 24, prs, prs)
    s.briefs = {b["number"]: b for b in briefs}
    s.held = [(n, session_plan.touches_of(s.briefs[n]["body"])) for n in held]
    s.files = {p["number"]: [{"filename": f, "status": "modified"}] for p, f in pulls.values()}
    return s


def judge(tmp_path, s: Survey, number: int) -> dict | None:
    return running_conflict(tmp_path, s, s.briefs[number], [])


TEST = "tests/kit_dev/test_upgrade.py"


def test_the_case_that_prompted_it(tmp_path):
    """Answer 5: a taken `Touches: **` brief whose pull request depends on an S brief."""
    s = scene(
        [issue(24, "**"), issue(31, TEST)],
        pulls={29: (pull(29, 24, 31), TEST)},
    )
    assert judge(tmp_path, s, 31) is None
    assert ahead_lines(s, 31) == [
        f"#31 starts ahead of #29, which depends on it (overlap on {TEST} ignored)"
    ]


def test_without_the_line_the_overlap_still_holds(tmp_path):
    """Before: the same scene without `Depends-on:` still waits (the rule only lifts it)."""
    s = scene([issue(24, "**"), issue(31, TEST)], pulls={29: (pull(29, 24), TEST)})
    assert judge(tmp_path, s, 31)["pull_request"] == 29


def test_the_holder_brief_body(tmp_path):
    """Answer 1: the taken holder brief's body names the brief (no pull request yet)."""
    s = scene([issue(24, "a.py", 31), issue(31, "a.py")], held=[24])
    assert judge(tmp_path, s, 31) is None
    assert ahead_lines(s, 31) == [
        "#31 starts ahead of #24, which depends on it (overlap on a.py ignored)"
    ]


def test_the_pull_request_body_only(tmp_path):
    """Answer 1: only the holder's pull request body carries the line."""
    s = scene([issue(24, "a.py"), issue(31, "a.py")], pulls={29: (pull(29, 24, 31), "a.py")})
    assert judge(tmp_path, s, 31) is None


def test_a_chain(tmp_path):
    """Answer 1: the holder depends on #m, which depends on #n."""
    s = scene([issue(24, "a.py", 40), issue(40, "z.py", 31), issue(31, "a.py")], held=[24])
    assert judge(tmp_path, s, 31) is None


def test_a_second_unrelated_holder_still_holds(tmp_path):
    """Answer 2: only the dependency is lifted."""
    s = scene([issue(24, "a.py", 31), issue(25, "a.py"), issue(31, "a.py")], held=[24, 25])
    assert judge(tmp_path, s, 31) == {"brief": 31, "waits_for": 25, "why": "both touch a.py"}


def test_a_two_brief_cycle(tmp_path):
    """Answer 3: the exact line, nothing starts, and the owner line names both lines."""
    s = scene([issue(24, "a.py", 31), issue(31, "a.py", 24)], held=[24])
    found = judge(tmp_path, s, 31)
    assert wait_text(found) == (
        "CYCLE: #24 and #31 wait on each other (Depends-on); the owner chooses which goes first"
    )
    assert found["owner"] == (
        "Owner needed: #24 and #31 wait on each other (Depends-on); remove one of: "
        "`Depends-on: #31` in #24, `Depends-on: #24` in #31"
    )


def test_a_three_brief_cycle(tmp_path):
    """Answer 3: down a chain both ways."""
    s = scene([issue(24, "a.py", 40), issue(40, "z.py", 31), issue(31, "a.py", 24)], held=[24])
    found = judge(tmp_path, s, 31)
    assert found["cycle"] == 24
    assert found["owner"].endswith(
        "`Depends-on: #40` in #24, `Depends-on: #31` in #40, `Depends-on: #24` in #31"
    )


@pytest.mark.parametrize("line", ["#77", "#29", "#31x", "#24"])
def test_only_open_valid_lines_count(tmp_path, line):
    """Answer 4: a closed brief (77), a merged pull request (29), a malformed number and the
    holder itself are ignored, so the overlap holds."""
    holder = issue(24, "a.py")
    holder["body"] += f"\nDepends-on: {line}"
    closed = issue(77, "q.py", 31, state="closed")
    s = scene([holder, issue(31, "a.py"), closed], held=[24])
    s.prs.append({"number": 29, "state": "closed", "merged_at": "2026-11-16T00:00:00Z"})
    assert judge(tmp_path, s, 31) == {"brief": 31, "waits_for": 24, "why": "both touch a.py"}


def test_the_brief_naming_itself_is_ignored(tmp_path):
    """Answer 4: the brief's own number is no dependency of the holder's chain."""
    s = scene([issue(24, "a.py"), issue(31, "a.py", 31)], held=[24])
    assert judge(tmp_path, s, 31)["waits_for"] == 24


def test_two_dependencies_that_overlap_keep_their_order(tmp_path):
    """Answer 5: both are lifted from the holder; priority then number still orders them."""
    s = scene([issue(24, "**", 31, 32), issue(31, "a.py"), issue(32, "a.py")], held=[24])
    chosen, waits = waves(tmp_path, s, [s.briefs[31], s.briefs[32]])
    assert [b["number"] for b in chosen] == [31]
    assert waits == [{"brief": 32, "waits_for": 31, "why": "both touch a.py"}]


def test_personal_mode_reads_the_same_bodies(tmp_path):
    """Answer 5: a sidecar's briefs and the local branch's pull request body arrive in the same
    survey shape (the files forge serves them), so the same rule applies."""
    s = scene([issue(3, "**"), issue(5, "src/app.py")], pulls={1: (pull(1, 3, 5), "src/app.py")})
    s.repo = "local/sidecar"
    assert judge(tmp_path, s, 5) is None


def test_the_holders_list_leaves_out_a_lifted_hold(tmp_path):
    """Answer 1: the plan's `Holds` lines agree with the wait judgement."""
    from datetime import UTC, datetime

    s = scene([issue(24, "**"), issue(31, TEST)], pulls={29: (pull(29, 24, 31), TEST)})
    s.builders[0]["updated_at"] = "2026-11-17T00:00:00Z"
    now = datetime(2026, 11, 17, tzinfo=UTC)
    assert session_plan.holders(tmp_path, s, [s.briefs[31]], now) == []


def test_the_plan_prints_the_reason_and_starts_it(tmp_path, repo, monkeypatch):
    """Answer 1: `session.py plan` prints the line and starts the brief; `--json` carries it."""
    import json

    from test_session import REPO as STUB_REPO
    from test_session import Stub, listing
    from test_session import issue as listed
    from test_session_flow import PULLS, brief, pr
    from test_session_plan import changed, free, plan

    monkeypatch.undo()  # the plan runs as a process, through the `gh` stub
    stub = Stub(tmp_path)
    repo.git("remote", "add", "origin", f"https://github.com/{STUB_REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    holder = pr(20, 90)
    holder["body"] += "Depends-on: #5\n"
    stub.serve(PULLS, [holder])
    changed(stub, 20, ("modified", "a.py"))
    listing(stub, [listed(5, brief("a.py"))])
    free(stub, 5)
    out = plan(repo, stub)
    assert "#5 starts ahead of #20, which depends on it (overlap on a.py ignored)" in out.stdout
    assert "takes #5" in out.stdout, out.stdout + out.stderr
    got = json.loads(plan(repo, stub, "--json").stdout)
    assert got["ahead"] == ["#5 starts ahead of #20, which depends on it (overlap on a.py ignored)"]


def test_next_and_claim_print_the_reason_and_a_cycle_is_refused(tmp_path, repo, monkeypatch):
    """Answers 1 and 3: `next` and `claim` share the judgement and print the same line; with the
    loop closed `claim` refuses with the CYCLE line and posts nothing, and `plan` prints the
    line once and carries the owner's line."""
    import json

    from test_session import REPO as STUB_REPO
    from test_session import Stub, comment, listing, posts, session
    from test_session import issue as listed
    from test_session_flow import DAY, PULLS, brief, pr
    from test_session_plan import changed, plan

    monkeypatch.undo()
    stub = Stub(tmp_path)
    repo.git("remote", "add", "origin", f"https://github.com/{STUB_REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    line = "#6 starts ahead of #20, which depends on it (overlap on a.py ignored)"
    holder = pr(20, 5)
    holder["body"] += "Depends-on: #6\n"
    stub.serve(PULLS, [holder])
    changed(stub, 20, ("modified", "a.py"))
    listing(stub, [listed(5, brief("**")), listed(6, brief("a.py"))])
    stub.serve(f"repos/{STUB_REPO}/issues/5/comments", [comment(1, "x", f"taken: s-other {DAY}")])
    stub.serve(f"repos/{STUB_REPO}/issues/6/comments", [])
    shown = session(repo, stub, "next", "--session", "s-me")
    assert line in shown.stdout.splitlines(), shown.stdout + shown.stderr
    out = session(repo, stub, "claim", "--session", "s-me", "--brief", "6")
    assert line in out.stdout.splitlines() and "claimed #6" in out.stdout, out.stdout + out.stderr
    listing(stub, [listed(5, brief("**")), listed(6, brief("a.py") + "Depends-on: #5\n")])
    stub.serve(f"repos/{STUB_REPO}/issues/6/comments", [])
    before = len(posts(stub))
    out = session(repo, stub, "claim", "--session", "s-me", "--brief", "6")
    cycle = "CYCLE: #5 and #6 wait on each other (Depends-on); the owner chooses which goes first"
    assert out.returncode == 1, out.stdout + out.stderr
    assert out.stdout.strip() == f"skip #6: {cycle}"
    assert len(posts(stub)) == before
    shown = plan(repo, stub)
    assert shown.stdout.splitlines().count(cycle) == 1, shown.stdout + shown.stderr
    got = json.loads(plan(repo, stub, "--json").stdout)
    assert got["cycles"] == [
        {
            "why": cycle,
            "owner": "Owner needed: #5 and #6 wait on each other (Depends-on); remove one of: "
            "`Depends-on: #5` in #6, `Depends-on: #6` in #5",
        }
    ]


@pytest.mark.parametrize("status", ["modified", "added"])
def test_the_file_is_read_from_both_wordings(tmp_path, status):
    """Fix list on d9e1694: `it changes <file>` and `it adds <file>` both name the file."""
    s = scene([issue(24, "**"), issue(31, TEST)], pulls={29: (pull(29, 24, 31), TEST)})
    s.files[29][0]["status"] = status
    assert judge(tmp_path, s, 31) is None
    assert ahead_lines(s, 31) == [
        f"#31 starts ahead of #29, which depends on it (overlap on {TEST} ignored)"
    ]


def test_an_unknown_wording_is_kept_whole():
    """Fix list on d9e1694: a reason in other words is kept, never raised on."""
    assert session_plan.conflict_file("it changes a.py") == "a.py"
    assert session_plan.conflict_file("it adds b/c.py") == "b/c.py"
    assert session_plan.conflict_file("some other reason") == "some other reason"
