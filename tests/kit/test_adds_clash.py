"""A brief whose `Adds:` another open brief or pull request holds is refused at filing, with a free
name; two lines of one key name both and the line to use (brief #1425, ADR-0598; REQ-050).

`check_brief.py --root` reads the open briefs from `--open-briefs FILE` or the plan's read cache,
never by a request. Recorded issue lists only, invented names, no network."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "agk" / "check_brief.py"
BODY = (
    'Sentence: "A team can run a thing."\n'
    "Answers (the maintainers'):\n1. one\n"
    "Size: M\nAdvances: new\nTouches: src/app.py\n{adds}"
    "Contexts: kit (x); github (x); local (x); personal (x); stacks (x)\n"
)


def other(number: int, adds: str, taken: bool = False) -> dict:
    labels = [{"name": "agk-brief"}] + ([{"name": "agk:taken"}] if taken else [])
    return {"number": number, "body": BODY.format(adds=f"Adds: {adds}\n"), "labels": labels}


def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "requirements.md").write_text("### REQ-001 a\n", encoding="utf-8")
    (root / "src").mkdir(exist_ok=True)
    (root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    return root


def check(tmp_path: Path, adds: str, opened, *extra: str):
    (tmp_path / "brief.md").write_text(BODY.format(adds=adds), encoding="utf-8")
    (tmp_path / "open.json").write_text(json.dumps(opened), encoding="utf-8")
    args = [str(tmp_path / "brief.md"), "--root", str(project(tmp_path))]
    args += ["--open-briefs", str(tmp_path / "open.json"), *extra]
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={"AGK_READ_CACHE": "off", "PATH": "/usr/bin:/bin"},
    )


def test_a_free_path_passes(tmp_path):
    """REQ-050"""
    out = check(tmp_path, "Adds: src/ac-m7-api/\n", [other(66, "src/gaps2/")])
    assert out.returncode == 0 and out.stdout.strip() == "ok brief"


def test_a_path_another_brief_adds_is_refused_with_a_free_name(tmp_path):
    """REQ-050"""
    out = check(tmp_path, "Adds: src/gaps2/\n", [other(66, "src/gaps2/", taken=True)])
    assert out.returncode == 1
    assert "Adds entry src/gaps2/ is held by #66 (src/gaps2/); free: src/gaps2-2/" in out.stdout


def test_case_and_covering_folder_clash(tmp_path):
    """REQ-050"""
    out = check(tmp_path, "Adds: src/Gaps2/a.py\n", [other(66, "src/gaps2/")])
    assert out.returncode == 1 and "free: src/gaps2-2/" in out.stdout  # the folder, not the file
    assert check(tmp_path, "Adds: ./src/gaps2\n", [other(66, "src/gaps2/x.py")]).returncode == 1


def test_a_file_an_open_pull_request_adds_is_refused(tmp_path):
    """REQ-050"""
    opened = {"briefs": [], "pulls": [{"number": 70, "brief": 66, "added": ["src/gaps2/a.py"]}]}
    out = check(tmp_path, "Adds: src/gaps2/\n", opened)
    assert out.returncode == 1 and "held by #70" in out.stdout


def test_the_brief_itself_is_left_out_by_its_number(tmp_path):
    """REQ-050: a brief edited keeps its own name; edited to take another's, it is refused."""
    mine = other(565, "src/gaps3/")
    assert check(tmp_path, "Adds: src/gaps3/\n", [mine], "--number", "565").returncode == 0
    out = check(tmp_path, "Adds: src/gaps2/\n", [mine, other(66, "src/gaps2/")], "--number", "565")
    assert out.returncode == 1 and "#66" in out.stdout


def test_a_windows_reserved_name_is_refused(tmp_path):
    """REQ-050"""
    out = check(tmp_path, "Adds: src/aux/\n", [])
    assert out.returncode == 1 and "Windows reserves" in out.stdout


def test_two_adds_lines_name_both_and_the_merged_line(tmp_path):
    """REQ-050"""
    out = check(tmp_path, "Adds: a.py, b.py\nAdds: c.py\n", [])
    assert out.returncode == 1
    assert (
        "line 7 and line 8 are both Adds: lines; use one line Adds: a.py, b.py, c.py" in out.stdout
    )
    assert "at most one line Adds" not in out.stdout


def test_two_reserved_and_two_expected_lines_are_refused(tmp_path):
    """REQ-050"""
    out = check(
        tmp_path, "Reserved: ADR-0001\nReserved: ADR-0002\nExpected: 1 hour\nExpected: 2\n", []
    )
    assert "Reserved: lines; use one line Reserved: ADR-0001, ADR-0002" in out.stdout
    assert "Expected: lines; keep one" in out.stdout


def test_the_event_passes_its_issue_number(tmp_path):
    """REQ-050: personal mode and CI pass the open briefs as a file, compared the same way."""
    (tmp_path / "open.json").write_text(json.dumps([other(66, "src/gaps2/")]), encoding="utf-8")
    issue = other(565, "src/gaps2/")
    payload = {"action": "edited", "issue": issue}
    (tmp_path / "event.json").write_text(json.dumps(payload), encoding="utf-8")
    args = ["--event", str(tmp_path / "event.json"), "--root", str(project(tmp_path))]
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args, "--open-briefs", str(tmp_path / "open.json")],
        capture_output=True,
        text=True,
        env={"AGK_READ_CACHE": "off", "PATH": "/usr/bin:/bin"},
    )
    found = json.loads(out.stdout)
    assert found["action"] == "fail" and any("#66" in p for p in found["problems"])


# --- answer 2: the plan starts neither brief of an older clash ----------------------------------

import pytest  # noqa: E402
from test_session import ISSUES, REPO, Stub, comment, issue, listing  # noqa: E402
from test_session_flow import DAY  # noqa: E402
from test_session_flow import brief as flow_brief  # noqa: E402
from test_session_plan import data, free, plan  # noqa: E402


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    return repo


def adding(touches: str, adds: str) -> str:
    return flow_brief(touches) + f"Adds: {adds}\n"


def test_the_plan_starts_neither_brief_of_a_clash(proj, stub):
    """REQ-050"""
    listing(
        stub,
        [
            issue(5, adding("docs/a.md", "src/gaps2/")),
            issue(6, adding("docs/b.md", "src/Gaps2/x.py")),
        ],
    )
    free(stub, 5, 6)
    got = data(proj, stub)
    assert got["start"] == [] and got["clashes"][0]["briefs"] == [5, 6]
    words = plan(proj, stub).stdout
    assert (
        "CLASH: #5 and #6 both add src/gaps2/; rename in the one not taken "
        "(#6, free: src/gaps2-2/)." in words
    )


def test_a_taken_brief_of_a_clash_keeps_running_and_the_other_waits(proj, stub):
    """REQ-050"""
    listing(
        stub,
        [issue(5, adding("docs/a.md", "src/gaps2/")), issue(6, adding("docs/b.md", "src/gaps2/"))],
    )
    stub.serve(f"{ISSUES}/6/comments", [comment(1, "x", f"taken: builder-x {DAY}")])
    free(stub, 5)
    got = data(proj, stub)
    assert got["start"] == [] and got["clashes"][0]["rename"] == 5
    assert got["clashes"][0]["taken"] == [6]


def test_without_a_clash_the_plan_is_as_before(proj, stub):
    """REQ-050"""
    listing(
        stub,
        [
            issue(5, adding("docs/a.md", "src/m1-api/")),
            issue(6, adding("docs/b.md", "src/m7-api/")),
        ],
    )
    free(stub, 5, 6)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [5, 6] and "clashes" not in got
