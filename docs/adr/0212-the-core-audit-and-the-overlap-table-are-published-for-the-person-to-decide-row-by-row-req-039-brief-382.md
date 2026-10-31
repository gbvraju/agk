# ADR-0212: the core audit and the overlap table are published for the person to decide row by row (REQ-039, brief 382)

- Status: Proposed
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0188, ADR-0210, ADR-0211
- Requirements: REQ-039

## Context

Brief #382 (priority 2, split from plan #278): plan #278 answer 2 says to measure first and publish the table in the ADR
before anything is removed. Answer 3 says overlapping rules are merged through spec amendments, a check is retired only
with an ADR that names what replaces it, and no safety rule (secrets, protected paths, approvals, privacy) is weakened to
make the core smaller.

The evidence, both written on 2026-10-31 (the date from `date -u`) and committed in this pull request:

- `docs/runs/core-audit-2026-10-31.md`, written by `python3 scripts/agk/core_audit.py --write` on the default branch at
  73558ce, the whole history (no `--only`): 286 pull requests; 3 unread pages (#1 `job`, #2 `combined step`, #32
  `combined step`); of the 23 governance checks, 10 failed at least once and 13 are `cannot-check` (no counted failure in
  the pull requests that could be read, and a page that could not be read, so never zero, ADR-0210); no check is listed
  as never fired; 21 of the 33 session rules were never cited by a verdict (session rule 34 was added by #407 after the run and has
  no count); totals ADRs 217, specs 37, requirements 44,
  scripts 56.
- `docs/runs/core-overlap-1.md`: for each session rule and each spec named below, the other rules that state the same
  thing, by number, with the audit's count for each.

A count is how often a verdict cited a rule or a check refused a pull request. A rule that was never cited was never named
in a refusal; that does not show that sessions do not follow it.

## Decision

Nothing is decided by this ADR while it is Proposed. Each row below is a proposal; a person fills each `Decision:` cell
(for example `accepted`, `rejected` or `changed: <how>`) and accepts the ADR. A row that is accepted is built by a later
brief, as plan #278 answers 3 to 6 say; this ADR changes no rule, spec, check or script (brief #382 answer 4).

