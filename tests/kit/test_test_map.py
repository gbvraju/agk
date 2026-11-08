"""Tests of `test_map.py build` (SPEC-0055 rule 5, build (c); REQ-062 AC3).

The map comes from the Python imports, the JavaScript or TypeScript import graph, Gradle modules,
Xcode targets and Go packages (build (d)) of the tree at the head, folder conventions are the
fallback, and the same tree gives the same bytes. Fixtures in
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
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *who, *args], cwd=root, capture_output=True, text=True
    )
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
    return subprocess.run(  # nosec B603 - fixed argument list from sys.executable, no shell
        argv, capture_output=True, text=True
    )


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


def test_the_installed_ignore_block_keeps_the_map_out_of_git(tmp_path):
    """REQ-062 AC3: brief #812 answer 3, the installed template ignores the map (ADR-0379)."""
    root = repo(tmp_path, PY, {"a.py": "x = 1\n"})
    template = KIT_ROOT / "kit" / "templates" / "gitignore"
    (root / ".gitignore").write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    (root / OUT).write_text("# tree example\n", encoding="utf-8")
    assert git(root, "status", "--porcelain", "--", OUT) == ""
    git(root, "check-ignore", "-q", OUT)


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


STACKS = 'test_dirs = ["."]\ntest_patterns = ["*Test.kt", "*_test.go", "*Tests.swift"]\n'
APP_TEST = "app/src/test/x/AppTest.kt"
CORE_TEST = "lib/core/src/test/CoreTest.kt"


def test_gradle_modules_reach_what_their_project_dependencies_reach(tmp_path):
    """REQ-062 AC3: rule 5, `settings.gradle` and `project(...)`, at module granularity."""
    settings = (
        "rootProject.name = 'shop'\n// include ':dead'\ninclude ':app',\n        ':lib:core'\n"
        "include(\":lib:base\", ':other', ':dead2')\nincludeBuild 'build-logic'\n"
    )
    app = "dependencies {\n  implementation project(':lib:core')\n  // project(':other')\n}\n"
    files = {
        "settings.gradle": settings,
        "gradle.properties": "a=b\n",
        "app/build.gradle": app,
        "app/src/main/x/App.kt": "",
        APP_TEST: "",
        "lib/core/build.gradle.kts": 'dependencies { api(project(path = ":lib:base")) }\n',
        "lib/core/src/main/Core.kt": "",
        CORE_TEST: "",
        "lib/base/build.gradle": "",
        "lib/base/src/main/Base.kt": "",
        "other/src/main/O.kt": "",
        "other/src/test/OTest.kt": "",
        "build-logic/src/main/P.kt": "",
    }
    both = [APP_TEST, CORE_TEST]
    assert built(repo(tmp_path, STACKS, files)) == {
        "app/build.gradle": [APP_TEST],
        "app/src/main/x/App.kt": [APP_TEST],
        "lib/base/build.gradle": both,
        "lib/base/src/main/Base.kt": both,
        "lib/core/build.gradle.kts": both,
        "lib/core/src/main/Core.kt": both,
        "other/src/main/O.kt": ["other/src/test/OTest.kt"],
    }


def test_gradle_kotlin_settings_in_a_folder_with_project_dirs(tmp_path):
    """REQ-062 AC3: rule 5, a build below the root, `projectDir` and a relative `project(...)`."""
    settings = (
        'include(":feature")\ninclude(":feature:api")\n'
        'project(":feature").projectDir = file("modules/feature")\n'
        'project(":feature:api").projectDir = File(rootDir, "modules/api")\n'
    )
    test = "android/modules/feature/src/test/FTest.kt"
    files = {
        "android/settings.gradle.kts": settings,
        "android/modules/feature/build.gradle.kts": 'dependencies { api(project("api")) }\n',
        "android/modules/feature/src/main/F.kt": "",
        test: "",
        "android/modules/api/src/main/A.kt": "",
        "android/tools/T.kt": "",
    }
    assert built(repo(tmp_path, STACKS, files)) == {
        "android/modules/api/src/main/A.kt": [test],
        "android/modules/feature/build.gradle.kts": [test],
        "android/modules/feature/src/main/F.kt": [test],
    }


def test_gradle_single_project_maps_only_its_source_folder(tmp_path):
    """REQ-062 AC3: rule 5, the root project owns `src/`; other root files stay unmapped."""
    files = {
        "settings.gradle": "rootProject.name = 'x'\n",
        "build.gradle": "",
        "src/main/a/A.kt": "",
        "src/test/a/BTest.kt": "",
        "tools/T.kt": "",
    }
    assert built(repo(tmp_path, STACKS, files)) == {"src/main/a/A.kt": ["src/test/a/BTest.kt"]}


