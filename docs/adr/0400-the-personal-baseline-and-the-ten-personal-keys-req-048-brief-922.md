# ADR-0400: The personal baseline and the checks of the ten personal keys

- Status: Proposed
- Date: 2026-11-09
- Deciders: maintainers
- Related: ADR-0267, ADR-0399, SPEC-0041, brief #922
- Requirements: REQ-048

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

SPEC-0041 rule 16 has the developer record once which tests already fail before AGK is used, so that the floor of
rule 18 can later tell an old failure from a new one. Rule 18 also lists the ten keys of the `[personal]` table with
the type and range of each, and says that no key and no value weakens the floor. `common.personal_table` knew the ten
names but checked only `forge`, `level` and `ai_disclosure`, so a `test_command` of spaces, which would skip the
no-regression step, read as valid. ADR-0267 asks each build of the spec for its own ADR naming its classes; this is
build (h), first part.

## Decision

1. `scripts/agk/personal.py` (new, installed) has one command, `baseline`. It finds the test command in
   `[personal] test_command`, else in the one test command the survey's `cache/inventory.json` declares, else it
   refuses naming `personal.test_command`; several different declared commands are refused the same way.
2. Without `--approve` it prints the command and runs nothing. With `--approve` it writes the clone's head tree with
   `git archive` into the sidecar's `cache/trees/<head>/`, runs the command there once, without a shell, and writes
   `records/baseline.json`: `head`, `command`, `per_test`, `run` (`passed` or `failed`) and `failing`.
3. With `{junit}` in the command, it is replaced by a report path under the sidecar's `cache/`, and `failing` lists
   the id (`file::name`, the classname where a case has no `file`) of each test case with a failure or an error, sorted. Without it, `failing` is null and
   `run` alone records the whole run (`Q-S0041-19`). A report that cannot be read is refused, naming the placeholder.
4. `common.personal_table` checks each of the ten keys by its type and range, as rule 18 lists them; a boolean is
   never taken for a whole number. A wrong type, a value out of range, a `test_command` that is empty or only spaces
   and an unknown key are refused naming the key, never the value. A repository without the table reads as today.
5. This build runs no floor and changes neither `prepush.py` nor `proof.py`; no key and no value removes, skips or
   weakens a floor step (principle 11).

## Consequences

A sidecar now holds the head and the failures the later floor compares with, and a setting that would make the
no-regression step vacuous is refused before anything reads it. The clone and its `.git/` are unchanged by a run:
git only reads the object store, and the command runs in the archived tree.

## Residual

- 2026-11-09: the skill's use of `--approve`, after the person says yes, is a later build.
- 2026-11-09: the run has no time limit; a command that never ends holds the terminal until the person stops it.
- 2026-11-09: the command is split with POSIX shell rules (`shlex`), so shell syntax such as `&&` or a pipe is not
  run as a shell would; a project that needs one names a script.
