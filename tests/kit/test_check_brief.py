"""check_brief.py and the shape of a brief (SPEC-0030 rule 4; REQ-037 AC4)."""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
GOOD = (
    'Sentence: "A team can run a thing."\n'
    "Answers (the maintainers'):\n1. one\n   wrapped\n2. two\n"
    "Depends-on: #3\nDepends-on: #4\nSize: M\n"
    "Advances: REQ-001, REQ-002\nTouches: scripts/agk/*.py, docs/**\nPriority: 1\n"
    "Contexts: kit (x); github (x); local (x); personal (x); stacks (x)\n"
)
STUDY = (  # brief #1800: a passing --root brief shows its study (ADR-0752)
    "Impact:\nSpeed: none: a test brief\nQuality: none: a test brief\nGitHub: none: a test brief\n"
    "Cost: none: a test brief\nTests: none: a test brief\nWiring: none: a test brief\n"
    "Prior: none: a test brief\nClass: a test brief; seen 0 (searched nothing)\n"
)


def check(tmp_path: Path, body: str | None, *extra: str):
    args = [str(tmp_path / "brief.md")] if body is not None else [str(tmp_path / "none.md")]
    if body is not None and "--root" in extra and "Impact:" not in body:
        body += STUDY
    if body is not None:
        (tmp_path / "brief.md").write_text(body, encoding="utf-8")
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "check_brief.py"), *args, *extra],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )


def test_ac4_a_good_body_passes(tmp_path):
    """REQ-037 AC4"""
    out = check(tmp_path, GOOD)
    assert out.returncode == 0 and out.stdout.strip() == "ok brief"


def test_ac4_depends_on_lines_are_optional_and_answers_may_be_plain(tmp_path):
    """REQ-037 AC4"""
    body = (
        'Sentence: "x"\nAnswers:\n1. a\nSize: S\nAdvances: new\nTouches: docs/requirements.md\n'
        "Contexts: kit (x); github (x); local (x); personal (x); stacks (x)\n"
    )
    assert check(tmp_path, body).stdout.strip() == "ok brief"


@pytest.mark.parametrize(
    ("body", "missing"),
    [
        (GOOD.replace('Sentence: "A team can run a thing."\n', ""), "Sentence"),
        (GOOD.replace('"A team can run a thing."', "no quotes"), "Sentence"),
        (GOOD.replace('"A team can run a thing."', '""'), "Sentence"),
        (GOOD.replace('"A team can run a thing."', '"' + "x" * 301 + '"'), "300"),
        (GOOD + 'Sentence: "second"\n', "Sentence"),
        (GOOD.replace("Answers (the maintainers'):\n", ""), "Answers"),
        (GOOD.replace("1. one\n   wrapped\n2. two\n", ""), "numbered"),
        (GOOD.replace("2. two", "3. two"), "numbered"),
        (GOOD.replace("1. one", "2. one"), "numbered"),
        (GOOD.replace("Depends-on: #4", "Depends-on: 4"), "Depends-on"),
        (GOOD.replace("Size: M\n", ""), "Size"),
        (GOOD.replace("Size: M", "Size: XL"), "Size"),
        (GOOD + "Size: S\n", "Size"),
        ("", "Sentence"),
    ],
)
def test_ac4_each_bad_shape_fails_naming_rule_4(tmp_path, body, missing):
    """REQ-037 AC4"""
    out = check(tmp_path, body)
    assert out.returncode == 1
    assert out.stdout.startswith("FAIL brief: rule 4: ") and missing in out.stdout


def test_ac4_a_failure_never_prints_the_sentence(tmp_path):
    """REQ-037 AC4"""
    out = check(tmp_path, GOOD.replace("Size: M\n", "").replace("run a thing", "UNIQUEWORDS"))
    assert out.returncode == 1 and "UNIQUEWORDS" not in out.stdout + out.stderr


def test_ac4_an_unreadable_file_and_a_bad_call_fail(tmp_path):
    """REQ-037 AC4"""
    out = check(tmp_path, None)
    assert out.returncode == 1 and out.stdout.startswith("FAIL brief: ")
    out = check(tmp_path, GOOD, "extra")
    assert out.returncode == 2 and out.stdout.startswith("usage: ")


def test_ac4_check_brief_makes_no_network_call():
    """REQ-037 AC4 and rule 5"""
    text = (SCRIPTS / "check_brief.py").read_text(encoding="utf-8")
    assert "subprocess" not in text and "urllib" not in text and '"gh"' not in text


# --- the lines of SPEC-0034 rule 2 (REQ-041 AC2) -----------------------------------------------


