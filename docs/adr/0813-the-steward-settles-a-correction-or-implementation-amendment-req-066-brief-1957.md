# ADR-0813: The steward settles a correction or implementation amendment, on the owner's setting

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers
- Related: SPEC-0059, SPEC-0039, ADR-0430, ADR-0714, ADR-0723, ADR-0595, ADR-0690, ADR-0763, amendment 251, amendment 252, brief #1957, plan #661
- Requirements: REQ-066

Protected classes: `scripts/agk/`, `.claude/hooks/`, `tests/kit/`, `docs/runs/`, `agk.toml`

## Context

Principle 6 says approved specs are owned by a reviewer group and agents propose patches. Every amendment waits for
`Maintainer answer: amendment <n> approved` (`route.APPROVAL_ASK`, the merger's `agk:approve` hold). Of the 61 items of
amendments 212 to 247, 31 only made the kit do what its Approved spec already said (brief #1957's measurement).

## Decision

1. **Two classes, written on the amendment.** Each item of an amendment file from 251 on carries one line
   `Class: correction`, `Class: implementation` or `Class: behaviour`. An item with no line, one that
   `check_amendments.BEHAVIOUR` marks (a new setting, gate, label, step, message or authority, or an intake) and a
   `correction` naming no rule of an Approved spec are `behaviour`; `check_numbers.py` fails a mismatch in an amendment
   file a pull request adds, naming the file, the item and this ADR, never the text.
2. **The steward settles only the first two.** `check_amendments.py settle` prints `Answer: amendment <n> settled
   (evidence: <e>; class: <class>; rule: <spec and rule>)` with `Who: AGK steward` only when the setting is on, the kit
   is not paused, the fresh reviewer (ADR-0430's form) agreed, every item is `correction` or `implementation`, the
   amendment names no principle, `constitution/` or `spec_approvers`, and it is not an intake's; else `owner:` and
   exit 1. It posts nothing; the steward posts the line with `steward_evidence.py answer` (`Q-ES-5`).
3. **The readers.** `route.py` (the `settle` fact) and `merge_cleared.py` (`settled_asks`) read the line, by an account
   in `spec_approvers` and with the marker, as the approval of its amendment only when the setting is on in the checkout
   they read; a line before the newest ask settles nothing. `.claude/hooks/steward_guard.py` denies a settled first line
   unless it is in the form, with the marker, and the setting is on. `Maintainer answer: amendment <n> approved` works
   as before.
4. **The owner keeps the last word.** An owner `Maintainer answer:` or `Correction:` naming a settled amendment is an
   override (`check_amendments.overrides`); two of one class in seven days stop `settle` for that class.
5. **The text.** Amendment 251 (SPEC-0059 rules 4, 11, 12 and 13) and amendment 252 (SPEC-0039 rule 5) propose the
   spec text. Principle 6's proposed clause, applied by the maintainers in its own commit and never by a build
   (`Q-ES-1`), is: append to principle 6 "; the steward may settle an amendment of class correction or
   implementation that a fresh reviewer agrees with, where the owner turns it on". Until principle 6 holds it,
   `settle_amendments = true` is refused naming principle 6.
6. **The setting.** `[steward] settle_amendments`, `true` or `false`, default `false`; another value is refused naming
   `steward.settle_amendments`; `misplaced_settings` reports it in another table through `TABLE_KEYS`. It is read as
   off while `config/reviewers.yaml` lists no `spec_approvers` login, in solo and team mode alike (`Q-ES-2`).

## Consequences

With no table, or the setting off, nothing changes. With it on and principle 6 applied, a correction or implementation
amendment that a fresh reviewer agrees with clears its approval ask without the owner's line. No workflow, label, ruleset
or required check changes; the class check runs inside the existing `numbers` governance step.

## Residual

- 2026-11-25: the daily list's settled entries and `session.py`'s owner wait reading the settled line are later work.
- 2026-11-25: the maintainers apply principle 6's clause (`Q-ES-1`).
