"""Tests of the `tests-floor` step of the `tests-first` gate (brief #1590, ADR-0670, amendment 198
of SPEC-0072 rules 2, 4 and 9; REQ-079).

A work-type sample with no test file, or with no integration test, is red; a change to a layer's
code file with no test change is red; a docs-only change, a deletion-only change and a change with
its test are green; the kit's own repository and a sample with no work type print `not run`; a
sample whose foundation has not merged prints `not run`; an adopted sample is green on its first
run. Each failure names the gate id, the rule and the path class, never a file or a value.
Fixtures in `tmp_path` only: invented data (example.com), no network.
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import run_gates  # noqa: E402
from gates import tests_floor  # noqa: E402

GIT = [
    "git",
    "-c",
    "user.name=Ada",
    "-c",
    "user.email=ada@example.com",
    "-c",
    "commit.gpgsign=false",
]
UNIT = "def test_unit() -> None:\n    assert 1 + 1 == 2\n"
INTEGRATION = 'def test_shop() -> None:\n    assert "shop.example.com".endswith(".example.com")\n'
CODE = 'HOST = "shop.example.com"\n\n\ndef total(a: int, b: int) -> int:\n    return a + b\n'
FOUNDED = {
    "docs/architecture.md": "# Architecture\n",
    "backend/shop.py": CODE,
    "tests/unit/test_shop.py": UNIT,
    "tests/integration/test_shop_flow.py": INTEGRATION,
}


def _git(root: Path, *args: str) -> str:
    cmd = [*GIT, "-C", str(root), *args]
    done = subprocess.run(cmd, check=True, capture_output=True, text=True)  # nosec B603 - fixed
    return done.stdout.strip()


def _project(
    tmp_path: Path, files: dict[str, str], work_type: str | None = "web-app", mode: str = "init"
) -> Path:
    """A committed sample; AGK_BASE names its first commit, so later edits are the change."""
    root = tmp_path / "shop"
    shutil.copytree(KIT_ROOT / "config" / "playbooks", root / "config" / "playbooks")
    toml = f'mode = "{mode}"\n'
    if work_type:
        toml += f'\n[delivery]\nwork_type = "{work_type}"\n'
    for rel, text in {"agk.toml": toml, **files}.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    (root / "tests").mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607 - fixed
    _git(root, "add", "-A", "-f")
    _git(root, "commit", "-q", "-m", "base")
    return root


@pytest.fixture(autouse=True)
def _base(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("AGK_BASE", "GITHUB_BASE_REF", "CI"):
        monkeypatch.delenv(name, raising=False)


def _change(root: Path, monkeypatch: pytest.MonkeyPatch, files: dict[str, str | None]) -> None:
    monkeypatch.setenv("AGK_BASE", _git(root, "rev-parse", "HEAD"))
    for rel, text in files.items():
        if text is None:
            (root / rel).unlink()
        else:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text, encoding="utf-8")


def _floor(root: Path, capsys: pytest.CaptureFixture[str]) -> list[str]:
    run_gates.main(["--root", str(root)])
    return [ln for ln in capsys.readouterr().out.splitlines() if "tests-first" in ln]


def test_an_empty_tests_folder_in_a_work_type_sample_is_red(tmp_path: Path, capsys) -> None:
    """REQ-079 AC4: rule (a), naming the rule and the setting's path class, never a file."""
    root = _project(tmp_path, {"docs/architecture.md": "# Architecture\n", "backend/shop.py": CODE})
    lines = _floor(root, capsys)
    assert f"FAIL gates: tests-first: {tests_floor.NO_TESTS} (path class: test_dirs)" in lines
    assert (
        f"FAIL gates: tests-first: {tests_floor.NO_INTEGRATION} (path class: tests/integration/)"
        in lines
    )
    assert run_gates.main(["--root", str(root)]) == 1
    assert "shop.py" not in capsys.readouterr().out


def test_a_sample_with_unit_tests_only_is_red_for_its_integration_folder(
    tmp_path: Path, capsys
) -> None:
    """REQ-079 AC4: rule (b)."""
    files = {k: v for k, v in FOUNDED.items() if "integration" not in k}
    lines = _floor(_project(tmp_path, files), capsys)
    assert lines == [
        f"FAIL gates: tests-first: {tests_floor.NO_INTEGRATION} (path class: tests/integration/)"
    ]


def test_a_founded_sample_is_green(tmp_path: Path, capsys) -> None:
    """REQ-079 AC4."""
    assert _floor(_project(tmp_path, FOUNDED), capsys) == ["ok tests-first"]


