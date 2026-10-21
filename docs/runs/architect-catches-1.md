# Architect catches 1 (design judgement as evidence, K5 candidate 19)

Date: 2026-10-21 (from `date -u`). AGK enforces the process well. Design judgement (the questions that expose a wrong assumption, the review that finds a test proving less than it claims) lives in the
architect session and with the maintainers, not in the kit; the reviewer agent measured 0 of 5 (`docs/runs/shadow-review-4.md`). This file records the catches with their kind and who caught them, the
architect's own misses included, so that the kit's question list and review checklist can be built from evidence and a catch rate can be measured.

## How the rows were checked

Each row of the list the maintainers gave was checked against the pull request or comment in this repository (GET only). A detail that did not match is corrected in the row and said so. A row that the
record of this repository cannot support is marked `(unverified)`: all the rows about the criterion g project, because that project is not named here (ADR-0025 decision 6) and its pull requests are not
in this repository ("project PR #n" is a pull request of that project). Nothing is added that the record does not support.

Kinds (fixed list): `wrong-assumption`, `false-declaration`, `test-proves-less`, `stale-claim`, `fragile-code`, `security`, `vendored-file-change`, `scope-rule`, `process-order`, `kit-defect`, `cost`,
`late-discovery` (a fact found after intake that should have been asked at intake). The column **Kind** is the architect's own reading `(architect-assigned)`. The column **Agrees** is the kind that the
implementation agent assigns from the record: `yes`, or `no` with its kind; a kind that the record does not support is not adopted, and a row whose record cannot be read is `not assessed`.

## The catches

| # | Date | Where | Kind (architect-assigned) | Caught by | What | Outcome | Agrees |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-19 | #81 | security | architect (the PR body calls it "the verdict"; the verdict is not posted on the PR) (unverified: caught by) | two guard bypasses: `git grep -O<program>` and `--open-files-in-pager=<program>` ran code, and the comment POST reached any repository, not only the origin | fixed in the two commits of the verdict (3 commits); the audit of every allowed git subcommand is in ADR-0042 Decision 2; merged 2026-10-19 | yes |
| 2 | 2026-10-18 | #77 | kit-defect | architect (the PR body calls it "the verdict"; the verdict is not posted on the PR) (unverified: caught by) | intake check C8 failed a Residual whose only bullet is `- none`, and C2 did not fix the names of the spec and ADR files | fixed in the two commits of the verdict (3 commits); merged 2026-10-18 | yes |
| 3 | 2026-10-20 | #93 | process-order | architect (decisions-log row "the #93 verdict") | a red commit was pushed: `311a081` after a failing `make test` | deviation recorded in ADR-0050 and in the decisions log (2026-10-20); the rule restated: the full `make test` passes before every push, no subsets | yes |
| 4 | 2026-10-20 | #103 | fragile-code | architect (the implementation agent had disclosed the choice as its reading 1 in the PR body) | At risk told "no verdict" from "not cleared" by the ending of the text `cleared_line` returns | a residual line (due 2026-12-31) in `docs/runs/residuals.md`; the code is unchanged | yes |
| 5 | 2026-10-20 | #104 | kit-defect | implementation agent | `done_on` needed `kit/facts-schema.json` and SPEC-0009 rule 8, which SPEC-0017 and the brief did not name | amendment 27 of SPEC-0009 and the schema property; Q-K4-213 raised and ruled as read | no: late-discovery |
| 6 | 2026-10-20 | #105 | cost | architect | one more GET (`pulls/{n}/commits`) per pull request in the window in `facts.py` | a residual line (due 2026-12-31) to measure; measured in `docs/runs/k5-early-live-1.md`: +33 s against the run before, not attributable, API calls not counted (its finding 5) | yes |
| 7 | 2026-10-21 | #106 | stale-claim, kit-defect | implementation agent | five findings of the live record: the footer `drift audit: none found` against At risk `1 finding`; Proven's `last change` attributed by a shared test file and by a `REQ-nnn` string in a test; the tag `V0.30.0`; the Node 20 pin of `actions/checkout`; no API count | four residual lines (findings 1, 2, 4, 5; finding 2 due 2026-11-30, the others 2026-12-31); finding 3 left to the maintainers (the tag) | no: kit-defect for findings 1, 2 and 4; cost for finding 5; process-order for finding 3; none is a stale claim |
| 8 | 2026-10-21 | #107 | scope-rule | implementation agent, from the rule of `check_adrs` (the list says: check; the check never fired, the rule was read before the ADR was written) | the brief asked for two ADRs in `Amends:`; `check_adrs` accepts one (`^ADR-NNNN$`) | Q-K4-215, ruled as read: `Amends: ADR-0025` and `Related: ADR-0053`; the check is not changed | yes |
| 9 | 2026-10-20 | #102 (and #103, not supported) | process-order | implementation agent (corrected from "maintainers") | on #102 the box said "is merged" while the pull request was open (GET: `state` open, `merged` false; `merged_at` 16:27:05Z). Not supported: that the cleared comment was missing before the merge: on #102 it is dated 16:23:05Z and on #103 17:11:42Z, before the merges at 16:27:05Z and 17:12:36Z; nothing shows #103 was claimed merged before it was | the implementation agent checked the state, reported it and did not start the next pull request | yes, for #102 only |
| 10 | (unknown) | project PR #2 | stale-claim | architect (unverified) | the charter said each report "already publishes" the facts; it did not yet | (unverified) | not assessed |
| 11 | (unknown) | project PR #3 | scope-rule | check (unverified) | the architect's instruction added a fourth file to a three-file intake | (unverified) | not assessed |
| 12 | (unknown) | project PR #3 | kit-defect | implementation agent (unverified) | intake numbered the first project requirement REQ-004 against the REQ-101 reservation | fixed in kit 0.32.0 (#110), which is in this repository: the fix and its tests are on `main` | not assessed (the project's record cannot be read); the defect itself is confirmed by #110 |
| 13 | (unknown) | project PR #3 | scope-rule | implementation agent (unverified) | the architect's plan put the kit upgrade on the intake pull request; it needed its own pull request and ADR | (unverified) | not assessed |
| 14 | (unknown) | project first brief | vendored-file-change | architect (unverified) | TypeScript tests must not be wired by editing kit workflows; `test_patterns` and `project_tests` instead | (unverified) | not assessed |
| 15 | (unknown) | project first brief | security | architect (unverified) | the artifact download redirect: record the host only, never the signed URL | (unverified) | not assessed |
| 16 | (unknown) | project PR #7 | test-proves-less | architect (unverified) | the placeholder test passed the patterns itself and would pass with a wrong `agk.toml` | (unverified) | not assessed |
| 17 | (unknown) | project PR #7 | false-declaration | maintainers (unverified) | `Behaviour: unchanged` in the body made CI proof skip on a behaviour change (seen on the proof job) | (unverified); added as evidence to the existing residual on self-declared `Behaviour: unchanged` | not assessed |
| 18 | (unknown) | project charter and SPEC-0001 | wrong-assumption | maintainers (unverified) | public repositories and no secret: the customers use private repositories; the architect missed it | (unverified) | not assessed |
| 19 | (unknown) | project access model | wrong-assumption | maintainers (unverified) | hosting must be portable (a core with host adapters), stateless and secure by default; the architect had not stated it | (unverified) | not assessed |

