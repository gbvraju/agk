"""check_brief.py --event: what the brief check does for one saved issue event (brief #770).

SPEC-0030 rule 4 and amendment 140; REQ-037; ADR-0357. A saved payload of an `issues` event goes in
and one JSON line comes out: `ignore`, `fail` (the label and the comment naming each failing rule,
never a value) or `pass` (the label and the comment go, and the wave names the milestone). Reads the
files only: no network, invented data."""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agk" / "check_brief.py"
WORDS = "A person at example.com can open a widget."
GOOD = (
    f'Sentence: "{WORDS}"\n'
    "Answers:\n1. one\n2. two\n"
    "Size: S\nAdvances: new\nTouches: docs/**\nPriority: 1\n"
    "Contexts: kit (x); github (x); local (x); personal (x); stacks (x)\n"
)
WAVED = GOOD + "Wave: 2\n"
LONG = GOOD.replace(WORDS, "x" * 301)
PLANNED = "[flow]\nplan_issue = 9\n"


def payload(body: str, action: str = "opened", labels=("agk-brief",), **extra) -> dict:
    issue = {
        "number": 12,
        "body": body,
        "labels": [{"name": n} for n in labels],
        "user": {"login": "filer"},
        **extra,
    }
    return {"action": action, "issue": issue}


def event(tmp_path: Path, data: dict, toml: str = "", *extra: str):
    root = tmp_path / "root"
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "requirements.md").write_text("### REQ-001\n", encoding="utf-8")
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    saved = tmp_path / "event.json"
    saved.write_text(json.dumps(data), encoding="utf-8")
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "--event", str(saved), "--root", str(root), *extra],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.parametrize("action", ["opened", "edited", "labeled"])
def test_a_malformed_brief_gets_the_label_and_a_comment_naming_the_rule(tmp_path, action):
    out = event(tmp_path, payload(LONG, action))
    assert out["action"] == "fail"
    assert out["issue"] == 12
    assert out["label"] == "agk-brief-invalid"
    assert out["problems"] == ["rule 4: the Sentence is not 1 to 300 characters"]
    assert "rule 4: the Sentence is not 1 to 300 characters" in out["comment"]
    assert out["comment"].startswith("<!-- agk-brief-check -->")
    assert "xxx" not in out["comment"]


def test_a_fixed_brief_loses_the_label_and_the_comment(tmp_path):
    out = event(tmp_path, payload(GOOD, "edited", labels=("agk-brief", "agk-brief-invalid")))
    assert out == {"action": "pass", "issue": 12, "label": "agk-brief-invalid", "wave": None}


@pytest.mark.parametrize(
    "data",
    [
        payload("no shape at all", labels=("bug",)),
        payload("no shape at all", action="closed"),
        payload("no shape at all", pull_request={"url": "https://example.com/pull/1"}),
    ],
)
def test_an_issue_that_is_not_a_brief_event_is_ignored(tmp_path, data):
    assert event(tmp_path, data) == {"action": "ignore"}


def test_a_missing_wave_is_refused_when_a_plan_issue_is_set(tmp_path):
    out = event(tmp_path, payload(GOOD), PLANNED)
    assert out["action"] == "fail"
    assert out["problems"] == ["rule 4: exactly one line Wave: n (setting: plan_issue)"]


def test_a_wave_the_plan_does_not_have_is_refused(tmp_path):
    out = event(tmp_path, payload(WAVED), PLANNED, "--waves", "1,3")
    assert out["problems"] == ["rule 4: the Wave line names a wave the plan does not have"]


def test_a_named_wave_passes_and_names_the_milestone(tmp_path):
    out = event(tmp_path, payload(WAVED), PLANNED, "--waves", "1,2")
    assert out == {"action": "pass", "issue": 12, "label": "agk-brief-invalid", "wave": 2}


def test_with_no_plan_issue_the_wave_line_is_optional(tmp_path):
    assert event(tmp_path, payload(GOOD))["action"] == "pass"
    assert event(tmp_path, payload(WAVED))["wave"] == 2


