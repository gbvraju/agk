"""A project brief names what already exists (brief #2065, ADR-0857; REQ-037).

Answer 1: without `kit/agk-kit.mk` a brief is held to the same `Existing:` line, warned before the
project's own `[flow] brief_study_fails_from` and failed from it. Answer 2: `project_source` is the
project's own code. Answer 3: `code_matches` searches it, the kit's copy, the reference guide, the
packs in use and the build files' dependencies, warning only. Each case is a stub root in
`tmp_path` with no kit marker, the day fixed by the test. Invented data only (example.com).
"""

from __future__ import annotations

import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import brief_study  # noqa: E402
import check_brief  # noqa: E402
import kit_root  # noqa: E402
import packs  # noqa: E402
import steward_owner  # noqa: E402
from test_check_brief_study import EXISTING as STUDIED_EXISTING  # noqa: E402
from test_check_brief_study import STUDIED as WITH_LINE  # noqa: E402
from test_check_brief_study import tree  # noqa: E402

DAY = "2026-12-14"
BEFORE, AFTER = "2026-12-13", "2026-12-15"
STUDIED = WITH_LINE.replace(STUDIED_EXISTING, "", 1)  # the shared brief without its line
REPORT = "site/src/report.ts"
NAMED = STUDIED.replace("1. one\n", "1. one: `weekSection()` builds the week (example.com).\n")
MISSING = "study: the Existing line is missing"
NONE = "Existing: none: `grep -rn weekSection site/` gives 0 matches\n"


def with_line(line: str, body: str = STUDIED) -> str:
    return body.replace("Answers:\n", line + "Answers:\n", 1)


def project(tmp_path: Path, day: str | None = DAY, toml: str = "") -> Path:
    root = tree(tmp_path)
    flow = f'[flow]\nbrief_study_fails_from = "{day}"\n' if day else ""
    (root / "agk.toml").write_text(toml + flow, "utf-8")  # top-level keys first
    (root / "site" / "src").mkdir(parents=True)
    (root / REPORT).write_text(
        "// the week\nconst x = 1;\nexport function weekSection() {\n  return x;\n}\n", "utf-8"
    )
    return root


def result(root: Path, body: str, today: str | None):
    return brief_study.study_result(body, root, today=today, briefs=[])


def existing(lines: list[str]) -> list[str]:
    return [x for x in lines if "Existing" in x]


def test_req037_a_project_brief_without_the_line_warns_then_fails_from_its_own_day(tmp_path):
    """REQ-037: answer 1 (no day: warn; before the day: warn; from it: fail)."""
    for day, today, failed in ((None, AFTER, False), (DAY, BEFORE, False), (DAY, AFTER, True)):
        root = project(tmp_path / str(day) / today, day)
        failures, warnings = result(root, STUDIED, today)
        assert any(x.startswith(MISSING) for x in (failures if failed else warnings))
        assert failed == bool(existing(failures))


def test_req037_the_placeholder_warns_on_any_day_and_a_priority_0_brief_is_not_held(tmp_path):
    """REQ-037: answer 1 (`placeholder_warnings`, `held`)."""
    root = project(tmp_path)
    body = with_line("Existing: none: (verify) for the person to state\n")
    for today in (BEFORE, AFTER):
        failures, warnings = result(root, body, today)
        assert failures == []
        assert "study: the Existing line is the render's placeholder" in warnings
    zero = STUDIED.replace("Priority: 1\n", "Priority: 0\n")
    assert existing(sum(result(root, zero, AFTER), [])) == []


def test_req037_an_item_may_name_a_kit_feature_without_a_line(tmp_path):
    """REQ-037: answer 1 (`Q-P0AP-2`: a kit command in backquotes, no file under the root)."""
    item = "Existing:\n- `session.py watch`: waits for an event; not enough: no week view.\n\n"
    failures, _ = result(project(tmp_path), with_line(item), AFTER)
    assert existing(failures) == []
    bare = "Existing:\n- waits for an event; not enough: no week view.\n\n"
    assert existing(result(project(tmp_path / "bare"), with_line(bare), AFTER)[0])


