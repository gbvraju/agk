# Architect catches 2 (design judgement as evidence, K5 candidate 19)

Date: 2026-10-23 (from `date -u`). The second list, in the form of `docs/runs/architect-catches-1.md`: the catches with their kind and who caught them, the architect's own misses included, so that the kit's
review checklist can grow from evidence and a catch rate can be measured. A question of `config/review-checklist.md` is added only from a row of a catch log (SPEC-0023 rule 5); this list changes no question.

## How the rows were checked

Each row of the list the maintainers gave was checked against the pull request or comment in this repository (GET only: the comments of #118 to #130 and the titles and merge times of the pull requests). A
detail that did not match is corrected in the row and said so. A row that the record of this repository cannot support is marked `(unverified)`: the rows about the criterion g project, because that project is
not named here (ADR-0025 decision 6) and its pull requests are not in this repository ("project PR #n" is a pull request of that project), and the parts of a row that happened in a session and were not written
on a pull request. Nothing is added that the record does not support.

Kinds (fixed list): `wrong-assumption`, `false-declaration`, `test-proves-less`, `stale-claim`, `fragile-code`, `security`, `vendored-file-change`, `scope-rule`, `process-order`, `kit-defect`, `cost`,
`late-discovery` (a fact found after intake that should have been asked at intake). The column **Kind** is the maintainers' own reading `(architect-assigned)`. The column **Agrees** is the kind that the
implementation agent assigns from the record: `yes`, or `no` with its kind; a kind that the record does not support is not adopted, and a row whose record cannot be read is `not assessed`.

## The catches

| # | Date | Where | Kind (architect-assigned) | Caught by | What | Outcome | Agrees |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | (unknown) | project PR #44 | scope-rule | maintainers (unverified) | the architect answered the intake's questions inside the intake pull request, so `check --final` made the spec say "before it was written" | (unverified); not readable from this repository | not assessed |
| 2 | (unknown) | project PR #45 | process-order | maintainers (unverified) | the architect's box said the maintainers merge without naming the cleared step; the builder session filled in and posted the cleared SHA itself | (unverified); not readable from this repository | not assessed |
| 3 | (unknown) | project PR #45 | process-order | architect (unverified) | the architect over-corrected to "a builder never posts a verdict", contradicting the standing practice; corrected to "a session posts a verdict only as the architect wrote it, with the SHA the architect named" | (unverified); not readable from this repository | not assessed |
| 4 | (unknown) | project PR #45 | test-proves-less | architect (unverified) | the approved mockup showed one tile per number; the architect's intake answer said only "tiles", so the build tiled each line | (unverified); not readable from this repository | not assessed |
| 5 | 2026-10-23 | #130 (the cleared comment 6373593139, for the later ruling) | process-order | implementation agent (unverified: the relay and the refusal are in the session, not on the pull request) | an intake item (4) was relayed without items 1 to 3; the agent refused to act on it. What the record shows on #130: the comment of 2026-10-23T19:59:55Z rules the counts intake's items 3, 5 and 6 "in place of the earlier item 3" and orders it after L3c; the relay of item 4 itself is not on the pull request | no action was taken on item 4 (the agent's own account; not in the record); the counts intake is ordered after L3c in the comment | not assessed |
| 6 | (unknown) | project PR #44 | kit-defect | implementation agent (unverified) | the intake ran from plugin 0.32.0 against kit 0.40.0; `check --final` arrived in 0.35.0. Confirmed here: kit 0.32.0 is #110 (merged 2026-10-21T04:14:44Z), `--final` is in kit 0.35.0 (#117, "an intake pull request may carry its own approval", merged 2026-10-21T17:46:18Z) and kit 0.40.0 is #125 (merged 2026-10-22T16:40:23Z); a plugin at 0.32.0 therefore has no `--final`. Not readable: the project's plugin version and its run | (unverified for the project); the kit side needs no change | not assessed (the project's record cannot be read); the kit side is confirmed |
| 7 | 2026-10-21 to 2026-10-23 | #118 to #129 | kit-defect | implementation agent | corrected from "11 of 12 single-item fix lists used placeholder paths": the record shows 8 of the 12 pull requests (#119, #121, #122, #123, #125, #126, #127, #128) with a fix list whose `Final:` line names a placeholder path (`docs/adr/<ADR-0071's file name>` and the like), which `covered_fix_list` cannot parse; of the 4 fix lists that were a single item, the covered form (#122, #126, #128, and the second of #129), 3 used a placeholder and 1 a real path; #118, #120 and #124 had no fix list. So no fix list of the 12 was a covered one until `8ecafb4` on #129 | the architect writes real paths from `8ecafb4` (#129) and in `39e2237` (#130, the only fix list there with a `Final:` line); the code is unchanged: the parser is right to refuse a placeholder | no: process-order (the writing of the verdicts; the kit's check is correct) |

## What this shows

Counted from the table and nothing else. 7 rows; 1 verified in this repository (row 7, corrected), 2 verified in part (row 5, the comment but not the relay; row 6, the kit side but not the project side), 4
not assessed (rows 1 to 4, project PR #44 and #45, all `(unverified)`).

- **By kind (architect-assigned, 7 entries for 7 rows):** `process-order` 3 (rows 2, 3, 5); `kit-defect` 2 (rows 6, 7); `scope-rule` 1 (row 1); `test-proves-less` 1 (row 4); the other eight kinds 0.
- **By the implementation agent's kind (the 1 row assessed in full):** `process-order` 1 (row 7). It disagrees with the maintainers' kind on that row (`kit-defect`); rows 5 and 6 are not assessed.
- **By who caught them, as the table states it:** implementation agent 3 (rows 5, 6, 7); maintainers 2 (rows 1, 2); architect 2 (rows 3, 4). Of these, only row 7 is verified in full; rows 1 to 4 are `(unverified)`.
- **Misses of the architect stated in the table: 5 (rows 1, 2, 3, 4, 7).** The maintainers caught 2 (rows 1, 2), the architect itself 2 (rows 3, 4), the implementation agent 1 (row 7). Only row 7 is verified
  in this repository; the other four rest on the maintainers' account.
- **Corrections of the given list:** row 7 ("11 of 12 single-item fix lists" is not what the record shows: 8 of 12 pull requests carry a placeholder path, 3 of the 4 single-item fix lists), row 5 (the relay
  of item 4 and the refusal are not on the pull request), row 6 (the project side is unverified; the kit side is confirmed by #110, #117 and #125).
