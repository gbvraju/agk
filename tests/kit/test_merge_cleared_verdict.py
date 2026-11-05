"""merge_cleared.py build (a): the auto-merge setting and the verdict reader (SPEC-0039 rules 1, 3).

Brief #528, ADR-0263, REQ-046. `merge_cleared.py --pr N --sha SHA` reads `[flow] auto_merge` and
`auto_merge_method` from agk.toml as committed on the default branch of the remote, as last fetched,
judges the latest `Verdict:` comment of the pull request and prints one line. Since build (b) (brief
#531, ADR-0265) a cleared pull request whose other re-checks pass is merged by the one pinned call,
so the saved world here is one the command may merge. Every test runs on a git repository in
`tmp_path` and a fake `gh` that answers from saved responses and records its argument lists. No
network; invented logins, addresses at example.com.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from test_doctor import doctor, prepare, stub_gh

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
SCRIPT = SCRIPTS / "merge_cleared.py"
sys.path.insert(0, str(SCRIPTS))

import doctor as doctor_module  # noqa: E402
import merge_cleared  # noqa: E402
import reviewers  # noqa: E402
from common import CheckError  # noqa: E402

HEAD = "a1b2c3d4e5" * 4
OLD = "0f9e8d7c6b" * 4
SHA12 = HEAD[:12]
REPO = "example-owner/example-repo"
ON = 'auto_merge = true\nauto_merge_method = "squash"\n'
HIDDEN = "not-for-output"  # a value no output line may ever show
CONDUCTOR = "conductor-two"
BUILDER = "builder-one"
OWNER = "owner-three"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "Example",
    "GIT_AUTHOR_EMAIL": "example@example.com",
    "GIT_COMMITTER_NAME": "Example",
    "GIT_COMMITTER_EMAIL": "example@example.com",
}


# --- fixtures -----------------------------------------------------------------------------------


def git(root: Path, *args: str) -> str:
    env = {**os.environ, **GIT_ENV}
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True, env=env
    ).stdout


def toml(flow: str, mode: str = "strict", local: bool = False) -> str:
    top = f'default_branch = "main"\npr_mode = "{mode}"\n'
    if local:
        top += 'execution = "local"\n'
    return top + ("[flow]\n" + flow if flow else "")


def repo(
    tmp_path: Path,
    main: str,
    head: str | None = None,
    reviewers_yaml: str | None = None,
    origin: str = f"https://github.com/{REPO}.git",
) -> Path:
    """A checkout whose `origin/main` holds MAIN; with HEAD, the checkout is a pull request's head
    branch whose agk.toml (committed and in the work tree) says HEAD instead."""
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    git(root, "init", "-q", "-b", "main")
    (root / "agk.toml").write_text(main, encoding="utf-8")
    if reviewers_yaml is not None:
        (root / "config").mkdir()
        (root / "config" / "reviewers.yaml").write_text(reviewers_yaml, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "main")
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    if origin:
        git(root, "remote", "add", "origin", origin)
    if head is not None:
        git(root, "checkout", "-q", "-b", "feature")
        (root / "agk.toml").write_text(head, encoding="utf-8")
        git(root, "commit", "-q", "-am", "head")
    return root


def comment(body: str, login: str = OWNER, at: int = 0, cid: int | None = None) -> dict:
    return {
        "id": cid if cid is not None else 1000 + at,
        "body": body,
        "created_at": f"2026-11-04T10:{at:02d}:00Z",
        "user": {"login": login},
    }


def evidence(sha: str = HEAD, check: str = "agrees") -> str:
    """The evidence lines of a verdict in local mode (docs/guides/local-mode.md)."""
    return (
        f"Local evidence: {sha} Evidence check: {check}, head {sha[:12]}, record {sha[:12]}, "
        "governance ok, sample 3 of 3 same exit (conductor's run); proof ok, tests 9 passed\n"
    )


def cleared(sha: str = HEAD, login: str = OWNER, at: int = 5, extra: str | None = None) -> dict:
    body = f"Verdict: cleared {sha}\n\nReviewed against the brief.\n"
    return comment(body + (evidence(sha) if extra is None else extra), login, at)


MERGE = "c0ffee5eed" * 4  # the merge commit GitHub answers with
MERGE12 = MERGE[:12]
GREEN_RUNS = [
    {"id": 11, "name": "proof", "status": "completed", "conclusion": "success"},
    {"id": 12, "name": "governance", "status": "completed", "conclusion": "success"},
]


def world(**saved: object) -> dict:
    """The saved GitHub answers of a pull request that the command may merge; SAVED replaces any
    of them: `pull`, `comments`, `issues` (the open ones), `runs` (the check runs of the head),
    `files`, `items` (issue or pull number -> its JSON, for `Depends-on`) and `merge` (the answer
    of the merge call: a JSON object, or {"http": <code>} for a failure)."""
    base = {
        "pull": {
            "number": 7,
            "head": {"sha": HEAD},
            "state": "open",
            "draft": False,
            "labels": [],
            "mergeable_state": "clean",
            "body": "Brief: #500\nAdvances: REQ-046\n",
        },
        "comments": [],
        "issues": [],
        "runs": GREEN_RUNS,
        "files": [{"filename": "scripts/agk/example.py", "status": "modified", "patch": "+x"}],
        "items": {},
        "commits": [{"sha": HEAD, "commit": {"message": "Example change\n\nA body.\n"}}],
        "merge": {"sha": MERGE, "merged": True, "message": "Pull Request successfully merged"},
    }
    base.update({k: v for k, v in saved.items() if v is not None})
    return base


FAKE_GH = """
import json, sys
args = sys.argv[1:]
with open(LOG, 'a', encoding='utf-8') as fh:
    fh.write(json.dumps(args) + '\\n')
