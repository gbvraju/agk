"""Tests of the evaluation set and its checks (SPEC-0077 rule 9; REQ-084 AC7, AC8; ADR-0846).

Brief #2042 build (a).

`evals/` holds two invented reference products and the rubric; `eval_run.py check` fails a malformed
product, rubric or run record naming the file class and the key, never a value; `median DIR` prints
the median of three complete runs per product and layer and the cost per accepted feature, and
`incomplete (<k> of 3 runs complete)` otherwise, never 0. Nothing under `evals/` is installed. Files
only; no network, no model.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from conftest import KIT_ROOT, manifest

SCRIPT = KIT_ROOT / "scripts" / "agk" / "eval_run.py"
EVALS = KIT_ROOT / "evals"
LAYERS = (
    "problem",
    "scope",
    "domain-rules",
    "architecture",
    "threats",
    "data",
    "usability",
    "code",
)


def run(*args: str, cwd: Path = KIT_ROOT, script: Path = SCRIPT) -> subprocess.CompletedProcess:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(cwd)}
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A saved copy of the shipped `evals/` with the kit's playbook stems beside it."""
    root = tmp_path / "kit"
    shutil.copytree(EVALS, root / "evals")
    shutil.copytree(KIT_ROOT / "config" / "playbooks", root / "config" / "playbooks")
    return root


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_ac7_the_shipped_set_passes_its_check():
    """REQ-084 AC7: SPEC-0077 rule 9 (two products and eight layers)."""
    proc = run("check")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.strip() == "ok evals: 2 products, 8 layers"


def test_ac7_the_products_are_invented_and_complete():
    """REQ-084 AC7: SPEC-0077 rule 9 (answer 1: the booking web app and the payments API)."""
    found = {}
    for name in ("booking-web", "payments-api"):
        data = tomllib.loads((EVALS / name / "product.toml").read_text("utf-8"))
        assert data["id"] == name and data["format"] == 1
        assert 3 <= len(data["acceptance"]) <= 12
        found[name] = (data["work_type"], data["domain"])
    assert found == {
        "booking-web": ("web-app", "none"),
        "payments-api": ("api-service", "payments"),
    }
    rubric = tomllib.loads((EVALS / "rubric.toml").read_text("utf-8"))
    assert tuple(layer["name"] for layer in rubric["layer"]) == LAYERS
    assert rubric["tolerance"] == 0 and rubric["scale"] == 6


@pytest.mark.parametrize(
    ("file", "old", "new", "line"),
    [
        (
            "booking-web/product.toml",
            'work_type = "web-app"',
            'work_type = "spaceship"',
            "FAIL evals: product file booking-web: rule 9: a value outside its list"
            " (setting: work_type)",
        ),
        (
            "payments-api/product.toml",
            'domain = "payments"',
            'domain = "casino"',
            "FAIL evals: product file payments-api: rule 9: a value outside its list"
            " (setting: domain)",
        ),
        (
            "booking-web/product.toml",
            "format = 1",
            "format = true",
            "FAIL evals: product file booking-web: rule 9: a value of the wrong type"
            " (setting: format)",
        ),
        (
            "booking-web/product.toml",
            'id = "AC2"',
            'id = "AC1"',
            "FAIL evals: product file booking-web: rule 9: a repeated acceptance id"
            " (setting: acceptance.id)",
        ),
        (
            "booking-web/product.toml",
            "https://studio.example.com",
            "https://studio.example.org",
            "FAIL evals: product file booking-web: rule 9: a host other than example.com"
            " (setting: host)",
        ),
        (
            "booking-web/product.toml",
            'title = "',
            'colour = "blue"\ntitle = "',
            "FAIL evals: product file booking-web: rule 9: an unknown key (setting: colour)",
        ),
        (
            "rubric.toml",
            "tolerance = 0",
            "tolerance = true",
            "FAIL evals: rubric: rule 10: a value of the wrong type (setting: rubric.tolerance)",
        ),
        (
            "rubric.toml",
            "tolerance = 0",
            "tolerance = 7",
            "FAIL evals: rubric: rule 10: a value outside 0 to 6 (setting: rubric.tolerance)",
        ),
        (
            "rubric.toml",
            "scale = 6",
            "scale = 6\nruns = 3",
            "FAIL evals: rubric: rule 9: an unknown key (setting: runs)",
        ),
    ],
)
def test_ac7_a_malformed_file_fails_naming_its_class_and_key(tree, file, old, new, line):
    """REQ-084 AC7: SPEC-0077 rule 9 (answers 2, 3 and 6)."""
    edit(tree / "evals" / file, old, new)
    proc = run("check", "--root", str(tree))
    assert proc.returncode == 1
    assert line in proc.stdout.splitlines(), proc.stdout
    for value in ("spaceship", "casino", "example.org", "blue"):
        assert value not in proc.stdout


