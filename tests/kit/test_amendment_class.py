"""Each amendment item carries a class; the steward settles only a correction or an implementation.

Brief #1957 (ADR-0813) answers 1, 2, 4, 6, 7 and 9: an item's `Class:` line, the one tuple of
what makes an item `behaviour`, the settle step with a reviewer's agreement, the override share
and the `[steward] settle_amendments` setting, refused naming principle 6 until it is applied.
Files only; invented data, no network.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import check_amendments as ca  # noqa: E402

from config import StewardSettingError, steward_settings  # noqa: E402

SPEC = "docs/specs/0072-example-spec.md"
NOW = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


def project(root: Path, on: bool | None = None, principle: bool = True) -> Path:
    toml = 'default_branch = "main"\nreview_mode = "solo"\n'
    if on is not None:
        toml += f"[steward]\nsettle_amendments = {'true' if on else 'false'}\n"
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    (root / "constitution").mkdir(exist_ok=True)
    six = "6. Approved specs are owned by a reviewer group; agents propose patches"
    six += f"; {ca.PRINCIPLE_CLAUSE}.\n" if principle else ".\n"
    (root / "constitution" / "principles.md").write_text(f"# Principles\n\n{six}", "utf-8")
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "reviewers.yaml").write_text(
        'version: 1\nverdict_authors: ["@boss"]\nspec_approvers: ["@owner"]\n', encoding="utf-8"
    )
    (root / "docs" / "specs").mkdir(parents=True, exist_ok=True)
    (root / SPEC).write_text("# SPEC-0072: Example\n\n- Status: Approved\n", encoding="utf-8")
    return root


def amendment(*items: str) -> str:
    body = "\n".join(f"{i}. **SPEC-0072 rule 4.** {text}" for i, text in enumerate(items, 1))
    head = "# Proposed spec amendments 900 (SPEC-0072; REQ-079)\n\nVia a proposal (principle 6)."
    return f"{head}\n\n## Items\n\n{body}\n"


CORRECTION = "The pins step reads each lock as rule 4 says.\n   Class: correction"
IMPLEMENTATION = "Reuse `config.py` for the read.\n   Class: implementation"


def test_req066_classes_are_read_and_behaviour_is_the_default(tmp_path):
    root = project(tmp_path, on=True)
    text = amendment(CORRECTION, IMPLEMENTATION, "Reword the table.", "x\n   Class: behaviour")
    found = [(n, ca.item_class(t, root)[0]) for n, t in ca.items(text)]
    assert found == [(1, "correction"), (2, "implementation"), (3, "behaviour"), (4, "behaviour")]


@pytest.mark.parametrize(
    "item",
    [
        "Adds a setting `[pins] strict` the rule reads.\n   Class: correction",
        "A new gate before the merge.\n   Class: implementation",
        "Adds a label for the router.\n   Class: correction",
        "Gives the steward the authority to file.\n   Class: correction",
        "The intake asks one more question.\n   Class: correction",
        "Corrects the read, naming no rule.\n   Class: correction".replace("SPEC", "x"),
    ],
)
def test_req066_a_marked_item_is_behaviour_whatever_its_line_says(tmp_path, item):
    root = project(tmp_path, on=True)
    text = amendment(item)
    if "naming no rule" in item:
        text = text.replace("SPEC-0072 rule 4", "the pins step")
    ((_, body),) = ca.items(text)
    assert ca.item_class(body, root)[0] == "behaviour"
    problems = ca.file_problems("docs/runs/proposed-spec-amendments-900.md", text, root)
    assert problems and "ADR-0813 answer 1" in problems[0] and "`[pins]" not in problems[0]


def test_req066_a_correction_of_a_rule_not_approved_is_behaviour(tmp_path):
    root = project(tmp_path, on=True)
    (root / SPEC).write_text("# SPEC-0072\n\n- Status: Draft\n", encoding="utf-8")
    ((_, body),) = ca.items(amendment(CORRECTION))
    assert ca.item_class(body, root)[0] == "behaviour"


def test_req066_an_item_without_a_class_line_fails_the_check(tmp_path):
    root = project(tmp_path, on=True)
    problems = ca.file_problems("x-900.md", amendment(CORRECTION, "Reword it."), root)
    assert problems == ["x-900.md item 2: no Class line (ADR-0813 answer 1)"]


def test_req066_with_the_setting_on_and_agreement_a_settled_line(tmp_path):
    root = project(tmp_path, on=True)
    found = ca.settle(900, amendment(CORRECTION, IMPLEMENTATION), root, "pins.py:41", True, now=NOW)
    first = found.splitlines()[0]
    assert ca.SETTLED.fullmatch(first), first
    assert found.splitlines()[1] == f"Text: {ca.digest(amendment(CORRECTION, IMPLEMENTATION))}"
    assert first.startswith("Answer: amendment 900 settled (evidence: pins.py:41; class: ")
    assert "rule: SPEC-0072 rule 4)" in first and found.rstrip().endswith(ca.WHO)


@pytest.mark.parametrize(
    "case",
    ["off", "unset", "disagree", "behaviour", "intake", "missing", "principle", "paused"],
)
def test_req066_each_other_case_goes_to_the_owner(tmp_path, case):
    on = {"off": False, "unset": None}.get(case, True)
    root = project(tmp_path, on=on)
    items = {
        "behaviour": (CORRECTION, "Adds a setting.\n   Class: behaviour"),
        "missing": (CORRECTION, "Reword it."),
        "principle": ("Changes principle 6 as rule 4 says.\n   Class: correction",),
    }.get(case, (CORRECTION,))
    if case == "paused":
        text = (root / "agk.toml").read_text(encoding="utf-8")
        (root / "agk.toml").write_text("paused = true\n" + text, encoding="utf-8")
    found = ca.settle(
        900, amendment(*items), root, "pins.py:41", case != "disagree", case == "intake", now=NOW
    )
    assert found is None


def test_req066_two_overrides_in_seven_days_stop_that_class(tmp_path):
    root = project(tmp_path, on=True)
    two = [("correction", NOW - timedelta(days=1)), ("correction", NOW - timedelta(days=6))]
    text = amendment(CORRECTION)
    assert ca.settle(900, text, root, "e", True, overrides=two, now=NOW) is None
    old = [("correction", NOW - timedelta(days=1)), ("correction", NOW - timedelta(days=8))]
    assert ca.settle(900, text, root, "e", True, overrides=old, now=NOW) is not None
    other = [("implementation", NOW - timedelta(days=1))] * 2
    assert ca.settle(900, text, root, "e", True, overrides=other, now=NOW) is not None


def test_req066_an_owner_answer_after_a_settled_line_is_an_override():
    settled = ca.SETTLED_FORM.format(900, "e", "correction", "SPEC-0072 rule 4")
    comments = [
        {
            "user": {"login": "owner"},
            "body": f"{settled}\n\n{ca.WHO}",
            "created_at": "2026-11-24T10:00:00Z",
        },
        {
            "user": {"login": "owner"},
            "body": "Maintainer answer: amendment 900 not approved",
            "created_at": "2026-11-24T11:00:00Z",
        },
        {
            "user": {"login": "owner"},
            "body": "Correction: amendment 901 is wrong",
            "created_at": "2026-11-24T12:00:00Z",
        },
    ]
    assert ca.overrides(comments) == [("correction", datetime(2026, 11, 24, 11, tzinfo=UTC))]


def test_req066_the_setting_is_read_and_refused_naming_it(tmp_path):
    from config import settle_refusal

    root = project(tmp_path)
    assert steward_settings(root)["settle_amendments"] is False
    assert steward_settings(project(tmp_path, on=True))["settle_amendments"] is True
    for value in ("1", "'yes'", "0"):
        (root / "agk.toml").write_text(f"[steward]\nsettle_amendments = {value}\n", "utf-8")
        with pytest.raises(StewardSettingError) as caught:
            steward_settings(root)
        assert "setting: steward.settle_amendments" in str(caught.value)
        assert "yes" not in str(caught.value)
    project(tmp_path, on=True, principle=False)
    with (root / "agk.toml").open("a", encoding="utf-8") as handle:
        handle.write("auto_file = 2\nfix_briefs = true\n")
    found = steward_settings(root)  # fix list item 5: only settle_amendments is refused
    assert found == {"auto_file": 2, "fix_briefs": True, "settle_amendments": False}
    assert "principle 6" in (settle_refusal(root) or "")
    assert "steward.settle_amendments" in (settle_refusal(root) or "")
    assert settle_refusal(project(tmp_path, on=True)) is None
    project(tmp_path, on=True, principle=False)
    assert ca.settle_on(root) is False


def test_req066_a_team_without_spec_approvers_reads_the_setting_off(tmp_path):
    root = project(tmp_path, on=True)
    (root / "config" / "reviewers.yaml").write_text(
        'version: 1\nverdict_authors: ["@boss"]\nspec_approvers: []\n', "utf-8"
    )
    assert ca.settle_on(root) is False


def run_settle(root: Path, *extra: str) -> subprocess.CompletedProcess:
    argv = [sys.executable, str(SCRIPTS / "check_amendments.py"), "settle", *extra]
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        argv, cwd=root, capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"}, check=False
    )


def command_project(tmp_path: Path, comments: object = ()) -> tuple[Path, str]:
    root = project(tmp_path, on=True)
    path = root / "docs" / "runs" / "proposed-spec-amendments-900.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(amendment(CORRECTION), encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607 - fixed list
    saved = tmp_path / "comments.json"
    saved.write_text(
        json.dumps(list(comments) if isinstance(comments, tuple) else comments), "utf-8"
    )
    return root, str(saved)


def test_req066_the_command_prints_and_posts_nothing(tmp_path):
    root, saved = command_project(tmp_path)
    args = ("--amendment", "900", "--evidence", "pins.py:41", "--comments", saved, "--agreed")
    proc = run_settle(root, *args, "yes")
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.startswith("Answer: amendment 900 settled (evidence: pins.py:41;")
    text = (root / "docs/runs/proposed-spec-amendments-900.md").read_text(encoding="utf-8")
    assert f"\nText: {ca.digest(text)}\n" in proc.stdout
    proc = run_settle(root, *args, "no")
    assert proc.returncode == 1 and proc.stdout.startswith("owner: amendment 900")
    for bad in ("\u00b2", "9x"):  # fix list item 6: ASCII digits only, never a traceback
        proc = run_settle(root, "--amendment", bad, *args[2:], "yes")
        assert proc.returncode == 2 and proc.stdout.startswith("usage:"), bad
    assert run_settle(root, *args[:4], "--agreed", "yes").returncode == 2  # no --comments


def test_req066_the_command_reads_the_overrides_from_the_comments(tmp_path):
    settled = ca.SETTLED_FORM.format(800, "e", "correction", "SPEC-0072 rule 4")
    now = datetime.now(UTC)
    stamp = [(now - timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ") for h in (3, 2, 1)]
    comments = [
        {"user": {"login": "owner"}, "body": f"{settled}\n\n{ca.WHO}", "created_at": stamp[0]},
        {"user": {"login": "owner"}, "body": "Correction: amendment 800", "created_at": stamp[1]},
        {
            "user": {"login": "owner"},
            "body": "Maintainer answer: amendment 800 no",
            "created_at": stamp[2],
        },
    ]
    root, saved = command_project(tmp_path, comments)
    args = ("--amendment", "900", "--evidence", "e", "--comments", saved, "--agreed", "yes")
    proc = run_settle(root, *args)
    assert proc.returncode == 1 and proc.stdout.startswith("owner: amendment 900"), proc.stdout
    for broken in ([{"body": "x"}], {"not": "a list"}, [1]):  # fix list item 3: refused, named
        root, saved = command_project(tmp_path, broken)
        proc = run_settle(
            root, "--amendment", "900", "--evidence", "e", "--comments", saved, "--agreed", "yes"
        )
        assert proc.returncode == 1 and proc.stdout.startswith("FAIL amendments:"), proc.stdout
        assert "Traceback" not in proc.stdout + proc.stderr


def test_req066_the_command_names_principle_6_until_it_is_applied(tmp_path):
    root, saved = command_project(tmp_path)
    project(root, on=True, principle=False)
    proc = run_settle(
        root, "--amendment", "900", "--evidence", "e", "--comments", saved, "--agreed", "yes"
    )
    assert proc.returncode == 1 and "principle 6" in proc.stdout


def test_req066_a_file_that_is_not_utf8_is_named_never_a_traceback(tmp_path):
    root, saved = command_project(tmp_path)
    path = "docs/runs/proposed-spec-amendments-900.md"
    (root / path).write_bytes(b"1. \xff\xfe Class: correction\n")
    assert ca.added_problems(root, [(900, path)]) == [
        f"{path}: not readable UTF-8 text (ADR-0813 answer 1)"
    ]
    proc = run_settle(
        root, "--amendment", "900", "--evidence", "e", "--comments", saved, "--agreed", "yes"
    )
    assert proc.returncode == 1 and "path class docs/runs/" in proc.stdout
    assert "Traceback" not in proc.stdout + proc.stderr


def test_req066_settleable_and_digests_read_the_text_at_hand(tmp_path):
    root = project(tmp_path, on=True)
    good, bad = amendment(CORRECTION), amendment(CORRECTION, "Adds a step.\n   Class: behaviour")
    found = ca.digests({"amendment 1": good, "amendment 2": bad, "amendment 3": None}, root)
    assert found == {"amendment 1": ca.digest(good)}
    owner = amendment("Changes principle 6 as SPEC-0072 rule 4 says.\n   Class: correction")
    assert not ca.settleable(owner, root)


def test_req066_the_shipped_amendments_carry_their_class():
    root = SCRIPTS.parents[1]
    for number in (251, 252):
        name = f"docs/runs/proposed-spec-amendments-{number}.md"
        text = (root / name).read_text(encoding="utf-8")
        assert ca.file_problems(name, text, root) == []


def test_req066_the_guard_allows_the_settled_line_only_with_the_setting_on(tmp_path):
    hook = SCRIPTS.parents[1] / ".claude" / "hooks" / "steward_guard.py"
    line = ca.SETTLED_FORM.format(900, "pins.py:41", "correction", "SPEC-0072 rule 4")

    def decide(root: Path, text: str) -> dict | None:
        (root / "body.md").write_text(text, encoding="utf-8")
        command = f"gh api --method POST repos/o/r/issues/9/comments -F body=@{root / 'body.md'}"
        payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(root)}
        proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(hook)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(root)},
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)["hookSpecificOutput"] if proc.stdout.strip() else None

    root, _ = command_project(tmp_path)
    path = root / "docs/runs/proposed-spec-amendments-900.md"
    good = f"{line}\nText: {ca.digest(path.read_text(encoding='utf-8'))}\n\n{ca.WHO}\n"
    assert decide(root, good) is None
    for bad in (
        f"{line}\n\n{ca.WHO}\n",  # no Text line
        f"{line}\nText: {'0' * 16}\n\n{ca.WHO}\n",  # another text
        f"{line}\n",
        "Answer: amendment 900 settled\n\nWho: AGK steward\n",
        "Approve: SPEC-0072\n",
        "Maintainer answer: amendment 900 approved\n",
    ):
        found = decide(root, bad)
        assert found is not None and found["permissionDecision"] == "deny", bad
    path.write_text(amendment("Adds a step.\n   Class: behaviour"), encoding="utf-8")
    behaviour = f"{line}\nText: {ca.digest(path.read_text(encoding='utf-8'))}\n\n{ca.WHO}\n"
    assert decide(root, behaviour)["permissionDecision"] == "deny"  # fix list item 2
    path.write_text(amendment(CORRECTION), encoding="utf-8")
    project(root, on=False)
    found = decide(root, good)
    assert found is not None and "steward.settle_amendments" in found["permissionDecisionReason"]


# --- brief #2002 (ADR-0828): a brief's quoted items are read and classed as a file's -------------

FILE_254 = Path(__file__).resolve().parents[2] / "docs" / "runs" / "proposed-spec-amendments-254.md"


def test_req066_2002_quoted_items_are_read_and_classed_as_a_file(tmp_path):
    """REQ-066: brief #2002 answer 1: the `> ` removed, `items` and `item_class` read the quote."""
    lines = ["Spec fit: SPEC-0072 rule 1 change by amendment 254",
             "> 1. **SPEC-0072 rule 1.** Append \"x\" (amendment 254).", "> Class: behaviour",
             "> 2. **SPEC-0072 rule 1.** Append \"y\".", "Size: M"]  # fmt: skip
    text = ca.quoted_items(lines, 0)
    assert [n for n, _ in ca.items(text)] == [1, 2]
    assert ca.file_problems("Spec fit: SPEC-0072", text, tmp_path) == [
        "Spec fit: SPEC-0072 item 2: no Class line (ADR-0813 answer 1)"
    ]
    assert ca.quoted_items(lines, 4) == ""


