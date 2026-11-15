"""The conductor runs each pass on the tier it needs (brief #1359, ADR-0571; REQ-050).

`conductor.py watchdog --pass` decides the tier of the job it starts from the queue it hands it:
`strongest` at `high` when a queued pull request changes a protected path class, adds or changes a
spec or ADR, is a first review of more than `[review] large_lines` changed lines, carries a
`Question:`, a `Correction:` or a disagreement between verdicts, or is an intake (and for a question
on a brief, or a queue it cannot read); `mid` at `medium` for every other pass. A mid job that
ends with `escalate: #<n> <reason>` is followed at once by one strongest job, and
`[models] conductor = "strongest"` pins every pass. Recorded queues, an adapter double and the
scripts of the pass replaced in this process: invented names, no network, no model.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_session import REPO, SHA, comment

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import conductor  # noqa: E402
from common import CheckError  # noqa: E402

import config  # noqa: E402

TAKEN = datetime(2026, 11, 15, 10, 0, tzinfo=UTC)
CLASSES = ["scripts/agk/", "agk.toml", ".claude/"]
VERDICT = f"Verdict: fix list {SHA}\n\n1. a finding"


def item(**extra) -> dict:
    """One queued pull request as `queued_items` reads it: a routine re-review by default."""
    base = {
        "number": 7,
        "title": "A small change (brief #9)",
        "author": "b1",
        "paths": ["docs/guides/example.md"],
        "changed": 40,
        "comments": [comment(1, "boss", VERDICT), comment(2, "b1", f"Report: {SHA[:9]} done")],
    }
    return {**base, **extra}


def reasons(one: dict, large: int = 300) -> list[str]:
    return conductor.strongest_reasons(one, CLASSES, ["boss"], large)


# --- answer 1: each row of the list picks its tier ----------------------------------------


def test_1359_a_routine_re_review_needs_no_strongest_pass():
    """REQ-050: brief #1359 answer 1 (the mid rows)."""
    assert reasons(item()) == []


@pytest.mark.parametrize(
    ("extra", "why"),
    [
        ({"paths": ["scripts/agk/example.py"]}, "#7 changes a protected path class"),
        ({"paths": ["agk.toml"]}, "#7 changes a protected path class"),
        ({"paths": ["docs/specs/SPEC-0099-example.md"]}, "#7 adds or changes a spec or ADR"),
        ({"paths": ["docs/adr/0999-example.md"]}, "#7 adds or changes a spec or ADR"),
        ({"comments": [], "changed": 301}, "#7 first review of 301 changed lines"),
        ({"title": "Intake: an example (brief #9)"}, "#7 is an intake"),
    ],
)
def test_1359_each_strongest_row_picks_the_strongest_tier(extra, why):
    """REQ-050: brief #1359 answer 1 (the strongest rows)."""
    assert why in reasons(item(**extra))


def test_1359_a_first_review_at_or_below_large_lines_stays_mid():
    """REQ-050: brief #1359 answer 1 (`large_lines` is the bound, 300 by default)."""
    assert reasons(item(comments=[], changed=300)) == []
    assert reasons(item(comments=[], changed=120), large=100) == [
        "#7 first review of 120 changed lines"
    ]


def test_1359_a_re_review_of_a_large_change_is_no_first_review():
    """REQ-050: brief #1359 answer 1 (only a first review counts the lines)."""
    assert reasons(item(changed=900)) == []


@pytest.mark.parametrize(
    ("line", "why"),
    [
        ("Question: Q-9-1 which reading holds?", "#7 carries a Question:"),
        ("Correction: the brief's answer 2 reads otherwise", "#7 carries a Correction:"),
    ],
)
def test_1359_a_question_or_a_correction_since_the_verdict_picks_strongest(line, why):
    """REQ-050: brief #1359 answer 1 (a `Question:` or a `Correction:`)."""
    said = [comment(1, "boss", VERDICT), comment(3, "b1", line)]
    assert reasons(item(comments=said)) == [why]


def test_1359_a_question_answered_by_a_later_verdict_is_routine():
    """REQ-050: brief #1359 answer 1 (a question the last verdict already answered)."""
    said = [comment(1, "b1", "Question: Q-9-1 which?"), comment(2, "boss", VERDICT)]
    assert reasons(item(comments=said)) == []