def test_ac7_a_layer_out_of_order_or_without_a_source_fails(tree):
    """REQ-084 AC7: SPEC-0077 rule 9 (the layers in rule 9's order, each criterion sourced)."""
    rubric = tree / "evals" / "rubric.toml"
    text = rubric.read_text("utf-8")
    edit(rubric, 'name = "problem"', 'name = "PLACEHOLDER"')
    edit(rubric, 'name = "scope"', 'name = "problem"')
    edit(rubric, 'name = "PLACEHOLDER"', 'name = "scope"')
    proc = run("check", "--root", str(tree))
    assert "FAIL evals: rubric: rule 9: a layer missing or out of order (setting: layer.name)" in (
        proc.stdout.splitlines()
    )
    rubric.write_text(re.sub(r'source = "[^"]*"', 'source = ""', text, count=1), "utf-8")
    proc = run("check", "--root", str(tree))
    assert proc.returncode == 1
    assert "FAIL evals: rubric: rule 9: a criterion with no source (setting: criteria.source)" in (
        proc.stdout.splitlines()
    )


def test_ac7_a_file_that_is_not_toml_or_holds_a_secret_fails_naming_its_class(tree):
    """REQ-084 AC7: SPEC-0077 rule 9 (answer 7: never the file's text)."""
    product = tree / "evals" / "payments-api" / "product.toml"
    product.write_text("this is = = not toml\n", "utf-8")
    proc = run("check", "--root", str(tree))
    assert proc.returncode == 1
    assert "FAIL evals: product file payments-api: rule 9: not TOML (setting: file)" in (
        proc.stdout.splitlines()
    )
    assert "not toml" not in proc.stdout
    shutil.copy(EVALS / "payments-api" / "product.toml", product)
    token = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
    edit(product, 'problem = "', f'problem = "{token} ')
    proc = run("check", "--root", str(tree))
    assert proc.returncode == 1
    assert "FAIL evals: product file payments-api: rule 9: a line the secret scan flags" in (
        proc.stdout
    )
    assert token not in proc.stdout


def record(n: int, product: str = "booking-web", **over) -> dict:
    data = {
        "product": product,
        "run": n,
        "kit": {"version": "0.66.0", "sha": "abc1234"},
        "tier": "strongest",
        "models": ["model-a"],
        "status": "complete",
        "objective": {"tests_passed": 10, "tests_failed": 0, "accessibility": "not-run"},
        "process": {"questions": 2, "records": 5, "rounds": 1, "minutes": 90},
        "cost": {
            "input": 1000,
            "cache_write": 10,
            "cache_read": 100,
            "output": 50,
            "other": 0,
            "total": 1160,
            "usd": 3.0 * n,
        },
        "review": {layer: n + 2 for layer in LAYERS},
        "accepted": ["AC1", "AC2", "AC3"],
    }
    data.update(over)
    return data


def write_runs(root: Path, records: list[dict]) -> Path:
    for rec in records:
        folder = root / rec["product"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"run-{rec['run']}.json").write_text(json.dumps(rec), "utf-8")
    return root


def test_ac8_the_median_of_three_complete_runs_and_the_cost_per_accepted_feature(tmp_path):
    """REQ-084 AC8: SPEC-0077 rule 9 (answer 3: the median and the cost per accepted feature)."""
    runs = write_runs(tmp_path / "runs", [record(1), record(3), record(2)])
    proc = run("median", str(runs))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = proc.stdout.splitlines()
    assert "booking-web problem 4" in lines and "booking-web code 4" in lines
    assert "booking-web cost per accepted feature 2.00 usd" in lines


def test_ac8_an_incomplete_run_gives_no_median_and_never_0(tmp_path):
    """REQ-084 AC8: SPEC-0077 rule 9 (`Q-PG-3`: incomplete is never scored 0)."""
    stuck = record(3, status="incomplete", stage="scope", review={}, accepted=[])
    runs = write_runs(tmp_path / "runs", [record(1), record(2), stuck])
    proc = run("median", str(runs))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines() == ["booking-web incomplete (2 of 3 runs complete)"]
    assert " 0" not in proc.stdout


def test_ac8_money_not_priced_or_nothing_accepted_is_unknown(tmp_path):
    """REQ-084 AC8: SPEC-0077 rule 9 (a missing figure is `unknown`, never 0)."""
    cost = dict(record(1)["cost"], usd="not priced (setting: cost.prices)")
    runs = write_runs(
        tmp_path / "runs", [record(1, cost=cost), record(2, accepted=[]), record(3, accepted=[])]
    )
    proc = run("median", str(runs))
    assert "booking-web cost per accepted feature unknown" in proc.stdout.splitlines()


