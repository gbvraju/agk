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

Signs: the checks of a new head never start (no run appears on the Actions tab for it), or every job fails at once with the
refusal message that recent account payments have failed or that the spending limit needs to be increased, before any step
runs. A billing block shows as red jobs carrying that message, not as missing checks. A builder says so in one line of its
`Report:` ("checks refused: Actions is blocked"), never as a red check of its own change. If a job starts, runs its steps and
fails, you are not in local mode: read the failing job's log.

Heads pushed before the workflows were disabled keep those red refusals. Once the workflows are off, each builder must push a new
head (an empty commit is enough) so that its checks show as never reported rather than red.

## Enter local mode

A person with admin on the repository does this once, in a terminal on their own machine with a logged-in `gh`.

1. **Disable the workflows**, so that nothing queues and nothing is billed when Actions returns. With the kit, one command
   lists every active workflow, the kit's and the project's, and the call that disables each; it is a dry run and changes
   nothing until you add `--write`, which makes the calls and prints one line per workflow (a refused call is reported, with
   the call to run by hand, and the rest are still made):

       python3 scripts/agk/local_mode.py enter
       python3 scripts/agk/local_mode.py enter --write

   It needs a token that may change workflows (Actions write is enough), so the person runs it in their own terminal:
   `--write` refuses to run inside an agent session, and the kit's settings deny it to a session. When every workflow is
   already off by hand, `enter` takes the day of the earliest as the start, opens the record issue of step 2 in the form
   `leave` reads (`--write`, only when none is open) and prints the exact `leave --since` command to keep. For a person without the
   kit, disable each workflow with one command (`gh workflow disable` takes the file name):

       gh workflow disable agk-brief.yml
       gh workflow disable agk-route.yml
       gh workflow disable governance.yml
       gh workflow disable proof.yml
       gh workflow disable drift-audit.yml
       gh workflow disable merger.yml
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

3. **Unfreeze the labels** (only with a kit before brief #1212; from it on `route.py --all` relabels them, see What is
   lost). The router's `agk:ci-running` label stays on every pull request that had it when Actions stopped,
   and `review-queue` skips such a pull request as "checks running". Remove it from each open pull request that carries it, one
   line per pull request:

       gh pr edit <n> --remove-label agk:ci-running

4. **The merge rule.** The ruleset of the default branch requires the `governance` check, which no longer reports. Merging
   while the check is missing is the admin's call, made pull request by pull request on the local evidence below: no session
   ever changes the ruleset, merges or bypasses it.

## What a builder runs before asking for review

A builder runs the governance checks and its own proof on its head, on its own machine, and records what ran in a file
instead of pasting output into the pull request body. Several sessions on one machine take turns through one lock, so two
heavy runs never compete for the same memory and disk: each heavy step, governance included, runs under `python3 scripts/agk/lock.py run --name heavy --session <id> -- <command...>`, which waits
its turn, runs the command without a shell and releases the lock when it ends, also when it fails or is interrupted. Each line
stands alone, so the lines can be run one by one, as an agent runs them:

    base=$(git merge-base HEAD origin/main)
    python3 scripts/agk/lock.py run --name heavy --session <id> -- make governance AGK_BASE="$base"
    python3 scripts/agk/lock.py run --name heavy --session <id> -- make test
    python3 scripts/agk/lock.py run --name heavy --session <id> -- python3 scripts/agk/proof.py --base "$base" --head HEAD
    python3 scripts/agk/check_pr_body.py --draft false body.md
    python3 scripts/agk/lock.py run --name heavy --session <id> -- python3 scripts/agk/prepush.py --body body.md --record <record file>

