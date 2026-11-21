"""Tests of the `secrets` and `environment-settings` steps (SPEC-0072 rules 2 and 12 build (f);
REQ-079 AC4; brief #1593, ADR-0673).

A tracked environment file, an unignored one, a planted fake key, an example settings file with a
value and a setting the code reads that the example file does not name are each red, naming the
gate id, the rule and the path class and never a value; `mode = "adopt"` holds the findings; the
kit's own tree is green. Fixtures in `tmp_path` only: invented data (example.com), an invented key
shape built at run time, no network.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import run_gates  # noqa: E402

GIT = [
    "git",
    "-c",
    "user.name=Ada",
    "-c",
    "user.email=ada@example.com",
    "-c",
    "commit.gpgsign=false",
]
# An invented key shape, built here so that no tracked file holds one (principle 9).
FAKE = "AKIA" + "QX7ZB3MPL2W6RTNJ"
APP = 'import os\n\nHOST = os.environ["SHOP_HOST"]\nLIMIT = os.getenv("SHOP_LIMIT", "10")\n'


def _project(tmp_path: Path, files: dict[str, str], mode: str = "init") -> Path:
    shutil.copytree(KIT_ROOT / "config" / "playbooks", tmp_path / "config" / "playbooks")
    files = {"agk.toml": f'mode = "{mode}"\n', ".gitignore": ".env\n", **files}
    for rel, text in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run([*GIT, "-C", str(tmp_path), "add", "-A", "-f"], check=True)
    subprocess.run([*GIT, "-C", str(tmp_path), "commit", "-q", "-m", "x"], check=True)
    return tmp_path


def _run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = run_gates.main(["--root", str(root)])
    return code, capsys.readouterr().out


CLEAN = {"app/main.py": APP, ".env.example": "# names only\nSHOP_HOST=\nSHOP_LIMIT=<a number>\n"}


def test_a_clean_sample_is_green(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """REQ-079 AC4."""
    code, out = _run(_project(tmp_path, CLEAN), capsys)
    assert code == 0, out
    assert "ok secrets\n" in out and "ok environment-settings\n" in out


@pytest.mark.parametrize(
    ("files", "gate", "cls"),
    [
        ({".env.local": "SHOP_HOST=shop.example.com\n"}, "secrets", "secret files (tracked)"),
        ({"config/key.py": f'TOKEN = "{FAKE}"\n'}, "secrets", "tracked files (a secret shape)"),
        (
            {".env.example": "SHOP_HOST=shop.example.com\nSHOP_LIMIT=\n"},
            "secrets",
            "example settings file (a value)",
        ),
        (
            {".env.example": "SHOP_HOST=\n"},
            "environment-settings",
            "settings read in code (not in the example file)",
        ),
        (
            {"app/jobs.py": 'import os\nHOST = os.environ.get("SHOP_HOST", "shop.example.com")\n'},
            "environment-settings",
            "settings read in code (a required one with a default)",
        ),
    ],
)
def test_each_finding_is_red_naming_the_gate_and_class_never_a_value(
    files: dict[str, str],
    gate: str,
    cls: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """REQ-079 AC4: principle 8."""
    code, out = _run(_project(tmp_path, {**CLEAN, **files}), capsys)
    assert code == 1
    assert f"FAIL gates: {gate}: SPEC-0072 rule 2: " in out and f"(path class: {cls})" in out, out
    for value in (FAKE, "shop.example.com", "SHOP_HOST", "SHOP_LIMIT", ".env.local"):
        assert value not in out


def test_an_unignored_environment_file_is_red(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4: on disk, untracked, and not ignored by `.gitignore`."""
    root = _project(tmp_path, CLEAN)
    (root / ".gitignore").write_text("", encoding="utf-8")
    (root / ".ENV").write_text("SHOP_HOST=shop.example.com\n", encoding="utf-8")
    code, out = _run(root, capsys)
    assert code == 1 and "(path class: environment files (not ignored))" in out
    (root / ".gitignore").write_text(".env\n.ENV\n", encoding="utf-8")
    assert _run(root, capsys)[0] == 0


def test_no_example_file_fails_only_when_the_code_reads_a_setting(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4: Q-1593-1."""
    assert _run(_project(tmp_path / "a", {"app/main.py": "print(1)\n"}), capsys)[0] == 0
    code, out = _run(_project(tmp_path / "b", {"app/main.py": APP}), capsys)
    assert code == 1 and "settings read in code (not in the example file)" in out


def test_kit_folders_and_tests_are_not_the_project_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4: the kit's installed folders and the test folders read their own settings."""
    read = 'import os\nX = os.environ["AGK_EXAMPLE"]\n'
    files = {"scripts/agk/x.py": read, ".claude/hooks/x.py": read, "tests/test_x.py": read}
    assert _run(_project(tmp_path, files), capsys)[0] == 0


def test_adopt_mode_holds_the_findings(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """REQ-079 AC4: held until brief #1600's baseline, so nothing existing goes red."""
    files = {"config/key.py": f'TOKEN = "{FAKE}"\n', "app/main.py": APP}
    code, out = _run(_project(tmp_path, files, mode="adopt"), capsys)
    assert code == 0, out


def test_the_kits_own_tree_is_green() -> None:
    """REQ-079 AC4: the kit's own repository runs `default.toml`'s two checks."""
    for step in ("secrets", "environment-settings"):
        module = run_gates.step_module(step)
        assert module is not None and module.check(KIT_ROOT, {}) == [], step
