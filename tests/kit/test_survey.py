"""SPEC-0041 build (f): the survey reads a codebase and never runs it (brief #852).

Rules 10 to 12: `survey.py` writes `cache/inventory.json` under the sidecar from tracked files
only, ranks them, spends a reading budget and states its coverage, and one function finds test
files in many languages. Small repositories in `tmp_path`; invented data only; no network.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import adopt  # noqa: E402
import survey  # noqa: E402

OVER_1MB = 1_000_001


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)  # nosec B603 B607 - fixed argument list, no shell


def commit(root: Path) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "change")


def write(root: Path, files: dict) -> None:
    for rel, body in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body if isinstance(body, bytes) else body.encode("utf-8"))


def clone_of(tmp_path: Path, files: dict, committed: bool = True) -> Path:
    root = tmp_path / "clone"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    write(root, files)
    if committed:
        commit(root)
    else:
        git(root, "add", "-A")
    return root


def sidecar_of(tmp_path: Path, budget: str | None = None) -> Path:
    side = tmp_path / "side"
    side.mkdir()
    extra = f"survey_budget = {budget}\n" if budget is not None else ""
    (side / "agk.toml").write_text(f'[personal]\nforge = "files"\n{extra}', encoding="utf-8")
    return side


def run(clone: Path, side: Path | None, *args: str, **env: str):
    where = ["--sidecar", str(side)] if side else []
    base = {k: v for k, v in os.environ.items() if k != "AGK_HOME"}
    cmd = [sys.executable, str(SCRIPTS / "survey.py"), "--clone", str(clone), *where, *args]
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        cmd, capture_output=True, text=True, env={**base, **env}
    )


def inventory(side: Path) -> dict:
    return json.loads((side / "cache" / "inventory.json").read_text(encoding="utf-8"))


def survey_of(tmp_path: Path, files: dict, budget: str | None = None) -> dict:
    clone, side = clone_of(tmp_path, files), sidecar_of(tmp_path, budget)
    done = run(clone, side)
    assert done.returncode == 0, done.stdout + done.stderr
    return inventory(side)


def snapshot(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and not p.is_symlink()
    }


def test_rule10_product_code_is_never_run_and_the_clone_is_untouched(tmp_path):
    """REQ-048 AC3: rule 10 (a test file that would write a sentinel if imported or run)."""
    sentinel = tmp_path / "sentinel.txt"
    code = f"open({str(sentinel)!r}, 'w').write('ran')\n"
    pkg = json.dumps({"scripts": {"test": f"touch {sentinel}"}}, indent=1)
    files = {"test_app.py": code, "setup.py": code, "conftest.py": code, "package.json": pkg}
    clone, side = clone_of(tmp_path, files), sidecar_of(tmp_path)
    before = snapshot(clone)
    assert run(clone, side).returncode == 0
    assert not sentinel.exists()
    assert snapshot(clone) == before


def test_rule10_two_runs_are_byte_identical_and_sorted(tmp_path):
    """REQ-048 AC3: rule 10 (sorted keys, no clock, the date only from `--today`)."""
    clone = clone_of(tmp_path, {"b/x.py": "import a\n", "a.py": "A = 1\n"})
    side, path = sidecar_of(tmp_path), None
    assert run(clone, side).returncode == 0
    path = side / "cache" / "inventory.json"
    first = path.read_bytes()
    assert run(clone, side).returncode == 0
    assert path.read_bytes() == first
    data = json.loads(first)
    assert first.decode("utf-8") == json.dumps(data, indent=1, sort_keys=True) + "\n"
    assert data["date"] is None
    assert run(clone, side, "--today", "2026-11-09").returncode == 0
    assert inventory(side)["date"] == "2026-11-09"


def test_rule10_binary_symlink_and_untracked_are_not_read(tmp_path):
    """REQ-048 AC3: rule 10 (binary skipped, no symlink followed, tracked files only)."""
    outside = tmp_path / "outside.py"
    outside.write_text("import outside_secret_name\n" * 3, encoding="utf-8")
    clone = clone_of(tmp_path, {"app.py": "A = 1\n", "logo.png": b"\x89PNG\x00\x01import zz\n"})
    (clone / "link.py").symlink_to(outside)
    commit(clone)
    (clone / "loose.py").write_text("import untracked_name\n", encoding="utf-8")
    side = sidecar_of(tmp_path)
    assert run(clone, side).returncode == 0
    data, raw = inventory(side), (side / "cache" / "inventory.json").read_text(encoding="utf-8")
    assert sorted(data["files"]) == ["app.py"]
    assert data["skipped"]["binary"] == ["logo.png"]
    assert data["skipped"]["symlink"] == ["link.py"]
    assert "outside_secret_name" not in raw and "loose.py" not in raw
    assert data["coverage"] == "0 of 1 files read"


def test_rule10_a_file_over_1mb_is_listed_and_not_read(tmp_path):
    """REQ-048 AC3: rule 10 (its import line names `lib`, and `lib` gains no fan-in from it)."""
    big = "import lib\n" + "#" * OVER_1MB
    data = survey_of(tmp_path, {"big.py": big, "lib.py": "L = 1\n"})
    assert data["skipped"]["large"] == ["big.py"]
    assert "big.py" not in data["files"]
    assert data["files"]["lib.py"]["fan_in"] == 0


def test_rule10_the_inventory_holds_what_the_rule_lists(tmp_path):
    """REQ-048 AC3: rule 10 (languages, manifests and commands, entry points, CI files)."""
    pkg = '{\n "main": "lib/start.js",\n "scripts": {\n  "test": "jest --ci"\n }\n}\n'
    pyproject = (
        '[project.scripts]\nrun-it = "app.cli:main"\n[tool.taskipy.tasks]\ntest = "pytest -q"\n'
    )
    data = survey_of(
        tmp_path,
        {
            "package.json": pkg,
            "pyproject.toml": pyproject,
            "web/App.csproj": '<Project Sdk="Microsoft.NET.Sdk"></Project>\n',
            "main.py": "A = 1\nB = 2\n",
            "cmd/tool/main.go": "package main\n",
            ".github/workflows/ci.yml": "on: push\n",
            ".gitlab-ci.yml": "a: 1\n",
            "Jenkinsfile": "pipeline {}\n",
        },
    )
    assert data["languages"]["Python"] == {"files": 1, "lines": 2}
    assert data["languages"]["Go"] == {"files": 1, "lines": 1}
    manifests = {m["path"]: m["test_commands"] for m in data["manifests"]}
    assert manifests == {
        "package.json": ["jest --ci"],
        "pyproject.toml": ["pytest -q"],
        "web/App.csproj": [],
    }
    entries = {(e["value"], e["source"]) for e in data["entry_points"]}
    assert ("lib/start.js", "package.json") in entries
    assert ("app.cli:main", "pyproject.toml") in entries
    assert ("main.py", "name") in entries and ("cmd/tool/main.go", "name") in entries
    assert data["ci_files"] == [".github/workflows/ci.yml", ".gitlab-ci.yml", "Jenkinsfile"]


def test_rule11_the_rank_is_fan_in_then_churn(tmp_path):
    """REQ-048 AC3: rule 11 (import fan-in first, then the commits that touched the file)."""
    clone = clone_of(
        tmp_path,
        {
            "core.py": "C = 1\n",
            "busy.py": "B = 1\n",
            "calm.py": "K = 1\n",
            "use1.py": "import core\n",
            "use2.py": "from core import C\n",
        },
    )
    write(clone, {"busy.py": "B = 2\n"})
    commit(clone)
    side = sidecar_of(tmp_path)
    assert run(clone, side).returncode == 0
    files = inventory(side)["files"]
    assert (files["core.py"]["fan_in"], files["core.py"]["rank"]) == (2, 1)
    assert (files["busy.py"]["churn"], files["busy.py"]["rank"]) == (2, 2)
    assert files["calm.py"]["churn"] == 1 and files["calm.py"]["rank"] > 2


@pytest.mark.parametrize(
    ("importer", "line", "target"),
    [
        ("a/u.py", "from pkg.mod import x\n", "pkg/mod.py"),
        ("a/u.py", "from . import sib\n", "a/sib.py"),
        ("a/u.js", "const x = require('./sib');\n", "a/sib.js"),
        ("a/u.ts", "import { x } from '../b/sib';\n", "b/sib.ts"),
        ("a/u.go", 'import "example.com/app/lib/geo"\n', "lib/geo/geo.go"),
        ("a/U.java", "import com.example.Thing;\n", "src/main/java/com/example/Thing.java"),
        ("a/U.cs", "using Example.Geo;\n", "Example/Geo/Point.cs"),
        ("a/u.rb", "require_relative 'sib'\n", "a/sib.rb"),
        ("a/u.rs", "use crate::geo::Point;\n", "src/geo.rs"),
        ("a/u.php", "use App\\Geo\\Point;\n", "src/Geo/Point.php"),
    ],
)
def test_rule11_import_lines_of_each_language_count(tmp_path, importer, line, target):
    """REQ-048 AC3: rule 11 (the tracked files whose import lines name it, by language)."""
    data = survey_of(tmp_path, {importer: line, target: "\n"})
    assert data["files"][target]["fan_in"] == 1
    assert data["files"][importer]["imports"] == 1


def test_rule11_the_budget_goes_round_robin_across_the_folders(tmp_path):
    """REQ-048 AC3: rule 11 (120 files, five folders, a budget of 40, highest rank first)."""
    folders = ["ant", "bee", "cat", "dog", "elk"]
    files = {f"{d}/m{n}.py": "A = 1\n" for d in folders for n in range(24)}
    files |= {f"{d}/top.py": "T = 1\n" for d in folders}
    for d in folders:
        files[f"{d}/m0.py"] = f"from {d} import top\n"
    data = survey_of(tmp_path, files)
    listed = data["reading_list"]
    assert len(listed) == 40 and len(set(listed)) == 40
    assert {p.split("/")[0] for p in listed} == set(folders)
    assert listed[:5] == [f"{d}/top.py" for d in folders]
    for d in folders:
        assert sum(p.startswith(d + "/") for p in listed) == 8


def test_rule11_a_later_pass_lists_changed_then_unread_and_states_coverage(tmp_path):
    """REQ-048 AC3: rule 11 (never a file whose blob equals its ledger entry; also at 0)."""
    clone = clone_of(tmp_path, {"a.py": "A = 1\n", "b.py": "B = 1\n", "c.py": "C = 1\n"})
    side = sidecar_of(tmp_path)
    first = run(clone, side)
    assert first.stdout.splitlines()[-1] == "0 of 3 files read"
    data = inventory(side)
    assert data["ledger"] == {} and data["coverage"] == "0 of 3 files read"
    data["ledger"] = {p: data["files"][p]["blob"] for p in ("a.py", "b.py")}
    (side / "cache" / "inventory.json").write_text(json.dumps(data), encoding="utf-8")
    write(clone, {"b.py": "B = 2\n"})
    commit(clone)
    second = run(clone, side)
    assert second.stdout.splitlines()[-1] == "1 of 3 files read"
    after = inventory(side)
    assert after["reading_list"] == ["b.py", "c.py"]
    assert after["coverage"] == "1 of 3 files read"
    assert set(after["ledger"]) == {"a.py", "b.py"}


@pytest.mark.parametrize("value", ["0", "1001", '"many"', "40.5", "true"])
def test_rule11_a_bad_budget_is_refused_naming_the_setting(tmp_path, value):
    """REQ-048 AC3: rule 11 (any other value is refused, naming the setting, never the value)."""
    clone, side = clone_of(tmp_path, {"a.py": "A = 1\n"}), sidecar_of(tmp_path, value)
    done = run(clone, side)
    assert done.returncode == 1
    assert "survey_budget" in done.stdout
    assert value.strip('"') not in done.stdout.replace("1 to 1000", "")
    assert not (side / "cache" / "inventory.json").exists()


@pytest.mark.parametrize(("value", "expected"), [(None, 40), ("1", 1), ("1000", 1000)])
def test_rule11_accepted_budgets(tmp_path, value, expected):
    """REQ-048 AC3: rule 11 (a whole number from 1 to 1000, 40 by default)."""
    files = {f"m{n}.py": "\n" for n in range(45)}
    data = survey_of(tmp_path, files, value)
    assert len(data["reading_list"]) == min(expected, 45)


def test_rule11_a_damaged_ledger_is_refused_naming_the_path(tmp_path):
    """REQ-048 AC3: rule 11 (a ledger that cannot be read is never silently emptied)."""
    clone, side = clone_of(tmp_path, {"a.py": "A = 1\n"}), sidecar_of(tmp_path)
    write(side, {"cache/inventory.json": "{not json"})
    done = run(clone, side)
    assert done.returncode == 1 and "cache/inventory.json" in done.stdout


@pytest.mark.parametrize(
    ("path", "language"),
    [
        ("test_a.py", "Python"),
        ("pkg/a_test.py", "Python"),
        ("src/a.test.js", "JavaScript"),
        ("src/a.spec.tsx", "TypeScript"),
        ("src/__tests__/a.ts", "TypeScript"),
        ("a/b_test.go", "Go"),
        ("mod/src/test/java/A.java", "Java"),
        ("mod/src/test/kotlin/A.kt", "Kotlin"),
        ("x/FooTest.java", "Java"),
        ("x/FooTests.java", "Java"),
        ("x/FooTests.cs", "C#"),
        ("x/App.Tests.csproj", "C#"),
        ("spec/a_spec.rb", "Ruby"),
        ("test/a_test.rb", "Ruby"),
        ("tests/it.rs", "Rust"),
        ("t/FooTest.php", "PHP"),
    ],
)
def test_rule12_each_language_is_found(path, language):
    """REQ-048 AC3: rule 12 (the rule's patterns, each with its language)."""
    assert survey.detect_test_files([path]) == [
        {"framework": None, "language": language, "path": path}
    ]


def test_rule12_a_mixed_codebase_with_framework_as_data(tmp_path):
    """REQ-048 AC3: rule 12 (a framework only where a manifest declares one; no false hits)."""
    files = {
        "package.json": '{"devDependencies": {"vitest": "1.0.0"}}\n',
        "web/a.test.js": "\n",
        "pyproject.toml": '[project]\ndependencies = ["pytest"]\n',
        "test_a.py": "\n",
        "b_test.go": "\n",
        "contest.py": "\n",
        "src/latest.js": "\n",
        "tests/data.json": "{}\n",
    }
    found = {t["path"]: t for t in survey_of(tmp_path, files)["test_files"]}
    assert sorted(found) == ["b_test.go", "test_a.py", "web/a.test.js"]
    assert found["web/a.test.js"]["framework"] == "vitest"
    assert found["test_a.py"]["framework"] == "pytest"
    assert found["b_test.go"]["framework"] is None


def table_names() -> set[str]:
    table = tomllib.loads((SCRIPTS.parents[1] / survey.SIGNALS).read_text(encoding="utf-8"))
    return {name for row in table["stack"] for name in row["manifests"]}


def test_one_list_the_survey_reads_the_table():
    """REQ-064 AC5: SPEC-0057 rule 8: only the names Q-879-1 asks about are outside the table."""
    assert set(survey.manifest_names()) - set(survey.OUTSIDE_TABLE) == table_names()
    assert set(survey.OUTSIDE_TABLE) == {"*.csproj", "Gemfile", "composer.json"}
    assert not set(survey.OUTSIDE_TABLE) & table_names()


def test_one_list_every_manifest_keeps_a_language():
    """REQ-064 AC5: SPEC-0057 rule 8: a manifest of the table is never dropped for no language."""
    assert set(survey.manifest_names()) == set(survey.MANIFESTS)
    assert all(survey.MANIFESTS.values())


def test_one_list_table_manifests_new_to_the_survey_are_listed(tmp_path):
    """REQ-064 AC5: SPEC-0057 rule 8 (`requirements.txt` declares its framework as data)."""
    files = {"requirements.txt": "pytest\n", "app/pubspec.yaml": "name: x\n", "test_a.py": "\n"}
    data = survey_of(tmp_path, files)
    assert {m["path"] for m in data["manifests"]} == {"app/pubspec.yaml", "requirements.txt"}
    assert data["test_files"] == [{"path": "test_a.py", "language": "Python", "framework": "pytest"}]


def test_one_list_the_table_is_the_kits_and_never_the_repositorys(tmp_path):
    """REQ-064 AC5: SPEC-0057 rule 5: a table in the repository read changes nothing."""
    plant = '[[stack]]\nname = "x"\nmanifests = ["zanzibar.manifest"]\nlocks = []\n'
    data = survey_of(tmp_path, {"config/stack-signals.toml": plant, "zanzibar.manifest": "\n"})
    assert data["manifests"] == []


@pytest.mark.parametrize("table", [None, "stack = ["])
def test_one_list_a_table_that_cannot_be_read_is_refused(tmp_path, table):
    """REQ-064 AC5: SPEC-0057 rule 8: never an empty list; the refusal names the path only."""
    kit = tmp_path / "kit"
    (kit / "scripts/agk").mkdir(parents=True)
    for name in ("survey.py", "common.py"):
        shutil.copy(SCRIPTS / name, kit / "scripts/agk" / name)
    if table is not None:
        (kit / "config").mkdir()
        (kit / survey.SIGNALS).write_text(table, encoding="utf-8")
    clone, side = clone_of(tmp_path, {"a.py": "\n"}), sidecar_of(tmp_path)
    cmd = [sys.executable, str(kit / "scripts/agk/survey.py"), "--clone", str(clone)]
    done = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [*cmd, "--sidecar", str(side)], capture_output=True, text=True
    )
    assert done.returncode == 1
    assert done.stdout == f"refused: the signal table cannot be read (path: {survey.SIGNALS})\n"
    assert not (side / "cache").exists()


