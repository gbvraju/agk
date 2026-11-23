# Proposed spec amendments 218 (SPEC-0038; REQ-045)

Date: 2026-11-22 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written
for ADR-0735 (brief #1757), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0038-a-project-s-work-type-selects-a-delivery-playbook-that-never-weakens-a-gate.md` (rule 5). Brief #1757
reserved number 218 at take (217 is held by the sibling brief). It proposes the lines and does not edit the spec. A
later pull request applies them word for word, on the owner's `Maintainer answer: amendment 218 approved`; no session
posts it.

The sentence (brief #1757): "The kind of product the owner names in discovery becomes the project's work type on the
owner's plain yes, so the matching playbook's checks switch on before the stack is chosen."

## What is on the default branch today

Read in the code by this session on main at b4a865c (2026-11-22): `front_door.py discovery-write` records `- Work type:
<type> (proposed)` in the discovery document and nothing reads it; rule 5 says a session "never writes, changes or
removes the line itself"; `engines.py stack-write` takes the `default` row of `config/stack-defaults.toml` without a
declaration.

## Items

1. **Rule 5, the sentence "A session may propose a work type, in the stack ADR's context or in a `Question:`, and never
   writes, changes or removes the line itself (`CLAUDE.md item 1`)."** Replace it with: "A session may propose a work
   type, in the stack ADR's context or in a `Question:`, and never writes, changes or removes the line itself
   (`CLAUDE.md item 1`), but one: in solo mode with one person listed, the steward writes the line, on a new branch
   with its Proposed ADR quoting the owner's words, only on that person's recorded plain yes to its one question about
   the work type a discovery document names (`steward_owner.py work-type`, by the rules of SPEC-0062 rule 13 for a
   yes); it never commits, pushes or merges it, and the owner's merge of that pull request is the approval. In team
   mode and in personal mode it only prints the change (amendment 218)."
2. **Rule 5, at its end.** Add: "While a discovery document under `docs/discovery/` names a work type other than
   `pilot` and none is declared, `engines.py stack-write` refuses, naming `delivery.work_type`, so a stack is never
   drafted without the playbook by omission; `doctor.py` warns once, naming the setting `work_type` (amendment 218)."

No other rule changes.
