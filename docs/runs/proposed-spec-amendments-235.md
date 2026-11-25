# Proposed spec amendments 235 (SPEC-0048; REQ-080)

Date: 2026-11-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0793 (brief #1918, SPEC-0073 rule 13), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0048-a-problem-in-a-person-s-words-takes-one-guided-path-to-the-builds.md` (rules 4 to 7 and 13). This file proposes the lines and does not edit the spec. SPEC-0073's build (c), after (b), applies it word for
word, on the owner's `Maintainer answer: amendment 235 approved`; no session posts it (`Q-PN-2`).

The sentence (brief #1918), quoted as data: "Intake for Day-1 quality: a grill interview tests every idea before its vision, and the same path then holds the product, design, architecture and build to industry practice, in solo and team, with no slower path and no new CI job."

Applied (2026-11-25, from `date -u`): items 1 to 5 to
`docs/specs/0048-a-problem-in-a-person-s-words-takes-one-guided-path-to-the-builds.md`, word for word, by SPEC-0073
build (c) (brief #1938, ADR-0803), on the owner's `Maintainer answer: amendment 235 approved` (#1920, 2026-11-25 10:25
UTC).

## Items

1. **SPEC-0048 rule 4, the grill.** After "`not known yet` is an allowed answer." add: "Before the vision's draft, the
   grill of SPEC-0073 asks the composed playbook's `[[discovery]]` entries that carry `depth` and `critical` (the grill
   items), for the depth of `[quality] grill`, each with a recommended answer, in the same rounds; grill ids are never
   ids of this rule's order, and a grill answer is recorded only in the discovery document's `## Assumptions` section
   (amendment 235)."
2. **SPEC-0048 rule 5, the three sections.** After "`## Open points`, every `open` answer and every point the person
   raised that no answer settles, each as `D-<n>`." add: "When the grill ran, three sections follow: `## Assumptions`
   (`A-<n>`: the grill id, the claim, `stated`, `assumption` with its test, or `open`), `## Risks` (`R-<n>`: the risk,
   its first sign and its owner) and `## Readiness` (one line `critical <settled>/<total>; risk accepted: <ids or
   none>; questions <asked>/<budget>; accepted recommendations <n>`); the check reads each only when present and fails
   a readiness line whose critical total is not the composed playbook's (amendment 235)."
3. **SPEC-0048 rule 6, alternatives.** After "a recommendation marked `(proposal)`." add: "At grill depth `standard` and
   `deep` the record also holds `## Alternatives today`: the discovery's `today` answer and at least one other option
   users have, each with a source line, or the one line `not researched: the person declined`, accepted in this section
   only (amendment 235)."
4. **SPEC-0048 rule 7, the hold.** After "and checks the record when it exists." add: "While `[quality] grill_hold` is
   true, `check_design.py` (the governance step `design`) holds a design whose problem's discovery document has a
   `## Readiness` section with a critical item open and no `Risk accepted:` line for it, naming the rule and the file;
   a discovery document with no `## Readiness` section is never held (amendment 235)."
5. **SPEC-0048 rule 13, auto-pilot rounds.** After "at most three questions each," add: "the grill's questions among
   them, each with its recommendation," (amendment 235).

No other rule changes.
