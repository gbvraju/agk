"""Exact `Touches:`, `Adds:` and `Broad:` (amendment 141 items 1, 2 and 9; REQ-057 AC8).

A broad `Touches:` entry over files that can hold a brief is refused unless the brief says it is
a sweep; `Adds:` names only new files; every reader takes the two lines as one list. Invented
trees and briefs only; a `gh` stub serves saved JSON; no network."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import doctor
import pytest
import route
import session
import session_plan
from common import CheckError
from test_session import ISSUES, REPO, Stub, issue, listing
from test_session_flow import brief, flow
from test_session_plan import free, plan

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
GOOD = (
    'Sentence: "A thing."\nAnswers:\n1. one\nSize: M\nAdvances: new\nTouches: src/a.py\n'
    "Contexts: kit (x); github (x); local (x); personal (x); stacks (x)\n"
)
OVER = "rule 4: Touches entry {} matches more than flow.max_touch_glob files"
EXISTS = "rule 4: Adds entry {} names an existing file"


def tree(root: Path, **counts: int) -> None:
    """COUNTS files `f<i>.py` in each folder (`__` is a slash), under ROOT."""
    for folder, count in counts.items():
        where = root / folder.replace("__", "/")
        where.mkdir(parents=True, exist_ok=True)
        for i in range(count):
            (where / f"f{i}.py").write_text("x\n", encoding="utf-8")


def problems(root: Path, body: str) -> list[str]:
    return session_plan.touch_problems(body, session_plan.touch_rules(root))


def with_touches(entry: str, *extra: str) -> str:
    return GOOD.replace("Touches: src/a.py", f"Touches: {entry}") + "".join(f"{x}\n" for x in extra)


def check(tmp_path: Path, body: str, *extra: str):
    (tmp_path / "brief.md").write_text(body, encoding="utf-8")
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "check_brief.py"), str(tmp_path / "brief.md"), *extra],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "line",
    ["Adds: a.py\nAdds: b.py", "Adds: a.py,", "Broad: one\nBroad: two", "Broad:   "],
)
def test_ac8_the_shape_of_adds_and_broad_is_checked_without_a_root(tmp_path, line):
    """REQ-057 AC8: without `--root` only the shape of the lines is checked."""
    proc = check(tmp_path, GOOD + line + "\n")
    assert proc.returncode == 1 and "rule 4" in proc.stdout


def test_ac8_good_adds_and_broad_lines_pass_without_a_root(tmp_path):
    """REQ-057 AC8: the lines are optional and one of each is good."""
    assert check(tmp_path, GOOD + "Adds: a.py, new/\nBroad: a sweep\n").returncode == 0


@pytest.mark.parametrize("entry", ["src/**", "src/", "src/*.py", "src"])
def test_ac8_a_broad_entry_is_refused_naming_rule_setting_and_entry(tmp_path, entry):
    """REQ-057 AC8: a folder, a wildcard or a folder without its slash over the limit."""
    tree(tmp_path, src=6)
    assert problems(tmp_path, with_touches(entry)) == [OVER.format(entry)]


def test_ac8_the_refusal_comes_from_check_brief_with_a_root_and_names_no_count(tmp_path):
    """REQ-057 AC8: `check_brief.py --root` holds the one function."""
    tree(tmp_path, src=6)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/requirements.md").write_text("### REQ-001 — a\n", encoding="utf-8")
    proc = check(tmp_path, with_touches("src/**"), "--root", str(tmp_path))
    assert proc.returncode == 1 and OVER.format("src/**") in proc.stdout
    assert " 6 " not in proc.stdout and " 5 " not in proc.stdout


def test_ac8_the_limit_is_exact_and_a_named_file_never_counts(tmp_path):
    """REQ-057 AC8: five files pass by default; an exact entry is no folder."""
    tree(tmp_path, src=5, big=9)
    assert problems(tmp_path, with_touches("src/**")) == []
    assert problems(tmp_path, with_touches("big/f0.py, big/f1.py")) == []


def test_ac8_only_files_that_can_hold_count(tmp_path):
    """REQ-057 AC8: shared-mechanical files, shared indexes and prose never count (Q-772-3)."""
    for i in range(9):
        path = tmp_path / "changelog.d" / f"c{i}.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text("x\n", encoding="utf-8")
        guide = tmp_path / "docs/guides" / f"g{i}.md"
        guide.parent.mkdir(parents=True, exist_ok=True)
        guide.write_text("x\n", encoding="utf-8")
    assert problems(tmp_path, with_touches("changelog.d/*.md, docs/guides/**")) == []


def test_ac8_specs_and_adrs_are_not_prose_so_they_count(tmp_path):
    """REQ-057 AC8: the default of `reprove_paths` leaves specs and ADRs as files that hold."""
    for i in range(6):
        path = tmp_path / "docs/specs" / f"000{i}-a.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")
    assert problems(tmp_path, with_touches("docs/specs/**")) == [OVER.format("docs/specs/**")]


def test_ac8_a_broad_line_passes_every_entry(tmp_path):
    """REQ-057 AC8: `Broad:` is the brief's own statement; no check judges the reason."""
    tree(tmp_path, src=6, lib=6)
    assert problems(tmp_path, with_touches("src/**, lib/**", "Broad: a rename everywhere")) == []


