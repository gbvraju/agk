"""Tests of `grill.py questions` (SPEC-0073 rules 2, 3 and 11; REQ-080 AC1 and AC7; brief #1933).

`grill.py questions [--depth D] [--playbook KIND] [--answers FILE] [--root DIR]` prints the grill
items to ask, in order: the items of `default.toml` at or below the depth, then the work type's own
items, then `success` among the critical items. Each is printed as `<id> (critical|-) <text>` with
a `Recommended: <steward fills>` line after it, and the last line is `budget: <n>`. It never prints
an id the answers file holds. Without `--depth` it reads `[quality] grill`. Fixtures in `tmp_path`
only: invented data, no network, no model.
"""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from test_check_playbooks import FULL, REL, clean_env, replace

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "agk" / "grill.py"
DEFAULT = KIT_ROOT / "config" / "playbooks" / "default.toml"
RECOMMENDED = "Recommended: <steward fills>"

LIGHT = ["problem", "who-hurts", "non-goals", "riskiest"]
STANDARD = [
    "problem",
    "evidence",
    "who-hurts",
    "job",
    "today",
    "why-now",
    "guardrails",
    "non-goals",
    "riskiest",
    "first-slice",
]
DEEP = [*STANDARD[:9], "pre-mortem", "stop", "first-slice"]
OWN = (
    '[[discovery]]\nid = "zz-offline"\ntext = "Must it work offline?"\ndepth = "light"\n'
    "critical = false\n\n"
)
SUCCESS = '[[discovery]]\nid = "success"\ntext = "How will we know the work succeeded?"\n\n'


def project(root: Path, agk: str = "", web_app: str | None = None) -> Path:
    folder = root / "config" / "playbooks"
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DEFAULT, folder / "default.toml")
    if web_app is not None:
        (root / REL).write_text(web_app, encoding="utf-8")
    runs = root / "docs" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "2026-11-01-example.md").write_text("# a run record\n", encoding="utf-8")
    if agk:
        (root / "agk.toml").write_text(agk, encoding="utf-8")
    return root


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 - fixed argument list
        [sys.executable, str(SCRIPT), "questions", "--root", str(root), *args],
        capture_output=True,
        text=True,
        env=clean_env(),
        check=False,
    )


def asked(result: subprocess.CompletedProcess[str]) -> tuple[list[str], list[str], str]:
    """The ids printed, their critical marks, and the budget line; each item followed by its
    recommendation line."""
    assert result.returncode == 0, result.stdout + result.stderr
    lines = result.stdout.splitlines()
    budget = lines.pop()
    items = [ln for n, ln in enumerate(lines) if n % 2 == 0]
    recs = [ln for n, ln in enumerate(lines) if n % 2 == 1]
    assert recs == [RECOMMENDED] * len(items), result.stdout
    ids = [ln.split(" ", 1)[0] for ln in items]
    marks = [ln.split(" ", 2)[1] for ln in items]
    return ids, marks, budget


@pytest.mark.parametrize(
    ("depth", "ids", "budget"),
    [
        ("light", [*LIGHT, "success"], "budget: 5"),
        ("standard", [*STANDARD, "success"], "budget: 12"),
        ("deep", [*DEEP, "success"], "budget: 20"),
    ],
)
def test_ac1_each_depth_prints_exactly_the_composed_items_in_order(tmp_path, depth, ids, budget):
    """REQ-080 AC1: SPEC-0073 rules 2 and 3 (each depth, in order, a recommendation each)."""
    found, marks, last = asked(run(project(tmp_path), "--depth", depth))
    assert found == ids and last == budget
    critical = [i for i, m in zip(found, marks, strict=True) if m == "(critical)"]
    assert critical == [*LIGHT, "success"]
    assert set(marks) <= {"(critical)", "-"}


