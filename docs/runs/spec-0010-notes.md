# Notes on SPEC-0010 (proof checks)

Date: 2026-10-16 (from `date -u`). Overnight brief 3, item B. The spec was written Draft and set **Approved** on the maintainers'
rulings of 2026-10-16 (final commit of the pull request); nothing is implemented and no protected path is changed by this pull request. It is the second of the five K4 specs of ADR-0021 (decision 2) and serves exit
criteria b and c. Every question below was raised with a conservative reading and has been ruled (section Rulings); none is open.

## What exists today (read on 2026-10-16, on `main` at 94a807d)

- **The requirement rule.** `check_requirements.py` fails a `done` requirement with no `REQ-nnn` token in the test files. It does not
  know `ACn`. `common.find_markers` returns file names only.
- **Acceptance lines.** All 20 `- Acceptance:` lines have the form `AC1 …; AC2 …`; no `done` requirement is unstructured. The
  requirement template installed into targets (`kit/templates/requirements.md`) has three requirements, all `planned`, so a fresh
  target has no `done` requirement to fail; a target's own `done` requirements are unknown until it is checked.
- **Markers.** 543 `REQ-nnn ACn` markers in 34 files under `tests/`; 542 name one requirement, 1 names two.
- **The list the brief asked for (read-only parse).** Statuses: 2 `done`, 1 `in-progress`, 17 `planned`. Both `done` requirements
  comply: REQ-001 has markers for AC1, AC2 and AC3; REQ-003 for AC1, AC2 and AC3. Criteria with no marker today, all of requirements that
  are not `done`: REQ-005 AC3, REQ-008 AC1, REQ-013 AC4, and every criterion of REQ-015 to REQ-020 (they are `planned` and nothing is built).
  So criterion b's clause "this repository's own `done` requirements all comply" is true today, and the check must keep it true: setting
  REQ-005, REQ-008 or REQ-013 `done` would fail it until the three markers exist. (An exact re-run is part of the implementation.)
- **The workflow.** `governance.yml` runs one step per check and a "Project tests" step (`make agk-project-test`, which reads
  `project_tests`). This repository's `project_tests` is `python3 -m pytest tests -q --ignore=tests/kit_dev; ...`. There is no job that
  runs tests on a base commit.
- **The body line.** `check_pr_body.py` requires `Advances:` and a dated `Build-state row:` and ignores every other line. `Issue:` was
  added to the template as optional by SPEC-0005.
- **The pilot.** The shortlist is in the pull request that opened K4; the leading candidate is a Go module with one command,
  `go test ./...`, and no third-party dependency in its root module. This repository never names the pilot.

## Decisions taken in the draft (each is a numbered rule)

- (a) is a rule inside `check_requirements`, not a new script, because the check already exists and fails the same way (rules 1, 2).
  It reuses the SPEC-0009 parsers, so the facts and the check can never disagree about what a criterion or a marker is.
- (a) ships as `warn` and is switched to `block` by an ADR, per the brief. The switch is a key in `agk.toml`, which is a protected
  path, so loosening it later needs an ADR (rule 5).
- (b) is one new script, `proof.py`, kept out of `make governance` (it runs the tests twice) and run by a CI job of its own that
  is not a required check in K4 (rules 7, 16).
- "Placed onto the base" is a copy of the changed test files over a detached `git worktree` of the base, with deletions applied
  (rule 10; the draft used `git archive`, changed by the ruling on Q-K4-25). The head is run from its own export, not from ROOT (rule 11).
- Four outcomes, one precedence order, exit 0 only for `proven` and `skipped`, `unknown` is exit 4 and never `ok` (rules 12, 13).
- A compile or import failure on the base is red in every language, as ADR-0021 decision 2 says (rule 11); the spec states plainly
  what that does and does not prove (rule 14).
- The outcome reaches the facts through step conclusions of the `proof` job, so no write permission and no comment are needed
  (rule 17).

## Options compared

