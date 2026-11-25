"""Tests of `domain_model.py`, the project domain model (SPEC-0074 rules 7 and 9; REQ-081 AC4;
brief #1954, ADR-0810).

The four files of `docs/domain/` keep rule 7's forms: a `BR-<n>` used twice, a rule with no
source, owner or status, a file over 200 rules, a data item outside the five classes, an entity
twice, a relation to no entity and a regulation of no pack in `[domain] packs` each fail naming
the rule, the file and the id, never a rule's text or a value. The writer numbers across areas,
refuses an overwrite, a 201st rule and a guarded value, and `confirm` changes only the status
word. Fixtures in `tmp_path` only: invented data (example.com), no network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
AGK = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(AGK))

import check_domains  # noqa: E402
import domain_model  # noqa: E402

PACK = """format = 1
domain = "zz-shop"
title = "An invented shop for the tests"
as_of = "2026-11-25"

[[terms]]
term = "basket"
meaning = "The items a buyer holds before paying"
synonyms = ["cart"]

[[regulations]]
id = "zz-rule"
title = "An invented consumer rule"
jurisdiction = "global"
source = "https://example.com/zz-rule"
as_of = "2026-11-25"
critical = true
"""
PLANTED = "INVENTEDRULETEXT"
CARD = "4111 1111 1111 1111"  # the well-known test card number, invented data

GOOD = {
    "entities.md": (
        "# Entities\n\n## Order\n\nWhat a buyer of example.com pays for.\n\n"
        "- relates to Buyer: many to one, a buyer places orders\n\n"
        "## Buyer\n\nA person who buys.\n"
    ),
    "rules-orders.md": (
        "# Rules: orders\n\n"
        f"- BR-1: {PLANTED} an order over 100 needs a check; with care; "
        "source: interview, kickoff notes; owner: sales lead; confirmed\n"
        "- BR-2: a refund goes to the card that paid; source: code, src/refund.py:12; "
        "owner: finance lead; inferred\n"
    ),
    "rules-stock.md": "# Rules: stock\n\n",
    "data.md": "# Data\n\n- buyer e-mail: personal\n- order total: confidential\n",
    "regulations.md": "# Regulations\n\n- zz-shop.zz-rule: in scope, buyers are consumers\n",
}


def model(root: Path, files: dict[str, str] | None = None, packs: bool = True) -> Path:
    folder = root / "docs" / "domain"
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in (GOOD if files is None else files).items():
        (folder / name).write_text(text, encoding="utf-8")
    (root / "config" / "domains").mkdir(parents=True, exist_ok=True)
    (root / "config" / "domains" / "zz-shop.toml").write_text(PACK, encoding="utf-8")
    table = '[domain]\npacks = ["zz-shop"]\n' if packs else ""
    (root / "agk.toml").write_text('mode = "init"\n' + table, encoding="utf-8")
    return root


def changed(root: Path, name: str, text: str) -> list[str]:
    model(root, {**GOOD, name: text})
    return domain_model.findings(root)


def no_value(lines: list[str]) -> None:
    for line in lines:
        assert PLANTED not in line and "sales lead" not in line and CARD not in line


def test_ac4_a_good_model_passes_and_no_folder_checks_nothing(tmp_path):
    """REQ-081 AC4: rule 7 (a sound model passes; without `docs/domain/` nothing is read)."""
    assert domain_model.findings(tmp_path) == []
    assert domain_model.findings(model(tmp_path)) == []
    assert check_domains.findings(tmp_path) == []


def test_ac4_check_domains_carries_the_model_lines(tmp_path):
    """REQ-081 AC4: rule 7 (the form check runs inside `check_domains.findings`)."""
    rules = GOOD["rules-orders.md"].replace("BR-2", "BR-1")
    model(tmp_path, {**GOOD, "rules-orders.md": rules})
    assert any(line.startswith("rule 7: docs/domain/") for line in check_domains.findings(tmp_path))


def test_ac4_a_rule_id_twice_fails_naming_both_files_and_the_id(tmp_path):
    """REQ-081 AC4: rule 7 (`BR-<n>` is unique across the folder)."""
    stock = "# Rules\n\n- BR-2: stock is counted daily; source: interview, x; owner: y; confirmed\n"
    found = changed(tmp_path, "rules-stock.md", stock)
    assert len(found) == 1
    assert "rules-stock.md" in found[0] and "rules-orders.md" in found[0]
    assert found[0].endswith("(id: BR-2)")


@pytest.mark.parametrize(
    "line, what",
    [
        ("- BR-3: a rule; owner: x; confirmed", "source"),
        ("- BR-3: a rule; source: interview, x; confirmed", "owner"),
        ("- BR-3: a rule; source: interview, x; owner: y", "status"),
        ("- BR-3: a rule; source: rumour, x; owner: y; confirmed", "source kind"),
        ("- BR-3: a rule; source: interview, x; owner: y; maybe", "status"),
    ],
)
def test_ac4_a_rule_with_no_source_owner_or_status_fails_naming_the_id(tmp_path, line, what):
    """REQ-081 AC4: rule 7 (each rule has a source of three kinds, an owner and a status)."""
    found = changed(tmp_path, "rules-stock.md", f"# Rules\n\n{line}\n")
    assert len(found) == 1 and what in found[0] and found[0].endswith("(id: BR-3)"), found
    assert found[0].startswith("rule 7: docs/domain/rules-stock.md: ")


@pytest.mark.parametrize("rid", ["BR-0", "BR-01", "BR-x"])
def test_ac4_a_malformed_id_fails_naming_it(tmp_path, rid):
    """REQ-081 AC4: rule 7 and answer 8 (`<n>` a whole number from 1, no leading zero)."""
    line = f"- {rid}: a rule; source: interview, x; owner: y; confirmed"
    found = changed(tmp_path, "rules-stock.md", f"# Rules\n\n{line}\n")
    assert found == [f"rule 7: docs/domain/rules-stock.md: the rule id is not BR-<n> (id: {rid})"]


def test_ac4_a_file_over_200_rules_and_a_bad_file_name_fail(tmp_path):
    """REQ-081 AC4: rule 7 (at most 200 rules per file; files are `rules-<area>.md`)."""
    lines = "".join(
        f"- BR-{n}: rule {n}; source: interview, x; owner: y; confirmed\n" for n in range(3, 204)
    )
    found = changed(tmp_path, "rules-stock.md", "# Rules\n\n" + lines)
    assert found == [
        "rule 7: docs/domain/rules-stock.md: the file holds over 200 rules (id: BR-203)"
    ]
    found = changed(tmp_path / "b", "rules-Big Area.md", "# Rules\n")
    assert found == [
        "rule 7: docs/domain/rules-Big Area.md: a rules file is not rules-<area>.md (id: file)"
    ]


@pytest.mark.parametrize(
    "text, what, ident",
    [
        ("- buyer e-mail: secret\n", "not one of the five classes", "buyer e-mail"),
        ("- buyer e-mail: personal\n- buyer e-mail: public\n", "named twice", "buyer e-mail"),
    ],
)
def test_ac4_a_data_item_outside_the_five_classes_or_twice_fails(tmp_path, text, what, ident):
    """REQ-081 AC4: rule 7 (personal, health, payment, confidential or public; each item once)."""
    found = changed(tmp_path, "data.md", "# Data\n\n" + text)
    assert len(found) == 1 and what in found[0] and found[0].endswith(f"(id: {ident})")


def test_ac4_an_entity_twice_or_a_relation_to_no_entity_fails(tmp_path):
    """REQ-081 AC4: answer 1 (one section per entity; a relation names an entity)."""
    twice = GOOD["entities.md"] + "\n## Order\n\nAgain.\n"
    assert changed(tmp_path, "entities.md", twice) == [
        "rule 7: docs/domain/entities.md: an entity is named twice (id: Order)"
    ]
    dangling = GOOD["entities.md"].replace("relates to Buyer", "relates to Seller")
    assert changed(tmp_path / "b", "entities.md", dangling) == [
        "rule 7: docs/domain/entities.md: a relation names no entity (id: Order)"
    ]
    bad = GOOD["entities.md"].replace("many to one", "lots to one")
    assert changed(tmp_path / "c", "entities.md", bad) == [
        "rule 7: docs/domain/entities.md: a relation is not <one|many> to <one|many> (id: Order)"
    ]


def test_ac4_a_regulation_of_no_pack_in_packs_fails_naming_the_id(tmp_path):
    """REQ-081 AC4: answer 7 (`[domain] packs` names the regulations `regulations.md` may list)."""
    model(tmp_path, packs=False)
    assert domain_model.findings(tmp_path) == [
        "rule 7: docs/domain/regulations.md: the regulation is of no pack in [domain] packs "
        "(id: zz-shop.zz-rule)"
    ]
    wrong = "# Regulations\n\n- zz-shop.zz-other: out of scope, no reason\n"
    assert changed(tmp_path / "b", "regulations.md", wrong)[0].endswith("(id: zz-shop.zz-other)")
    unsure = "# Regulations\n\n- zz-shop.zz-rule: maybe, unsure\n"
    assert "in scope or out of scope" in changed(tmp_path / "c", "regulations.md", unsure)[0]


def test_ac4_a_guarded_line_fails_naming_the_class_never_the_value(tmp_path):
    """REQ-081 AC4: answer 4 (any line `guard.scan_text` flags; no value printed)."""
    found = changed(tmp_path, "data.md", f"# Data\n\n- card {CARD}: payment\n")
    assert found and all("data guard flags" in line for line in found)
    no_value(found)


def test_ac4_a_semicolon_in_the_text_crlf_and_bom_read_the_same(tmp_path):
    """REQ-081 AC4: answer 8 (the line is read from the right; a CRLF or BOM file reads alike)."""
    text = "﻿" + GOOD["rules-orders.md"].replace("\n", "\r\n")
    assert changed(tmp_path, "rules-orders.md", text) == []
    rules = domain_model.rules(tmp_path)
    assert [(r.id, r.status, r.file) for r in rules] == [
        ("BR-1", "confirmed", "rules-orders.md"),
        ("BR-2", "inferred", "rules-orders.md"),
    ]
    assert rules[0].text.endswith("with care") and rules[0].source == "interview"


def test_ac4_every_failure_names_no_rule_text_or_value(tmp_path):
    """REQ-081 AC4: principle 8 (messages name the rule, the file and the id)."""
    bad = GOOD["rules-orders.md"].replace("confirmed", "unsure").replace("BR-2", "BR-1")
    found = changed(tmp_path, "rules-orders.md", bad)
    assert found
    no_value(found)


# --- the writer -------------------------------------------------------------------------------


def run(root: Path, *args: str) -> int:
    return domain_model.main(["--root", str(root), *args])


def test_ac4_init_writes_four_files_that_pass_and_refuses_an_overwrite(tmp_path, capsys):
    """REQ-081 AC4: answer 2 (`init` from the kit templates; never over a model)."""
    model(tmp_path, {})
    assert run(tmp_path, "init", "--area", "orders") == 0
    names = sorted(p.name for p in (tmp_path / "docs" / "domain").iterdir())
    assert names == ["data.md", "entities.md", "regulations.md", "rules-orders.md"]
    assert domain_model.findings(tmp_path) == []
    assert run(tmp_path, "init", "--area", "stock") == 1
    assert "the domain model exists" in capsys.readouterr().out


def test_ac4_rule_numbers_across_areas_and_refuses_the_201st(tmp_path, capsys):
    """REQ-081 AC4: answer 2 and 8 (the next free `BR-<n>` across the folder; 200 per file)."""
    model(tmp_path)
    args = ["--text", "stock is counted daily", "--source", "interview", "--where", "notes"]
    assert run(tmp_path, "rule", "--area", "stock", *args, "--owner", "ops", "--inferred") == 0
    text = (tmp_path / "docs" / "domain" / "rules-stock.md").read_text(encoding="utf-8")
    assert "- BR-3: stock is counted daily; source: interview, notes; owner: ops; inferred" in text
    assert run(tmp_path, "rule", "--area", "new-area", *args, "--owner", "ops") == 0
    assert "- BR-4: " in (tmp_path / "docs" / "domain" / "rules-new-area.md").read_text("utf-8")
    full = "".join(
        f"- BR-{n}: r; source: code, a.py:1; owner: o; inferred\n" for n in range(5, 205)
    )
    (tmp_path / "docs" / "domain" / "rules-full.md").write_text(full, encoding="utf-8")
    assert run(tmp_path, "rule", "--area", "full", *args, "--owner", "ops") == 1
    assert "split by area" in capsys.readouterr().out
    assert domain_model.findings(tmp_path) == []


def test_ac4_a_guarded_value_is_refused_naming_the_class(tmp_path, capsys):
    """REQ-081 AC4: answer 2 (each value is scanned before it is written; SPEC-0042)."""
    model(tmp_path)
    before = (tmp_path / "docs" / "domain" / "data.md").read_text(encoding="utf-8")
    assert run(tmp_path, "classify", "--item", f"card {CARD}", "--class", "payment") == 1
    out = capsys.readouterr().out
    assert "data guard" in out and CARD not in out
    assert (tmp_path / "docs" / "domain" / "data.md").read_text(encoding="utf-8") == before


def test_ac4_classify_entity_and_regulation_write_checked_lines(tmp_path):
    """REQ-081 AC4: answer 2 (each command writes one line in rule 7's form)."""
    model(tmp_path)
    assert run(tmp_path, "classify", "--item", "delivery address", "--class", "personal") == 0
    assert run(tmp_path, "classify", "--item", "delivery address", "--class", "public") == 1
    assert run(tmp_path, "classify", "--item", "x", "--class", "secret") == 1
    assert run(tmp_path, "entity", "--name", "Parcel", "--meaning", "What ships",
               "--relates", "Order:many-one:an order ships in parcels") == 0  # fmt: skip
    assert (
        run(tmp_path, "entity", "--name", "Box", "--meaning", "m", "--relates", "Nope:one-one:r")
        == 1
    )
    assert (
        run(tmp_path, "regulation", "--id", "zz-shop.zz-rule", "--scope", "out", "--reason", "r")
        == 1
    )
    assert (
        run(tmp_path, "regulation", "--id", "zz-shop.zz-none", "--scope", "in", "--reason", "r")
        == 1
    )
    assert domain_model.findings(tmp_path) == []
    text = (tmp_path / "docs" / "domain" / "entities.md").read_text(encoding="utf-8")
    assert "## Parcel\n\nWhat ships\n\n- relates to Order: many to one, an order ships" in text


def test_ac4_confirm_changes_only_the_status_word(tmp_path):
    """REQ-081 AC4: answer 3 and rule 9 (after the person's yes only the status word changes)."""
    model(tmp_path)
    path = tmp_path / "docs" / "domain" / "rules-orders.md"
    before = path.read_text(encoding="utf-8")
    assert run(tmp_path, "confirm", "--id", "BR-2") == 0
    assert path.read_text(encoding="utf-8") == before.replace(
        "owner: finance lead; inferred", "owner: finance lead; confirmed"
    )
    assert run(tmp_path, "confirm", "--id", "BR-2") == 1  # already confirmed
    assert run(tmp_path, "confirm", "--id", "BR-9") == 1


def test_ac4_the_forms_live_in_domain_model_only():
    """REQ-081 AC4: answer 10 (one place holds the `BR-<n>` pattern; its readers import it)."""
    for name in ("check_domains.py", "steward_onboard.py"):
        text = (AGK / name).read_text(encoding="utf-8")
        assert "domain_model" in text, name
        assert "BR-" not in text, name
