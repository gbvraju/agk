"""The two starts of SPEC-0059 rule 2 (brief #1322, ADR-0559; REQ-066 AC1).

The conductor's sweep starts the steward through the launch adapter when a `Question:` has waited
one conductor pass with no `Answer:`, `Maintainer answer:` or `Correction:`, its guard allows that
start through `launch.py` only, and a start the runtime refuses is listed as stuck. The steward
starts the conductor only when the plan passes every check. A launch stub stands in for the
runtime; no network, no model, invented data only (example.com).
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_conductor_guard_launch import (  # noqa: F401 - the fixtures `project` and `tmp`
    ADAPTER,
    allowed,
    on,
    project,
    run_hook,
    settings,
    tmp,
)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import conductor  # noqa: E402
import launch  # noqa: E402
import steward_owner  # noqa: E402

NOW = datetime(2026, 11, 15, 13, 0, tzinfo=UTC)
ANSWERERS = {"boss", "owner"}


def at(cid: int, login: str, body: str, minutes: int = 10) -> dict:
    when = (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": when}


ASKED = at(11, "builder1", "Question: Q-7-1 which runtime for the widget export?", 20)


def test_req066_a_question_is_waiting_until_an_answer_names_it():
    """REQ-066 AC1: rule 2, the waiting `Question:` lines and the three answers that end one."""
    assert conductor.waiting_questions([ASKED], ANSWERERS) == [("Q-7-1", 11)]
    for first in (
        "Answer: Q-7-1 the smaller one",
        "Maintainer answer: Q-7-1 yes",
        "Correction: Q-7-1 is withdrawn",
    ):
        assert conductor.waiting_questions([ASKED, at(12, "boss", first, 5)], ANSWERERS) == []
    other = at(12, "boss", "Answer: Q-7-2 another question", 5)
    assert conductor.waiting_questions([ASKED, other], ANSWERERS) == [("Q-7-1", 11)]
    by_builder = at(12, "builder1", "Answer: Q-7-1 my own guess", 5)
    assert conductor.waiting_questions([ASKED, by_builder], ANSWERERS) == [("Q-7-1", 11)]


@pytest.fixture
def marks(tmp_path, monkeypatch):
    monkeypatch.setattr(conductor, "configured_start_adapter", lambda root: None)
    return tmp_path


def test_req066_a_question_waiting_one_pass_starts_the_steward_until_it_takes_it(marks):
    """REQ-066 AC1: rule 2, a question younger than one conductor pass starts nothing; one that
    waited a pass names the steward's start through launch.py, the same line on every sweep of
    the same comments; a steward post, or an answer, after it starts nothing."""
    young = {7: [ASKED]}
    assert conductor.steward_lines(marks, young, ANSWERERS, NOW) == []
    kept = {7: [at(11, "builder1", "Question: Q-7-1 which runtime for the export?", 26)]}
    line = (
        "STEWARD: #7 Q-7-1 waited one pass unanswered; run: python3 scripts/agk/launch.py role "
        "--role steward --session steward-11"
    )
    assert conductor.steward_lines(marks, kept, ANSWERERS, NOW) == [line]
    assert conductor.steward_lines(marks, kept, ANSWERERS, NOW) == [line]  # no hidden state
    kept[7].append(
        at(
            12,
            "boss",
            "Question: Q-7-1 for the maintainers: Friday or later?\n\nWho: AGK steward",
            5,
        )
    )
    assert conductor.steward_lines(marks, kept, ANSWERERS, NOW) == []  # the steward took it
    answered = {8: [at(21, "builder2", "Question: Q-8-1 which date?", 30)]}
    answered[8].append(at(22, "boss", "Answer: Q-8-1 the first of the month", 1))
    assert conductor.steward_lines(marks, answered, ANSWERERS, NOW) == []


def test_req066_the_start_names_the_configured_adapter(marks, monkeypatch):
    """REQ-066 AC1: rule 2, with `auto_start` on the line carries `--adapter <launch_adapter>`."""
    monkeypatch.setattr(conductor, "configured_start_adapter", lambda root: ADAPTER)
    kept = {7: [at(11, "builder1", "Question: Q-7-1 which runtime?", 40)]}
    (line,) = conductor.steward_lines(marks, kept, ANSWERERS, NOW)
    assert line.endswith("--session steward-11 --adapter 'scripts/start-session.sh --cloud'")


def adapter_file(tmp_path: Path, code: int) -> str:
    script = tmp_path / "adapter.py"
    script.write_text(
        "import json, os, sys\n"
        f"open({str(tmp_path / 'seen.json')!r}, 'w').write(json.dumps("
        "{k: v for k, v in os.environ.items() if k.startswith('AGK_')} | "
        "{'prompt': sys.stdin.read()}))\n"
        f"sys.exit({code})\n",
        encoding="utf-8",
    )
    return f"{sys.executable} {script}"


def test_req066_launch_role_starts_the_steward_through_the_adapter(tmp_path, monkeypatch, capsys):
    """REQ-066 AC1: rule 2, one adapter call on the `strongest` tier with the role and no brief."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGK_BRIEF", "99")
    args = ["role", "--role", "steward", "--session", "steward-1"]
    assert launch.main([*args, "--adapter", adapter_file(tmp_path, 0)]) == 0
    seen = json.loads((tmp_path / "seen.json").read_text(encoding="utf-8"))
    assert seen["AGK_ROLE"] == "steward" and seen["AGK_AGENT"] == "steward"
    assert seen["AGK_TIER"] == "strongest" and seen["AGK_KIND"] == "design"
    assert "AGK_BRIEF" not in seen and "claude --agent steward" in seen["prompt"]
    assert capsys.readouterr().out.strip() == "started steward steward-1"


