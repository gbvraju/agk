"""SPEC-0041 build (o): the `[governance] level` setting in team mode (brief #1509, ADR-0639).

Rule 31: a new `[governance]` table accepts exactly one key, `level`, one of the five levels of
rule 17; anything else is refused naming the setting, never the value. New installs write
`light`; an existing project with no table reads as today; a sidecar keeps `[personal] level`.
No existing check is left out by any level (`Q-562-1`). Invented repositories only.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
KIT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402

LEVELS = ("light", "tests-first", "spec", "review", "evidence")


def write(root: Path, text: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "agk.toml").write_text(text, encoding="utf-8")
    return root


def refusal(root: Path) -> str:
    with pytest.raises(common.CheckError) as err:
        common.governance_level(root)
    return str(err.value)


@pytest.mark.parametrize("level", LEVELS)
def test_rule31_each_level_is_accepted(tmp_path, level):
    """REQ-048 AC1: rule 31 (each of the five levels of rule 17 is read in team mode)."""
    root = write(tmp_path, f'review_mode = "team"\n\n[governance]\nlevel = "{level}"\n')
    assert common.governance_level(root) == level
    assert common.GOVERNANCE_LEVELS == common.PERSONAL_CHOICES["level"]


def test_rule31_an_inline_table_is_the_same_table(tmp_path):
    """REQ-048 AC1: rule 31 (the templates' one-line form is the `[governance]` table)."""
    root = write(tmp_path, 'governance = { level = "spec" }\nreview_mode = "team"\n')
    assert common.governance_level(root) == "spec"


def test_rule31_skip_floor_is_refused_naming_the_setting(tmp_path):
    """REQ-048 AC1: rule 31 (any other key, for example `skip_floor`, is refused)."""
    root = write(tmp_path, '[governance]\nlevel = "light"\nskip_floor = true\n')
    assert refusal(root) == "unknown key in [governance] (setting: governance.skip_floor)"


@pytest.mark.parametrize(
    "body",
    ['level = "lightest-secret-value"', "level = 3", "level = true", 'level = ["light"]'],
)
def test_rule31_an_unknown_value_or_a_wrong_type_is_refused(tmp_path, body):
    """REQ-048 AC1: rule 31 (an unknown value or a wrong type names the setting, never the value)."""
    root = write(tmp_path, f"[governance]\n{body}\n")
    assert refusal(root) == "not an accepted value (setting: governance.level)"


def test_rule31_a_governance_value_that_is_not_a_table_is_refused(tmp_path):
    """REQ-048 AC1: rule 31 (`governance = "light"` is a wrong type for the table)."""
    text = refusal(write(tmp_path, 'governance = "light"\n'))
    assert text == "[governance] must be a table (setting: governance)"


def test_rule31_no_table_or_no_key_reads_as_today(tmp_path):
    """REQ-048 AC1: rule 31 (an existing project with no table or no key runs every check)."""
    assert common.governance_level(write(tmp_path / "a", 'review_mode = "team"\n')) is None
    assert common.governance_level(write(tmp_path / "b", "[governance]\n")) is None
    assert common.governance_level(tmp_path / "none") is None


def test_rule31_a_sidecar_never_reads_the_governance_table(tmp_path):
    """REQ-048 AC1: rules 17 and 31 (a sidecar keeps `[personal] level`; `[governance]` unread)."""
    root = write(
        tmp_path,
        '[personal]\nforge = "files"\nlevel = "spec"\n\n[governance]\nskip_floor = true\n',
    )
    assert common.governance_level(root) is None
    assert common.personal_table(root)["level"] == "spec"


def test_rule31_no_level_leaves_a_check_out(tmp_path):
    """REQ-048 AC1: rule 31 and Q-562-1 (until a person rules, no level leaves a check out)."""
    assert common.GOVERNANCE_SKIPS == {level: () for level in LEVELS}


@pytest.mark.parametrize("template", ["kit/templates/agk.toml", "kit/templates/agk.adopt.toml"])
def test_rule31_both_templates_write_light(tmp_path, template):
    """REQ-048 AC1: rule 31 (`init.py` and `adopt.py` write `level = "light"` for a new install)."""
    text = (KIT / template).read_text(encoding="utf-8")
    assert tomllib.loads(text)["governance"] == {"level": "light"}
    assert text.count('governance = { level = "light" }') == 1


def test_rule31_a_new_init_and_adopt_write_the_light_line(tmp_path):
    """REQ-048 AC1: rule 31 (a new `init` and `adopt` plan the light line in agk.toml)."""
    import adopt  # noqa: PLC0415 - kit-only modules, imported where used
    import init  # noqa: PLC0415

    target = tmp_path / "demo-app"
    (target / ".git" / "refs" / "heads").mkdir(parents=True)
    (target / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    items, _entries, _branch = init.build_items(target, "2026-11-18")
    planned = dict(items)["agk.toml"].decode("utf-8")
    assert tomllib.loads(planned)["governance"] == {"level": "light"}
    plan, _entries, _branch = adopt.build_plan(target, "2026-11-18")
    adopted = {rel: content for rel, _action, content, _detail in plan}["agk.toml"]
    assert tomllib.loads(adopted.decode("utf-8"))["governance"] == {"level": "light"}


def doctor(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "doctor.py"), *args, str(root)],
        capture_output=True,
        text=True,
        cwd=root,
    )


def test_rule31_doctor_prints_the_level_in_force(tmp_path):
    """REQ-048 AC1: rule 31 (`doctor.py` prints the level; `--json` carries `governance_level`)."""
    import doctor  # noqa: PLC0415 - kit-only module, imported where used

    root = write(tmp_path, '[governance]\nlevel = "tests-first"\n')
    assert doctor.governance_line(root) == (
        "governance level: tests-first (the floor, the secret scan and no regression, "
        "runs at every level)"
    )
    assert doctor.governance_line(write(tmp_path / "unset", 'review_mode = "team"\n')) is None
    data = json.loads(doctor.render_json([], "0.0.0", governance="governance level: light"))
    assert data["governance_level"] == "governance level: light"
    text = doctor.render_text(
        [], "0.0.0", scan="secret scan: x", governance="governance level: light"
    )
    assert text.splitlines()[1:3] == ["secret scan: x", "governance level: light"]


def test_rule31_doctor_refuses_a_bad_table_naming_the_setting(tmp_path):
    """REQ-048 AC1: rule 31 (doctor exits 1 on a refused table, naming the setting only)."""
    root = write(tmp_path, '[governance]\nlevel = "lightest-secret-value"\n')
    proc = doctor(root)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "governance.level" in proc.stdout
    assert "lightest-secret-value" not in proc.stdout + proc.stderr
