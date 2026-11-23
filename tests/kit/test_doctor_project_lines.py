"""Brief #269 (REQ-039, ADR-0164): the doctor compares only the kit's block of `.gitignore`.

Lines outside the block belong to the project: never a difference, reported once as
"project lines kept: n". The ignore lines are invented.
"""

from __future__ import annotations

import json
from pathlib import Path

from test_doctor import checks_of, doctor, prepare

BLOCK = "# >>> agk\n*.pyc\n# <<< agk\n"


def init_target(tmp_path: Path, gitignore: str, extendable: bool = True) -> dict[str, Path]:
    dirs = prepare("ok", tmp_path)
    kit, root = dirs["kit"], dirs["root"]
    manifest: dict = {
        "kit_version": "9.9.9",
        "verbatim": [".gitignore", "a.txt"],
        "templates": {},
        "rendered": [],
        "adopt": {
            "skip": [],
            "blocks": {".gitignore": "hash"},
            "block_sources": {".gitignore": "kit/templates/gitignore"},
            "templates": {},
        },
    }
    if extendable:
        manifest["extendable"] = {".gitignore": "hash"}
    (kit / "kit" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (kit / "kit" / "templates").mkdir(parents=True, exist_ok=True)
    (kit / "kit" / "templates" / "gitignore").write_text("*.pyc\n", encoding="utf-8")
    (kit / ".gitignore").write_text(BLOCK, encoding="utf-8")
    (kit / "a.txt").write_text("a\n", encoding="utf-8")
    (root / ".gitignore").write_text(gitignore, encoding="utf-8")
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    (root / "agk.toml").write_text('mode = "init"\nversion = "9.9.9"\n', encoding="utf-8")
    return dirs


def report_of(dirs: dict[str, Path]) -> dict[str, dict]:
    proc = doctor(
        "--api-dir", str(dirs["api"]), "--kit-root", str(dirs["kit"]), "--json", str(dirs["root"])
    )
    return checks_of(proc.stdout)


def test_init_project_lines_outside_the_block_are_not_a_difference(tmp_path):
    """REQ-039: brief #269 answer 2."""
    report = report_of(init_target(tmp_path, "# mine\n" + BLOCK + "private-src/\n"))
    assert report["vendored-differs"]["status"] == "ok"
    assert report["vendored-differs"]["message"].endswith(" (.gitignore: project lines kept: 2)")
    assert report["vendored-missing"]["status"] == "ok"


def test_init_the_kit_file_alone_reports_no_project_lines(tmp_path):
    """REQ-039: brief #269 answer 2 (nothing to report when there is no project line)."""
    report = report_of(init_target(tmp_path, BLOCK))
    assert report["vendored-differs"]["status"] == "ok"
    assert "project lines" not in report["vendored-differs"].get("message", "")


def test_init_edited_block_missing_and_broken_markers_differ(tmp_path):
    """REQ-039: brief #269 answers 2 and 3 (a file without markers waits for the upgrade)."""
    for i, text in enumerate(
        [
            "# >>> agk\n*.pyc\nprivate-src/\n# <<< agk\n",
            "*.pyc\nprivate-src/\n",
            "*.pyc\n",
            "# >>> agk\n*.pyc\n",
            BLOCK * 2,
        ]
    ):
        report = report_of(init_target(tmp_path / str(i), text))
        assert report["vendored-differs"]["status"] == "fail", text
        assert ".gitignore" in report["vendored-differs"]["message"], text


def test_init_without_the_extendable_key_compares_the_whole_file(tmp_path):
    """REQ-039: brief #269 answer 4 (only a file the manifest names is extendable)."""
    report = report_of(init_target(tmp_path, BLOCK + "private-src/\n", extendable=False))
    assert report["vendored-differs"]["status"] == "fail"
    report = report_of(init_target(tmp_path / "same", BLOCK, extendable=False))
    assert report["vendored-differs"]["status"] == "ok"


# Brief #1798 answer 2 (amendment 186 build (m)): the whole-tests count, a bad entry by its place.
import doctor as doctor_script  # noqa: E402


def whole_tree(tmp_path: Path, value: str) -> Path:
    root = tmp_path / "w"
    (root / "tests").mkdir(parents=True)
    for name in ("test_a.py", "test_b.py"):
        (root / "tests" / name).write_text("def test_x():\n    assert True\n", encoding="utf-8")
    (root / "agk.toml").write_text(f"[testing]\nwhole_tests = {value}\n", encoding="utf-8")
    return root


def test_doctor_counts_the_whole_tests(tmp_path):
    """REQ-062: brief #1798 answer 2."""
    root = whole_tree(tmp_path, '["tests/test_a.py", "tests/test_b.py"]')
    assert doctor_script.whole_lines(root) == ["tests: whole tests 2"]


def test_doctor_refuses_a_bad_whole_test_by_its_place_never_its_value(tmp_path):
    """REQ-062: brief #1798 answer 2 (each refused shape of amendment 186 rule 6a)."""
    for i, bad in enumerate(
        ["tests/nope_9.py", "tests/*.py", "/tests/abs_9.py", "../up_9.py", "tests\\\\bs_9.py", "7"]
    ):
        value = f'["tests/test_a.py", "{bad}"]' if bad != "7" else '["tests/test_a.py", 7]'
        lines = doctor_script.whole_lines(whole_tree(tmp_path / str(i), value))
        assert lines == [
            "tests: whole tests refused: entry 2 is not a test file of the repository"
            " (setting: testing.whole_tests)"
        ], bad
        assert "9" not in lines[0], bad


def test_doctor_refuses_a_whole_tests_that_is_not_a_list(tmp_path):
    """REQ-062: brief #1798 answer 2 (not a list, or empty)."""
    for i, value in enumerate(['"tests/test_a.py"', "[]"]):
        assert doctor_script.whole_lines(whole_tree(tmp_path / str(i), value)) == [
            "tests: whole tests refused: not a non-empty list (setting: testing.whole_tests)"
        ]


def test_doctor_prints_nothing_without_a_list(tmp_path):
    """REQ-062: brief #1798 answer 7 (a project with no list)."""
    root = tmp_path / "none"
    root.mkdir(parents=True)
    (root / "agk.toml").write_text('[testing]\nprofile = "fast"\n', encoding="utf-8")
    assert doctor_script.whole_lines(root) == []
    (root / "agk.toml").write_text('mode = "init"\n', encoding="utf-8")
    assert doctor_script.whole_lines(root) == []


def test_doctor_prints_the_count_in_its_report(tmp_path):
    """REQ-062: brief #1798 answer 2 (the line is wired into the text report)."""
    dirs = init_target(tmp_path, BLOCK)
    root = dirs["root"]
    (root / "tests").mkdir(exist_ok=True)
    (root / "tests" / "test_w.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    toml = 'mode = "init"\nversion = "9.9.9"\n[testing]\nwhole_tests = ["tests/test_w.py"]\n'
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    proc = doctor("--api-dir", str(dirs["api"]), "--kit-root", str(dirs["kit"]), str(root))
    assert "tests: whole tests 1" in proc.stdout, proc.stdout


# Brief #1812 (ADR-0755): doctor prints the retired key's line in its report.
RETIRED = "deprecated: testing.every_script_tests (ADR-0755)"


def test_doctor_prints_the_retired_key_line_in_its_report(tmp_path):
    """REQ-062: brief #1812 answer 3 (doctor's line when the key is set, none without)."""
    dirs = init_target(tmp_path, BLOCK)
    root = dirs["root"]
    (root / "tests").mkdir(exist_ok=True)
    (root / "tests" / "test_w.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    args = ("--api-dir", str(dirs["api"]), "--kit-root", str(dirs["kit"]), str(root))
    toml = 'mode = "init"\nversion = "9.9.9"\n[testing]\n'
    every = 'every_script_tests = ["tests/test_w.py"]\n'
    (root / "agk.toml").write_text(toml + every, encoding="utf-8")
    assert doctor(*args).stdout.count(RETIRED) == 1
    (root / "agk.toml").write_text(toml + 'profile = "fast"\n', encoding="utf-8")
    assert RETIRED not in doctor(*args).stdout


# Brief #1838 answer 3 (ADR-0768): one doctor line while the licences baseline holds a line.


def held_licences(tmp_path: Path, layout: str | None, held: str | None) -> Path:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))
    root = tmp_path / "proj"
    root.mkdir(parents=True)
    kit = f'\n[kit]\nlayout = "{layout}"\n' if layout else ""
    (root / "agk.toml").write_text('mode = "adopt"\n' + kit, encoding="utf-8")
    if held is not None:
        (root / "config" / "agk-baseline").mkdir(parents=True)
        (root / "config" / "agk-baseline" / "licences.txt").write_text(held, encoding="utf-8")
    return root


def test_doctor_names_the_command_while_the_licence_baseline_holds_a_line(tmp_path):
    """REQ-079, REQ-061: brief #1838 answer 3, the installed layout."""
    import doctor

    root = held_licences(tmp_path, None, "package-lock.json 2\n")
    assert doctor.held_licence_lines(root) == [
        "warn licences: the baseline holds 2 packages whose licence is not on the allowed list;"
        " name them with python3 scripts/agk/gates/licences.py --names, then replace, remove or"
        " allow each by a project ADR (path class: config/agk-baseline/)"
    ]
    one = held_licences(tmp_path / "one", "installed", "requirements.lock 1\n")
    assert "holds 1 package whose" in doctor.held_licence_lines(one)[0]


def test_doctor_licence_line_in_the_plugin_layout(tmp_path, monkeypatch):
    """REQ-079, REQ-061: brief #1838 answer 3: `<kit>` as `kit_root.form` gives it."""
    import doctor
    import kit_root

    plugin = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin))
    monkeypatch.setattr(kit_root, "plugin_root", lambda _root, _env=None: plugin.resolve())
    root = held_licences(tmp_path, "plugin", "package-lock.json 1\n")
    lines = doctor.held_licence_lines(root)
    assert (
        lines
        and 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk"/gates/licences.py --names' in lines[0]
    )


def test_doctor_has_no_licence_line_without_a_held_line(tmp_path):
    """REQ-079, REQ-061: brief #1838 answer 3."""
    import doctor

    assert doctor.held_licence_lines(held_licences(tmp_path, None, None)) == []
    assert doctor.held_licence_lines(held_licences(tmp_path / "z", None, "")) == []


def test_doctor_refuses_another_layout_naming_it(tmp_path):
    """REQ-079, REQ-061: brief #1838 answer 5."""
    import doctor
    import pytest

    root = held_licences(tmp_path, "elsewhere", "package-lock.json 1\n")
    with pytest.raises(doctor.Refusal) as info:
        doctor.held_licence_lines(root)
    assert "layout" in str(info.value) and "elsewhere" not in str(info.value)
