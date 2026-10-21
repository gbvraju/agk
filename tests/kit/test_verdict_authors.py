"""Tests of the listed verdict authors (SPEC-0021 rules 5 and 6, REQ-028 AC4 and AC5).

A comment is a verdict only when its author is a listed verdict author: the `verdict_authors`
list of `config/reviewers.yaml`, else the user handle of the team `maintainers`. A team handle
lists nobody, and then the verdict-dependent fields read `unknown`. No network, no model.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from test_facts import DROP, ENV_GIT, FACTS, FIXTURES, build_repo, git, no_gh_path

METRICS_FIXTURES = Path(__file__).parent / "fixtures" / "metrics"
CLEARED = "Verdict: cleared 0066abc"
FIX = "Verdict: fix list 0066abc"
REJECTED = "Verdict: rejected 0066abc"


def comment(body: str, login: str | None, at: int = 0) -> dict:
    found = {"body": body, "created_at": f"2026-10-06T10:{at:02d}:00Z"}
    if login is not None:
        found["user"] = {"login": login}
    return found


def config(handle: str = "@some-user", authors: str | None = None) -> str:
    extra = f"verdict_authors: {authors}\n" if authors is not None else ""
    return (
        "version: 1\n"
        f"{extra}"
        "classes:\n"
        "  protected: {paths: [config/], approvers: [maintainers]}\n"
        "teams:\n"
        f'  maintainers: {{github_team: "{handle}"}}\n'
    )


def with_config(repo, handle: str = "@some-user", authors: str | None = None) -> None:
    repo.write("config/reviewers.yaml", config(handle, authors))
    repo.write("config/protected-paths.txt", "config/\n")


# --- AC4: a verdict by an unlisted author is ignored ---------------------------------------------


@pytest.mark.parametrize(
    ("body", "kind"), [(CLEARED, "cleared"), (FIX, "fix"), (REJECTED, "rejected")]
)
def test_ac4_a_verdict_by_a_listed_author_counts_and_by_anyone_else_does_not(body, kind):
    """REQ-028 AC4: rule 5 (the three forms; `cleared` too)."""
    from metrics import verdicts

    comments = [comment(body, "reviewer"), comment(body, "stranger", 1)]
    assert verdicts(comments, ["reviewer"]) == [(kind, "0066abc")]
    assert verdicts([comments[1]], ["reviewer"]) == []


def test_ac4_the_author_is_compared_without_regard_to_case_and_an_at_sign():
    """REQ-028 AC4: rule 5."""
    from metrics import verdicts

    comments = [comment(CLEARED, "GbvRaju")]
    assert verdicts(comments, ["gbvraju"]) == [("cleared", "0066abc")]
    assert verdicts(comments, ["@GBVRAJU"]) == [("cleared", "0066abc")]


def test_ac4_a_comment_without_a_readable_author_is_not_a_verdict():
    """REQ-028 AC4: rule 5 (a missing `user`, a null `user`, an empty login)."""
    from metrics import verdicts

    bare = [comment(CLEARED, None), {**comment(CLEARED, None), "user": None}]
    assert verdicts(bare + [comment(CLEARED, "")], ["reviewer"]) == []


def test_ac4_without_a_list_the_reader_filters_nothing_as_before():
    """REQ-028 AC4: rule 5 (a caller that passes no list, such as the unit tests of the forms)."""
    from metrics import verdicts

    assert verdicts([comment(CLEARED, None)]) == [("cleared", "0066abc")]


def pull_case(tmp_path: Path, comments: list[dict]) -> Path:
    case = tmp_path / "case"
    shutil.copytree(METRICS_FIXTURES / "fix-lists-cleared", case)
    (case / "comments-102.json").write_text(json.dumps(comments))
    return case


def record(repo, case: Path) -> dict[str, str]:
    from test_metrics import metrics, table

    proc = metrics(repo, case)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return table(proc.stdout)[102]


def test_ac4_the_metrics_count_only_the_listed_authors_verdicts(repo, tmp_path):
    """REQ-028 AC4: rule 5 (rounds, rejections and the cleared head)."""
    with_config(repo, authors="[reviewer]")
    case = pull_case(
        tmp_path,
        [
            comment(FIX, "reviewer", 0),
            comment(FIX, "stranger", 1),
            comment(REJECTED, "stranger", 2),
            comment("Verdict: cleared 0066000", "stranger", 3),
        ],
    )
    row = record(repo, case)
    assert (row["review_rounds"], row["rejected_verdicts"]) == ("1", "0")
    assert row["merged_head_cleared"] == "no"


def test_ac4_a_stranger_alone_leaves_the_fields_unknown_not_zero(repo, tmp_path):
    """REQ-028 AC4: rule 5 (no verdict by a listed author reads as no verdict: `unknown`)."""
    with_config(repo, authors="[reviewer]")
    row = record(repo, pull_case(tmp_path, [comment("Verdict: cleared 0066000", "stranger")]))
    assert (row["review_rounds"], row["merged_head_cleared"]) == ("unknown", "unknown")


def facts_of(tmp_path: Path, comments: list[dict], authors: str | None) -> dict:
    """Facts of the `ok` case with pull request #5 given `comments`; `authors` is the list text."""
    api = tmp_path / "api"
    shutil.copytree(FIXTURES / "ok" / "api", api)
    (api / "comments-5.json").write_text(json.dumps(comments))
    root = build_repo("ok", tmp_path)
    reviewers = root / "config" / "reviewers.yaml"
    text = reviewers.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if not ln.startswith("verdict_authors")]
    if authors is not None:
        lines.insert(1, f"verdict_authors: {authors}")
    reviewers.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if git(root, "status", "--porcelain").strip():
        git(root, "commit", "-qam", "authors")
    meta = json.loads((FIXTURES / "ok" / "case.json").read_text())
    env = {k: v for k, v in os.environ.items() if k not in DROP} | ENV_GIT
    env["PATH"] = no_gh_path(tmp_path)
    args = ["--today", meta["today"], "--weeks", str(meta["weeks"]), *meta["args"]]
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(FACTS), *args, "--api-dir", str(api), str(root)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def pull(doc: dict, number: int = 5) -> dict:
    return next(p for p in doc["pull_requests"] if p["number"] == number)