The last line is the record the conductor checks. `prepush.py --record <file>` (brief #374) runs the body check, lint,
governance, the secret scan and the selected tests, in that order, and writes one JSON record of what ran: the head and
base, whether the work tree was clean, and each step's command, exit code and a digest of its output, never the output
itself. Keep the record file outside the repository (a
record inside it makes the tree dirty) and where the conductor can read it, on a machine you share. Run it on a clean tree:
a record of a dirty tree is reported as such.

In PowerShell write `$base = git merge-base HEAD origin/main` and `python` where `python3` is not on the path; the `lock.py`
lines are the same (`make governance AGK_BASE=$base` gives the base to the checks as an environment variable on every platform). While another session holds the lock, `lock.py` prints one line at once and then one a
minute, `lock heavy: waiting; held by <session> (pid <n>, host <name>) for <m> min`; `--timeout <seconds>` gives up with exit 3.
The lock is a folder `agk-lock-heavy` in the user's temp folder (or `lock_dir` in `agk.toml`), outside every repository, so it is
never committed and is shared by all of the machine's projects. A lock left by a session that died is cleared by the next run,
with a line saying so: when its process no longer runs on this machine. A holder that still runs here is never cleared, whatever
its age and also after the machine slept; a lock of another host is cleared only when its heartbeat, written about once a minute,
is older than `lock_stale_minutes` (120 by default, ADR-0295). `python3 scripts/agk/lock.py status --name heavy` prints the holder or `free` and changes nothing. `make test` runs the
kit's checks and the project's own tests (`project_tests` in `agk.toml`); `body.md` is a copy of the pull request body. The
secret scan of the governance workflow is not part of `make governance`: `prepush.py` runs the same scanner over the branch's
commits, and fails, naming the tool and the version the workflow pins, when the scanner is not installed (ADR-0306): install
it first, since a scan is never skipped in any mode. `doctor.py` prints whether the scanner is installed and at which version.

Then add the `Evidence:` line that prepush printed to the pull request body, beside `Verified:`, and one line that names
the head it ran on:

    Evidence: prepush schema 1, head <sha12>, <n> steps ok, record <sha12 of the file>
    Local evidence: <head sha> governance ok; tests <n> passed; proof <outcome>; pr body ok; secret scan <result>

with each figure copied verbatim from the output. A new push makes both lines stale: run again and replace them. Mark the pull
request ready only when they name the current head.

### The stop hook between turns

The stop hook (`.claude/hooks/stop_check.py`) runs at the end of every Claude turn, and in local mode it runs on this machine.
It runs only the governance checks that the session's own changes need (brief #1254, ADR-0531): it reads the changed files with
local git (the work tree and the branch's commits that are not on the default branch), runs nothing and lets the turn end at
once when there are none, runs the checks that read those files when every one is a documentation or configuration path that
`scripts/agk/governance_map.py` knows, and runs the full `make -f agk.mk agk-governance` for any other path. A check that runs
still keeps the turn going while it is red. Each run prints one line, `stop check: <n> checks for <m> changed files, <s> s` or
`stop check: no changes`. `[flow] stop_check` in `agk.toml` chooses the mode: `"changed"` (the default), `"full"` (every check on
every turn, as before) or `"off"` (none; refused when `review_mode` is `"solo"`, which has no other gate before a push). The
gates are unchanged: `prepush.py` before every push, CI's governance and the conductor's review still run every check.

## What the conductor checks instead of CI

Step 1 of the conductor's protocol (CI first) has nothing to read in local mode, so the conductor runs governance itself:

1. Run `python3 scripts/agk/session.py review-queue --all`. A pull request whose required checks never reported is listed with
   the reason `checks not reported`; one still labelled `agk:ci-running` shows as a skip line, and the person removes that label
   (see Enter local mode). That reason, and the one open record issue, is how the conductor knows it is in local mode. The
   exception to CI first holds only while the one local-mode record issue is open, and only for required checks that never
   reported on that head: a red check still blocks a clearing verdict.
2. Check the builder's record against the head with one command (brief #434):

       python3 scripts/agk/evidence.py check <record file> --head <sha>

   It reports `stale` when the record names another head, `dirty` when the builder's tree was not clean and `failed` when a
   recorded step failed; otherwise it adds a detached worktree of the head in a temporary folder, runs governance there with
   the record's base, rebuilds from the head the commands prepush runs (a recorded command that is not one of them is
   reported as `not what prepush runs` and never run), re-runs a sample of them (one by default, `--sample N` for more; the
   same head always gives the same sample) under the heavy-step lock, compares their exit codes with the record's and
   removes the worktree. A different
   output digest is a note, not a failure. It posts nothing and ends with one line to quote:
   `Evidence check: agrees|differs, head <sha12>, record <sha12>, governance <outcome>, sample <k> of <m> same exit`, exit 0
   when the record agrees and 1 when it differs. Its `record` digest must equal the one in the builder's `Evidence:` line.
3. Read the builder's `Local evidence:` line. It must name the head the verdict names; a line for an older head is no evidence.
4. Name in the verdict the local evidence it relied on, in one line:

       Local evidence: <head sha> Evidence check: agrees, ... (conductor's run); proof <outcome>, tests <n> passed (builder's line)

Without a record (a builder on a kit older than brief #374), re-run governance by hand as before: `git worktree add <scratch>
<sha>`, then `env -i PATH="$PATH" HOME=<scratch> AGK_BASE=<base sha> make -C <scratch> governance`, then remove the worktree.

A verdict in local mode that clears a head without that line clears nothing.

## Tidying finished builders

Each builder session gets a worktree and a branch of its own, and they stay after the pull request merges; `git branch -d`
refuses a squash-merged branch, so removing them by hand is slow and risky. From the main clone, run:

    python3 scripts/agk/session.py tidy

It changes nothing: it prints `remove <path> <branch> #<pr> merged|closed` for each builder worktree or local branch whose pull
request is merged or closed, whose tip is that pull request's last head, with no uncommitted or untracked files and no ignored file
outside a cache folder, unchanged for an hour, not locked, not the current worktree or the main clone, and not named as running by
a lock or queue file of `lock.py`; every other item prints `kept: <reason>`. A builder branch is the `[tidy] branch_prefix` of
`agk.toml` followed by a number; `[tidy] min_idle_minutes` (60) and `[tidy] caches` set the rest. A failed read of GitHub keeps the item. Add `--apply` to remove exactly the listed candidates (`git worktree
remove` without `--force`, then `git branch -D` after the tip is checked again); remote branches are never deleted, and `--json`
prints the same as JSON. The conductor runs `tidy --apply` at its start and after each merge it makes; a builder never does.
`doctor.py` prints `tidy: <n> finished worktrees; run session.py tidy` when more than five have piled up.

## Running unattended

In local mode nothing in the cloud starts a session: the launcher tasks of the cloud need Actions and cloud sessions. So that a
night is not lost when a builder or the conductor dies of a crash or a memory hit while nobody is watching, set up these four
things on the machine that runs the sessions, in this order (brief #1237, ADR-0525). Each change to `agk.toml` is a protected
change with an ADR in the same pull request.

1. **The adapter.** The kit installs two launch adapters, which a project then owns: `scripts/start-session-windows.ps1`
   (a Windows Terminal tab per session, in its own worktree; it needs PowerShell 7) and `scripts/start-session-local.sh`
   (Linux and macOS: a GNOME Terminal tab when a desktop is there, otherwise the background, with its output in the worktree's
   `.agk-session.log`). Each writes `<worktree>/.agk-session-exit` when its session ends. Set the one for the machine in the
   `[flow]` table, and try it once by hand as [the getting-started guide](getting-started.md) shows ("Automatic starts after
   a review pass"):

       launch_adapter = "pwsh -NoProfile -File scripts/start-session-windows.ps1"
       launch_adapter = "bash scripts/start-session-local.sh"

   `python3 scripts/agk/doctor.py` prints `launch adapter: auto_start is on and ...` with the file and the line to set when
   `auto_start` is on and the adapter is missing.
2. **`auto_start = true`** in the same table. The conductor then restarts a builder whose pull request is handed over or
   silent through that adapter, and the watchdog below starts the conductor through it; with it off, nothing starts.
3. **The capacity.** `[capacity] profile = "auto"`, with `builder_memory_gb` (in `[flow]` or `[capacity]`; the smaller
   counts) set to the memory one builder needs with its containers, so that the plan starts no more builders than the
   machine's free memory holds.
4. **The watchdog.** `python3 scripts/agk/conductor.py watchdog` is one pass, never a loop. It starts nothing while the project
   is paused, or unless `auto_start` and `launch_adapter` are set in the checkout and on the default branch alike. It reads the
   conductor's lease on the plan issue (`plan_issue` of the `[flow]` table; without it, nothing starts): while a live
   conductor holds it, it prints `watchdog: lease held by <name> until <time>; nothing started`. When the lease is free or
   expired, it prints the machine's free memory against `builder_memory_gb`, starts nothing when that is below one builder
   (`nothing started: free memory is below one builder`), and otherwise starts one conductor through the adapter, named
   `conductor-local` (or `--session NAME`), which takes the lease itself; the lease keeps two from running. It posts nothing.
   To run it every 30 minutes, print the one scheduler line for the machine and run that line yourself; the command runs
   nothing:

       python3 scripts/agk/conductor.py watchdog --install

   On Windows it is a `schtasks /Create /SC MINUTE /MO 30 /TN "AGK conductor watchdog" ...` line, elsewhere a crontab line
   (add it with `crontab -e`). Each runs `git fetch` in the checkout and then the pass `(verify: a scheduled task and a cron
   job start with a short PATH; check that python, git, gh and the adapter's terminal are found, and that the task runs
   while you are signed in, which a terminal tab needs)`.

## What is lost

Say it plainly to everyone working on the project:

- **Router labels from the local evidence.** The router's job does not run, so `python3 scripts/agk/route.py --all` is run
  once per review pass with a person's own `gh` (brief #1212, ADR-0513). Until the conductor's guard allows that command, a
  guarded conductor cannot run it: a person, or a conductor session without the guard, runs it. While the one record
  issue is open, a required check that never reported on a head is read from the builder's newest `Report:` on that head: its
  `Evidence:` line naming the head counts as green, a `prepush: stopped at ...` or `failed: step ...` line in it as red
  (`agk:ci-red`), and no such line leaves the pull request with the builder (`agk:build`), never at `agk:ci-running`. A check
  that did report is read as before. `agk:merge-ready` also needs the verdict's `Local evidence:` and `Evidence check: agrees`
  for the head, as the guarded merge reads them. `session.py watch` then also ends on a label change, and step 3 of Enter
  local mode (the unfreeze) is no longer needed. So that the labels move, a builder puts the `Evidence:` line in its
  `Report:` as well as in the body.
- **No server-side proof.** Governance, the tests and proof ran on the builder's and the conductor's machines, not on a clean
  runner that nobody controls. Nothing GitHub records shows that they ran.
- **No scheduled runs.** The drift audit, the metrics and the weekly report do not run until local mode ends.
- **Every merge is the person's call.** The required check is missing, so a merge rests on the local evidence of the builder and
  the conductor. The person who merges posts one comment on the record issue: `Local merge: #<n> <head sha> <evidence>`.

With `auto_merge = true`, the conductor merges a cleared pull request itself through the guarded command, which in local mode
needs the verdict's `Local evidence:` and `Evidence check: agrees` for the head and posts its `Auto merge:` line on this record
issue in place of `Local merge:`. [The auto-merge guide](auto-merge.md) says how to set it up, what each line means and how to stop it.

## Leave local mode

When Actions runs again (minutes renewed, billing fixed, the outage over):

1. **Re-enable the workflows.** With the kit, one command takes the start of local mode from the day the record issue names
   (`Local mode since YYYY-MM-DD`), lists every workflow disabled by hand since then and the call that enables each, the pull
   requests merged on local evidence since then, and the state of the catch-up run; it is a dry run until you add `--write`,
   which reads the merges first and then makes the calls:

       python3 scripts/agk/local_mode.py leave
       python3 scripts/agk/local_mode.py leave --write

   Run `leave` again after the next merge to read the catch-up: one line per check of `required_checks` on the head of the
   default branch, `catch-up: not run yet` until one runs, then `catch-up: green`, or a red line that says to file a
   priority-0 brief naming the failing run and the merges. Without an open record issue, give the day local mode began as
   `--since YYYY-MM-DD`; without either, `leave` enables nothing and says the start is unknown. A workflow disabled before
   local mode (one a person turned off for good, or one GitHub disabled for inactivity) is named and left as it is. A read
   that does not answer is printed as `unknown`, never as 0, and the command exits 4. For a person without the kit, enable
   each workflow with one command, and the project's own the same way:

       gh workflow enable agk-brief.yml
       gh workflow enable agk-route.yml
       gh workflow enable governance.yml
       gh workflow enable proof.yml
       gh workflow enable drift-audit.yml
       gh workflow enable merger.yml
       gh workflow enable metrics.yml
       gh workflow enable product-report.yml

2. **Let one pull request run green.** Push a new head to an open pull request (or open a small one) and wait until governance
   and proof both end green on GitHub. Its merge runs governance on the default branch again, which checks every commit merged
   in local mode.
3. **Close the record issue** with a last comment that names that pull request and its green run. From then on the normal
   rules apply again, and a verdict names CI, not local evidence.

If the first green run finds something a local run missed, file it as an issue and link it from the closed record issue.