def test_req066_a_refused_start_is_listed_as_stuck_never_silent(tmp_path, monkeypatch, capsys):
    """REQ-066 AC1: rule 2, a start the runtime refuses prints a `stuck:` line and exits 1."""
    monkeypatch.chdir(tmp_path)
    args = ["role", "--role", "steward", "--session", "steward-1"]
    assert launch.main([*args, "--adapter", adapter_file(tmp_path, 3)]) == 1
    assert capsys.readouterr().out.strip() == (
        "stuck: steward steward-1 not started (the adapter failed)"
    )
    assert launch.main(["role", "--role", "architect", "--session", "x"]) == 2


def test_req066_the_conductor_guard_allows_the_steward_start_through_launch_only(project, tmp):  # noqa: F811
    """REQ-066 AC1: rule 2, the guard allows `launch.py role --role steward`, the adapter only
    as configured, and no other role or spelling."""
    base = "python3 scripts/agk/launch.py role --role"
    settings(project, "[flow]\nauto_start = false\n")
    assert allowed(run_hook(f"{base} steward --session steward-1", project, tmp))
    adapted = f"{base} steward --session steward-1 --adapter '{ADAPTER}'"
    assert not allowed(run_hook(adapted, project, tmp))
    on(project)
    assert allowed(run_hook(adapted, project, tmp))
    assert not allowed(
        run_hook(f"{base} steward --session steward-1 --adapter other", project, tmp)
    )
    assert not allowed(run_hook(f"{base} conductor --session c1", project, tmp))
    assert not allowed(run_hook("claude --agent steward", project, tmp))


