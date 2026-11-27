"""Every kit step that writes into a project leaves a change that passes the project's own
protected-changes check (brief #1829, ADR-0761; REQ-036).

One table lists each kit step that writes into a project. For each, a scratch project made by
`init.py` or `adopt.py --unreleased` runs the step on a branch from the default branch, adds what
the step's own output says to add (its record, or one invented ADR naming the classes its
`protected:` line printed), and runs `check_protected_changes.py --base <default branch>`, which
must print `ok protected-changes`. The settings of answer 7 that reach the check are cases of the
stack accept; two of them run the project's whole governance (the plugin's `kit_root.py
governance` and the full copy's `make -f agk.mk agk-governance`). A census of `scripts/agk/`
finds each write whose target is a literal path of a protected class of either project list and
fails for a writer that neither table lists, so a new writer cannot land without its case.

Scratch projects in a temporary folder, local git only, no network; invented data only
(example.com, example-owner).
"""

from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import steward_owner  # noqa: E402
import test_front_door_derive as derive  # noqa: E402
import test_front_door_entry as entry  # noqa: E402

OK = "ok protected-changes"
PROTECTED = re.compile(r"^protected: (.+) \(name them in this change's ADR\)$", re.M)
PATH_CLASS = re.compile(r"\(path class: ([^)]+)\)")
IDEA = "A reading list for readers at example.com, kept by one person."
CLEAN_ENV = {k: v for k, v in os.environ.items() if not k.startswith(("AGK_", "GITHUB_"))}


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout


def kit(root: Path, script: str, *args: str, ok: bool = True) -> str:
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / script), *args],
        cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=120,
        env={**CLEAN_ENV, "AGK_SETUP_LOGIN": "example-owner"},
    )  # fmt: skip
    assert not ok or proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout


def setting(text: str, key: str, value: str) -> str:
    line = f"{key} = {value}"
    found = re.search(rf"(?m)^{key} = .*$", text)
    if found:
        return text[: found.start()] + line + text[found.end() :]
    return re.sub(r"(?m)^(default_branch = .*)$", lambda m: f"{m.group(1)}\n{line}", text, count=1)


def scratch(
    tmp: Path,
    adopt: bool = False,
    solo: bool = True,
    layout: str = "plugin",
    branch: str = "main",
    settings: dict[str, str] | None = None,
    listing=None,
) -> Path:
    """A committed project of `init.py` (or `adopt.py` over an invented product file)."""
    root = tmp / "product"
    root.mkdir()
    git(root, "init", "-q", "-b", branch)
    git(root, "config", "user.email", "owner@example.com")
    git(root, "config", "user.name", "Owner")
    if adopt:
        (root / "app").mkdir()
        (root / "app" / "main.py").write_text('print("example.com")\n', encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "--allow-empty", "-m", "start")
    args = [str(root), "--unreleased", "--login-from-env", *(["--solo"] if solo else [])]
    args += ["--layout", "plugin", "--rehearsal"] if layout == "plugin" else []
    kit(root, "adopt.py" if adopt else "init.py", *args)
    toml = root / "agk.toml"
    text = setting(toml.read_text(encoding="utf-8"), "default_branch", f'"{branch}"')
    for key, value in (settings or {}).items():
        table = key.startswith("[")
        text = text + f"\n{key}\n{value}\n" if table else setting(text, key, value)
    toml.write_text(text, encoding="utf-8")
    if listing is not None:
        path = root / "config" / "protected-paths.txt"
        path.write_text(listing(path.read_text(encoding="utf-8")), encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "the kit")
    return root


def default(root: Path) -> str:
    return re.search(r'(?m)^default_branch = "(.+)"$', (root / "agk.toml").read_text()).group(1)


def on(root: Path, name: str) -> None:
    git(root, "checkout", "-q", default(root))
    git(root, "checkout", "-q", "-b", name)