def test_ac4_the_facts_record_only_the_listed_authors_verdicts(tmp_path):
    """REQ-028 AC4: rule 5 (SPEC-0009 rule 14 reads the same function)."""
    doc = facts_of(
        tmp_path,
        [comment(FIX, "reviewer", 0), comment(CLEARED, "stranger", 1)],
        "[reviewer]",
    )
    assert [(v["kind"], v["sha"]) for v in pull(doc)["verdicts"]] == [("fix", "0066abc")]


# --- AC5: the list, the fallback and nobody listed -----------------------------------------------


def test_ac5_the_list_is_read_first_with_at_signs_and_case_removed(repo):
    """REQ-028 AC5: rule 5 (the `verdict_authors` list wins over the maintainers handle)."""
    from reviewers import verdict_authors

    with_config(repo, handle="@some-user", authors='[Alice, "@Bob-2"]')
    assert verdict_authors(repo.root) == ["alice", "bob-2"]


def test_ac5_without_a_list_the_maintainers_user_handle_is_the_only_author(repo):
    """REQ-028 AC5: rule 5."""
    from reviewers import verdict_authors

    with_config(repo, handle="@Some-User")
    assert verdict_authors(repo.root) == ["some-user"]


def test_ac5_a_team_handle_with_no_list_lists_nobody(repo):
    """REQ-028 AC5: rule 5 (a team cannot be expanded without a network call)."""
    from reviewers import verdict_authors

    with_config(repo, handle="@demo-org/maintainers")
    assert verdict_authors(repo.root) == []


@pytest.mark.parametrize("text", ["", "classes: [oops\n"])
def test_ac5_a_missing_or_unreadable_file_lists_nobody(repo, text):
    """REQ-028 AC5: rule 5 (fail closed)."""
    from reviewers import verdict_authors

    if text:
        repo.write("config/reviewers.yaml", text)
    assert verdict_authors(repo.root) == []


def test_ac5_the_metrics_read_unknown_when_nobody_is_listed(repo, tmp_path):
    """REQ-028 AC5: rule 6 (never 0 or `no`; `cost_class` follows)."""
    with_config(repo, handle="@demo-org/maintainers")
    row = record(repo, pull_case(tmp_path, [comment(CLEARED, "reviewer")]))
    for key in ("rejected", "rejected_verdicts", "review_rounds", "merged_head_cleared"):
        assert row[key] == "unknown", key
    assert row["cost_class"] == "unknown"


def test_ac5_the_facts_read_unknown_when_nobody_is_listed(tmp_path):
    """REQ-028 AC5: rule 6 (the facts' `verdicts` is the string `unknown`)."""
    doc = facts_of(tmp_path, [comment(CLEARED, "reviewer")], None)
    assert pull(doc)["verdicts"] == "unknown"


def check(repo):
    return repo.run("reviewers.py", "--check")


def test_ac5_check_passes_with_a_list_or_a_user_handle(repo):
    """REQ-028 AC5: rule 6."""
    with_config(repo, handle="@demo-org/maintainers", authors="[alice]")
    assert check(repo).returncode == 0
    with_config(repo, handle="@some-user")
    assert check(repo).returncode == 0


@pytest.mark.parametrize("authors", [None, "[]", "[a/b]", "[a b]", "[]x"])
def test_ac5_check_names_the_setting_when_nobody_is_listed(repo, authors):
    """REQ-028 AC5: rule 6 (a team handle and no valid list; the message never names a value)."""
    with_config(repo, handle="@demo-org/maintainers", authors=authors)
    proc = check(repo)
    assert proc.returncode == 1, proc.stdout
    assert "verdict_authors" in proc.stdout
    assert "demo-org" not in proc.stdout and "a/b" not in proc.stdout


def test_ac5_a_top_level_mapping_is_still_refused(repo):
    """REQ-028 AC5: rule 5 (only a list is new at the top level)."""
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: {a: b}\n")
    repo.write("config/protected-paths.txt", "config/\n")
    assert check(repo).returncode == 1
