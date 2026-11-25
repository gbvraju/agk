"""Tests of the designs comparison of the stack record (SPEC-0073 rule 8, amendment 236 item 2,
SPEC-0072 rule 5; REQ-080 AC5; brief #1952, ADR-0808).

The stack skill compares `[quality] designs` interface designs for each layer only when
`[architecture] layers` has more than the single default layer `src`, and keeps the rejected one
in a `## Designs compared` section of the stack ADR after `## Decision`, outside the `- Option`
bullets. `pins.OPTION`, `pins.CHOSEN` and `front_door.chosen_services` read the same option with
the section present or absent; the template carries the section empty. Fixtures in `tmp_path`
only: invented data (example.com), no network.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import front_door  # noqa: E402
from gates import pins  # noqa: E402

import config  # noqa: E402

pytestmark = pytest.mark.usefixtures("no_network")

SKILL = KIT_ROOT / "skills" / "stack" / "SKILL.md"
TEMPLATE = KIT_ROOT / "kit" / "templates" / "stack-adr.md"
STACK = """# ADR-0002: Stack options

- Status: Accepted

## Decision

1. **Options**
   - Option A — Python. External services: Mailrelay Example, Paygate Example. Practices: tests.
   - Option B — Node. External services: Queuehub Example. Practices: tests.
2. **Practices**
   - tests: judgement
3. **Chosen**: Option A — the invented need of example.com
{designs}
## Consequences

None.
"""
COMPARED = """
## Designs compared

- api layer: chosen: one call per order, kept in Option A; rejected: one call per line of an
  order (more calls for the busiest hour)
- data layer: chosen: one table per order; rejected: one document per shop (harder recovery)
"""


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the stack record parse opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def parsed(root: Path, designs: str) -> tuple[list[tuple[str, str]], str, list[str]]:
    text = STACK.format(designs=designs)
    path = root / "docs" / "adr" / "0002-stack-options.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    options = [m.groups() for ln in text.splitlines() if (m := pins.OPTION.match(ln))]
    chosen = pins.CHOSEN.search(text)
    assert chosen is not None
    return options, chosen.group(1), front_door.chosen_services(root)


def test_req_080_ac5_the_parse_reads_the_same_option_with_or_without_the_section(tmp_path):
    before = parsed(tmp_path / "before", "")
    after = parsed(tmp_path / "after", COMPARED)
    assert before == after
    assert after[1] == "A" and after[2] == ["Mailrelay Example", "Paygate Example"]
    assert [letter for letter, _ in after[0]] == ["A", "B"]


def test_req_080_ac5_the_template_carries_the_section_empty_after_the_decision():
    text = TEMPLATE.read_text(encoding="utf-8")
    heads = [ln[3:] for ln in text.split("\n") if ln.startswith("## ")]
    assert heads.index("Decision") + 1 == heads.index("Designs compared")
    body = text.split("## Designs compared\n", 1)[1].split("\n## ", 1)[0]
    assert body.strip() == ""
    assert not any(pins.OPTION.match(ln) for ln in body.split("\n"))


def test_req_080_ac5_the_skill_compares_designs_only_for_more_than_one_layer():
    text = " ".join(SKILL.read_text(encoding="utf-8").split())
    assert "[architecture] layers" in text and "the single default layer `src`" in text
    assert "[quality] designs" in text and "## Designs compared" in text
    assert "with `designs = 1`, write one design and say so" in text
    assert "outside the `- Option` bullets" in text


@pytest.mark.parametrize(
    ("toml", "want"),
    [
        ("", 2),
        ("[quality]\ndesigns = 1\n", 1),
        ('[delivery]\nwork_type = "pilot"\n', 1),
        ('[delivery]\nwork_type = "pilot"\n\n[quality]\ndesigns = 2\n', 2),
    ],
)
def test_req_080_ac5_the_number_of_designs_is_the_quality_setting(tmp_path, toml, want):
    (tmp_path / "agk.toml").write_text(f'mode = "init"\n\n{toml}', encoding="utf-8")
    assert config.quality_settings(tmp_path)["designs"] == want


def test_req_080_ac5_a_refused_designs_value_names_the_setting(tmp_path):
    toml = 'mode = "init"\n\n[quality]\ndesigns = 7\n'
    (tmp_path / "agk.toml").write_text(toml, encoding="utf-8")
    with pytest.raises(config.QualitySettingError) as caught:
        config.quality_settings(tmp_path)
    assert "quality.designs" in str(caught.value) and "7" not in str(caught.value)