@pytest.mark.parametrize(
    ("body", "missing"),
    [
        (GOOD.replace("Advances: REQ-001, REQ-002\n", ""), "Advances"),
        (GOOD.replace("Advances: REQ-001, REQ-002", "Advances: soon"), "Advances"),
        (GOOD.replace("Advances: REQ-001, REQ-002", "Advances: REQ-001 REQ-002"), "Advances"),
        (GOOD.replace("Advances: REQ-001, REQ-002", "Advances: new, REQ-001"), "Advances"),
        (GOOD + "Advances: REQ-003\n", "Advances"),
        (GOOD.replace("Touches: scripts/agk/*.py, docs/**\n", ""), "Touches"),
        (GOOD.replace("Touches: scripts/agk/*.py, docs/**", "Touches:"), "Touches"),
        (GOOD.replace("Touches: scripts/agk/*.py, docs/**", "Touches: docs/**,,x"), "Touches"),
        (GOOD + "Touches: docs/y\n", "Touches"),
        (GOOD.replace("Priority: 1", "Priority: 4"), "Priority"),
        (GOOD.replace("Priority: 1", "Priority: high"), "Priority"),
        (GOOD + "Priority: 2\n", "Priority"),
    ],
)
def test_rule2_each_bad_line_fails_naming_rule_2(tmp_path, body, missing):
    """REQ-041 AC2"""
    out = check(tmp_path, body)
    assert out.returncode == 1
    assert out.stdout.startswith("FAIL brief: rule 2: ") and missing in out.stdout


def requirements(tmp_path: Path, *ids: str) -> Path:
    root = tmp_path / "project"
    (root / "docs").mkdir(parents=True)
    text = "".join(f"### {i} a title\n\n- Status: planned\n\n" for i in ids)
    (root / "docs" / "requirements.md").write_text(text, encoding="utf-8")
    return root


def test_rule2_a_missing_line_names_the_rule_and_what_is_missing(tmp_path):
    """REQ-041 AC2"""
    out = check(tmp_path, GOOD.replace("Touches: scripts/agk/*.py, docs/**\n", ""))
    assert out.stdout.startswith("FAIL brief: rule 2: ") and "Touches" in out.stdout
    assert "Advances" not in out.stdout and "Priority" not in out.stdout


def test_rule2_priority_is_optional_and_advances_new_passes(tmp_path):
    """REQ-041 AC2"""
    body = GOOD.replace("Priority: 1\n", "").replace("REQ-001, REQ-002", "new")
    body = body.replace("Touches: ", "Touches: docs/requirements.md, ")
    assert check(tmp_path, body).stdout.strip() == "ok brief"


INTAKE_ONLY = "rule 2: Advances: new is only for an intake brief, whose Touches names"


@pytest.mark.parametrize(
    ("touches", "passes"),
    [
        ("src/ui/cart.ts", False),
        ("docs/requirements.md, docs/specs/*", True),
        ("docs/*", False),
        ("docs/requirements.md.bak", False),
    ],
)
def test_rule2_advances_new_passes_only_when_touches_names_the_requirements_file(
    tmp_path, touches, passes
):
    """REQ-041 AC2: brief #1929 answers 1 and 5, `new` is for an intake (SPEC-0034 rule 2)."""
    body = GOOD.replace("REQ-001, REQ-002", "new").replace("scripts/agk/*.py, docs/**", touches)
    out = check(tmp_path, body)
    if passes:
        assert out.returncode == 0 and out.stdout.strip() == "ok brief"
    else:
        assert out.returncode == 1 and out.stdout.startswith(f"FAIL brief: {INTAKE_ONLY}")
        assert "docs/requirements.md (SPEC-0034 rule 2)" in out.stdout
        assert "A team can run a thing" not in out.stdout


def test_rule2_a_requirement_id_needs_no_requirements_touch(tmp_path):
    """REQ-041 AC2: brief #1929 answer 1, `Advances: REQ-n` passes as today."""
    assert check(tmp_path, GOOD.replace("docs/**", "src/ui/cart.ts")).returncode == 0


def test_rule2_the_steward_is_refused_before_filing_a_build_brief_with_new(tmp_path):
    """REQ-041 AC2: brief #1929 answer 2, `file-brief` refuses in its brief check, so nothing is
    filed (the refusal returns before the post)."""
    sys.path.insert(0, str(SCRIPTS))
    import steward_owner

    body = GOOD.replace("REQ-001, REQ-002", "new").replace("scripts/agk/*.py, docs/**", "app/x.py")
    refusal = steward_owner.brief_refusal(tmp_path, body, None)
    assert refusal is not None and refusal.startswith("refused: the body fails the brief check")
    assert INTAKE_ONLY in refusal


