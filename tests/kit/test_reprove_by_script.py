"""The conductor re-proves by script (brief #2056, ADR-0854).

REQ-057. The supervisor's pass runs `conductor.reprove(root, n, apply=True)` once per pull request
and head for each light `re-prove:` line (answer 2); the conductor's records pass rule 4 (answer
3); `reprove --pr N --record [--apply]` records a head that lacks only its evidence record in local
mode (answer 4); the settings and edge cases of answers 6 and 7; the class stays closed (answer 9).
Git repositories in `tmp_path` and stubbed REST answers; invented data only, no network, no model.
"""

from __future__ import annotations

import inspect
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_light_reprove import (
    BODY,
    BOTTOM,
    EVIDENCE_LINE,
    LISTED,
    RECORD_TEXT,
    REPO,
    TOP,
    Runs,
    commit,
    git,
    world,
)

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import conductor  # noqa: E402
import merge_cleared  # noqa: E402

HEAD = "a" * 40
LIGHT = "re-prove: #7 agk.toml (changed by #9) light"
NOTE = "(the conductor's evidence record)"
AUTHOR = "builder-example"


# --- answer 2: the supervisor's pass ---------------------------------------------------------


class Pass:
    """The stubbed reads of one supervisor pass on which nothing else changed."""

    def __init__(self, monkeypatch, swept: str, stop: str | None = None, paused: bool = False):
        self.heads, self.calls, self.kept = {7: HEAD, 8: "b" * 40}, [], {}
        self.tip, self.fail = "m" * 40, set()
        now = conductor.stamp_of(datetime.now(UTC))
        self.state = {"fingerprint": "fp", "sweep": "dig", "job_at": now, "log_read": True}
        for name, value in {
            "pass_state": lambda root: dict(self.state),
            "job_running": lambda *a: False,
            "change_reads": lambda *a: (False, "d"),
            "refused_here": lambda root: False,
            "lease": lambda *a: 0,
            "plan_issue": lambda root: None,
            "keep_state": lambda root, state: self.kept.update(state),
            "pass_facts": lambda root: ("fp", False, "dig", swept),
            "logged_escalations": lambda *a: [],
            "steward_due": lambda *a: None,
            "cleared_due": lambda *a: None,  # main 9b6ab96a (brief #2058): no cleared head here
            "stop_reason": lambda *a: (stop, []),
            "record_health": lambda *a: None,
            "default_tip": lambda root: self.tip,
            "reprove": self.reprove,
        }.items():
            monkeypatch.setattr(conductor, name, value)
        monkeypatch.setattr(conductor.session, "paused_default", lambda root: paused)
        monkeypatch.setattr(conductor.session, "gh", self.gh)

    def gh(self, endpoint: str, *extra: str, method: str = "GET"):
        n = int(endpoint.rsplit("/", 1)[1])
        return {"number": n, "head": {"sha": self.heads[n]}}

    def reprove(self, root, number: int, apply: bool, record: bool = False) -> int:
        self.calls.append((number, apply, record))
        if number in self.fail:
            raise conductor.CheckError("update-branch was refused")
        print(f"reprove: #{number} {self.heads[number][:12]}: updated to {'c' * 12}; Report posted")
        return 0

    def run(self) -> int:
        code = conductor.watchdog_pass("root", "c1", REPO, "none")
        self.state.update(self.kept)
        return code


def test_req057_a_light_line_is_reproved_once_per_head(monkeypatch, capsys):
    """REQ-057: answer 2 and edge 7: once per pull request, head and default branch tip."""
    run = Pass(monkeypatch, LIGHT + "\n")
    assert run.run() == 0
    assert run.calls == [(7, True, False)]
    out = capsys.readouterr().out
    assert f"watchdog: reprove #7: reprove: #7 {HEAD[:12]}: updated to {'c' * 12}" in out
    assert "watchdog: nothing changed; no job started" in out
    assert run.run() == 0 and run.calls == [(7, True, False)]  # the same head: not again
    run.heads[7] = "d" * 40
    assert run.run() == 0 and run.calls[-1] == (7, True, False) and len(run.calls) == 2
    run.tip = "n" * 40
    assert run.run() == 0 and len(run.calls) == 3


