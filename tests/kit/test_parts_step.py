"""Kit tests: the `parts` step and the plan hold (SPEC-0076 build (d), rules 3, 8, 9, 11 and 17;
brief #2071, ADR-0867; REQ-083 AC4, AC5 and AC6).

On saved trees (Node and Python, one and two runtimes) the step fails a direct dependency the
parts record and the stack record do not name, a record part missing from its build file or at
another version than the build file or the lock, a row with an empty required column, a second
part for one need with no `Decision:` line and a stale health date, each naming the rule and the
component class and never a name or a version; it is not run, never `ok` and never red, with no
stack, no reader, no record, no foundation or a build file `pins` cannot read; under
`record = "optional"` (or no `[parts]` table) every finding is a warning; `check_plan.py` holds
the foundation brief under `required` until the record is confirmed. Invented names under a
temporary root (example.com); no network.
"""

from __future__ import annotations

import datetime
import json
import socket
import subprocess  # nosec B404 - the test drives git with fixed argument lists
import sys
from pathlib import Path

import pytest
from test_pins import HASH, NODE_PARTS, STACK, TWO_PARTS, node_files, project, py_files, record

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_plan  # noqa: E402
import run_gates  # noqa: E402
from gates import parts, pins  # noqa: E402

TODAY = datetime.datetime.now(datetime.UTC).date().isoformat()
OLD = "2020-01-02"
HEAD = (
    "| Need | Part | Version | Kind | Why | Alternatives considered | Licence | Health (date) "
    "| For the business |\n|---|---|---|---|---|---|---|---|---|\n"
)
QUIET = ("example-web", "example-extra", "example-clock", "examplelib", "4.21.1", "1.0.0", "2.0.0")
PY_PARTS = "Parts: python 3.12.7 PSF-2.0 (verify)."
EMPTY_PY = '[project]\nname = "s"\nversion = "0"\n'
REQUIRED = '[delivery]\nwork_type = "web-app"\n\n[parts]\nrecord = "required"\n'


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the parts step opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    for name in ("AGK_BASE", "GITHUB_BASE_REF", "CI"):
        monkeypatch.delenv(name, raising=False)


def row(
    part: str, version: str, need: str = "web-api", health: str = "", why: str = "REQ-001"
) -> str:
    health = health or f"maintained (read {TODAY}, https://example.com/registry)"
    cells = (need, part, version, "runtime", why, "none", "MIT", health, "Serves example.com.")
    return "| " + " | ".join(cells) + " |\n"


def write_record(
    root: Path, sections: dict[str, str], confirmed: str = "architect (2026-11-21)"
) -> None:
    body = "".join(f"## {name}\n\n{HEAD}{rows}\n" for name, rows in sections.items())
    text = f"# Parts\n\n{body}Questions for the person:\n\nConfirmed by: {confirmed}\n"
    (root / "docs" / "parts.md").write_text(text, encoding="utf-8")


