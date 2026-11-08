"""Tests of `test_map.py build` (SPEC-0055 rule 5, build (c); REQ-062 AC3).

The map comes from the Python imports and the JavaScript or TypeScript import graph of the tree at
the head, folder conventions are the fallback, and the same tree gives the same bytes. Fixtures in
`tmp_path` only: invented data (`example.com`), no network, no install.
"""

from __future__ import annotations

import ast
import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "agk" / "test_map.py"
sys.path.insert(0, str(SCRIPT.parent))

import impact  # noqa: E402

OUT = ".agk-test-map.toml"
PY = 'test_dirs = ["tests"]\ntest_patterns = ["test_*.py"]\n'
JS = 'test_dirs = ["."]\ntest_patterns = ["*.test.ts", "*.test.js", "*Test.kt"]\n'


def git(root: Path, *args: str) -> str:
    who = ["-c", "user.name=Example", "-c", "user.email=dev@example.com"]
    done = subprocess.run(["git", *who, *args], cwd=root, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def repo(tmp_path: Path, config: str, files: dict[str, str]) -> Path:
    root = tmp_path / "r"
    root.mkdir()
    git(root, "init", "-q")
    for rel, body in {"agk.toml": config, **files}.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "one")
    return root


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    argv = [sys.executable, str(SCRIPT), *(args or ("build", "--root", str(root)))]
    return subprocess.run(argv, capture_output=True, text=True)


def built(root: Path) -> dict[str, list[str]]:
    done = run(root)
    assert done.returncode == 0, done.stdout + done.stderr
    parsed = tomllib.loads((root / OUT).read_text(encoding="utf-8"))
    return {e["code"]: e["tests"] for e in parsed.get("testing", {}).get("map", [])}


def test_python_imports_reach_a_test_through_the_closure(tmp_path):
    """REQ-062 AC3: rule 5, absolute, relative, package and `src/` imports, closed over."""
    root = repo(
        tmp_path,
        PY,
        {
            "src/shop/__init__.py": "",
            "src/shop/cart.py": "from .price import total\n",
            "src/shop/price.py": "from . import rates\n",
            "src/shop/rates.py": "",
            "src/shop/alone.py": "",
            "tests/conftest.py": "import fixtures_data\n",
            "tests/fixtures_data.py": "",
            "tests/test_cart.py": "from shop import cart\n",
        },
    )
    assert built(root) == {
        "src/shop/__init__.py": ["tests/test_cart.py"],
        "src/shop/cart.py": ["tests/test_cart.py"],
        "src/shop/price.py": ["tests/test_cart.py"],
        "src/shop/rates.py": ["tests/test_cart.py"],
        "tests/conftest.py": ["tests/test_cart.py"],
        "tests/fixtures_data.py": ["tests/test_cart.py"],
    }


def test_javascript_import_forms_resolve_and_a_cycle_ends(tmp_path):
    """REQ-062 AC3: rule 5, import and require lines read as text; a package adds nothing."""
    root = repo(
        tmp_path,
        JS,
        {
            "src/a.ts": "import {\n  b,\n} from './b.js';\nexport * from './c';\nimport 'pad';\n",
            "src/b.ts": "import a from './a';\n",
            "src/c/index.ts": "const d = require('../d');\n",
            "src/d.js": "async function e() { return import('./e.json'); }\n",
            "src/e.json": "{}\n",
            "src/other.ts": "",
            "src/a.test.ts": "import { a } from './a';\n",
        },
    )
    tests = ["src/a.test.ts"]
    assert built(root) == {
        p: tests for p in ("src/a.ts", "src/b.ts", "src/c/index.ts", "src/d.js", "src/e.json")
    }


