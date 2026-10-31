# A self-hosted runner for heavy jobs: opt-in, ephemeral, and never for the kit's own checks

A project whose Actions minutes run short can move its heavy jobs (a full test suite, an image build, a long scan) to a runner
on a machine of its own, so that they spend no hosted minutes, while the kit's light checks stay on GitHub. This page is the one
way the kit documents, with the safety rules first (brief #372, ADR-0217). Nothing here is installed or switched on by the kit:
a project opts in by editing its own heavy job, and can step back by editing it again.

A careless self-hosted runner is a security risk. A runner that stays up between jobs keeps whatever the last job left behind,
and any code that reaches it runs with the machine's access. Follow the rules below as written.

## When it fits

All of these hold:

- **A private repository.** GitHub's hosted runners cost a public repository nothing on standard runners `(verify)`, and a
  public repository's pull requests can come from anyone: a self-hosted runner is never used on a public repository.
- **Heavy jobs only.** The jobs that use most of the minutes: the project's full test suite, image or package builds, long
  scans. `python3 scripts/agk/minutes.py` lists the minutes per workflow, so you can see which jobs those are
  ([project-ci.md](project-ci.md#how-many-minutes-are-left)).
- **Minutes short.** The included minutes of the plan run out before the month does, and the defaults of
  [project-ci.md](project-ci.md) (drafts skipped, superseded runs cancelled, caches) are already in place.

If the minutes are already gone and you need to keep working today, use [local mode](local-mode.md) instead; this page is the
longer-term change.

## The rules

1. **An ephemeral runner.** It takes one job and is then removed, and the next job gets a fresh one: nothing a job writes
   (files, caches, credentials, processes) survives into the next. A runner that is reused between jobs is not allowed, even on
   a machine you trust.
2. **Never on a public repository, never for forks.** Register the runner on the one private repository, not on an account or
   organisation that also holds public ones, and keep pull requests from forks off it: their code is not yours to run.
3. **No secret beyond the job's own.** The job gets only what its own steps need (its `GITHUB_TOKEN`, with the least
   `permissions:` it needs). The machine holds no other token, key or credential the job could read, and the runner's
   registration token is used once and not stored.
4. **Never deploy or production credentials.** A job on this runner never deploys, never publishes a release and never holds a
   production credential; those jobs stay on GitHub-hosted runners.
5. **The kit's checks stay on GitHub.** Governance and proof, and every workflow the kit installs, run on GitHub-hosted runners
   (see below). Only the project's own heavy jobs move.

## Set up an ephemeral runner

The steps depend on GitHub's current runner application and on your machine and plan; check each against GitHub's
documentation for self-hosted runners before you rely on it.

1. **Prepare a disposable machine** `(verify)`: a virtual machine or a container that you can throw away and recreate from a
   clean image after each job, with no personal files, no saved logins and no keys on it, and with only the tools the heavy
   job needs. A machine you also work on is not disposable.
2. **Get a registration token for the one repository** `(verify)`: under the repository's Settings, Actions, Runners, "New
   self-hosted runner", or with a token that may administer the repository:

       gh api --method POST repos/{owner}/{repo}/actions/runners/registration-token --jq .token

   It expires after about an hour `(verify)`; use it at once and do not save it.
3. **Register the runner as ephemeral, with a label of its own** `(verify)`: from the runner application's folder,

       ./config.sh --url https://github.com/<owner>/<repo> --token <registration token> --ephemeral --labels heavy --unattended
       ./run.sh

   `--ephemeral` makes the runner take one job and then unregister itself; `heavy` is the label the job will ask for (any
   name of your own; the runner also carries `self-hosted` and its operating system's label).
4. **Recreate it after each job** `(verify)`: when `run.sh` ends, destroy the machine, start a fresh one from the clean image
   and repeat steps 2 and 3, by a script of your own on the machine that hosts it. Until a fresh runner registers, the next
   heavy job waits.
5. **Keep forks off it** `(verify)`: in a private repository, the setting that runs workflows from fork pull requests stays
   off (Settings, Actions, General, "Fork pull request workflows"), and the heavy job also checks that the pull request comes
   from this repository (the `if:` below).

## How a heavy job opts in

A job moves to the runner by asking for its labels in `runs-on`; every other job, and every workflow the kit installs, keeps
`runs-on: ubuntu-latest`. In the project's own workflow (not a file of the kit):

```yaml
jobs:
  heavy-tests:
    if: github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository
    runs-on: [self-hosted, heavy]
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - run: ./scripts/heavy-suite.sh   # the project's own heavy step
```

Governance and proof stay on GitHub-hosted runners: they are the trust anchor of every merge, the checks that `required_checks`
names and that the reviewers read, and they must run on a machine nobody on the project controls. Never change their
`runs-on`:

```yaml
  governance:
    runs-on: ubuntu-latest
```

A job on the runner is never one of `required_checks`, so a runner that is down never blocks a merge by itself; the project's
heavy job reports to the reviewers as any other check does. `minutes.py` lists jobs on a self-hosted runner and does not count
their minutes.

## When the runner is down

A job that asks for the runner's labels waits in the queue until a matching runner is online; GitHub cancels it if none comes
within a day `(verify)`. When the runner is down for longer than you can wait:

- **Fall back to hosted runners for that job**: set its `runs-on` back to `ubuntu-latest` in a small pull request, which spends
  hosted minutes again until the runner is back. To switch without editing the workflow each time, read the runner from a
  repository variable `(verify)`:

      runs-on: ${{ vars.HEAVY_RUNNER == 'self' && fromJSON('["self-hosted", "heavy"]') || 'ubuntu-latest' }}

  and set the variable `HEAVY_RUNNER` to `self` while the runner is up, or anything else to fall back.
- **Or use local mode** when the hosted minutes are gone as well: [local-mode.md](local-mode.md) says how to keep working with
  every check run on your own machine and every merge recorded.

Cancel a heavy job that is still waiting once you have fallen back, so that it does not start later on a runner that comes
back.
