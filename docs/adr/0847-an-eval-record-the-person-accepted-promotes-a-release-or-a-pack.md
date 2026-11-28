# ADR-0847: An eval record the person accepted promotes a release or a pack

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2043, 2026-11-27T13:18:08Z)
- Related: ADR-0837, ADR-0846, ADR-0096, ADR-0430, SPEC-0077, SPEC-0028, SPEC-0047, SPEC-0048, SPEC-0062, REQ-084, brief #2043, brief #2042, plan #661
- Requirements: REQ-084

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`, `config/`

## Context

SPEC-0077 (Approved, ADR-0837) rule 10 lets a pack become `curated`, a kit release be cut and a tier's model mapping
change only with an eval record `docs/runs/evals/<date>.md` whose medians are no worse than the last accepted record's
beyond `tolerance` of `evals/rubric.toml`, accepted with the owner's one plain yes; the scorecard gains one line. Rule 14
build (h) builds it, after build (g) (brief #2042, ADR-0846), which gave `evals/`, the rubric and `eval_run.py`'s run
records. On main at 6aad1e8 neither `docs/runs/evals/` nor a reader of it existed.

## Decision

1. **The record.** New kit-only `scripts/agk/eval_record.py write --runs DIR [--date]` reads build (g)'s run records
   (checked by `eval_run.median`'s rules first) and writes `docs/runs/evals/<date>.md`: `- Status: proposed`, `- Kit:`,
   `- Rubric:` (the SHA-256 of `evals/rubric.toml`), `- Tolerance:`, `- Cost per accepted feature:`, `- Compared with:`,
   `- Regressions:` and one table `| product | layer | run 1 | run 2 | run 3 | median |` with the eight layers and the
   objective, process and cost figures of the runs. An incomplete run shows its stage and is never 0; a product with
   fewer than three complete runs is a regression line `<product> incomplete <stage>` (`Q-PH-2`). It never overwrites,
   and a line the data guard flags refuses the write naming the path class.
2. **The comparison.** `compare(new, last, tolerance)`: a median below the last accepted one by more than `tolerance`
   (higher is better) is `<product> <layer> <median> (was <median>, tolerance <n>)`; a product or layer of the last
   record missing from the new is `<product> <layer> missing`; with no accepted record there is no comparison. Cost is
   stated, never compared (`Q-PH-3`). A `tolerance` missing, a `bool`, not a number or outside 0 to 6 is refused
   `refused: evals/rubric.toml (setting: tolerance)`.
3. **The acceptance.** `accept <date> --said FILE --at <time> [--by]` asks `steward_owner.yes_of` (team on: a
   `spec_approvers` login; a supervisor-started session refused by `AGK_STEWARD_START`) and `steward_voice.is_yes`; only
   on a yes it records one `Setup` entry through `steward.record` (the sidecar's file with `forge = "files"`) and sets
   `- Status: accepted` with one `- Accepted:` line. Any other reply prints `eval-record <date>: not accepted` and changes
   no file. A record with a regression, one already accepted, or one whose rubric hash differs from today's is refused
   (`Q-PH-4`).
4. **The one reader.** `eval_record.accepted(root, ref=None, path=None)` is the newest well-formed record with
   `- Status: accepted`, an `- Accepted:` line and `- Regressions: none`; `applies(root, ref)` is whether the tree holds
   `evals/rubric.toml`. (a) `check_release.check`, after its rule 5 checks and only where the merge base holds
   `evals/rubric.toml`, fails `SPEC-0077 rule 10: a release pull request needs an accepted eval record (path class
   docs/runs/evals/)` unless the base holds an accepted record dated on or after the base's newest release heading, and
   fails closed naming `CHANGELOG.md` when no heading reads (`Q-PH-1`); strict mode and a base without `evals/` check as
   before, no workflow changes, and `valid_release` carries it. (b) `check_packs.problems(folder, root)`, only where
   `evals/rubric.toml` exists, adds `rule 10: <label>: a curated pack needs an accepted eval record (key: evals)` for a
   `curated` manifest whose `evals` names no accepted record (`Q-PH-5`). (c) A tier's mapping, `config.MODEL_DEFAULTS`,
   reaches a project only by a release, so (a) gates it (`Q-PH-6`). (d) `scorecard.scorecard` appends one note,
   `evals: <date> accepted, medians ...; cost per accepted feature ...` or `evals: no accepted record`, only where the
   kit-only script and `evals/rubric.toml` exist; a project's output is unchanged (`Q-PH-7`). It is a note, never a metric.
5. **Kit-only and closed.** `eval_record.py` is in `KIT_ONLY` of the manifest test and refuses outside the kit (path class
   `evals/`). Its importers mark the function-level import `kit-only`. A test asserts no other kit script names
   `docs/runs/evals` or writes `Status: accepted`, and that the three readers call `eval_record.accepted(`. The class test
   of build (g) (`test_eval_run.py`) now also exempts `eval_record.py`, rule 10's reader of `evals/`.
6. **Parity** (`Q-2043-1`, the maintainers' answer "a and b" on #2078, 2026-11-28). `parity.imports_of` skips a
   function-level import whose line carries the word `kit-only` (not the file name `config/kit-only.txt` alone), the
   mark `tests/kit/test_installed_imports.py` already reads: such an import is guarded and absent from an installed
   copy, so it reaches no project. `scripts/agk/eval_record.py` joins `config/kit-only.txt`, and the ceiling in
   `tests/kit/test_parity.py` rises from 12 (ADR-0852) to 13, as ADR-0846 raised it: rule 10 makes the record
   kit-only.
7. **Wiring.** A `[[testing.map]]` entry for `eval_record.py`; the entries of `check_release.py`, `check_packs.py`,
   `scorecard.py` and `eval_run.py` gain the new tests; the reference guide lists both commands.

## Consequences

The first kit release after this merges fails until a record is written by `eval_run.py run` and `write` and accepted by
the owner, as rule 10 says. A project's release, pack and scorecard results do not change.

## Residual

Who wrote the `- Accepted:` line cannot be told by a file check (`Q-PH-8`); the record lands in a pull request the owner
reviews. The first real record is its own pull request (`Q-PH-9`). Build (j) ships the first curated packs on (b)
(2026-11-27).
