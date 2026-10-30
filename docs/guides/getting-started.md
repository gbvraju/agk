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

1. **File the work as a brief.** A brief is an issue labelled `agk-brief`. Create the label once (the maintainer does; `session.py next` finds nothing without it), then write the issue in this shape and check a saved copy before filing it with `python3 scripts/agk/check_brief.py FILE`, which prints `ok brief`:

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
```

   `Depends-on` lines are optional, one per issue, and the brief waits until those issues are closed. `Size` is `S`, `M` or `L`. `Advances` names the requirements the work builds, separated by commas (`Advances: new` for a first brief that asks for a requirement), `Touches` the path globs it changes, separated by commas, and `Priority` is `1`, `2` or `3` (optional; 2 when absent). `check_brief.py FILE --root .` also fails an `Advances` that names a requirement `docs/requirements.md` does not have. A brief built in parts may carry one more line, `Builds: (a) the first part; (b) independent: the second part`: `session.py plan` and `/agk:launch` then name the next build that is not merged and has no live take and no open pull request (`build (b)` of brief #12), a build waits for the unmerged builds before it unless its text starts with `independent:`, and the session claims exactly that build with `session.py claim --brief 12 --build b`. A pull request names the build it delivers in its title, as `brief #12 build (a)`, and nowhere else (a sentence in its body never counts), and every open brief that the plan does not start is listed with its reason.

2. **Start a builder session.** In a fresh session run `python3 scripts/agk/session.py next --session <a short name>`. It prints the first free brief and takes it with one comment, `taken: <name> <date>`; it says why it skipped each of the others, and `no brief` when none is left. The session builds, pushes and opens one pull request, and stops. `next` takes nothing and prints `full <open>/<max>` when `[flow] max_builders` (3 by default) builder pull requests are open, skips a brief whose `Touches` overlap open work, and takes the briefs by `Priority`. Before every push run `python3 scripts/agk/session.py push-check`: it prints the files in which your head conflicts with the default branch and exits 1, or prints nothing. Then run `python3 scripts/agk/prepush.py` (add `--body FILE` with a saved copy of the pull request body, `--quick` to skip the tests): it runs the body check, `make lint`, the governance checks, the secret scan over the branch (when `gitleaks` is installed) and the tests the test plan selects, one timed line each, and stops at the first failure with its message, so a push rarely goes red in CI for a reason seconds of local checking would catch. On Windows, where `make` is not installed by default, the lint and governance steps are not run and say why, and the run ends `prepush: passed; not run: governance` (CI still runs governance); install make (`winget install ezwinports.make`) for the full local run. If you want git to run it for you, copy the optional hook yourself: `cp kit/templates/pre-push .git/hooks/pre-push && chmod +x .git/hooks/pre-push` from a clone of the kit (the kit never installs a hook; `git push --no-verify` skips it).


   To decide how many sessions to start, run `python3 scripts/agk/session.py plan` (add `--json` for the same plan as data). It reads GitHub and posts nothing, and prints in plain words, for example `Start 2: builder-a takes #250, builder-b takes #252. #251 waits for #250 (both touch scripts/agk/route.py). 3 pull requests wait for your merge: #240, #241 (safe to merge together), #243 after #240 (both change docs/x.md).` It never starts two briefs whose `Touches` overlap in the same wave, counts a claim that has no pull request yet as a running builder, and starts the smallest of the ready briefs, `max_builders` less the running ones and `reviews_in_flight` (3 by default) less the pull requests waiting for a verdict. While the pull requests labelled `agk:ready` exceed `merge_hours` (1 by default) times your merge rate of the last 14 days, it starts none and says so (it never stops a running session; with no merge in that time the rate is unknown and the limit does not apply). It lists the ready pull requests that share no changed file as one set you can merge together, marks those that change a protected path, and lists a ready pull request more than `stale_commits` (20 by default) behind the default branch for its builder to update, not for you to merge. A brief with the line `Status: stale` or the label `agk-stale` is skipped by `plan` and `next`. The three settings are whole numbers in the `[flow]` table of `agk.toml`.