def test_rule12_adopt_detect_tests_is_unchanged(tmp_path):
    """REQ-048 AC3: rule 12 (`adopt.detect_tests` keeps its answer)."""
    write(tmp_path, {"tests/test_a.py": "\n", "tests/deep/b_test.py": "\n", "x.test.js": "\n"})
    assert adopt.detect_tests(tmp_path) == (["tests"], ["*_test.py", "test_*.py"])


def test_rule10_the_sidecar_comes_from_the_registry(tmp_path):
    """REQ-048 AC3: rule 10 (the state of an attached clone, found through `AGK_HOME`)."""
    import personal_state  # noqa: PLC0415 - the attach of build (c)

    clone, home = clone_of(tmp_path, {"a.py": "A = 1\n"}), tmp_path / "home"
    template = (SCRIPTS.parents[1] / "kit/templates/personal.toml").read_text(encoding="utf-8")
    side = home / "projects" / personal_state.project_id(clone)
    write(side, {"agk.toml": template})
    home_clones = {personal_state.common_dir(clone): side.name}
    personal_state.write_registry(home, home_clones)
    done = run(clone, None, AGK_HOME=str(home))
    assert done.returncode == 0, done.stdout
    assert inventory(side)["coverage"] == "0 of 1 files read"
    assert (side / "cache" / "inventory.json").stat().st_mode & 0o077 == 0


