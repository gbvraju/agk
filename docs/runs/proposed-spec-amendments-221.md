# Proposed spec amendments 221 (SPEC-0072; REQ-079)

Date: 2026-11-23 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0773 (brief #1844), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0072-each-work-type-playbook-carries-its-architecture-a-stack-sta.md` (rules 7 and 9). This file
proposes the lines and does not edit the spec. A later pull request applies them word for word, on the owner's
`Maintainer answer: amendment 221 approved`; no session posts it.

The sentence (brief #1844): "An adopted project can set touched_files = \"meet\" so a file its change edits must pass
the standards pack in full, not only keep its baselined count; the default stays \"hold\" (SPEC-0072 rule 7, no rise),
and the owner decides whether the default changes."

## Items

1. **Rule 7, after "prints the lower count when one falls".** Add: "With `touched_files = \"meet\"`, a file the change
   touches is held to 0 by the steps of rule 6; the default `hold` keeps no-rise (amendment 221)."
2. **Rule 9's table, after the `project_lint_paths` row.** Add the row: "| `touched_files` (new) | `hold` | `hold`:
   rule 7's no-rise; `meet`: a file the change touches (from its merge base) meets the pack's `lint`, `format` and
   `type` in full; with no base not run; another value refused naming the setting |".

No other rule changes.