def source_tree(tmp_path: Path, toml: str = "") -> Path:
    root = project(tmp_path, toml=toml)
    for rel in (
        "src/app.py", "tests/test_app.py", "docs/x.md", "spec/unit/a.ts", "vendor/lib.js",
        "scripts/agk/kitfile.py", ".claude/hooks/h.py", "site/src/report.test.ts", "README.md",
        "config/x.py", ".github/x.py",
    ):  # fmt: skip
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("x = 1\n", "utf-8")
    return root


def test_req037_project_source_is_the_projects_own_code(tmp_path):
    """REQ-037: answer 2 (derived: tests, docs, test_dirs, vendor, kit folders, test files out)."""
    root = source_tree(tmp_path, 'test_dirs = ["tests", "spec"]\n')
    files, unread = brief_study.project_source(root)
    assert files == [REPORT, "src/app.py"] and unread == 0
    root = source_tree(tmp_path / "lint", 'project_lint_paths = ["src/**"]\n')
    assert brief_study.project_source(root)[0] == ["src/app.py"]


def test_req037_a_refused_project_lint_paths_runs_no_search(tmp_path):
    """REQ-037: answer 2 (the refusal names the setting, never the value)."""
    root = project(tmp_path, toml='project_lint_paths = ["/abs"]\n')
    matches, notes = brief_study.project_matches(NAMED, root)
    assert matches == []
    assert notes == ["not run code search: not an accepted value (setting: project_lint_paths)"]


def test_req037_a_function_in_the_projects_source_is_warned_and_naming_it_silences(tmp_path):
    """REQ-037: answer 3 (`declares` for a non-Python file); the Measured line's case."""
    root = project(tmp_path)
    _, warnings = result(root, with_line(NONE, NAMED), BEFORE)
    want = f"study: Existing leaves out {REPORT}:3, which defines weekSection()"
    assert want in warnings
    item = f"Existing:\n- `{REPORT}:3` (`weekSection`): the week; not enough: partial.\n\n"
    _, warnings = result(root, with_line(item, NAMED), BEFORE)
    assert not any("leaves out" in w and "weekSection" in w for w in warnings)


def test_req037_the_check_brief_command_prints_both_warnings(tmp_path):
    """REQ-037: the Measured line (`check_brief.py b.md --root <tree>`), no day set."""
    root = project(tmp_path, None)
    (tmp_path / "b.md").write_text(NAMED, encoding="utf-8")
    run = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "check_brief.py"), str(tmp_path / "b.md"), "--root",
         str(root)],
        capture_output=True, text=True, check=False, cwd=tmp_path,
    )  # fmt: skip
    out = run.stdout + run.stderr
    assert "warning: study: the Existing line is missing" in out
    assert f"study: Existing leaves out {REPORT}:3, which defines weekSection()" in out


def test_req037_a_dependency_and_a_used_pack_are_part_matches(tmp_path, monkeypatch):
    """REQ-037: answer 3 (parts: `pins.declared` names, `packs.used` ids)."""
    root = project(tmp_path)
    (root / "package.json").write_text(
        '{\n  "name": "site",\n  "dependencies": {\n    "left-pad": "1.3.0"\n  }\n}\n', "utf-8"
    )
    monkeypatch.setattr(packs, "used", lambda _root: [("node-web", root / "config/packs/x")])
    body = STUDIED.replace("1. one\n", "1. one uses `left-pad` and `node-web`.\n")
    matches, _ = brief_study.project_matches(body, root)
    assert ("package.json", 4, "left-pad", "declares") in matches
    assert any(m[2:] == ("node-web", "declares") for m in matches)


def test_req037_a_kit_command_in_the_reference_guide_is_documented(tmp_path):
    """REQ-037: answer 3 (the kit's `docs/guides/reference.md` through `kit_file`)."""
    root = project(tmp_path)
    (root / "docs" / "guides").mkdir(parents=True)
    (root / "docs" / "guides" / "reference.md").write_text(
        "# Reference\n\n`report.py week`: prints the week.\n", "utf-8"
    )
    body = with_line(NONE, STUDIED.replace("1. one\n", "1. one runs `report.py week`.\n"))
    _, warnings = result(root, body, BEFORE)
    want = "study: Existing leaves out docs/guides/reference.md:3, which documents report.py week"
    assert want in warnings


