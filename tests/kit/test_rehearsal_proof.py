"""Tests of SPEC-0071 rule 11, build (g) (brief #1459, ADR-0617; REQ-078 AC6 and AC7).

The rehearsal record in SPEC-0071's proof holds both runs' four figures for the same five briefs;
`rehearsal.py check` fails, naming the figure and never a value, when a figure is missing or the
clean run is worse than the installed one by more than 10%; and `upgrade.py --clean-repo` without
`--rehearsal` refuses, naming the proof, until the record passes and the maintainers' acceptance
line is dated. Saved spec texts in temporary folders only; no network; invented data only
(example.com, briefs of a sample project)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import rehearsal
import upgrade

ROOT = Path(__file__).resolve().parents[2]
BRIEFS = "#1, #2, #3, #4, #5"
HEAD = (
    "| Run | Dates | Briefs | Lead time per brief (hours) | Tokens per merged pull request "
    "| First-review pass rate (%) | Failed checks |\n|---|---|---|---|---|---|---|\n"
)


def record(clean: dict | None = None, accepted: str = "2026-12-01 by the maintainers") -> str:
    figures = {"lead": "10", "tokens": "100000", "rate": "80", "failed": "2"}
    worse = {**figures, **(clean or {})}

    def row(run: str, f: dict, briefs: str = BRIEFS) -> str:
        return (
            f"| {run} | 2026-11-20..2026-11-21 | {briefs} | {f['lead']} | {f['tokens']} "
            f"| {f['rate']} | {f['failed']} |\n"
        )

    clean_briefs = worse.pop("briefs", BRIEFS)
    return (
        "# SPEC-0071: sample\n\n## Proof\n\nREQ-078 AC6.\n\n"
        f"{rehearsal.HEADING}\n\n{HEAD}{row('installed', figures)}"
        f"{row('clean', worse, clean_briefs)}"
        f"\nAccepted: {accepted}\n\n## Residual\n"
    )


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "plugin-example" / rehearsal.SPEC
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return tmp_path / "plugin-example"


def test_the_shipped_spec_holds_no_figures_yet_so_the_gate_holds(capsys):
    """REQ-078 AC6: until the runs are written to the spec's proof, the check fails naming it."""
    problems, accepted = rehearsal.read((ROOT / rehearsal.SPEC).read_text(encoding="utf-8"))
    assert problems and not accepted and not rehearsal.proof_held(ROOT)
    assert rehearsal.main(["check"]) == 1 and "not held: " in capsys.readouterr().out


def test_a_full_record_within_ten_percent_and_accepted_holds_the_proof(tmp_path, capsys):
    """REQ-078 AC6: both runs' four figures, the same five briefs, the run dates and acceptance."""
    root = write(tmp_path, record({"lead": "11", "tokens": "110000", "rate": "72", "failed": "2"}))
    assert rehearsal.main(["check", "--root", str(root)]) == 0
    assert "proof held" in capsys.readouterr().out and rehearsal.proof_held(root)


@pytest.mark.parametrize(
    ("clean", "named"),
    [
        ({"lead": "11.5"}, "lead time per brief"),
        ({"tokens": "110001"}, "tokens per merged pull request"),
        ({"rate": "71"}, "first-review pass rate"),
        ({"failed": "3"}, "failed checks"),
    ],
)
def test_a_figure_worse_by_more_than_ten_percent_fails_naming_it(tmp_path, capsys, clean, named):
    """REQ-078 AC6: the check fails on each figure, naming the figure and never a value."""
    root = write(tmp_path, record(clean))
    assert rehearsal.main(["check", "--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert f"worse by more than 10%: {named}" in out and next(iter(clean.values())) not in out
    assert not rehearsal.proof_held(root)


@pytest.mark.parametrize(
    ("clean", "named"),
    [
        ({"tokens": ""}, "missing: tokens per merged pull request (clean)"),
        ({"lead": "—"}, "missing: lead time per brief (clean)"),
        ({"briefs": "#1, #2, #3, #4, #6"}, "not the same five briefs"),
        ({"briefs": "#1, #2, #3, #4"}, "not the same five briefs"),
    ],
)
def test_a_missing_figure_or_other_briefs_fail(tmp_path, capsys, clean, named):
    """REQ-078 AC6: a figure missing, or not the same five briefs, fails the check."""
    root = write(tmp_path, record(clean))
    assert rehearsal.main(["check", "--root", str(root)]) == 1
    assert named in capsys.readouterr().out and not rehearsal.proof_held(root)


def test_figures_without_the_acceptance_line_do_not_open_the_gate(tmp_path, capsys):
    """REQ-078 AC6: the maintainers accept the figures before any customer move."""
    root = write(tmp_path, record(accepted="—"))
    assert rehearsal.main(["check", "--root", str(root)]) == 1
    assert "not accepted" in capsys.readouterr().out and not rehearsal.proof_held(root)


def test_no_record_at_all_is_refused_naming_the_proof(tmp_path, capsys):
    """REQ-078 AC6: a plugin without the spec or the record does not hold the proof."""
    assert not rehearsal.proof_held(tmp_path)
    assert rehearsal.main(["check", "--root", str(tmp_path)]) == 1
    assert "SPEC-0071 rule 11" in capsys.readouterr().out
    assert rehearsal.main(["nonsense"]) == 2


def test_the_migration_gate_reads_the_proof(tmp_path, monkeypatch):
    """REQ-078 AC6: `upgrade.py --clean-repo` without `--rehearsal` refuses while the proof lacks a
    figure, and the same plan is not refused on the proof once it holds; CI mode still refuses."""
    data = tomllib.loads('version = "2.0.0"\nexecution = "local"\n')
    table = {"releases": {"2.0.0": {}}}
    held = write(tmp_path, record())
    with pytest.raises(upgrade.Refusal, match="SPEC-0071 rule 11"):
        upgrade.clean_refusal(data, "2.0.0", "2.0.0", table, False, tmp_path / "none")
    upgrade.clean_refusal(data, "2.0.0", "2.0.0", table, False, held)
    upgrade.clean_refusal(data, "2.0.0", "2.0.0", table, True, tmp_path / "none")
    hosted = {**data, "execution": "hosted"}
    with pytest.raises(upgrade.Refusal, match=r"\(setting: execution\)"):
        upgrade.clean_refusal(hosted, "2.0.0", "2.0.0", table, False, held)


def test_the_check_reads_only_and_the_kit_repository_keeps_its_layout(tmp_path):
    """REQ-078 AC7: the check writes nothing, and this repository has no `[kit]` table."""
    root = write(tmp_path, record())
    before = sorted((p, p.read_bytes()) for p in root.rglob("*") if p.is_file())
    rehearsal.main(["check", "--root", str(root)])
    assert sorted((p, p.read_bytes()) for p in root.rglob("*") if p.is_file()) == before
    assert "kit" not in tomllib.loads((ROOT / "agk.toml").read_text(encoding="utf-8"))
