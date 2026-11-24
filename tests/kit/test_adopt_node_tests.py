"""Adopt and init write the project's own `test_patterns` (brief #1891, ADR-0785; REQ-051 AC6).

`adopt.detect_tests` finds the web test names (`*.test.js`, `*.spec.mjs`, ... over the six
extensions the Node pack lints) as well as the Python ones, matched with `fnmatchcase` as
`impact.is_test_file` matches. With no test file it falls back to the stacks whose manifests of
`config/stack-signals.toml` the tree holds: a Python manifest gives today's `["test_*.py"]`, a
`package.json` the web names, both give both, and neither gives an empty list, which adopt names.
Init writes the same `test_patterns` line when it finds a test file or a manifest, and renders the
template byte for byte otherwise. A stamp that is not a list of strings is refused before any
write. Invented trees only (example.com), no network, no git call in adopt.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import adopt
import common
import doctor
import impact
import init
import pytest
import survey
import tree_walk

WEB = sorted(tree_walk.FRONTEND_PATTERNS)
EMPTY_LINE = (
    "tests: no test file found and no stack with known test names; test_patterns is empty, "
    "so no test is selected until a person sets it (setting: test_patterns)"
)


def tree(root: Path, *files: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for rel in files:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("// example.com\n" if not rel.endswith(".json") else "{}\n", "utf-8")
    return root


def git_dir(root: Path) -> Path:
    """A `.git` folder adopt reads without git: HEAD on `main`, no origin."""
    (root / ".git" / "refs" / "heads").mkdir(parents=True, exist_ok=True)
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    return root


def node_project(root: Path) -> Path:
    return tree(root, "package.json", "tsconfig.json", "src/price.ts", "tests/price.test.js")


def written(root: Path) -> dict:
    return tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))


# Answer 1: one list of web test patterns.


def test_req051_the_web_patterns_are_the_twelve_names():
    """REQ-051 AC6: answer 1 (the jest and vitest names over the six extensions)."""
    assert WEB == sorted(
        f"*.{kind}{ext}"
        for kind in ("test", "spec")
        for ext in (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")
    )
    assert adopt.FRONTEND_PATTERNS is tree_walk.FRONTEND_PATTERNS is doctor.FRONTEND_PATTERNS


def test_req051_every_web_extension_the_detector_knows_has_its_patterns():
    """REQ-051 AC6: answer 11 (the class stays closed: a language survey knows, adopt knows)."""
    missing = [
        f"{kind}{ext}"
        for ext, language in survey.LANGUAGES.items()
        if language in ("JavaScript", "TypeScript")
        for kind in ("*.test", "*.spec")
        if f"{kind}{ext}" not in tree_walk.FRONTEND_PATTERNS
    ]
    assert missing == [], (
        f"survey.LANGUAGES knows these, tree_walk.FRONTEND_PATTERNS not: {missing}"
    )


# Answer 2 and answer 9: detection by name, matched as the readers match.


def test_req051_the_measured_node_project_gives_its_js_pattern(tmp_path):
    """REQ-051 AC6: the brief's Measured line (before: `test_*.py`, after: `*.test.js`)."""
    root = node_project(tmp_path / "p")
    assert adopt.detect_tests(root) == (["tests"], ["*.test.js"])
    assert impact.is_test_file("tests/price.test.js", *adopt.detect_tests(root))


@pytest.mark.parametrize(
    ("files", "expected"),
    [
        (
            ("tests/test_a.py", "pkg/tests/b_test.py"),
            (["pkg/tests", "tests"], ["*_test.py", "test_*.py"]),
        ),
        (("package.json", "tests/cart.test.js"), (["tests"], ["*.test.js"])),
        (
            ("tsconfig.json", "src/a.test.ts", "src/b.spec.tsx", "src/c.test.js"),
            (["src"], ["*.spec.tsx", "*.test.js", "*.test.ts"]),
        ),
        (
            ("pyproject.toml", "package.json", "tests/test_a.py", "web/x.spec.jsx"),
            (["tests", "web"], ["*.spec.jsx", "test_*.py"]),
        ),
        (
            (
                "package.json",
                "packages/a/src/x.test.ts",
                "packages/b/tests/y.spec.mjs",
                "packages/a/node_modules/lib/z.test.js",
                "packages/b/node_modules/lib/w.spec.cjs",
            ),
            (["packages/a/src", "packages/b/tests"], ["*.spec.mjs", "*.test.ts"]),
        ),
        (("package.json", "x.test.cjs"), (["."], ["*.test.cjs"])),
    ],
    ids=["python-only", "node-only", "typescript-only", "mixed", "monorepo", "root-file"],
)
def test_req051_detection_by_name_for_each_layout(tmp_path, files, expected):
    """REQ-051 AC6: answers 2 and 9 (topmost folders as found, every pattern matched, sorted)."""
    assert adopt.detect_tests(tree(tmp_path / "p", *files)) == expected