| Question | Option taken | Not taken, and why |
| --- | --- | --- |
| Where rule (a) lives | inside `check_requirements` with a `warn`/`block` switch | a new check script (a second reader of the same file); an immediate block (existing targets would fail on their first upgrade) |
| Base with the tests | a detached `git worktree` of the base plus the test files (ruling on Q-K4-25; it keeps `.git`, so a test that runs `git` sees a repository; it writes and removes administrative entries under ROOT's `.git/worktrees`) | `git archive` (no `.git`, so a test that runs `git` is a false red: the draft's choice, changed); stashing in ROOT (touches the work tree) |
| Which files are "tests" | `test_dirs` and `test_patterns` only | any file with "test" in its path (language-dependent guessing); the diff of the pull request minus non-test code (needs a language) |
| Head run | a detached worktree of the head | ROOT itself (a dirty tree would change the answer) |
| Result transport | the step conclusions of the `proof` job | a `Proof:` comment (needs `pull-requests: write` in a job that runs the pull request's code, or a second job); an artifact (more API calls); a check-run output title (needs `checks: write`) |
| Required check | no, in K4 | required from the start (a false flag would block merges before the false-flag record exists) |
| Escape hatch | `Behaviour: unchanged`, counted | a label (not in the repository); a per-path allow-list (a second configuration to keep right) |
| Mutation testing | not in K4 | it would prove more; it needs a per-language tool, which breaks "language-agnostic by construction" |

## Questions raised (all ruled; see Rulings)

| Q | Question | Reading taken in the spec |
| --- | --- | --- |
| Q-K4-20 | Does rule (a) ship as `warn` and switch to `block`, or block at once? | a key `ac_coverage` (`warn` in the templates, `block` in this repository by the implementation ADR) (rule 5) |
| Q-K4-21 | What does a `done` requirement without an `ACn` structure do? | it fails (rule 3); none exists today |
| Q-K4-22 | Is a stray marker (`REQ-007 AC9` when there is no AC9) a failure? | no: a drift-audit finding `D7` (rule 4) |
| Q-K4-23 | A bare `REQ-nnn` marker: does it still satisfy the existing "some marker" rule? | yes, unchanged (rule 2) |
| Q-K4-24 | Is `proof.py` a `check_*` script? | no: it runs the tests, so it stays out of `agk-governance` and of `check_kit_tests` (rule 7) |
| Q-K4-25 | `git archive` drops `.git`; a test that runs `git` fails on the base and counts as red. | (draft) accepted as a false red. **Changed by the ruling:** a detached worktree (rules 8, 10, 11) |
| Q-K4-26 | Head from an export instead of ROOT. | yes (rule 11) |
| Q-K4-27 | Timeout 900 seconds per run; a timeout is `unknown`. | yes (rule 15); the value is a placeholder for the maintainers |
| Q-K4-28 | `red-on-head` as a reason of `not-proven`, or a fifth outcome? | a reason of `not-proven` (rule 12) |
| Q-K4-29 | A declaration with no `project_tests`: `skipped` or `unknown`? | `unknown` first (rule 12): nothing could have run |
| Q-K4-30 | The transport of the outcome, and `(verify)` that the jobs API returns every step's name and conclusion. | step conclusions (rule 17); a residual holds the fallback |
| Q-K4-31 | Make `proof` a required check? | no, in K4 (rule 16) |
| Q-K4-32 | Which toolchain does the runner have? | the hosted image's; the kit installs none (rule 16) |
| Q-K4-33 | `check_pr_body.py` fails a `Behaviour:` line whose value is not `unchanged`. | yes, so a typo is not an escape (rule 18) |
| Q-K4-34 | A test that depends on a changed helper that is not matched by `test_patterns`: the helper is not copied. | the base then has the old helper; the outcome may be a false red or a false green; accepted and written in rule 14 |
| Q-K4-35 | A local `make` target (`agk-proof`) for running the proof before pushing. | not added in the spec; `proof.py` runs by hand |
| Q-K4-36 | Criterion b on the sandbox: the agent reads the sandbox read-only with the kit's script. | rule 21; the sandbox is already attached by the maintainers' approval (K3); confirm it still is |
| Q-K4-37 | Criterion c on the pilot: who opens the seeded pull requests, and with what access? | (draft) the agent, in the pilot's own sessions. **Changed by the ruling:** the pilot's own session, under its `CLAUDE.md`, from a brief the maintainers paste (rule 20) |
| Q-K4-38 | "Unresolved false flag" = a false flag with no fix merged and no declaration by the Friday of its week. | rule 22; the maintainers may choose another cut-off |
| Q-K4-39 | REQ-003 AC4 text. | proposed below; added by ADR when this spec is Approved |

## Rulings (maintainers, 2026-10-16)

The default ruling is that every reading the draft took is accepted; the table lists each question and the exceptions. Pilot: the
pilot repository now exists (a Go module with `go test ./...` as `project_tests`, `test_dirs = ["."]`, `test_patterns = ["*_test.go"]`,
adopted on kit 0.11.0, ruleset applied, doctor 20 ok); it is still "the pilot repository" here and never named. The draft's sentence
that the pilot "does not exist yet" (Q-K4-37) is replaced.

| Q | Ruling | Where in the spec |
| --- | --- | --- |
| Q-K4-20 | accepted. Templates ship `ac_coverage = "warn"`; this repository sets `block` in the implementation ADR, because its `done` requirements already comply | rule 5 |
| Q-K4-21 | accepted as drafted: a `done` requirement without `ACn` structure fails | rule 3 |
| Q-K4-22 | accepted as drafted: a stray marker is drift finding `D7` | rule 4 |
| Q-K4-23 | accepted as drafted: a bare `REQ-nnn` still satisfies the existing rule | rule 2 |
| Q-K4-24 | accepted as drafted: `proof.py` is not a `check_*` script | rule 7 |
| Q-K4-25 | **changed:** no `git archive`. The base run uses a detached **`git worktree` of the base commit** (it has `.git`) with the pull request's test files copied in; the head run uses a worktree of the head. The false-red note for a missing `.git` is removed; the residual for helper files (Q-K4-34) is kept | rules 8, 10, 11; Residual |
| Q-K4-26 | accepted as drafted: the head is run from its own worktree, not ROOT | rule 11 |
| Q-K4-27 | accepted as drafted: 900 seconds per run; a timeout is `unknown` | rule 15 |
| Q-K4-28 | accepted as drafted: `red-on-head` is a reason of `not-proven` | rule 12 |
| Q-K4-29 | accepted as drafted: a declaration with no `project_tests` is `unknown` | rule 12 |
| Q-K4-30 | accepted with the `(verify)`: the implementation proves on this repository that the jobs API returns every step name and conclusion before the facts rely on it, and the Residual names the fallback | rule 17; Residual |
| Q-K4-31 | accepted as drafted: `proof` is not a required check in K4 | rule 16 |
| Q-K4-32 | accepted as drafted: the hosted image's tools, none installed by the kit | rule 16 |
| Q-K4-33 | accepted as drafted: `check_pr_body.py` fails a `Behaviour:` value other than `unchanged` | rule 18 |
| Q-K4-34 | accepted as drafted, and now written in rule 14 and the Residual: a changed helper outside `test_patterns` is not copied | rules 9, 14; Residual |
| Q-K4-35 | accepted as drafted: no local `make` target | not in the spec |
| Q-K4-36 | the sandbox attachment is per session; the implementation session asks for it again when criterion b is proven. The spec says so | rule 21 |
| Q-K4-37 | **changed:** the pilot exists; the seeded pull request there is opened by the **pilot's own session**, under its `CLAUDE.md`, from a brief the maintainers paste; this repository records only the outcome | rule 20 |
| Q-K4-38 | accepted as drafted: unresolved means no fix and no declaration by the Friday of the week | rule 22 |
| Q-K4-39 | accepted as drafted: REQ-003 AC4 is added by ADR when this spec is Approved | below |

**Sibling specs touched.** None. The `proof` field stays in SPEC-0009 rule 14 as drafted; the change to a worktree does not alter it.
The ruling on Q-K4-48 (a `drift` section) is in SPEC-0009 and SPEC-0011 and does not touch this spec.

## REQ-003 AC4, proposed (for the ADR that adds it)

`AC4 every acceptance criterion of a `done` requirement has a test marker `REQ-nnn ACn`` — appended to the acceptance line of
REQ-003, whose status stays `done` (its three criteria already have markers, and AC4 is itself tested by `REQ-003 AC4` markers in
`tests/kit/test_check_requirements_ac.py`).

## Proof plan

- Criterion b: the fixture in `block` mode, this repository at the default branch, and the sandbox: rules 19 and 21. The sandbox
  step is read-only.
- Criterion c: a seeded pull request in this repository and in the pilot, expected `not-proven`; a real change expected `proven`; two
  weeks of the false-flag record; the `unknown` case with no `project_tests`: rules 19, 20, 22. The agent opens the seeded pull
  requests and records the outputs; the maintainers decide what counts as a false flag.

## Dependencies on the other K4 specs

- SPEC-0009 supplies `common.parse_acceptance`, `common.find_ac_markers` and the `criteria` and `markers` sections; it carries the
  `proof` field that rule 17 here defines.
- SPEC-0011 reads `proof` (to print what is proven) and the count of `Behaviour: unchanged` declarations.

## Decisions-log rows (for the maintainers' log; not edited in this pull request)

| Date | Decision | Reason | Recorded in | By |
| --- | --- | --- | --- | --- |
| 2026-10-16 | SPEC-0010 proof checks Approved: a `done` requirement needs a marker for each criterion (`warn`, then `block` by ADR); `proof.py` runs `project_tests` on a worktree of the base with the pull request's test files and on a worktree of the head, four outcomes, `unknown` never `ok`; a separate non-required CI job; result read from step conclusions | criteria b and c of ADR-0021 | `docs/specs/0010-proof-checks.md` | reviewer |
| 2026-10-16 | Q-K4-20 to Q-K4-39 ruled: every reading of the draft accepted; Q-K4-20 templates ship `ac_coverage = "warn"`; Q-K4-25 a `git worktree` replaces `git archive`; Q-K4-30 accepted with the `(verify)` proved before the facts rely on it; Q-K4-36 the sandbox is attached again per session; Q-K4-37 the pilot's own session opens the seeded pull request | maintainers' rulings of 2026-10-16 on the Draft SPEC-0010 | `docs/runs/spec-0010-notes.md` | reviewer |