def test_ac8_a_repeated_broad_line_is_no_sweep(tmp_path):
    """REQ-057 AC8: one line `Broad:`, and two are not one."""
    tree(tmp_path, src=6)
    body = with_touches("src/**", "Broad: one", "Broad: two")
    assert problems(tmp_path, body) == [OVER.format("src/**")]


def test_ac8_max_touch_glob_sets_the_limit(tmp_path):
    """REQ-057 AC8: `[flow] max_touch_glob` replaces the default of 5."""
    tree(tmp_path, src=3)
    (tmp_path / "agk.toml").write_text("[flow]\nmax_touch_glob = 2\n", encoding="utf-8")
    assert problems(tmp_path, with_touches("src/**")) == [OVER.format("src/**")]


@pytest.mark.parametrize("value", ["0", '"many"', "true", "1.5"])
def test_ac8_a_bad_max_touch_glob_is_refused_naming_the_setting_only(tmp_path, value):
    """REQ-057 AC8: refused naming the setting, never the value."""
    (tmp_path / "agk.toml").write_text(f"[flow]\nmax_touch_glob = {value}\n", encoding="utf-8")
    with pytest.raises(CheckError) as caught:
        session_plan.touch_rules(tmp_path)
    assert "max_touch_glob" in str(caught.value) and value not in str(caught.value)


@pytest.mark.parametrize("value", ['"docs"', "[1]", '[""]', '["!"]'])
def test_ac8_a_bad_reprove_paths_is_refused_naming_the_setting_only(tmp_path, value):
    """REQ-057 AC8: `flow.reprove_paths` is a list of non-empty strings."""
    (tmp_path / "agk.toml").write_text(f"[flow]\nreprove_paths = {value}\n", encoding="utf-8")
    with pytest.raises(CheckError) as caught:
        session_plan.touch_rules(tmp_path)
    assert "setting: flow.reprove_paths" in str(caught.value)
    assert "docs" not in str(caught.value).replace("flow.reprove_paths", "")


def test_ac8_a_set_reprove_paths_replaces_the_default_and_bang_takes_away(tmp_path):
    """REQ-057 AC8: the list is read in order; a `!` entry takes matches away again."""
    tree(tmp_path, notes=6, notes__keep=1)
    for path in (tmp_path / "notes").rglob("*.py"):
        path.rename(path.with_suffix(".txt"))
    text = '[flow]\nreprove_paths = ["notes/**", "!notes/keep/**"]\n'
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    assert problems(tmp_path, with_touches("notes/**")) == []
    rules = session_plan.reprove_paths(tmp_path)
    assert session_plan.is_prose("notes/f0.txt", rules)
    assert not session_plan.is_prose("notes/keep/f0.txt", rules)
    assert not session_plan.is_prose("README.md", rules)


def test_ac8_the_default_of_reprove_paths(tmp_path):
    """REQ-057 AC8: every `.md` but specs and ADRs (Q-772-5)."""
    rules = session_plan.reprove_paths(tmp_path)
    assert session_plan.is_prose("README.md", rules)
    assert session_plan.is_prose("docs/guides/a.md", rules)
    assert not session_plan.is_prose("docs/specs/0001-a.md", rules)
    assert not session_plan.is_prose("docs/adr/0001-a.md", rules)
    assert not session_plan.is_prose("src/a.py", rules)


def test_ac8_adds_may_not_name_an_existing_file(tmp_path):
    """REQ-057 AC8: `Adds:` is no way round the count (Q-772-4)."""
    tree(tmp_path, src=2)
    body = with_touches("x.py", "Adds: src/**")
    assert problems(tmp_path, body) == [EXISTS.format("src/**")]


