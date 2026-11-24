"""Front-end and end-to-end test folders are in `test_dirs` (brief #1154, ADR-0490, REQ-062).

`init.py` writes the front-end test folders it finds into `test_dirs`, and `doctor.py` warns when
files that look like tests sit outside every `test_dirs` folder. Invented trees only, no network.
"""

from __future__ import annotations

import re
import subprocess  # nosec B404 - a fixed `git init`, no shell
import tomllib
from pathlib import Path

import pytest

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


# Brief #1899 (ADR-0787): a second init run reads `test_dirs` back from agk.toml (SPEC-0001 rule 14).
CONFLICT = "conflict agk.toml (path class agk.toml: differs)"
CLEAN = ["--layout", "plugin", "--rehearsal"]


def git_tree(root: Path, files: list[str]) -> Path:
    make_tree(root, files)
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)  # nosec B603 B607 - a fixed git init, no shell
    return root


def init_twice(target: Path, capsys, extra: list[str] = ()) -> tuple[int, str]:
    """Run init, then again with the same flags: (the second exit code, its output)."""
    args = [str(target), "--unreleased", *extra]
    assert init.main(args) == 0
    capsys.readouterr()
    code = init.main(args)
    return code, capsys.readouterr().out


def stamped_dirs(target: Path) -> list[str]:
    return tomllib.loads((target / "agk.toml").read_text(encoding="utf-8"))["test_dirs"]


@pytest.mark.parametrize("folder", ["e2e", "tests/e2e"])
def test_brief_1899_a_second_run_on_a_front_end_tree_is_unchanged(folder, tmp_path, capsys):
    """REQ-062: brief #1899 answers 1 and 7 (installed layout; `e2e/` and `tests/e2e/`)."""
    target = make_tree(tmp_path / "app", [f"{folder}/a.spec.ts"])
    code, out = init_twice(target, capsys)
    assert code == 0, out
    assert "unchanged agk.toml" in out and CONFLICT not in out
    assert stamped_dirs(target) == ["tests", folder]


@pytest.mark.parametrize("folder", ["e2e", "tests/e2e"])
def test_brief_1899_a_second_clean_run_on_a_front_end_tree_is_unchanged(folder, tmp_path, capsys):
    """REQ-062: brief #1899 answers 5 and 7 (`--layout plugin --rehearsal`, a git repository)."""
    target = git_tree(tmp_path / "shop-example", [f"{folder}/a.spec.ts"])
    code, out = init_twice(target, capsys, CLEAN)
    assert code == 0, out
    assert CONFLICT not in out
    assert stamped_dirs(target) == ["tests", folder]


def test_brief_1899_setup_flags_re_run_unchanged(tmp_path, capsys, monkeypatch):
    """REQ-062: brief #1899 answer 5 (`--solo` and `--login-from-env` are not read by the reuse)."""
    monkeypatch.setenv(init.LOGIN_ENV, "example-user")
    target = make_tree(tmp_path / "app", ["e2e/a.spec.ts"])
    code, out = init_twice(target, capsys, ["--solo", "--login-from-env"])
    assert code == 0, out
    assert CONFLICT not in out


def rewrite_line(target: Path, line: str) -> None:
    path = target / "agk.toml"
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"(?m)^test_dirs = .*$", lambda _m: line, text, count=1), "utf-8")


def test_brief_1899_a_persons_list_in_the_kit_form_is_unchanged(tmp_path, capsys):
    """REQ-062: brief #1899 answer 3 (a person's own list, in the kit's form, is reused)."""
    target = make_tree(tmp_path / "app", ["README.md"])
    assert init.main([str(target), "--unreleased"]) == 0
    rewrite_line(target, 'test_dirs = ["tests", "web/e2e"]')
    capsys.readouterr()
    assert init.main([str(target), "--unreleased"]) == 0
    out = capsys.readouterr().out
    assert "unchanged agk.toml" in out and CONFLICT not in out
    assert stamped_dirs(target) == ["tests", "web/e2e"]


@pytest.mark.parametrize(
    "line",
    [
        "test_dirs = ['tests', 'e2e']",  # reformatted by hand
        'test_dirs = "e2e"',  # a string, not a list
        'test_dirs = ["tests", 3]',  # a list holding a non-string
    ],
)
def test_brief_1899_a_reformatted_or_non_list_line_still_refuses(line, tmp_path, capsys):
    """REQ-062: brief #1899 answers 3 and 5 (the refusal names the path class, never a value)."""
    target = make_tree(tmp_path / "app", ["e2e/a.spec.ts"])
    assert init.main([str(target), "--unreleased"]) == 0
    rewrite_line(target, line)
    before = (target / "agk.toml").read_bytes()
    capsys.readouterr()
    assert init.main([str(target), "--unreleased"]) == 1
    out = capsys.readouterr().out
    assert CONFLICT in out.splitlines()  # the path class, never the value
    assert (target / "agk.toml").read_bytes() == before


def test_brief_1899_invalid_toml_still_refuses(tmp_path, capsys):
    """REQ-062: brief #1899 answer 6 (an agk.toml that is not TOML: the refusal as today)."""
    target = make_tree(tmp_path / "app", ["e2e/a.spec.ts"])
    (target / "agk.toml").write_text("test_dirs = [\n", encoding="utf-8")
    assert init.existing_test_dirs(target) is None
    assert init.main([str(target), "--unreleased"]) == 1
    assert CONFLICT in capsys.readouterr().out


def test_brief_1899_a_folder_made_after_the_first_run_is_not_added(tmp_path, capsys):
    """REQ-062: brief #1899 answer 2 (no re-detection on a re-run; adopt is the merge path)."""
    target = make_tree(tmp_path / "app", ["README.md"])
    assert init.main([str(target), "--unreleased"]) == 0
    make_tree(target, ["e2e/a.spec.ts"])
    capsys.readouterr()
    assert init.main([str(target), "--unreleased", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "unchanged agk.toml" in out and "test_dirs: added" not in out
    assert stamped_dirs(target) == ["tests"]


@pytest.mark.parametrize("extra", [[], CLEAN], ids=["installed", "plugin"])
def test_brief_1899_every_value_init_renders_from_the_tree_reads_back(extra, tmp_path, capsys):
    """REQ-062: brief #1899 answer 8 (the class stays closed: a second run plans no change)."""
    files = [f"{d}/a.spec.ts" for d in init.FRONT_END_TEST_DIRS]
    files += ["frontend/tests/b.test.tsx", "src/__tests__/c.test.js", "tests/test_d.py"]
    files += ["cypress/e.cy.ts", "pkg/f_test.py", "package.json"]
    target = git_tree(tmp_path / "shop-example", files)
    args = [str(target), "--unreleased", *extra]
    assert init.main(args) == 0
    capsys.readouterr()
    code = init.main(args)
    out = capsys.readouterr().out
    assert code == 0, out
    assert not [ln for ln in out.splitlines() if ln.startswith(("create ", "conflict "))], out
