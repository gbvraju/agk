"""Tests of scripts/agk/facts.py (SPEC-0009 rules 1-15, 20, 22). No network, no model, no `gh`.

Each case of `fixtures/facts/<case>/` holds `tree/` (the repository files), `api/` (recorded API
responses), `case.json` (arguments) and `facts.json` (the golden document). A golden is changed only
by a person who runs `python3 tests/kit/test_facts.py --write-goldens`; no test rewrites one.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
FIXTURES = Path(__file__).parent / "fixtures" / "facts"
FACTS = SCRIPTS / "facts.py"
CASES = sorted(p.name for p in FIXTURES.iterdir() if p.is_dir())
ENV_GIT = {
    "GIT_AUTHOR_NAME": "fixture",
    "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
    "GIT_COMMITTER_NAME": "fixture",
    "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    "GIT_AUTHOR_DATE": "2026-10-01T12:00:00+0000",
    "GIT_COMMITTER_DATE": "2026-10-01T12:00:00+0000",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}
DROP = ("GITHUB_BASE_REF", "AGK_BASE", "CI", "AGK_KIT_TESTS", "GITHUB_REPOSITORY")
SHA11 = "0b" + "c" * 38
SECTIONS = (
    "config requirements markers specs adrs residuals questions pull_requests issues drift"
).split()


def git(root: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if k not in DROP} | ENV_GIT
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True, env=env
    )
    return proc.stdout


def build_repo(case: str, dest: Path, skip: tuple[str, ...] = ()) -> Path:
    """The case's tree, committed once with fixed identity and date, then its `modify` applied."""
    root = dest / "work"
    shutil.copytree(FIXTURES / case / "tree", root)
    for rel in skip:
        (root / rel).unlink()
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "fixture")
    meta = json.loads((FIXTURES / case / "case.json").read_text())
    for rel, extra in meta.get("modify", {}).items():
        with (root / rel).open("a", encoding="utf-8") as handle:
            handle.write(extra)
    return root


def no_gh_path(dest: Path) -> str:
    """A PATH holding `git` and no `gh`."""
    bin_dir = dest / "bin"
    bin_dir.mkdir(exist_ok=True)
    link = bin_dir / "git"
    if not link.exists():
        link.symlink_to(shutil.which("git"))
    return str(bin_dir)


def run_facts(root: Path, case: str, dest: Path, *extra: str, api: bool | None = None):
    meta = json.loads((FIXTURES / case / "case.json").read_text())
    args = ["--today", meta["today"], "--weeks", str(meta["weeks"]), *meta["args"]]
    if meta["api"] if api is None else api:
        args += ["--api-dir", str(FIXTURES / case / "api")]
    env = {k: v for k, v in os.environ.items() if k not in DROP} | ENV_GIT
    env["PATH"] = no_gh_path(dest)
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(FACTS), *args, *extra, str(root)],
        capture_output=True,
        text=True,
        env=env,
    )


def document(case: str, dest: Path, skip: tuple[str, ...] = (), **kw) -> dict:
    root = build_repo(case, dest, skip)
    proc = run_facts(root, case, dest, **kw)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def has_unknown(value) -> bool:
    if isinstance(value, dict):
        return any(has_unknown(v) for v in value.values())
    if isinstance(value, list):
        return any(has_unknown(v) for v in value)
    return value == "unknown"


# --- rules 4, 22: determinism and the goldens -------------------------------------------------


@pytest.mark.parametrize("case", CASES)
def test_ac2_each_case_is_byte_identical_twice_and_equals_its_golden(case, tmp_path):
    """REQ-018 AC2: rules 4 and 22."""
    root = build_repo(case, tmp_path)
    first = run_facts(root, case, tmp_path)
    second = run_facts(root, case, tmp_path)
    assert first.returncode == 0, first.stdout + first.stderr
    assert first.stdout == second.stdout
    golden = (FIXTURES / case / "facts.json").read_text(encoding="utf-8")
    assert first.stdout == golden