if FAIL:
    sys.stderr.write('HTTP 502: Bad Gateway\\n'); sys.exit(1)
data = json.load(open(SAVED, encoding='utf-8'))
method = args[args.index('--method') + 1] if '--method' in args else 'GET'
path = next(a for a in args if a.startswith('repos/'))
route, _, query = path.partition('?')
page = int(query.split('page=')[-1]) if 'page=' in query else 1
parts = route.split('/')[3:]

def paged(items):
    return items[(page - 1) * 100 : page * 100]

def fail(code):
    sys.stderr.write('gh: Example failure (HTTP %d)\\n' % code); sys.exit(1)

if method == 'PUT' and parts[0] == 'pulls' and parts[2:] == ['merge']:
    answer = data['merge']
    if 'http' in answer:
        fail(answer['http'])
    out = answer
elif method != 'GET':
    fail(405)
elif parts[0] == 'pulls' and len(parts) == 2 and parts[1] == '7':
    out = data['pull']
elif parts[0] == 'pulls' and parts[2:] == ['files']:
    out = paged(data['files'][:3000])  # GitHub lists at most 3,000 files
elif parts[0] == 'pulls' and parts[2:] == ['commits']:
    out = paged(data['commits'][:250])  # GitHub lists at most 250 commits
elif parts[0] == 'issues' and parts[2:] == ['comments']:
    out = paged(data['comments'])
elif parts == ['issues']:
    out = paged(data['issues'])
elif parts[0] == 'commits' and parts[2:] == ['check-runs']:
    runs = paged(data['runs'])
    out = {'total_count': len(data['runs']), 'check_runs': runs}
elif parts[0] in ('issues', 'pulls') and len(parts) == 2 and parts[1] in data['items']:
    item = data['items'][parts[1]]
    if parts[0] == 'pulls' and 'pull' in item:
        out = item['pull']
    else:
        out = {k: v for k, v in item.items() if k != 'pull'}
elif parts[0] == 'contents' and '/'.join(parts[1:]) in data.get('contents', {}):
    out = data['contents']['/'.join(parts[1:])]
else:
    fail(404)
print(json.dumps(out))
"""


def fake_gh(
    tmp_path: Path,
    pull: object = None,
    comments: object = None,
    fail: bool = False,
    changed: bool = True,
    **saved: object,
):
    """A `gh` on PATH that answers from saved JSON (`world`) and logs each argument list; with
    CHANGED, a pull request without `changed_files` is given the number of its saved files."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    path = tmp_path / "saved.json"
    log = tmp_path / "gh-calls.jsonl"
    if pull is None:
        pull = world()["pull"]
    data = world(pull=pull, comments=comments, **saved)
    if changed and isinstance(data["pull"], dict) and "changed_files" not in data["pull"]:
        data["pull"] = {**data["pull"], "changed_files": len(data["files"])}
    if changed and isinstance(data["pull"], dict) and "commits" not in data["pull"]:
        data["pull"] = {**data["pull"], "commits": len(data["commits"])}
    path.write_text(json.dumps(data), encoding="utf-8")
    script = bin_dir / "gh"
    script.write_text(
        f"#!{sys.executable}\nLOG, SAVED, FAIL = {str(log)!r}, {str(path)!r}, {fail!r}\n" + FAKE_GH,
        encoding="utf-8",
    )
    script.chmod(0o755)
    return bin_dir, log


