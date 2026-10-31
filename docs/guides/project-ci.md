# Project CI: fast and cheap by default

A required check runs on every push of every pull request, so its cost is paid many times a day. A project made with the kit
keeps it to minutes, not tens of minutes, with five defaults. Each is a copyable snippet for a workflow of your own under
`.github/workflows/`; the kit's own workflows follow them where they apply and say why in a comment where they cannot. A change
under `.github/` is protected, so it comes with an ADR in the same pull request. Pin every action you use by its full commit sha,
as the kit's own workflows do; the snippets write `<pinned sha>` where yours goes.

`agk doctor` warns (never fails) about the first two: `ci-drafts` when a workflow that holds a check of `required_checks` runs on
draft pull requests, and `ci-concurrency` when it has no concurrency group. A warning names the setting and the path class, not
the workflow; look at the workflows that hold your required checks.

## 1. Heavy jobs run only on pull requests that are not drafts

A builder pushes a checkpoint to a draft pull request at every step; nothing on a draft can merge, so a heavy job there buys
nothing. Run it on a ready pull request and on pushes to the default branch, and add `ready_for_review` so it runs once the draft
is marked ready. A skipped job reports `skipped`, which GitHub counts as passing for a required check, and so does the router.
That is why `ready_for_review` is not optional: without it, a draft marked ready with no new commit keeps the green check of
its skipped run, and the pull request can merge with the heavy job never run.

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
  push:
    branches: [main]

jobs:
  suite:
    if: ${{ github.event_name != 'pull_request' || !github.event.pull_request.draft }}
    runs-on: ubuntu-latest
    steps:
      - run: make test
