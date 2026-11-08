"""Kit-only tests of `/agk:stack` reading the declared work type's playbook (SPEC-0038 rule 6;
REQ-045 AC3; brief #663, ADR-0316).

With a declared work type (`[delivery] work_type` in `agk.toml`), `engines.py stack-write` writes
into the stack ADR's skeleton one Practices bullet per playbook gate, `- <id>: check (step: <step>)`
or `- <id>: judgement`, marked `(playbook <work type>)`, and the playbook's `[testing]` profile,
`always_full` and `map` suggestions into the parenthesis of the `test selection` practice for each
option. They are proposals; nothing else of the ADR changes; no reader writes `agk.toml`. Without a
declaration the skeleton is the template, byte for byte. A declaration whose playbook is missing or
fails the playbook check is refused, naming the setting and never the value. The shipped `web-app`
playbook is the fixture (invented data); no network, no model.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib

import pytest
from conftest import KIT_ROOT, clean_env
from test_playbook import started as playbook_started  # noqa: F401  (wrapped below)

ENGINES = KIT_ROOT / "scripts" / "agk" / "engines.py"
TEMPLATE = KIT_ROOT / "kit" / "templates" / "stack-adr.md"
SKILL = KIT_ROOT / "skills" / "stack" / "SKILL.md"
WEB_APP = KIT_ROOT / "config" / "playbooks" / "web-app.toml"
ADR = "docs/adr/0002-stack-options.md"
DATE = "2026-11-07"
DECLARATION = '\n[delivery]\nwork_type = "web-app"\n'
TODO_PRACTICE = (
    "   - TODO(architect): check (step: the governance step the adopting build adds) or judgement\n"
)
PROPOSAL = (
    "profile balanced, always_full `contracts/**`, map `contracts/** -> tests/contract/**`, "
    "`mocks/** -> tests/mocks/**`, `frontend/** -> tests/frontend/**`, "
    "`backend/** -> tests/backend/**` (playbook web-app)"
)
TEST_SELECTION = f"   - test selection: judgement (Option A: {PROPOSAL}; Option B: {PROPOSAL})\n"
GATES = [
    "   - contract-tests: check (step: contract-tests) (playbook web-app)\n",
    "   - mock-parity: check (step: mock-parity) (playbook web-app)\n",
    "   - e2e-smoke: judgement (playbook web-app)\n",
    "   - accessibility: judgement (playbook web-app)\n",
]


@pytest.fixture
def started(request):
    return request.getfixturevalue("playbook_started")


def engines(root, *args):
    return subprocess.run(
        [sys.executable, str(ENGINES), *args, "--root", str(root)],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def stack_write(root):
    return engines(root, "stack-write", "--ref", "main", "--date", DATE)


def declare(root, work_type: str = "web-app", playbook: str | None = "shipped") -> None:
    """The one line of rule 5 in `agk.toml`, and the playbook file under `config/playbooks/`: the
    shipped web-app playbook, the given text, or none."""
    with (root / "agk.toml").open("a", encoding="utf-8") as handle:
        handle.write(DECLARATION.replace("web-app", work_type))
    if playbook == "shipped":
        playbook = WEB_APP.read_text(encoding="utf-8")
    if playbook is not None:
        path = root / "config" / "playbooks" / "web-app.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(playbook, encoding="utf-8")


def rendered_template() -> str:
    return TEMPLATE.read_text(encoding="utf-8").replace("{{adr}}", "0002").replace("{{date}}", DATE)


def practices(text: str) -> str:
    return text[text.index("2. **Practices**") : text.index("3. **Chosen**")]


# --- without a declaration ---------------------------------------------------------------------


def test_ac3_without_a_declaration_the_skeleton_is_the_template_byte_for_byte(started):
    """REQ-045 AC3: SPEC-0038 rule 6 (without a declaration the skeleton is the same as today)."""
    proc = stack_write(started)
    assert (proc.returncode, proc.stdout) == (0, "wrote docs/adr/0002-stack-options.md\n")
    assert (started / ADR).read_bytes() == rendered_template().encode("utf-8")


@pytest.mark.parametrize(
    "delivery",
    ["\n[delivery]\n", '\n# [delivery]\n# work_type = "web-app"\n'],
    ids=["empty", "comment"],
)
def test_ac3_an_empty_or_commented_table_is_no_declaration(started, delivery):
    """REQ-045 AC3: SPEC-0038 rule 5 (no `work_type`: nothing reads a playbook)."""
    with (started / "agk.toml").open("a", encoding="utf-8") as handle:
        handle.write(delivery)
    assert stack_write(started).returncode == 0
    assert (started / ADR).read_text(encoding="utf-8") == rendered_template()


# --- with a declaration ------------------------------------------------------------------------


def test_ac3_a_declared_work_type_adds_one_practice_per_gate_marked_with_the_playbook(started):
    """REQ-045 AC3: SPEC-0038 rule 6 (one bullet per gate, check with its step or judgement)."""
    declare(started)
    proc = stack_write(started)
    assert (proc.returncode, proc.stdout) == (0, "wrote docs/adr/0002-stack-options.md\n")
    block = practices((started / ADR).read_text(encoding="utf-8"))
    assert TODO_PRACTICE + "".join(GATES) in block
    gates = tomllib.loads(WEB_APP.read_text(encoding="utf-8"))["gates"]
    assert [g["id"] for g in gates] == [
        "contract-tests",
        "mock-parity",
        "e2e-smoke",
        "accessibility",
    ]
    for gate, line in zip(gates, GATES, strict=True):
        assert line.startswith(f"   - {gate['id']}: {gate['kind']}")
        assert ("(step: " in line) == (gate["kind"] == "check")
        assert line.rstrip("\n").endswith("(playbook web-app)")
    assert block.count("(playbook web-app)") == len(GATES) + 2


def test_ac3_the_test_selection_parenthesis_carries_the_testing_suggestion_per_option(started):
    """REQ-045 AC3: SPEC-0038 rule 6 (profile, always_full and map, for each option)."""
    declare(started)
    assert stack_write(started).returncode == 0
    block = practices((started / ADR).read_text(encoding="utf-8"))
    assert TEST_SELECTION in block
    testing = tomllib.loads(WEB_APP.read_text(encoding="utf-8"))["testing"]
    assert f"profile {testing['profile']}" in TEST_SELECTION
    for path in testing["always_full"]:
        assert f"always_full `{path}`" in TEST_SELECTION
    for entry in testing["map"]:
        assert f"`{entry['code']} -> {entry['tests']}`" in TEST_SELECTION


def test_ac3_an_empty_map_and_always_full_are_written_as_none(started):
    """REQ-045 AC3: SPEC-0038 rule 6 (a `[testing]` table with an empty `always_full` and `map`
    proposes `none` for each, never an empty segment)."""
    shipped = WEB_APP.read_text(encoding="utf-8")
    start = shipped.index('always_full = ["contracts/**"]')
    end = shipped.index("]\n\n[[gates]]") + 2
    declare(started, playbook=shipped[:start] + "always_full = []\nmap = []\n" + shipped[end:])
    proc = stack_write(started)
    assert proc.returncode == 0, proc.stdout
    block = practices((started / ADR).read_text(encoding="utf-8"))
    proposal = "profile balanced, always_full none, map none (playbook web-app)"
    assert f"   - test selection: judgement (Option A: {proposal}; Option B: {proposal})\n" in block


def test_ac3_nothing_else_of_the_adr_changes(started):
    """REQ-045 AC3: brief #663 answer 2 (the Practices item gains the blocks; the rest is the
    template)."""
    declare(started)
    assert stack_write(started).returncode == 0
    text = (started / ADR).read_text(encoding="utf-8")
    for line in GATES:
        assert text.count(line) == 1
        text = text.replace(line, "", 1)
    template = rendered_template()
    original = next(ln for ln in template.splitlines(keepends=True) if "- test selection:" in ln)
    assert text.count(TEST_SELECTION) == 1
    assert text.replace(TEST_SELECTION, original, 1) == template


def test_ac3_the_skeleton_with_the_playbook_practices_passes_the_check_once_drafted(started):
    """REQ-045 AC3: SPEC-0038 rule 6 (the bullets are well-formed practices; the proposals are
    read by `stack-check` as the chosen option's `[testing]` values)."""
    declare(started)
    assert stack_write(started).returncode == 0
    path = started / ADR
    text = path.read_text(encoding="utf-8")
    text = text.replace("- Requirements: TODO(architect)", "- Requirements: REQ-001")
    text = text.replace("TODO(architect): what the product needs", "A reading list; what it needs")
    lines = []
    for line in text.splitlines(keepends=True):
        if "Option A — TODO" in line:
            line = (
                "   - Option A — plain scripts. Trade-offs: nothing to host. "
                "Practices: contract-tests, test selection.\n"
            )
        elif "Option B — TODO" in line:
            line = (
                "   - Option B — a web framework. Trade-offs: a host to run. "
                "Practices: mock-parity, accessibility, test selection.\n"
            )
        elif line == TODO_PRACTICE:
            continue
        lines.append(line)
    path.write_text("".join(lines), encoding="utf-8")
    assert engines(started, "stack-check").stdout == "ok engines-stack\n"
    accepted = "".join(lines).replace("- Status: Proposed", "- Status: Accepted")
    path.write_text(
        accepted.replace("**Chosen**: none yet", "**Chosen**: Option A"), encoding="utf-8"
    )
    with (started / "agk.toml").open("a", encoding="utf-8") as handle:
        handle.write('\n[testing]\nprofile = "balanced"\nalways_full = ["contracts/**"]\n')
    proc = engines(started, "stack-check")
    assert proc.returncode == 0, proc.stdout
    assert "info engines: [testing] matches option A\n" in proc.stdout


def test_ac3_no_reader_writes_agk_toml(started):
    """REQ-045 AC3: SPEC-0038 rule 6 (the `[testing]` table changes only by the step after Chosen,
    never by a reader of the playbook)."""
    declare(started)
    before = (started / "agk.toml").read_bytes()
    playbook = (started / "config" / "playbooks" / "web-app.toml").read_bytes()
    assert stack_write(started).returncode == 0
    assert (started / "agk.toml").read_bytes() == before
    assert (started / "config" / "playbooks" / "web-app.toml").read_bytes() == playbook


# --- refusals ----------------------------------------------------------------------------------


def test_ac3_a_declared_type_whose_playbook_is_missing_is_refused_and_nothing_is_written(started):
    """REQ-045 AC3: brief #663 answer 2 (a missing playbook file is refused, naming rule 5, the
    file `agk.toml`, the folder and the setting, never the value)."""
    declare(started, playbook=None)
    proc = stack_write(started)
    assert proc.returncode == 1, proc.stdout
    assert proc.stdout.startswith("FAIL engines: rule 5: agk.toml:")
    for needle in ("playbook is missing", "config/playbooks/", "(setting: work_type)"):
        assert needle in proc.stdout, proc.stdout
    assert "web-app" not in proc.stdout
    assert not (started / ADR).exists()


def test_ac3_an_unknown_work_type_is_refused_naming_the_setting_never_the_value(started):
    """REQ-045 AC3: SPEC-0038 rule 5 (an unknown value fails naming the setting)."""
    declare(started, work_type="zz-unknown-type", playbook=None)
    proc = stack_write(started)
    assert (
        proc.returncode == 1 and "rule 5" in proc.stdout and "(setting: work_type)" in proc.stdout
    )
    assert "zz-unknown" not in proc.stdout
    assert not (started / ADR).exists()


def test_ac3_a_declared_playbook_that_fails_the_check_is_refused(started):
    """REQ-045 AC3: SPEC-0038 rules 2 and 6 (a playbook the check refuses is not read into the
    stack ADR; the refusal names the setting and the check, never a value)."""
    broken = WEB_APP.read_text(encoding="utf-8").replace("[milestones]", "[milestone]")
    declare(started, playbook=broken)
    proc = stack_write(started)
    assert proc.returncode == 1, proc.stdout
    assert proc.stdout.startswith("FAIL engines: rule 6:")
    assert "check_playbooks.py" in proc.stdout and "(setting: work_type)" in proc.stdout
    assert "web-app" not in proc.stdout and "milestone" not in proc.stdout
    assert not (started / ADR).exists()


def test_ac3_a_playbook_that_is_not_toml_is_refused_the_same_way(started):
    """REQ-045 AC3: SPEC-0038 rule 1 (a file that is not TOML is a failing playbook)."""
    declare(started, playbook="work_type = [unclosed\n")
    proc = stack_write(started)
    assert proc.returncode == 1 and proc.stdout.startswith("FAIL engines: rule 6:")
    assert not (started / ADR).exists()


# --- the skill ---------------------------------------------------------------------------------


def test_ac3_the_skill_says_what_the_declared_playbook_adds_and_that_it_only_proposes():
    """REQ-045 AC3: SPEC-0038 rule 6 (the architect chooses as today; a project adds a gate as a
    practice, never by editing the playbook; never a vendor choice)."""
    text = SKILL.read_text(encoding="utf-8")
    fill = " ".join(text[text.index("\n1. ") : text.index("\n3. ")].split())
    for needle in (
        "`[delivery]`",
        "`work_type`",
        "(playbook <work type>)",
        "`test selection`",
        "`always_full`",
        "`map`",
        "proposals",
        "never by editing the playbook",
        "never a vendor",
        "stack-write` refuses",
    ):
        assert needle in fill, needle
    for verb in ("git push", "git commit", "gh pr", "gh issue"):
        assert verb not in text
