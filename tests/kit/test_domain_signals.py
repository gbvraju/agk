"""Tests of the domain signal table (SPEC-0074 rule 5; REQ-081 AC3; brief #1936).

`config/domain-signals.toml` names, per shipped pack, plain words, file names and dependencies, in
the form of `config/stack-signals.toml` (SPEC-0057 rule 5). `front_door.signal_problems` checks it:
a row with an unknown key, a missing key, a value that is not a list of single words or a `name`
that is no shipped pack fails, naming the row and the key, never a value. Fixtures in `tmp_path`
only: invented tables and names, no network.
"""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import front_door  # noqa: E402

TABLE = "config/domain-signals.toml"
PLANT = "zanzibar-word"  # invented: it must never reach the output
ROW = '[[domain]]\nname = "zz-shop"\nwords = ["basket"]\nfiles = []\ndependencies = []\n'


def kit(root: Path, table: str) -> Path:
    """The kit's signal tables and playbooks, one invented pack and the given domain table."""
    (root / "config").mkdir()
    shutil.copy(KIT_ROOT / "config/stack-signals.toml", root / "config/stack-signals.toml")
    shutil.copytree(KIT_ROOT / "config/playbooks", root / "config/playbooks")
    (root / "config/domains").mkdir()
    (root / "config/domains/zz-shop.toml").write_text("format = 1\n", encoding="utf-8")
    (root / TABLE).write_text(table, encoding="utf-8")
    return root


def test_ac3_the_shipped_table_passes():
    """REQ-081 AC3: SPEC-0074 rule 5 (the kit's own table, one row per shipped pack)."""
    assert front_door.domain_signal_problems(KIT_ROOT) == []
    assert front_door.signal_problems(KIT_ROOT) == []
    rows = tomllib.loads((KIT_ROOT / TABLE).read_text(encoding="utf-8"))["domain"]
    packs = {p.stem for p in (KIT_ROOT / "config/domains").glob("*.toml")}
    assert sorted(r["name"] for r in rows) == sorted(packs)
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(KIT_ROOT / "scripts/agk/front_door.py"), "check-signals"],
        capture_output=True, text=True, check=False, cwd=KIT_ROOT,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_ac3_the_table_is_installed_verbatim():
    """REQ-081 AC3: SPEC-0074 rule 15 (layouts: the table joins `verbatim`)."""
    manifest = json.loads((KIT_ROOT / "kit/manifest.json").read_text(encoding="utf-8"))
    assert TABLE in manifest["verbatim"]


def test_ac3_a_good_table_passes(tmp_path):
    """REQ-081 AC3: SPEC-0074 rule 5."""
    assert front_door.domain_signal_problems(kit(tmp_path, ROW)) == []


HEAD = "rule 5: config/domain-signals.toml: [[domain]] row 1"
BAD = {
    "unknown": (ROW + f'{PLANT} = ["x"]\n', f"{HEAD} has an unknown key (key: {PLANT})"),
    "missing": (ROW.replace("files = []\n", ""), f"{HEAD} is missing a key (key: files)"),
    "not-list": (
        ROW.replace('words = ["basket"]', f'words = "{PLANT}"'),
        f"{HEAD} is not a list of single words (key: words)",
    ),
    "two-words": (
        ROW.replace("dependencies = []", f'dependencies = ["{PLANT} lib"]'),
        f"{HEAD} is not a list of single words (key: dependencies)",
    ),
    "no-pack": (ROW.replace("zz-shop", PLANT), f"{HEAD} `name` is no shipped pack (key: name)"),
    "name-type": (ROW.replace('"zz-shop"', "3"), f"{HEAD} `name` is no shipped pack (key: name)"),
}


@pytest.mark.parametrize("case", sorted(BAD))
def test_ac3_a_malformed_row_fails_naming_the_key(tmp_path, case):
    """REQ-081 AC3: SPEC-0074 rule 5 (each refusal names the key, never a value)."""
    table, line = BAD[case]
    found = front_door.domain_signal_problems(kit(tmp_path, table))
    assert found == [line]
    assert all(PLANT not in f.replace(f"(key: {PLANT})", "") for f in found)
    assert line in front_door.signal_problems(tmp_path)


def test_ac3_a_table_with_no_row_or_an_unknown_top_key_fails(tmp_path):
    """REQ-081 AC3: SPEC-0074 rule 5."""
    head = "rule 5: config/domain-signals.toml:"
    assert front_door.domain_signal_problems(kit(tmp_path, f"{PLANT} = 1\n")) == [
        f"{head} an unknown top-level key",
        f"{head} [[domain]] has no row",
    ]
