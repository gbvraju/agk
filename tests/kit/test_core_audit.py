"""core_audit.py: which checks and rules of the kit ever refused something (brief #328, REQ-011).

A read-only report, evidence for the smaller kit core of brief #278: per governance check the pull
requests whose governance run failed on it, per session rule and spec rule the verdicts that cite
it, what never fired, and the totals. Saved GitHub responses in a directory (`pulls.json`,
`commits-<n>.json`, `checks-<sha>.json`, `jobs-<id>.json`, `comments-<n>.json`), named as in
SPEC-0007 rule 20, and a small repository made here. No network, no model.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agk" / "core_audit.py"
AUTHORS = "boss"
OLD = "2026-01-05T10:00:00Z"
NEW = "2026-10-20T10:00:00Z"

WORKFLOW = """\
name: governance
on:
  pull_request:
jobs:
  governance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567   # v4
      - name: Install tooling
        run: python -m pip install pytest ruff
      - name: check_adrs
        run: python scripts/agk/check_adrs.py
      - name: check_specs
        if: ${{ !cancelled() }}
        run: python scripts/agk/check_specs.py --body "$RUNNER_TEMP/pr-body.md"
      - name: Lint
        run: make -f agk.mk agk-lint
      - name: Secret scan
        run: |
          echo "scanning"
          "$RUNNER_TEMP/gitleaks" git --no-banner --redact --exit-code 1 .
"""

SESSION_RULES = """\
# Session rules

Intro text.

1. A session acts only on a verdict.
2. A session never merges.
3. A session has one open pull request.
"""

SPEC = """\
# SPEC-0007: metrics

- Status: Approved

## Rules

### What is recorded

1. **One.** First rule.
2. **Two.** Second rule.
3. **Three.** Third rule.

## Tests

1. A test line that is not a rule.
"""


def sha_of(n: int, k: int) -> str:
    return f"{n:04d}{k:04d}".ljust(40, "a")


class Api:
    """Saved GitHub responses, one JSON file per request."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.mkdir()
        self.pulls: list[dict] = []

    def save(self, name: str, data) -> None:
        (self.path / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")

    def pull(
        self,
        n: int,
        failed: list[list[str]] | None = None,
        created: str = NEW,
        comments: list[dict] | None = None,
        commits: bool = True,
        checks: bool = True,
        jobs: bool = True,
        unsplit: bool = False,
    ) -> None:
        """Pull request N: one commit per entry of FAILED (the failed step names of its
        governance run; an empty entry is a green run), and its comments. A False flag leaves a
        page unsaved."""
        failed = [[]] if failed is None else failed
        self.pulls.append({"number": n, "created_at": created, "user": {"login": "builder"}})
        self.save("pulls", self.pulls)
        if commits:
            self.save(f"commits-{n}", [{"sha": sha_of(n, k)} for k in range(len(failed))])
        for k, steps in enumerate(failed):
            run_id = n * 100 + k
            conclusion = "failure" if steps or unsplit else "success"
            if checks:
                self.save(
                    f"checks-{sha_of(n, k)}",
                    {
                        "total_count": 2,
                        "check_runs": [
                            {"id": run_id, "name": "governance", "conclusion": conclusion},
                            {"id": run_id + 50, "name": "proof", "conclusion": "failure"},
                        ],
                    },
                )
            if jobs:
                names = ["Set up job", "Install tooling", "check_adrs", "check_specs", "Lint"]
                if unsplit:
                    shown = [{"name": "Governance checks", "conclusion": "failure"}]
                else:
                    shown = [
                        {"name": s, "conclusion": "failure" if s in steps else "success"}
                        for s in names + [s for s in steps if s not in names]
                    ]
                self.save(f"jobs-{run_id}", {"id": run_id, "steps": shown})
        if comments is not None:
            self.save(f"comments-{n}", comments)


def comment(cid: int, login: str, body: str) -> dict:
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": NEW}


def verdict(cid: int, text: str, who: str = "boss") -> dict:
    return comment(cid, who, f"Verdict: fix list {sha_of(1, 0)}\n\n1. {text}\n")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    files = {
        ".github/workflows/governance.yml": WORKFLOW,
        "config/session-rules.md": SESSION_RULES,
        "docs/specs/0007-metrics.md": SPEC,
        "docs/specs/TEMPLATE.md": "# SPEC-NNNN\n\n## Rules\n\n1. Placeholder.\n",
        "docs/adr/0001-first.md": "# ADR-0001\n",
        "docs/adr/0002-second.md": "# ADR-0002\n",
        "docs/adr/TEMPLATE.md": "# ADR-NNNN\n",
        "docs/requirements.md": "# Requirements\n\n### REQ-001 — One\n\n### REQ-002 — Two\n",
        "scripts/agk/one.py": "",
        "scripts/agk/two.py": "",
    }
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607 - fixed argument list, no shell
    return root


@pytest.fixture
def api(tmp_path: Path) -> Api:
    return Api(tmp_path / "api")


def run(repo: Path, api: Api, *extra: str, authors: str = AUTHORS):
    args = ["--api-dir", str(api.path), "--authors", authors, "--today", "2026-10-30"]
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args, *extra],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=60,
    )


