# ADR-0316: `/agk:stack` reads the declared work type and its playbook (REQ-045, brief 663)

- Status: Proposed
- Date: 2026-11-07
- Deciders: maintainers
- Related: ADR-0251, ADR-0259, ADR-0312, ADR-0313, ADR-0241, SPEC-0038
- Requirements: REQ-045

Protected classes: `scripts/agk/`, `skills/`, `tests/kit_dev/`

## Context

SPEC-0038 rule 12 build (e) builds rule 6: with a declared work type, `engines.py stack-write`
writes into the stack ADR's skeleton one Practices bullet for each gate of the playbook,
`- <id>: check (step: <step>)` or `- <id>: judgement`, marked `(playbook <work type>)`, beside the
practices the options name, and the playbook's `[testing]` profile, `always_full` and `map`
suggestions into the parenthesis of the `test selection` practice for each option; they are
proposals, the architect chooses as today, and the `[testing]` table of `agk.toml` changes only by
the step after **Chosen**; without a declaration the skeleton is the same as today (REQ-045 AC3).
Brief #663 gives the build (the sentence: never a vendor choice); ADR-0251 sets the direction and
lists the classes the builds of SPEC-0038 change; ADR-0312 built the declaration, read through
`playbook_format.declaration` (the brief's answer 1 names that module; rule 12 (e) still names
`playbook.py`, ADR-0259's residual); ADR-0313 shipped the web-app playbook that this build reads
in its tests; ADR-0241 (brief #450) made `stack-check` compare `[testing]` with the chosen option's
part of the `test selection` parenthesis. This ADR number was reserved for brief #663 by the
conductor.

## Decision

1. `engines.py stack-write` (kit-only) calls `playbook_format.declaration(root)` before it writes.
   With no declaration it writes the template as before, byte for byte. A declaration with a
   problem is refused with that problem line (rule 5, `agk.toml`, the setting `work_type`, never
   the value); a declared playbook that fails `playbook_format.problems` is refused with one line,
   `rule 6: the declared playbook fails check_playbooks.py (setting: work_type)`. A refusal writes
   nothing. Brief #663 answer 2 says a missing playbook file is "refused naming the file"; the
   refusal names `agk.toml` and the folder `config/playbooks/`, and not the file whose name is the
   value, by principle 8 and rule 5 (Q-663-1, Q-663-2).
2. The gate bullets are written after the template's `TODO(architect)` practice, one per gate in
   the playbook's order: `   - <id>: check (step: <step>) (playbook <work type>)` or
   `   - <id>: judgement (playbook <work type>)`. The form is rule 6's; `owner_only` is not
   marked, and an owner-only gate is read in the playbook (Q-663-3). `stack-check` reads each as
   a well-formed practice (`PRACTICE`: a check whose parenthesis starts `step:`).
3. The `test selection` parenthesis becomes `(Option A: <proposal>; Option B: <proposal>)`, one
   part per option of the template's Options item, where the proposal is `profile <profile>,
   always_full `<path>`, ..., map `<code> -> <tests>`, ... (playbook <work type>)` (`none` for an
   empty list). It is in the form `stack-check` reads after acceptance (ADR-0241): one profile word
   and the `always_full` paths in backticks. A map suggestion is one backticked `<code> -> <tests>`
   pair, and `testing_match` leaves out a backticked token that holds the arrow ` -> `, so a map
   suggestion is never compared as an `always_full` path. That is the one change to brief #450's
   reading: a plain backticked path is still a path.
4. Nothing else of the ADR changes: the Options, Chosen, Context, Consequences and Residual are the
   template's. No reader writes `agk.toml` or the playbook; `[testing]` of `agk.toml` still changes
   only by the step after **Chosen** (`skills/stack/SKILL.md`).
5. `skills/stack/SKILL.md` says, in step 1, what a declaration adds to the skeleton, that the bullets
   and the proposal are proposals and never a vendor choice, that a project adds a gate of its own
   as one more practice bullet and never by editing the playbook, and that a missing or failing
   playbook is refused naming the setting; step 2 keeps or amends the proposals.
6. `tests/kit_dev/test_stack_playbook.py` (new) reads the shipped `web-app` playbook as its fixture.
   `agk.toml` is not changed: the brief's `Touches:` line does not name it, and whether its test
   map names the new file for `engines.py` and `playbook_format.py` is asked (Q-663-4); until then
   CI's full suite runs it, and a prepush that changes `engines.py` runs the files the map names
   today. No installed file changes (`engines.py` is kit-only, the skill is not in
   `kit/manifest.json`), so there is no changelog fragment, no manifest change and no version bump;
   `kit/hashes.json` is not edited.

## Consequences

A project that declares no work type sees the same skeleton as before. A project that declares one
gets the playbook's gates and its testing suggestion in the skeleton it drafts from; the architect
still fills the options, chooses and accepts as today, and `stack-check` reads the proposals like any
other practice.

## Residual

- 2026-11-07: SPEC-0038 rule 12 (e) names `scripts/agk/playbook.py`; the module is
  `playbook_format.py` (ADR-0259's residual; the next amendment corrects the name, due 2026-12-31).
- 2026-11-07: whether a gate's `owner_only` should be marked in its bullet is Q-663-3; until a
  person rules the bullet is rule 6's form (due 2026-12-31).
- 2026-11-07: a project's own playbook problems are reported by `check_playbooks.py`; `stack-write`
  only says that the check fails (Q-663-2, due 2026-12-31).
- 2026-11-07: the test map of `agk.toml` does not name `tests/kit_dev/test_stack_playbook.py` yet
  (Q-663-4; a map change is the maintainers' and makes the prepush selection full, due 2026-12-31).
