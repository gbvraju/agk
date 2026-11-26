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


def record(
    options: str = OPTION_A + OPTION_B,
    status: str = "Proposed",
    chosen="none yet",
    classes: str | None = "`agk.toml`",
) -> str:
    line = "" if classes is None else f"Protected classes: {classes}\n\n"
    return f"""# ADR-0002: stack options

- Status: {status}
- Date: 2026-11-20
- Deciders: maintainers
- Related: ADR-0001
- Requirements: REQ-001

{line}## Context

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


LISTS = KIT_ROOT / "kit" / "templates"


def project(
    tmp: Path,
    text: str | None = None,
    toml: str = "",
    commit: bool = False,
    listing: str | None = "protected-paths.txt",
    mode: str = "init",
) -> Path:
    (tmp / "docs" / "adr").mkdir(parents=True)
    (tmp / "config").mkdir()
    if listing is not None:  # brief #1829: the project's own list
        shutil.copy(LISTS / listing, tmp / "config" / "protected-paths.txt")
    (tmp / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
    shutil.copytree(KIT_ROOT / "config" / "playbooks", tmp / "config" / "playbooks")
    head = f'default_branch = "main"\nmode = "{mode}"\n'
    (tmp / "agk.toml").write_text(head + toml, encoding="utf-8")
    if text is not None:
        (tmp / STACK).write_text(text, encoding="utf-8")
    return start(tmp) if commit else tmp


def start(tmp: Path) -> Path:
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


# Brief #1829 (ADR-0761): the record names the classes the accepting change meets.
ADOPT_CLASSES = "`agk.toml`, `config/`, `config/agk-baseline/`"


def classes_line(root: Path) -> str:
    (path,) = (root / "docs" / "adr").glob("*-stack-options.md")
    text = path.read_text(encoding="utf-8")
    return next(ln for ln in text.splitlines() if ln.startswith("Protected classes:"))


def test_the_template_has_the_classes_line_after_requirements():
    """REQ-036: brief #1829 answer 1, one plain header line, not a `- ` bullet."""
    lines = (KIT_ROOT / "kit" / "templates" / "stack-adr.md").read_text("utf-8").splitlines()
    at = lines.index("Protected classes: {{classes}}")
    assert lines[at - 2].startswith("- Requirements:") and lines[at - 1] == ""


@pytest.mark.parametrize(
    ("mode", "listing", "extra", "line"),
    [
        ("init", "protected-paths.txt", "", "`agk.toml`"),
        ("adopt", "protected-paths.adopt.txt", "", ADOPT_CLASSES),
        ("init", "protected-paths.txt", "docs/adr/\n", "`agk.toml`, `docs/adr/`"),
        ("init", None, "config/\n", "none"),
    ],
)
def test_stack_write_names_the_classes_of_the_project_list(tmp_path, mode, listing, extra, line):
    """REQ-036: brief #1829 answers 1 and 7, per mode and per project list; a class the project
    removed is left out, one it added that the change meets is named."""
    root = project(tmp_path, None, mode=mode, listing=listing or "protected-paths.txt")
    path = root / "config" / "protected-paths.txt"
    path.write_text(("" if listing is None else path.read_text("utf-8")) + extra, "utf-8")
    proc = engines(start(root), "stack-write", "--ref", "main", "--date", "2026-11-23")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert classes_line(root) == f"Protected classes: {line}"


def test_stack_write_refuses_an_unreadable_list_and_writes_nothing(tmp_path):
    """REQ-036: brief #1829 answer 1, the refusal names the class, never a value."""
    root = start(project(tmp_path, None, listing=None))
    proc = engines(root, "stack-write", "--ref", "main", "--date", "2026-11-23")
    assert proc.returncode == 1
    assert "rule 5: the protected path list cannot be read (path class config/)" in proc.stdout
    assert list((root / "docs" / "adr").glob("*.md")) == []