def test_a_layer_change_with_no_test_change_is_red(tmp_path: Path, capsys, monkeypatch) -> None:
    """REQ-079 AC4: rule (c), naming the layer's glob, never the file."""
    root = _project(tmp_path, FOUNDED)
    _change(root, monkeypatch, {"backend/shop.py": CODE + "\nLIMIT = 10\n"})
    cls = "backend/**; layer: backend"
    want = f"FAIL gates: tests-first: {tests_floor.NO_TEST_CHANGE} (path class: {cls})"
    assert _floor(root, capsys) == [want]


def test_a_layer_change_with_its_test_change_is_green(tmp_path: Path, capsys, monkeypatch) -> None:
    """REQ-079 AC4."""
    root = _project(tmp_path, FOUNDED)
    test = UNIT + "\n\ndef test_limit() -> None:\n    assert 10 > 0\n"
    _change(
        root,
        monkeypatch,
        {"backend/shop.py": CODE + "\nLIMIT = 10\n", "tests/unit/test_shop.py": test},
    )
    assert _floor(root, capsys) == ["ok tests-first"]


def test_a_docs_only_change_is_green(tmp_path: Path, capsys, monkeypatch) -> None:
    """REQ-079 AC4."""
    root = _project(tmp_path, FOUNDED)
    _change(root, monkeypatch, {"docs/guide.md": "# Shop\n\nSee https://shop.example.com.\n"})
    assert _floor(root, capsys) == ["ok tests-first"]


def test_a_deletion_only_change_is_green(tmp_path: Path, capsys, monkeypatch) -> None:
    """Q-1590-1 (the brief's recommendation): removing code with no test change is never red."""
    files = {**FOUNDED, "backend/old.py": "OLD = 1\n"}
    root = _project(tmp_path, files)
    _change(
        root,
        monkeypatch,
        {
            "backend/old.py": None,
            "backend/shop.py": CODE.replace('HOST = "shop.example.com"\n', ""),
        },
    )
    assert _floor(root, capsys) == ["ok tests-first"]


def test_a_sample_with_no_work_type_is_not_run(tmp_path: Path, capsys) -> None:
    """REQ-079 AC7: no `[delivery] work_type`, today's reading."""
    root = _project(tmp_path, {"backend/shop.py": CODE}, work_type=None)
    assert _floor(root, capsys) == [
        "not run tests-first: no work type",
        "ok gates (3 check gates; not run: tests-first)",
    ]
    assert run_gates.main(["--root", str(root)]) == 0


def test_the_kits_own_repository_is_not_run(capsys) -> None:
    """REQ-079 AC2: the kit's own run is unchanged but for the not-run line."""
    assert run_gates.main(["--root", str(KIT_ROOT)]) == 0
    out = capsys.readouterr().out
    assert out == (
        "not run tests-first: no work type\nok secrets\nok environment-settings\n"
        "ok gates (3 check gates; not run: tests-first)\n"
    )


def test_a_sample_before_its_foundation_merged_is_not_run(tmp_path: Path, capsys) -> None:
    """Q-1590-3: no architecture record yet, so the foundation build has not merged."""
    root = _project(tmp_path, {"backend/shop.py": CODE})
    assert _floor(root, capsys)[0] == "not run tests-first: no foundation yet"


def test_an_adopted_sample_is_green_on_its_first_run(tmp_path: Path, capsys, monkeypatch) -> None:
    """REQ-079 AC5: in `mode = "adopt"` rules (a) and (b) are held; rule (c) still applies."""
    root = _project(
        tmp_path,
        {"docs/architecture.md": "# Architecture\n", "backend/shop.py": CODE},
        mode="adopt",
    )
    assert _floor(root, capsys) == ["ok tests-first"]
    _change(root, monkeypatch, {"backend/shop.py": CODE + "\nLIMIT = 10\n"})
    assert _floor(root, capsys)[0].startswith(
        f"FAIL gates: tests-first: {tests_floor.NO_TEST_CHANGE}"
    )


def test_test_dirs_compare_by_forward_slash(tmp_path: Path, capsys) -> None:
    """REQ-079 AC7: a `test_dirs` entry with a back slash or a trailing slash is the same folder."""
    root = _project(tmp_path, FOUNDED)
    text = (root / "agk.toml").read_text(encoding="utf-8")
    (root / "agk.toml").write_text('test_dirs = [".\\\\tests\\\\"]\n' + text, encoding="utf-8")
    assert _floor(root, capsys) == ["ok tests-first"]


def test_the_gate_is_a_check_with_its_step() -> None:
    """REQ-079 AC1: `tests-first` is restated stronger: `kind = "check"`, `step = "tests-floor"`."""
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import check_playbooks  # noqa: PLC0415

    base = KIT_ROOT / "config" / "playbooks" / "default.toml"
    gate = next(g for g in check_playbooks.composed(base, KIT_ROOT)[0] if g["id"] == "tests-first")
    assert gate["kind"] == "check" and gate["step"] == "tests-floor"