def merged(root: Path) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "--allow-empty", "-m", "the step")
    work = git(root, "branch", "--show-current").strip()
    git(root, "checkout", "-q", default(root))
    git(root, "merge", "-q", "--no-ff", work, "-m", f"merge {work}")


def check(root: Path) -> str:
    """The project's protected-changes check against its default branch, committed or not."""
    script = root / "scripts" / "agk" / "check_protected_changes.py"
    if not script.is_file():
        script = SCRIPTS / "check_protected_changes.py"  # the plugin layout runs the kit's own
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(script), "--base", default(root)],
        cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=60, env=CLEAN_ENV,
    )  # fmt: skip
    return proc.stdout + proc.stderr


def named(root: Path, out: str) -> None:
    """One invented ADR naming the classes the step's `protected:` (or path class) line said."""
    found = PROTECTED.search(out)
    classes = found.group(1) if found else ", ".join(f"`{c}`" for c in PATH_CLASS.findall(out))
    assert classes and classes != "none", out
    (root / "docs" / "adr" / "0099-the-foundation.md").write_text(
        "# ADR-0099: the foundation\n\n- Status: Proposed\n- Date: 2026-11-23\n"
        f"- Deciders: the owner\n- Related: none\n- Requirements: REQ-001\n\n"
        f"Protected classes: {classes}\n\n## Context\n\nInvented.\n",
        encoding="utf-8",
    )


# --- the steps ---------------------------------------------------------------------------------

SELECTION = (
    "   - test selection: judgement (Option A: profile fast, always_full `app/auth/**`; "
    "Option B: profile thorough, always_full `src/**`)"
)
FILLS = (
    ("- Requirements: TODO(architect)", "- Requirements: REQ-001"),
    ("TODO(architect): what the product", "A reading list at example.com. What the product"),
    ("Option B — TODO(architect)", "Option B — a hosted service at example.com"),
    ("Cost: TODO(architect)", "Cost: a monthly fee"),
    ("Build speed: TODO(architect)", "Build speed: quick"),
    ("Security: TODO(architect)", "Security: the host holds the data"),
    ("Uptime: TODO(architect)", "Uptime: the host keeps it up"),
    ("Parts: TODO(architect)", "Parts: python 3.12 PSF-2.0"),  # option A: a stack of STACKS
    ("Parts: TODO(architect)", "Parts: a 1.0 MIT"),
    ("External services: TODO(architect)", "External services: none"),
)


def stack_write(root: Path) -> str:
    on(root, "stack/options")
    out = kit(root, "engines.py", "stack-write", "--ref", default(root), "--root", ".")
    (path,) = (root / "docs" / "adr").glob("*-stack-options.md")
    text = path.read_text(encoding="utf-8")
    for old, new in FILLS:
        text = text.replace(old, new, 1 if old.startswith("Parts") else -1)
    text = re.sub(r"(?m)^   - test selection: judgement.*$", lambda _: SELECTION, text)
    path.write_text(text, encoding="utf-8")
    assert "ok engines-stack" in kit(root, "engines.py", "stack-check", "--root", "."), text
    return out


def stack_accept(root: Path) -> str:
    stack_write(root)
    merged(root)
    on(root, "stack/accept")
    args = ("stack-accept", "--option", "A", "--reason", "small", "--root", ".")
    out = kit(root, "engines.py", *args)
    if "next: run_gates.py --root . writes config/agk-baseline/" in out:
        kit(root, "run_gates.py", "--root", ".", ok=False)  # the output's own next step
    return out


def stack_files(root: Path) -> str:
    stack_accept(root)
    merged(root)
    on(root, "foundation")
    out = kit(root, "engines.py", "stack-files", "--root", ".")
    named(root, out)
    return out


def write_record(root: Path) -> str:
    stack_accept(root)
    merged(root)
    on(root, "foundation")
    out = kit(root, "gates/layers.py", "--root", ".", "--write-record")
    named(root, out)
    return out


