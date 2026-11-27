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


# Build (b): `eval_run.py run` (brief #2042 answers 4, 5, 6, 7 and 8; ADR-0846 decision 8).

STUB = r"""
import json, os, pathlib, subprocess, sys
prompt = sys.stdin.read()
log = pathlib.Path(os.environ["STUB_LOG"])
names = ("AGK_TIER", "AGK_KIND", "AGK_AGENT", "AGK_MODEL", "GH_TOKEN", "GITHUB_TOKEN", "AGK_HOME",
         "GH_CONFIG_DIR")
seen = {k: os.environ.get(k) for k in names}
seen["data"] = "product file (data)" in prompt
seen["cwd"] = os.getcwd()
with log.open("a", encoding="utf-8") as out:
    out.write(json.dumps(seen) + "\n")
n = len(log.read_text(encoding="utf-8").splitlines())
home = pathlib.Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects" / "p"
home.mkdir(parents=True, exist_ok=True)
usage = {"input_tokens": 100, "output_tokens": 10, "cache_creation_input_tokens": 5,
         "cache_read_input_tokens": 20}
entry = {"type": "assistant", "cwd": os.getcwd(), "sessionId": f"s{n}",
         "message": {"id": f"m{n}", "model": "model-a", "usage": usage}}
(home / f"s{n}.jsonl").write_text(json.dumps(entry) + "\n", encoding="utf-8")
if os.environ["AGK_AGENT"] == "architect-review":
    if os.environ.get("STUB_REVIEW") == "bad":
        pathlib.Path("review.toml").write_text("[[layer\n", encoding="utf-8")
        sys.exit(0)
    rows = "".join(f'[[layer]]\nname = "{x}"\nscore = 4\nreason = "invented"\n\n'
                   for x in ("problem", "scope", "domain-rules", "architecture", "threats", "data",
                             "usability", "code"))
    pathlib.Path("review.toml").write_text('accepted = ["AC1", "AC2"]\n\n' + rows,
                                           encoding="utf-8")
    sys.exit(0)
pathlib.Path("README.md").write_text("invented\n", encoding="utf-8")
git = ["git", "-c", "user.name=e", "-c", "user.email=e@example.invalid", "-c",
       "commit.gpgsign=false"]
subprocess.run([*git, "add", "-A"], check=True)
subprocess.run([*git, "commit", "-qm", "invented", "--no-verify"], check=True)
sys.exit(3 if os.environ.get("STUB_FAIL") == str(n) else 0)
"""
BLOCK = (
    "import socket\n\n\nclass _Blocked(socket.socket):\n"
    "    def __init__(self, *a, **k):\n        raise OSError('network blocked')\n\n\n"
    "def _no(*a, **k):\n    raise OSError('network blocked')\n\n\n"
    "socket.socket = _Blocked\nsocket.create_connection = _no\n"
)
GH = '#!/bin/sh\necho called >> "$GH_LOG"\nexit 1\n'


@pytest.fixture
def stub(tmp_path: Path) -> dict:
    """A stub adapter, a recording `gh` on PATH, a blocked socket module and a scratch home."""
    (tmp_path / "bin").mkdir()
    (tmp_path / "stub.py").write_text(STUB, "utf-8")
    (tmp_path / "bin" / "gh").write_text(GH, "utf-8")
    (tmp_path / "bin" / "gh").chmod(0o755)
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "sitecustomize.py").write_text(BLOCK, "utf-8")
    (tmp_path / "said.txt").write_text("Yes\n", "utf-8")
    env = {
        "PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin",
        "HOME": str(tmp_path / "home"),
        "CLAUDE_CONFIG_DIR": str(tmp_path / "claude"),
        "PYTHONPATH": str(tmp_path / "site"),
        "STUB_LOG": str(tmp_path / "stub.log"),
        "GH_LOG": str(tmp_path / "gh.log"),
        "GH_TOKEN": "invented-value",
        "GITHUB_TOKEN": "invented-value",
    }
    return {"root": tmp_path, "env": env}


def run_eval(stub: dict, *more: str, **env: str) -> subprocess.CompletedProcess:
    root = stub["root"]
    given = {
        "--product": "booking-web",
        "--adapter": f"{sys.executable} {root / 'stub.py'}",
        "--said": str(root / "said.txt"),
        "--at": "2026-11-27T19:30:00Z",
        "--out": str(root / "out"),
    }
    given.update(zip(more[0::2], more[1::2], strict=True))  # an option given replaces its default
    args = ["run", *(x for pair in given.items() for x in pair)]
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env={**stub["env"], **env},
    )


