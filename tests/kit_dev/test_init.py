"""Tests of scripts/agk/init.py (SPEC-0001)."""

from __future__ import annotations

import ast
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from conftest import (
    INIT,
    KIT_ROOT,
    KitSuite,
    Run,
    clean_env,
    expected_files,
    make_repo,
    manifest,
    run_init,
    set_handle,
    snapshot,
)

INSTALLED_PROTECTED = [
    "constitution/",
    "config/",
    ".claude/",
    ".github/",
    "docs/requirements.md",
    "CLAUDE.md",
    "scripts/agk/",
    "Makefile",
    "pyproject.toml",
    "agk.mk",
    "agk.toml",
]


def make(target: Path, *args: str, **env: str):
    full = {**clean_env(), **env}
    return subprocess.run(["make", *args], cwd=target, capture_output=True, text=True, env=full)


# --- Interface and effects ------------------------------------------------------------------


def test_ac1_usage_errors_exit_2(tmp_path):
    """REQ-009 AC1: rules 1-2."""
    for args in ([], ["--bogus"], [str(tmp_path), "extra"], [str(tmp_path), "--dry-run", "--x"]):
        proc = subprocess.run(
            [sys.executable, str(INIT), *args], capture_output=True, text=True, env=clean_env()
        )
        assert proc.returncode == 2, args


def test_ac1_unusable_target_exits_1(tmp_path):
    """REQ-009 AC1: rule 2."""
    assert run_init(tmp_path / "missing").returncode == 1
    afile = tmp_path / "f"
    afile.write_text("x")
    assert run_init(afile).returncode == 1


def test_ac1_self_target_refused(tmp_path):
    """REQ-009 AC1: rule 5."""
    before = snapshot(KIT_ROOT / "docs")
    for tgt in (KIT_ROOT, KIT_ROOT / "docs"):
        proc = run_init(tgt)
        assert proc.returncode == 1
        assert "kit/" in proc.stdout + proc.stderr
    assert snapshot(KIT_ROOT / "docs") == before


def test_ac1_interpreter_refusal_below_3_11():
    """REQ-009 AC1: rule 4."""
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import init

    assert init.check_interpreter((3, 10, 9)) is not None
    assert init.check_interpreter((3, 11, 0)) is None
    assert init.check_interpreter((3, 13, 1)) is None


