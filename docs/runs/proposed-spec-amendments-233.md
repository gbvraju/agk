# Proposed spec amendments 233 (SPEC-0038; REQ-055)

Date: 2026-11-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0790 (brief #1908), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0038-a-project-s-work-type-selects-a-delivery-playbook-that-never-weakens-a-gate.md` (rule 5). This file
proposes the line and does not edit the spec. A later pull request applies it word for word, on the owner's
`Maintainer answer: amendment 233 approved`; no session posts it.

The sentence (brief #1908): "A project's derived playbook, written by derive-write with its research record, can be named
in `[delivery] work_type` and is then selected by every reader in both layouts; a typo of a kit work type, a bad name or
a missing or failing file is still refused."

## Items

1. **SPEC-0038 rule 5, its first sentence.** After "one value from the list of rule 1 that names a playbook present under
   `config/playbooks/`" add "or the slug of the project's derived playbook (SPEC-0048 rule 22), whose
   `config/playbooks/<slug>.toml` and research record `docs/research/<slug>.md` are both in the project (amendment 233)".

No other rule changes.

2026-11-26 (from `date -u`), brief #1966: item 1 (to rule 5) applied to `docs/specs/0038-a-project-s-work-type-selects-a-delivery-playbook-that-never-weakens-a-gate.md` word for word, on the maintainer's answer on #1912 (comment 7135904405).