3. **Start the conductor.** In another session that built nothing, accept the workspace trust dialog of the folder (the role's guard hook does not run without it) and start `claude --agent conductor`. It reviews every open pull request, runs its pre-verdict steps and posts one `Verdict:` comment on each; it edits no file and never merges.

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

4. **Let the builder wait.** After every push the builder runs `python3 scripts/agk/session.py watch --pr <number>`. It ends with one line when a verdict by a listed author names the pull request's head, when the pull request is merged or closed, when it has a conflict with its base, when a listed author posts a `Correction:` comment on the pull request or on the brief it took (`correction #<n> (comment <id>): ...`: the conductor was wrong about a cause, and the builder wakes on the correction with no person carrying it), or when the router's `agk:` label on the pull request changes (`label <name>`, for example `label agk:review` once the checks are green; the router sets one label per pull request from GitHub events). A watch that starts after a verdict for the current head, or after a `Correction:`, which landed since your last `Report:`, ends at once with that line; restart it with `--since <comment id>` (the id the line printed) when you have acted on it and only wait for CI or the merge. A wait that cannot read GitHub for five polls in a row ends with `error: <what> cannot be read` (exit 4) instead of waiting silently, or with `github-unreachable: <what> cannot be read; local head <sha> not pushed; next: push, then post the Report:/Question:` when `gh` could not connect (the session's own output is then the only channel left). `watch --merged <number>` waits for another pull request's merge, for a `Depends-on`. Start `watch` so that its end wakes the session: in Claude Code, as a background task (its end re-invokes the session); in another runtime, the equivalent that wakes the session when the command ends. Never in the foreground, and never detached with `&`: the session then sits idle after its verdict. A session that restarts after its machine was reclaimed runs `python3 scripts/agk/session.py queue --role conductor|builder|person` first: it lists the open pull requests whose label is that role's (`empty` when none), and the session carries on from there.

5. **Merge from the report.** The weekly report and the inbox list, first under Needs you, the group **Ready to merge**: the open pull requests whose head carries a clearing verdict. Merging is yours; no session merges, tags or enables auto-merge. A person approves every spec: for an intake the conductor ends its verdict with `Approval: SPEC-<n> <path> Draft -> Approved, waiting for a person: post "Approve: SPEC-<n>"` (the router labels the pull request `agk:approve`), and you post one comment whose first line is `Approve: SPEC-<n>`: no commit id to type, the text you approve is the spec as of your comment, and the approval stops counting if a later commit changes the spec apart from its status line. The long line `Approve: <head> SPEC-<n>` still works. A comment that an agent posted through its GitHub App never counts as your approval (`agent_apps` in `agk.toml`, default `["claude"]`), and while that list is not empty an approving GitHub review does not count either, because a review cannot show which app posted it: post the comment yourself, from your own account (the router tells you once). A project that sets `agent_apps = []` counts an approving review (at its own commit) when the pull request sets one spec `Approved`; `docs/guides/security.md` says what this proves and what it cannot. Only an account listed in `spec_approvers` of `config/reviewers.yaml` (user handles, never a session or conductor account) counts, and `check_final_clearance.py` fails a spec set `Approved` without that line. In solo mode (`review_mode = "solo"` with one person listed, ADR-0179), `/agk:confirm` prints one `Confirmed:` comment that counts as the verdict, its `Final:` lines and the spec approval together; you post it yourself, from the browser or the GitHub app (a session never does, session rule 29), and then re-run the governance check or push, because until amendment 97 is decided nothing re-runs it for you.

6. **When the credits run out.** Sessions stop without warning: the account runs out of credits or tokens, a usage limit is reached, an idle machine is reclaimed, or a person closes the session. Every session stops, and nothing it pushed is lost: a builder commits `checkpoint:` steps to its branch and keeps one `Progress:` comment on its pull request. The GitHub side (the router, the checks and the labels) keeps running and needs no model. Actions minutes on private repositories are a second budget, which the router uses one short job per event. When credits return, start a session with `python3 scripts/agk/session.py next --session <name>`: it offers a pull request that has waited on its builder for `stall_hours` before any new brief, and `python3 scripts/agk/session.py resume --pr <number>` prints where that work stands, so the new session continues from the branch and the progress line instead of starting again. A builder may end a `Report:` line with `Usage: <n> tokens` when its runtime shows the figure, the usage since the previous `Report:` of the same pull request and not a running total (a session that can only read a running total subtracts the total it reported last); the weekly report sums what is reported for each pull request and says `usage not reported` otherwise, never zero.

7. **Start builders by a launcher.** AGK ships no launcher that runs on its own, and no session starts, stops or reviews another, except that a session starts other sessions when a person runs `/agk:launch` and confirms its plan (it runs `python3 scripts/agk/session.py plan`, asks `yes` or `no`, then starts one session per planned slot through an adapter: in a runtime with one-time scheduled tasks one task for each session, firing at once, with the standard builder prompt; anywhere else it prints one ready-to-paste prompt for each session; it creates no recurring task, holds no credential and starts nothing later). A launcher that runs without a person is what a team writes or configures for its own runtime, and this is the contract it keeps. `python3 scripts/agk/session.py demand` prints one JSON line `{"ready": r, "open": o, "max": m, "start": s}`: `r` is the number of briefs `next` would not skip, `o` the open builder pull requests, `m` the `max_builders` of the `[flow]` table of `agk.toml` (3 by default) and `s = min(ready, max - open)`, 0 when negative. A launcher starts `start` builder sessions and nothing else. Each one runs `python3 scripts/agk/session.py next --session <a short name>`, works on what it hands out, and ends on `no brief` or `full` when there is nothing for it. A session started by a launcher uses `assign = "next"` in the `[flow]` table of `agk.toml` (the default): when its work is done it runs `python3 scripts/agk/session.py after --session <a short name>`, which is `next`. With `assign = "conductor"`, a session that finishes posts `Request:` on the one open issue labelled `agk-conductor` and waits there with `session.py watch --assign <a short name>` for the conductor's `Assign:` line. Two examples follow; both only read `demand`, and starting the sessions is the team's own step.

   A scheduled task of a session runtime (the text of the task):

   ```text
   Every 30 minutes run `python3 scripts/agk/session.py demand`. If "start" is more than 0,
   start that many builder sessions, each with this prompt:
   "Run `python3 scripts/agk/session.py next --session <a short name>`, build what it hands
   you, and stop on `no brief` or `full`."
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

8. **Automatic starts after a review pass.** Each `/agk:review-pass` ends by re-planning (brief 331, ADR-0190): the conductor runs `python3 scripts/agk/session.py plan --json` and prints its `Start` and `waits for` lines in the pass's last lines, so a brief that a merge unblocked is named at once. By default it starts nothing and prints the ready-to-paste prompts of the sessions to start, as `/agk:launch` does. To let the pass start them itself, set both settings in the `[flow]` table of `agk.toml`, a protected change with an ADR in the same pull request:

   ```toml
   [flow]
   auto_start = true
   launch_adapter = "scripts/start-session-cloud.sh"
   ```

   The pass then runs `python3 scripts/agk/launch.py prompts --plan <the plan> --adapter <launch_adapter>`, the one new command the conductor's guard allows, and only with the adapter exactly as written there. `launch.py` splits the command into words and runs it without a shell, from the folder the conductor runs in, once for each session the plan names, with the prompt on its standard input and `AGK_SESSION`, `AGK_BRIEF` and, for a brief built in parts, `AGK_BUILD` in its environment; it never starts more than the plan's capacity, and each started session claims its own brief. A failing adapter is reported in the pass's last lines and not retried. The adapter is a short script the project owns, and runs with the environment of the conductor's session; it holds no credential of its own. The kit installs neither of the two examples below; adapt each to your setup and try it once by hand (`echo hello | AGK_SESSION=builder-x scripts/start-session-local.sh`) before you turn `auto_start` on.

   A local terminal adapter, a new terminal tab running `claude` with the prompt `(verify: the terminal's command and its options are your desktop's; this one is GNOME Terminal)`:

   ```bash
   #!/usr/bin/env bash
   # scripts/start-session-local.sh: one new terminal tab per session, running claude with the prompt.
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
- **GitHub says the pull request has a conflict, only in `docs/runs/decisions-log.md`, `docs/runs/residuals.md` or `docs/runs/architect-catches-*.md`.** GitHub's check does not honour `merge=union`; run `git fetch origin && git merge origin/<default branch>` locally, git resolves it by keeping both rows, then push. Any other conflicting file is resolved by hand as before.
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
