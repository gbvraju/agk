"""Tests of the stack-keyed standards file (SPEC-0072 rules 2 and 6; REQ-079; brief #1974,
ADR-0817).

`config/standards.toml` holds the Python and Node `[[standards]]` entries, each with its `runtime`;
`check_playbooks.standard` composes the chosen runtime's entries for every work type, before the
playbook layers; a pack that is on with no composed entry prints one `not run` line; the file's form
is checked naming the key, never a value. Fixtures in `tmp_path` only: invented data (example.com),
no network.
"""

from __future__ import annotations

import shutil
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
AGK = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(AGK))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_playbooks  # noqa: E402
import kit_root  # noqa: E402
import playbook_format  # noqa: E402
import run_gates  # noqa: E402
from gates import bom, node_pack, pins, python_pack  # noqa: E402
from test_pins import with_lock  # noqa: E402
from test_python_pack import CLEAN  # noqa: E402

FILE = "config/standards.toml"
BOOKS = KIT_ROOT / "config" / "playbooks"
WORK_TYPES = sorted(p.stem for p in BOOKS.glob("*.toml") if p.stem != "default")
NONE_COMPOSED = (
    "not run standards python-pyproject: no standards entry composed (path class: "
    "config/standards.toml)"
)
PARTS = {"python": "python 3.12.7 PSF-2.0", "node": "node 22.11.0 MIT", "go": "go 1.23.4 BSD"}
SLUG = "chat-store-plugin"
SIGNALS = "config/stack-signals.toml"
RUNTIME, STACK = "(key: standards.runtime)", "(key: standards.stack)"


def record(runtime: str, status: str = "Accepted") -> str:
    return (
        f"# ADR-0002: stack options\n\n- Status: {status}\n- Date: 2026-11-20\n\n## Decision\n\n"
        f"1. **Options**\n   - Option A — one service at example.com. Parts: {PARTS[runtime]}, "
        "examplelib 1.2.3 MIT.\n3. **Chosen**: Option A\n"
    )


@pytest.fixture(autouse=True)
def _offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """No network; the `bom` step has its own tests (as in test_python_pack.py)."""

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("a standards reader opened a network connection")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(bom, "applies", lambda _root: False)


def project(
    tmp: Path,
    work_type: str | None = "data-pipeline",
    runtime: str | None = "python",
    status: str = "Accepted",
    toml: str = "",
    standards: bool = True,
) -> Path:
    """An installed project: the kit's playbooks and tables, a record, a Python product file."""
    shutil.copytree(BOOKS, tmp / "config" / "playbooks")
    shutil.copy(KIT_ROOT / "config" / "stack-signals.toml", tmp / "config")
    if standards:
        shutil.copy(KIT_ROOT / FILE, tmp / FILE)
    scope = "" if "project_lint_paths" in toml else 'project_lint_paths = ["src/**"]\n'
    text = f'mode = "init"\n{scope}{toml}\n'
    if work_type:
        text += f'\n[delivery]\nwork_type = "{work_type}"\n'
    (tmp / "agk.toml").write_text(text, encoding="utf-8")
    if runtime:
        (tmp / "docs" / "adr").mkdir(parents=True)
        (tmp / "docs/adr/0002-stack-options.md").write_text(
            record(runtime, status), encoding="utf-8"
        )
    template = KIT_ROOT / "kit/templates/stacks/python-pyproject/pyproject.toml"
    (tmp / "pyproject.toml").write_text(
        template.read_text(encoding="utf-8").replace("{{project}}", "sample"), encoding="utf-8"
    )
    (tmp / "src").mkdir()
    (tmp / "src" / "app.py").write_text(CLEAN, encoding="utf-8")
    return with_lock(tmp, runtime if runtime == "node" else "python")


def stacks(root: Path, name: str) -> list[str]:
    path = playbook_format.path(root, name)
    return [e["stack"] for e in check_playbooks.standard(path, root)[1]]


def own(work_type: str) -> list[str]:
    """The stacks a shipped playbook still carries itself (web-app, api-service, mobile: 19I-b)."""
    found = playbook_format.load(BOOKS / f"{work_type}.toml").get("standards", [])
    return [e["stack"] for e in found]


