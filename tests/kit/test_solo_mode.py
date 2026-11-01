# ruff: noqa: F811 - the fixtures and helpers of test_route are imported by name
"""Solo mode: one confirmation comment counts as the verdict and the approval (brief #277; REQ-039).

`review_mode = "solo"` in `agk.toml` (default `"team"`; Q-277-1: the brief's name `mode` already
holds the install stamp) lets one comment, posted by a session under the one person's account,
count as the verdict, its `Final:` lines and the spec approval of the head it names:

    Confirmed: <full head sha>
    Verdict: cleared|fix list|rejected <the same full sha>
    ... (Final: lines, findings, Approve: SPEC-nnnn lines)
    Shown:
    <three lines: the summary the person was shown>
    confirmed by <login> in a session at <YYYY-MM-DDTHH:MM:SSZ>

In team mode the same comment counts for nothing; a comment posted through an app of `agent_apps`
never counts; a confirmation that names another sha than its verdict, or another login than its
author, counts for nothing. Saved responses and git only; no network.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from test_route import HEAD, OLD, REPO_INFO, SPEC, approved_spec, facts, run_router, said
from test_route import proj as route_proj  # noqa: F401  (the fixtures of test_route)
from test_route import stub as route_stub  # noqa: F401

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import reviewers  # noqa: E402
import route  # noqa: E402

APPS = ["claude"]
SHOWN = ["Shown:", "1. what changes: x", "2. what it risks: y", "3. what stays: z"]
AT = "2026-10-30T02:30:00Z"
EVENT = {"pull_request": {"number": 7}, "repository": REPO_INFO}


@pytest.fixture
def stub(request):
    return request.getfixturevalue("route_stub")


@pytest.fixture
def proj(request):
    return request.getfixturevalue("route_proj")


def confirmation(
    sha: str = HEAD,
    verdict: str = "cleared",
    middle: tuple[str, ...] = (),
    login: str = "boss",
    named: str | None = None,
    shown: list[str] | None = None,
) -> str:
    lines = [f"Confirmed: {sha}", f"Verdict: {verdict} {named or sha}", "", *middle, ""]
    lines += SHOWN if shown is None else shown
    lines.append(f"confirmed by {login} in a session at {AT}")
    return "\n".join(lines)


def solo(**kw) -> dict:
    return facts(solo_person="boss", authors=["boss"], approvers=["boss"], author="boss", **kw)


# --- the setting (answer 1) ---------------------------------------------------------------------


def test_the_setting_is_team_by_default_and_reads_solo(tmp_path):
    """REQ-039: brief #277 answer 1."""
    assert common.review_mode(tmp_path) == "team"
    (tmp_path / "agk.toml").write_text('review_mode = "solo"\n')
    assert common.review_mode(tmp_path) == "solo"
    (tmp_path / "agk.toml").write_text('review_mode = "team"\n')
    assert common.review_mode(tmp_path) == "team"


@pytest.mark.parametrize("value", ['"Solo"', '"one"', '""', "1", "true", '["solo"]'])
def test_another_value_is_refused_naming_the_setting(tmp_path, value):
    """REQ-039: brief #277 answer 1 (a refusal names the setting, never the value)."""
    (tmp_path / "agk.toml").write_text(f"review_mode = {value}\n")
    with pytest.raises(common.CheckError) as err:
        common.review_mode(tmp_path)
    assert "setting: review_mode" in str(err.value)
    assert "one" not in str(err.value).replace("one of", "")


def test_the_install_stamp_mode_is_not_the_setting(tmp_path):
    """REQ-039: brief #277 answer 1 (Q-277-1: `mode` stays the install stamp)."""
    (tmp_path / "agk.toml").write_text('mode = "init"\n')
    assert common.review_mode(tmp_path) == "team"


def reviewers_yaml(authors: str, approvers: str) -> str:
    return (
        "version: 1\nclasses:\n  protected: {paths: [config/], approvers: [core]}\n"
        "teams:\n  core: {github_team: '@acme/core'}\n"
        f"verdict_authors: [{authors}]\nspec_approvers: [{approvers}]\n"
    )


