"""`/agk:ground`: the rule set grounded by the existing tools (brief #2094, ADR-0875; REQ-037).

The skill builds no measure and no cutter: it names `rules.py`, `core_audit.py`, `metrics.py`, the
drift audit and the steward's commands, sorts every rule into five classes and cuts only by a plan the
owner said yes to, applied by `rules.py consolidate --apply`. These tests hold its front matter, the
commands it names, the steward's guard on every form of them, its row of the steward's table, a plan
written as it says on an invented tree, the kit-finding split in a project and its signal of use.
Invented data only (example.com); no network, no model.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "ground" / "SKILL.md"
sys.path.insert(0, str(ROOT / "scripts" / "agk"))
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))

from test_guard_plugin_forms import CLEAN, allowed, decision, make_project  # noqa: E402
from test_metrics_signals import MIXED, Recorder  # noqa: E402
from test_metrics_signals import lines as signal_section  # noqa: E402
from test_metrics_signals import project as signals_project  # noqa: E402
from test_rules_consolidate import git, plan_hash, run, write  # noqa: E402
from test_rules_consolidate import project as rules_project  # noqa: E402

CALL = re.compile(r'^\s*python3 "\$\{CLAUDE_PLUGIN_ROOT\}/scripts/agk/(\w+\.py)"(.*)$', re.M)
KIT_CALL = re.compile(r"^\s*python3 scripts/agk/(\w+\.py)(.*)$", re.M)
CLASSES = ("checkable", "judgement", "duplicate", "unused", "contradicting")
NAMED = (
    '/rules.py" budget',
    '/rules.py" consolidate --plan',
    '/rules.py" dropped --since',
    '/rules.py" consolidate --plan --root',
    '/rules.py" consolidate --apply --hash',
    "python3 scripts/agk/core_audit.py --since",
    '/metrics.py" --signals',
    "agk-drift-audit",
    "`EXPECTED`",
    '/steward_owner.py" ask',
    '/steward_owner.py" park',
    '/steward_owner.py" file-brief',
    '/steward_evidence.py" triage',
    '/steward.py" record --kind Note',
    "config/rule-plan.txt",
    "kit/manifest.json",
)


def text() -> str:
    return SKILL.read_text(encoding="utf-8")


def calls() -> list[tuple[str, str]]:
    return [(m[1], m[2].strip()) for m in CALL.finditer(text())]


def test_req037_the_skill_has_its_front_matter_and_the_licence():
    head, _, body = text().partition("---\n")[2].partition("---\n")
    fields = dict(line.split(": ", 1) for line in head.strip().splitlines())
    assert fields["name"] == "ground"
    assert fields["description"] and "\n" not in fields["description"]
    assert fields["disable-model-invocation"] == "true"
    assert "SPDX-License-Identifier: LicenseRef-AGK-Proprietary" in body.split("-->")[0]
    assert "# /agk:ground" in body


def test_req037_the_skill_names_each_existing_command_and_the_five_classes():
    body = text()
    for named in NAMED:
        assert named in body, named
    for name in CLASSES:
        assert f"**{name}**" in body, name
    # core_audit.py is kit-only (config/kit-only.txt, Q-680-6): no plugin form reaches a project
    assert "${CLAUDE_PLUGIN_ROOT}/scripts/agk/core_audit.py" not in body
    assert "cannot-check (kit-only: core_audit)" in body
    for script, _ in calls() + [(m[1], "") for m in KIT_CALL.finditer(body)]:
        assert (ROOT / "scripts" / "agk" / script).is_file(), script


@pytest.mark.parametrize("layout", ["installed", "plugin"])
def test_req037_the_steward_guard_allows_every_command_the_skill_names(tmp_path, layout):
    root = make_project(tmp_path, "" if layout == "installed" else CLEAN, layout == "installed")
    found = calls()
    assert len(found) >= 12
    for script, args in found:
        if layout == "installed":
            (root / "scripts" / "agk" / script).write_text("print('x')\n", encoding="utf-8")
            command = f"python3 scripts/agk/{script} {args}"
        else:
            command = f'python3 "{ROOT}/scripts/agk/{script}" {args}'
        assert allowed(decision("steward_guard.py", root, command)), (layout, command)


def test_req037_the_stewards_table_names_the_skill_for_the_step():
    from steward_evidence import skill_line

    assert skill_line(ROOT, "grounding the rules") == "skill: `ground`"


def test_req037_a_plan_written_as_the_skill_says_lowers_the_counts(tmp_path):
    """Steps 3 and 5: the rows in the plan's own format, `--plan` twice gives one hash, `--apply`."""
    plan = "# grounding 2026-11-28\nconfig/session-rules.md 2 retire scripts/agk/check_x.py\n"
    root = rules_project(tmp_path, plan=plan)
    first, second = run(root, "--plan"), run(root, "--plan")
    assert first.returncode == 0, first.stdout + first.stderr
    assert plan_hash(first.stdout) == plan_hash(second.stdout)
    counts = {x.split(":")[0]: x for x in first.stdout.splitlines() if x[:7] in ("before:", "after: ")}
    words = {k: int(re.search(r"(\d+) words", v)[1]) for k, v in counts.items()}
    assert words["after"] < words["before"]
    applied = run(root, "--apply", "--hash", plan_hash(first.stdout))
    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert "2. Retired: enforced by `scripts/agk/check_x.py`" in (
        root / "config" / "session-rules.md"
    ).read_text(encoding="utf-8")


