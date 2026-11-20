# Proposed spec amendments 208 (SPEC-0062; REQ-069)

Date: 2026-11-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0679 (brief #1599, reserved number 208), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0062-in-solo-mode-the-steward-guides-the-person-and-asks-only-about-the-product.md` (rule 2 and the
`## Open questions` entry `Q-S0062-7`). This file proposes the lines and does not edit the spec; they are applied word
for word on a person's `Approve: SPEC-0062` on the pull request that carries this file; no session posts it.
Amendment 209 carries the SPEC-0048 side.

## What is on the default branch today

Read in the code by this session on main at b5f1a08 (2026-11-20):

- SPEC-0062 rule 2: "The steward never changes `review_mode` itself, since it decides who approves (`Q-S0062-7`)."
- `kit/templates/agk.toml` and `kit/templates/agk.adopt.toml` write `review_mode = "team"`; `reviewers.py`
  `solo_problems` refuses solo when the reviewers file lists nobody or more than one person.
- Nothing writes `review_mode = "solo"` in a new project: the person edits a protected file by hand, which SPEC-0062
  rule 11 says the person never does.

## Items

1. **Rule 2, its last sentence replaced.** "The steward never changes `review_mode` on its own, or after setup, since
   it decides who approves (`Q-S0062-7`). At setup only, it asks the person one plain question, 'Will you run this
   alone, or with a team? Alone (recommended for one person) · with a team', and the person's own answer is written by
   the install pull request of `init` or `adopt` (`--solo`), as `review_mode = "solo"` with its line in that install's
   ADR, or left `team`; it is recorded as one `Setup:` entry with the person's words. After the install the steward
   refuses to set it."
2. **`Q-S0062-7`, its reading extended.** "Reading: no, but at setup, from the person's own answer and only through the
   install pull request with its ADR (amendment 208); later, never."
3. **Unchanged:** rules 1 and 3 to 19, the Tests, the Proof, the Residual and the Contexts.

## Questions (brief #1599), each with the reading this proposal takes

- Q-1599-1 (the brief's Q-1): may the setup question set `review_mode`? Reading: yes, only at setup, only from the
  person's own answer, only through the install pull request with its ADR (the brief's recommendation). Without it,
  every solo person hand-edits a protected file.