def test_a_saved_brief_file_is_checked_for_the_wave_too(tmp_path):
    root = tmp_path / "root"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "requirements.md").write_text("### REQ-001\n", encoding="utf-8")
    (root / "agk.toml").write_text(PLANNED, encoding="utf-8")
    brief = tmp_path / "brief.md"
    brief.write_text(GOOD, encoding="utf-8")
    run = [sys.executable, str(SCRIPT), str(brief), "--root", str(root)]
    proc = subprocess.run(run, capture_output=True, text=True)  # nosec B603 - fixed list, no shell
    assert proc.returncode == 1
    assert "rule 4: exactly one line Wave: n (setting: plan_issue)" in proc.stdout
    brief.write_text(WAVED, encoding="utf-8")
    proc = subprocess.run(run, capture_output=True, text=True)  # nosec B603 - fixed list, no shell
    assert proc.returncode == 0, proc.stdout


# --- the job on GitHub (answer 2) and the doctor's label check -----------------------------------

WORKFLOW = SCRIPT.parents[2] / ".github" / "workflows" / "agk-brief.yml"
# Installed in projects (Q-770-4); a project that deletes it leaves these tests nothing to read.
needs_workflow = pytest.mark.skipif(not WORKFLOW.is_file(), reason="the workflow is absent")
REPO = "example-owner/example-repo"
ISSUE = f"repos/{REPO}/issues/12"


def job_script() -> str:
    """The `run:` text of the job's one script step, as GitHub would hand it to bash."""
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    start = lines.index("      - name: Check the brief")
    begin = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |") + 1
    block = []
    for line in lines[begin:]:
        if line.strip() and not line.startswith(" " * 10):
            break
        block.append(line[10:])
    return "\n".join(block) + "\n"


def run_job(tmp_path: Path, data: dict, comment_id: str = "", milestones: str = "7 Wave 2\n"):
    """The step's script with a stub `gh`, on a saved event: returns the logged calls."""
    root = tmp_path / "root"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "requirements.md").write_text("### REQ-001\n", encoding="utf-8")
    (root / "agk.toml").write_text(PLANNED, encoding="utf-8")
    (root / "scripts").symlink_to(SCRIPT.parents[1])
    saved = tmp_path / "event.json"
    saved.write_text(json.dumps(data), encoding="utf-8")
    temp = tmp_path / "runner"
    temp.mkdir()
    stubs = tmp_path / "bin"
    stubs.mkdir()
    log = tmp_path / "gh.log"
    gh = stubs / "gh"
    gh.write_text(
        '#!/usr/bin/env bash\necho "$*" >> "$STUB_LOG"\n'
        'for a in "$@"; do\n'
        '  if [ "$prev" = "--input" ]; then cat "$a" >> "$STUB_LOG"; echo >> "$STUB_LOG"; fi\n'
        '  prev="$a"\ndone\n'
        'case "$*" in\n'
        '  *"--method GET"*milestones*) [ -n "$STUB_MILESTONES" ] || exit 1;'
        ' printf "%s" "$STUB_MILESTONES" ;;\n'
        '  *"--method GET"*/comments*) [ -z "$STUB_COMMENT" ] || echo "$STUB_COMMENT" ;;\n'
        '  *"--method DELETE"*/labels/*) [ -z "$STUB_LABEL_GONE" ] || exit 1 ;;\n'
        "esac\n",
        encoding="utf-8",
    )
    gh.chmod(0o755)
    env = {
        "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}",
        "GITHUB_REPOSITORY": REPO,
        "GITHUB_EVENT_PATH": str(saved),
        "RUNNER_TEMP": str(temp),
        "STUB_LOG": str(log),
        "STUB_COMMENT": comment_id,
        "STUB_MILESTONES": milestones,
        "STUB_LABEL_GONE": "",
    }
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["bash", "-e", "-c", job_script()], cwd=root, env=env, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def writes(calls: list[str]) -> list[str]:
    return [c for c in calls if c.startswith("api --method") and "--method GET" not in c]


@needs_workflow
def test_the_workflow_starts_on_the_three_issue_events_with_the_two_permissions():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "  issues:\n    types: [opened, edited, labeled]\n" in text
    assert "\npermissions:\n  contents: read\n  issues: write\n" in text
    assert "contains(github.event.issue.labels.*.name, 'agk-brief')" in text
    assert "ref: ${{ github.event.repository.default_branch }}" in text


