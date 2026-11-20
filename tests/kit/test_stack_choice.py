"""Kit tests: the stack choice for a business person (brief #1591, ADR-0671, amendment 199).

A Proposed stack record gives each option its cost, build speed, security and uptime in plain
words and marks one option `(recommended)` with a `Why:`; `stack-write` writes the kit's default
for the declared work type as Option A; `stack-accept` makes the accepting change in the two
commits of `skills/stack/SKILL.md` step 4. Accepted records written before this change still pass.
Invented records under a temporary root (example.com); local git only, no network.
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
ENGINES = KIT_ROOT / "scripts" / "agk" / "engines.py"
DEFAULTS = KIT_ROOT / "config/stack-defaults.toml"
SIGNALS = KIT_ROOT / "config" / "stack-signals.toml"
STACK = "docs/adr/0002-stack-options.md"
EFFECTS = (
    "Cost: one small server, a low monthly cost; Build speed: quick, one program; "
    "Security: one sign-in in front of the data; Uptime: a short pause on a restart."
)
OPTION_A = (
    f"   - Option A — one web application (recommended). Trade-offs: {EFFECTS} "
    "Why: the busiest hour is small and an hour of downtime a month is allowed. "
    "Parts: a 1.0 MIT. Practices: pinned actions, test selection.\n"
)
OPTION_B = (
    f"   - Option B — a hosted service at example.com. Trade-offs: {EFFECTS} "
    "Parts: a 1.0 MIT. Practices: pinned actions, test selection.\n"
)
SELECTION = (
    "test selection: judgement (Option A: profile fast, always_full `app/auth/**`; "
    "Option B: profile thorough, always_full `src/**`)"
)


def record(options: str = OPTION_A + OPTION_B, status: str = "Proposed", chosen="none yet") -> str:
    return f"""# ADR-0002: stack options

- Status: {status}
- Date: 2026-11-20
- Deciders: maintainers
- Related: ADR-0001
- Requirements: REQ-001

## Context

A reading list for readers at example.com.

## Decision

1. **Options**
{options}2. **Practices**
   - pinned actions: check (step: the workflow lint of the adopting build)
   - {SELECTION}
3. **Chosen**: {chosen}

## Consequences

The architect accepts one option; the ADR then locks it.

## Residual