def test_rule2_every_guide_or_template_brief_with_new_is_an_intake(tmp_path):
    """REQ-041 AC2: brief #1929 answer 7, a template or guide brief that teaches `Advances: new`
    names `docs/requirements.md` in its `Touches:`, so it passes the check."""
    sys.path.insert(0, str(SCRIPTS))
    import check_brief

    base = SCRIPTS.parents[1]
    for top in ("kit/templates", "skills", "docs/guides"):
        assert (base / top).is_dir()
        for path in sorted((base / top).rglob("*")):
            if not path.is_file() or path.suffix not in {".md", ".txt", ".toml", ".j2", ""}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            lines = [x.strip() for x in text.splitlines()]
            if "Advances: new" not in lines:
                continue
            assert check_brief.intake_problems(text) == [], path
    assert check_brief.intake_problems("Advances: new\nTouches: docs/requirements.md\n") == []
    assert check_brief.intake_problems("Advances: new\nTouches: app/x.py\n") != []


def test_rule2_root_fails_an_absent_requirement_and_never_prints_it(tmp_path):
    """REQ-041 AC2: files only; the id is not repeated."""
    root = requirements(tmp_path, "REQ-001")
    out = check(tmp_path, GOOD, "--root", str(root))
    assert out.returncode == 1 and out.stdout.startswith("FAIL brief: rule 2: ")
    assert "REQ-002" not in out.stdout + out.stderr and "docs/requirements.md" in out.stdout


def test_rule2_root_passes_existing_requirements_and_new(tmp_path):
    """REQ-041 AC2"""
    root = requirements(tmp_path, "REQ-001", "REQ-002")
    assert check(tmp_path, GOOD, "--root", str(root)).stdout.strip() == "ok brief"
    new = GOOD.replace("REQ-001, REQ-002", "new").replace("docs/**", "docs/requirements.md")
    assert check(tmp_path, new, "--root", str(requirements(tmp_path / "e"))).returncode == 0


def test_rule2_without_root_the_shape_alone_is_checked(tmp_path):
    """REQ-041 AC2"""
    assert check(tmp_path, GOOD.replace("REQ-001, REQ-002", "REQ-999")).returncode == 0


def test_rule2_root_without_a_requirements_file_fails_and_a_bad_call_is_usage(tmp_path):
    """REQ-041 AC2"""
    out = check(tmp_path, GOOD, "--root", str(tmp_path / "nowhere"))
    assert out.returncode == 1 and out.stdout.startswith("FAIL brief: ")
    assert check(tmp_path, GOOD, "--root").returncode == 2
    assert check(tmp_path, GOOD, "--other", "x").stdout.startswith("usage: ")


# --- a measured cause (SPEC-0032 rule 9; REQ-039 AC6) -------------------------------------------

MEASURED = (
    "Measured: python3 scripts/agk/check_x.py -> before: FAIL x; after the change: ok x"
    " (the output before and after)\n"
)
ZERO = GOOD.replace("Priority: 1\n", "Priority: 0\n")


def test_ac6_a_priority_0_brief_with_a_measured_line_passes(tmp_path):
    """REQ-039 AC6: rule 9 (the command and the output before and after)."""
    assert check(tmp_path, ZERO + MEASURED).stdout.strip() == "ok brief"


def test_ac6_a_priority_0_brief_without_a_measured_line_fails_naming_the_rule(tmp_path):
    """REQ-039 AC6: rule 9 (a cause is measured, not reasoned); the sentence is not repeated."""
    out = check(tmp_path, ZERO)
    assert out.returncode == 1
    assert out.stdout.startswith("FAIL brief: rule 9: ") and "Measured" in out.stdout
    assert "A team can run a thing" not in out.stdout


@pytest.mark.parametrize(
    "line",
    [
        "Measured:\n",
        "Measured: python3 x.py\n",
        "Measured: before: FAIL only\n",
        "Measured: after: ok only\n",
        "measured: before: x after: y\n",
    ],
)
def test_ac6_a_measured_line_without_both_outputs_does_not_count(tmp_path, line):
    """REQ-039 AC6: rule 9 (the line holds the output before and after a change)."""
    assert check(tmp_path, ZERO + line).returncode == 1


def test_ac6_two_measured_lines_fail(tmp_path):
    """REQ-039 AC6: rule 9 (exactly one)."""
    assert check(tmp_path, ZERO + MEASURED + MEASURED).returncode == 1


def test_ac6_a_priority_1_to_3_brief_needs_no_measured_line_and_may_carry_one(tmp_path):
    """REQ-039 AC6: rule 9 (only Priority: 0 requires it)."""
    assert check(tmp_path, GOOD).stdout.strip() == "ok brief"
    assert check(tmp_path, GOOD + MEASURED).stdout.strip() == "ok brief"


def test_ac6_the_brief_the_router_writes_for_a_red_branch_needs_none(tmp_path):
    """REQ-039 AC6: rule 9 (the router names no cause, so it measures none)."""
    body = (
        'Sentence: "The default branch is red."\nAnswers:\n1. the failing check\nSize: S\n'
        "Advances: none\nTouches: docs/**\nPriority: 0\n"
    )
    assert check(tmp_path, body).stdout.strip() == "ok brief"


