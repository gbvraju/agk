# ADR-0408: the Approve design line and the frozen signed-off version (REQ-044, brief 459)

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: ADR-0204, ADR-0334, SPEC-0037
- Requirements: REQ-044

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`

## Context

SPEC-0037 (Approved; ADR-0204) makes a design sign-off a row of `docs/design/signoffs.md` that counts only with the
person's `Approve: inventory` or `Approve: design` line on the head it names (rules 3 and 9), freezes a signed-off
version (rule 9) and reads a theme's prototype evidence as approved only from a matching row (rule 12). Brief #459 is
build (f) of rule 14. ADR-0204 names only `docs/requirements.md`, so `Covered-by:` cannot cover the build. As for #458
(ADR-0334), the kit test of brief #878 needs each new test file in the `[[testing.map]]` entries of the scripts it runs
or imports, a change of `agk.toml` (the answer to Q-459-2 on #949, 2026-11-10).

## Decision

1. **The lines (answer 1).** `reviewers.py` gains `APPROVE_INVENTORY` (`Approve: inventory <40-hex>`), `APPROVE_DESIGN`
   (`Approve: design v<n> <40-hex>`) and `design_approvals(items, approvers, agent_apps)`, the set of (`inventory`,
   `-`, head) and (`design`, version, head) of first lines by accounts of `spec_approvers`, never through an app of
   `agent_apps`. In solo mode `confirmed_comments` adds such a line inside a `Confirmed:` comment as its own comment
   when it names the confirmed head, as `acceptance_heads` reads `Approve: acceptance`.
2. **The rows (answer 2, the fix list of 5aa97e0).** `check_final_clearance.py` reads the record with the new
   `design_signoff.parse_rows(text)` (`rows(root)` calls it) at the head and at the merge base with the default branch
   (the base rule 3a resolves; none resolving fails closed when the head has rows); a row absent at the merge base is
   added by the pull request, in whichever commit. An added row without its line fails
   `rule 9: a design sign-off row has no Approve line by an account in spec_approvers`; then each commit after the
   merge base that adds a row (absent at every parent) and also changes another file than the record (against its
   first parent) fails `rule 9: the sign-off commit changes more than docs/design/signoffs.md`. Without `--comments`
   it stays skipped.
3. **The frozen version (answer 3).** `design_signoff.frozen_problems(root)` fails each `design` row whose folder no
   longer has the row's digest, or is gone: `rule 9: docs/design/prototype/<version>: a signed-off version changed`,
   never a digest; `screenshots/` stays outside. `check_design.py` `cmd_check` calls it, and also runs when the record
   is its only design file.
4. **The evidence reading (answer 4).** `design_signoff.signed_off(root, version)` is rule 12: a theme whose evidence
   names a prototype version reads approved only with a `design` row of that version and its current digest; otherwise
   `design: the theme is not approved yet`, information.
5. **Nothing written (answer 5).** The three scripts only read.
6. **The test map.** `tests/kit/test_design_signoff.py` joins the entries of `check_design.py` and `design_signoff.py`;
   `tests/kit_dev/test_final_clearance_design.py` joins those of `check_final_clearance.py`, `reviewers.py` and
   `design_signoff.py`. Nothing else of `agk.toml` changes. This amends ADR-0204 decision 3 for this table only.

## Consequences

A sign-off row counts only with the person's own line; an agent cannot add one through its app, and a version once
signed off cannot change in place without `check_design.py` failing, naming the version. A change after sign-off is a
new version. The changelog fragment is `changelog.d/design-signoff-approve.md`.

## Residual

- Answer 6 (the session rule on where the lines go) is not built: `config/session-rules.md` is at its word budget, and
  which words make room is the owner's (Q-459-1).
- A row's digest is not compared with the version at the head it names; only the folder as it is now is compared.