def merge_call(
    number: int = 7, sha: str = HEAD, message: str = "Merged-by: merge_cleared.py"
) -> list[str]:
    """The one merge call of SPEC-0039 rule 6, pinned to the head, with merge_cleared.py's own
    squash message (brief #557: never GitHub's default, which copies the commit bodies)."""
    return [
        "api",
        "--method",
        "PUT",
        f"repos/{REPO}/pulls/{number}/merge",
        "-f",
        f"sha={sha}",
        "-f",
        "merge_method=squash",
        "-f",
        f"commit_message={message}",
    ]


def calls(log: Path) -> list[list[str]]:
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]


def run(root: Path, bin_dir: Path, *args: str):
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    temp = bin_dir.parent / "temp"  # the merge-cleared lock of this test alone
    temp.mkdir(exist_ok=True)
    env["TMPDIR"] = env["TEMP"] = env["TMP"] = str(temp)
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args], cwd=root, capture_output=True, text=True, env=env
    )


def merge_cleared_run(
    tmp_path,
    main,
    comments=None,
    head_toml=None,
    pull=None,
    reviewers_yaml=None,
    origin=f"https://github.com/{REPO}.git",
    **saved,
):
    root = repo(tmp_path, main, head_toml, reviewers_yaml, origin)
    bin_dir, log = fake_gh(tmp_path, pull, comments, **saved)
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    return proc, calls(log)


def one_line(proc) -> str:
    lines = proc.stdout.splitlines()
    assert len(lines) == 1, proc.stdout + proc.stderr
    return lines[0]


# --- rule 1: the setting ------------------------------------------------------------------------

MODES = [("strict", False), ("flow", False), ("strict", True), ("flow", True)]
OFF_CASES = [
    ("", "auto_merge"),  # no [flow] table
    ('assign = "next"\n', "auto_merge"),  # the table without the key
    ('auto_merge = false\nauto_merge_method = "squash"\n', "auto_merge"),
    ("auto_merge = false\n", "auto_merge"),
    (f'auto_merge = "{HIDDEN}"\nauto_merge_method = "squash"\n', "auto_merge"),
    ('auto_merge = 1\nauto_merge_method = "squash"\n', "auto_merge"),
    ('auto_merge = "true"\nauto_merge_method = "squash"\n', "auto_merge"),
    ('auto_merge = true\nauto_merge_method = "merge"\n', "auto_merge_method"),
    (f'auto_merge = true\nauto_merge_method = "{HIDDEN}"\n', "auto_merge_method"),
    ('auto_merge = true\nauto_merge_method = "Squash"\n', "auto_merge_method"),
    ("auto_merge = true\nauto_merge_method = 1\n", "auto_merge_method"),
    ("auto_merge = true\n", "auto_merge_method"),
]


@pytest.mark.parametrize(("mode", "local"), MODES)
@pytest.mark.parametrize(("flow", "setting"), OFF_CASES)
def test_every_setting_but_true_with_squash_merges_nothing_and_names_the_setting(
    tmp_path, mode, local, flow, setting
):
    """REQ-046 AC1: SPEC-0039 rule 1, in strict and flow and with execution local."""
    proc, made = merge_cleared_run(tmp_path, toml(flow, mode, local), [cleared()])
    line = one_line(proc)
    assert line.startswith(f"merge-cleared #7 {SHA12}: refused: "), line
    assert setting in line
    assert HIDDEN not in line and "Squash" not in line
    assert proc.returncode == 1
    assert made == [], "with the setting off nothing reads GitHub"


@pytest.mark.parametrize(("mode", "local"), MODES)
def test_a_well_formed_true_with_squash_lets_a_cleared_verdict_through(tmp_path, mode, local):
    """REQ-046 AC1: SPEC-0039 rule 1 (the one case that may merge)."""
    proc, made = merge_cleared_run(tmp_path, toml(ON, mode, local), [cleared()])
    assert one_line(proc) == f"merge-cleared #7 {SHA12}: merged {MERGE12}"
    assert proc.returncode == 0
    assert [c for c in made if "PUT" in c] == [merge_call()]


def test_a_head_that_turns_the_setting_on_while_the_default_branch_does_not_merges_nothing(
    tmp_path,
):
    """REQ-046 AC1: SPEC-0039 rule 1 (read from the default branch, never a pull request's head)."""
    proc, made = merge_cleared_run(
        tmp_path, toml("auto_merge = false\n", "flow"), [cleared()], head_toml=toml(ON, "flow")
    )
    line = one_line(proc)
    assert line.startswith(f"merge-cleared #7 {SHA12}: refused: ") and "auto_merge" in line
    assert proc.returncode == 1 and made == []