def test_stack_accept_adds_the_line_to_an_older_record_in_its_first_commit(tmp_path):
    """REQ-036: brief #1829 answer 2 (Q-G3-1), the one header line beside Status and Chosen."""
    root = project(tmp_path, record(classes=None), '\n[testing]\nprofile = "balanced"\n', True)
    proc = engines(root, "stack-accept", "--option", "A", "--reason", "nothing to host suits it")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (
        "added: Protected classes names 1 classes (setting: config/protected-paths.txt)"
        in proc.stdout
    )
    first = git(root, "diff", "-U0", "main", "HEAD~1", "--", STACK)
    added = [ln for ln in first.splitlines() if ln[:1] == "+" and ln[:3] != "+++"]
    assert "+Protected classes: `agk.toml`" in added and len(added) == 4  # with its blank line
    assert "ok protected-changes (protected change covered by an ADR)" in proc.stdout


def test_stack_accept_completes_a_line_that_misses_a_class(tmp_path):
    """REQ-036: brief #1829 answer 2, an adopted project's record that names only `agk.toml`."""
    root = project(
        tmp_path, record(), '\n[testing]\nprofile = "balanced"\n', True,
        listing="protected-paths.adopt.txt", mode="adopt",
    )  # fmt: skip
    proc = engines(root, "stack-accept", "--option", "A", "--reason", "nothing to host suits it")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "added: Protected classes names 3 classes" in proc.stdout
    assert classes_line(root) == f"Protected classes: {ADOPT_CLASSES}"
    assert (
        "next: run_gates.py --root . writes config/agk-baseline/ for the new gates;"
        " commit it in this pull request" in proc.stdout
    )
    assert len(git(root, "log", "--format=%s", "main..HEAD").splitlines()) == 2


def test_stack_accept_of_a_record_with_the_line_adds_nothing_and_passes(tmp_path):
    """REQ-036: brief #1829 answer 2, the protected-changes line after the two commits."""
    root = project(tmp_path, record(), '\n[testing]\nprofile = "balanced"\n', commit=True)
    proc = engines(root, "stack-accept", "--option", "A", "--reason", "nothing to host suits it")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "added:" not in proc.stdout and "next:" not in proc.stdout
    assert "ok protected-changes (protected change covered by an ADR)" in proc.stdout


def test_stack_accept_prints_a_failing_check_with_rc_1(tmp_path):
    """REQ-036: brief #1829 answer 2, a failure is printed, never committed over."""
    root = project(tmp_path, record(), '\n[testing]\nprofile = "balanced"\n', commit=True)
    (root / "CLAUDE.md").write_text("# a protected file, changed\n", encoding="utf-8")
    git(root, "add", "CLAUDE.md")
    git(root, "commit", "-q", "-m", "an unrelated protected change")
    proc = engines(root, "stack-accept", "--option", "A", "--reason", "nothing to host suits it")
    assert proc.returncode == 1
    assert "FAIL protected-changes: protected path class 'CLAUDE.md'" in proc.stdout
    assert git(root, "status", "--porcelain") == ""


# --- the stack's domain fit (SPEC-0074 rule 8, amendment 241; REQ-081 AC5; brief #1955) ---------

PACK = (
    'format = 1\ndomain = "zz-shop"\ntitle = "An invented pack"\nas_of = "2026-11-25"\n'
    '\n[[terms]]\nterm = "zz-shop term"\nmeaning = "An invented term"\nsynonyms = []\n'
    '\n[[constraints]]\nid = "orders-kept"\nattribute = "retention"\nscenario = "stimulus: an order'
    ' is closed; response: it is kept; measure: 5 years"\nhard = true\nbasis = "expected"\n'
    '\n[[constraints]]\nid = "logs-kept"\nattribute = "retention"\nscenario = "stimulus: a log is'
    ' written; response: it is kept; measure: 1 year"\nhard = false\nbasis = "expected"\n'
)
PACKS = '\n[domain]\npacks = ["zz-shop"]\n'
MEETS = "     Domain fit: meets\n"
CANNOT = "     Domain fit: cannot meet: zz-shop.orders-kept\n"


def fit_fails(tmp: Path, options: str, toml: str = PACKS, status: str = "Proposed") -> list[str]:
    root = project(tmp, None, toml)
    (root / "config" / "domains").mkdir()
    (root / "config" / "domains" / "zz-shop.toml").write_text(PACK, encoding="utf-8")
    chosen = "none yet" if status == "Proposed" else "Option B — kept on the person's yes."
    (root / STACK).write_text(record(options, status, chosen), encoding="utf-8")
    proc = engines(root, "stack-check")
    return [ln for ln in proc.stdout.splitlines() if ln.startswith("FAIL")]


