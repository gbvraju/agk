"""`claim` judges overlap as `next` and `plan` do, and the shared indexes are exempt (SPEC-0050).

Build (c) of SPEC-0050, brief #751; REQ-057 AC1 and AC2. Rules 2 to 4: `next`, `plan` and `claim`
call the one overlap judgement of `session_plan`, `claim` refuses an overlapping brief with the
same `skip` line and posts nothing, and `[flow] shared_indexes` (default the five indexes) never
makes an overlap. A `gh` stub serves saved JSON copies of the GitHub responses; no network."""

from __future__ import annotations

import pytest
from test_session import ISSUES, REPO, Stub, comment, issue, listing, posts, session
from test_session_flow import DAY, PULLS, brief, flow, pr
from test_session_next_plan import THREE
from test_session_plan import changed, data, free, plan

FILE = "scripts/agk/example.py"
WAIT = f"skip #6: waits for #5 (both touch {FILE})"


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    return repo


def look(proj, stub):
    return session(proj, stub, "next", "--session", "s-me")


def claim(proj, stub, number: int = 6, build: str | None = None):
    extra = ("--build", build) if build else ()
    return session(proj, stub, "claim", "--session", "s-me", "--brief", str(number), *extra)


def taken_by_other(stub: Stub, number: int, build: str | None = None) -> None:
    part = f" build ({build})" if build else ""
    stub.serve(f"{ISSUES}/{number}/comments", [comment(1, "x", f"taken: s-other {DAY}{part}")])


def lines(out) -> list[str]:
    return out.stdout.splitlines()


# --- rules 2 and 4: one judgement, three commands (REQ-057 AC1) ----------------------------------


def test_next_plan_and_claim_give_the_same_skip_line_and_claim_posts_nothing(proj, stub):
    """REQ-057 AC1: two briefs that both name scripts/agk/example.py, the first taken, give the
    same `skip` line from `next`, `plan` and `claim`, and `claim` posts nothing."""
    listing(stub, [issue(5, brief(f"{FILE}, a/x.py")), issue(6, brief(f"{FILE}, b/y.py"))])
    stub.serve(PULLS, [])
    taken_by_other(stub, 5)
    free(stub, 6)
    shown = look(proj, stub)
    assert WAIT in lines(shown), shown.stdout + shown.stderr
    got = data(proj, stub)
    assert {"brief": 6, "waits_for": 5, "why": f"both touch {FILE}"} in got["waits"]
    assert f"#6 waits for #5 (both touch {FILE})." in lines(plan(proj, stub))
    out = claim(proj, stub)
    assert out.returncode == 1, out.stdout + out.stderr
    assert out.stdout.strip() == WAIT
    assert posts(stub) == []


def test_claim_refuses_a_brief_that_overlaps_an_open_pull_request_that_modifies_the_file(
    proj, stub
):
    """REQ-057 AC1: an open builder pull request that modifies the file refuses the claim."""
    listing(stub, [issue(6, brief(FILE))])
    stub.serve(PULLS, [pr(20, 1)])
    changed(stub, 20, ("modified", FILE))
    free(stub, 6)
    out = claim(proj, stub)
    assert out.returncode == 1
    assert out.stdout.strip() == f"skip #6: waits for pull request #20 (it changes {FILE})"
    assert posts(stub) == []
    assert out.stdout.strip() in lines(look(proj, stub))


def test_claim_is_not_refused_by_a_pull_request_that_only_adds_another_file(proj, stub):
    """REQ-057 AC1: a file a pull request only adds blocks only on its exact path."""
    listing(stub, [issue(6, brief("scripts/agk/"))])
    stub.serve(PULLS, [pr(20, 1)])
    changed(stub, 20, ("added", "scripts/agk/other.py"))
    free(stub, 6)
    out = claim(proj, stub)
    assert out.returncode == 0 and out.stdout.strip() == "claimed #6", out.stdout + out.stderr
    assert [p[1] for p in posts(stub)] == [f"{ISSUES}/6/comments"]


def test_another_build_of_the_same_brief_is_not_a_rival(proj, stub):
    """REQ-057 AC1: an open pull request of build (a) that modifies the file, and a take of
    build (a) by another session, do not refuse a claim of build (b) of the same brief."""
    listing(stub, [issue(5, brief(FILE) + THREE)])
    stub.serve(PULLS, [{**pr(20, 5), "title": "feat: x (brief #5 build (a))"}])
    changed(stub, 20, ("modified", FILE))
    taken_by_other(stub, 5, "a")
    out = claim(proj, stub, 5, "b")
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.strip() == "claimed #5 build (b)"
    assert len(posts(stub)) == 1


def test_claim_still_takes_a_brief_that_overlaps_nothing(proj, stub):
    """REQ-057 AC7: with no running work the claim posts its one take, as today."""
    listing(stub, [issue(5, brief("a/x.py")), issue(6, brief(FILE))])
    stub.serve(PULLS, [])
    taken_by_other(stub, 5)
    free(stub, 6)
    out = claim(proj, stub)
    assert out.returncode == 0 and out.stdout.strip() == "claimed #6", out.stdout + out.stderr
    assert posts(stub)[0][2][1].startswith(f"body=taken: s-me {DAY}")


