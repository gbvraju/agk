"""No kit script reads a kit-only file at a project-relative path (brief #1826, ADR-0759;
SPEC-0071 rule 2; REQ-078).

A clean project (`[kit] layout = "plugin"`) holds only `upgrade.CLEAN_KEPT` and its records; every
other file of the manifest's `verbatim` and `snapshot` lists is the plugin's. This test parses every
`.py` under `scripts/agk/` and `.claude/hooks/` and fails on any `/` join, or call, that puts such a
kit-only path (a string literal, or a module constant that holds one) beside a project root name,
outside `kit_root.kit_file`. Brief #1887 (ADR-0781) widens what it reads: a constant of another
kit module (`playbook_format.FOLDER`), a kit-only folder (one whose every file in the kit's tree is
a kit-only file: `config/playbooks/`) as a match for any join that starts with it, and a
`.relative_to(<root name>)` called on what a resolver returns. The sites that are right as they are
stand in `ALLOWED`, each with its file, its function and its reason; a row that no longer matches a
site fails too, so the list only shrinks. A failure names the file, the function and the path class,
never the line's text. File reads only; no network.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import upgrade  # noqa: E402

ROOT_NAMES = frozenset({"root", "tree", "target", "repo", "clone", "project"})
REASONS = frozenset(
    {
        "installed layout only",
        "CI only",
        "a changed-path class",
        "falls back to the kit",
        "beside this script",
        "open",
        "the resolver",
        "the project's own file",
    }
)

# Calls that resolve a kit file themselves: the resolver, and new_spec's restatement of it, which a
# test of tests/kit_dev/test_new_spec.py holds equal (ADR-0503 keeps new_spec free of kit modules).
RESOLVERS = {"kit_file": None, "read_template": "scripts/agk/new_spec.py"}

INSTALLED, CI, CHANGED, FALLS_BACK, RESOLVER, OWN = (
    "installed layout only",
    "CI only",
    "a changed-path class",
    "falls back to the kit",
    "the resolver",
    "the project's own file",
)
# Brief #1887 answer 3: calls whose result is a kit file in a clean project, so a `relative_to` of
# a project root on it fails there; a bare name counts only inside the module that defines it.
RESOLVED = {
    "selected": "playbook_format",
    "path": "playbook_format",
    "folder": "playbook_format",
    "default_playbook": "playbook_format",
    "kit_file": "kit_root",
}
PLAYBOOKS = "config/playbooks/"
# (file, function, reason[, question]): a site that is right as it is, or `open` with the question
# whose own brief fixes it. Remove a row with its site; never add one to go green.
ALLOWED: tuple[tuple[str, ...], ...] = (
    (".claude/hooks/plugin_hooks.py", "project_runs_own", INSTALLED),
    ("scripts/agk/check_domains.py", "folders", OWN),  # a project's own pack, read first (ADR-0804)
    ("scripts/agk/check_licence_notice.py", "annotated", INSTALLED),
    ("scripts/agk/check_runbooks.py", "cmd_check", INSTALLED),
    ("scripts/agk/ci_tools.py", "read_pins", CI),
    ("scripts/agk/core_audit.py", "build", INSTALLED),
    ("scripts/agk/doctor.py", "brief_invalid_label_result", INSTALLED),
    ("scripts/agk/doctor.py", "drift_file_result", INSTALLED),
    ("scripts/agk/doctor.py", "merger_variable_result", INSTALLED),
    ("scripts/agk/doctor.py", "no_kit", INSTALLED),
    ("scripts/agk/doctor.py", "run_checks", INSTALLED),
    ("scripts/agk/front_door.py", "signal_problems", FALLS_BACK),
    ("scripts/agk/kit_root.py", "gate", INSTALLED),
    ("scripts/agk/playbook_format.py", "folder", RESOLVER),
    ("scripts/agk/playbook_format.py", "path", RESOLVER),
    ("scripts/agk/playbook_format.py", "playbooks", OWN),
    ("scripts/agk/playbook.py", "start_problems", CHANGED),
    ("scripts/agk/pr_body.py", "check_body", FALLS_BACK),
    ("scripts/agk/prepush.py", "no_ci_proof", CI),
    ("scripts/agk/release_pack.py", "scans_part", INSTALLED),
    ("scripts/agk/release_pack.py", "tools_at", INSTALLED),
    ("scripts/agk/session.py", "body_lines", "open", "Q-1826-4"),
    ("scripts/agk/session.py", "numbers_in_use", INSTALLED),
    ("scripts/agk/session.py", "rule_texts", "open", "Q-1826-4"),
    ("scripts/agk/setup.py", "merger_note", INSTALLED),
    ("scripts/agk/steward_outbound.py", "kit_repo", FALLS_BACK),
    ("scripts/agk/steward_owner.py", "composed_standard", OWN),
    ("scripts/agk/uninstall.py", "makefile_item", INSTALLED),
    ("scripts/agk/uninstall.py", "own_files", OWN),
    ("scripts/agk/wsl.py", "project_engines", INSTALLED),
)


def kit_only() -> frozenset[str]:
    """The kit-only files, and each kit-only folder with its closing `/` (brief #1887)."""
    files = kit_files()
    return files | kit_folders(files)


def kit_folders(files: frozenset[str]) -> frozenset[str]:
    """A folder that holds a kit-only file and whose every file in the kit's tree is one, so a
    clean project holds none of it (`config/playbooks/`); never one a project writes into."""
    out = set()
    for folder in {rel.rsplit("/", 1)[0] for rel in files if "/" in rel}:
        held = [
            p.relative_to(KIT_ROOT).as_posix()
            for p in (KIT_ROOT / folder).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        ]
        if held and all(rel in files for rel in held):
            out.add(f"{folder}/")
    return frozenset(out)


def kit_files() -> frozenset[str]:
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    rendered = set(manifest.get("rendered", []))  # written into a clean project (init.py)
    names = set()
    for key in ("verbatim", "snapshot"):
        for entry in manifest.get(key, []):
            rel = entry if isinstance(entry, str) else entry.get("path", "")
            if (
                rel
                and not rel.endswith("/")
                and rel not in rendered
                and not any(
                    rel == kept or (kept.endswith("/") and rel.startswith(kept))
                    for kept in upgrade.CLEAN_KEPT
                )
            ):
                names.add(rel)
    return frozenset(names)


def sources() -> list[Path]:
    hooks = KIT_ROOT / ".claude" / "hooks"
    return sorted([*SCRIPTS.glob("*.py"), *hooks.glob("*.py")])


def constants(tree: ast.Module) -> dict[str, str]:
    """Module-level names bound to one string, or to a tuple of strings (each name joined)."""
    out: dict[str, str] = {}
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else []
        if isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        value = getattr(node, "value", None)
        for target in targets:
            if isinstance(target, ast.Name) and isinstance(value, ast.Constant):
                if isinstance(value.value, str):
                    out[target.id] = value.value
    return out


def tuple_constants(tree: ast.Module) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, (ast.Tuple, ast.List)):
            items = [e.value for e in node.value.elts if isinstance(e, ast.Constant)]
            if items and all(isinstance(i, str) for i in items):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        out[target.id] = items
    return out


