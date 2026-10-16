# SPEC-0010: proof checks (every criterion has a test; a new test can fail)

- Status: Draft
- Owner: maintainers
- Requirements: REQ-015 (AC1 to AC3), REQ-016 (AC1 to AC3); REQ-003 (AC4, proposed in the notes and added later by ADR)

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
This is the second of the five K4 specs of ADR-0021 and serves exit criteria b and c. It reads the parsers of SPEC-0009
(`common.parse_acceptance`, `common.find_ac_markers`) and writes one field into the facts document (rule 17). The open
points `Q-K4-20` to `Q-K4-39` are in `docs/runs/spec-0010-notes.md`; none is ruled. Claude Code and GitHub facts not
reconfirmed are marked `(verify)`. The repository facts quoted here were read on 2026-10-16.

## Rules

### (a) Every acceptance criterion needs a test

1. **The rule.** A requirement whose status is `done` needs, for each criterion `ACn` of its `- Acceptance:` line, at least
   one marker `REQ-nnn ACn` in the test files (`test_dirs`, `test_patterns` of `agk.toml`). `check_requirements` gains the rule,
   beside its existing one (a `done` requirement needs some marker). A failure names the requirement and the criterion id,
   never the criterion's text: `FAIL requirements: REQ-007: done requires a test marker for AC2`. Requirements that are not
   `done` are never failed by this rule.
2. **Parsing is shared.** The criteria are those of `common.parse_acceptance` and the markers those of
   `common.find_ac_markers` (SPEC-0009 rules 8, 9, 17). The check does not parse again. The marker grammar in short: a run of
   `REQ-nnn` tokens followed by a space and `AC<n>` attaches that criterion to each requirement of the run; a bare `REQ-nnn` is a
   marker for the requirement only and satisfies the existing rule, not this one.
3. **Unstructured and duplicated acceptance.** A `done` requirement whose acceptance line has no `ACn` token (SPEC-0009
   `criteria_form: "unstructured"`) fails: `done requires an acceptance line with AC1, AC2, ...`. A `done` requirement
   with the same `ACn` twice fails: `acceptance repeats AC2`. Today no requirement is either (all 20 lines are structured).
4. **Stray markers.** A marker `REQ-nnn ACn` where requirement `REQ-nnn` has no `ACn` (or does not exist) is reported by the drift
   audit as a finding (`D7`, rule 5), not by `check_requirements`: a stray marker does not weaken anything and must not block a
   merge.
5. **Phases and the switch.** The rule ships as a warning and becomes blocking by decision. `agk.toml` gains `ac_coverage` with the
   values `warn` and `block`. In `warn` (the default of the template, so existing targets migrate on their own time),
   `check_requirements` prints `warn requirements: ...` for each shortfall and exits 0, and the drift audit reports each as
   finding `D7`. In `block`, a shortfall fails the check (exit 1). This repository's `agk.toml` is set to `block` by the ADR of the
   implementation pull request, because it complies (rule 6); a target changes the key in its own pull request, and `agk.toml` is
   a protected path, so the change needs an ADR. An unknown value is a refusal that names the setting.
6. **Migration, read on 2026-10-16.** On `main`, run read-only with the grammar above, both `done` requirements comply:
   REQ-001 (AC1 to AC3) and REQ-003 (AC1 to AC3) have a marker for every criterion. Not `done`, and therefore not failed, but
   short: REQ-005 AC3, REQ-008 AC1 and REQ-013 AC4 have no `REQ-nnn ACn` marker; REQ-015 to REQ-020 have none (all `planned`).
   If the maintainers set REQ-005, REQ-008 or REQ-013 `done` before the three markers exist, `block` fails them. The list is
   recomputed by the implementation pull request and recorded in `docs/runs/`. REQ-003's acceptance gains AC4 (the text is in
   the notes) by an ADR when this spec is Approved, as REQ-012 was widened in ADR-0016.

### (b) A new test can fail: red-then-green

7. **Command.** `python3 scripts/agk/proof.py [--base REF] [--head REF] [--body FILE|-] [--json] [ROOT]`. Standard library only;
   vendored into every target; it runs the project's own command and nothing else of the project's. `--base` defaults to the merge
   base of `HEAD` with the default branch (`AGK_BASE`, else `origin/<default>`, as `common.resolve_base`); `--head` defaults to
   `HEAD`; `--body` is the pull request body (a file, or `-` for stdin), read for one line (rule 18). It is not run by
   `make governance`: it runs the project's tests twice and needs the project's toolchain.
