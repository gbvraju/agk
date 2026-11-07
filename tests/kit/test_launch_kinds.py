"""Each prompt names its kind, tier and effort; lean prompts for small work; escalation; reviews.

REQ-052 AC3, AC4, AC5 and AC6, brief #709 (build (c) of SPEC-0045 rules 5 to 7, ADR-0289).
`launch.py prompts` reads each plan entry's `kind` (`session.py plan --json` writes it from the
brief by rule 4; none gives `design`, the highest), maps it to a tier and an effort with
`config.model_settings`, and names them in the prompt and the adapter's environment. A `small` or
`mechanical` prompt names only the lean reading list (rule 7); a `build` or `design` prompt keeps
today's reading line byte for byte. A running entry's `escalated_from` restarts it one tier up
(rule 5). Fixtures in `tmp_path`, invented values (example.com), no network."""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
import session_plan

KIT = Path(__file__).resolve().parents[2]
SCRIPT = KIT / "scripts" / "agk" / "launch.py"
SEPARATOR = "-" * 72
FULL = "Read CLAUDE.md and config/session-rules.md first and follow them in full."
LEAN = (
    "CLAUDE.md",
    "constitution/principles.md",
    "config/core-rules.md",
)
ODD = "turbo-x"  # an invented value that a refusal must never echo


def launch(tmp_path: Path, doc: dict, *args: str, toml: str | None = None, env: dict | None = None):
    (tmp_path / "plan.json").write_text(json.dumps(doc), encoding="utf-8")
    if toml is not None:
        (tmp_path / "agk.toml").write_text(toml, encoding="utf-8")
    full = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    full.update(env or {})
    argv = [sys.executable, str(SCRIPT), "prompts", "--plan", str(tmp_path / "plan.json"), *args]
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        argv, capture_output=True, text=True, env=full, cwd=tmp_path, timeout=60
    )


def start(kind: str | None = None, **more) -> dict:
    item = {"session": "builder-a", "brief": 5, "title": "t", **more}
    if kind is not None:
        item["kind"] = kind
    return {"start": [item], "capacity": {"slots": 1}}


def resume(**item) -> dict:
    return {"start": [], "running": [{"session": "builder-a", "brief": 5, **item}]}


def only(out) -> str:
    assert out.returncode == 0, out.stderr
    (text,) = [p for p in out.stdout.split(SEPARATOR + "\n") if p.strip()]
    return text


@pytest.mark.parametrize(
    ("kind", "tier", "effort"),
    [
        (None, "strongest", "high"),
        ("design", "strongest", "high"),
        ("build", "strongest", "medium"),
    ],
)
def test_a_full_prompt_names_its_kind_and_keeps_todays_reading_line(tmp_path, kind, tier, effort):
    """REQ-052 AC5: rule 7, a `build` or `design` prompt reads as today; no kind is `design`."""
    text = only(launch(tmp_path, start(kind)))
    assert f"Kind: {kind or 'design'}; tier: {tier}; effort: {effort}." in text
    assert FULL + "\n" in text.splitlines(keepends=True)[1]
    assert "config/core-rules.md" not in text


def test_a_small_prompt_names_only_the_lean_files(tmp_path):
    """REQ-052 AC5: rule 7, a `small` session reads the lean list, still running its commands."""
    text = only(launch(tmp_path, start("small")))
    assert "Kind: small; tier: mid; effort: low." in text
    assert FULL not in text and "config/session-rules.md first" not in text
    lean = text.splitlines()[1]
    assert all(name in lean for name in LEAN), lean
    assert "doctor.py --paused" in text and "prepush.py" in text


def test_a_mechanical_follow_up_is_lean_and_a_mechanical_start_is_refused(tmp_path):
    """REQ-052 AC2 and AC5: rule 4, `mechanical` is never a brief's kind, only a follow-up's."""
    text = only(launch(tmp_path, resume(kind="mechanical", pull_request=41), "--resume"))
    assert text.count("\n") == 1 and FULL not in text
    assert "Kind: mechanical; tier: mid; effort: low." in text
    assert all(name in text for name in LEAN)
    out = launch(tmp_path, start("mechanical"))
    assert out.returncode == 2 and "(field kind)" in out.stderr


@pytest.mark.parametrize("kind", ["review", ODD, 5, True, ""])
def test_a_kind_outside_the_list_is_refused_naming_the_field_never_the_value(tmp_path, kind):
    """REQ-052 AC2: a malformed kind lowers nothing; it is refused."""
    for doc, args in ((start(kind), ()), (resume(kind=kind), ("--resume",))):
        out = launch(tmp_path, doc, *args)
        assert out.returncode == 2 and "(field kind)" in out.stderr, out.stderr
        assert ODD not in out.stderr and out.stdout == ""


