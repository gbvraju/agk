# Proposed spec amendments 167 (SPEC-0043; REQ-050)

Date: 2026-11-12 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0478 (brief #1118), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0043-a-project-s-plan-is-drafted-from-its-sources-and-tracked-with-calibrated-ranges.md`. The numbers 167 and
0478 are the ones brief #1118 reserved. The rule text is not written into the spec in this pull request, whose `Touches:`
does not name the spec (as amendment 166's builds). The owner decides it with `Approve: <head> SPEC-0043` on this pull
request; no session posts that line.

The sentence (brief #1118): "A plan from a prototype and an OpenSpec file shows nothing is left out: each business rule and
each persona's access to each screen has an acceptance line and a test, and the trace counts both."

The owner's direction, as the brief restates it (2026-11-12): a customer project of many personas, screens and business
rules, whose delivery approach names "Checks prove it: Tests and every persona's access"; "it should not be over
engineerd, it should be real value". Nothing of the customer's material enters this repository; every example below and
every fixture is invented (a loans domain, `example.com`).

## What is on the default branch today

Read in the code by this session on `origin/main` (8c81359):

- `scripts/agk/check_plan.py` rule 11 counts in-scope source lines and screens with a requirement, and, with a
  `Kind: openspec` source, scenarios with an acceptance line and a test (amendment 166 item 5, ADR-0474). Nothing splits
  a requirement's statement into its `SHALL` or `SHALL NOT` sentences, though one OpenSpec requirement often holds
  several business rules.
- `scripts/agk/plan_intake.py` holds `personas` (amendment 164 item 2, ADR-0462) and a requirement's `statement`
  (amendment 166 item 3, ADR-0473), which `render` writes as a `Statement:` line. Nothing records which persona may use
  which screen; `grep -il persona scripts/agk/*.py` finds no persona-to-screen check.

## Items

1. **Rules (rule 4, rule 9).** "Each sentence of a requirement's statement that holds the word `SHALL` (`SHALL NOT`
   included) is one business rule, keyed `<requirement key>.r<n>` in order. A sentence ends at `.`, `!` or `?` followed
   by white space. An acceptance line names the rules it proves with `(rules r1, r2)` (or `(rule r1)`). `validate`
   refuses a criterion that names a rule its requirement's statement does not hold. `check_plan.py --trace`, when a
   requirement block of `docs/plan/requirements-proposed.md` or `docs/requirements.md` has a `Statement:` line, prints
   `info plan: <a> of <b> rules have an acceptance line and <c> a test` and one line
   `info plan: rule <key>.r<n>: no acceptance line` per rule with none, and, with `--facts`, one
   `info plan: rule <key>.r<n>: no test` per rule whose acceptance lines have no test; without `--facts` the count reads
   `... and a test: not read`." A test is a `REQ-nnn ACn` marker for the criterion n that names the rule, as amendment
   166 item 5 reads it: the `ACn` segment of an `Acceptance:` line, or the n-th list line after `Criteria:`.
2. **Access (rule 4, rule 5, rule 7, rule 9).** "The plan draft may hold `access`, a list of cells
   `{persona, screen, allowed, sources}`: `persona` a key of `personas`, `screen` a screen of `docs/design/inventory.md`,
   `allowed` `yes` or `no`, and `sources` the locations of the scenarios and screens that name the persona there
   (amendment 164's personas, amendment 166's scenario-to-screen match). A cell is keyed `<persona>/<screen>` and appears
   once. A cell with no source is an open question, never a guess: `validate` refuses it. An acceptance line names a cell
   with `(access <persona>/<screen>)`; each `no` cell needs one, its denial line, and `validate` refuses a mark that
   names no cell. `render` writes `docs/plan/access.md`, a table `| Persona | Screen | Allowed | Sources |`, when `access`
   is not empty. `check_plan.py --trace`, when that file exists, prints `info plan: <a> of <b> access cells have a test`
   (with `--facts`; without it `info plan: <b> access cells; with a test: not read`), one
   `info plan: access <persona>/<screen>: no acceptance line` per cell no line names and, with `--facts`, one
   `info plan: access <persona>/<screen>: no test` per named cell without a test."
3. **Information, not a failure.** The lines of items 1 and 2 never fail `check_plan.py`, as rule 11's counts do not,
   until the person confirms the plan. No test generator: the briefs carry the acceptance lines and the builders write
   the tests.
4. **Tests.** `tests/kit/test_plan_intake.py` and `tests/kit/test_check_plan_trace.py`, invented files in `tmp_path`, no
   network: three `SHALL` sentences give three rules; an acceptance line naming two of them leaves one listed; two
   personas by two screens with one `no` cell and its denial line pass; a cell without a source, a `no` cell without a
   denial line, a repeated cell, an unknown persona or screen, an `allowed` other than `yes` or `no`, and a mark naming no
   rule or no cell are refused; `render` writes the table and `check_plan.py` reads it back; the lines print only with
   `--trace` and never fail.
5. **Not in this amendment.** No other rule of SPEC-0043 changes; amendments 163, 164 and 166 stand. No workflow change.
   The `plan-intake` skill's text, which fills `access` from the sources, is not changed here.

## Contexts

- kit: installed `plan_intake.py` and `check_plan.py`, so every project's plan proves rules and access.
- github: no workflow change.
- local: the same commands on a laptop.
- personal: the same files, in the private state; nothing is posted.
- stacks: not applicable; no test or build step of a stack changes.

## Residual

- 2026-11-12: a sentence is split at `.`, `!` or `?` and white space, so an abbreviation such as `e.g.` splits one rule
  in two; the person reads the listed rules (due 2026-12-31).
- 2026-11-12: the `plan-intake` skill does not yet say how to fill `access` from scenarios and screens; a brief for
  `skills/plan-intake/SKILL.md` follows (due 2026-12-31).
- 2026-11-12: whether the lines fail after `Approve: plan` is the maintainers' to rule (due 2026-12-31).

## Questions

Each reading is the most conservative one, and applies until a person rules.

- Q-1118-1: the brief names no screen list for a cell. Reading: the screens of `docs/design/inventory.md`, as
  `components` read them (amendment 164 item 3), so a cell names a screen the person signed off, not a state heading.
- Q-1118-2: the brief names no mark for an acceptance line that proves a cell. Reading: `(access <persona>/<screen>)`,
  in the form of `(rules r1, r2)`.
- Q-1118-3: the brief's `<c>` has no `--facts` rule. Reading: as amendment 166 item 5, a test is read with `--facts`
  only, else `not read`.
