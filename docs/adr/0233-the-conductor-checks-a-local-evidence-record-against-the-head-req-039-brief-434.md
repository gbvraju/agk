# ADR-0233: the conductor checks a local evidence record against the head and re-runs a sample of it (REQ-039, brief 434)

- Status: Accepted
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0182, ADR-0186, ADR-0191, ADR-0208
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`

## Context

Brief #434 (#288 part 3). In the pilot's local mode the conductor re-ran governance by hand in a scratch worktree
(`docs/guides/local-mode.md`, "What the conductor checks instead of CI"), and its answer rested on what the builder pasted.
Brief #374 (ADR-0208) gave `prepush.py --record FILE`, a JSON record of what ran on which head. This decision makes one
command that checks that record against the head and re-runs part of it, so the answer does not depend on the builder. The
script, its tests and the kit manifest are protected path classes, so this ADR names them. The tests were written first
(`tests/kit/test_evidence.py`: 30 failed, 1 passed at the first checkpoint).

## Decision

1. **The command (answer 1; verdict on 57c122a, item 2).** `scripts/agk/evidence.py check RECORD [--head SHA] [--sample N]
   [--json]`. A record whose `schema` is not 1, or whose `head`, `base` (40 hex), `tree_clean` (a boolean), `result`
   (`passed` or `failed`) or `steps` (each with `name`, `outcome` (`ok`, `FAIL` or `skipped`), `argv`, `cwd`, `exit`,
   `output_sha256`, and `runs` of `name`, `command`, `cwd`, `exit` where present) are not as schema 1 writes them, is
   refused with exit 2, naming the field, never its value. It reports, in this order and each on its own line, `stale` when
   the record's `head` is not SHA (by default the current `HEAD`), `dirty` when `tree_clean` is false, and `failed` for each
   recorded step whose `exit` is neither 0 nor null or whose `outcome` is `FAIL` (prepush records some FAIL steps with no
   exit, or with the exit 0 of a command a refusal followed), for each run of the tests step whose `exit` is not 0 (null
   there is a timeout), and when `result` is not `passed`. Any of these is a difference, and nothing is re-run.
2. **The re-run never executes the record (answer 2; verdict on 57c122a, items 1 and 3).** Otherwise it makes a new
   temporary folder, adds a detached worktree of the head in it, runs `make -f agk.mk agk-governance` there with
   `AGK_BASE` set to the record's `base` (as prepush ran it), and rebuilds from the head what prepush runs: `pr-body`
   (`check_pr_body.py --draft false <body>`), `lint` (`make lint`), `governance`, `secret-scan` (gitleaks over merge base
   to head) and `tests` (`test_plan.py --json --base <merge base> --head HEAD`), and the test runs from that plan run in the
   worktree, with the regression set of `impact.py` where the head has a `[testing]` table, matched to the recorded runs by
   set and name. A recorded step or run whose name is not one of these, or whose argv, command (scrubbed as prepush scrubs
   it) or folder is not the rebuilt one, is reported as `not what prepush runs: <name> (field: name|argv|command|cwd)`, a
   difference, and never run. N rebuilt units (default 1) are re-run: an argv without a shell, a test run through `sh -c`
   with the project's `proof_timeout`. A kit script is the worktree's, or this kit's when the head has none. A body file
   outside the repository, or a gitleaks not installed on the conductor's machine, cannot be repeated: the unit is listed
   `not repeatable` and never sampled. Governance is always re-run, so it is not a sampled unit. Every command, governance
   and the plan run included, runs in its own process group; on a timeout, a signal or any error its whole tree is killed
   (`proof.kill_tree`) before the lock is released and the worktree removed. The worktree and the folder are removed in a
   `finally` and git's note of the worktree is pruned.
3. **The sample (answer 2).** The units are ordered by the sha256 of `<head sha>:<unit name>` and the first N taken; the
   same head always gives the same sample, the record's order does not matter and no random generator or Python version
   enters. It compares exit codes; a different output digest is printed as a note and never makes the record differ.
4. **The lock (answer 3).** Governance and the re-runs hold the heavy-step lock (`lock.py`, name `heavy`), taken with
   prepush's own `take_lock`, so a caller that already holds it (`lock.py run --name heavy -- evidence.py ...`) does not
   wait for itself, and it is released in the same `finally`.
5. **The answer (answer 4).** One `evidence: ...` line per finding, governance's own output when it fails, then one line to
   quote: `Evidence check: agrees|differs, head <sha12>, record <sha12 of the file>, governance ok|FAIL|not run, sample <k>
   of <m> same exit`. The record digest is the one of the builder's `Evidence:` line. `--json` prints one object (`result`,
   `head`, `record_sha256`, `problems` (with the `not what prepush runs` lines), `governance`, `sample` with `name`,
   `recorded_exit`, `exit`, `same_exit`, `same_output`, and `notes`). Exit 0 agrees, 1 differs, 2 a usage error, a bad
   record or a head that does not resolve, 3 an I/O error (a record that cannot be read, a temporary folder or worktree
   that cannot be made, make not installed). It posts nothing and makes no network call.
6. **The guide (answer 5).** `docs/guides/local-mode.md`: a builder adds `prepush.py --record` under the lock to its lines
   and puts the `Evidence:` line in the body beside its `Local evidence:` line; the conductor runs `evidence.py check` and
   quotes its line in the verdict's `Local evidence:` line. The hand-made worktree run stays as the way for a record-less
   builder. The lines the guide's existing tests read are kept.
7. **Outside `Touches:`.** `docs/guides/reference.md` names `evidence.py check` under Local mode, since every installed
   script is named there (`tests/kit_dev/test_reference_commands.py`). `kit/manifest.json` lists `scripts/agk/evidence.py`
   as installed verbatim. Flow mode: fragment `changelog.d/evidence-check.md`; no version bump.

## Consequences

- A clearing verdict in local mode can rest on a command the conductor ran on the exact head, not on pasted text.
- One sampled step per head keeps the check short; a conductor that doubts a record asks for more with `--sample N`.
- The conductor runs only commands rebuilt from the head it reviews, in a worktree of that head, as it already runs that
  head's governance; a record can name what ran, never what the conductor runs.
- A prepush that changes how it builds a step must change `evidence.py` with it, or its records are reported as `not what
  prepush runs`.

## Residual

- 2026-10-31: the record is still unsigned (ADR-0208); a hand-written record that names a head and agrees on a re-run passes
  the sampled steps it was not checked on (due 2026-12-31).
- 2026-10-31: session rule 30 still names only the `Local evidence:` line; pointing it at the record is a maintainers'
  change to a protected file (due 2026-12-31).