def report(repo: Path, api: Api, *extra: str) -> dict:
    proc = run(repo, api, "--json", *extra)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def history(api: Api) -> None:
    """check_adrs failed on two pull requests (twice on the second), check_specs never failed,
    session rule 2 and SPEC-0007 rule 3 are cited in a verdict."""
    api.pull(1, failed=[["check_adrs"], []], comments=[verdict(11, "per session rule 2")])
    api.pull(
        2,
        failed=[["check_adrs"], ["check_adrs", "Lint"], []],
        comments=[verdict(21, "SPEC-0007 rule 3 asks for the field")],
    )
    api.pull(3, failed=[[]], comments=[])


# --- the checks -------------------------------------------------------------------------------


def test_a_check_that_failed_on_two_pull_requests_counts_two(repo, api):
    """Brief #328 answer 1: pull requests whose governance run failed on the check, each once."""
    history(api)
    data = report(repo, api)
    assert data["checks"]["check_adrs"] == 2
    assert data["checks"]["Lint"] == 1
    assert data["pull_requests"] == {
        "total": 3,
        "unread_checks": 0,
        "unread_verdicts": 0,
        "unread": [],
    }


def test_a_check_that_never_failed_is_zero_and_listed_as_never_fired(repo, api):
    """Brief #328 answer 1: zero refusals in the period, listed."""
    history(api)
    data = report(repo, api)
    assert data["checks"]["check_specs"] == 0
    assert data["checks"]["Secret scan"] == 0
    assert data["never_fired"]["checks"] == ["check_specs", "Secret scan"]


def test_the_checks_are_the_workflow_steps_that_run_a_kit_script_or_the_scanner(repo, api):
    """Brief #328 answer 1: a setup step is not a check; the secret scan is."""
    history(api)
    data = report(repo, api)
    assert list(data["checks"]) == ["check_adrs", "check_specs", "Lint", "Secret scan"]


def test_a_failed_step_that_is_not_a_check_of_the_workflow_is_listed_apart(repo, api):
    """A renamed or removed step is still counted, under the steps outside the workflow."""
    api.pull(1, failed=[["check_old_name"]], comments=[])
    data = report(repo, api)
    assert data["other_steps"] == {"check_old_name": 1}
    assert "check_old_name" not in data["checks"]


def test_a_failed_proof_run_is_not_a_governance_failure(repo, api):
    """Only the check run named governance is read (every saved commit has a failed proof run)."""
    api.pull(1, failed=[[]], comments=[])
    data = report(repo, api)
    assert set(data["checks"].values()) == {0}
    assert data["other_steps"] == {}


# --- the rules --------------------------------------------------------------------------------


def test_a_rule_cited_in_a_verdict_is_counted(repo, api):
    """Brief #328 answer 1: session and spec rules cited in a Verdict: comment, with counts."""
    history(api)
    data = report(repo, api)
    assert data["session_rules"] == {"1": 0, "2": 1, "3": 0}
    assert data["spec_rules"] == {"SPEC-0007": {"1": 0, "2": 0, "3": 1}}
    assert data["never_fired"]["session_rules"] == ["1", "3"]
    assert data["never_fired"]["spec_rules"] == {"SPEC-0007": ["1", "2"]}