# --- brief #982 answer 1: a brief that touches a protected path class without an ADR -----------

PROTECTED = "# classes\nconstitution/\nscripts/agk/\nMakefile\ndocs/requirements.md\n"
WARN_4B = "rule 4b: Touches names a protected path class"


def protected_root(tmp_path: Path) -> Path:
    root = requirements(tmp_path, "REQ-001", "REQ-002")
    (root / "config").mkdir()
    (root / "config" / "protected-paths.txt").write_text(PROTECTED, encoding="utf-8")
    return root


def test_rule4b_a_protected_touch_without_an_adr_warns_and_still_passes(tmp_path):
    """REQ-013: brief #982 answer 1 (a warning, never a failure; the class is named)."""
    out = check(tmp_path, GOOD, "--root", str(protected_root(tmp_path)))
    assert out.returncode == 0, out.stdout
    warns = [ln for ln in out.stdout.splitlines() if WARN_4B in ln]
    assert warns == [
        "warning: rule 4b: Touches names a protected path class (scripts/agk/, "
        "docs/requirements.md) and the brief "
        "reserves no ADR and names no Covered-by"
    ]
    assert out.stdout.splitlines()[-1] == "ok brief"


@pytest.mark.parametrize("line", ["Reserved: ADR-0999\n", "Covered-by: ADR-0998\n"])
def test_rule4b_a_reserved_adr_or_a_covered_by_line_silences_the_warning(tmp_path, line):
    """REQ-013: brief #982 answer 1"""
    out = check(tmp_path, GOOD + line, "--root", str(protected_root(tmp_path)))
    assert out.returncode == 0 and out.stdout.strip() == "ok brief"


@pytest.mark.parametrize(
    ("touches", "named"),
    [
        ("docs/adr/0999-x.md, changelog.d/", None),
        ("Makefile", "Makefile"),
        ("scripts/, docs/requirements.md", "scripts/agk/, docs/requirements.md"),
        ("Makefile.bak", None),
    ],
)
def test_rule4b_the_classes_are_read_from_the_roots_protected_paths(tmp_path, touches, named):
    """REQ-013: brief #982 answer 1 (a folder class matches below it, a file class exactly)."""
    body = GOOD.replace("scripts/agk/*.py, docs/**", touches)
    out = check(tmp_path, body, "--root", str(protected_root(tmp_path)))
    assert out.returncode == 0, out.stdout
    warns = [ln for ln in out.stdout.splitlines() if WARN_4B in ln]
    assert warns == (
        []
        if named is None
        else [f"warning: {WARN_4B} ({named}) and the brief reserves no ADR and names no Covered-by"]
    )


def test_rule4b_without_root_or_without_the_file_nothing_is_warned(tmp_path):
    """REQ-013: brief #982 answer 1 (the classes come only from the root's file)."""
    assert check(tmp_path, GOOD).stdout.strip() == "ok brief"
    root = requirements(tmp_path, "REQ-001", "REQ-002")
    assert check(tmp_path, GOOD, "--root", str(root)).stdout.strip() == "ok brief"