def test_ac2_the_document_has_the_fixed_keys_sorted_and_one_trailing_newline(tmp_path):
    """REQ-018 AC2: rules 3 and 4."""
    root = build_repo("ok", tmp_path)
    out = run_facts(root, "ok", tmp_path).stdout
    doc = json.loads(out)
    assert list(doc) == sorted(doc)
    assert set(doc) == {"schema", "commit", "dirty", "today", "repo", *SECTIONS}
    assert doc["schema"] == 1
    assert doc["commit"] == git(root, "rev-parse", "HEAD").strip()
    assert out.endswith("}\n") and not out.endswith("\n\n")
    assert out == json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    assert str(tmp_path) not in out


def test_ac2_a_tracked_change_sets_dirty_and_a_clean_tree_does_not(tmp_path):
    """REQ-018 AC2: rule 3."""
    assert document("ok", tmp_path / "a")["dirty"] is False
    assert document("dirty", tmp_path / "b")["dirty"] is True


def test_ac2_it_reads_only_and_leaves_the_work_tree_alone(tmp_path):
    """REQ-018 AC2: rule 2."""
    root = build_repo("ok", tmp_path)
    before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
    stamps = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
    run_facts(root, "ok", tmp_path)
    after = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
    assert before == after
    assert {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()} == stamps
    assert git(root, "status", "--porcelain") == ""


# --- rules 5, 22: unknown, never a default ----------------------------------------------------


def test_ac2_the_baseline_of_the_ok_case_has_no_unknown(tmp_path):
    """REQ-018 AC2: rule 5 (the removals below start from a document without any)."""
    doc = document("ok", tmp_path)
    assert not has_unknown({k: v for k, v in doc.items() if k != "repo"})


@pytest.mark.parametrize(
    ("remove", "expected"),
    [
        ("docs/runs/residuals.md", {"residuals"}),
        ("docs/runs/decisions-log.md", {"questions", "specs"}),
        ("agk.toml", {"config", "markers", "drift"}),
        ("docs/requirements.md", {"requirements"}),
    ],
)
def test_ac2_removing_a_source_makes_exactly_its_sections_unknown(tmp_path, remove, expected):
    """REQ-018 AC2: rules 5 and 22 (the work tree is rebuilt without the file)."""
    baseline = document("ok", tmp_path / "base")
    doc = document("ok", tmp_path / "removed", skip=(remove,))
    for key in doc:
        if key == "commit":
            continue
        if key in expected:
            assert has_unknown(doc[key]), key
        else:
            assert doc[key] == baseline[key], key


def test_ac2_without_gh_exactly_the_github_sections_are_unknown(tmp_path):
    """REQ-018 AC2: rules 5 and 22 (`gh` is not on PATH and no --api-dir is given)."""
    baseline = document("ok", tmp_path / "base")
    doc = document("ok", tmp_path / "none", api=False)
    assert doc["pull_requests"] == "unknown" and doc["issues"] == "unknown"
    assert doc["drift"]["counts"]["D6"] == "unknown" and doc["drift"]["total"] == "unknown"
    assert all(doc["drift"]["counts"][k] != "unknown" for k in ("D1", "D2", "D3", "D4", "D5", "D7"))
    for key in doc:
        if key not in ("pull_requests", "issues", "drift"):
            assert doc[key] == baseline[key], key


def test_ac2_a_missing_number_is_never_filled_with_zero(tmp_path):
    """REQ-018 AC2: rule 5. The offline case reads `unknown` where the source is missing."""
    doc = document("offline", tmp_path)
    assert doc["pull_requests"] == "unknown" and doc["issues"] == "unknown"
    assert doc["drift"]["total"] == "unknown"


# --- rule 6: exit codes and refusals ----------------------------------------------------------


def test_ac2_refusals_exit_one_before_any_output_and_name_a_path_class(tmp_path):
    """REQ-018 AC2: rule 6."""
    env = {k: v for k, v in os.environ.items() if k not in DROP} | ENV_GIT
    missing = tmp_path / "does-not-exist"
    plain = tmp_path / "plain"
    plain.mkdir()
    empty = tmp_path / "empty"
    empty.mkdir()
    git(empty, "init", "-q", "-b", "main")
    for target, words in ((missing, "directory"), (plain, "git work tree"), (empty, "no commit")):
        proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(FACTS), str(target)], capture_output=True, text=True, env=env
        )
        assert proc.returncode == 1 and words in proc.stdout, proc.stdout + proc.stderr
        assert "path class: root" in proc.stdout and str(tmp_path) not in proc.stdout