def test_1359_two_verdicts_on_one_head_that_disagree_pick_strongest():
    """REQ-050: brief #1359 answer 1 (a disagreement between verdicts)."""
    said = [comment(1, "boss", VERDICT), comment(2, "boss", f"Verdict: cleared {SHA}")]
    assert reasons(item(comments=said)) == ["#7 disagreement between verdicts"]


def test_1359_a_verdict_by_an_unlisted_account_counts_for_nothing():
    """REQ-050: brief #1359 answer 1 (only a listed verdict author's verdict counts)."""
    said = [comment(1, "someone", VERDICT)]
    assert reasons(item(comments=said, changed=500)) == ["#7 first review of 500 changed lines"]


def test_1359_a_question_on_a_brief_picks_strongest():
    """REQ-050: brief #1359 answer 1 (a `Question:` with no pull request yet)."""
    one = {"number": 12, "brief_question": True}
    assert conductor.strongest_reasons(one, CLASSES, ["boss"], 300) == ["#12 question on a brief"]


# --- the queue the job is handed -----------------------------------------------------------


def queue_world(monkeypatch, listed: str, pulls: dict, files: dict, said: dict) -> None:
    def quietly(act, root, *args):
        return 0, listed

    def gh(endpoint, *extra, method="GET"):
        return pulls.get(endpoint)

    def pages(endpoint):
        return files.get(endpoint, said.get(endpoint))

    monkeypatch.setattr(conductor.session, "quietly", quietly)
    monkeypatch.setattr(conductor.session, "gh", gh)
    monkeypatch.setattr(conductor.session, "pages", pages)


def test_1359_the_queue_reads_only_the_pull_requests_listed_for_review(monkeypatch, tmp_path):
    """REQ-050: brief #1359 answer 1 (the queue it hands the job)."""
    listed = (
        f"#7 {SHA[:7]} review: Report: comment 2 since the last verdict\n"
        "#12 question on a brief\nrequest b2 (comment 40) waiting 3m\n"
        f"#8 {SHA[:7]} skip: draft\n"
    )
    pulls = {
        f"repos/{REPO}/pulls/7": {
            "number": 7, "title": "A change", "additions": 30, "deletions": 5,
            "user": {"login": "b1"},
        },
    }  # fmt: skip
    files = {f"repos/{REPO}/pulls/7/files": [{"filename": "docs/guides/example.md"}]}
    said = {f"repos/{REPO}/issues/7/comments": [comment(1, "boss", VERDICT)]}
    queue_world(monkeypatch, listed, pulls, files, said)
    found = conductor.queued_items(tmp_path, REPO)
    assert [one["number"] for one in found] == [7, 12]
    assert found[0]["paths"] == ["docs/guides/example.md"] and found[0]["changed"] == 35
    assert found[1] == {"number": 12, "brief_question": True}


def test_1359_a_queue_that_cannot_be_read_runs_the_strongest_pass(monkeypatch, tmp_path):
    """REQ-050: brief #1359 answer 2 (unsure: never down)."""
    listed = f"#7 {SHA[:7]} review: no verdict yet\n"
    queue_world(monkeypatch, listed, {}, {}, {})
    with pytest.raises(CheckError):
        conductor.queued_items(tmp_path, REPO)
    monkeypatch.setattr(conductor, "pass_classes", lambda root: CLASSES)
    tier = conductor.tier_for_pass(tmp_path, REPO)
    assert tier[:2] == ("strongest", "high") and tier[2] == ["the queue cannot be read"]


# --- answer 3: the pin, and the two settings ----------------------------------------------


def toml(tmp_path: Path, text: str) -> Path:
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    return tmp_path


def test_1359_the_pin_and_large_lines_are_read_and_checked(tmp_path):
    """REQ-050: brief #1359 answer 3 (the pin) and answer 1 (`large_lines`)."""
    root = toml(tmp_path, '[models]\nconductor = "strongest"\n[review]\nlarge_lines = 120\n')
    assert config.conductor_pin(root) == "strongest" and config.review_large_lines(root) == 120
    assert config.model_settings(root)["review"] == config.REVIEW_FLOOR  # the table still reads
    root = toml(tmp_path, "")
    assert config.conductor_pin(root) is None and config.review_large_lines(root) == 300


