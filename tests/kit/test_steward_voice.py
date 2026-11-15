"""Tests of scripts/agk/steward_voice.py, the steward's voice (brief #1382, ADR-0582; REQ-069 AC2).

Recorded replies (invented, example.com): a ten-option decision shows three or fewer, a recommendation
and "more"; grouping, evidence-dropping and the sharper question each produce their form; a status is
three lines; a 40-line summary fails and its shortened form passes; a form of four inputs shows each
default and a three-line confirmation; a kit term fails; the daily list counts shortened replies; the
role file names the voice. No network, no model.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import steward_daily  # noqa: E402
import steward_voice as voice  # noqa: E402

TEN = {
    "decision": "how the sign-in page looks first",
    "recommend": "Plain email link",
    "because": "it costs least and ships this week",
    "options": [
        {"label": f"Idea {n}", "score": n} for n in range(1, 10)
    ]
    + [{"label": "Plain email link", "score": 5}],
}


def lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def test_req069_a_ten_option_decision_shows_three_a_recommendation_and_more():
    text = voice.choose(TEN)
    assert voice.problems(text) == [], text
    assert "Plain email link because" in text and "I recommend" in text
    assert "say more for 7 other options" in text
    shown = [o["label"] for o in TEN["options"] if o["label"] in text]
    assert len(shown) == 3 and "Plain email link" in shown and "Idea 9" in shown, shown
    assert text.splitlines()[0].startswith("Decision: ")


def test_req069_three_options_take_the_one_decision_shape():
    data = {
        "decision": "the first release date",
        "options": [{"label": "1 March"}, {"label": "15 March"}, {"label": "1 April"}],
        "recommend": "15 March",
        "because": "testing needs two more weeks",
    }
    text = voice.choose(data)
    assert all(len(line) <= 100 for line in text.splitlines())
    flat = text.replace("\n", " · ")
    assert flat.startswith("Decision: the first release date · Options: A 1 March / B 15 March")
    assert "I recommend B 15 March because testing needs two more weeks · Reply A, B or C" in flat
    assert voice.problems(text) == []


def test_req069_kinds_of_options_are_grouped():
    data = {
        "decision": "what to fix after the pilot",
        "recommend": "quick fixes",
        "because": "they cost a day each",
        "options": [{"label": f"Fix {n}", "group": "quick fixes"} for n in range(3)]
        + [{"label": f"Change {n}", "group": "design changes"} for n in range(4)]
        + [{"label": f"Idea {n}", "group": "later ideas"} for n in range(3)],
    }
    text = voice.choose(data)
    assert "3 quick fixes, 4 design changes, 3 later ideas" in text
    assert "which group to open" in text and "I recommend quick fixes" in text
    assert voice.problems(text) == [], text


def test_req069_options_the_evidence_rules_out_are_dropped_and_counted():
    data = {
        "decision": "where the shop's data is kept",
        "recommend": "Region one",
        "because": "it is nearest to the customers",
        "options": [{"label": "Region one"}, {"label": "Region two"}]
        + [{"label": f"Far {n}", "ruled_out": "outside the allowed area"} for n in range(5)],
    }
    text = voice.choose(data)
    assert "Dropped 5 options the evidence rules out" in text
    assert "Far 0" not in text and voice.problems(text) == [], text


def test_req069_many_unranked_options_ask_one_sharper_question():
    data = {
        "decision": "which payment provider to use",
        "options": [{"label": f"Provider {n}"} for n in range(6)],
        "ask": {
            "question": "is speed or cost more important here?",
            "choices": ["speed", "cost"],
            "recommend": "cost",
            "because": "the pilot has a small budget",
        },
    }
    text = voice.choose(data)
    assert "is speed or cost more important here?" in text
    assert "Provider" not in text and "I recommend cost" in text
    assert voice.problems(text) == [], text


def test_req069_a_status_reply_is_three_lines():
    good = "Done: the sign-in page\nIn progress: the order list\nWaiting on you: reply yes to the date"
    assert voice.problems(good) == []
    four = good + "\nAlso: the logo"
    assert any("rule 5" in p for p in voice.problems(four))


def test_req069_a_forty_line_summary_fails_and_its_short_form_passes():
    long = "\n".join([f"- point {n} about the work this week" for n in range(40)])
    found = voice.problems("Here is everything.\n" + long)
    assert any("rule 2" in p for p in found), found
    short = (
        "The pilot is on track; one answer is needed from you.\n"
        "- Sign-in works for invited people\n"
        "- The order list ships on Friday\n"
        "- Reply yes to keep the 15 March date\n"
        "Say details for the full list."
    )
    assert voice.problems(short) == []


def test_req069_the_first_line_is_an_ask_or_an_answer():
    for first in ("# Summary", "Hello!", "Great question.", "Sure"):
        found = voice.problems(f"{first}\nThe date is 15 March.")
        assert any("rule 1" in p for p in found), (first, found)


def test_req069_a_long_line_and_too_many_choices_fail():
    assert any("rule 2" in p for p in voice.problems("The answer is " + "x" * 120))
    menu = "Pick one of these.\nA one\nB two\nC three\nD four\nI recommend A because it is fast"
    assert any("rule 3" in p for p in voice.problems(menu))
    assert voice.problems(menu + "\nSay more for other options") == []


def test_req069_a_decision_without_a_recommendation_fails():
    text = "Decision: the date · Options: A 1 March / B 15 March · Reply A or B"
    assert any("rule 4" in p for p in voice.problems(text))


def test_req069_a_kit_term_fails_and_plain_words_pass():
    for term in ("Merged pull request 12.", "See ADR-0001 for it.", "Run make lint now."):
        found = voice.problems(term)
        assert any("rule 8" in p and "kit term" in p for p in found), (term, found)
        assert term not in " ".join(found)
    assert voice.problems("Your shop opens on 15 March at 09:00 IST.") == []


def test_req069_a_form_of_four_inputs_shows_each_default_and_a_short_confirmation():
    fields = [
        {"name": "Shop name", "default": "Example Shop"},
        {"name": "Contact", "default": "owner@example.com"},
        {"name": "Currency", "default": "INR", "choices": ["INR", "USD"]},
        {"name": "Launch date", "default": "15 March"},
    ]
    form = voice.form(fields)
    for field in fields:
        assert f"{field['name']}: {field['default']}" in form
    assert form.splitlines()[0].startswith("4 answers needed") and "reply yes" in form
    assert voice.problems(form) == [], form
    done = voice.confirm(fields, {"Currency": "USD"})
    assert len(lines(done)) <= 3 and "Currency: USD" in done and "Shop name: Example Shop" in done
    assert voice.problems(done) == []
    assert not done.startswith("Confirmed:")


def test_req069_the_check_command_names_the_rule(tmp_path, capsys):
    bad = tmp_path / "reply.txt"
    bad.write_text("# Status\n" + "\n".join(f"- item {n}" for n in range(8)), encoding="utf-8")
    assert voice.main(["check", str(bad)]) == 1
    out = capsys.readouterr().out
    assert "rule 1" in out and "rule 2" in out and "item 3" not in out
    good = tmp_path / "good.txt"
    good.write_text("The site is live at https://example.com.\n", encoding="utf-8")
    assert voice.main(["check", str(good)]) == 0
    data = tmp_path / "ten.json"
    data.write_text(json.dumps(TEN), encoding="utf-8")
    assert voice.main(["choose", str(data)]) == 0
    assert "say more for 7 other options" in capsys.readouterr().out


def test_req069_the_daily_list_counts_shortened_replies():
    memory = [
        {"id": 1, "body": "Shortened: steward reply (voice rules 2)\n\nWho: AGK steward",
         "created_at": "2026-11-15T08:00:00Z"},
        {"id": 2, "body": "Shortened: steward reply (voice rules 3)\n\nWho: AGK steward",
         "created_at": "2026-11-15T09:00:00Z"},
    ]
    text = steward_daily.daily_text(date(2026, 11, 16), [date(2026, 11, 15)], [], memory, [])
    assert "Replies shortened (2026-11-15): 2" in text


def test_req069_shortened_records_one_marker(monkeypatch, capsys):
    seen = []
    import steward

    monkeypatch.setattr(steward, "write", lambda root, text, gh: (seen.append(text), (0, ["ok"]))[1])
    assert voice.main(["shortened", "--rules", "2,3"]) == 0
    assert seen == ["Shortened: steward reply (voice rules 2, 3)"]
    assert steward.entry_kind(seen[0]) == "Shortened"


def test_req069_the_role_file_and_the_guide_name_the_voice_and_its_check():
    text = (ROOT / ".claude" / "agents" / "steward.md").read_text(encoding="utf-8")
    assert "Voice." in text and "steward_voice.py check" in text
    assert "docs/guides/steward-voice.md" in text and "ADR-0582" in text
    for words in ("first line", "at most 5 bullets", "three choices", "say details", "yes"):
        assert words in text, words
    guide = (ROOT / "docs" / "guides" / "steward-voice.md").read_text(encoding="utf-8")
    for n in range(1, 10):
        assert f"\n{n}. **" in guide, n
    for words in ("say more for N other options", "which group to open", "sharper question",
                  "Waiting on you:", "multiple-choice question tool", "(verify", "never asked",
                  "Lines posted on GitHub keep the kit's forms"):
        assert words in guide, words
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/steward_voice.py" in manifest["verbatim"]
