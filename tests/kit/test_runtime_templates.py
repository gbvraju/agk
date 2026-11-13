"""The round-the-clock task texts ship as templates (brief #1117, ADR-0477; REQ-039).

`kit/templates/runtime/` holds the texts of the conductor, launcher and builder tasks a project
sets up in its own runtime, and one README; `docs/guides/getting-started.md` names each of them.
The kit installs and starts none of them (answer 3). Reads tracked files only; no network."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = "kit/templates/runtime"
TEXTS = ("conductor.txt", "launcher.txt", "builder.txt")
FILES = (*TEXTS, "README.md")
PATHS = (
    "kit/templates/runtime/conductor.txt",
    "kit/templates/runtime/launcher.txt",
    "kit/templates/runtime/builder.txt",
    "kit/templates/runtime/README.md",
)
GUIDE = ROOT / "docs" / "guides" / "getting-started.md"

# Answer 1: no repository name, no person's name, no date, no scheduled-task id.
NOT_GENERIC = [
    r"gbvraju",
    r"github\.com/(?!<owner>/<repo>)\S",
    r"\b(?!scripts/)[\w.-]+/agk(?![\w/-])",
    r"\b20\d\d-\d\d-\d\d\b",
    r"\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\b",
    r"\b\d{1,2}:\d\d ?(?:IST|UTC|Z)\b",
    r"\btrig_\w+",
    r"(?<![\w`])@[A-Za-z][\w-]+",
    r"\bco-owner\b",
]


def text(name: str) -> str:
    return (ROOT / RUNTIME / name).read_text(encoding="utf-8")


def test_a_the_four_templates_exist_and_the_readme_lists_the_three_texts():
    """REQ-039: answer 4 (a): the four files, listed by the folder's README."""
    for name in FILES:
        assert (ROOT / RUNTIME / name).is_file(), name
    readme = text("README.md")
    for name in TEXTS:
        assert f"`{name}`" in readme, name


def test_a_the_kit_installs_none_of_them():
    """REQ-039: answer 3: nothing is installed or started by the kit; the texts stay kit-side."""
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    listed = [
        *manifest["verbatim"],
        *manifest["experimental"],
        *manifest["templates"],
        *manifest["templates"].values(),
        *manifest["adopt"]["templates"].values(),
    ]
    assert not [p for p in listed if p.startswith(RUNTIME)]


def test_b_no_template_names_a_repository_a_person_or_a_date():
    """REQ-039: answer 4 (b): every text is generic, with `<owner>/<repo>` placeholders."""
    for name in FILES:
        body = text(name)
        for pattern in NOT_GENERIC:
            assert not re.search(pattern, body), (name, pattern)
    for name in TEXTS:
        assert "<owner>/<repo>" in text(name), name


def test_b_the_check_catches_a_named_repository_a_date_and_a_handle():
    """REQ-039: answer 4 (b): the patterns of the check refuse invented specific text."""
    for bad in (
        "Repository: example-org/agk.",
        "clone https://github.com/example-org/demo",
        "(owner, 2030-01-02 09:00)",
        "as on 3 Nov",
        "ping @example-person",
        "fire trig_0123abc",
    ):
        assert any(re.search(p, bad) for p in NOT_GENERIC), bad
    assert not any(re.search(p, "Repository: <owner>/<repo>.") for p in NOT_GENERIC)


def test_c_the_builder_text_carries_every_rule_by_its_first_words():
    """REQ-039: answer 4 (c): LIFETIME, hand-over, final lines, maintainers, the tiers."""
    body = text("builder.txt")
    for words in (
        "LIFETIME",
        "HANDING OVER",
        "Report: <head> handing over:",
        "FINAL LINES",
        "Merged-by: ",
        "for the maintainers",
        "TOKEN RULE",
        "Secret-scan: deferred to CI",
        "ESCALATION",
        "LEAN READING",
    ):
        assert words in body, words
    tier = [ln for ln in body.splitlines() if ln.startswith("Tier:")]
    assert len(tier) == 1 and "strongest" in tier[0] and "mid" in tier[0], tier
    for kind in ("design", "build", "small", "mechanical"):
        assert kind in tier[0], kind


def test_c_the_launcher_and_conductor_texts_keep_their_rules():
    """REQ-039: answer 1: the launcher's steps and the conductor's placeholder for its long run."""
    launcher = text("launcher.txt")
    for words in ("kind --brief N", "Capacity:", "Started: cb", "agk:handover"):
        assert words in launcher, words
    assert "REST only" in launcher
    conductor = text("conductor.txt")
    assert ".claude/agents/conductor.md" in conductor


