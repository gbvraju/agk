"""Tests of `check_acceptance.py` (SPEC-0051 rules 2 to 5 and 7, build (b); REQ-058).

A record quotes its goals from the discovery document's `success` answer and names evidence that
exists; a refusal names the rule and the file and never a quote, a value or an answer. Fixtures in
`tmp_path` only: invented data (`example.com`), no network, and no test runs a piece of evidence.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
SCRIPT = SCRIPTS / "check_acceptance.py"
SLUG = "example-signup"
REL = f"docs/acceptance/{SLUG}.md"
Q1 = "Zanzibar signups reach ten a day"
Q2 = "the Quokka report is sent weekly"
ANSWER = f"{Q1}, and {Q2}."
HIDDEN = ("Zanzibar", "Quokka", "signups", "weekly")
DEFINED = "test tests/test_example.py::test_signup"


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args, "--root", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def discovery(root: Path, answer: str | None, title: str = "Example signup") -> str:
    """Writes the document with the real `front_door.py discovery-write`; returns the digest."""
    issue = root / "issue.json"
    answers = root / "answers.json"
    body = "Problem: invented signups at example.com"
    issue.write_text(
        json.dumps(
            {
                "title": title,
                "html_url": "https://example.com/issues/1",
                "labels": [{"name": "agk-problem"}],
                "body": body,
            }
        ),
        encoding="utf-8",
    )
    where = "https://example.com/issues/1#c1"
    rows = [] if answer is None else [{"id": "success", "answer": answer, "where": where}]
    answers.write_text(json.dumps({"answers": rows}), encoding="utf-8")
    done = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [
            sys.executable,
            str(SCRIPTS / "front_door.py"),
            "discovery-write",
            "--issue",
            str(issue),
            "--answers",
            str(answers),
            "--root",
            str(root),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    issue.unlink()
    answers.unlink()
    return digest_of(answer or "")


def digest_of(words: str) -> str:
    return hashlib.sha256(words.encode("utf-8")).hexdigest()


def record(
    digest: str,
    goals: list[str] | None = None,
    status: str = "proposed",
    title: str = "Example signup",
) -> str:
    rows = (
        [f'- G-1: "{Q1}" -> {DEFINED}', f'- G-2: "{Q2}" -> not met'] if goals is None else goals
    )
    return "\n".join(
        [
            f"# Acceptance: {title}",
            "",
            f"- Discovery: docs/discovery/{SLUG}.md",
            f"- Success digest: {digest}",
            f"- Status: {status}",
            "",
            "## Goals",
            "",
            *rows,
            "",
        ]
    )


def write(root: Path, text: str, name: str = REL) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def project(tmp_path: Path) -> Path:
    write(tmp_path, "def test_signup():\n    assert True\n", "tests/test_example.py")
    write(tmp_path, "count: 3\n", "docs/runs/run-1.md")
    write(tmp_path, "count: 1\n", "docs/runs/demo-1.md")
    return tmp_path


def refused(result: subprocess.CompletedProcess, rule: int, name: str = REL) -> None:
    """Exactly one line, naming the rule and the file, and holding no word of the answer."""
    lines = result.stdout.strip().splitlines()
    assert result.returncode == 1, result.stdout + result.stderr
    assert len(lines) == 1, result.stdout
    assert lines[0].startswith(f"FAIL acceptance: rule {rule}: {name}: "), lines[0]
    for word in HIDDEN:
        assert word not in result.stdout + result.stderr


def test_ac1_a_good_record_passes(project: Path):
    """REQ-058 AC1: rules 2 to 5, two goals, one with a test that exists and one `not met`."""
    write(project, record(discovery(project, ANSWER)))
    result = run(project)
    assert result.returncode == 0, result.stdout
    assert result.stdout == "ok acceptance (1 records)\n"


def test_ac1_every_kind_of_evidence_and_several_items_pass(project: Path):
    """REQ-058 AC1: rules 3 and 4, the three kinds, separated by a comma and a space."""
    goals = [
        f'- G-1: "{Q1}" -> {DEFINED}, run docs/runs/run-1.md',
        f'- G-2: "{Q2}" -> demo docs/runs/demo-1.md',
    ]
    write(project, record(discovery(project, ANSWER), goals))
    result = run(project)
    assert result.returncode == 0, result.stdout


def test_ac1_a_method_of_a_test_class_is_a_test_function(project: Path):
    """REQ-058 AC1: rule 4, a test defined in a class of the file."""
    source = "class TestSignup:\n    def test_inner(self):\n        assert True\n"
    write(project, source, "tests/test_class.py")
    goals = [
        f'- G-1: "{Q1}" -> test tests/test_class.py::test_inner',
        f'- G-2: "{Q2}" -> not met',
    ]
    write(project, record(discovery(project, ANSWER), goals))
    assert run(project).returncode == 0


def test_ac1_a_test_file_of_the_testing_map_counts(project: Path):
    """REQ-058 AC1: rule 4, a file outside `tests/` that the `[testing]` map of agk.toml lists."""
    write(project, "def test_mapped():\n    assert True\n", "checks/verify_signup.py")
    write(
        project,
        '[testing]\nmap = [{ code = "src/*.py", tests = ["checks/verify_*.py"] }]\n',
        "agk.toml",
    )
    goals = [
        f'- G-1: "{Q1}" -> test checks/verify_signup.py::test_mapped',
        f'- G-2: "{Q2}" -> not met',
    ]
    write(project, record(discovery(project, ANSWER), goals))
    result = run(project)
    assert result.returncode == 0, result.stdout


def test_ac2_no_record_prints_zero_records(tmp_path: Path):
    """REQ-058 AC2: rule 5, a project with no record, with and without the folder."""
    result = run(tmp_path)
    assert (result.returncode, result.stdout) == (0, "ok acceptance (0 records)\n")
    (tmp_path / "docs" / "acceptance").mkdir(parents=True)
    result = run(tmp_path)
    assert (result.returncode, result.stdout) == (0, "ok acceptance (0 records)\n")


@pytest.mark.parametrize("answer", [None, "not known yet", "Not known yet."])
def test_ac2_an_answer_with_no_goals_fails_naming_the_rule(project: Path, answer: str | None):
    """REQ-058 AC2: rule 2, an `open` or `not known yet` success answer has no goals."""
    discovery(project, answer)
    write(project, record(digest_of(ANSWER)))
    refused(run(project), 2)


def test_ac1_a_discovery_document_that_does_not_exist_fails(project: Path):
    """REQ-058 AC1: rule 5, the record names a document that is not there."""
    write(project, record(digest_of(ANSWER)))
    refused(run(project), 3)


def test_ac1_a_discovery_document_that_fails_its_own_check_fails(project: Path):
    """REQ-058 AC1: rule 5, an answer edited under its digest is not read."""
    digest = discovery(project, ANSWER)
    path = project / "docs" / "discovery" / f"{SLUG}.md"
    path.write_text(path.read_text(encoding="utf-8").replace("ten a day", "nine"), encoding="utf-8")
    write(project, record(digest))
    refused(run(project), 2)


def test_ac1_a_digest_of_another_answer_is_stale(project: Path):
    """REQ-058 AC1: rules 2 and 5, the answer changed after the record was written."""
    discovery(project, ANSWER)
    write(project, record(digest_of("an earlier invented answer")))
    result = run(project)
    refused(result, 2)
    assert "stale" in result.stdout


def _swap(old: str, new: str):
    return lambda text: text.replace(old, new, 1)


def _drop(start: str):
    return lambda text: "\n".join(ln for ln in text.split("\n") if not ln.startswith(start))


FORM = {
    "title-missing": _drop("# Acceptance:"),
    "title-not-the-documents": _swap("# Acceptance: Example signup", "# Acceptance: Another"),
    "discovery-missing": _drop("- Discovery:"),
    "discovery-names-another": _swap(f"discovery/{SLUG}.md", "discovery/another.md"),
    "digest-missing": _drop("- Success digest:"),
    "digest-malformed": _swap("- Success digest: ", "- Success digest: x"),
    "status-missing": _drop("- Status:"),
    "status-unknown": _swap("- Status: proposed", "- Status: done"),
    "status-repeated": _swap("- Status: proposed", "- Status: proposed\n- Status: proposed"),
    "goals-missing": _swap("## Goals", "## Other"),
    "goals-repeated": _swap("## Goals\n", "## Goals\n\n## Goals\n"),
    "goals-empty": _drop("- G-"),
    "goal-malformed": _swap('- G-2: "', '- G-2 "'),
    "line-in-goals": _swap("## Goals\n", "## Goals\n\nSome words.\n"),
}


@pytest.mark.parametrize("name", sorted(FORM))
def test_ac1_a_form_problem_fails_naming_rule_3(project: Path, name: str):
    """REQ-058 AC1: rules 3 and 5, a missing or wrong line or section."""
    write(project, FORM[name](record(discovery(project, ANSWER))))
    refused(run(project), 3)


def test_ac1_a_file_name_that_is_no_slug_fails(project: Path):
    """REQ-058 AC1: rule 3, a record is `docs/acceptance/<slug>.md`."""
    text = record(discovery(project, ANSWER)).replace(SLUG, "Not_A_Slug")
    write(project, text, "docs/acceptance/Not_A_Slug.md")
    refused(run(project), 3, "docs/acceptance/Not_A_Slug.md")


GOALS = {
    "quote-not-in-answer": [f'- G-1: "{Q1}" -> not met', '- G-2: "Zanzibar invented" -> not met'],
    "repeated-quote": [f'- G-1: "{Q1}" -> not met', f'- G-2: "{Q1}" -> not met'],
    "repeated-goal": [f'- G-1: "{Q1}" -> not met', f'- G-1: "{Q2}" -> not met'],
    "a-part-left-out": [f'- G-1: "{Q1}" -> not met'],
    "words-between": ['- G-1: "Zanzibar signups" -> not met', f'- G-2: "{Q2}" -> not met'],
    "out-of-order": [f'- G-1: "{Q2}" -> not met', f'- G-2: "{Q1}" -> not met'],
    "numbering-gap": [f'- G-1: "{Q1}" -> not met', f'- G-3: "{Q2}" -> not met'],
    "numbering-not-from-one": [f'- G-2: "{Q1}" -> not met', f'- G-3: "{Q2}" -> not met'],
    "a-word-cut": [f'- G-1: "{Q1[:-1]}" -> not met', f'- G-2: "{Q2}" -> not met'],
    "a-quote-with-no-word": [
        f'- G-1: "{Q1}" -> not met',
        '- G-2: "," -> not met',
        f'- G-3: "{Q2}" -> not met',
    ],
}


@pytest.mark.parametrize("name", sorted(GOALS))
def test_ac1_a_wrong_quote_or_goal_fails_naming_rule_2(project: Path, name: str):
    """REQ-058 AC1: rules 2 and 5, the quotes must be the answer, once each and in order."""
    write(project, record(discovery(project, ANSWER), GOALS[name]))
    refused(run(project), 2)


def test_ac1_a_goal_both_met_and_not_met_fails(project: Path):
    """REQ-058 AC1: rule 3, a goal is `not met` or has evidence, never both."""
    goals = [f'- G-1: "{Q1}" -> not met, {DEFINED}', f'- G-2: "{Q2}" -> not met']
    write(project, record(discovery(project, ANSWER), goals))
    refused(run(project), 3)


EVIDENCE = {
    "unknown-kind": "recording docs/runs/run-1.md",
    "an-outside-link": "https://example.com/video",
    "a-persons-statement": "the owner said so",
    "test-file-missing": "test tests/test_absent.py::test_signup",
    "test-name-not-defined": "test tests/test_example.py::test_absent",
    "test-form": "test tests/test_example.py",
    "test-outside-tests-and-map": "test docs/runs/run-1.py::test_signup",
    "test-climbs-out": "test tests/../../outside.py::test_signup",
    "test-absolute": "test /etc/outside.py::test_signup",
    "run-missing": "run docs/runs/absent.md",
    "run-elsewhere": "run tests/test_example.py",
    "run-climbs-out": "run docs/runs/../../outside.md",
    "demo-missing": "demo docs/runs/absent.md",
    "demo-in-a-subfolder": "demo docs/runs/deep/demo-1.md",
    "second-item-bad": f"{DEFINED}, run docs/runs/absent.md",
}


@pytest.mark.parametrize("name", sorted(EVIDENCE))
def test_ac1_evidence_that_is_wrong_or_absent_fails_naming_rule_4(project: Path, name: str):
    """REQ-058 AC1: rules 4 and 5, three kinds only, and each names a file that exists."""
    goals = [f'- G-1: "{Q1}" -> {EVIDENCE[name]}', f'- G-2: "{Q2}" -> not met']
    write(project, record(discovery(project, ANSWER), goals))
    refused(run(project), 4)


def test_ac1_a_nested_or_helper_function_is_no_test_function(project: Path):
    """REQ-058 AC1: rule 4, only a `test...` function of the module or of a class."""
    source = "def helper():\n    def test_nested():\n        pass\n"
    write(project, source, "tests/test_helpers.py")
    for name in ("helper", "test_nested"):
        goals = [
            f'- G-1: "{Q1}" -> test tests/test_helpers.py::{name}',
            f'- G-2: "{Q2}" -> not met',
        ]
        write(project, record(digest_of(ANSWER), goals))
        if not (project / "docs" / "discovery" / f"{SLUG}.md").exists():
            discovery(project, ANSWER)
        refused(run(project), 4)


@pytest.mark.parametrize(
    ("file", "source"),
    [("tests/test_page.ts", "function test_signup() {}\n"), ("tests/test_bad.py", "def (:\n")],
)
def test_ac1_a_test_file_that_cannot_be_read_as_python_fails(
    project: Path, file: str, source: str
):
    """REQ-058 AC1: rule 4, the conservative reading of Q-762-3 for another language."""
    write(project, source, file)
    goals = [f'- G-1: "{Q1}" -> test {file}::test_signup', f'- G-2: "{Q2}" -> not met']
    write(project, record(discovery(project, ANSWER), goals))
    refused(run(project), 4)


def test_ac1_a_link_that_leaves_the_project_is_not_evidence(project: Path, tmp_path_factory):
    """REQ-058 AC1: rule 4, a symbolic link to a file outside the tree does not exist on it."""
    outside = tmp_path_factory.mktemp("outside") / "run.md"
    outside.write_text("count: 9\n", encoding="utf-8")
    (project / "docs" / "runs" / "linked.md").symlink_to(outside)
    goals = [f'- G-1: "{Q1}" -> run docs/runs/linked.md', f'- G-2: "{Q2}" -> not met']
    write(project, record(discovery(project, ANSWER), goals))
    refused(run(project), 4)


def test_ac3_an_accepted_record_fails_until_the_yes_can_be_read(project: Path):
    """REQ-058 AC3: rule 6, conservatively: no yes can be read before build (c)."""
    goals = [f'- G-1: "{Q1}" -> {DEFINED}', f'- G-2: "{Q2}" -> run docs/runs/run-1.md']
    write(project, record(discovery(project, ANSWER), goals, status="accepted"))
    refused(run(project), 6)


def test_ac7_a_secret_like_value_fails_naming_the_kind_and_the_position(project: Path):
    """REQ-058 AC7: rules 5 and 10, the guard scan of the record, never the value."""
    value = "10.1.2.3"  # an invented private address the data guard finds (kind IP)
    write(project, record(discovery(project, ANSWER)) + f"\n## Notes\n\nNote {value}\n")
    result = run(project)
    refused(result, 5)
    assert "IP" in result.stdout and "line 14 column 6" in result.stdout
    assert value not in result.stdout


def test_ac7_no_evidence_is_run_and_no_network_is_opened(project: Path):
    """REQ-058 AC7: rules 4 and 10, through a stub that fails on a socket or a new process."""
    sentinel = project / "ran.txt"
    source = (
        f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('x')\n"
        "def test_signup():\n    assert True\n"
    )
    write(project, source, "tests/test_example.py")
    write(project, f"touch {sentinel}\n", "docs/runs/run-1.md")
    goals = [f'- G-1: "{Q1}" -> {DEFINED}', f'- G-2: "{Q2}" -> run docs/runs/run-1.md']
    write(project, record(discovery(project, ANSWER), goals))
    stub = (
        "import runpy, socket, subprocess, sys\n"
        "def no(*a, **k):\n    raise RuntimeError('forbidden call')\n"
        "socket.socket = no\nsocket.create_connection = no\nsubprocess.Popen = no\n"
        f"sys.argv = ['check_acceptance.py', '--root', {str(project)!r}]\n"
        f"runpy.run_path({str(SCRIPT)!r}, run_name='__main__')\n"
    )
    result = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-c", stub], capture_output=True, text=True, encoding="utf-8", timeout=60
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "ok acceptance (1 records)\n"
    assert not sentinel.exists()


def tree(root: Path) -> dict[str, bytes]:
    return {str(p): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_ac6_status_prints_the_four_forms_and_writes_nothing(tmp_path: Path):
    """REQ-058 AC6: rule 7, one line per record, read from the files alone."""
    met = [f'- G-1: "{Q1}" -> run docs/runs/run-1.md', f'- G-2: "{Q2}" -> run docs/runs/run-1.md']
    unmet = [f'- G-1: "{Q1}" -> run docs/runs/run-1.md', f'- G-2: "{Q2}" -> not met']
    write(tmp_path, "count: 3\n", "docs/runs/run-1.md")
    cases = {
        "alpha": (met, "accepted", digest_of(ANSWER)),
        "bravo": (unmet, "accepted", digest_of(ANSWER)),
        "charlie": (unmet, "proposed", digest_of(ANSWER)),
        "delta": (met, "accepted", digest_of("an earlier invented answer")),
    }
    for name, (goals, status, digest) in cases.items():
        discovery(tmp_path, ANSWER, title=name)
        text = record(digest, goals, status, title=name).replace(SLUG, name)
        write(tmp_path, text, f"docs/acceptance/{name}.md")
    before = tree(tmp_path)
    result = run(tmp_path, "status")
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == [
        "alpha accepted",
        "bravo accepted with 1 not met",
        "charlie proposed",
        "delta stale",
    ]
    assert tree(tmp_path) == before


def test_ac6_status_never_calls_a_faulty_record_accepted(project: Path):
    """REQ-058 AC6: rule 7, a record the check refuses is not shown as accepted."""
    goals = [f'- G-1: "{Q1}" -> run docs/runs/absent.md', f'- G-2: "{Q2}" -> not met']
    write(project, record(discovery(project, ANSWER), goals, status="accepted"))
    result = run(project, "status")
    assert (result.returncode, result.stdout) == (0, f"{SLUG} proposed\n")


def test_ac2_status_of_an_open_answer_is_stale(project: Path):
    """REQ-058 AC2: rules 2 and 7, an open answer has nothing to accept."""
    discovery(project, None)
    write(project, record(digest_of(ANSWER), status="accepted"))
    result = run(project, "status")
    assert (result.returncode, result.stdout) == (0, f"{SLUG} stale\n")


def test_ac6_status_of_no_record_prints_nothing(tmp_path: Path):
    """REQ-058 AC6: rule 7, no record, no line."""
    result = run(tmp_path, "status")
    assert (result.returncode, result.stdout) == (0, "")


@pytest.mark.parametrize(
    "args", [["--comments"], ["status", "--comments", "file.json"], ["other"], ["--root"]]
)
def test_ac1_a_wrong_command_line_is_a_usage_error(args: list[str]):
    """REQ-058 AC1: rule 5, `--comments` takes a file and belongs to the check, not to `status`."""
    done = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        cwd=KIT_ROOT,
    )
    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stderr.startswith("usage: check_acceptance.py")


def test_ac7_the_check_reads_the_document_through_front_door():
    """REQ-058 AC7: brief answer 3, no second parser, and only installed modules are imported."""
    tree_of = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    names = {
        node.module if isinstance(node, ast.ImportFrom) else alias.name
        for node in ast.walk(tree_of)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    }
    assert "front_door" in names
    allowed = {
        "__future__",
        "front_door",
        "common",
        "impact",
        "reviewers",
        "check_final_clearance",
        "check_specs",
    }
    assert not {n for n in names - allowed if n not in sys.stdlib_module_names}
    assert not {"subprocess", "socket", "urllib", "http"} & names
    text = SCRIPT.read_text(encoding="utf-8")
    assert "agk:answer" not in text  # the markers are front_door's


def test_ac1_the_check_is_wired_in():
    """REQ-058 AC1: brief answer 3, the governance line, the manifest and the testing map."""
    mk = (KIT_ROOT / "agk.mk").read_text(encoding="utf-8")
    recipe = mk.split("agk-governance:\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert "\t$(PY) scripts/agk/check_acceptance.py" in recipe
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    rows = manifest["verbatim"]
    assert "scripts/agk/check_acceptance.py" in rows
    scripts = [r for r in rows if r.startswith("scripts/agk/check_")]
    assert scripts == sorted(scripts)
    table = tomllib.loads((KIT_ROOT / "agk.toml").read_text(encoding="utf-8"))
    entries = [e for e in table["testing"]["map"] if e["code"] == "scripts/agk/check_acceptance.py"]
    assert len(entries) == 1
    assert "tests/kit/test_check_acceptance.py" in entries[0]["tests"]


OWNER = "example-owner"
TEAM_TOML = ""
SOLO_TOML = 'review_mode = "solo"\n'
APP = {"slug": "claude"}
AT = "2026-11-09T12:00:00Z"


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-c", "user.name=Example", "-c", "user.email=a@example.com", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=60,
    ).stdout.strip()


def commit(root: Path) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "--no-gpg-sign", "-m", "invented")
    return git(root, "rev-parse", "HEAD")


def people(root: Path, toml: str = TEAM_TOML) -> None:
    roles = f"version: 1\nverdict_authors: [{OWNER}]\nspec_approvers: [{OWNER}]\n"
    write(root, roles, "config/reviewers.yaml")
    write(root, toml, "agk.toml")


def proposed_then_accepted(root: Path, toml: str = TEAM_TOML) -> str:
    """The record committed as `proposed` (the head a yes names), then its status-only commit."""
    people(root, toml)
    text = record(discovery(root, ANSWER))
    write(root, text)
    git(root, "init", "-q")
    head = commit(root)
    write(root, text.replace("- Status: proposed", "- Status: accepted"))
    commit(root)
    return head


def yes(head: str, slug: str = SLUG) -> str:
    return f"Approve: acceptance {slug} {head}"


def saved(root: Path, *comments: dict) -> str:
    path = root / "comments.json"
    path.write_text(json.dumps(list(comments)), encoding="utf-8")
    return str(path)


def comment(body: str, login: str = OWNER, **more) -> dict:
    return {"user": {"login": login}, "body": body, "created_at": AT, **more}


def confirmed(head: str, *middle: str) -> str:
    shown = ["Shown:", "1. what changes: x", "2. what it risks: y", "3. what stays: z"]
    lines = [f"Confirmed: {head}", f"Verdict: cleared {head}", "", *middle, "", *shown]
    return "\n".join([*lines, f"confirmed by {OWNER} in a session at {AT}"])


def with_comments(root: Path, *comments: dict) -> subprocess.CompletedProcess:
    return run(root, "--comments", saved(root, *comments))


def test_ac3_a_listed_accounts_yes_passes(project: Path):
    """REQ-058 AC3: rule 6, the one line by an account of `spec_approvers`."""
    head = proposed_then_accepted(project)
    result = with_comments(project, comment(yes(head)))
    assert (result.returncode, result.stdout) == (0, "ok acceptance (1 records)\n")


def test_ac3_the_yes_keeps_a_not_met_goal_not_met(project: Path):
    """REQ-058 AC3: rule 6 (Q-S0051-7), the record is accepted as it stands."""
    head = proposed_then_accepted(project)
    assert with_comments(project, comment(yes(head))).returncode == 0
    assert run(project, "status").stdout == f"{SLUG} accepted with 1 not met\n"


@pytest.mark.parametrize(
    "shape",
    ["session", "unlisted", "other-slug", "short-head", "not-first-line", "unknown-head"],
)
def test_ac3_a_line_that_is_no_yes_fails(project: Path, shape: str):
    """REQ-058 AC3: rule 6, an app's identical line, another account, slug or form is nothing."""
    head = proposed_then_accepted(project)
    item = {
        "session": comment(yes(head), performed_via_github_app=APP),
        "unlisted": comment(yes(head), login="someone-else"),
        "other-slug": comment(yes(head, "another-slug")),
        "short-head": comment(yes(head[:12])),
        "not-first-line": comment(f"Looks good.\n{yes(head)}"),
        "unknown-head": comment(yes("a" * 40)),
    }[shape]
    result = with_comments(project, item)
    refused(result, 6)
    assert head not in result.stdout