def test_only_a_verdict_of_a_listed_author_counts(repo, api):
    """A comment that is not a verdict, or a verdict by another account, cites nothing."""
    api.pull(
        1,
        comments=[
            verdict(11, "session rule 1", who="someone"),
            comment(12, "boss", "Report: abc session rule 1 and SPEC-0007 rule 1"),
        ],
    )
    data = report(repo, api)
    assert data["session_rules"]["1"] == 0
    assert data["spec_rules"]["SPEC-0007"]["1"] == 0


def test_lists_of_rules_and_the_long_form_are_read_and_a_verdict_counts_once(repo, api):
    """`rules 1 and 3`, `rules 1, 2 and 3`, `rule 3 of the session rules`; a verdict counts once."""
    body = (
        "session rules 1 and 3 hold; SPEC-0007 rules 1, 2 and 3 apply; "
        "again session rule 1, and rule 3 of the session rules"
    )
    api.pull(1, comments=[verdict(11, body)])
    data = report(repo, api)
    assert data["session_rules"] == {"1": 1, "2": 0, "3": 1}
    assert data["spec_rules"]["SPEC-0007"] == {"1": 1, "2": 1, "3": 1}


def test_a_numbered_line_outside_the_rules_section_is_not_a_spec_rule(repo, api):
    """The `## Tests` list of a spec and the template are not rules."""
    api.pull(1, comments=[])
    data = report(repo, api)
    assert data["spec_rules"] == {"SPEC-0007": {"1": 0, "2": 0, "3": 0}}


# --- what cannot be read ----------------------------------------------------------------------


def test_an_unreadable_page_gives_cannot_check_never_zero(repo, api):
    """Brief #328 answer 3: a missing page makes a zero `cannot-check` and keeps it off the list."""
    history(api)
    api.pull(4, failed=[["check_specs"]], commits=False)
    data = report(repo, api)
    assert data["pull_requests"]["unread_checks"] == 1
    assert data["checks"]["check_specs"] == "cannot-check"
    assert data["checks"]["check_adrs"] == "at least 2"
    assert "check_specs" not in data["never_fired"]["checks"]


def test_an_unreadable_comment_page_gives_cannot_check_for_the_rules(repo, api):
    """Brief #328 answer 3: the verdicts of a pull request that cannot be read."""
    history(api)
    api.pull(4)  # no comments page saved
    data = report(repo, api)
    assert data["pull_requests"]["unread_verdicts"] == 1
    assert data["session_rules"] == {"1": "cannot-check", "2": "at least 1", "3": "cannot-check"}
    assert data["never_fired"]["session_rules"] == []
    assert data["never_fired"]["spec_rules"] == {}


@pytest.mark.parametrize("missing", ["checks", "jobs", "unsplit"])
def test_a_missing_check_run_or_job_or_an_unsplit_job_cannot_be_checked(repo, api, missing):
    """No check runs saved, no job saved, or one combined step: the failure cannot be attributed."""
    flags = {"checks": {"checks": False}, "jobs": {"jobs": False}, "unsplit": {"unsplit": True}}
    api.pull(1, failed=[["check_adrs"]], comments=[], **flags[missing])
    data = report(repo, api)
    assert data["pull_requests"]["unread_checks"] == 1
    assert data["checks"]["check_adrs"] == "cannot-check"


def test_an_unreadable_list_of_pull_requests_makes_every_count_cannot_check(repo, api):
    """Without `pulls.json` nothing is zero."""
    proc = run(repo, api, "--json")
    assert proc.returncode == 0, proc.stdout
    data = json.loads(proc.stdout)
    assert data["pull_requests"]["total"] == "cannot-check"
    assert set(data["checks"].values()) == {"cannot-check"}
    assert set(data["session_rules"].values()) == {"cannot-check"}
    assert data["never_fired"] == {"checks": [], "session_rules": [], "spec_rules": {}}


def test_the_text_report_says_cannot_check(repo, api):
    history(api)
    api.pull(4, commits=False, comments=[])
    proc = run(repo, api)
    assert proc.returncode == 0, proc.stdout
    assert "check_specs: cannot-check" in proc.stdout
    assert "check_adrs: at least 2" in proc.stdout


# --- the period, the totals and the page ------------------------------------------------------