The proposals use three words: `keep` (no change), `merge into X` (the text moves into X, nothing of it is dropped, and the
rule's own number is no longer a rule) and `retire` (removed, with what replaces it). No row proposes `retire`.

### Governance checks

The count is the number of pull requests whose `governance` run failed on the check.

| Row | Check | Count | Proposal | Reason | Risk | Decision: |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Paused | cannot-check | keep | the pause of ADR-0196 stops every session; a safety rule | none from keeping; without it a paused kit would still accept pushes | |
| 2 | Status-only final commit | cannot-check | keep | runs the shortcut of session rule 4; no failure counted, but cannot-check is not zero | none from keeping | |
| 3 | Latest full run | at least 8 | keep | it refused pull requests | none from keeping | |
| 4 | PR states and open pull requests | cannot-check | keep | it reads what `check_pr_mode` (row 16) judges | none from keeping | |
| 5 | check_protected_changes | at least 42 | keep | the check that refused most; protected paths are a safety rule | none from keeping | |
| 6 | check_requirements | cannot-check | keep | no failure counted; re-read #1, #2 and #32 with `--only` before any retire is proposed | none from keeping | |
| 7 | check_adrs | at least 1 | keep | it refused a pull request; brief #382 answer 5 relies on it | none from keeping | |
| 8 | check_numbers | cannot-check | keep | it guards parallel sessions against duplicate numbers (SPEC-0025 rule 1) | none from keeping | |
| 9 | check_specs | at least 6 | keep | it refused pull requests | none from keeping | |
| 10 | check_neutrality | cannot-check | keep | names in tracked files are a privacy rule | none from keeping | |
| 11 | check_build_state | cannot-check | keep | no failure counted; re-read #1, #2 and #32 with `--only` before any retire is proposed | none from keeping | |
| 12 | check_kit_tests | cannot-check | keep | every check ships with tests of the check (CLAUDE.md item 4) | none from keeping | |
| 13 | check_design | cannot-check | keep | it guards the design sign-off of SPEC-0037, an approval | none from keeping | |
| 14 | reviewers --check | cannot-check | keep | the list of verdict authors and approvers is an approval rule | none from keeping | |
| 15 | reviewers --check-codeowners | cannot-check | keep | the owners of protected paths are an approval rule | none from keeping | |
| 16 | check_pr_mode | at least 10 | keep | it refused pull requests | none from keeping | |
| 17 | check_final_clearance | at least 1 | keep | it refused a pull request; approvals are a safety rule | none from keeping | |
| 18 | Release check | at least 1 | keep | it refused a pull request | none from keeping | |
| 19 | PR body shape | at least 9 | keep | it refused pull requests | none from keeping | |
| 20 | Lint | at least 6 | keep | it refused pull requests | none from keeping | |
| 21 | Tests of the checks | at least 30 | keep | it refused pull requests | none from keeping | |
| 22 | Project tests | cannot-check | keep | the step a project's own tests run in; no failure counted in this repository | none from keeping | |
| 23 | Secret scan | at least 20 | keep | it refused pull requests; secrets are a safety rule | none from keeping | |

### Session rules

The count is the number of verdicts that cite the rule; the overlaps are those of `docs/runs/core-overlap-1.md`.

| Row | Rule | Count | Proposal | Reason | Risk | Decision: |
| --- | --- | --- | --- | --- | --- | --- |
| 24 | session rule 1 | 1 | keep | what a session acts on, and the decided base of rules 16, 20 and 24 | none from keeping | |
| 25 | session rule 2 | 0 | keep | never merge, never touch a secret: a safety rule, stated again by rules 29 and 30 | a merge could drop a safety sentence | |
| 26 | session rule 3 | 0 | keep | one open pull request and `Depends-on` | none from keeping | |
| 27 | session rule 4 | 0 | keep | the one exception to the full suite | none from keeping | |
| 28 | session rule 5 | 0 | keep | how the next item is found | none from keeping | |
| 29 | session rule 6 | 0 | merge into session rule 21 | rule 21 states how a session asks when blocked; rule 6 states two of the cases | rule 21 must keep both cases of rule 6 | |
| 30 | session rule 7 | 1 | keep | checkpoints and draft pull requests | none from keeping | |
| 31 | session rule 8 | 0 | keep | the progress line | none from keeping | |
| 32 | session rule 9 | 0 | keep | resuming a stalled pull request | none from keeping | |
| 33 | session rule 10 | 0 | keep | how `watch` is started; receives row 47 | none from keeping | |
| 34 | session rule 11 | 0 | merge into session rule 33 | rules 11, 23 and 33 each say what runs first on a start or restart; one rule gives the order once | the order of `doctor.py --paused`, `push-check` and `queue` must be stated, not lost | |
| 35 | session rule 12 | 0 | keep | the usage figure | none from keeping | |
| 36 | session rule 13 | 2 | merge into session rule 31 | both say what runs before every push | "never rebases or force-pushes" guards history and must move whole | |
| 37 | session rule 14 | 1 | merge into session rule 15 | rule 14 only defines the files rule 15 resolves | none beyond the renumbering of the Consequences | |
| 38 | session rule 15 | 0 | keep | which conflicts a session resolves; receives row 37 | none from keeping | |
| 39 | session rule 16 | 0 | merge into session rule 17 | both say where `Question:` and `Report:` live | rule 17 must keep the shapes of both comments | |
| 40 | session rule 17 | 1 | keep | where each comment lives; receives row 39 | none from keeping | |
| 41 | session rule 18 | 0 | keep | what a builder does after its merge | none from keeping | |
| 42 | session rule 19 | 0 | keep | a cause is reproduced first | none from keeping | |
| 43 | session rule 20 | 0 | keep | the `Correction:` channel | none from keeping | |
| 44 | session rule 21 | 1 | keep | how a blocked session asks; receives row 29 | none from keeping | |
| 45 | session rule 22 | 1 | keep | the branch the runtime gives; no other rule states it | none from keeping | |
| 46 | session rule 23 | 0 | keep | the outage line; its restart sentence moves to rule 33 if row 34 is accepted | none from keeping | |
| 47 | session rule 24 | 1 | merge into session rule 10 | both say when `watch` ends | the "newer than the last `Report:`" detail must move whole | |
| 48 | session rule 25 | 0 | keep | the shadow's comment | none from keeping | |
| 49 | session rule 26 | 0 | keep | the marks | none from keeping | |
| 50 | session rule 27 | 1 | keep | the summary line | none from keeping | |
| 51 | session rule 28 | 1 | keep | closing a brief | none from keeping | |
| 52 | session rule 29 | 1 | keep | the person's confirmation: an approval rule | a merge could weaken an approval | |
| 53 | session rule 30 | 3 | keep | local mode, the rule cited most | none from keeping | |
| 54 | session rule 31 | 0 | keep | the pre-push run; receives row 36 | none from keeping | |
| 55 | session rule 32 | 0 | keep | messages through GitHub | none from keeping | |
| 56 | session rule 33 | 0 | keep | the pause check; receives row 34 | none from keeping | |
| 57 | session rule 34 | not in the audit | keep | added by #407 after the audit; a bug outside the brief is filed, not fixed | row 29 must keep rule 34's case beside rule 6's "a check fails in a way the brief does not cover" | |

### Specs

Each row is a spec with rules that a session rule states again (`docs/runs/core-overlap-1.md`, second table).

| Row | Spec rules | Count | Proposal | Reason | Risk | Decision: |
| --- | --- | --- | --- | --- | --- | --- |
| 58 | SPEC-0023 rule 2 | 0 | keep | the decided source of session rule 2 | none from keeping | |
| 59 | SPEC-0025 rules 2, 3, 5 and 6 | 0, 1, 2, 0 | keep | the decided source of session rules 3, 14 and 15 | none from keeping | |
| 60 | SPEC-0030 rules 1, 2 and 3 | 0, 0, 0 | keep | rule 1 asks for the session rules file; rows 29, 34 and 47 change the session rules, not this spec | an accepted merge may need an amendment that names the new rule numbers | |
| 61 | SPEC-0032 rules 3, 4, 5, 6, 8, 9 and 10 | 2, 1, 2, 1, 0, 0, 0 | keep | the decided source of session rules 2, 10, 11, 19, 20 and 29 | none from keeping | |
| 62 | SPEC-0033 rules 1, 2, 3, 4, 5, 7 and 8 | 1, 0, 0, 0, 0, 0, 0 | keep | rule 1 asks for one numbered session rule | none from keeping | |
| 63 | SPEC-0034 rules 5, 7, 9, 11 and 12 | 2, 0 (7b 1, 7c 1), 0, 1, 0 | keep | rule 7 names the shared-mechanical list of the session rules | rows 36 and 37 move the rules it points at | |
| 64 | SPEC-0035 rules 1, 2, 3 and 7 | 2, 0, 1, 0 | keep | rule 7 asks the session rules for the shapes | none from keeping | |
| 65 | SPEC-0036 rules 1 and 6 | 2, 0 | keep | the decided source of session rule 27 | none from keeping | |

## Consequences

- The person decides each row in one place, and nothing is removed before a row is decided.
- An accepted `merge into` row changes `config/session-rules.md`, a protected path, by its own brief with an ADR that names
  the class. The merged rule's number is cited by verdicts, ADRs and the counts of `core_audit.py`; that brief says whether
  the number is left as a pointer or reused (session rule 15 already moves a rule number to the next free one).
- The 13 `cannot-check` checks can be re-read with `python3 scripts/agk/core_audit.py --only 1,2,32` before any later
  proposal to retire one; such a run is not written as a page (ADR-0210).

## Residual

- Every `Decision:` cell is empty until a person fills it (2026-10-31).
