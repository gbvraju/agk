"""The `[models.routes]` table, `session.py route --brief N` and the `model-routes` doctor row.

REQ-052 AC7, brief #1099 answer 2 (amendment 145's routes as SPEC-0045 rule 3 and build (f) name
them, ADR-0470). `config.model_routes` reads the optional table, a tier to one of `task`, `flag` or
`slots`, and refuses each malformed shape naming `setting: models.routes` or
`setting: models.routes.<tier>`, never the value. `session.py route --brief N` prints one line
`route: <tier> <effort> task <label>` (or `flag`, or `slots ...`), with `via <tier>` when rule 5
moved it to a stronger tier's route, or `route: none` with no table. Fixtures in `tmp_path`, a `gh`
stub, invented values, no network. The tests were written first (answer 5)."""

from __future__ import annotations

import re
from pathlib import Path

import doctor
import pytest
from test_session import ISSUES, session
from test_session import proj as session_proj  # noqa: F401  (the fixtures of test_session)
from test_session import stub as session_stub  # noqa: F401
from test_session_kind import PROTECTED, brief

import config

ODD = "zz-odd-label-9"  # an invented value that a refusal must never echo
STRONG = "builder-strongest"
MID = "builder-mid"


def project(tmp_path: Path, text: str) -> Path:
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    return tmp_path


def refused(root: Path, start: str = "start", slots: int = 0) -> str:
    with pytest.raises(config.ModelSettingError) as caught:
        config.model_routes(root, start, slots)
    return str(caught.value)


# --- the reader (rule 3) ------------------------------------------------------------------------


def test_no_table_routes_nothing(tmp_path):
    """REQ-052 AC7: rule 3, no `[models.routes]` (brief #1099 test (d))."""
    assert config.model_routes(project(tmp_path, 'default_branch = "main"\n')) == {}
    assert config.model_routes(project(tmp_path, "[models]\n")) == {}


def test_task_and_flag_routes_are_read(tmp_path):
    """REQ-052 AC7: rule 3, a task label per tier, and a flag route with a name for the tier."""
    root = project(
        tmp_path,
        '[models.names]\nmid = "example-mid"\n'
        f'[models.routes]\nstrongest = {{ task = "{STRONG}" }}\nmid = {{ flag = true }}\n',
    )
    assert config.model_routes(root) == {"strongest": {"task": STRONG}, "mid": {"flag": True}}


def test_the_routes_key_does_not_refuse_the_models_table(tmp_path):
    """REQ-052 AC1: rule 2, `[models]` accepts `routes` beside the kinds."""
    root = project(tmp_path, f'[models.routes]\nstrongest = {{ task = "{STRONG}" }}\n')
    assert config.model_settings(root)["build"] == {"tier": "strongest", "effort": "medium"}


def test_slot_routes_under_assign(tmp_path):
    """REQ-052 AC7: rule 3, under `assign` every slot is in exactly one route."""
    root = project(
        tmp_path,
        '[models.routes]\nstrongest = { slots = ["s1", "s2"] }\nmid = { slots = ["s3"] }\n',
    )
    got = config.model_routes(root, "assign", 3)
    assert got == {"strongest": {"slots": ["s1", "s2"]}, "mid": {"slots": ["s3"]}}


