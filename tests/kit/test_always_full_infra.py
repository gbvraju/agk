"""Tests of the rule on `always_full` (brief #878 answers 1 and 3, ADR-0393, amendment 153).

`always_full` names the files that change how tests are found or run. `check_kit_tests.py` (the
kit) and `doctor.py` (a project) refuse any other entry without an adjacent `# full: <reason>`.
Fixture repositories and this repository's own `agk.toml`; no network.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import doctor
import impact
import pytest

ROOT = Path(__file__).resolve().parents[2]
RULE = "SPEC-0055 rule 6"
SETTING = "setting: testing.always_full"
INFRA = [
    "tests/kit/conftest.py",
    "tests/kit/pytest.ini",
    "tests/kit_dev/conftest.py",
    "Makefile",
    "agk.mk",
    "kit/agk-kit.mk",
    ".github/workflows/**",
    "scripts/agk/common.py",
    "scripts/agk/impact.py",
]
LEFT = [
    "check_adrs",
    "check_final_clearance",
    "check_pr_body",
    "check_specs",
    "drift_audit",
    "facts",
    "heavy_queue",
    "lock",
    "merge_cleared",
    "metrics",
    "minutes",
    "proof",
    "reviewers",
    "route",
    "session",
    "session_plan",
    "shadow_rate",
]
STACKS = [
    "conftest.py",
    "tests/conftest.py",
    "**/conftest.py",
    "pytest.ini",
    "pyproject.toml",
    "jest.config.*",
    "jest.config.js",
    "web/vitest.config.ts",
    "package.json",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "app/App.xcodeproj/project.pbxproj",
    "go.mod",
    ".github/workflows/**",
]
ORDINARY = [
    "app/auth/**",
    "migrations/**",
    "src/core.py",
    "scripts/agk/session.py",
    "**/*.py",
    "**",
]


def toml(body: str) -> str:
    return f'default_branch = "main"\ntest_dirs = ["tests"]\n[testing]\n{body}'


def problems(tmp_path: Path, body: str) -> list[str]:
    (tmp_path / "agk.toml").write_text(toml(body), encoding="utf-8")
    return impact.always_full_problems(tmp_path)


def test_this_repository_keeps_only_the_test_system_in_the_list():
    """REQ-051: brief #878 answer 1 (the list is exactly the test system's files)."""
    assert sorted(impact.testing_table(ROOT)["always_full"]) == sorted(INFRA)


def test_this_repository_passes_its_own_rule():
    """REQ-051: brief #878 answer 3 (no reason is needed for its entries)."""
    assert impact.always_full_problems(ROOT) == []


@pytest.mark.parametrize("stem", LEFT)
def test_a_script_that_left_the_list_has_a_map_entry_with_its_tests(stem):
    """REQ-051: brief #878 answer 2 (each one has a map entry built from the tests that name or
    import it, so nothing it touches goes unselected)."""
    path = f"scripts/agk/{stem}.py"
    entries = [e for e in impact.testing_table(ROOT)["map"] if impact.matches(path, e["code"])]
    named = {t for e in entries for t in e["tests"]}
    expected = set()
    for folder in ("tests/kit", "tests/kit_dev"):
        for test in (ROOT / folder).glob("test_*.py"):
            text = test.read_text(encoding="utf-8")
            if re.search(rf"\b{stem}\.py\b|^\s*(?:import|from)\s+{stem}\b", text, re.M):
                expected.add(test.relative_to(ROOT).as_posix())
    assert expected, stem
    assert expected <= named, sorted(expected - named)[:5]


@pytest.mark.parametrize("entry", INFRA + STACKS)
def test_test_infrastructure_needs_no_reason(entry):
    """REQ-051: brief #878 answers 1 and 3 (the test system's files, by stack)."""
    assert impact.is_test_infrastructure(entry), entry


@pytest.mark.parametrize("entry", ORDINARY)
def test_ordinary_code_is_not_test_infrastructure(entry):
    """REQ-051: brief #878 answer 1 (never ordinary code)."""
    assert not impact.is_test_infrastructure(entry), entry


def test_an_ordinary_entry_without_a_reason_is_refused_naming_rule_and_entry(tmp_path):
    """REQ-051: brief #878 answers 3, 7; principle 8 (the entry by place, never its value)."""
    found = problems(tmp_path, 'always_full = ["conftest.py", "app/secret-area/**"]\n')
    assert len(found) == 1
    assert RULE in found[0] and SETTING in found[0] and "testing.always_full[2]" in found[0]
    assert "secret-area" not in found[0]