def test_the_work_tree_is_never_read(tmp_path):
    """REQ-046 AC1: brief #528 answer 1 (an uncommitted change turns nothing on)."""
    root = repo(tmp_path, toml("auto_merge = false\n"))
    (root / "agk.toml").write_text(toml(ON), encoding="utf-8")
    bin_dir, log = fake_gh(tmp_path, comments=[cleared()])
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    assert "refused" in one_line(proc) and proc.returncode == 1 and calls(log) == []


def test_the_default_branch_turning_it_on_counts_whatever_the_checkout_says(tmp_path):
    """REQ-046 AC1: SPEC-0039 rule 1 (only the default branch decides)."""
    proc, _ = merge_cleared_run(
        tmp_path, toml(ON), [cleared()], head_toml=toml("auto_merge = false\n")
    )
    assert f"merged {MERGE12}" in one_line(proc) and proc.returncode == 0


def test_a_default_branch_not_fetched_or_without_agk_toml_is_refused(tmp_path):
    """REQ-046 AC1: brief #528 answer 1 (a failed read is never a pass)."""
    root = repo(tmp_path, toml(ON))
    git(root, "update-ref", "-d", "refs/remotes/origin/main")
    bin_dir, log = fake_gh(tmp_path, comments=[cleared()])
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    assert "refused" in one_line(proc) and proc.returncode == 1 and calls(log) == []


def test_unreadable_toml_on_the_default_branch_names_the_path_class(tmp_path):
    """REQ-046 AC1: SPEC-0039 rule 1 (malformed)."""
    proc, made = merge_cleared_run(tmp_path, f'[flow\nauto_merge = "{HIDDEN}"\n', [cleared()])
    line = one_line(proc)
    assert "refused" in line and "agk.toml" in line and HIDDEN not in line
    assert proc.returncode == 1 and made == []


def test_a_flow_key_that_is_not_a_table_is_refused(tmp_path):
    """REQ-046 AC1: SPEC-0039 rule 1 (malformed)."""
    proc, _ = merge_cleared_run(tmp_path, f'flow = "{HIDDEN}"\n', [cleared()])
    line = one_line(proc)
    assert "refused" in line and "flow" in line and HIDDEN not in line and proc.returncode == 1


def test_the_setting_reader_returns_off_or_on_and_refuses_naming_the_setting():
    """REQ-046 AC1: SPEC-0039 rule 1 (the one reading, shared with doctor.py)."""
    assert merge_cleared.auto_merge_setting({}) == "off"
    assert merge_cleared.auto_merge_setting({"flow": {"assign": "next"}}) == "off"
    assert merge_cleared.auto_merge_setting({"flow": {"auto_merge": False}}) == "off"
    on = {"flow": {"auto_merge": True, "auto_merge_method": "squash"}}
    assert merge_cleared.auto_merge_setting(on) == "on"
    for flow, name in (
        ({"auto_merge": HIDDEN}, "auto_merge"),
        ({"auto_merge": False, "auto_merge_method": "rebase"}, "auto_merge_method"),
        ({"auto_merge": True}, "auto_merge_method"),
    ):
        with pytest.raises(CheckError) as err:
            merge_cleared.auto_merge_setting({"flow": flow})
        assert name in str(err.value) and HIDDEN not in str(err.value)


# --- rule 1: the doctor line --------------------------------------------------------------------


def test_doctor_prints_auto_merge_off_or_on_with_the_method():
    """REQ-046 AC1: SPEC-0039 rule 1 and brief #528 answer 3 (the doctor line)."""
    off = doctor_module.auto_merge_result({"flow": {"auto_merge": False}})
    assert off.status == "ok" and off.message == "off"
    on = doctor_module.auto_merge_result(
        {"flow": {"auto_merge": True, "auto_merge_method": "squash"}}
    )
    assert on.status == "ok" and on.message == "on, method squash"
    assert doctor_module.auto_merge_result({}).message == "off"
    bad = doctor_module.auto_merge_result({"flow": {"auto_merge": HIDDEN}})
    assert bad.status == "fail" and "auto_merge" in bad.message and HIDDEN not in bad.message
    severity, ok_text, fail_text, _fix = doctor_module.CHECKS["auto-merge-setting"]
    assert severity == "error" and ok_text == "auto-merge: "