def gates(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = run_gates.main(["--root", str(root)])
    out = capsys.readouterr()
    return code, out.out + out.err


def form(tmp: Path, text: str) -> list[str]:
    root = project(tmp)
    (root / FILE).write_text(text, encoding="utf-8")
    return [ln for ln in check_playbooks.findings(root) if FILE in ln]


def entry(**changes: object) -> str:
    """The shipped python-pyproject entry as TOML, with keys changed (None drops one)."""
    data = next(e for e in tomllib.loads((KIT_ROOT / FILE).read_text())["standards"])
    data = {**data, **changes}
    lines = ["[[standards]]"]
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, dict):
            codes = ", ".join(f'"{c}"' for c in value["codes"])
            extra = f', version = "{value["version"]}"' if "version" in value else ""
            lines.append(f'{key} = {{ tool = "{value["tool"]}"{extra}, codes = [{codes}] }}')
        else:
            lines.append(f'{key} = "{value}"')
    return "\n".join(lines) + "\n"


def test_req079_the_file_holds_the_three_entries_as_web_app_holds_them() -> None:
    """Answer 1: the same step names, config, tool, version and codes, each with its runtime."""
    shipped = tomllib.loads((KIT_ROOT / FILE).read_text(encoding="utf-8"))["standards"]
    web = playbook_format.load(BOOKS / "web-app.toml")["standards"]
    assert [{k: v for k, v in e.items() if k != "runtime"} for e in shipped] == web
    assert {e["stack"]: e["runtime"] for e in shipped} == {
        "python-pyproject": "python",
        "python-pip": "python",
        "node": "node",
    }
    manifest = (KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8")
    assert f'"{FILE}"' in manifest


def test_req079_the_shipped_file_passes_its_form_check() -> None:
    """Answer 4: the kit's own file raises no finding."""
    assert check_playbooks.standards_file(KIT_ROOT)[1] == []


@pytest.mark.parametrize("work_type", WORK_TYPES)
def test_req079_every_work_type_composes_the_python_entries(work_type: str, tmp_path: Path) -> None:
    """Answers 2 and 5, Q-19I-1: the stack decides, once per stack."""
    root = project(tmp_path, work_type)
    found = stacks(root, work_type)
    assert sorted(found) == sorted({*python_pack.STACKS, *own(work_type)})


@pytest.mark.parametrize("work_type", WORK_TYPES)
def test_req079_every_work_type_composes_the_node_entry(work_type: str, tmp_path: Path) -> None:
    """Answers 2 and 5: a Node record composes the Node entry and no Python one."""
    root = project(tmp_path, work_type, runtime="node")
    assert stacks(root, work_type) == own(work_type)  # answer 6: no package.json, pack not on
    (root / "package.json").write_text('{"name": "sample"}\n', encoding="utf-8")
    found = stacks(root, work_type)
    assert sorted(found) == sorted({"node", *own(work_type)})


@pytest.mark.parametrize(
    ("work_type", "runtime", "status"),
    [(None, "python", "Accepted"), ("data-pipeline", "python", "Proposed"),
     ("data-pipeline", None, "Accepted"), ("data-pipeline", "go", "Accepted")],
)
def test_req079_no_chosen_runtime_composes_nothing_of_the_file(
    work_type: str | None, runtime: str | None, status: str, tmp_path: Path
) -> None:
    """Answer 5: no work type, a Proposed record, no record or another runtime: as today."""
    root = project(tmp_path, work_type, runtime, status)
    assert stacks(root, work_type or "default") == []


def test_req079_two_records_compose_nothing(tmp_path: Path) -> None:
    """Answer 5 and Q-19I-3: two records give no chosen runtime."""
    root = project(tmp_path)
    (root / "docs/adr/0003-stack-options.md").write_text(record("python"), encoding="utf-8")
    assert pins.chosen(root) is None and stacks(root, "data-pipeline") == []


@pytest.mark.parametrize("work_type", ["data-pipeline", "rag-app", "mobile", "pilot"])
def test_req079_a_python_project_of_any_work_type_runs_the_pack(
    work_type: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Measured: before this build no `standards` line; now the pack's lines."""
    code, out = gates(project(tmp_path, work_type), capsys)
    assert "ok standards python-pyproject" in out, out
    assert NONE_COMPOSED not in out


def test_req079_a_derived_playbook_composes_the_python_entries(tmp_path: Path) -> None:
    """Answer 5: a derived playbook name (brief #1908) with no module gets the stack's entries."""
    root = project(tmp_path, SLUG)
    research = root / "docs" / "research" / f"{SLUG}.md"
    research.parent.mkdir(parents=True)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_front_door_derive import record_text

    research.write_text(record_text(), encoding="utf-8")
    done = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(AGK / "front_door.py"), "derive-write", "--slug", SLUG,
         "--root", str(root)],
        capture_output=True, text=True, check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert sorted(stacks(root, SLUG)) == sorted(python_pack.STACKS)


def test_req079_a_playbook_entry_replaces_the_files_and_never_drops_a_code(
    tmp_path: Path,
) -> None:
    """Answers 2 and 6: one entry per stack; a weaker `rules` list is refused naming the key."""
    root = project(tmp_path, "api-service")
    assert sorted(stacks(root, "api-service")) == sorted(python_pack.STACKS)
    book = root / "config/playbooks/api-service.toml"
    text = book.read_text(encoding="utf-8")
    book.write_text(text.replace('codes = ["E", "F", "I", "B", "UP"]', 'codes = ["E"]', 1))
    found = check_playbooks.standard(book, root)[2]
    assert found == [
        "SPEC-0072 rule 2: config/playbooks/api-service.toml: a pack's `rules` drops a rule "
        "code (key: standards.rules)"
    ]


def test_req079_a_missing_file_says_no_entry_composed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Answer 3: a pack that is on with no composed entry is never silent; exit unchanged."""
    root = project(tmp_path, standards=False)
    assert check_playbooks.standards_file(root) == ([], [])
    code, out = gates(root, capsys)
    assert NONE_COMPOSED in out and code == 0, out
    assert "standards python-pyproject" in out.splitlines()[-1]


def test_req079_a_node_record_with_no_package_json_prints_nothing_new(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Answer 6: `node_pack.on` is false, so the no-pack line of brief #1685, as today."""
    root = project(tmp_path, runtime="node")
    assert not node_pack.on(root)
    _, out = gates(root, capsys)
    assert "no pack for node" in out and "no standards entry composed" not in out


def test_req079_the_warning_counts_the_files_stacks(tmp_path: Path) -> None:
    """Answer 3: `cmd_check`'s `no pack for them yet` warning counts the file's stacks."""
    root = project(tmp_path, None, None)
    for name in ("web-app", "api-service", "mobile"):
        (root / f"config/playbooks/{name}.toml").unlink()
    known = len(playbook_format.stacks(root) or [])

    def warned(path: Path) -> str:
        done = subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(AGK / "check_playbooks.py"), "--root", str(path)],
            capture_output=True, text=True, check=False,
        )
        return done.stderr

    assert f"warn playbooks: {known - 3} stacks" in warned(root)
    (root / FILE).unlink()
    assert f"warn playbooks: {known} stacks" in warned(root)


