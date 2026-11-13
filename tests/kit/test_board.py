"""/agk:board: one owner command makes the plan's GitHub Project board and adds every brief issue
with its size and expected hours (brief #1190, REQ-050, ADR-0506).

`gh` is a fake on `PATH` that keeps its state in one JSON file, records every call and answers in
JSON as `gh project ... --format json` does. Invented issues of example.com; no network.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import board  # noqa: E402
from common import CheckError, plan_settings  # noqa: E402

REPO = "example/proj"
NEEDS_MACHINE = (
    "board: needs a machine with your own gh (cloud sessions cannot reach GitHub Projects)"
)
WRITES = ("create", "link", "field-create", "item-add", "item-edit")

FAKE = r"""#!/usr/bin/env python3
import json, os, sys
state_path = os.environ["FAKE_GH_STATE"]
with open(state_path, encoding="utf-8") as f:
    state = json.load(f)
args = sys.argv[1:]
with open(state_path + ".calls", "a", encoding="utf-8") as f:
    f.write(json.dumps(args) + "\n")

def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default

def save():
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f)

def out(data):
    print(json.dumps(data))
    save()
    sys.exit(0)

if args[:1] == ["api"]:
    out(state["issues"])
if args[:1] != ["project"]:
    sys.stderr.write("fake gh: unknown command\n")
    sys.exit(1)
fail = state.get("fail")
if fail == "scope":
    sys.stderr.write("error: your authentication token is missing required scopes [project]\n"
                     "To request it, run:  gh auth refresh -s project\n")
    sys.exit(1)
if fail == "graphql":
    sys.stderr.write("gh: GitHub GraphQL is not available from these sessions;"
                     " use the REST API (HTTP 403)\n")
    sys.exit(1)
sub = args[1]
if fail == sub:
    sys.stderr.write("HTTP 502: bad gateway\n")
    sys.exit(1)
projects = state.setdefault("projects", {})
if sub == "create":
    number = str(state.get("next", 5))
    projects[number] = {"id": "PVT_" + number, "title": opt("--title"), "links": [],
                        "fields": [{"id": "F_title", "name": "Title", "type": "ProjectV2Field"},
                                   {"id": "F_status", "name": "Status",
                                    "type": "ProjectV2SingleSelectField",
                                    "options": [{"id": "o1", "name": "Todo"}]},
                                   {"id": "F_ms", "name": "Milestone", "type": "ProjectV2Field"}],
                        "items": []}
    out({"number": int(number), "id": "PVT_" + number, "title": opt("--title")})
number = args[2] if len(args) > 2 and args[2].isdigit() else None
if sub == "item-edit":
    for p in projects.values():
        for item in p["items"]:
            if item["id"] == opt("--id"):
                value = opt("--single-select-option-id") or float(opt("--number"))
                item.setdefault("values", {})[opt("--field-id")] = value
    out({"id": opt("--id")})
p = projects.get(number)
if p is None:
    sys.stderr.write("could not find project\n")
    sys.exit(1)
if sub == "view":
    out({"number": int(number), "id": p["id"], "title": p["title"]})
if sub == "link":
    p["links"].append(opt("--repo"))
    out({})
if sub == "field-list":
    out({"fields": p["fields"], "totalCount": len(p["fields"])})
if sub == "field-create":
    field = {"id": "F_" + opt("--name").replace(" ", "_"), "name": opt("--name")}
    if opt("--data-type") == "SINGLE_SELECT":
        field["type"] = "ProjectV2SingleSelectField"
        names = opt("--single-select-options").split(",")
        field["options"] = [{"id": "opt_" + n, "name": n} for n in names]
    else:
        field["type"] = "ProjectV2Field"
    p["fields"].append(field)
    out(field)
if sub == "item-list":
    out({"items": p["items"], "totalCount": len(p["items"])})
if sub == "item-add":
    url = opt("--url")
    item = {"id": "PVTI_" + url.rsplit("/", 1)[1], "content": {"url": url, "type": "Issue",
            "number": int(url.rsplit("/", 1)[1]), "repository": "example/proj"}}
    p["items"].append(item)
    out(item)
