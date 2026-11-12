"""Front-end and end-to-end test folders are in `test_dirs` (brief #1154, ADR-0490, REQ-062).

`init.py` writes the front-end test folders it finds into `test_dirs`, and `doctor.py` warns when
files that look like tests sit outside every `test_dirs` folder. Invented trees only, no network.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import doctor
import init

WARNING = "doctor: warning: test files outside test_dirs: "


def make_tree(root: Path, files: list[str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for rel in files:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("// example.com\n", encoding="utf-8")
    return root


def run_init(target: Path, capsys) -> tuple[list[str], str]:
    assert init.main([str(target), "--unreleased"]) == 0
    out = capsys.readouterr().out
    data = tomllib.loads((target / "agk.toml").read_text(encoding="utf-8"))
    return data["test_dirs"], out


def project(root: Path, test_dirs: list[str], files: list[str]) -> Path:
    make_tree(root, files)
    listed = ", ".join(f'"{d}"' for d in test_dirs)
    (root / "agk.toml").write_text(
        f'test_dirs = [{listed}]\ntest_patterns = ["test_*.py"]\n', encoding="utf-8"
    )
    return root


def test_a_init_writes_the_front_end_folders_it_finds(tmp_path, capsys):
    """REQ-062: brief #1154 answer 1 (init on a tree with `e2e/` and `frontend/src/test/`)."""
    target = make_tree(tmp_path / "app", ["e2e/login.spec.ts", "frontend/src/test/cart.test.tsx"])
    dirs, out = run_init(target, capsys)
    assert dirs == ["tests", "e2e", "frontend/src/test"]
    assert "test_dirs: added e2e, frontend/src/test" in out


def test_b_init_on_a_plain_tree_writes_tests_only(tmp_path, capsys):
    """REQ-062: brief #1154 answer 1 (a repository with none of the folders)."""
    target = make_tree(tmp_path / "plain", ["README.md"])
    dirs, out = run_init(target, capsys)
    assert dirs == ["tests"]
    assert "test_dirs: added" not in out


def test_c_doctor_names_a_front_end_folder_outside_test_dirs(tmp_path):
    """REQ-062: brief #1154 answer 2 (a `*.test.tsx` file outside `test_dirs`)."""
    root = project(tmp_path / "p", ["tests"], ["frontend/src/test/cart.test.tsx"])
    assert doctor.outside_test_dirs_lines(root) == [
        WARNING + "frontend/src/test; fix: add them to test_dirs in agk.toml"
    ]


def test_d_no_warning_once_the_folder_is_in_test_dirs(tmp_path):
    """REQ-062: brief #1154 answer 2 (no warning when there are none outside)."""
    root = project(
        tmp_path / "p", ["tests", "frontend/src/test"], ["frontend/src/test/cart.test.tsx"]
    )
    assert doctor.outside_test_dirs_lines(root) == []


def test_e_node_modules_and_the_kit_fixtures_are_skipped(tmp_path):
    """REQ-062: brief #1154 answer 2 (`node_modules/`, `.git/`, `vendor/`, `tests/kit/`)."""
    root = project(
        tmp_path / "p",
        ["src"],
        [
            "node_modules/pkg/index.test.js",
            ".git/hooks/x.spec.ts",
            "vendor/lib/thing_test.go",
            "tests/kit/fixtures/a.test.ts",
        ],
    )
    assert doctor.outside_test_dirs_lines(root) == []


def test_at_most_three_folders_are_named(tmp_path):
    """REQ-062: brief #1154 answer 2 (up to three folders, the topmost of each)."""
    root = project(
        tmp_path / "p",
        ["tests"],
        ["a/x.spec.ts", "a/deep/y.spec.ts", "b/z_test.go", "c/w.test.js", "d/v.test.js"],
    )
    assert doctor.outside_test_dirs_lines(root) == [
        WARNING + "a, b, c; fix: add them to test_dirs in agk.toml"
    ]


def test_a_name_that_matches_test_patterns_is_not_warned(tmp_path):
    """REQ-062: brief #1154 answer 2 (a file that matches `test_patterns` is not warned)."""
    root = project(tmp_path / "p", ["tests"], ["scripts/test_tool.py"])
    assert doctor.outside_test_dirs_lines(root) == []