@pytest.mark.parametrize(
    ("authors", "approvers", "ok"),
    [
        ("boss", "boss", True),
        ("Boss", "@boss", True),
        ("boss", "", True),
        ("boss, other", "boss", False),
        ("boss", "other", False),
        ("", "", False),
    ],
)
def test_solo_is_refused_unless_exactly_one_person_is_listed(authors, approvers, ok):
    """REQ-039: brief #277 answer 1 (and the field note: no listed person is refused too)."""
    data = reviewers.parse(reviewers_yaml(authors, approvers))
    problems = reviewers.solo_problems(data, "solo")
    assert (problems == []) is ok, problems
    assert all("setting: review_mode" in p for p in problems)
    assert reviewers.solo_problems(data, "team") == []


def test_the_reviewers_check_refuses_solo_with_two_people(repo):
    """REQ-039: brief #277 answer 1 (`reviewers.py --check`, run by governance)."""
    repo.commit(
        {
            "agk.toml": 'review_mode = "solo"\n',
            "config/protected-paths.txt": "config/\n",
            "config/reviewers.yaml": reviewers_yaml("boss, other", "boss"),
        }
    )
    proc = repo.run("reviewers.py", "--check")
    assert proc.returncode == 1 and "setting: review_mode" in proc.stdout, proc.stdout
    repo.commit({"config/reviewers.yaml": reviewers_yaml("boss", "boss")})
    proc = repo.run("reviewers.py", "--check")
    assert proc.returncode == 0, proc.stdout


# --- reading a confirmation (answer 2) ----------------------------------------------------------


def read(*comments: dict, apps=APPS, person="boss", heads=None, runs=None) -> list[dict]:
    return reviewers.confirmed_comments(list(comments), apps, person, heads, runs)


def test_a_confirmation_adds_its_verdict_and_its_approvals_as_the_person():
    """REQ-039: brief #277 answer 2."""
    body = confirmation(middle=("Approve: SPEC-0032", "Approve: SPEC-0007"))
    found = read(said(5, "boss", body))
    added = found[1:]
    assert found[0]["body"] == body  # the comment itself is kept as it is
    assert [c["body"].splitlines()[0] for c in added] == [
        f"Verdict: cleared {HEAD}",
        f"Approve: {HEAD} SPEC-0032",
        f"Approve: {HEAD} SPEC-0007",
    ]
    assert all(
        c["user"] == {"login": "boss"} and c["created_at"] == found[0]["created_at"] for c in added
    )
    assert all("Shown:" not in c["body"] and "confirmed by" not in c["body"] for c in added)


@pytest.mark.parametrize(
    "body",
    [
        confirmation(sha=HEAD[:7]),  # not the full head ID
        confirmation(named=OLD),  # the verdict names another head
        confirmation(named=HEAD[:7]),
        confirmation(login="someone-else"),  # the last line names another login
        confirmation(shown=SHOWN[:3]),  # two lines shown
        confirmation(shown=[*SHOWN, "4. more"]),
        confirmation(shown=[]),
        confirmation().replace("Verdict:", "Verdict"),
        confirmation().rsplit("\n", 1)[0],  # no last line
        confirmation().replace(AT, "yesterday"),
        confirmation().replace("Confirmed:", "Confirmed "),
        "Confirmed: " + HEAD,
    ],
)
def test_a_confirmation_of_another_shape_adds_nothing(body):
    """REQ-039: brief #277 answers 2 and 7 (one that names an old head counts for nothing)."""
    assert read(said(5, "boss", body)) == [said(5, "boss", body)]


def test_a_confirmation_through_an_agent_app_never_counts():
    """REQ-039: brief #277 answer 3."""
    sent = {**said(5, "boss", confirmation()), "performed_via_github_app": {"slug": "claude"}}
    assert read(sent) == [sent]
    assert len(read(sent, apps=[])) == 2  # a project that lists no app


def test_only_the_one_listed_person_confirms():
    """REQ-039: brief #277 answer 2 (the verdict on f58803a: the single listed person)."""
    body = confirmation(login="other")
    assert read(said(5, "other", body)) == [said(5, "other", body)]
    assert len(read(said(5, "other", body), person="other")) == 2
    assert read(said(5, "boss", confirmation()), person=None) == [said(5, "boss", confirmation())]


