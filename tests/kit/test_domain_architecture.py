"""Tests of the domain constraints in the architecture record (SPEC-0074 rule 8, amendment 241 to
SPEC-0072 rule 5; REQ-081 AC5; brief #1955, ADR-0811).

With `[domain] packs` set, each composed constraint is one row of the record's
`## Quality scenarios`, ending ` [<pack>.<constraint>]`; a constraint with no row, or a row citing
no composed constraint, fails naming the id (the `domain-scenarios` step). Where
`docs/domain/data.md` exists, each flow of `## Threats` that names a classified data item carries
`(class: <class>)`; a flow without it, or a class outside the five, fails naming the flow's number
and the item (the `domain-threats` step), and without `data.md` that step is `not run: no data
classification`. With no packs and no `data.md` neither step applies, so a record passes as today.
Fixtures in `tmp_path` only: invented packs and data (example.com), no network.
"""

from __future__ import annotations

import json
import re
import shutil
import socket
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
AGK = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(AGK))

import check_domains  # noqa: E402
import front_door  # noqa: E402
import run_gates  # noqa: E402
from gates import domain_scenarios, domain_threats  # noqa: E402

pytestmark = pytest.mark.usefixtures("no_network")

HEAD = 'format = 1\ndomain = "{name}"\ntitle = "An invented pack"\nas_of = "2026-11-25"\n'
TERM = '\n[[terms]]\nterm = "{name} term"\nmeaning = "An invented term"\nsynonyms = []\n'
CONSTRAINT = (
    '\n[[constraints]]\nid = "{id}"\nattribute = "retention"\nscenario = "stimulus: an order is'
    ' closed; response: it is kept; measure: {years} years"\nhard = {hard}\nbasis = "expected"\n'
)
ROW = "- retention: an order is closed -> it is kept (at least {years} years) [{cite}]"
OTHER = "- security: a stranger calls the order api -> it is refused (100 percent of calls)"
THREATS = (
    "- web to api: S, T, I: TLS on every call (class: payment)\n"
    "- api to Mailrelay Example: I: accepted: the receipts hold only a thank-you"
)
DATA = "# Data classification\n\n- card number: payment\n- order total: confidential\n"
MISSING = "SPEC-0074 rule 8: a domain constraint has no quality scenario"
UNKNOWN = "SPEC-0074 rule 8: a quality scenario cites no composed domain constraint"
UNCLASSED = "SPEC-0074 rule 8: a threat flow does not carry the class of its data item"
BAD_CLASS = "SPEC-0074 rule 8: a threat flow names a class outside the five"
SCENARIOS = f"{front_door.RECORD}; section: Quality scenarios"


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the domain architecture check opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def pack(name: str, *constraints: tuple[str, int, str]) -> str:
    body = "".join(CONSTRAINT.format(id=i, years=y, hard=h) for i, y, h in constraints)
    return HEAD.format(name=name) + TERM.format(name=name) + body


def project(
    root: Path,
    listed: list[str] | None = ("zz-shop",),
    scenarios: str = "",
    threats: str = THREATS,
    data: str | None = None,
) -> Path:
    """A record with its quality sections, one invented pack with two constraints, `agk.toml`."""
    write(
        root,
        "config/domains/zz-shop.toml",
        pack("zz-shop", ("orders-kept", 5, "true"), ("logs-kept", 1, "false")),
    )
    table = "" if listed is None else f"[domain]\npacks = {json.dumps(list(listed))}\n"
    write(root, "agk.toml", table)
    rows = scenarios or "\n".join(
        [
            OTHER,
            ROW.format(years=5, cite="zz-shop.orders-kept"),
            ROW.format(years=1, cite="zz-shop.logs-kept"),
        ]
    )
    record = (
        f"# Architecture\n\n## Quality scenarios\n\n{rows}\n\n## Threats\n\n{threats}\n\n"
        "## Operations\n\n- traced: each order call\n"
    )
    write(root, front_door.RECORD, record)
    if data is not None:
        write(root, "docs/domain/data.md", data)
    return root


def scenario_problems(root: Path) -> list[tuple[str, str]]:
    assert domain_scenarios.applies(root) and domain_scenarios.skipped(root) is None
    return domain_scenarios.check(root, {})


# --- constraints become quality scenarios (brief answer 1) --------------------------------------