@pytest.mark.parametrize(
    ("text", "setting"),
    [
        ('[models]\nconductor = "mid"\n', "models.conductor"),
        ("[models]\nconductor = 3\n", "models.conductor"),
        ("[review]\nlarge_lines = 0\n", "review.large_lines"),
        ('[review]\nlarge_lines = "many"\n', "review.large_lines"),
    ],
)
def test_1359_a_wrong_pin_or_bound_is_refused_naming_the_setting(tmp_path, text, setting):
    """REQ-050: brief #1359 answer 3; principle 8 (the setting, never the value)."""
    root = toml(tmp_path, text)
    with pytest.raises(CheckError, match=setting.replace(".", r"\.")) as caught:
        config.conductor_pin(root) if setting.startswith("models") else config.review_large_lines(
            root
        )
    assert '"mid"' not in str(caught.value) and "many" not in str(caught.value)


def test_1359_the_pin_forces_the_strongest_pass(monkeypatch, tmp_path):
    """REQ-050: brief #1359 answer 3 (a project may pin the conductor)."""
    root = toml(tmp_path, '[models]\nconductor = "strongest"\n')
    monkeypatch.setattr(conductor, "queued_items", lambda root, repo: [item()])
    assert conductor.tier_for_pass(root, REPO) == (
        "strongest", "high", ["pinned by [models] conductor"]
    )  # fmt: skip


# --- answers 1 and 2 through the scripted pass ----------------------------------------------

ADAPTER = """import json, os, sys
with open(sys.argv[1], "a", encoding="utf-8") as log:
    keys = ("AGK_SESSION", "AGK_ROLE", "AGK_TIER", "AGK_EFFORT")
    log.write(json.dumps({**{k: os.environ.get(k) for k in keys}, "prompt": sys.stdin.read()}))
    log.write("\\n")
if os.environ.get("AGK_TIER") == "mid" and os.environ.get("ESCALATE"):
    print("pass done")
    print(os.environ["ESCALATE"])
"""


@pytest.fixture
def local(repo, tmp_path, monkeypatch):
    """A project in local mode with an adapter double; the scripts of the pass are replaced and
    the queue is recorded."""
    import common

    double = tmp_path / "adapter.py"
    double.write_text(ADAPTER, encoding="utf-8")
    log = tmp_path / "adapter.log"
    text = (
        'default_branch = "main"\n[flow]\nplan_issue = 61\nauto_start = true\n'
        f"launch_adapter = {json.dumps(f'{sys.executable} {double} {log}')}\n"
    )
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.commit(
        {"agk.toml": text, "config/reviewers.yaml": "version: 1\nverdict_authors: [boss]\n"}
    )
    repo.git("update-ref", "refs/remotes/origin/main", "HEAD")
    monkeypatch.delenv("ESCALATE", raising=False)
    monkeypatch.setattr(common, "available_memory", lambda: None)
    facts = {"fingerprint": "fingerprint aaa", "queue": [item()]}

    def lease(root, mode, name, takeover=True):
        print(f"lease: taken by {name}")
        return 0

    monkeypatch.setattr(conductor, "lease", lease)
    monkeypatch.setattr(conductor, "plan_comments", lambda repo, issue: [])
    monkeypatch.setattr(conductor, "lease_holder", lambda c, a, now: ("conductor-local", TAKEN))
    monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(
        conductor.session, "review_queue", lambda root, m: print(facts["fingerprint"]) or 0
    )
    monkeypatch.setattr(conductor.session_plan, "plan", lambda root, *a: print("Start 0: no.") or 0)
    monkeypatch.setattr(conductor, "sweep", lambda root: print("x") or 0)
    monkeypatch.setattr(conductor, "queued_items", lambda root, repo: facts["queue"])
    monkeypatch.setattr(conductor, "pass_classes", lambda root: CLASSES)
    monkeypatch.setattr(conductor, "builder_pass", lambda root, repo, adapter: None)
    return {"repo": repo, "log": log, "facts": facts}