def node_tree(tmp: Path, toml: str = REQUIRED, rows: str | None = None, extra: bool = True) -> Path:
    """The brief's measured tree: the stack record names example-web, the build file and the lock
    also hold example-extra, and the record names another part."""
    root = project(tmp, record(a_parts=NODE_PARTS, status="Accepted", chosen="Option A"), toml=toml)
    deps = {"example-web": "4.21.1", **({"example-extra": "1.0.0"} if extra else {})}
    pkg = {"name": "sample", "version": "0.0.0", "dependencies": deps}
    (root / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    packages = {"": {"name": "sample"}}
    packages.update({f"node_modules/{n}": {"version": v} for n, v in deps.items()})
    lock = {"lockfileVersion": 3, "packages": packages}
    (root / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
    write_record(
        root, {"node": rows if rows is not None else row("example-clock", "2.0.0", "time")}
    )
    return root


def named_tree(tmp: Path, toml: str = REQUIRED) -> Path:
    """A green tree: every dependency of the build file has its full row."""
    return node_tree(tmp, toml, rows=row("example-extra", "1.0.0", "http-client"))


def found(root: Path) -> list[tuple[str, str, str]]:
    fails, warns = parts.evaluate(root)
    return sorted(fails + warns)


def rows_of(root: Path) -> list[tuple[object, str]]:
    return [r for r in run_gates.results(root) if r[1].startswith(("parts", "warn parts"))]


def quiet(text: str) -> None:
    for word in QUIET:
        assert word not in text


# Rule 8 (REQ-083 AC4): each finding names the rule and the component class, never a value.


def test_req083_ac4_the_measured_tree_is_red_under_required(tmp_path: Path) -> None:
    rows = rows_of(node_tree(tmp_path))
    assert rows == [
        (
            False,
            f"parts: {parts.RULE}: a direct dependency the record does not name "
            "(component class: dependency) (path class: package.json)",
        ),
        (
            False,
            f"parts: {parts.RULE}: a record part is missing from its build file "
            "(component class: record part) (path class: docs/parts.md)",
        ),
    ]
    quiet(repr(rows))


def test_req083_ac4_the_measured_tree_warns_with_no_parts_table(tmp_path: Path, capsys) -> None:
    root = node_tree(tmp_path, toml='[delivery]\nwork_type = "web-app"\n')
    assert rows_of(root) == [
        (
            run_gates.NOTE,
            f"warn parts: {parts.RULE}: a direct dependency the record does not name "
            "(component class: dependency) (path class: package.json)",
        ),
        (
            run_gates.NOTE,
            f"warn parts: {parts.RULE}: a record part is missing from its build file "
            "(component class: record part) (path class: docs/parts.md)",
        ),
        (run_gates.HELD, "parts: 2 warnings (setting: parts.record)"),
    ]
    run_gates.cmd_check(root)
    out = capsys.readouterr().out
    assert "ok parts" not in out and "FAIL gates: parts" not in out
    quiet(out)


def test_req083_ac4_a_named_tree_passes_and_the_platform_counts_as_named(tmp_path: Path) -> None:
    """`Q-PD-2`: example-web is named by the chosen option's `Parts:` and needs no row."""
    assert rows_of(named_tree(tmp_path)) == [(True, "parts")]


def test_req083_ac4_versions_differ_from_the_build_file_and_the_lock(tmp_path: Path) -> None:
    root = named_tree(tmp_path)
    write_record(root, {"node": row("example-extra", "1.0.1", "http-client")})
    lock = json.loads((root / "package-lock.json").read_text(encoding="utf-8"))
    lock["packages"]["node_modules/example-extra"]["version"] = "1.0.2"
    (root / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
    assert [(m, c) for m, c, _ in found(root)] == [
        ("a record version differs from the build file", "record part"),
        ("a record version differs from the lock", "record part"),
    ]


@pytest.mark.parametrize("cell", range(4, 9))
def test_req083_ac4_an_empty_required_column_fails(tmp_path: Path, cell: int) -> None:
    root = named_tree(tmp_path)
    cells = row("example-extra", "1.0.0", "http-client").strip().strip("|").split("|")
    cells[cell] = " "
    write_record(root, {"node": "|" + "|".join(cells) + "|\n"})
    assert found(root) == [
        ("a record row is empty in a required column", "record row", parts.RECORD)
    ]


def test_req083_ac4_a_second_part_for_one_need_needs_a_decision(tmp_path: Path) -> None:
    root = named_tree(tmp_path)
    two = row("example-extra", "1.0.0", "http-client") + row("stdlib", "none", "http-client")
    write_record(root, {"node": two})
    assert found(root) == [
        ("a second part for one need has no Decision: line", "record row", parts.RECORD)
    ]
    write_record(root, {"node": two + "\nDecision: http-client: the runtime's own for one call\n"})
    assert found(root) == []


def test_req083_ac4_a_stdlib_part_needs_no_dependency(tmp_path: Path) -> None:
    root = named_tree(tmp_path)
    write_record(
        root, {"node": row("example-extra", "1.0.0", "http-client") + row("stdlib", "none", "time")}
    )
    assert found(root) == []


def test_req083_ac4_a_record_that_cannot_be_read_names_no_text(tmp_path: Path) -> None:
    root = named_tree(tmp_path)
    (root / "docs" / "parts.md").write_bytes(b"# Parts\n\xff\xfe\n")
    assert found(root) == [("the parts record cannot be read", "record", parts.RECORD)]
    (root / "docs" / "parts.md").write_text(
        "# Parts\n\n| Need | Part |\n|---|---|\n", encoding="utf-8"
    )
    assert found(root) == [("the parts record cannot be read", "record", parts.RECORD)]


def test_req083_ac4_python_files_and_their_r_files_are_read(tmp_path: Path) -> None:
    root = project(
        tmp_path, record(a_parts=PY_PARTS, status="Accepted", chosen="Option A"), toml=REQUIRED
    )
    (root / "pyproject.toml").write_text(EMPTY_PY, encoding="utf-8")
    (root / "requirements.txt").write_text("examplelib==1.2.3\n-r extra.txt\n", encoding="utf-8")
    (root / "extra.txt").write_text("example_Extra==1.0.0\n", encoding="utf-8")
    lock = f"examplelib==1.2.3 \\\n    {HASH}\nexample-extra==1.0.0 \\\n    {HASH}\n"
    (root / "requirements.lock").write_text(lock, encoding="utf-8")
    write_record(root, {"python": row("examplelib", "1.2.3")})
    assert found(root) == [
        ("a direct dependency the record does not name", "dependency", "extra.txt")
    ]
    write_record(
        root, {"python": row("examplelib", "1.2.3") + row("Example.Extra", "1.0.0", "time")}
    )
    assert found(root) == []


def test_req083_ac4_two_runtimes_read_their_own_sections(tmp_path: Path) -> None:
    text = record(a_parts=TWO_PARTS, status="Accepted", chosen="Option A")
    root = project(tmp_path, text, toml=REQUIRED)
    node_files(root, extra=None)
    py_files(
        root / "service",
        req="examplelib==1.2.3\nexample-extra==1.0.0\n",
        lock=f"examplelib==1.2.3 \\\n    {HASH}\nexample-extra==1.0.0 \\\n    {HASH}\n",
    )
    write_record(root, {"Node.js": "", "Python": row("example-extra", "1.0.0", "time")})
    assert found(root) == []
    write_record(root, {"node": row("example-extra", "1.0.0", "time"), "python": ""})
    assert found(root) == [
        ("a direct dependency the record does not name", "dependency", "service/requirements.txt"),
        ("a record part is missing from its build file", "record part", parts.RECORD),
    ]


def test_req083_ac4_a_missing_lock_compares_the_build_file_only(tmp_path: Path) -> None:
    root = named_tree(tmp_path)
    (root / "package-lock.json").unlink()
    (root / "docs" / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
    assert found(root) == []


# A stale health date fails only a change that touches the record or a build file (Q-S0076-12).


def git(root: Path, *args: str) -> None:
    subprocess.run(  # nosec B603 B607 - fixed git arguments, no shell
        ["git", *args], cwd=root, check=True, capture_output=True
    )


def history(root: Path) -> Path:
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    git(root, "checkout", "-q", "-b", "feature")
    return root


def stale_tree(tmp: Path) -> Path:
    root = named_tree(tmp)
    write_record(
        root,
        {"node": row("example-extra", "1.0.0", "http-client", health=f"maintained (read {OLD})")},
    )
    return root


STALE = ("a record row's health date is older than the limit", "record row", parts.RECORD)


def test_req083_ac4_a_stale_date_warns_on_an_untouched_record(tmp_path: Path) -> None:
    root = history(stale_tree(tmp_path))
    assert parts.evaluate(root) == ([], [STALE])
    (root / "README.md").write_text("# Sample\n", encoding="utf-8")
    assert parts.evaluate(root) == ([], [STALE])


@pytest.mark.parametrize("rel", ["docs/parts.md", "package.json", "package-lock.json"])
def test_req083_ac4_a_stale_date_fails_a_change_that_touches_the_record(
    tmp_path: Path, rel: str
) -> None:
    root = history(stale_tree(tmp_path))
    path = root / rel
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert parts.evaluate(root) == ([STALE], [])


def test_req083_ac4_a_stale_date_with_no_git_or_no_base_in_ci_warns(
    tmp_path: Path, monkeypatch
) -> None:
    root = stale_tree(tmp_path)
    assert parts.evaluate(root) == ([], [STALE])
    history(root)
    git(root, "branch", "-q", "-D", "main")
    monkeypatch.setenv("CI", "true")
    assert parts.evaluate(root) == ([], [STALE])


def test_req083_ac4_the_health_limit_is_the_setting(tmp_path: Path) -> None:
    root = named_tree(tmp_path, toml=REQUIRED + "max_age_months = 2\n")
    month = (datetime.datetime.now(datetime.UTC).date() - datetime.timedelta(days=95)).isoformat()
    write_record(
        root, {"node": row("example-extra", "1.0.0", "http-client", health=f"ok (read {month})")}
    )
    assert parts.evaluate(root) == ([], [STALE])
    (root / "agk.toml").write_text('default_branch = "main"\n' + REQUIRED + "max_age_months = 6\n")
    assert parts.evaluate(root) == ([], [])


# Not run, never `ok` and never red (rules 8 and 11).


def test_req083_ac4_no_stack_chosen_is_not_run(tmp_path: Path) -> None:
    root = node_tree(tmp_path)
    (root / STACK).write_text(record(a_parts=NODE_PARTS), encoding="utf-8")
    assert rows_of(root) == [(None, "parts: no stack chosen")]


def test_req083_ac4_a_stack_with_no_reader_is_not_run(tmp_path: Path) -> None:
    root = node_tree(tmp_path)
    parts_line = "Parts: example-runtime 1.0.0 MIT (verify)."
    (root / STACK).write_text(record(a_parts=parts_line, status="Accepted", chosen="Option A"))
    assert rows_of(root) == [(None, "parts: no reader for this stack")]


def test_req083_ac4_no_parts_record_is_not_run(tmp_path: Path) -> None:
    root = node_tree(tmp_path)
    (root / "docs" / "parts.md").unlink()
    assert rows_of(root) == [(None, "parts: no parts record")]


def test_req083_ac4_no_foundation_yet_is_not_run(tmp_path: Path) -> None:
    root = project(
        tmp_path, record(a_parts=NODE_PARTS, status="Accepted", chosen="Option A"), toml=REQUIRED
    )
    write_record(root, {"node": row("example-clock", "2.0.0", "time")})
    assert rows_of(root) == [(None, "parts: no foundation yet")]


def test_req083_ac4_a_build_file_pins_cannot_read_is_left_to_pins(tmp_path: Path) -> None:
    root = node_tree(tmp_path)
    (root / "package.json").write_text("{ not json", encoding="utf-8")
    assert rows_of(root) == [(None, "parts: the build files are not read")]


# Settings (rule 9, REQ-083 AC6).


@pytest.mark.parametrize(
    ("table", "key"),
    [
        ('record = "always"', "record"),
        ("record = true", "record"),
        ('colour = "blue"', "colour"),
        ("max_age_months = true", "max_age_months"),
        ("max_age_months = 1.5", "max_age_months"),
        ("max_age_months = 61", "max_age_months"),
        ("max_age_months = 0", "max_age_months"),
    ],
)
def test_req083_ac6_a_refused_table_is_one_failure_naming_the_setting(
    tmp_path: Path, table: str, key: str
) -> None:
    root = node_tree(tmp_path, toml=f'[delivery]\nwork_type = "web-app"\n\n[parts]\n{table}\n')
    line = f"the [parts] table is refused (setting: parts.{key})"
    assert rows_of(root) == [(False, f"parts: {line}")]
    plan(root)
    assert check_plan.parts_problems(root) == [line]


@pytest.mark.parametrize("value", ['"critical"', '"any"', '"critical-high"'])
def test_req083_ac6_advisories_is_not_read_by_the_step(tmp_path: Path, value: str) -> None:
    root = node_tree(tmp_path, toml=REQUIRED + f"advisories = {value}\n")
    assert rows_of(root) == rows_of(node_tree(tmp_path / "plain"))


def test_req083_ac6_no_work_type_has_no_parts_row_and_no_hold(tmp_path: Path) -> None:
    root = node_tree(tmp_path, toml='[parts]\nrecord = "required"\n')
    assert rows_of(root) == []
    plan(root)
    assert check_plan.parts_problems(root) == []


def test_req083_ac6_the_kit_itself_prints_no_parts_row() -> None:
    assert not parts.applies(KIT_ROOT)
    assert rows_of(KIT_ROOT) == []


def test_req083_ac6_every_other_row_is_unchanged(tmp_path: Path, monkeypatch) -> None:
    """Answer 3: only the `parts` rows are new; every other step's rows are today's."""
    root = node_tree(tmp_path, toml='[delivery]\nwork_type = "web-app"\n')
    now = [r for r in run_gates.results(root) if not r[1].startswith(("parts", "warn parts"))]
    monkeypatch.setattr(run_gates, "PRODUCT_STEPS", ("pins", "bom", "licences"))
    assert run_gates.results(root) == now


# The plan hold (rule 3, REQ-083 AC5).


def plan(root: Path) -> None:
    folder = root / "docs" / "plan" / "briefs" / "M1"
    folder.mkdir(parents=True, exist_ok=True)
    (root / "docs" / "plan" / "milestones.md").write_text("# Milestones\n\n### M1 Foundation\n")
    (folder / "B1.md").write_text("# B1\n\nMilestone: M1\nKind: foundation\n", encoding="utf-8")


HOLD = (
    "SPEC-0076 rule 3: B1: the foundation brief before a confirmed parts record "
    "(setting: parts.record)"
)


@pytest.mark.parametrize(
    "said", ["none yet", "TODO(person) (2026-11-21)", "architect (2026-13-40)", "architect"]
)
def test_req083_ac5_the_foundation_brief_waits_for_a_confirmed_record(
    tmp_path: Path, said: str
) -> None:
    root = named_tree(tmp_path)
    write_record(root, {"node": row("example-extra", "1.0.0", "http-client")}, confirmed=said)
    plan(root)
    assert check_plan.parts_problems(root) == [HOLD]
    (root / "docs" / "parts.md").unlink()
    assert check_plan.parts_problems(root) == [HOLD]


def test_req083_ac5_a_confirmed_record_optional_or_no_foundation_holds_nothing(
    tmp_path: Path,
) -> None:
    root = named_tree(tmp_path)
    plan(root)
    assert parts.confirmed(root)
    assert check_plan.parts_problems(root) == []
    root = named_tree(tmp_path / "optional", toml='[delivery]\nwork_type = "web-app"\n')
    write_record(root, {"node": ""}, confirmed="none yet")
    plan(root)
    assert check_plan.parts_problems(root) == []
    root = named_tree(tmp_path / "nofoundation")
    write_record(root, {"node": ""}, confirmed="none yet")
    assert check_plan.parts_problems(root) == []


def test_req083_ac5_check_plan_prints_the_hold(tmp_path: Path, capsys) -> None:
    root = named_tree(tmp_path)
    write_record(root, {"node": ""}, confirmed="none yet")
    plan(root)
    check_plan.cmd_check(root)
    assert f"FAIL plan: {HOLD}" in capsys.readouterr().out


# Rule 17 (answer 8): the class stays closed over every build file pins reads.


BUILD_FILES = {
    "package.json": ("node", NODE_PARTS),
    "pyproject.toml": ("python", PY_PARTS),
    "requirements.txt": ("python", PY_PARTS),
}


def test_req083_ac4_every_build_file_pins_reads_is_checked(tmp_path: Path) -> None:
    names = {n for places in pins.PLACES.values() for n in places} | {
        s[1] for s in pins.STACKS.values()
    }
    assert names == set(BUILD_FILES)
    for name, (runtime, line) in BUILD_FILES.items():
        root = project(
            tmp_path / name,
            record(a_parts=line, status="Accepted", chosen="Option A"),
            toml=REQUIRED,
        )
        if name == "package.json":
            text = json.dumps(
                {"name": "s", "version": "0.0.0", "devDependencies": {"example-extra": "1.0.0"}}
            )
        elif name == "pyproject.toml":
            text = '[project]\nname = "s"\nversion = "0"\ndependencies = ["example-extra==1.0.0"]\n'
        else:
            text = "example-extra==1.0.0\n"
            (root / "pyproject.toml").write_text(EMPTY_PY, encoding="utf-8")
        (root / name).write_text(text, encoding="utf-8")
        (root / "docs" / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
        write_record(root, {runtime: ""})
        assert parts.evaluate(root)[0] == [
            ("a direct dependency the record does not name", "dependency", name)
        ]


def test_req083_ac4_the_step_is_installed_and_after_pins() -> None:
    steps = run_gates.PRODUCT_STEPS
    assert steps.index("parts") == steps.index("pins") + 1
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/gates/parts.py" in manifest["verbatim"]
