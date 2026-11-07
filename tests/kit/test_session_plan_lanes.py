"""session.py plan: each ready brief's lane, the phase order and the heavy steps of the playbook.

SPEC-0038 rule 8, build (g); REQ-045 AC3 and AC4; brief #665, ADR-0318. With a declared work type
(`[delivery] work_type` of `agk.toml`, build (b)) the plan names, for each ready brief, the lane
whose `kinds` hold the brief's `Kind:` line, or `lane: none` for a brief without one (`Q-S0038-8`)
or whose kind is in no lane, never an error; within the same priority the earlier phase starts
first and parallel builders are offered briefs from different lanes first; the playbook's
`heavy_steps` are printed once, as the steps a builder runs under `lock.py run --name heavy`;
waves, capacity, the merge queue and the safe merge set do not change, so two overlapping briefs in
different lanes still wait (SPEC-0034 rule 15). Without a declaration the plan prints exactly what
it prints today. Fixture repository in `tmp_path` (two lanes, three briefs, one without a kind), a
`gh` stub with saved JSON copies, invented data, no network."""

from __future__ import annotations

import json

import pytest
from test_session import ISSUES, REPO, Stub, issue, listing, posts
from test_session_flow import brief
from test_session_plan import data, free, plan

PLAYBOOK = """format = 1
work_type = "web-app"
title = "Contract first, then mocks, then both sides in parallel, then joins"
heavy_steps = ["e2e smoke run"]
evidence = ["the contract test output"]

[[phases]]
name = "contract"
order = 1
after = []

[[phases]]
name = "mocks"
order = 2
after = ["contract"]

[[phases]]
name = "front-end"
order = 3
after = ["mocks"]

[[phases]]
name = "back-end"
order = 3
after = ["mocks"]

[[phases]]
name = "joins"
order = 4
after = ["front-end", "back-end"]

[split]
brief_order = ["contract", "mock", "front-end", "back-end", "join"]
depends_on = [
  ["mock", "contract"],
  ["front-end", "mock"],
  ["back-end", "mock"],
  ["join", "front-end"],
  ["join", "back-end"],
]

[[lanes]]
name = "front-end"
kinds = ["front-end"]

[[lanes]]
name = "back-end"
kinds = ["back-end"]

[testing]
profile = "balanced"
always_full = ["contracts/**"]
map = [{ code = "frontend/**", tests = "tests/frontend/**" }]

[[gates]]
id = "contract-tests"
kind = "check"
text = "Contract tests: the testing map names a test glob for every contract path."
step = "contract-tests"
owner_only = false

[milestones]
shape = "per-batch"
batch_by = "demo value"

[[claims]]
text = "Both sides are built in parallel, so a feature is expected to finish sooner."
basis = "expected"
"""
DECLARED = '[delivery]\nwork_type = "web-app"\n'
RATE = "Your merge rate is unknown (no pull request merged in the last 14 days): the merge queue limit does not apply."
TODAY_KEYS = {
    "start",
    "running",
    "waits",
    "skipped",
    "stale_claims",
    "capacity",
    "merge",
    "merge_set",
    "behind",
    "behind_unknown",
    "conflicts",
    "default_branch",
    "stale_commits",
}


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    repo.write("config/protected-paths.txt", "config/\nscripts/agk/\n")
    repo.write("config/playbooks/web-app.toml", PLAYBOOK)
    return repo


def declare(proj, extra: str = "") -> None:
    """The fixture declaration, with any `[flow]` lines of the test."""
    proj.write("agk.toml", (f"[flow]\n{extra}\n" if extra else "") + DECLARED)


def kinded(touches: str, kind: str | None, priority: int | None = None) -> str:
    """A brief body with a `Kind:` line, or without one."""
    return brief(touches, priority=priority) + (f"Kind: {kind}\n" if kind else "")


def three(stub: Stub) -> None:
    """The fixture: a front-end brief, a back-end brief and one without a kind."""
    listing(
        stub,
        [
            issue(5, kinded("frontend/a.js", "front-end")),
            issue(6, kinded("backend/b.py", "back-end")),
            issue(7, kinded("docs/c.md", None)),
        ],
    )
    free(stub, 5, 6, 7)


def lines_of(out) -> list[str]:
    assert out.returncode == 0, out.stdout + out.stderr
    return out.stdout.splitlines()


# --- rule 5 and rule 8: without a declaration the plan prints exactly what it prints today --------


