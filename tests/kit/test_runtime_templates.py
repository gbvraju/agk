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
        "Merged-by: merge_cleared.py",
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
    for words in ("session.py kind --brief", "Capacity:", "Started: cb", "agk:handover"):
        assert words in launcher, words
    assert "REST only" in launcher
    conductor = text("conductor.txt")
    assert "<long-run rules>" in conductor
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
