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
   organisation that also holds public ones, and keep pull requests from forks off it: their code is not yours to run. An
   organisation with several private projects can instead share one pool limited to them by name:
   [one pool for an organisation](#one-pool-for-an-organisation).
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

## One pool for an organisation

An organisation with several AGK projects can run one pool of ephemeral runners that serves the heavy jobs of all of them,
with shared caches, so that a new project adds work for the pool instead of hosted minutes (brief #410, ADR-0224). The rules
above still hold for every runner of the pool; these are added:

- **A runner group limited to named private repositories.** The pool's runners belong to one organisation runner group whose
  repository access is "Selected repositories", each a private repository named one by one; never a public repository, and
  never "All repositories", which would take in a public one created later.
- **Ephemeral runners only.** Each runner takes one job and is then removed, as in rule 1. Start with one machine that
  recreates its runner after each job, and autoscale later, when the jobs wait too long, by starting more such machines.
- **Shared caches that hold no credential.** The caches that make a fresh runner fast (container layers, package managers'
  downloads, browsers for end-to-end tests) live on one volume that every runner mounts. The volume holds no credential: no
  token, key, login or configuration file with a secret, so a job that writes to it leaves nothing another project's job could
  use to act as it.
- **No deploy or production secret on any runner.** No job on the pool deploys, publishes or holds a production credential,
  and the job token has read permissions only (`permissions: contents: read`); a job that needs more stays on GitHub-hosted
  runners.
- **Governance and proof stay on GitHub-hosted runners.** The kit's governance and proof checks are the trust anchor of every
  merge in every project of the organisation, and no project moves them to the pool (see [how a heavy job opts
  in](#how-a-heavy-job-opts-in)).

### The job: the pool when the variable is set, GitHub-hosted runners otherwise

In each project's own workflow (not a file of the kit), the heavy job reads its runner from the repository variable
`AGK_HEAVY_RUNNER` and falls back to GitHub-hosted runners when the variable is unset, and its `if:` keeps a pull request from a
fork off the pool, while a push still runs the job:

```yaml
jobs:
  heavy-tests:
    if: github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository
    runs-on: ${{ vars.AGK_HEAVY_RUNNER || 'ubuntu-latest' }}
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - run: ./scripts/heavy-suite.sh   # the project's own heavy step
```

Set the variable to `self-hosted` `(verify)`: every self-hosted runner carries that label, so it picks the pool only while the
pool's group holds the repository's only self-hosted runners `(verify)` (step 4 below checks it), and `minutes.py` reads a job
as self-hosted by that label among the labels the job asked for. A label of the
pool's own alone (for example `heavy`) still runs on the pool, but `minutes.py` would count the job as hosted minutes. To step
back, delete the variable: the next run uses `ubuntu-latest`.

### What the person sets up

The kit sets up no runner, no runner group and no variable. Each is a step the person takes, with an owner's rights, in the
organisation's or the repository's settings; check each against GitHub's documentation for self-hosted runners and runner
groups, which depend on the plan:

1. **Create the runner group** `(verify)`: in the organisation's Settings, Actions, Runner groups, a new group with repository
   access "Selected repositories", naming each private project, and with public repositories not allowed.
2. **Start one ephemeral runner in the group** `(verify)`: as in [set up an ephemeral runner](#set-up-an-ephemeral-runner), but
   with an organisation registration token (`gh api --method POST orgs/{org}/actions/runners/registration-token --jq .token`)
   and `./config.sh --url https://github.com/<org> --runnergroup <group> --ephemeral --unattended`, on a machine that mounts the
   cache volume and holds no credential.
3. **Keep forks off** `(verify)`: in the organisation's and each repository's Settings, Actions, General, the setting that runs
   workflows from fork pull requests stays off; the `if:` above is the second guard.
4. **Check that the repository reaches no other self-hosted runner** `(verify)`: in the repository's Settings, Actions, Runners,
   the only self-hosted runners listed are the pool's. That means no runner registered on the repository (the one-project setup
   above), and an organisation Default group that holds no runner or does not include the repository; a runner there also
   carries `self-hosted` and could take the job.
5. **Set the variable in each project that opts in** `(verify)`: in the repository's Settings, Secrets and variables, Actions,
   Variables, `AGK_HEAVY_RUNNER` with the value `self-hosted`, or `gh variable set AGK_HEAVY_RUNNER --body self-hosted` in the
   repository. A project without the variable keeps its heavy job on GitHub-hosted runners.

### How to measure it

`python3 scripts/agk/minutes.py` already lists a job on a self-hosted runner and counts it as not billed
([project-ci.md](project-ci.md#how-many-minutes-are-left)). In each project that opts in, run it one week before the variable is
set and note the estimate and the minutes per merged pull request; run it again one week after and compare: the heavy job's
minutes should leave the estimate and appear as jobs on a self-hosted runner. Compare the time the heavy job waits in the queue
too: when it grows, add a machine to the pool.

## A batch run of ready pull requests

When several pull requests are ready at once, each one's heavy job runs the project's heavy checks on its own head, so five
ready pull requests cost five heavy runs. `python3 scripts/agk/batch.py PR [PR...]` (brief #436, ADR-0235) runs them once for
the batch instead: it fetches each head (`refs/pull/<n>/head`, with git alone), merges the heads in the order given onto the
default branch in a scratch worktree, leaves out a head that does not merge cleanly as `conflict`, and runs the heavy command
(`--command CMD`, by default `make -f agk.mk agk-project-test`) once, under the heavy-step lock. When that run passes, each
pull request is `batch-green <sha12>`; only when it fails does the command run again on each pull request's own head merged
onto the default branch, and the red ones are named. A green batch of five therefore costs one heavy run instead of five.

A batch run replaces the per-pull-request heavy runs when all of these hold:

- **Several ready pull requests.** Two or more are ready for review at the same time and each would otherwise run the same
  heavy check; for one pull request a batch saves nothing.
- **On the pool or a local machine.** It runs where the heavy jobs already run: a runner of the pool (above), or a person's or
  a session's own machine in [local mode](local-mode.md), where the heavy-step lock keeps it to one heavy run at a time.
- **Only the project's heavy checks.** The kit's governance and proof still run per pull request on GitHub-hosted runners, as
  every rule above says; a batch never stands in for them.
- **A person decides what it stands in for.** The command only reports: it labels, merges and posts nothing, and changes no
  repository setting. `--record FILE` writes the batch result as a record in the schema of a local run
  ([local-mode.md](local-mode.md)), so it is evidence a reviewer can check; whether that evidence replaces a pull request's own
  required heavy check is the person's decision, not the kit's.

GitHub's merge queue does the same job inside GitHub where the plan and the repository's visibility allow it; turning it on is
a repository setting and a person's decision, and the kit never turns it on. Where it is on, the batch command is not needed.
