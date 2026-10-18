# ADR-0031: installed fixtures are invisible to a project's own test runners, kit 0.16.1

- Status: Proposed
- Date: 2026-10-18
- Deciders: maintainers
- Related: ADR-0008, ADR-0023
- Requirements: REQ-010

Protected classes: `tests/kit/`, `kit/`, `.claude-plugin/`

## Context

The pilot found a kit defect. The installed fixture tree `tests/kit/fixtures/facts/go-style/tree/` holds deliberately malformed Go test
files (`pkg/bar_test.go` with the wrong signature, and empty `node_modules/x/y_test.go` and `vendor/dep_test.go`). In an adopted Go
repository, `go test ./...` compiles them and fails: adoption broke the product's own tests, which REQ-010 AC1 ("no product file
modified") exists to prevent and which the zero-touch rule of ADR-0008 promises.

Reproduced here in a throwaway Go module (Go 1.24.7, `go mod init x`, one passing test, committed, `refs/remotes/origin/HEAD` set),
adopting from the kit at 0.16.0 (`main` after the merge of the product report live record). Before adopting, `go test ./...` printed
`ok  	x	0.003s`. After adopting, `go test -count=1 ./...` exited 1 (the module path of the throwaway directory is shown as `<module>`):

```
# x/tests/kit/fixtures/facts/go-style/tree/node_modules/x
tests/kit/fixtures/facts/go-style/tree/node_modules/x/y_test.go:1:16: expected 'package', found 'EOF'
FAIL	x/tests/kit/fixtures/facts/go-style/tree/node_modules/x [setup failed]
# x/tests/kit/fixtures/facts/go-style/tree/pkg
<module>/tests/kit/fixtures/facts/go-style/tree/pkg/bar_test.go:3:1: wrong signature for TestBar, must be: func TestBar(t *testing.T)
FAIL	x/tests/kit/fixtures/facts/go-style/tree/pkg [setup failed]
# x/tests/kit/fixtures/facts/go-style/tree/vendor
tests/kit/fixtures/facts/go-style/tree/vendor/dep_test.go:1:16: expected 'package', found 'EOF'
FAIL	x/tests/kit/fixtures/facts/go-style/tree/vendor [setup failed]
ok  	x	0.002s
FAIL
```

That is the pilot's report, line for line.

## Decision

1. **The `go-style` case's tree moves to `tests/kit/fixtures/facts/go-style/testdata/tree/`.** The go tool does not descend into a
   directory named `testdata`, so none of the Go files there is a package of the product. `test_facts.py` finds a case's tree by one
   helper, `tree_of`, which looks under `testdata/` first; it copies the tree to a temporary repository, so every path the facts
   engine sees is the same as before. The `go-style` golden `facts.json` is unchanged, byte for byte, and so is the test that asserts
   its markers (`pkg/bar_test.go`, `pkg/foo_test.go`). Only the fixture's own path changed. No other installed fixture holds a file
   a toolchain could discover (below), so no other tree moves.
2. **A deterministic kit test, `tests/kit/test_fixture_discovery.py`** (installed, so a target can run it): no file under
   `tests/kit/fixtures` ends in `.go` unless a path segment is `testdata`; no file there is named as a Python test (`test*.py`,
   `*_test.py`) or a JavaScript test (`*.test.*`, `*.spec.*` with a script extension, or under `__tests__`) unless below `testdata`;
   the Go fixtures still exist (the rule is not vacuous); and, where `go` is on `PATH`, `go test ./...` over a module that holds a
   copy of the fixtures passes offline. Run on the old layout, the first, third and fourth tests fail (the same three directories as
   above), which is the red.
