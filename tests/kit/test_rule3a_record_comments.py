"""The record comments reach the after-merge run and prepush (brief #601 fix list, amendment 122).

ADR-0293 decisions 3 and 4, SPEC-0039 rule 6 as amendment 122 changes it. `merge_cleared.py`
fetches the Final comment of each rule 3a record in the merge commit's history (the GETs of the
workflow's `Record comments` step), writes them to `<scratch>/home/record-comments.json` and adds
`AGK_RECORD_COMMENTS=<that file>` to the `env -i` list of its governance run;
`check_protected_changes.py` and `check_release.py` read that variable when `--comments` is
absent. `prepush.py` fetches the same comments (GET only) when the body has `Covered-by:` and the
base has a record, and fails closed, naming the option, when it cannot. Saved responses, a fake
`gh`, invented logins, no network.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from test_merge_cleared_after import MERGED, in_process, main_in
from test_merge_cleared_verdict import BASE
from test_prepush import GOOD_BODY, TOML, path_with
from test_rule3a_covered_and_label import CONFIG, RECORD, base, final_comment, fix_list

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import check_release  # noqa: E402
import merge_cleared  # noqa: E402

VARIABLE = "AGK_RECORD_COMMENTS"
COVERED = "Brief: #1\nAdvances: REQ-028\nCovered-by: ADR-0009\n"
PREPUSH_BODY = GOOD_BODY.replace("Advances: REQ-001\n", "Advances: REQ-001\nCovered-by: ADR-0009\n")
ORIGIN = "https://github.com/example-owner/example-repo.git"
COMMENT_PATH = "repos/example-owner/example-repo/issues/comments/42"


# --- 1. merge_cleared.py: the after-merge run gets the record comments -------------------------


def test_req028_the_after_merge_argument_list_carries_the_variable():
    """REQ-028: fix list item 1 (`AGK_RECORD_COMMENTS=<scratch>/home/record-comments.json`)."""
    home = Path("home")
    argv = merge_cleared.governance_argv(Path("tree"), home, home / "pr-body.md", BASE, 1800.0)
    cut = argv.index("make")
    assert argv[cut - 4 : cut] == [
        argv[cut - 4],
        f"HOME={home}",
        f"AGK_PR_BODY={home / 'pr-body.md'}",
        f"{VARIABLE}={home / 'record-comments.json'}",
    ]
    assert argv[cut - 4].startswith("PATH=") and argv[cut - 6 : cut - 4] == ["env", "-i"]


SEES_COMMENTS = """
import json, os, sys
path = os.environ.get('AGK_RECORD_COMMENTS')
text = open(path, encoding='utf-8').read() if path and os.path.isfile(path) else None
with open(LOG, 'a', encoding='utf-8') as fh:
    fh.write(json.dumps({'env': dict(os.environ), 'comments': text}) + '\\n')