```

When the job must still run some light steps on a draft, keep the job and skip only the heavy steps with the same condition on
each step, as the kit's `governance` does.

## 2. One concurrency group per pull request, cancelling the superseded run

A new push makes the run of the previous commit worthless. Cancel it for pull requests; never cancel a push to the default
branch, whose run is the record of what merged.

```yaml
concurrency:
  group: suite-${{ github.event.pull_request.number || github.sha }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

For a workflow that runs only on pull requests, `cancel-in-progress: true` is enough.

## 3. Cache dependency installs and container layers

Restore what the last run installed, keyed on the lock files, so an unchanged dependency set is not downloaded again:

```yaml
      - uses: actions/cache@<pinned sha>
        with:
          path: ~/.cache/pip
          key: deps-${{ runner.os }}-${{ hashFiles('**/requirements*.txt', '**/package-lock.json') }}
```

Build container images with the layer cache of GitHub Actions, so an unchanged layer is not built again:

```yaml
      - uses: <the container build action>@<pinned sha>
        with:
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

Measure before you cache a large image: restoring a tarball of a very large image can be slower than pulling a pinned base by
digest and rebuilding. Keep the cache only where the run gets faster.

## 4. A heavy check runs only when its inputs change

A heavy check, such as the project's tests or its local profile, reads only some of the repository: its application code, its
tests, its container build files, its compose files and its own workflow. A change to anything else (a brief, documentation,
the kit's own files, another workflow) cannot change its result, so the check runs in full only when a file it reads changed,
and otherwise ends green in seconds with the reason in its step summary.

Never use `paths-ignore` (or `paths`) on a workflow that holds a required check: when it does not start, the check never reports
and the pull request waits for it forever. Start the job every time, compare the files the pull request changed against its
base with the job's own input globs, and skip the heavy steps when none matched. Four rules hold:

- a required check is never removed or weakened: the job always starts and always reports, and only its heavy steps skip;
- a push to the default branch and `ready_for_review` always run in full, as does any other event, so the record of what merged
  and the run of a draft marked ready never rest on a skip;
- any error (no base, a base the clone does not hold, a failed diff) runs in full;
- the skip reason is always visible: the step summary and the log say `skipped: none of <globs> changed`.

Write the globs once, on the job, as `INPUTS`, with the workflow's own file name in place of `<this workflow>`; a glob's `*`
also matches `/`, so `src/*` is everything under `src/`. Add every file the heavy steps read, or the check skips a change it
should have tested.

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
  push:
    branches: [main]

jobs:
  suite:
    runs-on: ubuntu-latest
    env:
      # The files this job reads: application code, tests, the build file of `make test`, container build files, compose
      # files and this workflow. Write your container build file and this workflow's file by their names in your repository.
      INPUTS: "src/* tests/* Makefile *Containerfile* *compose*.y*ml .github/workflows/<this workflow>.yml"
    steps:
      - uses: actions/checkout@<pinned sha>
        with:
          fetch-depth: 0
      - name: Inputs changed
        id: inputs
        shell: bash
        env:
          EVENT: ${{ github.event_name }}
          ACTION: ${{ github.event.action }}
          BASE: ${{ github.event.pull_request.base.sha }}
        run: |
          # Runs in full unless this is an ordinary pull request update whose files match none of INPUTS.
          set -f
          run=true
          if [ "$EVENT" = pull_request ] && [ "$ACTION" != ready_for_review ] && [ -n "$BASE" ] &&
            files="$(git diff --name-only "$BASE" "$GITHUB_SHA")"; then
            run=false
            while IFS= read -r file; do
              for glob in $INPUTS; do
                case "$file" in $glob) run=true ;; esac
              done
            done <<< "$files"
          fi
          echo "run=$run" >> "$GITHUB_OUTPUT"
      - name: Skip reason
        if: ${{ steps.inputs.outputs.run == 'false' }}
        run: |
          echo "skipped: none of $INPUTS changed" | tee -a "$GITHUB_STEP_SUMMARY"
      - name: Tests
        if: ${{ steps.inputs.outputs.run != 'false' }}
        run: make test
```

Give every heavy step the same condition, `!= 'false'`, so a step whose output is missing runs rather than skips. A job that
must also skip drafts keeps the condition of default 1 beside it.

This replaces the documentation-only step of earlier versions of this guide (`steps.changes.outputs.docs_only`): a change only
to documentation matches none of the globs, so it skips as before, and so does a change only to briefs or to the kit's files.

The kit's `governance` does not do this: its checks read the documentation, so a documentation change runs them all. For the
proof check, a change with no test of its own is reported as skipped, and the `[proof]` table of `agk.toml` runs only the pull
request's own tests per test area (see the reference guide); use that rather than a second copy of the suite.

## 5. No build-record uploads, and a short artifact retention

A container build action may upload a build record for every run; on a private repository those records fill the Actions storage
quota. Turn off the build action's options that upload a build record and write a build summary; turn both off, using the
names its own documentation gives them `(verify)`.

Upload an artifact only when a person or a later job reads it, and keep it a few days:

```yaml
      - uses: actions/upload-artifact@<pinned sha>
        with:
          name: report
          path: report/
          retention-days: 3
```

The kit's router keeps its pipeline document for 7 days; the weekly product report keeps its data for 90 days on purpose, since
readers of later weeks use it.

## What the doctor checks

| Id | Warns when | Fix |
|---|---|---|
| `ci-drafts` | a workflow that holds a check of `required_checks` and runs on `pull_request` never reads `github.event.pull_request.draft` (outside a comment) | default 1 |
| `ci-concurrency` | a workflow that holds a check of `required_checks` has no `concurrency:` group, at the top or on a job | default 2 |
| `actions-minutes` | the Actions minutes have passed the `50%` level (the line of `minutes.py --line`, below); `cannot check (minutes-unknown)` when the token can read neither billing nor the run history | the section below |

The router's own workflow is not judged: it labels every pull request, drafts included, and runs no test.

## How many minutes are left

A plan's included Actions minutes are counted per account, each job rounded up to a whole minute, so many short jobs cost more
than their seconds suggest. One command shows where the month stands; it only reads (`gh api` with GET, `gh` holds the
credential) and writes nothing:

```sh
python3 scripts/agk/minutes.py          # or --json for the same figures as JSON
```

It prints:

- **minutes used this month**: the billing figure of the whole account where the token can read billing, otherwise the
  estimate below;
- **included minutes**: the plan's, or `unknown (the token cannot read billing: refused|missing|unreadable)`; reading billing
  needs a token with the account's billing read permission `(verify)`, and some billing setups no longer answer the endpoint
  it reads `(verify)`;
- **estimate from run history**: this repository's jobs that started this month (UTC) on GitHub-hosted runners, each rounded up
  to a whole minute, per workflow. It says `at least` when the run list was capped or a run's jobs could not be read; jobs on a
  self-hosted runner and jobs still running are listed, not counted. In a private repository a job's minutes are multiplied
  by its runner's rate, read from its labels, as the included minutes are used: a Windows job counts 2x and a macOS job 10x
  `(verify)`. A known limit: re-runs of runs created before this month are not counted, since a re-run keeps its run's
  creation time;
- **minutes per merged pull request**: the estimate divided by the pull requests merged this month, the figure to compare with
  the defaults above;
- a **warning** line once the higher of the two figures passes `minutes_warn` percent of the included minutes (`minutes_warn`
  in `agk.toml`, 80 when unset); it then exits 3. With the included minutes unknown it never warns.

- a **level** and the day the minutes **run out** (brief #370): the level is the highest of `50%`, `minutes_warn` (80 when
  unset) and `95%` that the higher figure has reached of the included minutes, else `ok`, and `unknown` with the included
  minutes unknown; the day is when the included minutes are used up at this month's daily rate so far (the minutes used over
  the days of the month through today): `runs out about <YYYY-MM-DD>`, or `not this month`.

`python3 scripts/agk/minutes.py --line` prints only the level and the day, in one line, reading billing first and the run
history only when billing cannot be read, for example
`actions minutes: 1900 of 2000 used (95%), level 95%; runs out about 2026-10-20; at this level, see local mode in
docs/guides/local-mode.md`. The doctor prints the same line as its check `actions-minutes`, a warning from the `50%` level on and
never a failure, and `/agk:launch` prints it before it asks to start sessions.

When the minutes run out, the checks cannot run on GitHub until the month turns or the plan changes: see local mode
(brief #322) for how to keep working.

When the minutes run short month after month, a private repository can move its own heavy jobs, never the kit's checks, to
an ephemeral runner on a machine of its own: [self-hosted-runner.md](self-hosted-runner.md) says when that fits and the
rules that keep it safe.
