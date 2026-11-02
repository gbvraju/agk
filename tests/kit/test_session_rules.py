"""config/session-rules.md and the role files that point at it (SPEC-0030 rule 1; REQ-037 AC1).

The merge of the rules that say the same thing keeps every number (brief 384, ADR-0243).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "config" / "session-rules.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_ac1_the_rules_file_states_each_rule():
    """REQ-037 AC1"""
    text = read(RULES).lower()
    for phrase in (
        "verdict:",
        "listed verdict author",
        "names its current head",
        "merge of its pull request",
        "ignores every other comment",
        "never merges",
        "tags",
        "auto-merge",
        "posts a verdict",
        "touches a secret",
        "one open pull request",
        "depends-on: #n",
        "make governance",
        "check_final_clearance.py",
        "not the full suite",
        "stops and asks",
        "session.py watch",
    ):
        assert phrase in text, phrase


def test_ac1_the_rules_are_numbered_without_a_gap():
    """REQ-037 AC1"""
    numbers = [int(line.split(".")[0]) for line in read(RULES).splitlines() if line[:1].isdigit()]
    assert numbers == list(range(1, len(numbers) + 1)) and len(numbers) >= 6


def test_ac1_claude_md_and_the_architect_file_point_at_the_rules_file():
    """REQ-037 AC1"""
    for rel in ("CLAUDE.md", ".claude/agents/architect.md"):
        assert "config/session-rules.md" in read(ROOT / rel), rel


def test_ac1_nothing_in_the_operating_rules_contradicts_the_rules_file():
    """REQ-037 AC1: the rules file does not allow what CLAUDE.md forbids."""
    claude = read(ROOT / "CLAUDE.md").lower()
    assert "never merge" in claude and "never poll ci" in claude
    assert "never merges" in read(RULES).lower()


def test_ac8_the_rules_say_how_watch_is_started_so_that_its_end_wakes_the_session():
    """REQ-039 AC8: rule 4 (the Claude Code form; never in the foreground, never detached)."""
    text = " ".join(read(RULES).split())
    assert "run_in_background" in text
    assert "re-invokes the session" in text
    assert "never in the foreground" in text
    assert "`&`" in text and "`nohup`" in text
    assert "exits" in text and "each event is one wake" in text
    assert "session.py queue" in text and "first" in text
    assert "equivalent" in text


def test_ac6_ac7_the_rules_say_reproduce_first_and_what_a_correction_asks():
    """REQ-039 AC6 and AC7: rules 9 and 10 (a measured cause; the correction travels on)."""
    text = " ".join(read(RULES).split())
    assert "to reproduce that cause" in text and "`Measured:`" in text
    assert "`Question:`" in text and "builds nothing" in text
    assert "`Correction:`" in text
    assert "never force-pushes" in text
    assert "one `Report:`" in text
    assert "listed verdict author" in text and "`Correction:` comment" in text


# --- the merged rules (brief 384, ADR-0243) -----------------------------------------------------

ADR = "ADR-0243"
# The rows the person accepted (plan 278): each merged number and the rule that now holds it.
MERGED = {5: 18, 6: 21, 13: 31, 16: 17, 20: 1, 23: 21, 24: 1}
# Row 8: the rules that bind the reporter and the shadow reviewer move to the file of their readers.
MOVED = {
    12: "docs/guides/getting-started.md",
    25: ".claude/agents/shadow.md",
    26: ".claude/agents/shadow.md",
}
# Every rewording of a moved text (answer 1): only a citation of the rule that now holds it.
REWORDED = {
    23: [
        ("follows the five polls of rule 21 and", "follows the five polls above and"),
        (" (rule 21)", ""),
    ],
}

# The text of each merged or moved rule before the change, word for word.
BEFORE = {
    5: (
        "A session finds its next item with `python3 scripts/agk/session.py next --session "
        "ID`, which only shows the brief it would take, posts nothing and prints the "
        "command that takes it; a builder takes a brief only with `python3 "
        "scripts/agk/session.py claim --session ID --brief N`, which posts one comment and "
        "nothing else, or with `next --session ID --take`, which chooses and takes in one "
        "step."
    ),
    6: (
        "A session stops and asks when a brief needs a decision it does not give, or when "
        "a check fails in a way the brief does not cover."
    ),
    12: (
        "A `Report:` line may end with `Usage: <n> tokens`, a whole number, when the "
        "runtime shows the session's own usage. The figure is the usage since the previous "
        "`Report:` of the same pull request, never a running total: a session that can "
        "only read a running total subtracts the total it reported last. The weekly report "
        "sums the figures of a pull request, so a running total would count the early work "
        "several times."
    ),
    13: (
        "A session runs `python3 scripts/agk/session.py push-check` before every push. It "
        "prints the files in which the session's head conflicts with the default branch "
        "and exits 1, or prints nothing. On a conflict the session merges the default "
        "branch first and never rebases or force-pushes."
    ),
    16: (
        "A session puts its questions and its reports on its pull request. A comment whose "
        "first line is `Question: Q-<id> <text>` asks the conductor; a comment whose first "
        "line is `Report: <head> <what changed and the CI>` reports a push. The conductor "
        "answers only by a `Verdict:` comment that names the head, which ends `watch` as "
        "before, and the session restarts `watch` after every push and every event, so no "
        "person carries messages between them."
    ),
    20: (
        "A `Correction:` comment by a listed verdict author, on a pull request or on the "
        "brief it took (the `Brief: #n` line of the pull request body), is acted on like a "
        "verdict, and `python3 scripts/agk/session.py watch --pr N` ends on it. Work built "
        "on a withdrawn cause is already checkpointed on its branch (rule 7); the builder "
        "resets it with one `Report:` saying what was discarded and why, and never "
        "force-pushes."
    ),
    23: (
        "When GitHub cannot be reached at all, a session keeps committing locally, with "
        "its `checkpoint:` steps, and loses nothing. A wait or a push that cannot connect "
        "follows the five polls of rule 21 and then ends with the one line "
        "`github-unreachable: <what failed>; local head <sha> not pushed; next: push, then "
        "post the `Report:`/`Question:``, which is the only channel left; there is no "
        "second one (not mail, not a file drop), and a person reads that line and acts. A "
        "refused push or a 403 on one action is not an outage: GitHub answered, so the "
        "session asks with `Question:` (rule 21). A rate limit is not an outage either: "
        "the session waits until the reset time that GitHub reports, then retries, and "
        "does not end. A session that restarts after an outage runs `python3 "
        "scripts/agk/session.py push-check`, pushes its local commits and posts the "
        "`Report:` or `Question:` it could not post, before anything else; `resume` then "
        "works as today."
    ),
    24: (
        "`python3 scripts/agk/session.py watch --pr N` ends at once, printing the verdict "
        "line, when the latest verdict by a listed verdict author names the current head "
        "of the pull request and is newer than the last `Report:` that the pull request's "
        "author posted; an older verdict on a previous head never ends it. It ends the "
        "same way on a `Correction:` newer than that `Report:`. A verdict that landed "
        "between the push and the start of the watch is therefore never missed. A session "
        "that has already acted on a verdict and only waits for CI or for the merge "
        "restarts the watch with `--since <comment id>`, the id of that verdict as the "
        "line printed it, so that the verdict is not reported again."
    ),
    25: (
        "Only the shadow reviewer posts a `Shadow:` comment, on the one open issue "
        "labelled `agk-shadow`: its first line is `Shadow: #<pr> <sha> cleared|fix "
        "list|rejected`, then numbered findings `S1.`, `S2.` with the path and the line, "
        "in the shape of a fix list. It posts one for every head the conductor gives a "
        "verdict on. The shadow reads the pull request, its checks and its diff and never "
        "the verdict comments of the conductor before it posts, posts no verdict, and "
        "starts, stops or reviews no session."
    ),
    26: (
        "The `Marks:` comment lives on the pull request, after it merges: its first line "
        "is `Marks:`, then one line per finding of the conductor's verdicts and of the "
        "shadow's comments for that pull request, `<C|S><sha7>-<n> right|wrong|both`, "
        "where `C` is a finding of the conductor, `S` of the shadow, `<sha7>` the first "
        "seven characters of the head and `<n>` the number of the finding, and `both` "
        "means the other reviewer raised the same finding and it is right. For the first "
        "ten pull requests after the shadow review starts the maintainer writes the marks, "
        "or at least confirms every `wrong` mark; after that the builder writes them and a "
        "person may change any mark. When the builder has ended before the merge, the "
        "person who merges it writes them, at merge. A reviewer never marks its own "
        "findings, and a pull request without a `Marks:` comment is counted as unmarked: "
        "an unmarked head is `unmarked`, never zero."
    ),
}

SAFETY = {
    2: (
        "A session never merges, never tags, never enables auto-merge, never posts a "
        "verdict and never touches a secret."
    ),
    14: (
        "The shared-mechanical files are the files marked `merge=union` in "
        "`.gitattributes` and `changelog.d/`; the maintainers own this list. "
        "`kit/hashes.json` is a release file that a build never edits, not a file it "
        "resolves."
    ),
    15: (
        "A session resolves only a mechanical conflict: an appended line in a "
        "shared-mechanical file, a file that a kit script regenerates, a number moved by "
        "`intake.py renumber`, and a session rule number moved to the next free one "
        "(`session.py ids` prints it). Any other conflict ends the work: the session posts "
        "one comment `conflict needs a person: <files>` on its pull request and pushes "
        "nothing."
    ),
    22: (
        "A session pushes only the branch its runtime gives it, and opens its pull request "
        "from that branch; a push that is refused for another branch is a block (rule 21), "
        "not a reason to try another name."
    ),
    29: (
        "A session never posts a comment whose first line is `Confirmed:`. In solo mode "
        '(`review_mode = "solo"` in `agk.toml`) that comment is the one person\'s yes: '
        "the verdict, its `Final:` lines and the spec approval of the head it names. The "
        "session prints its exact text (the `Confirmed:` and `Verdict:` lines, the "
        "`Final:` and `Approve:` lines, `Shown:` with the three lines the person was "
        "shown, and `confirmed by <login> in a session at <time>`), and the person posts "
        "it from the browser or the GitHub app. GitHub cannot tell a comment the person "
        "typed from one a session posted under the same account, so this rule and the "
        "conductor's guard are what hold it. After the person's confirmation is on the "
        "pull request, the session may make the `Final:` commit as in rule 4."
    ),
    30: (
        "When GitHub Actions is blocked (minutes exhausted, billing blocked, an outage), a "
        "session follows `docs/guides/local-mode.md`: a builder runs governance and its "
        "own proof on its head under the heavy-step lock, taken with `python3 "
        "scripts/agk/lock.py run --name heavy --session ID -- <command...>`, which waits "
        "its turn and releases the lock when the command ends, and puts one `Local "
        "evidence: <head> ...` line in its pull request body, and a verdict in local mode "
        "names, in one `Local evidence:` line, the local evidence it relied on (the "
        "conductor's own governance run on the head and the builder's line). That local "
        "evidence stands in for CI only while the one local-mode record issue is open, and "
        "only for required checks that never reported on that head. A red check still "
        "blocks a clearing verdict. A session never disables or enables a workflow, "
        "changes the ruleset or merges in local mode; those are a person's."
    ),
    33: (
        "A session runs `git fetch origin <default branch>` and then `python3 "
        "scripts/agk/doctor.py --paused --ref origin/<default branch>` before anything "
        "else, and again on every wake, so that it reads the default branch and not its "
        "own branch, which may predate a pause. When it prints `agk paused` (the top-level "
        "line `paused = true` in `agk.toml`, a protected change with an ADR, ADR-0196), "
        "the kit is paused: the session stops with that one line, posts nothing, claims "
        "nothing, pushes nothing and starts no `watch`. Removing the line resumes the kit, "
        "and the session then starts as after a restart (rule 11); nothing is deleted "
        "while paused. The conductor reads `agk.toml` of the default branch for the same "
        'line with the one GET `gh api -H "Accept: application/vnd.github.raw" '
        "repos/{owner}/{repo}/contents/agk.toml`, which its guard allows."
    ),
}


def numbered() -> dict[int, str]:
    """Each numbered line of the rules file, by its number, without the number."""
    lines = [line for line in read(RULES).splitlines() if line[:1].isdigit()]
    return {int(line.split(".")[0]): line.split(". ", 1)[1] for line in lines}


def flat(text: str) -> str:
    return " ".join(text.split())


def moved_text(number: int) -> str:
    text = BEFORE[number]
    for old, new in REWORDED.get(number, []):
        assert old in text, (number, old)
        text = text.replace(old, new)
    return flat(text)


def test_ac1_every_rule_number_is_kept_without_a_gap():
    """REQ-039: brief 384 answer 2 (no number is reused or dropped)."""
    numbers = [int(line.split(".")[0]) for line in read(RULES).splitlines() if line[:1].isdigit()]
    assert numbers == list(range(1, len(numbers) + 1)) and len(numbers) >= 35


def test_ac1_each_merged_number_is_one_pointer_line_to_a_rule_that_exists():
    """REQ-039: brief 384 answer 2."""
    rules = numbered()
    pointers = set(MERGED) | set(MOVED)
    for number, target in MERGED.items():
        assert rules[number] == f"Merged into rule {target} ({ADR}).", number
        assert target in rules and target not in pointers, number


def test_ac1_each_surviving_rule_holds_the_text_of_the_rules_merged_into_it():
    """REQ-039: brief 384 answers 1 and 5."""
    rules = numbered()
    for number, target in MERGED.items():
        assert moved_text(number) in flat(rules[target]), number


def test_ac1_each_moved_rule_is_a_pointer_line_and_its_file_holds_its_text():
    """REQ-039: brief 384 answer 3."""
    rules = numbered()
    for number, rel in MOVED.items():
        assert rules[number] == f"Moved to `{rel}` ({ADR}).", number
        assert moved_text(number) in flat(read(ROOT / rel)), number


def test_ac1_every_command_and_comment_shape_of_a_merged_rule_is_still_named():
    """REQ-039: brief 384 answer 5 (each command, option and comment shape stays word for word)."""
    rules = numbered()
    for number in BEFORE:
        where = rules[MERGED[number]] if number in MERGED else read(ROOT / MOVED[number])
        for span in re.findall(r"`([^`]+)`", moved_text(number)):
            assert f"`{span}`" in flat(where), (number, span)


def test_ac1_no_rule_cites_a_number_that_is_now_a_pointer():
    """REQ-039: brief 384 answer 2 (a citation in the file names the rule that holds the text)."""
    pointers = set(MERGED) | set(MOVED)
    for number, text in numbered().items():
        if number in pointers:
            continue
        # "`check_pr_mode.py` rule 5" or "SPEC-0030 rule 1" cites another file, not this one.
        cited = {int(n) for n in re.findall(r"(?<!` )(?<!\d )\brules? (\d+)\b", text)}
        assert not cited & pointers, (number, sorted(cited & pointers))


def test_ac1_the_safety_rules_are_unchanged_byte_for_byte():
    """REQ-039: brief 384 answer 4 (merging, secrets, conflicts, branches, confirmation, local
    mode and the pause keep every word)."""
    rules = numbered()
    for number, text in SAFETY.items():
        assert rules[number] == text, number