@pytest.mark.parametrize(
    ("over", "line"),
    [
        ({"tier": "fast"}, "a value outside its list (setting: tier)"),
        ({"status": "incomplete"}, "a missing key (setting: stage)"),
        ({"stage": "scope"}, "a stage on a complete run (setting: stage)"),
        ({"review": {layer: 7 for layer in LAYERS}}, "a score outside 0 to 6 (setting: review)"),
        ({"accepted": ["AC1", "AC1"]}, "a repeated acceptance id (setting: accepted)"),
        ({"cost": {"input": True}}, "a value of the wrong type (setting: cost.input)"),
        ({"surprise": 1}, "an unknown key (setting: surprise)"),
    ],
)
def test_ac8_a_malformed_run_record_is_refused_naming_its_class(tmp_path, over, line):
    """REQ-084 AC8: SPEC-0077 rule 9 (answer 3: the record form's every part)."""
    base = record(1)
    if "cost" in over:
        over = {"cost": dict(base["cost"], **over["cost"])}
    runs = write_runs(tmp_path / "runs", [record(1, **over), record(2), record(3)])
    proc = run("median", str(runs))
    assert proc.returncode == 1
    assert f"FAIL evals: run record booking-web run-1: rule 9: {line}" in proc.stdout.splitlines()


def test_ac8_a_run_record_that_is_not_json_is_refused_without_its_text(tmp_path):
    """REQ-084 AC8: SPEC-0077 rule 9 (answer 7)."""
    runs = write_runs(tmp_path / "runs", [record(2), record(3)])
    (runs / "booking-web" / "run-1.json").write_text("{secret words", "utf-8")
    proc = run("median", str(runs))
    assert proc.returncode == 1
    assert "FAIL evals: run record booking-web run-1: rule 9: not JSON (setting: file)" in (
        proc.stdout.splitlines()
    )
    assert "secret words" not in proc.stdout


def test_ac8_options_out_of_form_are_refused_with_exit_2(tmp_path):
    """REQ-084 AC8: SPEC-0077 rule 9 (answer 6: the option is named)."""
    proc = run("median", str(tmp_path / "missing"))
    assert proc.returncode == 2
    assert "(option: DIR)" in proc.stderr
    assert run("check", "--root").returncode == 2
    assert run("dance").returncode == 2


def test_ac7_the_script_refuses_outside_the_kit_repository(tmp_path):
    """REQ-084 AC7: SPEC-0077 rule 9 (answer 6: `[kit] layout`, the plugin's copy in a project)."""
    copy = tmp_path / "project" / "scripts" / "agk" / "eval_run.py"
    copy.parent.mkdir(parents=True)
    shutil.copy(SCRIPT, copy)
    for args in (["check"], ["median", str(tmp_path)]):
        proc = run(*args, cwd=tmp_path / "project", script=copy)
        assert proc.returncode == 2
        assert "(path class: evals/)" in proc.stderr


def test_ac7_evals_is_never_installed():
    """REQ-084 AC7: SPEC-0077 rule 9 (answer 1: kit-only, in no installer list)."""
    m = manifest()
    listed = [*m["verbatim"], *m.get("experimental", []), *m["templates"], *m["templates"].values()]
    listed += [*m.get("snapshot", [])]
    assert not [p for p in listed if p.startswith("evals")]
    assert "scripts/agk/eval_run.py" not in m["verbatim"]
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import upgrade

    assert not [p for p in upgrade.installed_set(m, "init")[0] if p.startswith("evals")]


def test_ac7_the_class_stays_closed():
    """REQ-084 AC7: SPEC-0077 rule 9 (answer 9: no check, gate, workflow or step reads it)."""
    pattern = re.compile(r"\beval_run\b|[\"']evals/")
    for path in (KIT_ROOT / "scripts" / "agk").rglob("*.py"):
        if path.name != "eval_run.py":
            assert not pattern.search(path.read_text("utf-8")), path.name
    named = [*(KIT_ROOT / ".github" / "workflows").glob("*.yml"), KIT_ROOT / "agk.mk"]
    for path in named:
        assert "eval_run" not in path.read_text("utf-8"), path.name


def test_ac7_evals_is_a_protected_class():
    """REQ-084 AC7: SPEC-0077 rule 10 (`Q-PG-7`: a rubric change carries an ADR)."""
    lines = (KIT_ROOT / "config" / "protected-paths.txt").read_text("utf-8").splitlines()
    assert "evals/" in lines
    assert "evals/" in (KIT_ROOT / "config" / "reviewers.yaml").read_text("utf-8")
