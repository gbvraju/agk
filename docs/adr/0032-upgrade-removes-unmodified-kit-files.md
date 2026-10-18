# ADR-0032: upgrade deletes unmodified kit files the new kit no longer ships (ADR-0031 residual), and the end-to-end test

- Status: Proposed
- Date: 2026-10-18
- Deciders: maintainers
- Related: ADR-0020, ADR-0026, ADR-0031
- Requirements: REQ-014, REQ-016

Protected classes: `scripts/agk/`, `tests/kit_dev/`

## Context

ADR-0031 moved the installed Go fixture tree under `testdata`. `agk upgrade` installed the new paths but only reported the old ones as
`removed-in-kit` (SPEC-0008 rule 7: "never deleted"), so an adopted Go repository stayed broken until someone deleted the old tree by
hand: the pilot's step 3b. The maintainers ruled the next step (the ADR-0031 residual, due 2026-11-07): upgrade deletes a path the new
kit no longer ships only when its content matches a hash of that path in `kit/hashes.json` history (an unmodified kit file); otherwise
it reports the path and leaves it. This is that change. The same pull request carries the first end-to-end test, which the brief asked
for with this item.

## Decision

1. **`scripts/agk/upgrade.py`**: a path that the row of the installed version lists, the present manifest does not, and the target has,
   is `removed-in-kit` as before. Now:
   - a regular file whose SHA-256 equals a hash that the table lists for that path in any release is deleted:
     `removed-in-kit PATH (unmodified, deleted)`;
   - any other content is kept: `removed-in-kit PATH (modified, kept)`;
   - never deleted, whatever the content: a symlink or a non-file (`(not a regular file, kept)`), a file the row lists but the present
     manifest still ships as an optional file (the experimental reviewer; ADR-0020 decision 3 stays: reported, never deleted;
     `(optional file, kept)`), and, in an adopt target, a path the adopt install leaves to the project (its skip list and marked blocks;
     `(kept: left to the project in adopt mode)`).
   - The candidates are the installed version's row minus the present manifest, as before; the history decides only whether the bytes
     are a kit copy. A path the table never listed is not a kit path and is never touched.
2. **Order and report.** The deletions follow the writes, in sorted path order, then the directories they emptied (never the target
   root); the version line of `agk.toml` stays the last write. The item lines are the same in a dry run and in a real run (SPEC-0008
   rule 14); the summary says `upgraded N files and deleted M; ...` or, in a dry run, `dry run: N files would change, M would be deleted;
   ...`. A deletion in a protected class is named in the printed `Protected classes:` line like a write. An upgrade that only deletes is
   not `nothing to do`; the next run is. An error on a deletion stops the run (exit 3), as an error on a write.
3. **SPEC-0008 is amended** (`docs/runs/proposed-spec-amendments-20.md`, applied here on the maintainers' ruling): rule 7's row, rule 14
   and rule 15.
4. **`tests/kit_dev/test_upgrade.py`**: an unmodified removed file is deleted; a modified one is kept and reported; a copy from any
   release counts; nothing outside the table's paths is touched; a symlink is kept; emptied directories go and others stay; a delete-only
   run; an adopt target; the adopt skip list; the protected classes; the existing rows of rule 7 now expect the deletion.
5. **`tests/kit_dev/test_end_to_end.py`** (the validation brief, item 1 and 2): in `tmp_path`, `init` a fresh repository, add one
   requirement with two criteria and their tests, run `make governance`, the proof, the facts and the report renderer, and assert the
   Proven and Needs-you lines; once with a test that fails without the change (`proven`, "REQ-101 is proven (last change PR #1: proven)")
   and once with a test that passes without it (`not-proven`, carried through the facts into the Proven line); and the same flow in a Go
   layout (`go test ./...` as the project's tests, `*_test.go` markers), skipped only when `go` is not installed. Run against a renderer
   whose Proven wording is changed, two of the three fail. The only stand-ins are the project's test command and the pull request record
   that GitHub would supply, written into the facts document as the recorded API files are in the facts fixtures.
6. **No kit version change.** `upgrade.py` and the tests are kit-only: no installed file and no hash changes.
   `docs/runs/pilot-upgrade-brief.md` drops step 3b (below).

## The live proof (2026-10-18)

A throwaway Go module (Go 1.24.7, `go mod init x`, one passing test, committed, `refs/remotes/origin/HEAD` set), adopted with the kit as
merged for 0.16.0 (commit `dc2ab4d`); there `go test -count=1 ./...` printed three `[setup failed]` lines (the pilot's report). Then,
with this branch (kit 0.16.1), with no manual step:

```
$ python3 scripts/agk/upgrade.py <module> --dry-run
removed-in-kit tests/kit/fixtures/facts/go-style/tree/.claude/settings.json (unmodified, deleted)
... (16 lines in all, every one of them under tests/kit/fixtures/facts/go-style/tree/)
dry run: 18 files would change, 16 would be deleted; the version line of agk.toml would be set to 0.16.1; nothing was written
$ python3 scripts/agk/upgrade.py <module>
upgraded 18 files and deleted 16; the version line of agk.toml is set to 0.16.1
$ go test -count=1 ./...
ok  	x	0.002s
exit=0
$ ls tests/kit/fixtures/facts/go-style/
api  case.json  facts.json  testdata
$ python3 scripts/agk/upgrade.py <module>
nothing to do
```

`git status` in the module showed 16 deletions, 2 modified files and 2 untracked; the zero-product-file script of the pilot brief (every
changed path is a kit path or the old go-style tree) printed `35 paths changed; 0 are not kit files`.

## Consequences

- From a kit checkout that has this change, no manual step is needed for the Go fixtures. A checkout without it prints a summary with no
  `deleted` and leaves the old tree; the pilot brief says to update the checkout then.
- Every future move or removal of an installed file is cleaned up by the next upgrade, unless the target edited the file.
- Deleting a protected file in a target (for example under `tests/kit/`) needs the same ADR in the target's pull request as writing one;
  the printed skeleton names the class.

## Questions

| Q | Question | Reading taken (conservative) |
| --- | --- | --- |
| Q-K4-152 | The change touches `upgrade.py`, which is kit-only; does the kit version move? | no: no installed file or hash changes; the marker for the pilot is the `deleted N` in the summary of the kit checkout's upgrade |
| Q-K4-153 | "A hash of that path in the history": the installed row only, or every release? | every release row that lists the path (a copy the kit ever shipped is unmodified); the candidates stay the installed row's paths |
| Q-K4-154 | Optional files and adopt-mode project paths are in the rows but are not "no longer shipped". | kept, with a reason; ADR-0020 decision 3 is unchanged |
| Q-K4-155 | The dry run and the real run print the same item lines (SPEC-0008 rule 14). | the line says `(unmodified, deleted)` in both; the dry run's summary says `would be deleted` |
| Q-K4-156 | The version-line text of the summary when the version does not change. | `the version line is unchanged` (the old text claimed a set that did not happen) |
| Q-K4-157 | The end-to-end test needs a pull request record. | it is written into the facts document by the test (a stand-in for the recorded API files); every stage is the real script |

## Residual

- 2026-10-18: a modified removed file is reported only by the run that upgrades from the version whose row lists it; later runs
  from the new version do not repeat the line (the row of the installed version no longer lists it); this is the old behaviour and is
  not changed here (due 2026-12-31).
- 2026-10-18: the end-to-end test does not yet cover intake and the playbook (they are not built); extend it as they land
  (due 2026-11-30).