@pytest.mark.parametrize(
    "args", [["--today", "2026-13-01"], ["--weeks", "0"], ["--weeks", "x"], ["--nope"]]
)
def test_ac2_bad_arguments_exit_two_with_the_usage(args, tmp_path):
    """REQ-018 AC2: rule 6."""
    root = build_repo("empty", tmp_path)
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(FACTS), *args, str(root)], capture_output=True, text=True
    )
    assert proc.returncode == 2 and "usage: facts.py" in proc.stderr and proc.stdout == ""


def test_ac2_today_defaults_to_the_current_utc_date_and_weeks_to_eight(tmp_path):
    """REQ-018 AC2: rules 1 and 14."""
    root = build_repo("empty", tmp_path)
    env = {k: v for k, v in os.environ.items() if k not in DROP} | ENV_GIT
    env["PATH"] = no_gh_path(tmp_path)
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(FACTS), str(root)], capture_output=True, text=True, env=env
    )
    from datetime import UTC, datetime

    assert json.loads(proc.stdout)["today"] == datetime.now(UTC).date().isoformat()


# --- rules 7 to 15: the sections --------------------------------------------------------------


def test_ac2_config_copies_only_the_five_values(tmp_path):
    """REQ-018 AC2: rule 7."""
    ok = document("ok", tmp_path / "a")["config"]
    assert ok == {
        "default_branch": "main",
        "test_dirs": ["tests"],
        "test_patterns": ["probe_*.py"],
        "inbox_hours": 48,
        "project_tests_declared": True,
    }
    assert "project_tests" not in ok
    assert document("empty", tmp_path / "b")["config"]["project_tests_declared"] is False


def test_ac2_requirements_titles_statuses_and_criteria(tmp_path):
    """REQ-018 AC2: rule 8; REQ-015 AC1: the criteria as read."""
    doc = document("ok", tmp_path)["requirements"]
    first = doc[0]
    assert (first["id"], first["title"], first["status"]) == ("REQ-001", "First thing", "done")
    assert [c["id"] for c in first["criteria"]] == ["AC1", "AC2"]
    assert first["criteria"][1]["text"] == "given d, when e, then f"
    assert first["criteria_form"] == "structured" and first["line"] == 3


def test_ac2_unstructured_and_duplicate_acceptance(tmp_path):
    """REQ-018 AC2: rule 8 (no invented criterion; a duplicate number is unknown)."""
    reqs = document("unstructured-acceptance", tmp_path / "a")["requirements"]
    assert [(r["criteria"], r["criteria_form"]) for r in reqs] == [
        ([], "unstructured"),
        ([], "unstructured"),
        ([{"id": "AC1", "text": "a"}], "structured"),
    ]
    assert reqs[2]["status"] == "unknown"
    dup = document("duplicate-ac", tmp_path / "b")["requirements"]
    assert dup[0]["criteria"] == "unknown"


def test_ac2_markers_attach_the_ac_to_every_requirement_of_a_run(tmp_path):
    """REQ-018 AC2: rule 9."""
    markers = document("multi-req-marker", tmp_path)["markers"]
    got = {(m["file"], m["line"], m["req"], m["ac"]) for m in markers}
    assert ("tests/probe_multi.py", 1, "REQ-001", "AC2") in got
    assert ("tests/probe_multi.py", 1, "REQ-002", "AC2") in got
    assert ("tests/probe_multi.py", 2, "REQ-003", "AC1") in got
    assert ("tests/probe_multi.py", 2, "REQ-004", "AC1") in got
    assert ("tests/probe_multi.py", 3, "REQ-006", "AC3") in got
    assert ("tests/probe_multi.py", 3, "REQ-005", "AC3") in got
    assert ("tests/probe_multi.py", 3, "REQ-007", None) in got
    keys = [(m["file"], m["line"], m["req"], m["ac"] or "") for m in markers]
    assert keys == sorted(keys)


