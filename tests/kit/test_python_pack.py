"""Tests of the Python standards pack (SPEC-0072 rules 6 and 8; REQ-079 AC4; brief #1589, ADR-0669).

On a sample Python API service with an Accepted stack record, the pack's `lint`, `format` and
`type` steps run over `project_lint_paths` (default: the layers' paths): a planted lint fault and a
planted type fault each fail naming the rule and the path class and no value; a missing tool fails
naming the tool and the setting; a team configuration missing a floor rule code is refused naming
the code; with no stack chosen the pack does not run; and `agk-lint` over `lint_paths` is as
before. Fixtures in `tmp_path` only: invented data (example.com), no network.
"""

from __future__ import annotations

import shutil
import sys
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
AGK = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(AGK))

import check_playbooks  # noqa: E402
import run_gates  # noqa: E402
from common import DEFAULT_CONFIG, CheckError  # noqa: E402
from gates import python_pack  # noqa: E402

from config import project_lint_paths  # noqa: E402

PLAYBOOKS = KIT_ROOT / "config" / "playbooks"
# The playbooks that hold the two Python entries, one entry each (brief #1638, the
# conductor's ruling on brief #1589's `Broad:` line): the base `default.toml` names no tool
# or version, and a playbook whose own test refuses a tool or a version holds none (Q-1638-1).
WORK_TYPES = ["api-service", "web-app"]
CODES = ["E", "F", "I", "B", "UP"]
VALUES = ("examplelib", "greeting", "app.py", "hello", "unused")
CLEAN = (
    '"""A greeting service at example.com."""\n\n\n'
    'def greeting(name: str) -> str:\n    return "hello " + name\n'
)
RECORD = """# ADR-0002: stack options

- Status: Accepted
- Date: 2026-11-20

## Decision

1. **Options**
   - Option A — one service at example.com. Parts: python 3.12.7 PSF-2.0, examplelib 1.2.3 MIT.
3. **Chosen**: Option A
"""


def _pins(name: str) -> str:
    text = (KIT_ROOT / "config" / "ci-tools.txt").read_text(encoding="utf-8")
    return next(ln.split("==")[1].strip() for ln in text.splitlines() if ln.startswith(name + "=="))


def sample(tmp: Path, code: str = CLEAN, toml: str = "", record: bool = True) -> Path:
    shutil.copytree(PLAYBOOKS, tmp / "config" / "playbooks")
    (tmp / "agk.toml").write_text(
        f'mode = "init"\n{toml}\n[delivery]\nwork_type = "api-service"\n', encoding="utf-8"
    )
    template = KIT_ROOT / "kit" / "templates" / "stacks" / "python-pyproject" / "pyproject.toml"
    (tmp / "pyproject.toml").write_text(
        template.read_text(encoding="utf-8").replace("{{project}}", "sample"), encoding="utf-8"
    )
    if record:
        (tmp / "docs" / "adr").mkdir(parents=True)
        (tmp / "docs" / "adr" / "0002-stack-options.md").write_text(RECORD, encoding="utf-8")
    (tmp / "api").mkdir()
    (tmp / "api" / "app.py").write_text(code, encoding="utf-8")
    return tmp