def test_ac3_solo_a_yes_counts_inside_the_confirmation(project: Path):
    """REQ-058 AC3: rule 6, solo mode, the person's `Confirmed:` comment holds the line."""
    head = proposed_then_accepted(project, SOLO_TOML)
    result = with_comments(project, comment(confirmed(head, yes(head))))
    assert (result.returncode, result.stdout) == (0, "ok acceptance (1 records)\n")


def test_ac3_solo_a_plain_line_counts_for_nothing(project: Path):
    """REQ-058 AC3: rule 6, solo mode, the bare line is not the person's confirmation."""
    head = proposed_then_accepted(project, SOLO_TOML)
    refused(with_comments(project, comment(yes(head))), 6)


def test_ac3_solo_a_session_cannot_post_the_confirmation(project: Path):
    """REQ-058 AC3: rules 6 and session rule 29, a `Confirmed:` posted through an app is nothing."""
    head = proposed_then_accepted(project, SOLO_TOML)
    item = comment(confirmed(head, yes(head)), performed_via_github_app=APP)
    refused(with_comments(project, item), 6)


def test_ac3_solo_the_yes_names_the_confirmed_head(project: Path):
    """REQ-058 AC3: rule 6, solo mode, a line for another head is not what was confirmed."""
    head = proposed_then_accepted(project, SOLO_TOML)
    later = git(project, "rev-parse", "HEAD")
    refused(with_comments(project, comment(confirmed(later, yes(head)))), 6)