def test_rule4b_a_failing_brief_still_fails_and_the_event_carries_the_warning(tmp_path):
    """REQ-013: brief #982 answer 1 (a saved `issues` event passes and carries the warning)."""
    import json

    root = protected_root(tmp_path)
    assert check(tmp_path, GOOD.replace("Size: M\n", ""), "--root", str(root)).returncode == 1
    event = {
        "action": "opened",
        "issue": {"number": 5, "body": GOOD, "labels": [{"name": "agk-brief"}]},
    }
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [
            sys.executable,
            str(SCRIPTS / "check_brief.py"),
            "--event",
            str(tmp_path / "event.json"),
            "--root",
            str(root),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    result = json.loads(out.stdout)
    assert result["action"] == "pass"
    assert result["warnings"] and WARN_4B in result["warnings"][0]


# --- brief #1063: a Screens line names an imported version i<n> (amendment 161 item 5) ----------

DIGEST = "ab" * 32
HEAD = "0123456789abcdef0123456789abcdef01234567"
LINK = "https://example.com/owner/project/pull/7#issuecomment-1"
UNSEEN = "zz-hidden-screen"  # an invented value that a refusal must never print
IMPORTED_MAP = """# Map of i1

- index.html -> books/default
- `empty.html` -> books/empty
- shot.png -> account/default
- old.html -> out: replaced by the list
"""


def ui_brief(screens: str) -> str:
    return GOOD.replace("Touches: scripts/agk/*.py, docs/**", "Touches: web/**") + screens + "\n"


def imported_root(tmp_path: Path, signed=("i1",)) -> Path:
    """An invented project: `web/**` is UI, a kit version v1 has the page books--error.html, and
    an imported version i1 maps books/default, books/empty and account/default."""
    root = tmp_path / "project"
    (root / "docs" / "design" / "prototype" / "v1").mkdir(parents=True)
    (root / "docs" / "design" / "prototype" / "v1" / "books--error.html").write_text("x\n", "utf-8")
    (root / "docs" / "requirements.md").write_text(
        "# Requirements\n\n### REQ-001 — One\n\n### REQ-002 — Two\n", encoding="utf-8"
    )
    (root / "agk.toml").write_text('[design]\nui_paths = ["web/**"]\n', encoding="utf-8")
    rows = "".join(
        f"| design | {v} | {DIGEST} | {HEAD} | 2026-11-12 | {LINK} |\n" for v in ("v1", *signed)
    )
    (root / "docs" / "design" / "signoffs.md").write_text(
        "# Design sign-offs\n\n| kind | version | digest | head | date | comment |\n"
        "|---|---|---|---|---|---|\n" + rows,
        encoding="utf-8",
    )
    folder = root / "docs" / "design" / "imported" / "i1"
    (folder / "files").mkdir(parents=True)
    for name in ("index.html", "empty.html", "old.html"):
        (folder / "files" / name).write_text("<!doctype html>\n", encoding="utf-8")
    (folder / "map.md").write_text(IMPORTED_MAP, encoding="utf-8")
    return root


def check_screens(tmp_path: Path, line: str, signed=("i1",), drop_map=False):
    root = imported_root(tmp_path, signed)
    if drop_map:
        (root / "docs" / "design" / "imported" / "i1" / "map.md").unlink()
    return check(tmp_path, ui_brief(line), "--root", str(root))


@pytest.mark.parametrize(
    "line",
    [
        "Screens: i1 books/default",
        "Screens: i1 books/empty, account/default",
        "Screens: i1 books/*",
    ],
)
def test_ac5_a_screens_line_naming_a_mapped_imported_state_passes(tmp_path, line):
    """REQ-044 AC5: amendment 161 item 5 (`i<n>` with states that its map covers)."""
    out = check_screens(tmp_path, line)
    assert out.returncode == 0 and out.stdout.strip() == "ok brief", out.stdout + out.stderr


def test_ac5_a_star_of_an_imported_version_is_every_mapped_state_of_the_screen(tmp_path):
    """REQ-044 AC5: amendment 161 item 5 (`*` is every state of the screen the map covers; an
    `out:` row covers nothing, and a page of a kit version is not the imported version's)."""
    sys.path.insert(0, str(SCRIPTS))
    import check_brief

    root = imported_root(tmp_path)
    found = check_brief.screens_named("Screens: i1 books/*, account/default", root)
    assert found == [("books", "default"), ("books", "empty"), ("account", "default")]
    assert check_brief.imported_map(root, "i1") == {
        ("books", "default"): "index.html",
        ("books", "empty"): "empty.html",
        ("account", "default"): "shot.png",
    }


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("Screens: i1 books/error", "rule 10: a Screens screen or state is not covered by the map"),
        (f"Screens: i1 {UNSEEN}/*", "rule 10: a Screens screen or state is not covered"),
        ("Screens: i2 books/default", "rule 10: the Screens version is not signed off"),
    ],
)
def test_ac5_an_unmapped_state_or_an_unlisted_imported_version_is_refused(tmp_path, line, message):
    """REQ-044 AC5: amendment 161 item 5 (refused naming the rule, never a value)."""
    out = check_screens(tmp_path, line)
    assert out.returncode == 1, out.stdout
    assert message in out.stdout
    for value in (UNSEEN, "books/error", "i2"):
        assert value not in out.stdout + out.stderr


def test_ac5_an_imported_version_without_a_signoff_row_is_refused(tmp_path):
    """REQ-044 AC5: amendment 161 item 5 (a version `docs/design/signoffs.md` does not list)."""
    out = check_screens(tmp_path, "Screens: i1 books/default", signed=())
    assert out.returncode == 1
    assert "rule 10: the Screens version is not signed off in docs/design/signoffs.md" in out.stdout


def test_ac5_an_imported_version_without_a_map_covers_nothing(tmp_path):
    """REQ-044 AC5: amendment 161 item 5 (no map, no covered state)."""
    out = check_screens(tmp_path, "Screens: i1 books/default", drop_map=True)
    assert out.returncode == 1 and "not covered by the map" in out.stdout


@pytest.mark.parametrize("line", ["Screens: x1 books/default", "Screens: i0 books/default"])
def test_ac5_a_version_of_neither_kind_is_a_shape_error(tmp_path, line):
    """REQ-044 AC5: the version is `v<n>` or `i<n>`, n from 1."""
    out = check_screens(tmp_path, line)
    assert out.returncode == 1 and "rule 10: the Screens line is not one line" in out.stdout