def work_type_yes(root: Path) -> str:
    """The two writes of `work-type --yes` (its line and its record), then the new gates'
    baselines that `run_gates.py` writes on the same branch in an adopted project."""
    on(root, steward_owner.WORK_TYPE_BRANCH)
    toml = root / "agk.toml"
    toml.write_text(steward_owner.with_work_type(toml.read_text("utf-8"), "web-app"), "utf-8")
    ask = {"work_type": "web-app", "discovery": [], "at": "2026-11-23T09:00Z", "question": "?"}
    steward_owner.work_type_adr(root, ask, "Yes", "2026-11-23T09:05Z")
    return kit(root, "run_gates.py", "--root", ".", ok=False)


def domain_yes(root: Path) -> str:
    """Brief #1937 (ADR-0806): the two writes of `domain --yes`, its line and its record."""
    import domain_ask

    on(root, domain_ask.BRANCH)
    toml = root / "agk.toml"
    toml.write_text(domain_ask.with_packs(toml.read_text("utf-8"), ["payments"]), "utf-8")
    ask = {"at": "2026-11-23T09:00Z", "question": "?"}
    domain_ask.adr(root, ask, ["payments"], "Yes", "2026-11-23T09:05Z")
    return ""


def baseline_write(root: Path) -> str:
    on(root, "gates")
    out = kit(root, "run_gates.py", "--root", ".", ok=False)
    assert "written (path class: config/agk-baseline/)" in out, out
    named(root, out)
    return out


def inventory(root: Path) -> str:
    on(root, "design/inventory")
    return kit(root, "design.py", "inventory", "--root", ".")


def signoff_row(root: Path) -> str:
    inventory(root)
    merged(root)
    on(root, "design/signoff")
    import design_signoff  # noqa: PLC0415 - the digest the row records

    path = root / "docs" / "design" / "signoffs.md"
    shutil.copy(KIT_ROOT / "kit" / "templates" / "design-signoffs.md", path)
    head = git(root, "rev-parse", "HEAD").strip()
    row = f"| inventory | - | {design_signoff.inventory_digest(root)} | {head} | 2026-11-23 |"
    path.write_text(path.read_text("utf-8") + row + " https://example.com/review/1 |\n", "utf-8")
    return "appended the inventory row"


def prototype(root: Path) -> str:
    signoff_row(root)
    merged(root)
    on(root, "design/prototype")
    return kit(root, "design.py", "prototype", "--root", ".")


def discovery_write(root: Path) -> str:
    on(root, "discovery")
    files = root.parent
    issue = entry.issue(files, f"Problem: {entry.WORDS}\nKind: web-app")
    args = ("--issue", str(issue), "--answers", str(entry.answers(files)), "--root", ".")
    return kit(root, "front_door.py", "discovery-write", *args)


def derive_write(root: Path) -> str:
    on(root, "playbook")
    record = root / "docs" / "research" / f"{derive.SLUG}.md"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(derive.record_text(), encoding="utf-8")
    out = kit(root, "front_door.py", "derive-write", "--slug", derive.SLUG, "--root", ".")
    named(root, out)
    return out


def vision_write(root: Path) -> str:
    """The vision and the charter ADR the stack skill's first step writes beside it."""
    on(root, "vision")
    idea = root.parent / "idea.txt"
    idea.write_text(IDEA + "\n", encoding="utf-8")
    out = kit(root, "engines.py", "vision-write", "--idea-file", str(idea), "--root", ".")
    (root / "docs" / "adr" / "0002-project-charter.md").write_text(
        "# ADR-0002: project charter\n\n- Status: Proposed\n- Date: 2026-11-23\n"
        "- Deciders: the owner\n- Related: none\n- Requirements: REQ-001\n\n"
        "Protected classes: `constitution/`\n",
        encoding="utf-8",
    )
    return out


