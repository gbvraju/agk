# Notes on SPEC-0007 (per-PR metrics)

Date: 2026-10-15 (from `date -u`). Overnight brief 2, item C. The spec is Draft; nothing is implemented. No protected
path is changed by this pull request.

## REQ-012 as written, and what the draft adds

REQ-012, "Metrics per merged PR (K3)", status planned, has one criterion: "AC1 rejections, blocked weakenings,
deviations, cost class". The draft keeps those four as **core fields** (rules 4, 6, 7, 9). The brief's other examples
are **supporting fields** (hours open to merge, review rounds, protected paths touched, ADRs added, tests before and
after, merged head cleared). REQ-012's text is protected (`docs/requirements.md`), so widening it is an ADR; proposed
acceptance text for that ADR:

> AC1 each closed pull request has a derived record of rejections, blocked weakenings, deviations and cost class;
> AC2 the record also carries hours open to merge, review rounds, protected classes touched, ADRs added, tests before and
> after, and whether the merged head was cleared; AC3 a weekly issue lists every pull request closed in the week.

## Decisions taken in the draft

- Everything is derived after the close; nothing is typed into the pull request body (rule 1). So `check_pr_body.py`
  and the pull request template do not change, and no agent can inflate a number. The cost: two fields are `unknown`
  until a definition exists (rules 6, 9, 13).
- One place for the weekly numbers: a GitHub issue per ISO week, written by its own workflow on Monday, not by the
  drift audit (rule 11). Reasons: SPEC-0004 rule 14 says a clean drift run writes nothing, which cannot evidence two
  weeks; mixing the two would change a read-only audit; a file committed by a workflow needs a pull request and the
  ruleset allows no bypass (SPEC-0006 rule 5, `ruleset-bypass`). The issue is a record an admin can edit; recomputation
  with `--today` is the check (rule 12 and the last residual).
- A week with nothing closed is still written (rule 14), because the issue is the evidence the run happened. This is
  the opposite of SPEC-0004 rule 14; Q-K3-31 asks if that is accepted.
- The window is the full ISO week before the run, half-open, so a Monday-morning run sees a complete week (rule 12).
- Completeness is counted by two queries and printed (`INCOMPLETE`, exit 1) (rule 16).
- Two consecutive weeks are evidenced by two issues created by the workflow on schedule, each with `closed in window`
  equal to `recorded` and to the maintainers' hand count (rule 24).

## Where each field comes from, who records it, when

| Field | Source | Recorded by | When |
| --- | --- | --- | --- |
| `hours_open_to_merge`, `size` | `pulls/N` | `metrics.py` | the Monday run after the close |
| `rejected`, `rejection_reviews` | `pulls/N`, `pulls/N/reviews` | `metrics.py` | same |
| `review_rounds` | `issues/N/comments`, `pulls/N/reviews`, `pulls/N/commits` | `metrics.py` | same |
| `blocked_weakenings`, `governance_failures` | check runs and job steps per head commit | `metrics.py` | same |
| `deviations`, `adrs_added`, `protected_classes` | `pulls/N/files`, `config/protected-paths.txt` at the merge base | `metrics.py` | same |
| `tests_before`, `tests_after` | local git objects | `metrics.py` (`fetch-depth: 0`) | same |
| `merged_head_cleared` | `pulls/N/reviews` `commit_id` | `metrics.py` | same |
| `cost_class` | none | not defined | Q-K3-34 |

## Open

- **Q-K3-30.** What does "the merged head was the cleared commit" mean on this repository? Maintainers clear by a
  comment and a comment names no commit; the repository requires 0 approvals, so there is no approving review either.
  Draft: `yes` only for an `APPROVED` review on the head, else `no` or `unknown`. A convention such as "cleared
  <short sha>" in a maintainer comment would make it derivable; the draft does not invent one.
- **Q-K3-31.** A week with no closed pull request is written (rule 14) while a clean drift run writes nothing
  (SPEC-0004 rule 14). Accept the difference?
- **Q-K3-32.** Rejections and review rounds: the maintainers' fix lists are comments, not `CHANGES_REQUESTED` reviews,
  and one account may write both the work and the comments, so `rejected` misses comment rejections and
  `review_rounds` may over-count. Options: a marker line in a fix-list comment (for example `Fix list:`), or accept the
  proxy. Draft: the proxy, with the limit stated.
- **Q-K3-33.** What counts as a "blocked weakening", and may `governance.yml` be split into one step per check so a
  failing check can be named? Draft set: `check_protected_changes`, `check_adrs`, `check_specs`, `check_neutrality`.
  Splitting the workflow is a protected change in the implementation PR.
- **Q-K3-34.** Define "cost class": the value set, what it measures (tokens, wall time, review effort), and who records
  it. Draft: the field is absent.
- **Q-K3-35.** Are the supporting fields in scope for REQ-012, given its one acceptance criterion? An ADR must widen
  the text (proposal above).
- **Q-K3-36.** Should `agk init` and `agk adopt` install the metrics workflow by default (draft: yes, as for the drift
  audit, SPEC-0004 rule 16)? A target without admin rights to create labels or issues would see it fail.

## Decisions-log rows (for the maintainers' log; not edited in this pull request)

| Date | Decision | Reason | Recorded in | By |
| --- | --- | --- | --- | --- |
| 2026-10-15 | SPEC-0007 drafted: all fields derived, none typed by an agent; weekly issue by its own run | a derived number is a measurement; a clean drift run cannot evidence two weeks | `docs/specs/0007-metrics.md` | agent |
| 2026-10-15 | Q-K3-30 to Q-K3-36 opened | cleared commit, empty weeks, review rounds, weakening set, cost class, scope, default install | `docs/runs/spec-0007-notes.md` | agent |