def test_tsconfig_paths_as_the_compiler_reads_them(tmp_path):
    """REQ-062 AC3: rule 5, the nearest config, `extends`, comments, longest pattern, baseUrl."""
    base = """{
      // the shared settings
      "compilerOptions": {
        "baseUrl": ".",
        "paths": { "@/*": ["src/*"], "@/a/*": ["libs/x/*"], "exact": ["libs/one.ts"], },
      },
    }"""
    root = repo(
        tmp_path,
        JS,
        {
            "tsconfig.base.json": base,
            "app/tsconfig.json": '{ "extends": "../tsconfig.base.json" }',
            "src/a/b.ts": "",
            "src/plain.ts": "",
            "libs/x/b.ts": "",
            "libs/one.ts": "",
            "app/n.test.ts": "import '@/a/b';\nimport '@/plain';\nimport 'exact';\n"
            "import 'src/a/b';\n",
        },
    )
    tests = ["app/n.test.ts"]
    assert built(root) == {
        p: tests for p in ("libs/one.ts", "libs/x/b.ts", "src/a/b.ts", "src/plain.ts")
    }


def test_paths_without_base_url_are_relative_to_their_config(tmp_path):
    """REQ-062 AC3: rule 5, a pattern with no baseUrl is read from the folder of its config."""
    config = '{ "compilerOptions": { "paths": { "~/*": ["./src/*"] } } }'
    files = {"web/tsconfig.json": config, "web/src/z.ts": "", "web/z.test.ts": "import '~/z';\n"}
    assert built(repo(tmp_path, JS, files)) == {"web/src/z.ts": ["web/z.test.ts"]}


def test_a_malformed_tsconfig_adds_nothing_and_names_the_setting(tmp_path):
    """REQ-062 AC3: rule 5, one line naming the setting, never a value; the file stays unmapped."""
    files = {"tsconfig.json": "{ Zanzibar", "src/z.ts": "", "src/y.test.ts": "import '@/z';\n"}
    root = repo(tmp_path, JS, files)
    assert built(root) == {}
    out = run(root).stdout
    assert "setting: compilerOptions.paths" in out and "Zanzibar" not in out


def test_folder_conventions_are_the_fallback_only(tmp_path):
    """REQ-062 AC3: rule 5, a sibling and a module's `src/test/`, only where no import was read."""
    root = repo(
        tmp_path,
        JS,
        {
            "src/a/b.ts": "",
            "src/a/b.test.ts": "// no import of it\n",
            "src/a/c.ts": "",
            "src/a/c.test.ts": "import './d';\n",
            "src/a/d.ts": "",
            "src/a/d.test.ts": "import './c';\n",
            "m/src/main/x/Foo.kt": "class Foo\n",
            "m/src/test/x/FooTest.kt": "class FooTest\n",
            "m/src/main/x/Bar.kt": "class Bar\n",
        },
    )
    assert built(root) == {
        "m/src/main/x/Foo.kt": ["m/src/test/x/FooTest.kt"],
        "src/a/b.ts": ["src/a/b.test.ts"],
        "src/a/c.ts": ["src/a/d.test.ts"],
        "src/a/d.ts": ["src/a/c.test.ts"],
    }


def test_two_commits_with_one_tree_give_the_same_bytes_from_the_head(tmp_path):
    """REQ-062 AC3: rule 5, the first line names the tree; the working tree is not read."""
    files = {"app.py": "", "tests/test_app.py": "import app\n"}
    root = repo(tmp_path, PY, files)
    built(root)
    first = (root / OUT).read_bytes()
    assert first.split(b"\n")[0].decode() == f"# tree {git(root, 'rev-parse', 'HEAD^{tree}')}"
    git(root, "commit", "-q", "--allow-empty", "-m", "two")
    (root / "tests/test_app.py").write_text("", encoding="utf-8")
    (root / "agk.toml").write_text('test_patterns = ["nothing"]\n', encoding="utf-8")
    built(root)
    assert (root / OUT).read_bytes() == first


