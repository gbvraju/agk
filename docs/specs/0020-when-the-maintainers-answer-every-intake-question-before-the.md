# SPEC-0020: An intake pull request may carry its own approval

- Status: Draft
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-027

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "When the maintainers answer every intake question before the files are written, the intake pull request may carry the approval itself: its final commit, on
their word, sets the spec Approved and the ADR Accepted, and no separate rulings pull request is needed." It is the second item of the lighter-path brief (L2), which follows the measure of
`docs/runs/method-weight-1.md`: eight of fifteen pull requests ended with a commit that changed status lines only. The maintainers answered three questions before it was written: the final-commit mode is
in `intake.py`, because it is the intake's rule, and L3 later generalises "a final commit changes only named status lines" into governance, which this mode then reuses; the test is that the spec has no open `Q-S`
id, and the answers are recorded in the spec's opening paragraph ("The maintainers answered N questions before it was written: ..."), not as a pull request comment, and the check requires that paragraph when the final
commit approves; the answers live in that paragraph and the pull request body, with no fourth file and no decisions-log row in the intake pull request. A question raised after the files exist keeps the two-pull-request path.

## Rules

1. **One mode.** `python3 scripts/agk/intake.py check --final [--base REF]` checks an intake pull request whose last commit is the approving commit. It reads git and the files of the work tree only. It uses no
   network and no model. `check` without `--final` is unchanged and still refuses a spec `Approved` and an ADR `Accepted` (SPEC-0012 rule 11, C6).
2. **A separate last commit.** In the final-commit mode the commit before `HEAD` (`HEAD~1`) is not the merge base: the approving commit is its own commit, on top of an intake commit. A pull request whose first
   commit already carries `Approved` or `Accepted`, or whose only commit is the approving one, is refused.
3. **The draft before it.** The tree of `HEAD~1`, compared with the merge base, passes every check of `check` without `--final` (C1 to C9): the same three files, the spec `Draft`, the ADR `Proposed`, the
   requirement `planned`. The approving commit is not allowed to repair a draft that would not have passed.
4. **The approving commit changes two lines.** The difference `HEAD~1` to `HEAD` is exactly two files, the spec and the ADR of the intake. In the spec it removes the line `- Status: Draft` and adds the line
   `- Status: Approved`; in the ADR it removes the line `- Status: Proposed` and adds the line `- Status: Accepted`. Nothing else is added, removed or reordered, no other file changes, and
   `docs/requirements.md` is not among the files, so the requirement stays `planned` (SPEC-0012 rule 14: the merge makes it `planned`; `done` is the build's).
5. **No open question.** The spec at `HEAD` has no `Q-` id of any family and its `## Open questions` section is `none`. A spec with an open `Q-S` id cannot be set `Approved` (SPEC-0013 rule 24), so a question
   raised after the files were written goes the old way: the intake pull request is merged as a draft and a rulings pull request approves it.
6. **The answers are written down.** The spec's opening paragraph (the text before the first `## ` heading) contains the sentence `The maintainers answered N question` followed by `s` or not, `N` being 1, 2 or
   3, then ` before it was written`. The skill writes it from the answers the person gave in the session. A spec without it is refused.
7. **The word is not checked.** That the maintainers gave the word is not something a check can see: the session makes the approving commit only on their written word, as a verdict item or an instruction in the
   session, and the pull request body quotes it (CLAUDE.md rule 1). The check makes the commit safe to merge, not authorised.
8. **The skill and the printed steps.** `skills/spec/SKILL.md` says: when every question is answered before the files are written, write the answers in the spec's opening paragraph and no `Q-S` id; when a
   question is raised after the files exist, leave it as a `Q-S` id. The skill never makes the approving commit (SPEC-0005 rules 8 and 10). `intake.py next-steps` prints one more line, after the pull request
   body, that names the final-commit mode and the two status lines, as text and not as a command to run on its own.
9. **How it changes.** SPEC-0012 is Approved. The build changes it by `docs/runs/proposed-spec-amendments-N.md`, applied by its ADR (rule 11 C6 gains the final-commit mode, rule 14 says what the merge approves
   in that path). `intake.py` and its tests are kit-only (SPEC-0012 rule 18). `skills/spec/SKILL.md` changes the plugin, so the build is a kit change: a bump, the hashes, the plugin and `agk.toml` versions, and an
   ADR that names the protected classes it touches.
10. **The tests.** Fixtures in `tmp_path`: a good draft with an approving commit passes; each of the refusals of rules 2 to 6 fails with the rule named and never the sentence; `check` without `--final` gives
    the same output as before for a good draft and the same refusal for an `Approved` spec.

## Tests

- Rules 1 and 4: a good draft with an approving commit that changes the two status lines passes `check --final`; REQ-027 AC1.
- Rule 4: a final commit that changes a third line, a third file, either status to another value (`Draft` to `Accepted`, `Proposed` to `Approved`) or `docs/requirements.md` is refused; REQ-027 AC2.
- Rules 5 and 6: a spec with a `Q-S` id, with an `## Open questions` section that is not `none`, or without the paragraph of rule 6 (also `N` of 0, 4 or text) is refused; REQ-027 AC3.
- Rules 1 and 10: `check` without `--final` on the good draft prints what it printed before, and refuses a spec `Approved` and an ADR `Accepted`; REQ-027 AC4.
- Rules 2 and 3: a pull request whose first commit already carries the approved statuses, whose only commit is the approving one, or whose `HEAD~1` fails a check of C1 to C9, is refused; REQ-027 AC5.
- Rules 1, 4 and 7: the mode runs with the network and the model unreachable, the requirement is `planned` at `HEAD`, and a test that the mode reads no file other than the three, `agk.toml` and git; REQ-027 AC6.
- Rule 8: a test reads `skills/spec/SKILL.md` and `intake.py next-steps` for the lines of rule 8 and for no forbidden verb (SPEC-0005 rule 10); REQ-027 AC1.

## Proof

REQ-027 AC1 and AC4: *a requirement can reach the default branch approved in one merge, and the old path is untouched.* Rules 1 and 4. REQ-027 AC2, AC3 and AC5: *the approving commit cannot carry anything but
the two status lines, a question, or a draft that was not already good.* Rules 2 to 6. REQ-027 AC6: *nothing new is read or decided by the kit.* Rule 7. The first intake after the build that is
merged in one pull request, with the number of the maintainers' round trips it took, is recorded by the maintainers in `docs/runs/method-weight-2.md`.

## Residual

- 2026-10-21: the ADR stub's Decision text (SPEC-0012 rule 8) says the spec "stays `Draft` until its open questions are ruled and a later change sets it `Approved`"; after an approving final commit that sentence is stale for the ADR it sits in. The stub is fixed text and is not changed here (due 2026-12-31).
- 2026-10-21: a check cannot see the maintainers' word (rule 7); a session that makes the approving commit without it is caught only by the review of the pull request (due 2026-12-31).
- 2026-10-21: L3 generalises the status-lines check into governance and the metrics; until then the final-commit mode is the only place that knows the two lines (due 2026-12-31).

## Open questions

none