def test_req066_2002_the_items_digest_is_the_same_in_the_brief_and_in_the_file():
    """REQ-066: brief #2002 answers 5 and 6: the digest of the brief's quoted items equals that of
    the file the builder writes word for word, whatever its wrapping, header or closing line."""
    text = FILE_254.read_text(encoding="utf-8")
    quoted = "\n".join(
        "> " + line
        for line in text.split("## Items\n", 1)[1].split("\n\n", 1)[0].strip().splitlines()
    )
    brief = ca.quoted_items(["Spec fit: SPEC-0030 rules 4 and 6 change by amendment 254",
                             *quoted.splitlines()], 0)  # fmt: skip
    assert ca.items_digest(brief) == ca.items_digest(text)
    wrapped = text.replace(" insert ", "\n   insert ", 1)
    assert ca.items_digest(wrapped) == ca.items_digest(text)
    assert ca.items_digest(text.replace("never an owner ask", "an owner ask")) != ca.items_digest(
        text
    )
    assert ca.items_digest("no items") is None


def test_req066_2002_the_digest_reads_each_item_whole(tmp_path):
    """REQ-066: fix list 7202066567 item 4: a second paragraph added to an item changes the
    digest; the closing `## ` section after the items is not an item."""
    text = (FILE_254.parent / "proposed-spec-amendments-255.md").read_text(encoding="utf-8")
    added = text.replace("Class: behaviour\n", "Class: behaviour\n\nAlso a new paragraph.\n", 1)
    assert ca.items_digest(added) != ca.items_digest(text)
    closing = text.replace("No other rule changes.", "Rule 7 changes too.")
    assert ca.items_digest(closing) == ca.items_digest(text)
    assert "Rule 7" not in "".join(body for _, body in ca.items(closing))
