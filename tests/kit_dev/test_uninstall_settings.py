"""The uninstall knows every agk.toml setting the kit reads (brief #1892, ADR-0786; REQ-009).

`config.KIT_SETTINGS` is the one list of the top-level keys and tables the kit reads: an AST walk of
`scripts/agk` finds every name read from `config_source(...)` and each must be listed (answer 9 (a),
answer 10), and every top-level key and table of both agk.toml templates is listed too (9 (b)).
`uninstall.py` deletes an agk.toml that holds only those names, keeps one with the person's own
key, table or key inside a known table, naming each by key and never a value (answers 2 and 3);
deletes `config/reviewers.yaml` only when it is a released template with its one maintainers
handle filled in (answer 4); and names `config/agk-baseline/` without deleting it (answer 5).

A stub plugin at 2.0.0 whose table lists the real reviewers templates, git work trees in temporary
folders, invented data only (`dev-example`, example.com) and no network.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AGK = ROOT / "scripts" / "agk"
sys.path.insert(0, str(AGK))
import common  # noqa: E402
import config  # noqa: E402
import uninstall  # noqa: E402

REVIEWERS = ("kit/templates/reviewers.yaml", "kit/templates/reviewers.adopt.yaml")
TOML_TEMPLATES = ("kit/templates/agk.toml", "kit/templates/agk.adopt.toml")
# The names the brief found missing on main at 130d5bbf (AD-10).
MISSING_ON_MAIN = (
    "project_lint_paths",
    "rule_tags_from",
    "personal",
    "proof",
    "capacity",
    "caps",
    "failures",
    "scorecard",
    "checklist",
    "cost",
    "tidy",
)
BASELINE_LINE = (
    "kept config/agk-baseline/ (path class config/agk-baseline/: the gates' and the history "
    "scan's records of your project; delete by hand if no longer wanted)"
)
# An adopted web project of the clean layout: only the kit's settings, `project_lint_paths` among them.
WEB_TOML = (
    'mode = "adopt"\nversion = "2.0.0"\ninstalled = "2026-11-24"\ndefault_branch = "main"\n'
    'test_dirs = ["tests"]\ntest_patterns = ["*.test.js"]\nlint_paths = ["scripts/agk"]\n'
    'project_lint_paths = ["src/**"]\nproject_tests = ""\nunused_code = ""\ncoverage = ""\n'
    'mutation = ""\nac_coverage = "warn"\nproof_timeout = 900\ninbox_hours = 48\n'
    'pr_mode = "strict"\nrequired_checks = ["proof", "governance"]\nagent_apps = ["claude"]\n'
    'review_mode = "solo"\ngovernance = { level = "light" }\nexecution = "local"\n'
    'touched_files = "hold"\n\n[kit]\nlayout = "plugin"\nplugin_version = "2.0.0"\n'
)
INIT_TOML = (
    'mode = "init"\nversion = "2.0.0"\ninstalled = "2026-11-24"\ndefault_branch = "main"\n'
    'test_dirs = ["tests"]\npr_mode = "strict"\nreview_mode = "{review}"\n'
    'governance = {{ level = "light" }}\nexecution = "hosted"\ntouched_files = "meet"\n'
)
BASELINE = {
    "config/agk-baseline/lint.json": '{"src/app.js": 2}\n',
    "config/agk-baseline/history.json": '{"scanned": "2026-11-24"}\n',
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - local git, fixed list
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout


def write(root: Path, files: dict[str, str | bytes]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(text, encoding="utf-8", newline="")


def rendered(src: str, handle: str = "@dev-example") -> str:
    """What init or adopt writes from SRC with the person's login (`init.apply_setup`)."""
    return (ROOT / src).read_text(encoding="utf-8").replace("@REPLACE-ME", handle)