def test_req051_python_only_output_is_unchanged(tmp_path):
    """REQ-051 AC6: answer 2 (Python output byte for byte as before)."""
    root = tree(tmp_path / "p", "requirements.txt", "tests/test_a.py", "tests/unit/test_b.py")
    assert adopt.detect_tests(root) == (["tests"], ["test_*.py"])


def test_req051_names_are_matched_with_case(tmp_path):
    """REQ-051 AC6: answer 2 and 9 (`fnmatchcase`, as `impact.is_test_file`, on every system)."""
    root = tree(tmp_path / "p", "package.json", "web/Cart.Test.js", "tests/cart.test.js")
    assert adopt.detect_tests(root) == (["tests"], ["*.test.js"])
    assert not impact.is_test_file("web/Cart.Test.js", ["web"], ["*.test.js"])


def test_req051_mts_and_cts_are_not_detected(tmp_path):
    """REQ-051 AC6: answer 9, Q-AN-5 (`.mts` and `.cts` are not names survey knows)."""
    root = tree(tmp_path / "p", "package.json", "tests/a.test.mts", "tests/b.spec.cts")
    assert adopt.detect_tests(root) == (["tests"], WEB)


# Answer 3: no test file found, the stack's patterns or none.


@pytest.mark.parametrize(
    ("files", "patterns"),
    [
        (("package.json", "src/index.js"), WEB),
        (("pyproject.toml", "src/app.py"), ["test_*.py"]),
        (("setup.py",), ["test_*.py"]),
        (("pyproject.toml", "web/package.json"), sorted(["test_*.py", *WEB])),
        (("go.mod", "main.go"), []),
        (("Cargo.toml",), []),
        ((), []),
        (("node_modules/lib/package.json", "examples/demo/package.json", "src/app.ts"), []),
    ],
    ids=["node", "python", "python-pip", "both", "go", "rust", "empty", "ignored-manifests"],
)
def test_req051_no_test_file_gives_the_stacks_patterns(tmp_path, files, patterns):
    """REQ-051 AC6: answer 3 (stack-signals manifests outside the skipped folders)."""
    assert adopt.detect_tests(tree(tmp_path / "p", *files)) == (["tests"], patterns)


def test_req051_adopt_names_an_empty_list(tmp_path, capsys):
    """REQ-051 AC6: answer 3 (adopt prints the line naming `test_patterns`)."""
    root = git_dir(tree(tmp_path / "p", "go.mod", "main.go"))
    assert adopt.main([str(root), "--unreleased"]) == 0
    assert EMPTY_LINE in capsys.readouterr().out.splitlines()
    assert written(root)["test_patterns"] == []
    assert written(root)["test_dirs"] == ["tests"]


# Answer 2 end to end: adopt writes the patterns, and the readers then select the test.


def test_req051_adopt_writes_the_node_patterns_and_the_test_is_selected(tmp_path, capsys):
    """REQ-051 AC6: the Measured line through `adopt.main` and `impact.is_test_file`."""
    root = git_dir(node_project(tmp_path / "p"))
    assert adopt.main([str(root), "--unreleased"]) == 0
    out = capsys.readouterr().out
    assert EMPTY_LINE not in out
    cfg = written(root)
    assert (cfg["test_dirs"], cfg["test_patterns"]) == (["tests"], ["*.test.js"])
    assert impact.is_test_file("tests/price.test.js", cfg["test_dirs"], cfg["test_patterns"])
    assert cfg["lint_paths"] == ["scripts/agk", ".claude/hooks"]  # Q-AN-1: unchanged
    assert "project_lint_paths" not in cfg


def test_req051_the_plugin_layout_writes_the_same_lines(tmp_path, capsys):
    """REQ-051 AC6: answer 8 (`--layout plugin` writes the same two lines)."""
    root = git_dir(node_project(tmp_path / "p"))
    code = adopt.main([str(root), "--unreleased", "--layout", "plugin", "--rehearsal"])
    out = capsys.readouterr().out
    assert code == 0, out
    cfg = written(root)
    assert (cfg["test_dirs"], cfg["test_patterns"]) == (["tests"], ["*.test.js"])


# Answer 4: init writes the same line.


