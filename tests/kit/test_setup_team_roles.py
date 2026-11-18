"""/agk:setup build (h): each machine gets exactly the roles the repository allows, a restart of
stopped roles, and a team-wide read-only status (brief #1467, SPEC-0065 rules 14 and 15,
ADR-0625; REQ-072 AC7).

A fake machine read (`--machine FILE`), saved GitHub answers (`--github FILE`: the lease, the live
steward, the running builders and the signed-in login) and a stub runner that records every
command; no network, no model. Invented names of example.com only.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location("agk_setup_h", SCRIPTS / "setup.py")
setup = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(setup)

SKILL = ROOT / "skills" / "setup" / "SKILL.md"
TOOLS = {"python": "3.12.1", "git": "2.43.0", "gh": "2.50.0", "claude": "2.1.0", "node": "20.11.0"}
REVIEWERS = "verdict_authors: [author-example-1]\nspec_approvers: [approver-example-1]\n"
TEAM = (
    'execution = "local"\nreview_mode = "team"\n[flow]\nmax_builders = 4\n'
    '[team]\nmembers = ["member-example-1"]\n'
)
HELD = "held by cb-example-9 until 2026-11-18T05:00Z"
ALL = ["steward", "conductor", "builders"]


def machine() -> dict:
    return {
        "os": "Linux", "os_version": "6.1", "wsl": "absent", "memory_total_gb": 32,
        "memory_available_gb": 28, "cores": 16, "disk_free_gb": 100, "admin": False,
        "tools": dict(TOOLS, podman=None, docker=None), "winget": "absent",
        "proxy": "none", "remote": "example-org/example-project",
    }  # fmt: skip


def project(tmp_path: Path, toml: str = TEAM) -> Path:
    (tmp_path / "agk.toml").write_text(toml, encoding="utf-8")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "reviewers.yaml").write_text(REVIEWERS, encoding="utf-8")
    return tmp_path


def github(login, lease="free", steward=None, running=0, **over):
    found = {"lease": lease, "running": running, "steward": steward, "login": login,
             "sessions": [], "waiting": 0}  # fmt: skip
    return found | over


STARTED = "watchdog: lease free\nwatchdog: started conductor-local\n"


def run(root, capsys, monkeypatch, gh, form="plan", extra=(), code_of=0, said=STARTED):
    calls: list[list[str]] = []

    def fake(args, cwd):
        calls.append(list(args))
        return code_of, said

    monkeypatch.setattr(setup, "run_cmd", lambda args, cwd: calls.append(list(args)) or 0)
    monkeypatch.setattr(setup, "run_out", fake)
    m, g = root.parent / "machine.json", root.parent / "github.json"
    m.write_text(json.dumps(machine()), encoding="utf-8")
    g.write_text(json.dumps(gh), encoding="utf-8")
    args = [form, "--machine", str(m), "--github", str(g), "--root", str(root), *extra]
    code = setup.main(args)
    return code, capsys.readouterr().out, calls


def roles_of(root, capsys, monkeypatch, gh, extra=()):
    code, out, _ = run(root, capsys, monkeypatch, gh, extra=["--json", *extra])
    assert code == 0, out
    return json.loads(out)


@pytest.mark.parametrize(
    ("case", "toml", "gh", "want"),
    [
        ("solo", TEAM.replace('"team"', '"solo"'), github("member-example-1"), ALL),
        ("first reviewer machine", TEAM, github("author-example-1"), ALL),
        ("non-reviewer, no conductor", TEAM, github("member-example-1"), ["builders"]),
        ("member while a conductor lives", TEAM, github("member-example-1", lease=HELD),
         ["builders"]),
        ("reviewer while a conductor lives", TEAM, github("author-example-1", lease=HELD),
         ["steward", "builders"]),
        ("author whose steward is live", TEAM, github("author-example-1", steward="cb-example-2"),
         ["conductor", "builders"]),
        ("spec approver, no conductor", TEAM, github("approver-example-1"),
         ["steward", "builders"]),
        ("unknown login", TEAM, github(None), ["builders"]),
    ],
)  # fmt: skip
def test_ac7_each_role_case_gets_exactly_the_roles_of_rule_14(
    tmp_path, capsys, monkeypatch, case, toml, gh, want
):
    """REQ-072 AC7: rule 14: the four role cases of rule 19 and their neighbours."""
    table = roles_of(project(tmp_path, toml), capsys, monkeypatch, gh)
    assert table["roles"] == want, case
    assert table["roles_why"]


def test_ac7_a_non_reviewer_hears_the_conductor_waits_and_no_login_is_printed(
    tmp_path, capsys, monkeypatch
):
    """REQ-072 AC7: rule 14: builders only, the waiting line, the login compared, never printed."""
    root = project(tmp_path)
    code, out, _ = run(root, capsys, monkeypatch, github("member-example-1"))
    assert code == 0
    assert setup.WAITS in out
    table = roles_of(root, capsys, monkeypatch, github("member-example-1"))
    assert "member-example-1" not in out + json.dumps(table)


def test_ac7_a_login_outside_verdict_authors_never_gets_the_conductor(
    tmp_path, capsys, monkeypatch
):
    """REQ-072 AC7: rule 14: a listed spec approver that is not a verdict author: no conductor."""
    root = project(tmp_path)
    table = roles_of(root, capsys, monkeypatch, github("approver-example-1"))
    assert "conductor" not in table["roles"]
    for lease in (HELD, "off (setting: plan_issue in the flow table of agk.toml)", None):
        table = roles_of(root, capsys, monkeypatch, github("author-example-1", lease=lease))
        assert "conductor" not in table["roles"]  # never a second conductor, never unread


def test_ac7_the_team_builders_stay_within_max_builders(tmp_path, capsys, monkeypatch):
    """REQ-072 AC7: rule 14: this machine's builders are capped by max_builders less the live."""
    table = roles_of(project(tmp_path), capsys, monkeypatch, github("member-example-1", running=3))
    assert table["builders"]["figure"] == 1 and table["builders"]["limit"] == "team"
    assert "max_builders 4" in table["roles_why"] and "3 live" in table["roles_why"]


