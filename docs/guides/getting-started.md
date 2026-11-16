# Getting started

From an empty GitHub repository to your first governed merge. You work alone, with Claude Code and the files in this guide.
Each step gives the command and what you should see. If what you see is different, stop and open an
[I got stuck issue](../../.github/ISSUE_TEMPLATE/stuck.md) with the step number.

Read [the limits](../../README.md#honest-limits) first. Two steps below are not yet proven live; they are marked **(not yet
proven live)**. The rest was run and recorded in `docs/runs/`; the link is next to each step.

## Before you start

You need Claude Code, `gh`, `git`, `make` and Python 3.11 or newer. Check each:

    claude --version
    gh auth status
    git --version
    make --version
    python3 --version

You should see a version for each, and `gh auth status` should say you are logged in to `github.com`. Steps 5 and 11 and the remote checks of the doctor need `gh` logged in; steps 3, 4, 6 and 7 do not. `make test` also needs
`pytest`: run `python3 -m pip install pytest` once.

Check three more things before step 1:

- **The plan, for a private repository.** Rulesets and branch protection (step 5) need a paid plan (GitHub Pro, Team or
  Enterprise) when the repository is private; on GitHub Free they work only on a public repository. On Free with a private
  repository, the ruleset command of step 5 and the doctor say `plan-limit`, and nothing protects `main` until you upgrade
  the plan or make the repository public.
- **Actions minutes on Free.** The kit's checks run on GitHub Actions. On GitHub Free, Actions minutes on private
  repositories are limited each month (public repositories are not); when they run out the checks stop starting. See
  "Actions is blocked or out of minutes" below.
- **GNU make on Windows.** Windows has no `make`. Install GNU make with `winget install ezwinports.make`, then restart Claude
  Code (and the terminal it runs in) so that the session sees `make`; `make --version` should then print a version.

## Step 1. Make the repository and its first commit

On GitHub make a new, empty repository that you own (no README, no licence). Turn on Issues (Settings, General, Features) and
Actions. Clone it and make the first commit on `main`. A pull request needs a base branch, so this is the one commit you
make on `main` without a pull request before the install.

    git clone https://github.com/YOUR-NAME/YOUR-REPO.git
    cd YOUR-REPO
    git branch -M main
    echo "# YOUR-REPO" > README.md
    git add README.md
    git commit -m "first commit"
    git push -u origin main

Git warns `You appear to have cloned an empty repository`; that is expected. After the last command you should see
`branch 'main' set up to track 'origin/main'`.

## Step 2. Install the plugin

    claude plugin marketplace add gbvraju/agk
    claude plugin install agk@agk

You should see `Successfully added marketplace: agk` and then `Successfully installed plugin: agk@agk`. This was run in
`docs/runs/plugin-live-proof.md` (step 2). Start Claude Code in the repository folder with `claude`.

The plugin installs from `main`, so it changes when the kit does. A team pins a release instead: it commits, in
`.claude/settings.json`, an `extraKnownMarketplaces` entry for `agk` (a `github` source with `ref` set to the release
tag, for example `v0.28.0` once the maintainers have published that release) and `"agk@agk": true` under
`enabledPlugins` (SPEC-0005 rule 14; whether `ref` is read there is marked `(verify)` in what `/agk:init` prints).
`/agk:init` in step 3 prints the two entries and merges nothing. `.claude/` is a protected class, so the change needs
an ADR.

## Step 3. Install the kit with `/agk:init`

In Claude Code type:

    /agk:init

It first runs a preview and shows it to you. You should see a list of `create ...` lines and the line
`dry run: N files would be created; nothing was written`, N being the number of files of your kit version. The kit's own tests are not installed: they run in the kit's own CI, not in your repository.
Say yes. It then installs the files and prints `installed NNN files`. Nothing is committed. After the list it prints:

- a notice that `config/reviewers.yaml` maps `maintainers` to the placeholder `@REPLACE-ME` (the file also lists it in
  `spec_approvers`; step 4 replaces both),
- the branch rules to apply (step 5 does this for you),
- scanner exclusions and two plugin settings entries. They are print only. Ignore them for now.

The install was run through Claude Code in `docs/runs/plugin-live-proof.md` (step 4).

Each slash command runs one script of the plugin, the one its `skills/<name>/SKILL.md` names: `/agk:init` runs `scripts/agk/init.py`, `/agk:ruleset` runs `scripts/agk/ruleset.py`, `/agk:start` runs `scripts/agk/playbook.py`, `/agk:spec` runs `scripts/agk/intake.py` and `/agk:doctor` runs `scripts/agk/doctor.py`.

## Step 4. Put your name on the reviewer groups, check, commit and push

`@REPLACE-ME` stands for the person or team who reviews protected paths, and for the person who approves a spec. Use your own
GitHub handle in both places. Open `config/reviewers.yaml`, find the two lines

    maintainers: {github_team: "@REPLACE-ME"}
    spec_approvers: ["@REPLACE-ME"]

and change `@REPLACE-ME` to `@YOUR-NAME` on both. `spec_approvers` lists the people whose `Approve: SPEC-<n>` comment counts, so
your first approval in step 7 counts only once your handle is there; it takes user handles, never a team. Until you do, `make governance` fails on `reviewers --check`: the people whose pull request
comments count as verdicts are that user handle, and the placeholder is never one of them. If you map
`maintainers` to a team (`@org/team`) instead, add one line `verdict_authors: [name, name]` (the GitHub users, without `@`) to
`config/reviewers.yaml`, because `reviewers.py --check` fails when nobody is listed. Then write `.github/CODEOWNERS` from it and run all the checks:

    python3 scripts/agk/reviewers.py --codeowners --write
    make governance