## What this shows

Counted from the table and nothing else. 19 rows; 9 assessed (rows 1 to 9, this repository), 10 not assessed (rows 10 to 19, the criterion g project, all `(unverified)`); rows 1 and 2 also have an
unverified "caught by" cell.

- **By kind (architect-assigned; row 7 has two kinds and counts once under each, so 20 entries for 19 rows):** `kit-defect` 4 (rows 2, 5, 7, 12); `scope-rule` 3 (rows 8, 11, 13); `security` 2 (rows 1, 15);
  `process-order` 2 (rows 3, 9); `stale-claim` 2 (rows 7, 10); `wrong-assumption` 2 (rows 18, 19); `fragile-code` 1 (row 4); `cost` 1 (row 6); `vendored-file-change` 1 (row 14); `test-proves-less` 1
  (row 16); `false-declaration` 1 (row 17); `late-discovery` 0.
- **By the implementation agent's kind (the 9 assessed rows):** `kit-defect` 2 (rows 2, 7); `process-order` 2 (rows 3, 9); `security` 1; `fragile-code` 1; `late-discovery` 1 (row 5); `cost` 1 (row 6);
  `scope-rule` 1 (row 8). It agrees with the architect on 7 of the 9 rows and not on 2 (rows 5 and 7).
- **By who caught them, as the table states it:** architect 9 (rows 1, 2, 3, 4, 6, 10, 14, 15, 16; rows 1 and 2 with an unverified cell); implementation agent 6 (rows 5, 7, 8, 9, 12, 13); maintainers 3 (rows
  17, 18, 19); check 1 (row 11). Of the 9 assessed rows: architect 5 (rows 1, 2, 3, 4, 6); implementation agent 4 (rows 5, 7, 8, 9).
- **Misses of the architect that the maintainers caught:** 2 (rows 18 and 19: the architect missed that customers use private repositories, and had not stated that hosting must be portable), both
  `(unverified)`. None is verified in this repository.
- **Corrections of the given list:** row 8 (the check never fired; the implementation agent read its rule), row 9 (the cleared comment was not missing before the merge; the catch was the implementation
  agent's), rows 1 and 2 (the verdict is not posted on the pull request, so "caught by" rests on the PR body).