def test_req037_a_plugin_tree_without_its_plugin_leaves_the_kit_layer_out(tmp_path, monkeypatch):
    """REQ-037: answer 3 (no kit copy: one `not run` line, no warning)."""
    root = project(tmp_path, toml='[kit]\nlayout = "plugin"\n')

    def refuse(*_args, **_kwargs):
        raise kit_root.Refused("kit_root: no plugin root (setting: CLAUDE_PLUGIN_ROOT)")

    monkeypatch.setattr(kit_root, "plugin_root", refuse)
    body = STUDIED.replace("1. one\n", "1. one runs `tool.main()`.\n")
    matches, notes = brief_study.project_matches(body, root)
    assert matches == []
    assert "not run kit search: no kit copy (setting: CLAUDE_PLUGIN_ROOT)" in notes


def test_req037_2001_source_files_read_2000_and_count_the_rest(tmp_path):
    """REQ-037: answer 2 (`SOURCE_FILES`)."""
    root = project(tmp_path)
    many = root / "src"
    many.mkdir()
    for n in range(2000):
        (many / f"m{n:04}.py").write_text("x = 1\n", "utf-8")
    files, unread = brief_study.project_source(root)
    assert len(files) == brief_study.SOURCE_FILES == 2000 and unread == 1
    assert "code search: 1 files not read" in brief_study.project_matches(NAMED, root)[1]


def test_req037_eleven_matches_give_ten_warnings_and_one_count_line(tmp_path):
    """REQ-037: answer 3 (all classes share `CODE_WARNINGS`)."""
    root = project(tmp_path)
    names = [f"stub{n}" for n in range(11)]
    (root / "site" / "src" / "stubs.ts").write_text(
        "".join(f"export const {n} = 1;\n" for n in names), "utf-8"
    )
    body = with_line(
        NONE, STUDIED.replace("1. one\n", "1. " + " ".join(f"`{n}()`" for n in names) + "\n")
    )
    _, warnings = result(root, body, BEFORE)
    assert len([w for w in warnings if "leaves out" in w]) == brief_study.CODE_WARNINGS
    assert any("more code matches not warned" in w for w in warnings)


def test_req037_the_project_search_makes_no_network_call(tmp_path, monkeypatch):
    """REQ-037: answer 3 (files only)."""

    def refuse(*_args, **_kwargs):
        raise AssertionError("no network")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    assert brief_study.code_matches(NAMED, project(tmp_path))


def test_req037_every_writer_reports_the_same_existing_problem_in_a_project(tmp_path, monkeypatch):
    """REQ-037: answer 9 (the check, the steward's refusal and the plan's shape agree)."""
    root = project(tmp_path)
    (root / "config").mkdir()
    (root / "config" / "neutrality.txt").write_text("", "utf-8")
    body = with_line("Existing:\n- `site/src/gone.ts:1`; not enough: gone.\n\n")
    problem = existing(brief_study.study_failures(body, root, None, AFTER))
    assert len(problem) == 1 and "site/src/" in problem[0] and "gone" not in problem[0]
    failures, _ = check_brief.brief_result(body, root, today=AFTER)
    assert existing(failures) == problem
    monkeypatch.setattr(check_brief, "utc_day", lambda: AFTER)
    assert problem[0] in (steward_owner.brief_refusal(root, body, None) or "")


@pytest.mark.parametrize("ext", sorted({".py", ".ts", ".go", ".rs", ".java"}))
def test_req037_declares_reads_a_declaration_in_each_language(ext):
    """REQ-037: answer 3 (`declares` beside `defines`)."""
    text = {
        ".py": "def week_section():\n",
        ".ts": "export async function week_section() {}\n",
        ".go": "func week_section() {}\n",
        ".rs": "pub fn week_section() {}\n",
        ".java": "class week_section {}\n",
    }[ext]
    assert brief_study.declare_line("// head\n" + text, "week_section", ext) == 2