@pytest.mark.parametrize("case", ["paused", "red", "stop", "full", "unknown", "none"])
def test_req057_the_pass_reproves_nothing_when_a_rule_holds(monkeypatch, case):
    """REQ-057: answer 2: a paused kit, a red-branch issue, a stop rule, a full or unreadable
    line, or no line: nothing is called."""
    swept = {
        "red": LIGHT + "\nred-branch issue: #5\n",
        "full": "re-prove: #7 scripts/agk/x.py (changed by #9)\n",
        "unknown": "re-prove: #7 unknown (cannot be read)\n",
        "none": "BEHIND #7 2\n",
    }.get(case, LIGHT + "\n")
    stop = "the GitHub limit is low" if case == "stop" else None
    run = Pass(monkeypatch, swept, stop=stop, paused=case == "paused")
    run.run()
    assert run.calls == []


def test_req057_a_failed_reprove_is_printed_and_the_pass_goes_on(monkeypatch, capsys):
    """REQ-057: answer 2: an exit 1 is printed; the next line is still tried."""
    run = Pass(monkeypatch, LIGHT + "\nre-prove: #8 agk.toml (changed by #9) light\n")
    run.fail = {7}
    assert run.run() == 0
    assert run.calls == [(7, True, False), (8, True, False)]
    assert "watchdog: reprove #7: update-branch was refused" in capsys.readouterr().out


def test_req057_the_pass_starts_no_model_for_a_reprove():
    source = inspect.getsource(conductor.pass_reprove)
    assert "start_job" not in source and "launch" not in source and "adapter" not in source


# --- answer 4: the evidence-only record -------------------------------------------------------


class Hub:
    """The REST answers of pull request #7 whose head is HEAD and stays there."""

    def __init__(self, head: str, comments: list, issues=None, fork: bool = False, body=BODY):
        self.head, self.comments, self.issues, self.calls = head, comments, issues or [], []
        self.fork, self.body = fork, body

    def gh(self, endpoint: str, *extra: str, method: str = "GET"):
        self.calls.append((method, endpoint, *extra))
        if endpoint == f"repos/{REPO}/pulls/7" and method == "GET":
            head = {"sha": self.head, "repo": {"full_name": "fork/agk" if self.fork else REPO}}
            return {"number": 7, "head": head, "base": {"ref": "main", "repo": {"full_name": REPO}},
                    "body": self.body, "user": {"login": AUTHOR}}  # fmt: skip
        if method in ("POST", "PUT"):
            return {"id": 1}
        return None

    def pages(self, endpoint: str):
        self.calls.append(("GET", endpoint))
        if endpoint.startswith(f"repos/{REPO}/issues/7/comments"):
            return self.comments
        if endpoint.startswith(f"repos/{REPO}/issues?state=open"):
            return self.issues
        return None

    def posted(self) -> list[str]:
        return [c[-1] for c in self.calls if c[0] == "POST"]


def said(login: str, body: str, cid: int = 1) -> dict:
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": "2026-11-27T10:00:00Z"}


def evidence_of(sha: str) -> str:
    return f"Evidence: prepush schema 1, head {sha[:12]}, 1 steps ok, record 0123456789ab"


def agreeing(sha: str) -> str:
    return f"Local evidence: {sha} {EVIDENCE_LINE.format(sha[:12])}"


