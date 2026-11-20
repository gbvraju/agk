# ADR-0640: The personal-mode guide names exactly what the code accepts, and a recorded walk shows the product untouched

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: ADR-0267, ADR-0637, ADR-0638, SPEC-0041, brief #1510
- Requirements: REQ-048

Protected classes: `tests/kit/`, `agk.toml`

## Context

SPEC-0041 rule 30 build (n) asks for `docs/guides/personal-mode.md`, the rewrite of `docs/guides/security.md` and of
the existing-codebase guide's paragraph that rule 29 names, the limits in `README.md` and a recorded live walk on an
invented project in `docs/runs/`. On main builds (a) to (m) had merged, but there was no guide, and the security guide
still said "Nothing outside your repository.", which personal mode makes untrue. ADR-0267 asks each build of the spec
for its own ADR naming its classes; this is build (n).

## Decision

1. `docs/guides/personal-mode.md` covers, in order: when to use it, the user-scope install (marked `(verify)` as the
   reference is), attach, survey and adopt, the terminal confirmation, the levels and the floor, a change from start
   to finish, `pr-summary` and disclosure, `report`, export, upgrade and detach, the settings and the limits. It says
   that there is no `sync` command and no `/agk:personal push` command on main, and that `sync_remote` is accepted
   but not used.
2. `tests/kit/test_personal_guide.py` finds the commands, steps and options by asking the parsers of `personal.py` and
   `personal_state.py` which of the strings in their source they accept, so the list is the code's and not a copy. It
   fails when the guide leaves one out, when the guide's code names a command, a step or an option the parser refuses,
   and when the guide's settings table differs from `common.PERSONAL_KEYS`. It also checks the security,
   existing-codebase and README text, the walk's steps and hosts, and the neutrality tokens on the new files.
3. `docs/guides/security.md` says that in team mode nothing is stored outside the repository and in personal mode
   nothing in it, and lists what the state folder holds: `AGK_HOME`, `0700` and `0600` on POSIX, no code excerpt by
   default (`quote_lines`), no credential, sync off, no push. `docs/guides/existing-codebase.md` gains the paragraph
   that behaviour observed in code is an allowed `Proposed` source, cited, never `done` until a test asserts it.
   `README.md` states the limits in one bullet of two lines and lists the guide.
4. The walk, `docs/runs/personal-mode-walk.md`, was run once by the builder session on main as merged, invented data
   only (`example.com`). `confirm` is recorded as refused in the agent session, as rule 8 requires; the person's
   terminal yes is not in it.
5. `agk.toml` maps `personal.py` and `personal_state.py` to the new test, so a change to either parser runs it.

## Consequences

A developer can follow one page from install to detach, and a command added to `personal.py` without a line in the
guide turns the kit's tests red. The walk is evidence of the commands as merged on 2026-11-20, not of later builds.

## Residual

- 2026-11-20: the walk holds no terminal confirmation by a person; an agent session cannot make one (Q-1510-1).
- 2026-11-20: the brief asks for `Secret-scan: deferred to CI`; the owner's direction of 2026-11-20 says never to
  write it, so the body does not carry it and the scan ran in the session.