def test_req_081_ac5_each_option_with_its_domain_fit_passes(tmp_path):
    """REQ-081 AC5: an option that cannot meet a hard constraint is shown and kept, never dropped."""
    assert fit_fails(tmp_path, OPTION_A + MEETS + OPTION_B + CANNOT) == []


def test_req_081_ac5_an_option_that_cannot_meet_may_still_be_chosen(tmp_path):
    options = OPTION_A + MEETS + OPTION_B + CANNOT
    assert fit_fails(tmp_path, options, status="Accepted") == []


def test_req_081_ac5_an_option_missing_its_domain_fit_fails_with_packs_only(tmp_path):
    found = fit_fails(tmp_path / "packs", OPTION_A + MEETS + OPTION_B)
    assert found == ["FAIL engines: SPEC-0074 rule 8: option B has no Domain fit line"]
    assert fit_fails(tmp_path / "none", OPTION_A + OPTION_B, toml="") == []


@pytest.mark.parametrize(
    ("fit", "why"),
    [
        ("zz-shop.nothing-here", "names an unknown domain constraint (id: zz-shop.nothing-here)"),
        ("zz-shop.logs-kept", "names a constraint that is not hard (id: zz-shop.logs-kept)"),
        (
            "Some Words",
            "names an unknown domain constraint (id: not of the form <pack>.<constraint>)",
        ),
    ],
)
def test_req_081_ac5_an_unknown_or_soft_id_fails(tmp_path, fit, why):
    line = f"     Domain fit: cannot meet: {fit}\n"
    assert fit_fails(tmp_path, OPTION_A + MEETS + OPTION_B + line) == [
        f"FAIL engines: SPEC-0074 rule 8: option B {why}"
    ]


@pytest.mark.parametrize("misplaced", ["before", "bullet"])
def test_req_081_ac5_a_domain_fit_line_out_of_place_fails(tmp_path, misplaced):
    options = (
        MEETS + OPTION_A + OPTION_B + MEETS
        if misplaced == "before"
        else OPTION_A + "   - Domain fit: meets\n" + OPTION_B + MEETS
    )
    assert "FAIL engines: SPEC-0074 rule 8: option A has no Domain fit line" in fit_fails(
        tmp_path, options
    )


def test_req_081_ac5_an_accepted_record_written_before_packs_is_held(tmp_path):
    """An upgrade fails nothing: an Accepted record with no Domain fit line is held."""
    assert fit_fails(tmp_path, OPTION_A + OPTION_B, status="Accepted") == []


def test_req_081_ac5_the_option_parsers_read_every_option_with_the_lines():
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import engines as engines_module  # noqa: PLC0415
    from gates import pins  # noqa: PLC0415

    text = record(OPTION_A + MEETS + OPTION_B + CANNOT, "Accepted", "Option B — kept.")
    for pattern in (pins.OPTION, engines_module.OPTION):
        found = [m.group(1) for ln in text.splitlines() if (m := pattern.match(ln))]
        assert found == ["A", "B"]
    assert pins.chosen_parts(
        [text.replace("3. **Chosen**: Option B — kept.", "3. **Chosen**: Option B")]
    ) == [("a", "1.0", "MIT")]


def test_req_081_ac5_stack_write_leaves_a_domain_fit_slot_with_packs_set(tmp_path):
    root = project(tmp_path, None, PACKS)
    (root / "config" / "domains").mkdir()
    (root / "config" / "domains" / "zz-shop.toml").write_text(PACK, encoding="utf-8")
    start(root)
    proc = engines(root, "stack-write", "--ref", "main", "--date", "2026-11-20")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    (path,) = (root / "docs" / "adr").glob("*-stack-options.md")
    lines = path.read_text(encoding="utf-8").splitlines()
    slots = [i for i, ln in enumerate(lines) if ln == "     Domain fit: TODO(architect)"]
    assert [lines[i - 1].lstrip()[:10] for i in slots] == ["- Option A", "- Option B"]
