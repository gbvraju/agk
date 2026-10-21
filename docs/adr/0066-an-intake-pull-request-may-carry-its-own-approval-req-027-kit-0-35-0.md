# ADR-0066: an intake pull request may carry its own approval (REQ-027, SPEC-0020), kit 0.35.0

- Status: Proposed
- Date: 2026-10-21
- Deciders: maintainers
- Related: ADR-0065, ADR-0064
- Requirements: REQ-027

Protected classes: `scripts/agk/`, `tests/kit_dev/`, `skills/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

`docs/runs/method-weight-1.md` measured 7.0 maintainer actions per delivered requirement; one of the steps is a rulings-and-approval pull request, and eight of fifteen pull requests ended with a commit that
changed status lines only. L2 of the lighter path lets an intake pull request carry the approval itself when the maintainers answered every question before the files were written: its final commit, on their
word, sets the spec `Approved` and the ADR `Accepted`. SPEC-0020 (Approved with ADR-0065, #116) states the rules; this ADR builds them. The tests were written first and run on unchanged `main`
(35 failed, 4 passed, the 4 being the guards: `check` without `--final` as before, the flag refused for the other commands, and no network import; the output is in the pull request body).

## Decision

1. **The mode** (SPEC-0020 rules 1 to 6): `intake.py check --final [--base REF]` reads the commits `HEAD~1` and `HEAD` and the files at them with git, with no network and no model. `HEAD` must have one parent
   and that parent must not be the merge base (rule 2); the tree of `HEAD~1` must pass every check C1 to C9 (rule 3), through `Draft` reading the commit instead of the work tree; the difference `HEAD~1` to
   `HEAD` is exactly the spec and the ADR of the intake, each with one removed and one added line, `- Status: Draft` to `- Status: Approved` and `- Status: Proposed` to `- Status: Accepted` (rule 4);
   the spec at `HEAD` has no question id and its `## Open questions` is `none` (rule 5); its opening paragraph, the text before the first `## ` heading, has `The maintainers answered 1 question`, `2 questions`
   or `3 questions` `before it was written`, or `The maintainers answered no questions before it was written; the sentence settled every point.` (rule 6, Q-K4-217 ruled). Each refusal names the rule and
   never a status or the sentence. `check` without `--final` is unchanged; `--final` with another command is a usage error.
2. **The stub** (Q-K4-218, ruled): the Decision text of the ADR stub says the spec "stays `Draft` until it is approved, by a later pull request or by this intake's own final commit". The ADRs of
   past intakes keep the text they were rendered with.
3. **The skill and the printed steps** (rule 8): `skills/spec/SKILL.md` says when the answers go in the opening paragraph and that the skill never makes the approving commit; `intake.py next-steps` prints a
   closing paragraph that names the final-commit mode and the two status lines, as text.
4. **Amendment 32** (`docs/runs/proposed-spec-amendments-32.md`) is applied to SPEC-0012 rules 8, 11, 13 and 14 and its Tests list.
5. **Tests, first** (`tests/kit_dev/test_intake_final.py`, new, kit-only): the approving commit passes for N of 1, 2, 3 and the zero form; a third line, a reworded line, a third file, the requirements file, a status
   other than the two (5 cases) and one file only are refused; an open question id, a section that is not `none` and 8 wordings of the paragraph are refused; `check` without `--final` prints what it printed and
   refuses `Approved` and `Accepted` as before; a first commit that already carries the statuses, a single commit, a `HEAD~1` that fails a check and a merge commit are refused; the requirement is `planned`
   at `HEAD`; `intake.py` imports nothing that reaches a network; the skill, the printed steps and the stub carry the rule 8 text.
6. **Kit 0.35.0**: the manifest `kit_version`, `kit/hashes.json`, the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7). No file is added to or removed from the manifest.

## Consequences

- An intake whose questions were answered first reaches the default branch approved in one merge; one pull request and its verdict rounds are saved for those requirements. `method-weight-2.md` judges it
  against `method-weight-1.md` after the next three requirements.
- A question raised after the files exist keeps the two-pull-request path unchanged.
- `intake.py` is kit-only, so a project gets the mode through the plugin (`skills/spec/SKILL.md` and the scripts the plugin runs from its own root) on its next `agk upgrade`.
- L3 generalises "a final commit changes only named status lines" into governance and the metrics; this mode is then the first caller of that check.

## Residual

- 2026-10-21: the check cannot see that the maintainers gave the word (SPEC-0020 rule 7); the pull request body quotes it and the review of the pull request is the control (due 2026-12-31).
- 2026-10-21: the paragraph of rule 6 accepts digits only (`2 questions`), while the K5 intakes wrote the number in words (`three questions`); a spec written in words is refused with the rule named (due 2026-12-31).
