"""Tests of the architecture record's required parts and target numbers (brief #1595, ADR-0675;
amendments 203 to 205: SPEC-0029 rule 4, SPEC-0072 rule 5, SPEC-0048 rule 7; REQ-079 AC1, REQ-055).

The product's one record, `docs/architecture.md`, holds `## Context`, `## Parts`, `## Data stores`,
`## Outside services`, `## Needs`, `## Diagram` and `## Layers`. The `architecture-record` step of
`run_gates.py` and `front_door.py check-design` refuse a record missing a section, an outside
service of the chosen stack option missing from the record or from its diagram, and a `Needs`
number that the quoted needs answer does not give; each line names the section and the rule,
never a value. A record written before this change (none of the new sections) is held as
`not run`, never `ok`, until its next edit. A front-door design is a slice document with one
`Architecture: docs/architecture.md` line: refused without it when the design is named (edited),
a warning when the whole folder is read. The needs question is asked once, with its
recommendation, in each app shape's words. Fixtures in `tmp_path` only: invented data, no network.
"""

from __future__ import annotations

import shutil
import socket
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
AGK = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(AGK))

import engines  # noqa: E402
import front_door  # noqa: E402
import run_gates  # noqa: E402
from gates import architecture_record  # noqa: E402

pytestmark = pytest.mark.usefixtures("no_network")

PLAYBOOKS = KIT_ROOT / "config" / "playbooks"
TODAY = "2026-11-21"
SLUG = "orders-are-lost"
SERVICE = "Mailrelay Example"
ANSWER = "up to 300 at once, at most 2 hours down a month, under 80 dollars a month"
SECTIONS = {
    "Context": "An invented shop for example.com that takes orders.",
    "Parts": "- web: the pages\n- api: the order calls",
    "Data stores": "- orders store: one database",
    "Outside services": f"- {SERVICE}: sends the receipts",
    "Needs": (
        "- Busiest hour: 300 people at once\n- Downtime: at most 2 hours a month\n"
        "- Cost: under 80 dollars a month\n- Recovery time: 4 hours\n"
        "- Logged: each order call and each sign-in"
    ),
    "Diagram": f"```mermaid\nflowchart LR\n  web --> api --> store\n  api --> mail[{SERVICE}]\n```",
    "Layers": "| Layer | Paths |\n|-------|-------|\n| `src` | `src/**` |",
}
STACK = """# ADR-0002: Stack options

- Status: Accepted

## Decision

1. **Options**:
   - Option A — Python. External services: {services}. Practices: tests.
2. **Practices**: tests.
3. **Chosen**: Option A
"""


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the architecture record check opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def project(root: Path, answer: str | None = ANSWER, services: str = SERVICE) -> Path:
    shutil.copytree(PLAYBOOKS, root / "config" / "playbooks")
    write(root, "agk.toml", 'mode = "init"\n\n[delivery]\nwork_type = "web-app"\n')
    write(root, "docs/adr/0002-stack-options.md", STACK.format(services=services))
    if answer is not None:
        charter = f"# ADR-0003: Project charter\n\n1. **Discovery**:\n   - scale: {answer}\n"
        write(root, "docs/adr/0003-project-charter.md", charter)
    return root


def record(root: Path, drop: str = "", **change: str) -> Path:
    parts = [f"## {k}\n\n{change.get(k, v)}\n" for k, v in SECTIONS.items() if k != drop]
    return write(root, "docs/architecture.md", "# Architecture\n\n" + "\n".join(parts))


def found(root: Path) -> list[tuple[str, str]]:
    return architecture_record.check(root, {})


# --- the record's required parts (amendment 204, SPEC-0072 rule 5) ------------------------------


def test_req_079_ac1_a_full_record_passes(tmp_path):
    """REQ-079 AC1: every section, the services in the diagram, the quoted numbers: no failure."""
    record(project(tmp_path))
    assert found(tmp_path) == []
    assert architecture_record.skipped(tmp_path) is None
    assert architecture_record.applies(tmp_path)