def test_a_committed_map_is_refused_and_the_build_commits_nothing(tmp_path):
    """REQ-062 AC3: rule 5 and principle 5, a generated map is never committed."""
    root = repo(tmp_path, PY, {"app.py": "", "tests/test_app.py": "import app\n"})
    head = git(root, "rev-parse", "HEAD")
    built(root)
    assert git(root, "rev-parse", "HEAD") == head and OUT not in git(root, "ls-files")
    git(root, "add", OUT)
    git(root, "commit", "-qm", "wrong")
    done = run(root)
    assert done.returncode == 1 and done.stdout.startswith("FAIL test_map:")


def test_an_unreadable_stack_adds_no_entries(tmp_path):
    """REQ-062 AC3: rule 5, a file that cannot be parsed or read leaves its files unmapped."""
    files = {
        "lib.py": "",
        "tests/test_bad.py": "def (:\nimport lib\n",
        "main.go": 'package main\nimport "lib"\n',
        "tests/test_big.py": "import lib\n" + "#" * (3 * 1024 * 1024),
    }
    assert built(repo(tmp_path, PY, files)) == {}


def test_entries_are_the_shape_impact_reads_and_select_a_test(tmp_path):
    """REQ-062 AC3: rule 5, the file's entries as `[testing] map` give a selection."""
    root = repo(tmp_path, PY, {"app.py": "", "tests/test_app.py": "import app\n"})
    built(root)
    body = (root / OUT).read_text(encoding="utf-8")
    config = root / "agk.toml"
    config.write_text(PY + '[testing]\nprofile = "balanced"\n' + body, encoding="utf-8")
    git(root, "add", "agk.toml")
    git(root, "commit", "-qm", "map")
    base = git(root, "rev-parse", "HEAD")
    (root / "app.py").write_text("x = 1\n", encoding="utf-8")
    git(root, "add", "app.py")
    git(root, "commit", "-qm", "change")
    found = impact.select(root, base, "HEAD")
    assert not found.full and [s.test for s in found.selected] == ["tests/test_app.py"]


def test_a_path_impact_would_refuse_is_left_out_and_quotes_stay_toml(tmp_path):
    """REQ-062 AC3: rule 5, a path that is no glob is unmapped; any other name is valid TOML."""
    files = {
        "a.py": "",
        "b.py": "",
        "a:b.py": "",
        "tests/test_w.py": "import a\nimport b\n",
        'tests/test_"é.py': "import a\n",
        "tests/test_x:y.py": "import a\n",
    }
    root = repo(tmp_path, PY, files)
    assert built(root) == {
        "a.py": ['tests/test_"é.py', "tests/test_w.py"],
        "b.py": ["tests/test_w.py"],
    }


def test_outside_a_repository_and_a_bad_call_are_refused(tmp_path):
    """REQ-062 AC3: rule 5, a tree that cannot be read fails with one line; usage is exit 2."""
    done = run(tmp_path, "build", "--root", str(tmp_path))
    assert done.returncode == 1 and done.stdout.startswith("FAIL test_map:")
    assert run(tmp_path, "nonsense").returncode == 2


def test_installed_standard_library_only_and_mapped():
    """REQ-062 AC3: rule 5, a sorted manifest entry, no third-party import, one map entry."""
    verbatim = json.loads((KIT_ROOT / "kit/manifest.json").read_text(encoding="utf-8"))["verbatim"]
    assert "scripts/agk/test_map.py" in verbatim
    scripts = [p for p in verbatim if p.startswith("scripts/agk/")]
    assert scripts == sorted(scripts)
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    names = {
        a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    names |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    local = {p.stem for p in SCRIPT.parent.glob("*.py")}
    assert names - set(sys.stdlib_module_names) - local == set() and not names & {
        "socket",
        "urllib",
    }
    entries = tomllib.loads((KIT_ROOT / "agk.toml").read_text(encoding="utf-8"))["testing"]["map"]
    assert any(e["code"] == "scripts/agk/test_map.py" for e in entries)
