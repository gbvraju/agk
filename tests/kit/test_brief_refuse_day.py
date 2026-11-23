"""A brief filed from a day set in agk.toml without its study is refused (brief #1815, ADR-0757).

`[flow] brief_study_fails_from` is the one switch: unset, the study lines warn; a day, a brief
filed on or after it (the issue's `created_at`, else the caller's `today`) fails them in
`check_brief.py` and is MALFORMED in the plan's `session.brief_shape`. No date is written in
`brief_study.py` or `check_brief.py`, and neither reads the live clock, so no check or test
changes on a calendar day. Invented data only (example.com); no network. REQ-037.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import brief_study  # noqa: E402
import check_brief  # noqa: E402
import forge  # noqa: E402
import session  # noqa: E402
from test_check_brief_study import CLASS, PRIOR, SHAPE, STUDIED, tree  # noqa: E402

import config  # noqa: E402

REFUSED = "rule 4: the setting is refused (setting: flow.brief_study_fails_from)"
DAY = "2026-12-14"
BEFORE, AFTER = "2026-12-13", "2026-12-15"
CHILD = "AGK_REFUSE_DAY_CHILD"  # set in the child run of answer 9, so it never runs itself
BRIEF_FILES = (
    "tests/kit/test_check_brief.py",
    "tests/kit/test_adds_clash.py",
    "tests/kit/test_brief_event_check.py",
    "tests/kit/test_plan_render.py",
    "tests/kit/test_personal_two_roots.py",
)


def rooted(tmp_path: Path, setting: str | None = f'"{DAY}"') -> Path:
    root = tree(tmp_path)
    if setting is not None:
        (root / "agk.toml").write_text(f"[flow]\nbrief_study_fails_from = {setting}\n", "utf-8")
    return root


def event(body: str, created: object = None, action: str = "opened") -> dict:
    issue = {"number": 9, "body": body, "labels": [{"name": "agk-brief"}]}
    if created is not None:
        issue["created_at"] = created
    return {"action": action, "issue": issue}


# --- answer 1: the setting ------------------------------------------------------------------------


def test_ac4_unset_is_none_and_the_key_is_known(tmp_path):
    """REQ-037 AC4: answers 1 and 7 (unset: warnings only, today's behaviour)."""
    assert config.brief_study_fails_from(rooted(tmp_path, None)) is None
    assert "brief_study_fails_from" in config.TABLE_KEYS["flow"]
    assert not hasattr(brief_study, "STUDY_FAILS_FROM")


@pytest.mark.parametrize("setting", [DAY, f'"{DAY}"'])
def test_ac4_a_toml_date_or_a_day_string_is_read(tmp_path, setting):
    """REQ-037 AC4: answer 1 (a TOML date or a "YYYY-MM-DD" string, UTC)."""
    assert config.brief_study_fails_from(rooted(tmp_path, setting)) == date(2026, 12, 14)


@pytest.mark.parametrize(
    "setting",
    ["20261214", "true", "2026-12-14T00:00:00", '"2026-12-14T00:00:00Z"', '"2026-13-01"',
     f'["{DAY}"]', '"20261214"', '""'],
)  # fmt: skip
def test_ac4_a_value_outside_its_form_is_refused_naming_the_setting(tmp_path, setting):
    """REQ-037 AC4: answer 7 (refused naming the setting, never the value)."""
    root = rooted(tmp_path, setting)
    with pytest.raises(config.CheckError) as caught:
        config.brief_study_fails_from(root)
    assert str(caught.value) == REFUSED
    (tmp_path / "brief.md").write_text(STUDIED, encoding="utf-8")
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "check_brief.py"), str(tmp_path / "brief.md"), "--root",
         str(root)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert out.returncode == 1 and REFUSED in out.stdout, out.stdout
    assert "2026" not in out.stdout
    with pytest.raises(config.CheckError, match=re.escape(REFUSED)):
        session.brief_shape(root, "example/agk")  # what `session.py plan` and `next` build


# --- answer 2: judged by the day the brief was filed ----------------------------------------------


def test_ac4_enforced_compares_the_filed_day_else_today(tmp_path):
    """REQ-037 AC4: answer 2 (on or after the day; created_at first, else today)."""
    root = rooted(tmp_path)
    assert brief_study.enforced(root, DAY) and brief_study.enforced(root, AFTER)
    assert not brief_study.enforced(root, BEFORE)
    assert not brief_study.enforced(root, AFTER, f"{BEFORE}T23:59:59Z")
    assert brief_study.enforced(root, BEFORE, f"{DAY}T00:00:00Z")
    assert brief_study.enforced(root, AFTER, "not a time")  # unreadable: judged by today
    assert not brief_study.enforced(rooted(tmp_path / "unset", None), "2999-01-01")


# --- answer 3: the brief check --------------------------------------------------------------------


