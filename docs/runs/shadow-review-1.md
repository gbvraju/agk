# Shadow review 1 (SPEC-0003 rule 23)

Date of the run: 2026-10-15 (`date -u`). Operator: a session separate from the implementation sessions, read-only on
product code. Kit scripts (`review_context.py`, `check_review_report.py`) and the `reviewer` subagent definition are
from `origin/main` fa30cea; each target was checked out detached in its own worktree. Contexts were built with
`--base <the PR's base commit>`. Every report below is the first and only report for its target and is recorded
verbatim; no verdict was changed after the human reviews were read. The human reviews were read only after the four
reports were saved.

## Limitations of this run (read first)

- **PR body.** The GitHub API returns only the current PR body, not the body as it stood at an earlier commit. For #12
  and #6 the body used was the final body, paired with the first commit's diff. The body therefore describes fixes the
  diff does not yet contain. This is a defect of the run's input, not of the agent, and it produced every finding
  on #12 and #6. For #22 (final commit) and #23 (single commit) the body and the diff correspond.
- **Human verdicts.** The PR conversations of #6, #12, #22 and #23 hold no comments, reviews or review threads
  (API read on 2026-10-15), and `docs/runs/decisions-log.md` has no `Review verdict (human):` line for them. The
  human findings below are those named in the shadow-review brief, with the fixes recorded in the PR bodies and in
  `docs/runs/day-3.md`, `day-5.md`. The human verdicts are inferred, marked (inferred); the maintainers should
  confirm them.
- Four reports are too few to say whether the agent can be relied on; that is for the maintainers (principle 1).

## Summary

| PR | Commit | Agent verdict | Validator | Truncated | Human verdict | Agreement | Caught | Missed | Noise |
|---|---|---|---|---|---|---|---|---|---|
| #12 | bd381ef (first) | fix list (3) | ok | no | fix list (inferred) | yes | partially (1 of 1) | 0 clear misses | 3 (input artefacts) |
| #6 | e001628 (first) | fix list (1) | ok | no | fix list (inferred) | yes | 0 of 1 | 1 | 1 (input artefact) |
| #22 | 312e82a (final) | cleared (0) | ok | no | merged (inferred: cleared) | yes | not testable (fixed before this commit) | 0 | 0 |
| #23 | 9d39017 (open) | rejected (2) | ok | no | none yet | not comparable | not comparable | not comparable | not comparable |

## PR #12 — chore(k2): ADR-0007 shared kit layout (REQ-010), first commit bd381ef, base 0114a93

- Context truncated: no. Validator: `ok review-report`, footer `<!-- agk-review: verdict=fix list findings=3 truncated=false -->`.
- Report (verbatim):

~~~~
Verdict: fix list
Context truncated: no

1. Where: docs/adr/0007-shared-kit-layout.md:H16
   Rule: principle 10
   Wrong: The PR body says ADR-0007 is set to Accepted and gains a Consequences line about `project_tests`, but the ADR in the diff is `Status: Proposed` and has no such line.
   Fix: Add the final ADR-0007 commit to the diff, or correct the PR body to say what the diff contains.

2. Where: docs/runs/proposed-spec-amendments-2.md:H18
   Rule: principle 6
   Wrong: The PR body says the spec amendments were applied to `docs/specs/0001-agk-init.md` and `docs/specs/0002-agk-adopt.md`, but the diff has no hunk for either spec and the amendments file says "Proposed. Not applied."
   Fix: Include the spec edits in the diff, or remove the "applied" claim from the PR body.

3. Where: PR body
   Rule: principle 10
   Wrong: The body describes "project_tests", "agk-project-test", a "Project tests" workflow step and "Review fix 2" (no `[tool.agk]` table on new installs). The diff has none of these: the Makefile `test` target and the workflow have no project-test step, and `agk.mk` has no `agk-project-test` target.
   Fix: Add the missing changes to the diff, or rewrite the Decisions taken and Verified sections to match it (the 199-test count is also unsupported by the diff).
~~~~

- Human verdict: fix list (inferred from "Review fix 1" and "Review fix 2" in the PR body).

### Human findings

- CI no longer runs project tests (the first commit's workflow and `Makefile` do not run `project_tests`; fixed by
  `agk-project-test`): **partially**. Agent finding 3 observes that the first commit has no project-test step and no
  `agk-project-test` target, but only because the final body claims them. Against a body of the first commit the
  agent would have had no claim to contrast with, so whether it catches the defect itself is not shown by this run.

### Agent findings the human did not raise

- 1 (ADR-0007 Proposed vs body): **noise** — input artefact; the Accepted flip is the final commit.
- 2 (spec amendments not applied): **noise** — input artefact; applied in the second commit on the maintainers' instruction.
- 3 (body vs diff): **noise** for everything except the project-test absence counted above; the rest is the same artefact.