def test_ac8_a_broad_line_does_not_excuse_adds_naming_an_existing_file(tmp_path):
    """REQ-057 AC8: `Broad:` passes the count only."""
    tree(tmp_path, src=2)
    body = with_touches("x.py", "Adds: src/f0.py", "Broad: a sweep")
    assert problems(tmp_path, body) == [EXISTS.format("src/f0.py")]


def test_ac8_adds_names_new_files_and_new_folders_and_shared_mechanical_files(tmp_path):
    """REQ-057 AC8: a new name passes; an existing shared-mechanical file is set aside."""
    tree(tmp_path, src=2)
    (tmp_path / "changelog.d").mkdir()
    (tmp_path / "changelog.d/old.md").write_text("x\n", encoding="utf-8")
    body = with_touches("x.py", "Adds: src/new.py, brand/, brand2, changelog.d/old.md")
    assert problems(tmp_path, body) == []


def test_ac8_an_existing_folder_named_in_adds_without_its_slash_is_refused(tmp_path):
    """REQ-057 AC8: the folder is read as a folder, so it matches what lies under it."""
    tree(tmp_path, src=1)
    assert problems(tmp_path, with_touches("x.py", "Adds: src")) == [EXISTS.format("src")]


def test_ac8_the_tree_is_git_s_list_in_a_repository(repo):
    """REQ-057 AC8: untracked files of a checkout do not count."""
    repo.commit({"src/a.py": "x\n"}, "base")
    for i in range(9):
        repo.write(f"src/u{i}.py", "x\n")
    assert (
        session_plan.touch_problems(with_touches("src/**"), session_plan.touch_rules(repo.root))
        == []
    )


def test_ac8_the_red_branch_brief_of_the_router_says_it_is_a_sweep(tmp_path):
    """REQ-057 AC8: `Touches: **` of the router is a sweep, so a red branch is never refused."""
    tree(tmp_path, src=6)
    body = route.red_body("Lint", "abc1234", "https://example.com/run")
    assert session.brief_problems(body) == []
    assert problems(tmp_path, body) == []


def test_touches_of_reads_both_lines_as_one_list():
    """Amendment 141 item 1: every reader takes `Touches:` and `Adds:` as one list."""
    assert session.touches_of(GOOD + "Adds: b.py, new/\n") == ["src/a.py", "b.py", "new/"]


def test_a_new_file_in_adds_does_not_lower_the_kind():
    """Amendment 141 item 1: moving a protected new file to `Adds:` never lowers a kind."""
    body = GOOD.replace("Size: M", "Size: S") + "Adds: scripts/agk/new.py\n"
    assert session.kind_of(body, ["scripts/agk/"]) == "build"
    assert session.kind_of(GOOD.replace("Size: M", "Size: S"), ["scripts/agk/"]) == "small"


def test_a_repeated_adds_line_reads_as_design():
    """Amendment 141 item 1: an unreadable line never lowers a kind."""
    body = GOOD.replace("Size: M", "Size: S") + "Adds: a.py\nAdds: b.py\n"
    assert session.kind_of(body, ["scripts/agk/"]) == "design"


def test_a_ui_file_in_adds_needs_a_screens_line(tmp_path):
    """Amendment 141 item 1: `Adds:` does not hide a UI brief (SPEC-0037 rule 10)."""
    (tmp_path / "agk.toml").write_text('[design]\nui_paths = ["app/**"]\n', encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/requirements.md").write_text("### REQ-001 — a\n", encoding="utf-8")
    proc = check(tmp_path, GOOD + "Adds: app/new.html\n", "--root", str(tmp_path))
    assert proc.returncode == 1 and "Screens" in proc.stdout


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    repo.write("config/protected-paths.txt", "config/\nscripts/agk/\n")
    repo.commit({f"src/f{i}.py": "x\n" for i in range(6)}, "base")
    return repo


def test_ac8_plan_prints_the_refusal_on_its_malformed_line(proj, stub):
    """REQ-057 AC8: `plan` agrees with the brief check."""
    listing(stub, [issue(5, brief("src/**"))])
    free(stub, 5)
    lines = plan(proj, stub).stdout.splitlines()
    assert any(x.startswith(f"MALFORMED: #5 {OVER.format('src/**')}") for x in lines)


def test_ac8_next_does_not_take_a_broad_brief(proj, stub):
    """REQ-057 AC8: `next` applies the same function."""
    listing(stub, [issue(5, brief("src/**"))])
    free(stub, 5)
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "session.py"), "next", "--session", "s1"],
        cwd=proj.root,
        capture_output=True,
        text=True,
        env=stub_env(stub),
    )
    assert OVER.format("src/**") in out.stdout + out.stderr
    assert not any(c[:2] == ["POST", f"{ISSUES}/5/comments"] for c in stub.calls())


