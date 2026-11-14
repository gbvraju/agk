"""/agk:board: one owner command makes the plan's GitHub Project board and adds every brief issue
with its size and expected hours (brief #1190, REQ-050, ADR-0506); brief #1195 (ADR-0507): the board
is copied from the owner's template board and carries Persona, Requirement, Screens and Sign-off.

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
WRITES = ("create", "copy", "link", "field-create", "item-add", "item-edit")

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

if args[:1] == ["api"]:  # the REST read of the open issues, filtered by its label (brief #1196)
    wanted = [a.split("labels=", 1)[1].split("&")[0] for a in args if "labels=" in a]
    out([i for i in state["issues"]
         if not wanted or wanted[0] in [x["name"] for x in i.get("labels", [])]])
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
    if state.get("builtin_type"):  # brief #1240: GitHub's own Type field (issue types)
        projects[number]["fields"].append({"id": "F_issue_type", "name": "Type",
                                           "type": "ProjectV2IssueTypeField"})
    out({"number": int(number), "id": "PVT_" + number, "title": opt("--title")})
number = args[2] if len(args) > 2 and args[2].isdigit() else None
if sub == "copy":
    source = state.get("templates", {}).get(number)
    if source is None:
        sys.stderr.write("could not find project\n")
        sys.exit(1)
    made = str(state.get("next", 5))
    projects[made] = {"id": "PVT_" + made, "title": opt("--title"), "links": [],
                      "fields": json.loads(json.dumps(source["fields"])),
                      "views": list(source["views"]), "items": []}
    out({"number": int(made), "id": "PVT_" + made, "title": opt("--title")})
if sub == "item-edit":
    for p in projects.values():
        for item in p["items"]:
            if item["id"] == opt("--id"):
                value = opt("--single-select-option-id") or opt("--text")
                value = value if value is not None else float(opt("--number"))
                item.setdefault("values", {})[opt("--field-id")] = value
    out({"id": opt("--id")})
p = projects.get(number)
if p is None and sub == "field-list":  # the dry run reads a template board's fields
    p = state.get("templates", {}).get(number)
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
    name = opt("--name")
    if name == "Type" or name == state.get("fail_field"):  # brief #1240: as GitHub answers now
        sys.stderr.write("GraphQL: Name cannot have a reserved value, Name has already been taken"
                         " (createProjectV2Field)\n")
        sys.exit(1)
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
        11: {"F_Size": "opt_S", "F_Expected_hours": 4.0, "F_Sign-off": "opt_Pending"},
        12: {"F_Size": "opt_M", "F_Expected_hours": 8.0, "F_Sign-off": "opt_Pending"},
        13: {"F_Size": "opt_L", "F_Expected_hours": 16.0, "F_Sign-off": "opt_Pending"},
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
    assert item_values(world.load())[14] == {
        "F_Size": "opt_S",
        "F_Expected_hours": 3.0,
        "F_Sign-off": "opt_Pending",
    }
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
    assert item_values(world.load())[16] == {"F_Sign-off": "opt_Pending"}


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


# --- brief #1195 (ADR-0507): the template board and the business fields ---------------------------

TEMPLATE_FIELDS = [
    {"id": "T_title", "name": "Title", "type": "ProjectV2Field"},
    {
        "id": "T_status",
        "name": "Status",
        "type": "ProjectV2SingleSelectField",
        "options": [{"id": "s1", "name": "Todo"}, {"id": "s2", "name": "Done"}],
    },
    {"id": "T_persona", "name": "Persona", "type": "ProjectV2Field"},
    {
        "id": "T_signoff",
        "name": "Sign-off",
        "type": "ProjectV2SingleSelectField",
        "options": [
            {"id": "p1", "name": "Pending"},
            {"id": "p2", "name": "Signed off"},
            {"id": "p3", "name": "Changes asked"},
        ],
    },
]
BUSINESS = ("Persona", "Requirement", "Screens", "Sign-off")
VIEWS_LINE = (
    "make the three views once in GitHub's screen: Sign-off (a board by Status), Questions"
    " (a table filtered to Card kind Question), Roadmap (by Milestone); or copy a template board"
    " with --template OWNER/NUMBER"
)


def business_issue(n: int) -> dict:
    """An invented published brief issue: the visible part, a Persona line, the hidden brief."""
    body = (
        "## What\n\nThe invented sign-in of example.com.\n\n## Acceptance\n\n- [ ] it signs in\n\n"
        "Persona: P1 Shop owner\n\nPart of milestone M1.\n\n<!-- agk\n# Sign in\n\n"
        "Advances: REQ-101, REQ-102\nSize: M\nExpected: 4-8 hours\nMilestone: M1\n"
        "Screens: v2 login/*, home/empty\n-->\n"
    )
    return issue(n) | {"body": body}


def with_template(world: World) -> None:
    world.state["templates"] = {"3": {"fields": TEMPLATE_FIELDS, "views": BUSINESS[3:] + ("x",)}}
    world.state["issues"] = [business_issue(21), issue(22)]
    world.save()


def second(world: World) -> World:
    """Another invented repository beside the first, with its own fake gh state."""
    where = world.root.parent / "second"
    where.mkdir()
    return World(where)


def field_creates(calls: list[list[str]]) -> list[str]:
    return [c[c.index("--name") + 1] for c in calls if c[:2] == ["project", "field-create"]]


def test_1195_a_a_template_is_copied_on_the_first_run_and_never_created(world: World) -> None:
    """REQ-050: brief #1195 answer 5 (a), answer 1."""
    with_template(world)
    dry = world.run("--template", "boss/3")
    assert dry.returncode == 0, dry.stdout + dry.stderr
    assert "would copy project boss/3 as 'proj plan' under example" in dry.stdout
    assert "would create project" not in dry.stdout
    assert writes(world.calls()) == []
    proc = world.run("--yes", "--template", "boss/3")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = world.calls()
    assert not [c for c in calls if c[:2] == ["project", "create"]]
    copy = [c for c in calls if c[:2] == ["project", "copy"]]
    assert len(copy) == 1 and copy[0][2] == "3"
    assert copy[0][copy[0].index("--source-owner") + 1] == "boss"
    assert copy[0][copy[0].index("--target-owner") + 1] == "example"
    assert copy[0][copy[0].index("--title") + 1] == "proj plan"
    state = world.load()
    assert state["projects"]["5"]["links"] == [REPO]
    assert state["projects"]["5"]["views"] == ["Sign-off", "x"]
    assert "copied project boss/3 as 5 'proj plan' under example" in proc.stdout
    assert "add to agk.toml under [plan], and commit: board = 5" in proc.stdout
    assert VIEWS_LINE not in proc.stdout


