"""Tests of `check_playbooks.py` (SPEC-0038 rules 1 to 4; REQ-045 AC1 and AC4).

A playbook under `config/playbooks/<work type>.toml` is checked data: a missing or unknown section
or key, a wrong type, an unknown work type, a name that differs from `work_type`, a phase cycle, an
unknown lane kind, a check gate without a step, a claim with no basis or a `measured` claim whose
record is missing fails (rules 1 to 3); a playbook that could lower a gate fails as well (rule 4).
Every failure names the rule and the file and never the value. Fixtures in `tmp_path` only:
invented data, no network.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "agk" / "check_playbooks.py"
REL = "config/playbooks/web-app.toml"

FULL = """format = 1
work_type = "web-app"
title = "Contract first, then mocks, then both sides in parallel, then joins"
heavy_steps = ["smoke run"]
evidence = ["the smoke run record", "the contract test output"]

[[phases]]
name = "contract"
order = 1
after = []

[[phases]]
name = "mocks"
order = 2
after = ["contract"]

[[phases]]
name = "front-end"
order = 3
after = ["mocks"]

[[phases]]
name = "back-end"
order = 3
after = ["mocks"]

[[phases]]
name = "joins"
order = 4
after = ["front-end", "back-end"]

[split]
brief_order = ["contract", "mock", "front", "back", "join"]
depends_on = [["mock", "contract"], ["front", "mock"], ["back", "mock"], ["join", "front"]]

[[lanes]]
name = "front lane"
kinds = ["front"]

[[lanes]]
name = "back lane"
kinds = ["back"]

[testing]
profile = "balanced"
always_full = ["contract/**"]
map = [{ code = "app/web/**", tests = "tests/web/**" }]

[[gates]]
id = "contract-tests"
kind = "check"
text = "Every contract path has a mapped test glob"
step = "check_contract_map"
owner_only = false

[[gates]]
id = "smoke"
kind = "judgement"
text = "Test execution is recorded for each merge batch"
owner_only = false

[[gates]]
id = "publish"
kind = "judgement"
text = "The owner signs and makes the release"
owner_only = true

[milestones]
shape = "per-batch"
batch_by = "demo value"

[[claims]]
text = "The critical path is shorter than one flow for every kind"
basis = "expected"

[[claims]]
text = "Parallel lanes cut the wait for joins"
basis = "measured"
record = "docs/runs/2026-11-01-example.md"
"""


def clean_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}


def write(root: Path, text: str = FULL, rel: str = REL, record: bool = True) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if record:
        runs = root / "docs" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        (runs / "2026-11-01-example.md").write_text("# a run record\n", encoding="utf-8")
    return path


def check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 - fixed argument list
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
        env=clean_env(),
        check=False,
    )


def assert_fails(root: Path, rule: int, value: str | None = None, rel: str = REL) -> str:
    result = check(root)
    out = result.stdout + result.stderr
    assert result.returncode == 1, out
    fails = [ln for ln in out.splitlines() if ln.startswith("FAIL playbooks:")]
    assert fails, out
    assert any(f"rule {rule}" in ln and rel in ln for ln in fails), out
    if value is not None:
        assert value not in out, out
    return out


def replace(old: str, new: str, text: str = FULL) -> str:
    assert old in text, old
    return text.replace(old, new, 1)


def test_ac1_a_full_playbook_passes(tmp_path):
    """REQ-045 AC1: SPEC-0038 rules 1 to 3 (every section of the format, a known work type)."""
    write(tmp_path)
    result = check(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "ok playbooks (1 playbooks)"


def test_ac1_an_absent_folder_prints_none(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 4 (a project with no playbook passes and says so)."""
    result = check(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "ok playbooks (none)"


def test_ac1_the_repository_itself_passes():
    """REQ-045 AC1: SPEC-0038 rule 4 (the step of agk-governance passes on this repository)."""
    result = check(KIT_ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("ok playbooks")


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('[milestones]\nshape = "per-batch"\nbatch_by = "demo value"\n', ""),
        ('heavy_steps = ["smoke run"]\n', ""),
        ('title = "Contract first, then mocks, then both sides in parallel, then joins"\n', ""),
    ],
    ids=["section", "list", "key"],
)
def test_ac1_a_missing_section_fails(tmp_path, old, new):
    """REQ-045 AC1: SPEC-0038 rule 2 (each section and key is required)."""
    write(tmp_path, replace(old, new))
    assert_fails(tmp_path, 2)