def passed(local, capsys) -> tuple[int, str]:
    """One scheduled pass, past the first lease window of the last job."""
    state = conductor.pass_state_file(local["repo"].root)
    if state.exists():
        kept = json.loads(state.read_text())
        if kept.get("job_at"):
            start = datetime.strptime(kept["job_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
            kept["job_at"] = conductor.stamp_of(start - timedelta(minutes=11))
            state.write_text(json.dumps(kept))
    code = conductor.main(["watchdog", "--pass"], root=local["repo"].root)
    return code, capsys.readouterr().out


def jobs(local) -> list[dict]:
    log = local["log"]
    return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []


def test_1359_a_routine_queue_starts_the_job_on_mid(local, capsys):
    """REQ-050: brief #1359 answer 1 (every other pass on `mid` at `medium`)."""
    code, out = passed(local, capsys)
    assert code == 0 and "watchdog: job started conductor-local on mid at medium" in out
    job = jobs(local)[0]
    assert (job["AGK_TIER"], job["AGK_EFFORT"]) == ("mid", "medium")
    assert "`mid` tier" in job["prompt"] and "escalate: #<n> <reason>" in job["prompt"]
    assert "tier: mid" in job["prompt"]  # the verdict names its tier in its Read: line


def test_1359_a_protected_change_starts_the_job_on_strongest(local, capsys):
    """REQ-050: brief #1359 answer 1 (a strongest row in the queue)."""
    local["facts"]["queue"] = [item(), item(number=8, paths=["scripts/agk/x.py"])]
    code, out = passed(local, capsys)
    assert code == 0 and "on strongest at high" in out
    assert "watchdog: tier strongest: #8 changes a protected path class" in out
    job = jobs(local)[0]
    assert (job["AGK_TIER"], job["AGK_EFFORT"]) == ("strongest", "high")
    assert "escalate:" not in job["prompt"]


def test_1359_a_mid_escalation_runs_one_strongest_pass_at_once(local, capsys, monkeypatch):
    """REQ-050: brief #1359 answer 2 (a step up, never down; one strongest pass)."""
    monkeypatch.setenv("ESCALATE", "escalate: #7 unsure of the verdict")
    code, out = passed(local, capsys)
    assert code == 0
    tiers = [(j["AGK_TIER"], j["AGK_EFFORT"]) for j in jobs(local)]
    assert tiers == [("mid", "medium"), ("strongest", "high")]
    assert "watchdog: escalated #7 to strongest: unsure of the verdict" in out
    assert "#7 (unsure of the verdict)" in jobs(local)[1]["prompt"]
    code, out = passed(local, capsys)  # nothing changed: no further job
    assert "nothing changed" in out and len(jobs(local)) == 2


def test_1359_an_escalation_in_the_jobs_log_runs_the_strongest_pass_next(
    local, capsys, monkeypatch, tmp_path
):
    """REQ-050: brief #1359 answer 2 (a background job's escalation, read from its log)."""
    folder = tmp_path / "agk-conductor-local"  # the job's worktree, kept inside this test
    monkeypatch.setattr(conductor.launch, "worktree_of", lambda root, name: folder)
    passed(local, capsys)
    assert len(jobs(local)) == 1
    folder.mkdir(parents=True, exist_ok=True)
    (folder / conductor.JOB_LOG).write_text("pass done\nescalate: #7 a protected path\n")
    code, out = passed(local, capsys)
    assert code == 0 and "watchdog: escalated #7 to strongest: a protected path" in out
    assert [j["AGK_TIER"] for j in jobs(local)] == ["mid", "strongest"]
    code, out = passed(local, capsys)  # the log is read once
    assert len(jobs(local)) == 2


def test_1359_the_pin_starts_every_job_on_strongest(local, capsys):
    """REQ-050: brief #1359 answer 3 (the pin forces `strongest`)."""
    root = local["repo"].root
    text = (root / "agk.toml").read_text() + '[models]\nconductor = "strongest"\n'
    (root / "agk.toml").write_text(text)
    local["repo"].git("commit", "-qam", "pin")
    local["repo"].git("update-ref", "refs/remotes/origin/main", "HEAD")
    code, out = passed(local, capsys)
    assert code == 0 and "watchdog: tier strongest: pinned by [models] conductor" in out
    assert jobs(local)[0]["AGK_TIER"] == "strongest"