def test_a_confirmation_counts_only_for_a_head_the_reader_names():
    """REQ-039: brief #277 answer 7 (the verdict on f58803a: the current head when read)."""
    item = said(5, "boss", confirmation(middle=("Approve: SPEC-0032",)))
    assert len(read(item, heads={HEAD})) == 3
    assert read(item, heads={OLD}) == [item]
    before = {"event": "pull_request", "head_sha": HEAD, "created_at": "2026-10-25T10:00:00Z"}
    later = {"event": "pull_request", "head_sha": OLD, "created_at": "2026-10-25T10:01:00Z"}
    assert len(read(item, runs=[before])) == 3  # the head when it was posted, by GitHub's times
    assert read(item, runs=[before, later]) == [item]
    assert read(item, runs=[]) == [item]  # no run: no head is known, nothing counts


def test_the_one_person_is_read_from_the_project(tmp_path):
    """REQ-039: brief #277 answer 1 (solo mode with one person listed, else nobody)."""
    (tmp_path / "config").mkdir()
    yaml = tmp_path / "config" / "reviewers.yaml"
    yaml.write_text("version: 1\nverdict_authors: [Boss]\nspec_approvers: [boss]\n")
    assert reviewers.solo_person(tmp_path) is None  # team mode by default
    (tmp_path / "agk.toml").write_text('review_mode = "solo"\n')
    assert reviewers.solo_person(tmp_path) == "boss"
    yaml.write_text("version: 1\nverdict_authors: [boss, other]\nspec_approvers: [boss]\n")
    assert reviewers.solo_person(tmp_path) is None


# --- the router (answers 2, 3 and 7) ------------------------------------------------------------


def test_a_solo_confirmation_clears_the_head():
    """REQ-039: brief #277 answers 2 and 7."""
    assert route.decide(solo(comments=[said(5, "boss", confirmation())])) == "agk:ready"


def test_a_solo_confirmation_that_approves_a_spec_needs_no_second_step():
    """REQ-039: brief #277 answers 2 and 7 (the verdict and the approval together)."""
    with_approve = said(5, "boss", confirmation(middle=("Approve: SPEC-0032",)))
    assert route.decide(solo(comments=[with_approve], files=approved_spec())) == "agk:ready"
    without = said(5, "boss", confirmation())
    assert route.decide(solo(comments=[without], files=approved_spec())) == "agk:approve"


def test_a_solo_fix_list_confirmation_is_fix():
    """REQ-039: brief #277 answer 2 (any verdict kind)."""
    fix = said(5, "boss", confirmation(verdict="fix list", middle=("1. do this",)))
    assert route.decide(solo(comments=[fix])) == "agk:fix"


def test_the_same_comment_in_team_mode_counts_for_nothing():
    """REQ-039: brief #277 answers 2 and 7."""
    body = confirmation(middle=("Approve: SPEC-0032",))
    team = solo(comments=[said(5, "boss", body)], files=approved_spec())
    team["solo_person"] = None
    assert route.decide(team) == "agk:review"
    del team["solo_person"]
    assert route.decide(team) == "agk:review"


def test_an_agent_app_confirmation_never_counts_in_solo_mode():
    """REQ-039: brief #277 answers 3 and 7."""
    sent = {**said(5, "boss", confirmation()), "performed_via_github_app": {"slug": "claude"}}
    assert route.decide(solo(comments=[sent], agent_apps=APPS)) == "agk:review"


def test_a_confirmation_naming_an_old_head_counts_for_nothing():
    """REQ-039: brief #277 answer 7 (also the parent of a head that is not its Final commit)."""
    parent = said(5, "boss", confirmation(sha=OLD, middle=("Approve: SPEC-0032",)))
    commit = {"parents": [{"sha": OLD}], "files": [{"filename": "x.py", "status": "modified"}]}
    assert route.decide(solo(comments=[parent], commit=commit)) == "agk:review"
    assert route.decide(solo(comments=[parent], commit=commit, files=approved_spec())) == (
        "agk:review"
    )
    old = said(5, "boss", confirmation(sha=OLD))
    assert route.decide(solo(comments=[old])) == "agk:review"
    mixed = said(5, "boss", confirmation(named=OLD))
    assert route.decide(solo(comments=[mixed])) == "agk:review"