def test_gradle_settings_too_large_to_read_leave_the_folder_convention(tmp_path):
    """REQ-062 AC3: rule 5, a stack that cannot be read adds nothing; the convention remains."""
    files = {
        "settings.gradle": "include ':m'\n" + "//" * (2 * 1024 * 1024),
        "m/src/main/x/Foo.kt": "",
        "m/src/main/x/Bar.kt": "",
        "m/src/test/x/FooTest.kt": "",
    }
    assert built(repo(tmp_path, STACKS, files)) == {"m/src/main/x/Foo.kt": ["m/src/test/x/FooTest.kt"]}


def test_go_packages_follow_the_import_lines_and_go_mod(tmp_path):
    """REQ-062 AC3: rule 5, grouped and named imports, comments and strings, `replace`, a nested module."""
    cart = (
        'package cart // one\n\n/* import "example.com/shop/dead" */\nimport (\n'
        '\tp "example.com/shop/price"\n\t_ `example.com/pad`\n\t// "example.com/shop/dead"\n'
        '\t"example.com/shop/sub"\n\t"fmt"\n)\n\nconst s = `\nimport "example.com/shop/dead"\n`\n'
    )
    files = {
        "go.mod": "module example.com/shop // the shop\n\ngo 1.22\n\nreplace example.com/pad => ./third/pad\n",
        "third/pad/go.mod": "module example.com/forked\n",
        "third/pad/pad.go": "package pad\n",
        "sub/go.mod": "module example.com/other\n",
        "sub/sub.go": "package sub\n",
        "cart/cart.go": cart,
        "cart/more.go": "package cart\n",
        "cart/cart_test.go": "package cart\n",
        "price/price.go": 'package price\nimport "example.com/shop/rate"\n',
        "price/extra.go": "package price\n",
        "price/price_test.go": 'package price\n\nimport h "example.com/shop/helper"\n',
        "rate/rate.go": "package rate\n",
        "helper/helper.go": "package helper\n",
        "dead/dead.go": "package dead\n",
        "alone/alone.go": "package alone\n",
    }
    one, two = ["cart/cart_test.go"], ["cart/cart_test.go", "price/price_test.go"]
    assert built(repo(tmp_path, STACKS, files)) == {
        "cart/cart.go": one,
        "cart/more.go": one,
        "helper/helper.go": ["price/price_test.go"],
        "price/extra.go": two,
        "price/price.go": two,
        "rate/rate.go": two,
        "third/pad/pad.go": one,
    }


def test_go_with_no_readable_go_mod_adds_only_the_convention(tmp_path):
    """REQ-062 AC3: rule 5, no `go.mod`, or none that names a module, adds no package entries."""
    code = 'package a\nimport "example.com/x/b"\n'
    files = {"a.go": code, "o.go": "package a\n", "b/b.go": "package b\n", "a_test.go": code}
    for name, extra in (("none", {}), ("bad", {"go.mod": "go 1.22\n"})):
        (tmp_path / name).mkdir()
        assert built(repo(tmp_path / name, STACKS, {**files, **extra})) == {"a.go": ["a_test.go"]}


PBX = """// !$*UTF8*$!
{
  archiveVersion = 1;
  objects = {
    F1 /* Cart.swift in Sources */ = {isa = PBXBuildFile; fileRef = R1 /* Cart.swift */; };
    F2 = {isa = PBXBuildFile; fileRef = R2; };
    F3 = {isa = PBXBuildFile; fileRef = R3; };
    F4 = {isa = PBXBuildFile; fileRef = R4; };
    F5 = {isa = PBXBuildFile; fileRef = V1; };
    F6 = {isa = PBXBuildFile; fileRef = R9; };
    R1 /* Cart.swift */ = {isa = PBXFileReference; path = Cart.swift; sourceTree = "<group>"; };
    R2 = {isa = PBXFileReference; name = Price; path = "My Lib/Price.swift"; sourceTree = SOURCE_ROOT; };
    R3 = {isa = PBXFileReference; path = CartTests.swift; sourceTree = "<group>"; };
    R4 = {isa = PBXFileReference; path = Other.swift; sourceTree = "<group>"; };
    R5 = {isa = PBXFileReference; path = en.lproj/Main.strings; sourceTree = "<group>"; };
    R9 = {isa = PBXFileReference; path = App.app; sourceTree = BUILT_PRODUCTS_DIR; };
    V1 = {isa = PBXVariantGroup; children = (R5,); name = Main.strings; sourceTree = "<group>"; };
    G0 = {isa = PBXGroup; children = (G1, G2, G3, R2, R9,); sourceTree = "<group>"; };
    G1 = {isa = PBXGroup; children = (R1, V1,); path = App; sourceTree = "<group>"; };
    G2 = {isa = PBXGroup; children = (R3,); path = AppTests; sourceTree = "<group>"; };
    G3 = {isa = PBXGroup; children = (R4,); name = Virtual; sourceTree = "<group>"; };
    S1 = {isa = PBXSourcesBuildPhase; files = (F1 /* Cart.swift in Sources */, F2,); };
    S2 = {isa = PBXSourcesBuildPhase; files = (F3,); };
    S3 = {isa = PBXSourcesBuildPhase; files = (F4,); };
    S4 = {isa = PBXResourcesBuildPhase; files = (F5, F6,); };
    D1 = {isa = PBXTargetDependency; target = T1 /* App */; };
    T1 = {isa = PBXNativeTarget; buildPhases = (S1, S4,); dependencies = (); name = App; };
    T2 = {isa = PBXNativeTarget; buildPhases = (S2,); dependencies = (D1,); name = AppTests; };
    T3 = {isa = PBXNativeTarget; buildPhases = (S3,); dependencies = (); name = Other; };
    P1 = {isa = PBXProject; mainGroup = G0; projectDirPath = ""; targets = (T1, T2, T3,); };
  };
  rootObject = P1;
}
"""
PBX_FILE = "ios/Shop.xcodeproj/project.pbxproj"
XCODE_TREE = {
    "ios/App/Cart.swift": "",
    "ios/App/en.lproj/Main.strings": "",
    "ios/My Lib/Price.swift": "",
    "ios/AppTests/CartTests.swift": "",
    "ios/Other.swift": "",
}