def test_req051_init_writes_the_patterns_it_finds(tmp_path, capsys):
    """REQ-051 AC6: answer 4 (init on the Node project)."""
    root = node_project(tmp_path / "p")
    assert init.main([str(root), "--unreleased"]) == 0
    out = capsys.readouterr().out
    assert 'test_patterns: ["*.test.js"] (test files or a stack manifest found)' in out
    cfg = written(root)
    assert (cfg["test_dirs"], cfg["test_patterns"]) == (["tests"], ["*.test.js"])
    text = (root / "agk.toml").read_text(encoding="utf-8").splitlines()
    assert text[text.index('test_dirs = ["tests"]') + 1] == 'test_patterns = ["*.test.js"]'


def test_req051_init_on_a_manifest_only_tree_writes_the_stack(tmp_path, capsys):
    """REQ-051 AC6: answer 4 (a bare `package.json` gives web names, `go.mod` an empty list)."""
    node = tree(tmp_path / "n", "package.json")
    assert init.main([str(node), "--unreleased"]) == 0
    assert written(node)["test_patterns"] == WEB
    go = tree(tmp_path / "g", "go.mod")
    assert init.main([str(go), "--unreleased"]) == 0
    assert written(go)["test_patterns"] == []
    capsys.readouterr()


@pytest.mark.parametrize(
    "files",
    [
        (),
        ("README.md",),
        ("requirements.txt", "tests/test_a.py"),
        ("requirements.txt", "pkg/tests/a_test.py"),
        ("tests/test_a.py", "pkg/b_test.py"),
    ],
    ids=["empty", "plain", "python", "python-suffix", "python-both"],
)
def test_req051_init_on_an_empty_or_python_tree_renders_as_before(tmp_path, capsys, files):
    """REQ-051 AC6: answer 4, Q-AN-4 (byte for byte the template, no `test_patterns` line)."""
    root = tree(tmp_path / "p", *files)
    assert init.main([str(root), "--unreleased"]) == 0
    assert "test_patterns:" not in capsys.readouterr().out
    text = (root / "agk.toml").read_text(encoding="utf-8")
    assert "\ntest_patterns" not in text
    template = (init.KIT_ROOT / "kit" / "templates" / "agk.toml").read_text(encoding="utf-8")
    assert init.TEST_DIRS_LINE in template
    assert [ln for ln in text.splitlines() if ln.startswith("test_")] == [init.TEST_DIRS_LINE]


def test_req051_an_init_rerun_keeps_its_file(tmp_path, capsys):
    """REQ-051 AC6: answer 4 (a re-run compares against the same rendered file)."""
    root = node_project(tmp_path / "p")
    assert init.main([str(root), "--unreleased"]) == 0
    before = (root / "agk.toml").read_bytes()
    tree(root, "web/more.spec.tsx")
    assert init.main([str(root), "--unreleased"]) == 0
    assert (root / "agk.toml").read_bytes() == before
    assert "test_patterns:" not in capsys.readouterr().out.split("installed")[-1]


# Answer 5 and answer 8: the stamp is read in its form.


def stamp(root: Path, dirs: str, patterns: str) -> Path:
    git_dir(tree(root, "tests/test_a.py"))
    (root / "agk.toml").write_text(
        f'mode = "adopt"\ndefault_branch = "main"\n'
        f"test_dirs = {dirs}\ntest_patterns = {patterns}\n",
        encoding="utf-8",
    )
    return root


@pytest.mark.parametrize(
    ("dirs", "patterns", "setting"),
    [
        ('"tests"', '["test_*.py"]', "test_dirs"),
        ('["tests", 3]', '["test_*.py"]', "test_dirs"),
        ('["tests"]', '"test_*.py"', "test_patterns"),
        ('["tests"]', '["test_*.py", 1]', "test_patterns"),
    ],
    ids=["dirs-string", "dirs-number", "patterns-string", "patterns-number"],
)
def test_req051_a_malformed_stamp_is_refused_before_any_write(
    tmp_path, capsys, dirs, patterns, setting
):
    """REQ-051 AC6: answer 5 (refused naming the setting; nothing written; the stamp kept)."""
    root = stamp(tmp_path / "p", dirs, patterns)
    before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))
    stamped = (root / "agk.toml").read_bytes()
    assert adopt.main([str(root), "--unreleased"]) == 1
    out = capsys.readouterr().out
    what = "folder paths" if setting == "test_dirs" else "file-name patterns"
    assert f"refused: {setting} must be a list of {what} (setting: {setting})" in out
    assert sorted(p.relative_to(root).as_posix() for p in root.rglob("*")) == before
    assert (root / "agk.toml").read_bytes() == stamped