def test_ac3_a_record_changed_after_the_yes_fails(project: Path):
    """REQ-058 AC3: rule 6, evidence changed with no new yes."""
    head = proposed_then_accepted(project)
    path = project / REL
    changed = path.read_text(encoding="utf-8").replace(DEFINED, "run docs/runs/run-1.md")
    path.write_text(changed, encoding="utf-8")
    commit(project)
    refused(with_comments(project, comment(yes(head))), 6)


def test_ac3_a_yes_at_a_head_where_the_record_differs_fails(project: Path):
    """REQ-058 AC3: rule 6, the yes names a head where a goal was different."""
    people(project)
    digest = discovery(project, ANSWER)
    goals = [f'- G-1: "{Q1}" -> run docs/runs/run-1.md', f'- G-2: "{Q2}" -> not met']
    write(project, record(digest, goals))
    git(project, "init", "-q")
    early = commit(project)
    write(project, record(digest, status="accepted"))
    commit(project)
    refused(with_comments(project, comment(yes(early))), 6)


def test_ac3_a_yes_at_a_head_already_accepted_fails(project: Path):
    """REQ-058 AC3: rule 6, the yes names a head where the record says `proposed`."""
    head = proposed_then_accepted(project)
    refused(with_comments(project, comment(yes(git(project, "rev-parse", "HEAD")))), 6)
    assert with_comments(project, comment(yes(head))).returncode == 0


