"""Tests of scripts/agk/doctor.py (SPEC-0006). No network: `gh` is never called except by stubs."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from doctor import CHECKS, RULESET_IDS, targets_default

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agk" / "doctor.py"
FIXTURES = Path(__file__).parent / "fixtures" / "doctor"
CASES = sorted(p.name for p in FIXTURES.iterdir() if p.is_dir())
IDS = list(CHECKS)
REMOTE = {
    "ruleset-missing",
    *RULESET_IDS,
    "repo-auto-merge",
    "repo-delete-branch",
    "drift-workflow-state",
    "default-branch-config",
}
LOCAL = set(IDS) - REMOTE


def overlay(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)


def prepare(case: str, tmp_path: Path) -> dict[str, Path]:
    """root (a git work tree), api and kit directories for a case: `ok` with the case laid over."""
    root, api, kit = tmp_path / "root", tmp_path / "api", tmp_path / "kit"
    meta = json.loads((FIXTURES / case / "case.json").read_text(encoding="utf-8"))
    for name, target in (("tree", root), ("api", api), ("kit", kit)):
        overlay(FIXTURES / "ok" / name, target)
        overlay(FIXTURES / case / name, target)
    for rel in meta.get("delete", []):
        (root / rel).unlink()
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607 - fixed argument list, no shell
    if meta.get("origin_head", True):
        subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            [
                "git",
                "-C",
                str(root),
                "symbolic-ref",
                "refs/remotes/origin/HEAD",
                "refs/remotes/origin/main",
            ],
            check=True,
        )
    return {"root": root, "api": api, "kit": kit}


def stub_gh(directory: Path, body: str = "exit 1") -> Path:
    """A `gh` on PATH that records every call, then runs `body`."""
    directory.mkdir(parents=True, exist_ok=True)
    log = directory / "gh-calls"
    gh = directory / "gh"
    gh.write_text(f'#!/bin/sh\necho "$@" >> "{log}"\n{body}\n')
    gh.chmod(0o755)
    return log


def doctor(*args: str, path: str | None = None, cwd: Path | None = None):
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    if path is not None:
        env["PATH"] = path
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env, cwd=cwd
    )


def run_case(case: str, tmp_path: Path, *extra: str, kit: bool = True):
    dirs = prepare(case, tmp_path)
    stub = tmp_path / "bin"
    log = stub_gh(stub)
    args = ["--api-dir", str(dirs["api"]), "--repo", "example-owner/example-repo", *extra]
    if kit:
        args += ["--kit-root", str(dirs["kit"])]
    proc = doctor(*args, str(dirs["root"]), path=f"{stub}{os.pathsep}{os.environ['PATH']}")
    return proc, log, dirs


def checks_of(stdout: str) -> dict[str, dict]:
    return {c["id"]: c for c in json.loads(stdout)["checks"]}


def expected_exit(report: dict[str, dict]) -> int:
    if any(c["status"] == "fail" and c["severity"] == "error" for c in report.values()):
        return 1
    return 4 if any(c["status"] != "ok" for c in report.values()) else 0


@pytest.mark.parametrize("case", CASES)
def test_ac1_each_case_reports_exactly_its_misconfiguration(case, tmp_path):
    """REQ-002 AC1: rules 5, 7, 12, 15 (the ids that fail and the ones that cannot be checked)."""
    meta = json.loads((FIXTURES / case / "case.json").read_text(encoding="utf-8"))
    proc, log, _ = run_case(case, tmp_path, "--json")
    report = checks_of(proc.stdout)
    assert list(report) == IDS
    assert sorted(i for i, c in report.items() if c["status"] == "fail") == meta["fail"]
    cannot = {i: c["reason"] for i, c in report.items() if c["status"] == "cannot-check"}
    assert cannot == meta["cannot"]
    assert proc.returncode == expected_exit(report)
    assert not log.exists(), "gh must never be called with --api-dir"


def test_ac1_the_ok_case_reports_none_and_exits_0(tmp_path):
    """REQ-002 AC1: rule 16."""
    proc, _, _ = run_case("ok", tmp_path)
    assert proc.returncode == 0, proc.stdout
    assert "FAIL" not in proc.stdout and "??" not in proc.stdout
    assert proc.stdout.splitlines()[0] == "agk doctor 9.9.9"
    assert proc.stdout.splitlines()[-1] == "summary: 20 ok, 0 fail, 0 cannot-check"


def test_ac1_stricter_than_the_minimum_is_ok(tmp_path):
    """REQ-002 AC1: rule 7 (1+ approvals, a team approver, an extra check, an extra rule)."""
    proc, _, dirs = run_case("stricter-ok", tmp_path)
    assert proc.returncode == 0, proc.stdout
    ruleset = json.loads((dirs["api"] / "ruleset-1.json").read_text(encoding="utf-8"))
    params = next(r for r in ruleset["rules"] if r["type"] == "pull_request")["parameters"]
    assert params["required_approving_review_count"] == 1 and params["required_reviewers"]
    assert "rebase" in params["allowed_merge_methods"]


def test_ac1_no_ruleset_makes_the_other_ruleset_checks_unknown_not_ok(tmp_path):
    """REQ-002 AC1: rules 3 and 5 (nothing is ok because nothing could be read)."""
    proc, _, _ = run_case("no-ruleset", tmp_path, "--json")
    report = checks_of(proc.stdout)
    assert report["ruleset-missing"]["status"] == "fail"
    assert all(report[i]["reason"] == "no-ruleset" for i in RULESET_IDS)
    assert proc.returncode == 1


def test_ac1_a_403_is_cannot_check_never_ruleset_missing(tmp_path):
    """REQ-002 AC1: rule 6."""
    proc, _, _ = run_case("no-admin", tmp_path, "--json")
    report = checks_of(proc.stdout)
    assert report["ruleset-missing"]["status"] == "cannot-check"
    assert report["ruleset-missing"]["reason"] == "no-admin"
    assert proc.returncode == 4  # cannot-check never exits 0, and it is not an error finding


def test_ac1_warn_findings_exit_4_and_error_findings_exit_1(tmp_path):
    """REQ-002 AC1: rule 12."""
    assert run_case("auto-merge-off", tmp_path / "a")[0].returncode == 4
    assert run_case("bypass-actor", tmp_path / "b")[0].returncode == 1


def test_ac1_text_and_json_carry_the_same_findings(tmp_path):
    """REQ-002 AC1: rule 11."""
    for case in ("version-mismatch", "no-admin", "vendored-edited"):
        text, _, _ = run_case(case, tmp_path / case / "t")
        data, _, _ = run_case(case, tmp_path / case / "j", "--json")
        report = checks_of(data.stdout)
        marks = {"ok": "ok", "fail": "FAIL", "cannot-check": "??"}
        lines = [
            ln for ln in text.stdout.splitlines() if not ln.startswith(("  ", "agk ", "summary"))
        ]
        assert lines == [
            f"{marks[c['status']]} {c['id']} {c['severity']} {c['message']}"
            for c in report.values()
        ]
        assert text.returncode == data.returncode


def test_ac1_text_report_shape(tmp_path):
    """REQ-002 AC1: rule 10 (FAIL lines are followed by a fix, ?? lines by what is needed)."""
    proc, _, _ = run_case("version-mismatch", tmp_path)
    lines = proc.stdout.splitlines()
    i = lines.index(next(ln for ln in lines if ln.startswith("FAIL kit-version warn ")))
    assert lines[i + 1] == "  fix: run /agk:upgrade (SPEC-0008)"
    j = lines.index(next(ln for ln in lines if ln.startswith("?? vendored-missing error ")))
    assert lines[j + 1].startswith("  to check: ")
    assert lines[-1] == "summary: 17 ok, 1 fail, 2 cannot-check"


def test_ac1_json_has_sorted_keys_the_summary_and_no_timestamp(tmp_path):
    """REQ-002 AC1: rule 11."""
    proc, _, _ = run_case("vendored-edited", tmp_path, "--json")
    data = json.loads(proc.stdout)
    assert list(data) == sorted(data) == ["checks", "doctor", "summary"]
    assert data["summary"] == {"cannot-check": 0, "fail": 1, "ok": 19}
    for check in data["checks"]:
        assert list(check) == sorted(check)
        assert (check["status"] == "cannot-check") == ("reason" in check)
    assert "T" not in proc.stdout.split('"doctor"')[1][:20]


@pytest.mark.parametrize("case", CASES)
def test_ac1_runs_are_byte_identical(case, tmp_path):
    """REQ-002 AC1: rules 10, 11 and 17."""
    for flag in ([], ["--json"]):
        one, _, _ = run_case(case, tmp_path / "1", *flag)
        two, _, _ = run_case(case, tmp_path / "2", *flag)
        assert one.stdout == two.stdout and one.returncode == two.returncode


def test_ac1_messages_name_settings_not_values(tmp_path):
    """REQ-002 AC1: rule 4 (no identifier or count of a found value appears in a message)."""
    proc, _, _ = run_case("bypass-actor", tmp_path, "--json")
    message = checks_of(proc.stdout)["ruleset-bypass"]["message"]
    assert "bypass_actors" in message
    for found in ("RepositoryRole", "always", "actor_id", "5"):
        assert found not in message.split()


def test_ac1_the_vendored_message_lists_paths(tmp_path):
    """REQ-002 AC1: rule 8."""
    proc, _, _ = run_case("vendored-missing", tmp_path, "--json")
    assert "scripts/agk/y.txt" in checks_of(proc.stdout)["vendored-missing"]["message"]


def test_ac1_without_kit_root_the_three_kit_checks_cannot_be_checked(tmp_path):
    """REQ-002 AC1: rule 8."""
    proc, _, _ = run_case("ok", tmp_path, "--json", kit=False)
    report = checks_of(proc.stdout)
    for check in ("kit-version", "vendored-missing", "vendored-differs"):
        assert (report[check]["status"], report[check]["reason"]) == ("cannot-check", "no-kit-root")
    assert json.loads(proc.stdout)["doctor"] == "unknown"
    assert proc.returncode == 4


def test_ac1_a_kit_without_a_manifest_is_bad_response(tmp_path):
    """REQ-002 AC1: rule 3."""
    dirs = prepare("ok", tmp_path)
    (dirs["kit"] / "kit" / "manifest.json").unlink()
    proc = doctor(
        "--api-dir", str(dirs["api"]), "--kit-root", str(dirs["kit"]), "--json", str(dirs["root"])
    )
    report = checks_of(proc.stdout)
    assert report["vendored-differs"]["reason"] == "bad-response"


# --- adopt targets: verbatim files, skips and marked blocks --------------------------------------


def adopt_target(tmp_path: Path, gitignore: str) -> dict[str, Path]:
    dirs = prepare("ok", tmp_path)
    kit, root = dirs["kit"], dirs["root"]
    manifest = {
        "kit_version": "9.9.9",
        "verbatim": ["Makefile", ".gitignore", "a.txt", ".github/CODEOWNERS"],
        "templates": {},
        "rendered": [".github/CODEOWNERS"],
        "adopt": {
            "skip": ["Makefile"],
            "blocks": {".gitignore": "hash", ".github/CODEOWNERS": "hash"},
            "templates": {},
        },
    }
    (kit / "kit" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (kit / "Makefile").write_text("kit makefile\n", encoding="utf-8")
    (kit / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
    (kit / "a.txt").write_text("a\n", encoding="utf-8")
    (kit / ".github").mkdir(exist_ok=True)
    (kit / ".github" / "CODEOWNERS").write_text("* @kit\n", encoding="utf-8")
    (root / "Makefile").write_text("the project's own makefile\n", encoding="utf-8")
    (root / ".gitignore").write_text(gitignore, encoding="utf-8")
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    (root / "agk.toml").write_text('mode = "adopt"\nversion = "9.9.9"\n', encoding="utf-8")
    return dirs


def adopt_report(dirs: dict[str, Path]) -> dict[str, dict]:
    proc = doctor(
        "--api-dir", str(dirs["api"]), "--kit-root", str(dirs["kit"]), "--json", str(dirs["root"])
    )
    return checks_of(proc.stdout)


def test_ac1_adopt_compares_inside_the_markers_only(tmp_path):
    """REQ-002 AC1: rule 8 (text around the block, a skipped Makefile, CODEOWNERS not compared)."""
    mine = "build/\n# >>> agk\n*.pyc\n# <<< agk\nmy-own-line\n"
    report = adopt_report(adopt_target(tmp_path, mine))
    assert report["vendored-differs"]["status"] == "ok"
    assert report["vendored-missing"]["status"] == "ok"


def test_ac1_adopt_block_edited_inside_the_markers_differs(tmp_path):
    """REQ-002 AC1: rule 8."""
    report = adopt_report(adopt_target(tmp_path, "# >>> agk\n*.pyc\nsecret.txt\n# <<< agk\n"))
    assert report["vendored-differs"]["status"] == "fail"
    assert ".gitignore" in report["vendored-differs"]["message"]


def test_ac1_adopt_without_markers_and_broken_markers_differ(tmp_path):
    """REQ-002 AC1: rule 8 (a .gitignore with the content but no markers is not the block)."""
    for i, text in enumerate(
        ["*.pyc\n", "# >>> agk\n*.pyc\n", "# >>> agk\n*.pyc\n# <<< agk\n" * 2]
    ):
        report = adopt_report(adopt_target(tmp_path / str(i), text))
        assert report["vendored-differs"]["status"] == "fail", text


def test_ac1_adopt_edited_verbatim_file_differs_and_missing_one_is_missing(tmp_path):
    """REQ-002 AC1: rule 8."""
    dirs = adopt_target(tmp_path, "# >>> agk\n*.pyc\n# <<< agk\n")
    (dirs["root"] / "a.txt").write_text("changed\n", encoding="utf-8")
    assert adopt_report(dirs)["vendored-differs"]["status"] == "fail"
    (dirs["root"] / "a.txt").unlink()
    report = adopt_report(dirs)
    assert report["vendored-missing"]["status"] == "fail"


def test_ac1_an_unknown_mode_cannot_be_checked(tmp_path):
    """REQ-002 AC1: rule 8."""
    dirs = prepare("ok", tmp_path)
    (dirs["root"] / "agk.toml").write_text('mode = "other"\nversion = "9.9.9"\n', encoding="utf-8")
    report = adopt_report(dirs)
    assert report["vendored-differs"]["reason"] == "bad-response"


# --- live mode: `gh` stubs -----------------------------------------------------------------------


def live(tmp_path: Path, body: str | None, *extra: str):
    """Run without --api-dir. body None: no `gh` at all on PATH."""
    dirs = prepare("ok", tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "git").symlink_to(shutil.which("git") or "git")
    log = None
    if body is not None:
        log = stub_gh(bin_dir, body)
    proc = doctor(
        "--repo", "example-owner/example-repo", "--kit-root", str(dirs["kit"]), "--json",
        *extra, str(dirs["root"]), path=str(bin_dir),
    )  # fmt: skip
    return proc, log, dirs


def test_ac1_no_gh_makes_every_remote_check_cannot_check(tmp_path):
    """REQ-002 AC1: rules 3 and 15 (`no-gh`); the local checks still run."""
    proc, _, _ = live(tmp_path, None)
    report = checks_of(proc.stdout)
    for check in REMOTE:
        assert (report[check]["status"], report[check]["reason"]) == ("cannot-check", "gh-missing")
    assert all(report[c]["status"] == "ok" for c in LOCAL)
    assert proc.returncode == 4


def test_ac1_gh_not_authenticated(tmp_path):
    """REQ-002 AC1: rule 3."""
    body = 'echo "To get started with GitHub CLI, please run:  gh auth login" >&2; exit 4'
    proc, log, _ = live(tmp_path, body)
    report = checks_of(proc.stdout)
    assert {report[c]["reason"] for c in REMOTE} == {"gh-unauthenticated"}
    assert log.exists()


def test_ac1_gh_403_and_offline_are_classified(tmp_path):
    """REQ-002 AC1: rule 3."""
    body = (
        'echo \'{"message":"Must have admin rights","status":"403"}\'; '
        'echo "gh: HTTP 403" >&2; exit 1'
    )
    proc, _, _ = live(tmp_path / "a", body)
    assert {checks_of(proc.stdout)[c]["reason"] for c in REMOTE} == {"no-admin"}
    proc, _, _ = live(
        tmp_path / "b", 'echo "dial tcp: lookup api.github.com: no such host" >&2; exit 1'
    )
    assert {checks_of(proc.stdout)[c]["reason"] for c in REMOTE} == {"offline"}
    proc, _, _ = live(tmp_path / "c", "echo 'not json'")
    assert {checks_of(proc.stdout)[c]["reason"] for c in REMOTE} == {"bad-response"}


def test_ac1_live_mode_makes_only_get_reads_on_the_four_paths(tmp_path):
    """REQ-002 AC1: rules 2 and 6 (the endpoints are exactly those of the rule)."""
    api = FIXTURES / "ok" / "api"
    body = (
        'case "$*" in\n'
        f"  *rulesets/1) /bin/cat '{api}/ruleset-1.json';;\n"
        f"  *rulesets) /bin/cat '{api}/rulesets.json';;\n"
        f"  *workflows/drift-audit.yml) /bin/cat '{api}/workflow-drift-audit.json';;\n"
        f"  *) /bin/cat '{api}/repo.json';;\n"
        "esac"
    )
    proc, log, _ = live(tmp_path, body)
    assert proc.returncode == 0, proc.stdout
    calls = sorted(log.read_text(encoding="utf-8").splitlines())
    base = "api --method GET repos/example-owner/example-repo"
    assert calls == sorted(
        [
            base,
            f"{base}/rulesets",
            f"{base}/rulesets/1",
            f"{base}/actions/workflows/drift-audit.yml",
        ]
    )


def test_ac1_an_installed_report_workflow_adds_the_fifth_read_to_the_one_check(tmp_path):
    """REQ-002 AC1: the state of the product-report workflow is read only where the file exists."""
    api = FIXTURES / "report-installed" / "api"
    ok = FIXTURES / "ok" / "api"
    dirs = prepare("report-installed", tmp_path)
    stub = tmp_path / "bin"
    body = (
        'case "$*" in\n'
        f"  *rulesets/1) /bin/cat '{ok}/ruleset-1.json';;\n"
        f"  *rulesets) /bin/cat '{ok}/rulesets.json';;\n"
        f"  *workflows/drift-audit.yml) /bin/cat '{ok}/workflow-drift-audit.json';;\n"
        f"  *workflows/product-report.yml) /bin/cat '{api}/workflow-product-report.json';;\n"
        f"  *) /bin/cat '{ok}/repo.json';;\n"
        "esac"
    )
    log = stub_gh(stub, body)
    proc = doctor(
        "--repo", "example-owner/example-repo", "--kit-root", str(dirs["kit"]), "--json",
        str(dirs["root"]), path=f"{stub}{os.pathsep}{os.environ['PATH']}",
    )  # fmt: skip
    assert proc.returncode == 0, proc.stdout
    calls = log.read_text(encoding="utf-8").splitlines()
    base = "api --method GET repos/example-owner/example-repo"
    assert f"{base}/actions/workflows/product-report.yml" in calls
    assert len(calls) == 5
    assert checks_of(proc.stdout)["drift-workflow-state"]["status"] == "ok"


def test_ac1_no_new_check_id_for_the_report_workflow():
    """REQ-002 AC1: the amendment extends drift-workflow-state and adds no id."""
    assert not [i for i in IDS if "report" in i]
    assert IDS.count("drift-workflow-state") == 1


def test_ac1_no_github_origin_is_not_github(tmp_path):
    """REQ-002 AC1: rule 3 (no --repo and no origin remote on github.com)."""
    dirs = prepare("ok", tmp_path)
    stub = tmp_path / "bin"
    log = stub_gh(stub)
    proc = doctor(
        "--kit-root", str(dirs["kit"]), "--json", str(dirs["root"]),
        path=f"{stub}{os.pathsep}{os.environ['PATH']}",
    )  # fmt: skip
    report = checks_of(proc.stdout)
    assert {report[c]["reason"] for c in REMOTE} == {"not-github"}
    assert not log.exists()


# --- refusals, usage, read-only ---------------------------------------------------------------


def test_ac1_missing_agk_toml_is_a_refusal_with_no_checks(tmp_path):
    """REQ-002 AC1: rule 13."""
    proc = doctor(str(tmp_path))
    assert proc.returncode == 1
    assert proc.stdout.startswith("refused: agk.toml missing")
    assert "ruleset" not in proc.stdout


def test_ac1_root_must_be_a_directory(tmp_path):
    """REQ-002 AC1: rule 13."""
    assert doctor(str(tmp_path / "nope")).returncode == 1


def test_ac1_an_api_file_that_is_not_json_is_an_io_error(tmp_path):
    """REQ-002 AC1: rule 13."""
    dirs = prepare("ok", tmp_path)
    (dirs["api"] / "repo.json").write_text("{not json", encoding="utf-8")
    proc = doctor("--api-dir", str(dirs["api"]), str(dirs["root"]))
    assert proc.returncode == 3
    assert "api-dir" in proc.stdout


def test_ac1_usage_errors_exit_2(tmp_path):
    """REQ-002 AC1: rule 1."""
    assert doctor("--bogus").returncode == 2
    assert doctor("--repo").returncode == 2
    assert doctor("a", "b").returncode == 2


def tree_hash(root: Path) -> dict[str, str]:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and ".git" not in p.relative_to(root).parts:
            out[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def test_ac1_the_doctor_writes_nothing(tmp_path):
    """REQ-002 AC1: rule 2 (the work tree, the api and the kit are unchanged)."""
    dirs = prepare("vendored-edited", tmp_path)
    before = {k: tree_hash(v) for k, v in dirs.items()}
    stub = tmp_path / "bin"
    stub_gh(stub)
    doctor(
        "--api-dir", str(dirs["api"]), "--kit-root", str(dirs["kit"]), str(dirs["root"]),
        path=f"{stub}{os.pathsep}{os.environ['PATH']}",
    )  # fmt: skip
    assert {k: tree_hash(v) for k, v in dirs.items()} == before
    assert sorted(p.name for p in dirs["root"].iterdir() if p.name != ".git") == sorted(
        p.name for p in (FIXTURES / "ok" / "tree").iterdir()
    )


def test_ac1_default_root_is_the_current_directory(tmp_path):
    """REQ-002 AC1: rule 1."""
    dirs = prepare("ok", tmp_path)
    proc = doctor(
        "--api-dir", str(dirs["api"]), "--kit-root", str(dirs["kit"]), "--json", cwd=dirs["root"]
    )
    assert proc.returncode == 0, proc.stdout


def test_ac1_every_id_has_a_severity_and_a_printed_fix():
    """REQ-002 AC1: rule 5."""
    assert len(IDS) == 20
    for severity, ok_text, fail_text, fix in CHECKS.values():
        assert severity in ("error", "warn") and ok_text and fail_text and fix
    assert CHECKS["ruleset-missing"][3].endswith("use a ruleset (ADR-0001 decision 3)")


def test_ac1_only_an_active_ruleset_protects(tmp_path):
    """REQ-002 AC1: rule 7 (a disabled ruleset holding every rule adds nothing to an active one)."""
    proc, _, _ = run_case("disabled-holds-every-rule", tmp_path, "--json")
    report = checks_of(proc.stdout)
    failing = sorted(i for i, c in report.items() if c["status"] == "fail")
    assert failing == [
        "required-check-governance",
        "ruleset-force-push",
        "ruleset-linear-history",
        "ruleset-pull-request",
    ]
    assert report["ruleset-enforcement"]["status"] == "ok"
    assert report["ruleset-deletion"]["status"] == "ok"  # the active ruleset has it
    assert proc.returncode == 1


def test_ac1_no_active_ruleset_fails_every_element_check(tmp_path):
    """REQ-002 AC1: rule 7 (with no active candidate the element checks fail, not pass)."""
    proc, _, _ = run_case("weak-enforcement", tmp_path, "--json")
    report = checks_of(proc.stdout)
    failing = {i for i, c in report.items() if c["status"] == "fail"}
    assert failing == {"ruleset-enforcement", *RULESET_IDS} - {"ruleset-target"}


def test_ac1_a_bypass_actor_on_a_disabled_ruleset_is_not_a_bypass(tmp_path):
    """REQ-002 AC1: rule 7."""
    proc, _, _ = run_case("bypass-on-disabled-ruleset", tmp_path, "--json")
    report = checks_of(proc.stdout)
    assert report["ruleset-bypass"]["status"] == "ok"
    assert proc.returncode == 0, proc.stdout


@pytest.mark.parametrize(
    ("include", "exclude", "expected"),
    [
        (["~DEFAULT_BRANCH"], [], True),
        (["~ALL"], [], True),
        (["refs/heads/main"], [], True),
        (["refs/heads/dev"], [], False),
        ([], [], False),
        (["~DEFAULT_BRANCH"], ["~DEFAULT_BRANCH"], False),
        (["~ALL"], ["~DEFAULT_BRANCH"], False),
        (["~ALL"], ["refs/heads/main"], False),
        (["~ALL"], ["refs/heads/dev"], True),
    ],
)
def test_ac1_targets_default_branch(include, exclude, expected):
    """REQ-002 AC1: rule 5 (`~ALL` includes the default branch; an exclude removes it)."""
    ruleset = {"conditions": {"ref_name": {"include": include, "exclude": exclude}}}
    assert targets_default(ruleset, "main") is expected