def test_since_leaves_out_older_pull_requests(repo, api):
    """`--since DATE`: only pull requests opened on or after it."""
    api.pull(1, failed=[["check_specs"]], created=OLD, comments=[verdict(11, "session rule 3")])
    api.pull(2, comments=[])
    data = report(repo, api, "--since", "2026-06-01")
    assert data["since"] == "2026-06-01"
    assert data["pull_requests"]["total"] == 1
    assert data["checks"]["check_specs"] == 0
    assert data["session_rules"]["3"] == 0
    assert report(repo, api)["checks"]["check_specs"] == 1


def test_the_totals_count_adrs_specs_requirements_and_scripts(repo, api):
    """Brief #328 answer 1: totals, templates aside."""
    api.pull(1, comments=[])
    data = report(repo, api)
    assert data["totals"] == {"adrs": 2, "specs": 1, "requirements": 2, "scripts": 2}


def test_the_text_report_has_every_part(repo, api):
    history(api)
    proc = run(repo, api)
    assert proc.returncode == 0, proc.stdout
    out = proc.stdout
    for part in (
        "Governance checks",
        "check_adrs: 2",
        "session rule 2: 1",
        "SPEC-0007 rule 3: 1",
        "Never fired",
        "check_specs, Secret scan",
        "Totals: ADRs 2, specs 1, requirements 2, scripts 2",
    ):
        assert part in out, part


def test_it_writes_nothing_without_write(repo, api):
    """REQ-011 AC3: read-only; brief #328 answer 2 (the page only with --write)."""
    history(api)
    assert run(repo, api).returncode == 0
    assert not (repo / "docs" / "runs").exists()


def test_write_puts_the_page_with_its_evidence_line_at_the_top(repo, api):
    """Brief #328 answer 2: `docs/runs/core-audit-<date>.md`, evidence for #278, not a decision."""
    history(api)
    proc = run(repo, api, "--write")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    page = repo / "docs" / "runs" / "core-audit-2026-10-30.md"
    lines = page.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# Core audit 2026-10-30"
    assert "evidence for #278, not a decision" in lines[2]
    assert "check_adrs: 2" in page.read_text(encoding="utf-8")


def test_write_refuses_to_overwrite_the_page_of_the_day(repo, api):
    history(api)
    assert run(repo, api, "--write").returncode == 0
    proc = run(repo, api, "--write")
    assert proc.returncode == 1
    assert "path class docs/runs" in proc.stdout


@pytest.mark.parametrize(
    "args",
    [["--since"], ["--since", "yesterday"], ["--today", "2026-13-01"], ["--bogus"]],
)
def test_a_bad_call_prints_the_usage(repo, api, args):
    proc = run(repo, api, *args)
    assert proc.returncode == 2
    assert proc.stdout.startswith("usage: core_audit.py")


def test_it_reads_with_get_only_and_holds_no_credential():
    """REQ-011 AC3: GET only and git; no write method, no token."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert not re.search(r"\b(POST|PATCH|PUT|DELETE)\b", text)
    assert "GH_TOKEN" not in text and "GITHUB_TOKEN" not in text


def test_one_unreadable_check_run_page_among_readable_ones_cannot_be_checked(repo, api):
    """A failure on the commit whose page is missing could hide behind a green later commit."""
    api.pull(1, failed=[["check_specs"], []], comments=[])
    (api.path / f"checks-{sha_of(1, 0)}.json").unlink()
    data = report(repo, api)
    assert data["checks"]["check_specs"] == "cannot-check"


def test_a_short_read_of_check_runs_counts_what_was_read_as_at_least(repo, api):
    """Verdict on 9ec1d99 item 1: `total_count` above the runs received is a short read."""
    api.pull(1, failed=[["check_adrs"]], comments=[])
    name = f"checks-{sha_of(1, 0)}"
    page = json.loads((api.path / f"{name}.json").read_text(encoding="utf-8"))
    page["total_count"] = 101
    api.save(name, page)
    data = report(repo, api)
    assert data["pull_requests"]["unread_checks"] == 1
    assert data["checks"]["check_adrs"] == "at least 1"
    assert data["checks"]["check_specs"] == "cannot-check"


def test_a_short_read_of_the_commits_of_a_pull_request_is_unread(repo, api):
    """Verdict on 9ec1d99 item 1: fewer commits than the pull request's `commits` count."""
    api.pull(1, failed=[["check_adrs"], []], comments=[])
    api.pulls[-1]["commits"] = 3
    api.save("pulls", api.pulls)
    data = report(repo, api)
    assert data["pull_requests"]["unread_checks"] == 1
    assert data["checks"]["check_adrs"] == "at least 1"