@needs_workflow
def test_the_workflow_never_puts_issue_text_into_a_command():
    """A body or title is the filer's text: the job reads it from the saved event, a file."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "github.event.issue.body" not in text and "github.event.issue.title" not in text
    assert "pull_request_target" not in text
    assert all("@" in ln for ln in text.splitlines() if ln.strip().startswith("- uses:"))


@needs_workflow
def test_the_job_labels_and_comments_on_a_malformed_brief(tmp_path):
    calls = run_job(tmp_path, payload(LONG))
    done = writes(calls)
    assert done[0] == f"api --method POST {ISSUE}/labels -f labels[]=agk-brief-invalid"
    assert done[1].startswith(f"api --method POST {ISSUE}/comments --input ")
    assert len(done) == 2
    sent = json.loads(next(c for c in calls if c.startswith("{")))
    assert sent["body"].startswith("<!-- agk-brief-check -->")
    assert "rule 4" in sent["body"] and "xxx" not in sent["body"]


@needs_workflow
def test_the_job_updates_its_one_comment_rather_than_adding_another(tmp_path):
    done = writes(run_job(tmp_path, payload(LONG, "edited"), comment_id="55"))
    assert any(c.startswith(f"api --method PATCH repos/{REPO}/issues/comments/55 ") for c in done)
    assert not any(c.startswith(f"api --method POST {ISSUE}/comments") for c in done)


@needs_workflow
def test_the_job_clears_a_fixed_brief_and_sets_its_milestone(tmp_path):
    done = writes(run_job(tmp_path, payload(WAVED, "edited"), comment_id="55"))
    assert done == [
        f"api --method DELETE {ISSUE}/labels/agk-brief-invalid",
        f"api --method DELETE repos/{REPO}/issues/comments/55",
        f"api --method PATCH {ISSUE} -F milestone=7",
    ]


@needs_workflow
def test_the_job_writes_nothing_for_an_event_it_ignores(tmp_path):
    assert writes(run_job(tmp_path, payload("no shape at all", labels=("bug",)))) == []


@needs_workflow
def test_with_the_milestones_unreadable_the_shape_is_enough_and_no_milestone_is_set(tmp_path):
    done = writes(run_job(tmp_path, payload(WAVED), milestones=""))
    assert not any("milestone=" in c for c in done)
    assert not any("POST" in c for c in done)


class Answers:
    """The doctor's read of one label: (data, reason class), as `Reads.get` returns it."""

    def __init__(self, answer: tuple) -> None:
        self.answer = answer
        self.paths: list[str] = []

    def get(self, name: str, path: str, not_found: str | None = None) -> tuple:
        self.paths.append(path)
        return self.answer


def label_result(tmp_path: Path, answer: tuple, installed: bool = True):
    sys.path.insert(0, str(SCRIPT.parent))
    import doctor

    if installed:
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "agk-brief.yml").write_text("x\n", encoding="utf-8")
    reads = Answers(answer)
    return doctor.brief_invalid_label_result(tmp_path, reads), reads


def test_the_doctor_warns_when_the_workflow_is_here_and_its_label_is_missing(tmp_path):
    result, _ = label_result(tmp_path, (None, "missing"))
    assert result.status == "fail"


def test_the_doctor_says_cannot_check_when_the_label_cannot_be_read(tmp_path):
    result, _ = label_result(tmp_path, (None, "offline"))
    assert (result.status, result.reason) == ("cannot-check", "offline")


def test_the_doctor_asks_nothing_of_a_project_without_the_workflow(tmp_path):
    result, reads = label_result(tmp_path, (None, "missing"), installed=False)
    assert result.status == "ok" and reads.paths == []


def test_the_check_is_a_warning_that_names_the_label_and_who_creates_it():
    sys.path.insert(0, str(SCRIPT.parent))
    import doctor

    severity, _, failed, fix = doctor.CHECKS["brief-invalid-label"]
    assert severity == "warn"
    assert "agk-brief-invalid" in failed and "agk-brief-invalid" in fix


def test_the_doctor_finds_the_label_present(tmp_path):
    result, reads = label_result(tmp_path, ({"name": "agk-brief-invalid"}, ""))
    assert result.status == "ok" and reads.paths == ["/labels/agk-brief-invalid"]