def test_ac1_markers_in_a_go_tree_with_slash_comments(tmp_path):
    """REQ-016 AC1: rule 9 and the `go-style` case (the pilot's test_patterns and test_dirs)."""
    doc = document("go-style", tmp_path)
    got = [(m["file"], m["line"], m["req"], m["ac"]) for m in doc["markers"]]
    assert got == [
        ("pkg/bar_test.go", 4, "REQ-002", "AC1"),
        ("pkg/foo_test.go", 3, "REQ-001", "AC1"),
    ]
    assert doc["config"]["test_patterns"] == ["*_test.go"]


def test_ac2_specs_and_open_questions(tmp_path):
    """REQ-018 AC2: rule 10."""
    specs = document("ok", tmp_path)["specs"]
    assert [s["id"] for s in specs] == ["SPEC-0001", "SPEC-0002"]
    assert specs[0]["status"] == "Approved" and specs[0]["notes"] is None
    assert specs[0]["requirements"] == ["REQ-001"] and specs[0]["open_questions"] == []
    assert specs[1]["status"] == "Draft" and specs[1]["notes"] == "docs/runs/spec-0002-notes.md"
    assert specs[1]["open_questions"] == ["Q-X1-1"]


def test_ac2_adrs_fields(tmp_path):
    """REQ-018 AC2: rule 11."""
    adrs = document("ok", tmp_path)["adrs"]
    first, second = adrs
    assert first["id"] == "ADR-0001" and first["status"] == "Accepted"
    assert first["amends"] == ["ADR-0002"] and first["requirements"] == ["REQ-001"]
    assert first["protected_classes"] == ["scripts/agk/", ".claude/"]
    assert first["date"] == "2026-09-01" and first["title"] == "Demo"
    assert second["status"] == "Proposed" and second["amends"] == []
    assert second["protected_classes"] == []


def test_ac2_residual_forms(tmp_path):
    """REQ-018 AC2: rule 12."""
    rows = document("residual-forms", tmp_path)["residuals"]
    by_text = {r["text"].split(" (due")[0].split(" |")[0][:40]: r for r in rows}
    dated = next(r for r in rows if r["text"].startswith("2026-10-01: nothing"))
    assert (dated["due"], dated["state"], dated["source"]) == (
        "2027-01-01",
        "open",
        "docs/specs/0001-demo.md",
    )
    assert next(r for r in rows if "undated item" in r["text"])["due"] is None
    assert next(r for r in rows if "bad date" in r["text"])["due"] == "unknown"
    assert next(r for r in rows if "free text" in r["text"])["due"] is None
    assert "continued on a second line" in next(r for r in rows if "free text" in r["text"])["text"]
    register = [r for r in rows if r["source"] == "docs/runs/residuals.md"]
    assert {r["state"] for r in register} == {"open", "closed"}
    assert next(r for r in register if r["text"].startswith("has | a pipe"))["due"] == "2026-06-01"
    assert next(r for r in register if "no date here" in r["text"])["due"] == "unknown"
    assert [r["state"] for r in register if r["state"] == "closed"] == ["closed", "closed"]
    assert by_text


def test_ac2_question_states(tmp_path):
    """REQ-018 AC2: rule 13."""
    found = {q["id"]: q for q in document("question-forms", tmp_path)["questions"]}
    assert found["Q-X1-2"]["ruled"] is True and found["Q-X1-2"]["named_in_log"] is True
    assert found["Q-X1-3"]["ruled"] is False and found["Q-X1-3"]["named_in_log"] is True
    assert found["Q-X1-1"]["open_in"] == ["docs/runs/spec-0002-notes.md"]
    assert found["Q-X1-4"]["open_in"] == [] and found["Q-X1-4"]["ruled"] is False
    assert found["Q-X1-5"]["open_in"] == ["docs/runs/spec-0001-notes.md"]
    assert found["Q-X1-6"]["open_in"] == ["docs/adr/0002-proposed.md"]
    assert found["Q-X1-7"]["open_in"] == [] and found["Q-X1-7"]["named_in_log"] is False
    assert found["Q-X1-1"]["files"] == [
        "docs/runs/other.md",
        "docs/runs/spec-0002-notes.md",
    ]
    assert found["Q-X1-10"]["ruled"] is False  # `Q-X1-1 ruled` must not match `Q-X1-10`
    assert list(found) == sorted(found)