def test_a_confirmation_by_an_unlisted_account_counts_for_nothing():
    """REQ-039: brief #277 answer 2 (only the listed person)."""
    stranger = said(5, "stranger", confirmation(login="stranger"))
    assert route.decide(solo(comments=[stranger])) == "agk:review"


def test_the_router_reads_the_mode_from_the_project(proj, stub, tmp_path):
    """REQ-039: brief #277 answer 2 (end to end: the label from a solo confirmation)."""
    (proj / "agk.toml").write_text('review_mode = "solo"\n', encoding="utf-8")
    (proj / "config" / "reviewers.yaml").write_text(
        "version: 1\nverdict_authors: [boss]\nspec_approvers: [boss]\n", encoding="utf-8"
    )
    stub.pull(7)
    stub.serve("issues/7/comments", [said(5, "boss", confirmation())])
    proc = run_router(proj, stub, tmp_path, "pull_request", EVENT)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    adds = [w for w in stub.writes() if w[0] == "POST" and w[1].endswith("/issues/7/labels")]
    assert adds and "labels[]=agk:ready" in adds[0][2]
    (proj / "agk.toml").write_text('review_mode = "team"\n', encoding="utf-8")
    proc = run_router(proj, stub, tmp_path, "pull_request", EVENT)
    adds = [w for w in stub.writes() if w[0] == "POST" and w[1].endswith("/issues/7/labels")]
    assert "labels[]=agk:review" in adds[-1][2]


# --- the final-clearance check (answers 2 and 5) ------------------------------------------------

ADR = "docs/adr/0001-x.md"
REVIEWERS = "version: 1\nverdict_authors: [boss]\nspec_approvers: [boss]\n"


def adr(status: str) -> str:
    return f"# ADR-0001: x\n\n- Status: {status}\n- Date: 2026-10-22\n"


def spec(status: str) -> str:
    return f"# SPEC-0032: x\n\n- Status: {status}\n"


def reviewed(repo, mode: str) -> str:
    repo.commit(
        {
            "agk.toml": f'review_mode = "{mode}"\n',
            "config/reviewers.yaml": REVIEWERS,
            ADR: adr("Proposed"),
            SPEC: spec("Draft"),
        },
        "reviewed",
    )
    return repo.git("rev-parse", "HEAD").strip()


def comments(tmp_path: Path, body: str, login: str = "boss", app: str | None = None) -> Path:
    item = {"body": body, "created_at": "2026-10-30T02:30:00Z", "user": {"login": login}}
    if app:
        item["performed_via_github_app"] = {"slug": app}
    path = tmp_path / "comments.json"
    path.write_text(json.dumps([item]), encoding="utf-8")
    return path


def test_the_final_commit_after_a_solo_confirmation_is_checked_as_covered(repo, tmp_path):
    """REQ-039: brief #277 answers 2 and 5 (the session's status commit, as today)."""
    sha = reviewed(repo, "solo")
    body = confirmation(sha=sha, verdict="fix list", middle=(f"Final: {ADR} Proposed -> Accepted",))
    repo.commit({ADR: adr("Accepted")}, "final")
    proc = repo.run("check_final_clearance.py", "--comments", str(comments(tmp_path, body)))
    assert proc.returncode == 0, proc.stdout
    repo.commit({ADR: adr("Rejected")}, "not the named line")
    proc = repo.run("check_final_clearance.py", "--comments", str(comments(tmp_path, body)))
    assert proc.returncode == 1 and "rule 7" in proc.stdout, proc.stdout