def stub_calls(stub: dict) -> list[dict]:
    log = stub["root"] / "stub.log"
    if not log.is_file():
        return []
    return [json.loads(x) for x in log.read_text("utf-8").splitlines()]


def test_ac8_run_writes_three_records_with_no_github_call(stub):
    """REQ-084 AC8: SPEC-0077 rule 9 (answers 4 and 5: three runs, each with a fresh review)."""
    proc = run_eval(stub)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = stub["root"] / "out"
    records = [json.loads((out / "booking-web" / f"run-{n}.json").read_text()) for n in (1, 2, 3)]
    assert [r["status"] for r in records] == ["complete"] * 3
    assert all(r["tier"] == "strongest" and r["models"] == ["model-a"] for r in records)
    assert records[0]["accepted"] == ["AC1", "AC2"]
    assert records[0]["review"] == {layer: 4 for layer in LAYERS}
    cost = records[0]["cost"]
    assert (cost["input"], cost["output"], cost["cache_write"], cost["cache_read"]) == (
        200,
        20,
        10,
        40,
    )
    assert cost["usd"] == "not priced (setting: cost.prices)"  # the kit has no [cost] table
    assert records[0]["objective"]["accessibility"] == "not-run"
    assert records[0]["objective"]["tests"] == "not-run (setting: personal.test_command)"
    calls = stub_calls(stub)
    assert len(calls) == 6
    builds, reviews = calls[0::2], calls[1::2]
    assert all(c["AGK_TIER"] == "strongest" and c["data"] for c in calls)
    assert all(c["GH_TOKEN"] is None and c["GITHUB_TOKEN"] is None for c in calls)
    assert all(c["AGK_MODEL"] is None for c in calls)  # the kit sets no [models.names] strongest
    assert [c["AGK_AGENT"] for c in reviews] == ["architect-review"] * 3
    assert all(c["AGK_KIND"] == "build" and c["cwd"].endswith("product") for c in builds)
    assert all(not c["cwd"].endswith("product") for c in reviews)
    assert all(Path(c["GH_CONFIG_DIR"]).is_dir() for c in calls)
    assert not (stub["root"] / "gh.log").exists()
    assert run("median", str(out)).returncode == 0


def test_ac8_a_failed_run_or_review_is_incomplete_and_the_next_run_starts(stub):
    """REQ-084 AC8: SPEC-0077 rule 9 (answers 5 and 7: incomplete, never 0)."""
    proc = run_eval(stub, STUB_FAIL="3")  # the second run's build session (calls 1, 2, then 3)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    folder = stub["root"] / "out" / "booking-web"
    second = json.loads((folder / "run-2.json").read_text())
    assert second["status"] == "incomplete" and second["review"] == {}
    assert json.loads((folder / "run-3.json").read_text())["status"] == "complete"
    shown = run("median", str(stub["root"] / "out"))
    assert shown.stdout.splitlines() == ["booking-web incomplete (2 of 3 runs complete)"]


def test_ac8_a_malformed_review_leaves_the_run_incomplete_at_review(stub):
    """REQ-084 AC8: SPEC-0077 rule 9 (answer 5: a malformed review is never scored 0)."""
    proc = run_eval(stub, STUB_REVIEW="bad")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads((stub["root"] / "out" / "booking-web" / "run-1.json").read_text())
    assert (rec["status"], rec["stage"], rec["review"]) == ("incomplete", "review", {})


def test_ac8_an_adapter_that_cannot_start_is_incomplete(stub):
    """REQ-084 AC8: SPEC-0077 rule 9 (answer 7)."""
    root = stub["root"]
    args = ["--adapter", str(root / "missing-adapter")]
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "run", "--product", "payments-api", *args]
        + ["--said", str(root / "said.txt"), "--at", "2026-11-27T19:30:00Z"]
        + ["--out", str(root / "out")],
        capture_output=True,
        text=True,
        check=False,
        env=stub["env"],
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    for n in (1, 2, 3):
        rec = json.loads((root / "out" / "payments-api" / f"run-{n}.json").read_text())
        assert rec["status"] == "incomplete" and rec["cost"]["total"] == "unknown"


