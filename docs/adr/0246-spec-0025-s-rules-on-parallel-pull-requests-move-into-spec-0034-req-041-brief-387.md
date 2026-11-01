# ADR-0246: SPEC-0025's rules on parallel pull requests move into SPEC-0034, and SPEC-0025 says where each went (REQ-041, brief 387)

- Status: Proposed
- Date: 2026-11-01
- Deciders: maintainers
- Related: ADR-0096, ADR-0212
- Requirements: REQ-041

Protected classes: `tests/kit/`

## Context

SPEC-0025 (a team runs independent pull requests in parallel without colliding) and SPEC-0034 (parallel builder sessions get
briefs by capacity, overlap, reserved numbers and claims) govern parallel work from two sides, so any change to how parallel
work is judged had to read both. The core audit (brief #328) found verdicts citing SPEC-0025 rules 3, 5 and 10 and SPEC-0034
rules 4, 5, 7b, 7c and 11. The person accepted row 11 of the decision table of plan #278 on 2026-11-01 (the field note on #278,
closed as decided): SPEC-0025 into SPEC-0034, never renumbering, a merged number staying as a pointer line. Brief #387 gives the
answers. The tests were written first (15 failed, 2 passed before the change).

## Decision

1. **One spec, one amendment (answer 1).** `docs/runs/proposed-spec-amendments-108.md` moves SPEC-0025 rules 1 to 11 into a new
   section of SPEC-0034's `## Rules`, "Independent pull requests (from SPEC-0025)", as rules 17 to 27 (rule n becomes n + 16;
   15 and 16 stay for the new rules amendments 88 and 89 propose), their text unchanged. Rule 8, now rule 24, keeps its first
   two sentences and carries the release model in the text SPEC-0028 gave it by amendment 50, item 2.
2. **Pointer lines (answer 2).** SPEC-0025 keeps its number, title, status, opening paragraphs and its `## Tests`, `## Proof`,
   `## Residual` and `## Open questions` sections. Its `## Rules` holds one sentence saying where the rules went and one line
   per old rule, `N. Now SPEC-0034 rule M.`.
3. **No behaviour changes (answer 3).** No script, workflow, setting or role file is touched. Every script, test, ADR,
   amendment or verdict that cites a SPEC-0025 rule still resolves through its pointer line; `core_audit.py` counts the moved
   rules as SPEC-0034 rules and the pointer lines as SPEC-0025's. No rule is weakened.
4. **Approval (answer 4).** Both specs stay `Approved` in this pull request; it approves nothing. A person approves SPEC-0034
   after the change with `Approve: SPEC-0034` on the pull request; no session posts it.
5. **Tests first (answer 5).** `tests/kit/test_core_parallel_specs.py` (marker REQ-041): each rule of SPEC-0025 is in SPEC-0034
   after the change, pinned by digest and checked against SPEC-0025 before the fold where the history has it; each pointer
   line names a rule that exists; `check_specs.py` passes the change with the amendment and fails it without.

## Consequences

A reader of parallel work reads one spec. A verdict may cite either `SPEC-0025 rule 5` or `SPEC-0034 rule 21`; both name the
same text. The earlier amendments of SPEC-0025 (50 item 3, 94 and 97) stay as written and now reach SPEC-0034 through the
pointer lines.

## Residual

- 2026-11-01: Q-387-1: the amendment number 108 is the next free one, not one the conductor named; ADR-0246 is the conductor's
  reservation, while `session.py claim` reserved ADR-0243, which this pull request does not use (due 2026-12-31).
- 2026-11-01: Q-387-2: amendments 50 item 3, 94 and 97 are not applied into the moved text, as the brief says "text unchanged";
  applying them is a later amendment if the maintainers want it (due 2026-12-31).
- 2026-11-01: Q-387-3: SPEC-0034's `- Requirements:` line still names REQ-041 alone, and REQ-032 stays named by SPEC-0025 (due
  2026-12-31).
