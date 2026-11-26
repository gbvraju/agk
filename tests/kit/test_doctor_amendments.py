"""Doctor warns about an approved spec amendment left unapplied (brief #1967; REQ-020, ADR-0814).

`amendment-unapplied` lists `amendment <n> (#<pr>)` for each amendment file on the default branch,
added in the last 30 days (the 20 newest), with no applied line, whose adding pull request holds an
answerer's approval older than a day. A warning only. Commits come from a temporary git repository;
comments are `--api-dir` fixtures. Invented data; no network.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import check_amendments as ca  # noqa: E402
import doctor  # noqa: E402

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=UTC)
OLD = "2026-11-24T09:09:05Z"  # two days before NOW
YOUNG = "2026-11-26T08:00:00Z"  # four hours before NOW
SPEC = "docs/specs/0072-example-spec.md"
FORM_A = (
    "2026-11-24 (from `date -u`), brief #900: items 1 and 2 (to rule 3) applied to "
    f"`{SPEC}` word for word, on the maintainer's answer on #7 (comment 1).\n"
)
FORM_B = (
    "Applied (2026-11-25, from `date -u`): items 1 to 5 to\n"
    f"`{SPEC}`, word for word, by SPEC-0072\nbuild (c) (brief #900, ADR-0900).\n"
)


def git(root: Path, *args: str, when: str | None = None) -> str:
    env = dict(os.environ)
    if when:
        env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"] = when
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True, env=env
    )
    return proc.stdout


def text(number: int, tail: str = "") -> str:
    head = (
        f"# Proposed spec amendments {number} (SPEC-0072; REQ-079)\n\nVia a proposal (principle 6)."
    )
    item = "1. **SPEC-0072 rule 4.** Reuse `config.py` for the read.\n   Class: implementation\n"
    return f"{head}\n\n## Items\n\n{item}\n{tail}"


def project(tmp_path: Path, toml: str = "", approvers: str = '["@owner"]') -> Path:
    root = tmp_path / "root"
    (root / "config").mkdir(parents=True)
    (root / "docs" / "runs").mkdir(parents=True)
    (root / "docs" / "specs").mkdir(parents=True)
    (root / "constitution").mkdir()
    (root / "agk.toml").write_text(f'default_branch = "main"\n{toml}', encoding="utf-8")
    (root / "config" / "reviewers.yaml").write_text(
        f'version: 1\nverdict_authors: ["@boss"]\nspec_approvers: {approvers}\n', encoding="utf-8"
    )
    six = "6. Approved specs are owned by a reviewer group; agents propose patches"
    six += f"; {ca.PRINCIPLE_CLAUSE}.\n"
    (root / "constitution" / "principles.md").write_text(f"# Principles\n\n{six}", "utf-8")
    (root / SPEC).write_text("# SPEC-0072: Example\n\n- Status: Approved\n", encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    for key, value in (("user.email", "t@example.com"), ("user.name", "t")):
        git(root, "config", key, value)
    git(root, "add", "-A")
    git(root, "commit", "-q", "--no-gpg-sign", "-m", "base", when="2026-11-01T00:00:00Z")
    return root


def add(root: Path, number: int, pr: int | None = 7, when: str = "2026-11-23T10:00:00Z", tail=""):
    path = root / "docs" / "runs" / f"proposed-spec-amendments-{number}.md"
    path.write_text(text(number, tail), encoding="utf-8")
    git(root, "add", "-A")
    subject = f"Add amendment {number}" + (f" (#{pr})" if pr is not None else "")
    git(root, "commit", "-q", "--no-gpg-sign", "-m", subject, when=when)


def comment(body: str, login: str = "owner", at: str = OLD) -> dict:
    return {"id": 1, "user": {"login": login}, "created_at": at, "body": body}


def approved(n: int = 226, login: str = "owner", at: str = OLD) -> dict:
    return comment(f"Maintainer answer: amendment {n} approved", login, at)


def check(root: Path, api: dict[str, object] | None = None, now: datetime = NOW) -> doctor.Result:
    folder = root.parent / "api"
    folder.mkdir(exist_ok=True)
    for name, data in (api or {}).items():
        (folder / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
    reads = doctor.Reads("example-owner/example-repo", folder)
    return doctor.amendment_result(root, doctor.read_config(root), reads, now)


def test_1967_an_approval_older_than_a_day_is_listed(tmp_path):
    """REQ-020: brief #1967 answer 2."""
    root = project(tmp_path)
    add(root, 226)
    res = check(root, {"comments-7": [approved()]})
    assert (res.status, res.message) == ("fail", " (amendment 226 (#7))")


def test_1967_an_approval_younger_than_a_day_is_not_listed(tmp_path):
    """REQ-020: brief #1967 answer 2 (a day's grace)."""
    root = project(tmp_path)
    add(root, 226)
    assert check(root, {"comments-7": [approved(at=YOUNG)]}).status == "ok"