@pytest.mark.parametrize(
    ("text", "what"),
    [
        (entry(runtime=None), "an entry is missing the key `runtime` (key: standards.runtime)"),
        (entry(extra="x"), "an entry has a key outside the format (key: standards.extra)"),
        (entry(runtime="cobol"), f"a `runtime` is not a key of the stack table {RUNTIME}"),
        (entry(stack="zz-invented"), f"a `stack` is not a stack of {SIGNALS} {STACK}"),
        (entry(runtime="node"), f"a `stack` is not one the runtime's pack serves {STACK}"),
        (entry() + entry(), f"a `stack` appears twice {STACK}"),
        (entry(lint=None), "an entry is missing the key `lint` (key: standards.lint)"),
        ("[[standards]\n", "the file is not TOML (path class: config/standards.toml)"),
    ],
)
def test_req079_each_form_refusal_names_the_key(text: str, what: str, tmp_path: Path) -> None:
    """Answer 4: each refusal names the key or the path class, never a value."""
    found = form(tmp_path, text)
    assert found == [f"SPEC-0072 rule 2: {FILE}: {what}"]
    for value in ("cobol", "zz-invented", "x\n"):
        assert all(value not in line for line in found)


def test_req079_a_missing_file_has_no_finding(tmp_path: Path) -> None:
    """Answer 4: a missing file is no entries, never a finding."""
    root = project(tmp_path, standards=False)
    assert [ln for ln in check_playbooks.findings(root) if FILE in ln] == []