sys.exit(0)
"""


def comments_world(tmp_path: Path, monkeypatch, records: dict) -> Path:
    """An in-process run whose merge commit's history holds RECORDS and whose fake make saves
    the file that AGK_RECORD_COMMENTS names."""
    saved = {"record_comments": {"1005": {"id": 1005, "body": "Verdict: fix list"}}}
    root = in_process(tmp_path, monkeypatch, **saved)
    log = tmp_path / "make-seen.jsonl"
    (tmp_path / "bin" / "make").write_text(
        f"#!{sys.executable}\nLOG = {str(log)!r}\n" + SEES_COMMENTS, encoding="utf-8"
    )
    monkeypatch.setattr(merge_cleared, "final_records", lambda root_, ref: records)
    return root


def seen(tmp_path: Path) -> list[dict]:
    log = tmp_path / "make-seen.jsonl"
    return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]


def test_req028_the_after_merge_run_gets_the_final_comment_of_each_record(
    tmp_path, monkeypatch, capsys
):
    """REQ-028: fix list item 1 (the workflow's GETs; an unreadable one is left out)."""
    records = {"0009": (7, 1005), "0010": (8, 999)}
    root = comments_world(tmp_path, monkeypatch, records)
    code, lines, made = main_in(root, capsys)
    assert lines == [MERGED] and code == 0
    gets = [c for c in made if c[3].startswith("repos/") and "/issues/comments/" in c[3]]
    assert all(c[1:3] == ["--method", "GET"] for c in gets), gets
    assert {c[3].rsplit("/", 1)[-1] for c in gets} == {"1005", "999"}
    run = seen(tmp_path)
    assert len(run) == 2, "the run before the merge (brief #610) and the run after it"
    for one in run:
        assert json.loads(one["comments"]) == [{"id": 1005, "body": "Verdict: fix list"}]
        path = Path(one["env"][VARIABLE])
        assert path.parent == Path(one["env"]["HOME"]) and path.name == "record-comments.json"
        assert not path.exists(), "removed with the scratch folder"
        assert set(one["env"]) - {"LC_CTYPE"} == {"PATH", "HOME", "AGK_PR_BODY", VARIABLE}


def test_req028_no_record_writes_an_empty_list_and_reads_nothing(tmp_path, monkeypatch, capsys):
    """REQ-028: fix list item 1 (no record: no GET, and the checks read an empty list)."""
    root = comments_world(tmp_path, monkeypatch, {})
    code, _, made = main_in(root, capsys)
    assert code == 0
    assert not [c for c in made if "/issues/comments/" in c[3]]
    assert json.loads(seen(tmp_path)[0]["comments"]) == []


def test_req028_the_after_merge_run_passes_a_rule_3a_covered_by(repo, tmp_path):
    """REQ-028: fix list item 1 (`check_protected_changes.py` reads AGK_RECORD_COMMENTS)."""
    base(repo)
    home = tmp_path / "home"
    home.mkdir()
    (home / "pr-body.md").write_text(COVERED, encoding="utf-8")
    (home / "record-comments.json").write_text(json.dumps([final_comment()]), encoding="utf-8")
    env = {
        "HOME": str(home),
        "AGK_PR_BODY": str(home / "pr-body.md"),
        VARIABLE: str(home / "record-comments.json"),
    }
    proc = repo.run("check_protected_changes.py", "--base", "main", **env)
    assert proc.returncode == 0, proc.stdout
    assert "Covered-by" in proc.stdout


def test_req028_an_option_given_wins_over_the_variable(repo, tmp_path):
    """REQ-028: fix list item 1 (the variable is read only when `--comments` is absent)."""
    base(repo)
    good, empty = tmp_path / "good.json", tmp_path / "empty.json"
    good.write_text(json.dumps([final_comment()]), encoding="utf-8")
    empty.write_text("[]", encoding="utf-8")
    body = tmp_path / "pr-body.md"
    body.write_text(COVERED, encoding="utf-8")
    args = ("--base", "main", "--body", str(body), "--comments", str(empty))
    proc = repo.run("check_protected_changes.py", *args, **{VARIABLE: str(good)})
    assert proc.returncode == 1, proc.stdout


def test_req028_check_release_reads_the_variable_without_the_option(tmp_path, monkeypatch):
    """REQ-028: fix list item 1 (`check_release.py` reads AGK_RECORD_COMMENTS)."""
    saved = tmp_path / "record-comments.json"
    saved.write_text(json.dumps([final_comment()]), encoding="utf-8")
    got: list = []
    monkeypatch.setattr(check_release, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(check_release, "check", lambda root, comments: got.append(comments) or 0)
    monkeypatch.setattr(sys, "argv", ["check_release.py"])
    monkeypatch.setenv(VARIABLE, str(saved))
    assert check_release.main() == 0
    monkeypatch.delenv(VARIABLE)
    assert check_release.main() == 0
    assert got == [[final_comment()], None]


# --- 2. prepush.py: the same comments, GET only, fail closed ------------------------------------

FAKE_GH = """#!{python}
import json, sys
with open({log!r}, 'a', encoding='utf-8') as fh:
    fh.write(json.dumps(sys.argv[1:]) + '\\n')
if {fail!r}:
    sys.stderr.write('HTTP 502: Bad Gateway\\n'); sys.exit(1)
print(json.dumps({answer!r}))
"""
NEEDS_COMMENTS = (
    "agk-governance:\n"
    '\t@test -n "$$AGK_RECORD_COMMENTS" && grep -q \'"id": 42\' "$$AGK_RECORD_COMMENTS"'
    " && echo GOVERNANCE_RAN\n"
)
PLAIN = "agk-governance:\n\t@echo GOVERNANCE_RAN\n"


def prepush_world(repo, tmp_path: Path, mk: str, record: str | None = RECORD, fail=False):
    """A project whose base holds (by default) a rule 3a record, an origin on GitHub, a body with
    `Covered-by:`, and a fake gh that saves its argument lists. (folder of the fake gh, body)."""
    repo.commit({"agk.toml": TOML, "agk.mk": mk, "src/code.txt": "base\n"}, "base")
    if record is not None:
        repo.commit({"README.md": "x\n"}, record)
    repo.git("remote", "add", "origin", ORIGIN)
    repo.branch("feature")
    repo.commit({"src/code.txt": "change\n"}, "change")
    tools = tmp_path / "tools"
    tools.mkdir()
    gh = tools / "gh"
    log = tmp_path / "gh-calls.jsonl"
    gh.write_text(
        FAKE_GH.format(python=sys.executable, log=str(log), fail=fail, answer=final_comment()),
        encoding="utf-8",
    )
    gh.chmod(0o755)
    body = tmp_path / "pr-body.md"
    body.write_text(PREPUSH_BODY, encoding="utf-8")
    return tools, body


def gh_calls(tmp_path: Path) -> list[list[str]]:
    log = tmp_path / "gh-calls.jsonl"
    if not log.exists():
        return []
    return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]


def prepush(repo, tools: Path, *args: str):
    env = {k: v for k, v in os.environ.items() if k != VARIABLE}
    env["PATH"] = path_with(tools)
    return repo.run("prepush.py", *args, "--quick", "--base", "main", **env)


def test_req028_prepush_passes_the_record_comments_file(repo, tmp_path):
    """REQ-028: fix list item 2 (GET only, into a temporary file the governance step reads)."""
    tools, body = prepush_world(repo, tmp_path, NEEDS_COMMENTS)
    proc = prepush(repo, tools, "--body", str(body))
    assert "prepush: governance ok" in proc.stdout, proc.stdout
    assert gh_calls(tmp_path) == [["api", "--method", "GET", COMMENT_PATH]]
    left = set(repo.git("status", "--porcelain", "-uall").split("\n")) - {""}
    ours = {"?? gh-calls.jsonl", "?? pr-body.md", "?? tools/gh"}  # this test's own files
    assert left == ours, "prepush leaves no file in the checkout"


def test_req028_a_failed_fetch_fails_closed_naming_the_option(repo, tmp_path):
    """REQ-028: fix list item 2 (a comment that cannot be read fails the step)."""
    tools, body = prepush_world(repo, tmp_path, PLAIN, fail=True)
    proc = prepush(repo, tools, "--body", str(body))
    assert proc.returncode == 1
    assert "prepush: governance FAIL" in proc.stdout
    assert "--comments" in proc.stdout and "rule 3a" in proc.stdout
    assert "GOVERNANCE_RAN" not in proc.stdout, "make did not run"
    assert "502" not in proc.stdout, "the message names the option, not the answer"


@pytest.mark.parametrize(
    ("record", "text"),
    [(None, PREPUSH_BODY), (RECORD, GOOD_BODY)],
    ids=["no-record", "no-covered-by"],
)
def test_req028_prepush_fetches_nothing_without_covered_by_or_a_record(
    repo, tmp_path, record, text
):
    """REQ-028: fix list item 2 (only a `Covered-by:` body on a base with a record fetches)."""
    tools, body = prepush_world(repo, tmp_path, PLAIN, record=record)
    body.write_text(text, encoding="utf-8")
    proc = prepush(repo, tools, "--body", str(body))
    assert "prepush: governance ok" in proc.stdout, proc.stdout
    assert gh_calls(tmp_path) == []


# --- 3. brief #1181: the workflow fetches only the record comments a check reads ----------------
# `check_adrs.py --record-ids --body FILE` prints every record's id for a release pull request
# (a version of agk.toml other than the merge base's, as `check_release.check` tests it), else the
# ids of the records of the ADRs that a `Covered-by:` line names, else nothing (ADR-0501).

RELEASE_ADRS = {
    "0009": "docs/adr/0009-intake-of-an-invented-requirement.md",
    "0010": "docs/adr/0010-another-invented-decision.md",
}
RECORDS = {"0009": (7, 42), "0010": (8, 77)}
RELEASE_CLASSES = "config/\nscripts/agk/\nkit/\nagk.toml\n.claude-plugin/\ndocs/adr/\n"
CHANGES = (
    "# Changelog\n\n## Unreleased\n\n- #5 an invented change\n\n## 1.0.0 (2026-01-01)\n\n- #1 x\n"
)
RELEASED = (
    "# Changelog\n\n## Unreleased\n\n## 1.1.0 (2026-11-13)\n\n- #5 an invented change\n\n"
    "## 1.0.0 (2026-01-01)\n\n- #1 x\n"
)


def adr_of(number: str, status: str) -> str:
    return (
        f"# ADR-{number}: An invented decision\n\n- Status: {status}\n- Date: 2026-01-01\n"
        "- Deciders: maintainers\n- Related: none\n- Requirements: REQ-028\n\n"
        "## Decision\n\nThe build changes `config/` `scripts/agk/`.\n"
    )


def versions_of(version: str) -> dict[str, str]:
    return {
        "agk.toml": f'version = "{version}"\npr_mode = "flow"\n',
        "kit/manifest.json": json.dumps({"kit_version": version}),
        ".claude-plugin/plugin.json": json.dumps({"name": "example", "version": version}),
    }


def all_comments() -> list[dict]:
    """The Final comment of each record, as `gh api repos/{repo}/issues/comments/<id>` answers."""
    return [
        {
            "id": cid,
            "issue_url": f"https://api.example.com/repos/example-owner/example-repo/issues/{pr}",
            "user": {"login": "reviewer"},
            "body": fix_list("a1b2c3d", f"Final: {RELEASE_ADRS[n]} Proposed -> Accepted"),
        }
        for n, (pr, cid) in sorted(RECORDS.items())
    ]


def records_world(repo, change: str):
    """A flow-mode kit at 1.0.0 whose base records ADR-0009 (Final 42) and ADR-0010 (Final 77),
    and a branch that makes CHANGE: `plain` (a file outside every protected class), `covered`
    (a protected file, for a `Covered-by:` body) or `release` (the three versions raised, the
    changelog moved and both recorded ADRs flipped)."""
    files = {
        "config/protected-paths.txt": "# c\n" + RELEASE_CLASSES,
        "config/reviewers.yaml": CONFIG,
        "config/x.txt": "x\n",
        "CHANGELOG.md": CHANGES,
        "kit/hashes.json": "{}\n",
        "scripts/agk/check_release.py": "# the check exists on the base\n",
        "src/code.txt": "base\n",
        **versions_of("1.0.0"),
        **{path: adr_of(n, "Proposed") for n, path in RELEASE_ADRS.items()},
    }
    repo.commit(files, "base")
    for n, (pr, cid) in sorted(RECORDS.items()):
        record = f"Example (#{pr})\n\nADR-{n} Accepted (Final {cid})\nMerged-by: merge_cleared.py\n"
        repo.commit({"README.md": f"{n}\n"}, record)
    repo.branch()
    if change == "plain":
        repo.commit({"src/code.txt": "change\n"})
    elif change == "covered":
        repo.commit({"config/x.txt": "y\n"})
    else:
        flips = {path: adr_of(n, "Accepted") for n, path in RELEASE_ADRS.items()}
        repo.commit(
            {**versions_of("1.1.0"), "CHANGELOG.md": RELEASED, "kit/hashes.json": "{}\n\n", **flips}
        )
    return repo


@pytest.fixture
def outside(tmp_path_factory) -> Path:
    """A folder outside the repository (the runner's temporary directory): `check_release`
    counts every file of the checkout as changed."""
    return tmp_path_factory.mktemp("runner-temp")


def body_file(tmp_path: Path, text: str) -> str:
    path = tmp_path / "pr-body.md"
    path.write_text(text, encoding="utf-8")
    return str(path)


def printed_ids(repo, *args: str) -> list[int]:
    proc = repo.run("check_adrs.py", "--record-ids", *args)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return [int(x) for x in proc.stdout.split()]


NO_COVER = "Brief: #1\nAdvances: REQ-028\n"
COVER_0009 = "Brief: #1\nAdvances: REQ-028\nCovered-by: ADR-0009\n"


def test_req039_a_body_without_covered_by_and_no_version_change_prints_nothing(repo, outside):
    """REQ-039: brief #1181 answer 4 (a): an ordinary pull request fetches no record comment."""
    records_world(repo, "plain")
    assert printed_ids(repo, "--body", body_file(outside, NO_COVER)) == []


def test_req039_a_push_writes_an_empty_body_and_prints_nothing(repo, outside):
    """REQ-039: brief #1181 answer 2 (the `PR body file` step writes an empty body on a push)."""
    records_world(repo, "plain")
    assert printed_ids(repo, "--body", body_file(outside, "\n")) == []


def test_req039_covered_by_a_recorded_adr_prints_that_record_id_only(repo, outside):
    """REQ-039: brief #1181 answer 4 (b)."""
    records_world(repo, "covered")
    assert printed_ids(repo, "--body", body_file(outside, COVER_0009)) == [42]


def test_req039_covered_by_an_adr_without_a_record_prints_nothing(repo, outside):
    """REQ-039: brief #1181 answer 1 (only an ADR that has a record)."""
    records_world(repo, "covered")
    text = COVER_0009.replace("ADR-0009", "ADR-0011")
    assert printed_ids(repo, "--body", body_file(outside, text)) == []


def test_req039_a_version_change_prints_every_id(repo, outside):
    """REQ-039: brief #1181 answer 4 (c): a release pull request reads every record."""
    records_world(repo, "release")
    assert printed_ids(repo, "--body", body_file(outside, NO_COVER)) == [42, 77]


def test_req039_without_body_every_id_is_printed_as_before(repo):
    """REQ-039: brief #1181 answer 4 (d): nothing changes until the workflow passes `--body`."""
    records_world(repo, "plain")
    assert printed_ids(repo) == [42, 77]


def test_req039_an_unreadable_body_prints_every_id(repo, outside):
    """REQ-039: brief #1181 answer 1 (fail closed: a body that cannot be read narrows nothing)."""
    records_world(repo, "plain")
    assert printed_ids(repo, "--body", str(outside / "missing.md")) == [42, 77]


def results(repo, tmp_path: Path, body: str, comments: list[dict]) -> tuple:
    """The exit and output of `check_protected_changes.py` and `check_release.py` given COMMENTS."""
    saved = tmp_path / "record-comments.json"
    saved.write_text(json.dumps(comments), encoding="utf-8")
    env = {"AGK_BASE": "main"}
    protected = repo.run(
        "check_protected_changes.py", "--body", body, "--comments", str(saved), **env
    )
    release = repo.run("check_release.py", "--comments", str(saved), **env)
    return (protected.returncode, protected.stdout, release.returncode, release.stdout)


@pytest.mark.parametrize(
    ("change", "text", "expected"),
    [
        ("plain", NO_COVER, "ok protected-changes\n"),
        ("covered", COVER_0009, "Covered-by"),
        ("release", NO_COVER, "(a release pull request)"),
    ],
    ids=["a-nothing", "b-covered-by", "c-release"],
)
def test_req039_the_printed_comments_give_the_checks_the_same_result_as_all(
    repo, outside, change, text, expected
):
    """REQ-039: brief #1181 answer 4 (e): only the printed comments, the same verdicts."""
    records_world(repo, change)
    body = body_file(outside, text)
    ids = set(printed_ids(repo, "--body", body))
    full = results(repo, outside, body, all_comments())
    narrow = results(repo, outside, body, [c for c in all_comments() if c["id"] in ids])
    assert narrow == full
    assert full[0] == 0 and expected in full[1], full
    assert full[2:] == (0, "ok release\n"), full