def evidence_world(tmp_path: Path, execution: str = "local", same_tree: bool = False):
    """A clone whose `refs/pull/7/head` changes no file the default branch changed (no re-prove
    state): (the clone, the head, the earlier head). With SAME_TREE the head only re-words the
    earlier head's commit, so both have one tree."""
    line = f'execution = "{execution}"\n'
    root, old, _ = world(tmp_path, {"docs/example.md": "b\n"}, {"agk.toml": BOTTOM + line})
    git(root, "checkout", "-q", "feature")
    if same_tree:
        git(root, "commit", "-q", "--allow-empty", "-m", "the same tree")
        head = git(root, "rev-parse", "HEAD")
    else:
        head = commit(root, {"docs/feature.md": "new code\n"}, "new code")
    git(root, "checkout", "-q", "main")
    origin = tmp_path / "origin.git"
    git(tmp_path, "clone", "-q", "--bare", str(root), str(origin))
    git(origin, "update-ref", "refs/pull/7/head", head)
    clone = tmp_path / "clone"
    git(tmp_path, "clone", "-q", str(origin), str(clone))
    return clone, head, old


def hooked(monkeypatch, hub: Hub, runs=None, gitleaks: bool = True) -> None:
    monkeypatch.setattr(conductor.session, "gh", hub.gh)
    monkeypatch.setattr(conductor.session, "pages", hub.pages)
    monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(conductor, "verdict_authors", lambda root: list(LISTED))
    monkeypatch.setattr(conductor.shutil, "which", lambda name: "/bin/x" if gitleaks else None)
    if runs is not None:
        monkeypatch.setattr(conductor, "reprove_run", runs)


RECORD = ["reprove", "--pr", "7", "--record", "--apply"]


def test_req057_case_a_the_authors_evidence_line_is_recorded(tmp_path, monkeypatch, capsys):
    """REQ-057: answer 4 (a): the author posted `Evidence:` for the head; the conductor records
    it with no update-branch and posts the Report with the record."""
    clone, head, _ = evidence_world(tmp_path)
    hub, runs = Hub(head, [said(AUTHOR, f"Report: {head} ready\n\n{evidence_of(head)}")]), None
    runs = Runs(clone, head)
    hooked(monkeypatch, hub, runs)
    assert conductor.main(RECORD, clone) == 0
    assert not [c for c in hub.calls if c[0] == "PUT"]
    [body] = hub.posted()
    local = f"Local evidence: {head} {EVIDENCE_LINE.format(head[:12])} {NOTE}"
    assert body.startswith(f"body=Report: {head} evidence record {NOTE}\n\nEvidence: ")
    assert f"\n{local}\n" in body and f"```json\n{RECORD_TEXT.format(head)}\n```" in body
    assert local in capsys.readouterr().out
    verdict = {
        "id": 9,
        "user": {"login": LISTED[0]},
        "body": f"Verdict: cleared {head}\n\n{local}\n",
    }
    merge_cleared.local_evidence(verdict, [verdict], head, [])  # answer 3: it passes rule 4


def test_req057_case_b_an_equal_tree_of_an_evidenced_head_is_recorded(tmp_path, monkeypatch):
    """REQ-057: answer 4 (b): the head's tree equals an earlier head's with agreeing evidence."""
    clone, head, old = evidence_world(tmp_path, same_tree=True)
    hub = Hub(head, [said(LISTED[0], f"Verdict: fix list {old}\n\n{agreeing(old)}")])
    hooked(monkeypatch, hub, Runs(clone, head))
    assert conductor.main(RECORD, clone) == 0
    assert hub.posted()[0].startswith(f"body=Report: {head} evidence record {NOTE}")