8. **What it reads.** `project_tests` (a shell command), `test_dirs`, `test_patterns` and `proof_timeout` (seconds, default 900)
   from `agk.toml`; the file changes between base and head from `git diff --name-status`; and the body line of rule 18. It writes
   nothing in ROOT: all work happens in a temporary directory created outside ROOT and removed at the end, also on a failure.
9. **The test file set.** The files changed between base and head (status added, modified, renamed or deleted) that lie under one of
   `test_dirs` and whose name matches one of `test_patterns` (shell-style globs on the file name, as `common.find_markers`). Nothing
   else is a test file: a changed fixture or helper outside the patterns is part of the change, not of the tests. A repository whose
   test files cannot be told apart this way has an empty set (rule 12, `unknown`).
10. **Placing the tests on the base.** The base commit is exported into the temporary directory (`git archive`, so no `.git` and
    no history). Each test file added or modified at head is copied from the head over the same path; each test file deleted at head
    is removed; a renamed one is the deletion of the old path and the addition of the new. No other file of the pull request is copied.
    The result is "the base code with the pull request's tests".
11. **The two runs.** Run 1: `project_tests` in the temporary directory (the base with the new tests), expected to fail. Run 2:
    `project_tests` in a second temporary export of the head (not ROOT, so a dirty tree cannot change the answer), expected to pass.
    The command is run through the shell with the same environment as the caller, no extra variables, working directory the export, and
    its output is shown (the last 40 lines of each run) and never stored. Exit status 0 is a pass, any other status is a fail; a
    compile or import error on the base (the new test cannot be built without the change) is a fail and so counts as red, in every
    language alike.
12. **Outcomes.** Exactly one, evaluated in this order:
    - `unknown` (`no-project-tests`) when `project_tests` is absent or empty;
    - `skipped` when the body has the line of rule 18;
    - `unknown` (`no-test-files`) when the test file set is empty, or contains only deletions;
    - `unknown` (`timeout`) when either run exceeds `proof_timeout`; the process group is killed;
    - `proven` when run 1 failed and run 2 passed;
    - `not-proven` (`green-on-base`) when run 1 passed: the new tests pass without the change;
    - `not-proven` (`red-on-head`) when run 2 failed: the head is red, which `governance`'s project-tests step reports too.
    An error that is not one of these (the export fails, a temporary directory cannot be made) is exit 3 and no outcome.
13. **Output and exit.** One line, `proof: <outcome> (<reason>)` (the reason is omitted for `proven` and `skipped`), after the shown
    output; with `--json`, one object with `outcome`, `reason`, `base`, `head` and the test file set (sorted). Exit 0 for `proven` and
    `skipped`; 1 for `not-proven`; 4 for `unknown`; 2 usage; 3 I/O. `unknown` is never exit 0: it is never `ok`.
14. **What it proves, and what it does not.** *It proves:* that the project's own test command fails on the base once the pull
    request's tests are placed on it, and passes on the head; so the pull request's tests, taken together, can fail, and the change
    outside the test files is what turns them green. *It does not prove:* that a test checks the right thing; that every new test is
    red, only that the run as a whole is; that a red base is red for the reason the pull request claims (a missing dependency that the
    pull request adds also makes the base red); that a test that was already red on the base for an unrelated reason is meaningful;
    anything about code or behaviour with no test change (rule 18 exists for that); or that the marker in a test names a criterion that
    the test exercises (SPEC-0009 rule 9 counts a marker in a comment). It makes no judgement of quality and uses no model.
    Mutation testing is a K5 candidate (ADR-0021).
15. **Timeouts.** `proof_timeout` applies to each of the two runs separately. A run that exceeds it is killed, with its children,
    and the outcome is `unknown`, never `proven` or `not-proven`: a slow suite is not evidence either way. The value must be a
    positive integer; an invalid value is a refusal that names the setting.
16. **Where it runs.** A separate CI job named `proof` in `.github/workflows/proof.yml`, on `pull_request` (`opened`, `synchronize`,
    `reopened`, `edited`), with `permissions: contents: read`, a full checkout (`fetch-depth: 0`) and no secret. It is **not** a
    required status check in K4: the `governance` job and its ruleset entry are unchanged, and the ruleset is not touched. Its
    runner uses the tools the hosted image already has; the kit installs no language toolchain, and `project_tests` may install what
    it needs. A repository that wants a different runner edits its own copy and records an ADR (the file is verbatim, so the doctor
    reports it). The workflow runs the project's code on the pull request head, as `governance` does; it uses the `pull_request` event,
    never `pull_request_target`.