def test_a_reason_on_the_same_line_allows_it(tmp_path):
    """REQ-051: brief #878 answer 3 (an adjacent `# full: <reason>`)."""
    body = 'always_full = [\n  "app/auth/**", # full: every test logs in\n]\n'
    assert problems(tmp_path, body) == []


def test_a_reason_on_the_line_above_allows_only_the_next_entry(tmp_path):
    """REQ-051: brief #878 answer 3 (adjacent means that line or the line above it)."""
    body = (
        'always_full = [\n  # full: every test logs in\n  "app/auth/**",\n  "migrations/**",\n]\n'
    )
    found = problems(tmp_path, body)
    assert len(found) == 1 and "testing.always_full[2]" in found[0]


def test_a_reason_on_one_line_list_allows_it(tmp_path):
    """REQ-051: brief #878 answer 3 (a list written on one line)."""
    assert problems(tmp_path, 'always_full = ["migrations/**"] # full: schema\n') == []


def test_an_empty_reason_is_no_reason(tmp_path):
    """REQ-051: brief #878 answer 3 (`# full:` with nothing after it)."""
    assert len(problems(tmp_path, 'always_full = [\n  "app/**", # full:\n]\n')) == 1


def test_another_comment_is_no_reason(tmp_path):
    """REQ-051: brief #878 answer 3 (only `# full: <reason>` counts)."""
    assert len(problems(tmp_path, 'always_full = [\n  "app/**", # the core\n]\n')) == 1


def test_a_hash_inside_an_entry_is_not_a_comment(tmp_path):
    """REQ-051: brief #878 answer 3 (a `#` inside a string starts no comment)."""
    assert len(problems(tmp_path, 'always_full = ["a#full: x/**"]\n')) == 1


def test_no_table_and_no_key_have_nothing_to_refuse(tmp_path):
    """REQ-051: brief #878 answer 3 (the key is optional)."""
    assert problems(tmp_path, 'profile = "balanced"\n') == []
    (tmp_path / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    assert impact.always_full_problems(tmp_path) == []


def kit(repo, body: str) -> None:
    manifest = {"kit_version": "0.0.0", "kit_tests": "tests/kit", "verbatim": []}
    repo.commit({"kit/manifest.json": json.dumps(manifest) + "\n", "agk.toml": toml(body)})


def test_the_kit_check_refuses_an_ordinary_entry(repo):
    """REQ-051: brief #878 answers 3 and 7 (`check_kit_tests.py` in the kit)."""
    kit(repo, 'always_full = ["src/core.py"]\n')
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1, proc.stdout
    assert "FAIL kit-tests" in proc.stdout and RULE in proc.stdout
    assert "src/core.py" not in proc.stdout


def test_the_kit_check_passes_with_a_reason(repo):
    """REQ-051: brief #878 answer 3."""
    kit(repo, 'always_full = [\n  "src/core.py", # full: imported by everything\n]\n')
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 0, proc.stdout


def result(tmp_path: Path, body: str) -> doctor.Result:
    (tmp_path / "agk.toml").write_text(toml(body), encoding="utf-8")
    return doctor.always_full_result(tmp_path)


def test_doctor_fails_an_ordinary_entry_in_a_project(tmp_path):
    """REQ-051: brief #878 answers 3 and 7 (`doctor.py` in a project), naming no value."""
    found = result(tmp_path, 'always_full = ["app/private/**"]\n')
    assert found.status == "fail"
    assert RULE in found.message and "private" not in found.message
    assert doctor.CHECKS["always-full-infra"][0] == "error"


def test_doctor_passes_a_project_with_infrastructure_or_reasons(tmp_path):
    """REQ-051: brief #878 answer 3."""
    assert result(tmp_path, 'always_full = ["conftest.py", "package.json"]\n').status == "ok"
    body = 'always_full = [\n  "app/**", # full: every test logs in\n]\n'
    assert result(tmp_path, body).status == "ok"


def test_doctor_leaves_a_malformed_table_to_the_commands_that_read_it(tmp_path):
    """REQ-051: brief #878 answer 3 (the setting is refused elsewhere, as for the other lines)."""
    assert result(tmp_path, "always_full = 1\n").status == "ok"


def test_the_shipped_examples_name_only_infrastructure():
    """REQ-051: brief #878 answer 3 (what a new project copies names the test system only)."""
    for name in ("agk.toml", "agk.adopt.toml"):
        text = (ROOT / "kit" / "templates" / name).read_text(encoding="utf-8")
        example = re.search(r"^# always_full = (\[.*\])$", text, re.M)
        assert example, name
        for entry in json.loads(example.group(1)):
            assert impact.is_test_infrastructure(entry), (name, entry)