@pytest.fixture
def plan_root(tmp_path, monkeypatch):
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(tmp_path / "cache.json"))
    (tmp_path / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    (tmp_path / "docs" / "plan").mkdir(parents=True)
    (tmp_path / "docs" / "plan" / "scope-lock.md").write_text("# Scope lock: Widgets\n")
    (tmp_path / "cache.json").write_text(
        json.dumps(
            {
                "issue": 3,
                "comments": [
                    {"id": 1, "body": "Owner question: Q-9-1 M2 Which colour? I recommend blue."},
                ],
            }
        )
    )
    (tmp_path / "plan.json").write_text('{"malformed": [], "start": []}')
    (tmp_path / "trace.txt").write_text("| row |\nok plan: 4 of 4 in-scope source lines\n")
    calls: list = []
    monkeypatch.setattr(steward_owner.launch, "role_main", lambda a: calls.append(a) or 0)
    monkeypatch.setattr(steward_owner.launch, "launch_settings", lambda root: (True, ADAPTER))
    return tmp_path, calls


def ready(root: Path) -> int:
    args = [
        "ready",
        "--plan",
        str(root / "plan.json"),
        "--trace",
        str(root / "trace.txt"),
        "--session",
        "c1",
        "--start",
    ]
    return steward_owner.main(args)


def test_req066_a_ready_plan_leaves_the_conductor_start_to_the_supervisor(
    plan_root, monkeypatch, capsys
):
    """REQ-066 AC1: rule 2, as SPEC-0064 rule 14 moves it (brief #1387, ADR-0585): with an
    adapter a plan that passes every check starts no conductor itself, the supervisor's next pass
    does; without one it prints the conductor's prompt through `launch.py role`."""
    root, calls = plan_root
    monkeypatch.setattr(steward_owner, "repo_root", lambda: root)
    assert ready(root) == 0
    assert calls == [] and "the supervisor starts the conductor" in capsys.readouterr().out
    monkeypatch.setattr(steward_owner.launch, "launch_settings", lambda root: (False, None))
    assert ready(root) == 0
    assert calls == [["role", "--role", "conductor", "--session", "c1"]]


@pytest.mark.parametrize("broken", ["trace", "malformed", "scope", "question", "memory"])
def test_req066_a_plan_that_fails_any_check_starts_no_conductor(
    plan_root, monkeypatch, capsys, broken
):
    """REQ-066 AC1: rule 2, each failed check prints `not ready:` and starts no conductor."""
    root, calls = plan_root
    monkeypatch.setattr(steward_owner, "repo_root", lambda: root)
    if broken == "trace":
        (root / "trace.txt").write_text("rule 10: a location\nplan: 3 of 4 in-scope source lines\n")
    elif broken == "malformed":
        (root / "plan.json").write_text('{"malformed": [{"brief": 5, "why": "x", "filer": ""}]}')
    elif broken == "scope":
        (root / "docs" / "plan" / "scope-lock.md").unlink()
    elif broken == "question":
        (root / "cache.json").write_text(
            json.dumps(
                {
                    "issue": 3,
                    "comments": [
                        {
                            "id": 2,
                            "body": "Owner question: Q-9-2 Ship M1 now or wait? I recommend wait.",
                        },
                    ],
                }
            )
        )
    else:
        (root / "cache.json").unlink()
    assert ready(root) == 1
    out = capsys.readouterr().out
    assert out.count("not ready:") == 1 and "conductor: not started" in out
    assert calls == []


def test_req066_the_agent_files_name_the_two_starts():
    """REQ-066 AC1: rule 2 and rule 15, the conductor names its one start of the steward and
    leaves the answers from the rules to a running steward; the steward names its commands."""
    conductor_text = (ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    steward_text = (ROOT / ".claude" / "agents" / "steward.md").read_text(encoding="utf-8")
    # SPEC-0064 rule 14 (brief #1387, ADR-0585): the conductor's start of the steward is the
    # supervisor's.
    assert "the supervisor starts the steward job" in conductor_text and "stuck:" in conductor_text
    assert "where a steward runs" in conductor_text.lower()
    for command in (
        "steward_owner.py ask",
        "steward_owner.py relay",
        "steward_owner.py park",
        "steward_owner.py ready",
    ):
        assert command in steward_text