17. **How the result reaches the facts.** The job has one step that runs `proof.py` with `--json` and exits 0 whatever the outcome,
    and four steps named `outcome: proven`, `outcome: not-proven`, `outcome: skipped` and `outcome: unknown`, each guarded by an `if:`
    on the step's output, so that exactly one of them ends `success` and three end `skipped`. The job itself ends `failure` only
    when `proof.py` itself failed (usage, I/O). `facts.py` reads, for each pull request in its window, the workflow run of the head SHA
    named `proof` and its job's steps (`GET repos/{o}/{r}/actions/runs?head_sha=SHA` and `GET repos/{o}/{r}/actions/runs/{id}/jobs`
    `(verify)` that a step's name and conclusion are returned for every step) and sets the field `proof` of that pull request to the
    outcome word, or `"unknown"` when there is no run, more than one step succeeded, or the API could not be read. SPEC-0009 rule
    14 carries the field. No write permission is needed and no comment is posted.
18. **`Behaviour: unchanged`.** A pull request that changes no behaviour (a refactor, documentation, a rename) declares it with the
    body line `Behaviour: unchanged`, exactly. `check_pr_body.py` accepts the line as optional, and fails a `Behaviour:` line with any
    other value (`FAIL pr-body: 'Behaviour:' must be 'unchanged'`) so that a typo is not a silent escape. The pull request template
    gains an optional line `Behaviour: unchanged (optional; delete the line for a change in behaviour)`, as `Issue:` was added. The
    declaration is a person's statement and is counted, not checked: SPEC-0011 prints how many were declared in the week, so overuse is
    visible. `proof.py` reports `skipped` for it; the declaration is never judged.

### Tests and proof

19. **Tests, no language toolchain.** `tests/kit/test_proof.py` (installed with the script): every case builds a git repository in
    `tmp_path` and uses a fake `project_tests` command that only needs `python3` (for example one that exits 1 unless a named file
    exists). The cases: *seeded* (a new test file whose fake test passes on the base: `not-proven`, `green-on-base`); *real change*
    (the change adds the file the fake test needs: `proven`); *refactor with the declaration* (`skipped`); *no `project_tests`*
    (`unknown`); *no test file changed* (`unknown`); *a test deleted and one renamed* (the base keeps no stale file); *head red*
    (`red-on-head`); *a timeout* (`proof_timeout = 1`, `unknown`); *a build failure on the base* (a command that exits 2 until the
    change exists: `proven`); *a test-looking file outside `test_dirs`* (ignored); *a dirty work tree* (the head is exported, so the
    answer is the same). `tests/kit/test_check_requirements_ac.py`: the rule of (a) in `warn` and `block`, on a fixture with a
    `done` requirement whose second criterion has no marker, a stray marker, an unstructured line, a duplicate `ACn`, and a
    bare marker. `tests/kit/test_pr_body_behaviour.py`: the line of rule 18. The workflow is tested like the other workflows
    (`tests/kit/test_workflow.py`): job name, permissions, event, no `pull_request_target`, SHA-pinned actions, the four outcome steps.
    The reader of rule 17 is tested in SPEC-0009's fixtures with recorded run and job files.
20. **Live proof of criterion c, and the pilot.** (Described here; done by the maintainers and the agent when the code exists, not
    in this pull request.) In this repository: a seeded pull request that adds a test passing on the base (opened to be closed
    unmerged), expected `not-proven` (`green-on-base`), and a real pull request with a change and its test, expected `proven`. In
    the pilot repository, which is a Go module whose `project_tests` is `go test ./...` and whose `test_patterns` is `["*_test.go"]`
    with `test_dirs = ["."]`: a seeded pull request that adds a `Test...` function calling existing code and asserting what it already
    does, expected `not-proven`; and a pull request that adds a test for a changed behaviour, expected `proven`; a compile error on the
    base (a test calling a function that the change adds) is the Go form of the build failure case and must be `proven`. The commands
    and the outputs are recorded in `docs/runs/`. The agent opens the seeded pull requests; the maintainers decide what is flagged
    wrongly.
21. **Live proof of criterion b.** (a) The fixture of rule 19 fails in `block` mode. (b) This repository's default branch passes in
    `block` mode, with the list of rule 6 recomputed. (c) The sandbox passes: the kit's `check_requirements.py` is run read-only against
    the sandbox work tree, and the requirements it inherits from the template (all `planned`) and its own are reported; if the sandbox has
    a `done` requirement with an untested criterion, the finding is recorded and the sandbox's requirement is set back to `in-progress`
    in the sandbox's own pull request, or the criterion is tested, by the maintainers' choice. Recorded in `docs/runs/`.
