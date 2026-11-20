# Proposed spec amendments 209 (SPEC-0048; REQ-069)

Date: 2026-11-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0679 (brief #1599, reserved number 209), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0048-a-problem-in-a-person-s-words-takes-one-guided-path-to-the-builds.md` (rule 5 and its open question
`Q-S0048-6`). SPEC-0062 rule 8 and `Q-S0062-8` ask for this proposal from build (b). This file proposes the lines and
does not edit the spec; they apply on a person's `Approve: SPEC-0048`, and a later build changes
`front_door.py discovery-write` and `check-discovery` to match; no session posts the approval. Amendment 208 carries
the SPEC-0062 side.

## What is on the default branch today

Read in the code by this session on main at b5f1a08 (2026-11-20):

- SPEC-0048 rule 5: `- Work type:` is "one value of SPEC-0038 rule 1 followed by `(proposed)`, or `pilot (proposed)`
  when the kind is not yet clear (`Q-S0048-6`)", written by `front_door.py discovery-write` and read only by its own
  check; nothing reads it to choose a playbook (SPEC-0062 rule 1).
- SPEC-0062 rule 8: the kit's default is an enterprise product; a pilot is planned only on the person's words.

## Items

1. **Rule 5, the `- Work type:` clause replaced.** "`- Work type:` one value of SPEC-0038 rule 1 followed by
   `(proposed)`; `unclear (proposed)` when the kind is not yet clear, which plans the product on the kit's full path as
   an enterprise product and records an open point `D-<n>` that the kind is not settled; and `pilot (proposed)` only
   when the person's own words ask for a pilot (a short trial to test the idea) (`Q-S0048-6`, SPEC-0062 rule 8)."
2. **`Q-S0048-6`, its reading replaced.** "Reading: an unclear kind is `unclear (proposed)`, an enterprise product on
   the full path, never a pilot by default (amendment 209)."
3. **The build.** `front_door.py discovery-write` writes `unclear (proposed)` in place of `pilot (proposed)` when no
   kind is given, and `check-discovery` accepts `unclear` beside the values of SPEC-0038 rule 1; filed later by the
   `brief` skill, tests first, after the approval.
4. **Unchanged:** every other rule of SPEC-0048, and SPEC-0038's work types: `unclear` is a value of this line only,
   never a work type that `[delivery] work_type` can declare.
