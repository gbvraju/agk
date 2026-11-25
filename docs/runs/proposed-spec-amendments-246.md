# Proposed spec amendments 246 (SPEC-0073; REQ-080)

Date: 2026-11-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written
for ADR-0802 (brief #1934, SPEC-0073 build (b)), on the conductor's fix list on #1946 (comment 7170304873). The path:
`docs/specs/0073-every-idea-is-grilled-before-its-vision-and-held-to-industr.md` (rules 2 and 6). This file proposes the
lines and does not edit the spec; it is applied word for word on the owner's `Maintainer answer: amendment 246
approved`, and no session posts that line.

Why: the discovery document's `## Readiness` section is build (c)'s, so build (b)'s `grill.py ready` reads the
answers file, where `grill.py record` keeps the answers (brief #1934 answer 3); and `grill.py record` runs the data guard
of rule 14 on every value it writes, so `grill.py` imports `guard.py`, the reader `front_door.py` already uses.

## Items

1. **SPEC-0073 rule 6, the readiness command.** Replace "`grill.py ready --discovery <file>`" with "`grill.py ready
   --answers <file>`" (amendment 246).
2. **SPEC-0073 rule 2, the script's imports.** In the list as amendment 245 reads it, replace "(standard library,
   `common.py`, `config.py` and `playbook_format.py` only, no network, no model)" with "(standard library, `common.py`,
   `config.py`, `playbook_format.py` and `guard.py` only, no network, no model) (amendment 246)".

No other rule changes.