def pack_add(root: Path) -> str:
    """Brief #2033 (ADR-0840): `packs.py add` on the person's yes writes the pack and the lock."""
    import packs
    import test_packs_lock as lock

    on(root, "pack")
    src = lock.stub_pack(root.parent / "pack-source" / "zz-shop")
    words = root.parent / "said.txt"
    words.write_text("yes", encoding="utf-8")
    notes = lambda r, text: (0, ["recorded"])  # noqa: E731 - the Setup note, never posted here
    code, lines = packs.add(root, str(src), words, "2026-11-27T10:00Z", record=notes)
    out = "\n".join(lines)
    assert code == 0, out
    named(root, out)
    return out


# Each kit step that writes into a project: (file::function, how the test runs it, the scratch).
ADOPTED = {"adopt": True}
WEB_APP = {"settings": {"[delivery]": 'work_type = "web-app"'}}
STEPS = {
    "stack-write": ("scripts/agk/engines.py::cmd_stack_write", stack_write, {}),
    "stack-accept": ("scripts/agk/engines.py::cmd_stack_accept", stack_accept, {}),
    "stack-accept adopted": ("scripts/agk/engines.py::cmd_stack_accept", stack_accept, ADOPTED),
    "stack-files": ("scripts/agk/engines.py::cmd_stack_files", stack_files, WEB_APP),
    "layers --write-record": ("scripts/agk/gates/layers.py::write_record", write_record, WEB_APP),
    "work-type yes adopted": (
        "scripts/agk/steward_owner.py::work_type_yes",
        work_type_yes,
        ADOPTED,
    ),
    "domain yes adopted": ("scripts/agk/domain_ask.py::yes", domain_yes, ADOPTED),
    "adopt baseline write": ("scripts/agk/run_gates.py::ratchet", baseline_write, ADOPTED),
    "design inventory": ("scripts/agk/design.py::inventory", inventory, {}),
    "sign-off row": ("docs/design/signoffs.md", signoff_row, {}),
    "design prototype": ("scripts/agk/design.py::prototype", prototype, {}),
    "discovery-write": ("scripts/agk/front_door.py::discovery_write", discovery_write, {}),
    "derive-write": ("scripts/agk/front_door.py::derive_write", derive_write, {"layout": "full"}),
    "vision-write with charter": ("scripts/agk/engines.py::cmd_vision_write", vision_write, {}),
    "pack add": ("scripts/agk/packs.py::add", pack_add, {}),
}

# Writers of a protected path that are no step of this table, each with where it is held.
ELSEWHERE = {
    "scripts/agk/personal.py::upgrade": "the sidecar's own schema, never a product repository",
    "scripts/agk/req_status.py::edit": "a Status-only edit of the requirements file is exempt",
    "scripts/agk/setup.py::write_settings": "writes its own ADR naming `agk.toml` (rule 9)",
    "scripts/agk/uninstall.py::pause": "the pause needs the person's own ADR (ADR-0196)",
    "scripts/agk/wsl.py::make_pr": "writes the project's ADR beside the adapter change",
}


@pytest.mark.parametrize("name", sorted(STEPS))
def test_req036_each_kit_step_s_change_passes_protected_changes(tmp_path, name):
    """REQ-036: brief #1829 answer 6, the step's change and what its output says to add."""
    _, step, kind = STEPS[name]
    root = scratch(tmp_path, **kind)
    step(root)
    out = check(root)
    assert OK in out and "FAIL" not in out, out