def test_a_solo_confirmation_carries_the_spec_approval(repo, tmp_path):
    """REQ-039: brief #277 answers 2 and 7 (the Approve: line inside the confirmation)."""
    sha = reviewed(repo, "solo")
    final = f"Final: {SPEC} Draft -> Approved"
    repo.commit({SPEC: spec("Approved")}, "final")
    without = confirmation(sha=sha, verdict="fix list", middle=(final,))
    proc = repo.run("check_final_clearance.py", "--comments", str(comments(tmp_path, without)))
    assert proc.returncode == 1 and "rule 5" in proc.stdout, proc.stdout
    body = confirmation(sha=sha, verdict="fix list", middle=(final, "Approve: SPEC-0032"))
    proc = repo.run("check_final_clearance.py", "--comments", str(comments(tmp_path, body)))
    assert proc.returncode == 0, proc.stdout
    sent = comments(tmp_path, body, app="claude")
    proc = repo.run("check_final_clearance.py", "--comments", str(sent))
    assert proc.returncode == 0 and "ok" in proc.stdout  # nothing is covered: nothing to check
    repo.commit({"config/reviewers.yaml": REVIEWERS.replace("[boss]\n", "[boss, other]\n", 1)})
    proc = repo.run(
        "check_final_clearance.py", "--comments", str(comments(tmp_path, body)), "--head", "HEAD~1"
    )
    assert proc.returncode == 0 and "ok" in proc.stdout  # two people listed: solo reads nothing


def test_in_team_mode_the_confirmation_covers_nothing(repo, tmp_path):
    """REQ-039: brief #277 answer 7 (team mode: a commit that is not the named lines passes,
    because no verdict covers it, while in solo mode the same comment covers it and it fails)."""
    sha = reviewed(repo, "team")
    body = confirmation(sha=sha, verdict="fix list", middle=(f"Final: {ADR} Proposed -> Accepted",))
    repo.commit({ADR: adr("Rejected")}, "not the named line")
    proc = repo.run("check_final_clearance.py", "--comments", str(comments(tmp_path, body)))
    assert proc.returncode == 0, proc.stdout
    repo.commit({"agk.toml": 'review_mode = "solo"\n'}, "solo now")
    proc = repo.run(
        "check_final_clearance.py", "--comments", str(comments(tmp_path, body)), "--head", "HEAD~1"
    )
    assert proc.returncode == 1 and "rule 3" in proc.stdout, proc.stdout


# --- the spec check (answer 2: the approval inside the confirmation) ----------------------------

SPEC_ONE = "docs/specs/0001-thing.md"


def thing(status: str) -> str:
    return (
        f"# SPEC-0001: Thing\n\n- Status: {status}\n- Owner: reviewers\n\n## Rules\n\n1. A rule.\n"
    )


def spec_case(repo, mode: str, authors: str = "boss") -> str:
    """main with a Draft spec; the branch's reviewed commit (its sha) and the Final commit."""
    reviewers_text = f"version: 1\nverdict_authors: [{authors}]\nspec_approvers: [boss]\n"
    repo.commit(
        {"config/reviewers.yaml": reviewers_text, SPEC_ONE: thing("Draft")},
        "base",
    )
    repo.branch()
    repo.commit({"agk.toml": f'agent_apps = ["claude"]\nreview_mode = "{mode}"\n'}, "reviewed")
    sha = repo.git("rev-parse", "HEAD").strip()
    repo.commit({SPEC_ONE: thing("Approved")}, "final")
    return sha


def spec_check(repo, sha: str, login: str = "boss", app: str | None = None, pinned: str = ""):
    final = f"Final: {SPEC_ONE} Draft -> Approved"
    body = confirmation(
        sha=sha, verdict="fix list", middle=(final, "Approve: SPEC-0001"), login=login
    )
    item = {"user": {"login": login}, "body": body, "created_at": "2026-10-30T02:30:00Z"}
    if app:
        item["performed_via_github_app"] = {"slug": app}
    runs = [
        {"event": "pull_request", "head_sha": pinned or sha, "created_at": "2026-10-30T02:00:00Z"}
    ]
    repo.write("comments.json", json.dumps([item]))
    repo.write("runs.json", json.dumps({"total_count": 1, "workflow_runs": runs}))
    args = ["--base", "main", "--comments", "comments.json", "--runs", "runs.json"]
    return repo.run("check_specs.py", *args)