def test_the_projects_table_sets_the_tier_and_a_malformed_one_is_refused(tmp_path):
    """REQ-052 AC1 and AC5: rule 2, the `[models]` table of the checkout decides the tier."""
    text = only(
        launch(
            tmp_path, start("small"), toml='[models]\nsmall = { tier = "fast", effort = "low" }\n'
        )
    )
    assert "Kind: small; tier: fast; effort: low." in text
    out = launch(
        tmp_path, start("small"), toml=f'[models]\nsmall = {{ tier = "{ODD}", effort = "low" }}\n'
    )
    assert out.returncode == 2 and "setting: models.small" in out.stderr
    assert ODD not in out.stderr and out.stdout == ""


def test_a_model_name_is_named_only_from_the_projects_names_table(tmp_path):
    """REQ-052 AC1: rule 3, the tier's model name comes from `[models.names]` alone."""
    toml = (
        '[models]\nsmall = { tier = "fast", effort = "low" }\n'
        '[models.names]\nfast = "example-fast-1"\n'
    )
    assert "model: example-fast-1" in only(launch(tmp_path, start("small"), toml=toml))
    assert "model:" not in only(launch(tmp_path, start("small"), toml=""))


@pytest.fixture
def adapter(tmp_path: Path) -> Path:
    script = tmp_path / "adapter.py"
    script.write_text(
        "import json, os\n"
        "with open(os.environ['ADAPTER_LOG'], 'a') as f:\n"
        "    f.write(json.dumps({k: os.environ.get(k) for k in\n"
        "        ('AGK_KIND', 'AGK_TIER', 'AGK_EFFORT', 'AGK_MODEL')}) + '\\n')\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


def test_the_adapter_gets_the_kind_tier_effort_and_the_projects_model_name(tmp_path, adapter):
    """REQ-052 AC3: answer 2, the conductor starts the session on the adapter for its tier."""
    log = tmp_path / "calls.log"
    toml = '[models.names]\nmid = "example-mid-1"\n'
    out = launch(
        tmp_path,
        start("small"),
        "--adapter",
        f"{sys.executable} {adapter}",
        toml=toml,
        env={"ADAPTER_LOG": str(log)},
    )
    assert out.returncode == 0, out.stderr
    (got,) = [json.loads(x) for x in log.read_text().splitlines()]
    assert got == {
        "AGK_KIND": "small",
        "AGK_TIER": "mid",
        "AGK_EFFORT": "low",
        "AGK_MODEL": "example-mid-1",
    }


@pytest.mark.parametrize(
    ("kind", "was", "tier", "effort"),
    [
        ("small", "fast", "mid", "medium"),
        ("small", "mid", "strongest", "medium"),
        ("mechanical", "mid", "strongest", "medium"),
        ("build", "fast", "strongest", "medium"),  # never below the kind's own tier
        ("design", "mid", "strongest", "high"),  # never below the kind's own effort
    ],
)
def test_an_escalation_restarts_one_tier_up_on_the_same_pull_request(
    tmp_path, kind, was, tier, effort
):
    """REQ-052 AC3: rule 5, one tier up, at least `build`'s effort, same branch and pull request."""
    text = only(
        launch(tmp_path, resume(kind=kind, pull_request=41, escalated_from=was), "--resume")
    )
    assert f"tier: {tier}; effort: {effort}." in text
    assert "resume --pr 41" in text and "never open a second one" in text


@pytest.mark.parametrize("was", ["strongest", ODD, 3])
def test_no_escalation_from_strongest_or_from_a_tier_outside_the_list(tmp_path, was):
    """REQ-052 AC3: rule 5, a builder on `strongest` asks with `Question:`; it never escalates."""
    out = launch(tmp_path, resume(kind="small", pull_request=41, escalated_from=was), "--resume")
    assert out.returncode == 2 and "(field escalated_from)" in out.stderr
    assert ODD not in out.stderr
    out = launch(tmp_path, start("small", escalated_from="fast"))
    assert out.returncode == 2 and "(field escalated_from)" in out.stderr


def test_a_prompt_below_strongest_names_the_escalation_stop_and_one_on_strongest_asks(tmp_path):
    """REQ-052 AC3: rule 5, the three stops, the `Report:` line, and `Question:` on `strongest`."""
    low = only(launch(tmp_path, start("small")))
    assert "Report: <head> escalate <reason>" in low and "session rule 21" in low
    high = only(launch(tmp_path, start("build")))
    assert "Report: <head> escalate" not in high and "Question:" in high


def test_the_plan_writes_each_briefs_kind_from_its_size_and_touches():
    """REQ-052 AC2: rule 4, `session.py plan --json` names the kind; it is only raised."""
    protected = ["scripts/agk/", "tests/kit/", "agk.toml"]
    small = {"number": 5, "title": "t", "body": "Size: S\nTouches: tests/kit/test_x.py\n"}
    build = {
        "number": 6,
        "title": "u",
        "body": "Size: M\nTouches: scripts/agk/x.py\n",
        "build": "b",
    }
    unread = {"number": 7, "title": "v", "body": None}
    assert session_plan.start_entry("b1", small, protected) == {
        "session": "b1",
        "brief": 5,
        "title": "t",
        "kind": "small",
    }
    assert session_plan.start_entry("b2", build, protected)["kind"] == "design"  # may match a guard
    assert session_plan.start_entry("b2", build, protected)["build"] == "b"
    assert session_plan.start_entry("b3", unread, protected)["kind"] == "design"
    flat = {"number": 8, "title": "w", "body": "Size: M\nTouches: tests/kit/test_y.py\n"}
    assert session_plan.start_entry("b4", flat, protected)["kind"] == "build"


# --- the instructions (rules 5 to 7) ---------------------------------------------------------


def read(rel: str) -> str:
    return " ".join((KIT / rel).read_text(encoding="utf-8").split())


def test_the_session_rules_name_the_escalation_stop():
    """REQ-052 AC3: rule 5 in session rule 21, the three stops, one tier up, `Question:` on top."""
    rule = next(
        x
        for x in (KIT / "config/session-rules.md").read_text().splitlines()
        if x.startswith("21. ")
    )
    for words in (
        "below `strongest`",
        "the same check fails in two runs in a row",
        "a conflict it cannot resolve",
        "a protected class its brief's `Touches:` does not name",
        "`Report: <head> escalate <reason>`",
        "one tier up on the same branch and pull request",
        "on `strongest` it asks",
    ):
        assert words in rule, words


def test_the_core_rules_page_names_the_lean_reading_list():
    """REQ-052 AC5: rule 7, a lean session reads the page, the constitution and its brief."""
    page = read("config/core-rules.md")
    assert "A `small` or `mechanical` session reads only" in page
    assert all(f"`{name}`" in page or name == "config/core-rules.md" for name in LEAN)
    assert "`session rule 33`" in page and "`session rule 31`" in page
    assert "escalate" in page


REVIEW_AGENTS = ("conductor", "architect", "architect-review", "reviewer", "shadow")


@pytest.mark.parametrize("name", REVIEW_AGENTS)
def test_every_review_agent_runs_on_strongest_at_high(name):
    """REQ-052 AC4: rule 6, a review never runs below `strongest` at `high`."""
    assert "the `strongest` tier at `high` effort" in read(f".claude/agents/{name}.md")


def test_the_conductor_reads_the_kind_escalates_and_names_the_re_review_diff():
    """REQ-052 AC3, AC4 and AC6: answer 2 and rule 6."""
    text = read(".claude/agents/conductor.md")
    for words in (
        "`kind`",
        "`escalated_from`",
        "one tier up",
        "raise a kind, never lower it",
        "the diff from the head its last verdict named",
        "not an ancestor of the new head",
        "a merge of the default branch changed a file of the pull request's own diff",
        "a first review reads the whole diff",
    ):
        assert words in text, words


def test_no_gate_reads_the_kind():
    """REQ-052 AC4: rule 1, no check, test list or gate differs between kinds."""
    for name in (
        "prepush.py",
        "test_plan.py",
        "check_pr_body.py",
        "governance.py",
        "merge_cleared.py",
    ):
        path = KIT / "scripts" / "agk" / name
        if path.is_file():
            body = path.read_text(encoding="utf-8")
            assert not re.search(r"model_settings|kind_of|AGK_KIND|AGK_TIER", body), name


def test_launch_holds_no_model_name():
    """REQ-052 AC1: rule 3, the kit's script names tiers, never a model."""
    body = SCRIPT.read_text(encoding="utf-8")
    assert "strongest" in body and "[models.names]" in body
    assert not re.search(r'"[a-z]+-\d', body)
