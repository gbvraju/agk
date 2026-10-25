# Proposed spec amendments 57 (SPEC-0030; REQ-039)

Date: 2026-10-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0118. The path: `docs/specs/0030-a-conductor-role-reviews-every-pull-request-posts-the-verdic.md`. The number 57 is the next one free on the default branch when this was written.

1. **SPEC-0030 rule 2, a fourth end of `watch --pr`.** `session.py watch --pr N` also exits 0 with one line, `label <name>` (or `label none`), when the `agk:` label that the router sets on the pull request (SPEC-0032 rule 2) changes from the one read at its first poll. Verdict, merge, close and conflict come before it; `--merged N` ignores labels; `watch` prints its event and exits, so each event is one wake (SPEC-0032 rule 3). The `ci` end asked for in answer 8 of #176 is met by this end.
2. **SPEC-0030 rule 3, a second command.** `session.py queue --role conductor|builder|person [--author LOGIN]` prints `#N <label>` for each open pull request whose router label is the role's (SPEC-0032 rule 3), or `empty`; a session that restarts runs it first. It writes nothing.
