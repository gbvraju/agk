"""Only a verdict author's machine starts a conductor (brief #1449, ADR-0607).

REQ-071. Before any conductor start the kit makes (`watchdog`, `watchdog --pass`, `launch.py role
--role conductor`), it reads the signed-in login with one `gh api user`, cached for the run,
compared and never printed, and starts a conductor only when that login is in `verdict_authors`
(the list, else the `maintainers` team handle). Otherwise it prints one line naming the setting
and goes on to the builder checks; an unreadable login is `unknown` and starts no conductor. The
`gh` stub serves saved GitHub answers, the adapter is a recording double: no network, no model.
"""

from __future__ import annotations

import pytest
from test_conductor_watchdog import PLAN, marker, starts, stub, watchdog, world  # noqa: F401
from test_session import comment, iso

NOT_AUTHOR = (
    "watchdog: this login is not a verdict author; conductor not started, builders only "
    "(setting: verdict_authors in config/reviewers.yaml)\n"
)
UNKNOWN = (
    "watchdog: this login is unknown; conductor not started, builders only "
    "(setting: verdict_authors in config/reviewers.yaml)\n"
)


@pytest.fixture
def builders(monkeypatch):
    """Records each builder pass, so a test sees that the builders still run."""
    import conductor

    ran: list[str] = []
    monkeypatch.setattr(conductor, "builder_pass", lambda root, repo, adapter: ran.append(repo))
    return ran


def signed_in(world, login: str | None) -> None:  # noqa: F811
    if login is not None:
        world["stub"].serve("user", {"login": login, "id": 7})


def free_lease(world) -> None:  # noqa: F811
    world["stub"].serve(PLAN, [comment(1, "builder", "Request: b1 new", iso())])


def test_a_member_with_a_free_lease_starts_builders_only(world, capsys, builders):  # noqa: F811
    """REQ-071: brief #1449 answers 1 and 6 (a member login not in verdict_authors)."""
    signed_in(world, "member-example-1")
    free_lease(world)
    code, out, err = watchdog(world, capsys)
    assert code == 0, err
    assert starts(world) == []
    assert NOT_AUTHOR in out and builders == ["acme/widgets"]
    assert "member-example-1" not in out + err  # compared, never printed


def test_a_verdict_author_with_a_free_lease_starts_one(world, capsys, builders):  # noqa: F811
    """REQ-071: brief #1449 answer 6 (a verdict author with a free lease starts)."""
    signed_in(world, "Boss")
    free_lease(world)
    code, out, err = watchdog(world, capsys)
    assert code == 0, err
    assert len(starts(world)) == 1 and "started conductor-local" in out
    assert "verdict author" not in out and builders == ["acme/widgets"]


def test_a_verdict_author_beside_a_held_lease_starts_none(world, capsys, builders):  # noqa: F811
    """REQ-071: brief #1449 answer 6 (another holds the lease: no start, as today)."""
    signed_in(world, "boss")
    world["stub"].serve(PLAN, [marker(4, who="c1")])
    code, out, _ = watchdog(world, capsys)
    assert code == 0 and starts(world) == []
    assert "watchdog: lease held by c1 until " in out


def test_an_unreadable_login_starts_no_conductor(world, capsys, builders):  # noqa: F811
    """REQ-071: brief #1449 answer 3 (no `user` answer: `unknown`, builders kept)."""
    signed_in(world, None)
    free_lease(world)
    code, out, err = watchdog(world, capsys)
    assert code == 0, err
    assert starts(world) == [] and UNKNOWN in out and builders == ["acme/widgets"]


def test_the_scripted_pass_of_a_member_takes_no_lease(world, capsys, builders, monkeypatch):  # noqa: F811
    """REQ-071: brief #1449 answer 1 (`watchdog --pass`: no lease marker, no job)."""
    import conductor

    monkeypatch.setattr(conductor, "watchdog_pass", lambda *a: pytest.fail("a conductor pass ran"))
    signed_in(world, "member-example-1")
    free_lease(world)
    code, out, err = watchdog(world, capsys, "--pass")
    assert code == 0, err
    assert NOT_AUTHOR in out and builders == ["acme/widgets"]
    assert [c for c in world["stub"].calls() if c[0] != "GET"] == []


def test_solo_mode_starts_for_its_one_person(world, capsys, builders):  # noqa: F811
    """REQ-071: brief #1449 answer 2 (solo mode: the one listed person is the verdict author)."""
    repo = world["repo"]
    repo.commit({"agk.toml": 'review_mode = "solo"\n' + world["toml"]})
    repo.git("update-ref", "refs/remotes/origin/main", "HEAD")
    signed_in(world, "boss")
    free_lease(world)
    code, _, err = watchdog(world, capsys)
    assert code == 0, err
    assert len(starts(world)) == 1


@pytest.mark.parametrize(("login", "count"), [("boss", 1), ("member-example-1", 0)])
def test_the_maintainers_team_fallback_counts(world, capsys, builders, login, count):  # noqa: F811
    """REQ-071: brief #1449 answer 6 (no list: the `maintainers` handle of `authors_of`)."""
    repo = world["repo"]
    yaml = 'version: 1\nteams:\n  maintainers: {github_team: "@boss"}\nspec_approvers: [o]\n'
    repo.commit({"config/reviewers.yaml": yaml})
    repo.git("update-ref", "refs/remotes/origin/main", "HEAD")
    signed_in(world, login)
    free_lease(world)
    code, _, err = watchdog(world, capsys)
    assert code == 0, err
    assert len(starts(world)) == count


def test_the_login_is_read_once_per_run(world):  # noqa: F811
    """REQ-071: brief #1449 answer 1 (one `gh api user`, cached for the run)."""
    import launch

    signed_in(world, "boss")
    root = world["repo"].root
    assert launch.conductor_refusal(root) is None
    assert launch.conductor_refusal(root) is None
    reads = [c for c in world["stub"].calls() if c[1] == "user"]
    assert len(reads) == 1


@pytest.mark.parametrize(("login", "code"), [("member-example-1", 1), ("boss", 0)])
def test_launch_role_conductor_obeys_the_rule(world, capsys, monkeypatch, login, code):  # noqa: F811
    """REQ-071: brief #1449 answers 1 and 5 (`launch.py role --role conductor`, used by the
    autopilot and the hosted start)."""
    import launch

    monkeypatch.setattr(launch, "live_conductors", lambda root: [])
    signed_in(world, login)
    args = ["role", "--role", "conductor", "--session", "cb-example-1", "--adapter", "true"]
    assert launch.role_main(args, root=world["repo"].root) == code
    out = capsys.readouterr().out
    if code:
        assert "stuck: conductor cb-example-1 not started (this login is not a verdict author;" in out
        assert login not in out
    else:
        assert "started conductor cb-example-1" in out


def test_a_steward_start_reads_no_login(world, capsys, monkeypatch):  # noqa: F811
    """REQ-071: brief #1449 answer 1 governs conductor starts only."""
    import launch

    args = ["role", "--role", "steward", "--session", "cb-example-1", "--adapter", "true"]
    assert launch.role_main(args, root=world["repo"].root) == 0
    assert [c for c in world["stub"].calls() if c[1] == "user"] == []
