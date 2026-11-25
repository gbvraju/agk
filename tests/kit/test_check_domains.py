"""Tests of `check_domains.py` (SPEC-0074 rule 2; REQ-081 AC1; brief #1935).

A domain pack, `config/domains/<slug>.toml`, is checked data: a missing required key or section,
an unknown key, a wrong type (a `bool` is never a number), a `domain` that is not the file's name,
an id used twice, a `[[discovery]]` id that reuses a topic, fixed, playbook or grill id, a dangling
`regulation` or `constraint` reference, a regulation, constraint or gate with neither `source` nor
`basis = "expected"`, a `judgement` gate on no critical regulation and a line the data guard flags
each fail naming the rule, the file and the key, never a value. The seed packs pass, and
`check_playbooks.findings` carries a pack's problem. Fixtures in `tmp_path` only: invented data,
no network.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_domains  # noqa: E402
import check_playbooks  # noqa: E402

SCRIPT = KIT_ROOT / "scripts" / "agk" / "check_domains.py"
REL = "config/domains/zz-shop.toml"

GOOD = """format = 1
domain = "zz-shop"
title = "An invented shop for the tests"
as_of = "2026-11-25"

[[terms]]
term = "basket"
meaning = "The items a buyer holds before paying"
synonyms = ["cart"]

[[kpis]]
id = "zz-conversion"
text = "Share of visits that end in an order"
unit = "percent"

[[regulations]]
id = "zz-rule"
title = "An invented consumer rule"
jurisdiction = "global"
source = "https://example.com/zz-rule"
as_of = "2026-11-25"
critical = true

[[constraints]]
id = "zz-keep"
attribute = "retention"
scenario = "stimulus: an order is closed; response: it is kept; measure: 5 years"
hard = true
regulation = "zz-rule"
basis = "expected"

[[discovery]]
id = "zz-returns"
text = "How do buyers return an item?"
depth = "standard"
critical = false

[[acceptance]]
id = "zz-accept"
text = "A closed order is still readable after a year"
constraint = "zz-keep"