def stub_env(stub: Stub) -> dict:
    from test_session import clean_env

    env = clean_env()
    env.update(PATH=f"{stub.bin}:{env.get('PATH', '')}", GH_STUB_DIR=str(stub.dir))
    return env


def test_ac8_a_bad_setting_stops_the_plan_naming_the_setting(proj, stub):
    """REQ-057 AC8: a wrong value is refused naming the setting."""
    flow(proj, "max_touch_glob = 0")
    listing(stub, [issue(5, brief("src/a.py"))])
    free(stub, 5)
    out = plan(proj, stub)
    assert out.returncode != 0 and "max_touch_glob" in out.stdout + out.stderr


def test_two_briefs_adding_one_new_file_overlap(proj, stub):
    """Amendment 141 item 2, as ADR-0598 (brief #1425 answer 2) changes it: two waiting briefs
    that add one file are a clash; neither starts until one is renamed."""
    one, two = brief("a.txt") + "Adds: new/one.py\n", brief("b.txt") + "Adds: new/one.py\n"
    listing(stub, [issue(5, one), issue(6, two)])
    free(stub, 5, 6)
    out = json.loads(plan(proj, stub, "--json").stdout)
    assert out["start"] == []
    assert out["clashes"][0]["briefs"] == [5, 6] and out["clashes"][0]["path"] == "new/one.py"


def test_a_new_folder_holds_on_what_lies_under_it(proj, stub):
    """Amendment 141 item 2, as ADR-0598 changes it: a new folder holds what lies under it."""
    one, two = brief("a.txt") + "Adds: new/\n", brief("b.txt") + "Adds: new/one.py\n"
    listing(stub, [issue(5, one), issue(6, two)])
    free(stub, 5, 6)
    out = json.loads(plan(proj, stub, "--json").stdout)
    assert out["start"] == [] and out["clashes"][0]["rename"] == 6


class Reads:
    def __init__(self, briefs, why=""):
        self.result = (briefs, why)
        self.paths = []

    def get(self, key, path, **_):
        self.paths.append(path)
        return self.result


def test_item9_the_doctor_names_the_brief_and_the_entry(tmp_path):
    """Amendment 141 item 9: `brief-broad-touches` names both."""
    tree(tmp_path, src=6)
    reads = Reads([{"number": 5, "body": with_touches("src/**")}, {"number": 6, "body": GOOD}])
    result = doctor.broad_touches_result(tmp_path, reads)
    assert result.status == "fail" and "#5" in result.message and "src/**" in result.message
    assert "#6" not in result.message
    assert reads.paths == ["/issues?state=open&labels=agk-brief&per_page=100"]


def test_item9_the_doctor_is_quiet_for_exact_lines_and_a_sweep(tmp_path):
    """Amendment 141 item 9: a `Broad:` brief is not reported."""
    tree(tmp_path, src=6)
    swept = {"number": 5, "body": with_touches("src/**", "Broad: a sweep")}
    pull = {"number": 7, "body": with_touches("src/**"), "pull_request": {}}
    assert doctor.broad_touches_result(tmp_path, Reads([swept, pull])).status == "ok"


def test_item9_the_doctor_says_cannot_check_when_the_briefs_cannot_be_read(tmp_path):
    """Amendment 141 item 9: an unread list is not a pass."""
    result = doctor.broad_touches_result(tmp_path, Reads(None, "offline"))
    assert (result.status, result.reason) == ("cannot-check", "offline")


def test_item9_the_doctor_says_cannot_check_on_a_bad_setting(tmp_path):
    """Amendment 141 item 9: a bad setting is reported by its name, not raised."""
    (tmp_path / "agk.toml").write_text("[flow]\nmax_touch_glob = 0\n", encoding="utf-8")
    result = doctor.broad_touches_result(tmp_path, Reads([]))
    assert result.status == "cannot-check" and "max_touch_glob" in result.reason


def test_item9_the_row_is_a_warning_after_the_invalid_label_row():
    """Amendment 141 item 9: the severity and the place of the row."""
    assert doctor.CHECKS["brief-broad-touches"][0] == "warn"
    names = list(doctor.CHECKS)
    assert names.index("brief-broad-touches") == names.index("brief-invalid-label") + 1


