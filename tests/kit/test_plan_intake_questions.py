"""Planning keeps open questions few, and its render can run again (brief #1221, REQ-050, ADR-0520).

REQ-050 AC2.

`validate` prints `warning: <n> open questions` when the questions for business are more than
`[plan] max_questions` (60 by default). Open questions of one kind (`<section> <key>: <text>`, the
same text) and one area (the feature area of the requirement the question names, else the file of
its first source) are one question for business, whose `Blocks:` line names the keys it holds. A
cross-reference gap is a `Note:` line of its requirement, never a question. `render --again`
rewrites only the files an earlier render wrote whose bytes are unchanged since (the digests in
`docs/plan/render-digests.json`), creates files that are new, and leaves a file a person edited as
it is, naming it. Invented sources only (example.com), no network.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import common
import plan_intake
import pytest
from test_plan_intake import PRD, SOW, write
from test_plan_render import no_network as no_network  # noqa: F401 - the guard, reused
from test_plan_render import proposals, render, tree
from test_plan_render import repo as repo  # noqa: F401 - the fixture, reused

DIGESTS = "docs/plan/render-digests.json"
KIND = "no scenario, so no acceptance line (verify)"
CROSS = "cross-reference 2 of its statement names no one source heading (verify)"


def two_areas() -> dict:
    """The render fixture with a second requirement R2 in a second area, Billing."""
    data = proposals()
    second = copy.deepcopy(data["requirements"][0]) | {"key": "R2"}
    data["requirements"].append(second)
    data["areas"].append({"name": "Billing", "requirements": ["R2"]})
    data["briefs"][1]["advances"] = ["R2"]
    return data


def many(data: dict, n: int, text=lambda i: f"requirements R{1 + i % 2}: {KIND}") -> dict:
    data["scope"]["open_questions"] = [
        {"key": f"Q{i + 1}", "text": text(i), "sources": [f"{SOW}#Scope"]} for i in range(n)
    ]
    return data


def validate(root: Path, data: dict, capsys) -> tuple[int, str]:
    path = root.parent / "proposals.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    code = plan_intake.main(["validate", "--proposals", str(path), "--root", str(root)])
    out = capsys.readouterr()
    return code, out.out + out.err


def again(root: Path, data: dict, capsys) -> tuple[int, str]:
    path = root.parent / "proposals.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    code = plan_intake.main(["render", "--proposals", str(path), "--again", "--root", str(root)])
    out = capsys.readouterr()
    return code, out.out + out.err


def business(root: Path) -> list[str]:
    scope = (root / "docs/plan/scope.md").read_text(encoding="utf-8")
    return scope.split("\n## Questions for business\n", 1)[1].split("\n### ")[1:]


# --- answer 1: few, grouped questions --------------------------------------------------------


def test_1221_200_questions_of_one_kind_are_one_per_area(repo: Path, capsys) -> None:  # noqa: F811
    """REQ-050: brief #1221 answers 1 and 3, 200 same-kind questions over two areas are two."""
    code, out = render(repo, many(two_areas(), 200), capsys)
    assert code == 0, out
    blocks = business(repo)
    assert len(blocks) == 2, blocks
    first, second = blocks
    assert first.startswith("Q1\n") and second.startswith("Q2\n")
    assert f"\nQuestion: requirements R1 (area Orders): {KIND}\n" in first
    assert f"\nQuestion: requirements R2 (area Billing): {KIND}\n" in second
    assert first.split("\nBlocks: ", 1)[1].split("\n")[0].split(", ")[0] == "R1"
    assert second.split("\nBlocks: ", 1)[1].split("\n")[0].split(", ")[0] == "R2"
    assert out.count(KIND) == 2  # the person's list is grouped too
    _, out = validate(repo, many(two_areas(), 200), capsys)
    assert "warning:" not in out and "ok proposals" in out


def test_1221_one_question_stays_as_it_was(repo: Path, capsys) -> None:  # noqa: F811
    """REQ-050: brief #1221 answer 1, a kind asked once keeps its key, text and blocks."""
    assert render(repo, many(two_areas(), 1), capsys)[0] == 0
    (block,) = business(repo)
    assert block.startswith("Q1\n") and f"\nQuestion: requirements R1: {KIND}\n" in block