@pytest.mark.parametrize(
    ("old", "new", "value"),
    [
        ("format = 1\n", 'format = 1\nnotes = "zz-extra-key"\n', "zz-extra-key"),
        ("[milestones]\n", '[zzsection]\nkey = "zz-extra-value"\n\n[milestones]\n', "zzsection"),
        ('batch_by = "demo value"\n', 'batch_by = "demo value"\nzz_merge = true\n', "zz_merge"),
    ],
    ids=["top-level", "section", "in-section"],
)
def test_ac1_an_unknown_key_fails(tmp_path, old, new, value):
    """REQ-045 AC1 and AC4: SPEC-0038 rules 2 and 4 (no key outside the format)."""
    write(tmp_path, replace(old, new))
    out = assert_fails(tmp_path, 4)
    assert "rule 2" in out
    assert value not in out


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("format = 1\n", 'format = "1"\n'),
        ("order = 1\n", 'order = "first"\n'),
        ('kinds = ["front"]\n', 'kinds = "front"\n'),
        ("owner_only = true\n", 'owner_only = "yes"\n'),
        ('always_full = ["contract/**"]\n', 'always_full = "contract/**"\n'),
    ],
    ids=["format", "order", "kinds", "owner_only", "always_full"],
)
def test_ac1_a_wrong_type_fails(tmp_path, old, new):
    """REQ-045 AC1: SPEC-0038 rule 2 (every key has its type)."""
    write(tmp_path, replace(old, new))
    assert_fails(tmp_path, 2)


def test_ac1_a_format_other_than_one_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 2 (`format = 1`)."""
    write(tmp_path, replace("format = 1\n", "format = 7\n"))
    assert_fails(tmp_path, 2)


def test_ac1_an_unknown_work_type_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 1 (the work types are a fixed list)."""
    rel = "config/playbooks/zz-kiosk.toml"
    write(tmp_path, replace('work_type = "web-app"', 'work_type = "zz-kiosk"'), rel=rel)
    out = assert_fails(tmp_path, 1, rel=rel)
    assert '"zz-kiosk"' not in out and "= zz-kiosk" not in out


