"""Kit tests: `engines.py stack-files` writes the build file from the parts record (SPEC-0076 build
(e), rules 3 and 8, amendment 259 to SPEC-0072 rule 4; brief #2072, ADR-0862; REQ-083 AC5).

With a confirmed `docs/parts.md` the chosen stack's build file holds exactly the record's runtime
parts as dependencies and its dev parts as dev dependencies, at their recorded versions, and
nothing else; a row it cannot write, a record it cannot read, a refused `[parts]` table and
`record = "required"` with no confirmed record each refuse before any write, naming the rule and
the class or setting, never a name or a version; with no confirmed record the output is today's.
Invented names under a temporary root (example.com); no network.
"""

from __future__ import annotations

import json
import re
import socket
import sys
import tomllib
from pathlib import Path

import pytest
from test_pins import ENGINES, NODE_PARTS, PY_PARTS, project, record, run

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

from gates import parts, pins  # noqa: E402
from init import render, slug  # noqa: E402

HEAD = (
    "| Need | Part | Version | Kind | Why | Alternatives considered | Licence | Health (date) "
    "| For the business |\n|---|---|---|---|---|---|---|---|---|\n"
)
CONFIRMED = "Confirmed by: architect (2026-11-21)"
WORDS = ("example-web", "example-lint", "examplelib", "example-test", "4.21.1", "2.0.0", "1.2.3")
NO_TABLE = '[delivery]\nwork_type = "web-app"\n'
REQUIRED = NO_TABLE + '\n[parts]\nrecord = "required"\n'
OPTIONAL = NO_TABLE + '\n[parts]\nrecord = "optional"\n'
NODE_ROWS = ("example-web", "4.21.1", "runtime"), ("example-lint", "2.0.0", "dev")
PY_ROWS = ("examplelib", "1.2.3", "runtime"), ("example-test", "8.0.0", "dev")
AMENDMENT = KIT_ROOT / "docs" / "runs" / "proposed-spec-amendments-259.md"
SPEC = next((KIT_ROOT / "docs" / "specs").glob("0072-*.md"))


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("stack-files opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def row(part: str, version: str, kind: str, need: str = "") -> str:
    health = "maintained (read 2026-11-20, https://example.com/registry)"
    cells = (need or part, part, version, kind, "REQ-001", "none", "MIT", health, "Serves people.")
    return "| " + " | ".join(cells) + " |\n"


def write_record(root: Path, sections: dict[str, tuple], confirmed: str = CONFIRMED) -> None:
    body = "".join(
        f"## {name}\n\n{HEAD}{''.join(row(*r) for r in rows)}\n" for name, rows in sections.items()
    )
    text = f"# Parts\n\n{body}Questions for the person:\n\n{confirmed}\n"
    (root / "docs" / "parts.md").write_text(text, encoding="utf-8")


def node(tmp: Path, toml: str = NO_TABLE, rows: tuple | None = NODE_ROWS, **kw: str) -> Path:
    root = project(tmp, record(a_parts=NODE_PARTS, status="Accepted", chosen="Option A"), toml)
    if rows is not None:
        write_record(root, {"node": rows}, **kw)
    return root


def python(tmp: Path, toml: str = NO_TABLE, rows: tuple | None = PY_ROWS) -> Path:
    root = project(tmp, record(a_parts=PY_PARTS, status="Accepted", chosen="Option A"), toml)
    if rows is not None:
        write_record(root, {"python": rows})
    return root


def stack_files(root: Path):
    result = run(ENGINES, "stack-files", "--root", str(root))
    for word in WORDS:
        assert word not in result.stdout + result.stderr, word
    return result


def today(root: Path, name: str) -> str:
    """The build file today's `stack-files` writes: the template rendered, nothing filled."""
    folder = "node" if name == "package.json" else "python-pyproject"
    source = KIT_ROOT / "kit" / "templates" / "stacks" / folder / name
    return render(source.read_text(encoding="utf-8"), {"project": slug(root.resolve().name)}, name)


def package(root: Path) -> dict:
    return json.loads((root / "package.json").read_text(encoding="utf-8"))


def nothing_written(root: Path) -> None:
    assert not (root / "package.json").exists() and not (root / "pyproject.toml").exists()
    assert not (root / "config" / "licences.toml").exists()


# Rule 8 "Written" (REQ-083 AC5): the record's rows, at their versions, and nothing else.


def test_req083_ac5_node_writes_the_runtime_and_dev_parts(tmp_path: Path) -> None:
    root = node(tmp_path, rows=(*NODE_ROWS, ("stdlib", "", "runtime", "time")))
    result = stack_files(root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (
        "wrote package.json from docs/parts.md (1 runtime, 1 dev parts); make package-lock.json "
        "with the stack's own tool and commit both"
    ) in result.stdout
    data = package(root)
    assert data["dependencies"] == {"example-web": "4.21.1"}
    assert data["devDependencies"] == {"example-lint": "2.0.0"}
    assert data["private"] is True
    text = (root / "package.json").read_text(encoding="utf-8")
    assert text == json.dumps(data, indent=2) + "\n"


def test_req083_ac5_python_writes_dependencies_and_a_dev_group(tmp_path: Path) -> None:
    root = python(tmp_path)
    result = stack_files(root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "wrote pyproject.toml from docs/parts.md (1 runtime, 1 dev parts)" in result.stdout
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["dependencies"] == ["examplelib==1.2.3"]
    assert data["project"]["optional-dependencies"] == {"dev": ["example-test==8.0.0"]}
    assert data["build-system"]["requires"] == ["setuptools==80.9.0"]
    got = sorted(pins.declared(root, "requirements", "pyproject.toml"))
    assert [(n, v) for n, v, _ in got] == [("example-test", "8.0.0"), ("examplelib", "1.2.3")]


def test_req083_ac5_the_parts_step_finds_nothing_once_the_lock_is_made(tmp_path: Path) -> None:
    root = node(tmp_path, toml=REQUIRED)
    assert stack_files(root).returncode == 0
    locked = {f"node_modules/{n}": {"version": v} for n, v, _ in NODE_ROWS}
    lock = {"lockfileVersion": 3, "packages": {"": {"name": "s"}, **locked}}
    (root / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
    assert parts.skipped(root) is None
    assert parts.evaluate(root) == ([], [])


def test_req083_ac5_sorted_by_name_and_spelled_as_the_record(tmp_path: Path) -> None:
    rows = (("zeta-example", "1.0.0", "runtime"), ("Example_Web", "4.21.1", "runtime"))
    root = node(tmp_path, rows=rows)
    assert stack_files(root).returncode == 0
    assert list(package(root)["dependencies"]) == ["Example_Web", "zeta-example"]


# Answer 2: every row is checked first, so a refusal writes nothing.


@pytest.mark.parametrize(
    "bad",
    [
        ("example-web", "^4.21.1", "runtime"),
        ("example-web", "4.21.1 (verify)", "runtime"),
        ("example-web", "", "runtime"),
        ("example-web", "4.21.1", "peer"),
    ],
)
def test_req083_ac5_a_row_that_cannot_be_written_is_refused(tmp_path: Path, bad: tuple) -> None:
    root = node(tmp_path, rows=(("example-lint", "2.0.0", "dev"), bad))
    result = stack_files(root)
    assert result.returncode == 1
    assert (
        "FAIL engines: SPEC-0076 rule 8: a record part cannot be written "
        "(component class: record part)"
    ) in result.stdout + result.stderr
    nothing_written(root)


def test_req083_ac5_a_python_range_is_refused(tmp_path: Path) -> None:
    root = python(tmp_path, rows=(("examplelib", ">=1.2.3", "runtime"),))
    assert stack_files(root).returncode == 1
    nothing_written(root)


def test_req083_ac5_a_record_it_cannot_read_is_refused(tmp_path: Path) -> None:
    root = node(tmp_path, rows=None)
    (root / "docs" / "parts.md").write_text(f"# Parts\n\nNo table.\n\n{CONFIRMED}\n", "utf-8")
    result = stack_files(root)
    assert result.returncode == 1
    assert (
        "FAIL engines: SPEC-0076 rule 8: the parts record cannot be read "
        "(path class: docs/parts.md)"
    ) in result.stdout + result.stderr
    nothing_written(root)


# Answer 4: the settings.


@pytest.mark.parametrize("toml", [NO_TABLE, OPTIONAL])
def test_req083_ac5_no_record_is_today_byte_for_byte(tmp_path: Path, toml: str) -> None:
    for name, make in (("package.json", node), ("pyproject.toml", python)):
        root = make(tmp_path / name, toml=toml, rows=None)
        result = stack_files(root)
        assert result.returncode == 0
        assert (root / name).read_text(encoding="utf-8") == today(root, name)
        assert "parts" not in result.stdout + result.stderr
        assert re.search(rf"^wrote {re.escape(name)}; make ", result.stdout, re.M)


@pytest.mark.parametrize("toml", [NO_TABLE, OPTIONAL])
def test_req083_ac5_an_unconfirmed_record_is_today_and_says_so(tmp_path: Path, toml: str) -> None:
    root = node(tmp_path, toml=toml, confirmed="Confirmed by: TODO(person)")
    result = stack_files(root)
    assert result.returncode == 0
    assert (root / "package.json").read_text(encoding="utf-8") == today(root, "package.json")
    assert package(root)["dependencies"] == {} and package(root)["devDependencies"] == {}
    assert "not written from docs/parts.md: not confirmed (setting: parts.record)" in result.stdout


@pytest.mark.parametrize("toml", [NO_TABLE, OPTIONAL, REQUIRED])
def test_req083_ac5_a_confirmed_record_is_written_under_any_value(
    tmp_path: Path, toml: str
) -> None:
    root = node(tmp_path, toml=toml)
    assert stack_files(root).returncode == 0
    assert package(root)["dependencies"] == {"example-web": "4.21.1"}


@pytest.mark.parametrize("confirmed", [None, "Confirmed by: TODO(person)"])
def test_req083_ac5_required_waits_for_a_confirmed_record(tmp_path: Path, confirmed) -> None:
    root = node(tmp_path, toml=REQUIRED, rows=None if confirmed is None else NODE_ROWS)
    if confirmed:
        write_record(root, {"node": NODE_ROWS}, confirmed=confirmed)
    result = stack_files(root)
    assert result.returncode == 1
    assert (
        "FAIL engines: SPEC-0076 rule 3: the build file waits for a confirmed parts record "
        "(setting: parts.record)"
    ) in result.stdout + result.stderr
    nothing_written(root)


@pytest.mark.parametrize(
    ("table", "key"),
    [('record = "always"', "parts.record"), ("colour = 1", "parts.colour")],
)
def test_req083_ac5_a_refused_table_writes_nothing(tmp_path: Path, table: str, key: str) -> None:
    root = node(tmp_path, toml=f"{NO_TABLE}\n[parts]\n{table}\n")
    result = stack_files(root)
    assert result.returncode == 1
    assert f"FAIL engines: the [parts] table is refused (setting: {key})" in result.stdout
    nothing_written(root)


def test_req083_ac5_the_age_and_advisory_settings_change_nothing(tmp_path: Path) -> None:
    texts = set()
    for n, extra in enumerate(("", "max_age_months = 3\nadvisories = \"any\"\n")):
        root = node(tmp_path / str(n) / "same", toml=f"{OPTIONAL}{extra}")
        assert stack_files(root).returncode == 0
        texts.add((root / "package.json").read_text(encoding="utf-8"))
    assert len(texts) == 1


def test_req083_ac5_no_stack_chosen_is_not_run(tmp_path: Path) -> None:
    root = project(tmp_path, record(a_parts=NODE_PARTS), REQUIRED)
    write_record(root, {"node": NODE_ROWS})
    result = stack_files(root)
    assert result.returncode == 0
    assert result.stdout.strip() == "stack-files: not run: no stack chosen"


def test_req083_ac5_two_runtimes_are_not_run(tmp_path: Path) -> None:
    both = "Parts: node 22.11.0 MIT, python 3.12.7 PSF-2.0 (verify)."
    root = project(tmp_path, record(a_parts=both, status="Accepted", chosen="Option A"))
    write_record(root, {"node": NODE_ROWS, "python": PY_ROWS})
    assert "not run: no stack chosen" in stack_files(root).stdout
    nothing_written(root)


# Answer 5: the edge cases.


def test_req083_ac5_a_second_run_keeps_the_written_file(tmp_path: Path) -> None:
    root = node(tmp_path)
    assert stack_files(root).returncode == 0
    first = (root / "package.json").read_bytes()
    write_record(root, {"node": (*NODE_ROWS, ("example-later", "1.0.0", "runtime"))})
    result = stack_files(root)
    assert result.returncode == 0 and "kept package.json" in result.stdout
    assert (root / "package.json").read_bytes() == first


def test_req083_ac5_an_adopted_build_file_is_kept(tmp_path: Path) -> None:
    root = node(tmp_path, toml=f'mode = "adopt"\n{NO_TABLE}')
    own = '{"name": "theirs", "dependencies": {"example-web": "4.0.0"}}\n'
    (root / "package.json").write_text(own, encoding="utf-8")
    result = stack_files(root)
    assert result.returncode == 0 and "kept package.json" in result.stdout
    assert (root / "package.json").read_text(encoding="utf-8") == own


def test_req083_ac5_another_runtime_section_is_not_read(tmp_path: Path) -> None:
    root = node(tmp_path, rows=None)
    write_record(root, {"node": NODE_ROWS[:1], "python": PY_ROWS})
    assert stack_files(root).returncode == 0
    assert package(root)["dependencies"] == {"example-web": "4.21.1"}
    assert package(root)["devDependencies"] == {}


def test_req083_ac5_no_row_for_the_runtime_writes_the_empty_lists(tmp_path: Path) -> None:
    """The stack record's `Parts:` names example-web (the platform); it is not a record row."""
    root = node(tmp_path, rows=None)
    write_record(root, {"python": PY_ROWS})
    result = stack_files(root)
    assert result.returncode == 0
    assert "wrote package.json from docs/parts.md (0 runtime, 0 dev parts)" in result.stdout
    assert package(root)["dependencies"] == {} and package(root)["devDependencies"] == {}


# Answer 7: the class stays closed; answer 3: the amendment is applied word for word.


def test_req083_ac5_every_written_dependency_is_a_record_row(tmp_path: Path) -> None:
    root = node(tmp_path)
    assert stack_files(root).returncode == 0
    data = package(root)
    written = {**data["dependencies"], **data["devDependencies"]}
    assert written == {n: v for n, v, _ in NODE_ROWS}


def test_req083_ac5_spec_0072_holds_amendment_259_word_for_word() -> None:
    item = AMENDMENT.read_text(encoding="utf-8").split("## Items", 1)[1]
    quoted = re.findall(r'"([^"]+)"', " ".join(item.split()))
    anchor, inserted = quoted[0], quoted[1]
    spec = " ".join(SPEC.read_text(encoding="utf-8").split())
    assert spec.count(anchor + inserted) == 1
