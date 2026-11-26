"""Every ADR the kit writes into a project passes the project's own ADR check (brief #1827,
ADR-0760; REQ-045).

One table lists each kit writer of a project ADR with a builder that makes its text from invented
data; each must pass `check_adrs.validate`. A census finds every writer by its text (a code line
of `scripts/agk/**/*.py` that emits `# ADR-{` or `"# ADR-`, each `kit/templates/**/*.md` whose
first line is `# ADR-`, and `docs/adr/TEMPLATE.md`) and fails naming `<file>:<line>` for one the
table does not list. The printed skeletons a person copies are listed as `printed` and not
validated (Q-G2-3).

Local files and local git only, no network; invented data only (example.com).
"""

from __future__ import annotations

import ast
import re
import shutil
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_adrs  # noqa: E402
import domain_ask  # noqa: E402
import init  # noqa: E402
import intake  # noqa: E402
import new_spec  # noqa: E402
import personal_adopt  # noqa: E402
import setup  # noqa: E402
import steward_owner  # noqa: E402
import upgrade  # noqa: E402
import wsl  # noqa: E402

TODAY = "2026-11-23"
WRITER_LINE = re.compile(r'# ADR-\{|"# ADR-')
KNOWN = {f"{n:04d}" for n in range(1, 10)}


def checked(rel: str, text: str) -> list[str]:
    name = rel.rsplit("/", 1)[-1]
    return check_adrs.validate(name, text, KNOWN)


def written(root: Path, pattern: str) -> tuple[str, str]:
    (path,) = sorted((root / "docs" / "adr").glob(pattern))
    return path.name, path.read_text(encoding="utf-8")


def filled(rel: str) -> str:
    """A kit template with every `{{name}}` filled by invented data, as `init.render` does."""
    text = (KIT_ROOT / rel).read_text(encoding="utf-8")
    return re.sub(r"\{\{([a-z_]+)\}\}", lambda m: "2026-11-23" if m[1] == "date" else "demo", text)


def adr_project(tmp: Path) -> Path:
    root = tmp / "product"
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "docs" / "adr" / "0001-adopt-agk.md").write_text(filled("kit/templates/adr-0001.md"))
    return root


# --- the builders, one per writer ----------------------------------------------------------------


def steward_work_type(tmp: Path) -> tuple[str, str]:
    root = adr_project(tmp)
    ask = {
        "work_type": "web-app",
        "discovery": ["docs/discovery/idea-1.md"],
        "at": "2026-11-23T09:00Z",
        "question": "Your discovery says this is a web app. Shall I set that up?",
    }
    steward_owner.work_type_adr(root, ask, "Yes", "2026-11-23T09:05Z")
    return written(root, "*-work-type.md")


def steward_domain(tmp: Path) -> tuple[str, str]:
    """Brief #1937 (ADR-0806): the record of `domain --yes`."""
    root = adr_project(tmp)
    ask = {"at": "2026-11-23T09:00Z", "question": "This looks like a shop. Shall I use it?"}
    domain_ask.adr(root, ask, ["payments"], "Yes", "2026-11-23T09:05Z")
    return written(root, "*-domain.md")


def steward_draft(tmp: Path) -> tuple[str, str]:
    from test_standard_confirm import RESEARCH, project

    root = project(tmp, work_type=None)
    (root / "docs" / "research").mkdir(parents=True)
    (root / "docs" / "research" / "clinic-booking.md").write_text(RESEARCH, encoding="utf-8")
    (root / "docs" / "adr").mkdir()
    (root / "docs" / "adr" / "0001-adopt-agk.md").write_text(filled("kit/templates/adr-0001.md"))
    code, lines = steward_owner.draft(root, "clinic-booking")
    assert code == 0, lines
    return written(root, "*-the-project-s-work-type-*.md")


def init_template(rel: str, solo: bool):
    def build(tmp: Path) -> tuple[str, str]:
        text = filled(rel)
        if solo:  # the replacement init.py makes for `--solo`
            text = text.replace("\n## Consequences", init.SOLO_ADR + "\n## Consequences", 1)
        return "0001-adopt-agk.md", text

    return build


def stack_record(tmp: Path) -> tuple[str, str]:
    from test_stack_choice import engines
    from test_stack_choice import project as stack_project

    root = stack_project(tmp / "stack", None, commit=True)
    proc = engines(root, "stack-write", "--ref", "main", "--date", TODAY)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return written(root, "*-stack-options.md")


def intake_stub(tmp: Path) -> tuple[str, str]:
    ids = {"req": "REQ-101", "spec": "0101", "adr": "0002"}
    return "0002-add-req-101.md", intake.render_stub(ids, "A cart", "Add a cart.", TODAY)