None.
"""


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout


def project(tmp: Path, text: str | None = None, toml: str = "", commit: bool = False) -> Path:
    (tmp / "docs" / "adr").mkdir(parents=True)
    (tmp / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
    shutil.copytree(KIT_ROOT / "config" / "playbooks", tmp / "config" / "playbooks")
    (tmp / "agk.toml").write_text('default_branch = "main"\n' + toml, encoding="utf-8")
    if text is not None:
        (tmp / STACK).write_text(text, encoding="utf-8")
    if commit:
        git(tmp, "init", "-q", "-b", "main")
        git(tmp, "config", "user.email", "builder@example.com")
        git(tmp, "config", "user.name", "Builder")
        git(tmp, "add", "-A")
        git(tmp, "commit", "-q", "-m", "start")
        git(tmp, "checkout", "-q", "-b", "stack/accept")
    return tmp


def engines(root: Path, *args: str):
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(ENGINES), *args, "--root", str(root)],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def fails(tmp: Path, text: str) -> list[str]:
    proc = engines(project(tmp, text), "stack-check")
    return [ln for ln in proc.stdout.splitlines() if ln.startswith("FAIL")]


def test_a_complete_proposed_record_passes(tmp_path):
    """REQ-036 AC4: the four effects on each option and one recommendation pass."""
    assert fails(tmp_path, record()) == []


@pytest.mark.parametrize("effect", ["Cost:", "Build speed:", "Security:", "Uptime:"])
def test_an_option_missing_an_effect_is_refused_by_letter(tmp_path, effect):
    """REQ-036 AC4: answer 1, the effect and the option letter are named, never a value."""
    text = record(OPTION_A + OPTION_B.replace(effect, "Note:"))
    found = fails(tmp_path, text)
    assert found == [f"FAIL engines: rule 5: option B lacks {effect[:-1]} in its Trade-offs"]


def test_an_empty_effect_is_refused(tmp_path):
    """REQ-036 AC4: answer 1, each effect is a plain phrase."""
    text = record(OPTION_A + OPTION_B.replace("Uptime: a short pause on a restart.", "Uptime:."))
    assert fails(tmp_path, text) == [
        "FAIL engines: rule 5: option B lacks Uptime in its Trade-offs"
    ]


def test_no_recommendation_is_refused(tmp_path):
    """REQ-036 AC4: answer 1, one option is marked recommended."""
    text = record(OPTION_A.replace(" (recommended)", "") + OPTION_B)
    assert fails(tmp_path, text) == ["FAIL engines: rule 5: no option is marked (recommended)"]


def test_two_recommendations_are_refused(tmp_path):
    """REQ-036 AC4: answer 1, never more than one recommended option."""
    text = record(OPTION_A + OPTION_B.replace("example.com.", "example.com (recommended)."))
    assert "FAIL engines: rule 5: more than one option is marked (recommended)" in fails(
        tmp_path, text
    )


def test_a_recommendation_without_why_is_refused(tmp_path):
    """REQ-036 AC4: answer 1, the recommendation names a need with `Why:`."""
    text = record(OPTION_A.replace("Why: the busiest hour", "So the busiest hour") + OPTION_B)
    assert fails(tmp_path, text) == [
        "FAIL engines: rule 5: option A is recommended with no Why: naming a need"
    ]


def test_an_accepted_record_written_before_still_passes(tmp_path):
    """REQ-036 AC4: Q-1591-3, the new rules apply to a Proposed record only (principle 11)."""
    old = (
        "   - Option A — plain scripts. Trade-offs: nothing to host. "
        "Parts: a 1.0 MIT. Practices: pinned actions, test selection.\n"
        "   - Option B — a web framework. Trade-offs: a host to run. "
        "Parts: a 1.0 MIT. Practices: pinned actions, test selection.\n"
    )
    assert fails(tmp_path, record(old, "Accepted", "Option A — nothing to host.")) == []


def write_option_a(tmp: Path, work_type: str | None) -> str:
    toml = f'\n[delivery]\nwork_type = "{work_type}"\n' if work_type else ""
    root = project(tmp, None, toml, commit=True)
    proc = engines(root, "stack-write", "--ref", "main", "--date", "2026-11-20")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    (path,) = (root / "docs" / "adr").glob("*-stack-options.md")
    return next(ln for ln in path.read_text(encoding="utf-8").splitlines() if "Option A" in ln)


@pytest.mark.parametrize("work_type", [None, "web-app", "data-pipeline"])
def test_two_runs_for_one_shape_recommend_the_same_option(tmp_path, work_type):
    """REQ-069 AC4: answer 2, the default for the shape is Option A, recommended, every run."""
    first = write_option_a(tmp_path / "one", work_type)
    second = write_option_a(tmp_path / "two", work_type)
    assert first == second
    assert "(recommended)" in first and "Why:" in first
    for effect in ("Cost:", "Build speed:", "Security:", "Uptime:"):
        assert effect in first
    assert "TODO" not in first.split("Parts:")[0]


def test_the_shapes_get_their_own_default(tmp_path):
    """REQ-069 AC4: answer 2, `[delivery] work_type` picks the row."""
    assert write_option_a(tmp_path / "w", "web-app") != write_option_a(
        tmp_path / "d", "data-pipeline"
    )


def test_every_default_row_names_a_known_stack_and_shape():
    """REQ-069 AC4: answer 2, each row's stack is a `[[stack]]` name of stack-signals.toml."""
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    from playbook_format import WORK_TYPES

    stacks = {row["name"] for row in tomllib.loads(SIGNALS.read_text("utf-8"))["stack"]}
    rows = tomllib.loads(DEFAULTS.read_text("utf-8"))["default"]
    shapes = [row["work_type"] for row in rows]
    assert "default" in shapes and len(shapes) == len(set(shapes))
    for row in rows:
        assert row["work_type"] in {"default", *WORK_TYPES}
        assert row["stack"] in stacks
        assert "code checks for this choice come later" in row["build_speed"] + row["security"]


def test_stack_accept_writes_exactly_the_two_commits(tmp_path):
    """REQ-036 AC4: answer 4, Status and Chosen in one commit, the [testing] copy in a second."""
    root = project(tmp_path, record(), '\n[testing]\nprofile = "balanced"\n', commit=True)
    proc = engines(root, "stack-accept", "--option", "A", "--reason", "nothing to host suits it")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    log = git(root, "log", "--format=%s", "main..HEAD").splitlines()
    assert len(log) == 2
    first = git(root, "show", "--format=", "--name-only", "HEAD~1").split()
    second = git(root, "show", "--format=", "--name-only", "HEAD").split()
    assert (first, second) == ([STACK], ["agk.toml"])
    diff = git(root, "diff", "-U0", "main", "HEAD~1", "--", STACK)
    changed = [ln for ln in diff.splitlines() if ln[:1] in "+-" and ln[:3] not in ("+++", "---")]
    assert changed == [
        "-- Status: Proposed",
        "+- Status: Accepted",
        "-3. **Chosen**: none yet",
        "+3. **Chosen**: Option A — nothing to host suits it",
    ]
    table = tomllib.loads((root / "agk.toml").read_text("utf-8"))["testing"]
    assert table == {"profile": "fast", "always_full": ["app/auth/**"]}
    check = engines(root, "stack-check")
    assert "info engines: [testing] matches option A" in check.stdout, check.stdout
    assert git(root, "status", "--porcelain") == ""


def test_stack_accept_refuses_an_unknown_option_and_changes_nothing(tmp_path):
    """REQ-036 AC4: answer 4, a refusal names the option, never a value, and writes nothing."""
    root = project(tmp_path, record(), commit=True)
    proc = engines(root, "stack-accept", "--option", "C", "--reason", "a reason")
    assert proc.returncode == 1
    assert "option C" in proc.stdout
    assert git(root, "log", "--format=%s", "main..HEAD") == ""
    assert git(root, "status", "--porcelain") == ""