@pytest.mark.parametrize(
    ("text", "start", "slots", "setting"),
    [
        (f'[models]\nroutes = "{ODD}"\n', "start", 0, "models.routes"),
        (
            f'[models.routes]\nstrongest = {{ task = "{STRONG}" }}\n{ODD} = {{ task = "x" }}\n',
            "start",
            0,
            "models.routes",
        ),  # a tier outside the three
        (
            f'[models.routes]\nmid = {{ task = "{MID}" }}\n',
            "start",
            0,
            "models.routes",
        ),  # no strongest
        (f'[models.routes]\nstrongest = "{ODD}"\n', "start", 0, "models.routes.strongest"),
        (
            f'[models.routes]\nstrongest = {{ {ODD} = "x" }}\n',
            "start",
            0,
            "models.routes.strongest",
        ),
        (
            f'[models.routes]\nstrongest = {{ task = "{STRONG}", flag = true }}\n',
            "start",
            0,
            "models.routes.strongest",
        ),  # two of them
        ("[models.routes]\nstrongest = {}\n", "start", 0, "models.routes.strongest"),  # none
        (
            '[models.routes]\nstrongest = { task = "has space!" }\n',
            "start",
            0,
            "models.routes.strongest",
        ),  # a label of the wrong shape
        ("[models.routes]\nstrongest = { task = 7 }\n", "start", 0, "models.routes.strongest"),
        (
            "[models.routes]\nstrongest = { flag = true }\n",
            "start",
            0,
            "models.routes.strongest",
        ),  # no name and no provider list
        (
            '[models.names]\nstrongest = "example-s"\n'
            "[models.routes]\nstrongest = { flag = false }\n",
            "start",
            0,
            "models.routes.strongest",
        ),
        (
            '[models.routes]\nstrongest = { slots = ["s1"] }\n',
            "start",
            1,
            "models.routes.strongest",
        ),  # slots under start
        (
            f'[models.routes]\nstrongest = {{ task = "{STRONG}" }}\n',
            "assign",
            1,
            "models.routes.strongest",
        ),  # a task under assign
        (
            '[models.routes]\nstrongest = { slots = ["s1", "s9"] }\n',
            "assign",
            2,
            "models.routes.strongest",
        ),  # a slot outside s1 to s<builder_slots>
        ("[models.routes]\nstrongest = { slots = [] }\n", "assign", 1, "models.routes.strongest"),
        (
            '[models.routes]\nstrongest = { slots = ["s1"] }\nmid = { slots = ["s1"] }\n',
            "assign",
            1,
            "models.routes",
        ),  # a slot in two routes
        (
            '[models.routes]\nstrongest = { slots = ["s1"] }\n',
            "assign",
            2,
            "models.routes",
        ),  # s2 in none
    ],
)
def test_each_refusal_names_the_setting_never_the_value(tmp_path, text, start, slots, setting):
    """REQ-052 AC7: rule 3's refusals (brief #1099 test (e))."""
    message = refused(project(tmp_path, text), start, slots)
    assert message.endswith(f"(setting: {setting})"), message
    assert ODD not in message and "has space" not in message and STRONG not in message


def test_a_flag_route_takes_the_name_from_the_provider_list(tmp_path):
    """REQ-052 AC7: rule 3, a flag route is allowed with a provider list for the tier."""
    root = project(
        tmp_path,
        '[models.providers]\nstrongest = ["example-p1"]\n'
        "[models.routes]\nstrongest = { flag = true }\n",
    )
    assert config.model_routes(root) == {"strongest": {"flag": True}}


def test_the_route_of_a_tier_is_its_own_or_the_next_stronger():
    """REQ-052 AC7: rule 5, a tier with no route goes to a stronger one, never a weaker one."""
    routes = {"strongest": {"task": STRONG}, "fast": {"task": "builder-fast"}}
    assert config.route_of(routes, "strongest") == ("strongest", {"task": STRONG})
    assert config.route_of(routes, "mid") == ("strongest", {"task": STRONG})
    assert config.route_of(routes, "fast") == ("fast", {"task": "builder-fast"})
    assert config.route_of({}, "mid") is None


# --- session.py route --brief N (rules 3 and 5) -------------------------------------------------


@pytest.fixture
def stub(request):
    return request.getfixturevalue("session_stub")


@pytest.fixture
def proj(request):
    found = request.getfixturevalue("session_proj")
    found.write("config/protected-paths.txt", PROTECTED)
    return found


def route(proj, stub, body: str, number: int = 41):
    stub.serve(f"{ISSUES}/{number}", {"number": number, "state": "open", "body": body})
    return session(proj, stub, "route", "--brief", str(number))


ROUTES = f'[models.routes]\nstrongest = {{ task = "{STRONG}" }}\nmid = {{ task = "{MID}" }}\n'