def test_req051_a_stamp_is_reused_never_widened(tmp_path, capsys):
    """REQ-051 AC6: answer 8 (stamped lists, a `\\` and a `./` folder kept as written)."""
    root = stamp(tmp_path / "p", '["web\\\\tests", "./tests"]', '["test_*.py"]')
    tree(root, "web/tests/a.test.js")
    plan, _entries, _branch = adopt.build_plan(root, "2026-11-24")
    toml = dict((rel, content) for rel, _action, content, _ in plan)["agk.toml"].decode("utf-8")
    cfg = tomllib.loads(toml)
    assert cfg["test_dirs"] == ["web\\tests", "./tests"]
    assert cfg["test_patterns"] == ["test_*.py"]
    assert [common.test_folder(d) for d in cfg["test_dirs"]] == ["web/tests", "tests"]
    capsys.readouterr()


# Answer 6: test files no name pattern can reach.


def test_req051_unreached_test_folder_files_are_counted(tmp_path, capsys):
    """REQ-051 AC6: answer 6, Q-AN-3 (`__tests__/` and a `test/` beside `package.json`)."""
    root = tree(
        tmp_path / "p",
        "package.json",
        "src/__tests__/cart.js",
        "src/__tests__/nav.test.ts",
        "test/price.mjs",
        "lib/test/helper.js",
        "test/readme.md",
    )
    scan = adopt.scan_tests(root)
    assert (scan.dirs, scan.patterns) == (["src/__tests__"], ["*.test.ts"])
    assert adopt.unreached(scan, scan.patterns) == 2
    assert adopt.unreached(scan, ["*.js", "*.mjs", "*.ts"]) == 0
    line = (
        "tests: 2 files in __tests__ or test folders match no test_patterns entry "
        "(setting: test_patterns)"
    )
    git_dir(root)
    assert adopt.main([str(root), "--unreleased"]) == 0
    assert line in capsys.readouterr().out.splitlines()
    assert "*.js" not in written(root)["test_patterns"]
    other = node_project(tmp_path / "i")
    tree(other, "test/price.cjs")
    assert init.main([str(other), "--unreleased"]) == 0
    assert line.replace("2 files", "1 files") in capsys.readouterr().out.splitlines()


# Answer 8: the readers of an empty list.


def test_req051_an_empty_list_is_read_without_error(tmp_path, repo):
    """REQ-051 AC6: answer 8 (`[]` read by impact, markers and doctor)."""
    toml = 'default_branch = "main"\ntest_dirs = ["tests"]\ntest_patterns = []\n'
    repo.commit({"agk.toml": toml, "tests/test_a.py": "# REQ-001\n", "app.py": "# a\n"}, "base")
    base = repo.git("rev-parse", "HEAD").strip()
    repo.commit({"tests/test_a.py": "# REQ-001 changed\n"}, "change")
    found = impact.impact(repo.root, base, repo.git("rev-parse", "HEAD").strip())
    assert "tests/test_a.py" not in [t for t, *_ in getattr(found, "tests", [])]
    assert not impact.is_test_file("tests/test_a.py", ["tests"], [])
    assert common.find_markers(repo.root, ["tests"], []) in ({}, [], set())
    assert doctor.frontend_lines(repo.root) == []
    repo.write("tests/cart.test.js", "// example.com\n")
    assert doctor.frontend_lines(repo.root) == [
        "tests: test_dirs and test_patterns match no test file; 1 files match the "
        "front-end test patterns (setting: test_dirs)"
    ]


def test_req051_an_unreadable_stack_table_is_refused_before_any_write(
    tmp_path, capsys, monkeypatch
):
    """REQ-051 AC6: answer 3 (the kit's own table cannot be read: adopt writes nothing, exit 3)."""
    root = git_dir(tree(tmp_path / "p", "package.json"))
    monkeypatch.setattr(adopt, "SIGNALS", tmp_path / "missing" / "stack-signals.toml")
    assert adopt.main([str(root), "--unreleased"]) == 3
    assert "error: cannot read the kit sources (FileNotFoundError)" in capsys.readouterr().out
    assert sorted(p.name for p in root.iterdir()) == [".git", "package.json"]


def test_req051_a_test_folder_beside_a_nested_package_json_is_counted(tmp_path):
    """REQ-051 AC6: answer 6 (mocha's `test/` beside a workspace's own `package.json`)."""
    root = tree(
        tmp_path / "p",
        "packages/api/package.json",
        "packages/api/test/route.js",
        "packages/web/test/page.js",
        "tests/cart.test.js",
    )
    scan = adopt.scan_tests(root)
    assert scan.candidates == ["route.js"]
    assert adopt.unreached(scan, scan.patterns) == 1