@pytest.mark.parametrize("section", list(SECTIONS))
def test_req_079_ac1_a_record_missing_a_section_is_refused(tmp_path, section):
    """REQ-079 AC1: each missing section is one failure that names it and the rule."""
    record(project(tmp_path), drop=section)
    lines = found(tmp_path)
    assert lines, section
    assert all(rule.startswith("SPEC-0072 rule 5") for rule, _ in lines)
    assert any(f"section: {section}" in cls for _, cls in lines)


def test_req_079_ac1_a_diagram_without_a_fenced_block_is_refused(tmp_path):
    record(project(tmp_path), Diagram="web, then api, then store")
    assert any("section: Diagram" in cls for _, cls in found(tmp_path))


def test_req_079_ac1_an_outside_service_missing_from_the_diagram_is_refused(tmp_path):
    """REQ-079 AC1: a service the record lists that the diagram does not draw; no value named."""
    record(project(tmp_path), Diagram="```text\nweb -> api -> store\n```")
    lines = found(tmp_path)
    assert any("diagram" in rule and "section: Diagram" in cls for rule, cls in lines)
    assert SERVICE not in str(lines)


def test_req_079_ac1_a_service_of_the_chosen_option_missing_from_the_record_is_refused(tmp_path):
    record(project(tmp_path, services=f"{SERVICE}, Paystub Example"))
    lines = found(tmp_path)
    assert any("section: Outside services" in cls for _, cls in lines)
    assert "Paystub" not in str(lines)


@pytest.mark.parametrize(
    ("key", "line"),
    [
        ("Busiest hour", "- Busiest hour: 900 people at once"),
        ("Downtime", "- Downtime: at most 7 hours a month"),
        ("Cost", "- Cost: under 500 dollars a month"),
    ],
)
def test_req_079_ac1_a_needs_number_other_than_the_quoted_one_is_refused(tmp_path, key, line):
    """REQ-079 AC1: a number the quoted needs answer does not give; the line, never the number."""
    needs = SECTIONS["Needs"].split("\n")
    needs = [line if n.startswith(f"- {key}:") else n for n in needs]
    record(project(tmp_path), Needs="\n".join(needs))
    lines = found(tmp_path)
    assert [cls for _, cls in lines] == [f"docs/architecture.md; section: Needs; line: {key}"]
    assert not any(ch.isdigit() for ch in lines[0][1])


def test_req_079_ac1_needs_numbers_with_no_quoted_answer_are_refused(tmp_path):
    """Nothing is decided that the person did not give (SPEC-0029 rule 4)."""
    record(project(tmp_path, answer=None))
    assert any("quoted" in rule for rule, _ in found(tmp_path))


def test_req_079_ac1_a_needs_line_missing_is_refused(tmp_path):
    needs = "\n".join(n for n in SECTIONS["Needs"].split("\n") if not n.startswith("- Logged"))
    record(project(tmp_path), Needs=needs)
    assert any("line: Logged" in cls for _, cls in found(tmp_path))


def test_req_079_ac1_the_discovery_answer_is_read_as_the_quoted_answer(tmp_path):
    project(tmp_path, answer=None)
    sha = "0" * 64
    body = f"- scale: (given: in session {TODAY})\n<!-- agk:answer sha256={sha} -->\n{ANSWER}\n"
    write(tmp_path, f"docs/discovery/{SLUG}.md", body + "<!-- agk:answer-end -->\n")
    record(tmp_path)
    assert found(tmp_path) == []


