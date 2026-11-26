"""The domain is proposed and confirmed with one yes, and its questions join the grill
(SPEC-0074 rules 5, 6 and 14; REQ-081 AC3; brief #1937, ADR-0806).

`front_door.py detect` proposes a domain from the repository's files and dependencies;
`steward_owner.py domain --propose` (`domain_ask.propose`) adds the words of the recorded vision
and discovery and asks one plain question; `domain --yes` writes `[domain] packs` and a Proposed
project ADR only from that recorded ask, on the person's yes. The composed packs' `[[discovery]]`
items join `grill.py`: one list, one budget; a regulated pack's critical items are asked at every
depth and past the budget, with one line.

Stub packs, saved trees, local git only, a recorded memory double; invented data (example.com);
no network, no model.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import domain_ask  # noqa: E402
import grill  # noqa: E402
import steward_owner  # noqa: E402

NOW = datetime(2026, 11, 26, 10, 0, tzinfo=UTC)
AT = "2026-11-26T09:58Z"
SOLO = 'default_branch = "main"\nreview_mode = "solo"\n'
TEAM = 'default_branch = "main"\nreview_mode = "team"\n'
ONE = "version: 1\nverdict_authors: [boss]\nspec_approvers: [boss]\n"
HEAD = 'format = 1\ndomain = "{name}"\ntitle = "{title}"\nas_of = "2026-11-25"\n'
TERM = '\n[[terms]]\nterm = "{name} term"\nmeaning = "An invented term"\nsynonyms = []\n'
REG = (
    '\n[[regulations]]\nid = "{name}-law"\ntitle = "An invented rule"\njurisdiction = "global"\n'
    'source = "https://example.com/law"\nas_of = "2026-11-25"\ncritical = true\n'
)
ITEM = (
    '\n[[discovery]]\nid = "{id}"\ntext = "An invented question {id}?"\ndepth = "{depth}"\n'
    "critical = {crit}\n"
)
LINE = "A few more questions are needed for the rules of this business."


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout


def pack(name: str, items: list[tuple[str, str, bool]], regulated: bool, title: str = "") -> str:
    body = HEAD.format(name=name, title=title or f"An invented {name} business")
    body += TERM.format(name=name) + (REG.format(name=name) if regulated else "")
    for item_id, depth, critical in items:
        body += ITEM.format(id=item_id, depth=depth, crit="true" if critical else "false")
    return body


LAW = pack("zz-law", [("zz-law-a", "deep", True), ("zz-law-b", "light", False)], True)
SHOP = pack("zz-shop", [("zz-shop-a", "standard", True), ("zz-shop-b", "deep", False)], False)


def grill_project(tmp: Path, listed: list[str] | None, extra: str = "") -> Path:
    root = tmp / "g"
    shutil.copytree(KIT_ROOT / "config" / "playbooks", root / "config" / "playbooks")
    (root / "config" / "domains").mkdir(parents=True)
    for name, text in {"zz-law": LAW, "zz-shop": SHOP}.items():
        (root / "config" / "domains" / f"{name}.toml").write_text(text, encoding="utf-8")
    table = "" if listed is None else f"[domain]\npacks = {json.dumps(listed)}\n"
    (root / "agk.toml").write_text(SOLO + extra + table, encoding="utf-8")
    return root


def ids(lines: list[str]) -> list[str]:
    return [
        x.split(" ", 1)[0] for x in lines if not x.startswith(("Recommended:", "budget:", "A "))
    ]


# --- rule 6: discovery is the grill ------------------------------------------------------------


def test_ac3_packs_empty_gives_the_grills_own_items_only(tmp_path):
    """REQ-081 AC3: rule 6, `packs = []` and no table give the same list, no pack item."""
    none = grill.questions(grill_project(tmp_path / "a", None), "deep", None, None)
    empty = grill.questions(grill_project(tmp_path / "b", []), "deep", None, None)
    assert none == empty
    assert not [x for x in ids(none) if x.startswith("zz-")]


def test_ac3_a_regulated_packs_critical_items_are_asked_at_light(tmp_path):
    """REQ-081 AC3: rule 6, critical at every depth, the others at standard and deep."""
    root = grill_project(tmp_path, ["zz-law", "zz-shop"])
    light = ids(grill.questions(root, "light", None, None))
    assert "zz-law-a" in light and "zz-law-b" not in light
    assert "zz-law-b" in ids(grill.questions(root, "standard", None, None))
    own = ids(grill.questions(grill_project(tmp_path / "own", None), "light", None, None))
    assert light.index("zz-law-a") > light.index(own[-2])  # after the playbook's, success last
    assert light[-1] == "success"


def test_ac3_a_non_regulated_packs_items_follow_their_depth(tmp_path):
    """REQ-081 AC3: rule 6, no regulation, no promotion."""
    root = grill_project(tmp_path, ["zz-shop"])
    assert "zz-shop-a" not in ids(grill.questions(root, "light", None, None))
    assert "zz-shop-a" in ids(grill.questions(root, "standard", None, None))
    assert "zz-shop-b" not in ids(grill.questions(root, "standard", None, None))
    assert "zz-shop-b" in ids(grill.questions(root, "deep", None, None))


def answers(tmp: Path, done: list[str]) -> Path:
    path = tmp / "answers.json"
    rows = [{"id": x, "claim": "An invented answer", "status": "stated"} for x in done]
    path.write_text(json.dumps({"answers": [], "grill": rows}), encoding="utf-8")
    return path


def test_ac3_past_the_budget_only_regulated_critical_items_are_asked_with_one_line(tmp_path):
    """REQ-081 AC3: rule 6 and rule 14 (grill budget, a pilot's light grill)."""
    root = grill_project(tmp_path, ["zz-law", "zz-shop"])
    own = [i[0] for i in grill.composed(root, None) if not i[0].startswith("zz-")]
    path = answers(tmp_path, own[: grill.BUDGET["light"]])
    out = grill.questions(root, "light", None, str(path))
    assert ids(out) == ["zz-law-a"]
    assert LINE in out and out[-1] == f"budget: {grill.BUDGET['light']}"
    assert out.count(LINE) == 1


def test_ac3_a_refused_domain_table_refuses_the_questions(tmp_path):
    """REQ-081 AC3: answer 4, a refused `[domain]` table is never read as no packs."""
    root = grill_project(tmp_path, None, extra='[domain]\npacks = "zz-law"\n')
    with pytest.raises(grill.CheckError, match=r"domain\.packs"):
        grill.questions(root, "light", None, None)


def test_ac3_past_the_budget_a_playbook_held_id_is_not_asked_again(tmp_path, monkeypatch):
    """REQ-081 AC3: fix list item 6, only the ids the pack itself contributes pass the budget."""
    import check_domains

    root = grill_project(tmp_path, ["zz-law"])
    own = [i[0] for i in grill.composed(root, None) if not i[0].startswith("zz-")]
    taken = own[-2]  # a playbook item, not yet answered below
    real = check_domains.items

    def items(r):
        found = real(r)
        clash = {"id": taken, "text": "?", "depth": "light", "critical": True, "pack": "zz-law"}
        return {**found, "discovery": [clash, *found["discovery"]]}

    monkeypatch.setattr(check_domains, "items", items)
    done = [x for x in own if x != taken][: grill.BUDGET["light"]]
    out = grill.questions(root, "light", None, str(answers(tmp_path, done)))
    assert ids(out) == ["zz-law-a"]


def test_ac3_within_the_budget_no_extra_line(tmp_path):
    """REQ-081 AC3: rule 6, the line only once the budget is spent."""
    root = grill_project(tmp_path, ["zz-law"])
    assert LINE not in grill.questions(root, "light", None, None)


def test_ac3_pack_critical_items_count_in_the_readiness_total(tmp_path):
    """REQ-081 AC3: rule 6, SPEC-0073 rule 6's hold applies to them."""
    root = grill_project(tmp_path, ["zz-law", "zz-shop"])
    base = grill_project(tmp_path / "base", None)
    critical = [i[0] for i in grill.composed(root, None) if i[3]]
    own = [i[0] for i in grill.composed(base, None) if i[3]]
    assert set(critical) - set(own) == {"zz-law-a", "zz-shop-a"}
    path = answers(tmp_path, own)
    line, ok = grill.readiness(root, str(path), "light", None)
    assert not ok and line.startswith(f"critical {len(own)}/{len(own) + 2};")
    assert grill.main(["record", "--answers", str(path), "--id", "zz-law-a", "--open",
                       "--root", str(root)]) == 0  # fmt: skip


# --- rule 5: the proposal in detect --------------------------------------------------------------


def saved_tree(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "owner@example.com")
    git(root, "config", "user.name", "Owner")
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    (root / "README.md").write_text("invented\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "start")
    return root


def detect(root: Path) -> list[str]:
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / "front_door.py"), "detect", "--root", str(root)],
        capture_output=True, text=True, check=False, timeout=60,
    )  # fmt: skip
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout.splitlines()


