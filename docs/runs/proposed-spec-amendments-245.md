# Proposed spec amendments 245 (SPEC-0073; REQ-080)

Date: 2026-11-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written
for ADR-0801 (brief #1933, SPEC-0073 build (a)), on the conductor's fix list on #1945 (comment 7160998083). The path:
`docs/specs/0073-every-idea-is-grilled-before-its-vision-and-held-to-industr.md` (rules 2 and 15). This file proposes the
lines and does not edit the spec; it is applied word for word on the owner's `Maintainer answer: amendment 245
approved`, and no session posts that line.

Why: build (a) reuses the playbook reader and the settings reader instead of copying them, so `grill.py` imports
`playbook_format.py` and `config.py` beside `common.py`; and the derived playbook's skeleton in `front_door.py` copies
`default.toml`'s `[[discovery]]` entries, so it must leave the new grill items out, or a derived playbook would ask
them as discovery questions. The kit's manifest test requires every shipped `scripts/agk/` file to be listed, so the
new script takes its one `kit/manifest.json` row in the build that adds it.

## Items

1. **SPEC-0073 rule 2, the script's imports.** Replace "(standard library and `common.py` only, no network, no
   model)" with "(standard library, `common.py`, `config.py` and `playbook_format.py` only, no network, no model)
   (amendment 245)".
2. **SPEC-0073 rule 15, build (a)'s paths.** At the end of build (a)'s bullet add: "Build (a) may touch `front_door.py`
   as a seventh code path, so the derived playbook's skeleton copies no grill item, and adds the one `kit/manifest.json`
   row the manifest test requires for `grill.py` (amendment 245)."

No other rule changes.

2026-11-26 (from `date -u`), brief #1966: items 1 (to rule 2, as amendment 246 item 2 reads it) and 2 (to rule 15) applied to `docs/specs/0073-every-idea-is-grilled-before-its-vision-and-held-to-industr.md` word for word, on the maintainer's answer on #1945 (comment 7169031896).