def test_ac5_a_kit_version_line_still_reads_its_pages(tmp_path):
    """REQ-044 AC5: SPEC-0037 rule 10 unchanged for `v<n>` beside an imported version."""
    assert check_screens(tmp_path, "Screens: v1 books/error").returncode == 0
    out = check_screens(tmp_path / "x", "Screens: v1 books/default")
    assert out.returncode == 1 and "rule 10: a Screens screen or state is not in" in out.stdout


# --- a brief's size limits its code paths (amendment 168 of SPEC-0030 rule 4, brief #1121) -------

SIZED = (
    'Sentence: "A team can size a thing."\nAnswers:\n1. one\n{size}\n'
    "Advances: REQ-001\nTouches: {touches}\n{extra}"
    "Contexts: kit (x); github (x); local (x); personal (x); stacks (x)\n"
)
NOT_CODE = "tests/kit/test_x.py, docs/x.md, docs/adr/0001-*, changelog.d/*, kit/hashes.json"


def sized(size: str, code: int, extra: str = "", not_code: bool = False) -> str:
    paths = [f"scripts/agk/p{i}.py" for i in range(code)] + ([NOT_CODE] if not_code else [])
    return SIZED.format(size=f"Size: {size}", touches=", ".join(paths) or "docs/x.md", extra=extra)


@pytest.mark.parametrize(("size", "limit"), [("S", 3), ("M", 6)])
def test_rule4_a_size_allows_its_code_paths_and_refuses_one_more(tmp_path, size, limit):
    """REQ-039: brief #1121 answer 4 (a) and (b), amendment 168."""
    assert check(tmp_path, sized(size, limit)).stdout.strip() == "ok brief"
    out = check(tmp_path, sized(size, limit + 1))
    assert out.returncode == 1
    assert (
        f"rule 4: Size {size} allows at most {limit} code paths, Touches names {limit + 1}: "
        "split the brief or raise Size"
    ) in out.stdout


def test_rule4_tests_docs_changelog_and_hashes_are_not_code_paths(tmp_path):
    """REQ-039: brief #1121 answer 4 (c)."""
    assert check(tmp_path, sized("S", 3, not_code=True)).stdout.strip() == "ok brief"


def test_rule4_a_broad_line_lifts_the_limit(tmp_path):
    """REQ-039: brief #1121 answer 4 (d), amendment 141's sweep."""
    body = sized("S", 9, extra="Broad: a sweep of every script\n")
    assert check(tmp_path, body).stdout.strip() == "ok brief"


def test_rule4_size_l_is_refused_only_with_a_wave_line(tmp_path):
    """REQ-039: brief #1121 answer 4 (e)."""
    assert check(tmp_path, sized("L", 12)).stdout.strip() == "ok brief"
    out = check(tmp_path, sized("L", 1, extra="Wave: 4\n"))
    assert out.returncode == 1
    assert "rule 4: Size L is refused for a planned build (Wave:): split the brief" in out.stdout


def sized_root(tmp_path: Path, setting: str) -> Path:
    root = requirements(tmp_path, "REQ-001")
    (root / "agk.toml").write_text(f"[flow]\n{setting}\n", encoding="utf-8")
    return root


def test_rule4_the_flow_setting_changes_the_limits(tmp_path):
    """REQ-039: brief #1121 answer 4 (f), `[flow] brief_code_paths`."""
    root = sized_root(tmp_path, "brief_code_paths = { S = 1, M = 8 }")
    out = check(tmp_path, sized("S", 2), "--root", str(root))
    assert "rule 4: Size S allows at most 1 code paths, Touches names 2" in out.stdout
    assert check(tmp_path, sized("M", 8), "--root", str(root)).stdout.strip() == "ok brief"


@pytest.mark.parametrize(
    "setting",
    [
        'brief_code_paths = "many"',
        "brief_code_paths = { S = 0, M = 6 }",
        "brief_code_paths = { S = 3, M = true }",
        "brief_code_paths = { S = 3, M = 6, L = 9 }",
        'brief_code_paths = { S = "3", M = 6 }',
    ],
)
def test_rule4_an_invalid_setting_is_refused_naming_it_and_never_its_value(tmp_path, setting):
    """REQ-039: brief #1121 answer 4 (f) (principle 8)."""
    out = check(tmp_path, sized("S", 1), "--root", str(sized_root(tmp_path, setting)))
    assert out.returncode == 1
    assert "setting: flow.brief_code_paths" in out.stdout
    assert "many" not in out.stdout