def test_req_081_ac5_every_constraint_with_its_row_passes(tmp_path):
    """REQ-081 AC5: a constraint becomes a quality-scenario row, citing its pack id."""
    assert scenario_problems(project(tmp_path)) == []


def test_req_081_ac5_a_constraint_with_no_row_fails_naming_its_id(tmp_path):
    rows = "\n".join([OTHER, ROW.format(years=5, cite="zz-shop.orders-kept")])
    assert scenario_problems(project(tmp_path, scenarios=rows)) == [
        (MISSING, f"{SCENARIOS}; id: zz-shop.logs-kept")
    ]


def test_req_081_ac5_a_row_for_an_unknown_id_fails_naming_it(tmp_path):
    rows = "\n".join(
        [
            ROW.format(years=5, cite="zz-shop.orders-kept"),
            ROW.format(years=1, cite="zz-shop.logs-kept"),
            ROW.format(years=2, cite="zz-shop.nothing-here"),
        ]
    )
    assert scenario_problems(project(tmp_path, scenarios=rows)) == [
        (UNKNOWN, f"{SCENARIOS}; id: zz-shop.nothing-here")
    ]


def test_req_081_ac5_a_citation_out_of_its_form_is_never_echoed(tmp_path):
    rows = "\n".join(
        [
            ROW.format(years=5, cite="zz-shop.orders-kept"),
            ROW.format(years=1, cite="zz-shop.logs-kept"),
            ROW.format(years=2, cite="Some Words"),
        ]
    )
    found = scenario_problems(project(tmp_path, scenarios=rows))
    assert found == [(UNKNOWN, f"{SCENARIOS}; id: not of the form <pack>.<constraint>")]


def test_req_081_ac5_a_cited_row_keeps_the_form_of_build_g(tmp_path):
    """The citation is one optional tail of the scenario line; the form check still passes it."""
    line = ROW.format(years=5, cite="zz-shop.orders-kept")
    assert front_door.quality_line_ok("Quality scenarios", line)
    assert not front_door.quality_line_ok("Quality scenarios", line + " trailing words")
    # a pack's attribute word is taken only on a cited row; an uncited row keeps the eight
    assert not front_door.quality_line_ok("Quality scenarios", line.rsplit(" [", 1)[0])


def test_req_081_ac5_a_row_naming_another_attribute_fails_naming_its_id(tmp_path):
    """Fix list on 92250ef9 item 4: the row names its constraint's own attribute."""
    rows = "\n".join(
        [
            ROW.format(years=5, cite="zz-shop.orders-kept").replace("- retention:", "- audit:"),
            ROW.format(years=1, cite="zz-shop.logs-kept"),
        ]
    )
    assert scenario_problems(project(tmp_path, scenarios=rows)) == [
        (
            "SPEC-0074 rule 8: a quality scenario names another attribute than its constraint",
            f"{SCENARIOS}; id: zz-shop.orders-kept",
        )
    ]


def test_req_081_ac5_two_packs_with_one_constraint_are_each_cited(tmp_path):
    """Fix list on 92250ef9 item 3 (brief answer 6): cited by pack, so both rows."""
    root = project(tmp_path, listed=["zz-shop", "zz-other"])
    write(root, "config/domains/zz-other.toml", pack("zz-other", ("orders-kept", 5, "true")))
    assert sorted(check_domains.cited(root)) == [
        "zz-other.orders-kept",
        "zz-shop.logs-kept",
        "zz-shop.orders-kept",
    ]
    assert scenario_problems(root) == [(MISSING, f"{SCENARIOS}; id: zz-other.orders-kept")]
    text = (root / front_door.RECORD).read_text(encoding="utf-8")
    row = ROW.format(years=5, cite="zz-other.orders-kept")
    write(root, front_door.RECORD, text.replace("## Threats", f"{row}\n\n## Threats"))
    assert scenario_problems(root) == []


def test_req_081_ac5_no_packs_adds_nothing(tmp_path):
    """`[domain] packs` empty or absent: the step does not apply and the record passes as today."""
    for listed in ([], None):
        root = project(tmp_path / str(listed), listed=listed, scenarios=OTHER)
        assert not domain_scenarios.applies(root)
        assert not domain_threats.applies(root)


