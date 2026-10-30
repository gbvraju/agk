# ADR-0182: local mode is a documented way to keep working when GitHub Actions is blocked (REQ-039, brief 322)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0173, ADR-0180
- Requirements: REQ-039

Protected classes: `config/`, `.claude/`, `tests/kit_dev/`

## Context

Brief #322 (priority 1): in a pilot (the field notes of #287 and #283) a private organisation repository used up its Actions
minutes on day 2, and GitHub then refused every job, the router's included. The team invented "local mode" by hand over several
hours: workflows disabled, builders running governance and the project tests locally under a lock, the conductor's own
governance run as the gate, and merges on local evidence recorded on one issue. Nothing in the kit said how to do it safely or
how to come back. The brief names no `Measured:` cause; it asks for a guide and the lines that point to it.

## Decision

1. **The guide (answer 1).** `docs/guides/local-mode.md` has six sections in order: when to use it (minutes exhausted, billing
   blocked, an outage; never because a check is red); how to enter it (one `gh workflow disable <file>` per installed workflow,
   the REST form beside it, and one record issue opened with `gh api`); what a builder runs before asking for review (`make
   governance`, `make test`, `proof.py` and `check_pr_body.py` on its head under a lock directory `agk-heavy.lock` in the git
   directory, taken with `mkdir` and released with `rmdir`, and one `Local evidence:` line in the pull request body that names
   the head); what the conductor checks instead of CI (`review-queue` and its `checks not reported`, governance re-run on the
   head with the bounded run of its role, the builder's line); what is lost (no router labels, no server-side proof, no
   scheduled runs, every merge the person's call, recorded as `Local merge:` on the record issue); how to leave it (one `gh
   workflow enable <file>` per workflow, one pull request green on GitHub, the record issue closed).
2. **Session rule 30 and the conductor role (answer 2).** The session rules gain rule 30, and the conductor role one paragraph
   after its seven steps: both point to the guide and say that a verdict in local mode names, in one `Local evidence:` line, the
   local evidence it relied on. The conductor's seven steps keep their numbers.
3. **The reference and getting started (answer 3).** `reference.md` lists the guide in a section of its own;
   `getting-started.md` links it from `When something goes wrong`, the section that sends a person to the Actions tab.
4. **Tests (answer 4).** `tests/kit_dev/test_local_mode_guide.py` checks each section and its key commands, that every
   `gh workflow` subcommand is `disable`, `enable` or `list`, that every installed workflow (read from `kit/manifest.json`) has
   its disable and enable line, that every kit script, make target and `session.py` subcommand the guide calls exists, and that
   the guide names no vendor beyond GitHub from a fixed list.
5. **Reading Q-322-1 (taken, the conservative one).** The kit has no lock command; the brief asks for "a heavy-step lock file".
   The guide uses a lock directory made with `mkdir`, which is atomic on every system the kit supports and lives in the git
   directory, so it needs no ignore line. A kit command that takes and releases the lock, and removes a stale one, would be its
   own brief.
6. **Reading Q-322-2 (taken, the conservative one).** The ruleset requires the `governance` check, which no longer reports in
   local mode. The guide says that merging while it is missing is the admin's call, pull request by pull request, and gives no
   command that changes or bypasses the ruleset; no session does either.
7. **Reading Q-322-3 (taken, the conservative one).** The secret scan of the governance workflow is not part of `make governance`
   and its scanner is not installed by the kit; the guide asks the builder to run the same scanner when it is installed and to
   write `secret scan: not run` otherwise, never to leave it out silently.
8. **Flow mode.** Fragment `changelog.d/local-mode.md`; no version bump; `kit/hashes.json` is not edited (session rule 14).

## Consequences

- A project whose Actions is blocked keeps building with one page to follow, and every merge in that time is on one issue.
- A verdict in local mode names the evidence it relied on, so a later reader can tell a merge on local evidence from one on CI.
- Pull request #317 (solo mode) appended session rule 29 and merged first; this rule took the next free number, 30
  (`session.py ids`, session rule 15).

## Residual

- 2026-10-30: the lock is a convention, not a command: a session that does not take it can still run heavy steps at the same
  time as another, and a stale lock needs a person (due 2026-12-15).
- 2026-10-30: nothing checks that a pull request merged in local mode has a `Local merge:` comment on the record issue; the
  catch-up run on the default branch after local mode ends is the only server-side check of those merges (due 2026-12-15).
