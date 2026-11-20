"""Tests of SPEC-0062 build (a): in solo mode the steward learns who it talks to and plays back what
it understood (rules 3 to 7 and 10; brief #1598, ADR-0678; REQ-069 AC1 and AC2).

Saved chat turns and a recorded `gh` double stand in for the runtime, the model and GitHub; no
network, invented data only (example.com).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import steward  # noqa: E402
import steward_voice as voice  # noqa: E402
from test_steward_memory import NOW, GitHub  # noqa: E402

WORDS = "business: a booking site for dog walkers in Pune, for pet owners"
TERMS = voice.planted_terms()


@pytest.fixture
def solo(tmp_path, monkeypatch):
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(tmp_path / "cache.json"))
    (tmp_path / "agk.toml").write_text('review_mode = "solo"\n', encoding="utf-8")
    return tmp_path


def bodies(gh: GitHub) -> list[str]:
    return [c["body"] for c in gh.issues[1]["c"]]


def test_req069_ac1_a_first_solo_start_asks_one_question_and_records_one_person_entry(solo):
    """REQ-069 AC1: rules 3 and 4, day 0 holds no product fact; one question; one `Person:`."""
    gh = GitHub()
    code, lines = steward.start(solo, "s1", gh, NOW)
    assert code == 0
    asks = [line for line in lines if line.startswith("ask: ")]
    assert len(asks) == 1 and asks[0].count("?") == 1
    assert "in your own words" in asks[0] and "business side or the technical side" in asks[0]
    assert not [line for line in lines[1:] if not line.startswith(("ask: ", "first start"))]
    code, _ = steward.record(solo, "Person", WORDS, gh)
    assert code == 0
    person = [b for b in bodies(gh) if steward.entry_kind(b) == "Person"]
    assert len(person) == 1
    assert person[0].startswith(f"Person: {WORDS}")
    assert person[0].rstrip().endswith("Who: ProductOwner")
    steward.end(solo, "s1", gh, NOW)
    _, again = steward.start(solo, "s2", gh, NOW)
    assert not [line for line in again if line.startswith("ask: ")]
    assert any(line.startswith("Person: business: a booking site") for line in again)


def test_req069_ac1_a_person_entry_takes_its_form_and_the_guard():
    """REQ-069 AC1: rule 4's form `<business|technical>: <their words>`; the data guard holds."""
    gh = GitHub()
    for bad in ("a booking site", "manager: a booking site", "business:"):
        code, lines = steward.record(ROOT, "Person", bad, gh)
        assert code == 2 and "Person" in lines[0] and bad not in lines[0]
    assert gh.calls == []


def test_req069_ac1_personal_mode_writes_the_person_entry_to_the_sidecar(solo):
    """REQ-069 AC1: rule 16, personal mode keeps the entry in the sidecar; nothing is posted."""
    (solo / "agk.toml").write_text('review_mode = "solo"\n[personal]\nforge = "files"\n', "utf-8")
    gh = GitHub()
    code, lines = steward.start(solo, "s1", gh, NOW)
    assert code == 0 and sum(line.startswith("ask: ") for line in lines) == 1
    steward.record(solo, "Person", WORDS, gh)
    text = (solo / steward.PERSONAL_FILE).read_text(encoding="utf-8")
    assert f"Person: {WORDS}\n\nWho: ProductOwner" in text
    assert gh.calls == []


def test_req069_ac8_team_mode_asks_nothing_new(tmp_path, monkeypatch):
    """REQ-069 AC8: rule 2, with `review_mode = "team"` the start is SPEC-0059's exactly."""
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(tmp_path / "cache.json"))
    (tmp_path / "agk.toml").write_text('review_mode = "team"\n', encoding="utf-8")
    code, lines = steward.start(tmp_path, "s1", GitHub(), NOW)
    assert code == 0 and lines == ["memory: #1"]


def run_stage(turns: list[tuple[str, str]], out: Path, tmp_path: Path) -> list[int]:
    """The saved chat: each turn is a play-back and the person's reply; the stage's skill stub
    writes its output only after the gate says go on."""
    codes = []
    for n, (playback, reply) in enumerate(turns):
        said = tmp_path / f"playback-{n}.txt"
        said.write_text(playback, encoding="utf-8")
        code = voice.main(["playback", str(said), "--reply", reply])
        codes.append(code)
        if code == 0:
            out.write_text("# Vision\n", encoding="utf-8")
            break
    return codes


PLAYBACK = (
    "You want a booking site where pet owners in Pune find a dog walker. "
    "Owners pay when they book. Walkers set their own hours."
)


def test_req069_ac1_no_stage_output_before_a_confirmed_play_back(tmp_path, capsys):
    """REQ-069 AC1: rule 4, nothing is written on a play-back that has no yes."""
    out = tmp_path / "vision.md"
    assert run_stage([(PLAYBACK, "yes but walkers are paid weekly")], out, tmp_path) == [1]
    assert not out.exists()
    assert "play back again" in capsys.readouterr().out
    assert run_stage([(PLAYBACK, "Yes, go ahead.")], out, tmp_path) == [0]
    assert out.exists()