def test_claim_posts_nothing_when_the_open_briefs_cannot_be_read(proj, stub):
    """REQ-057 AC1: a read that fails never passes as no overlap."""
    stub.serve(ISSUES, "FAIL")
    stub.serve(PULLS, [])
    free(stub, 6)
    out = claim(proj, stub)
    assert out.returncode != 0 and posts(stub) == []


# --- rule 3: the shared indexes (REQ-057 AC2) ----------------------------------------------------

INDEXES = (
    "kit/manifest.json",
    "agk.toml",
    "config/rule-budget.txt",
    "docs/requirements.md",
    "docs/build-state.md",
)


@pytest.mark.parametrize("index", INDEXES)
def test_two_briefs_that_share_only_a_shared_index_both_start(proj, stub, index):
    """REQ-057 AC2: each default shared index never makes an overlap, in `plan`, `next` and
    `claim`."""
    listing(stub, [issue(5, brief(f"{index}, a/x.py")), issue(6, brief(f"{index}, b/y.py"))])
    stub.serve(PULLS, [])
    free(stub, 5, 6)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [5, 6] and got["waits"] == []
    taken_by_other(stub, 5)
    shown = look(proj, stub)
    assert "brief #6" in lines(shown), shown.stdout + shown.stderr
    out = claim(proj, stub)
    assert out.returncode == 0 and out.stdout.strip() == "claimed #6", out.stdout + out.stderr


def test_an_open_pull_request_that_changes_a_shared_index_does_not_refuse(proj, stub):
    """REQ-057 AC2: `docs/requirements.md` modified by an open pull request refuses nothing."""
    listing(stub, [issue(6, brief("docs/requirements.md, b/y.py"))])
    stub.serve(PULLS, [pr(20, 1)])
    changed(stub, 20, ("modified", "docs/requirements.md"), ("modified", "agk.toml"))
    free(stub, 6)
    out = claim(proj, stub)
    assert out.returncode == 0 and out.stdout.strip() == "claimed #6", out.stdout + out.stderr


def test_a_set_list_replaces_the_default(proj, stub):
    """REQ-057 AC2: with `shared_indexes` set, `agk.toml` overlaps again and the set path does
    not."""
    flow(proj, 'shared_indexes = ["docs/index.md"]')
    listing(
        stub,
        [
            issue(5, brief("agk.toml, docs/index.md")),
            issue(6, brief("agk.toml")),
            issue(7, brief("docs/index.md")),
        ],
    )
    stub.serve(PULLS, [])
    free(stub, 5, 6, 7)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [5, 7]
    assert got["waits"] == [{"brief": 6, "waits_for": 5, "why": "both touch agk.toml"}]
    taken_by_other(stub, 5)
    out = claim(proj, stub)
    assert out.returncode == 1 and out.stdout.strip() == "skip #6: waits for #5 (both touch agk.toml)"
    assert claim(proj, stub, 7).returncode == 0


def test_an_empty_list_exempts_no_index(proj, stub):
    """REQ-057 AC2: a set list replaces the default, so an empty one exempts nothing."""
    flow(proj, "shared_indexes = []")
    listing(stub, [issue(5, brief("docs/requirements.md")), issue(6, brief("docs/requirements.md"))])
    stub.serve(PULLS, [])
    free(stub, 5, 6)
    assert [w["brief"] for w in data(proj, stub)["waits"]] == [6]


@pytest.mark.parametrize(
    "value",
    [
        '"docs/zq-index.md"',
        '[""]',
        '["   "]',
        '["docs/zq-*.md"]',
        '["docs/zq-index?.md"]',
        '["docs/zq-dir/"]',
        "[7]",
        '["docs/zq-index.md", 7]',
    ],
)
def test_a_bad_value_is_refused_naming_the_setting_and_never_the_value(proj, stub, value):
    """REQ-057 AC2: a string, an empty entry, a wildcard path, a folder or a non-string is
    refused by `plan`, `next` and `claim`, naming `flow.shared_indexes` and not the value; `claim`
    posts nothing."""
    flow(proj, f"shared_indexes = {value}")
    listing(stub, [issue(6, brief(FILE))])
    stub.serve(PULLS, [])
    free(stub, 6)
    for out in (plan(proj, stub), look(proj, stub), claim(proj, stub)):
        text = out.stdout + out.stderr
        assert out.returncode != 0, text
        assert "setting: flow.shared_indexes" in text
        assert "zq-" not in text and "[7]" not in text
    assert posts(stub) == []


def test_the_default_list_is_the_five_indexes_of_rule_3():
    """REQ-057 AC7: a project that sets no key gets the default."""
    import session_plan

    assert tuple(session_plan.SHARED_INDEXES) == INDEXES
