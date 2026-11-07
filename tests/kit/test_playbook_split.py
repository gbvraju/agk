"""Tests of `playbook.py split` (SPEC-0038 rule 7; REQ-045 AC2 and AC3; brief #664, ADR-0317).

With a declared work type, `python3 scripts/agk/playbook.py split [--goal TEXT] [--kind KIND]`
prints, for the owner and the session filling briefs, the proposed brief kinds of the playbook's
`brief_order`, each later kind with the `Depends-on:` line its `depends_on` pairs give, each kind's
lane (`lane: none` for a kind no lane holds) and the milestone shape. It prints and writes no file,
and never writes `agk.toml`. Without a declaration it prints nothing, so `/agk:brief` prints and
writes exactly what it printed and wrote before. A declaration or a playbook with a problem, and a
`--kind` outside `brief_order`, are refused naming the rule, the file and the key, never the value.
The logic is `playbook_format.split`, so the kit-only command reads the playbook through the
installed module (ADR-0259 decision 1). Both shipped playbook shapes are read: a copy of the shipped
`web-app.toml` and a rag-app fixture with the phases and kinds of rule 11. Fixtures in `tmp_path`
only: invented data, no network.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import playbook_format
import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
PLAYBOOK = SCRIPTS / "playbook.py"
NEW_SPEC = SCRIPTS / "new_spec.py"
WEB_APP = KIT_ROOT / "config" / "playbooks" / "web-app.toml"
BASE_TOML = 'mode = "init"\nversion = "9.9.9"\ninstalled = "2020-01-02"\ndefault_branch = "main"\n'
GOAL = "Invoice viewer for example.com"
UNKNOWN = "zz-unknown-kind"

RAG_APP = """format = 1
work_type = "rag-app"
title = "Corpus and its privacy review, the evaluation set, then retrieval and answers, then joins"
heavy_steps = ["evaluation run"]
evidence = ["the evaluation run record", "the privacy review"]

[[phases]]
name = "corpus"
order = 1
after = []

[[phases]]
name = "evaluation set"
order = 2
after = ["corpus"]

[[phases]]
name = "retrieval"
order = 3
after = ["evaluation set"]

[[phases]]
name = "answers"
order = 3
after = ["evaluation set"]

[[phases]]
name = "joins"
order = 4
after = ["retrieval", "answers"]

[split]
brief_order = ["corpus", "evaluation-set", "retrieval", "answers", "join"]
depends_on = [
  ["evaluation-set", "corpus"],
  ["retrieval", "evaluation-set"],
  ["answers", "evaluation-set"],
  ["join", "retrieval"],
  ["join", "answers"],
]

[[lanes]]
name = "retrieval"
kinds = ["retrieval"]

[[lanes]]
name = "answers"
kinds = ["answers"]

[testing]
profile = "balanced"
always_full = ["evaluation/**"]
map = [{ code = "retrieval/**", tests = "tests/retrieval/**" }]

[[gates]]
id = "evaluation-set"
kind = "check"
text = "A versioned evaluation set with invented data only."
step = "evaluation-set"
owner_only = false

[[gates]]
id = "privacy-review"
kind = "judgement"
text = "A privacy review of the corpus."
owner_only = false

[milestones]
shape = "per-phase"
batch_by = "the phase"

