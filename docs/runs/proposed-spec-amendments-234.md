# Proposed spec amendments 234 (SPEC-0072; REQ-079)

Date: 2026-11-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0791 (brief #1909), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0072-each-work-type-playbook-carries-its-architecture-a-stack-sta.md` (rule 4). This file proposes the line and
does not edit the spec. A later pull request applies it word for word, on the owner's
`Maintainer answer: amendment 234 approved`; no session posts it (`Q-PN-2`).

The sentence (brief #1909): "In a new project, from the stack's acceptance to the foundation, while no lock is committed and
the build file declares no dependency, governance prints `not run pins: no foundation yet`, never a failure or `ok`; a
dependency, a lock or the architecture record makes pins strict."

## Items

1. **SPEC-0072 rule 4, the `pins` step.** After "it prints `not run: no stack chosen`" add: "; in a project not adopted,
   while the architecture record of rule 5 is absent, no lock is committed and the build file is absent or declares no
   dependency, it prints `not run: no foundation yet`, never `ok`" (amendment 234).

No other rule changes.
