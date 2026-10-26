# ADR-0156: a new project names its spec approver at install (REQ-039, brief 254, SPEC-0032 rule 5)

- Status: Proposed
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0150
- Requirements: REQ-039

Protected classes: `kit/`, `scripts/agk/`, `tests/kit/`

## Context

Brief #254 (priority 1, found 2026-10-26 while writing the start-a-project guide for an org pilot): step 4 of the getting-started
guide has the person replace `@REPLACE-ME` in `config/reviewers.yaml` but never add `spec_approvers`, and the installed file has no
such line. With nobody listed (`reviewers.approvers_of`) no `Approve:` counts, so the intake of step 7 can never be approved. The
tests were written first (`tests/kit/test_reviewers_approvers_install.py`) and failed on the unchanged tree.

## Decision

1. **The templates.** `kit/templates/reviewers.yaml` and `kit/templates/reviewers.adopt.yaml` gain one line after the
   `maintainers` line: `spec_approvers: ["@REPLACE-ME"]` with a one-line comment.
2. **The check.** `reviewers.py --check` (`approver_problems`) fails while `spec_approvers` lists nothing but the placeholder, in
   any spelling, naming the setting and never a value. Absent or empty stays allowed, as SPEC-0032 rule 5 says (reading Q-254-1),
   and a real handle beside the placeholder passes. A fresh install therefore fails on both `verdict_authors` and
   `spec_approvers` until both placeholders are replaced.
3. **The doctor.** `placeholder-team-reviewers` already fails on any `@REPLACE-ME` in the file (SPEC-0006); its failure message and
   fix now name `maintainers` and `spec_approvers`. No new check id.
4. **An upgrade.** The reviewers file is a template, which an upgrade prints and never writes: a project without the line gets the
   note `template-changed config/reviewers.yaml (...)` and its file is unchanged (reading Q-254-2: no note of its own). By the
   ruling on Q-254-3, option (b), `upgrade.py` prints `run: python3 scripts/agk/reviewers.py --codeowners --write` only when the
   run writes, deletes or stamps something or writes the generator, never after `nothing to do`: between this build and the
   release whose row holds the new template digest, a second upgrade would otherwise end with that line.
5. **The guides.** Step 4 of the getting-started guide and its counterpart in the existing-codebase guide say to replace both
   placeholders, and that `spec_approvers` takes user handles only. No spec rule changes, so no amendment. Flow mode: fragment
   `changelog.d/spec-approvers-install.md`; no version bump.

## Consequences

- A person who follows the guide is a listed spec approver before the first intake, so their first `Approve: SPEC-<n>` counts.
- A project that edited its file to `spec_approvers: ["@REPLACE-ME"]` by hand now fails `reviewers --check` until it names a person.

## Residual

- 2026-10-26: an upgraded project with no `spec_approvers` line is told only by the generic template note, not by name; a person
  reads the note and adds the line (due 2026-12-31).
