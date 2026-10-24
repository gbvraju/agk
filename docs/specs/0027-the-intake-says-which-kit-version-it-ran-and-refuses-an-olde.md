# SPEC-0027: The intake says which kit version it ran and refuses an older one, and a question answered at review has a true form

- Status: Approved
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-034

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "The intake says which kit version it ran and refuses an older one, and a question the maintainers answered at review, before approval, has a true form that the final check accepts." It is the fourth item of the stable-release brief, generic and project-agnostic: it holds for every project the kit is installed in and names no project and no reader. Evidence: an intake ran from a plugin much older than the kit installed in the project it ran against and produced files the newer checks did not expect; and an intake whose questions were answered at review could not truthfully say "before it was written", so the final check refused the true wording.
The maintainers answered 3 questions before it was written: the intake prints the kit version of the script that ran in the first line of its output and refuses, naming the rule and both versions, when that version is older than the one in `agk.toml`, while a newer version runs and prints a one-line note; the opening paragraph of an intake spec may say either that the maintainers answered N questions before it was written or that they answered N questions at review, before approval, each followed by the answers, and `check --final` accepts both while still requiring no open question and a final commit that changes only the status lines, neither form being usable for questions answered after approval; and `check --final` also accepts "The maintainers gave N answers before it was written" for any N when the answers were given in a brief or an issue and not as interview questions, the cap of three applying to interview questions only.

## Rules

1. **The first line.** Every command of `scripts/agk/intake.py` (`ids`, `stub`, `check`, `check --final`, `next-steps`, `renumber`) prints, as the first line of its output, `intake: kit <version>`, the `kit_version` of `kit/manifest.json` in the root of the script that ran (the plugin or kit root above `scripts/`). The rest of the output follows on the lines after it and is unchanged. If that manifest cannot be read, the command refuses naming the rule and the file class and prints no version; it never guesses a version.
2. **An older script is refused.** When the project in `--root` records a kit version in `agk.toml` (`version`, as `common.installed_version` reads it) and the version of the script is older, the command refuses after the first line: `refused: rule 2: the kit version of the script is older than the one the project records (script <a>, project <b>)`, naming both versions, and writes nothing. Versions are compared as dotted whole numbers; a version that is not of that form is not compared and the command runs. A project that records no version is not compared.
3. **A newer script runs.** When the version of the script is newer than the one the project records, the command runs and prints one line after the first: `note: the script is newer than the kit the project records (script <a>, project <b>)`. An equal version prints no note. Neither the refusal nor the note makes a network call.
4. **The forms of the opening paragraph.** The text before the first `## ` heading of the spec contains one of these, and `check --final` accepts each: (a) `The maintainers answered N questions before it was written` for N of 1 to 3 (`1 question` for one) and the zero form of SPEC-0020 rule 6, as now; (b) `The maintainers answered N questions at review, before approval` for N of 1 to 3 (`1 question` for one), used when the questions were asked and answered while the pull request was under review and before the approving commit; (c) `The maintainers gave N answers before it was written` for any whole N from 1 (`1 answer` for one), used when the answers were given in a brief or an issue and not as interview questions. The cap of three belongs to the interview questions of (a) and (b) only. The answers are written after the sentence, in the same paragraph.
5. **Never after approval.** None of the forms may be used for a question answered after the approving commit: a question raised after approval is a new pull request. A check cannot see when an answer was given, so the rule is the author's and the reviewers'; `check --final` refuses any wording that is not one of the forms of rule 4, including a review form that says `after approval`.
6. **The rest of `check --final` is unchanged.** It still requires that the spec has no open question or question id, that the draft before the last commit passes the checks of `check`, and that the approving commit changes exactly the two status lines (SPEC-0020 rules 2 to 5). It reads git and the files of the work tree only and makes no network call. The refusal for the paragraph names the rule and never the sentence.
7. **How it changes.** SPEC-0012 and SPEC-0020 are Approved: the build changes them by `docs/runs/proposed-spec-amendments-N.md`, applied by its ADR: SPEC-0012 (the first line, the refusal and the note), SPEC-0020 rule 6 (the forms of the paragraph). `intake.py` and its tests are kit-only (SPEC-0012 rule 18), and `skills/spec/SKILL.md` says which form to write, so the build is a kit change: a bump, the hashes, the plugin and `agk.toml` versions, and an ADR that names the protected classes it touches. It is small.
8. **The tests.** Fixtures in `tmp_path`: each command prints the version first and the rest unchanged; a project recording a newer version refuses with both versions and writes nothing; a newer script prints the note; an equal version and a project with no version run with no note; each form of rule 4 passes `check --final` and the old forms still pass; another wording, a number outside the range, `at review` with N of 4, `gave 0 answers` and `after approval` are refused with the rule named and never the sentence; an open question and a final commit with a third line are still refused. No network and no model.

## Tests

- Rule 1: each command prints `intake: kit <version>` first and the rest of its output is unchanged; REQ-034 AC1.
- Rules 2 and 3: a newer recorded version refuses with both versions and writes nothing; a newer script prints the note; an equal version, a version that is not dotted numbers and no recorded version print no note; REQ-034 AC2; REQ-034 AC3.
- Rule 4: forms (a), (b) and (c) pass `check --final`, with the numbers at the edges of their ranges; REQ-034 AC4; REQ-034 AC5.
- Rule 5: the review form with N of 4 or 0, the interview forms with N of 4, `gave 0 answers`, and a paragraph that says `after approval` are refused, naming the rule and not the sentence; REQ-034 AC6.
- Rule 6: an open question, a final commit with a third line and the old refusals are unchanged; REQ-034 AC7.

## Proof

REQ-034 AC1 to AC3: *an intake cannot silently run from a kit older than the project's, and says what it ran.* Rules 1 to 3. REQ-034 AC4 to AC6: *a spec can say truthfully when its questions were answered, and the final check accepts the true wording and nothing else.* Rules 4 and 5. REQ-034 AC7: *the approving commit is as safe as before.* Rule 6.

## Residual

- 2026-10-24: a check cannot see when an answer was given, so a review form used for an answer given after approval is caught only by the review of the pull request (rule 5) (due 2026-12-31).

## Open questions

none