[[claims]]
text = "The evaluation set before any retrieval brief is expected to find a weak retriever earlier."
basis = "expected"
"""


def clean_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}


def project(
    root: Path, work_type: str | None = "web-app", playbook: str | None = "web-app"
) -> Path:
    """A fixture project: `agk.toml` with or without a declaration, and one playbook or none."""
    root.mkdir(parents=True, exist_ok=True)
    delivery = f'\n[delivery]\nwork_type = "{work_type}"\n' if work_type else ""
    (root / "agk.toml").write_text(BASE_TOML + delivery, encoding="utf-8")
    if playbook:
        path = root / "config" / "playbooks" / f"{playbook}.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        text = WEB_APP.read_text(encoding="utf-8") if playbook == "web-app" else RAG_APP
        path.write_text(text, encoding="utf-8")
    return root


def split(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(PLAYBOOK), "split", "--root", str(root), *args],
        capture_output=True,
        text=True,
        env=clean_env(),
        timeout=120,
    )


def blocks(lines: list[str]) -> dict[str, list[str]]:
    """The indented lines of each numbered brief, by its `Kind:`."""
    out: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in lines:
        if line[:1].isdigit():
            current = []
        elif line.startswith("   ") and current is not None:
            current.append(line.strip())
            if line.strip().startswith("Kind: "):
                out[line.strip()[len("Kind: ") :]] = current
    return out


def depends(block: list[str]) -> list[str]:
    return [line for line in block if line.startswith("Depends-on: ")]


def lane(block: list[str]) -> str:
    (value,) = [line[len("lane: ") :] for line in block if line.startswith("lane: ")]
    return value


# --- rule 7: the kinds in brief_order with their Depends-on lines and lanes (AC3) ---


def test_ac3_the_shipped_web_app_playbook_splits_a_goal_in_brief_order(tmp_path):
    """REQ-045 AC3: rule 7 with the shipped `web-app.toml` (rule 11)."""
    proc = split(project(tmp_path / "proj"), "--goal", GOAL)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = proc.stdout.splitlines()
    assert lines[0] == "work type: web-app (playbook config/playbooks/web-app.toml)"
    titles = [line for line in lines if line[:1].isdigit()]
    assert titles == [
        f"1. {GOAL}: contract",
        f"2. {GOAL}: mock",
        f"3. {GOAL}: front-end",
        f"4. {GOAL}: back-end",
        f"5. {GOAL}: join",
    ]
    by_kind = blocks(lines)
    assert list(by_kind) == ["contract", "mock", "front-end", "back-end", "join"]
    assert depends(by_kind["contract"]) == []
    assert depends(by_kind["mock"]) == ["Depends-on: #<contract brief>"]
    assert depends(by_kind["front-end"]) == ["Depends-on: #<mock brief>"]
    assert depends(by_kind["back-end"]) == ["Depends-on: #<mock brief>"]
    assert depends(by_kind["join"]) == [
        "Depends-on: #<front-end brief>",
        "Depends-on: #<back-end brief>",
    ]


def test_ac3_a_kind_in_a_lane_shows_the_lane_and_one_without_shows_none(tmp_path):
    """REQ-045 AC3: rule 7 and the lane of rule 8 (`Q-S0038-8`)."""
    proc = split(project(tmp_path / "proj"))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    by_kind = blocks(proc.stdout.splitlines())
    assert lane(by_kind["front-end"]) == "front-end"
    assert lane(by_kind["back-end"]) == "back-end"
    assert lane(by_kind["contract"]) == lane(by_kind["mock"]) == lane(by_kind["join"]) == "none"


def test_ac3_without_a_goal_the_titles_are_the_kinds(tmp_path):
    """REQ-045 AC3: rule 7 (the goal is optional; the maintainers decide each brief's content)."""
    proc = split(project(tmp_path / "proj"))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    titles = [line for line in proc.stdout.splitlines() if line[:1].isdigit()]
    assert titles == ["1. contract", "2. mock", "3. front-end", "4. back-end", "5. join"]


def test_ac3_the_milestone_shape_is_printed_with_its_meaning(tmp_path):
    """REQ-045 AC3: rule 7 (per-batch: numbered as one milestone; a milestone never merges)."""
    proc = split(project(tmp_path / "proj"))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = proc.stdout.splitlines()
    assert lines[1].startswith("milestone shape: per-batch (batch_by: demo value")
    assert "numbered as one milestone in their titles" in lines[2]
    assert "never merges them" in lines[2]
    assert "one pull request per brief" in lines[2]


def test_ac3_the_rag_app_shape_puts_the_evaluation_set_before_retrieval_and_answers(tmp_path):
    """REQ-045 AC3: rule 7 reads the rag-app shape of rule 11 (both playbooks read)."""
    root = project(tmp_path / "proj", work_type="rag-app", playbook="rag-app")
    proc = split(root, "--goal", GOAL)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = proc.stdout.splitlines()
    assert lines[0] == "work type: rag-app (playbook config/playbooks/rag-app.toml)"
    assert lines[1] == "milestone shape: per-phase (batch_by: the phase)"
    assert "the briefs of a phase are numbered as one milestone in their titles" in lines[2]
    by_kind = blocks(lines)
    assert list(by_kind) == ["corpus", "evaluation-set", "retrieval", "answers", "join"]
    assert depends(by_kind["evaluation-set"]) == ["Depends-on: #<corpus brief>"]
    assert depends(by_kind["retrieval"]) == ["Depends-on: #<evaluation-set brief>"]
    assert depends(by_kind["answers"]) == ["Depends-on: #<evaluation-set brief>"]
    assert depends(by_kind["join"]) == [
        "Depends-on: #<retrieval brief>",
        "Depends-on: #<answers brief>",
    ]
    assert lane(by_kind["retrieval"]) == "retrieval"
    assert lane(by_kind["answers"]) == "answers"
    assert lane(by_kind["corpus"]) == lane(by_kind["evaluation-set"]) == "none"


def test_ac3_per_brief_shape_says_one_pull_request_per_brief_as_today(tmp_path):
    """REQ-045 AC3: rule 7 (`per-brief`)."""
    root = project(tmp_path / "proj")
    path = root / "config" / "playbooks" / "web-app.toml"
    text = path.read_text(encoding="utf-8").replace('shape = "per-batch"', 'shape = "per-brief"')
    path.write_text(text, encoding="utf-8")
    proc = split(root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = proc.stdout.splitlines()
    assert lines[1].startswith("milestone shape: per-brief")
    assert lines[2].strip() == "one pull request per brief, as today"


def test_ac3_one_kind_prints_only_that_brief(tmp_path):
    """REQ-045 AC3: rule 7 (`--kind` for the session filling one brief)."""
    proc = split(project(tmp_path / "proj"), "--goal", GOAL, "--kind", "join")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = proc.stdout.splitlines()
    assert lines[0] == "work type: web-app (playbook config/playbooks/web-app.toml)"
    titles = [line for line in lines if line[:1].isdigit()]
    assert titles == [f"5. {GOAL}: join"]
    by_kind = blocks(lines)
    assert list(by_kind) == ["join"]
    assert depends(by_kind["join"]) == [
        "Depends-on: #<front-end brief>",
        "Depends-on: #<back-end brief>",
    ]


def test_ac3_the_module_gives_the_same_lines_as_the_command(tmp_path):
    """REQ-045 AC3: the command reads the playbook through `playbook_format` (ADR-0259)."""
    root = project(tmp_path / "proj")
    lines, problems = playbook_format.split(root, goal=GOAL)
    assert problems == []
    assert split(root, "--goal", GOAL).stdout == "".join(f"{line}\n" for line in lines)


def test_ac3_a_depends_on_pair_is_ordered_by_brief_order(tmp_path):
    """REQ-045 AC3: rule 7 (the Depends-on lines follow `brief_order`, not the pair order)."""
    root = project(tmp_path / "proj")
    path = root / "config" / "playbooks" / "web-app.toml"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        '["join", "front-end"],\n  ["join", "back-end"],',
        '["join", "back-end"],\n  ["join", "front-end"],',
    )
    assert '["join", "back-end"],\n  ["join", "front-end"]' in text
    path.write_text(text, encoding="utf-8")
    lines, problems = playbook_format.split(root)
    assert problems == []
    assert depends(blocks(lines)["join"]) == [
        "Depends-on: #<front-end brief>",
        "Depends-on: #<back-end brief>",
    ]


# --- rule 5: no declaration, nothing changes; the refusals (AC2) ---


def test_ac2_without_a_declaration_split_prints_nothing(tmp_path):
    """REQ-045 AC2: rule 5 (no command reads a playbook; the output is unchanged)."""
    for root in (
        project(tmp_path / "no-table", work_type=None),
        project(tmp_path / "no-playbook", work_type=None, playbook=None),
    ):
        proc = split(root, "--goal", GOAL)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert proc.stdout == "" and proc.stderr == ""
        assert playbook_format.split(root, goal=GOAL) == ([], [])


def test_ac2_without_a_declaration_the_brief_skill_writes_byte_for_byte_what_it_wrote(tmp_path):
    """REQ-045 AC2: rule 5 (`/agk:brief` creates the same file whether or not a playbook ships)."""
    outputs = []
    for name, playbook in (("a", None), ("b", "web-app")):
        root = project(tmp_path / name, work_type=None, playbook=playbook)
        (root / "docs" / "briefs").mkdir(parents=True)
        shutil.copy(KIT_ROOT / "docs" / "briefs" / "TEMPLATE.md", root / "docs" / "briefs")
        proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, "-I", str(NEW_SPEC), "brief", GOAL],
            cwd=root,
            capture_output=True,
            text=True,
            env=clean_env(),
            timeout=120,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        shown = split(root, "--goal", GOAL)
        assert shown.returncode == 0 and shown.stdout == ""
        (written,) = [p for p in (root / "docs" / "briefs").iterdir() if p.name != "TEMPLATE.md"]
        outputs.append((proc.stdout, written.name, written.read_bytes()))
    assert outputs[0] == outputs[1]