def test_req037_a_moved_branch_changes_the_hash_and_apply_refuses_it(tmp_path):
    """Answer 5: the default branch moves between packet and apply."""
    plan = "config/session-rules.md 2 retire scripts/agk/check_x.py\n"
    root = rules_project(tmp_path, plan=plan)
    old = plan_hash(run(root, "--plan").stdout)
    write(root, "config/rule-plan.txt", plan + "config/session-rules.md 3 guide\n")
    git(root, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qam", "moved")
    assert plan_hash(run(root, "--plan").stdout) != old
    assert run(root, "--apply", "--hash", old).returncode != 0


def test_req037_in_a_project_a_row_on_a_kit_file_is_a_kit_finding(tmp_path):
    """Answer 4: the files the plugin's kit/manifest.json lists go to the kit by triage."""
    from steward_guard import kit_paths

    root = make_project(tmp_path, CLEAN)
    listed = kit_paths(str(root))[0]
    rows = ["config/session-rules.md 2 guide", "docs/rules/team.md 1 guide"]
    kit = [r for r in rows if r.split()[0] in listed]
    assert kit == ["config/session-rules.md 2 guide"]
    assert "agk-kit-defect" in text() and "verbatim" in text()


def test_req037_the_signal_of_use_is_a_comment_row_of_the_note(tmp_path):
    import metrics

    rows = tomllib.loads((ROOT / "config" / "signals.toml").read_text(encoding="utf-8"))["signal"]
    row = next(r for r in rows if r["id"] == "ground-run")
    assert (row["feature"], row["kind"]) == ("ADR-0875", "comment")
    pattern = re.compile(row["pattern"])
    note = "Note: grounding 2026-11-28: 15691 to 15100 words, 194 to 180 rule lines"
    assert pattern.search(note) and not pattern.search("Note: a grounding wire")
    assert note.split(": ", 1)[1].startswith("grounding") and "Note: grounding <date>" in text()
    out = signal_section(signals_project(tmp_path), Recorder(MIXED))
    assert not out[0].startswith("signals: refused")
    assert metrics.SIGNAL_KINDS[1] == "comment"


def test_req037_no_kit_script_but_rules_py_writes_the_plan():
    """Answer 7: the class stays closed."""
    namers = sorted(
        p.relative_to(ROOT).as_posix()
        for folder in ("scripts", ".claude/hooks")
        for p in (ROOT / folder).rglob("*.py")
        if "rule-plan.txt" in p.read_text(encoding="utf-8")
    )
    assert namers == ["scripts/agk/rules.py"]