@pytest.mark.parametrize(
    ("size", "touches", "want"),
    [
        ("S", "tests/kit/test_example.py", f"route: mid low task {MID}"),  # small
        ("M", "scripts/agk/session.py", f"route: strongest medium task {STRONG}"),  # build
        ("M", "docs/specs/0045-example.md", f"route: strongest high task {STRONG}"),  # design
    ],
)
def test_route_prints_the_task_of_the_kinds_tier(proj, stub, size, touches, want):
    """REQ-052 AC7: rule 3 and 5 (brief #1099 test (c))."""
    proj.write("agk.toml", ROUTES)
    out = route(proj, stub, brief(size, touches))
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout == want + "\n"


def test_a_tier_with_no_route_goes_via_strongest(proj, stub):
    """REQ-052 AC7: rule 5, `mid` with no route goes `via strongest`."""
    proj.write("agk.toml", f'[models.routes]\nstrongest = {{ task = "{STRONG}" }}\n')
    out = route(proj, stub, brief("S", "tests/kit/test_example.py"))
    assert out.stdout == f"route: mid low task {STRONG} via strongest\n", out.stdout + out.stderr


def test_no_table_prints_route_none(proj, stub):
    """REQ-052 AC7: rule 5, no `[models.routes]` keeps today's one route (brief #1099 test (d))."""
    proj.write("agk.toml", 'default_branch = "main"\n')
    out = route(proj, stub, brief("S", "tests/kit/test_example.py"))
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout == "route: none\n"


def test_a_refused_table_names_the_setting(proj, stub):
    """REQ-052 AC7: rule 3, the command refuses naming the setting, never the value."""
    proj.write("agk.toml", f'[models.routes]\nmid = {{ task = "{ODD}" }}\n')
    out = route(proj, stub, brief("S", "tests/kit/test_example.py"))
    assert out.returncode == 2
    assert "(setting: models.routes)" in out.stdout and ODD not in out.stdout + out.stderr


# --- the model-routes doctor row (SPEC-0006 rule 5, amendment 145 item 6) ------------------------


def test_doctor_row_with_no_table_is_one_route(tmp_path):
    """REQ-052 AC7: the doctor row's first case."""
    got = doctor.model_routes_result(project(tmp_path, 'default_branch = "main"\n'))
    assert (got.status, got.message) == ("ok", " (one route)")


def test_doctor_row_warns_on_a_tier_without_its_own_route(tmp_path):
    """REQ-052 AC7: the doctor row's second case; `small` and `mechanical` use `mid`."""
    got = doctor.model_routes_result(
        project(tmp_path, f'[models.routes]\nstrongest = {{ task = "{STRONG}" }}\n')
    )
    assert got.status == "fail"
    assert got.message == " (mid has no route; it uses the route of strongest)"
    assert STRONG not in got.message


def test_doctor_row_warns_on_a_refused_table(tmp_path):
    """REQ-052 AC7: the doctor row's third case, naming the setting, never the value."""
    got = doctor.model_routes_result(
        project(tmp_path, f'[models.routes]\nmid = {{ task = "{ODD}" }}\n')
    )
    assert got.status == "fail"
    assert got.message == " (setting: models.routes)"


def test_doctor_row_is_ok_when_every_used_tier_has_a_route(tmp_path):
    """REQ-052 AC7: every tier the kinds use has its own route."""
    got = doctor.model_routes_result(project(tmp_path, ROUTES))
    assert got.status == "ok"
    assert doctor.CHECKS["model-routes"][0] == "warn"


def test_the_kit_ships_no_routes_table_and_the_templates_only_a_comment():
    """REQ-052 AC7: rule 3, no routes table in the kit's `agk.toml` or templates (brief #1099
    answer 3: the templates carry it commented, with no model name)."""
    kit = Path(__file__).resolve().parents[2]
    assert config.model_routes(kit) == {}
    for name in ("agk.toml", "agk.adopt.toml"):
        text = (kit / "kit" / "templates" / name).read_text(encoding="utf-8")
        assert "# [models.routes]" in text
        live = [x for x in text.splitlines() if not x.lstrip().startswith("#")]
        assert not any(re.match(r"\s*\[models", x) for x in live), name