def test_req069_ac1_a_correction_is_played_back_again(tmp_path):
    """REQ-069 AC1: rule 4, a correction is taken and played back again before anything runs."""
    out = tmp_path / "vision.md"
    fixed = PLAYBACK.replace("Owners pay when they book.", "Walkers are paid each week.")
    turns = [(PLAYBACK, "No, walkers are paid each week."), (fixed, "yes")]
    assert run_stage(turns, out, tmp_path) == [1, 0]
    assert out.exists()


def test_req069_ac1_a_play_back_is_three_sentences_or_fewer(tmp_path, capsys):
    long = tmp_path / "long.txt"
    long.write_text(PLAYBACK + " They rate each walk.", encoding="utf-8")
    assert voice.main(["playback", str(long), "--reply", "yes"]) == 2
    assert "three sentences" in capsys.readouterr().err
    for reply in ("yes?", "maybe", "", "👍", "go ahead if it is cheap", "approved, with a change"):
        assert not voice.is_yes(reply), reply
    for reply in ("yes", "Yes.", "approved", "go ahead with it", "that's right"):
        assert voice.is_yes(reply), reply


def test_req069_ac2_the_planted_list_is_read_from_the_guide():
    """REQ-069 AC2: rule 5, one kit file holds the terms the role file and the check use (Q-1)."""
    guide = (ROOT / "docs" / "guides" / "steward-voice.md").read_text(encoding="utf-8")
    assert "## Kit terms" in guide
    assert len(TERMS) >= 8 and "pull request" in TERMS
    for term, explained in TERMS.items():
        assert explained.endswith(".") and explained.count(". ") == 0, term
        assert voice.problems(explained, TERMS) == [], term


def test_req069_ac2_a_kit_term_is_flagged_unless_explained_and_never_explained_twice():
    """REQ-069 AC2: rule 5, a planted term needs its one sentence on first use, and not again."""
    plain = "Your change is ready to check. Shall I send it?"
    assert voice.problems(plain, TERMS) == []
    bare = "I opened a pull request for the sign-up screen. Shall I go on?"
    found = voice.problems(bare, TERMS)
    assert any("rule 8" in p and "explanation" in p for p in found)
    assert "pull request" not in " ".join(found)
    told = f"I opened a pull request: {TERMS['pull request']} Shall I go on?"
    assert voice.problems(told, TERMS) == []
    assert voice.explained_terms(told, TERMS) == ["pull request"]
    assert voice.problems(bare, TERMS, {"pull request"}) == []
    twice = voice.problems(told, TERMS, {"pull request"})
    assert any("explained twice" in p for p in twice)
    assert voice.explained_terms(told, TERMS, {"pull request"}) == []


def test_req069_ac2_an_explained_term_is_recorded_once_as_a_kit_term(solo, monkeypatch, capsys):
    """REQ-069 AC2: rule 5, the `Term:` entry is marked `kit`; a known term is not recorded."""
    (solo / "agk.toml").write_text('review_mode = "solo"\n[personal]\nforge = "files"\n', "utf-8")
    monkeypatch.setattr(voice, "repo_root", lambda: solo)
    reply = solo / "reply.txt"
    reply.write_text(f"I opened a pull request: {TERMS['pull request']} Go on?", encoding="utf-8")
    assert voice.main(["explained", str(reply)]) == 0
    assert voice.main(["explained", str(reply)]) == 0
    text = (solo / steward.PERSONAL_FILE).read_text(encoding="utf-8")
    assert text.count("Term: kit: pull request: ") == 1
    assert voice.known_terms(solo) == {"pull request"}
    assert voice.main(["check", str(reply)]) == 1
    assert "explained twice" in capsys.readouterr().out


def test_req069_ac2_an_off_topic_turn_gets_one_line_back_to_the_product(capsys):
    """REQ-069 AC2: rule 10, one polite line and a return to the product, in the person's words."""
    assert voice.main(["offtopic", "--product", "the dog walker booking site"]) == 0
    out = capsys.readouterr().out.strip()
    assert len(out.splitlines()) == 1 and out.endswith("the dog walker booking site?")
    assert voice.problems(out, TERMS) == []


def test_req069_the_role_file_points_at_the_solo_section():
    """REQ-069 AC1 and AC2: rules 3 to 7 and 10 are the guide's solo section, named by the role."""
    role = (ROOT / ".claude" / "agents" / "steward.md").read_text(encoding="utf-8")
    assert "Solo." in role and "steward_voice.py playback" in role
    assert "--kind Person" in role and "steward_voice.py explained" in role
    guide = (ROOT / "docs" / "guides" / "steward-voice.md").read_text(encoding="utf-8")
    for words in (
        "## Solo mode",
        "assumes nothing about the product",
        "their own words",
        "three sentences or fewer",
        "only when the person asks",
        "`Decision:`",
        "one polite line",
        "what, how, when and why",
        "team mode",
    ):
        assert words in guide, words
