"""Tests of the playbook resolver in a clean-layout project (REQ-078; brief #1666, ADR-0697).

A clean project (`[kit] layout = "plugin"`) carries no `config/playbooks/`: every reader takes the
project's own file of a name when it has one, else the plugin's. Each shipped work type selects the
plugin's file; a project file wins; no playbook anywhere fails naming the setting; the gates, the
layers step and the plan's foundation rule run in the clean fixture; the installed layout is
unchanged. Fixtures in `tmp_path` only: invented data, no network.
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

import check_plan  # noqa: E402
import check_playbooks  # noqa: E402
import engines  # noqa: E402
import kit_root  # noqa: E402
import playbook_format  # noqa: E402
import run_gates  # noqa: E402

PLUGIN_BOOKS = KIT_ROOT / "config" / "playbooks"
WORK_TYPES = sorted(p.stem for p in PLUGIN_BOOKS.glob("*.toml") if p.stem != "default")
LAYERED = {
    "api/__init__.py": "",
    "api/routes.py": "from domain import rules\n",
    "domain/__init__.py": "",
    "domain/rules.py": "import data.store\n",
    "data/__init__.py": "",
    "data/store.py": "import os\n",
    "contracts/__init__.py": "",
}


@pytest.fixture(autouse=True)
def plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    """The kit repository is the plugin, named by the variable; no network."""
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(KIT_ROOT))

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("a playbook reader opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def _clean(tmp_path: Path, work_type: str | None, layout: str = "plugin") -> Path:
    text = f'mode = "init"\n\n[kit]\nlayout = "{layout}"\n'
    if work_type:
        text += f'\n[delivery]\nwork_type = "{work_type}"\n'
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("work_type", WORK_TYPES)
def test_each_shipped_work_type_selects_the_plugins_file(work_type: str, tmp_path: Path) -> None:
    """REQ-078."""
    root = _clean(tmp_path, work_type)
    assert playbook_format.declaration(root) == (work_type, [])
    assert playbook_format.selected(root) == PLUGIN_BOOKS / f"{work_type}.toml"
    assert check_playbooks.findings(root) == []


def test_no_work_type_reads_the_plugins_default(tmp_path: Path) -> None:
    """REQ-078."""
    root = _clean(tmp_path, None)
    assert playbook_format.selected(root) is None
    assert playbook_format.default_playbook(root) == PLUGIN_BOOKS / "default.toml"
    assert run_gates.playbook(root) == PLUGIN_BOOKS / "default.toml"


def test_a_project_file_wins_and_is_checked(tmp_path: Path) -> None:
    """REQ-078: the project's own file of a shipped name is read and checked."""
    root = _clean(tmp_path, "web-app")
    own = root / "config" / "playbooks"
    own.mkdir(parents=True)
    shutil.copy(PLUGIN_BOOKS / "web-app.toml", own / "web-app.toml")
    assert playbook_format.selected(root) == own / "web-app.toml"
    assert playbook_format.playbooks(root) == [own / "web-app.toml"]
    (own / "web-app.toml").write_text('work_type = "web-app"\n', encoding="utf-8")
    assert any("web-app.toml" in line for line in check_playbooks.findings(root))


def test_a_module_resolves_through_the_resolver(tmp_path: Path) -> None:
    """REQ-078: a playbook's `modules` name the plugin's shipped files in a clean project."""
    root = _clean(tmp_path, None)
    own = root / "config" / "playbooks"
    own.mkdir(parents=True)
    (own / "invented.toml").write_text('modules = ["web-app"]\n', encoding="utf-8")
    assert playbook_format.modules(own / "invented.toml", root) == ["web-app"]


def test_the_installed_layout_is_unchanged(tmp_path: Path) -> None:
    """REQ-078: installed reads the project's folder alone, as before."""
    root = _clean(tmp_path, "data-pipeline", layout="installed")
    assert playbook_format.folder(root) == root / "config" / "playbooks"
    _, found = playbook_format.declaration(root)
    assert found and "missing under config/playbooks/" in found[0]
    assert found[0].endswith("(setting: work_type)")


def test_another_layout_is_refused_naming_layout(tmp_path: Path) -> None:
    root = _clean(tmp_path, "web-app", layout="invented")
    _, found = playbook_format.declaration(root)
    assert found == ["kit_root: [kit] layout is neither installed nor plugin (setting: layout)"]


def test_an_unknown_work_type_is_refused_as_today(tmp_path: Path) -> None:
    root = _clean(tmp_path, "invented-kind")
    _, found = playbook_format.declaration(root)
    assert found and found[0].endswith("(setting: work_type)") and "invented" not in found[0]


def test_no_playbook_anywhere_fails_naming_the_setting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-078: no plugin root, so no playbook: never `ok gates (no check gate)`."""
    elsewhere = tmp_path / "not-a-plugin"
    (elsewhere / "a" / "b").mkdir(parents=True)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(elsewhere))
    monkeypatch.setattr(kit_root, "HERE", elsewhere / "a" / "b")
    (tmp_path / "project").mkdir()
    root = _clean(tmp_path / "project", None)
    assert run_gates.main(["--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert "FAIL gates: playbook: " in out and "(path class: config/playbooks/)" in out
    assert "no check gate" not in out
    _clean(root, "data-pipeline")
    _, found = playbook_format.declaration(root)
    assert found and found[0].endswith("(setting: CLAUDE_PLUGIN_ROOT)")
    assert run_gates.main(["--root", str(root)]) == 1
    assert "(setting: work_type)" in capsys.readouterr().out


def test_the_gates_of_a_clean_data_pipeline_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-078: the gates of the declared work type run from the plugin's playbook."""
    root = _clean(tmp_path, "data-pipeline")
    run_gates.main(["--root", str(root)])
    out = capsys.readouterr().out
    assert "ok secrets\n" in out and "ok environment-settings\n" in out
    assert "no check gate" not in out


def test_a_layers_violation_fails_in_the_clean_fixture(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-078: data may not import api, read from the plugin's api-service playbook."""
    root = _clean(tmp_path, "api-service")
    for rel, body in {**LAYERED, "data/store.py": "from api import routes\n"}.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    assert run_gates.main(["--root", str(root)]) == 1
    assert "(path class: data/**; layers: data to api)" in capsys.readouterr().out


def test_check_plan_refuses_a_plan_with_no_foundation_brief(tmp_path: Path) -> None:
    """REQ-078: the foundation-first rule runs in the clean fixture."""
    root = _clean(tmp_path, "web-app")
    briefs = root / check_plan.BRIEFS
    briefs.mkdir(parents=True)
    (briefs / "b1.md").write_text("# Invented\n\nKind: front-end\n", encoding="utf-8")
    found = check_plan.foundation_problems(root)
    assert found and "no brief is Kind: foundation" in found[0]


def test_check_plan_says_not_run_when_the_playbook_is_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-078: a missing declared playbook is `not run`, never a silent pass."""
    root = _clean(tmp_path, "web-app", layout="installed")
    (root / check_plan.PLAN).mkdir(parents=True)
    check_plan.cmd_check(root)
    out = capsys.readouterr().out
    assert "not run plan work-type rules: " in out and "(setting: work_type)" in out
    assert "ok plan" not in out


def test_engines_read_the_plugins_playbook(tmp_path: Path) -> None:
    """REQ-078: the discovery questions and practices come from the plugin's file."""
    root = _clean(tmp_path, "web-app")
    assert engines.playbook_questions(root, "web-app")
    assert engines.playbook_practices(root) is not None
    assert engines.playbook_practices(_clean(tmp_path, None)) is not None