@pytest.mark.parametrize(
    ("flow", "expected", "code"),
    [
        ("", "ok auto-merge-setting error auto-merge: off", 0),
        (ON, "ok auto-merge-setting error auto-merge: on, method squash", 0),
        (f'auto_merge = "{HIDDEN}"\n', "FAIL auto-merge-setting error", 1),
    ],
)
def test_doctor_reports_the_line_in_a_full_run(tmp_path, flow, expected, code):
    """REQ-046 AC1: brief #528 answer 3 (a malformed value fails, naming the setting)."""
    dirs = prepare("ok", tmp_path)
    toml_path = dirs["root"] / "agk.toml"
    text = toml_path.read_text(encoding="utf-8")
    toml_path.write_text(text + ("\n[flow]\n" + flow if flow else ""), encoding="utf-8")
    stub = tmp_path / "bin"
    stub_gh(stub)
    proc = doctor(
        "--api-dir",
        str(dirs["api"]),
        "--repo",
        REPO,
        "--kit-root",
        str(dirs["kit"]),
        str(dirs["root"]),
        path=f"{stub}{os.pathsep}{os.environ['PATH']}",
    )
    line = next(x for x in proc.stdout.splitlines() if "auto-merge-setting" in x)
    assert line.startswith(expected), proc.stdout
    assert HIDDEN not in proc.stdout
    if code:
        assert proc.returncode == 1


# --- rule 3: the verdict ------------------------------------------------------------------------

FIX_LIST = comment(f"Verdict: fix list {HEAD}\n\n1. Fix the test.\nVerdict: cleared {HEAD}\n", at=6)
REJECTED = comment(f"Verdict: rejected {HEAD}", at=6)
VERDICT_CASES = [
    ("the previous head", [cleared(OLD)], "held"),
    ("a 12-character sha", [comment(f"Verdict: cleared {SHA12}", at=5)], "held"),
    ("text after the sha", [comment(f"Verdict: cleared {HEAD}, after the fix", at=5)], "held"),
    ("a space after the sha", [comment(f"Verdict: cleared {HEAD} ", at=5)], "held"),
    ("text before the verdict", [comment(f"Note. Verdict: cleared {HEAD}", at=5)], "held"),
    ("upper case", [comment(f"Verdict: cleared {HEAD.upper()}", at=5)], "held"),
    ("a multi-line fix list", [FIX_LIST], "held"),
    ("hidden by a newer verdict", [cleared(at=5), REJECTED], "held"),
    ("hidden by a builder's verdict", [cleared(at=5), comment("Verdict: hm", BUILDER, 7)], "held"),
    ("no verdict at all", [comment("Report: ready", BUILDER, 3)], "held"),
    ("no comment at all", [], "held"),
]


@pytest.mark.parametrize(("name", "comments", "outcome"), VERDICT_CASES)
def test_only_an_exact_cleared_verdict_for_the_head_clears(tmp_path, name, comments, outcome):
    """REQ-046 AC2: SPEC-0039 rule 3 (every case that does not count)."""
    proc, _ = merge_cleared_run(tmp_path, toml(ON), comments)
    line = one_line(proc)
    assert line.startswith(f"merge-cleared #7 {SHA12}: {outcome}: "), (name, line)
    assert "rule 3" in line
    assert HEAD not in line and OLD[:12] not in line
    assert proc.returncode == 3


def test_a_cleared_verdict_after_other_comments_clears(tmp_path):
    """REQ-046 AC2: SPEC-0039 rule 3 (the latest `Verdict:` decides; other comments do not hide)."""
    comments = [
        comment(f"Verdict: fix list {OLD}", at=1),
        comment(f"Report: {HEAD[:7]} ready for review", BUILDER, 2),
        cleared(at=3),
        comment("Progress: done 6/6", BUILDER, 4),
    ]
    proc, _ = merge_cleared_run(tmp_path, toml(ON), comments)
    assert one_line(proc).endswith(f": merged {MERGE12}") and proc.returncode == 0


def test_a_crlf_body_still_reads_its_first_line(tmp_path):
    """REQ-046 AC2: SPEC-0039 rule 3 (a body written on Windows)."""
    body = f"Verdict: cleared {HEAD}\r\n\r\nReviewed.\r\n"
    proc, _ = merge_cleared_run(tmp_path, toml(ON), [comment(body, at=5)])
    assert one_line(proc).endswith(f": merged {MERGE12}")


def test_the_newest_verdict_is_found_by_time_not_by_list_order(tmp_path):
    """REQ-046 AC2: SPEC-0039 rule 3 (the latest comment)."""
    comments = [comment(f"Verdict: fix list {HEAD}", at=9), cleared(at=5)]
    proc, _ = merge_cleared_run(tmp_path, toml(ON), comments)
    assert ": held: " in one_line(proc) and proc.returncode == 3


def test_a_cleared_verdict_on_the_second_page_counts(tmp_path):
    """REQ-046 AC2: brief #528 answer 1 (the comments are read page by page)."""
    comments = [comment(f"Report: {i}", BUILDER, 0, cid=i) for i in range(150)]
    comments.append(cleared(at=30))
    proc, made = merge_cleared_run(tmp_path, toml(ON), comments)
    assert one_line(proc).endswith(f": merged {MERGE12}")
    assert len([c for c in made if any("/comments" in a for a in c)]) == 2