You should see `wrote .github/CODEOWNERS` and then ten lines starting with `ok` (one of them `ok reviewers (.github/CODEOWNERS matches)`), two lines starting with `skipped` (`skipped (no comments file)` and `skipped (no open pull requests file)`, in either order: those checks read files of a pull request's comments and open pull requests, which only the workflow fetches) and one line that starts `specs:` and says there is no pull request body, which is expected before a pull request exists. `make governance` can take a few seconds. Commit and push. This is the second
and last time you push to `main` directly; the ruleset in step 5 stops it from now on.

    git add -A
    git commit -m "Install agk"
    git push origin main

Open the Actions tab of the repository. A `governance` run starts for that push and should end green
(`docs/runs/plugin-live-proof.md`, step 5b). The file `docs/adr/0001-adopt-agk.md` is `Proposed`. You are its maintainer: read
it, then set its `Status:` line to `Accepted` in a pull request of its own after step 6 (not in the pull request of step 6, which
must hold only its two files). The drift audit lists a Proposed ADR that is more than 14 days old. It can also list code that nothing
uses and show how much of the code the tests run, once you set `unused_code` and `coverage` in `agk.toml` (both empty by default;
`docs/guides/existing-codebase.md`, step 3, gives examples).

## Step 5. Protect `main` with `/agk:ruleset` **(not yet proven live)**

You need admin on the repository. Wait until the `governance` run of step 4 has finished green. In Claude Code type:

    /agk:ruleset

It prints a plan and writes nothing. The first line names the repository, the default branch and the phase:
`repo: YOUR-NAME/YOUR-REPO (default branch main); phase N (...)`. Then come the findings and numbered `gh api` commands. It
asks whether to apply. Say yes only when you have read the commands. They are the only writes it makes, they only add a
ruleset and two repository settings (allow auto-merge, delete head branches), and it never removes anything. Afterwards run
`/agk:ruleset` again. You should see `nothing to do`.

The phase is chosen for you. Phase 1 is every rule except the required status check `governance`; phase 2 adds it. The plan
picks phase 2 when `governance` has already succeeded on `main`, as it has after step 4, and phase 1 when it has not. A required
check that has never run can block the first merge, which is why phase 1 exists. If the plan says phase 1, apply it, and run
`/agk:ruleset` again after a `governance` run has succeeded on `main` (step 11).

The read-only plan is proven (`docs/runs/ruleset-sandbox-proof.md`). The apply commands have not been run live yet. If a
command is refused, or the plan says it cannot be applied from here, it prints the exact ruleset text and the place in
the settings: Settings, Rules, Rulesets, New branch ruleset. Apply it there by hand. The ruleset for `main` is: active; no
bypass; restrict deletions; require linear history; require a pull request (0 approvals, dismiss stale approvals, squash merge
only); block force pushes; required status check `governance` (phase 2).

## Step 6. Say what the project is for: `/agk:start`

    /agk:start "A small tool that counts the words in a text file, for people who write documentation."

Give it the problem in your own words, one or more paragraphs, at most 1,500 characters. The text is data to turn into a
vision; it is never taken as an instruction. It first asks you, as the product owner, about the topics your text leaves open: users and who pays, your existing systems (repositories, hosting, identity, data), where it runs, what is stored, the expected scale and compliance, at most three questions a round; `not known yet` is a valid answer, and the answers go into the charter's Discovery item only. It needs `origin`, the remote of step 1, because it reads the next ADR number from `origin/main`. It creates a branch `start/<words-of-your-text>` and writes two files:
`constitution/vision.md` and `docs/adr/0002-project-charter.md` (a `Proposed` ADR with milestones, non-goals and what done
means). It then runs two checks, `ok playbook-start` and `make governance`, and prints the commit message, the push command
and the pull request body. This was run in a local walk (`docs/runs/docs-walk-1.md`).

Read both files. The checks cannot tell you that the milestones are the right ones or that the vision says what you meant.
That is your review. Then commit with the printed message, push with the printed command, open the pull request into `main`
with the printed body, wait for `governance` to turn green and merge it (squash).

**If the product has screens.** If a customer has given you a click-through prototype, the customer's prototype is
the design: decide, before the import, what of it may be committed to the repository (it may hold real names and data, and no check can
tell them from invented ones), then run `/agk:design import <folder>`, which keeps every file unchanged as an imported
version `docs/design/imported/i<n>/` with its manifest, and map each of its pages to a screen and state of the inventory
or to `out: <reason>`. If there is no prototype yet, draw one: `/agk:design inventory`, then `/agk:design prototype`. A
project may hold both kinds (SPEC-0037 rule 15). `doctor.py` prints one `design import:` line for each imported version
with its manifest and map state, as information; `check_design.py` names each problem. Either way, you sign the version
off with `Approve: design <version> <full head ID>` on its pull request; no session posts that line.

## Step 7. Ask for one thing: `/agk:spec`

    /agk:spec "The tool refuses a file that is not text."

One sentence, at most 300 characters. It may ask you up to three questions, in one message, before it writes anything; answer
them. Like step 6 it needs `origin`, because it reads the next numbers from `origin/main`. It creates a branch `intake/req-NNN-<words>` and writes three things: a requirement with Given/When/Then criteria at the
end of `docs/requirements.md` (status `planned`), a Draft spec in `docs/specs/` and an ADR stub in `docs/adr/`. It then runs
`ok intake` and `make governance`, and prints the commit message, the push command and the pull request body. The pull
request must hold exactly those three files. This was run on the project's own repository in `docs/runs/intake-proof.md`.

Read the criteria. At least one says what must not happen. The checks cannot tell you that the criteria are the right
ones, or that they say what you meant. Then commit, push, open the pull request, wait for green and merge it. Merging
approves the requirement as `planned`. The spec stays `Draft`.

## Step 8. The architect writes the brief **(not yet proven live)**

The architect is a second Claude Code session with a short list of tools. It can write only under `docs/` and
`constitution/vision.md`, it never writes code and it never merges. Start it in the repository folder in a new terminal:

    claude --agent architect

If you are not sure, `/agk:architect` prints the command and checks that `agk.toml` is present and that `gh` is logged in.
Ask the architect, for example: "Read the Draft spec for REQ-NNN. Write a brief with one item, on its own branch, and
open a pull request."

The architect writes a brief in `docs/briefs/` from the template: the rules that apply, one item with `Advances:`, the paths
it may change, how to know it is done, and the branch name. You read the brief and the spec.

The spec must be `Approved` before step 9: `make governance` fails an implementation pull request whose `Advances:` line names
a requirement that no Approved spec names (`FAIL specs: REQ-NNN: no Approved spec names it`). A spec cannot be `Approved`
while it has an open question without a ruling. When you agree with the spec, you approve it: change its `Status: Draft` line to
`Status: Approved`. Either do it yourself, or order the architect to do it as the final commit of its pull request. It does not
do it on its own. Merge that pull request.

Whether the architect starts with its hook active by that flag is not confirmed: it is marked `(verify)` in
`.claude/agents/architect.md`. If it does not start, open `claude` as usual, tell the session to read
`.claude/agents/architect.md` and follow it, and know that then only the rules of that file bind it, not its tool list.

## Step 9. An implementation session builds from the brief and stops

Open a third terminal, a normal `claude` session in the repository. It reads `CLAUDE.md`, which holds the operating rules.
Tell it:

    Build item 1 of docs/briefs/YOUR-BRIEF.md. Tests first. One pull request from the default branch. Push and stop. Do not merge.

It opens one pull request whose body has the lines `Advances:`, `Build-state row:`, `Decisions taken:`, `Questions:` and
`Verified:`, and it stops. `governance` runs on the pull request and should turn green. The `proof` job runs too. Look at its
steps: the one that ran is named `outcome: proven`, `outcome: not-proven (reason)`, `outcome: skipped` or
`outcome: unknown (reason)`. A change to behaviour is `proven` when its new tests fail on the base and pass on the head.

## Step 10. The architect reviews; you merge

Go back to the architect session. Ask it to review the pull request. It reads the pull request and its checks and posts one
comment whose first line is exactly

    Verdict: cleared 1a2b3c4

(or `Verdict: fix list`, or `Verdict: rejected`), where the number is the first characters of the pull request's head commit.
Findings follow after a blank line. If the implementation session pushes again, the architect must post a new verdict line
for the new head. You read the pull request yourself and merge it (squash) when you agree. Nobody and nothing merges for you.

## Step 11. Phase 2 of the ruleset

If the plan in step 5 said `phase 1`, run `/agk:ruleset` again once `governance` has succeeded on `main`. The plan then says
`phase 2` and adds the required status check `governance`. Apply it as in step 5. If step 5 already said `phase 2`, the plan
says `nothing to do` and this step is done.

## Step 12. Your first Monday report

On Monday the two weekly workflows write one issue each: `agk metrics <year>-W<week>` (label `agk-metrics`) and
`agk product report <year>-W<week>` (label `agk-product-report`). The report covers the whole ISO week before the Monday it
runs. A pull request merged this week is therefore in next Monday's report.

To see one now, start the workflow by hand: Actions, `product-report`, Run workflow. The `today` box is optional. The
report has six headings: `Delivered`, `Proven`, `Needs you`, `At risk`, `Cost`, `Flow`. A value the report cannot find prints
`unknown`; it never guesses.

## Running the loop

Once the first spec is built by hand you can let sessions find their own work. Three roles take part: a builder session, the conductor and you. The working rule of a session is in `config/session-rules.md`; read it once.

**With the autopilot.** One supervisor per machine starts every session as a short job (SPEC-0064), so you start no conductor or builder by hand (items 2 and 3 are the manual way):
- On each machine run `agk autopilot on` (`python3 scripts/agk/autopilot.py on`) once: it installs the supervisor's scheduler entry, checks the machine and prints the `[autopilot] mode` line to set by pull request.
- `agk status` shows the running jobs, the queue and what waits on you.
- `agk next` (`python3 scripts/agk/autopilot.py next`) runs the next review, fix or build job in the foreground and ends, posting nothing; `agk next --brief <n>` builds brief n. In personal mode it is the way to run jobs.
- In CI mode the launcher task (`kit/templates/runtime/launcher.txt`) is the supervisor and starts each job as a cloud session.

1. **File the work as a brief.** A brief is an issue labelled `agk-brief`. Create the label once (the maintainer does; `session.py next` finds nothing without it); `session.py claim` also labels a brief it takes `agk:taken`, which GitHub creates on its first use, so that the plan sees the take in the listing (ADR-0529), then write the issue in this shape and check a saved copy before filing it with `python3 scripts/agk/check_brief.py FILE`, which prints `ok brief`:

```text
Sentence: "A visitor can reset a password from the sign-in page."
Answers (the maintainers'):
1. The reset link expires after one hour.
2. The page shows the same message for a known and an unknown address.
Depends-on: #12
Size: M
Advances: REQ-004
Touches: src/auth/**, docs/guides/auth.md
Priority: 2
Contexts: kit (not applicable: a change to this project only); github (the same); local (the same); personal (the same); stacks (the same).
```

   `Depends-on` lines are optional, one per issue, and the brief waits until those issues are closed. `Size` is `S`, `M` or `L`. `Advances` names the requirements the work builds, separated by commas (`Advances: new` for a first brief that asks for a requirement), `Touches` the existing files it changes (one optional line `Adds:` lists the new files it creates, and a folder or wildcard over more than `[flow] max_touch_glob` files is refused unless the brief says `Broad: <reason>`), separated by commas, `Priority` is `1`, `2` or `3` (optional; 2 when absent), and `Contexts` states `kit`, `github`, `local`, `personal` and `stacks`, each with how the change works there or `not applicable: <reason>`. `check_brief.py FILE --root .` also fails an `Advances` that names a requirement `docs/requirements.md` does not have. A brief built in parts may carry one more line, `Builds: (a) the first part; (b) independent: the second part`: `session.py plan` and `/agk:launch` then name the next build that is not merged and has no live take and no open pull request (`build (b)` of brief #12), a build waits for the unmerged builds before it unless its text starts with `independent:`, and the session claims exactly that build with `session.py claim --brief 12 --build b`. A pull request names the build it delivers in its title, as `brief #12 build (a)`, and nowhere else (a sentence in its body never counts), and every open brief that the plan does not start is listed with its reason.

2. **Start a builder session.** In a fresh session run `python3 scripts/agk/session.py next --session <a short name>`. It prints the first free brief and the command that takes it, `take it with: session.py claim --session <name> --brief <n>`, and posts nothing, so looking never starts work; it says why it skipped each of the others, and `no brief` when none is left. Run the printed `claim` to take the brief with one comment, `taken: <name> <date>` (`next --session <name> --take` chooses and takes in one step, as `next` did before). The session builds, pushes and opens one pull request, and stops. A builder commits a `checkpoint:` at every step but pushes only at milestones (the first checkpoint, which opens the draft; the tests red; the tests green; marking it ready; and before any stop it can foresee), so a draft costs a few CI runs instead of one per step (session rule 7). `next` shows and takes nothing and prints `full <open>/<max>` when `[flow] max_builders` (3 by default) builder pull requests are open, skips a brief whose `Touches` overlap open work, and takes the briefs by `Priority`. Before every push run `python3 scripts/agk/session.py push-check`: it prints the files in which your head conflicts with the default branch and exits 1, or prints nothing. Then run `python3 scripts/agk/prepush.py` (add `--body FILE` with a saved copy of the pull request body, `--quick` to skip the tests): it runs the body check, `make lint`, the governance checks, the secret scan over the branch (when `gitleaks` is installed) and the tests the test plan selects, one timed line each, and stops at the first failure with its message, so a push rarely goes red in CI for a reason seconds of local checking would catch. On Windows, where `make` is not installed by default, the lint and governance steps are not run and say why, and the run ends `prepush: passed; not run: governance` (CI still runs governance); install make (`winget install ezwinports.make`) for the full local run. A builder of a UI brief (one with a `Screens:` line) runs `design_compare.py` from the plugin, as the design skill does (`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/design_compare.py" --version <v> --screens "<the line's pairs>"`, or through `/agk:design`), before it marks its pull request ready and puts each line it prints in the body as a `Design match:` line; the script is kit-only and never installed in a project, and the conductor only reads the `Design match:` lines; drift fails nothing, and the conductor names every drift in its verdict. A build that changes no screen named by a `Screens:` line runs none. If you want git to run it for you, copy the optional hook yourself: `cp kit/templates/pre-push .git/hooks/pre-push && chmod +x .git/hooks/pre-push` from a clone of the kit (the kit never installs a hook; `git push --no-verify` skips it).


   To decide how many sessions to start, run `python3 scripts/agk/session.py plan` (add `--json` for the same plan as data). It reads GitHub and posts nothing, and prints in plain words, for example `Start 2: builder-a takes #250, builder-b takes #252. #251 waits for #250 (both touch scripts/agk/route.py). 3 pull requests wait for your merge: #240, #241 (safe to merge together), #243 after #240 (both change docs/x.md).` It never starts two briefs whose `Touches` overlap in the same wave, counts a claim that has no pull request yet as a running builder, and starts the smallest of the ready briefs, `max_builders` less the running ones and `reviews_in_flight` (by default `max_builders`) less the pull requests waiting for a verdict. A `[capacity]` table picks a profile: `full` ignores the machine, `balanced` and `small` keep a quarter and a half of its memory, cores and disk free (`small` runs at most 2), and `fixed` reads `max_builders` alone; every plan prints `Capacity: <n> of <ceiling> (<profile>; limit: <name> <figure>)`. While the pull requests labelled `agk:merge-ready` or `agk:owner-merge` (or the old `agk:ready`) exceed `merge_hours` (1 by default) times your merge rate of the last 14 days, it starts none and says so (it never stops a running session; with no merge in that time the rate is unknown and the limit does not apply). It lists the ready pull requests that share no changed file as one set you can merge together, marks those that change a protected path, and lists a ready pull request more than `stale_commits` (20 by default) behind the default branch for its builder to update, not for you to merge. A brief with the line `Status: stale` or the label `agk-stale` is skipped by `plan` and `next`. The three settings are whole numbers in the `[flow]` table of `agk.toml`. Ready briefs go milestone by milestone (brief #1232, ADR-0523): the plan fills free slots from the earliest GitHub milestone of the brief issues (by due date, then number; a brief without a milestone comes last) and reaches a later milestone only when the earlier ones have no ready brief that overlaps nothing; within a milestone the brief that the most remaining hours wait on (the mid points of the `Expected:` ranges of every open brief whose `Depends-on` names it, directly or further down; S 3 hours, M 6 hours without one) starts first, then priority, then the smaller `Expected:`, then number. It prints `#<n> <milestone>: unblocks <h> h.` for each start and `idle: no ready brief in <milestones>; first wait: <the wait>.` for each free slot it cannot fill. To start only some milestones, list their titles in `[plan] active_milestones` of `agk.toml` (absent: every milestone is active). The plan reads only what it needs (brief #1251, ADR-0529): it judges each open brief from the listing (a `Depends-on` brief that no open listing holds is closed, with no read of its own), reads the comments of the briefs that pass in that milestone order only until the free slots are filled (and always of a brief labelled `agk:taken` or named by an open pull request), and reads the open pull requests and the closed ones of the last 14 days, never every pull request ever. It ends with `reads: <n> calls (<m> from cache), <s> s` (`reads` in `--json`), and `checklist.py` adds the last plan's figure to point 8. Every read keeps GitHub's ETag in a cache file per repository in your temp folder (never in the checkout; `AGK_READ_CACHE` names another folder, or `off` turns it off) and asks again with `If-None-Match`, so an unchanged answer is a `304` that GitHub does not count against its hourly limit; the plan asks again only the comments that one repository-wide `since` read shows changed since its last pass, and `plan --if-changed`, the conductor's re-plan, reuses the last plan while nothing changed on GitHub (for at most 30 minutes, and never after a commit or an edit of `agk.toml`). The waits (`session.py watch --pr` and `--assign`) read only the comments since the newest they have seen and slow from one poll a minute to one in five while nothing changes. When the `agk-conductor` issue passes 500 comments, `session.py rollover` (run by the conductor each pass) opens a new one with the same label, links it from the old one with `Continued in #<n>` and closes the old one; every reader takes the newest open one, and a running wait follows the link (brief #1251 build (b)). With `github_transport = "direct"` in the `[flow]` table, the reads of one command go over one kept-alive connection to GitHub, with the sign-in token that `gh auth token` gives held in memory only; the default is `"gh"`, one `gh api` call each (brief #1336, ADR-0566). When the token cannot be read, a proxy is set or the connection fails, the command prints `github: direct transport unavailable, using gh` once and finishes with `gh`. To return to the old way, set `github_transport = "gh"` or remove the line.
3. **Start the conductor.** In another session that built nothing, accept the workspace trust dialog of the folder (the role's guard hook does not run without it) and start `claude --agent conductor`. It reviews every open pull request, runs its pre-verdict steps and posts one `Verdict:` comment on each; it edits no file and never merges. Its `conductor.py watch` also ends with `HELD VERDICT #<n>` when a ready, green head has waited 15 minutes with no verdict, so a report that landed while it was busy is still reviewed (brief #1125), and with `START #<brief> <kind>` (a red-branch brief first, as `START #<brief> red`) when the plan offers a brief that nobody has started, so it starts builders within about a minute (brief #1151); the `START` lines come with any return of the watch, after its other lines, and with `conductor.py sweep`, so a brief offered while it is busy is started at its next step (brief #1179). When a pull request's only re-prove files are shared indexes and it merges cleanly, `python3 scripts/agk/conductor.py reprove --pr <n> --apply` brings its branch up to date and its clearing verdict carries over once the checks pass, with no builder round trip (brief #1163).

   **A review pass, again and again.** One pass over the queue is `/agk:review-pass` in the conductor session. It reviews exactly the pull requests that `python3 scripts/agk/session.py review-queue` lists, read-only, with the reason for each: labelled `agk:review`; a `Question:`, `Report:`, `Correction:` or `Maintainer answer:` comment created or edited after the last verdict; a head that differs from the last verdict's; green checks under a stale `agk:ci-running` label. It never gives two verdicts on one head, skips drafts and pull requests whose checks still run (whatever the label), names `checks not reported` when the required checks never reported, and ends with one line per pull request (`#<n> <head7> <action>`) and a `NEEDS-YOU: #<n> <what>` line for each decision that is yours. Running it twice on an unchanged queue posts nothing the second time.

   To run passes without prompting, run a loop on your own machine that wakes the conductor only when the queue changes. `python3 scripts/agk/session.py review-queue --fingerprint` prints one line, `fingerprint <sha256>` of the heads, labels, draft flags, comment times (edits included) and check states of the open pull requests; the loop compares it with the last one, runs `review-queue --all` when it changed, and starts a headless conductor only when that is not `empty`. The loop runs from a clean worktree of the default branch, outside the work tree and outside the system temp directory, so that the conductor's role file and guard are the default branch's, never a pull request's.

   **First, the guard check.** A project agent's hooks are skipped until the folder's workspace trust dialog is accepted, and a `-p` session may not count as trusted `(verify)`. Before you start a loop, check both halves of the guard in the worktree:

   ```text
   echo '{"tool_name":"Bash","tool_input":{"command":"git push origin HEAD"}}' | python3 .claude/hooks/conductor_guard.py
   claude -p --agent conductor "Run exactly this command and report its result: git push --dry-run origin HEAD"
   ```

   The first must print a `deny` decision naming `conductor guard rule 6`; the second must report that command refused by the guard. If either does not, the guard does not run headless on this machine: do not start the loop.

   Linux and macOS (bash):

   ```bash
   wt="$HOME/agk-review-loop"   # a clean worktree of the default branch, never in the temp directory
   [ -d "$wt" ] || git worktree add --detach "$wt" origin/main
   cd "$wt" || exit 1
   last=""
   while true; do
     git fetch -q origin && git checkout -q --detach origin/main
     fp=$(python3 scripts/agk/session.py review-queue --fingerprint) || { sleep 300; continue; }
     if [ "$fp" != "$last" ]; then
       queue=$(python3 scripts/agk/session.py review-queue --all)
       if [ "$(printf '%s\n' "$queue" | head -n 1)" != "empty" ]; then
         claude -p --agent conductor "/agk:review-pass
   $queue"
       fi
       last=$(python3 scripts/agk/session.py review-queue --fingerprint)
     fi
     sleep 120
   done
   ```

   Windows (PowerShell; `python` where `python3` is not on the path `(verify)`):

   ```powershell
   $wt = Join-Path $HOME 'agk-review-loop'   # a clean worktree of the default branch, never in the temp directory
   if (-not (Test-Path $wt)) { git worktree add --detach $wt origin/main }
   Set-Location $wt
   $last = ''
   while ($true) {
     git fetch -q origin; git checkout -q --detach origin/main
     $fp = python3 scripts/agk/session.py review-queue --fingerprint
     if ($LASTEXITCODE -ne 0) { Start-Sleep -Seconds 300; continue }
     if ($fp -ne $last) {
       $queue = (python3 scripts/agk/session.py review-queue --all) -join "`n"
       if (($queue -split "`n")[0] -ne 'empty') { claude -p --agent conductor "/agk:review-pass`n$queue" }
       $last = python3 scripts/agk/session.py review-queue --fingerprint
     }
     Start-Sleep -Seconds 120
   }
   ```

   The fingerprint is read again after a pass, so the pass's own verdicts do not wake it; the router's new label then wakes it once, and `review-queue` finds nothing to do, so no conductor starts. In a conductor session on Windows the verdict file's path is written with forward slashes (`C:/Users/<user>/AppData/Local/Temp/agk-conductor-<n>/verdict.md`) and the comment `POST` carries no `--jq` or other flag; the skill says so. What the loop cannot do: it runs with your own GitHub identity, which can merge and push, so the guard and the role file are the only boundary while no one watches. That stays a residual until a comment-only identity (read pull requests and checks, write comments, nothing else) is set up by a maintainer for the conductor.

4. **Let the builder wait.** After every push the builder runs `python3 scripts/agk/session.py watch --pr <number>`. It ends with one line when a verdict by a listed author names the pull request's head, when the pull request is merged or closed, when it has a conflict with its base, when a listed author posts a `Correction:` comment on the pull request or on the brief it took (`correction #<n> (comment <id>): ...`: the conductor was wrong about a cause, and the builder wakes on the correction with no person carrying it), when an answer to the builder's own `Question: Q-…` arrives (`answer <Q-id> (comment <id>)`: apply it and post a fresh `Report: <head> ready for review`) or a spec approver posts `Approve: <head> SPEC-nnnn` naming the current head (`approve <head7> SPEC-nnnn`: nothing to change; brief #1112), or when the router's `agk:` label on the pull request changes (`label <name>`, for example `label agk:review` once the checks are green; the router sets one label per pull request from GitHub events). A watch that starts after a verdict for the current head, or after a `Correction:`, which landed since your last `Report:`, ends at once with that line; restart it with `--since <comment id>` (the id the line printed) when you have acted on it and only wait for CI or the merge. A wait that cannot read GitHub for five polls in a row ends with `error: <what> cannot be read` (exit 4) instead of waiting silently, or with `github-unreachable: <what> cannot be read; local head <sha> not pushed; next: push, then post the Report:/Question:` when `gh` could not connect (the session's own output is then the only channel left). `watch --merged <number>` waits for another pull request's merge, for a `Depends-on`. Start `watch` so that its end wakes the session: in Claude Code, as a background task (its end re-invokes the session); in another runtime, the equivalent that wakes the session when the command ends. Never in the foreground, and never detached with `&`: the session then sits idle after its verdict. The one exception is a builder run as a cloud scheduled task, which ends when its session goes idle: it waits in the foreground (see `Running around the clock` under item 7). In an interactive session add `--session <name> --until-event` (brief #1310, ADR-0554): the watch then returns only on an event, every event line of one read printed, or after `[flow] wake_minutes` (110 by default, below the runtime's 2-hour background limit `(verify)`) with `renew: no event`, on which the builder starts it again at once, so a quiet hour costs at most one short turn. Keep a working summary on the pull request with `python3 scripts/agk/session.py summary --pr <number> --file <file>` (at most 25 lines, `[flow] summary_lines`), posted when the draft opens and when it is ready, refreshed after each fix list and before any hand-over; it edits the one comment in place, and `session.py resume --pr <number>` prints it with the `git diff` since its head, so a session that must restart reads that, the newest verdict and the diff, not the whole history. A session that restarts after its machine was reclaimed runs `python3 scripts/agk/session.py queue --role conductor|builder|person` first: it lists the open pull requests whose label is that role's (`empty` when none), and the session carries on from there.

   **Who posted it.** The owner and every AGK session post as one GitHub login, so each comment AGK posts ends with one last line `Who: AGK` (a builder's `Report:`, `Progress:` and `Question:` end `Who: AGK builder`, the conductor's `Verdict:` and `Answer:` end `Who: AGK conductor`), and a post that relays the owner's decision ends `Who: ProductOwner` after the owner's quoted words and time. The kit's scripts add the line to the comments they post; a comment the owner types carries nothing. It is a marker, not a rule: no check, guard, router or merge step reads or requires it, and every first line is read as before (brief #1289, ADR-0546).

5. **Merge from the report.** The weekly report and the inbox list, first under Needs you, the group **Ready to merge**: the open pull requests whose head carries a clearing verdict. Merging is yours; no session merges, tags or enables auto-merge. A person approves every spec: for an intake the conductor ends its verdict with `Approval: SPEC-<n> <path> Draft -> Approved, waiting for a person: post "Approve: SPEC-<n>"` (the router labels the pull request `agk:approve`), and you post one comment whose first line is `Approve: SPEC-<n>`: no commit id to type, the text you approve is the spec as of your comment, and the approval stops counting if a later commit changes the spec apart from its status line. The long line `Approve: <head> SPEC-<n>` still works. A comment that an agent posted through its GitHub App never counts as your approval (`agent_apps` in `agk.toml`, default `["claude"]`), and while that list is not empty an approving GitHub review does not count either, because a review cannot show which app posted it: post the comment yourself, from your own account (the router tells you once). A project that sets `agent_apps = []` counts an approving review (at its own commit) when the pull request sets one spec `Approved`; `docs/guides/security.md` says what this proves and what it cannot. Only an account listed in `spec_approvers` of `config/reviewers.yaml` (user handles, never a session or conductor account) counts, and `check_final_clearance.py` fails a spec set `Approved` without that line. In solo mode (`review_mode = "solo"` with one person listed, ADR-0179), `/agk:confirm` prints one `Confirmed:` comment that counts as the verdict, its `Final:` lines and the spec approval together; you post it yourself, from the browser or the GitHub app (a session never does, session rule 29), and then re-run the governance check or push, because until amendment 97 is decided nothing re-runs it for you.

6. **When the credits run out.** Sessions stop without warning: the account runs out of credits or tokens, a usage limit is reached, an idle machine is reclaimed, or a person closes the session. Every session stops, and nothing it pushed is lost: a builder commits `checkpoint:` steps to its branch and keeps one `Progress:` comment on its pull request. The GitHub side (the router, the checks and the labels) keeps running and needs no model. Actions minutes on private repositories are a second budget, which the router uses one short job per event. When credits return, start a session with `python3 scripts/agk/session.py next --session <name>`: it offers a pull request that has waited on its builder for `stall_hours` before any new brief (`next --session <name> --take` takes it over), and `python3 scripts/agk/session.py resume --pr <number>` prints where that work stands, so the new session continues from the branch and the progress line instead of starting again. A builder may end a `Report:` line with `Usage: <n> tokens` when its runtime shows the figure, the usage since the previous `Report:` of the same pull request and not a running total (a session that can only read a running total subtracts the total it reported last); the weekly report sums what is reported for each pull request and says `usage not reported` otherwise, never zero. The rule itself, which was session rule 12 (`config/session-rules.md` keeps its number as a pointer line, ADR-0243): A `Report:` line may end with `Usage: <n> tokens`, a whole number, when the runtime shows the session's own usage. The figure is the usage since the previous `Report:` of the same pull request, never a running total: a session that can only read a running total subtracts the total it reported last. The weekly report sums the figures of a pull request, so a running total would count the early work several times.

7. **Start builders by a launcher.** AGK ships no launcher that runs on its own, and no session starts, stops or reviews another, except that a session starts other sessions when a person runs `/agk:launch` and confirms its plan (it runs `python3 scripts/agk/session.py plan`, asks `yes` or `no`, then starts one session per planned slot through an adapter: in a runtime with one-time scheduled tasks one task for each session, firing at once, with the standard builder prompt; anywhere else it prints one ready-to-paste prompt for each session; it creates no recurring task, holds no credential and starts nothing later). A launcher that runs without a person is what a team writes or configures for its own runtime, and this is the contract it keeps. `python3 scripts/agk/session.py demand` prints one JSON line `{"ready": r, "open": o, "max": m, "start": s}`: `r` is the number of briefs `next` would not skip, `o` the open builder pull requests, `m` the `max_builders` of the `[flow]` table of `agk.toml` (3 by default) and `s = min(ready, max - open)`, 0 when negative. A launcher starts `start` builder sessions and nothing else. Each one runs `python3 scripts/agk/session.py next --session <a short name> --take`, works on what it hands out, and ends on `no brief` or `full` when there is nothing for it. A session started by a launcher uses `assign = "next"` in the `[flow]` table of `agk.toml` (the default): when its work is done it runs `python3 scripts/agk/session.py after --session <a short name>`, which is `next --take`, which takes the next brief. With `assign = "conductor"`, a session that finishes posts `Request:` on the one open issue labelled `agk-conductor` and waits there with `session.py watch --assign <a short name>` for the conductor's `Assign:` line. Two examples follow; both only read `demand`, and starting the sessions is the team's own step.

   A scheduled task of a session runtime (the text of the task):

   ```text
   Every 30 minutes run `python3 scripts/agk/session.py demand`. If "start" is more than 0,
   start that many builder sessions, each with this prompt:
   "Run `python3 scripts/agk/session.py next --session <a short name> --take`, build what it
   hands you, and stop on `no brief` or `full`."
   ```

   A CI schedule (the step that starts the sessions is the team's own script):

   ```yaml
   on:
     schedule:
       - cron: "*/30 * * * *"
   jobs:
     demand:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@<the pinned sha of your repository>
         - run: python3 scripts/agk/session.py demand
         - run: ./start-builders "$(python3 scripts/agk/session.py demand | python3 -c 'import json,sys; print(json.load(sys.stdin)["start"])')"
   ```

   **Running around the clock.** Four roles keep the work moving without a person at the keyboard: the launcher, the conductor, and a builder on the strongest tier or on the mid tier. The kit ships their task texts as templates, `kit/templates/runtime/launcher.txt`, `kit/templates/runtime/conductor.txt` and `kit/templates/runtime/builder.txt` (one text for both builder tasks, by its `Tier:` line: strongest for `design` and `build`, mid for `small` and `mechanical`), with `kit/templates/runtime/README.md` saying which is which; it installs and starts none of them. Replace `<owner>/<repo>` and `<default branch>` and keep every rule. The launcher is the supervisor in CI mode: it runs `autopilot.py jobs --claim` and starts each review, build and fix job as a short cloud session, and is the backup for a builder silent for 45 minutes; the conductor text is one review job.

   - On a laptop: `agk autopilot on` (see **With the autopilot.** above); in personal mode, which has no scheduled tasks, run `agk next` for each job. By hand, run the conductor loop of item 3 in one terminal and start builders with `/agk:launch`; each builder follows `builder.txt` from its second paragraph on.
   - In a cloud runtime: one scheduled task per template. The launcher runs every 30 minutes and fires the other tasks, each one short job with its item in a second message: the conductor task for a review job (it no longer runs every 12 hours), a builder task for each build or fix job; a builder waits in the foreground no more.

   What you still do: approve specs, merge workflow and ruleset changes, and answer every `Question:` whose first line says `for the maintainers`. A workflow change comes to you as a file, not as text to paste: the builder commits the whole proposed file at `.agk/workflow-proposals/<name>.yml` on its branch (a path the cloud accepts; it never changes `.github/workflows/` itself) and its `Question: Q-<N>-n for the maintainers:` names `/agk:workflow-apply <pr>`. Run that command from your checkout: it checks each file, shows the diff and, after your yes, moves it into `.github/workflows/`, commits, pushes the branch with your own `git` and `gh` and answers the question (ADR-0505). Governance fails while a proposal is still on the head, so none reaches the default branch. A push refused for the workflow permission prints `gh auth refresh -s workflow`. How a builder waits: in an interactive Claude Code session it runs `session.py watch` as a background task, whose end wakes the session (item 4); in a cloud scheduled task it runs `watch` in the foreground with a timeout of at most 9 minutes and runs it again, because such a task ends as soon as its session goes idle.

8. **Automatic starts after a review pass.** Each `/agk:review-pass` ends by re-planning (brief 331, ADR-0190): the conductor runs `python3 scripts/agk/session.py plan --json` and prints its `Start` and `waits for` lines in the pass's last lines, so a brief that a merge unblocked is named at once. By default it starts nothing and prints the ready-to-paste prompts of the sessions to start, as `/agk:launch` does. To let the pass start them itself, set both settings in the `[flow]` table of `agk.toml`, a protected change with an ADR in the same pull request:

   ```toml
   [flow]
   auto_start = true
   launch_adapter = "scripts/start-session-cloud.sh"
   ```

   The pass then runs `python3 scripts/agk/launch.py prompts --plan <the plan> --adapter <launch_adapter>`, the one new command the conductor's guard allows, and only with the adapter exactly as written there and only while the default branch (as the conductor last fetched it) says the same: turning `auto_start` off on the default branch stops the starts even for a conductor whose checkout is older. `launch.py` splits the command into words and runs it without a shell, from the folder the conductor runs in, once for each session the plan names, with the prompt on its standard input and `AGK_SESSION`, `AGK_BRIEF` and, for a brief built in parts, `AGK_BUILD` in its environment; it starts nothing for a plan without its capacity, never more than the plan's capacity or `max_builders`, and each started session claims its own brief. A failing adapter is reported in the pass's last lines and not retried. The adapter is a short script the project owns, and runs with the environment of the conductor's session; it holds no credential of its own. The kit installs two adapters as templates, written once and then the project's own (brief #1237, ADR-0525): `scripts/start-session-local.sh`, for Linux and macOS, and the Windows one below, `scripts/start-session-windows.ps1`; `doctor.py` names the missing one and the `launch_adapter` line to set while `auto_start` is on. The kit installs neither of the two short examples below. Adapt the one you use to your setup and try it once by hand (`echo hello | AGK_SESSION=builder-x bash scripts/start-session-local.sh`) before you turn `auto_start` on. [The local-mode guide](local-mode.md), "Running unattended", adds the watchdog that restarts the conductor.

   A local terminal adapter at its shortest, a new terminal tab running `claude` with the prompt and no worktree of its own `(verify: the terminal's command and its options are your desktop's; this one is GNOME Terminal)`; the installed `scripts/start-session-local.sh` is the Windows adapter's twin, with a worktree per session, the background where there is no desktop, and the exit file:

   ```bash
   #!/usr/bin/env bash
   # scripts/start-session-tab.sh: one new terminal tab per session, running claude with the prompt.
   set -euo pipefail
   prompt="$(cat)"
   gnome-terminal --tab --title "$AGK_SESSION" -- claude "$prompt"
   ```

   A cloud adapter, a one-time cloud session with the prompt `(verify: the command that starts a cloud session from a terminal, and its flag, are the runtime's and may change)`:

   ```bash
   #!/usr/bin/env bash
   # scripts/start-session-cloud.sh: one one-time cloud session per session, with the prompt as its message.
   set -euo pipefail
   prompt="$(cat)"
   claude --remote "$prompt"
   ```

   A Windows Terminal adapter, a new tab in its own worktree that closes when the session ends `(verify: the options of wt, the profile settings of Windows Terminal and the PowerShell calls are the terminal's and the shell's, and were not run by the session that wrote this example)`. The kit installs the script `scripts/start-session-windows.ps1` shown here, as a template that is written only where the file is absent; set `launch_adapter = "pwsh -NoProfile -File scripts/start-session-windows.ps1"`. It reads `AGK_SESSION`, `AGK_BRIEF` and the prompt on standard input; creates the session's worktree with `git worktree add`, or, when the folder `..\agk-<session>` is still there from an earlier start (a session that ended or crashed), reuses it if it is a clean worktree of this repository (fetch, then the default branch checked out detached) and otherwise starts nothing, exiting 2 with one line naming the folder, so a restart after a crash works (brief #1237, ADR-0525); and waits until its folder exists, so that no tab opens on a folder that is not there yet; and writes a small wrapper that the tab runs. The wrapper builds the tab's environment itself, because a tab opened in a running Windows Terminal window may start from the terminal's environment rather than the adapter's: PATH read fresh from the machine and user values, `TEMP`, `TMP` and `TMPDIR` set to the long path of the temporary folder (not its short `~1` form), and `CLAUDE_CODE_CHILD_SESSION` removed, so the builder is a session of its own and its transcript is saved. It then starts `claude` with the prompt, adding `--model <name>` and `--effort <level>` when the adapter was given `AGK_MODEL` and `AGK_EFFORT` (the tier of the brief's kind, from `[models.names]`; brief #1252, ADR-0530), and when `claude` exits it writes `<worktree>/.agk-session-exit` with the exit code and the UTC time, and exits with the same code. The job runs headless (`claude -p`) with its output in `<worktree>/.agk-session.log`, and is started hidden with `Start-Process`, needing no Windows Terminal; the tab and the profile below are used only with `show_jobs = true` in the `[autopilot]` table, which `launch.py` passes as `AGK_SHOW_JOBS` (brief #1388, ADR-0588). Once the worktree exists, the script appends `.agk-session-exit` to the worktree's exclude file (the path `git -C <worktree> rev-parse --git-path info/exclude` names), so the exit file, which is written into the worktree untracked, never reaches a commit, not even through a later `git add -A` in that worktree. Before `claude` starts, the wrapper writes `<worktree>/.agk-session-pid` (the session, the wrapper's process id, the UTC start time and the brief), excluded the same way; the watchdog and `launch.py` read it (brief #1355, ADR-0568). The adapter needs PowerShell 7 (`pwsh`; install it with `winget install Microsoft.PowerShell`), which Windows does not install by default, and it must not be run under Windows PowerShell 5.1 (`powershell.exe`): there, `& claude @flags -p $prompt` passes the prompt to a native program with its embedded double quotes stripped, so a prompt that holds quotes arrives changed.

   ```powershell
   # scripts/start-session-windows.ps1: one background job per session, in its own worktree; a tab only with show_jobs.
   $ErrorActionPreference = 'Stop'
   $session = $env:AGK_SESSION
   $brief = $env:AGK_BRIEF
   if (-not $session) { throw 'AGK_SESSION is not set' }
   $prompt = [Console]::In.ReadToEnd()

   # 1. The worktree first, and wait until its folder exists.
   $repo = (git rev-parse --show-toplevel).Trim()
   $worktree = Join-Path (Split-Path $repo -Parent) "agk-$session"
   # One conductor per machine (brief #1409): a conductor job starts nothing while a record of kind conductor beside this
   # checkout names a live process that has not written its exit file (verify: not run on Windows by the session that wrote it).
   if ($env:AGK_JOB_KIND -eq 'conductor') {
       foreach ($dir in @(Get-ChildItem -LiteralPath (Split-Path $repo -Parent) -Directory -Filter 'agk-*')) {
           $record = Join-Path $dir.FullName '.agk-session-pid'
           if (-not (Test-Path -LiteralPath $record)) { continue }
           $f = @{}
           foreach ($file in @($record, (Join-Path $dir.FullName '.agk-session-exit'))) {
               if (Test-Path -LiteralPath $file) {
                   Get-Content -LiteralPath $file | ForEach-Object { $k, $v = $_ -split '=', 2; if ($null -ne $v) { $f[$k.Trim()] = $v.Trim() } }
               }
           }
           $live = $f['pid'] -match '^\d+$' -and (Get-Process -Id ([int]$f['pid']) -ErrorAction SilentlyContinue)
           if ($f['kind'] -eq 'conductor' -and $live -and (-not $f['ended_utc'] -or $f['ended_utc'] -lt $f['started_utc'])) {
               [Console]::Error.WriteLine("start-session-windows: conductor $($f['session']) is running on this machine; nothing started")
               exit 3
           }
       }
   }
   git -C $repo fetch --quiet origin
   if (Test-Path -LiteralPath $worktree) {
       # The folder is there from an earlier start (a session that ended or crashed): reuse it when it is a clean
       # worktree of this repository, otherwise start nothing for this session.
       function Get-FullPath([string]$Path) {
           [IO.Path]::GetFullPath($Path).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
       }
       $ours = Get-FullPath (git -C $repo rev-parse --path-format=absolute --git-common-dir).Trim()
       $common = git -C $worktree rev-parse --path-format=absolute --git-common-dir 2>$null
       $top = git -C $worktree rev-parse --show-toplevel 2>$null
       if ($LASTEXITCODE -ne 0 -or -not $common -or -not $top -or
           (Get-FullPath $common.Trim()) -ne $ours -or (Get-FullPath $top.Trim()) -ne (Get-FullPath $worktree)) {
           [Console]::Error.WriteLine("start-session-windows: $worktree exists and is not a worktree of this repository; nothing started"); exit 2
       }
       $changes = @(git -C $worktree status --porcelain --untracked-files=all | Where-Object { $_ -and $_ -notmatch '\.agk-session-(exit|pid)$' })
       if ($LASTEXITCODE -ne 0 -or $changes.Count -gt 0) {
           [Console]::Error.WriteLine("start-session-windows: $worktree is not clean; nothing started"); exit 2
       }
       git -C $worktree fetch --quiet origin
       git -C $worktree checkout --quiet --detach origin/main   # your default branch
       if ($LASTEXITCODE -ne 0) { throw 'git checkout of origin/main failed' }
   } else {
       git -C $repo worktree add --detach $worktree origin/main   # your default branch
       if ($LASTEXITCODE -ne 0) { throw 'git worktree add failed' }
   }
   $deadline = (Get-Date).AddSeconds(30)
   while (-not (Test-Path -LiteralPath (Join-Path $worktree '.git'))) {
       if ((Get-Date) -gt $deadline) { throw 'the worktree folder did not appear' }
       Start-Sleep -Milliseconds 200
   }
   # Keep the exit file, the process record and the log out of git: the worktree's exclude file names them.
   $exclude = (git -C $worktree rev-parse --git-path info/exclude).Trim()
   if (-not [IO.Path]::IsPathRooted($exclude)) { $exclude = Join-Path $worktree $exclude }
   New-Item -ItemType Directory -Force -Path (Split-Path $exclude -Parent) | Out-Null
   if (-not ((Test-Path -LiteralPath $exclude) -and (Select-String -LiteralPath $exclude -SimpleMatch -Quiet '.agk-session-exit'))) {
       Add-Content -LiteralPath $exclude -Value '.agk-session-exit'
   }
   if (-not ((Test-Path -LiteralPath $exclude) -and (Select-String -LiteralPath $exclude -SimpleMatch -Quiet '.agk-session-pid'))) {
       Add-Content -LiteralPath $exclude -Value '.agk-session-pid'
   }
   if (-not ((Test-Path -LiteralPath $exclude) -and (Select-String -LiteralPath $exclude -SimpleMatch -Quiet '.agk-session.log'))) {
       Add-Content -LiteralPath $exclude -Value '.agk-session.log'
   }

   # 2. The prompt and the wrapper, in a folder of the session under the long temporary path.
   $longTemp = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Temp'
   $work = Join-Path $longTemp "agk-$session"
   New-Item -ItemType Directory -Force -Path $work | Out-Null
   $promptFile = Join-Path $work 'prompt.txt'
   Set-Content -LiteralPath $promptFile -Value $prompt -Encoding utf8
   # The job's kind, item and head (SPEC-0064 rule 3), from AGK_JOB_KIND, AGK_ITEM and AGK_HEAD, for the record.
   $Kind = $env:AGK_JOB_KIND; $Item = $env:AGK_ITEM; $Head = $env:AGK_HEAD
   Set-Content -LiteralPath (Join-Path $work 'job.txt') -Encoding utf8 -Value "kind=$Kind", "item=$Item", "head=$Head"
   # A tab only with [autopilot] show_jobs = true, which launch.py passes as AGK_SHOW_JOBS (SPEC-0064 rule 5).
   $show = $env:AGK_SHOW_JOBS -eq 'true'
   Set-Content -LiteralPath (Join-Path $work 'show.txt') -Encoding utf8 -Value $(if ($show) { 'true' } else { 'false' })
   $wrapper = Join-Path $work 'run.ps1'
   Set-Content -LiteralPath $wrapper -Encoding utf8 -Value @'
   param($Worktree, $PromptFile, $LongTemp, $Session, $Brief, $Model, $Effort)
   # The job's environment: PATH fresh, TEMP long, no inherited child-session marker.
   $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
               [Environment]::GetEnvironmentVariable('Path', 'User')
   $env:TEMP = $LongTemp
   $env:TMP = $LongTemp
   $env:TMPDIR = $LongTemp
   Remove-Item Env:CLAUDE_CODE_CHILD_SESSION -ErrorAction SilentlyContinue
   $env:AGK_SESSION = $Session
   $env:AGK_BRIEF = $Brief
   Set-Location -LiteralPath $Worktree
   # The process record before the first turn: this wrapper's process holds claude.
   $started = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
   $job = @(Get-Content -LiteralPath (Join-Path (Split-Path $PromptFile -Parent) 'job.txt'))
   Set-Content -LiteralPath (Join-Path $Worktree '.agk-session-pid') -Value (@("session=$Session", "pid=$PID", "started_utc=$started", "brief=$Brief") + $job)
   $prompt = Get-Content -LiteralPath $PromptFile -Raw
   # The tier's model name and effort: no flag without a model (verify: the flags are claude's).
   $flags = @()
   if ($Model) { $flags += '--model', $Model; if ($Effort) { $flags += '--effort', $Effort } }
   # Headless (-p), the output in the log; with show_jobs also in the tab (verify: the runtime's headless flag on Windows).
   $log = Join-Path $Worktree '.agk-session.log'
   $shown = (Get-Content -LiteralPath (Join-Path (Split-Path $PromptFile -Parent) 'show.txt') -ErrorAction SilentlyContinue) -eq 'true'
   try {
       if ($shown) { & claude @flags -p $prompt 2>&1 | Tee-Object -FilePath $log } else { & claude @flags -p $prompt *> $log }
       $code = $LASTEXITCODE
   } catch { $code = 1 }
   if ($null -eq $code) { $code = 1 }
   $at = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
   Set-Content -LiteralPath (Join-Path $Worktree '.agk-session-exit') -Value "exit_code=$code", "ended_utc=$at"
   exit $code
   '@

   # 3. The job, only now that the worktree exists: hidden, with no Windows Terminal, or with show_jobs a tab that closes
   #    when it ends. The model and effort follow as arguments, never empty ones (verify: Start-Process's quoting).
   $extra = @()
   if ($env:AGK_MODEL) { $extra += $env:AGK_MODEL; if ($env:AGK_EFFORT) { $extra += $env:AGK_EFFORT } }
   if ($show) {
       wt -w 0 new-tab --profile "AGK builder" --title $session -d $worktree `
           pwsh -NoProfile -File $wrapper $worktree $promptFile $longTemp $session $brief @extra
   } else {
       $quoted = @($wrapper, $worktree, $promptFile, $longTemp, $session, $brief) + $extra | ForEach-Object { '"' + $_ + '"' }
       Start-Process -FilePath pwsh -WindowStyle Hidden -WorkingDirectory $worktree -ArgumentList (@('-NoProfile', '-File') + $quoted)
   }
   ```

   The tab uses a Windows Terminal profile named "AGK builder". Add it to the `profiles.list` of the terminal's `settings.json`:

   ```json
   {
       "name": "AGK builder",
       "guid": "{<a new GUID, from New-Guid>}",
       "commandline": "pwsh.exe -NoLogo",
       "closeOnExit": "always",
       "hidden": true
   }
   ```

   `"closeOnExit": "always"` closes the tab on any exit of the wrapper, a crash included. The terminal's default, `graceful`, closes a tab only after a clean exit and keeps it open on a bare shell or an error after a non-zero one; the setting belongs to this profile alone, so your other tabs keep their own. A builder's tab therefore closes by itself when its pull request is ready and the session ends, or when the session crashes; the exit file in the worktree then tells the two apart: `exit_code=0` for a session that ended, any other code for a crash, with the UTC time it ended. Try the adapter once by hand from the repository's folder before you turn `auto_start` on: `$env:AGK_SESSION = 'builder-x'; $env:AGK_BRIEF = '1'; 'hello' | pwsh -NoProfile -File scripts/start-session-windows.ps1`, then type `/exit` in the new tab, check that the tab closes and that `..\agk-builder-x\.agk-session-exit` reads `exit_code=0`, and remove the trial worktree with `git worktree remove ..\agk-builder-x`.

**When work waits on the owner.** A pull request whose newest open item is a `Question: Q-… for the maintainers`, an `Owner needed:`, a spec waiting for `Approve:` or a merge only the owner may do waits `owner_wait_minutes` of the `[flow]` table (30 by default; 0 parks at once), and not at all during `owner_rest_hours`, read at the fixed offset `owner_utc_offset` (no time-zone database is needed). Then `session.py watch` or `conductor.py sweep` labels it `agk:parked` with one comment `Parked-by: wait <Q-id>`; its builder posts `Report: <head> handing over: blocked: <Q-id> waits for the owner` and runs `session.py after`, and the slot goes to the next brief. Nothing is closed. When the owner answers, the next sweep removes the label and prints the `resume --pr <n>` command, and `session.py next` offers that pull request before any new brief. A person's own `agk:parked` is never removed. For an owner who rests from 8 PM to 8 AM in India:

```toml
[flow]
owner_wait_minutes = 30
owner_rest_hours = "20:00-08:00"
owner_utc_offset = "+05:30"
```

## Working as a team

Four people can work one repository from four laptops, each running two or three builders. Nothing runs between the laptops: every builder coordinates through GitHub, the one place all of them can read. A brief is an issue, a claim is one `taken:` comment on it, and a pull request is the work. The working rule of a session is still `config/session-rules.md`.

1. **One shared conductor.** One conductor reviews every pull request of the team, in the cloud or on one person's machine. It holds the lease on the plan issue (`python3 scripts/agk/conductor.py lease --show` prints `held by <name> until <time>` or `free`). A second conductor started by someone else exits 3 and is a standby: nobody has to coordinate who runs it, and nobody runs a conductor "just in case" on a laptop.
2. **Set up each laptop once.** Clone the repository, run `gh auth login` with your own account (never a shared one: the `taken:` comment and the pull request carry the author), install the plugin (Step 2) and check with `/agk:doctor`. Make one git worktree per builder, so two builders never share a working directory: `git worktree add ../<repository>-b1 origin/main --detach`, then `b2`, `b3`. Keep the clone's own folder on the default branch and only pull it: every session, also one you open by hand, starts in its own worktree (`git worktree add ../agk-<session> origin/main`), since the conductor and the planner read the main folder (brief #1301).
3. **Name sessions so no two match.** A session name is a plain word and unique across the team: `<person>-b<n>`, for example `ana-b1`, `ana-b2`, `ben-b1`. The name is on every `taken:` comment, so the team reads who holds what.
4. **Start builders.** In each worktree run `/agk:launch` and say `yes` to its plan, or by hand `python3 scripts/agk/session.py next --session ana-b1`, then the `claim` command it prints. A builder takes one brief and one pull request, builds, pushes, marks it ready and stays until the pull request closes (`session.py watch --pr <n>`).
5. **A refusal is not a failure.** When two builders reach one brief together, `claim` keeps the oldest `taken:` and the other prints `lost the take to <name>` or `taken by <name>`. Run `next` again: it names the next free brief. Do not repeat the same claim and do not delete the other's comment.
6. **When a laptop sleeps or closes.** The branch and the draft pull request are on GitHub; nothing is lost. After the claim hours pass without a pull request, the brief is free again. Anyone, from any laptop, continues the pull request with `python3 scripts/agk/session.py resume --pr <n>`: it posts nothing and prints the pull request, its brief, the last `Progress:` line and where to continue from, and you check out the branch in your own worktree. Before you take over, read the newest comments: a builder that posted or pushed in the last 30 minutes is still working, and the one that stops says so with a `Report: <head> handing over:` line.
7. **Size `max_builders` for the team.** `[flow] max_builders` in `agk.toml` counts the open builder pull requests of the whole repository, not of one laptop. Four people with three builders each need 12. `python3 scripts/agk/session.py plan` also caps the starts by the conductor's review capacity (`reviews_in_flight`) and by the memory of the machine it runs on, and its capacity line names the limit that bit. Two or three builders is what one laptop holds; each builder runs its own tests, so a laptop with little memory should start fewer. Changing `max_builders` is a change of a protected path class; the owner makes it, by an ADR in the same pull request.
8. **What stays with the maintainers.** A person approves every spec; workflow files and the ruleset change only by a person; and `config/reviewers.yaml` (who may post a verdict or an approval) is the maintainers' list. A builder asks with `Question:` and waits; it never decides.

## The merge queue

With `[flow] auto_merge = true` the merger merges each cleared pull request itself. In a repository owned by an
organization it can instead add each cleared head to GitHub's merge queue, which tests up to five pull requests together on
top of `main`, so a pull request's checks run once on its own head and once in its batch, never again after each merge to
`main` (brief #972, ADR-0416, ADR-0417). GitHub offers the merge queue only to repositories owned by an organization
(public, or on Enterprise Cloud), not to a repository owned by a personal account `(verify)`.

The ruleset of `main` is yours to set; no session sets or reads it. In Settings, Rules, Rulesets, the ruleset of `main`,
in the order of that page `(verify: the labels are read from GitHub's documentation)`:

1. **Require merge queue**: on.
   - Merge method: **Squash**.
   - Build concurrency: 5.
   - Minimum group size: 1. Maximum group size: 5.
   - Wait time to meet minimum group size: 5 minutes.
   - Require all queue entries to pass required checks: on (only non-failing pull requests merge).
2. **Require status checks to pass**: the required checks are `governance` and `proof`, the names the workflows already
   use. Do not add `agk/verdict`: GitHub sets it only on a pull request's head, the queue's commit never carries it, and
   the queue would wait for it forever.
3. **Require branches to be up to date before merging**: off, with the queue on or off. `merge_cleared.py` already
   re-proves a head only when `main` changed its files (SPEC-0050 rule 6) and runs `[testing] pre_merge_tests` on the
   would-be merge.

Switch over in this order:

(i) the pull request of brief #972 merges, with `merge_queue = false` in the `[flow]` table of `agk.toml`;
(ii) you turn on **Require merge queue** as above and turn off **Require branches to be up to date before merging**. In a
repository owned by a personal account there is no queue: turn off only the up-to-date rule, which removes the reruns
after every merge to `main`, and stop here;
(iii) you set `merge_queue = true` in the `[flow]` table of `agk.toml`, in a pull request with an ADR. `/agk:doctor` then
prints `merge queue: on`.

A pull request that fails its batch is removed by GitHub, and the merger posts one line on it,
`Removed from the merge queue: <check> failed on <queue sha>`. The merger then holds that head and never queues it again
until a new verdict, which a new head needs anyway. GitHub's merge
queue is not the conductor's `conductor.py merge-queue`, which stays as it is.

**When only the owner may merge** (brief #1358, ADR-0570). The merger holds a release or a change to a protected class for
you (`held: protected class <class> (rule 5)`), and the GitHub button merges the head as it is, untested against the
latest `main`. So the merger still tests the would-be merge of such a pull request and the line ends
`would-be merge: pass` or `would-be merge: fail`; it merges nothing. Merge it through the kit, not the button:
`python3 scripts/agk/merge_cleared.py --pr <n> --owner` runs the same checks with the owner-only holds lifted for that one
call and merges, as the account you are signed in to `gh` with, only when the would-be merge passes; it refuses an account
that is not in `spec_approvers` (`config/reviewers.yaml`), and it refuses inside an agent session (`CLAUDECODE`,
`AGK_SESSION` or `AGK_ROLE` set), because sessions run under your account: run it in your own terminal.
It works with `[flow] auto_merge` off as well, so a project where you merge everything by hand gets the same test. The result is reused while the head and `main` stay the same.
On `fail` the builder updates its branch first. In a repository owned by an organization with `merge_queue = true`, your
button queues the pull request and the queue's own runs test it, so `--owner` is optional there; in a repository owned by
a personal account, where `/agk:doctor` prints `merge queue: unavailable (user-owned repository)`, or with the queue off,
`--owner` is the way.

## Upgrading the kit

Run `/agk:upgrade` (or `python3 scripts/agk/upgrade.py <your repository>` from the kit) to bring the kit's files to a newer
release. It replaces each kit file you have not edited and refuses, writing nothing, when one differs from every released copy.

- **Your own make targets go in `project.mk`.** The kit's `Makefile` is a kit file, so an edit to it stops every upgrade. It
  includes `project.mk` after `agk.mk` when that file exists; the kit never installs, lists or writes `project.mk`, so your
  targets survive every upgrade. If an upgrade refuses over `Makefile`, move your own targets to `project.mk`, restore the
  kit's `Makefile`, and run the upgrade again. A new project protects `project.mk` beside `Makefile`; where yours protects
  `Makefile` but not `project.mk`, add `project.mk` to `config/protected-paths.txt` and `config/reviewers.yaml` in the same
  pull request.
- **`project.mk` adds targets; it extends a kit target only by a prerequisite.** Never give a kit target (`test`, `lint`,
  `governance`, `traceability` or an `agk-` one) a second recipe: make keeps one recipe per target and, when it sees two,
  drops one and only prints `warning: overriding recipe`. To run your own steps with a kit target, give them a target of
  their own and add it as a prerequisite, with no recipe:

  ```make
  test: project-test

  project-test:
  	python3 -m pytest -q tests/app
  ```

  `make test` then runs the kit's recipe and `project-test`.
- **Windows.** Fetch the kit from its release tag with git and no line-ending conversion
  (`git -c core.autocrlf=false clone --branch v<version> <the kit repository URL>`), or use the plugin cache. A copy
  with CRLF line endings is read as LF by the upgrade, so line endings alone never cause a refusal.

## Handing a project over without AGK

A project can drop AGK at any time; its engineers keep building from the same issues without it. The issues that
`plan_intake.py publish` printed read as ordinary issues (a `## What` paragraph, `## Acceptance` checkboxes, the milestone
and what each depends on), with AGK's own fields in a hidden block that GitHub does not show; you may delete that block once
AGK is gone. `/agk:uninstall` (see [the reference](reference.md)) prints every GitHub item AGK left; do them in this order:

1. **Stop the sessions.** Stop the scheduled tasks or loops that start AGK sessions (conductors and builders) for this
   project, so nothing acts while you remove the kit.
2. **Pause.** `/agk:uninstall --pause` makes one branch with `paused = true`; merge it. Governance and proof then pass with
   `agk paused`, the router labels nothing, and engineers merge as in any repository.
3. **Relax the ruleset.** Delete or relax the default branch's ruleset, whose required checks name the kit's workflows.
   Local mode has no ruleset: skip this step.
4. **Merge the removal branch.** `/agk:uninstall` makes one branch that deletes the kit's unchanged files and keeps your
   own work; review it, commit it and merge it.
5. **Then the rest.** Delete the `merge` environment and its secret `AGK_MERGE_TOKEN`, the branches named `claude/*` that
   builders left once their pull requests are closed, and the kit's labels; close the kit's own issues; remove the plugin on
   each machine.

Install from a release, not between releases, if you want step 4 to delete every kit file: an install from the default
branch with `--unreleased` holds files no release lists, and the removal keeps those as `changed`, for you to delete by hand.

## When something goes wrong

- **A scheduled run did not happen on Monday.** Expect the Monday issues hours late; in India, usually Monday evening. On
  2026-10-19 the metrics issues of the project's repository and of a fork came about 7 hours after their slot, and the report about
  7.5 hours. The drift audit of the project's own repository ran 4 hours 20 minutes after its slot on 2026-10-17. Wait a few hours, then start the workflow by hand
  from the Actions tab.
- **Actions is blocked or out of minutes.** The checks of a new head never start, and the Actions tab shows a job refused
  for billing or no run at all. Follow [local-mode.md](local-mode.md): it says how to disable the workflows, what the builders
  and the conductor run instead, what is lost, and how to come back when Actions returns.
- **A scheduled run never happens, in a fork.** Scheduled runs worked on a fork once Actions were on (the scheduled metrics run
  of a fork on 2026-10-19). If no scheduled run ever appears, enable the workflows from the Actions tab of the fork.
- **A workflow fails when it writes its issue.** Issues must be on for the repository: Settings, General, Features. The
  doctor checks it: run `/agk:doctor` and read the line `issues-disabled`.
- **`/agk:ruleset` says it cannot apply.** It needs admin on the repository and a logged-in `gh`. Run `gh auth status`. If
  you are not an admin, ask the owner. It prints the exact settings to apply by hand.
- **`proof` reads `not-proven`.** The reason is in the step name, `outcome: not-proven (reason)`, for example `red-on-head` (the
  tests fail on the head commit). Read the reason first; it names what to fix.
- **`make test` prints that the kit's own tests are not installed.** That is expected: they are not part of your repository. In a new repository `make test` takes well under a second (0.05 s measured) and runs your own tests, if you have any.
- **`numbers` fails: two requirements, two specs or two ADRs carry the same number.** Run `python3 scripts/agk/intake.py renumber <id>` with the id of your own requirement, spec or ADR, before or after you bring the default branch in; if bringing it in conflicts on the last line of `docs/requirements.md`, keep both sections before you run it.
- **A decision is recorded.** A new decisions-log row is one file `docs/runs/decisions/<YYYY-MM-DD>-<id>.md` holding that one table row, so two pull requests never touch the same lines; `docs/runs/decisions-log.md` is frozen at its length and `check_specs.py` refuses a row added there.
- **GitHub says the pull request has a conflict, only in `docs/runs/residuals.md` or `docs/runs/architect-catches-*.md`.** GitHub's check does not honour `merge=union`; run `git fetch origin && git merge origin/<default branch>` locally, git resolves it by keeping both rows, then push. Any other conflicting file is resolved by hand as before.
- **`pr-mode` fails.** In the default mode, `strict`, a person has one open pull request at a time (the older one wins) and a `Depends-on: #n` line in a body fails. Merge or close the older pull request, or remove the line. A repository that wants several open pull requests, with `Depends-on: #n` lines that fail until #n is a merged pull request or a brief closed as completed (an open brief, one closed as not planned and an unmerged pull request each fail with their own message; a dependency already on the default branch needs no line), sets `pr_mode = "flow"` in `agk.toml`; that file is protected, so the change comes with an ADR in the same pull request. New projects start `strict` and switch once the team knows the method.
- **A hosting platform runs `pip install .` at the root and the deploy fails, or you deploy a subfolder.** The kit's root `pyproject.toml` installs as nothing (`[build-system]` and `[tool.setuptools] packages = []`), so a host that auto-detects Python at the root now succeeds and installs nothing. A project that installed the kit earlier gets the two tables from `agk upgrade` when its file has a `[project]` table that is still the one the kit rendered (`name`, `version = "0.0.0"`, `requires-python` and `dependencies = []`, nothing else) and neither a `[build-system]` nor a `[tool.setuptools]` table; the upgrade appends them, changes no other line, and names the file in its plan (`pyproject.toml` is protected, so the change comes with an ADR). A `[project]` table you changed is yours: the upgrade leaves the file alone and prints how to add the tables by hand, only if the project builds no package, because `packages = []` would empty a real one. A project that deploys a subfolder sets the host's root directory to that folder.
- **A pull request is labelled `agk:ci-red` by a check that is not yours, or a check you want counted is ignored.** The router judges a pull request's CI, and the default branch, by the checks named in `required_checks` in `agk.toml` (default `["proof", "governance"]`) and no others: a failing preview build of a hosting service never makes a pull request red, and a listed check that has not reported keeps it `agk:ci-running`. To count one more check, add its exact name (the name of its check run, or the context of its commit status) to the list, for example `required_checks = ["proof", "governance", "build"]`; the file is protected, so the change comes with an ADR in the same pull request. A value that is not a list of names is refused, naming the setting.
- **Every check of a pull request is green, but it stays labelled `agk:ci-running`.** The router sets the label when a workflow it listens to finishes; `workflow_run` takes workflow names, not patterns, so `.github/workflows/agk-route.yml` lists by name each workflow that holds a check of `required_checks`. `agk upgrade` writes that list from `required_checks` and your workflows, and keeps names you added to it; `agk doctor` warns (`router-wake`) when a workflow of a required check is missing from it. So after adding a check to `required_checks`, run `agk upgrade` (the router file is protected, so the change comes with an ADR). Until then, any of these wakes the router at once: a comment whose first line starts with `Verdict:`, `Approve:`, `Approval:` or `Correction:`, or an edit of the pull request's title or description. An ordinary comment does not wake it.
- **A check fails on files the pull request did not change.** In CI the checks compare the change with the base that GitHub merged it
  with. The event's base sha can be older than the branch GitHub merged into, when other pull requests merged after yours was
  opened; the diff then holds their files. The step `Base of the merge ref` is the one place that sets `AGK_BASE` for a
  `pull_request` run: the first parent of the checked-out merge commit (`git rev-parse HEAD^1`), or the event's base sha when the
  checkout is not a merge commit. To reproduce a run locally, check out the merge ref and run
  `AGK_BASE=$(git rev-parse HEAD^1) make governance`; a stale `AGK_BASE` shows the symptom.
- **`make governance` fails.** Read the first line that does not start with `ok`. It names the rule, a setting or a path class.
- **`/agk:doctor` says `placeholder-team-reviewers` or `placeholder-team-codeowners`.** Step 4 was not finished: put your
  handle in `config/reviewers.yaml` and run `python3 scripts/agk/reviewers.py --codeowners --write`. Until then `make governance`
  fails on `reviewers --check`, naming `verdict_authors` or `spec_approvers`: the placeholder is never a listed verdict author
  or spec approver.

## What to do next

Read [the product-owner guide](product-owner.md) for what the Monday report says, [the security page](security.md) for what AGK
does with your code and credentials, and [the reference](reference.md) for every command. For a repository that already has code,
read [the existing-codebase guide](existing-codebase.md) before step 3. Run `/agk:doctor` for a report of what is misconfigured; it only reads.