def test_ac1_an_item_line_carries_the_playbook_text(tmp_path):
    """REQ-080 AC1: SPEC-0073 rule 2 (`<id> (critical|-) <text>`)."""
    result = run(project(tmp_path), "--depth", "light")
    first = result.stdout.splitlines()[0]
    assert first.startswith("problem (critical) ") and first.endswith("?")
    success = [ln for ln in result.stdout.splitlines() if ln.startswith("success ")]
    assert success and success[0].startswith("success (critical) ")


def test_ac7_without_depth_the_quality_grill_setting_decides(tmp_path):
    """REQ-080 AC7: SPEC-0073 rule 11 (`grill`: absent standard, set, and light for a pilot)."""
    root = project(tmp_path)
    assert asked(run(root))[2] == "budget: 12"
    (root / "agk.toml").write_text('[quality]\ngrill = "deep"\n', encoding="utf-8")
    assert asked(run(root))[2] == "budget: 20"
    assert asked(run(root, "--depth", "light"))[2] == "budget: 5"


def test_ac7_a_declared_pilot_runs_the_light_grill(tmp_path):
    """REQ-080 AC7: SPEC-0073 rule 11 (`light` with a declared pilot and no `grill` key)."""
    pilot = (KIT_ROOT / "config" / "playbooks" / "pilot.toml").read_text(encoding="utf-8")
    root = project(tmp_path, '[delivery]\nwork_type = "pilot"\n')
    (root / "config" / "playbooks" / "pilot.toml").write_text(pilot, encoding="utf-8")
    ids, _, budget = asked(run(root))
    assert ids == [*LIGHT, "success"] and budget == "budget: 5"


def test_ac7_a_refused_quality_table_is_refused_naming_the_key(tmp_path):
    """REQ-080 AC7: SPEC-0073 rule 11 (`grill = 3` is refused naming quality.grill)."""
    root = project(tmp_path, "[quality]\ngrill = 3\n")
    result = run(root)
    assert result.returncode == 1
    assert "(setting: quality.grill)" in result.stdout + result.stderr


def test_ac1_an_answered_item_is_never_printed(tmp_path):
    """REQ-080 AC1: SPEC-0073 rule 2 (never an item already answered)."""
    answers = tmp_path / "answers.json"
    rows = [{"id": "problem", "answer": "zz-words"}, {"id": "success", "open": True}]
    answers.write_text(json.dumps({"answers": rows, "grill": [{"id": "riskiest"}]}), "utf-8")
    result = run(project(tmp_path / "p"), "--depth", "light", "--answers", str(answers))
    ids, _, budget = asked(result)
    assert ids == ["who-hurts", "non-goals"] and budget == "budget: 5"
    assert "zz-words" not in result.stdout


def test_ac1_an_unreadable_answers_file_is_refused_never_read_as_empty(tmp_path):
    """REQ-080 AC1: brief #1933 answer 9 (refused naming `--answers`)."""
    bad = tmp_path / "answers.json"
    bad.write_text("zz-not-json", encoding="utf-8")
    root = project(tmp_path / "p")
    for path in (bad, tmp_path / "missing.json"):
        result = run(root, "--answers", str(path))
        out = result.stdout + result.stderr
        assert result.returncode == 1 and "--answers" in out and "zz-not-json" not in out


def test_ac1_a_work_type_s_own_items_follow_the_default_s(tmp_path):
    """REQ-080 AC1: SPEC-0073 rule 3 (a work type may add its own items, after the defaults)."""
    web_app = replace(SUCCESS, SUCCESS + OWN, FULL)
    root = project(tmp_path, web_app=web_app)
    ids, marks, _ = asked(run(root, "--depth", "light", "--playbook", "web-app"))
    assert ids == [*LIGHT, "zz-offline", "success"] and marks[4] == "-"
    (root / "agk.toml").write_text('[delivery]\nwork_type = "web-app"\n', encoding="utf-8")
    assert asked(run(root, "--depth", "light"))[0] == ids