def test_a_sha_that_is_not_the_head_is_refused(tmp_path):
    """REQ-046 AC2: SPEC-0039 rule 3 (a `--sha` that differs from the head)."""
    pull = {"number": 7, "head": {"sha": OLD}, "state": "open"}
    proc, _ = merge_cleared_run(tmp_path, toml(ON), [cleared()], pull=pull)
    line = one_line(proc)
    assert line.startswith(f"merge-cleared #7 {SHA12}: refused: head moved")
    assert OLD[:12] not in line and proc.returncode == 3


@pytest.mark.parametrize(
    "args",
    [
        ["--pr", "7", "--sha", SHA12],
        ["--pr", "7", "--sha", HEAD.upper()],
        ["--pr", "7", "--sha", HEAD + "0"],
        ["--pr", "x7", "--sha", HEAD],
        ["--pr", "0", "--sha", HEAD],
        ["--sha", HEAD, "--pr", "7"],
        ["--pr", "7"],
        ["--pr", "7", "--sha", HEAD, "--force"],
        [],
    ],
)
def test_anything_but_the_two_options_in_order_is_refused_before_any_read(tmp_path, args):
    """REQ-046 AC2: SPEC-0039 rule 2 (two options in that order, a number and a full sha)."""
    root = repo(tmp_path, toml(ON))
    bin_dir, log = fake_gh(tmp_path, comments=[cleared()])
    proc = run(root, bin_dir, *args)
    line = one_line(proc)
    assert line.startswith("merge-cleared #? ?: refused: ") and "usage" in line
    assert proc.returncode == 1 and calls(log) == []


# --- rule 3: conductor_accounts -----------------------------------------------------------------


def yaml(*extra: str) -> str:
    return "version: 1\n" + f'spec_approvers: ["@{OWNER}"]\n' + "".join(e + "\n" for e in extra)


def test_without_conductor_accounts_a_cleared_verdict_by_any_author_clears(tmp_path):
    """REQ-046 AC2: SPEC-0039 rule 3 (one account is the default)."""
    for login, sub in ((BUILDER, "a"), (OWNER, "b")):
        proc, _ = merge_cleared_run(
            tmp_path / sub, toml(ON), [cleared(login=login)], reviewers_yaml=yaml()
        )
        assert one_line(proc).endswith(f": merged {MERGE12}")


def test_an_empty_conductor_accounts_list_is_the_one_account_default(tmp_path):
    """REQ-046 AC2: brief #528 answer 2 (absent or empty)."""
    proc, _ = merge_cleared_run(
        tmp_path, toml(ON), [cleared(login=BUILDER)], reviewers_yaml=yaml("conductor_accounts: []")
    )
    assert one_line(proc).endswith(f": merged {MERGE12}")


def test_with_conductor_accounts_only_a_listed_author_clears(tmp_path):
    """REQ-046 AC2: SPEC-0039 rule 3 (the second-account option)."""
    listed = yaml(f'conductor_accounts: ["@{CONDUCTOR}"]')
    proc, _ = merge_cleared_run(
        tmp_path / "a", toml(ON), [cleared(login=CONDUCTOR.upper())], reviewers_yaml=listed
    )
    assert one_line(proc).endswith(f": merged {MERGE12}")
    proc, _ = merge_cleared_run(
        tmp_path / "b", toml(ON), [cleared(login=BUILDER)], reviewers_yaml=listed
    )
    line = one_line(proc)
    assert ": held: " in line and "conductor_accounts" in line and BUILDER not in line
    assert proc.returncode == 3


@pytest.mark.parametrize(
    "entry",
    [
        'conductor_accounts: ["@REPLACE-ME"]',
        f'conductor_accounts: ["@{CONDUCTOR}", "@replace-me"]',
        f'conductor_accounts: ["@{OWNER}"]',
        f'conductor_accounts: ["@{CONDUCTOR}", "{OWNER.upper()}"]',
        'conductor_accounts: ["@org/secretvalue-team"]',
        "conductor_accounts: secretvalue",
    ],
)
def test_a_placeholder_a_spec_approver_or_a_bad_list_is_refused_naming_the_setting(tmp_path, entry):
    """REQ-046 AC2: SPEC-0039 rule 3 (`@REPLACE-ME` or a spec approver is refused)."""
    proc, made = merge_cleared_run(
        tmp_path, toml(ON), [cleared(login=CONDUCTOR)], reviewers_yaml=yaml(entry)
    )
    line = one_line(proc)
    assert line.startswith(f"merge-cleared #7 {SHA12}: refused: ")
    assert "conductor_accounts" in line
    assert HIDDEN not in line and OWNER not in line
    assert proc.returncode == 1 and made == []


