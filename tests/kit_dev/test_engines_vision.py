"""Kit-only tests of `/agk:vision` (SPEC-0029 rule 4; REQ-036 AC3).

`engines.py` writes the owner's idea unchanged as the first section of the vision, lists the ten
discovery questions and checks the vision. The charter must record
all ten topics when the vision has the idea section. No model, no network.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env
from test_playbook import (  # noqa: F401
    GOOD_CHARTER,
    GOOD_VISION,
    check_start,
    failed,
    good_start,
)
from test_playbook import started as playbook_started  # noqa: F401  (wrapped below)


@pytest.fixture
def started(request):
    return request.getfixturevalue("playbook_started")


SCRIPT = KIT_ROOT / "scripts" / "agk" / "engines.py"
IDEA = (
    "I want a small app\nthat keeps my reading list — in *my* words.  \n\n"
    "Two paragraphs, one `code`.\n"
)
TEN = (
    "users",
    "existing",
    "runs",
    "data",
    "scale",
    "compliance",
    "devices",
    "accessibility",
    "languages",
    "brand",
)
ANSWERS = {t: f"answer for {t}" for t in TEN}


def engines(root, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--root", str(root)],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def write_idea(root, idea=IDEA):
    path = root.parent / "idea.txt"
    path.write_text(idea, encoding="utf-8")
    return path


def vision_write(root, idea=IDEA, *extra):
    return engines(root, "vision-write", "--idea-file", str(write_idea(root, idea)), *extra)


def draft_file(root, text=None):
    text = text or GOOD_VISION.replace("# Vision\n\n", "", 1)
    path = root.parent / "draft.md"
    path.write_text(text, encoding="utf-8")
    return path


def vision_text(root):
    return (root / "constitution" / "vision.md").read_text(encoding="utf-8")


# --- the questions -----------------------------------------------------------------------------


def test_ac3_the_discovery_questions_are_the_ten_topics_in_order(tmp_path):
    """REQ-036 AC3: SPEC-0029 rule 4 (users and payer ... brand; the template's own wording)."""
    proc = engines(tmp_path, "questions")
    assert proc.returncode == 0
    lines = proc.stdout.strip().splitlines()
    assert [ln.split("\t")[0] for ln in lines] == list(TEN)
    assert all(len(ln.split("\t")[1]) > 20 and ln.endswith("?") for ln in lines)
    assert "payer" in lines[0] or "pay" in lines[0]


# --- the vision --------------------------------------------------------------------------------


def test_ac3_the_idea_is_the_first_section_unchanged_and_the_four_headings_follow(started):
    """REQ-036 AC3: SPEC-0029 rule 4 (the owner's words, byte for byte, before anything drafted)."""
    proc = vision_write(started, IDEA, "--draft-file", str(draft_file(started)))
    assert proc.returncode == 0, proc.stdout
    text = vision_text(started)
    assert text.startswith("# Vision\n\n## The idea\n")
    assert IDEA.rstrip("\n") in text
    body = text.split("<!-- agk-idea sha256:", 1)[1].split("-->\n\n", 1)[1]
    assert body.split("\n\n<!-- /agk-idea -->")[0] == IDEA.rstrip("\n")
    digest = hashlib.sha256(IDEA.rstrip("\n").encode()).hexdigest()
    assert f"sha256:{digest} -->" in text
    heads = [ln for ln in text.splitlines() if ln.startswith("## ")]
    assert heads[:5] == [
        "## The idea",
        "## What this is for",
        "## Who it serves",
        "## How success is measured",
        "## Out of scope",
    ]
    assert engines(started, "vision-check").stdout == "ok engines-vision\n"


def test_ac3_without_a_draft_the_template_leaves_marked_placeholders_and_the_check_says_so(started):
    """REQ-036 AC3: SPEC-0029 rule 4 (the template drafts nothing the owner did not give)."""
    assert vision_write(started).returncode == 0
    text = vision_text(started)
    assert text.count("TODO(owner)") == 4
    proc = engines(started, "vision-check")
    assert proc.returncode == 1 and "rule 4" in proc.stdout and "not drafted" in proc.stdout


@pytest.mark.parametrize(
    ("idea", "needle"),
    [
        ("", "empty"),
        ("   \n\n", "empty"),
        ("x" * 1501, "1500"),
        ("a\n<!-- /agk-idea -->\nb", "marker"),
    ],
)
def test_ac3_an_idea_that_cannot_be_kept_unchanged_is_refused(started, idea, needle):
    """REQ-036 AC3: SPEC-0029 rule 4 (nothing is written for an idea that cannot be kept)."""
    before = vision_text(started)
    proc = vision_write(started, idea)
    assert proc.returncode == 1 and "rule 4" in proc.stdout and needle in proc.stdout
    assert vision_text(started) == before


@pytest.mark.parametrize(
    ("change", "needle"),
    [
        (lambda t: t.replace("## Who it serves\n\n", ""), "four headings"),
        (lambda t: t.replace("## Out of scope", "## Scope"), "four headings"),
        (lambda t: "## The idea\n\nmine\n\n" + t, "idea"),
        (lambda t: t + "\n<!-- agk-idea sha256:00 -->\n", "idea"),
    ],
)
def test_ac3_a_draft_that_fails_the_template_is_refused(started, change, needle):
    """REQ-036 AC3: SPEC-0029 rule 4 (the draft is written through the template or not at all)."""
    draft = draft_file(started, change(GOOD_VISION.replace("# Vision\n\n", "", 1)))
    before = vision_text(started)
    proc = vision_write(started, IDEA, "--draft-file", str(draft))
    assert proc.returncode == 1 and "rule 4" in proc.stdout and needle in proc.stdout
    assert vision_text(started) == before


def test_ac3_a_vision_that_holds_content_is_never_overwritten(started):
    """REQ-036 AC3: SPEC-0029 rule 4 (an adopted project's real vision is not replaced)."""
    good_start(started)
    before = vision_text(started)
    proc = vision_write(started, IDEA, "--draft-file", str(draft_file(started)))
    assert proc.returncode == 1 and "rule 4" in proc.stdout and "placeholder" in proc.stdout
    assert vision_text(started) == before


def test_ac3_a_missing_vision_file_is_written(started):
    """REQ-036 AC3: SPEC-0029 rule 4 (the file may be absent)."""
    (started / "constitution" / "vision.md").unlink()
    proc = vision_write(started, IDEA, "--draft-file", str(draft_file(started)))
    assert proc.returncode == 0 and vision_text(started).startswith("# Vision\n\n## The idea\n")


@pytest.mark.parametrize("command", ["stack-ids", "stack-write", "stack-check", "nothing"])
def test_ac3_a_step_that_does_not_exist_is_a_usage_error_not_a_pass(started, command):
    """REQ-036 AC3: SPEC-0029 rule 4 (an unbuilt command never prints ok)."""
    proc = engines(started, command)
    assert (
        proc.returncode == 2 and proc.stdout == "" and proc.stderr.startswith("usage: engines.py")
    )


def test_ac3_an_existing_idea_is_never_overwritten(started):
    """REQ-036 AC3: SPEC-0029 rule 4 (the idea is the owner's, written once)."""
    assert vision_write(started, IDEA, "--draft-file", str(draft_file(started))).returncode == 0
    first = vision_text(started)
    proc = vision_write(started, "another idea", "--draft-file", str(draft_file(started)))
    assert proc.returncode == 1 and "rule 4" in proc.stdout
    assert vision_text(started) == first


@pytest.mark.parametrize(
    "change",
    [
        lambda t: t.replace("small app", "big app"),
        lambda t: t.replace("*my*", "my"),
        lambda t: t.replace("<!-- /agk-idea -->", ""),
        lambda t: t.replace("## The idea\n", "## Idea\n"),
        lambda t: t.replace("# Vision\n\n", "# Vision\n\nPreface.\n\n"),
        lambda t: re.sub(r"sha256:[0-9a-f]+", "sha256:" + "0" * 64, t),
    ],
)
def test_ac3_a_vision_whose_first_section_is_not_the_idea_as_given_fails(started, change):
    """REQ-036 AC3: SPEC-0029 rule 4 (a check fails an altered, moved or unmarked idea)."""
    vision_write(started, IDEA, "--draft-file", str(draft_file(started)))
    (started / "constitution" / "vision.md").write_text(change(vision_text(started)))
    proc = engines(started, "vision-check")
    assert proc.returncode == 1 and "rule 4" in proc.stdout and "idea" in proc.stdout
    assert "small app" not in proc.stdout and "reading list" not in proc.stdout


def test_ac3_a_vision_without_the_idea_section_is_not_this_checks_business(started):
    """REQ-036 AC3: SPEC-0029 rule 4 (a vision written by /agk:start alone passes as before)."""
    good_start(started)
    assert engines(started, "vision-check").stdout == "ok engines-vision (no idea section)\n"


# --- the charter records every answer ---------------------------------------------------------


def charter_of(topics, answers=None, slice_lines=()):
    answers = {**ANSWERS, **(answers or {})}
    discovery = "".join(f"   - {t}: {answers[t]}\n" for t in topics)
    text = re.sub(r"   - (?:users|existing|runs|data|scale|compliance): [^\n]*\n", "", GOOD_CHARTER)
    text = text.replace("4. **Discovery**\n", "4. **Discovery**\n" + discovery, 1)
    if slice_lines:
        text = text.replace(
            "\n## Consequences",
            "5. **Slice**\n" + "".join(f"   - {ln}\n" for ln in slice_lines) + "\n## Consequences",
        )
    return text


def idea_start(root, topics=TEN, answers=None, slice_lines=()):
    vision_write(root, IDEA, "--draft-file", str(draft_file(root)))
    (root / "docs" / "adr" / "0002-project-charter.md").write_text(
        charter_of(topics, answers, slice_lines), encoding="utf-8"
    )


def test_ac3_a_start_with_the_idea_section_and_all_ten_answers_passes(started):
    """REQ-036 AC3: SPEC-0029 rule 4 (the charter records every answer)."""
    idea_start(started)
    assert check_start(started).stdout == "ok playbook-start\n"


@pytest.mark.parametrize("topic", TEN[6:])
def test_ac3_a_start_with_the_idea_section_and_a_missing_answer_fails(started, topic):
    """REQ-036 AC3: SPEC-0029 rule 4 (the four new topics are required once the idea is there)."""
    idea_start(started, topics=[t for t in TEN if t != topic])
    out = failed(started, "rule 6")
    assert topic in out


def test_ac3_the_six_topics_alone_are_enough_without_the_idea_section(started):
    """REQ-036 AC3: SPEC-0029 rule 4 (a start without /agk:vision is checked as before)."""
    good_start(started, charter=charter_of(TEN[:6]))
    assert check_start(started).stdout == "ok playbook-start\n"


def test_ac3_not_known_yet_for_a_new_topic_needs_its_slice_line(started):
    """REQ-036 AC3: SPEC-0029 rule 4 (nothing is decided that the owner did not give)."""
    idea_start(started, answers={"brand": "not known yet"})
    out = failed(started, "Slice")
    assert "brand" in out
    idea_start(
        started,
        answers={"brand": "not known yet"},
        slice_lines=["brand: colours would be guessed, so the design waits"],
    )
    assert check_start(started).stdout == "ok playbook-start\n"


def test_ac3_check_start_fails_a_changed_idea(started):
    """REQ-036 AC3: SPEC-0029 rule 4 (the start check runs the vision check)."""
    idea_start(started)
    (started / "constitution" / "vision.md").write_text(
        vision_text(started).replace("small app", "big app")
    )
    failed(started, "idea")


# --- the skills --------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["vision"])
def test_ac3_the_skill_names_the_engine_the_template_and_the_checks(name):
    """REQ-036 AC3: SPEC-0029 rules 3 and 4 (an engine drafts; the owner decides)."""
    text = (KIT_ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith(f"---\nname: {name}\n") and "disable-model-invocation: true" in text
    assert "[engines]" in text and f"`{name}`" in text and "never decides" in text
    assert "engines.py" in text and "check-start" in text
    for verb in ("git push", "git commit", "gh pr", "gh issue"):
        assert verb not in text
    assert "protected" in text and "template" in text


def test_ac3_the_order_message_names_the_count_it_wants(started):
    """REQ-036 AC3: SPEC-0029 rule 4 (six without the idea section, ten with it)."""
    swapped = (TEN[1], TEN[0], *TEN[2:])
    idea_start(started, topics=swapped)
    assert "the ten topics in their order" in failed(started, "rule 6")
    good_start(started, charter=charter_of((TEN[1], TEN[0], *TEN[2:6])))
    assert "the six topics in their order" in failed(started, "rule 6")