sys.stderr.write("fake gh: unknown project command\n")
sys.exit(1)
"""


def issue(n: int, size: str = "M", expected: str = "4-8 hours", pull: bool = False) -> dict:
    body = (
        f"Sentence: the invented brief {n} of example.com.\n\nSize: {size}\n"
        f"Expected: {expected}\nMilestone: M1\n"
    )
    data = {
        "number": n,
        "title": f"Brief {n}",
        "body": body,
        "html_url": f"https://github.com/{REPO}/issues/{n}",
        "labels": [{"name": "agk-brief"}],
    }
    if pull:
        data["pull_request"] = {"url": "x"}
    return data


class World:
    def __init__(self, tmp: Path) -> None:
        self.root = tmp / "proj"
        self.root.mkdir()
        (self.root / "agk.toml").write_text("[plan]\niteration_days = 10\n", encoding="utf-8")
        self.bin = tmp / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(
            FAKE.replace("#!/usr/bin/env python3", f"#!{sys.executable}"), encoding="utf-8"
        )
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
        self.state_path = tmp / "gh-state.json"
        self.state: dict = {
            "issues": [issue(11, "S", "2-4 hours"), issue(12), issue(13, "L", "8-16 hours")]
        }
        self.save()

    def save(self) -> None:
        self.state_path.write_text(json.dumps(self.state), encoding="utf-8")

    def load(self) -> dict:
        self.state = json.loads(self.state_path.read_text(encoding="utf-8"))
        return self.state

    def calls(self) -> list[list[str]]:
        log = Path(str(self.state_path) + ".calls")
        return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []

    def run(self, *args: str) -> subprocess.CompletedProcess:
        env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "CI")}
        env.update(
            PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}", FAKE_GH_STATE=str(self.state_path)
        )
        return subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(SCRIPTS / "board.py"), "--repo", REPO, *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World(tmp_path)


def writes(calls: list[list[str]]) -> list[list[str]]:
    return [c for c in calls if c[:1] == ["project"] and c[1] in WRITES]


def item_values(state: dict, number: str = "5") -> dict[int, dict]:
    p = state["projects"][number]
    return {i["content"]["number"]: i.get("values", {}) for i in p["items"]}


def test_a_the_dry_run_prints_every_step_and_writes_nothing(world: World) -> None:
    """REQ-050: brief #1190 answer 7 (a)."""
    proc = world.run()
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = proc.stdout
    assert "would create project 'proj plan' under example" in out
    assert f"would link the project to {REPO}" in out
    assert "would add field Size (single select S, M, L)" in out
    assert "would add field Expected hours (number)" in out
    for n, size, hours in ((11, "S", 4), (12, "M", 8), (13, "L", 16)):
        assert f"would add #{n} Size {size}, Expected hours {hours}" in out
    assert out.strip().splitlines()[-1] == (
        "ok board: 3 to add, 0 already there; dry run, nothing changed (run again with --yes)"
    )
    assert writes(world.calls()) == []


