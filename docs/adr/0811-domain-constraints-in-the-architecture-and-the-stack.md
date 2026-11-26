# ADR-0811: Domain constraints in the architecture record and the stack's domain fit

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers
- Related: SPEC-0074, SPEC-0072, SPEC-0073, ADR-0804, ADR-0805, ADR-0808, ADR-0810, ADR-0794, ADR-0671, ADR-0667, brief #1955, plan #661
- Requirements: REQ-081

Protected classes: `scripts/agk/`, `skills/`, `kit/`, `tests/kit/`, `docs/specs/`, `agk.toml`

## Context

SPEC-0074 (Approved) rule 8, "Domain-aware architecture", and rule 16 build (e); amendment 241 to SPEC-0072 rule 5,
approved by the owner on #1922 (comment 7172954642, `Maintainer answer: amendment 241 approved`). Before this change,
on the default branch at e3646ac, a composed pack's `[[constraints]]` (ADR-0804, ADR-0805) reached no check of the
architecture record, the record's `## Threats` (ADR-0808) named no data class of `docs/domain/data.md` (ADR-0810), and
`engines.py stack-check` passed a stack ADR whose options said nothing of a hard constraint they cannot meet. A hard
limit known in planning was found only in review.

## Decision

1. `check_domains.py` gains `CITATION`, the one pattern of `<pack>.<constraint>`, and `cited(root)`: the composed
   constraints of `items` keyed by that citation; `{}` with no `[domain] packs`, None when the table is refused. No
   other module holds the pattern; the two checks below import it.
2. A scenario line of `## Quality scenarios` may end ` [<citation>]` (`front_door.SCENARIO` gains that optional tail;
   every line valid before stays valid). A new step `domain-scenarios` (`scripts/agk/gates/domain_scenarios.py`,
   installed, the runner's interface) applies where the record holds its quality sections and `[domain] packs` is set
   or refused: each composed constraint without a row, and each row citing no composed constraint, fails as
   `SPEC-0074 rule 8` naming the section and the id (a citation out of its form is never echoed); a refused table is
   `not run domain-scenarios: [domain] is refused (setting: domain)`. The scenario's attribute stays one of the eight
   ISO/IEC 25010 characteristics of ADR-0808; the citation carries the pack's attribute.
3. A new step `domain-threats` (`scripts/agk/gates/domain_threats.py`, installed) applies where the record holds its
   quality sections and `docs/domain/data.md` exists or packs are set: each `## Threats` flow that names a classified
   data item (a whole-word match, case ignored) carries `(class: <class>)` for it; a missing class, or a class outside
   the five of SPEC-0074 rule 7, fails naming the flow's number and the item, never the flow's text. With no
   `data.md` it prints `not run domain-threats: no data classification`. Both steps follow `architecture-quality` in
   `run_gates.ARCHITECTURE_STEPS`; with no packs and no `data.md` neither applies, so output is as today.
4. `engines.py stack-check`, with packs set, requires after each `- Option <X> — ...` bullet one indented line
   `Domain fit: meets` or `Domain fit: cannot meet: <citation>, ...`, each id a composed `hard` constraint; a missing
   or misplaced line (before a bullet, or written as a `- ` bullet), an unknown id or a soft one fails naming the
   option and the id. An option that cannot meet a hard constraint is kept and may be chosen. An Accepted stack ADR
   with no `Domain fit:` line was written before packs and is held (an upgrade fails nothing); a refused table prints
   `not run engines-stack domain fit: [domain] is refused (setting: domain)`. `pins.OPTION`, `pins.chosen_parts` and
   `engines.OPTION` are unchanged and read every option with the lines present.
5. `engines.py stack-write`, with packs set, writes `Domain fit: TODO(architect)` after each option, so the skeleton
   is not drafted until each is filled. `skills/stack/SKILL.md` step 2 names the line and offers a pack's
   `[[references]]` as options with their source, never imposed. `kit/templates/architecture.md` names the citation
   tail and the class mark in its `TODO(architect)` lines.
6. Amendment 241 items 1 and 2 are applied word for word to SPEC-0072 rule 5, after amendment 236's lines.

## Consequences

With packs set, every domain constraint is a measurable scenario, each threat names the class of the data it carries,
and the stack choice shows what each option cannot meet. The kit has no `[domain]` table and no record, so its own
governance is unchanged. No workflow, label, required check, `agk.mk` recipe, `governance_map.CHECKS` or setting
changes; the steps run in `prepush.py`, `make governance` and the `proof` job, and read files only. `kit/hashes.json`
and the version stay the release's.

## Residual

- 2026-11-26: a project pack constraint that restates a shipped one (SPEC-0074 rule 4) is kept beside it by
  `check_domains.items`, so each needs its row until a person decides; the composer does not choose the stricter.
- 2026-11-26: an item named in a threat flow is matched by its words; a flow that carries an item under another name
  is the reviewer's to read.