def pulls(tmp_path) -> dict[int, dict]:
    return {p["number"]: p for p in document("pr-states", tmp_path)["pull_requests"]}


def test_ac2_pull_request_set_and_states(tmp_path):
    """REQ-018 AC2: rule 14 (open plus the window; sorted by number)."""
    found = pulls(tmp_path)
    assert list(found) == [11, 12, 13, 14, 15, 16, 18, 19]  # 17 closed before the window
    assert found[18]["state"] == "open" and found[19]["state"] == "open"
    assert found[11]["state"] == "merged" and found[12]["state"] == "closed"
    assert found[11]["files"] == ["a/b.txt", "z.txt"]
    assert found[19]["files"] == "unknown" and found[19]["head"] == "13" + "c" * 38
    assert found[11]["base"] == "main"


def test_ac2_verdicts_are_in_time_order_by_the_first_line(tmp_path):
    """REQ-018 AC2: rule 14 (a later line or a short sha is not a verdict)."""
    found = pulls(tmp_path)
    assert [(v["kind"], v["sha"]) for v in found[11]["verdicts"]] == [
        ("fix", None),
        ("cleared", SHA11[:7]),
    ]
    assert [v["at"] for v in found[11]["verdicts"]] == [
        "2026-10-06T12:00:00Z",
        "2026-10-08T12:00:00Z",
    ]
    assert [v["kind"] for v in found[12]["verdicts"]] == ["rejected"]
    assert found[13]["verdicts"] == [] and found[19]["verdicts"] == "unknown"


def test_ac2_behaviour_is_read_from_a_line_outside_a_fence(tmp_path):
    """REQ-018 AC2: rule 14; ADR-0021 criterion e (nothing else is read from a body)."""
    found = pulls(tmp_path)
    assert found[18]["behaviour"] == "unchanged"  # a line of the body
    assert found[15]["behaviour"] == "unchanged"
    assert found[13]["behaviour"] is None  # inside a code fence
    assert found[14]["behaviour"] is None  # an indented line is not the declaration
    assert found[12]["behaviour"] is None  # another value is not a declaration
    assert found[19]["behaviour"] is None  # an empty description
    assert found[11]["behaviour"] is None


def test_ac2_proof_is_the_one_outcome_step_that_succeeded(tmp_path):
    """REQ-018 AC2: rule 14 and SPEC-0010 rule 17 (all four outcomes; two winners; no run)."""
    found = pulls(tmp_path)
    assert found[11]["proof"] == "proven" and found[12]["proof"] == "not-proven"
    assert found[14]["proof"] == "skipped" and found[15]["proof"] == "unknown"
    assert found[16]["proof"] == "unknown"  # two succeeded outcome steps
    assert found[13]["proof"] == "unknown"  # the only run is not named `proof`
    assert found[19]["proof"] == "unknown"  # no run recorded
    assert found[18]["proof"] == "proven"


def test_ac2_issues_are_listed_by_label_without_their_bodies(tmp_path):
    """REQ-018 AC2: rule 15."""
    issues = document("ok", tmp_path)["issues"]
    assert issues == [
        {"number": 3, "title": "agk metrics 2026-W41", "label": "agk-metrics", "state": "closed"}
    ]


# --- rule 15 `drift`: the audit's own counts --------------------------------------------------


def drift_repo(dest: Path) -> Path:
    sys.path.insert(0, str(Path(__file__).parent))
    import drift_fixtures as fx

    root = dest / "drift"
    repo = fx.base(root)
    fx.add_protected_change(repo, 3)
    repo.edit("docs/requirements.md", "- Status: planned", "- Status: done")
    repo.commit(2, "mark done with no marker")
    fx.draft_spec(repo, 30)
    fx.overdue_adr_residual(repo)
    repo.write(".github/CODEOWNERS", "* @someone\n")
    repo.commit(1, "hand edit")
    return root