def test_req_079_ac1_a_record_written_before_this_change_is_held_not_ok(tmp_path, capsys):
    """Principle 11: the record of build (d) (only Layers) is `not run` until its next edit."""
    project(tmp_path)
    write(tmp_path, "docs/architecture.md", "# Architecture\n\n## Layers\n\n| a | b |\n")
    assert architecture_record.skipped(tmp_path)
    run_gates.main(["--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "not run architecture-record:" in out
    assert "ok architecture-record" not in out


def test_req_079_ac1_the_runner_runs_the_step_and_names_the_section(tmp_path, capsys):
    record(project(tmp_path), drop="Needs")
    assert run_gates.main(["--root", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "FAIL gates: architecture-record: SPEC-0072 rule 5" in out
    assert "section: Needs" in out


def test_req_079_ac1_no_record_means_the_step_does_not_apply(tmp_path):
    project(tmp_path)
    assert not architecture_record.applies(tmp_path)


def test_req_079_ac1_the_record_the_foundation_writes_passes_the_step(tmp_path, capsys):
    """The foundation's record names and draws the chosen option's services, so it passes."""
    from gates import layers  # noqa: PLC0415

    project(tmp_path)
    assert layers.main(["--root", str(tmp_path), "--write-record"]) == 0
    text = (tmp_path / "docs/architecture.md").read_text(encoding="utf-8")
    assert f"- {SERVICE}:" in text and "{{" not in text
    # brief #1842 answer 4: the written record holds the template's markers until the foundation
    # fills it; each marked section fails, and nothing else does
    # brief #1952: and the three quality sections, so its first edit fills them too
    marked = {*front_door.NEW_SECTIONS, *front_door.QUALITY_SECTIONS}
    assert found(tmp_path) == sorted((MARKER, f"{front_door.RECORD}; section: {s}") for s in marked)
    filled = text.replace("TODO(architect): ", "").replace("TODO(architect)", "none")
    for name in front_door.QUALITY_SECTIONS:
        head, _, rest = filled.partition(f"## {name}\n")
        filled = f"{head}## {name}\n\n{QUALITY[name]}\n\n## {rest.split('## ', 1)[1]}"
    (tmp_path / "docs/architecture.md").write_text(filled, encoding="utf-8")
    assert found(tmp_path) == []
    capsys.readouterr()


MARKER = "SPEC-0072 rule 5: the record holds a TODO(architect) marker"


@pytest.mark.parametrize(
    "section", ["Context", "Parts", "Data stores", "Outside services", "Needs", "Diagram"]
)
def test_req079_a_section_with_a_todo_marker_fails_naming_it(tmp_path, section):
    """REQ-079 (brief #1842 answer 4): one line per section, never the line's text."""
    root = project(tmp_path)
    record(root)
    text = (root / "docs/architecture.md").read_text(encoding="utf-8")
    head = f"## {section}\n"
    planted = "TODO(architect): INVENTEDPLANTEDWORD\n"
    if section == "Diagram":  # inside the fenced block: still the kit's own word
        text = text.replace(head + "\n```mermaid\n", head + "\n```mermaid\n" + planted)
    else:
        text = text.replace(head, head + "\n" + planted)
    (root / "docs/architecture.md").write_text(text, encoding="utf-8")
    rows = found(root)
    assert rows == [(MARKER, f"docs/architecture.md; section: {section}")], rows
    assert all("INVENTEDPLANTEDWORD" not in r + c for r, c in rows)


def test_req079_a_held_record_with_markers_stays_not_run(tmp_path):
    """REQ-079 (brief #1842 answer 4): `record_held` is unchanged."""
    write(tmp_path, "docs/architecture.md", "# Architecture\n\nTODO(architect): all\n\n## Layers\n")
    assert architecture_record.skipped(tmp_path) == architecture_record.HELD


def test_req_079_ac1_the_template_carries_every_section():
    text = (KIT_ROOT / "kit" / "templates" / "architecture.md").read_text(encoding="utf-8")
    heads = [ln[3:].strip() for ln in text.split("\n") if ln.startswith("## ")]
    assert all(s in heads for s in SECTIONS)
    assert "{{layers}}" in text


# --- one record: the front-door design is a slice (amendment 205, SPEC-0048 rule 7) -------------


def design(root: Path, *extra: str) -> str:
    write(root, f"docs/research/{SLUG}.md", "# Research\n")
    lines = ["# Architecture: Orders are lost", f"Research: docs/research/{SLUG}.md", *extra]
    lines += ["", "```text", "shop api -> queue -> worker", "```", ""]
    rel = f"docs/design/architecture/{SLUG}.md"
    write(root, rel, "\n".join(lines))
    return rel


def problems(root: Path, rel: str, strict: bool) -> tuple[list[str], list[str]]:
    text = (root / rel).read_text(encoding="utf-8")
    return front_door.slice_problems(rel, text, strict)


def test_req_055_a_named_design_without_the_architecture_line_is_refused(tmp_path):
    """REQ-055: an edited (named) design without `Architecture: docs/architecture.md` is refused."""
    rel = design(tmp_path)
    out, notes = problems(tmp_path, rel, strict=True)
    assert len(out) == 1 and "Architecture: docs/architecture.md" in out[0]
    assert out[0].startswith("rule 7:")
    assert notes == []


def test_req_055_an_existing_design_is_held_as_a_warning_until_its_next_edit(tmp_path):
    """Q-2: a design read with the whole folder (not edited) is a warning, never a failure."""
    rel = design(tmp_path)
    out, notes = problems(tmp_path, rel, strict=False)
    assert out == [] and len(notes) == 1 and "until its next edit" in notes[0]


@pytest.mark.parametrize(
    "lines",
    [
        ("Architecture: docs/other.md",),
        ("Architecture: docs/architecture.md", "Architecture: docs/architecture.md"),
    ],
)
def test_req_055_a_wrong_or_repeated_architecture_line_is_refused(tmp_path, lines):
    rel = design(tmp_path, *lines)
    assert problems(tmp_path, rel, strict=False)[0]


def test_req_055_a_design_with_the_line_passes_the_slice_rule(tmp_path):
    rel = design(tmp_path, "Architecture: docs/architecture.md")
    assert problems(tmp_path, rel, strict=True) == ([], [])


def test_req_055_check_design_reads_the_record_and_names_its_section(tmp_path, capsys):
    record(project(tmp_path), drop="Context")
    code = front_door.main(["check-design", "--date", TODAY, "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 1
    assert "section: Context" in out


# --- the needs question (amendment 203, SPEC-0029 rule 4) ---------------------------------------


def questions(root: Path, capsys: pytest.CaptureFixture[str], *args: str) -> list[str]:
    assert engines.main(["questions", *args, "--root", str(root)]) == 0
    return capsys.readouterr().out.splitlines()


def test_req_079_ac1_the_needs_question_is_asked_once_with_its_recommendation(tmp_path, capsys):
    lines = questions(tmp_path, capsys)
    asked = [ln for ln in lines if "Recommended:" in ln]
    assert len(asked) == 1
    topic, text = asked[0].split("\t")
    assert topic == "scale"  # the topic keeps its id, so every existing answer still passes
    for words in ("busiest hour", "down", "cost", "up to 200 at once", "under 50 dollars"):
        assert words in text
    assert not any("What scale is expected" in ln for ln in lines)


@pytest.mark.parametrize(
    ("kind", "words"),
    [("web-app", "people"), ("api-service", "calls per minute"), ("data-pipeline", "runs per day")],
)
def test_req_079_ac1_the_needs_question_takes_the_app_shape_words(tmp_path, capsys, kind, words):
    shutil.copytree(PLAYBOOKS, tmp_path / "config" / "playbooks")
    lines = questions(tmp_path, capsys, "--work-type", kind)
    asked = [ln for ln in lines if "Recommended:" in ln]
    assert len(asked) == 1 and words in asked[0]


def test_req_079_ac1_the_vision_skill_asks_it_in_plain_words():
    text = (KIT_ROOT / "skills" / "vision" / "SKILL.md").read_text(encoding="utf-8")
    assert "busiest hour" in text and "Recommended:" in text
    stack = (KIT_ROOT / "skills" / "stack" / "SKILL.md").read_text(encoding="utf-8")
    assert "docs/architecture.md" in stack and "## Diagram" in stack


# --- the quality sections (SPEC-0073 rule 8, amendment 236; brief #1952, ADR-0808; REQ-080 AC5) --

QUALITY = {
    "Quality scenarios": (
        "- performance efficiency: 300 people order at once -> each page answers"
        " (under 2 seconds)\n"
        "- reliability: the orders store fails -> the shop is back (within 4 hours)\n"
        "- security: a stranger calls the order api -> it is refused (100 percent of calls)\n"
        "- maintainability: the month's bill comes -> it stays in budget (under 80 dollars)"
    ),
    "Threats": (
        "- web to api: S, T, I: signed sessions and TLS on every call\n"
        "- api to Mailrelay Example: I: accepted: the receipts hold no card number"
    ),
    "Operations": (
        "- traced: each order call, end to end\n- alerted: the order api down for 5 minutes"
    ),
}
QUALITY_HELD = "the record predates its quality sections; held until its next edit"


def quality_record(root: Path, drop: tuple[str, ...] = (), **change: str) -> Path:
    path = record(root)
    parts = [f"## {k}\n\n{change.get(k, v)}\n" for k, v in QUALITY.items() if k not in drop]
    path.write_text(path.read_text(encoding="utf-8") + "\n" + "\n".join(parts), encoding="utf-8")
    return path


def test_req_080_ac5_the_tuple_is_the_three_sections_apart_from_the_rest():
    """REQ-080 AC5: one tuple, apart from the sections of amendment 204, which are unchanged."""
    assert front_door.QUALITY_SECTIONS == ("Quality scenarios", "Threats", "Operations")
    assert front_door.NEW_SECTIONS == (
        "Context", "Parts", "Data stores", "Outside services", "Needs", "Diagram"
    )
    assert front_door.RECORD_SECTIONS == (*front_door.NEW_SECTIONS, "Layers")


def test_req_080_ac5_a_full_record_with_the_quality_sections_passes(tmp_path, capsys):
    quality_record(project(tmp_path))
    assert found(tmp_path) == []
    run_gates.main(["--root", str(tmp_path)])  # the fixture's other gates are not this test's
    out = capsys.readouterr().out
    assert "ok architecture-record" in out and "architecture-quality" not in out


def test_req_080_ac5_a_record_without_the_quality_sections_is_a_note(tmp_path, capsys):
    """REQ-080 AC5: all six sections and none of the quality ones: ok plus the quality hold."""
    record(project(tmp_path))
    assert front_door.quality_held((tmp_path / front_door.RECORD).read_text(encoding="utf-8"))
    assert found(tmp_path) == []
    run_gates.main(["--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "ok architecture-record\n" in out
    assert f"not run architecture-quality: {QUALITY_HELD}" in out
    assert "ok architecture-quality" not in out and "FAIL gates: architecture" not in out


def test_req_080_ac5_a_held_record_prints_both_reasons_and_never_ok(tmp_path, capsys):
    project(tmp_path)
    write(tmp_path, "docs/architecture.md", "# Architecture\n\n## Layers\n\n| a | b |\n")
    run_gates.main(["--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "not run architecture-record:" in out and "not run architecture-quality:" in out
    assert "ok architecture-record" not in out and "ok architecture-quality" not in out


@pytest.mark.parametrize(
    ("kept", "missing"),
    [
        ("Threats", ["Operations", "Quality scenarios"]),
        ("Operations", ["Quality scenarios", "Threats"]),
        ("Quality scenarios", ["Operations", "Threats"]),
    ],
)
def test_req_080_ac5_one_quality_section_fails_the_missing_ones(tmp_path, capsys, kept, missing):
    """REQ-080 AC5: a record with one section fails each missing one, naming the section."""
    root = project(tmp_path)
    quality_record(root, drop=tuple(s for s in QUALITY if s != kept))
    lack = "SPEC-0072 rule 5: the record lacks a required section"
    assert found(root) == [(lack, f"{front_door.RECORD}; section: {s}") for s in missing]
    assert run_gates.main(["--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert all(f"section: {s}" in out for s in missing)
    assert "architecture-quality" not in out


@pytest.mark.parametrize("section", list(QUALITY))
def test_req_080_ac5_a_marker_in_a_quality_section_fails(tmp_path, section):
    root = project(tmp_path)
    planted = f"TODO(architect): INVENTEDPLANTEDWORD\n{QUALITY[section]}"
    quality_record(root, **{section: planted})
    rows = found(root)
    assert rows == [(MARKER, f"docs/architecture.md; section: {section}")], rows
    assert all("INVENTEDPLANTEDWORD" not in r + c for r, c in rows)


FORM = "SPEC-0072 rule 5: a line of the section is not of its form"


@pytest.mark.parametrize(
    ("section", "text"),
    [
        ("Quality scenarios", "- speed: 300 people -> pages answer (under 2 seconds)"),
        ("Quality scenarios", "- reliability: the store fails -> it is back"),
        ("Quality scenarios", "- reliability: the store fails, it is back (4 hours)"),
        ("Threats", "- web to api: S, X: signed sessions"),
        ("Threats", "- web to api: signed sessions"),
        ("Threats", "- web to api: S, S: signed sessions"),
        ("Threats", "- web to api: T: accepted:"),
        ("Operations", "- watched: each order call"),
        ("Operations", "- traced:"),
    ],
)
def test_req_080_ac5_a_line_out_of_form_fails_naming_the_section(tmp_path, section, text):
    root = project(tmp_path)
    quality_record(root, **{section: f"{QUALITY[section]}\n{text}"})
    rows = found(root)
    assert rows == [(FORM, f"docs/architecture.md; section: {section}")], rows
    assert all(text not in r + c for r, c in rows)


EMPTY = "SPEC-0072 rule 5: the section holds none of its lines"


@pytest.mark.parametrize("section", list(QUALITY))
def test_req_080_ac5_an_empty_quality_section_fails(tmp_path, section):
    root = project(tmp_path)
    quality_record(root, **{section: "Nothing yet."})
    assert found(root) == [(EMPTY, f"docs/architecture.md; section: {section}")]


def test_req_080_ac5_each_numbered_need_has_a_scenario(tmp_path):
    """Four `## Needs` lines of the fixture hold a number (`Logged` does not): three scenarios
    fail; the fixture's four pass."""
    root = project(tmp_path)
    fewer = "\n".join(QUALITY["Quality scenarios"].split("\n")[:3])
    quality_record(root, **{"Quality scenarios": fewer})
    few = "SPEC-0072 rule 5: the section has fewer scenarios than numbered needs"
    assert found(root) == [(few, "docs/architecture.md; section: Quality scenarios")]
    quality_record(root)
    assert found(root) == []


@pytest.mark.parametrize(
    "attribute",
    [
        "functional suitability", "performance efficiency", "compatibility", "usability",
        "reliability", "security", "maintainability", "portability",
    ],
)
def test_req_080_ac5_each_of_the_eight_attributes_is_read(tmp_path, attribute):
    root = project(tmp_path)
    extra = f"- {attribute}: an invented stimulus -> an invented response (1 second)"
    quality_record(root, **{"Quality scenarios": f"{QUALITY['Quality scenarios']}\n{extra}"})
    assert found(root) == []


def test_req_080_ac5_a_crlf_record_is_read_the_same(tmp_path):
    root = project(tmp_path)
    path = quality_record(root, drop=("Operations",))
    path.write_bytes(path.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
    lack = "SPEC-0072 rule 5: the record lacks a required section"
    assert found(root) == [(lack, "docs/architecture.md; section: Operations")]


def test_req_080_ac5_check_design_reads_the_quality_sections(tmp_path, capsys):
    root = project(tmp_path)
    quality_record(root, drop=("Threats",))
    with pytest.raises(front_door.Refusal) as caught:
        front_door.check_design([], root, front_door.iso_date(TODAY))
    assert any("section: Threats" in p for p in caught.value.problems)
    record(root)
    front_door.check_design([], root, front_door.iso_date(TODAY))
    assert "quality sections" in capsys.readouterr().out


def test_req_080_ac5_the_template_carries_the_quality_sections_with_markers():
    """REQ-080 AC5: the one tuple is read by the template test, the writer and the check."""
    text = (KIT_ROOT / "kit" / "templates" / "architecture.md").read_text(encoding="utf-8")
    body = dict(front_door.sections_of(text.split("\n")))
    heads = list(body)
    assert heads.index("Diagram") < heads.index("Quality scenarios")
    for name in front_door.QUALITY_SECTIONS:
        assert any(front_door.MARKER in ln for ln in body[name]), name