3. **Kit 0.16.1**: manifest (the moved paths and the new test), hashes, plugin version.
4. **Which default test discovery could see installed fixtures today, and why each is safe:**

   | Language, runner | What its default discovery finds | Fixtures that match | Why safe |
   | --- | --- | --- | --- |
   | Go, `go test ./...` | every `*_test.go` in every package directory except those named `testdata` or starting with `.` or `_` (it does not skip `vendor` or `node_modules` in module mode when they are inside the module) | only the four `*_test.go` of the `go-style` case | they are below `testdata`; the kit test and the live proof below |
   | Python, `pytest` and `unittest` | `test*.py` and `*_test.py` (pytest, `python_files`), `test*.py` (unittest) | none: the fixtures that carry markers are named `probe_*.py`, and the rest are not tests | no name matches; `tests/kit/conftest.py` also ignores everything under `tests/kit` unless the kit's own targets set `AGK_KIT_TESTS` |
   | JavaScript and TypeScript, `jest`, `vitest`, `mocha` | `*.test.*`, `*.spec.*`, files under `__tests__` | none: there is no script file in any fixture | no file of that kind exists; the kit test fails if one is added |

   Other toolchains (Rust `cargo test` over `tests/*.rs`, Java under `src/test`, Ruby `spec/`) find nothing: no fixture has such a
   file or such a layout. The kit test does not cover them yet (residual).

## The live proof (2026-10-18)

A second throwaway module made the same way (Go 1.24.7, one passing test, `refs/remotes/origin/HEAD` set). `python3
scripts/agk/adopt.py <module>` from this branch (kit 0.16.1) installed the kit; then, in the module:

```
$ go test -count=1 ./...
ok  	x	0.002s
exit=0
```

The only `.go` files below the module root afterwards are the module's own `one_test.go` and four under
`tests/kit/fixtures/facts/go-style/testdata/tree/`. With the control (the kit at 0.16.0 in an identical module) `go test` exited 1
with the output in the Context.

## Consequences

- An adopted repository that is not Go loses nothing and gains nothing. An adopted Go repository that holds 0.16.0 or earlier has the
  old files at the old paths. `agk upgrade` installs the new paths and lists each old path as `removed-in-kit`; it never deletes a
  file (SPEC-0008). Shown on the control module of the live proof: after `upgrade.py` to 0.16.1 (`upgraded 18 files; the version line
  of agk.toml is set to 0.16.1`), `go test -count=1 ./...` still printed three `[setup failed]` lines; after `rm -rf
  tests/kit/fixtures/facts/go-style/tree` it printed `ok  	x	0.002s` and exited 0. **The pilot needs that one deletion, in its own
  change, after the upgrade**; the pilot brief step for it is step 3b of `docs/runs/pilot-upgrade-brief.md`
  (added by this pull request).
- Every fixture added from now on is checked by the same test, so the same defect cannot come back for the three languages.

## Questions

| Q | Question | Reading taken (conservative) |
| --- | --- | --- |
| Q-K4-148 | Move only the Go files, or the whole tree? | the whole `go-style` tree moves, so the facts engine still sees one repository and its other files (`docs/`, `agk.toml`) stay with the Go files; the golden does not change |
| Q-K4-149 | The brief asks for a rule about `.go` only. | the test also rejects Python and JavaScript test names outside `testdata`, because the ADR claims those two are safe and a claim without a test is a guess |
| Q-K4-150 | The Go check needs a Go toolchain. | it runs where `go` is on `PATH` and is skipped elsewhere; the live proof above is the record that it ran, on Go 1.24.7 |
| Q-K4-151 | What upgrade does with the paths the new kit no longer lists. | nothing new: it lists them as `removed-in-kit` and never deletes; the pilot deletes the old go-style tree itself (Consequences) |

## Residual

- 2026-10-18: the discovery test covers Go, Python and JavaScript names only; extend it when a fixture in another language
  (Rust, Java, Ruby) is added (due 2026-11-30).
- 2026-10-18: upgrade leaves the old go-style tree in place in every repository that adopted 0.16.0 or earlier, and the Go ones fail
  until it is deleted by hand; whether upgrade should offer to remove `removed-in-kit` fixture paths is the maintainers' ruling (due 2026-10-31).