def test_1221_different_kinds_are_not_grouped(repo: Path, capsys) -> None:  # noqa: F811
    """REQ-050: brief #1221 answer 1, only one kind and one area make one question."""
    data = many(two_areas(), 3, lambda i: f"requirements R1: kind {i} is open (verify)")
    assert render(repo, data, capsys)[0] == 0
    assert len(business(repo)) == 3


@pytest.mark.parametrize("count, warned", [(60, False), (61, True)])
def test_1221_validate_warns_above_the_default_limit(
    repo: Path,  # noqa: F811
    count: int,
    warned: bool,
    capsys,
) -> None:
    """REQ-050: brief #1221 answers 1 and 3, `[plan] max_questions` is 60 by default; the
    warning is printed and the exit stays 0."""
    data = many(two_areas(), count, lambda i: f"Question {i} for business? (verify)")
    code, out = validate(repo, data, capsys)
    assert code == 0 and "ok proposals" in out, out
    assert (f"warning: {count} open questions" in out) is warned, out


def test_1221_validate_reads_the_limit_from_the_plan_table(repo: Path, capsys) -> None:  # noqa: F811
    """REQ-050: brief #1221 answer 1, the setting of `agk.toml`; a bad one names the setting."""
    write(repo, "agk.toml", "[plan]\nmax_questions = 2\n")
    data = many(two_areas(), 3, lambda i: f"Question {i} for business? (verify)")
    code, out = validate(repo, data, capsys)
    assert code == 0 and "warning: 3 open questions" in out and "max_questions" in out, out
    grouped = many(two_areas(), 30)  # thirty of one kind in two areas: two questions
    assert "warning:" not in validate(repo, grouped, capsys)[1]
    write(repo, "agk.toml", "[plan]\nmax_questions = 0\n")
    code, out = validate(repo, data, capsys)
    assert code == 1 and "(setting: [plan] max_questions)" in out, out
    with pytest.raises(common.CheckError, match=r"setting: \[plan\] max_questions"):
        common.plan_settings(repo)
    write(repo, "agk.toml", "[plan]\nmax_questions = 7\n")
    assert common.plan_settings(repo)["max_questions"] == 7


def test_1221_a_cross_reference_gap_is_a_note_never_a_question(repo: Path, capsys) -> None:  # noqa: F811
    """REQ-050: brief #1221 answer 1, the gap goes on its requirement's block."""
    data = many(two_areas(), 1, lambda i: f"requirements R1: {CROSS}")
    data["scope"]["open_questions"].append(
        {"key": "Q2", "text": "Who signs the list off? (verify)", "sources": [f"{PRD}:8"]}
    )
    code, out = render(repo, data, capsys)
    assert code == 0, out
    (block,) = business(repo)
    assert block.startswith("Q2\n")
    proposed = (repo / "docs/plan/requirements-proposed.md").read_text(encoding="utf-8")
    r1 = proposed.split("\n### R1 ", 1)[1].split("\n### ", 1)[0]
    assert f"\nNote: {CROSS}\n" in r1
    assert CROSS not in out


def test_1221_a_requirement_may_carry_notes(repo: Path, capsys) -> None:  # noqa: F811
    """REQ-050: brief #1221 answer 1, `notes` is an optional list of a requirement."""
    data = two_areas()
    data["requirements"][0]["notes"] = [CROSS]
    assert validate(repo, data, capsys)[0] == 0
    data["requirements"][0]["notes"] = "one note"
    code, out = validate(repo, data, capsys)
    assert code == 1 and "rule 4: requirements R1: notes is not list" in out, out


# --- answer 2: render --again ----------------------------------------------------------------


def test_1221_render_keeps_a_digest_list_beside_the_plan(repo: Path, capsys) -> None:  # noqa: F811
    """REQ-050: brief #1221 answer 2, one digest per file it wrote, and the area specs."""
    assert render(repo, proposals(), capsys)[0] == 0
    listed = json.loads((repo / DIGESTS).read_text(encoding="utf-8"))
    assert listed["schema"] == 1
    assert "docs/plan/scope.md" in listed["files"] and DIGESTS not in listed["files"]
    assert listed["specs"] == {"Orders": "docs/specs/0001-orders.md"}