def test_two_hundred_and_fifty_commits_without_a_count_are_a_short_read(repo, api):
    """GitHub lists at most 250 commits of a pull request; with no count, 250 is a short read."""
    api.pull(1, failed=[["check_adrs"]] + [[] for _ in range(249)], comments=[])
    data = report(repo, api)
    assert data["pull_requests"]["unread_checks"] == 1
    assert data["checks"]["check_adrs"] == "at least 1"


# --- the unread pages (brief #381) ------------------------------------------------------------


def unread_lines(out: str) -> list[str]:
    """The lines of the `Unread pages:` section of the text report."""
    lines = out.splitlines()
    at = lines.index("Unread pages:")
    found = []
    for line in lines[at + 1 :]:
        if not line.startswith("  "):
            break
        found.append(line.strip())
    return found


@pytest.mark.parametrize(
    ("flags", "page"),
    [
        ({"commits": False}, "commits"),
        ({"checks": False}, "check runs"),
        ({"jobs": False}, "job"),
        ({"unsplit": True}, "combined step"),
    ],
)
def test_a_pull_request_whose_check_pages_cannot_be_read_is_named_with_the_page(
    repo, api, flags, page
):
    """Brief #381 answer 1: one entry per pull request and page, in the text and in the JSON."""
    history(api)
    api.pull(4, failed=[["check_adrs"]], comments=[], **flags)
    data = report(repo, api)
    assert data["pull_requests"]["unread"] == [{"number": 4, "page": page}]
    proc = run(repo, api)
    assert proc.returncode == 0, proc.stdout
    assert unread_lines(proc.stdout) == [f"#4 {page}"]


def test_a_pull_request_whose_comments_cannot_be_read_is_named_with_comments(repo, api):
    """Brief #381 answer 1: the comments page."""
    history(api)
    api.pull(4)  # no comments page saved
    data = report(repo, api)
    assert data["pull_requests"]["unread"] == [{"number": 4, "page": "comments"}]
    assert unread_lines(run(repo, api).stdout) == ["#4 comments"]


def test_a_short_read_of_check_runs_is_named_check_runs(repo, api):
    """A `total_count` above the runs received is an unread check-runs page."""
    api.pull(1, failed=[["check_adrs"]], comments=[])
    name = f"checks-{sha_of(1, 0)}"
    page = json.loads((api.path / f"{name}.json").read_text(encoding="utf-8"))
    page["total_count"] = 101
    api.save(name, page)
    assert report(repo, api)["pull_requests"]["unread"] == [{"number": 1, "page": "check runs"}]


def test_a_short_read_of_commits_is_named_commits(repo, api):
    """Fewer commits than the pull request's `commits` count is an unread commits page."""
    api.pull(1, failed=[["check_adrs"], []], comments=[])
    api.pulls[-1]["commits"] = 3
    api.save("pulls", api.pulls)
    assert report(repo, api)["pull_requests"]["unread"] == [{"number": 1, "page": "commits"}]


def test_the_unread_list_is_in_number_order_and_matches_the_text(repo, api):
    """Brief #381 answers 1 and 4: number order; a pull request with two unread pages has two."""
    api.pull(9, failed=[["check_adrs"]], comments=[], checks=False)
    api.pull(3)  # no comments page
    api.pull(5, failed=[["check_adrs"]], unsplit=True)  # and no comments page
    api.pull(7, comments=[])
    data = report(repo, api)
    expected = [
        {"number": 3, "page": "comments"},
        {"number": 5, "page": "combined step"},
        {"number": 5, "page": "comments"},
        {"number": 9, "page": "check runs"},
    ]
    assert data["pull_requests"]["unread"] == expected
    assert data["pull_requests"]["unread_checks"] == 2
    assert data["pull_requests"]["unread_verdicts"] == 2
    text = unread_lines(run(repo, api).stdout)
    assert text == [f"#{u['number']} {u['page']}" for u in expected]