@pytest.mark.parametrize(("today", "fails"), [(BEFORE, False), (DAY, True), (AFTER, True)])
def test_ac4_brief_result_fails_from_the_day_and_warns_before(tmp_path, today, fails):
    """REQ-037 AC4: answer 3 (`check` passes today; the study fails from the day)."""
    root = rooted(tmp_path)
    failures, warnings = check_brief.brief_result(SHAPE, root, today=today)
    if fails:
        assert failures and all(f.startswith("study: ") for f in failures), failures
    else:
        assert failures == [] and any(w.startswith("study: ") for w in warnings)
    assert check_brief.brief_result(STUDIED, root, today=today)[0] == []


def test_ac4_the_cli_takes_today_from_the_pinned_clock(tmp_path, clock):
    """REQ-037 AC4: answer 3 (`FAIL brief: study: ...` from the day; the clock is the pin)."""
    from datetime import UTC, datetime

    root = rooted(tmp_path)
    (tmp_path / "brief.md").write_text(SHAPE, encoding="utf-8")
    command = [sys.executable, str(SCRIPTS / "check_brief.py"), str(tmp_path / "brief.md"),
               "--root", str(root)]  # fmt: skip
    for at, code in ((BEFORE, 0), (DAY, 1)):
        clock.set(datetime.fromisoformat(f"{at}T12:00:00+00:00").astimezone(UTC))
        out = subprocess.run(command, capture_output=True, text=True, check=False)  # nosec B603 - fixed argument list, no shell
        assert out.returncode == code, out.stdout + out.stderr
        assert ("FAIL brief: study: " in out.stdout) == bool(code), out.stdout


@pytest.mark.parametrize(
    ("created", "action", "verdict"),
    [
        (f"{BEFORE}T08:00:00Z", "opened", "pass"),
        (f"{DAY}T08:00:00Z", "opened", "fail"),
        (f"{BEFORE}T08:00:00Z", "edited", "pass"),  # filed before, edited after: warned only
    ],
)
def test_ac4_an_event_is_judged_by_its_created_at(tmp_path, created, action, verdict):
    """REQ-037 AC4: answers 2, 3 and 8 (the event's created_at, whatever the edit)."""
    root = rooted(tmp_path)
    got = check_brief.event_result(event(SHAPE, created, action), root, None, today=AFTER)
    assert got["action"] == verdict, got
    if verdict == "fail":
        assert got["label"] == check_brief.INVALID_LABEL
        assert all(p.startswith("study: ") for p in got["problems"])
    else:
        assert any(w.startswith("study: ") for w in got["warnings"])


def test_ac4_an_event_without_created_at_is_judged_by_today(tmp_path):
    """REQ-037 AC4: answer 8 (no readable created_at: today)."""
    root = rooted(tmp_path)
    assert check_brief.event_result(event(SHAPE), root, None, today=AFTER)["action"] == "fail"
    assert check_brief.event_result(event(SHAPE), root, None, today=BEFORE)["action"] == "pass"


def test_ac4_prior_leaves_out_stays_a_warning_on_every_day(tmp_path):
    """REQ-037 AC4: answer 3 (the `Prior leaves out` lines are never failures)."""
    root = rooted(tmp_path)
    (root / "docs" / "adr" / "0001-tool.md").write_text(
        "# ADR-0001: tool\n\n- Status: Accepted\n\n## Decision\n\nscripts/agk/tool.py\n", "utf-8"
    )
    failures, warnings = check_brief.brief_result(STUDIED, root, today=AFTER)
    assert failures == [] and any("Prior leaves out ADR-0001" in w for w in warnings)


# --- answer 4: the plan stops handing it out ------------------------------------------------------


def test_ac4_brief_shape_refuses_a_brief_filed_from_the_day(tmp_path):
    """REQ-037 AC4: answer 4 (MALFORMED in the plan, skipped by next, with the study line)."""
    root = rooted(tmp_path)
    shape = session.brief_shape(root, "example/agk")
    found = shape(SHAPE, 9, f"{DAY}T08:00:00Z")
    assert found and found[0].startswith("rule 4: study: "), found
    assert shape(SHAPE, 9, f"{BEFORE}T08:00:00Z") == []
    assert shape(STUDIED, 9, f"{DAY}T08:00:00Z") == []
    unset = session.brief_shape(rooted(tmp_path / "unset", None), "example/agk")
    assert unset(SHAPE, 9, f"{DAY}T08:00:00Z") == []


def test_ac4_judge_hands_the_issue_created_at_to_the_shape(tmp_path):
    """REQ-037 AC4: answer 4 (`session.judge` passes the listing's created_at)."""
    seen = []

    def shape(body, number=None, filed=None):
        seen.append((number, filed))
        return ["rule 4: study: x"]

    brief = {"number": 9, "body": SHAPE, "created_at": f"{DAY}T08:00:00Z", "labels": []}
    why, _ = session.judge("example/agk", brief, "me", [], 1, shape, rooted(tmp_path))
    assert why == "rule 4: study: x" and seen == [(9, f"{DAY}T08:00:00Z")]