def gates(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = run_gates.main(["--root", str(root)])
    out = capsys.readouterr()
    return code, out.out + out.err


def no_values(text: str) -> None:
    for word in VALUES:
        assert word not in text, word


@pytest.mark.parametrize("work_type", WORK_TYPES)
def test_each_playbook_carries_the_python_pack_pinned_to_ci_tools(work_type: str) -> None:
    """REQ-079 AC4: both Python stacks, the pinned ruff and its codes, the config file."""
    _, packs, problems = check_playbooks.standard(PLAYBOOKS / f"{work_type}.toml", KIT_ROOT)
    assert problems == []
    found = {e["stack"]: e for e in packs}
    for stack in python_pack.STACKS:
        entry = found[stack]
        assert (entry["lint"], entry["format"], entry["type"]) == python_pack.STEP_NAMES
        assert entry["rules"] == {"tool": "ruff", "version": _pins("ruff"), "codes": CODES}
        assert entry["config"] == "pyproject.toml"
    assert python_pack.MYPY_VERSION == _pins("mypy")


def test_the_base_holds_no_pack_and_the_other_playbooks_none_of_their_own() -> None:
    """REQ-079 AC4: brief #1638, the pack moved out of `default.toml` (found bug #1636)."""
    base = (PLAYBOOKS / "default.toml").read_text(encoding="utf-8")
    assert "standards" not in tomllib.loads(base)
    for path in sorted(PLAYBOOKS.glob("*.toml")):
        if path.stem not in WORK_TYPES:
            assert check_playbooks.standard(path, KIT_ROOT)[1] == [], path.stem


def test_a_clean_python_service_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """REQ-079 AC4."""
    code, out = gates(sample(tmp_path), capsys)
    assert code == 0, out
    assert "ok standards python-pyproject" in out


def test_a_planted_lint_fault_fails_naming_the_rule_and_path_class(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4: the brief's Measured line, an unused import in a product file."""
    code, out = gates(sample(tmp_path, "import json\n" + CLEAN.split("\n", 1)[1]), capsys)
    assert code == 1
    assert "FAIL gates: standards python-pyproject lint: SPEC-0072 rule 6: lint rule F401" in out
    assert "(path class: api/**)" in out
    no_values(out)


def test_a_planted_type_fault_fails_naming_the_rule_and_path_class(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4."""
    fault = CLEAN.replace('"hello " + name', "len(name)")
    code, out = gates(sample(tmp_path, fault), capsys)
    assert code == 1
    assert "standards python-pyproject type: SPEC-0072 rule 6: type rule return-value" in out
    assert "(path class: api/**)" in out
    no_values(out)


def test_an_unformatted_file_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """REQ-079 AC4."""
    code, out = gates(sample(tmp_path, CLEAN.replace("-> str:", "->str :")), capsys)
    assert code == 1
    assert "standards python-pyproject format: SPEC-0072 rule 6: the file is not formatted" in out
    no_values(out)


@pytest.mark.parametrize(
    ("tool", "setting"), [("ruff", "standards.rules"), ("mypy", "standards.type")]
)
def test_a_missing_tool_fails_naming_the_tool_and_setting(
    tool: str,
    setting: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REQ-079 AC4: never a silent pass."""
    monkeypatch.setattr(python_pack, "installed", lambda name: name != tool)
    code, out = gates(sample(tmp_path), capsys)
    assert code == 1
    assert f"the pack's tool {tool} is not installed (setting: {setting})" in out


@pytest.mark.parametrize(
    ("ruff", "missing"),
    [
        ('select = ["E", "F"]', ["B", "I", "UP"]),
        ('select = ["ALL"]\nignore = ["B"]', ["B"]),
        ('select = ["E", "F", "I", "B", "UP"]\nignore = ["E501"]', ["E"]),
    ],
)
def test_a_team_configuration_missing_a_floor_rule_is_refused(
    ruff: str, missing: list[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4, SPEC-0072 rule 8 (Q-S0072-14): the floor is the pack's whole `rules` list."""
    root = sample(tmp_path)
    path = root / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('select = ["E", "F", "I", "B", "UP"]', ruff), encoding="utf-8")
    code, out = gates(root, capsys)
    assert code == 1
    for rule in missing:
        assert (
            f"floor: SPEC-0072 rule 8: the configuration does not enable the pack's rule {rule} "
            in out
        )
    assert out.count("floor:") == len(missing)


def test_a_team_configuration_that_adds_rules_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4: a configuration may add rules."""
    root = sample(tmp_path)
    path = root / "pyproject.toml"
    text = path.read_text(encoding="utf-8").replace('"UP"]', '"UP", "SIM"]')
    path.write_text(text, encoding="utf-8")
    code, out = gates(root, capsys)
    assert code == 0, out


def test_with_no_stack_chosen_the_pack_does_not_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4: only a chosen Python stack turns the pack on."""
    code, out = gates(sample(tmp_path, "import json\n", record=False), capsys)
    assert code == 0, out
    assert "standards" not in out


def test_project_lint_paths_names_the_code_the_pack_reads(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4: a fault outside `project_lint_paths` is not read."""
    root = sample(tmp_path, "import json\n" + CLEAN, toml='project_lint_paths = ["domain/**"]')
    (root / "domain").mkdir()
    (root / "domain" / "rules.py").write_text(CLEAN, encoding="utf-8")
    code, out = gates(root, capsys)
    assert code == 0, out


@pytest.mark.parametrize("value", ['"api/**"', "[]", '["/srv/api"]', '["../api"]', "[1]"])
def test_an_unknown_form_of_project_lint_paths_is_refused(
    value: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4: refused naming the setting, never the value."""
    root = sample(tmp_path, toml=f"project_lint_paths = {value}")
    with pytest.raises(CheckError, match=r"setting: project_lint_paths\)$"):
        project_lint_paths(root)
    code, out = gates(root, capsys)
    assert code == 1
    assert "(setting: project_lint_paths)" in out
    assert "srv" not in out


def test_absent_project_lint_paths_reads_the_layers(tmp_path: Path) -> None:
    root = sample(tmp_path)
    assert project_lint_paths(root) is None
    assert python_pack.patterns(root) == ["contracts/**", "api/**", "domain/**", "data/**"]


def test_the_kit_lint_is_unchanged() -> None:
    """REQ-079 AC4: `lint_paths`, `AGK_RUFF_FLAGS` and `agk-lint` stay as they are."""
    assert DEFAULT_CONFIG["lint_paths"] == ["scripts/agk", ".claude/hooks"]
    mk = (KIT_ROOT / "agk.mk").read_text(encoding="utf-8")
    flags = (
        "AGK_RUFF_FLAGS := --isolated --line-length 100 --target-version py311 --select E,F,I,B,UP"
    )
    assert flags in mk
    assert (
        "ruff check $(AGK_RUFF_FLAGS) $(wildcard $(shell $(PY) scripts/agk/config.py lint_paths))"
        in mk
    )
    assert "project_lint_paths" not in mk
    assert ",".join(CODES) in flags


def test_the_tools_run_as_modules_of_this_python_never_a_shell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-079 AC4: `python -m ruff` and `python -m mypy`, for Windows, WSL and macOS alike."""
    calls: list[tuple[list[str], dict]] = []

    class Done:
        returncode = 0
        stdout = "[]"

    def fake(argv: list[str], **kwargs: object) -> Done:
        calls.append((argv, dict(kwargs)))
        return Done()

    monkeypatch.setattr(python_pack.subprocess, "run", fake)
    python_pack.lint(sample(tmp_path), CODES, [("api/app.py", "api/**")])
    argv, kwargs = calls[0]
    assert argv[:3] == [sys.executable, "-m", "ruff"]
    assert kwargs.get("shell", False) is False
    assert tomllib.loads((tmp_path / "pyproject.toml").read_text(encoding="utf-8"))


def test_the_layers_line_comes_before_the_pack_lines(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4 (conductor's correction on #1630): an architecture of two or more layers and a
    Python stack give the `layers` line, then the pack's lines."""
    code, out = gates(sample(tmp_path, "import json\n" + CLEAN.split("\n", 1)[1]), capsys)
    assert code == 1
    lines = out.splitlines()
    layers = next(i for i, ln in enumerate(lines) if ln == "ok layers")
    pack = next(i for i, ln in enumerate(lines) if "standards python-pyproject" in ln)
    assert layers < pack
