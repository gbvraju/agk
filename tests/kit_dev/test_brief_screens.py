"""Kit-only tests of the `Screens:` line of a UI brief (SPEC-0037 rule 10, build (g); brief #460).

A brief is a UI brief when a glob of its `Touches:` line and a glob of `ui_paths` in the `[design]`
table of `agk.toml` meet. `check_brief.py FILE --root DIR` then needs exactly one line
`Screens: v<n> <screen>/<state>, ...` whose version has a `design` row in
`docs/design/signoffs.md` and whose screens and states are pages `<screen>--<state>.html` of the
version's frozen folder; `*` stands for every state of the screen. The conductor's guard files no
UI brief without the line, and doctor reports the setting absent when a prototype exists.
Invented projects in `tmp_path` only; files only, no network and no model.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import check_brief  # noqa: E402
import doctor  # noqa: E402

CHECK = KIT_ROOT / "scripts" / "agk" / "check_brief.py"
HOOK = KIT_ROOT / ".claude" / "hooks" / "conductor_guard.py"
DOCTOR = KIT_ROOT / "scripts" / "agk" / "doctor.py"
DOCTOR_FIXTURES = KIT_ROOT / "tests" / "kit" / "fixtures" / "doctor" / "ok"
HEAD = "0123456789abcdef0123456789abcdef01234567"
DIGEST = "ab" * 32
LINK = "https://example.com/owner/project/pull/7#issuecomment-1"
REQUIREMENTS = "# Requirements\n\n### REQ-001 — A reader keeps a list of books\n\n- Status: planned\n"
PAGES = ("index.html", "books--default.html", "books--empty.html", "books--error.html",
         "account--default.html")  # fmt: skip
SECRET_SCREEN = "zz-hidden-screen"  # an invented value that a refusal must never print


def brief(touches: str, screens: str | None = None) -> str:
    lines = [
        "Brief: a reader sees the list",
        "",
        'Sentence: "A reader sees the list of books."',
        "",
        "Answers:",
        "1. The list shows the books.",
        "",
        "Advances: REQ-001",
        f"Touches: {touches}",
    ]
    if screens is not None:
        lines.append(screens)
    lines += ["Priority: 2", "Size: S", ""]
    return "\n".join(lines)


def project(tmp_path: Path, ui_paths: list[str] | None = ("web/**",), signed=("v1",)) -> Path:
    root = tmp_path / "project"
    (root / "docs" / "design" / "prototype" / "v1").mkdir(parents=True)
    (root / "docs" / "requirements.md").write_text(REQUIREMENTS, encoding="utf-8")
    toml = 'version = "0.0.0"\n'
    if ui_paths is not None:
        toml += "[design]\nui_paths = " + json.dumps(list(ui_paths)) + "\n"
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    for name in PAGES:
        (root / "docs" / "design" / "prototype" / "v1" / name).write_text(
            "<!doctype html>\n", encoding="utf-8"
        )
    rows = "".join(f"| design | {v} | {DIGEST} | {HEAD} | 2026-11-01 | {LINK} |\n" for v in signed)
    (root / "docs" / "design" / "signoffs.md").write_text(
        "# Design sign-offs\n\n| kind | version | digest | head | date | comment |\n"
        f"|---|---|---|---|---|---|\n| inventory | - | {DIGEST} | {HEAD} | 2026-10-31 | {LINK} |\n"
        + rows,
        encoding="utf-8",
    )
    return root


def run_check(root: Path, body: str):
    path = root.parent / "brief.md"
    path.write_text(body, encoding="utf-8")
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(CHECK), str(path), "--root", str(root)],
        capture_output=True,
        text=True,
    )


# --- answers 2 and 3: the check ------------------------------------------------------------------


def test_ac5_a_ui_brief_with_a_valid_screens_line_passes(tmp_path):
    """REQ-044 AC5: SPEC-0037 rule 10 (a signed-off version, its screens and states)."""
    root = project(tmp_path)
    out = run_check(root, brief("web/app/list.js", "Screens: v1 books/empty, account/default"))
    assert out.returncode == 0 and out.stdout.strip() == "ok brief", out.stdout + out.stderr


@pytest.mark.parametrize(
    ("screens", "message"),
    [
        (None, "rule 10: a brief that touches ui_paths has no Screens line"),
        ("Screens: v2 books/empty", "rule 10: the Screens version is not signed off"),
        (f"Screens: v1 {SECRET_SCREEN}/default", "rule 10: a Screens screen or state is not in"),
        ("Screens: v1 books/zz-hidden-state", "rule 10: a Screens screen or state is not in"),
        (f"Screens: v1 {SECRET_SCREEN}/*", "rule 10: a Screens screen or state is not in"),
    ],
)
def test_ac5_a_ui_brief_without_a_sound_line_is_refused_naming_the_rule(tmp_path, screens, message):
    """REQ-044 AC5: SPEC-0037 rule 10 (refused naming the rule, never a value)."""
    root = project(tmp_path)
    out = run_check(root, brief("web/**", screens))
    assert out.returncode == 1, out.stdout
    text = out.stdout + out.stderr
    assert message in text
    for value in (SECRET_SCREEN, "zz-hidden-state", "v2", "web/"):
        assert value not in text


def test_ac5_a_version_that_exists_but_is_not_signed_off_is_refused(tmp_path):
    """REQ-044 AC5: SPEC-0037 rule 10 (only a `design` row of that version counts)."""
    root = project(tmp_path, signed=())
    out = run_check(root, brief("web/**", "Screens: v1 books/empty"))
    assert out.returncode == 1
    assert "rule 10: the Screens version is not signed off in docs/design/signoffs.md" in out.stdout


@pytest.mark.parametrize(
    "line",
    [
        "Screens: books/empty",
        "Screens: v1",
        "Screens: v1 books",
        "Screens: v1 books/empty,, account/default",
        "Screens: version1 books/empty",
    ],
)
def test_ac5_a_screens_line_of_another_shape_is_refused(tmp_path, line):
    """REQ-044 AC5: SPEC-0037 rule 10 (the line's shape; Decisions taken of brief #460)."""
    root = project(tmp_path)
    out = run_check(root, brief("web/**", line))
    assert out.returncode == 1 and "rule 10: " in out.stdout


def test_ac5_two_screens_lines_are_refused(tmp_path):
    """REQ-044 AC5: SPEC-0037 rule 10 (exactly one line)."""
    root = project(tmp_path)
    body = brief("web/**", "Screens: v1 books/empty\nScreens: v1 account/default")
    out = run_check(root, body)
    assert out.returncode == 1 and "rule 10: " in out.stdout


def test_ac5_a_star_expands_to_every_state_of_the_screen_in_the_version(tmp_path):
    """REQ-044 AC5: SPEC-0037 rule 10 (`*` is every state of the screen)."""
    root = project(tmp_path)
    found = check_brief.screens_named("Screens: v1 books/*, account/default", root)
    assert found == [
        ("books", "default"),
        ("books", "empty"),
        ("books", "error"),
        ("account", "default"),
    ]
    assert run_check(root, brief("web/**", "Screens: v1 books/*")).returncode == 0


@pytest.mark.parametrize(
    ("touches", "ui", "is_ui"),
    [
        ("web/app/list.js", ["web/**"], True),  # the path matches the glob
        ("web/**", ["web/app/*.js"], True),  # the literal parts meet
        ("src/*.css", ["src/theme.css"], True),  # the glob matches the path
        ("docs/**, web/x.js", ["web/*.js"], True),  # one glob of several
        ("scripts/agk/check.py", ["web/**"], False),
        ("docs/guides/*.md", ["web/**", "app/ui/**"], False),
    ],
)
def test_ac5_a_brief_is_a_ui_brief_only_when_a_touches_glob_meets_a_ui_glob(touches, ui, is_ui):
    """REQ-044 AC5: SPEC-0037 rule 10, Q-S0037-8 (the project's ui_paths decides)."""
    assert check_brief.touches_ui(touches_list(touches), ui) is is_ui


def touches_list(text: str) -> list[str]:
    return [g.strip() for g in text.split(",")]


def test_ac5_a_brief_whose_touches_meet_no_ui_glob_needs_no_screens_line(tmp_path):
    """REQ-044 AC5: SPEC-0037 rule 10 (not a UI brief)."""
    root = project(tmp_path)
    out = run_check(root, brief("scripts/agk/check.py, docs/**"))
    assert out.returncode == 0, out.stdout


@pytest.mark.parametrize("ui_paths", [None, []])
def test_ac5_a_project_without_ui_paths_has_no_ui_briefs(tmp_path, ui_paths):
    """REQ-044 AC5: SPEC-0037 rule 10 (no setting, no UI briefs)."""
    root = project(tmp_path, ui_paths=ui_paths)
    assert run_check(root, brief("web/**, **")).returncode == 0


def test_ac5_a_project_without_agk_toml_has_no_ui_briefs(tmp_path):
    """REQ-044 AC5: SPEC-0037 rule 10 (no `[design]` table at all)."""
    root = project(tmp_path)
    (root / "agk.toml").unlink()
    assert run_check(root, brief("web/**")).returncode == 0


@pytest.mark.parametrize("value", ['"web/**"', "[1, 2]", '["web/**", 3]'])
def test_ac5_a_malformed_ui_paths_is_refused_naming_the_setting(tmp_path, value):
    """REQ-044 AC5: SPEC-0037 rule 10 (principle 8: the setting, never its value)."""
    root = project(tmp_path)
    (root / "agk.toml").write_text(f"[design]\nui_paths = {value}\n", encoding="utf-8")
    out = run_check(root, brief("web/**", "Screens: v1 books/empty"))
    assert out.returncode == 1 and "ui_paths" in out.stdout and "web/" not in out.stdout


def test_ac5_without_root_the_line_is_not_read(tmp_path):
    """REQ-044 AC5: brief #460 out of scope (`brief_problems` does not change)."""
    path = tmp_path / "brief.md"
    path.write_text(brief("web/**"), encoding="utf-8")
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(CHECK), str(path)], capture_output=True, text=True
    )
    assert out.returncode == 0, out.stdout