def test_ac4_what_if_is_judged_by_today(tmp_path, monkeypatch):
    """REQ-037 AC4: answer 2 (a saved file has no created_at: judged by today)."""
    import common

    root = rooted(tmp_path)
    monkeypatch.setattr(common, "utc_day", lambda: AFTER)
    assert session.brief_shape(root, "example/agk")(SHAPE)
    monkeypatch.setattr(common, "utc_day", lambda: BEFORE)
    assert session.brief_shape(root, "example/agk")(SHAPE) == []


# --- answer 5: the router's red-branch brief is held to Class and Prior ---------------------------


def test_ac4_a_priority_0_brief_is_held_to_class_and_prior_only(tmp_path):
    """REQ-037 AC4: answers 5 and 8 (the router's pair is held as any Priority: 0 brief)."""
    import route

    root = rooted(tmp_path)
    red = route.red_body("proof", "9f8e7d6c", "https://example.com/runs/42")
    assert brief_study.held(red) == (True, False)
    assert brief_study.study_result(red, root, today=AFTER) == ([], [])
    for line in ("Prior:", "Class:"):
        cut = "\n".join(x for x in red.splitlines() if not x.startswith(line)) + "\n"
        failed, _ = brief_study.study_result(cut, root, today=AFTER)
        assert any(line in f for f in failed), failed
    zero = SHAPE.replace("Priority: 1", "Priority: 0") + PRIOR + CLASS
    assert brief_study.study_result(zero, root, today=AFTER) == ([], [])


# --- answer 7: personal mode ----------------------------------------------------------------------


def test_ac4_a_sidecar_reads_its_own_day_and_the_files_forge_created_at(tmp_path):
    """REQ-037 AC4: answer 7 (the sidecar's [flow] day, the files forge's created_at)."""
    root = rooted(tmp_path)
    toml = (root / "agk.toml").read_text("utf-8")
    (root / "agk.toml").write_text(f'[personal]\nforge = "files"\n\n{toml}', "utf-8")
    for at, verdict in ((f"{BEFORE}T10:00:00Z", "pass"), (f"{AFTER}T10:00:00Z", "fail")):
        record = forge.FilesForge.base_record(
            SimpleNamespace(now=lambda at=at: at, person="dev"), 9, "t", SHAPE
        )
        record["labels"] = [{"name": "agk-brief"}]
        got = check_brief.event_result({"action": "opened", "issue": record}, root, None)
        assert got["action"] == verdict, got


# --- answer 9: the class stays closed -------------------------------------------------------------


@pytest.mark.parametrize("name", ["brief_study.py", "check_brief.py"])
def test_ac4_no_date_literal_and_no_live_clock_in_the_check(name):
    """REQ-037 AC4: answer 9 (the day only from the setting, today only from the caller)."""
    tree_ = ast.parse((SCRIPTS / name).read_text(encoding="utf-8"))
    dated = re.compile(r"\d{4}-\d{2}-\d{2}")
    found = []
    for node in ast.walk(tree_):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if dated.search(node.value):
                found.append(f"{name}:{node.lineno}: a date literal")
        if isinstance(node, ast.Attribute) and node.attr in ("now", "today", "utcnow"):
            if isinstance(node.value, ast.Name) and node.value.id in ("datetime", "date"):
                found.append(f"{name}:{node.lineno}: reads the live clock")
    assert found == []


_PLUGIN = '''
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, {scripts!r})
import brief_study

_KIT = Path({kit!r}).resolve()
_read = brief_study.brief_study_fails_from


def _kit_day(root):
    """The kit's own agk.toml with the day set to 2000-01-01; every other root as written."""
    if Path(root).resolve() == _KIT:
        return date(2000, 1, 1)
    return _read(root)


brief_study.brief_study_fails_from = _kit_day
'''


@pytest.mark.skipif(bool(os.environ.get(CHILD)), reason="the child run of answer 9")
def test_ac4_the_brief_tests_pass_with_the_kits_day_in_the_past(tmp_path):
    """REQ-037 AC4: answer 9 (the kit's day reaches no test root: each brief test still passes)."""
    plugin = tmp_path / "kit_day_past.py"
    plugin.write_text(_PLUGIN.format(scripts=str(SCRIPTS), kit=str(KIT_ROOT)), encoding="utf-8")
    env = {**os.environ, CHILD: "1", "PYTHONPATH": os.pathsep.join(
        filter(None, [str(tmp_path), os.environ.get("PYTHONPATH")]))}  # fmt: skip
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-m", "pytest", "-q", "-c", "tests/kit/pytest.ini", "-p", "kit_day_past",
         "-p", "no:cacheprovider", *BRIEF_FILES],
        cwd=KIT_ROOT, capture_output=True, text=True, env=env, check=False,
    )  # fmt: skip
    assert out.returncode == 0, out.stdout[-3000:] + out.stderr[-2000:]
    assert " passed" in out.stdout