def test_ac1_init_has_no_network_or_process_imports():
    """REQ-009 AC1: rule 3 (no network, git, gh); rule 1 (standard library only)."""
    tree = ast.parse(INIT.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    forbidden = {"subprocess", "socket", "urllib", "http", "ftplib", "smtplib", "requests", "ssl"}
    assert not names & forbidden
    local = {"common", "reviewers"}
    assert names <= set(sys.stdlib_module_names) | local


def test_ac1_symlinked_path_is_refused_and_nothing_written(target, tmp_path):
    """REQ-009 AC1: rule 3."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    os.symlink(elsewhere, target / ".claude")
    before = snapshot(target)
    proc = run_init(target)
    assert proc.returncode == 1
    assert ".claude/" in proc.stdout + proc.stderr
    assert snapshot(target) == before
    assert not any(elsewhere.rglob("*"))


def test_ac1_target_without_git_gets_a_notice_and_succeeds(tmp_path):
    """REQ-009 AC1: rule 3."""
    plain = tmp_path / "plain"
    plain.mkdir()
    proc = run_init(plain)
    assert proc.returncode == 0
    assert "not a git" in proc.stdout.lower()
    assert (plain / "Makefile").is_file()


# --- Target result ----------------------------------------------------------------------------


def test_ac2_creates_exactly_the_planned_file_list(target):
    """REQ-009 AC2: rule 10."""
    readme = (target / "README.md").read_bytes()
    before = set(snapshot(target))
    proc = run_init(target)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    created = set(snapshot(target)) - before
    assert created == expected_files()
    assert (target / "README.md").read_bytes() == readme
    for rel in manifest()["verbatim"]:
        assert (target / rel).read_bytes() == (KIT_ROOT / rel).read_bytes(), rel


def test_ac2_kit_only_files_are_not_installed(installed):
    """REQ-009 AC2: rules 6-7, 18."""
    for rel in ("scripts/agk/init.py", "kit", "tests/kit_dev"):
        assert not (installed / rel).exists(), rel


def test_ac2_governance_and_tests_green_in_target(shared_copy, kit_suite: KitSuite):
    """REQ-009 AC2: rule 23 (governance green after init). `make test` ran once, in a copy."""
    gov = make(shared_copy, "governance")
    assert gov.returncode == 0, gov.stdout + gov.stderr
    test = kit_suite.alias
    assert test.returncode == 0, test.stdout[-2000:] + test.stderr[-2000:]


def test_ac2_seeded_requirements(installed):
    """REQ-009 AC2: rule 11."""
    text = (installed / "docs" / "requirements.md").read_text(encoding="utf-8")
    ids = re.findall(r"^### (REQ-\d{3})", text, flags=re.M)
    assert ids == ["REQ-001", "REQ-002", "REQ-003"]
    assert re.findall(r"^- Status: (.*)$", text, flags=re.M) == ["planned"] * 3
    assert "agk doctor" not in text


def test_ac2_installed_protected_list_and_reviewers_equal(installed):
    """REQ-009 AC2: rule 21."""
    listed = [
        ln.strip()
        for ln in (installed / "config" / "protected-paths.txt").read_text().splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    assert listed == INSTALLED_PROTECTED
    set_handle(installed)
    assert make(installed, "governance").returncode == 0


def test_ac2_reviewers_placeholder_codeowners_and_notice(target):
    """REQ-009 AC2: rule 12 (warn only)."""
    proc = run_init(target)
    assert "@REPLACE-ME" in (target / "config" / "reviewers.yaml").read_text()
    assert "@REPLACE-ME" in (target / ".github" / "CODEOWNERS").read_text()
    assert "config/reviewers.yaml" in proc.stdout and "@REPLACE-ME" in proc.stdout
    check = subprocess.run(
        [sys.executable, "scripts/agk/reviewers.py", "--check-codeowners"],
        cwd=target,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0


def test_ac2_adr_names_every_protected_entry_and_is_proposed(installed):
    """REQ-009 AC2: rule 13."""
    text = (installed / "docs" / "adr" / "0001-adopt-agk.md").read_text(encoding="utf-8")
    assert "- Status: Proposed" in text
    for entry in INSTALLED_PROTECTED:
        assert entry in text, entry
    assert not re.findall(r"ADR-(?!0001)\d{4}", text)


def test_ac2_version_stamp_and_date(installed):
    """REQ-009 AC2: rule 14 (amended): the stamp lives in agk.toml only, not in pyproject.toml."""
    import tomllib

    pyproject = tomllib.loads((installed / "pyproject.toml").read_text(encoding="utf-8"))
    assert "agk" not in pyproject.get("tool", {})
    cfg = tomllib.loads((installed / "agk.toml").read_text(encoding="utf-8"))
    assert cfg["version"] == manifest()["kit_version"]
    assert cfg["test_dirs"] == ["tests"]
    assert cfg["installed"] == datetime.now(UTC).date().isoformat()
    assert pyproject["project"]["name"] == "my-project"


def test_ac2_branch_rules_are_printed_not_applied(target):
    """REQ-009 AC2: rule 19."""
    proc = run_init(target)
    out = " ".join(proc.stdout.split())
    for phrase in (
        "ruleset for the default branch is exactly",
        "required status check `governance`",
        "allow auto-merge; auto-delete head branches",
    ):
        assert phrase in out, phrase
    dry = run_init(target, "--dry-run")
    assert "required status check `governance`" in " ".join(dry.stdout.split())


# --- Idempotence, refusal, dry run --------------------------------------------------------------


def test_ac1_second_run_changes_nothing(installed):
    """REQ-009 AC1: rule 15 (hashes and mtimes equal)."""
    before = snapshot(installed)
    proc = run_init(installed)
    assert proc.returncode == 0
    assert "nothing to do" in proc.stdout
    assert snapshot(installed) == before


sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import init as init_module  # noqa: E402

OLD_DATE = "2020-01-02"
STAMPED = {"agk.toml", "constitution/vision.md", "docs/adr/0001-adopt-agk.md"}


def install_made_on(root: Path, date: str) -> list[str]:
    """Rewrite the stamped files of ROOT as an install made on DATE would have written them.

    The installer stamps its date through the `{{date}}` of the rendered templates, so the files are
    rendered again with another date (in a fresh directory of the same name, which has no stamp to
    read) and only the files that differ are written. No other file is touched, whatever it says
    (ADR-0112, brief #185).
    """
    fresh = root.parent / "fresh-stamp" / root.name
    fresh.mkdir(parents=True)
    items, _, _ = init_module.build_items(fresh, date)
    changed = []
    for rel, content in items:
        if rel in set(manifest()["templates"]) and (root / rel).read_bytes() != content:
            (root / rel).write_bytes(content)
            changed.append(rel)
    return sorted(changed)


def copy_of_the_kit(dest: Path) -> Path:
    """The files init needs, copied, so a test can change a kit document, not the kit."""
    shutil.copytree(
        KIT_ROOT / "scripts" / "agk",
        dest / "scripts" / "agk",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    shutil.copytree(KIT_ROOT / "kit", dest / "kit")
    for rel in manifest()["verbatim"]:
        if not (dest / rel).exists():
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(KIT_ROOT / rel, dest / rel)
    return dest


def run_copy_init(kit: Path, target: Path):
    return subprocess.run(
        [sys.executable, str(kit / "scripts" / "agk" / "init.py"), str(target), "--unreleased"],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def test_ac1_second_run_reads_the_stamped_date(installed):
    """REQ-009 AC1: rule 14. An install made on another date is still unchanged (any day)."""
    changed = install_made_on(installed, OLD_DATE)
    assert set(changed) == STAMPED, changed
    proc = run_init(installed)
    assert proc.returncode == 0, proc.stdout
    assert "nothing to do" in proc.stdout


def test_ac1_a_kit_document_that_quotes_todays_date_does_not_break_a_second_install(tmp_path):
    """REQ-009 AC1: rule 14 (brief #185: a role file quoted the day and the suite went red)."""
    today = datetime.now(UTC).date().isoformat()
    kit = copy_of_the_kit(tmp_path / "kit")
    document = kit / ".claude" / "agents" / "architect.md"
    document.write_text(
        document.read_text(encoding="utf-8") + f"\nRead on {today}.\n", encoding="utf-8"
    )
    target = make_repo(tmp_path / "proj")
    assert run_copy_init(kit, target).returncode == 0
    assert today in (target / ".claude" / "agents" / "architect.md").read_text(encoding="utf-8")
    assert set(install_made_on(target, OLD_DATE)) == STAMPED
    proc = run_copy_init(kit, target)
    assert proc.returncode == 0 and "nothing to do" in proc.stdout, proc.stdout


def test_ac1_rewriting_every_occurrence_of_the_date_is_what_made_the_suite_depend_on_the_day(
    tmp_path,
):
    """REQ-009 AC1: control of the test above (rewriting every occurrence reports a conflict)."""
    today = datetime.now(UTC).date().isoformat()
    kit = copy_of_the_kit(tmp_path / "kit")
    document = kit / ".claude" / "agents" / "architect.md"
    document.write_text(
        document.read_text(encoding="utf-8") + f"\nRead on {today}.\n", encoding="utf-8"
    )
    target = make_repo(tmp_path / "proj")
    assert run_copy_init(kit, target).returncode == 0
    for path in target.rglob("*"):
        if (
            path.is_file()
            and ".git" not in path.relative_to(target).parts
            and path.suffix in {".md", ".toml"}
        ):
            data = path.read_bytes()
            if today.encode() in data:
                path.write_bytes(data.replace(today.encode(), OLD_DATE.encode()))
    proc = run_copy_init(kit, target)
    assert proc.returncode == 1 and "conflict .claude/agents/architect.md" in proc.stdout


def test_ac1_conflict_refuses_lists_files_and_writes_nothing(target):
    """REQ-009 AC1: rule 16."""
    (target / "Makefile").write_text("all:\n\ttrue\n")
    (target / "pyproject.toml").write_text("[project]\nname='x'\n")
    before = snapshot(target)
    proc = run_init(target)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 1
    assert "Makefile" in out and "pyproject.toml" in out
    assert snapshot(target) == before
    assert (target / "Makefile").read_text() == "all:\n\ttrue\n"


def test_ac1_conflict_message_never_prints_content(target):
    """REQ-009 AC1: rule 2 (principle 8)."""
    (target / "Makefile").write_text("SECRET_MARKER_12345 := 1\n")
    proc = run_init(target)
    assert "SECRET_MARKER_12345" not in proc.stdout + proc.stderr


def test_ac1_partial_install_completes(installed):
    """REQ-009 AC1: rule 16."""
    (installed / "docs" / "build-state.md").unlink()
    before = snapshot(installed)
    proc = run_init(installed)
    assert proc.returncode == 0
    after = snapshot(installed)
    assert "docs/build-state.md" in after
    for rel, value in before.items():
        assert after[rel] == value, rel


def test_ac1_dry_run_writes_nothing_and_exit_code_matches(target):
    """REQ-009 AC1: rule 17."""
    before = snapshot(target)
    proc = run_init(target, "--dry-run")
    assert proc.returncode == 0
    assert snapshot(target) == before
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("create ")]
    assert {ln.split(" ", 1)[1] for ln in lines} == expected_files()
    (target / "Makefile").write_text("x:\n")
    dry = run_init(target, "--dry-run")
    assert dry.returncode == 1
    assert any(ln.startswith("conflict Makefile") for ln in dry.stdout.splitlines())


def test_ac1_dry_run_on_installed_target_says_unchanged(installed):
    """REQ-009 AC1: rule 17."""
    proc = run_init(installed, "--dry-run")
    assert proc.returncode == 0
    assert "create " not in proc.stdout and "unchanged " in proc.stdout


# --- Neutrality ----------------------------------------------------------------------------------

FORBIDDEN = [r"gbvraju", r"day-\d", r"\bK[0-4]\b", r"PR #\d+", r"Q-K\d"]


def test_ac2_rendered_output_is_neutral(installed):
    """REQ-009 AC2: rule 20."""
    for rel in expected_files():
        text = (installed / rel).read_text(encoding="utf-8")
        for pat in FORBIDDEN:
            assert not re.search(pat, text), (rel, pat)
    for rel in manifest()["templates"]:
        text = (installed / rel).read_text(encoding="utf-8")
        assert not re.findall(r"ADR-(?!0001)\d{4}", text), rel
        assert "{{" not in text, rel


# --- Project tests run under make test (SPEC-0001 rule 18, amended) ----------------------------


def test_ac2_project_tests_are_collected_and_run_by_make_test(shared_copy):
    """REQ-009 AC2: rule 18. A project test under tests/ runs in the target's make test.

    `make -o agk-test test` is the `test` target without its kit-suite prerequisite, which
    `kit_suite` runs once; `test_ac2_make_test_is_the_kit_suite_then_the_project_tests` pins that
    the prerequisite is the only difference.
    """
    (shared_copy / "tests").mkdir(exist_ok=True)
    (shared_copy / "tests" / "test_sample.py").write_text(
        "def test_sample_runs():\n    assert 1 + 1 == 2\n", encoding="utf-8"
    )
    proc = make(shared_copy, "-o", "agk-test", "test", PYTEST_ADDOPTS="-rA")
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert "PASSED tests/test_sample.py::test_sample_runs" in proc.stdout
    assert "tests/kit" not in proc.stdout  # the kit suite did not run again


def test_ac2_failing_project_test_makes_make_test_fail(shared_copy):
    """REQ-009 AC2: rule 18 (`make -o agk-test test`, as in the test above)."""
    (shared_copy / "tests").mkdir(exist_ok=True)
    (shared_copy / "tests" / "test_sample.py").write_text(
        "def test_sample_fails():\n    assert False\n", encoding="utf-8"
    )
    proc = make(shared_copy, "-o", "agk-test", "test", PYTEST_ADDOPTS="-rA")
    assert proc.returncode != 0
    assert "FAILED tests/test_sample.py::test_sample_fails" in proc.stdout


def test_ac2_make_test_is_the_kit_suite_then_the_project_tests(shared_copy):
    """REQ-009 AC2: rule 18. `make test` runs agk-test, then agk-project-test, and nothing else."""
    plan = make(shared_copy, "-n", "test").stdout
    suite = plan.index("kit's own tests are not installed")  # the notice of agk-test in a project
    project = plan.index("scripts/agk/project_tests.py")
    assert suite < project
    skipped = make(shared_copy, "-n", "-o", "agk-test", "test").stdout
    assert "kit's own tests are not installed" not in skipped
    assert "scripts/agk/project_tests.py" in skipped


def test_ac2_installed_adr_records_the_one_direct_commit(installed):
    """REQ-009 AC2: the rendered ADR-0001 of a target names its creation commit."""
    text = (installed / "docs" / "adr" / "0001-adopt-agk.md").read_text(encoding="utf-8")
    assert (
        "one direct commit to the default branch is the repository's creation commit"
        in " ".join(text.split())
    )


# --- Shared kit layout: agk.mk, agk.toml, thin Makefile (SPEC-0002 rules 5-8, 10, 12) ---------


def test_ac1_installs_agk_mk_and_agk_toml_with_the_stamp(installed):
    """REQ-010 AC1: rule 5."""
    import tomllib

    assert (installed / "agk.mk").read_bytes() == (KIT_ROOT / "agk.mk").read_bytes()
    cfg = tomllib.loads((installed / "agk.toml").read_text(encoding="utf-8"))
    assert cfg["mode"] == "init"
    assert cfg["version"] == manifest()["kit_version"]
    assert cfg["installed"] == datetime.now(UTC).date().isoformat()
    assert cfg["default_branch"] == "main"
    assert cfg["test_dirs"] == ["tests"]
    assert cfg["lint_paths"] == ["scripts/agk", ".claude/hooks"]


def test_ac1_makefile_is_thin_aliases_of_agk_mk(installed):
    """REQ-010 AC1: rule 5."""
    text = (installed / "Makefile").read_text(encoding="utf-8")
    assert "include agk.mk" in text
    for alias in ("governance: agk-governance", "lint: agk-lint", "test: agk-test"):
        assert alias in text


def test_ac1_both_forms_are_green_in_the_target(shared_copy, kit_suite: KitSuite):
    """REQ-010 AC1: rule 5. make governance (alias) and make -f agk.mk agk-governance agree.

    `make -f agk.mk agk-test` ran once, in a copy of the same install (`kit_suite.direct`).
    """
    assert make(shared_copy, "governance").returncode == 0
    proc = subprocess.run(
        ["make", "-f", "agk.mk", "agk-governance"],
        cwd=shared_copy,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert proc.returncode == 0, proc.stdout[-1500:] + proc.stderr[-1500:]
    direct = kit_suite.direct
    assert direct.returncode == 0, direct.stdout[-1500:] + direct.stderr[-1500:]


def test_ac1_bare_pytest_in_the_target_collects_no_kit_test(installed):
    """REQ-010 AC1: rule 6."""
    (installed / "tests").mkdir(exist_ok=True)
    (installed / "tests" / "test_sample.py").write_text("def test_sample():\n    assert True\n")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "."],
        cwd=installed,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert "tests/test_sample.py::test_sample" in proc.stdout
    assert "tests/kit/" not in proc.stdout


def test_ac1_default_branch_is_detected_and_governance_is_green_on_master(tmp_path):
    """REQ-010 AC1: rules 7-8. A master repository gets default_branch = master."""
    import tomllib

    tgt = make_repo(tmp_path / "proj", "master")
    assert run_init(tgt).returncode == 0
    set_handle(tgt)
    cfg = tomllib.loads((tgt / "agk.toml").read_text(encoding="utf-8"))
    assert cfg["default_branch"] == "master"
    assert make(tgt, "governance").returncode == 0
    adr = (tgt / "docs" / "adr" / "0001-adopt-agk.md").read_text(encoding="utf-8")
    assert "master" in adr and "ruleset `main`" not in adr
    out = run_init(tgt, "--dry-run").stdout
    assert "master" in out


def test_ac1_stamped_default_branch_survives_a_branch_rename(installed):
    """REQ-010 AC1: rule 8 and SPEC-0001 rule 15. The second run reads agk.toml."""
    subprocess.run(["git", "branch", "-m", "trunk"], cwd=installed, check=True)
    proc = run_init(installed)
    assert proc.returncode == 0 and "nothing to do" in proc.stdout


def test_ac1_installed_text_does_not_assume_main(installed):
    """REQ-010 AC1: rule 8."""
    claude = (installed / "CLAUDE.md").read_text(encoding="utf-8")
    principles = (installed / "constitution" / "principles.md").read_text(encoding="utf-8")
    assert "origin/main" not in claude
    assert "branched from main" not in principles
    assert "default branch" in claude and "default branch" in principles


def test_ac1_older_install_stamp_in_pyproject_is_still_read(tmp_path):
    """REQ-010 AC1: rule 5 (earlier installs): init reads the stamp from pyproject [tool.agk]."""
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import init

    (tmp_path / "pyproject.toml").write_text(
        '[tool.agk]\ninstalled = "2020-01-02"\ndefault_branch = "trunk"\n'
    )
    assert init.stamped(tmp_path, "2026-01-01") == ("2020-01-02", "trunk")


CI_STEP = re.compile(r"^\s*run:\s*((?:make -f agk\.mk|python scripts/agk/)[^\n]*?)\s*$", re.M)


def ci_steps(root: Path) -> list[str]:
    """The `run:` commands of the workflow that a repository at ROOT runs: a step guarded by the
    presence of the kit's own suite (`kit/agk-kit.mk`, SPEC-0028) is left out of a project."""
    text = (root / ".github" / "workflows" / "governance.yml").read_text(encoding="utf-8")
    kit = (root / "kit" / "agk-kit.mk").is_file()
    steps: list[str] = []
    for block in re.split(r"(?m)^      - ", text):
        if "hashFiles('kit/agk-kit.mk') != ''" in block and not kit:
            continue
        steps += CI_STEP.findall(block)
    return steps


KIT_SUITE_STEP = "make -f agk.mk agk-test"


def run_ci(root: Path, kit_suite: Run) -> list[int]:
    """The exit status of each CI step; the kit-suite step is the one `kit_suite.direct` ran."""
    codes = []
    runner_temp = root.parent / "runner-temp"  # the workflow's "PR body file" step writes this
    runner_temp.mkdir(exist_ok=True)
    (runner_temp / "pr-body.md").write_text("\n", encoding="utf-8")
    (runner_temp / "comments.json").write_text("[]\n", encoding="utf-8")  # the "PR comments" step
    (runner_temp / "reviews.json").write_text("[]\n", encoding="utf-8")  # same step: the reviews
    (runner_temp / "states.json").write_text("", encoding="utf-8")  # the fetch step's files
    (runner_temp / "open-prs.json").write_text("[]\n", encoding="utf-8")
    env = {**clean_env(), "RUNNER_TEMP": str(runner_temp)}
    for step in ci_steps(root):
        if step == KIT_SUITE_STEP:
            codes.append(kit_suite.returncode)
            continue
        argv = [
            a.replace("$RUNNER_TEMP", str(runner_temp)).replace("$HEAD_SHA", "HEAD")
            for a in shlex.split(step)
        ]
        if argv[0] == "python":
            argv[0] = sys.executable
        proc = subprocess.run(argv, cwd=root, capture_output=True, text=True, env=env)
        codes.append(proc.returncode)
    return codes


def test_ac1_ci_steps_include_the_project_tests_and_pass_when_they_pass(
    shared_copy, kit_suite: KitSuite
):
    """REQ-010 AC1: rule 5 (project_tests)."""
    steps = ci_steps(shared_copy)
    assert len(steps) == 16  # thirteen checks, one step each (SPEC-0007 rule 13), then three makes
    assert all(s.startswith("python scripts/agk/") for s in steps[:13])
    assert [s.split()[-1] for s in steps[13:]] == ["agk-lint", "agk-test", "agk-project-test"]
    assert KIT_SUITE_STEP in steps
    (shared_copy / "tests").mkdir(exist_ok=True)
    (shared_copy / "tests" / "test_p.py").write_text("def test_p():\n    assert True\n")
    assert run_ci(shared_copy, kit_suite.direct) == [0] * 16


def test_ac1_failing_project_test_makes_the_ci_steps_fail(shared_copy, kit_suite: KitSuite):
    """REQ-010 AC1: rule 5. The regression guard: CI runs the project's own tests."""
    (shared_copy / "tests").mkdir(exist_ok=True)
    (shared_copy / "tests" / "test_p.py").write_text("def test_p():\n    assert False\n")
    codes = run_ci(shared_copy, kit_suite.direct)
    assert codes[-1] != 0
    assert codes[:-1] == [0] * 15


def test_ac1_agk_toml_of_an_init_repo_has_project_tests_with_exit_5_handling(installed):
    """REQ-010 AC1: rule 5."""
    import tomllib

    cfg = tomllib.loads((installed / "agk.toml").read_text(encoding="utf-8"))
    assert "pytest tests" in cfg["project_tests"] and "exit $rc" in cfg["project_tests"]
    # a fresh install has no project tests: pytest exits 5, which the command treats as success
    proc = subprocess.run(
        ["make", "-f", "agk.mk", "agk-project-test"],
        cwd=installed,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_scanner_excludes_are_printed_not_written(target):
    """REQ-010: ADR-0010 decision 3. The snippet printed after a run is the template file."""
    template = (KIT_ROOT / "kit" / "templates" / "scanner-excludes.txt").read_text(encoding="utf-8")
    proc = run_init(target)
    assert " ".join(template.split()) in " ".join(proc.stdout.split())
    dry = run_init(target, "--dry-run")
    assert " ".join(template.split()) in " ".join(dry.stdout.split())
    assert not (target / "scanner-excludes.txt").exists()
    assert not any(p.name == "scanner-excludes.txt" for p in target.rglob("*"))


OWN_REGISTER = (
    "# Ours\n\n## Open\n\n- docs/adr/0001-x.md 2026-10-01 | ours | (due 2026-12-01) | open\n"
)

# --- the residuals register (Day 14 E1c): created when absent, never overwritten ---------------

REGISTER = "docs/runs/residuals.md"


def test_ac2_an_empty_residuals_register_is_installed_and_facts_reads_a_list(installed):
    """REQ-009 AC2: the register exists with its Open heading and no line; facts is not unknown."""
    import json

    text = (installed / REGISTER).read_text(encoding="utf-8")
    assert "\n## Open\n" in text
    assert not [ln for ln in text.splitlines() if ln.startswith("- ")]
    proc = subprocess.run(
        [sys.executable, "scripts/agk/facts.py", "--today", "2026-10-14", "--repo", "o/r"],
        cwd=installed,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    residuals = json.loads(proc.stdout)["residuals"]
    assert isinstance(residuals, list)  # not the string "unknown"
    assert [r for r in residuals if r["source"] == REGISTER] == []


def test_ac1_an_existing_residuals_register_is_left_as_it_is(target):
    """REQ-009 AC2: additive only; an existing register is never rewritten or refused."""
    own = OWN_REGISTER
    (target / "docs" / "runs").mkdir(parents=True)
    (target / REGISTER).write_text(own, encoding="utf-8")
    first = run_init(target)
    assert first.returncode == 0, first.stdout + first.stderr
    assert (target / REGISTER).read_text(encoding="utf-8") == own
    before = snapshot(target)
    second = run_init(target)
    assert second.returncode == 0 and snapshot(target) == before


def test_ac1_a_symlinked_residuals_register_is_still_refused(target, tmp_path):
    """REQ-009 AC2: the symlink rule of init holds for the register as for every file."""
    (target / "docs" / "runs").mkdir(parents=True)
    (tmp_path / "elsewhere.md").write_text("x\n", encoding="utf-8")
    (target / REGISTER).symlink_to(tmp_path / "elsewhere.md")
    proc = run_init(target)
    assert proc.returncode == 1 and "symlink" in proc.stdout


def test_ac1_init_installs_no_kit_tests_and_a_gitattributes_that_marks_the_scripts(installed):
    """REQ-009 AC1: lean install (ADR-0052): the kit's own tests are not installed."""
    assert not (installed / "tests" / "kit").exists()
    assert not (installed / "tests").exists()
    template = (KIT_ROOT / manifest()["templates"][".gitattributes"]).read_bytes()
    assert (installed / ".gitattributes").read_bytes() == template


def test_ac1_an_existing_gitattributes_is_left_alone_by_init(target):
    """REQ-009 AC1: `.gitattributes` is create-only, like the residuals register."""
    (target / ".gitattributes").write_text("*.png binary\n", encoding="utf-8")
    proc = run_init(target)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (target / ".gitattributes").read_text(encoding="utf-8") == "*.png binary\n"
    assert run_init(target).returncode == 0


def test_ac1_a_fresh_install_and_its_printed_text_do_not_mention_the_kit_tests(target):
    """REQ-009 AC2: lean install (ADR-0052), Q-K4-207: no `tests/kit` anywhere in a new install."""
    proc = run_init(target)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    found = [
        p.relative_to(target).as_posix()
        for p in sorted(target.rglob("*"))
        if p.is_file()
        and ".git" not in p.relative_to(target).parts
        and p.relative_to(target).as_posix()
        != ".claude/settings.json"  # guard patterns, not text (Q-K4-211)
        and b"tests/kit" in p.read_bytes()
    ]
    assert found == []
    assert "tests/kit" not in proc.stdout