## PR #6 — chore(k1): agk init, kit manifest and templates, ADR-0004 (REQ-009), first commit e001628, base b21f79c

- Context truncated: no. Validator: `ok review-report`, footer `<!-- agk-review: verdict=fix list findings=1 truncated=false -->`.
- Report (verbatim):

~~~~
Verdict: fix list
Context truncated: no

1. Where: PR body
   Rule: principle 1
   Wrong: The PR body says ADR-0004 is set to Accepted, but the ADR in the diff (docs/adr/0004-init-protected-list-and-neutral-context.md:H8) still has `Status: Proposed`, so the protected-path changes are covered by an ADR that is not yet a decision.
   Fix: Either change the ADR's Status line to Accepted in this PR, if the maintainers' ruling is recorded, or correct the PR body and Build-state row to say Proposed and leave the flip to the maintainers.
~~~~

- Human verdict: fix list (inferred from the "reviewer fix" for CLAUDE.md rule 8 and the ADR-0004 ruling in `docs/runs/day-3.md`).

### Human findings

- CLAUDE.md rule 8 wrong for installed targets (the first commit's rule referred to a file the target does not have;
  fixed to the neutrality.txt wording): **missed**. The agent did not mention CLAUDE.md. Whether it could have seen it is
  open: the first-commit diff contains the CLAUDE.md text, and the Principles section of the context carries the rule
  it breaks, but the finding needs knowledge of the installed layout that the context does not carry.

### Agent findings the human did not raise

- 1 (ADR-0004 Proposed vs body): **noise** — input artefact (final body, first commit); the Accepted flip was the
  maintainers' ruling and is made in the second commit, not a defect of the first.

## PR #22 — feat(k2): reviewer agent per SPEC-0003 (REQ-013), final commit 312e82a, base e78d67d

- Context truncated: no. Validator: `ok review-report`, footer `<!-- agk-review: verdict=cleared findings=0 truncated=false -->`.
- Report (verbatim):

~~~~
Verdict: cleared
Context truncated: no

Findings: none
~~~~

- Human verdict: merged 2026-10-15 after the final commit (inferred: cleared).

### Human findings

- Installed check's tests not installed (principle 4): **not testable here**. The finding applied to the first
  commit; the final commit 312e82a, which the brief names as the target, already moves the tests to `tests/kit/`. The
  agent saw the fixed state and rightly raised nothing. A review of the first commit of #22 would test this finding;
  it was not part of this run.

### Agent findings the human did not raise

- None.

## PR #23 — feat(k2): drift audit per SPEC-0004 (REQ-011, ADR-0012), commit 9d39017, base fa30cea (open)

- Context truncated: no. Validator: `ok review-report`, footer `<!-- agk-review: verdict=rejected findings=2 truncated=false -->`.
- Report (verbatim):

~~~~
Verdict: rejected
Context truncated: no

1. Where: .github/workflows/drift-audit.yml:H1
   Rule: SPEC-0004 rule 21
   Wrong: The workflow runs the `gh issue list` verb, but the Approved rule allows only `issue create`, `issue edit` and `label create`. The PR itself asks about this in Q-K2-23, and `docs/runs/proposed-spec-amendments-8.md` proposes the change without applying it.
   Fix: Maintainers decide on amendments 8 item 2; until the spec is amended, find the open audit issue without `gh issue list`.

2. Where: tests/kit/test_drift_workflow.py:H11
   Rule: SPEC-0004 rule 21
   Wrong: The `ALLOWED_GH` set includes `issue list`, so the workflow shape test accepts a verb the Approved rule does not allow.
   Fix: Keep the test at the rule 21 verbs until maintainers apply amendments 8, or remove `issue list` together with the workflow call.
~~~~

- Human verdict: none yet (PR open, no comment or review). To be compared when the maintainers review.

### Provisional notes (not a comparison)

- Finding 1: a real deviation from the Approved text, but the PR discloses it as Q-K2-23 and proposes amendments 8.
  Whether "rejected" is proportionate to a disclosed question is for the maintainers.
- Finding 2: follows from finding 1 (same call, same rule).

## Per-PR summary

- #12: verdict agreement yes (inferred); caught partially (1 of 1); missed 0 clear; noise 3 (all input artefacts).
- #6: verdict agreement yes (inferred); caught 0 of 1; missed 1 (CLAUDE.md rule 8 for installed targets); noise 1.
- #22: verdict agreement yes (inferred); caught n/a (defect fixed before the target commit); missed 0; noise 0.
- #23: not comparable until a human review exists.
