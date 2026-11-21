"""Tests of the architecture record and the `layers` step (SPEC-0072 rules 5 and 8; REQ-079
AC4 and AC6; brief #1588, ADR-0668).

On a sample feature build of a work-type project a disallowed layer import, absolute or relative,
fails naming both layers and the path class and no value; an allowed one, a standard library
import and a project with no work type pass; a non-Python stack prints `not run`, never `ok`; the
foundation writes `docs/architecture.md` from the template once; the record is a protected path of
every project template; a build brief without `Layer:`, with an unknown layer or missing a layer
its `Touches:` meets is refused, while the foundation brief and a project with no work type need
none; and the builder prompt names the record. Fixtures in `tmp_path` only: invented data, no
network.
"""

from __future__ import annotations

import shutil
import socket
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
AGK = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(AGK))

import check_brief  # noqa: E402
import run_gates  # noqa: E402
from gates import layers  # noqa: E402

PLAYBOOKS = KIT_ROOT / "config" / "playbooks"
PLANTED = "INVENTEDPLANTEDWORD"
SAMPLE = {
    "contracts/__init__.py": "",
    "contracts/orders.py": "SHAPE = {'site': 'https://example.com'}\n",
    "api/__init__.py": "",
    "api/routes.py": "import json\nfrom domain import rules\nfrom contracts.orders import SHAPE\n",
    "domain/__init__.py": "",
    "domain/rules.py": "import data.store\nfrom . import helpers\n",
    "domain/helpers.py": "",
    "data/__init__.py": "",
    "data/store.py": "import os\n",
}


def _project(tmp_path: Path, work_type: str | None = "api-service") -> Path:
    shutil.copytree(PLAYBOOKS, tmp_path / "config" / "playbooks")
    text = 'mode = "init"\n'
    if work_type:
        text += f'\n[delivery]\nwork_type = "{work_type}"\n'
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    for rel, body in SAMPLE.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(body, encoding="utf-8")
    return tmp_path


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the layers step opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def _gates(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = run_gates.main(["--root", str(root)])
    return code, capsys.readouterr().out


def test_allowed_imports_pass(tmp_path: Path, no_network: None, capsys) -> None:
    """REQ-079 AC4."""
    code, out = _gates(_project(tmp_path), capsys)
    assert code == 0, out
    assert "ok layers\n" in out


@pytest.mark.parametrize(
    ("rel", "body"),
    [
        ("data/store.py", f"from api import routes  # {PLANTED}\n"),
        ("data/store.py", f"import api.routes as {PLANTED.lower()}\n"),
        ("data/deep/repo.py", "from ...api import routes\n"),
    ],
)
def test_a_disallowed_import_fails_naming_both_layers_and_the_path_class(
    rel: str, body: str, tmp_path: Path, no_network: None, capsys
) -> None:
    """REQ-079 AC4: data may not import api; the line names no file, module or value."""
    root = _project(tmp_path)
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(body, encoding="utf-8")
    code, out = _gates(root, capsys)
    assert code == 1
    assert "FAIL gates: layers: SPEC-0072 rule 5: " in out
    assert "(path class: data/**; layers: data to api)" in out
    for value in (PLANTED, PLANTED.lower(), "routes", "store.py", "repo.py"):
        assert value not in out


def test_a_reverse_direction_is_refused_too(tmp_path: Path, capsys) -> None:
    """REQ-079 AC4: `allow` names api to domain, never domain to api."""
    root = _project(tmp_path)
    (root / "domain/back.py").write_text("from api.routes import x\n", encoding="utf-8")
    code, out = _gates(root, capsys)
    assert code == 1 and "(path class: domain/**; layers: domain to api)" in out


def test_an_unreadable_source_file_fails_naming_its_layer(tmp_path: Path, capsys) -> None:
    """REQ-079 AC4: a file the reader cannot parse is never a silent pass."""
    root = _project(tmp_path)
    (root / "api/broken.py").write_text("def (:\n", encoding="utf-8")
    code, out = _gates(root, capsys)
    assert code == 1 and "FAIL gates: layers: " in out and "(path class: api/**" in out


def test_no_work_type_constrains_nothing(tmp_path: Path, no_network: None, capsys) -> None:
    """REQ-079 AC4: `default.toml`'s one `src` layer; the same import is green."""
    root = _project(tmp_path, None)
    (root / "data/store.py").write_text("from api import routes\n", encoding="utf-8")
    code, out = _gates(root, capsys)
    # `default.toml`'s two checks since brief #1593 (ADR-0673); no `layers` line
    gates = "not run tests-first: no work type\nok secrets\nok environment-settings\n"
    gates += "ok gates (3 check gates; not run: tests-first)\n"  # brief #1590 (ADR-0670)
    assert code == 0 and out == gates


STACK_RECORD = (
    "# ADR-0003: Stack options\n\n- Status: Accepted\n\n"
    "1. **Options**:\n   - Option A — Parts: node 22.11.0 MIT. Why: invented.\n"
    "3. **Chosen**: Option A\n"
)


def test_a_non_python_stack_is_not_run_never_ok(tmp_path: Path, capsys) -> None:
    """REQ-079 AC4, brief #1588 Q-1: `not run: no reader for <stack>` until its reader exists."""
    root = _project(tmp_path)
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "docs/adr/0003-stack-options.md").write_text(STACK_RECORD, encoding="utf-8")
    (root / "data/store.py").write_text("from api import routes\n", encoding="utf-8")
    code, out = _gates(root, capsys)
    assert code == 0
    assert "not run layers: no reader for node\n" in out and "ok layers" not in out
    # the checks of briefs #1593 (ADR-0673), #1590 (ADR-0670) and contract-tests (ADR-0677)
    idle = "tests-first, contract-tests, layers"
    assert out.splitlines()[-1] == f"ok gates (5 check gates; not run: {idle})"