@pytest.fixture
def kit(tmp_path, monkeypatch) -> Path:
    """A stub plugin at 2.0.0 whose table lists the real reviewers templates of this checkout."""
    root = tmp_path / "plugin-example"
    shipped = {"scripts/agk/check_x.py": "print('x')\n"}
    write(root, shipped)
    for src in (*REVIEWERS, *TOML_TEMPLATES, "kit/templates/clean-claude.md"):
        write(root, {src: (ROOT / src).read_text(encoding="utf-8")})
    manifest = {
        "kit_version": "2.0.0",
        "verbatim": sorted(shipped),
        "templates": {
            "agk.toml": "kit/templates/agk.toml",
            "config/reviewers.yaml": "kit/templates/reviewers.yaml",
        },
        "rendered": [],
        "adopt": {
            "skip": [],
            "blocks": {},
            "templates": {
                "agk.toml": "kit/templates/agk.adopt.toml",
                "config/reviewers.yaml": "kit/templates/reviewers.adopt.yaml",
            },
        },
    }
    templates = {src: [digest(common.lf((ROOT / src).read_bytes()))] for src in REVIEWERS}
    table = {
        "table": 1,
        "releases": {
            "1.0.0": {"verbatim": {}, "blocks": {}, "templates": {REVIEWERS[0]: ["0" * 64]}},
            "2.0.0": {
                "verbatim": {p: [digest(t.encode())] for p, t in shipped.items()},
                "blocks": {},
                "templates": templates,
            },
        },
    }
    write(root, {"kit/manifest.json": json.dumps(manifest), "kit/hashes.json": json.dumps(table)})
    monkeypatch.setattr(uninstall, "KIT_ROOT", root)
    return root


def project(tmp_path: Path, files: dict[str, str | bytes], name: str = "web") -> Path:
    target = tmp_path / name
    target.mkdir()
    git(target, "init", "-q", "-b", "main")
    git(target, "config", "user.email", "dev@example.com")
    git(target, "config", "user.name", "dev-example")
    git(target, "config", "commit.gpgsign", "false")
    listed = {"config/protected-paths.txt": "config/\nagk.toml\n"}
    write(target, {"README.md": "A sample web product of example.com.\n", **listed, **files})
    git(target, "add", "-A")
    git(target, "commit", "-q", "-m", "install")
    return target


def run(capsys, target: Path, *args: str) -> tuple[int, list[str]]:
    code = uninstall.main([str(target), *args])
    return code, capsys.readouterr().out.splitlines()


def line_of(out: list[str], rel: str) -> str:
    return next(ln for ln in out if ln.split(" ", 1)[-1].startswith(rel + " ") or ln.endswith(rel))


# --- answer 9 (a): every name a reader takes is listed -------------------------------------------


def _constants(trees: dict[Path, ast.Module]) -> tuple[dict, dict]:
    local: dict[Path, dict[str, str]] = {}
    every: dict[str, set[str]] = {}
    for path, tree in trees.items():
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                if isinstance(node.value.value, str):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            local.setdefault(path, {})[target.id] = node.value.value
                            every.setdefault(target.id, set()).add(node.value.value)
    return local, every