@pytest.mark.parametrize("case", ["nothing", "new-code", "stranger"])
def test_req057_neither_case_is_the_builders_record(tmp_path, monkeypatch, capsys, case):
    """REQ-057: answer 4 and `Q-RP-1`: new code, or a line by someone else, is proved by its
    author first: exit 3, nothing posted, nothing run."""
    clone, head, old = evidence_world(tmp_path)
    comments = {
        "nothing": [],
        "new-code": [said(LISTED[0], f"Verdict: fix list {old}\n\n{agreeing(old)}")],
        "stranger": [said("someone-example", evidence_of(head))],
    }[case]
    hub, runs = Hub(head, comments), Runs(clone, head)
    hooked(monkeypatch, hub, runs)
    assert conductor.main(RECORD, clone) == 3
    assert hub.posted() == [] and runs.argv == []
    assert f"reprove: #7 {head[:12]}: the builder records it (rule 4)" in capsys.readouterr().out


def test_req057_without_apply_the_case_is_printed_and_nothing_runs(tmp_path, monkeypatch, capsys):
    clone, head, _ = evidence_world(tmp_path)
    hub, runs = Hub(head, [said(AUTHOR, evidence_of(head))]), Runs(clone, head)
    hooked(monkeypatch, hub, runs)
    assert conductor.main(["reprove", "--pr", "7", "--record"], clone) == 0
    assert hub.posted() == [] and runs.argv == []
    assert "add --apply to do it" in capsys.readouterr().out


def test_req057_an_evidenced_head_has_nothing_to_record(tmp_path, monkeypatch, capsys):
    """REQ-057: edge 7: answer 4 on a head already evidenced: `nothing to record`, exit 0."""
    clone, head, _ = evidence_world(tmp_path)
    hub, runs = Hub(head, [said(LISTED[0], f"Verdict: cleared {head}\n\n{agreeing(head)}")]), None
    runs = Runs(clone, head)
    hooked(monkeypatch, hub, runs)
    assert conductor.main(RECORD, clone) == 0
    assert hub.posted() == [] and runs.argv == []
    assert "nothing to record" in capsys.readouterr().out


@pytest.mark.parametrize("execution", ["hosted", "hybrid", "pool"])
def test_req057_record_is_refused_outside_local_mode_naming_execution(
    tmp_path, monkeypatch, capsys, execution
):
    """REQ-057: answer 6: with no record issue `--record` is refused naming `execution`."""
    clone, head, _ = evidence_world(tmp_path, execution)
    hub = Hub(head, [said(AUTHOR, evidence_of(head))])
    hooked(monkeypatch, hub, Runs(clone, head))
    assert conductor.main(RECORD, clone) == 1
    assert hub.posted() == []
    assert "(setting: execution)" in capsys.readouterr().err


def test_req057_the_open_record_issue_allows_record_in_hosted_mode(tmp_path, monkeypatch):
    clone, head, _ = evidence_world(tmp_path, "hosted")
    issue = {"number": 3, "title": "Local mode since 2026-11-17"}
    hub = Hub(head, [said(AUTHOR, evidence_of(head))], issues=[issue])
    hooked(monkeypatch, hub, Runs(clone, head))
    assert conductor.main(RECORD, clone) == 0
    assert "```json" in hub.posted()[0]


@pytest.mark.parametrize("case", ["malformed", "forge", "paused", "gitleaks", "deferred"])
def test_req057_the_settings_of_answer_6(tmp_path, monkeypatch, capsys, case):
    """REQ-057: answers 6 and 7: a malformed `execution` and `forge = "files"` are refused before
    anything is run; paused runs nothing; no gitleaks or a deferred scan is `none`, exit 3."""
    clone, head, _ = evidence_world(tmp_path, "cloudy" if case == "malformed" else "local")
    if case == "forge":
        (clone / "agk.toml").write_text('forge = "files"\n', encoding="utf-8")
    body = BODY + ("Secret-scan: deferred to CI\n" if case == "deferred" else "")
    hub, runs = Hub(head, [said(AUTHOR, evidence_of(head))], body=body), Runs(clone, head)
    hooked(monkeypatch, hub, runs, gitleaks=case != "gitleaks")
    if case == "paused":
        monkeypatch.setattr(conductor.session, "paused_default", lambda root: True)
    code = conductor.main(RECORD, clone)
    out, err = capsys.readouterr()
    assert runs.argv == []
    if case in ("malformed", "forge"):
        assert code == 1 and hub.posted() == []
        assert (
            "(setting: execution in agk.toml)" if case == "malformed" else "(setting: forge)"
        ) in err
    elif case == "paused":
        assert code == 0 and hub.posted() == [] and "reprove: agk paused; nothing updated" in out
    else:
        [body] = hub.posted()
        assert code == 3 and "Local evidence: none (" in body and "```json" not in body


