# Notes on SPEC-0007 (per-PR metrics)

Date: 2026-10-15 (from `date -u`). Overnight brief 2, item C. The spec was written Draft and set Approved on the maintainers' rulings of 2026-10-15 (final commit of the pull request); nothing is implemented. No protected
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
  and the pull request template do not change, and no agent can inflate a number. The one human input is the verdict
  line of rule 4, relayed by the session. `blocked_weakenings` is `unknown` until `governance.yml` is split (rule 13).
- One place for the weekly numbers: a GitHub issue per ISO week, written by its own workflow on Monday, not by the
  drift audit (rule 11). Reasons: SPEC-0004 rule 14 says a clean drift run writes nothing, which cannot evidence two
  weeks; mixing the two would change a read-only audit; a file committed by a workflow needs a pull request and the
  ruleset allows no bypass (SPEC-0006 rule 5, `ruleset-bypass`). The issue is a record an admin can edit; recomputation
  with `--today` is the check (rule 12 and the last residual).
- A week with nothing closed is still written (rule 14), because the issue is the evidence the run happened. This is
  the opposite of SPEC-0004 rule 14; accepted (Q-K3-31).
- The window is the full ISO week before the run, half-open, so a Monday-morning run sees a complete week (rule 12).
- Completeness is counted by two queries and printed (`INCOMPLETE`, exit 1) (rule 16).
- Two consecutive weeks are evidenced by two issues created by the workflow on schedule, each with `closed in window`
  equal to `recorded` and to the maintainers' hand count (rule 24).

## Where each field comes from, who records it, when

| Field | Source | Recorded by | When |
| --- | --- | --- | --- |
| `hours_open_to_merge`, `size` | `pulls/N` | `metrics.py` | the Monday run after the close |
| `review_rounds`, `rejected`, `merged_head_cleared` | `Verdict:` comments in `issues/N/comments` (posted by the session from the reviewer's paste), `pulls/N` | `metrics.py` | same |
| `blocked_weakenings`, `governance_failures` | check runs and job steps per head commit | `metrics.py` | same |
| `deviations`, `adrs_added`, `protected_classes` | `pulls/N/files`, `config/protected-paths.txt` at the merge base | `metrics.py` | same |
| `tests_before`, `tests_after` | local git objects | `metrics.py` (`fetch-depth: 0`) | same |
| `cost_class` | `review_rounds`, `hours_open_to_merge` | `metrics.py` | same |

## Rulings (maintainers, 2026-10-15)

| Q | Ruling | Where in the spec |
| --- | --- | --- |
| Q-K3-30, Q-K3-32 | Verdicts become derivable: every reviewer verdict starts with `Verdict: cleared <short sha>`, `Verdict: fix list` or `Verdict: rejected`, and the session posts that line verbatim as a PR comment. `merged_head_cleared`, `review_rounds` and `rejected` derive from those comments; the `CHANGES_REQUESTED` and comment-then-commit proxies are dropped; residual: a relayed record, not a signed one | rules 4, 5, 8, residual |
| Q-K3-31 | Accepted: an empty week is still written | rule 14 |
| Q-K3-33 | Weakening set: `check_protected_changes`, `check_requirements`, `check_adrs`, `check_specs`, `reviewers --check-codeowners`, `check_kit_tests`; `governance.yml` split into one step per check, job and required check unchanged; the field counts law checks that blocked a head commit, including honest mistakes | rules 6, 13 |
| Q-K3-34 | Cost class is the maintainers' review cost, derived: S (0 rounds, under 24 h), M (at most 2 rounds, under 72 h), L (else or closed unmerged); `unknown` when rounds are unknown | rule 9 |
| Q-K3-35 | In scope; the implementation's ADR amends REQ-012 with the text below plus the cost class line | rule 19 |
| Q-K3-36 | Installed by default, as the drift audit; init and adopt print that it needs `issues: write` | rule 19 |

No question is open.

The cost class line for the ADR's REQ-012 text: "AC4 cost class is the maintainers' review cost, derived from fix-list rounds and hours
open to merge: S, M or L; `unknown` when the rounds are unknown."

## Decisions-log rows (for the maintainers' log; not edited in this pull request)

| Date | Decision | Reason | Recorded in | By |
| --- | --- | --- | --- | --- |
| 2026-10-15 | SPEC-0007 drafted: all fields derived, none typed by an agent; weekly issue by its own run | a derived number is a measurement; a clean drift run cannot evidence two weeks | `docs/specs/0007-metrics.md` | agent |
| 2026-10-15 | Q-K3-30 to Q-K3-36 ruled (verdict lines make rounds, rejection and cleared derivable; weakening set; derived cost class; default install); SPEC-0007 Approved | maintainers' rulings | `docs/runs/spec-0007-notes.md`, SPEC-0007 | reviewer |