def test_ac3_detect_proposes_a_domain_from_a_file(tmp_path):
    """REQ-081 AC3: rule 5, `domain: <pack> (proposed) file <file>`."""
    out = detect(saved_tree(tmp_path / "r", {"app/payments.py": "x = 1\n"}))
    assert 'domain: payments (proposed) file "app/payments.py"' in out


def test_ac3_detect_says_none_and_mixed(tmp_path):
    """REQ-081 AC3: rule 5, no signal, and two packs as one mixed line."""
    assert "domain: none (proposed; no signal of a domain)" in detect(
        saved_tree(tmp_path / "a", {})
    )
    out = detect(saved_tree(tmp_path / "b", {"payments.py": "\n", "dispatch.py": "\n"}))
    assert "domain: mixed (2 candidates)" in out
    assert not [x for x in out if "(proposed) file" in x and x.startswith("domain: ")]


# --- rule 5: the ask and the yes -----------------------------------------------------------------


def project(tmp: Path, toml: str = SOLO, files: dict[str, str] | None = None) -> Path:
    root = tmp / "product"
    (root / "docs" / "adr").mkdir(parents=True)
    adr = (KIT_ROOT / "kit" / "templates" / "adr-0001.md").read_text(encoding="utf-8")
    (root / "docs" / "adr" / "0001-adopt-agk.md").write_text(
        re.sub(r"\{\{([a-z_]+)\}\}", lambda m: "2026-11-26" if m[1] == "date" else "demo", adr),
        encoding="utf-8",
    )
    (root / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
    shutil.copytree(KIT_ROOT / "config" / "playbooks", root / "config" / "playbooks")
    shutil.copytree(KIT_ROOT / "config" / "domains", root / "config" / "domains")  # installed
    (root / "config" / "reviewers.yaml").write_text(ONE, encoding="utf-8")
    shutil.copy(KIT_ROOT / "kit/templates/protected-paths.txt", root / "config/protected-paths.txt")
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    return saved_tree(root, files or {"payments.py": "x = 1\n"})


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(tmp_path / "state" / "memory.json"))
    for name in ("AGK_STEWARD_START", "CLAUDE_CODE_REMOTE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AGK_SESSION", "s1")
    monkeypatch.setenv("AGK_ROLE", "steward")
    records: list = []
    monkeypatch.setattr(
        steward_owner.steward,
        "record",
        lambda r, kind, text, gh: records.append((kind, text)) or (0, ["recorded"]),
    )
    return tmp_path, records