def test_without_a_declaration_the_plan_prints_exactly_what_it_prints_today(proj, stub):
    """Answer 2: the briefs carry `Kind:` lines and the playbook is present, yet nothing is read."""
    three(stub)
    assert lines_of(plan(proj, stub)) == [
        "Start 3: builder-a takes #5, builder-b takes #6, builder-c takes #7.",
        RATE,
    ]
    got = data(proj, stub)
    assert set(got) == TODAY_KEYS
    assert [s["brief"] for s in got["start"]] == [5, 6, 7]


def test_a_commented_delivery_table_is_no_declaration(proj, stub):
    """The table the kit's template carries, commented out, reads a playbook no more than none."""
    proj.write("agk.toml", '# [delivery]\n# work_type = "web-app"\n')
    three(stub)
    assert lines_of(plan(proj, stub)) == [
        "Start 3: builder-a takes #5, builder-b takes #6, builder-c takes #7.",
        RATE,
    ]
    assert "playbook" not in data(proj, stub)


def test_a_refused_declaration_plans_as_today_and_reads_no_playbook(proj, stub):
    """A `work_type` outside the list is refused by `doctor.py` and `check_playbooks.py` (rule 5);
    the plan reads no playbook for it and prints the setting's value nowhere."""
    proj.write("agk.toml", '[delivery]\nwork_type = "zz-unknown-type"\n')
    three(stub)
    out = plan(proj, stub)
    assert lines_of(out)[0] == "Start 3: builder-a takes #5, builder-b takes #6, builder-c takes #7."
    assert "zz-unknown-type" not in out.stdout and "lane" not in out.stdout
    assert "playbook" not in data(proj, stub)


# --- rule 8: each ready brief is named with its lane ----------------------------------------------


def test_each_ready_brief_is_named_with_its_lane_or_lane_none(proj, stub):
    """Answer 1: two lanes, three briefs, one without a kind (`Q-S0038-8`)."""
    declare(proj)
    three(stub)
    lines = lines_of(plan(proj, stub))
    assert lines[0] == "Start 3: builder-a takes #5, builder-b takes #6, builder-c takes #7."
    assert "Lanes (web-app): #5 lane: front-end; #6 lane: back-end; #7 lane: none." in lines
    got = data(proj, stub)
    assert got["playbook"]["work_type"] == "web-app"
    assert got["playbook"]["lanes"] == [
        {"brief": 5, "kind": "front-end", "lane": "front-end"},
        {"brief": 6, "kind": "back-end", "lane": "back-end"},
        {"brief": 7, "kind": None, "lane": None},
    ]
    assert set(got) == TODAY_KEYS | {"playbook"}


def test_a_kind_in_no_lane_prints_lane_none_never_an_error(proj, stub):
    """Answer 2: a contract brief (a kind of `brief_order` that no lane holds) and a brief whose
    kind the playbook does not know both read `lane: none`; the plan exits 0."""
    declare(proj)
    listing(
        stub,
        [issue(8, kinded("contracts/a.yaml", "contract")), issue(9, kinded("x/y.md", "zebra"))],
    )
    free(stub, 8, 9)
    lines = lines_of(plan(proj, stub))
    assert "Lanes (web-app): #8 lane: none; #9 lane: none." in lines
    assert not any(line.startswith(("FAIL", "error")) for line in lines)
    got = data(proj, stub)
    assert got["playbook"]["lanes"] == [
        {"brief": 8, "kind": "contract", "lane": None},
        {"brief": 9, "kind": "zebra", "lane": None},
    ]


def test_a_waiting_brief_is_named_with_its_lane_too(proj, stub):
    """The lane labels every ready brief, not only the ones that start."""
    declare(proj, "max_builders = 1")
    three(stub)
    lines = lines_of(plan(proj, stub))
    assert lines[0] == "Start 1: builder-a takes #5."
    assert "Lanes (web-app): #5 lane: front-end; #6 lane: back-end; #7 lane: none." in lines


# --- rule 8: the lane orders the ready briefs; the phase first, then different lanes --------------


def test_within_a_priority_the_earlier_phase_starts_first(proj, stub):
    """A join brief (the last phase) and a contract brief (the first): the contract brief starts
    first although its number is higher; between priorities the priority still decides."""
    declare(proj, "max_builders = 1")
    listing(
        stub,
        [issue(5, kinded("joins/a.md", "join")), issue(6, kinded("contracts/b.yaml", "contract"))],
    )
    free(stub, 5, 6)
    assert lines_of(plan(proj, stub))[0] == "Start 1: builder-a takes #6."
    listing(
        stub,
        [
            issue(5, kinded("joins/a.md", "join", priority=1)),
            issue(6, kinded("contracts/b.yaml", "contract")),
        ],
    )
    assert lines_of(plan(proj, stub))[0] == "Start 1: builder-a takes #5."