def test_conductor_accounts_are_read_from_the_default_branch(tmp_path):
    """REQ-046 AC2: Q-528-3 (the list is read where the setting is, never from the work tree)."""
    root = repo(tmp_path, toml(ON), reviewers_yaml=yaml(f'conductor_accounts: ["@{CONDUCTOR}"]'))
    (root / "config" / "reviewers.yaml").write_text(yaml(), encoding="utf-8")
    bin_dir, _ = fake_gh(tmp_path, comments=[cleared(login=BUILDER)])
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    assert ": held: " in one_line(proc) and proc.returncode == 3


def test_reviewers_reads_the_optional_conductor_accounts():
    """REQ-046 AC2: brief #528 answer 2 (`reviewers.py` reads the key; absent or empty is none)."""
    assert reviewers.conductors_of({}) == []
    assert reviewers.conductors_of({"conductor_accounts": []}) == []
    data = {"conductor_accounts": [f"@{CONDUCTOR}", "Other-Login"], "spec_approvers": [f"@{OWNER}"]}
    assert reviewers.conductors_of(data) == [CONDUCTOR, "other-login"]
    for bad in (
        {"conductor_accounts": ["@REPLACE-ME"]},
        {"conductor_accounts": [f"@{OWNER}"], "spec_approvers": [f"@{OWNER}"]},
        {"conductor_accounts": HIDDEN},
        {"conductor_accounts": [f"@org/{HIDDEN}"]},
    ):
        with pytest.raises(CheckError) as err:
            reviewers.conductors_of(bad)
        assert "conductor_accounts" in str(err.value) and HIDDEN not in str(err.value)
        assert OWNER not in str(err.value)
    assert "conductor_accounts" in reviewers.TOP_KEYS


def test_the_repository_reviewers_file_is_unchanged_and_lists_no_conductor():
    """REQ-046 AC2: brief #528 answer 2 (`config/reviewers.yaml` is not changed)."""
    root = SCRIPTS.parents[1]
    data = reviewers.parse((root / "config" / "reviewers.yaml").read_text(encoding="utf-8"))
    assert "conductor_accounts" not in data


# --- reads: REST only, no shell, no --jq, the same on Windows, five failures ----------------------


def test_the_reads_are_rest_gets_as_argument_lists_with_no_jq(tmp_path):
    """REQ-046 AC2: brief #528 answer 1 (`gh api`, REST, argument lists, no `--jq`)."""
    proc, made = merge_cleared_run(tmp_path, toml(ON), [cleared()])
    assert proc.returncode == 0
    assert made == [
        ["api", "--method", "GET", f"repos/{REPO}/pulls/7"],
        ["api", "--method", "GET", f"repos/{REPO}/issues/7/comments?per_page=100&page=1"],
        ["api", "--method", "GET", f"repos/{REPO}/issues?state=open&per_page=100&page=1"],
        ["api", "--method", "GET", f"repos/{REPO}/commits/{HEAD}/check-runs?per_page=100&page=1"],
        ["api", "--method", "GET", f"repos/{REPO}/pulls/7/files?per_page=100&page=1"],
        ["api", "--method", "GET", f"repos/{REPO}/pulls/7/commits?per_page=100&page=1"],
        merge_call(),
    ]
    flat = [a for c in made for a in c]
    assert "--jq" not in flat and "graphql" not in flat


def recorded_runs(monkeypatch, platform: str) -> list[tuple[list[str], dict]]:
    seen: list[tuple[list[str], dict]] = []
    answers = {
        "pulls/7": {"head": {"sha": HEAD}},
        "comments": [cleared()],
    }

    def fake_run(argv, **kwargs):
        seen.append((list(argv), kwargs))
        out = answers["comments"] if "comments" in argv[-1] else answers["pulls/7"]
        return subprocess.CompletedProcess(argv, 0, json.dumps(out), "")

    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr(merge_cleared.subprocess, "run", fake_run)
    monkeypatch.setattr(merge_cleared.shutil, "which", lambda name: f"/fake/{name}")
    pull = merge_cleared.read_json(f"repos/{REPO}/pulls/7", dict, "the pull request")
    found = merge_cleared.read_comments(REPO, 7)
    assert pull["head"]["sha"] == HEAD and len(found) == 1
    return seen