[[gates]]
id = "zz-scope"
kind = "judgement"
text = "A person confirms which systems hold orders"
owner_only = false
regulation = "zz-rule"
basis = "expected"
"""


def write(root: Path, text: str, rel: str = REL) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def found(root: Path, text: str) -> list[str]:
    write(root, text)
    return check_domains.findings(root)


def test_ac1_a_good_pack_and_a_terms_only_pack_pass(tmp_path):
    """REQ-081 AC1: SPEC-0074 rule 2 (a sound pack passes; only `[[terms]]` is required)."""
    assert found(tmp_path, GOOD) == []
    terms_only = GOOD.split("\n[[kpis]]")[0] + "\n"
    assert found(tmp_path, terms_only) == []


def test_ac1_no_folder_is_ok_none(tmp_path):
    """REQ-081 AC1: SPEC-0074 rule 2 (no `config/domains/`: nothing to check)."""
    assert check_domains.findings(tmp_path) == []
    proc = subprocess.run(  # nosec B603 - fixed argument list
        [sys.executable, str(SCRIPT), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0 and proc.stdout.strip() == "ok domains (none)"


@pytest.mark.parametrize(
    ("old", "new", "key"),
    [
        ('title = "An invented shop for the tests"\n', "", "title"),
        ("[[terms]]", "[[zz_extra]]", "terms"),
        ('unit = "percent"', 'unit = "percent"\nzz_colour = "blue"', "zz_colour"),
        ("format = 1", "format = true", "format"),
        ("critical = true", 'critical = "true"', "critical"),
        ('depth = "standard"', 'depth = "medium"', "depth"),
        ("critical = false\n", "", "critical"),
        ('domain = "zz-shop"', 'domain = "zz-other"', "domain"),
        ('as_of = "2026-11-25"\n\n[[terms]]', 'as_of = "25 Nov"\n\n[[terms]]', "as_of"),
        ('id = "zz-accept"', 'id = "zz-keep"', "id"),
        ('id = "zz-returns"', 'id = "data-rules"', "id"),
        ('id = "zz-returns"', 'id = "compliance"', "id"),
        ('regulation = "zz-rule"\nbasis', 'regulation = "zz-none"\nbasis', "regulation"),
        ('constraint = "zz-keep"', 'constraint = "zz-gone"', "constraint"),
        ('source = "https://example.com/zz-rule"\n', "", "source"),
        ('hard = true\nregulation = "zz-rule"\nbasis = "expected"', "hard = true", "source"),
        ('owner_only = false\nregulation = "zz-rule"\nbasis = "expected"', "owner_only = false",
         "source"),
        ('attribute = "retention"', 'attribute = "colour"', "attribute"),
        ('basis = "expected"\n\n[[discovery]]', 'basis = "measured"\n\n[[discovery]]', "basis"),
        ("critical = true", "critical = false", "regulation"),
    ],
)  # fmt: skip
def test_ac1_each_malformed_pack_fails_naming_the_rule_file_and_key(tmp_path, old, new, key):
    """REQ-081 AC1: SPEC-0074 rule 2 (each failure names the rule, the file and the key)."""
    assert old in GOOD
    lines = found(tmp_path, GOOD.replace(old, new, 1))
    assert lines, (old, new)
    assert any(line.startswith(f"rule 2: {REL}: ") for line in lines), lines
    assert any(line.endswith(f"(key: {key})") for line in lines), lines
    for value in ("zz-other", "25 Nov", "colour", "blue"):
        assert all(value not in line.split("(key:")[0] for line in lines), lines


def test_ac1_a_reused_playbook_or_grill_id_fails(tmp_path):
    """REQ-081 AC1: SPEC-0074 rule 2 (a `[[discovery]]` id of a playbook, its grill ids too)."""
    write(
        tmp_path,
        '[[discovery]]\nid = "zz-pb"\ntext = "Who?"\ndepth = "light"\ncritical = true\n',
        "config/playbooks/default.toml",
    )
    lines = found(tmp_path, GOOD.replace('id = "zz-returns"', 'id = "zz-pb"'))
    assert lines == [f"rule 2: {REL}: a `[[discovery]]` id reuses a kit question id (key: id)"]


def test_ac1_a_line_the_data_guard_flags_fails_naming_the_class(tmp_path):
    """REQ-081 AC1: SPEC-0074 rule 2 (any line `guard.scan_text` flags; no value printed)."""
    text = GOOD.replace("https://example.com/zz-rule", "mail zz.person@zz-mail.test")
    lines = found(tmp_path, text)
    assert any("data guard flags EMAIL" in line and "(key: source)" in line for line in lines)
    assert all("zz.person" not in line for line in lines)


def test_ac1_two_packs_with_one_domain_fail_naming_both_files(tmp_path):
    """REQ-081 AC1: SPEC-0074 rule 14 (the same `domain` twice)."""
    write(tmp_path, GOOD)
    write(tmp_path, GOOD, "config/domains/zz-copy.toml")
    lines = check_domains.findings(tmp_path)
    assert (
        "rule 2: config/domains/zz-shop.toml: the domain of config/domains/zz-copy.toml "
        "(key: domain)"
    ) in lines


def test_ac1_a_bom_and_crlf_pack_reads_the_same(tmp_path):
    """REQ-081 AC1: SPEC-0074 rule 2 (a BOM or CRLF is read as UTF-8 TOML)."""
    (tmp_path / "config" / "domains").mkdir(parents=True)
    (tmp_path / REL).write_bytes(b"\xef\xbb\xbf" + GOOD.replace("\n", "\r\n").encode())
    assert check_domains.findings(tmp_path) == []
    (tmp_path / REL).write_text("format = [", encoding="utf-8")
    assert check_domains.findings(tmp_path) == [
        f"rule 2: {REL}: the pack is not readable TOML (key: format)"
    ]


def test_ac1_a_stale_as_of_warns_and_never_fails(tmp_path):
    """REQ-081 AC7: SPEC-0074 rule 14 (an `as_of` older than `stale_months` warns)."""
    write(tmp_path, GOOD.replace('as_of = "2026-11-25"', 'as_of = "2020-01-01"', 1))
    assert check_domains.findings(tmp_path) == []
    import datetime

    warn = check_domains.stale(tmp_path, datetime.date(2026, 11, 25))
    assert warn == [f"warn domains: {REL} as_of is older than [domain] stale_months (verify)"]
    assert check_domains.stale(tmp_path, datetime.date(2020, 6, 1)) == []


def test_ac1_the_seed_packs_pass_and_the_kit_check_prints_two_packs():
    """REQ-081 AC1: SPEC-0074 rule 3 (two seed packs, one regulated, one operational)."""
    names = [p.name for p in check_domains.packs(KIT_ROOT)]
    assert names == ["field-service.toml", "payments.toml"]
    assert check_domains.findings(KIT_ROOT) == []
    proc = subprocess.run(  # nosec B603 - fixed argument list
        [sys.executable, str(SCRIPT), "--root", str(KIT_ROOT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0 and proc.stdout.strip() == "ok domains (2 packs)"
    import tomllib

    pay = tomllib.loads((KIT_ROOT / "config/domains/payments.toml").read_text(encoding="utf-8"))
    ops = tomllib.loads(
        (KIT_ROOT / "config/domains/field-service.toml").read_text(encoding="utf-8")
    )
    assert any(r["critical"] for r in pay["regulations"]) and "regulations" not in ops


def test_ac1_the_playbooks_step_carries_a_pack_problem(tmp_path):
    """REQ-081 AC1: SPEC-0074 rule 2 (`check_playbooks.findings` runs the pack check)."""
    write(tmp_path, GOOD.replace("format = 1", "format = 2"))
    lines = check_playbooks.findings(tmp_path)
    assert f"rule 2: {REL}: the key has the wrong value (key: format)" in lines
    assert check_playbooks.findings(tmp_path, []) == []  # a named playbook alone reads no pack
    proc = subprocess.run(  # nosec B603 - fixed argument list
        [sys.executable, str(KIT_ROOT / "scripts/agk/check_playbooks.py"), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert f"FAIL playbooks: rule 2: {REL}: the key has the wrong value (key: format)" in (
        proc.stdout
    )