22. **The weekly false-flag record.** For two consecutive weeks of this repository's real pull requests, every `not-proven` and
    every `unknown` that is not `no-test-files` is listed with its pull request number in `docs/runs/`, and the maintainers write
    against each: *correct* (the tests really pass on the base: fixed or declared), or *false flag* with the cause. **An unresolved
    false flag** is a false flag with no fix to `proof.py` merged and no declaration on the pull request by the Friday of its week.
    Criterion c needs none for both weeks. The list is derived from the facts (`proof` per pull request) and typed by nobody.
23. **Installed files and classes.** Installed (verbatim): `scripts/agk/proof.py`, the changes to `scripts/agk/common.py`,
    `check_requirements.py`, `check_pr_body.py`, `drift_audit.py` (finding `D7`), `.github/workflows/proof.yml`,
    `.github/PULL_REQUEST_TEMPLATE.md` (one optional line), `tests/kit/test_proof.py`, `tests/kit/test_check_requirements_ac.py`,
    `tests/kit/test_pr_body_behaviour.py`, fixtures; templates: the two `agk.toml` templates gain `ac_coverage = "warn"` and
    `proof_timeout = 900`. The classes touched are `scripts/agk/`, `.github/`, `tests/kit/`, `kit/` and, for this repository's own
    `agk.toml`, `agk.toml`; the implementation pull request carries an ADR that names each. The kit version is bumped.
24. **No language in the kit.** Nothing in `proof.py` or in the criteria check reads a language: the test command, the directories
    and the patterns come from `agk.toml`, the markers are plain text. A pilot in another language changes `agk.toml` and nothing
    else. `tests_before` and `tests_after` of the metrics stay Python-specific until their residual is closed (ADR-0021).
25. **Order.** Built after SPEC-0009 (it uses the parsers of rule 2 and the field of rule 17); before SPEC-0011 (the report reads
    `proof` and the declaration count). ADR-0021 decision 7: proof checks by 2026-11-16.

## Tests

- Rules 1 to 5: `tests/kit/test_check_requirements_ac.py`, marker `REQ-015 AC1`; rule 6 (this repository complies): the same file
  over the real `docs/requirements.md`, marker `REQ-015 AC3`; the sandbox run (rule 21): marker `REQ-015 AC2`, a record.
- Rules 7 to 15, 19: `tests/kit/test_proof.py`, marker `REQ-016 AC1`; the no-project-tests case, marker `REQ-016 AC3`.
- Rule 16: `tests/kit/test_workflow.py`, marker `REQ-016 AC1`.
- Rule 17: SPEC-0009's fixture `pr-states` extended with recorded run and job files, marker `REQ-016 AC1`.
- Rule 18: `tests/kit/test_pr_body_behaviour.py`, marker `REQ-016 AC1`.
- Rules 20 and 22: records in `docs/runs/`, checked by the maintainers, not by a test (markers `REQ-016 AC1`, `REQ-016 AC2`).

## Proof

Exit criterion b of ADR-0021: *the check fails a fixture with a `done` requirement whose second criterion has no test, passes on this
repository's default branch and on the sandbox, and this repository's own `done` requirements all comply.* Rules 1 to 6, 19 and 21.

Exit criterion c: *the check flags a seeded pull request whose new test passes on the base commit, in this repository and in the pilot
repository (a different language); over two consecutive weeks of this repository's real pull requests it reports no unresolved false
flag; a repository with no `project_tests` reports `unknown`, never `ok`.* Rules 7 to 15, 19, 20, 22. The records are in `docs/runs/`.

## Residual

- 2026-10-16: red-then-green proves that a test can fail, not that it checks the right thing; mutation testing is a K5 candidate
  (due 2027-01-31).
- 2026-10-16: the `proof` job is not a required check; making it required is a ruleset change for a later ADR, after two weeks of
  false-flag records (due 2026-12-31).
- 2026-10-16: the outcome reaches the facts through the step conclusions of the `proof` job (rule 17); if GitHub does not return
  step names for every run `(verify)`, the fallback is the job summary, which is not machine-read today (due 2026-11-16).
- 2026-10-16: a base that is red because the pull request adds a dependency is counted as proof; the report cannot tell the two
  apart (due 2026-12-31).
- 2026-10-16: `proof.py` runs the project's whole suite twice per pull request; a project with a slow suite times out to `unknown`
  and has no selective mode (due 2026-12-31).
