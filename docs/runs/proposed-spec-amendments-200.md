# Proposed spec amendments 200 (SPEC-0029; REQ-036)

Date: 2026-11-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0672 (brief #1592), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0029-a-product-owner-starts-from-a-brief-idea-the-vision-the-stac.md` (rule 5, the `## Tests` section and
the `## Contexts` section). Brief #1592 reserved amendment 200. This file proposes the lines and does not edit the spec.
They are applied word for word, on a person's `Approve: SPEC-0029`; no session posts it.

The sentence (brief #1592): "The chosen stack is recorded with each main part's exact version and licence, and the
foundation writes that stack's own build file and lock file, so every build of the product is repeatable and no Python
file is forced on a non-Python product."

## Why

On the default branch at 294b9e8 (2026-11-20) `kit/templates/stack-adr.md` has `Options`, `Practices` and `Chosen` with
no version or licence field, and `engines.py` `stack_problems` checks none (gap G21, brief #1592).

## Items

1. **Rule 5, one sentence added after the sentence that begins "In a Proposed record".** "In a Proposed record, each
   option also names its `Parts:`, a list of `<name> <exact version> <licence id>` for the runtime, the framework, the
   database engine and each library it names, the licence as an SPDX id and the version the latest stable read on the
   record's date, marked `(verify)` until the foundation's build installs it; a range, no version or no licence id is
   refused naming the rule, the option letter and the part's place, never a value, and an Accepted record is checked as
   before." (answer 1)
2. **The `## Tests` section, one line added after the "Rule 5, the choice" line.** "- Rule 5, the parts: a Proposed
   record whose part has a range, no version or no licence id is refused naming the option letter and the part's place,
   and an Accepted record without parts still passes; REQ-036 AC4."
3. **The `## Contexts` section, its `kit` line becomes:** "- kit: the stack check's four effects, recommendation and
   pinned parts, the per-shape defaults, the accept command and the steward's plain presentation."
4. **Unchanged:** rules 1 to 4 and 6 to 10, the Proof, the Residual and the Open questions.

## Questions (brief #1592), each with the reading this proposal takes

- Q-1592-1: what is an exact version? Reading: two or more numeric fields with at most a pre-release or build tag
  (`3.12.7`, `16.4`, `1.0.0rc1`); `^`, `~`, `>=`, `*`, `x` and a single number are ranges.
- Q-1592-2: which licence ids? Reading: an SPDX id or expression in its usual form (`MIT`, `Apache-2.0`,
  `MIT OR Apache-2.0`, `LicenseRef-...`), checked for form only, offline; the SPDX list itself is not read.