def loop_names(tree: ast.AST, tuples: dict[str, list[str]]) -> dict[str, list[str]]:
    """Names a `for` or a comprehension binds over a tuple constant: each item of it."""
    out: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.comprehension)) and isinstance(node.target, ast.Name):
            if isinstance(node.iter, ast.Name) and node.iter.id in tuples:
                out.setdefault(node.target.id, []).extend(tuples[node.iter.id])
    return out


def chain(node: ast.AST) -> list[ast.AST]:
    """The operands of a `/` chain, left to right."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return [*chain(node.left), *chain(node.right)]
    return [node]


def is_root(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id in ROOT_NAMES
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Path":
        return len(node.args) == 1 and is_root(node.args[0])
    return False


def resolver(func: ast.AST, rel: str) -> bool:
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
    return name in RESOLVERS and RESOLVERS[name] in (None, rel)


_MODULES: dict[str, dict[str, str]] = {}


def module_constants(name: str) -> dict[str, str]:
    """The string constants of the kit module `name` (brief #1887 answer 3), {} for another."""
    if name not in _MODULES:
        path = SCRIPTS / f"{name}.py"
        _MODULES[name] = constants(ast.parse(path.read_text("utf-8"))) if path.is_file() else {}
    return _MODULES[name]


def text_of(node: ast.AST, names: dict[str, str]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return names.get(node.id)
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return module_constants(node.value.id).get(node.attr)
    return None


def joined(parts: list[ast.AST], names: dict[str, str]) -> str | None:
    texts = [text_of(p, names) for p in parts]
    return None if any(t is None for t in texts) else "/".join(t for t in texts if t is not None)


def leading(parts: list[ast.AST], names: dict[str, str]) -> str:
    """The joined text of the parts before the first one whose text is unknown."""
    texts: list[str] = []
    for part in parts:
        text = text_of(part, names)
        if text is None:
            break
        texts.append(text)
    return "/".join(texts)


def in_folder(text: str, kit: frozenset[str]) -> str | None:
    """The kit-only folder that `text` names or lies in, or None."""
    return next((f for f in kit if f.endswith("/") and f"{text}/".startswith(f)), None)


def resolved_call(node: ast.AST, rel: str) -> str | None:
    """The resolver a call names (brief #1887 answer 3), or None."""
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        found = func.attr if RESOLVED.get(func.attr) == func.value.id else None
    else:
        name = getattr(func, "id", None)
        found = name if name in RESOLVED and rel == f"scripts/agk/{RESOLVED[name]}.py" else None
    return found


def resolved_names(function: ast.AST, rel: str) -> dict[str, str]:
    """Names a function binds to a resolver's result: `path = playbook_format.selected(root)`."""
    out: dict[str, str] = {}
    for node in ast.walk(function):
        call = resolved_call(getattr(node, "value", None), rel)
        if isinstance(node, ast.Assign) and call is not None:
            out.update({t.id: call for t in node.targets if isinstance(t, ast.Name)})
    return out


def relative_site(
    node: ast.AST, rel: str, held: dict[str, str], names: dict[str, str]
) -> str | None:
    """The path class of `<resolver result>.relative_to(<root name>)`, or None."""
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "relative_to"
        and len(node.args) == 1
        and is_root(node.args[0])
    ):
        return None
    receiver = node.func.value
    call = resolved_call(receiver, rel)
    if call is None and isinstance(receiver, ast.Name):
        call = held.get(receiver.id)
    if call is None:
        return None
    if call != "kit_file":
        return PLAYBOOKS
    args = receiver.args if isinstance(receiver, ast.Call) else []
    text = text_of(args[1], names) if len(args) > 1 else None
    return text if text else "kit_root.kit_file/"


def sites(text: str, rel: str, kit: frozenset[str]) -> list[tuple[str, str, str]]:
    """(file, function, kit path) for each project-relative lookup of a kit-only file."""
    tree = ast.parse(text)
    names = constants(tree)
    module = tuple_constants(tree)
    tuples = module
    held: dict[str, str] = {}
    found: list[tuple[str, str, str]] = []

    def visit(node: ast.AST, function: str) -> None:
        nonlocal tuples
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            function = node.name if function == "<module>" else f"{function}.{node.name}"
            tuples = module | loop_names(node, module)  # a loop binds a name in its function
            held.clear()
            held.update(resolved_names(node, rel))
        relative = relative_site(node, rel, held, names)
        if relative is not None:
            found.append((rel, function, relative))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            parts = chain(node)
            if is_root(parts[0]):
                text = joined(parts[1:], names)
                folder = in_folder(leading(parts[1:], names), kit)
                if text in kit:
                    found.append((rel, function, text))
                elif folder is not None:
                    found.append((rel, function, folder))
                if len(parts) == 2 and isinstance(parts[1], ast.Name):
                    found.extend(
                        (rel, function, t) for t in tuples.get(parts[1].id, []) if t in kit
                    )
                return
        if isinstance(node, ast.Call) and resolver(node.func, rel):
            return
        if isinstance(node, ast.Call) and any(is_root(a) for a in node.args):
            for arg in node.args:
                text = text_of(arg, names)
                if text in kit:
                    found.append((rel, function, text))
        for child in ast.iter_child_nodes(node):
            visit(child, function)

    visit(tree, "<module>")
    return [site for site in found if site[:2] != ("scripts/agk/kit_root.py", "kit_file")]


def all_sites() -> list[tuple[str, str, str]]:
    kit = kit_only()
    return [
        site
        for path in sources()
        for site in sites(path.read_text("utf-8"), path.relative_to(KIT_ROOT).as_posix(), kit)
    ]


def test_req078_no_new_project_relative_lookup_of_a_kit_only_file() -> None:
    """REQ-078: every such site is `kit_root.kit_file` or a row of `ALLOWED`."""
    allowed = {row[:2] for row in ALLOWED}
    new = sorted(
        {(f, fn, t.rsplit("/", 1)[0] + "/") for f, fn, t in all_sites() if (f, fn) not in allowed}
    )
    assert not new, "\n".join(
        f"{f}: {fn} reads a kit-only file under the project root (path class {cls}); "
        "use kit_root.kit_file or add an ALLOWED row with its reason"
        for f, fn, cls in new
    )


def test_req078_every_allowed_row_still_matches_a_site() -> None:
    """REQ-078: the list only shrinks; a row whose site is gone is removed with it."""
    live = {site[:2] for site in all_sites()}
    stale = [row[:2] for row in ALLOWED if row[:2] not in live]
    assert not stale, f"ALLOWED rows that match no site: {stale}"


def test_req078_every_allowed_row_has_a_known_reason() -> None:
    """REQ-078: one of the reasons; an `open` row names the brief that fixes it."""
    for row in ALLOWED:
        assert row[2] in REASONS, row[:2]
        if row[2] == "open":
            assert len(row) == 4 and row[3].startswith("Q-"), row[:2]
    assert len({row[:2] for row in ALLOWED}) == len(ALLOWED)


@pytest.mark.parametrize(
    ("code", "hit"),
    [
        ('def f(root):\n    return root / "docs/specs/TEMPLATE.md"\n', True),
        ('def f(root):\n    return root / "docs" / "specs" / "TEMPLATE.md"\n', True),
        ('T = "constitution/principles.md"\ndef f(root):\n    return read_text(root, T)\n', True),
        ('G = ("scripts/agk/guard.py",)\ndef f(root):\n    return [root / g for g in G]\n', True),
        ('G = ("scripts/agk/guard.py",)\ndef f(root):\n    return root / G\n', True),
        ('def f(root):\n    return root / "agk.toml"\n', False),
        ('def f(here):\n    return here / "docs/specs/TEMPLATE.md"\n', False),
        ('def f(root):\n    return kit_root.kit_file(root, "docs/specs/TEMPLATE.md")\n', False),
    ],
)
def test_req078_the_scan_finds_each_form(code: str, hit: bool) -> None:
    """REQ-078: the scan's own test: a literal, a split join, a constant and a loop over a tuple
    constant are found; a project file of `CLEAN_KEPT` and a name that is no root are not."""
    found = sites(code, "scripts/agk/example_probe.py", kit_only())
    assert bool(found) is hit, found


@pytest.mark.parametrize(
    ("code", "hit"),
    [
        ('def f(root):\n    return root / playbook_format.FOLDER / "web-app.toml"\n', True),
        ("def f(root):\n    return root / playbook_format.RUNS\n", False),
        ('def f(root, name):\n    return root / "config/playbooks" / f"{name}.toml"\n', True),
        ("def f(root):\n    return Path(root) / playbook_format.FOLDER\n", True),
        ('def f(root, name):\n    return root / "docs/plan" / f"{name}.md"\n', False),
        (
            "def f(root):\n    path = playbook_format.selected(root)\n"
            "    return path.relative_to(root).as_posix()\n",
            True,
        ),
        (
            'def f(root):\n    return kit_root.kit_file(root, "docs/specs/TEMPLATE.md")'
            ".relative_to(root)\n",
            True,
        ),
        ("def f(root, path):\n    return path.relative_to(root)\n", False),
        ("def f(root):\n    path = playbook_format.selected(root)\n    return path.name\n", False),
    ],
)
def test_req078_the_scan_finds_each_form_of_brief_1887(code: str, hit: bool) -> None:
    """REQ-078 (brief #1887 answer 3): another kit module's constant, a kit-only folder joined with
    an unknown name, and `relative_to(<root name>)` on a resolver's result are found; a project
    folder, a constant that names none, and `relative_to` on a parameter are not."""
    found = sites(code, "scripts/agk/example_probe.py", kit_only())
    assert bool(found) is hit, found


def test_req078_the_playbook_folder_is_kit_only_and_a_project_folder_is_not() -> None:
    """REQ-078 (brief #1887 answer 3): `config/playbooks/` holds only kit-only files; the kit's
    `docs/specs/` holds its own specs too, so it is never read as kit-only."""
    kit = kit_only()
    assert "config/playbooks/" in kit
    assert "docs/specs/" not in kit and "docs/adr/" not in kit