def test_b_yes_on_a_new_repository_creates_links_fields_and_adds_three(world: World) -> None:
    """REQ-050: brief #1190 answer 7 (b)."""
    proc = world.run("--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    state = world.load()
    p = state["projects"]["5"]
    assert p["title"] == "proj plan"
    assert p["links"] == [REPO]
    names = [f["name"] for f in p["fields"]]
    assert "Size" in names and "Expected hours" in names
    assert item_values(state) == {
        11: {"F_Size": "opt_S", "F_Expected_hours": 4.0},
        12: {"F_Size": "opt_M", "F_Expected_hours": 8.0},
        13: {"F_Size": "opt_L", "F_Expected_hours": 16.0},
    }
    out = proc.stdout
    assert "add to agk.toml under [plan], and commit: board = 5" in out
    assert "added #11" in out and "set #11 Size S" in out and "set #11 Expected hours 4" in out
    assert out.strip().splitlines()[-1] == "ok board: 3 added, 0 already there"
    create = [c for c in world.calls() if c[:2] == ["project", "create"]][0]
    assert create[create.index("--owner") + 1] == "example"


def test_c_a_second_run_adds_only_the_new_fourth_issue(world: World) -> None:
    """REQ-050: brief #1190 answer 7 (c)."""
    assert world.run("--yes").returncode == 0
    world.load()
    world.state["issues"].append(issue(14, "S", "1-3 hours"))
    world.state["issues"].append(issue(15, pull=True))
    world.save()
    (world.root / "agk.toml").write_text("[plan]\nboard = 5\n", encoding="utf-8")
    before = len(world.calls())
    proc = world.run("--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    new = world.calls()[before:]
    assert not [c for c in new if c[:2] == ["project", "create"]]
    assert not [c for c in new if c[:2] == ["project", "field-create"]]
    adds = [c for c in new if c[:2] == ["project", "item-add"]]
    assert [c[c.index("--url") + 1] for c in adds] == [f"https://github.com/{REPO}/issues/14"]
    assert item_values(world.load())[14] == {"F_Size": "opt_S", "F_Expected_hours": 3.0}
    assert proc.stdout.strip().splitlines()[-1] == "ok board: 1 added, 3 already there"


def test_c_project_option_names_the_board_and_a_rerun_finishes_missing_fields(world: World) -> None:
    """REQ-050: brief #1190 answer 7 (c)."""
    world.state["fail"] = "field-create"
    world.save()
    first = world.run("--yes")
    assert first.returncode == 1
    assert "failed: gh project field-create 5" in first.stdout
    assert "add to agk.toml under [plan], and commit: board = 5" in first.stdout
    world.load()
    world.state.pop("fail")
    world.save()
    second = world.run("--yes", "--project", "5")
    assert second.returncode == 0, second.stdout + second.stderr
    assert len(world.load()["projects"]) == 1
    assert set(item_values(world.state)) == {11, 12, 13}


def test_d_an_item_already_on_the_board_is_not_edited(world: World) -> None:
    """REQ-050: brief #1190 answer 7 (d)."""
    assert world.run("--yes").returncode == 0
    world.load()
    moved = world.state["projects"]["5"]["items"][1]
    moved["values"] = {"F_status": "o1", "F_Size": "opt_L"}
    world.save()
    before = len(world.calls())
    proc = world.run("--yes", "--project", "5")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert writes(world.calls()[before:]) == [
        c for c in world.calls()[before:] if c[:2] == ["project", "link"]
    ]
    assert world.load()["projects"]["5"]["items"][1]["values"] == {
        "F_status": "o1",
        "F_Size": "opt_L",
    }
    assert proc.stdout.strip().splitlines()[-1] == "ok board: 0 added, 3 already there"


def test_e_a_missing_project_scope_exits_2_with_the_refresh_line(world: World) -> None:
    """REQ-050: brief #1190 answer 7 (e)."""
    world.state["fail"] = "scope"
    world.save()
    proc = world.run("--yes")
    assert proc.returncode == 2
    assert "gh auth refresh -s project" in proc.stdout
    assert not [c for c in world.calls() if c[:2] == ["project", "item-add"]]


def test_f_a_graphql_refusal_prints_the_needs_a_machine_line_and_exits_0(world: World) -> None:
    """REQ-050: brief #1190 answer 7 (f)."""
    world.state["fail"] = "graphql"
    world.save()
    proc = world.run("--yes")
    assert proc.returncode == 0
    assert proc.stdout.strip().splitlines() == [NEEDS_MACHINE]
    world.state["fail"] = "graphql"
    (world.root / "agk.toml").write_text("[plan]\nboard = 5\n", encoding="utf-8")
    dry = world.run()
    assert dry.returncode == 0
    assert dry.stdout.strip().splitlines() == [NEEDS_MACHINE]


def test_other_gh_failure_names_the_command_and_exits_1(world: World) -> None:
    """REQ-050: brief #1190 answer 3 and 4."""
    world.state["fail"] = "item-add"
    world.save()
    proc = world.run("--yes")
    assert proc.returncode == 1
    assert "failed: gh project item-add 5" in proc.stdout


def test_personal_mode_needs_the_github_forge(world: World) -> None:
    """REQ-050: brief #1190 answer 3 and 4."""
    (world.root / "agk.toml").write_text('[personal]\nforge = "files"\n', encoding="utf-8")
    proc = world.run("--yes")
    assert proc.returncode == 0
    assert proc.stdout.strip() == board.PERSONAL
    assert world.calls() == []


def test_title_and_owner_options_and_a_brief_without_estimate(world: World) -> None:
    """REQ-050: brief #1190 answer 3 and 4."""
    world.state["issues"].append({**issue(16), "body": "Sentence: no estimate.\n"})
    world.save()
    proc = world.run("--yes", "--title", "Wave plan", "--owner", "someone")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    create = [c for c in world.calls() if c[:2] == ["project", "create"]][0]
    assert create[create.index("--title") + 1] == "Wave plan"
    assert create[create.index("--owner") + 1] == "someone"
    assert "note: #16 has no Size line" in proc.stdout
    assert "note: #16 has no Expected line" in proc.stdout
    assert item_values(world.load())[16] == {}


def test_plan_board_setting_is_a_positive_whole_number(tmp_path: Path) -> None:
    """REQ-050: brief #1190 answer 3 and 4."""
    (tmp_path / "agk.toml").write_text("[plan]\nboard = 7\n", encoding="utf-8")
    assert plan_settings(tmp_path)["board"] == 7
    for bad in ("0", '"7"', "true"):
        (tmp_path / "agk.toml").write_text(f"[plan]\nboard = {bad}\n", encoding="utf-8")
        with pytest.raises(CheckError, match=r"setting: \[plan\] board"):
            plan_settings(tmp_path)
    (tmp_path / "agk.toml").write_text("[plan]\niteration_days = 5\n", encoding="utf-8")
    assert "board" not in plan_settings(tmp_path)


def test_the_hours_field_takes_the_high_end_of_the_range() -> None:
    """REQ-050: brief #1190 answer 3 and 4."""
    assert board.estimate("Size: M\nExpected: 4-8 hours\n") == ("M", 8.0)
    assert board.estimate("Size: S\nExpected: 1.5-2.5 hours\n") == ("S", 2.5)
    assert board.estimate("nothing\n") == (None, None)
