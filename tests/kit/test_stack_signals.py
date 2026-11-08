"""Tests of the signal table and `front_door.py check-signals` (SPEC-0057 rule 5, build (a)).

REQ-064 AC4: a table that names something the kit cannot declare, or forgets a kind, cannot ship.
Each refusal names the setting and never a value. The table is read from the script's own root.
Fixtures in `tmp_path` only: invented tables and names, no network, no install.
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
TABLE = "config/stack-signals.toml"
PLANT = "zanzibar-kind"  # invented: it must never reach the output
PLAYBOOKS = ("default", "pilot", "kind-a", "kind-b")
STACK = '[[stack]]\nname = "lang-tool"\nmanifests = ["lang.manifest"]\nlocks = []\n'
ROW = '[[work_type]]\nname = "{}"\nsignal = "slug"\nfile = "lang.manifest"\ncontains = "word"\n'
LISTS = 'no_signal = ["kind-b", "pilot"]\nignore = ["vendor"]\n'
GOOD = LISTS + "\n" + STACK + "\n" + ROW.format("kind-a")


def kit(root: Path, table: str | None, playbooks=PLAYBOOKS) -> Path:
    """A copy of the script with its own config, as an installed kit holds it."""
    (root / "scripts/agk").mkdir(parents=True)
    for name in ("front_door.py", "guard.py", "playbook_format.py"):
        shutil.copy(SCRIPTS / name, root / "scripts/agk" / name)
    (root / "config/playbooks").mkdir(parents=True)
    for name in playbooks:
        (root / f"config/playbooks/{name}.toml").write_text("format = 1\n", encoding="utf-8")
    if table is not None:
        (root / TABLE).write_text(table, encoding="utf-8")
    return root / "scripts/agk/front_door.py"


def check(script: Path, *extra: str, cwd: Path | None = None):
    return subprocess.run(
        [sys.executable, "-I", str(script), "check-signals", *extra],
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd or script.parent,
    )


def test_ac4_a_good_table_passes(tmp_path):
    """REQ-064 AC4: rule 5."""
    proc = check(kit(tmp_path, GOOD))
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.startswith("ok front-door")


REFUSED = {
    "row-no-playbook": (GOOD + "\n" + ROW.format(PLANT), "`name` has no file in config/playbooks/"),
    "default-in-row": (GOOD + "\n" + ROW.format("default"), "`name` holds the base playbook"),
    "pilot-in-row": (GOOD + "\n" + ROW.format("pilot"), "`name` holds the kind never proposed"),
    "default-in-stack": (
        GOOD + '\n[[stack]]\nname = "default"\nmanifests = ["m"]\nlocks = []\n',
        "`name` holds the base playbook",
    ),
    "pilot-in-stack": (
        GOOD + '\n[[stack]]\nname = "pilot"\nmanifests = ["m"]\nlocks = []\n',
        "`name` holds the kind never proposed",
    ),
    "default-in-no-signal": (
        GOOD.replace('"kind-b", "pilot"', '"default", "kind-b", "pilot"'),
        "`no_signal` holds the base playbook",
    ),
    "pilot-missing": (
        GOOD.replace('"kind-b", "pilot"', '"kind-b"'),
        "`no_signal` lacks the kind never proposed",
    ),
    "no-signal-no-playbook": (
        GOOD.replace('"kind-b", "pilot"', f'"kind-b", "pilot", "{PLANT}"'),
        "`no_signal` holds a name with no file in config/playbooks/",
    ),
    "playbook-unaccounted": (
        GOOD.replace('"kind-b", "pilot"', '"pilot"'),
        "a playbook has no row and is not in `no_signal`",
    ),
    "rows-and-no-signal": (
        GOOD.replace('"kind-b", "pilot"', '"kind-a", "kind-b", "pilot"'),
        "`no_signal` holds a name that has rows",
    ),
    "unknown-key-top": (f'{PLANT} = 1\n{GOOD}', "an unknown top-level key"),
    "unknown-key-stack": (
        GOOD.replace('locks = []', f'locks = []\n{PLANT} = 1'),
        "[[stack]] row 1 has an unknown key",
    ),
    "unknown-key-work-type": (
        GOOD.replace('contains = "word"', f'contains = "word"\n{PLANT} = 1'),
        "[[work_type]] row 1 has an unknown key",
    ),
    "missing-key": (GOOD.replace('signal = "slug"\n', ""), "`signal` is missing or malformed"),
    "bad-slug": (GOOD.replace('"slug"', f'"{PLANT} X"'), "`signal` is missing or malformed"),
    "two-words": (GOOD.replace('"word"', f'"{PLANT} X"'), "`contains` is missing or malformed"),
    "empty-manifests": (
        GOOD.replace('["lang.manifest"]', "[]", 1),
        "`manifests` is missing or malformed",
    ),
    "ignore-not-a-list": (GOOD.replace('["vendor"]', f'"{PLANT}"'), "`ignore` is not a list"),
    "row-not-a-table": (f'{LISTS}stack = ["{PLANT}"]\n', "[[stack]] row 1 is not a table"),
    "not-toml": (f"{PLANT} = = =\n", f"{TABLE} cannot be read"),
}


@pytest.mark.parametrize("case", sorted(REFUSED))
def test_ac4_each_refused_form_names_the_setting_and_never_a_value(case, tmp_path):
    """REQ-064 AC4: rule 5, refusals by principle 8."""
    table, expected = REFUSED[case]
    proc = check(kit(tmp_path, table))
    assert proc.returncode == 1, proc.stdout
    assert "FAIL front-door: rule 5:" in proc.stdout and expected in proc.stdout
    for value in (PLANT, "pilot", "default", "kind-a", "kind-b"):
        assert value not in proc.stdout + proc.stderr


def test_ac4_a_missing_table_is_refused(tmp_path):
    """REQ-064 AC4: rule 5."""
    proc = check(kit(tmp_path, None))
    assert proc.returncode == 1 and f"{TABLE} cannot be read" in proc.stdout


def test_ac4_a_name_outside_the_playbooks_folder_is_not_a_file_there(tmp_path):
    """REQ-064 AC4: rule 5: a name is matched against the folder's list, never as a path."""
    (tmp_path / "config").mkdir()
    (tmp_path / "config/outside.toml").write_text("format = 1\n", encoding="utf-8")
    (tmp_path / "x").mkdir()
    table = GOOD + "\n" + ROW.format("../outside")
    proc = check(kit(tmp_path / "x", table))
    assert proc.returncode == 1 and "`name` has no file in" in proc.stdout