def test_with_every_page_read_the_unread_list_is_empty(repo, api):
    """Brief #381 answer 3: the counts stay as they were; the section says none."""
    history(api)
    data = report(repo, api)
    assert data["pull_requests"]["unread"] == []
    assert data["checks"]["check_adrs"] == 2
    assert unread_lines(run(repo, api).stdout) == ["none"]


def test_an_unreadable_list_of_pull_requests_has_no_unread_list(repo, api):
    """Without `pulls.json` no pull request can be named: the list is cannot-check, never empty."""
    data = report(repo, api)
    assert data["pull_requests"]["unread"] == "cannot-check"
    assert unread_lines(run(repo, api).stdout) == ["cannot-check"]


# --- --only (brief #381 answer 2) -------------------------------------------------------------


def test_only_reads_just_the_named_pull_requests(repo, api):
    """Brief #381 answers 2 and 4: the others are not read (their pages are missing here)."""
    history(api)
    api.pull(4, failed=[["check_specs"]], commits=False)  # unread, and not named
    data = report(repo, api, "--only", "2,3")
    assert data["pull_requests"]["total"] == 2
    assert data["pull_requests"]["unread"] == []
    assert data["checks"]["check_adrs"] == 1
    assert data["checks"]["Lint"] == 1
    assert data["spec_rules"]["SPEC-0007"]["3"] == 1
    assert data["session_rules"]["2"] == 0


def test_only_names_the_pages_it_still_cannot_read(repo, api):
    """A re-read that fails again names the pull request again."""
    history(api)
    api.pull(4, failed=[["check_specs"]], commits=False, comments=[])
    data = report(repo, api, "--only", "4")
    assert data["pull_requests"]["unread"] == [{"number": 4, "page": "commits"}]
    assert data["checks"]["check_specs"] == "cannot-check"


def test_only_keeps_the_period(repo, api):
    """Every other rule unchanged: a named pull request older than --since is left out."""
    api.pull(1, failed=[["check_specs"]], created=OLD, comments=[])
    api.pull(2, comments=[])
    data = report(repo, api, "--only", "1,2", "--since", "2026-06-01")
    assert data["pull_requests"]["total"] == 1
    assert data["checks"]["check_specs"] == 0


def test_only_refuses_a_number_that_is_no_pull_request(repo, api):
    """A named number missing from the list of pull requests is a bad call, never a quiet zero."""
    history(api)
    proc = run(repo, api, "--only", "2,8")
    assert proc.returncode == 2
    assert "--only" in proc.stdout


def test_only_writes_nothing(repo, api):
    history(api)
    assert run(repo, api, "--only", "1").returncode == 0
    assert not (repo / "docs" / "runs").exists()


@pytest.mark.parametrize("value", ["", "x", "1,,2", "1;2", "-3", "0"])
def test_a_bad_only_prints_the_usage(repo, api, value):
    proc = run(repo, api, "--only", value)
    assert proc.returncode == 2
    assert proc.stdout.startswith("usage: core_audit.py")


def test_only_says_so_in_the_header(repo, api):
    """Verdict on a29c44d item 1: a report from `--only` names the pull requests it read."""
    history(api)
    data = report(repo, api, "--only", "3,1")
    assert data["only"] == [1, 3]
    assert report(repo, api)["only"] is None
    proc = run(repo, api, "--only", "3,1")
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.splitlines()[0] == "agk core audit, only #1, #3, read on 2026-10-30"
    since = run(repo, api, "--only", "1", "--since", "2026-01-01").stdout.splitlines()[0]
    assert since == "agk core audit, since 2026-01-01, only #1, read on 2026-10-30"


def test_only_judges_nothing_as_never_fired(repo, api):
    """Verdict on a29c44d item 1: a subset is no evidence that a check or rule never fired."""
    history(api)
    data = report(repo, api, "--only", "3")
    assert data["never_fired"] == "not judged (--only)"
    out = run(repo, api, "--only", "3").stdout
    assert "Never fired in the period: not judged (--only)" in out
    assert "  checks: " not in out


def test_only_with_write_is_refused(repo, api):
    """Verdict on a29c44d item 1: no evidence page is ever written from a subset."""
    history(api)
    proc = run(repo, api, "--only", "1", "--write")
    assert proc.returncode == 2
    assert "--only" in proc.stdout and "--write" in proc.stdout
    assert not (repo / "docs" / "runs").exists()