def test_ac3_a_head_outside_the_history_fails(project: Path):
    """REQ-058 AC3: rule 6, a commit the tree does not descend from says nothing about it."""
    head = proposed_then_accepted(project)
    proposed = (project / REL).read_text(encoding="utf-8")
    branch = git(project, "rev-parse", "--abbrev-ref", "HEAD")
    git(project, "checkout", "-q", "--orphan", "other")
    write(project, proposed.replace("- Status: accepted", "- Status: proposed"))
    write(project, "another line\n", "docs/runs/other.md")
    other = commit(project)
    git(project, "checkout", "-q", branch)
    assert head != other
    refused(with_comments(project, comment(yes(other))), 6)


def test_ac3_no_comments_file_reads_as_before(project: Path):
    """REQ-058 AC3: brief answer 2, without `--comments` an accepted record still fails."""
    head = proposed_then_accepted(project)
    assert head
    refused(run(project), 6)


def test_ac3_a_proposed_record_is_unaffected_by_the_comments(project: Path):
    """REQ-058 AC3: brief answer 2, the file changes nothing for a `proposed` record."""
    people(project)
    write(project, record(discovery(project, ANSWER)))
    result = with_comments(project, comment("Nothing here."))
    assert (result.returncode, result.stdout) == (0, "ok acceptance (1 records)\n")


def test_ac3_an_unreadable_comments_file_fails_naming_no_value(project: Path):
    """REQ-058 AC3: rule 10, a refusal, no traceback, with the option named by the file's role."""
    write(project, record(discovery(project, ANSWER)))
    result = run(project, "--comments", str(project / "absent.json"))
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout == "FAIL acceptance: the comments file cannot be read\n"
    assert "Traceback" not in result.stderr