# --- brief #1717: a later build is not refused for a file its own earlier build added -----------

OWN = "rule 4: Adds entry src/f0.py names an existing file"


def timeline(stub, number: int, *pulls: tuple[int, int, str | None]) -> None:
    """The timeline of brief NUMBER: one cross-reference per (pull, brief it names, merged_at)."""
    events = [
        {
            "event": "cross-referenced",
            "source": {
                "issue": {
                    "number": p,
                    "body": f"Advances: REQ-001\nBrief: #{b}\n",
                    "pull_request": {"merged_at": at},
                }
            },
        }
        for p, b, at in pulls
    ]
    stub.serve(f"{ISSUES}/{number}/timeline", events)


def added(stub, pull: int, *files: str, status: str = "added") -> None:
    stub.serve(f"repos/{REPO}/pulls/{pull}/files", [{"filename": f, "status": status} for f in files])


MERGED = "2026-11-20T10:00:00Z"


def later_build(stub, adds: str = "src/f0.py") -> None:
    listing(stub, [issue(5, brief("a.txt") + f"Adds: {adds}\n")])
    free(stub, 5)


def malformed(proj, stub) -> list[str]:
    out = plan(proj, stub)
    assert out.returncode == 0, out.stdout + out.stderr
    return [x for x in out.stdout.splitlines() if x.startswith("MALFORMED: #5")]


def test_1717_touch_problems_sets_aside_the_brief_s_own_added_files(tmp_path):
    """REQ-041 (brief #1717 answer 1): an entry whose every match is the brief's own is not refused."""
    tree(tmp_path, src=2)
    rules = session_plan.touch_rules(tmp_path)
    body = with_touches("x.py", "Adds: src/f0.py")
    assert session_plan.touch_problems(body, rules) == [OWN]
    assert session_plan.touch_problems(body, rules, frozenset({"src/f0.py"})) == []
    globbed = with_touches("x.py", "Adds: src/**")
    assert session_plan.touch_problems(globbed, rules, frozenset({"src/f0.py"})) == [
        EXISTS.format("src/**")
    ]


def test_1717_plan_offers_a_later_build_whose_own_merged_pull_request_added_the_file(proj, stub):
    """REQ-041 (brief #1717 answers 2 and 3): the plan reads the brief's own merged pull request."""
    later_build(stub)
    timeline(stub, 5, (9, 5, MERGED))
    added(stub, 9, "src/f0.py")
    assert malformed(proj, stub) == []
    assert all(c[0] == "GET" for c in stub.calls())


def test_1717_next_takes_the_later_build(proj, stub):
    """REQ-041 (brief #1717 answer 3): `next` reads the same shape."""
    later_build(stub)
    timeline(stub, 5, (9, 5, MERGED))
    added(stub, 9, "src/f0.py")
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "session.py"), "next", "--session", "s1"],
        cwd=proj.root,
        capture_output=True,
        text=True,
        env=stub_env(stub),
    )
    assert OWN not in out.stdout + out.stderr and "#5" in out.stdout


@pytest.mark.parametrize(
    "pulls, status",
    [
        ([(9, 6, MERGED)], "added"),  # another brief's pull request added it
        ([(9, 5, None)], "added"),  # closed without merge
        ([(9, 5, MERGED)], "modified"),  # merged, but it changed the file, not added it
        ([], "added"),  # no pull request of the brief at all
    ],
)
def test_1717_every_other_history_is_refused_as_today(proj, stub, pulls, status):
    """REQ-041 (brief #1717 answer 5): only a merged pull request of the brief that added it."""
    later_build(stub)
    timeline(stub, 5, *pulls)
    added(stub, 9, "src/f0.py", status=status)
    assert malformed(proj, stub) == [f"MALFORMED: #5 {OWN}"]


def test_1717_a_glob_over_an_own_file_and_another_file_is_refused(proj, stub):
    """REQ-041 (brief #1717 answer 5): every match must be the brief's own."""
    later_build(stub, "src/**")
    timeline(stub, 5, (9, 5, MERGED))
    added(stub, 9, "src/f0.py")
    assert malformed(proj, stub) == [f"MALFORMED: #5 {EXISTS.format('src/**')}"]