@pytest.mark.parametrize("form", [FORM_A, FORM_B], ids=["brief-form", "applied-wrapped"])
def test_1967_each_applied_form_is_not_listed(tmp_path, form):
    """REQ-020: brief #1967 answer 1 (both forms, the second wrapped over lines)."""
    assert ca.applied(text(226, form))
    root = project(tmp_path)
    add(root, 226, tail=form)
    assert check(root, {"comments-7": [approved()]}).status == "ok"


def test_1967_a_mention_of_applied_is_not_an_applied_line():
    """REQ-020: brief #1967 answer 1 (one pattern per form, not the word)."""
    assert not ca.applied(text(226, "Items 2 and 3 are applied by a later build.\n"))


def test_1967_an_answer_by_a_non_answerer_is_not_counted(tmp_path):
    """REQ-020: brief #1967 answer 1 (`session.owner_people`)."""
    root = project(tmp_path)
    add(root, 226)
    assert check(root, {"comments-7": [approved(login="someone")]}).status == "ok"
    assert ca.approval([approved(login="someone")], {"owner"}, 226) is None
    assert ca.approval([approved()], {"@Owner"}, 226) == datetime(2026, 11, 24, 9, 9, 5, tzinfo=UTC)
    assert ca.approval([approved(227)], {"owner"}, 226) is None


def test_1967_a_correction_withdrawing_the_approval_is_not_listed(tmp_path):
    """REQ-020: brief #1967 answer 4."""
    root = project(tmp_path)
    add(root, 226)
    later = comment("Correction: amendment 226 is withdrawn", at="2026-11-24T10:00:00Z")
    assert check(root, {"comments-7": [approved(), later]}).status == "ok"


def test_1967_the_thirty_day_and_twenty_file_bounds(tmp_path):
    """REQ-020: brief #1967 answer 2 (`AMENDMENT_DAYS`, `AMENDMENT_FILES`; Q-AA-5)."""
    root = project(tmp_path)
    add(root, 200, pr=5, when="2026-10-20T10:00:00Z")  # 37 days old: not read
    for n in range(201, 222):  # 21 files: the oldest (201) is past the 20 newest
        add(root, n, pr=n, when=f"2026-11-{n - 200:02d}T10:00:00Z")
    api = {f"comments-{n}": [approved(n)] for n in range(200, 222)}
    res = check(root, api)
    assert res.status == "fail"
    assert "amendment 221 (#221)" in res.message and "amendment 202 (#202)" in res.message
    assert "(#201)" not in res.message and "(#5)" not in res.message
    assert (doctor.AMENDMENT_DAYS, doctor.AMENDMENT_FILES) == (30, 20)


def test_1967_an_applied_file_takes_no_place_in_the_twenty(tmp_path):
    """REQ-020: brief #1967 answer 2 (the 20 newest files with no applied line)."""
    root = project(tmp_path)
    add(root, 201, pr=201, when="2026-11-01T10:00:00Z")
    for n in range(202, 222):  # 20 newer files, each applied
        add(root, n, pr=n, when=f"2026-11-{n - 200:02d}T10:00:00Z", tail=FORM_A)
    res = check(root, {"comments-201": [approved(201)]})
    assert (res.status, res.message) == ("fail", " (amendment 201 (#201))")


@pytest.mark.parametrize(
    "api", [{}, {"comments-7": {"message": "Bad credentials", "status": "401"}}]
)
def test_1967_a_failed_read_is_cannot_check_never_ok(tmp_path, api):
    """REQ-020: brief #1967 answer 4 (a reason class, never `ok`)."""
    root = project(tmp_path)
    add(root, 226)
    res = check(root, api)
    assert res.status == "cannot-check" and res.reason in ("bad-response", "gh-unauthenticated")


def test_1967_more_pages_than_read_is_cannot_check(tmp_path):
    """REQ-020: brief #1967 answer 4 (`LOST_PAGES`)."""
    root = project(tmp_path)
    add(root, 226)
    page = [comment("Progress: x")] * 100
    api = {"comments-7": page, **{f"comments-7-p{p}": page for p in range(2, 11)}}
    res = check(root, api)
    assert (res.status, res.reason) == ("cannot-check", "comments-unbounded")


def test_1967_a_file_with_no_pull_request_is_skipped_and_counted(tmp_path):
    """REQ-020: brief #1967 answer 4 (`unread <k>`)."""
    root = project(tmp_path)
    add(root, 226)
    add(root, 227, pr=None)
    res = check(root, {"comments-7": [approved()]})
    assert (res.status, res.message) == ("fail", " (amendment 226 (#7)) (unread 1)")


def test_1967_a_later_build_named_in_the_file_is_still_listed(tmp_path):
    """REQ-020: brief #1967 answer 4 (240 and 241's case)."""
    root = project(tmp_path)
    add(root, 240, tail="Items 1 and 2 are build (i)'s, applied there.\n")
    assert check(root, {"comments-7": [approved(240)]}).status == "fail"


def test_1967_no_file_or_no_branch(tmp_path):
    """REQ-020: brief #1967 answer 3 (`default_branch`): none to read is ok; a file in the tree
    with no branch to read it from is `cannot-check`."""
    root = project(tmp_path)
    assert check(root).status == "ok"
    (root / "agk.toml").write_text('default_branch = "trunk"\n', encoding="utf-8")
    add(root, 226)
    res = check(root, {"comments-7": [approved()]})
    assert (res.status, res.reason) == ("cannot-check", "no-default-branch")


