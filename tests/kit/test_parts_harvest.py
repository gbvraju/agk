"""Kit tests: an adopted project's parts are harvested inferred, with a green baseline that
ratchets (SPEC-0076 build (g), rule 10; SPEC-0072 rule 7; SPEC-0059 rule 20; brief #2074,
ADR-0864; REQ-083).

On saved git trees (invented names, example.com): `parts.py --harvest` drafts `docs/parts.md`
from the build files and locks, every row `inferred`; the first `mode = "adopt"` run writes
`config/agk-baseline/parts.txt` and prints `parts (baseline): <n> held`; a new dependency without
its row and a touched inferred row fail; completing a row lowers the line. Onboarding and
`detect` name the record. No network, no model.
"""

from __future__ import annotations

import json
import shutil
import socket
import subprocess  # nosec B404 - the test drives git with fixed argument lists
import sys
from pathlib import Path

import pytest
from test_pins import NODE_PARTS, PY_PARTS, project, record

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import front_door  # noqa: E402
import parts_record  # noqa: E402
import run_gates  # noqa: E402
import steward_onboard  # noqa: E402
from gates import baseline, parts  # noqa: E402

AT = "2026-12-01"
ADOPT = 'mode = "adopt"\n\n[delivery]\nwork_type = "web-app"\n\n[parts]\nrecord = "required"\n'
BASE_FILE = "config/agk-baseline/parts.txt"
HELD_40 = (run_gates.HELD, "parts (baseline): 40 held (path class: docs/parts.md)")
FULL = (
    "| http-client | {name} | {version} | runtime | REQ-001; a small client | none | MIT "
    "| maintained (read {today}, https://example.com/registry) | Calls example.com. |"
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the harvest opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    for name in ("AGK_BASE", "GITHUB_BASE_REF", "CI"):
        monkeypatch.delenv(name, raising=False)


def git(root: Path, *args: str) -> None:
    subprocess.run(  # nosec B603 B607 - fixed git arguments, no shell
        ["git", *args], cwd=root, check=True, capture_output=True
    )


def commit(root: Path, message: str = "base") -> Path:
    if not (root / ".git").exists():
        git(root, "init", "-q", "-b", "main")
        git(root, "config", "user.email", "t@example.invalid")
        git(root, "config", "user.name", "t")
        git(root, "config", "commit.gpgsign", "false")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return root


def deps40() -> tuple[dict[str, str], dict[str, str]]:
    runtime = {"example-web": "4.21.1", "express": "4.21.2"}
    runtime.update({f"example-lib-{n:02d}": f"1.0.{n}" for n in range(3, 31)})
    dev = {f"example-dev-{n:02d}": f"2.0.{n}" for n in range(1, 11)}
    return runtime, dev


def write_node(root: Path, runtime: dict, dev: dict, lock: bool = True) -> None:
    pkg = {"name": "sample", "version": "0.0.0", "dependencies": runtime, "devDependencies": dev}
    (root / "package.json").write_text(json.dumps(pkg, indent=1), encoding="utf-8")
    if lock:
        packages: dict = {"": {"name": "sample"}}
        for name, version in {**runtime, **dev}.items():
            packages[f"node_modules/{name}"] = {"version": version, "license": "MIT"}
        text = json.dumps({"lockfileVersion": 3, "packages": packages}, indent=1)
        (root / "package-lock.json").write_text(text, encoding="utf-8")


def node40(tmp: Path, toml: str = ADOPT, lock: bool = True) -> Path:
    """The brief's fixture: 30 `dependencies` and 10 `devDependencies`, with a lock."""
    text = record(a_parts=NODE_PARTS, status="Accepted", chosen="Option A")
    root = project(tmp, text, toml=toml)
    shutil.copytree(KIT_ROOT / "config" / "parts", root / "config" / "parts")  # installed layout
    write_node(root, *deps40(), lock=lock)
    return commit(root)


def harvest(root: Path, capsys) -> tuple[int, list[str]]:
    code = parts.main(["--harvest", "--at", AT, "--root", str(root)])
    return code, capsys.readouterr().out.splitlines()


def rows_of(root: Path, write: bool = False) -> list[tuple[object, str]]:
    found = run_gates.results(root, write)
    return [r for r in found if r[1].startswith(("parts", "warn parts", "baseline parts"))]


def harvested(tmp: Path, capsys, toml: str = ADOPT) -> Path:
    root = node40(tmp, toml)
    assert harvest(root, capsys)[0] == 0
    return commit(root, "harvest")


def complete(root: Path, name: str, version: str) -> None:
    """Replace the row of NAME with its full row (the architect completes it)."""
    path = root / parts.RECORD
    lines = path.read_text(encoding="utf-8").splitlines()
    full = FULL.format(name=name, version=version, today=parts.datetime.date.today())
    out = [full if ln.startswith(("| unassigned | " + name + " |",)) else ln for ln in lines]
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def add_row(root: Path, name: str, version: str) -> None:
    path = root / parts.RECORD
    lines = path.read_text(encoding="utf-8").splitlines()
    last = max(i for i, ln in enumerate(lines) if ln.startswith("|"))
    lines.insert(
        last + 1, FULL.format(name=name, version=version, today=parts.datetime.date.today())
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# Answer 1: the harvest.


def test_req083_the_harvest_writes_forty_inferred_rows(tmp_path: Path, capsys) -> None:
    root = node40(tmp_path)
    code, out = harvest(root, capsys)
    assert code == 0
    assert out == ["parts: harvested 40 rows (1 needs named, 39 unassigned)", "protected: none"]
    text = (root / parts.RECORD).read_text(encoding="utf-8")
    rows = parts_record.rows(text)["node"]
    assert len(rows) == 40
    assert [r["Part"] for r in rows][:3] == ["example-web", "express", "example-lib-03"]
    assert all(r["Why"].startswith("inferred") for r in rows)
    by = {r["Part"]: r for r in rows}
    assert by["example-web"]["Why"] == "inferred: from the stack record"
    assert by["example-lib-03"]["Why"] == "inferred: not recorded"
    assert by["express"]["Need"] == "web-api"
    assert by["example-lib-03"]["Need"] == "unassigned"
    assert sum(r["Kind"] == "dev" for r in rows) == 10
    assert by["example-dev-01"]["Kind"] == "dev"
    assert by["example-lib-03"] == {
        "Need": "unassigned",
        "Part": "example-lib-03",
        "Version": "1.0.3",
        "Kind": "runtime",
        "Why": "inferred: not recorded",
        "Alternatives considered": "not recorded",
        "Licence": "MIT",
        "Health (date)": f"not read ({AT})",
        "For the business": "not recorded",
    }
    assert text.rstrip().splitlines()[-1] == f"Confirmed by: not yet (harvested {AT})"
    assert not parts.confirmed(root)
    assert not (root / BASE_FILE).exists()


def test_req083_an_existing_record_refuses_the_harvest(tmp_path: Path, capsys) -> None:
    root = node40(tmp_path)
    (root / parts.RECORD).write_text("# Parts\n", encoding="utf-8")
    code, out = harvest(root, capsys)
    assert code == 1
    assert "docs/parts.md" in out[0] and out[0].startswith("refused: SPEC-0076 rule 10")
    assert (root / parts.RECORD).read_text(encoding="utf-8") == "# Parts\n"


def test_req083_the_harvest_takes_a_utc_date(tmp_path: Path, capsys) -> None:
    root = node40(tmp_path)
    assert parts.main(["--harvest", "--root", str(root)]) == 2
    assert parts.main(["--harvest", "--at", "tomorrow", "--root", str(root)]) == 2
    assert not (root / parts.RECORD).exists()


def test_req083_a_missing_lock_records_no_version_or_licence(tmp_path: Path, capsys) -> None:
    text = record(a_parts=NODE_PARTS, status="Accepted", chosen="Option A")
    root = project(tmp_path, text, toml=ADOPT)
    write_node(root, {"example-web": "4.21.1", "example-float": "^1.0.0"}, {}, lock=False)
    assert harvest(commit(root), capsys)[0] == 0
    by = {r["Part"]: r for r in parts_record.rows((root / parts.RECORD).read_text())["node"]}
    assert by["example-web"]["Version"] == "4.21.1"
    assert by["example-float"]["Version"] == "not recorded"
    assert by["example-float"]["Licence"] == "not recorded"


def test_req083_a_python_tree_is_harvested(tmp_path: Path, capsys) -> None:
    text = record(a_parts=PY_PARTS, status="Accepted", chosen="Option A")
    root = project(tmp_path, text, toml=ADOPT)
    (root / "requirements.txt").write_text("examplelib==1.2.3\nexample-req>=2\n", encoding="utf-8")
    (root / "requirements.lock").write_text(
        "examplelib==1.2.3\nexample-req==2.0.1\n", encoding="utf-8"
    )
    code, out = harvest(commit(root), capsys)
    assert code == 0 and out[0] == "parts: harvested 2 rows (0 needs named, 2 unassigned)"
    rows = parts_record.rows((root / parts.RECORD).read_text())["python"]
    by = {r["Part"]: r for r in rows}
    assert by["examplelib"]["Why"] == "inferred: from the stack record"
    assert by["examplelib"]["Licence"] == "MIT"
    assert by["example-req"]["Version"] == "2.0.1"
    assert {r["Kind"] for r in rows} == {"runtime"}


def test_req083_optional_dependency_groups_are_dev(tmp_path: Path, capsys) -> None:
    root = project(tmp_path, None, toml=ADOPT)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "s"\nversion = "0"\ndependencies = ["examplelib==1.2.3"]\n'
        '[project.optional-dependencies]\ntest = ["example-test==1.0.0"]\n',
        encoding="utf-8",
    )
    assert harvest(commit(root), capsys)[0] == 0
    by = {r["Part"]: r for r in parts_record.rows((root / parts.RECORD).read_text())["python"]}
    assert (by["examplelib"]["Kind"], by["example-test"]["Kind"]) == ("runtime", "dev")
    assert by["examplelib"]["Why"] == "inferred: not recorded"  # no stack record here


def test_req083_an_unreadable_build_file_and_a_stack_with_no_reader(tmp_path: Path, capsys) -> None:
    root = project(tmp_path, None, toml=ADOPT)
    (root / "web").mkdir()
    (root / "web" / "package.json").write_text("not json", encoding="utf-8")
    (root / "go.mod").write_text("module example.com/s\n", encoding="utf-8")
    (root / "requirements.txt").write_text("examplelib==1.2.3\n", encoding="utf-8")
    code, out = harvest(commit(root), capsys)
    assert code == 0
    assert "parts: not harvested package.json: cannot be read" in out
    assert "parts: no reader for this stack" in out
    assert out[-2:] == ["parts: harvested 1 rows (0 needs named, 1 unassigned)", "protected: none"]
    assert list(parts_record.rows((root / parts.RECORD).read_text())) == ["python"]


def test_req083_nothing_to_harvest_writes_nothing(tmp_path: Path, capsys) -> None:
    root = project(tmp_path, None, toml=ADOPT)
    (root / "go.mod").write_text("module example.com/s\n", encoding="utf-8")
    code, out = harvest(commit(root), capsys)
    assert code == 1 and out[-1] == "parts: nothing harvested; nothing is written"
    assert not (root / parts.RECORD).exists()


def test_req083_two_runtimes_in_two_folders_are_two_sections(tmp_path: Path, capsys) -> None:
    root = project(tmp_path, None, toml=ADOPT)
    (root / "web").mkdir()
    write_node(root / "web", {"example-web": "4.21.1"}, {})
    (root / "api").mkdir()
    (root / "api" / "requirements.txt").write_text("examplelib==1.2.3\n", encoding="utf-8")
    assert harvest(commit(root), capsys)[0] == 0
    found = parts_record.rows((root / parts.RECORD).read_text())
    assert {k: [r["Part"] for r in v] for k, v in found.items()} == {
        "python": ["examplelib"],
        "node": ["example-web"],
    }


# Answers 2 and 8: the baseline, and the class stays closed.


def test_req083_the_first_adopt_run_writes_the_baseline_held(tmp_path: Path, capsys) -> None:
    root = harvested(tmp_path, capsys)
    assert parts.counts(root, {}) == {"docs/parts.md": 40}  # no build-file finding (answer 8)
    assert rows_of(root) == [
        HELD_40,
        (run_gates.NOTE, "baseline parts: written (path class: config/agk-baseline/)"),
    ]
    assert (root / BASE_FILE).read_text(encoding="utf-8") == "docs/parts.md 40\n"
    assert rows_of(root) == [HELD_40]


def test_req083_a_new_dependency_needs_its_full_row(tmp_path: Path, capsys) -> None:
    root = harvested(tmp_path, capsys)
    rows_of(root)
    runtime, dev = deps40()
    write_node(root, {**runtime, "example-new": "1.0.0"}, dev)
    assert (False, f"parts: {baseline.RULE} (path class: {baseline.CLASS})") in rows_of(root)
    add_row(root, "example-new", "1.0.0")
    assert rows_of(root) == [HELD_40]


def test_req083_a_touched_inferred_row_needs_its_full_row(tmp_path: Path, capsys) -> None:
    root = harvested(tmp_path, capsys)
    rows_of(root)
    commit(root, "baseline")
    git(root, "checkout", "-q", "-b", "feature")
    runtime, dev = deps40()
    write_node(root, {**runtime, "example-lib-03": "1.0.99"}, dev)
    path = root / parts.RECORD
    path.write_text(
        path.read_text(encoding="utf-8").replace("| 1.0.3 |", "| 1.0.99 |"), encoding="utf-8"
    )
    assert parts.counts(root, {}) == {"docs/parts.md": 40, "package.json": 1}
    assert (False, f"parts: {baseline.RULE} (path class: {baseline.CLASS})") in rows_of(root)
    complete(root, "example-lib-03", "1.0.99")
    assert rows_of(root) == [
        (run_gates.HELD, "parts (baseline): 39 held (path class: docs/parts.md)"),
        (
            run_gates.NOTE,
            "baseline parts: a count fell in 1 file (path class: config/agk-baseline/)",
        ),
    ]


def test_req083_completing_a_row_and_baseline_lowers_the_line(tmp_path: Path, capsys) -> None:
    root = harvested(tmp_path, capsys)
    rows_of(root)
    complete(root, "example-lib-03", "1.0.3")
    rows_of(root, write=True)
    assert (root / BASE_FILE).read_text(encoding="utf-8") == "docs/parts.md 39\n"


def test_req083_the_harvest_is_the_only_writer_of_inferred_rows() -> None:
    writers = [
        p.relative_to(KIT_ROOT).as_posix()
        for p in (KIT_ROOT / "scripts" / "agk").rglob("*.py")
        if parts.INFERRED in p.read_text(encoding="utf-8")
    ]
    assert writers == ["scripts/agk/gates/parts.py"]


# Answer 5: the settings.


def test_req083_init_mode_writes_no_baseline(tmp_path: Path, capsys) -> None:
    root = harvested(tmp_path, capsys, toml=ADOPT.replace('mode = "adopt"', 'mode = "init"'))
    assert all(r[0] is False for r in rows_of(root))
    assert rows_of(root)
    assert not (root / BASE_FILE).exists()


def test_req083_optional_warns_and_still_writes_the_baseline(tmp_path: Path, capsys) -> None:
    root = harvested(tmp_path, capsys, toml=ADOPT.replace("required", "optional"))
    found = rows_of(root)
    assert (run_gates.HELD, f"parts: 1 warning ({parts.NOTED})") in found
    assert not [r for r in found if r[0] is True or r[0] is False]
    assert (root / BASE_FILE).read_text(encoding="utf-8") == "docs/parts.md 40\n"
    (root / "agk.toml").write_text(
        (root / "agk.toml").read_text().replace("optional", "required"), encoding="utf-8"
    )
    assert rows_of(root) == [HELD_40]


def test_req083_a_refused_table_writes_no_baseline(tmp_path: Path, capsys) -> None:
    root = harvested(tmp_path, capsys, toml=ADOPT.replace('"required"', '"maybe"'))
    found = rows_of(root)
    assert found and all(r[0] is False and "parts.record" in r[1] for r in found)
    assert not (root / BASE_FILE).exists()


def test_req083_a_not_read_health_is_a_row_finding_never_a_date(tmp_path: Path, capsys) -> None:
    toml = ADOPT + "max_age_months = 1\n"
    root = harvested(tmp_path, capsys, toml=toml)
    assert parts.counts(root, {}) == {"docs/parts.md": 40}
    assert rows_of(root)[0] == HELD_40


def test_req083_no_work_type_runs_no_step_and_writes_no_baseline(tmp_path: Path, capsys) -> None:
    root = harvested(tmp_path, capsys, toml='mode = "adopt"\n')
    assert rows_of(root) == []
    assert not (root / BASE_FILE).exists()


# Answer 3: onboarding.


def test_req083_onboarding_notes_the_record_or_its_gap(tmp_path: Path, capsys) -> None:
    root = node40(tmp_path)
    gaps: list = []
    assert steward_onboard.from_parts(root, gaps) == []
    assert gaps == ["no parts record: parts.py --harvest drafts one (source: package.json)"]
    harvest(root, capsys)
    gaps = []
    assert steward_onboard.from_parts(root, gaps) == [
        "docs/parts.md: 40 parts, 0 confirmed, 40 inferred (source: docs/parts.md)"
    ]
    assert gaps == []
    (root / parts.RECORD).write_bytes(b"\xff\xfe")
    assert steward_onboard.from_parts(root, gaps) == []
    assert gaps == ["docs/parts.md cannot be read"]


def test_req083_onboarding_with_no_build_file_says_nothing(tmp_path: Path) -> None:
    gaps: list = []
    assert steward_onboard.from_parts(project(tmp_path, None), gaps) == [] and gaps == []


def test_req083_harvest_calls_from_parts() -> None:
    source = Path(steward_onboard.__file__).read_text(encoding="utf-8")
    body = source.split("def harvest(", 1)[1].split("\ndef ", 1)[0]
    assert body.index("from_domain(") < body.index("from_parts(")


# Answer 4: detect.


def test_req083_detect_names_the_parts_record(tmp_path: Path, capsys) -> None:
    root = node40(tmp_path)
    facts = front_door.detect_facts(root, KIT_ROOT)
    assert facts["parts"] == [{"build": "package.json", "count": 40, "record": False}]
    want = 'parts: 40 direct dependencies in "package.json", no parts record'
    want += " (proposed: parts.py --harvest)"
    assert want in front_door.detect_lines(facts)
    harvest(root, capsys)
    commit(root, "harvest")
    assert "parts: record present" in front_door.detect_lines(
        front_door.detect_facts(root, KIT_ROOT)
    )


def test_req083_detect_with_no_kit_copy_of_pins(tmp_path: Path, monkeypatch) -> None:
    root = node40(tmp_path)
    monkeypatch.setitem(sys.modules, "gates.pins", None)
    facts = front_door.detect_facts(root, KIT_ROOT)
    assert "parts: not read (no kit copy)" in front_door.detect_lines(facts)