@pytest.mark.parametrize(("mode", "code"), [("solo", 0), ("team", 1)])
def test_the_spec_check_reads_the_approval_of_a_solo_confirmation(repo, mode, code):
    """REQ-039: brief #277 answers 2 and 7 (check_specs, run by governance)."""
    sha = spec_case(repo, mode)
    proc = spec_check(repo, sha)
    assert proc.returncode == code, proc.stdout


def test_the_spec_check_refuses_a_confirmation_by_another_account(repo):
    """REQ-039: brief #277 (the verdict on 1ae4fd4, item 2: another account)."""
    sha = spec_case(repo, "solo")
    assert spec_check(repo, sha, login="stranger").returncode == 1


def test_the_spec_check_refuses_a_confirmation_through_an_agent_app(repo):
    """REQ-039: brief #277 answer 3 (the verdict on 1ae4fd4, item 2: an agent app)."""
    sha = spec_case(repo, "solo")
    assert spec_check(repo, sha, app="claude").returncode == 1


def test_the_spec_check_refuses_solo_mode_with_two_people_listed(repo):
    """REQ-039: brief #277 answer 1 (the verdict on 1ae4fd4, item 2: more than one person)."""
    sha = spec_case(repo, "solo", authors="boss, other")
    assert spec_check(repo, sha).returncode == 1


def test_the_spec_check_refuses_a_confirmation_of_another_head_than_the_runs_show(repo):
    """REQ-039: brief #277 answer 7 (the sha read by the rule of a team short Approve: line)."""
    sha = spec_case(repo, "solo")
    assert spec_check(repo, sha, pinned="f" * 40).returncode == 1


# --- the weekly report (metrics.py) --------------------------------------------------------------


class Saved(dict):
    def get(self, key, endpoint=None):
        return dict.get(self, key)


@pytest.mark.parametrize(("is_solo", "cleared"), [(True, "yes"), (False, "unknown")])
def test_the_weekly_report_counts_a_solo_confirmation_as_the_verdict(is_solo, cleared):
    """REQ-039: brief #277 answer 2 (the report reads what the router reads)."""
    import metrics

    src = Saved({"comments-7": [said(5, "boss", confirmation())]})
    detail = {
        "number": 7,
        "merged_at": "2026-10-30T03:00:00Z",
        "created_at": "2026-10-30T01:00:00Z",
        "head": {"sha": HEAD},
        "user": {"login": "boss"},
        "body": "",
    }
    ctx = metrics.Context(src, Path("."), [], ["boss"], "boss" if is_solo else None, ("claude",))
    assert metrics.build_record(ctx, detail)["merged_head_cleared"] == cleared


# --- only the person posts the confirmation (the verdicts on f58803a and 1ae4fd4) ----------------

KIT = Path(__file__).resolve().parents[2]


def flat(rel: str) -> str:
    return " ".join((KIT / rel).read_text(encoding="utf-8").split())


def test_the_rules_say_a_session_never_posts_a_confirmation():
    """REQ-039: brief #277 (session rule 29, the builder's and the conductor's rules)."""
    rules = flat("config/session-rules.md")
    assert "29. A session never posts a comment whose first line is `Confirmed:`" in rules
    assert "the person posts it from the browser or the GitHub app" in rules
    # CLAUDE.md points at the core-rules page, which holds its former list (ADR-0247).
    operating = flat("CLAUDE.md") + " " + flat("config/core-rules.md")
    assert "Never post a comment whose first line is `Confirmed:`" in operating
    assert "Post a comment whose first line is `Confirmed:`" in flat(".claude/agents/conductor.md")


@pytest.mark.parametrize(
    "rel", ["agk.toml", "kit/templates/agk.toml", "kit/templates/agk.adopt.toml"]
)
def test_the_setting_says_the_person_posts_it(rel):
    """REQ-039: brief #277 (the verdict on 1ae4fd4, item 1)."""
    text = flat(rel)
    assert 'review_mode = "team"' in text
    assert "the person posts from the browser or the GitHub app, never a # session" in text
    assert "posted by a session" not in text