def said(tmp: Path, words: str) -> Path:
    path = tmp / "words.txt"
    path.write_text(words + "\n", encoding="utf-8")
    return path


def propose(root: Path, minutes: float = 5):
    return domain_ask.propose(root, NOW - timedelta(minutes=minutes))


def yes(tmp: Path, root: Path, words: str = "Yes", by: str | None = None):
    return domain_ask.yes(root, said(tmp, words), AT, by, NOW)


def packs_of(root: Path) -> object:
    return tomllib.loads((root / "agk.toml").read_text(encoding="utf-8")).get("domain")


def test_ac3_one_signal_asks_one_plain_question_and_applies_nothing(env):
    """REQ-081 AC3: rule 5, one plain yes, no kit term; nothing written before the yes."""
    tmp, _ = env
    root = project(tmp)
    before = (root / "agk.toml").read_text(encoding="utf-8")
    code, lines = propose(root)
    assert code == 0, lines
    sentence = lines[-1].removeprefix("ask the person: ")
    assert sentence.startswith("This looks like taking, refunding and settling payments")
    assert "Yes or not yet; I recommend yes." in sentence
    assert steward_owner.question_problem(sentence) is None
    (ask,) = [a for a in steward_owner.load_asks(root) if a["open"]]
    assert ask["form"] == "domain" and ask["packs"] == ["payments"]
    assert (root / "agk.toml").read_text(encoding="utf-8") == before


def test_ac3_mixed_signals_give_one_choice_of_at_most_three_with_none_of_these(env):
    """REQ-081 AC3: rule 5, the vision's words add to the repository's files."""
    tmp, _ = env
    files = {"dispatch.py": "\n", "payments.py": "\n", "constitution/vision.md": "A refund desk.\n"}
    root = project(tmp, files=files)
    code, lines = propose(root)
    assert code == 0, lines
    sentence = lines[-1].removeprefix("ask the person: ")
    assert "none of these" in sentence and steward_owner.question_problem(sentence) is None
    (ask,) = [a for a in steward_owner.load_asks(root) if a["open"]]
    assert ask["packs"] == ["payments", "field-service"]  # the most signals first, recommended
    assert sentence.endswith("I recommend the first.")