def test_ac2_a_declaration_with_a_problem_is_refused_naming_the_setting(tmp_path):
    """REQ-045 AC2: rule 5 (an unknown work type, or one whose playbook is missing)."""
    for name, work_type, playbook in (
        ("unknown", "zz-unknown-type", "web-app"),
        ("missing", "rag-app", "web-app"),
    ):
        root = project(tmp_path / name, work_type=work_type, playbook=playbook)
        proc = split(root, "--goal", GOAL)
        assert proc.returncode == 1, proc.stdout + proc.stderr
        assert proc.stdout.startswith("FAIL playbook: rule 5: agk.toml:")
        assert "(setting: work_type)" in proc.stdout
        assert work_type not in proc.stdout + proc.stderr
        assert not [line for line in proc.stdout.splitlines() if line[:1].isdigit()]


def test_ac2_a_playbook_with_a_problem_is_not_split(tmp_path):
    """REQ-045 AC2 and AC1: rules 2 and 7 (a playbook that fails the check gives no proposal)."""
    root = project(tmp_path / "proj")
    path = root / "config" / "playbooks" / "web-app.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('kinds = ["front-end"]', 'kinds = ["zz-no-kind"]'),
        encoding="utf-8",
    )
    proc = split(root, "--goal", GOAL)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert proc.stdout.splitlines() == [
        "FAIL playbook: rule 2: config/playbooks/web-app.toml: a lane kind is not in `brief_order`"
    ]
    assert "zz-no-kind" not in proc.stdout