def test_rule4_the_size_limits_are_in_brief_problems_for_next_and_plan():
    """REQ-039: brief #1121 answer 2 (`check_brief.py`, `next` and `plan` share the function)."""
    sys.path.insert(0, str(SCRIPTS))
    import session

    assert session.brief_problems(sized("S", 3)) == []
    assert session.brief_problems(sized("S", 4)) == [
        "rule 4: Size S allows at most 3 code paths, Touches names 4: split the brief or raise Size"
    ]
    assert session.brief_problems(sized("S", 4), {"S": 4, "M": 6}) == []


def test_req037_a_brief_naming_the_import_phrase_is_warned_never_failed(tmp_path):
    """REQ-037: brief #1972 answer 4 (ADR-0824: one warning before `ok brief`, none without it)."""
    body = GOOD.replace("Size: M\n", "Size: M\nPlan: standard library and `common.py` only.\n")
    out = check(tmp_path, body)
    assert out.returncode == 0
    assert out.stdout.splitlines() == [
        'warning: ADR-0824: "standard library and common.py only" is read as the kit\'s offline '
        "set; name in Questions any other kit module the build needs",
        "ok brief",
    ]
    assert check(tmp_path, GOOD).stdout.strip() == "ok brief"


# --- brief #2002 (ADR-0828): the Spec fit line of each Approved spec a brief names ----------------

sys.path.insert(0, str(SCRIPTS))

import check_brief  # noqa: E402

FIT_SPEC = (
    "# SPEC-0901: a test spec\n\n- Status: {status}\n- Date: 2026-11-01\n- Requirements: {req}\n\n"
    "## Rules\n\n1. **One.** A thing.\n2. **Two.** Send in batches of at most five.\n"
    "7a. **Lettered.** A lettered rule.\n\n## Tests\n\n1. Not a rule.\n"
)
FIT_ITEMS = '> 1. **SPEC-0901 rule 2.** Append "x" (amendment 254).\n> Class: behaviour\n'


def fit_root(tmp_path: Path, status: str = "Approved", req: str = "REQ-001", day: str = "") -> Path:
    root = requirements(tmp_path, "REQ-001", "REQ-002")
    (root / "docs" / "specs").mkdir()
    spec = FIT_SPEC.format(status=status, req=req)
    (root / "docs" / "specs" / "0901-a-test-spec.md").write_text(spec, encoding="utf-8")
    draft = FIT_SPEC.format(status="Draft", req="REQ-009").replace("0901", "0902")
    (root / "docs" / "specs" / "0902-a-draft-spec.md").write_text(draft, encoding="utf-8")
    flow = f'[flow]\nbrief_study_fails_from = "{day}"\n' if day else ""
    (root / "agk.toml").write_text(flow, encoding="utf-8")
    return root


def fit(body: str, root: Path, filed: str | None = None):
    return check_brief.spec_fit_problems(body, root, "2026-11-26", filed)


def fitted(line: str, extra: str = "") -> str:
    return GOOD.replace("2. two\n", "2. two, by SPEC-0901 rule 2\n") + line + extra


def test_req066_2002_a_fitted_spec_without_a_line_warns_before_the_day_and_fails_after(tmp_path):
    """REQ-066: answers 2 and 9: an Approved spec whose Requirements names an Advances id needs
    the line; a warning with no day, a failure for a brief filed on or after it."""
    want = ["spec fit: SPEC-0901 has no Spec fit: line (setting: Spec fit:)"]
    assert fit(GOOD, fit_root(tmp_path)) == ([], want)
    late = fit_root(tmp_path / "late", day="2026-11-20")
    assert fit(GOOD, late, "2026-11-25T10:00:00Z") == (want, [])
    assert fit(GOOD, late, "2026-11-19T10:00:00Z") == ([], want)


def test_req066_2002_a_line_naming_each_named_rule_passes_and_a_left_out_rule_is_named(tmp_path):
    """REQ-066: answer 1: every rule the brief names is in the line; the text is never printed."""
    root = fit_root(tmp_path)
    assert fit(fitted("Spec fit: SPEC-0901 rules 1 and 2 within\n"), root) == ([], [])
    body = fitted("Spec fit: SPEC-0901 rule 1 within\n")
    assert fit(body, root)[1][0] == (
        "spec fit: the Spec fit: line of SPEC-0901 leaves out rule 2 (setting: Spec fit:)"
    )


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("Spec fit: SPEC-0901 rule 9 within\n", "names rule 9, which SPEC-0901 does not have"),
        ("Spec fit: SPEC-0902 rule 1 within\n", "names SPEC-0902, which is not Approved"),
        ("Spec fit: SPEC-0901 rule 2 fits nicely\n", "a Spec fit: line is malformed"),
        ("Spec fit: SPEC-0901 rule 2 within\nSpec fit: SPEC-0901 rule 2 within\n", "two Spec fit:"),
        ("Spec fit: SPEC-0901 rule 2 within; rule 2 change by amendment 254\n" + FIT_ITEMS,
         "states rule 2 both within and changed"),
        ("Spec fit: SPEC-0901 rule 2 change by amendment 254\n" + FIT_ITEMS,
         "changes by amendment 254, which Reserved: does not name"),
        ("Reserved: amendment 254\nSpec fit: SPEC-0901 rule 2 change by amendment 254\n",
         "changes by amendment 254 with no quoted items under the line"),
        ("Reserved: amendment 254\nSpec fit: SPEC-0901 rule 2 change by amendment 254\n"
         "> 1. **SPEC-0901 rule 2.** Append \"x\".\n", "item 1: no Class line"),
    ],
)  # fmt: skip
def test_req066_2002_each_bad_line_fails_on_any_day(tmp_path, line, message):
    """REQ-066: answer 2 and edge cases 10: a wrong line fails whatever the day, naming the line,
    the spec and the rule, never the brief's text."""
    fails, _ = fit(fitted(line), fit_root(tmp_path))
    assert any(message in f for f in fails), fails
    assert all("A team can run" not in f for f in fails)