def test_xcode_targets_reach_their_files_and_their_dependencies(tmp_path):
    """REQ-062 AC3: rule 5, build phases, groups, a variant group and target dependencies."""
    test = ["ios/AppTests/CartTests.swift"]
    assert built(repo(tmp_path, STACKS, {PBX_FILE: PBX, **XCODE_TREE})) == {
        "ios/App/Cart.swift": test,
        "ios/App/en.lproj/Main.strings": test,
        "ios/My Lib/Price.swift": test,
    }


def test_xcode_synchronized_folders_belong_to_their_target(tmp_path):
    """REQ-062 AC3: rule 5, a folder synchronized with a target gives that target its files."""
    project = """{ objects = {
      Y1 = {isa = PBXFileSystemSynchronizedRootGroup; path = App; sourceTree = "<group>"; };
      Y2 = {isa = PBXFileSystemSynchronizedRootGroup; path = AppTests; sourceTree = "<group>"; };
      G0 = {isa = PBXGroup; children = (Y1, Y2,); sourceTree = "<group>"; };
      D1 = {isa = PBXTargetDependency; target = T1; };
      T1 = {isa = PBXNativeTarget; buildPhases = (); dependencies = ();
            fileSystemSynchronizedGroups = (Y1,); };
      T2 = {isa = PBXNativeTarget; buildPhases = (); dependencies = (D1,);
            fileSystemSynchronizedGroups = (Y2,); };
      P1 = {isa = PBXProject; mainGroup = G0; targets = (T1, T2,); };
    }; rootObject = P1; }"""
    files = {
        "A.xcodeproj/project.pbxproj": project,
        "App/x/Cart.swift": "",
        "AppTests/CartTests.swift": "",
        "Apps/Far.swift": "",
    }
    assert built(repo(tmp_path, STACKS, files)) == {"App/x/Cart.swift": ["AppTests/CartTests.swift"]}


def test_a_broken_xcode_project_adds_no_entries(tmp_path):
    """REQ-062 AC3: rule 5, a project file that cannot be parsed leaves its files unmapped."""
    for name, broken in (("cut", PBX[:400]), ("eq", PBX.replace("rootObject =", "rootObject"))):
        (tmp_path / name).mkdir()
        assert built(repo(tmp_path / name, STACKS, {PBX_FILE: broken, **XCODE_TREE})) == {}


def test_the_three_stacks_give_the_same_bytes_from_the_head(tmp_path):
    """REQ-062 AC3: rule 5, two commits with one tree give the same bytes for these stacks too."""
    files = {
        PBX_FILE: PBX,
        **XCODE_TREE,
        "go.mod": "module example.com/z\n",
        "g/g.go": "package g\n",
        "g/g_test.go": "package g\n",
        "settings.gradle": "include ':m'\n",
        "m/M.kt": "",
        "m/MTest.kt": "",
    }
    root = repo(tmp_path, STACKS, files)
    built(root)
    first = (root / OUT).read_bytes()
    assert b'code = "m/M.kt"' in first and b'code = "g/g.go"' in first
    git(root, "commit", "-q", "--allow-empty", "-m", "two")
    (root / "go.mod").write_text("", encoding="utf-8")
    built(root)
    assert (root / OUT).read_bytes() == first
