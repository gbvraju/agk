# Shadow review summary (SPEC-0003 rule 23), K2

Date: 2026-10-15 (from `date -u`). Summary of `docs/runs/shadow-review-1.md`, `shadow-review-2.md` and
`shadow-review-3.md`. The reviewer agent ran on pull requests where the maintainers' findings are on record.

## Runs

| Review | Targets | Input | Result |
| --- | --- | --- | --- |
| 1 | #12 and #6 (first commits), #22 (final), #23 (open) | final PR bodies; human verdicts inferred | inconclusive: bodies did not match the diffs and the human verdicts were not in the repository |
| 2 | #12 (bd381ef), #6 (e001628), #22 (071ded6) | minimal bodies (`Advances:`, dated `Build-state row:`) | 0 of 3 human findings caught; all three `cleared` |
| 3 | the same three | the same bodies, reviewer fixed by #26 (CLAUDE.md and changed files in full, cross-file check; kit 0.6.1) | 0 of 3 caught; all three `cleared`; two of three contexts truncated |

## Human findings on record (confirmed by the maintainers, Q-SR2-1)

| PR | Commit | Human verdict | Finding |
| --- | --- | --- | --- |
| #12 | bd381ef | fix list | CI no longer runs project tests |
| #6 | e001628 | fix list | CLAUDE.md rule 8 wrong for installed targets |
| #22 | 071ded6 (first commit) | fix list | an installed check's tests are not installed (principle 4) |

## Result

- Across reviews 2 and 3 (the two with matching inputs): 0 of 3 human findings caught in each, 6 runs, 6 reports
  `cleared`, 0 agent findings, 0 invalid reports.
- Giving the agent more context between review 2 and review 3 did not change a verdict.
- Each of the three findings is outside the checks that SPEC-0003 rule 11 lists (Q-SR3-1).

## Rulings (maintainers, 2026-10-15)

- The reviewer is advisory. Human review stays required for every pull request; a `cleared` report is not an approval.
- Improvement of the reviewer moves to K3.
- A recurring finding becomes a deterministic check, not a reviewer prompt. The first one is the installed-tests
  check (`check_kit_tests.py`, ADR-0014), which fails on the shape of #22's first commit.
- Human verdicts are recorded in the repository (the shadow-review records carry them), not only in pull request
  conversations.
- Q-SR2-1 is confirmed: the human verdicts above are the verdicts of record. Q-SR3-1 (is the agent expected to catch
  these findings at all) is read as answered by the rulings above: advisory now, deterministic checks for recurring
  findings, improvement at K3. This reading is mine; the maintainers can correct it.

## Open

- Reviewer effectiveness is measured again at K3 start (register line in `docs/runs/residuals.md`).