def test_1195_a_the_template_setting_and_no_template_names_the_three_views(world: World) -> None:
    """REQ-050: brief #1195 answer 1."""
    with_template(world)
    (world.root / "agk.toml").write_text('[plan]\nboard_template = "boss/3"\n', encoding="utf-8")
    assert world.run("--yes").returncode == 0
    assert [c for c in world.calls() if c[:2] == ["project", "copy"]]
    other = second(world)
    proc = other.run("--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert VIEWS_LINE in proc.stdout
    assert proc.stdout.strip().splitlines()[-1] == "ok board: 3 added, 0 already there"


@pytest.mark.parametrize("bad", ['"boss"', '"boss/0"', '"boss/three"', "3", '"a b/3"'])
def test_1195_a_board_template_is_owner_slash_number(tmp_path: Path, bad: str) -> None:
    """REQ-050: brief #1195 answer 1; a refusal names the setting, never the value."""
    (tmp_path / "agk.toml").write_text(f"[plan]\nboard_template = {bad}\n", encoding="utf-8")
    with pytest.raises(CheckError, match=r"setting: \[plan\] board_template") as caught:
        plan_settings(tmp_path)
    assert bad.strip('"') not in str(caught.value).replace("board_template", "")
    (tmp_path / "agk.toml").write_text('[plan]\nboard_template = "boss/3"\n', encoding="utf-8")
    assert plan_settings(tmp_path)["board_template"] == "boss/3"


def test_1195_a_the_template_option_is_owner_slash_number(world: World) -> None:
    """REQ-050: brief #1195 answer 1."""
    proc = world.run("--yes", "--template", "boss")
    assert proc.returncode == 2
    assert "option: --template" in proc.stdout
    assert world.calls() == []


def test_1195_b_the_four_fields_are_added_only_when_missing(world: World) -> None:
    """REQ-050: brief #1195 answer 5 (b), answer 2."""
    with_template(world)
    proc = world.run("--yes", "--template", "boss/3")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert field_creates(world.calls()) == ["Size", "Expected hours", "Requirement", "Screens"]
    fields = {f["name"]: f for f in world.load()["projects"]["5"]["fields"]}
    assert all(name in fields for name in BUSINESS)
    assert [o["name"] for o in fields["Sign-off"]["options"]] == [
        "Pending",
        "Signed off",
        "Changes asked",
    ]
    fresh = second(world)
    assert fresh.run("--yes").returncode == 0
    made = [c for c in fresh.calls() if c[:2] == ["project", "field-create"]]
    kinds = {c[c.index("--name") + 1]: c[c.index("--data-type") + 1] for c in made}
    assert kinds == {
        "Size": "SINGLE_SELECT",
        "Expected hours": "NUMBER",
        "Persona": "TEXT",
        "Requirement": "TEXT",
        "Screens": "TEXT",
        "Sign-off": "SINGLE_SELECT",
    }
    signoff = [c for c in made if "Sign-off" in c][0]
    assert (
        signoff[signoff.index("--single-select-options") + 1] == "Pending,Signed off,Changes asked"
    )
    before = len(fresh.calls())
    assert fresh.run("--yes", "--project", "5").returncode == 0
    assert field_creates(fresh.calls()[before:]) == []


def test_1195_c_persona_requirement_and_screens_come_from_the_issue(world: World) -> None:
    """REQ-050: brief #1195 answer 5 (c), answer 2."""
    with_template(world)
    dry = world.run("--template", "boss/3")
    assert (
        "would add #21 Size M, Expected hours 8, Persona P1 Shop owner, Requirement REQ-101,"
        " REQ-102, Screens v2 login/*, home/empty, Sign-off Pending" in dry.stdout
    )
    proc = world.run("--yes", "--template", "boss/3")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    values = item_values(world.load())
    assert values[21] == {
        "F_Size": "opt_M",
        "F_Expected_hours": 8.0,
        "T_persona": "P1 Shop owner",
        "F_Requirement": "REQ-101, REQ-102",
        "F_Screens": "v2 login/*, home/empty",
        "T_signoff": "p1",
    }
    assert values[22] == {"F_Size": "opt_M", "F_Expected_hours": 8.0, "T_signoff": "p1"}
    out = proc.stdout
    assert "set #21 Persona P1 Shop owner" in out and "set #21 Sign-off Pending" in out
    assert "set #21 Requirement REQ-101, REQ-102" in out
    assert "set #21 Screens v2 login/*, home/empty" in out


def test_1195_d_a_sign_off_a_person_set_is_left_alone(world: World) -> None:
    """REQ-050: brief #1195 answer 5 (d), answer 2."""
    with_template(world)
    assert world.run("--yes", "--template", "boss/3").returncode == 0
    world.load()
    item = world.state["projects"]["5"]["items"][0]
    item["values"]["T_signoff"] = "p2"
    item["values"]["T_persona"] = "P2 Buyer"
    world.save()
    before = len(world.calls())
    proc = world.run("--yes", "--project", "5", "--template", "boss/3")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    new = world.calls()[before:]
    assert not [c for c in new if c[:2] in (["project", "item-edit"], ["project", "copy"])]
    assert world.load()["projects"]["5"]["items"][0]["values"]["T_signoff"] == "p2"
    assert world.state["projects"]["5"]["items"][0]["values"]["T_persona"] == "P2 Buyer"


def test_1195_d_an_old_board_gets_the_new_fields_filled_once(world: World) -> None:
    """REQ-050: brief #1195 answer 2: a #1190 board that lacks the four fields gains them, and its
    items get them filled once, in the run that added them."""
    world.state["issues"] = [business_issue(21)]
    world.state["projects"] = {
        "5": {
            "id": "PVT_5",
            "title": "proj plan",
            "links": [],
            "fields": [],
            "items": [
                {
                    "id": "PVTI_21",
                    "content": {
                        "url": f"https://github.com/{REPO}/issues/21",
                        "number": 21,
                        "repository": REPO,
                    },
                    "values": {"F_Size": "opt_L"},
                }
            ],
        }
    }
    world.save()
    proc = world.run("--yes", "--project", "5")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert item_values(world.load())[21] == {
        "F_Size": "opt_L",
        "F_Persona": "P1 Shop owner",
        "F_Requirement": "REQ-101, REQ-102",
        "F_Screens": "v2 login/*, home/empty",
        "F_Sign-off": "opt_Pending",
    }
    assert proc.stdout.strip().splitlines()[-1] == "ok board: 0 added, 1 already there"
    before = len(world.calls())
    assert world.run("--yes", "--project", "5").returncode == 0
    assert not [c for c in world.calls()[before:] if c[:2] == ["project", "item-edit"]]


# --- brief #1196 (ADR-0508): the business questions on the board ----------------------------------

QUESTION_LABEL = "agk-business-question"


def question_issue(n: int) -> dict:
    """An invented business question issue as `plan_intake.py publish` prints it."""
    body = (
        "## Question\n\nWho signs the list off at example.com?\n\n"
        "Source: `docs/sources/sow.md#Scope`\nBlocks: B1\n\n## Answer\n"
    )
    return issue(n) | {"body": body, "labels": [{"name": QUESTION_LABEL}]}


def test_1196_c_the_board_adds_the_questions_with_type_question(world: World) -> None:
    """REQ-050: brief #1196 answer 2 and answer 5 (c): Type Question, Sign-off left empty; the
    marker field (`Card kind` since brief #1240) is added once a question is there, and the briefs are Work."""
    world.state["issues"] = [issue(11, "S", "2-4 hours"), question_issue(31)]
    world.save()
    dry = world.run()
    assert dry.returncode == 0, dry.stdout + dry.stderr
    assert "would add field Card kind (single select Work, Question)" in dry.stdout
    assert "would add #31 Card kind Question" in dry.stdout
    assert "note: #31" not in dry.stdout
    proc = world.run("--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    fields = {f["name"]: f for f in world.load()["projects"]["5"]["fields"]}
    assert [o["name"] for o in fields["Card kind"]["options"]] == ["Work", "Question"]
    values = item_values(world.state)
    assert values[31] == {"F_Card_kind": "opt_Question"}
    assert values[11]["F_Card_kind"] == "opt_Work" and values[11]["F_Sign-off"] == "opt_Pending"
    assert "set #31 Card kind Question" in proc.stdout and "note: #31" not in proc.stdout
    assert proc.stdout.strip().splitlines()[-1] == "ok board: 2 added, 0 already there"


def test_1196_c_a_later_question_fills_type_once_on_the_cards_there(world: World) -> None:
    """REQ-050: brief #1196 answer 2, an old board gains the marker field; its brief cards are Work once."""
    assert world.run("--yes").returncode == 0
    assert "Card kind" not in field_creates(world.calls())
    world.load()
    world.state["issues"].append(question_issue(31))
    world.save()
    before = len(world.calls())
    proc = world.run("--yes", "--project", "5")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert field_creates(world.calls()[before:]) == ["Card kind"]
    values = item_values(world.load())
    assert {values[n]["F_Card_kind"] for n in (11, 12, 13)} == {"opt_Work"}
    assert values[31] == {"F_Card_kind": "opt_Question"}
    assert proc.stdout.strip().splitlines()[-1] == "ok board: 1 added, 3 already there"
    before = len(world.calls())
    assert world.run("--yes", "--project", "5").returncode == 0
    assert not [c for c in world.calls()[before:] if c[:2] == ["project", "item-edit"]]


def test_1196_c_a_closed_question_is_not_read(world: World) -> None:
    """REQ-050: brief #1196 answer 2, only the open questions are read, with one REST call."""
    world.state["issues"] = [issue(11)]
    world.save()
    assert world.run("--yes").returncode == 0
    reads = [c for c in world.calls() if c[:1] == ["api"]]
    assert [c[-1] for c in reads] == [
        f"repos/{REPO}/issues?state=open&labels=agk-brief&per_page=100",
        f"repos/{REPO}/issues?state=open&labels={QUESTION_LABEL}&per_page=100",
    ]


# --- brief #1240 (ADR-0526): GitHub's built-in Type field; the marker field is Card kind ---------


def user_type_field() -> dict:
    """The marker field of an older board: a user single select `Type` of Work and Question."""
    return {
        "id": "F_Type",
        "name": "Type",
        "type": "ProjectV2SingleSelectField",
        "options": [{"id": "opt_Work", "name": "Work"}, {"id": "opt_Question", "name": "Question"}],
    }


@pytest.mark.parametrize("listed", [True, False])
def test_1240_a_board_with_the_built_in_type_gets_card_kind_and_its_cards(
    world: World, listed: bool
) -> None:
    """REQ-050: brief #1240 answer 1 and 4: GitHub refuses a field named Type, so the marker
    field is `Card kind`; the built-in Type, listed by gh or not, is never created or written."""
    world.state["issues"] = [issue(11, "S", "2-4 hours"), question_issue(31)]
    world.state["builtin_type"] = listed
    world.save()
    dry = world.run()
    assert dry.returncode == 0, dry.stdout + dry.stderr
    assert "would add field Card kind (single select Work, Question)" in dry.stdout
    assert "would add field Type" not in dry.stdout
    proc = world.run("--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Type" not in field_creates(world.calls())
    assert field_creates(world.calls()).count("Card kind") == 1
    edits = [c for c in world.calls() if c[:2] == ["project", "item-edit"]]
    assert not [c for c in edits if c[c.index("--field-id") + 1] == "F_issue_type"]
    values = item_values(world.load())
    assert values[31] == {"F_Card_kind": "opt_Question"}
    assert values[11]["F_Card_kind"] == "opt_Work"
    assert proc.stdout.strip().splitlines()[-1] == "ok board: 2 added, 0 already there"


def test_1240_an_old_board_with_a_user_type_field_keeps_using_it(world: World) -> None:
    """REQ-050: brief #1240 answer 1 and 4: a user `Type` of Work and Question is read and
    written as before, and no `Card kind` is added beside it."""
    assert world.run("--yes").returncode == 0
    world.load()
    world.state["projects"]["5"]["fields"].append(user_type_field())
    world.state["issues"].append(question_issue(31))
    world.save()
    dry = world.run("--project", "5")
    assert dry.returncode == 0, dry.stdout + dry.stderr
    assert "would add field" not in dry.stdout
    assert "would add #31 Type Question" in dry.stdout
    before = len(world.calls())
    proc = world.run("--yes", "--project", "5")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert field_creates(world.calls()[before:]) == []
    assert item_values(world.load())[31] == {"F_Type": "opt_Question"}
    assert "set #31 Type Question" in proc.stdout
    assert "Card kind" not in proc.stdout


def test_1240_a_failed_field_creation_is_printed_with_gh_s_message(world: World) -> None:
    """REQ-050: brief #1240 answer 2 and 4: the field's name and gh's own message, exit 1, and
    no card is added."""
    world.state["issues"] = [issue(11), question_issue(31)]
    world.state["fail_field"] = "Card kind"
    world.save()
    proc = world.run("--yes")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "failed: gh project field-create 5" in proc.stdout
    assert (
        "board: the field Card kind was not added; gh said: GraphQL: Name cannot have a reserved"
        " value, Name has already been taken (createProjectV2Field)"
    ) in proc.stdout
    assert not [c for c in world.calls() if c[:2] == ["project", "item-add"]]


def test_1240_a_rerun_after_the_failure_adds_every_card_once(world: World) -> None:
    """REQ-050: brief #1240 answer 3 and 4: the board left with fields and no cards gets its
    cards on the rerun, with no second copy of any field."""
    world.state["issues"] = [issue(11), issue(12), question_issue(31)]
    world.state["fail_field"] = "Card kind"
    world.save()
    assert world.run("--yes").returncode == 1
    world.load()
    assert world.state["projects"]["5"]["items"] == []
    world.state.pop("fail_field")
    world.save()
    proc = world.run("--yes", "--project", "5")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    names = [f["name"] for f in world.load()["projects"]["5"]["fields"]]
    assert len(names) == len(set(names))
    adds = [c for c in world.calls() if c[:2] == ["project", "item-add"]]
    assert sorted(c[c.index("--url") + 1].rsplit("/", 1)[1] for c in adds) == ["11", "12", "31"]
    assert item_values(world.state)[31] == {"F_Card_kind": "opt_Question"}
    assert proc.stdout.strip().splitlines()[-1] == "ok board: 3 added, 0 already there"
    before = len(world.calls())
    again = world.run("--yes", "--project", "5")
    assert again.returncode == 0
    new = world.calls()[before:]
    assert not [c for c in new if c[:2] in (["project", "item-add"], ["project", "field-create"])]