def test_1967_the_origin_branch_is_read_before_the_local_one(tmp_path):
    """REQ-020: brief #1967 answer 3 (`lost_ref`: `origin/<default_branch>` first)."""
    root = project(tmp_path)
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    add(root, 226)  # on the local branch only
    assert check(root, {"comments-7": [approved()]}).status == "ok"
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    assert check(root, {"comments-7": [approved()]}).status == "fail"


@pytest.mark.parametrize("approvers", ['["@REPLACE-ME"]', "[]"])
def test_1967_no_answerer_is_cannot_check_naming_the_setting(tmp_path, approvers):
    """REQ-020: brief #1967 answer 3 (`config/reviewers.yaml`)."""
    root = project(tmp_path, approvers=approvers)
    (root / "config" / "reviewers.yaml").write_text(
        f'version: 1\nverdict_authors: ["@REPLACE-ME"]\nspec_approvers: {approvers}\n', "utf-8"
    )
    add(root, 226)
    res = check(root, {"comments-7": [approved()]})
    assert (res.status, res.reason) == ("cannot-check", "no-answerer")
    assert (
        "spec_approvers" in doctor.HINTS["no-answerer"] and "@" not in doctor.HINTS["no-answerer"]
    )


@pytest.mark.parametrize("mode", ["team", "solo"])
def test_1967_review_mode(tmp_path, mode):
    """REQ-020: brief #1967 answer 3 (`review_mode`): solo counts the first line exact only."""
    root = project(tmp_path, toml=f'review_mode = "{mode}"\n')
    add(root, 226)
    loose = comment("Maintainer answer: amendment 226 approved, with thanks")
    assert check(root, {"comments-7": [approved()]}).status == "fail"
    expected = "ok" if mode == "solo" else "fail"
    assert check(root, {"comments-7": [loose]}).status == expected


@pytest.mark.parametrize("on", [False, True])
def test_1967_settle_amendments_counts_a_settled_line_only_when_on(tmp_path, on):
    """REQ-020: brief #1967 answer 3 (`[steward] settle_amendments`, through `settled_keys`)."""
    root = project(tmp_path, toml=f"[steward]\nsettle_amendments = {str(on).lower()}\n")
    add(root, 226)
    body = (root / "docs" / "runs" / "proposed-spec-amendments-226.md").read_text("utf-8")
    line = ca.settle(226, body, root, "the spec says it", True)
    assert line is not None or not on
    line = line or ca.SETTLED_FORM.format(226, "e", "implementation", "SPEC-0072 rule 4") + (
        f"\nText: {ca.digest(body)}\n\n{ca.WHO}\n"
    )
    res = check(root, {"comments-7": [comment(line)]})
    assert res.status == ("fail" if on else "ok")


@pytest.mark.parametrize("mode", ["strict", "flow"])
@pytest.mark.parametrize("execution", ["hosted", "hybrid", "pool", "local"])
def test_1967_pr_mode_and_execution_change_nothing(tmp_path, mode, execution):
    """REQ-020: brief #1967 answer 3 (`pr_mode`, `execution`: no effect)."""
    root = project(tmp_path, toml=f'pr_mode = "{mode}"\nexecution = "{execution}"\n')
    add(root, 226)
    assert check(root, {"comments-7": [approved()]}).message == " (amendment 226 (#7))"


def test_1967_personal_mode_is_not_applicable(tmp_path):
    """REQ-020: brief #1967 answer 3 (`[personal] forge = "files"`: no forge read)."""
    root = project(tmp_path, toml='[personal]\nforge = "files"\n')
    add(root, 226)
    res = check(root)  # no recorded comments: a read would be cannot-check
    assert res.status == "ok" and "not applicable" in res.message


def run(root: Path, api: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "doctor.py"), "--api-dir", str(api), *extra, str(root)],
        capture_output=True,
        text=True,
    )


def test_1967_the_check_is_a_warning_and_paused_prints_only_its_line(tmp_path):
    """REQ-020: brief #1967 answers 2 and 3 (a warning, never an error; `paused = true`)."""
    root = project(tmp_path)
    add(root, 226)
    check(root, {"comments-7": [approved()]})  # writes the recorded comments
    entry = doctor.CHECKS["amendment-unapplied"]
    assert entry[0] == "warn" and "brief #1900" in entry[3]
    (root / "agk.toml").write_text('paused = true\ndefault_branch = "main"\n', encoding="utf-8")
    proc = run(root, tmp_path / "api")
    assert "amendment-unapplied" not in proc.stdout


def test_1967_a_malformed_agk_toml_is_refused_naming_the_setting(tmp_path):
    """REQ-020: brief #1967 answer 3 (refused as today, naming the path class)."""
    root = project(tmp_path)
    (root / "agk.toml").write_text("default_branch = \n", encoding="utf-8")
    with pytest.raises(doctor.Refusal, match="path class agk.toml"):
        doctor.read_config(root)
    assert timedelta(days=1) == doctor.FINISHED_AFTER