def drift_counts(root: Path, tmp_path: Path, issues: list[int] | None):
    api = tmp_path / "api"
    api.mkdir(parents=True)
    for name in ("pulls-open", "pulls"):
        (api / f"{name}.json").write_text("[]")
    for label in ("agk-metrics", "agk-product-report"):
        (api / f"issues-{label}.json").write_text("[]")
    listed = [{"number": n, "title": "audit", "state": "open"} for n in issues or []]
    (api / "issues-agk-drift-audit.json").write_text(json.dumps(listed))
    env = {k: v for k, v in os.environ.items() if k not in DROP} | ENV_GIT
    env["PATH"] = no_gh_path(tmp_path)
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(FACTS), "--today", "2026-10-15", "--api-dir", str(api), str(root)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)["drift"]


def test_ac2_drift_counts_equal_the_audit_with_and_without_open_audit_issues(tmp_path):
    """REQ-018 AC2: rule 15. The counts are the audit's findings, called and not recounted."""
    import drift_audit

    root = drift_repo(tmp_path)
    found, _ = drift_audit.audit(root, __import__("datetime").date(2026, 10, 15), "main", [])
    expected = {c: sum(1 for f in found if f.code == c) for c in drift_audit.CODES}
    assert list(expected) == ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]
    assert all(expected[c] >= 1 for c in ("D1", "D2", "D3", "D4", "D5", "D7")), expected
    total = len(found)
    without = drift_counts(root, tmp_path / "a", None)
    assert without == {"counts": expected, "total": total}
    assert without["counts"]["D6"] == 0
    duplicated = drift_counts(root, tmp_path / "b", [10, 11])
    assert duplicated["counts"]["D6"] == 1 and duplicated["total"] == total + 1
    single = drift_counts(root, tmp_path / "c", [10])
    assert single["counts"]["D6"] == 0 and single["total"] == total


# --- rules 16, 18: reuse, never re-parse ------------------------------------------------------


def test_ac2_facts_imports_the_parsers_it_reuses_and_copies_no_pattern():
    """REQ-018 AC2: rule 16 (the import list is asserted by reading the script)."""
    source = FACTS.read_text(encoding="utf-8")
    for needle in (
        "import check_adrs",
        "import check_specs",
        "import drift_audit",
        "import metrics",
        "find_ac_markers",
        "parse_acceptance",
        "parse_requirements",
        "load_config",
        "check_specs.status_of",
        "check_adrs.status_of",
        "check_adrs.FIELD_RE",
        "check_adrs.FILE_RE",
        "check_adrs.TITLE_RE",
        "drift_audit.residual_bullets",
        "drift_audit.DUE",
        "drift_audit.parse_date",
        "drift_audit.register_lines",
        "drift_audit.audit",
        "metrics.verdicts",
        "metrics.Gh",
        "metrics.ApiDir",
    ):
        assert needle in source, needle
    assert "Verdict:" not in source and "VERDICT" not in source  # the rule is metrics'
    assert "def d1" not in source and "d4_" not in source


def test_ac2_facts_writes_nothing_and_never_posts_or_prints_a_credential():
    """REQ-018 AC2: rule 2 (static reading of the script; GitHub is read through metrics)."""
    source = FACTS.read_text(encoding="utf-8")
    for needle in ("write_text", ".write_bytes", "open(", "POST", "PATCH", "token", "TOKEN"):
        assert needle not in source, needle
    assert '["gh"' not in source and "gh api" not in source.split('"""', 2)[2]
    assert "subprocess.run" in source and '"status", "--porcelain"' in source


def test_ac2_it_counts_nothing_the_existing_scripts_count():
    """REQ-018 AC2: rule 18 (no metrics field, no test count)."""
    doc_keys = set(json.loads((FIXTURES / "ok" / "facts.json").read_text()))
    assert not doc_keys & {"tests_before", "tests_after", "metrics"}


# --- regenerating the goldens (by a person, never by a test) ----------------------------------

if __name__ == "__main__":  # pragma: no cover
    import tempfile

    if sys.argv[1:] != ["--write-goldens"]:
        raise SystemExit("usage: python3 tests/kit/test_facts.py --write-goldens")
    for name in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            proc = run_facts(build_repo(name, work), name, work)
            if proc.returncode != 0:
                raise SystemExit(f"{name}: {proc.stdout}{proc.stderr}")
            (FIXTURES / name / "facts.json").write_text(proc.stdout, encoding="utf-8")
            print("wrote", name)