def test_parallel_builders_are_offered_briefs_from_different_lanes_first(proj, stub):
    """Two front-end and two back-end briefs, two slots: one of each lane starts, and the plan
    orders the rest the same way."""
    declare(proj, "max_builders = 2")
    listing(
        stub,
        [
            issue(5, kinded("frontend/a.js", "front-end")),
            issue(6, kinded("frontend/b.js", "front-end")),
            issue(7, kinded("backend/c.py", "back-end")),
            issue(8, kinded("backend/d.py", "back-end")),
        ],
    )
    free(stub, 5, 6, 7, 8)
    lines = lines_of(plan(proj, stub))
    assert lines[0] == "Start 2: builder-a takes #5, builder-b takes #7."
    assert (
        "Lanes (web-app): #5 lane: front-end; #7 lane: back-end; #6 lane: front-end; "
        "#8 lane: back-end." in lines
    )


def test_a_brief_without_a_kind_is_planned_after_the_kinded_briefs_of_its_priority(proj, stub):
    """`Q-665-2`: a brief with no kind belongs to no phase, so within its priority it follows the
    briefs that have one, by number among themselves as today."""
    declare(proj, "max_builders = 1")
    listing(
        stub,
        [
            issue(4, kinded("docs/a.md", None)),
            issue(5, kinded("docs/b.md", None)),
            issue(6, kinded("joins/c.md", "join")),
        ],
    )
    free(stub, 4, 5, 6)
    lines = lines_of(plan(proj, stub))
    assert lines[0] == "Start 1: builder-a takes #6."
    assert "Lanes (web-app): #6 lane: none; #4 lane: none; #5 lane: none." in lines


# --- rule 8: a lane never lets two overlapping briefs run together --------------------------------


def test_two_overlapping_briefs_in_different_lanes_still_wait(proj, stub):
    """SPEC-0034 rule 15 decides the waves: the back-end brief waits for the front-end brief
    that touches the same file, and both are still named with their lanes."""
    declare(proj)
    listing(
        stub,
        [
            issue(5, kinded("shared/api.py", "front-end")),
            issue(6, kinded("shared/api.py", "back-end")),
        ],
    )
    free(stub, 5, 6)
    lines = lines_of(plan(proj, stub))
    assert lines[0] == "Start 1: builder-a takes #5."
    assert "#6 waits for #5 (both touch shared/api.py)." in lines
    assert "Lanes (web-app): #5 lane: front-end; #6 lane: back-end." in lines
    got = data(proj, stub)
    assert got["waits"] == [{"brief": 6, "waits_for": 5, "why": "both touch shared/api.py"}]


# --- rule 8: the heavy steps, printed once ----------------------------------------------------------


def test_the_heavy_steps_are_printed_once_as_the_steps_run_under_the_lock(proj, stub):
    declare(proj)
    three(stub)
    lines = lines_of(plan(proj, stub))
    heavy = [line for line in lines if line.startswith("Heavy steps")]
    assert heavy == [
        "Heavy steps (web-app): e2e smoke run; a builder runs each under lock.py run --name heavy."
    ]
    assert data(proj, stub)["playbook"]["heavy_steps"] == ["e2e smoke run"]


def test_a_playbook_without_heavy_steps_says_none(proj, stub):
    declare(proj)
    proj.write("config/playbooks/web-app.toml", PLAYBOOK.replace('["e2e smoke run"]', "[]"))
    three(stub)
    assert "Heavy steps (web-app): none." in lines_of(plan(proj, stub))


def test_the_lock_settings_are_not_changed_by_the_playbook(proj, stub):
    """The plan changes neither `lock_slots` nor any lock setting: `agk.toml` is as written."""
    declare(proj)
    before = (proj.root / "agk.toml").read_text(encoding="utf-8")
    three(stub)
    plan(proj, stub)
    assert (proj.root / "agk.toml").read_text(encoding="utf-8") == before
    assert "lock_slots" not in json.dumps(data(proj, stub)["playbook"])


# --- the plan only reads --------------------------------------------------------------------------


def test_the_plan_with_a_declaration_posts_nothing_and_only_gets(proj, stub):
    declare(proj)
    three(stub)
    plan(proj, stub)
    assert posts(stub) == [] and all(c[0] == "GET" for c in stub.calls())
