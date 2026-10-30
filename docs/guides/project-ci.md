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

## 4. A documentation-only change skips the heavy steps and still reports success

Never use `paths-ignore` (or `paths`) on a workflow that holds a required check: when it does not start, the check never reports
and the pull request waits for it forever. Start the job every time, find out whether only documentation changed, and skip the
heavy steps; the job then ends green.

```yaml
      - uses: actions/checkout@<pinned sha>
        with:
          fetch-depth: 0
      - name: Documentation only
        id: changes
        env:
          BASE: ${{ github.event.pull_request.base.sha || github.event.before }}
        run: |
          # Any error, or any file outside docs/ that is not Markdown, runs every step.
          files="$(git diff --name-only "$BASE" "$GITHUB_SHA" 2>/dev/null)" || files="unknown"
          if [ -n "$files" ] && ! printf '%s\n' "$files" | grep -qvE '^docs/|\.md$'; then
            echo "docs_only=true" >> "$GITHUB_OUTPUT"
          else
            echo "docs_only=false" >> "$GITHUB_OUTPUT"
          fi
      - name: Tests
        if: ${{ steps.changes.outputs.docs_only != 'true' }}
        run: make test
```

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

The router's own workflow is not judged: it labels every pull request, drafts included, and runs no test.