def test_ac3_more_than_three_candidates_offer_the_three_with_most_signals():
    """REQ-081 AC3: rule 5, at most three."""
    counts = {"a": 3, "b": 1, "c": 4, "d": 2}
    assert domain_ask.offered(counts) == ["c", "a", "d"]


def test_ac3_the_yes_writes_the_packs_and_a_proposed_project_adr(env):
    """REQ-081 AC3: rule 5, as `work-type --yes`: a new branch, nothing committed."""
    tmp, records = env
    root = project(tmp)
    propose(root)
    code, lines = yes(tmp, root)
    assert code == 0, lines
    assert packs_of(root) == {"packs": ["payments"]}
    assert git(root, "branch", "--show-current").strip() == domain_ask.BRANCH
    (adr,) = sorted((root / "docs" / "adr").glob("0002-*.md"))
    text = adr.read_text(encoding="utf-8")
    assert "- Status: Proposed" in text and "`agk.toml`" in text
    assert records and records[0][0] == "Decision"


def test_ac3_a_team_mode_plain_yes_is_refused_naming_review_mode(env):
    """REQ-081 AC3: rule 5, SPEC-0073 rule 12: the approver's own words, never a plain yes."""
    tmp, _ = env
    root = project(tmp, TEAM)
    propose(root)
    code, lines = yes(tmp, root, "Yes", by="boss")
    assert code == 2 and "review_mode" in lines[0]
    assert packs_of(root) is None


@pytest.mark.parametrize("words", ["not yet", "None of these."])
def test_ac3_not_yet_or_none_of_these_writes_nothing_and_records_it(env, words):
    """REQ-081 AC3: rule 5, the answer is recorded; no setting is written."""
    tmp, records = env
    root = project(tmp)
    propose(root)
    code, lines = yes(tmp, root, words)
    assert code == 1 and lines == ["not yet: recorded, nothing written"]  # as work-type
    assert packs_of(root) is None and records[-1][0] == "Decision"
    assert not [a for a in steward_owner.load_asks(root) if a["open"]]


def writes(monkeypatch) -> list[str]:
    """Every file `domain_ask` writes through `Path.write_text`, by name."""
    seen: list[str] = []
    real = Path.write_text
    monkeypatch.setattr(
        Path, "write_text", lambda self, *a, **k: seen.append(self.name) or real(self, *a, **k)
    )
    return seen


def test_ac3_the_setting_is_written_only_from_a_recorded_ask(env, monkeypatch):
    """REQ-081 AC3: answer 7, a yes with no open domain ask writes no file and no setting."""
    tmp, _ = env
    root = project(tmp)
    seen = writes(monkeypatch)
    code, lines = yes(tmp, root)
    assert code == 2 and "propose again" in lines[0]
    assert packs_of(root) is None and [x for x in seen if x != "words.txt"] == []


@pytest.mark.parametrize(
    "words",
    ["No, not payments.", "payments, but not until next month", "Not yet, maybe payments later",
     "No payments", "payments?"],
)  # fmt: skip
def test_ac3_a_negative_or_conditional_reply_is_refused_before_any_write(env, monkeypatch, words):
    """REQ-081 AC3: answer 2 (fix list item 1), SPEC-0062 rule 14: a pack in a no is no yes."""
    tmp, records = env
    root = project(tmp)
    propose(root)
    seen = writes(monkeypatch)
    code, lines = yes(tmp, root, words)
    assert code == 2 and "not a yes" in lines[0]
    assert packs_of(root) is None and [x for x in seen if x != "words.txt"] == []
    assert records == [] and git(root, "branch", "--show-current").strip() == "main"


def mixed(tmp: Path, toml: str = SOLO) -> Path:
    files = {"dispatch.py": "\n", "payments.py": "\n", "constitution/vision.md": "A refund desk.\n"}
    root = project(tmp, toml, files=files)
    propose(root)
    return root


