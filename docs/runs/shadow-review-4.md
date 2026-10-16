# Shadow review 4 (K3 criterion e, ADR-0015, SPEC-0003 rule 23)

Date of the run: 2026-10-16 (`date -u`). Kit scripts and the `reviewer` subagent definition are from `origin/main`
3a3686f. Each target was checked out detached in its own worktree. Contexts were built with
`review_context.py --base <merge base of the commit and origin/main>`. The body was **minimal**: the commit subject as
the title and an `Advances:` line, nothing else (no `Build-state row:`, no paths). One run per target; no re-runs,
no prompt changes, no hints. The PR conversations, verdict comments, later commits, decisions-log rows, ADR changes and
proposed spec amendments of #38 and #41 were not read before all five reports were saved. Reports are recorded
verbatim. The maintainers pasted the human findings after the reports were saved; no report was changed afterwards.

## Criterion e, as written

The reviewer catches at least 3 of 5 findings: the 3 recorded shadow findings (#12, #6, #22) plus at least 2 new
held-out K3 findings, with at least 1 held-out finding caught. Otherwise the reviewer is moved to experimental.

## Targets

| PR | Commit | Base | Kind | Minimal body `Advances:` | Context `Truncated:` | Validator |
|---|---|---|---|---|---|---|
| #12 | bd381ef | 0114a93 | recorded shadow finding | REQ-010, REQ-009 | yes (850 lines omitted) | **FAIL** (below) |
| #6 | e001628 | b21f79c | recorded shadow finding | REQ-009, REQ-001, REQ-003, REQ-005 | no | **FAIL** (below) |
| #22 | 071ded6 | e78d67d | recorded shadow finding | REQ-013 | yes (499 lines omitted) | `ok review-report`, `<!-- agk-review: verdict=fix list findings=1 truncated=true -->` |
| #38 | c3a7ed3 | 3474d94 | held-out K3 | REQ-012 | yes (2342 lines omitted) | **FAIL** (below) |
| #41 | d846e41 | c815150 | held-out K3 | REQ-002 | yes (1312 lines omitted) | `ok review-report`, `<!-- agk-review: verdict=fix list findings=1 truncated=true -->` |

The `Advances:` lines for #38 and #41 were inferred from the REQ markers in each commit's diff (the PR bodies were not
read) and were confirmed by the maintainers (REQ-012 and REQ-002).

Validator messages:

- #12: `FAIL review-report: finding 1 field Fix: must stay on one line`; `FAIL review-report: finding 1 field Rule:
  does not resolve to a rule in the context`.
- #6: `FAIL review-report: finding 1 field Fix: must stay on one line`.
- #38: `FAIL review-report: finding 1 field Fix: must stay on one line`.

The "must stay on one line" failures come from free text the agent added after the finding (a "checked, no finding"
or "notes" list); the validator counts those lines as continuation of the last field. Per the template, a report that
fails the validator is recorded as invalid and counts as no verdict. The text is still recorded and compared below,
because the brief asks for every report to be compared; the invalidity does not change the score.

## Reports (verbatim)

### #12 (bd381ef)

~~~~
Verdict: fix list
Context truncated: yes

1. Where: PR body
   Rule: CLAUDE.md operating rule 7 as restated in the context (the PR body has `Advances:` and a dated `Build-state row:`)
   Wrong: The PR body has `Advances: REQ-010, REQ-009` but no dated `Build-state row:` line. It also states no paths the diff changes, so the "diff stays inside the paths the PR body says it changes" check cannot pass.
   Fix: Add a `Build-state row: <date from date -u> ...` line to the PR body, and name the paths the PR changes.

Notes, none of them findings:
- The context was truncated: parts of the Referenced specs and ADRs section and one test file were omitted. I checked everything that was present.
- Both advanced requirements have test markers: REQ-010 in `tests/kit/test_agk_config.py` and `test_agk_mk.py`, REQ-009 in the kit_dev tests.
- The ADR-0007 file in the diff names every changed protected class, including `agk.mk` and `agk.toml`.
- `docs/build-state.md` is not edited.
- No Accepted ADR is edited beyond Status. Approved specs are not edited; the changes go through `docs/runs/proposed-spec-amendments-2.md`.
- Accepted ADR-0001, ADR-0003 and ADR-0004 are not contradicted. `make governance` still runs the checks through the aliases, the settings still allow only the one push command, and the repository's protected list is the installed list plus `kit/` and `tests/kit_dev/`.
- I found no contradiction with SPEC-0002 rules 5-8, 10 and 12 for the shared-kit step.
~~~~

### #6 (e001628)

~~~~
Verdict: fix list
Context truncated: no

1. Where: PR body
   Rule: principle 10
   Wrong: The PR body has an `Advances:` line but no dated `Build-state row:` line, and it names no paths the diff changes, so the diff cannot be checked against them.
   Fix: Add a `Build-state row:` line with a `date -u` date to the PR body, and list the changed path classes in it. The run report docs/runs/day-3.md says "See the PR body" for Verified, so add `Verified:` too.

Checks that found nothing:
- ADR-0004 names every changed protected class and is Proposed, so no Accepted ADR is edited.
- SPEC-0001 is not edited.
- docs/build-state.md is not touched.
- The init.py, manifest and template changes match SPEC-0001 rules 1-24. I could not read the bodies of the other verbatim files, which are unchanged in this diff, so I could not confirm rule 20 for them.
- Every advanced requirement has markers in the repository: REQ-009 in tests/kit_dev, REQ-003 in tests/kit and tests/kit_dev, REQ-001 in tests/kit and tests/kit_dev, and REQ-005 in tests/kit/test_reviewers.py.
~~~~

### #22 (071ded6)

~~~~
Verdict: fix list
Context truncated: yes

1. Where: PR body
   Rule: SPEC-0003 rule 11
   Wrong: The PR body has an `Advances:` line but no dated `Build-state row:` line, and it names no paths the diff changes.
   Fix: Add a `Build-state row: <date> | <change> | REQ-013` line, with the date from `date -u`, and list the paths the PR changes.
~~~~

### #38 (c3a7ed3)

~~~~
Verdict: fix list
Context truncated: yes

1. Where: PR body
   Rule: principle 10
   Wrong: The PR body has `Advances: REQ-012` but no dated `Build-state row:` line.
   Fix: Add a `Build-state row:` line with a date taken from `date -u`. Do not edit `docs/build-state.md`.

Checked and no finding:
- All four REQ-012 criteria (AC1 to AC4) have test markers in the diff.
- ADR-0016 names every protected class the diff touches.
- No Accepted ADR is edited.
- No Approved spec is edited. The departures from SPEC-0007 are listed in `docs/runs/proposed-spec-amendments-10.md`, and that file names SPEC-0007.
- I found no contradiction with SPEC-0007 rules 11 to 19 or with the ADR-0016 decisions.
- The diff does not touch `docs/build-state.md`.
- The "diff stays inside the paths the PR body says it changes" check could not be run, because the PR body names no paths.
- I read the context only as far as the truncation allows. The SPEC-0007 text and the changed-file listings were fully visible. Some fixtures and the later part of `metrics.py` were not read.
~~~~

### #41 (d846e41)

~~~~
Verdict: fix list
Context truncated: yes

1. Where: PR body
   Rule: principle 10
   Wrong: The PR body has `Advances: REQ-002` but no dated `Build-state row:` line, and it names no paths the diff changes, so "the diff stays inside the paths the body says" cannot be checked.
   Fix: Add a `Build-state row:` line with its date from `date -u`, and list the changed paths (or path classes) in the body.
~~~~

## Human findings (pasted by the maintainers)

| # | PR | Commit | Kind | Human finding |
|---|---|---|---|---|
| 1 | #12 | bd381ef | recorded | CI no longer runs the project's own tests: the governance workflow lost the project-tests step (the project_tests regression). |
| 2 | #6 | e001628 | recorded | CLAUDE.md rule 8 is wrong for installed targets: it states a kit-repo rule that does not hold in a repository the kit is installed into. |
| 3 | #22 | 071ded6 | recorded | The installed check's tests are not installed: the check is vendored into targets but its `tests/kit/` test is not, which breaks principle 4. |
| 4 | #38 | c3a7ed3 | held-out | `governance.yml` was split into one step per check without `if: ${{ !cancelled() }}`. The first failing check skips every later check step, so later failures are hidden and `blocked_weakenings` is undercounted (SPEC-0007 rules 6 and 13). |
| 5 | #41 | d846e41 | held-out | The doctor collects ruleset elements from all rulesets that target the default branch, including disabled or evaluate-mode ones, so a switched-off ruleset holding every rule plus any active ruleset reports ok while nothing is enforced: a false ok (SPEC-0006 rules 3 and 7). Secondary miss: `~ALL` and exclude targeting. |

## Scoring of the human findings

| # | PR | Result | Reason |
|---|---|---|---|
| 1 | #12 | **missed** | The only finding is about the PR body (no `Build-state row:`, no paths). Nothing about the workflow, the `Makefile` or project tests. |
| 2 | #6 | **missed** | The only finding is about the PR body. Nothing about CLAUDE.md rule 8 or installed targets. |
| 3 | #22 | **missed** | The only finding is about the PR body. Nothing about where the check's tests live or principle 4. |
| 4 | #38 | **missed** | The only finding is about the PR body. The notes say no contradiction with SPEC-0007 rules 11 to 19 was found; rules 6 and 13 and the `!cancelled()` condition are not mentioned. |
| 5 | #41 | **missed** | The only finding is about the PR body. Nothing about ruleset collection, enforcement state, or SPEC-0006 rules 3 and 7. |

No partial catches. Held-out findings caught: 0 of 2.

## Scoring of the agent findings

Every agent finding is the same one: the body has no dated `Build-state row:` line and names no paths. None is a
human finding.

| PR | Agent finding | Result | One line |
|---|---|---|---|
| #12 | Build-state row and paths missing (cites CLAUDE.md rule 7) | noise | The body was the brief's minimal body, which omits the row by construction; the finding comes from the test setup and says nothing about the diff. |
| #6 | Build-state row and paths missing; add `Verified:` | noise | Same cause. |
| #22 | Build-state row and paths missing (SPEC-0003 rule 11) | noise | Same cause. |
| #38 | Build-state row missing (principle 10) | noise | Same cause. |
| #41 | Build-state row and paths missing (principle 10) | noise | Same cause. |

These findings are correct against the body that was supplied, so none is a hallucination; they are scored noise
because the body's shape was fixed by the brief and is not a defect of the PR.

## Criterion e

- Caught: **0 of 5** (needs at least 3).
- Held-out findings caught: **0** (needs at least 1).
- Criterion e: **not met.**

The consequence under ADR-0015 is for the maintainers to apply (principle 1); this record does not apply it.

## Analysis

In all five reports the agent raised only body-shape issues (missing `Build-state row:`, no paths named) that
`check_pr_body.py` already enforces deterministically, so the agent added nothing over a check that exists. The five
human findings are behaviour or semantic defects: a workflow step removed, a CLAUDE.md rule that is wrong in another
layout, tests not vendored, a missing `!cancelled()` condition, a ruleset-state false ok. None is a conformance check
of a kind SPEC-0003 rule 11 lists. Three of the five reports (#12, #6, #38) broke the report format by appending free
text after the finding, and #12 also cited a rule that does not resolve in the context; those three are invalid under
the validator. Four of the five contexts were truncated (#12, #22, #38, #41). Across shadow reviews 2, 3 and 4 the
agent has caught none of the three recorded human findings (#12, #6, #22), and in this review none of the two
held-out ones. Whether this comes from the reviewer's definition, the scope of rule 11 or the context cap is not
shown by this run.

## Questions

- Q-SR4-1: criterion e is not met; whether ADR-0015's consequence (experimental status) is applied, and whether the
  reviewer's scope is widened beyond rule 11 or left as is, are for the maintainers.
- Q-SR4-2: should the validator tolerate trailing notes, or the agent definition forbid them? Three of five reports
  failed on exactly this. Not decided here.