def test_d_the_guide_names_every_template_and_both_ways_to_wait():
    """REQ-039: answer 4 (d) and answer 2: the section, each template, foreground and background."""
    guide = GUIDE.read_text(encoding="utf-8")
    assert "Running around the clock" in guide
    section = guide.split("Running around the clock", 1)[1].split("\n8. ", 1)[0]
    assert PATHS == tuple(f"{RUNTIME}/{name}" for name in FILES)
    for path in PATHS:
        assert path in section, path
    for words in ("foreground", "background", "for the maintainers", "/agk:launch"):
        assert words in section, words
    assert "30 minutes" in section and "12 hours" in section


# Brief #1202 (ADR-0510): the texts match the running autopilot.


def last_paragraph(name: str) -> str:
    return [p for p in text(name).strip().split("\n\n") if p.strip()][-1]


def test_1202_a_the_conductor_text_holds_no_long_run_placeholder():
    """REQ-039: brief #1202 answer 4 (a): the `<long-run rules>` line is replaced by the rules."""
    conductor = text("conductor.txt")
    assert "<long-run rules>" not in conductor
    assert not [ln for ln in conductor.splitlines() if ln.strip() == "<long-run rules>"]
    readme = text("README.md")
    assert "<long-run rules>" not in readme


def test_1202_b_the_conductor_starts_builders_within_the_limits():
    """REQ-039: brief #1202 answer 4 (b) and answer 1: both builder tasks, `Started: cb`, limits."""
    conductor = text("conductor.txt")
    for words in (
        "<mid builder task>",
        "<strongest builder task>",
        "kind: small",
        "START #<brief>",
        "Started: cb<brief> <UTC time> by the conductor (<kind>)",
        "Session name: cb<brief>[<build letter>]. Item: brief #<brief>[ build (<x>)].",
        "2 hours",
        "Capacity:",
        "cb<brief>r",
        "agk:handover",
        "45 minutes",
        "Owner needed:",
        "<plan issue>",
        "merger.yml",
    ):
        assert words in conductor, words
    six = [ln for ln in conductor.splitlines() if ln.startswith("6. ")]
    assert len(six) == 1 and "START" in six[0], six


def test_1202_c_the_conductor_may_fire_only_the_builder_tasks():
    """REQ-039: brief #1202 answer 4 (c): the last paragraph allows only firing builder tasks."""
    last = last_paragraph("conductor.txt")
    assert (
        "never create, change or delete a scheduled task; firing the two builder tasks is the "
        "only scheduled-task action allowed" in last
    ), last
    assert "conductor task" not in last


def test_1202_d_the_launcher_is_the_backup_at_45_minutes():
    """REQ-039: brief #1202 answer 4 (d) and answer 2: 45 minutes of silence, not 90; a backup."""
    launcher = text("launcher.txt")
    assert "45 minutes" in launcher
    assert "90 minutes" not in launcher
    assert "backup" in launcher
    tasks = ("<mid builder task>", "<strongest builder task>", "<conductor task>", "<plan issue>")
    for words in tasks:
        assert words in launcher, words


def test_1202_e_the_builder_text_carries_the_running_rules():
    """REQ-039: brief #1202 answer 4 (e) and answer 2: hand-over, CI red, Finishes, testing map."""
    body = text("builder.txt")
    for words in (
        "Before you start work on an open pull request",
        "On a red `governance` or `proof` on your head",
        "Finishes: #<N>",
        "[[testing.map]]",
        "On an `Answer:`, `Correction:` or `Maintainer answer:`",
        "a merge of main without a conflict, a status or body fix",
    ):
        assert words in body, words
    kit_only = "Kit repository only (where kit/agk-kit.mk exists):"
    assert body.count(kit_only) == 1, kit_only
    tail = body.split(kit_only, 1)[1]
    for words in ("ALWAYS ALSO", "RELEASE EXCEPTION", "kit_hashes.py", "changelog.d"):
        assert words in tail, words
        assert words not in body.split(kit_only, 1)[0], words


def test_1202_f_the_readme_and_guide_say_the_launcher_is_the_backup():
    """REQ-039: brief #1202 answer 3: the conductor starts builders; the launcher is its backup."""
    readme = text("README.md")
    assert "starts builders itself" in readme and "backup" in readme
    guide = GUIDE.read_text(encoding="utf-8")
    section = guide.split("Running around the clock", 1)[1].split("\n8. ", 1)[0]
    assert "starts builders itself" in section and "backup" in section
