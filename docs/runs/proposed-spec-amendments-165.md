# Proposed spec amendments 165 (SPEC-0045; REQ-052)

Date: 2026-11-12 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0470 (brief #1099), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0045-each-kind-of-work-runs-on-the-model-it-needs.md` (rule 4). The number 165 is the one brief #1099
reserved. The brief asks for the amendment and its build in one pull request, so this amendment is applied to the spec
text in the same pull request: one sentence in rule 4. The owner decides it with `Approve: <head> SPEC-0045` on this
pull request; no session posts it.

The sentence (brief #1099): "Each brief runs on the model tier its kind needs: a brief's own new ADR no longer makes every
brief `design`, `session.py route` names the scheduled task for the brief's tier, and the launcher fires that task, so
small and mechanical work stops running on the strongest model."

## What is on the default branch today

Read in the code by this session (main ebcaa30):

- `session.kind_of` gives `design` to any `Touches:` or `Adds:` glob that may match `docs/adr/` (rule 4's list,
  `DESIGN_DIRS`). Nearly every brief names its own reserved ADR there, so on 2026-11-12 `session.py kind` printed
  `kind: design` for every open brief it was run on (the brief's `Measured:` line).
- `changelog.d/` is in no list of rule 4 and in no protected class, so a changelog fragment already lowers nothing.
- Amendment 145's routes (rule 3) are in the spec text but not in the code; build (f) builds them in this pull request
  (brief #1099 answer 2).

## Items

1. **SPEC-0045 rule 4, the brief's own new ADR.** A `Touches:` or `Adds:` glob whose literal start is `docs/adr/<n>-`,
   where `ADR-<n>` is a number of the brief's one `Reserved:` line and no ADR of that number is in the checkout's
   `docs/adr/`, is the brief's own new ADR and does not by itself give `design`; nor does a `changelog.d/` glob. Every
   other glob of rule 4's list still gives `design`: an existing ADR, a glob that may match any ADR (`docs/adr/*`), a
   spec, the requirements and the other paths. A missing or repeated `Reserved:` line names no own ADR.
2. **Nothing is lowered (rule 1).** The kind still decides only the tier, the effort and the reading list; a review
   stays on `strongest` (rule 6), a builder below `strongest` still escalates by rule 5, and the ADR the brief adds is
   reviewed as before.

## Text applied to SPEC-0045

In rule 4, after "gives `design` (`Q-S0045-4`)": "; a glob whose literal start is `docs/adr/<n>-` for an `ADR-<n>` of the
brief's one `Reserved:` line, with no ADR of that number in `docs/adr/`, is the brief's own new ADR and does not by itself
give `design`, nor does a `changelog.d/` glob (amendment 165)".

## Tests

`tests/kit/test_models_table.py` (brief #1099 tests (a) and (b)): a `Size: S` brief whose only protected or design globs
are its own reserved ADR and a changelog fragment prints `small`; one that names another ADR, `docs/adr/*`, a spec, an
ADR that already exists, or has no or two `Reserved:` lines prints `design`. Invented data only, no network.

## Contexts

- kit: the installed `session.py kind` gives a project's briefs the same reading
- github: no workflow change
- local: `kind` and `route` print the same lines on a laptop
- personal: not applicable: no builder sessions are started
- stacks: not applicable: no test or build step of a stack changes

## Residual

- 2026-11-12: a brief may reserve an ADR number and then use its ADR to decide more than its brief says; the conductor
  may raise a brief's kind (rule 4) and the review reads the ADR as before (due 2027-01-31).

## Questions

- **Q-1099-1:** see the pull request: answer 3's `[models.routes]` in this repository's `agk.toml` is refused by rule 3
  as written; the reading is to leave `agk.toml` without the table until a person rules.
