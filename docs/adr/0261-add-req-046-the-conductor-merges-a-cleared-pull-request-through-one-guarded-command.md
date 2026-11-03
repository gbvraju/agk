# ADR-0261: Add REQ-046: The conductor merges a cleared pull request through one guarded kit command

- Status: Accepted
- Date: 2026-11-03
- Deciders: maintainers
- Related: SPEC-0039, SPEC-0032, SPEC-0030, SPEC-0021, REQ-039, REQ-016
- Requirements: REQ-046

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-03:

> With `[flow] auto_merge` on, a kit merge loop the owner starts merges each pull request whose trusted verdict clears its exact head, so delivery runs 24/7, while no session merges and anything risky waits for the person.

The brief is issue #518, which folds in issue #498. The owner's direction, dated 2026-11-03 in the
brief and quoted as data: "Can we include auto-merge option also for local and solo, autopilot
modes. I think this is useful when we have work clarity, 24*7 agent sessions can work for
delivery." The owner then ruled on the design, quoted as data from the conductor's field note on
#518 (2026-11-03): "Merge Loop, build as part of KIT solution, instead of poll, see if we can
subscribe, push solution, currently it is polling every 2mins. It should be single account only,
if possible users can configure second account as well. Simplest way conductor only post verdict
cleared and merged." The ruling refines the sentence: no polling loop, one account by default. Both
are recorded in one row of `docs/runs/decisions-log.md`. In the pilot (2026-11-02 and 2026-11-03)
the owner ran a hand-written merge loop overnight, polling every two minutes: it merged 11 pull
requests unattended, but failed silently once on shell quoting, would have read a multi-line fix
list as cleared, and could not tell the conductor's verdict from one any session posted, because
every session posts from the owner's one account (#498).

## Decision

1. REQ-046 is added to `docs/requirements.md` as `planned`. SPEC-0039 is added as `Draft`. Merging
   this pull request approves the requirement as a proposal; it does not approve the spec, which
   stays `Draft` until the owner's own `Approve:` line approves it (SPEC-0032 rule 5).
2. The setting `[flow] auto_merge` is off by default and is turned on only by an ADR in the pull
   request that changes `agk.toml`, which is the owner's choice (SPEC-0039 rule 1). With it on,
   the conductor, in the same act as posting `Verdict: cleared <sha>`, runs one kit command,
   `scripts/agk/merge_cleared.py --pr N --sha <sha>`, which re-checks the head, the evidence, the
   hold list and the default branch at that moment and merges with the head sha pinned; there is
   no polling loop, and a merge that could not run is retried by the conductor's next
   event-driven review pass (SPEC-0039 rules 2 to 6 and 9).
3. This is the one exception to session rule 2, and to principle 2 of the constitution: only the
   conductor role may merge, and only through `merge_cleared.py`, which
   `.claude/hooks/conductor_guard.py` allows and nothing else that merges, while builders stay
   blocked from any merge (SPEC-0039 rule 8). It takes effect only when build (b) adds that one
   sentence to principle 2 and to session rule 2 (`Q-S0039-14`).
4. One account is the default: a `Verdict:` comment on its own merges nothing, so trust rests on
   who can run the guarded command, not on who posted the comment. An optional
   `conductor_accounts` key of `config/reviewers.yaml`, when set, also requires the verdict's
   author to be listed (SPEC-0039 rule 3). This closes the gap of #498 as far as one account
   allows; the residual of SPEC-0039 names what remains.
5. The builds of SPEC-0039 rule 12 will change these protected path classes: `scripts/agk/`
   (`merge_cleared.py`, new and installed, `reviewers.py`, `doctor.py`, `session.py` and
   `route.py`), `config/` (`config/session-rules.md` rule 2; `config/reviewers.yaml` only when an
   owner lists a second account, never by a build), `constitution/` (principle 2, one sentence, in
   build (b)), `.claude/` (`.claude/hooks/conductor_guard.py`, `.claude/agents/conductor.md` and
   the builders' deny of the command), `kit/` (`kit/manifest.json` and the commented keys of
   `kit/templates/agk.toml`), `agk.toml` (the same commented keys; this repository does not turn
   the setting on) and `tests/kit/` (their tests). Each build adds its own ADR naming the classes
   it changes and citing this one, because the protected-path check counts only an ADR added or
   changed in the same pull request. No build changes `.github/`, `agk.mk`, `CLAUDE.md`,
   `Makefile`, `pyproject.toml`, `skills/`, `.claude-plugin/` or the ruleset files.
6. When this pull request merges, #498 is closed with a pointer to it.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. No check, flow
or setting changes in this pull request, and a project that never turns `auto_merge` on sees no
change from any build. A project that turns it on needs no second account; one is an option.

## Residual

None beyond SPEC-0039's residual. The intake checks cannot tell whether the criteria, the hold list
or the trust rule are the right ones; that is the review of this pull request.
