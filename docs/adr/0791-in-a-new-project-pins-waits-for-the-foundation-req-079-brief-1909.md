# ADR-0791: In a new project, pins waits for the foundation instead of failing the stack's acceptance (REQ-079)

- Status: Proposed
- Date: 2026-11-24
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1909, the test-run re-run on #1769 (IB-11), ADR-0672 (the stack writes its own build file and lock),
  ADR-0742 (the runner runs pins), ADR-0768 (pins reads `requirements.txt`), ADR-0668 (brief #1588: a step that cannot
  read the project is never `ok`), SPEC-0072 rule 4, amendment 234, plan #661
- Requirements: REQ-079

Protected classes: `scripts/agk/`, `tests/kit/`, `skills/`

## Context

On the branch where `engines.py stack-accept` accepts the stack of a new (init) project, `kit_root.py governance` exits 1
on `pins`: `the lock file is missing` for a Python stack, `the build file is missing or unreadable` for a Node stack. The
stack skill says `stack-check` and governance must both pass on that pull request, and the line stays red on the default
branch after the merge and on every planning pull request until the foundation. SPEC-0072 rule 4 places the build file
(`engines.py stack-files`) and the lock (made by the stack's own tool on the builder's machine) in the foundation build,
and also fails a missing lock from the acceptance on; for an init project the two sentences conflict. The owner's word
(2026-11-24, the steward chat, quoted as data): "Yes, file the four test-run briefs".

## Decision

1. `gates/pins.py` gains `waiting(root)`, true only when all hold: a stack is chosen (`chosen`); the project is not
   adopted (`baseline.adopted`: `mode = "adopt"` in `agk.toml`; an unreadable `agk.toml` reads as not adopted); the
   architecture record `docs/architecture.md` (the path of `layers.RECORD`) is absent; the stack's lock (the third
   column of `STACKS`) is absent; and the stack's build file is absent, or `declared` reads it and finds no direct
   dependency (Python: `pyproject.toml`, `requirements.txt` and each file it names, as `python_files` reads them). A
   Python build file that is absent beside a `requirements.txt`, and a build file that cannot be read, never wait.
2. `skipped` returns `no stack chosen` as before, else `no foundation yet` while `waiting`, else None; `findings`
   returns None while waiting, so `counts` is empty, the runner prints `not run pins: no foundation yet` and names
   `pins` in its last line's `not run:` list, and `gates/pins.py` prints `pins: not run: no foundation yet`, exit 0.
   It is never `ok` (ADR-0668).
3. Any one of a declared dependency (pinned or not), a committed lock (then read in full as before) or the architecture
   record ends the wait, so the foundation pull request, which writes all three (SPEC-0072 rules 4 and 5), and every
   later one is checked as before. `stack-files` alone still waits.
4. An adopted project never waits (`Q-PN-3`): its missing lock fails and its baseline holds it, as before.
5. No step makes the lock (`Q-PN-4`): the lock is still the stack's own tool's, on the builder's machine.
6. SPEC-0072 rule 4 is not edited here: `docs/runs/proposed-spec-amendments-234.md` proposes its words (`Q-PN-2`).
7. `skills/stack/SKILL.md` step 4 says the accepting branch, and every branch until the foundation, prints
   `not run pins: no foundation yet`; the prompt for the accepting change is unchanged.

Options weighed (`Q-PN-1`): (a) the skill orders the lock into the accepting pull request, and (c) `stack-accept`
writes the lock step: refused, since `stack-accept` makes exactly two commits and nothing else, and the lock needs the
stack's own tool and the network on the person's machine. (b) the gate allows a missing lock only on the pull request
that adds the Accepted record: refused, since the default branch itself and every next branch are red after that merge,
and the step would need a base diff that `personal.py floor` and a plain `gates/pins.py` run do not have. Chosen: a
state read offline from the tree, as `tests-first` and `injection-set` do, which ends at the first thing to pin.

## Consequences

The accepting and planning pull requests of a new project pass governance with `pins` not run. Every declared
dependency is still pinned and locked from the first one on, and from the foundation on in any case. The line names
the reason only, never a file name, a package or a version (principle 8). `pins.ARCHITECTURE` repeats the path of
`layers.RECORD`, because `gates/layers.py` imports `gates/pins.py`; a test holds the two equal.

## Residual

None.