def test_ac7_a_person_may_choose_fewer_roles_never_more(tmp_path, capsys, monkeypatch):
    """REQ-072 AC7: rule 14: `--roles` lowers the set; a role the repository refuses is refused."""
    root = project(tmp_path)
    table = roles_of(root, capsys, monkeypatch, github("author-example-1"), ["--roles", "builders"])
    assert table["roles"] == ["builders"]
    code, out, _ = run(root, capsys, monkeypatch, github("member-example-1"),
                       extra=["--roles", "steward,builders"])  # fmt: skip
    assert code == 1 and "refused" in out and "config/reviewers.yaml" in out
    assert "member-example-1" not in out


def test_ac7_personal_and_hosted_run_no_role(tmp_path, capsys, monkeypatch):
    """REQ-072 AC7: rule 16: for me only and on GitHub's machines this machine runs no role."""
    root = project(tmp_path)
    personal = roles_of(root, capsys, monkeypatch, github("author-example-1"),
                        ["--answer", "where=personal"])  # fmt: skip
    hosted = roles_of(root, capsys, monkeypatch, github("author-example-1"),
                      ["--answer", "where=hosted"])  # fmt: skip
    assert personal["roles"] == [] and hosted["roles"] == []


def test_ac7_a_restart_of_a_builders_only_machine_starts_builders_only(
    tmp_path, capsys, monkeypatch
):
    """REQ-072 AC7: rule 15: no conductor start, no steward line; the builders through launch."""
    root = project(tmp_path)
    code, out, calls = run(root, capsys, monkeypatch, github("member-example-1", lease=HELD),
                           form="restart", extra=["--yes"])  # fmt: skip
    assert code == 0, out
    assert calls == []  # the watchdog never runs on a builders-only machine
    assert "/agk:launch" in out and "claude --agent steward" not in out
    assert "conductor" not in [line.split()[0] for line in out.splitlines() if line.strip()]


def test_ac7_a_restart_of_a_first_reviewer_machine_restarts_every_role(
    tmp_path, capsys, monkeypatch
):
    """REQ-072 AC7: rule 15: the conductor through the watchdog's start, the steward's command."""
    root = project(tmp_path)
    code, out, calls = run(root, capsys, monkeypatch, github("author-example-1"),
                           form="restart", extra=["--yes", "--json"])  # fmt: skip
    table = json.loads(out)
    assert code == 0 and [c[-2:] for c in calls] == [["watchdog", "--conductor-only"]]
    rows = {r["step"]: r for r in table["steps"]}
    assert rows["conductor"] == {"step": "conductor", "result": "done",
                                 "note": "watchdog: started conductor-local"}  # fmt: skip
    assert "claude --agent steward" in rows["steward"]["note"]
    assert "/agk:launch" in rows["builders"]["note"]


def test_ac7_restart_without_the_yes_starts_nothing(tmp_path, capsys, monkeypatch):
    """REQ-072 AC7: rule 15: before the person's yes nothing is started."""
    root = project(tmp_path)
    code, out, calls = run(root, capsys, monkeypatch, github("author-example-1"), form="restart")
    assert code == 1 and calls == [] and "--yes" in out


