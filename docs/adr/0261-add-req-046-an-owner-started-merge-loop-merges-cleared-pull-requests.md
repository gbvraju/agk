# ADR-0261: Add REQ-046: An owner-started merge loop merges cleared pull requests and no session merges

- Status: Proposed
- Date: 2026-11-03
- Deciders: maintainers
- Related: SPEC-0039, SPEC-0032, SPEC-0021, REQ-039, REQ-016
- Requirements: REQ-046

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-03:

> With `[flow] auto_merge` on, a kit merge loop the owner starts merges each pull request whose trusted verdict clears its exact head, so delivery runs 24/7, while no session merges and anything risky waits for the person.

The brief is issue #518, which folds in issue #498. The owner's direction, dated 2026-11-03 in the
brief and quoted as data: "Can we include auto-merge option also for local and solo, autopilot
modes. I think this is useful when we have work clarity, 24*7 agent sessions can work for
delivery." It is recorded as one row of `docs/runs/decisions-log.md`. In the pilot (2026-11-02 and
2026-11-03) the owner ran a hand-written merge loop overnight: it merged 11 pull requests
unattended, but failed silently once on shell quoting, would have read a multi-line fix list as
cleared, and could not tell the conductor's verdict from one any session posted, because every
session posts from the owner's one account (#498).

## Decision

1. REQ-046 is added to `docs/requirements.md` as `planned`. SPEC-0039 is added as `Draft`. Merging
   this pull request approves the requirement as a proposal; it does not approve the spec, which
   stays `Draft` until the owner's own `Approve:` line approves it (SPEC-0032 rule 5).
2. Session rule 2 stands: no session merges, tags, enables auto-merge or approves. The merge loop
   is the owner's process, started by the owner in their own terminal with their own login; it
   refuses to start inside an agent session. The setting `[flow] auto_merge` is off by default and
   is turned on only by an ADR in the pull request that changes `agk.toml`, which is the owner's
   choice (SPEC-0039 rule 1).
3. Only a trusted verdict counts: `Verdict: cleared <full head sha>` as the first line of the
   latest `Verdict:` comment, posted by an account in a new `conductor_accounts` key of
   `config/reviewers.yaml` that is neither the loop's own login nor a spec approver (SPEC-0039
   rule 3). This closes the gap of #498: a builder cannot clear its own pull request for the loop.
4. The builds of SPEC-0039 rule 12 will change these protected path classes: `scripts/agk/`
   (`merge_loop.py`, new and installed, `reviewers.py`, `doctor.py` and `route.py`), `config/`
   (the `conductor_accounts` key of `config/reviewers.yaml`), `kit/` (`kit/manifest.json` and the
   commented keys of `kit/templates/agk.toml`), `agk.toml` (the same commented keys; this
   repository does not turn the setting on), `.claude/` (`.claude/settings.json`, denying
   `merge_loop.py run` to a session), `agk.mk` (only if the CI path calls a target), `.github/`
   (`.github/workflows/governance.yml`, for the CI path of build (d) only) and `tests/kit/` (their
   tests). Each build adds its own ADR naming the classes it changes and citing this one, because
   the protected-path check counts only an ADR added or changed in the same pull request. No build
   changes `constitution/`, `CLAUDE.md`, `config/session-rules.md`, `Makefile`, `pyproject.toml`,
   `skills/`, `.claude-plugin/` or the ruleset files.
5. When this pull request merges, #498 is closed with a pointer to it.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. No check, flow
or setting changes in this pull request, and a project that never turns `auto_merge` on sees no
change from any build. A project that turns it on needs a second GitHub account for its conductor
before anything merges.

## Residual

None beyond SPEC-0039's residual. The intake checks cannot tell whether the criteria, the hold list
or the trust rule are the right ones; that is the review of this pull request.
