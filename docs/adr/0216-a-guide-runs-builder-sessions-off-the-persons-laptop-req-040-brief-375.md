# ADR-0216: a guide runs builder sessions off the person's laptop (REQ-040, brief 375)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: none
- Requirements: REQ-040

Protected classes: `tests/kit_dev/`

## Context

Brief #375 (#288 part 5): in a pilot two builders and their heavy runs shared one laptop with the person's own work, and a memory
kill stopped a builder's watch unnoticed. A session can already resume from GitHub alone (REQ-040), which is what a session in a
remote development environment needs. The brief asks for one guide and a kit_dev test of it; the test is under `tests/kit_dev/`, a
protected path class, so this record names it (the conductor reserved this number for that case).

## Decision

1. **One guide (answer 1).** `docs/guides/remote-builders.md` says what a remote builder needs (a git checkout of its own,
   python3, `gh` signed in with a builder token with write access to contents, pull requests and issues and no administration,
   secrets or members access, the Workflows permission only when builds change workflow files, permission names marked
   `(verify)`; the ruleset of the default branch (`/agk:ruleset`), since a token's permissions are per repository and the
   ruleset, not the token, refuses a direct push or an unchecked merge to the default branch; the project's toolchain, a way to keep `session.py watch` in the background), how it starts (the pause
   check of session rule 33, `session.py next`, a claim) and resumes from GitHub (`session.py resume --pr`, `session.py after`,
   the outage rule), and what stays on the person's machine: review, approval, merge, secrets and the repository's settings.
2. **The safety rules (answer 2)**, each in the guide's own section: no production secret in the environment; no admin token; a
   session's token can only push branches and comment, with the ruleset, not the token, guarding the default branch; the environment is stopped when idle; the person's own sign-in is never
   copied into it.
3. **Generic (answer 3).** The guide names no provider; each need is a capability. Starting remote sessions from the steward is
   not part of it (#286, Autopilot phase 3).
4. **Tests first (answer 4).** `tests/kit_dev/test_remote_builders_guide.py`: the guide exists with its four sections in order,
   names each need, each safety rule and the start and resume commands, names only commands that `session.py` has, keeps review,
   approval, merge and secrets with the person, says what the ruleset enforces and the token does not, and names no provider
   from a list of hosts, clouds and tools.

## Consequences

A person whose laptop cannot carry builders has one page to follow, and the safety rules are checked to stay in it. No script,
check or session rule changes.

## Residual

- 2026-10-30: the verdict on 00251ed, finding 1: the guide no longer says the token refuses a push to the default branch or a
  change to workflows; it names the token's permissions (marked `(verify)`) and the ruleset as what guards the default branch
  (decisions 1 and 2), and the test checks that the ruleset is named.