def test_the_same_argument_lists_on_a_fake_windows_platform(monkeypatch):
    """REQ-046 AC2: brief #528 answer 5 (the same lists on Windows, no shell)."""
    posix = recorded_runs(monkeypatch, "linux")
    windows = recorded_runs(monkeypatch, "win32")
    assert [argv for argv, _ in posix] == [argv for argv, _ in windows]
    for argv, kwargs in posix + windows:
        assert argv[0] == "gh" and "--jq" not in argv
        assert not kwargs.get("shell")


def test_five_failed_reads_in_a_row_exit_4_and_never_read_as_empty(tmp_path):
    """REQ-046 AC2: SPEC-0039 rule 2 (exit 4; a failed read is never an empty list or a pass)."""
    root = repo(tmp_path, toml(ON))
    bin_dir, log = fake_gh(tmp_path, comments=[cleared()], fail=True)
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    line = one_line(proc)
    assert line.startswith(f"merge-cleared #7 {SHA12}: refused: ") and "GitHub" in line
    assert proc.returncode == 4
    assert len(calls(log)) == 5


def test_a_read_that_answers_the_wrong_shape_is_a_failed_read(monkeypatch):
    """REQ-046 AC2: brief #528 answer 1 (a failed read is never taken as an empty list)."""
    count = []

    def fake_run(argv, **kwargs):
        count.append(argv)
        return subprocess.CompletedProcess(argv, 0, '{"message": "Not Found"}', "")

    monkeypatch.setattr(merge_cleared.subprocess, "run", fake_run)
    monkeypatch.setattr(merge_cleared.shutil, "which", lambda name: f"/fake/{name}")
    monkeypatch.setattr(merge_cleared, "PAUSE", 0)
    with pytest.raises(merge_cleared.Unreadable):
        merge_cleared.read_comments(REPO, 7)
    assert len(count) == 5


def test_one_failed_read_is_retried(monkeypatch):
    """REQ-046 AC2: SPEC-0039 rule 2 (five reads in a row, as session rule 21 counts)."""
    answers = iter(
        [
            subprocess.CompletedProcess([], 1, "", "HTTP 502"),
            subprocess.CompletedProcess([], 0, json.dumps({"head": {"sha": HEAD}}), ""),
        ]
    )
    monkeypatch.setattr(merge_cleared.subprocess, "run", lambda argv, **kw: next(answers))
    monkeypatch.setattr(merge_cleared.shutil, "which", lambda name: f"/fake/{name}")
    monkeypatch.setattr(merge_cleared, "PAUSE", 0)
    assert merge_cleared.read_json("repos/x/y/pulls/7", dict, "the pull request")["head"]


def test_a_remote_that_is_not_github_or_no_gh_is_refused(tmp_path):
    """REQ-046 AC2: brief #528 answer 1 (refusals name the setting or the tool, never a value)."""
    proc, made = merge_cleared_run(
        tmp_path, toml(ON), [cleared()], origin="https://example.com/secretvalue.git"
    )
    line = one_line(proc)
    assert "refused" in line and "origin" in line and HIDDEN not in line
    assert proc.returncode == 1 and made == []


# --- this build merges nothing ------------------------------------------------------------------


def test_the_script_writes_no_file_and_makes_no_other_write():
    """REQ-046 AC5: SPEC-0039 rule 8 (build (b) adds the one merge call and nothing else)."""
    text = SCRIPT.read_text(encoding="utf-8")
    words = ('"POST"', '"PATCH"', '"DELETE"', ".write_text(", "open(", '"push"', "--jq")
    words += ("shell=True", "graphql", '"tag"', "/reviews")
    for word in words:
        assert word not in text, word


def test_the_script_is_installed_and_the_templates_carry_the_commented_keys():
    """REQ-046 AC1: brief #528 answers 1 and 4 (installed; the template's keys commented, off).

    This repository's own agk.toml turns it on by the owner's choice (brief #534, ADR-0266).
    """
    root = SCRIPTS.parents[1]
    manifest = json.loads((root / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/merge_cleared.py" in manifest["verbatim"]
    assert manifest["verbatim"] == sorted(manifest["verbatim"])
    lines = (root / "kit/templates/agk.toml").read_text(encoding="utf-8").splitlines()
    assert "# auto_merge = false" in lines
    assert '# auto_merge_method = "squash"' in lines
    assert not any(x.startswith("auto_merge") for x in lines)
    import tomllib

    template = tomllib.loads((root / "kit/templates/agk.toml").read_text(encoding="utf-8"))
    assert merge_cleared.auto_merge_setting(template) == "off"
    lines = (root / "agk.toml").read_text(encoding="utf-8").splitlines()
    assert "auto_merge = true" in lines
    assert 'auto_merge_method = "squash"' in lines
    data = tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
    assert merge_cleared.auto_merge_setting(data) == "on"