@pytest.mark.parametrize("pilot", [True, False])
def test_ac4_the_shipped_table_passes_with_and_without_the_pilot_playbook(pilot, tmp_path):
    """REQ-064 AC4: rule 5."""
    script = kit(tmp_path, (KIT_ROOT / TABLE).read_text(encoding="utf-8"), ())
    for path in (KIT_ROOT / "config/playbooks").glob("*.toml"):
        if pilot or path.stem != "pilot":
            shutil.copy(path, tmp_path / "config/playbooks" / path.name)
    proc = check(script)
    assert proc.returncode == 0, proc.stdout


def test_ac4_every_shipped_playbook_is_accounted_for_and_only_rows_are_proposable():
    """REQ-064 AC4: rule 5, `Q-S0057-6`; the rows of the table as this build chose them."""
    table = tomllib.loads((KIT_ROOT / TABLE).read_text(encoding="utf-8"))
    rows = {row["name"] for row in table["work_type"]}
    held = set(table["no_signal"])
    shipped = {p.stem for p in (KIT_ROOT / "config/playbooks").glob("*.toml")} - {"default"}
    assert rows | held == shipped and not rows & held
    assert held == {"cloud-migration", "pilot"}
    manifests = [name for row in table["stack"] for name in row["manifests"]]
    assert len(manifests) == len(set(manifests))  # one stack per manifest name
    assert {row["file"] for row in table["work_type"]} <= set(manifests)


def test_ac4_the_table_is_read_from_the_script_root_never_the_repository(tmp_path):
    """REQ-064 AC4: rule 5, `Q-S0057-2`."""
    (tmp_path / "kit").mkdir()
    script = kit(tmp_path / "kit", GOOD)
    product = tmp_path / "product"
    (product / "config").mkdir(parents=True)
    (product / TABLE).write_text("not a table = = =\n", encoding="utf-8")
    assert check(script, cwd=product).returncode == 0
    assert check(script, "--root", str(product), cwd=product).returncode == 2
    (tmp_path / "bare").mkdir()
    bare = kit(tmp_path / "bare", None)
    (product / TABLE).write_text(GOOD, encoding="utf-8")
    assert check(bare, cwd=product).returncode == 1


def test_ac4_check_signals_takes_no_argument(tmp_path):
    """REQ-064 AC4: rule 5: usage is exit 2."""
    assert check(kit(tmp_path, GOOD), "extra").returncode == 2