# --- the note: the conductor's guard files no UI brief without the line --------------------------


def guard(project_dir: Path, body_file: Path, tmpdir: Path):
    command = (
        "gh api --method POST repos/o/r/issues -f 'title=Brief: x y'"
        f" -f 'labels[]=agk-brief' -F body=@{body_file}"
    )
    env = {"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(project_dir), "TMPDIR": str(tmpdir)}
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK)], input=json.dumps(payload), capture_output=True, text=True,
        env=env,
    )  # fmt: skip
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)["hookSpecificOutput"] if out.stdout.strip() else None


def test_ac5_the_conductor_guard_files_no_ui_brief_without_the_screens_line(tmp_path):
    """REQ-044 AC5: brief #460 note (`brief_checked` calls `screens_problems`)."""
    root = project(tmp_path)
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/o/r.git\n', encoding="utf-8"
    )
    systmp = tmp_path / "systmp"
    (systmp / "agk-conductor-1").mkdir(parents=True)
    body = systmp / "agk-conductor-1" / "brief.md"
    body.write_text(brief("web/**"), encoding="utf-8")
    denied = guard(root, body, systmp)
    assert denied is not None and denied["permissionDecision"] == "deny"
    body.write_text(brief("web/**", "Screens: v1 books/*"), encoding="utf-8")
    assert guard(root, body, systmp) is None