def new_spec_requirement(tmp: Path) -> tuple[str, str]:
    root = tmp / "product"
    (root / "docs" / "adr").mkdir(parents=True)
    shutil.copy(KIT_ROOT / "docs" / "adr" / "TEMPLATE.md", root / "docs" / "adr" / "TEMPLATE.md")
    (root / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
    new_spec.make_requirement(root, "A cart", None, TODAY)
    return written(root, "[0-9]*-add-req-*.md")


def setup_adr(back: bool):
    def build(tmp: Path) -> tuple[str, str]:
        text = setup.project_adr(2, [(None, "review_mode", "solo")], TODAY, back=back)
        return "0002-project-settings.md", text

    return build


def wsl_adr(to: str):
    def build(tmp: Path) -> tuple[str, str]:
        return "0002-workforce.md", wsl.adr_text(2, to, TODAY)

    return build


def upgrade_adr(tmp: Path) -> tuple[str, str]:
    plan = upgrade.Plan(version="1.0.0", kit_version="2.0.0", mode="init")
    plan.items.append(upgrade.Item("Makefile", "replace", content=b"new\n"))
    return "0002-upgrade-agk.md", upgrade.adr_text(2, plan, ["kit"], TODAY)


def upgrade_clean(tmp: Path) -> tuple[str, str]:
    import uninstall

    target = adr_project(tmp)
    plan = uninstall.Plan(items=[uninstall.Item("Makefile", "delete")], entries=["Makefile"])
    path, text = upgrade.clean_adr(target, plan, "2.0.0", TODAY)
    return path.name, text


def charter_record(tmp: Path) -> tuple[str, str]:
    """Brief #1888 (ADR-0782): the charter template `/agk:start` and `/agk:vision` copy, filled."""
    values = {"adr": "0002", "date": TODAY, "related": "ADR-0001", "slice_topic": "scale"}
    text = (KIT_ROOT / "kit" / "templates" / "charter-adr.md").read_text(encoding="utf-8")
    return "0002-project-charter.md", re.sub(
        r"\{\{([a-z_]+)\}\}", lambda m: values.get(m[1], "an invented answer"), text
    )


def personal_record(tmp: Path) -> tuple[str, str]:
    text = personal_adopt.adr_text("ADR-0002", "Carts are kept", [], [], ["REQ-001"], TODAY)
    return "0002-carts-are-kept.md", text


# Each row: a writer as `<file>::<function>` (the function that holds the census line, or the
# template's path) and its builder, or the reason it is only printed.
WRITERS: dict[str, object] = {
    "scripts/agk/steward_owner.py::work_type_adr": steward_work_type,
    "scripts/agk/steward_owner.py::draft": steward_draft,
    "scripts/agk/domain_ask.py::adr": steward_domain,
    "kit/templates/adr-0001.md": init_template("kit/templates/adr-0001.md", solo=False),
    "kit/templates/adr-0001.md (solo)": init_template("kit/templates/adr-0001.md", solo=True),
    "kit/templates/adr-0001-adopt.md": init_template("kit/templates/adr-0001-adopt.md", False),
    "kit/templates/adr-0001-adopt.md (solo)": init_template(
        "kit/templates/adr-0001-adopt.md", solo=True
    ),
    "kit/templates/stack-adr.md": stack_record,
    "kit/templates/charter-adr.md": charter_record,
    "scripts/agk/intake.py::render_stub": intake_stub,
    "scripts/agk/new_spec.py::make_requirement": new_spec_requirement,
    "docs/adr/TEMPLATE.md": new_spec_requirement,
    "scripts/agk/setup.py::project_adr": setup_adr(back=False),
    "scripts/agk/setup.py::project_adr (back)": setup_adr(back=True),
    "scripts/agk/wsl.py::adr_text": wsl_adr("wsl"),
    "scripts/agk/wsl.py::adr_text (back)": wsl_adr("windows"),
    "scripts/agk/upgrade.py::adr_text": upgrade_adr,
    "scripts/agk/upgrade.py::clean_adr": upgrade_clean,
    "scripts/agk/personal_adopt.py::adr_text": personal_record,
    "scripts/agk/upgrade.py::report": "printed: the skeleton without --write-adr, never written",
    "scripts/agk/uninstall.py::adr_skeleton": "printed: a skeleton a person copies, never written",
}
BUILT = {k: v for k, v in WRITERS.items() if callable(v)}


@pytest.mark.parametrize("writer", sorted(BUILT))
def test_req045_every_kit_writer_of_a_project_adr_passes_its_check(tmp_path, writer):
    """REQ-045: brief #1827 answer 3, each listed writer's text passes `check_adrs.validate`."""
    name, text = BUILT[writer](tmp_path)
    assert checked(name, text) == [], writer


def enclosing(tree: ast.AST, line: int) -> str | None:
    best: tuple[int, str] | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            end = node.end_lineno or node.lineno
            if node.lineno <= line <= end and (best is None or node.lineno > best[0]):
                best = (node.lineno, node.name)
    return best[1] if best else None


def census(root: Path) -> dict[str, str]:
    """`{key: <file>:<line>}` of every writer found by its text under ROOT."""
    found: dict[str, str] = {}
    for path in sorted((root / "scripts" / "agk").rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for n, line in enumerate(source.splitlines(), 1):
            if WRITER_LINE.search(line) and not line.lstrip().startswith("#"):
                found.setdefault(f"{rel}::{enclosing(tree, n)}", f"{rel}:{n}")
    for path in sorted((root / "kit" / "templates").rglob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        if lines and lines[0].startswith("# ADR-"):
            rel = path.relative_to(root).as_posix()
            found[rel] = f"{rel}:1"
    if (root / "docs" / "adr" / "TEMPLATE.md").is_file():
        found["docs/adr/TEMPLATE.md"] = "docs/adr/TEMPLATE.md:1"
    return found


def unlisted(root: Path) -> list[str]:
    listed = {key.split(" (", 1)[0] for key in WRITERS}
    return [where for key, where in census(root).items() if key not in listed]


def test_req045_the_census_finds_no_writer_the_table_does_not_list():
    """REQ-045: brief #1827 answer 3, every writer found by its text is a row of the table."""
    assert unlisted(KIT_ROOT) == []


def test_req045_the_census_lists_no_row_it_cannot_find():
    """REQ-045: answer 3, a row whose writer is gone is named, so the table stays the census."""
    found = set(census(KIT_ROOT))
    found.add("scripts/agk/personal_adopt.py::adr_text")  # its title is `# {aid}`, no census text
    assert sorted({k.split(" (", 1)[0] for k in WRITERS} - found) == []


def test_req045_an_invented_writer_is_named_by_file_and_line(tmp_path):
    """REQ-045: answer 3, a new writer in a copy of the census input is named `<file>:<line>`."""
    copy = tmp_path / "kit"
    shutil.copytree(KIT_ROOT / "scripts" / "agk", copy / "scripts" / "agk")
    shutil.copytree(KIT_ROOT / "kit" / "templates", copy / "kit" / "templates")
    (copy / "scripts" / "agk" / "extra.py").write_text(
        'def record(n):\n    return f"# ADR-{n:04d}: An extra record"\n', encoding="utf-8"
    )
    (copy / "kit" / "templates" / "extra-adr.md").write_text("# ADR-{{adr}}: Extra\n", "utf-8")
    assert unlisted(copy) == ["scripts/agk/extra.py:2", "kit/templates/extra-adr.md:1"]


def test_req045_a_field_check_adrs_requires_is_in_every_built_text(tmp_path):
    """REQ-045: answer 3, the table reads the check's own lists, so a new field turns it red."""
    name, text = steward_work_type(tmp_path)
    for field in check_adrs.FIELDS:
        assert re.search(rf"(?m)^- {field}: \S", text), field
    for section in check_adrs.SECTIONS:
        assert f"\n## {section}\n" in text, section


# Brief #1888 (ADR-0782): a skill step that has the model write an ADR by hand copies a kit
# template that the table above lists; `stack` and `upgrade` write theirs by script, and `design`
# only reads the charter. A new skill that names an ADR file fails, named, until review lists it.
SKILL_WRITERS = {
    "start": "kit/templates/charter-adr.md",
    "vision": "kit/templates/charter-adr.md",
}
SKILL_OTHERS = {"stack", "upgrade", "design"}
HAND_ADR = re.compile(r"`docs/adr/<[a-z]+>-[a-z0-9<>-]+\.md`")


def hand_writers(root: Path) -> list[str]:
    """The skills whose text names an ADR file it writes (`docs/adr/<n>-<slug>.md`)."""
    return sorted(
        path.parent.name
        for path in (root / "skills").glob("*/SKILL.md")
        if HAND_ADR.search(path.read_text(encoding="utf-8"))
    )


def test_req045_a_skill_that_writes_an_adr_by_hand_copies_a_listed_template():
    """REQ-045: brief #1888 answer 9, each such step names a `kit/templates/` file of the census."""
    found = set(hand_writers(KIT_ROOT)) - SKILL_OTHERS
    assert sorted(found - set(SKILL_WRITERS)) == []
    for skill, template in SKILL_WRITERS.items():
        body = (KIT_ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        assert template in body, skill
        assert template in WRITERS, skill


def test_req045_a_new_skill_that_writes_an_adr_is_named(tmp_path):
    """REQ-045: brief #1888 answer 9, a new hand-writing skill is named, never its text."""
    copy = tmp_path / "kit"
    shutil.copytree(KIT_ROOT / "skills", copy / "skills")
    extra = copy / "skills" / "extra" / "SKILL.md"
    extra.parent.mkdir()
    extra.write_text("Write `docs/adr/<adr>-extra-record.md` with the fields.\n", "utf-8")
    assert set(hand_writers(copy)) - SKILL_OTHERS - set(SKILL_WRITERS) == {"extra"}