def test_ac7_status_shows_the_team_and_posts_nothing(tmp_path, capsys, monkeypatch):
    """REQ-072 AC7: rule 15: the lease holder, the steward, each builder with its brief, the
    members and what waits on the owner; read-only, no file written, no command but the proofs."""
    root = project(tmp_path)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    sessions = [{"session": "cb-example-1", "brief": 12}, {"session": "cb-example-2", "brief": 14}]
    gh = github("member-example-1", lease=HELD, steward="cb-example-3", running=2,
                sessions=sessions, waiting=1)  # fmt: skip
    code, out, calls = run(root, capsys, monkeypatch, gh, form="status")
    assert code == 0
    assert HELD in out and "cb-example-3" in out
    assert "cb-example-1 #12" in out and "cb-example-2 #14" in out
    assert "1 member" in out and "1 pull request waits" in out
    assert all("watchdog" not in c and "comments" not in " ".join(c) for c in calls)
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
    code, out, _ = run(root, capsys, monkeypatch, gh, form="status", extra=["--json"])
    team = json.loads(out)["team"]
    assert team["lease"] == HELD and team["steward"] == "cb-example-3"
    assert team["builders"] == sessions and team["waiting"] == 1 and team["members"] == 1


def test_ac7_the_skill_restarts_and_shows_the_team():
    """REQ-072 AC7: rule 15: the skill names the restart form and the team status."""
    text = SKILL.read_text(encoding="utf-8")
    assert 'setup.py" restart' in text and "claude --agent steward" in text
    assert "--roles" in text


@pytest.mark.parametrize(
    "said",
    [
        "watchdog: lease held by cb-example-9 until 2026-11-18T05:00Z; nothing started\n",
        "watchdog: lease free\nwatchdog: this login is not a verdict author; conductor not "
        "started, builders only (setting: verdict_authors in config/reviewers.yaml)\n",
        "watchdog: lease free\nwatchdog: conductor cb-example-4 is running on this machine; "
        "nothing started\n",
        "",
    ],
)
def test_ac7_a_restart_that_starts_no_conductor_is_never_done(tmp_path, capsys, monkeypatch, said):
    """REQ-072 AC7: rule 15: `done` only on the watchdog's `started` line; else `waiting` with
    the watchdog's own last line."""
    root = project(tmp_path)
    code, out, _ = run(root, capsys, monkeypatch, github("author-example-1"), form="restart",
                       extra=["--yes", "--json", "--roles", "conductor"], said=said)  # fmt: skip
    row = json.loads(out)["steps"][0]
    assert code == 0 and row["step"] == "conductor" and row["result"] == "waiting"
    assert row["note"] == (said.strip().splitlines() or ["the watchdog printed nothing"])[-1]


def test_ac7_a_team_answer_never_widens_the_roles_of_a_team_repository(
    tmp_path, capsys, monkeypatch
):
    """REQ-072 AC7: rule 14: `--answer team=solo` counts only while `review_mode` is unset."""
    root = project(tmp_path)
    table = roles_of(root, capsys, monkeypatch, github("member-example-1"),
                     ["--answer", "team=solo"])  # fmt: skip
    assert table["roles"] == ["builders"]
    (tmp_path / "unset").mkdir()
    unset = project(tmp_path / "unset", TEAM.replace('review_mode = "team"\n', ""))
    table = roles_of(unset, capsys, monkeypatch, github("member-example-1"),
                     ["--answer", "team=solo"])  # fmt: skip
    assert table["roles"] == ALL


def test_ac7_setup_and_the_conductor_share_one_verdict_author_check(tmp_path, monkeypatch):
    """REQ-072 AC7: rule 14: `login_state` and `conductor_refusal` read `is_verdict_author`."""
    import common

    root = project(tmp_path)
    seen: list[str] = []
    monkeypatch.setattr(common, "is_verdict_author", lambda r, login: seen.append(login) or True)
    monkeypatch.setattr(common, "signed_in_login", lambda r: "member-example-1")
    assert setup.login_state(root, "member-example-1") == "author"
    assert common.conductor_refusal(root) is None
    assert seen == ["member-example-1", "member-example-1"]


def test_ac7_the_conductor_only_watchdog_runs_no_builder_pass(monkeypatch, tmp_path):
    """REQ-072 AC7: rule 15: `watchdog --conductor-only` starts the conductor and never the
    builder pass, so a restart restarts no builder without `/agk:launch`'s yes."""
    import conductor

    ran: list[str] = []
    monkeypatch.setattr(conductor.session, "paused_default", lambda root: False)
    monkeypatch.setattr(conductor.launch, "default_branch", lambda root: "main")
    monkeypatch.setattr(conductor.launch, "launch_settings", lambda root, ref=None: (True, "x"))
    monkeypatch.setattr(conductor, "plan_issue", lambda root: 7)
    monkeypatch.setattr(conductor.session, "repo_name", lambda root: "example-org/example")
    monkeypatch.setattr(conductor, "watchdog_once", lambda *a: ran.append("conductor") or 0)
    monkeypatch.setattr(conductor, "builder_pass", lambda *a: ran.append("builders"))
    assert conductor.main(["watchdog", "--conductor-only"], root=tmp_path) == 0
    assert ran == ["conductor"]
    assert conductor.main(["watchdog"], root=tmp_path) == 0
    assert ran == ["conductor", "conductor", "builders"]