@pytest.mark.parametrize("unread", ["timeline", "files"])
def test_1717_an_unreadable_history_fails_closed(proj, stub, unread):
    """REQ-041 (brief #1717 answer 2): a timeline or file list that cannot be read refuses."""
    later_build(stub)
    if unread != "timeline":
        timeline(stub, 5, (9, 5, MERGED))
    assert malformed(proj, stub) == [f"MALFORMED: #5 {OWN}"]


def test_1717_a_brief_with_no_adds_refusal_reads_no_timeline(proj, stub):
    """REQ-041 (brief #1717 answer 2): nothing is read for a brief that is not refused."""
    listing(stub, [issue(5, brief("a.txt") + "Adds: new/one.py\n")])
    free(stub, 5)
    assert malformed(proj, stub) == []
    assert not any(c[1].split("?")[0].endswith("/issues/5/timeline") for c in stub.calls())


def test_1717_check_brief_stays_network_free_and_refuses(tmp_path):
    """REQ-041 (brief #1717 answer 3, Q-1717-2): the brief check passes no own files."""
    tree(tmp_path, src=2)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/requirements.md").write_text("### REQ-001 — a\n", encoding="utf-8")
    proc = check(tmp_path, GOOD + "Adds: src/f0.py\n", "--root", str(tmp_path))
    assert proc.returncode == 1 and OWN in proc.stdout


@pytest.mark.parametrize(
    "text",
    [
        'default_branch = "trunk"\n',
        "[flow]\nclaim_hours = 1\n",
        '[flow]\nassign = "next"\n',
        '[flow]\nassign = "conductor"\n',
        '[flow]\nbuilder_start = "start"\n',
        '[flow]\nbuilder_start = "assign"\n',
        "[flow]\nmax_builders = 1\n",
        'pr_mode = "strict"\n',
        'pr_mode = "flow"\n',
        'review_mode = "solo"\n',
        'review_mode = "team"\n',
        'execution = "hosted"\n',
        'execution = "hybrid"\n',
        'execution = "pool"\n',
        'execution = "local"\n',
        '[kit]\nlayout = "installed"\n',
        '[kit]\nlayout = "plugin"\n',
    ],
)
def test_1717_the_exemption_holds_under_each_setting(proj, stub, text):
    """REQ-041 (brief #1717 answer 4): settings the exemption does not read leave it as it is;
    `claim_hours` of one hour still counts a first build merged days before."""
    proj.write("agk.toml", text)
    later_build(stub)
    timeline(stub, 5, (9, 5, "2026-01-01T00:00:00Z"))
    added(stub, 9, "src/f0.py")
    assert malformed(proj, stub) == []


def test_1717_a_shared_index_refuses_unless_it_is_the_brief_s_own(proj, stub):
    """REQ-041 (brief #1717 answer 4): `[flow] shared_indexes` gives no exemption of its own."""
    flow(proj, 'shared_indexes = ["src/f0.py"]')
    later_build(stub)
    timeline(stub, 5, (9, 6, MERGED))
    added(stub, 9, "src/f0.py")
    assert malformed(proj, stub) == [f"MALFORMED: #5 {OWN}"]
    timeline(stub, 5, (9, 5, MERGED))
    assert malformed(proj, stub) == []


def test_1717_a_merge_union_file_never_refuses(proj, stub):
    """REQ-041 (brief #1717 answer 4): a shared-mechanical file is set aside as today."""
    proj.commit({".gitattributes": "src/f0.py merge=union\n"}, "union")
    later_build(stub)
    assert malformed(proj, stub) == []


@pytest.mark.parametrize("key", ["max_touch_glob", "claim_hours"])
def test_1717_a_bad_flow_number_is_refused_naming_the_setting(proj, stub, key):
    """REQ-041 (brief #1717 answer 4): a value below 1 is refused by its name, never the value."""
    flow(proj, f"{key} = 0")
    later_build(stub)
    timeline(stub, 5, (9, 5, MERGED))
    added(stub, 9, "src/f0.py")
    out = plan(proj, stub)
    assert out.returncode != 0
    assert f"{key} of the flow table must be a whole number, 1 or more" in out.stdout + out.stderr


def test_1717_personal_files_mode_reads_no_pull_request_and_keeps_the_refusal(proj, stub):
    """REQ-041 (brief #1717 answer 4, Q-1717-1): no pull request exists to read, so own is empty."""
    proj.write("agk.toml", '[personal]\nforge = "files"\n')
    later_build(stub)
    assert malformed(proj, stub) == [f"MALFORMED: #5 {OWN}"]