def test_ac2_a_kind_outside_brief_order_is_refused_naming_the_key(tmp_path):
    """REQ-045 AC2: rule 7 (brief #664 answer 2: refused naming the key, never the value)."""
    root = project(tmp_path / "proj")
    proc = split(root, "--goal", GOAL, "--kind", UNKNOWN)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert proc.stdout.splitlines() == [
        "FAIL playbook: rule 7: config/playbooks/web-app.toml: the kind is not in `brief_order` "
        "(key: brief_order)"
    ]
    assert UNKNOWN not in proc.stdout + proc.stderr
    lines, problems = playbook_format.split(root, kind=UNKNOWN)
    assert lines == [] and len(problems) == 1 and UNKNOWN not in problems[0]


def test_ac3_no_reader_writes_agk_toml_or_any_file(tmp_path):
    """REQ-045 AC3: rule 5 (a session never writes the declaration; split writes no file)."""
    root = project(tmp_path / "proj")
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert split(root, "--goal", GOAL, "--kind", "mock").returncode == 0
    assert split(root, "--kind", UNKNOWN).returncode == 1
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


# --- the command's form ---


def test_ac3_split_is_a_command_of_playbook_py_and_its_usage_names_it():
    """REQ-045 AC3: rule 7 names `playbook.py split`; the usage lines name it."""
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(PLAYBOOK)], capture_output=True, text=True, env=clean_env()
    )
    assert proc.returncode == 2
    assert "split" in proc.stderr
    bad = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(PLAYBOOK), "split", "--goal"],
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert bad.returncode == 2 and bad.stdout == ""


@pytest.mark.parametrize("flag", ["--goal", "--kind"])
def test_ac3_the_brief_skill_shows_the_split_before_filling(flag):
    """REQ-045 AC3: rule 7 (`skills/brief/SKILL.md` tells the session to show it)."""
    text = (KIT_ROOT / "skills" / "brief" / "SKILL.md").read_text(encoding="utf-8")
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/playbook.py" split' in text
    assert flag in text
    assert "Kind:" in text and "Depends-on:" in text
    assert text.index("new_spec.py") < text.index("playbook.py")
    assert "maintainers" in text
