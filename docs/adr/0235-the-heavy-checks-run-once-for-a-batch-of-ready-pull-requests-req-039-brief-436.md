# ADR-0235: the heavy checks run once for a batch of ready pull requests, and per pull request only on failure (REQ-039, brief 436)

- Status: Accepted
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0191, ADR-0208, ADR-0217, ADR-0224
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`

## Context

When several pull requests are ready, each one runs the project's heavy checks on its own head, so a batch of five costs five
heavy runs. A merge queue would run them once for the batch on GitHub, but whether it is available depends on the plan and the
visibility, and turning it on is a repository setting, a person's decision (#288 part 6). Brief #436 gives the kit's own
fallback, which the steward (#286) can later call; its dependence, the local run record of brief #374 (ADR-0208), has merged.

## Decision

1. **The command (answer 1).** `scripts/agk/batch.py PR [PR...] [--command CMD] [--base REF] [--json] [--record FILE]` fetches
   each head with git alone (`git fetch origin refs/pull/<n>/head`), makes a detached worktree of the base in a new temporary
   folder, and merges the heads into it in the given order (`git merge --no-ff`, with a fixed committer identity of its own). A
   head that does not merge cleanly is aborted and left out as `conflict`; a head that cannot be fetched is left out as
   `not-fetched` (Q-436-3); the rest go on. The base is the one every kit check uses (`--base`, `AGK_BASE`, then the default
   branch as `origin/<default_branch>`), and a base that does not resolve exits 2 naming those settings. A pull request number
   is a positive whole number, given once.
2. **One heavy run, then per pull request (answer 2).** CMD (default `make -f agk.mk agk-project-test`) is split as a shell
   would split it and run without a shell in the worktree's root, once, under the heavy-step lock (`lock.py`, name `heavy`,
   taken as `prepush.py` takes it, so a caller that already holds it through `lock.py run` is not made to wait for itself). When
   it passes, each included pull request is reported `batch-green <sha12>`, the first twelve characters of the pull request's
   own head, which is what a verdict names (Q-436-1). When it fails, the worktree is reset to the base and CMD runs on each
   included head merged alone onto the base, still under the same lock; each is `green` or `red`, and a red run's output is
   printed. With one included pull request the batch run is already its own run, so it is not run again (Q-436-2). A command
   that cannot start is a red run (exit 127). The output prints one line per pull request in the given order, `#<n> <status>
   <sha12|->`, after the run lines; `--json` prints one object instead (`base`, `batch`, `pulls`) and sends the lock's lines to
   stderr. When the batch run fails but no pull request is red on its own (they pass alone but fail together), the command
   prints `batch: #<a>, #<b> pass alone but fail together` and none of them counts as green: merging them all would break the
   default branch (verdict on f3d89dd, item 1); `--json` marks it `together: "FAIL"`. Exit 0 when every pull request is green
   and the batch did not fail together, 1 when any is red, `conflict` or `not-fetched` or when they fail together, 2 for a usage
   error or an unresolved base, 3 when the lock folder cannot be written.
3. **It only reports (answer 3).** It labels, merges and posts nothing, changes no branch, ref or file of the checkout, and
   calls no network but `git fetch`. The worktree and its temporary folder are removed when the run ends, also after a failure
   or an interrupt. `--record FILE` writes a record in the schema of brief #374: `schema: 1`, `kind: "batch"`, `head` (the batch
   merge commit), `base`, `started`, `tree_clean` (of the checkout it was started in), `versions`, and one step per run
   (`batch`, then `pr-<n>`) with the fields of ADR-0208 (`argv` scrubbed the same way, `cwd` `.` for the worktree's root), plus
   `pulls` (number, head, status), `not_run` and `result`. It holds no output text, no environment value and no path outside the
   repository. It then prints `Evidence: batch schema 1, head <sha12>, <n> steps ok, record <sha12 of the file>`. When nothing
   merged, the record's `head` is `null` and the line's head is `-`, so the two agree (verdict on f3d89dd, item 2); `result` is
   `failed` whenever the exit is 1.
4. **The guide (answer 4).** `docs/guides/self-hosted-runner.md` gains a section saying when a batch run on the pool or a local
   machine replaces the per-pull-request heavy runs: several ready pull requests, the kit's governance and proof still per pull
   request on GitHub-hosted runners, and a person's decision whether a batch result stands in for a required check.
5. **The manifest.** `scripts/agk/batch.py` is a verbatim kit file, listed in `kit/manifest.json`; the release file
   `kit/hashes.json` is left to the release (session rule 14).
6. **Tests first (answer 5).** `tests/kit/test_batch.py` builds a clone of a bare repository whose `refs/pull/<n>/head` stand in
   for GitHub's, and covers three pull requests green together in one run, one red among three found by the per-pull-request
   runs, pull requests that pass alone but fail together, a conflict left out, a single pull request, the worktree removed after
   a failure, the default command, an unfetchable head, `--json`, `--record` (and its head when nothing merged), usage errors,
   an unresolved base, and that it changes nothing.

## Consequences

A batch of ready pull requests costs one heavy run when it is green, and one more per pull request when it is red. The result is
evidence for a person or the steward; it sets no label and replaces no required check by itself. A merge queue on GitHub, where a
person turns it on, does the same job inside GitHub and makes this command unnecessary there.

## Residual

- 2026-10-31: Q-436-1 (the sha of `batch-green` is the pull request's head, the batch commit is in the record), Q-436-2 (a single
  pull request is not run twice) and Q-436-3 (a head that cannot be fetched is left out like a conflict) are read conservatively.
- 2026-10-31: CMD has no time limit of its own; the heavy-step lock's stale limit applies. Whether a batch run takes
  `proof_timeout` is a later brief.
