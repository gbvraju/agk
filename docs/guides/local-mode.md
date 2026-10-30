# Local mode: keep working when GitHub Actions is blocked

Local mode is how a project keeps building when its GitHub Actions jobs cannot run, and how it comes back. Every check still
runs, on a machine you control instead of on GitHub, and every merge is recorded in one place. Follow the steps as written; the
point of this page is that nobody has to invent the process under pressure (brief #322, ADR-0182).

Read it once before you need it. In a pilot the team found each step by hand over several hours, and a person nearly pasted a
command into the wrong window.

## When to use it

Use local mode only when GitHub refuses to start the jobs, never because a check is red:

- **Minutes exhausted.** A private repository has a monthly allowance of Actions minutes. When it runs out, every job is refused,
  the router's job included.
- **Billing blocked.** A failed payment or a spending limit of zero stops every job with a message that recent account payments
  have failed or that the spending limit needs to be increased.
- **An outage.** GitHub's status page reports that Actions is down or degraded for more than an hour.

Signs: the pull request's checks never start (no run appears on the Actions tab for the new head), and the pull request keeps
whatever `agk:` label it had. A builder says so in one line of its `Report:` ("checks never started: Actions is blocked"), never
as a red check. If only some jobs are refused, or a job starts and fails, you are not in local mode: read the failing job's log.

## Enter local mode

A person with admin on the repository does this once, in a terminal on their own machine with a logged-in `gh`.

1. **Disable the workflows**, one command per workflow, so that nothing queues and nothing is billed when Actions returns
   (`gh workflow disable` takes the file name):

       gh workflow disable agk-route.yml
       gh workflow disable governance.yml
       gh workflow disable proof.yml
       gh workflow disable drift-audit.yml
       gh workflow disable metrics.yml
       gh workflow disable product-report.yml

   Disable the project's own workflows the same way, by their file names under `.github/workflows/`. `gh workflow list --all`
   shows each one and its state. Where `gh workflow` is not available, the REST form is
   `gh api --method PUT repos/{owner}/{repo}/actions/workflows/<file>/disable` (and `/enable` to leave).

2. **Open the record issue**, the one place where every merge in local mode is written down:

       gh api --method POST repos/{owner}/{repo}/issues -f title="Local mode since $(date -u +%F)" \
         -f body="Actions is blocked: <minutes exhausted | billing blocked | outage>. One comment per merge: Local merge: #<n> <head sha> <evidence>."

   `gh api` fills `{owner}/{repo}` from the checkout. Keep exactly one such issue open; the conductor and the builders find it
   by its title.

3. **The merge rule.** The ruleset of the default branch requires the `governance` check, which no longer reports. Merging
   while the check is missing is the admin's call, made pull request by pull request on the local evidence below: no session
   ever changes the ruleset, merges or bypasses it.

## What a builder runs before asking for review

A builder runs the governance checks and its own proof on its head, on its own machine, and pastes the result in the pull
request body. Several sessions on one machine take turns through a lock file, so two heavy runs never compete for the same
memory and disk.

    lock="$(git rev-parse --git-common-dir)/agk-heavy.lock"
    until mkdir "$lock" 2>/dev/null; do sleep 30; done      # wait for the lock; mkdir is atomic
    trap 'rmdir "$lock"' EXIT
    base=$(git merge-base HEAD origin/main)
    AGK_BASE=$base make governance
    make test
    python3 scripts/agk/proof.py --base "$base" --head HEAD
    python3 scripts/agk/check_pr_body.py --draft false body.md

The lock is a directory inside the repository's git directory, so it is never committed and needs no ignore line. If a run is
killed, the lock stays: a person removes it with `rmdir` once no heavy run is going on. `make test` runs the kit's checks and
the project's own tests (`project_tests` in `agk.toml`); `body.md` is a copy of the pull request body. The secret scan of the
governance workflow is not part of `make governance`: run the same scanner over the branch's commits when it is installed, and
write `secret scan: not run` when it is not.

Then add one line to the pull request body, beside `Verified:`, that names the head it ran on:

    Local evidence: <head sha> governance ok; tests <n> passed; proof <outcome>; pr body ok; secret scan <result>

with each figure copied verbatim from the output. A new push makes the line stale: run again and replace it. Mark the pull request
ready only when the line names the current head.

## What the conductor checks instead of CI

Step 1 of the conductor's protocol (CI first) has nothing to read in local mode, so the conductor runs governance itself:

1. Run `python3 scripts/agk/session.py review-queue`. A pull request whose required checks never reported is listed with the
   reason `checks not reported`; that reason, and an open record issue, is how the conductor knows it is in local mode.
2. Re-run governance on the exact head with the bounded run of the conductor role: `git worktree add <scratch> <sha>`, then
   `env -i PATH="$PATH" HOME=<scratch> AGK_BASE=<base sha> make -C <scratch> governance`, then remove the worktree.
3. Read the builder's `Local evidence:` line. It must name the head the verdict names; a line for an older head is no evidence.
4. Name in the verdict the local evidence it relied on, in one line:

       Local evidence: <head sha> governance ok (conductor's run); proof <outcome>, tests <n> passed (builder's line)

A verdict in local mode that clears a head without that line clears nothing.

## What is lost

Say it plainly to everyone working on the project:

- **No router labels.** The router does not run, so no `agk:` label moves and `session.py watch` ends only on a verdict, a merge,
  a close or a conflict. The conductor finds its work with `review-queue`, not with labels.
- **No server-side proof.** Governance, the tests and proof ran on the builder's and the conductor's machines, not on a clean
  runner that nobody controls. Nothing GitHub records shows that they ran.
- **No scheduled runs.** The drift audit, the metrics and the weekly report do not run until local mode ends.
- **Every merge is the person's call.** The required check is missing, so a merge rests on the local evidence of the builder and
  the conductor. The person who merges posts one comment on the record issue: `Local merge: #<n> <head sha> <evidence>`.

## Leave local mode

When Actions runs again (minutes renewed, billing fixed, the outage over):

1. **Re-enable the workflows**, one command per workflow, and the project's own the same way:

       gh workflow enable agk-route.yml
       gh workflow enable governance.yml
       gh workflow enable proof.yml
       gh workflow enable drift-audit.yml
       gh workflow enable metrics.yml
       gh workflow enable product-report.yml

2. **Let one pull request run green.** Push a new head to an open pull request (or open a small one) and wait until governance
   and proof both end green on GitHub. Its merge runs governance on the default branch again, which checks every commit merged
   in local mode.
3. **Close the record issue** with a last comment that names that pull request and its green run. From then on the normal
   rules apply again, and a verdict names CI, not local evidence.

If the first green run finds something a local run missed, file it as an issue and link it from the closed record issue.