def _is_source(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (isinstance(func, ast.Name) and func.id == "config_source") or (
        isinstance(func, ast.Attribute) and func.attr == "config_source"
    )


def names_read() -> dict[str, set[str]]:
    """Name -> the files that read it from `config_source(...)`: by `.get`, `[...]` or `in`,
    directly or through a local bound to it; a literal or a module constant (its own file's, else
    any file's of that name, as an import brings it)."""
    trees = {p: ast.parse(p.read_text(encoding="utf-8")) for p in sorted(AGK.rglob("*.py"))}
    local, every = _constants(trees)
    found: dict[str, set[str]] = {}

    def resolve(node: ast.AST, path: Path) -> set[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return {node.value}
        if isinstance(node, ast.Name):
            mine = local.get(path, {})
            return {mine[node.id]} if node.id in mine else every.get(node.id, set())
        if isinstance(node, ast.Attribute):
            return every.get(node.attr, set())
        return set()

    for path, tree in trees.items():
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            bound = {
                t.id
                for n in ast.walk(fn)
                if isinstance(n, ast.Assign) and _is_source(n.value)
                for t in n.targets
                if isinstance(t, ast.Name)
            }

            def source(node: ast.AST, bound: set[str] = bound) -> bool:
                return _is_source(node) or (isinstance(node, ast.Name) and node.id in bound)

            for n in ast.walk(fn):
                got: set[str] = set()
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                    if n.func.attr == "get" and source(n.func.value) and n.args:
                        got = resolve(n.args[0], path)
                elif isinstance(n, ast.Subscript) and source(n.value):
                    got = resolve(n.slice, path)
                elif isinstance(n, ast.Compare) and len(n.ops) == 1:
                    if isinstance(n.ops[0], (ast.In, ast.NotIn)) and source(n.comparators[0]):
                        got = resolve(n.left, path)
                for name in got:
                    found.setdefault(name, set()).add(path.relative_to(ROOT).as_posix())
    return found


def test_every_name_a_reader_takes_is_a_kit_setting():
    """REQ-009: answers 1, 9 (a) and 10 (a new reader's name cannot be missed again)."""
    found = names_read()
    assert {"flow", "testing", "project_lint_paths", "personal"} <= set(found)  # the walk sees
    missing = sorted(f"{n} ({', '.join(sorted(f))})" for n, f in found.items() if n not in
                     config.KIT_SETTINGS)  # fmt: skip
    assert missing == [], f"names read by the kit that config.KIT_SETTINGS lacks: {missing}"


def test_the_names_missing_on_main_are_kit_settings_now():
    """REQ-009: answer 1 (the 11 names of AD-10 and the readers the walk cannot follow)."""
    assert set(MISSING_ON_MAIN) <= config.KIT_SETTINGS
    assert {"lock_dir", "lock_stale_minutes", "guard", "engines", "paused"} <= config.KIT_SETTINGS
    assert set(common.DEFAULT_CONFIG) | set(config.TABLE_KEYS) <= config.KIT_SETTINGS
    assert config.KIT_SETTINGS == (
        frozenset(common.DEFAULT_CONFIG)
        | config.TOP_KEYS
        | frozenset(config.TABLE_KEYS)
        | config.OTHER_TABLES
    )
    assert uninstall.kit_settings() is config.KIT_SETTINGS
    assert not hasattr(uninstall, "MORE_SETTINGS")  # the template parse is gone
    # A key of a table never counts at the top level (ADR-0527's misplaced settings).
    inner = set().union(*config.TABLE_KEYS.values(), common.PERSONAL_KEYS)
    assert {"auto_merge", "queue", "strongest"} & config.KIT_SETTINGS == set()
    assert inner - config.KIT_SETTINGS == inner


# --- answer 9 (b): every template name is listed ---------------------------------------------------

HEAD = re.compile(r"^#?\s*\[([A-Za-z_][\w-]*)(?:\.[\w.-]+)?\]\s*$")
KEY = re.compile(r"^#?\s*([A-Za-z_][\w-]*)\s*=")


def template_names(text: str) -> set[str]:
    """The top-level keys and tables of a template, set or commented out: a key counts only above
    the first table header, set or commented."""
    names, table = set(), None
    for line in text.splitlines():
        head = HEAD.match(line)
        if head:
            table = head.group(1)
            names.add(table)
        elif table is None and (key := KEY.match(line)):
            names.add(key.group(1))
    return names


@pytest.mark.parametrize("src", TOML_TEMPLATES)
def test_every_top_level_name_of_the_templates_is_a_kit_setting(src):
    """REQ-009: answer 9 (b), with the `[kit]` table `init.clean_toml` adds."""
    import init  # noqa: PLC0415

    text = (ROOT / src).read_text(encoding="utf-8")
    names = template_names(text) | template_names(init.clean_toml(text, "2.0.0"))
    assert {"mode", "version", "governance", "kit"} <= names
    assert sorted(names - config.KIT_SETTINGS) == []


# --- answers 3 to 5 on a project ----------------------------------------------------------------


def web_files(newline: str = "\n") -> dict[str, str | bytes]:
    files: dict[str, str | bytes] = {
        "agk.toml": WEB_TOML,
        "config/reviewers.yaml": rendered(REVIEWERS[1]),
        **BASELINE,
        "src/app.js": "console.log('example.com')\n",
    }
    if newline != "\n":
        for rel in ("agk.toml", "config/reviewers.yaml"):
            text = files[rel]
            assert isinstance(text, str)
            files[rel] = text.replace("\n", newline).encode("utf-8")
    return files


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_an_adopted_clean_project_loses_its_kit_settings_and_reviewers(
    tmp_path, kit, capsys, newline
):
    """REQ-009: answers 3, 4, 5 and 9 (c), (h): AD-10's web project, LF and CRLF."""
    target = project(tmp_path, web_files(newline))
    code, out = run(capsys, target)
    assert code == 0, out
    assert "delete agk.toml (the kit's settings only)" in out, out
    assert "delete config/reviewers.yaml (unchanged kit file)" in out, out
    assert out.count(BASELINE_LINE) == 1, out
    assert not [ln for ln in out if ln.startswith("changed ")], out
    code, out = run(capsys, target, "--write")
    assert code == 0, out
    assert not (target / "agk.toml").exists()
    assert not (target / "config" / "reviewers.yaml").exists()
    assert sorted(p.name for p in (target / "config" / "agk-baseline").iterdir()) == [
        "history.json",
        "lint.json",
    ]
    assert (target / "src" / "app.js").is_file()


@pytest.mark.parametrize(
    ("review", "src", "handle", "kept"),
    [
        ("solo", REVIEWERS[0], "@dev-example", False),  # one login: what init wrote
        ("solo", REVIEWERS[0], "@dev.example-2", False),  # a handle with `.` and `-`
        ("team", REVIEWERS[0], "@REPLACE-ME", False),  # the placeholder: the template itself
        ("team", REVIEWERS[1], "@dev-example", False),  # adopt's template, installed layout
        ("team", REVIEWERS[0], "@org", True),  # breaks the template's `@org/team`: kept
    ],
)
def test_an_installed_init_project_solo_and_team(tmp_path, kit, capsys, review, src, handle, kept):
    """REQ-009: answers 4, 7 and 9 (d): the installed layout, no licence or history lines."""
    files = {"agk.toml": INIT_TOML.format(review=review), "config/reviewers.yaml": rendered(src, handle)}
    target = project(tmp_path, files)
    code, out = run(capsys, target)
    assert code == 0, out
    assert "delete agk.toml (the kit's settings only)" in out, out
    line = line_of(out, "config/reviewers.yaml")
    if kept:
        assert line.startswith("changed config/reviewers.yaml") and "differs from" in line
    else:
        assert line == "delete config/reviewers.yaml (unchanged kit file)"
    assert not any(ln.startswith(("History clean-up", "kept config/agk-baseline/")) for ln in out)


def test_two_handles_or_an_edited_class_keep_reviewers(tmp_path, kit, capsys):
    """REQ-009: answers 4 and 9 (f): a second approver or an edited class is the person's."""
    second = rendered(REVIEWERS[0]).replace(
        'spec_approvers: ["@dev-example"]', 'spec_approvers: ["@dev-example", "@dev-example-2"]'
    )
    edited = rendered(REVIEWERS[0]).replace("docs:          {paths: [docs/", "docs: {paths: [doc/")
    broken = "teams: [not, a, map]\n"
    for n, text in enumerate((second, edited, broken)):
        assert text != rendered(REVIEWERS[0])
        files = {"agk.toml": INIT_TOML.format(review="team"), "config/reviewers.yaml": text}
        target = project(tmp_path, files, name=f"p{n}")
        code, out = run(capsys, target)
        assert code == 0, out
        assert line_of(out, "config/reviewers.yaml").startswith("changed config/reviewers.yaml")


def test_the_persons_own_keys_keep_agk_toml_named_by_key(tmp_path, kit, capsys):
    """REQ-009: answers 2, 3 and 9 (e): own key, own table, own key in a kit table, a misplaced
    table key; named by key, never a value."""
    mine = (
        'own_key = "secret-value-example"\nauto_merge = true\n'
        + INIT_TOML.format(review="team")
        + '\n[flow]\nassign = "next"\nown_flow = "v-example"\n\n[own]\nlevel = 3\n'
        + '\n[personal]\nforge = "files"\nown_personal = 1\n'
    )
    target = project(tmp_path, {"agk.toml": mine, "config/reviewers.yaml": rendered(REVIEWERS[0])})
    code, out = run(capsys, target, "--write")
    assert code == 0, out
    line = line_of(out, "agk.toml")
    assert line == (
        "changed agk.toml (path class agk.toml: settings the kit does not read: auto_merge, "
        "flow.own_flow, own, own_key, personal.own_personal; kept for you to decide)"
    ), line
    assert (target / "agk.toml").read_text(encoding="utf-8") == mine


@pytest.mark.parametrize(
    "extra",
    [
        "paused = true\n",  # after --pause
        'rule_tags_from = "x"\nlock_dir = ""\nlock_stale_minutes = 5\n',
        "project_lint_paths = 7\n",  # outside the reader's form: still the kit's name
        "\n[proof]\nx = 1\n\n[caps]\nS = { tokens = 1, hours = 1 }\n\n[tidy]\na = 1\n"
        "\n[checklist]\na = 1\n\n[cost]\na = 1\n\n[scorecard]\na = 1\n\n[failures]\na = 1\n"
        "\n[capacity]\nprofile = \"auto\"\n\n[engines]\nvision = \"v\"\n\n[models.routes]\n"
        "mid = { task = \"t\" }\n\n[guard]\ndeny_paths = []\n",
    ],
)
def test_every_kit_setting_counts_as_the_kits(tmp_path, kit, capsys, extra):
    """REQ-009: answer 7 (each setting and table the kit reads; the uninstall runs no reader)."""
    text = INIT_TOML.format(review="team") + extra
    target = project(tmp_path, {"agk.toml": text})
    code, out = run(capsys, target)
    assert code == 0, out
    assert "delete agk.toml (the kit's settings only)" in out, out
    assert not any(ln.startswith("refused") for ln in out)


def test_a_sidecar_with_personal_only_loses_agk_toml(tmp_path, kit, capsys):
    """REQ-009: answers 7 and 9 (g): personal mode's `[personal]` table and its keys count."""
    text = 'version = "2.0.0"\n\n[personal]\nforge = "files"\nlevel = "light"\nsign = false\n'
    target = project(tmp_path, {"agk.toml": text}, name="sidecar")
    code, out = run(capsys, target)
    assert code == 0, out
    assert "delete agk.toml (the kit's settings only)" in out, out


def test_unreadable_toml_and_an_empty_baseline(tmp_path, kit, capsys):
    """REQ-009: answers 5 and 7: not readable TOML kept as today; an empty baseline names none."""
    target = project(tmp_path, {"agk.toml": "mode = [\n"})
    (target / "config" / "agk-baseline").mkdir(parents=True)
    code, out = run(capsys, target)
    assert code == 0, out
    assert "changed agk.toml (path class agk.toml: not readable TOML; kept for you to decide)" in out
    assert not any(ln.startswith("kept config/agk-baseline/") for ln in out)