def test_1221_render_again_rewrites_untouched_files_and_keeps_an_edited_one(
    repo: Path,  # noqa: F811
    capsys,
) -> None:
    """REQ-050: brief #1221 answers 2 and 3."""
    assert render(repo, proposals(), capsys)[0] == 0
    edited = "the person's own scope\n"
    (repo / "docs/plan/scope.md").write_text(edited, encoding="utf-8")
    spec = (repo / "docs/specs/0001-orders.md").read_bytes()
    data = proposals()
    data["milestones"][0]["acceptance"] = "The list shows every order"
    third = copy.deepcopy(data["briefs"][0]) | {"key": "B3", "depends_on": []}
    data["briefs"].append(third)
    code, out = again(repo, data, capsys)
    assert code == 0, out
    assert "kept docs/plan/scope.md: edited since the last render" in out
    assert (repo / "docs/plan/scope.md").read_text(encoding="utf-8") == edited
    assert "rewrote docs/plan/milestones.md" in out
    milestones = (repo / "docs/plan/milestones.md").read_text(encoding="utf-8")
    assert "\nAcceptance: The list shows every order\n" in milestones
    assert "created docs/plan/briefs/M1/B3.md" in out
    assert "unchanged docs/plan/personas.md" in out
    assert "kept docs/specs/0001-orders.md: a Draft spec is written once" in out
    assert (repo / "docs/specs/0001-orders.md").read_bytes() == spec
    assert not (repo / "docs/specs/0002-orders.md").exists()
    before = tree(repo)
    code, out = again(repo, data, capsys)  # a third pass: the edit is still the person's
    assert code == 0 and "kept docs/plan/scope.md: edited since the last render" in out
    assert tree(repo) == before


def test_1221_render_again_keeps_a_file_it_did_not_write(repo: Path, capsys) -> None:  # noqa: F811
    """REQ-050: brief #1221 answer 2, only files of the digest list are ever rewritten."""
    assert render(repo, proposals(), capsys)[0] == 0
    data = proposals()
    data["briefs"].append(copy.deepcopy(data["briefs"][0]) | {"key": "B3", "depends_on": []})
    write(repo, "docs/plan/briefs/M1/B3.md", "a person's brief\n")
    code, out = again(repo, data, capsys)
    assert code == 0 and "kept docs/plan/briefs/M1/B3.md: not written by render" in out, out
    assert (repo / "docs/plan/briefs/M1/B3.md").read_text(encoding="utf-8") == "a person's brief\n"


def test_1221_render_again_writes_a_spec_for_a_new_area(repo: Path, capsys) -> None:  # noqa: F811
    """REQ-050: brief #1221 answer 2, an area the first render did not have gets its spec."""
    assert render(repo, proposals(), capsys)[0] == 0
    code, out = again(repo, two_areas(), capsys)
    assert code == 0, out
    assert (repo / "docs/specs/0002-billing.md").is_file()
    listed = json.loads((repo / DIGESTS).read_text(encoding="utf-8"))
    assert listed["specs"]["Billing"] == "docs/specs/0002-billing.md"


def test_1221_render_again_needs_the_digest_list(repo: Path, capsys) -> None:  # noqa: F811
    """REQ-050: brief #1221 answer 2, without the list nothing is known to be render's."""
    before = tree(repo)
    code, out = again(repo, proposals(), capsys)
    assert code == 1 and f"rule 7: {DIGESTS} cannot be read; nothing was written" in out, out
    assert tree(repo) == before
    assert render(repo, proposals(), capsys)[0] == 0
    (repo / DIGESTS).write_text("not json\n", encoding="utf-8")
    before = tree(repo)
    code, out = again(repo, proposals(), capsys)
    assert code == 1 and f"{DIGESTS} cannot be read" in out and tree(repo) == before


def test_1221_a_first_render_refuses_over_an_existing_digest_list(repo: Path, capsys) -> None:  # noqa: F811
    """REQ-050: brief #1221 answer 2, the render without `--again` is unchanged: new files only."""
    write(repo, DIGESTS, "{}\n")
    code, out = render(repo, proposals(), capsys)
    assert code == 1 and f"rule 7: {DIGESTS} already exists; nothing was written" in out, out


def test_1221_again_is_only_an_option_of_render(capsys) -> None:
    """REQ-050: brief #1221 answer 2, `--again` takes no value and belongs to render alone."""
    assert plan_intake.main(["validate", "--proposals", "p.json", "--again"]) == 2
    assert "render --proposals FILE [--again]" in capsys.readouterr().err