@pytest.mark.parametrize(
    ("words", "packs"), [("2", ["field-service"]), ("(1)", ["payments"]),
                         ("field-service please", ["field-service"]), ("Yes", ["payments"])],
)  # fmt: skip
def test_ac3_a_choice_by_name_or_whole_number(env, words, packs):
    """REQ-081 AC3: answer 2 (fix list item 2), a number only as the whole reply."""
    tmp, _ = env
    root = mixed(tmp)
    code, lines = yes(tmp, root, words)
    assert code == 0, lines
    assert packs_of(root) == {"packs": packs}


def test_ac3_a_stray_number_is_no_choice(env):
    """REQ-081 AC3: fix list item 2, "yes, in 2 weeks" picks nothing."""
    tmp, _ = env
    root = mixed(tmp)
    code, lines = yes(tmp, root, "yes, in 2 weeks")
    assert code == 1 and lines[0].startswith("not a yes")
    assert packs_of(root) is None


def test_ac3_a_team_approvers_own_words_print_the_change_only(env):
    """REQ-081 AC3: answer 2, SPEC-0073 rule 12: the approver's words name the pack; printed."""
    tmp, _ = env
    root = project(tmp, TEAM)
    propose(root)
    code, lines = yes(tmp, root, "payments fits this shop", by="boss")
    assert code == 0 and lines[0].startswith("printed only") and 'packs = ["payments"]' in lines
    assert packs_of(root) is None
    assert yes(tmp, root, "payments fits this shop", by="stranger")[0] == 2  # not an approver


def test_ac3_a_packs_value_over_several_lines_is_replaced_whole(env):
    """REQ-081 AC3: fix list item 4, the whole value, valid TOML."""
    text = SOLO + "[domain]\npacks = [\n]\nstale_months = 12\n\n[flow]\nowner_wait_minutes = 10\n"
    out = domain_ask.with_packs(text, ["payments"])
    assert tomllib.loads(out)["domain"] == {"packs": ["payments"], "stale_months": 12}
    assert tomllib.loads(out)["flow"] == {"owner_wait_minutes": 10}
    added = domain_ask.with_packs(SOLO + "[domain]\nstale_months = 6\n", ["payments"])
    assert tomllib.loads(added)["domain"] == {"packs": ["payments"], "stale_months": 6}


def test_ac3_a_declared_domain_is_kept(env):
    """REQ-081 AC3: answer 4, `[domain] packs` set: nothing to propose, or kept when it differs."""
    tmp, _ = env
    field = SOLO + '[domain]\npacks = ["field-service"]\n'
    code, lines = propose(project(tmp / "a", field))
    assert lines == ["domain: declared; it differs from the signals and the declared one is kept"
                     " (setting: domain.packs)"]  # fmt: skip
    paid = SOLO + '[domain]\npacks = ["payments"]\n'
    assert propose(project(tmp / "b", paid))[1] == ["domain: declared; nothing to propose"]


@pytest.mark.parametrize("role", ["builder", None])
def test_ac3_a_builder_or_unset_role_is_refused(env, monkeypatch, role):
    """REQ-081 AC3: answer 2 (fix list item 3), only the steward asks or writes the domain."""
    tmp, _ = env
    root = project(tmp)
    if role is None:
        propose(root)
        monkeypatch.delenv("AGK_ROLE")
        code, lines = yes(tmp, root)
        assert code == 2 and "AGK_ROLE" in lines[0] and packs_of(root) is None
        assert propose(root)[0] == 2
        return
    monkeypatch.setenv("AGK_ROLE", role)
    code, lines = propose(root)
    assert code == 2 and "AGK_ROLE" in lines[0]
    assert steward_owner.load_asks(root) == []


def test_ac3_an_old_ask_is_refused_past_owner_wait(env):
    """REQ-081 AC3: answer 4, `[flow] owner_wait_minutes`: past it nothing is assumed."""
    tmp, _ = env
    root = project(tmp, SOLO + "[flow]\nowner_wait_minutes = 10\n")
    propose(root, minutes=120)
    code, lines = domain_ask.yes(root, said(tmp, "Yes"), "2026-11-26T08:01Z", None, NOW)
    assert code == 2 and "owner_wait_minutes" in lines[0]
    assert packs_of(root) is None


def test_ac3_the_steward_subcommand_runs_the_proposal(env, monkeypatch):
    """REQ-081 AC3: the wiring, `steward_owner.py domain --propose`."""
    tmp, _ = env
    root = project(tmp)
    monkeypatch.chdir(root)
    assert steward_owner.main(["domain", "--propose"]) == 0
    assert [a["form"] for a in steward_owner.load_asks(root)] == ["domain"]