# --- answer 4: doctor ----------------------------------------------------------------------------


def test_ac5_doctor_has_one_information_entry_for_the_setting():
    """REQ-044 AC5: brief #460 answer 4 (one entry in CHECKS, never a failure)."""
    ids = list(doctor.CHECKS)
    assert ids.count("design-ui-paths") == 1
    assert ids.index("design-ui-paths") < ids.index("engines-keys")


@pytest.mark.parametrize(
    ("ui_paths", "prototype", "word"),
    [(None, True, "absent"), ([], True, "absent"), (["web/**"], True, "set"),
     (None, False, "not needed")],
)  # fmt: skip
def test_ac5_doctor_reports_ui_paths_absent_when_a_prototype_exists(
    tmp_path, ui_paths, prototype, word
):
    """REQ-044 AC5: SPEC-0037 rule 10 (doctor reports the setting; information only)."""
    root = tmp_path / "p"
    root.mkdir()
    if prototype:
        (root / "docs" / "design" / "prototype").mkdir(parents=True)
    config = {} if ui_paths is None else {"design": {"ui_paths": ui_paths}}
    result = doctor.design_ui_result(root, config)
    assert result.status == "ok"
    assert result.message.startswith(word)


def run_doctor(tmp_path: Path, extra_toml: str) -> dict:
    root, api, kit = tmp_path / "root", tmp_path / "api", tmp_path / "kit"
    for name, target in (("tree", root), ("api", api), ("kit", kit)):
        shutil.copytree(DOCTOR_FIXTURES / name, target)
    (root / "docs" / "design" / "prototype" / "v1").mkdir(parents=True)
    toml = (root / "agk.toml").read_text(encoding="utf-8")
    (root / "agk.toml").write_text(toml + extra_toml, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607 - fixed argument list, no shell
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), "symbolic-ref", "refs/remotes/origin/HEAD",
         "refs/remotes/origin/main"],
        check=True,
    )  # fmt: skip
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(DOCTOR), "--api-dir", str(api), "--repo", "example-owner/example-repo",
         "--kit-root", str(kit), "--json", str(root)],
        capture_output=True, text=True, env=env,
    )  # fmt: skip
    return {c["id"]: c for c in json.loads(out.stdout)["checks"]}


@pytest.mark.parametrize(
    ("extra", "word"), [("", "absent"), ('\n[design]\nui_paths = ["web/**"]\n', "set")]
)
def test_ac5_the_doctor_line_with_and_without_the_setting(tmp_path, extra, word):
    """REQ-044 AC5: brief #460 answer 4 (the `design-ui-paths` line of a full run)."""
    entry = run_doctor(tmp_path, extra)["design-ui-paths"]
    assert entry["status"] == "ok"
    assert word in entry["message"]
    assert "web/" not in entry["message"]