def test_req066_2002_a_change_with_its_reserved_amendment_and_items_passes(tmp_path):
    """REQ-066: answer 1: the quoted items are read and classed as a file's (ADR-0813)."""
    body = fitted(
        "Reserved: amendments 254 and 255\n"
        "Spec fit: SPEC-0901 rule 1 within; rule 2 change by amendment 254\n" + FIT_ITEMS
    )
    assert fit(body, fit_root(tmp_path)) == ([], [])
    assert check_brief.fit_changes(body) == [254]


def test_req066_2002_a_number_limit_stated_otherwise_warns_modelled_on_1954(tmp_path):
    """REQ-066: answer 2's one heuristic: #1954's "at most 20" against a rule's "at most five"
    warns naming the rule while the line leaves it out, and never fails."""
    body = GOOD.replace("2. two\n", "2. two: send at most 20 questions\n")
    body += "Spec fit: SPEC-0901 rule 1 within\n"
    assert fit(body, fit_root(tmp_path)) == ([], [
        "spec fit: SPEC-0901 rule 2 states a number limit the brief states with another number;"
        " name rule 2 in the Spec fit: line (setting: Spec fit:)"
    ])  # fmt: skip
    same = (
        GOOD.replace("2. two\n", "2. two: send at most five\n")
        + "Spec fit: SPEC-0901 rule 1 within\n"
    )
    assert fit(same, fit_root(tmp_path / "b")) == ([], [])


def test_req066_2002_a_draft_spec_or_a_spec_named_only_in_prior_needs_no_line(tmp_path):
    """REQ-066: edge cases 10: a Draft spec named in the Answers, and a spec named only in Prior
    or Evidence, need no line; a lettered rule counts as written."""
    root = fit_root(tmp_path, req="REQ-077")
    draft = GOOD.replace("2. two\n", "2. two, by SPEC-0902 rule 1\n")
    assert fit(draft, root) == ([], [])
    assert fit(GOOD + "Prior: SPEC-0901 rule 2\n", root) == ([], [])
    named = GOOD.replace("2. two\n", "2. two, by SPEC-0901 rule 7a\n")
    assert fit(named, root)[1] == ["spec fit: SPEC-0901 has no Spec fit: line (setting: Spec fit:)"]
    assert fit(named + "Spec fit: SPEC-0901 rule 7a within\n", root) == ([], [])


def test_req066_2002_a_priority_0_brief_is_held_only_for_a_change(tmp_path):
    """REQ-066: answer 9: the router's red-branch brief needs no line, but a change still fails."""
    root = fit_root(tmp_path, day="2026-11-20")
    zero = GOOD.replace("Priority: 1", "Priority: 0")
    assert fit(zero, root, "2026-11-25T10:00:00Z") == ([], [])
    bad = zero + "Spec fit: SPEC-0901 rule 2 change by amendment 254\n" + FIT_ITEMS
    assert fit(bad, root)[0]


def test_req066_2002_brief_result_runs_the_spec_fit_after_the_study(tmp_path):
    """REQ-066: answer 12: the one reading every writer reaches carries the check, and no root
    leaves it out (a kit brief triaged in a project)."""
    root = fit_root(tmp_path)
    out = check(tmp_path, GOOD, "--root", str(root))
    assert out.returncode == 0
    assert "warning: spec fit: SPEC-0901 has no Spec fit: line (setting: Spec fit:)" in out.stdout
    bad = GOOD + STUDY + "Spec fit: SPEC-0901 rule 2 change by amendment 254\n" + FIT_ITEMS
    failed = check(tmp_path, bad, "--root", str(root))
    assert failed.returncode == 1 and "which Reserved: does not name" in failed.stdout
    assert "spec fit" not in check(tmp_path, bad).stdout