def test_ac1_a_copied_playbook_with_no_grill_items_adds_nothing(tmp_path):
    """REQ-080 AC1: brief #1933 answer 9 (a playbook copied before this build)."""
    root = project(tmp_path, web_app=FULL)
    assert asked(run(root, "--depth", "light", "--playbook", "web-app"))[0] == [*LIGHT, "success"]


def test_ac1_a_work_type_outside_the_list_is_refused_naming_the_setting(tmp_path):
    """REQ-080 AC1: brief #1933 answer 8 (refused as `engines.playbook_questions` refuses it)."""
    result = run(project(tmp_path), "--playbook", "zz-unknown")
    out = result.stdout + result.stderr
    assert result.returncode == 1 and "(setting: work-type)" in out and "zz-unknown" not in out


@pytest.mark.parametrize(
    "args",
    [["--depth", "zz-extreme"], ["--depth"], ["--zz-flag", "x"]],
    ids=["bad-depth", "no-value", "unknown-flag"],
)
def test_ac1_a_usage_error_exits_2(tmp_path, args):
    """REQ-080 AC1: brief #1933 answer 5 (exit 2 for usage)."""
    result = run(project(tmp_path), *args)
    assert result.returncode == 2
    assert "zz-extreme" not in result.stdout


def test_ac1_no_command_is_a_usage_error():
    """REQ-080 AC1: brief #1933 answer 5 (`record` and `ready` are build (b)'s)."""
    for args in ([], ["record"]):
        result = subprocess.run(  # nosec B603 - fixed argument list
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            env=clean_env(),
            check=False,
        )
        assert result.returncode == 2


@pytest.mark.parametrize(
    "text",
    ['{"answers": 5}', '{"answers": null}', '{"grill": "zz-x"}', '{"answers": [5]}', "[]"],
    ids=["a-number", "null", "a-string", "a-row-not-an-object", "a-list"],
)
def test_ac1_an_answers_file_of_another_shape_is_refused_without_a_traceback(tmp_path, text):
    """REQ-080 AC1: brief #1933 answer 9 (refused naming `--answers`, never a traceback)."""
    bad = tmp_path / "answers.json"
    bad.write_text(text, encoding="utf-8")
    result = run(project(tmp_path / "p"), "--answers", str(bad))
    out = result.stdout + result.stderr
    assert result.returncode == 1, out
    assert "the answers file is not an object of lists (setting: --answers)" in out
    assert "Traceback" not in out and "zz-x" not in out


def test_ac7_the_plugin_layout_reads_the_plugin_s_playbooks_and_installed_the_project_s(tmp_path):
    """REQ-080 AC7: brief #1933 answer 8 (`[kit] layout = "plugin"`: the playbooks from the plugin
    root, as `engines.py` reads them; installed: from the project)."""
    env = {**clean_env(), "CLAUDE_PLUGIN_ROOT": str(KIT_ROOT)}
    clean = tmp_path / "clean"
    clean.mkdir()
    (clean / "agk.toml").write_text('mode = "init"\n\n[kit]\nlayout = "plugin"\n', "utf-8")
    assert not (clean / "config" / "playbooks").exists()
    found = subprocess.run(  # nosec B603 - fixed argument list
        [sys.executable, str(SCRIPT), "questions", "--root", str(clean), "--depth", "light"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert asked(found)[0] == [*LIGHT, "success"]
    installed = project(tmp_path / "installed", '[kit]\nlayout = "installed"\n')
    own = installed / "config" / "playbooks" / "default.toml"
    text = own.read_text(encoding="utf-8")
    cut = text.index('[[discovery]]\nid = "riskiest"')
    end = text.index("[[discovery]]", cut + 1)
    own.write_text(text[:cut] + text[end:], encoding="utf-8")
    found = subprocess.run(  # nosec B603 - fixed argument list
        [sys.executable, str(SCRIPT), "questions", "--root", str(installed), "--depth", "light"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert asked(found)[0] == ["problem", "who-hurts", "non-goals", "success"]
