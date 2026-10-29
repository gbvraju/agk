# Adopting AGK in an existing codebase

For a repository that already has code, tests and history. The order matters: install without touching your product, write down
what the product does today as requirements with tests, and only then change anything. Each step has its command and what to see.
The commands of steps 1 to 3 were run on a throwaway copy of a small repository; the record is
[docs-walk-2.md](../runs/docs-walk-2.md).

Read [the limits](../../README.md#honest-limits) first. The path after step 4 is the one of [the getting-started guide](getting-started.md),
which is written for a new repository; this page says only where an existing codebase differs.

## Step 1. Install with `/agk:adopt`, which touches no product file

Prepare as in steps 1 and 2 of [getting started](getting-started.md) (the plugin installed, `gh` logged in, Issues and Actions
on). Your repository needs a remote named `origin` whose `HEAD` is known. A normal `git clone` has it. If you made the
repository with `git init` and `git remote add`, adopt refuses and says what to run:

    git remote set-head origin --auto

In Claude Code, on a new branch:

    /agk:adopt

It shows a preview first: a list of `create ...` lines and `dry run: NNN files would change; nothing was written`. Say yes. It
creates its own files (`agk.mk`, `agk.toml`, `scripts/agk/`, `.claude/`, `config/`, `constitution/`, `docs/` and
the governance workflow; about 50 files, 225 KB; the kit's own tests are not installed), appends one marked block to `.gitignore`,
`.gitattributes` and, when they exist, to `CLAUDE.md`, `.github/CODEOWNERS` and
`.github/PULL_REQUEST_TEMPLATE.md`, and refuses rather than overwrite. Your `Makefile`, `pyproject.toml`, tests and product files
are not touched: after the run no product file shows as modified. Nothing is committed.

Two things differ from a new repository:

- **`make governance` does not exist.** Your `Makefile` is yours and is not changed, and your `make test` runs your own tests. The
  kit's checks run as `make -f agk.mk agk-governance`; you should see ten lines starting with `ok` and one `skipped (no comments file)`.
- **`project_tests` is empty in `agk.toml`.** The `proof` check needs your test command. See step 4.

Put your GitHub handle in `config/reviewers.yaml` in place of `@REPLACE-ME` on both lines that hold it,
`maintainers: {github_team: "@REPLACE-ME"}` and `spec_approvers: ["@REPLACE-ME"]` (the people whose `Approve: SPEC-<n>` counts;
user handles only, never a team), and run
`python3 scripts/agk/reviewers.py --codeowners --write`; it prints `wrote agk block of .github/CODEOWNERS`. Open a pull request with
everything adopt created, wait for `governance`, and merge. Then run `/agk:ruleset` as in step 5 of getting started.

## Step 2. Write down today's behaviour before any change

Before you change anything, record what the product does now. One requirement for each behaviour your documentation already
promises (your README, your manual, your API description). Do not invent behaviour you do not document.

For each, give `/agk:spec` one plain sentence:

    /agk:spec "Running wc on a text file prints the number of words in it, where words are separated by any white space."

It writes a requirement with Given/When/Then criteria at the end of `docs/requirements.md` (status `planned`), a Draft spec and an ADR
stub, on a new branch, and prints the commit message and pull request body. At least one criterion says what must not happen. Read
the criteria against what the product really does; the checks cannot tell you they are right. Merge it.

The criteria describe what the product does today, including what you might call a flaw. Recording a flaw is not endorsing it;
changing it is a later, separate change.

## Step 3. Add tests that assert today's behaviour

For each criterion add a test that passes on the unchanged code and assert what it does now. Mark each test with its requirement and
criterion in its name or docstring, for example `REQ-101 AC1`. Then a person sets the `Status:` of your own requirements to `done` (an agent
never marks anything done). Leave `REQ-001` to `REQ-003` alone: they are the kit's own requirements, installed as `planned`, and
`make -f agk.mk agk-governance` fails with `done requires a test marker` if you mark them done.

Two more statuses and lists help you keep the tests honest. A requirement for a feature you drop goes to `retired` (a person changes the
`Status:` line, with an ADR); from then on its `REQ-nnn` markers fail `check_requirements`, naming the requirement and the files, so the same
pull request removes those tests or retags them to a requirement they still prove. The weekly drift audit also lists, as finding `D8`
and never blocking, the test files that carry no `REQ-nnn` marker (up to 20 paths and the count), and `traceability.py` ends with the
retired requirements and the untagged test files. A pull request that removes such a test declares `Behaviour: unchanged` and keeps the proof green.

The pull request body for this change says:

    Advances: REQ-101
    Behaviour: unchanged
    Build-state row: 2026-10-19 REQ-101 baseline tests

`Behaviour: unchanged` is true here and is the only time it is: nothing the product does has changed. The `proof` check reads
`skipped`, and the report counts the pull request among those that declared it. Adding the tests while changing no product file is
what the line means. Do not use it for a change that alters behaviour.

## Step 4. Tell the proof check how to run your tests

Open `agk.toml` and set `project_tests` to the command that runs your tests, for example:

    project_tests = "python3 -m pytest -q"

`agk.toml` is a protected file: the pull request that changes it needs an ADR whose `Protected classes:` line names `agk.toml`.
Without the ADR `make -f agk.mk agk-governance` fails with `protected path class 'agk.toml' changed without an ADR that names it`.
Until `project_tests` is set the `proof` check reads `unknown` with the reason `no-project-tests`. Your test command runs twice in
the `proof` job, once on the base and once on the head, within `proof_timeout` in `agk.toml` (900 seconds by default); a suite slower
than that reads `unknown`. A run that times out is ended with every process it started, on Windows as on Linux and
macOS, and the line reads `proof: unknown (timeout after N s, setting: proof_timeout)`: the tests did not fail, they did not
finish. When proof nears its limit on a busy machine, run it alone. Raising `proof_timeout` is a protected change (an ADR, as
above); a slow suite is better fixed (#289).

When your suite is slow, or your tests live in more than one place (a back end and a front end, say), give proof one area per
place in a `[proof]` table instead. Proof then runs each area's own command with only the test files the pull request adds or
changes in that area, on the base and on the head:

    [proof]
    backend = { dirs = ["backend/tests"], patterns = ["test_*.py"], cwd = "backend", command = "cd backend && uv run pytest {files}" }
    frontend = { dirs = ["frontend/src"], patterns = ["*.test.ts"], cwd = "frontend", command = "cd frontend && npx vitest run {files}" }

`{files}` is required; proof replaces it with the area's files, relative to the area's `cwd` (the repository root when it is not
set) and quoted. The command runs from the repository root, so it changes into its folder itself. The result is `proven` only when
every area with files is red on the base and green on the head; otherwise the line names the area, as in
`proof: not-proven (frontend: green-on-base)`. Without the table proof uses `project_tests` as above.

## Step 5. The first real change, tests first

Follow steps 7 to 10 of [getting started](getting-started.md): a sentence, a Draft spec, the architect's brief, an Approved spec,
then an implementation session that builds from the brief. For an existing codebase add one rule to the brief: **the new test
is written first and must fail on the unchanged code.** The `proof` check runs the pull request's test files on the base commit and
on the head; it reads `proven` when they fail on the base and pass on the head, `not-proven` with a reason when they do not, and
`unknown` when it cannot tell. In the walk, a change that made a missing file exit with 1 read `proven`, and the same change with
`project_tests` empty read `unknown`.

## What is recorded, and what is not

Nobody outside the project has followed this guide. The proof check was read as `proven` in CI on this project's own repository (the
`Proven` line for REQ-001 to REQ-003 in [issue 88](https://github.com/gbvraju/agk/issues/88)); the pilot's two proven examples are
not yet recorded in this repository, so none is linked here. The adoption of a real existing repository is recorded in
[k2-live-proof.md](../runs/k2-live-proof.md); the first readings of the proof check, including its false flags, are in
[proof-checks-live-2.md](../runs/proof-checks-live-2.md).

AGK does not read your product code for meaning. It cannot tell that a baseline requirement describes the product correctly or that a
baseline test is a good test; those are your review.
