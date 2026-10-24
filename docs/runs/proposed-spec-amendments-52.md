# Proposed spec amendments 52 (SPEC-0030; REQ-037)

Date: 2026-10-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0102. The path: `docs/specs/0030-a-conductor-role-reviews-every-pull-request-posts-the-verdic.md`.

1. **SPEC-0030 rule 2, a third end of `watch --pr`.** The verdict on #169 ordered it: `session.py watch --pr N` also exits 0 with one line, `conflict #N`, when the pull request's `mergeable_state` is `dirty` (it conflicts with its base), because GitHub starts no pull-request workflow on such a pull request and a session would otherwise wait for CI that never runs. Other states (`clean`, `blocked`, `behind`, `unstable`, `unknown`) do not end the wait; `--merged N` ignores it.
2. **SPEC-0030 rule 11, build (b) is split as measured.** Build (b1) is rule 4 (`check_brief.py`) with the `conflict #N` end of `watch`; build (b2) is rule 6 (the conductor role file and its guard hook), as the verdict on #169 recorded.
