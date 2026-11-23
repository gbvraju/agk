# ADR-0771: The stack skeleton names the inventory's screens, and Node.js reads as node (REQ-079)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers
- Related: SPEC-0072 rule 4, SPEC-0029 rule 5, SPEC-0037 rule 13, ADR-0744, ADR-0672, ADR-0745, brief #1843, brief #1778, plan #661
- Requirements: REQ-036, REQ-079

Protected classes: `scripts/agk/`, `kit/`, `skills/`, `tests/kit/`, `tests/kit_dev/`

## Context

PB-06 (plan 2, 2026-11-23) found two gaps on the prototype path. `engines.py stack-write` filled the stack record from
the template, the playbook and the recommended option only, so a record written beside a design inventory named none
of its screens, and nothing made the options say how each builds them. And `pins.option_parts` read a part's runtime
only when its first word equalled a `STACKS` key but for case (ADR-0744 decision 1); decision 2 kept `Node.js` and
`nodejs` out as the conservative reading of `Q-F3-1`. A record that wrote `Node.js 22.11.0` read as `no stack chosen`:
`stack-check` printed a false runtime note, and pins, the node pack, layers and the tests floor said not run.

## Decision

1. When `docs/design/inventory.md` exists and its `## Screens` part has at least one screen, `stack-write` writes, in
   the `{{screens}}` slot under the Context's `TODO(architect)` line, one line `Screens to build
   (docs/design/inventory.md; <version>): \`<id>\` (<pattern>), ... Each option says, in its Build speed phrase, how
   it builds these screens.`, the screens in file order. `<version>` is `signed-off version <v>` for the newest
   version with a `design` row whose digest its folder still has (`design_signoff.signed_off`), a kit version `v<n>`
   before an imported `i<n>` and the higher number first within each, else `no signed-off version yet`. It names
   screen ids and patterns only, never a page's text or an imported file. With no inventory, or none with screens,
   the slot line is removed and the skeleton is as before.
2. `skills/stack/SKILL.md` step 2 fills each option's `Build speed:` phrase with how it builds those screens, from the
   inventory and the signed-off version only, and keeps the line in the Context.
3. `pins.option_parts` reads a part's first word through one table, `RUNTIME_NAMES`, case-folded: `node`, `node.js`,
   `nodejs` give `node`; `python`, `python3`, `cpython` give `python`; every other name is kept as written. Its
   readers (`pick`, `chosen`, layers, the tests floor, both packs, `stack-files`, `runtime_notes`, `licence_notes`,
   `parts_problems`) change nothing of their own. Two-word forms (`Node JS 22.11.0`) stay two words. This supersedes
   ADR-0744 decision 2 only; decisions 1 and 3 are kept.
4. A kit test holds every value of `RUNTIME_NAMES` to a `STACKS` key and every key to its own row, so a runtime added
   to `STACKS` without its spellings fails.

## Consequences

The architect sees on the record which screens each option must build. A record written `Node.js`, `NodeJS`, `nodejs`,
`python3` or `CPython` gets its pins, standards pack, layers, tests floor and `stack-files` without a rename, in
GitHub, local and personal modes alike, with no workflow change. An Accepted record that already says `Node.js` gets
those gates from this release and may fail governance until its build file and lock are in step (`Q-HI-2`); an
adopted project is held by its baseline. The licence list is unchanged (`Q-HI-3`).

## Residual

- 2026-11-23: `Q-F3-1` (ADR-0744's Residual) is answered here by PB-06's evidence; the reviewers accept or reject it
  with this record.
- 2026-11-23: whether `PostgreSQL` joins the kit's default licence list is open as `Q-HI-3`, for its own brief.