def _clean(tmp: Path, monkeypatch: pytest.MonkeyPatch, plugin: Path | None) -> Path:
    root = project(tmp, toml='[kit]\nlayout = "plugin"')
    shutil.rmtree(root / "config" / "playbooks")
    (root / FILE).write_text("", encoding="utf-8")  # the project's copy is never read here
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin or KIT_ROOT))
    return root


def test_req079_a_clean_project_reads_the_plugins_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Answer 5, `[kit] layout = "plugin"`: the plugin's copy, never the project's."""
    root = _clean(tmp_path, monkeypatch, None)
    assert sorted(stacks(root, "data-pipeline")) == sorted(python_pack.STACKS)


def test_req079_a_clean_project_with_no_plugin_is_refused_naming_the_setting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Answer 5: refused as `kit_root` refuses it, naming the setting."""
    elsewhere = tmp_path / "not-a-plugin"
    (elsewhere / "a" / "b").mkdir(parents=True)
    (tmp_path / "p").mkdir()
    root = _clean(tmp_path / "p", monkeypatch, elsewhere)
    monkeypatch.setattr(kit_root, "HERE", elsewhere / "a" / "b")  # not the kit's own folder
    with pytest.raises(playbook_format.Refused, match=r"\(setting: CLAUDE_PLUGIN_ROOT\)"):
        check_playbooks.standards_file(root)


@pytest.mark.parametrize(
    ("toml", "line"),
    [
        ('touched_files = "hold"', "ok standards python-pyproject"),
        ('touched_files = "meet"', "not run standards touched: no base (setting: touched_files)"),
        ('project_lint_paths = ["src/**"]', "ok standards python-pyproject"),
        ('project_lint_paths = ["none/**"]', "not run standards python-pyproject: no product file"),
        ("", "ok standards python-pyproject"),
        ('execution = "hosted"', "ok standards python-pyproject"),
        ('execution = "hybrid"', "ok standards python-pyproject"),
        ('execution = "pool"', "ok standards python-pyproject"),
        ('execution = "local"', "ok standards python-pyproject"),
        ('pr_mode = "strict"', "ok standards python-pyproject"),
        ('pr_mode = "flow"', "ok standards python-pyproject"),
        ('review_mode = "solo"', "ok standards python-pyproject"),
        ('review_mode = "team"', "ok standards python-pyproject"),
        ('[personal]\nforge = "files"', "ok standards python-pyproject"),
    ],
)
def test_req079_each_setting_applies_to_a_file_entry_as_to_a_playbook_entry(
    toml: str, line: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Answer 5: no new setting and no new value; each value runs the same pack lines."""
    _, out = gates(project(tmp_path, toml=toml), capsys)
    assert line in out, out
    assert NONE_COMPOSED not in out


def test_req079_adopt_mode_holds_a_file_entry_in_the_baseline(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Answer 5, `mode = "adopt"`: a finding is written to the baseline, as for a playbook's."""
    root = project(tmp_path)
    (root / "agk.toml").write_text(
        (root / "agk.toml").read_text().replace('mode = "init"', 'mode = "adopt"'), encoding="utf-8"
    )
    (root / "src" / "app.py").write_text("import json\n", encoding="utf-8")
    code, out = gates(root, capsys)
    assert code == 0, out
    assert (root / "config/agk-baseline/standards-python-pyproject-lint.txt").is_file()


def test_req079_the_kit_itself_composes_nothing_of_the_file() -> None:
    """Answer 6: no work type in the kit, so its run is unchanged."""
    assert pins.chosen(KIT_ROOT) is None
    assert stacks(KIT_ROOT, "default") == []