def test_rule10_refusals_name_the_option_and_nothing_else(tmp_path):
    """REQ-048 AC3: rule 10 (no state, a bad date, not a repository: refused, nothing written)."""
    clone = clone_of(tmp_path, {"a.py": "\n"})
    home = tmp_path / "empty"
    done = run(clone, None, AGK_HOME=str(home))
    assert done.returncode == 1 and "attached" in done.stdout
    side = sidecar_of(tmp_path)
    done = run(clone, side, "--today", "soon")
    assert done.returncode == 1 and "--today" in done.stdout and "soon" not in done.stdout
    plain = tmp_path / "plain"
    plain.mkdir()
    done = run(plain, side)
    assert done.returncode == 1 and not (side / "cache").exists()


def test_rule10_a_clone_with_no_commit_is_surveyed(tmp_path):
    """REQ-048 AC3: rule 10 (the index holds the files; churn is 0 and the coverage line prints)."""
    clone, side = clone_of(tmp_path, {"a.py": "A = 1\n"}, committed=False), sidecar_of(tmp_path)
    done = run(clone, side)
    assert done.stdout.splitlines()[-1] == "0 of 1 files read"
    assert inventory(side)["files"]["a.py"]["churn"] == 0


def test_rule10_the_script_imports_no_network_module_and_no_runner():
    """REQ-048 AC3: rule 10 (standard library only; nothing that imports or runs product code)."""
    tree = ast.parse((SCRIPTS / "survey.py").read_text(encoding="utf-8"))
    names = {
        a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    names |= {
        (n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
    }
    assert not names & {"socket", "urllib", "http", "requests", "importlib", "runpy", "ast"}
    assert names <= set(sys.stdlib_module_names) | {"common", "personal_state"}
    calls = {
        n.func.id
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert not calls & {"exec", "eval", "compile", "__import__"}