def test_req_081_ac5_a_record_without_quality_sections_stays_held(tmp_path):
    root = project(tmp_path)
    write(root, front_door.RECORD, "# Architecture\n\n## Context\n\nAn invented shop.\n")
    assert not domain_scenarios.applies(root)


def test_req_081_ac5_a_refused_domain_table_is_not_run(tmp_path):
    root = project(tmp_path)
    write(root, "agk.toml", '[domain]\npacks = ["zz-shop", "zz-shop"]\n')
    assert domain_scenarios.applies(root)
    assert domain_scenarios.skipped(root) == "[domain] is refused (setting: domain)"


# --- threats carry the data class (brief answer 2) ----------------------------------------------


def test_req_081_ac5_a_flow_carrying_its_class_passes(tmp_path):
    root = project(tmp_path, data=DATA, threats=THREATS.replace("TLS", "the card number under TLS"))
    assert domain_threats.applies(root) and domain_threats.skipped(root) is None
    assert domain_threats.check(root, {}) == []


def test_req_081_ac5_a_flow_with_an_unclassified_item_fails_naming_it(tmp_path):
    threats = THREATS.replace("TLS on every call (class: payment)", "the order total under TLS")
    root = project(tmp_path, data=DATA, threats=threats)
    assert domain_threats.check(root, {}) == [
        (UNCLASSED, f"{front_door.RECORD}; section: Threats; flow: 1; item: order total")
    ]


def test_req_081_ac5_an_item_ending_in_punctuation_is_still_found(tmp_path):
    """Fix list on 92250ef9 item 2: the match does not hang on the item's last character."""
    data = DATA + "- card (PAN): payment\n- card no.: payment\n"
    for item in ("card (PAN)", "card no."):
        threats = THREATS.replace("TLS on every call (class: payment)", f"the {item} under TLS")
        root = project(tmp_path / item.replace(" ", "-"), data=data, threats=threats)
        assert domain_threats.check(root, {}) == [
            (UNCLASSED, f"{front_door.RECORD}; section: Threats; flow: 1; item: {item}")
        ]


def test_req_081_ac5_a_class_outside_the_five_fails(tmp_path):
    root = project(
        tmp_path, data=DATA, threats=THREATS.replace("(class: payment)", "(class: secret)")
    )
    assert domain_threats.check(root, {}) == [
        (BAD_CLASS, f"{front_door.RECORD}; section: Threats; flow: 1")
    ]


def test_req_081_ac5_no_data_classification_is_not_run(tmp_path):
    root = project(tmp_path)
    assert domain_threats.applies(root)
    assert domain_threats.skipped(root) == "no data classification"


def test_req_081_ac5_data_without_packs_still_checks_the_threats(tmp_path):
    root = project(tmp_path, listed=None, scenarios=OTHER, data=DATA)
    assert not domain_scenarios.applies(root)
    assert domain_threats.applies(root) and domain_threats.check(root, {}) == []


def test_req_081_ac5_the_runner_runs_both_steps_and_prints_not_run(tmp_path, capsys):
    """Through `run_gates`: a missing row fails by the step's name; no data.md is `not run`."""
    rows = "\n".join([OTHER, ROW.format(years=5, cite="zz-shop.orders-kept")])
    root = project(tmp_path, scenarios=rows)
    shutil.copytree(KIT_ROOT / "config" / "playbooks", root / "config" / "playbooks")
    lines = [line for _, line in run_gates.results(root)]
    assert f"domain-scenarios: {MISSING} (path class: {SCENARIOS}; id: zz-shop.logs-kept)" in lines
    assert "domain-threats: no data classification" in lines
    run_gates.main(["--root", str(root)])
    out = capsys.readouterr().out
    assert "not run domain-threats: no data classification" in out


# --- the class stays closed (brief answer 8) ----------------------------------------------------


def test_req_081_ac5_the_citation_form_is_one_pattern(tmp_path):
    """One pattern of `<pack>.<constraint>`, in the composition's reader; both checks import it."""
    source = check_domains.CITATION.pattern
    holders = [
        p.relative_to(KIT_ROOT).as_posix()
        for p in sorted(AGK.rglob("*.py"))
        if source in p.read_text(encoding="utf-8")
    ]
    assert holders == ["scripts/agk/check_domains.py"]
    for name in ("front_door.py", "engines.py"):
        assert re.search(r"check_domains\.CITATION", (AGK / name).read_text(encoding="utf-8"))