def test_req057_a_head_in_the_re_prove_state_is_not_an_evidence_only_head(tmp_path, monkeypatch):
    root, head, _ = world(
        tmp_path, {"agk.toml": TOP}, {"agk.toml": BOTTOM + 'execution = "local"\n'}
    )
    origin = tmp_path / "origin.git"
    git(tmp_path, "clone", "-q", "--bare", str(root), str(origin))
    git(origin, "update-ref", "refs/pull/7/head", head)
    clone = tmp_path / "clone"
    git(tmp_path, "clone", "-q", str(origin), str(clone))
    hub, runs = Hub(head, [said(AUTHOR, evidence_of(head))]), Runs(clone, head)
    hooked(monkeypatch, hub, runs)
    assert conductor.main(RECORD, clone) == 3
    assert hub.posted() == [] and runs.argv == []


def test_req057_a_fork_head_is_refused_and_nothing_updated(tmp_path, monkeypatch, capsys):
    """REQ-057: edge 7: a light line for a fork head: refused, no update-branch."""
    root, head, _ = world(tmp_path, {"agk.toml": TOP}, {"agk.toml": BOTTOM})
    origin = tmp_path / "origin.git"
    git(tmp_path, "clone", "-q", "--bare", str(root), str(origin))
    git(origin, "update-ref", "refs/pull/7/head", head)
    clone = tmp_path / "clone"
    git(tmp_path, "clone", "-q", str(origin), str(clone))
    hub = Hub(head, [], fork=True)
    hooked(monkeypatch, hub)
    assert conductor.main(["reprove", "--pr", "7", "--apply"], clone) == 1
    assert not [c for c in hub.calls if c[0] in ("PUT", "POST")]
    assert "fork" in capsys.readouterr().err


# --- answers 5 and 9: the role file and the closed class ---------------------------------------


def test_req057_the_role_file_runs_the_two_commands():
    text = (SCRIPTS.parents[1] / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    assert "conductor.py reprove --pr <n> --apply" in text
    assert "conductor.py reprove --pr <n> --record --apply" in text


def test_req057_only_the_record_step_writes_the_evidence_folder():
    """REQ-057: answer 9: no other conductor routine names the clone's `agk-evidence` folder,
    and the two notes come only from `reprove` and the evidence-only record."""
    names = [
        name
        for name, fn in inspect.getmembers(conductor, inspect.isfunction)
        if fn.__module__ == "conductor" and "agk-evidence" in inspect.getsource(fn)
    ]
    assert names == ["record_in"]
    for note in ("RECORD_NOTE", "EVIDENCE_NOTE"):
        users = [
            name
            for name, fn in inspect.getmembers(conductor, inspect.isfunction)
            if fn.__module__ == "conductor" and note in inspect.getsource(fn)
        ]
        assert users == (["reprove"] if note == "RECORD_NOTE" else ["evidence_record"]), users


def test_req057_the_new_tests_are_mapped():
    data = tomllib.loads((SCRIPTS.parents[1] / "agk.toml").read_text(encoding="utf-8"))
    maps = {m["code"]: m["tests"] for m in data["testing"]["map"]}
    assert "tests/kit/test_reprove_by_script.py" in maps["scripts/agk/conductor.py"]
    assert "tests/kit/test_conductor_guard_reprove.py" in maps[".claude/hooks/conductor_guard.py"]