@pytest.mark.parametrize(
    ("more", "env", "line", "code"),
    [
        ((), {"CI": "true"}, "(setting: CI)", 2),
        ((), {"GITHUB_ACTIONS": "true"}, "(setting: CI)", 2),
        (("--minutes", "0"), {}, "(option: --minutes)", 2),
        (("--minutes", "601"), {}, "(option: --minutes)", 2),
        (("--at", "yesterday"), {}, "(option: --at)", 2),
        (("--product", "spaceship"), {}, "(option: --product)", 2),
        (("--product", "../evals"), {}, "(option: --product)", 2),
        (("--adapter", ""), {}, "(option: --adapter)", 2),
        (("--colour", "red"), {}, "(option: --colour)", 2),
        (("--out", str(KIT_ROOT / "build")), {}, "(path class: the kit's work tree)", 2),
        (("--said", "/nonexistent/said.txt"), {}, "(option: --said)", 2),
    ],
)
def test_ac8_run_refusals_name_the_option_or_setting_and_start_nothing(stub, more, env, line, code):
    """REQ-084 AC8: SPEC-0077 rule 9 (answer 6: each option and setting, nothing started)."""
    proc = run_eval(stub, *more, **env)
    assert proc.returncode == code, proc.stdout + proc.stderr
    assert line in proc.stderr
    assert stub_calls(stub) == [] and not (stub["root"] / "out").exists()


def test_ac8_run_without_a_yes_starts_nothing_and_writes_nothing(stub):
    """REQ-084 AC8: SPEC-0077 rule 9 (`Q-PG-5`: the person's yes in `--said`)."""
    (stub["root"] / "said.txt").write_text("maybe later\n", "utf-8")
    proc = run_eval(stub)
    assert proc.returncode == 1
    assert "(option: --said)" in proc.stderr
    assert stub_calls(stub) == [] and not (stub["root"] / "out").exists()


def test_ac8_in_team_mode_only_a_spec_approver_yes_starts_a_run(stub, monkeypatch, capsys):
    """REQ-084 AC8: SPEC-0077 rule 9 (answer 6: `review_mode = "team"`, `spec_approvers`)."""
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import eval_run
    import reviewers
    import steward_owner

    monkeypatch.setattr(steward_owner, "review_mode", lambda root: "team")
    monkeypatch.setattr(reviewers, "spec_approvers", lambda root: ["approver-a"])
    for key in ("CI", "GITHUB_ACTIONS"):
        monkeypatch.delenv(key, raising=False)
    root = stub["root"]
    argv = ["run", "--product", "booking-web", "--adapter", f"{sys.executable} {root / 'stub.py'}"]
    argv += ["--said", str(root / "said.txt"), "--at", "2026-11-27T19:30:00Z"]
    argv += ["--out", str(root / "out"), "--by", "someone-else"]
    assert eval_run.main(argv) == 2
    assert "(setting: spec_approvers)" in capsys.readouterr().err
    assert stub_calls(stub) == [] and not (root / "out").exists()


def test_ac8_the_cost_is_priced_by_kind_and_a_reply_of_another_model_fails_the_tier():
    """REQ-084 AC8: SPEC-0077 rule 9 (answer 6: `[cost] prices`; answer 7 and `Q-PG-8`)."""
    from decimal import Decimal

    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import eval_run

    tokens = {"input": 1_000_000, "output": 1_000_000, "cache_write": 0, "cache_read": 0}
    replies = [{"model": "model-a", "tokens": tokens}]
    prices = {"model-a": {"input": Decimal("1"), "output": Decimal("2")}}
    cost = eval_run.cost_of(replies, prices)
    assert cost["usd"] == 3.0 and cost["total"] == 2_000_000 and cost["other"] == "unknown"
    assert eval_run.cost_of(replies, {})["usd"] == "not priced (setting: cost.prices)"
    assert eval_run.cost_of([], prices)["input"] == "unknown"
    missing = [{"model": "model-a", "tokens": dict(tokens, output=None)}]
    assert eval_run.cost_of(missing, prices)["usd"] == "unknown"
    assert eval_run.tier_ok(["model-a"], "model-a")
    assert not eval_run.tier_ok(["model-a", "model-b"], "model-a")
    assert eval_run.tier_ok(["model-a", "model-b"], None)  # unset: recorded, `(verify)`