def test_ac1_a_name_that_differs_from_work_type_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 1 (the file's name and its `work_type` are the same)."""
    write(tmp_path, replace('work_type = "web-app"', 'work_type = "rag-app"'))
    assert_fails(tmp_path, 1, "rag-app")


def test_ac1_a_file_that_is_not_toml_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 1 (a playbook is TOML read with tomllib)."""
    write(tmp_path, FULL + "\nzz broken = = \n")
    assert_fails(tmp_path, 1)


def test_ac1_a_phase_cycle_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 2 (the phase graph has no cycle)."""
    text = replace(
        'name = "contract"\norder = 1\nafter = []',
        'name = "contract"\norder = 1\nafter = ["joins"]',
    )
    write(tmp_path, text)
    assert_fails(tmp_path, 2, "joins")


def test_ac1_a_phase_after_an_unknown_phase_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 2 (`after` names known phases)."""
    write(tmp_path, replace('after = ["contract"]', 'after = ["zz-phase"]'))
    assert_fails(tmp_path, 2, "zz-phase")


def test_ac1_an_unknown_lane_kind_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 2 (a lane's kinds are within `brief_order`)."""
    write(tmp_path, replace('kinds = ["front"]', 'kinds = ["zz-kind"]'))
    assert_fails(tmp_path, 2, "zz-kind")


def test_ac1_an_unknown_split_kind_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 2 (a `depends_on` kind is within `brief_order`)."""
    write(tmp_path, replace('["join", "front"]', '["join", "zz-kind"]'))
    assert_fails(tmp_path, 2, "zz-kind")


def test_ac1_an_unknown_milestone_shape_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 2 (`shape` is per-brief, per-phase or per-batch)."""
    write(tmp_path, replace('shape = "per-batch"', 'shape = "zz-shape"'))
    assert_fails(tmp_path, 2, "zz-shape")


def test_ac1_an_unknown_gate_kind_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 2 (a gate is `check` or `judgement`)."""
    write(
        tmp_path,
        replace('kind = "judgement"\ntext = "The owner', 'kind = "zz-kind"\ntext = "The owner'),
    )
    assert_fails(tmp_path, 2, "zz-kind")


def test_ac1_a_check_gate_without_a_step_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 2 (a check gate names its governance step)."""
    write(tmp_path, replace('step = "check_contract_map"\n', ""))
    assert_fails(tmp_path, 2)


def test_ac1_a_claim_with_no_basis_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 3 (every claim is measured or expected)."""
    write(tmp_path, replace('basis = "expected"\n', ""))
    assert_fails(tmp_path, 3)


def test_ac1_a_claim_with_another_basis_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 3 (no basis but measured or expected)."""
    write(tmp_path, replace('basis = "expected"', 'basis = "zz-proven"'))
    assert_fails(tmp_path, 3, "zz-proven")


def test_ac1_a_measured_claim_with_a_missing_record_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 3 (the record file under docs/runs/ exists)."""
    write(tmp_path, record=False)
    assert_fails(tmp_path, 3, "2026-11-01-example.md")


def test_ac1_a_measured_claim_with_no_record_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 3 (a measured claim names its record)."""
    write(tmp_path, replace('record = "docs/runs/2026-11-01-example.md"\n', ""))
    assert_fails(tmp_path, 3)


def test_ac1_a_measured_record_outside_docs_runs_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 3 (the record is a file under `docs/runs/`)."""
    (tmp_path / "zz-outside.md").write_text("x\n", encoding="utf-8")
    write(
        tmp_path, replace('record = "docs/runs/2026-11-01-example.md"', 'record = "zz-outside.md"')
    )
    assert_fails(tmp_path, 3, "zz-outside.md")


def test_ac1_a_measured_record_that_climbs_out_of_docs_runs_fails(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 3 (`..` never leaves `docs/runs/`)."""
    (tmp_path / "zz-outside.md").write_text("x\n", encoding="utf-8")
    write(
        tmp_path,
        replace(
            'record = "docs/runs/2026-11-01-example.md"', 'record = "docs/runs/../../zz-outside.md"'
        ),
    )
    assert_fails(tmp_path, 3, "zz-outside.md")


def test_ac4_a_fast_profile_fails(tmp_path):
    """REQ-045 AC4: SPEC-0038 rule 4 (`profile = "fast"` would only list unmapped files)."""
    write(tmp_path, replace('profile = "balanced"', 'profile = "fast"'))
    assert_fails(tmp_path, 4, "fast")


def test_ac4_a_pr_tests_key_fails(tmp_path):
    """REQ-045 AC4: SPEC-0038 rule 4 (a `pr_tests` key)."""
    write(
        tmp_path, replace('profile = "balanced"\n', 'profile = "balanced"\npr_tests = "selected"\n')
    )
    assert_fails(tmp_path, 4, "selected")


def test_ac4_a_top_level_key_that_skips_a_step_fails(tmp_path):
    """REQ-045 AC4: SPEC-0038 rule 4 (no key can name a governance step to skip)."""
    write(tmp_path, replace("format = 1\n", 'format = 1\nskip = ["zz_step_name"]\n'))
    assert_fails(tmp_path, 4, "zz_step_name")


@pytest.mark.parametrize(
    "text",
    [
        "Set `required_checks` to fewer names",
        "required_checks = [] for this kind",
        "required_checks: none",
        "Use `paused` while the batch runs",
        "review_mode = solo for joins",
        "`execution` runs on the host",
        "ac_coverage: off",
        "`agent_apps` may merge",
        "pr_mode = flow",
        "`pr_tests`",
    ],
)
def test_ac4_a_governance_setting_named_as_a_setting_fails(tmp_path, text):
    """REQ-045 AC4: SPEC-0038 rule 4 (a backticked token, `<setting> =` or `<setting>:`)."""
    write(tmp_path, replace("Every contract path has a mapped test glob", text))
    assert_fails(tmp_path, 4, text)


def test_ac4_a_setting_named_in_a_nested_value_fails(tmp_path):
    """REQ-045 AC4: SPEC-0038 rule 4 (in any of its values, a list or a table as well)."""
    write(
        tmp_path,
        replace('evidence = ["the smoke run record"', 'evidence = ["`required_checks` trimmed"'),
    )
    assert_fails(tmp_path, 4)
    write(tmp_path, replace('tests = "tests/web/**"', 'tests = "pr_tests: none"'))
    assert_fails(tmp_path, 4)


def test_ac4_a_principle_set_aside_fails(tmp_path):
    """REQ-045 AC4: SPEC-0038 rule 4 (a principle or a session rule to set aside)."""
    write(
        tmp_path,
        replace("Every contract path has a mapped test glob", "Set aside principle 11 for joins"),
    )
    assert_fails(tmp_path, 4)
    write(
        tmp_path,
        replace("Every contract path has a mapped test glob", "session rule 31 is skipped here"),
    )
    assert_fails(tmp_path, 4)


@pytest.mark.parametrize(
    "text",
    [
        "The owner signs the store build",
        "Apply the infrastructure plan",
        "Cut the release",
        "Rotate the secret",
    ],
)
def test_ac4_an_owner_action_with_owner_only_false_fails(tmp_path, text):
    """REQ-045 AC4: SPEC-0038 rule 4 (signing, an infrastructure apply, a release or a secret)."""
    write(
        tmp_path,
        replace(
            'The owner signs and makes the release"\nowner_only = true',
            text + '"\nowner_only = false',
        ),
    )
    assert_fails(tmp_path, 4)


@pytest.mark.parametrize(
    "text",
    [
        "Test execution is recorded for each merge batch",
        "A paused pipeline resumes after the smoke run",
        "Required checks stay as they are",
        "Review mode is the owner's choice",
    ],
)
def test_ac4_the_same_word_in_plain_english_passes(tmp_path, text):
    """REQ-045 AC4: SPEC-0038 rule 4 (a plain word is not a setting named as one)."""
    write(tmp_path, replace("Every contract path has a mapped test glob", text))
    result = check(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_ac4_every_problem_is_one_fail_line(tmp_path):
    """REQ-045 AC4: SPEC-0038 rule 4 (one FAIL line per problem, exit 1)."""
    text = replace('profile = "balanced"', 'profile = "fast"')
    text = replace('basis = "expected"\n', "", text)
    write(tmp_path, text)
    result = check(tmp_path)
    fails = [ln for ln in result.stdout.splitlines() if ln.startswith("FAIL playbooks:")]
    assert result.returncode == 1
    assert len(fails) == 2, result.stdout
    assert not result.stdout.startswith("ok")


def test_ac1_two_playbooks_are_counted(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 1 (every `config/playbooks/*.toml` is checked)."""
    write(tmp_path)
    write(
        tmp_path,
        replace('work_type = "web-app"', 'work_type = "rag-app"'),
        rel="config/playbooks/rag-app.toml",
    )
    result = check(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "ok playbooks (2 playbooks)"


# --- where the reader lives and how governance runs it (rulings on Q-513-1 and Q-513-2) ----------

MODULE = KIT_ROOT / "scripts" / "agk" / "playbook_format.py"
EIGHT = (
    "web-app",
    "mobile",
    "cloud-migration",
    "rag-app",
    "mcp-server",
    "multi-agent",
    "voice-agent",
    "pilot",
)


def load_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("playbook_format_under_test", MODULE)
    assert spec and spec.loader, MODULE
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ac1_the_format_module_holds_the_work_types_and_the_format():
    """REQ-045 AC1: SPEC-0038 rules 1 and 2 (one constant of the eight work types, `FORMAT = 1`)."""
    module = load_module()
    assert tuple(module.WORK_TYPES) == EIGHT
    assert module.FORMAT == 1


def test_ac1_problems_reads_one_playbook(tmp_path):
    """REQ-045 AC1: SPEC-0038 rules 1 to 4 (`problems(path, root)` returns one line per problem)."""
    module = load_module()
    path = write(tmp_path)
    assert module.problems(path, tmp_path) == []
    path.write_text(replace('profile = "balanced"', 'profile = "fast"'), encoding="utf-8")
    found = module.problems(path, tmp_path)
    assert len(found) == 1 and "rule 4" in found[0] and REL in found[0], found
    assert all(isinstance(line, str) for line in found)


def test_ac1_every_shipped_work_type_is_a_valid_file_name(tmp_path):
    """REQ-045 AC1: SPEC-0038 rule 1 (each of the eight work types passes as its own file)."""
    for work_type in EIGHT:
        write(
            tmp_path,
            replace('work_type = "web-app"', f'work_type = "{work_type}"'),
            rel=f"config/playbooks/{work_type}.toml",
        )
    result = check(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "ok playbooks (8 playbooks)"


def test_ac1_both_scripts_are_installed_and_the_start_helper_stays_kit_only():
    """REQ-045 AC1: SPEC-0038 rule 12 (a), ruling on Q-513-1 (`playbook.py` is not installed)."""
    import json

    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    verbatim = manifest["verbatim"]
    assert "scripts/agk/playbook_format.py" in verbatim
    assert "scripts/agk/check_playbooks.py" in verbatim
    assert "scripts/agk/playbook.py" not in verbatim
    assert verbatim == sorted(verbatim)


def test_ac4_the_check_runs_in_governance_after_the_design_check():
    """REQ-045 AC4: SPEC-0038 rule 4 (one line of `agk-governance`, after `check_design.py`)."""
    mk = (KIT_ROOT / "agk.mk").read_text(encoding="utf-8")
    recipe = mk.split("agk-governance:\n", 1)[1].split("\n\n", 1)[0]
    lines = [ln.strip() for ln in recipe.splitlines()]
    design = lines.index("$(PY) scripts/agk/check_design.py")
    assert lines[design + 1] == "$(PY) scripts/agk/check_playbooks.py"


def test_ac4_the_workflow_runs_the_check_as_its_own_step():
    """REQ-045 AC4: ruling on Q-513-2 (the `check_playbooks` step follows `check_design`)."""
    text = (KIT_ROOT / ".github" / "workflows" / "governance.yml").read_text(encoding="utf-8")
    design = text.index("      - name: check_design\n")
    step = text.index("      - name: check_playbooks\n")
    assert design < step
    block = text[step:].split("\n      - ", 1)[0]
    assert "run: python scripts/agk/check_playbooks.py" in block
    assert "steps.paused.outputs.paused != 'true'" in block
