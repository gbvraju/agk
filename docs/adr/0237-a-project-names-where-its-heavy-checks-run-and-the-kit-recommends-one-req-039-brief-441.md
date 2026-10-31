# ADR-0237: a project names where its heavy checks run in one setting, and the kit recommends one (REQ-039, brief 441)

- Status: Accepted
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0184, ADR-0215, ADR-0217, ADR-0224
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`

## Context

Brief #441 (#288 part 1). Where a project's checks run is implicit: every workflow says `runs-on: ubuntu-latest`, and local
mode is a guide a person follows by hand. `minutes.py` (ADR-0184, ADR-0215) already reads the repository's visibility, the
plan's included minutes and the minutes used, but nothing turns that reading into a recommendation. The script, its tests,
`common.py`, the templates and the manifest are protected path classes, so this ADR names them. The brief names no
`Measured:` line. The tests were written first (`tests/kit/test_execution.py`: 47 failed at the first checkpoint, feac151).

## Decision

1. **The setting (answer 1).** `agk.toml` gains an optional top-level `execution`, one of `hosted`, `hybrid` (the required
   light checks on GitHub-hosted runners, the heavy checks on a pool or locally), `pool` or `local`. Absent reads `hosted`, so
   nothing changes for a project that does not set it. `common.execution` reads it straight from `agk.toml` (as `lock_slots`
   is read, so `DEFAULT_CONFIG` and its tests are unchanged); any other value, a value that is not a string included, is
   refused with `execution must be one of hosted, hybrid, pool or local (setting: execution)`, naming the setting and never
   the value. Both templates (`kit/templates/agk.toml`, `kit/templates/agk.adopt.toml`) list it commented out,
   `# execution = "hosted"`, after the lock settings of brief #426, which stay.
2. **The command (answer 2).** `scripts/agk/execution.py [--json] [--repo OWNER/REPO] [--api-dir DIR]` (standard library)
   prints `execution: <set> (recommended: <profile>: <reason>)`. It reads through `minutes.py`'s sources (`Gh`, GET only, and
   `ApiDir` for recorded responses) and its reading functions (`repo_of`, `billing`, `reason_of`, and the constants `HALF`
   and `LOCAL_MODE`); it imports no `subprocess` and has no API path of its own. The table, first match wins:
   - Actions disabled for the repository (`/repos/{repo}/actions/permissions` answers `enabled: false`): `local`, with
     `see docs/guides/local-mode.md`. It comes first, since no hosted runner runs then, public or not;
   - a public repository: `hosted` (`a public repository's minutes are not billed`);
   - the billing reading unknown: `hosted`, with the reason class (`the token cannot read billing: refused|missing|
     unreadable`), or, when the plan includes no minutes, `the plan includes no minutes to compare against` (Q-441-2);
   - the included minutes used up (used at least included): `local`, with the local-mode guide;
   - past `minutes_warn`: `hybrid` (`<used> of <included> included minutes used (<n>%), past minutes_warn (<w>%)`);
   - past half (half used included): `hybrid` (`..., past half`);
   - otherwise, more than half left: `hosted` (`..., more than half left`).
   An Actions permission that cannot be read is not taken for a disabled one (Q-441-1). A repository that cannot be read is
   refused (exit 1, `path class: repository`), as in `minutes.py`. `--json` prints the same as one object (`execution`,
   `recommended`, `reason`, `repository`, `private`, `actions_enabled`, `used`, `included`, `warn_percent`, `runner`).
3. **Reports only (answer 3).** It changes no workflow and writes nothing (exit 0 printed, 1 refused, 2 usage). With `pool`
   or `hybrid` set, it reads the repository variable `AGK_HEAVY_RUNNER` (`/repos/{repo}/actions/variables/AGK_HEAVY_RUNNER`);
   when it is not set (404), or cannot be read (with its reason class), a second line says so and points to
   `docs/guides/self-hosted-runner.md`. The variable's value is never printed. With `hosted` or `local` it is not read.
4. **Tests (answer 4).** `tests/kit/test_execution.py`, with saved API responses in `tests/kit/fixtures/execution/private`
   and no network: each row of the table (public; more than half left; exactly half; past half; past `minutes_warn`, also
   one set below half; used up; Actions disabled, also on a public repository; unreadable permissions); each value read, a
   refused value (in `common` and as exit 1), no setting; a token that cannot read billing, missing billing, a plan with no
   included minutes; `pool` and `hybrid` without the variable, with an unreadable one, with it set (value never printed);
   the JSON shape; nothing written; usage errors; no API path of its own; the templates and the manifest.
5. **Kit and flow mode.** `kit/manifest.json` lists `scripts/agk/execution.py` as a verbatim file. One changelog fragment
   of one line, `changelog.d/execution-setting.md`; no version bump; `kit/hashes.json` not edited (session rule 14).
   `docs/guides/reference.md` gains a section "Where checks run" (outside `Touches`: the kit's test of the reference
   requires every installed script to be named there).

## Consequences

- A person sets `execution` once, and `python3 scripts/agk/execution.py` says whether the repository's minutes still suit it.
- Nothing runs elsewhere because of the setting yet: moving the heavy jobs remains the project's own edit, as the
  self-hosted runner guide and local mode describe.
- The recommendation reads the account's billing figures, as `minutes.py` does; a token that cannot read them gets `hosted`
  with that reason, never a guess.

## Residual

- Q-441-1 (2026-10-31): the brief names "Actions disabled for the repository" but no reading for it, and `minutes.py` has
  none. Read conservatively, the command reads `/repos/{repo}/actions/permissions` through `minutes.py`'s sources (the same
  GET path, not a second one), and a permission that cannot be read (refused or missing) is never taken for a disabled one.
- Q-441-2 (2026-10-31): the table does not cover a plan whose billing answers with 0 included minutes. Read conservatively,
  that is an unknown reading (`hosted`, with its own reason), not minutes used up.
- Q-441-3 (2026-10-31): `AGK_HEAVY_RUNNER` may also be set as an organisation variable (the shared pool of brief #410); the
  brief names the repository variable, so only that one is read (verify: whether a pool project sets it per repository).