TEAM = {"solo": False}
CASES = {
    "team review": TEAM,
    "full copy": {"layout": "full"},
    "default branch trunk": {"branch": "trunk"},
    "execution hosted": {"settings": {"execution": '"hosted"'}},
    "pr_mode flow": {"settings": {"pr_mode": '"flow"'}},
    "work type set": {"settings": {"[delivery]": 'work_type = "web-app"'}},
    "testing already the option": {
        "settings": {"[testing]": 'profile = "fast"\nalways_full = ["app/auth/**"]'}
    },
    "list without agk.toml": {"listing": lambda t: t.replace("agk.toml\n", "")},
    "list with docs/adr/": {"listing": lambda t: t + "docs/adr/\n"},
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_req036_the_accept_passes_under_each_setting(tmp_path, name):
    """REQ-036: brief #1829 answers 7 and 8, each setting that reaches the check."""
    root = scratch(tmp_path, **CASES[name])
    out = stack_accept(root)
    assert OK in out, out
    result = check(root)
    assert OK in result and "FAIL" not in result, result
    if name == "testing already the option":
        assert "unchanged: [testing] already matches option A" in out
    if name == "list with docs/adr/":
        text = next((root / "docs" / "adr").glob("*-stack-options.md")).read_text("utf-8")
        assert "Protected classes: `agk.toml`, `docs/adr/`" in text


@pytest.mark.parametrize("layout", ["plugin", "full"])
def test_req036_the_project_s_whole_governance_passes_the_accept(tmp_path, layout):
    """REQ-036: brief #1829 answer 7 (`[kit] layout`), governance from the plugin and from the
    full copy; before this build its only failure was protected-changes on `agk.toml`."""
    root = scratch(tmp_path, layout=layout)
    stack_accept(root)
    if layout == "plugin":
        args = [sys.executable, "-I", str(SCRIPTS / "kit_root.py"), "governance"]
    else:
        args = [shutil.which("make") or "make", "-f", "agk.mk", "agk-governance"]
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        args, cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=300, env=CLEAN_ENV
    )
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-2000:]
    assert OK in proc.stdout


# --- the census --------------------------------------------------------------------------------

# The classes of either project list a kit step writes by a literal path (brief #1829 answer 6).
CLASSES = ("agk.toml", "config/", "pyproject.toml", "docs/architecture.md", "docs/requirements.md")
LISTS = ("kit/templates/protected-paths.txt", "kit/templates/protected-paths.adopt.txt")
WRITES = {"write_text", "write_bytes"}


def test_req036_the_census_classes_are_in_both_project_lists():
    """REQ-036: each class the census looks for is a class of a project list."""
    for cls in CLASSES:
        assert any(cls in (KIT_ROOT / rel).read_text("utf-8").split() for rel in LISTS), cls


def literal(node, consts: dict, local: dict) -> str | None:
    """The path a write's target spells from string literals and constants, or None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in local:
            return literal(local[node.id], consts, {})
        return consts.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left, right = literal(node.left, consts, local), literal(node.right, consts, local)
        return None if right is None else right if left is None else f"{left}/{right}"
    return None


def census() -> dict[str, str]:
    """`file::function` -> the literal protected path it writes, for every write in scripts/agk/."""
    entries, found = CLASSES, {}
    for path in sorted(SCRIPTS.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        consts = {
            t.id: n.value.value
            for n in tree.body
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
            for t in n.targets
            if isinstance(t, ast.Name) and isinstance(n.value.value, str)
        }
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef):
                continue
            local = {
                t.id: n.value
                for n in ast.walk(fn)
                if isinstance(n, ast.Assign)
                for t in n.targets
                if isinstance(t, ast.Name)
            }
            for call in ast.walk(fn):
                if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)):
                    continue
                if call.func.attr not in WRITES:
                    continue
                target = literal(call.func.value, consts, local)
                if target and any(
                    target == e or (e.endswith("/") and target.startswith(e)) for e in entries
                ):
                    found[f"{path.relative_to(KIT_ROOT).as_posix()}::{fn.name}"] = target
    return found


def test_req036_every_writer_of_a_protected_path_is_in_a_table():
    """REQ-036: brief #1829 answer 6, a new writer cannot land without its governance case."""
    listed = {writer for writer, _, _ in STEPS.values()} | set(ELSEWHERE)
    missing = sorted(w for w in census() if w not in listed)
    assert missing == [], f"add a governance case to STEPS for: {missing}"


def test_req036_the_census_finds_the_writers_it_names():
    """REQ-036: the census is not empty-handed: each ELSEWHERE row and the stack writers are
    found by it, so a table row cannot outlive its writer."""
    found = census()
    for writer in [*ELSEWHERE, "scripts/agk/engines.py::cmd_stack_accept"]:
        assert writer in found, writer
