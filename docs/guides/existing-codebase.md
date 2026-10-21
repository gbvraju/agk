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
  kit's checks run as `make -f agk.mk agk-governance`; you should see nine lines starting with `ok`.
- **`project_tests` is empty in `agk.toml`.** The `proof` check needs your test command. See step 4.

Put your GitHub handle in `config/reviewers.yaml` in place of `@REPLACE-ME` and run
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
than that reads `unknown`.

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
