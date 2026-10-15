# Shadow review 2 (SPEC-0003 rule 23)

Date of the run: 2026-10-15 (`date -u`). Re-run of the three targets of shadow review 1 (`docs/runs/shadow-review-1.md`,
PR #24, judged inconclusive by the maintainers: the bodies did not match the diffs and the human verdicts were not in
the repository). Kit scripts and the `reviewer` subagent definition are from `origin/main` fa30cea; each target was
checked out detached in its own worktree. Each context was built with `--base <the PR's base commit>` and a **minimal
body** holding only `Advances:` and a dated `Build-state row:` (both pass `check_pr_body.py`). Each report was saved,
and validated, before this comparison was written. Reports are recorded verbatim. No report is invalid. All three
contexts say `Truncated: no`. Item 4 (#23) was not re-run, as instructed.

## Targets

| PR | Commit | Base | Minimal body |
|---|---|---|---|
| #12 | bd381ef (first of 3) | 0114a93 | `Advances: REQ-010, REQ-009` and `Build-state row: 2026-10-14 \| Shared kit layout: agk.mk, agk.toml, default branch, per-mode protected lists \| REQ-010, REQ-009` |
| #6 | e001628 (first of 3) | b21f79c | `Advances: REQ-009, REQ-001, REQ-003, REQ-005` and `Build-state row: 2026-10-14 \| agk init, kit manifest and templates, ADR-0004 \| REQ-009, REQ-001, REQ-003, REQ-005` |
| #22 | 071ded6 (first of 2) | e78d67d | `Advances: REQ-013` and `Build-state row: 2026-10-15 \| Reviewer agent: review_context.py, check_review_report.py, reviewer subagent, ADR-0011 \| REQ-013` |

## Reports (verbatim) and validator

All three reports are the same text. Validator on each: `ok review-report`,
footer `<!-- agk-review: verdict=cleared findings=0 truncated=false -->`.

~~~~
Verdict: cleared
Context truncated: no

Findings: none
~~~~

## Human verdicts (as given by the maintainers, verbatim)

The instruction said to record the human verdicts verbatim from "the table above", i.e. the summary table of shadow
review 1; the pasted text was a placeholder, so the rows of that table for these three PRs are recorded here as
given. Their human columns are: #12 "fix list (inferred)", #6 "fix list (inferred)", #22 "merged (inferred: cleared)".
The #22 row refers to the final commit. This run reviews #22's first commit, where the human finding is the principle 4
finding below, so the verdict for that commit is read as `fix list` from that finding. Q-SR2-1 asks the maintainers to confirm.

| PR | Commit (shadow review 1) | Agent verdict | Findings | Human verdict | Agreement | Caught | Missed | Noise |
|---|---|---|---|---|---|---|---|---|
| #12 | first, `bd381ef` | fix list | 3 | fix list (inferred) | yes | partially | 0 clear | 3 (all from the body mismatch) |
| #6 | first, `e001628` | fix list | 1 | fix list (inferred) | yes | 0 of 1 | 1 (CLAUDE.md rule 8) | 1 (same cause) |
| #22 | final, `312e82a` | cleared | 0 | merged, so cleared (inferred) | yes | not testable | 0 | 0 |

Human findings named by the maintainers: #12 CI no longer runs project tests; #6 CLAUDE.md rule 8 wrong for
installed targets; #22 the installed check's tests are not installed (principle 4).

## Comparison

| PR | Agent verdict | Human verdict | Agreement | Human finding | Result | Agent findings |
|---|---|---|---|---|---|---|
| #12 | cleared | fix list (inferred) | **no** | CI no longer runs project tests | **missed** | none |
| #6 | cleared | fix list (inferred) | **no** | CLAUDE.md rule 8 wrong for installed targets | **missed** | none |
| #22 (first commit) | cleared | fix list (inferred from the finding) | **no** | installed check's tests not installed (principle 4) | **missed** | none |

No agent finding exists, so no finding is marked valid or noise.

### #12

- Missed: with an honest body the agent cleared. The defect is a CI behaviour (the workflow and `Makefile` no longer
  run `project_tests`); the first commit's diff shows the workflow and `Makefile`, but the body claims nothing about
  project tests and Approved text has no rule that says CI must run them (SPEC-0002 rule 5 was amended in the same
  PR, per `docs/runs/proposed-spec-amendments-2.md`). SPEC-0003 rule 11 limits the review to rules stated in Approved
  text, so this is outside what the agent is asked to check.
- Shadow review 1's partial catch is withdrawn: it depended on the final body naming the missing step.

### #6

- Missed. **The human finding is semantic and outside SPEC-0003 rule 11.** Rule 11 limits the reviewer to rules stated
  in Approved text (REQ test markers, an ADR naming each protected class, ADR/spec status, the body's `Advances:` and
  `Build-state row:`, no `docs/build-state.md` edit, diff inside the paths the body names, with no style opinions and
  no speculation about intent). That a CLAUDE.md rule is wrong in an installed target needs knowledge of the installed
  layout; no rule 11 item covers it. The agent did what the spec asks; a miss here is a scope limit of the spec, not a
  fault of the agent.

### #22 (first commit)

- Missed. Principle 4 (tests of the checks ship with the checks) is a numbered principle and is in the context's
  Principles section, but rule 11 lists no check that installed checks ship with tests in the installed layout, and at
  071ded6 the tests sit in `tests/kit_dev/`. Whether the agent could be expected to infer it is a question for the
  maintainers.

## Observations (facts only; the maintainers decide, principle 1)

- With bodies that match the diffs, the agent cleared all three first commits; with the final bodies against the same
  commits (review 1) it found body-versus-diff mismatches. The agent's findings in review 1 therefore came from
  mismatches, and none from the defects the humans found.
- All three human findings are outside the checks that SPEC-0003 rule 11 lists. Zero of three caught.
- Three reports are too few to estimate a rate; #23 has no human review yet.

## Questions

- Q-SR2-1: confirm the human verdicts recorded above (they were inferred in shadow review 1 and were not pasted into
  the instruction); in particular the verdict for #22's first commit.
- Q-SR2-2: whether the three human findings should become checkable rules (an amendment to SPEC-0003 rule 11), or the
  reviewer agent is meant to stay limited to Approved-text conformance. Not decided here.
