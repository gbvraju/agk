# Proposed spec amendments 237 (SPEC-0038; SPEC-0037; REQ-080)

Date: 2026-11-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0793 (brief #1918, SPEC-0073 rule 13), which stays `Proposed` for the maintainers' decision. The paths:
`docs/specs/0038-a-project-s-work-type-selects-a-delivery-playbook-that-never-weakens-a-gate.md` (rules 2 and 10) and `docs/specs/0037-a-project-s-design-phase-delivers-a-click-through-prototype.md` (rule 7). This file proposes the lines and does not edit the specs. SPEC-0073's build (a) (item 1) and build (i) (items 2 and 3) applies it word for
word, on the owner's `Maintainer answer: amendment 237 approved`; no session posts it (`Q-PN-2`).

The sentence (brief #1918), quoted as data: "Intake for Day-1 quality: a grill interview tests every idea before its vision, and the same path then holds the product, design, architecture and build to industry practice, in solo and team, with no slower path and no new CI job."

## Items

1. **SPEC-0038 rule 2, two keys of `[[discovery]]`.** In the list of the format's sections, to the `[[discovery]]`
   entry add: "with two optional keys, `depth` (`light`, `standard` or `deep`) and `critical` (a boolean), which make
   the entry a grill item of SPEC-0073; an entry with neither is a discovery question as before, and `check_playbooks.py`
   refuses a grill id that reuses a topic, fixed or other `[[discovery]]` id, another `depth` and a `critical` that is
   not a boolean, naming the playbook and the key (amendment 237)."
2. **SPEC-0038 rule 10, the usability check.** Under **web-app** and **mobile** add: "usability, `check` (each screen of
   the inventory lists the ten usability heuristics in `docs/design/usability.md`, each as `pass`, `finding: <text>` or
   `not applicable`, one section per prototype version, read by `check_design.py`) (amendment 237)."
3. **SPEC-0037 rule 7, the target standard.** Add at the end of the rule: "The `accessibility` gate's text names WCAG 2.2
   level AA as the target unless the discovery's `accessibility` answer names another standard, and the usability
   record of SPEC-0038 rule 10 is checked beside the prototype for `web-app` and `mobile`, outside the version folder,
   so a signed-off version stays frozen (amendment 237)."

No other rule changes.

2026-11-25 (from `date -u`), brief #1933: item 1 (to rule 2) applied to `docs/specs/0038-a-project-s-work-type-selects-a-delivery-playbook-that-never-weakens-a-gate.md` word for word, its last full stop made a comma so the sentence goes on, on the maintainer's answer on #1920 (comment 7159666133); items 2 and 3 are build (i)'s.

2026-11-25 (from `date -u`), brief #1953: items 2 (to SPEC-0038 rule 10, under **web-app** and **mobile**, each bullet's
last full stop made a semicolon so the list goes on) and 3 (at the end of SPEC-0037 rule 7's own paragraph, before its
amendment 173 bullet) applied word for word, on the maintainer's answer on #1920 (comment 7159666133). All three items
are now applied.