def test_windows_line_ends_and_paths_compare_by_forward_slash(tmp_path: Path, capsys) -> None:
    """REQ-079 AC4."""
    root = _project(tmp_path)
    (root / "data/store.py").write_bytes(b"import os\r\nfrom api import routes\r\n")
    code, out = _gates(root, capsys)
    assert code == 1 and "(path class: data/**; layers: data to api)" in out


# --- the architecture record (rule 5) ------------------------------------------------------------


def test_the_foundation_writes_the_record_from_the_template_once(tmp_path: Path, capsys) -> None:
    """REQ-079 AC4: the layers, their paths, the allowed directions and the stack record's ADR."""
    template = (KIT_ROOT / "kit/templates/architecture.md").read_text(encoding="utf-8")
    assert "{{layers}}" in template and "{{allow}}" in template and "{{stack_adr}}" in template
    root = _project(tmp_path)
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "docs/adr/0003-stack-options.md").write_text(STACK_RECORD, encoding="utf-8")
    assert layers.main(["--root", str(root), "--write-record"]) == 0
    text = (root / "docs/architecture.md").read_text(encoding="utf-8")
    assert "| `api` | `api/**` |" in text and "- `domain` may import `data`" in text
    assert "ADR-0003" in text and "{{" not in text
    capsys.readouterr()
    (root / "docs/architecture.md").write_text("kept\n", encoding="utf-8")
    assert layers.main(["--root", str(root), "--write-record"]) == 1
    assert "exists" in capsys.readouterr().out
    assert (root / "docs/architecture.md").read_text(encoding="utf-8") == "kept\n"


def test_no_work_type_writes_no_record(tmp_path: Path, capsys) -> None:
    """REQ-079 AC6: the record needs a work type, refused naming the setting."""
    root = _project(tmp_path, None)
    assert layers.main(["--root", str(root), "--write-record"]) == 1
    assert "(setting: work_type)" in capsys.readouterr().out
    assert not (root / "docs/architecture.md").exists()


@pytest.mark.parametrize(
    "rel",
    [
        "kit/templates/protected-paths.txt",
        "kit/templates/protected-paths.adopt.txt",
        "kit/templates/reviewers.yaml",
        "kit/templates/reviewers.adopt.yaml",
    ],
)
def test_the_record_is_a_protected_path_of_every_project(rel: str) -> None:
    """REQ-079 AC4: the record changes only by an ADR in the project."""
    assert "docs/architecture.md" in (KIT_ROOT / rel).read_text(encoding="utf-8")


def test_the_builder_prompt_reads_the_record_and_the_pack() -> None:
    """REQ-079 AC6: write to the standard, not only check it (rule 8). The agent file holds no
    rule of its own (its rule budget) and points to the task text, which holds this one."""
    text = (KIT_ROOT / "kit/templates/runtime/builder.txt").read_text(encoding="utf-8")
    assert "docs/architecture.md" in text and "pack" in text
    agent = (KIT_ROOT / ".claude/agents/builder.md").read_text(encoding="utf-8")
    assert "kit/templates/runtime/builder.txt" in agent


# --- the Layer: line (rule 8) --------------------------------------------------------------------

BRIEF = 'Sentence: "x"\nTouches: api/routes.py, domain/**, tests/api/**\n'


@pytest.mark.parametrize(
    ("extra", "found"),
    [
        ("", "SPEC-0072 rule 8: a build brief of a work-type project has no Layer: line"),
        ("Layer: api, domain\nLayer: api\n", "SPEC-0072 rule 8: a build brief of a work-type"),
        ("Layer: api, domain, " + PLANTED + "\n", "SPEC-0072 rule 8: a Layer: entry is no layer"),
        ("Layer: api\n", "SPEC-0072 rule 8: the Layer: line misses a layer that Touches meets"),
    ],
)
def test_a_brief_without_a_sound_layer_line_is_refused(
    extra: str, found: str, tmp_path: Path
) -> None:
    """REQ-079 AC6, Q-S0072-15."""
    root = _project(tmp_path)
    problems = check_brief.layer_problems(BRIEF + extra, root)
    assert problems and problems[0].startswith(found)
    assert PLANTED not in " ".join(problems)


def test_a_sound_layer_line_passes(tmp_path: Path) -> None:
    """REQ-079 AC6."""
    assert check_brief.layer_problems(BRIEF + "Layer: api, domain\n", _project(tmp_path)) == []


def test_the_foundation_brief_and_no_work_type_need_no_line(tmp_path: Path) -> None:
    """REQ-079 AC6: the foundation brief itself, and a project with no work type, need none."""
    assert check_brief.layer_problems(BRIEF + "Kind: foundation\n", _project(tmp_path)) == []
    other = tmp_path / "other"
    other.mkdir()
    assert check_brief.layer_problems(BRIEF, _project(other, None)) == []
