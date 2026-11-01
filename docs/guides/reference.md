# Reference

Every command and file of the kit, one section each. For the first steps in a new repository read
[getting-started.md](getting-started.md) first. This page is the former command reference of the README, moved here unchanged
in substance.

## Run the checks

    make governance   # all checks against the base branch (the default branch in agk.toml)
    make test         # tests of the checks (needs pytest)
    make lint         # ruff over the kit paths in agk.toml

The kit's own commands are in `agk.mk` (`make -f agk.mk agk-governance | agk-lint | agk-test`); the `Makefile` is thin
aliases of them. Kit tests are collected only through `agk.mk` (they need `AGK_KIT_TESTS=1`).

Set `AGK_BASE=<ref>` (or pass `--base`) to compare against another base. In CI the pull-request base SHA is used.

Before a push, `python3 scripts/agk/prepush.py [--body FILE] [--base REF] [--quick]` runs the fast checks CI would fail on
first, in order, and stops at the first failure with its message: the pull request body check (on `FILE`), `make lint` where
the Makefile has the target, `make -f agk.mk agk-governance` (no network; `not run` without `make`), the secret scan over the branch's commits when
`gitleaks` is installed (else `secret scan: not run`), and the tests that `test_plan.py` selects (`--quick` skips them). It prints
`prepush: <step> ok|FAIL|skipped (<s>s)` per step and exits 0 when no step failed, 1 when one did, 2 on a usage error (session
rule 31, ADR-0186). The optional hook `kit/templates/pre-push` calls it; see [getting-started.md](getting-started.md).
`python3 scripts/agk/reviewers.py --codeowners` prints the rendered CODEOWNERS; with `--write` it writes the file (in an
adopted repository only the marked block). `python3 scripts/agk/traceability.py` prints the requirement-to-test matrix to stdout; it is never committed.

## Installing

1. Create the target repository empty (no files).
2. Make one first commit directly on the default branch (a PR needs a base branch); record it in the target's
   ADR-0001.
3. From a checkout of agk, run init as a maintainer-approved step (an agent session blocks running a cloned script
   until a maintainer authorizes it):

       python3 scripts/agk/init.py TARGET [--dry-run] [--unreleased]

   Init never overwrites a differing file (it refuses and lists it) and a second run changes nothing.
   Init installs only the files of a release: run it from a release tag (`git checkout v<version>`). Between two
   releases it refuses, naming the release; `--unreleased` installs the checkout as it is, for the kit's own tests.
4. Apply the printed ruleset and repository settings by hand on GitHub; init configures nothing there.

See `docs/specs/0001-agk-init.md` and `docs/runs/k1-live-proof.md`.

## Adopting an existing repository

    python3 scripts/agk/adopt.py TARGET [--dry-run]

Run from a checkout of agk as a maintainer-approved step. TARGET is an existing git work tree. Adopt touches no
product file: it creates its own files (`agk.mk`, `agk.toml`, `scripts/agk/`, `.claude/`, `config/`,
`constitution/`, `docs/`, `.github/workflows/governance.yml`), appends one marked block to `.gitignore` and `.gitattributes`
(`scripts/agk/** linguist-generated=true`, so GitHub collapses the kit's scripts in diffs) and, when they
exist, to `CLAUDE.md`, `.github/CODEOWNERS` and `.github/PULL_REQUEST_TEMPLATE.md`, and refuses rather than overwrite.
The project's `Makefile`, `pyproject.toml` and tests are untouched. See `docs/specs/0002-agk-adopt.md`.

## Drift audit

    python3 scripts/agk/drift_audit.py [--today YYYY-MM-DD]

A read-only audit of the default branch: protected changes that reached it without an ADR (the last 7 days), done
requirements without a test marker, stale Draft specs and Proposed ADRs, overdue residuals (`(due YYYY-MM-DD)` on
a bullet, or a line of `docs/runs/residuals.md`), and reviewers and CODEOWNERS drift. The installed workflow
`.github/workflows/drift-audit.yml` runs it every Saturday and files at most one issue labelled `agk-drift-audit`;
a clean run writes nothing. GitHub may disable scheduled workflows after a period of repository inactivity: if
scheduled runs stop, start the workflow by hand (`workflow_dispatch`). See `docs/specs/0004-drift-audit.md` and
ADR-0012.

## Per-PR metrics

    python3 scripts/agk/metrics.py [--today YYYY-MM-DD] [--repo OWNER/REPO]

Reads the GitHub REST API (`gh api`, GET only) and local git objects, and prints the report for the ISO week before
`--today`: one derived record per closed pull request (rejections, blocked weakenings, deviations, cost class, review
rounds, protected classes, ADRs added, tests before and after, hours open to merge, whether the merged head was
cleared). Review rounds, rejection and the cleared head come from comments whose first line is `Verdict: cleared <short
sha>`, `Verdict: fix list` or `Verdict: rejected`. The installed workflow `.github/workflows/metrics.yml` runs every
Monday and files one issue per week labelled `agk-metrics` (it needs `issues: write`); a week with no closed pull
request is still written. See `docs/specs/0007-metrics.md` and ADR-0016.

## Doctor

    python3 scripts/agk/doctor.py [--kit-root PATH] [--repo OWNER/REPO] [--json] [ROOT]

A read-only report of what is misconfigured: the ruleset on the default branch against ADR-0001 decision 3 (a minimum, so
stricter is fine), the required status check `governance`, the placeholder team in `config/reviewers.yaml` and CODEOWNERS, a
missing `refs/remotes/origin/HEAD`, the drift-audit workflow (file, schedule, state), and with `--kit-root` the version and every
vendored file against the kit's copy. It reads GitHub with `gh api` (GET only) and holds no credential. A check it could not make
prints `??` with the reason (`gh-unauthenticated`, `no-admin`, `no-kit-root`, ...), never `ok`; exit 0 only when every check is
ok, 1 for an error finding, 4 for a warning or an unchecked item. See `docs/specs/0006-doctor.md` and ADR-0017. Two warnings
keep a project's CI fast and cheap: `ci-drafts` (a workflow of `required_checks` runs on draft pull requests) and
`ci-concurrency` (it has no concurrency group); the five defaults and their snippets are in `docs/guides/project-ci.md`.
With `--kit-root` it also warns `kit-behind` when `version` in `agk.toml` is older than the newest release of the kit's own
repository (the `repository` of the kit's `.claude-plugin/plugin.json`), naming both versions: one more GET, of that
repository's latest release. A kit newer than the newest release (a checkout between releases) is `ok`; a release it cannot
read is `??` (`no-release`, `release-unreadable`, `offline`, ...), never `ok`.

## Stalls

    python3 scripts/agk/stalls.py [--json]

Lists every place where the project's pull requests or sessions have stopped, each with its cause and its fix in one line:
`stall <kind> #<n>: <cause>; fix: <one plain step>`, or `no stall`. The kinds are `stale-label` (green checks, `agk:ci-running`
still on after 10 minutes), `no-verdict` (`agk:review` for 30 minutes with no verdict naming the head), `stuck-run` (a required
run queued or in progress for 60 minutes, or cancelled with no newer run), `red-default` (the issue "The default branch is
red" is open), `idle-capacity` (the plan names sessions to start and no brief was taken for 15 minutes) and `claim-no-pr` (a
live take with no pull request and no post by its session for 2 hours). `--json` gives the same. It reads with `gh api` (GET
only) and writes nothing; exit 0 with no stall, 3 with any, 1 when the repository cannot be read (ADR-0205).

## Pausing the kit

    python3 scripts/agk/doctor.py --paused [--ref REF] [ROOT]

To pause the kit, add the top-level line `paused = true` to `agk.toml` (before any `[table]`) in one pull request with an ADR,
since `agk.toml` is a protected path. Once it is on the default branch, governance and proof report success with the one line
`agk paused` and skip every other step, the router writes no label, the conductor and builder sessions stop with that line
(session rule 33), and `agk doctor` reports the state `paused` instead of its checks. On a pull request the workflows read the
setting at the base, so the pull request that pauses is itself checked in full, and no change can skip its own checks; a
push reads the commit pushed. The local targets (`make governance`, `prepush.py`) are unchanged and run every check. While the kit
is paused no pull request is checked in CI, the one that resumes it included. Remove the line to resume; nothing is deleted while
paused. Sessions read the setting on the default branch after a fetch, not on their own branch. `session.py` refuses `claim`, `next`, `queue`, `watch` and `after`
while the default branch is paused, with one line `agk paused` that names the setting, and exits 5 (ADR-0218). The query form above prints `agk paused` or `agk not paused` (exit 0), reads
only `agk.toml` (at `REF` when given) and calls no `gh`; a value other than `true` or `false` is refused by the setting's name
(brief #348, ADR-0196). `/agk:uninstall --pause` writes that line for you on a new branch `agk-pause` (see below).

## Removing the kit

    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/uninstall.py" TARGET [--write] [--remove-docs]
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/uninstall.py" TARGET --pause [--write]

`/agk:uninstall` runs `scripts/agk/uninstall.py` from the plugin (or a kit checkout), never the copy in the repository, since
the removal deletes it. Without `--write` it is a dry run and writes nothing. With `--write` it refuses a work tree with
changes, makes one new branch (`agk-uninstall`, or `agk-pause` for `--pause`) and writes the change there, uncommitted: you
review it, commit it, push it and open one pull request, which git can revert.

- **Deleted:** every kit file whose content (CRLF read as LF) equals a copy that some release row of the kit's
  `kit/hashes.json` lists for its path, whatever release the project was installed at; `agk.toml` when it holds only the kit's
  settings; `.github/CODEOWNERS` when it is what the kit generates from `config/reviewers.yaml`.
- **Edited:** a file that holds the project's own lines and an agk block a release shipped (`.gitignore`, `.gitattributes`,
  `CLAUDE.md`, the pull request template, `CODEOWNERS`) loses the block only; the project's `Makefile` loses the line
  `include agk.mk` when `agk.mk` goes (targets that call `agk-*` are yours to change).
- **Listed as `changed`, kept:** a kit file, block or `agk.toml` that the project changed; you decide.
- **Kept, never deleted or edited:** the project's own work: `docs/requirements.md`, ADRs, specs, briefs, `docs/runs/`,
  `docs/build-state.md`, `constitution/vision.md`, design documents and the tests (not the kit's own `tests/kit/`, which
  releases up to 0.27.0 installed), and `pyproject.toml` (a kit 0.1.0 or 0.2.0 install loses only its `[tool.agk]` stamp). `--remove-docs`
  lists those documents for you to delete by hand.
- **GitHub, printed only:** the ruleset to delete or relax, by name; the kit's labels; the issues it opened (the red-branch
  issue and the drift-audit, metrics and product-report issues); the plugin removal command. Each needs a person with admin
  rights; the tool does none of them.

The output names the protected classes the branch changes and prints an ADR skeleton; write the ADR yourself. After the
removal merges, `agk doctor` reports `no kit installed` (exit 0) instead of failing: in a git work tree with no `agk.toml`,
no `[tool.agk]` stamp in `pyproject.toml`, and none of `agk.mk`, `scripts/agk/`, `tests/kit/`, the governance, proof and
router workflows and the stop hook (brief #348 build (b), ADR-0203).

## Local mode

When GitHub Actions is blocked (minutes exhausted, billing blocked, an outage), follow [local-mode.md](local-mode.md): how to
disable and re-enable the workflows with `gh workflow`, what a builder runs and pastes as its `Local evidence:` line, what the
conductor runs instead of reading CI, what is lost, and the one issue that records every merge (session rule 30, ADR-0182).

A person enters local mode with `python3 scripts/agk/local_mode.py enter` and leaves it with `python3 scripts/agk/local_mode.py
leave`: each lists the workflows and the one `gh api` call that disables (or enables) each, the kit's and the project's, as a dry
run that changes nothing; `--write` makes the calls, one line per workflow, and reports a refused call while it makes the rest.
`--write` is the person's: it is refused inside an agent session and denied in the kit's settings. `leave` takes the start of
local mode from the day the open record issue names (or `--since YYYY-MM-DD`), enables only the workflows disabled since then,
and lists the pull requests merged on local evidence since then and the catch-up run of each check of `required_checks` on the
default branch, or `catch-up: not run yet`; a red catch-up says to file a priority-0 brief (exit 3 on a refused call or a red
catch-up, 4 when the start, the merges or the catch-up are unknown; ADR-0213).

Several sessions on one machine take turns on heavy steps (governance, the tests, proof) with `python3 scripts/agk/lock.py run
--name heavy --session <id> -- <command...>`: it waits its turn, printing the holder once a minute (`--timeout S` gives up with
exit 3), runs the command without a shell and releases the lock when it ends, also on failure or interrupt, with the command's exit
code. A lock left by a session that died is cleared with a line saying so: when neither its process nor its command runs on this
machine, or when it is older than `lock_stale_minutes` (120 by default). The lock is a folder in the user's temp folder, or
`lock_dir` in `agk.toml`. `python3 scripts/agk/lock.py status --name heavy` prints the holder or `free` (ADR-0191).

When several pull requests are ready, `python3 scripts/agk/batch.py PR [PR...] [--command CMD] [--json] [--record FILE]` merges
their heads in a scratch worktree and runs the heavy command (`make -f agk.mk agk-project-test` by default) once under the
heavy-step lock, and per pull request only when that run fails; it only reports, one `#<n> <status> <sha12>` line per pull
request ([self-hosted-runner.md](self-hosted-runner.md#a-batch-run-of-ready-pull-requests), ADR-0235).

A machine that can carry several heavy runs sets `lock_slots` in `agk.toml` (a positive whole number, 1 by default; with 1
nothing changes): `run` takes any free slot (slot 1 is the folder `agk-lock-heavy`, slot k `agk-lock-heavy.k`) and `status`
prints one line per slot with its holder. `run --priority P` (0 to 3, 2 by default) orders the waiting runs: a run that waits
leaves a ticket, a free slot goes to the lowest priority and then to the oldest ticket, and the ticket of a process that no
longer runs is dropped with a line saying so. `lock_cleanup` in `agk.toml` (empty by default; the kit ships none) is a command
run once, through `sh -c`, when the lock of a run whose process no longer runs is cleared, with `AGK_LOCK_SESSION` and
`AGK_LOCK_PID` of that run; its output is shown, and a failure is reported and never blocks. It is not run for a lock cleared by
age, whose run may still go on, nor for one that names no session. The locked command gets `AGK_LOCK_SESSION`, so a project can
label what it starts, for example containers, by session (ADR-0231).

A builder in local mode records its run with `python3 scripts/agk/prepush.py --record FILE` (ADR-0208), and the conductor checks
that record before its verdict with `python3 scripts/agk/evidence.py check RECORD [--head SHA] [--sample N] [--json]`: `stale`,
`dirty` or `failed` when the record names another head, an unclean tree or a failed step; otherwise, in a temporary worktree of
the head under the heavy-step lock, governance runs and a sample of the steps (one by default, chosen from the head sha) re-runs
as prepush builds them from the head, never as the record writes them, exit codes compared; a recorded command that is not what
prepush runs is a difference. It ends with one `Evidence check: agrees|differs, ...` line to quote, posts nothing, and
exits 0 when the record agrees, 1 when it differs, 2 on a usage error or a bad record, 3 on an I/O error (ADR-0233).

## Actions minutes

    python3 scripts/agk/minutes.py [--json | --line] [--repo OWNER/REPO] [--today YYYY-MM-DD] [--api-dir DIR]

Shows how many GitHub Actions minutes the repository has used this month and warns before they run out. It prints the
minutes used, the plan's included minutes where the billing API answers, an estimate from the run history, the minutes per
merged pull request, and a warning past `minutes_warn` percent; a figure it cannot read is `unknown`, never 0. It reads with
`gh api` (GET only) and writes nothing. It also gives a level (`ok`, `50%`, `minutes_warn`, `95%`) and the day the included
minutes run out at this month's rate; `--line` prints only that, the line that `doctor.py` (`actions-minutes`) and
the launch skill print (ADR-0215). See [project-ci.md](project-ci.md#how-many-minutes-are-left) and ADR-0184.

A private repository short of minutes can run its own heavy jobs on an ephemeral self-hosted runner, one job per runner, no
secret beyond the job's own, never for forks, while governance and proof stay on GitHub-hosted runners:
[self-hosted-runner.md](self-hosted-runner.md) (ADR-0217).

## Test plan

    python3 scripts/agk/test_plan.py [--base REF] [--head REF] [--json] [ROOT]

Shows, before anything runs, which tests proof will run for a change and why. For each `[proof]` area it lists the added or
changed test files, the command line with `{files}` filled in and its folder, then the areas with nothing to run and the test
files in no area as "not run by proof"; without the table it prints `project_tests` and the files it selects. It reads git and
files only and runs no test. See [existing-codebase.md](existing-codebase.md#step-4-tell-the-proof-check-how-to-run-your-tests)
and ADR-0185.

## Core audit

    python3 scripts/agk/core_audit.py [--since YYYY-MM-DD] [--json] [--write] [--today YYYY-MM-DD] [--repo OWNER/REPO | --api-dir DIR] [--authors LOGIN,LOGIN]

Reports which of the kit's governance checks and rules ever refused something, and which never fired. It lists each check
with the pull requests whose governance run failed on it, each session and spec rule with the verdicts that cite it, and the
totals; an unread page is `at least N` or `cannot-check`, never zero. It reads with `gh api` (GET only) and writes only to
stdout, except `--write`, which writes `docs/runs/core-audit-<date>.md` as evidence, not a decision. It audits the kit itself
and is not installed in projects. See
[ADR-0188](../adr/0188-the-kit-reports-which-of-its-checks-and-rules-ever-fired-req-011-brief-328.md).

## Engines

`[engines]` in `agk.toml` names, for each of `vision`, `stack`, `design` and `review`, a skill the session can see. A key that is
absent means the kit's own template is used; the kit pins no engine (a commented example in the template of `agk.toml` shows the
shape). The owner chooses once, and a change is a change of `agk.toml`, a protected path, so it needs an ADR in the same pull
request that names it. An engine only drafts: its output is always written through the kit's template and passed through the
kit's checks, and an engine never decides, never approves, and never edits a protected file by itself (SPEC-0029 rule 3).
`agk doctor` reports each engine as `present` (the skill file exists in the project's `.claude/skills/`, in the user's
`~/.claude/skills/` or in the plugin; only its existence is tested), `absent` (the template is used) or `missing` (named but
not found), and names the setting, never the skill's name. A skill that another plugin provides is not read, so such a name is
reported as unchecked (verify how Claude Code lists plugin skills).

`/agk:vision` is the step an owner takes from a brief idea (SPEC-0029 rule 4). It keeps the idea, in the owner's own words and
unchanged, as the first section of `constitution/vision.md` (between two markers with its digest, so `engines.py vision-check` and
`playbook.py check-start` fail an altered idea), asks the ten discovery questions (users and payer, what exists, where it runs, data,
scale, compliance, devices and widths, accessibility, languages, brand), and the charter records every answer or `not known yet`. The
engine in `[engines]`, or the kit's template, only drafts; the owner approves the step by merging before the next.

`/agk:stack` (SPEC-0029 rule 5) writes one Proposed ADR, `docs/adr/<n>-stack-options.md`, that sets out two or three stacks as options,
each with its trade-offs and the practices it brings. Every practice is marked `check` (it can be verified, and the build that adopts
the stack adds the governance step: pinned actions, least privilege, security headers, a host-boundary test) or `judgement` (recorded
only, enforced by review). The architect accepts one option, and the ADR then locks it (`Chosen`); `engines.py stack-check` fails an
ADR with another number of options, an option without trade-offs or practices, a practice that is not marked, or a lock that does not
name exactly one option. An option is accepted in one plain step: one ordinary commit, in its own pull request, sets `Status: Accepted`
and `Chosen: Option <X> — <one-line reason>` together; `stack-check` accepts the pair and the verdict is a plain `cleared`. It is not a
`Final:` commit, which may change only status lines; `check_final_clearance.py` says so when one changes `Chosen`.

## Design check

    python3 scripts/agk/check_design.py [--root DIR]

An installed check, a step of `make governance` and of the governance workflow (SPEC-0029 rules 7 and 9). It reads `docs/design/theme.md` and the mockup folders `docs/design/mockups/<date>-<name>/` and fails, naming the
rule and the path and never a value, on: a script or an event handler, an external request or a loaded resource, a colour that is not a token
(every colour of a mockup is a `var(--token)`), tokens that are not one block with a light and a dark set, a contrast under 4.5:1 (computed from
the hex tokens in both modes, for the pairs the theme lists under `## Contrast`), a brand value with no `source:`, and an evidence line that
points to no mockup folder. Two things it prints without failing: `design: the theme is not approved yet` when the evidence folder's `README.md`
has no line `Approved by <name> on <YYYY-MM-DD>`, and `at risk design: placeholder brand` when a brand value is still a `[bracketed]` placeholder
(SPEC-0029 rule 7). The files it reads are written by `/agk:design` (the theme from the engine named by `design` in `[engines]` or from the kit's template, a mockup folder with `Approved: not yet` in its `README.md`, and four screenshots, 360 and 1280 px wide, light and dark, when a headless browser is found) or by hand. The approval line is the owner's: the session never writes `Approved by`. With no `docs/design/` it prints `ok design (no design record)`.

## Upgrade

    python3 scripts/agk/upgrade.py TARGET [--dry-run]

Run from the kit checkout or the plugin root (not installed into targets). Brings an init or adopt target from the kit
version in its `agk.toml` to this kit: a file that equals the kit's copy is skipped, a file that is an old released copy is
replaced, a new file is created; a file the user edited stops the whole run and nothing is written; a file removed from
the kit is reported, never deleted. `kit/hashes.json` (a committed generated file, regenerated by
`python3 scripts/agk/kit_hashes.py --write`) says what each file was at each version. User-owned files are never
rewritten; changed templates and new `agk.toml` keys are printed; only the `version` line of `agk.toml` is set, last. It
prints the target's protected classes and an ADR skeleton for the upgrade pull request. An install stamped only in
`pyproject.toml [tool.agk]` (kits 0.1.0 and 0.2.0) is upgraded through that stamp: `agk.toml` is created last and `pyproject.toml` is
never written. From kit 0.28.0 the kit's own tests are not installed in a project: an upgrade from an earlier kit deletes the
unmodified files of `tests/kit/` and keeps one you edited, reporting it as `removed-in-kit (modified, kept)`; that file tests the kit
and cannot run without the kit's fixtures, so delete it in your own change. The kit's `.gitignore` lines sit
between `# >>> agk` and `# <<< agk`: add your own ignore lines outside that block, and the upgrade and the doctor compare and
replace only the block and report your lines once as `project lines kept: n`; an older `.gitignore` without the markers, the kit's
lines followed by yours, gets the block on the next upgrade (ADR-0164). After a written upgrade it ends with one line
`opt-in: <setting>: <summary>` for each setting of each entry of the kit's `CHANGELOG.md` between your old version and
the new one that ends with the marker `(opt-in: <setting>)` or `(opt-in: <setting>, <setting>)`: a feature that stays off
until you set that setting in `agk.toml` (a change that needs an ADR). An entry that starts `<version> added ` speaks for
that earlier release and is listed when your upgrade crosses it, so an upgrade from 0.58.0 or older also lists the opt-in
settings of 0.59.0 (ADR-0193). With no such entry it prints nothing more; a dry run lists none, and the listing writes
nothing (ADR-0181). See `docs/specs/0008-upgrade.md` and ADR-0018.

## Experimental: reviewer agent

Experimental, advisory and never a gate: the reviewer is not counted as review and human review stays required. In
the shadow reviews it caught 0 of 5 human findings, 3 recorded and 2 held-out (`docs/runs/shadow-review-4.md`).
It is not installed by default: `agk init` and `agk adopt` do not write `.claude/agents/reviewer.md`,
`scripts/agk/review_context.py`, `scripts/agk/check_review_report.py` or their tests. To opt in, set
`experimental_reviewer = true` in `agk.toml` and run `agk upgrade` (or `/agk:upgrade`); `agk doctor` then checks those files
too. This repository keeps its own copies for the experiment.

    python3 scripts/agk/review_context.py [--base REF] --body PR_BODY.md > review-context.md
    # ask the `reviewer` subagent (.claude/agents/reviewer.md) to review review-context.md, save its answer
    python3 scripts/agk/check_review_report.py --context review-context.md --report report.md

The reviewer reads one pull request against its stated intent and the repository's Approved text, and returns a
verdict (`cleared`, `fix list`, `rejected`) with cited findings. It is read-only (`Read`, `Grep`, `Glob`), advises
and never approves or merges; the context and the report are local files and are never committed. The optional
`agk.toml` keys `review_diff_cap` (default 4000) and `review_other_cap` (default 1500) set the line caps of the
context. The context holds the full current text of every changed file and the operating rules of `CLAUDE.md`,
so a rule next to a change is visible. See `docs/specs/0003-reviewer-agent.md`, ADR-0011 and `docs/runs/shadow-review-template.md`.

## Plugin

The workflow commands are also a Claude Code plugin; this repository is its marketplace. The repository works without it
(`make governance`, the stop hook, the workflows and the `reviewer` subagent need no plugin).

    claude plugin marketplace add gbvraju/agk
    claude plugin install agk@agk

| Command | What it runs | Writes |
| --- | --- | --- |
| `/agk:init` | `scripts/agk/init.py` | new files in the repository |
| `/agk:adopt` | `scripts/agk/adopt.py` | owned files and marked blocks |
| `/agk:doctor` | `scripts/agk/doctor.py --kit-root` the plugin | nothing (a report) |
| `/agk:upgrade` | `scripts/agk/upgrade.py` | vendored files |
| `/agk:uninstall` | `scripts/agk/uninstall.py` (a dry run; `--write` after you say yes) | one new branch: the kit's unchanged files deleted and its own lines removed, or `paused = true` with `--pause`; nothing committed |
| `/agk:ruleset` | `scripts/agk/ruleset.py plan`, then the `gh api` commands it prints, after you say yes | the default branch's ruleset and two repository settings (add-only) |
| `/agk:start` | `scripts/agk/playbook.py start-ids`, `check-start` | `constitution/vision.md` and a project charter ADR on a new branch |
| `/agk:vision` | `scripts/agk/playbook.py start-ids`, `scripts/agk/engines.py vision-write`, `questions`, `vision-check`, `playbook.py check-start` | `constitution/vision.md` (the owner's idea unchanged as its first section) and a project charter ADR on a new branch |
| `/agk:stack` | `scripts/agk/engines.py stack-ids`, `stack-write`, `stack-check` | one Proposed ADR of stack options on a new branch |
| `/agk:design` | `scripts/agk/design.py write`, `screenshots`, `scripts/agk/check_design.py` | `docs/design/theme.md` (when absent) and a mockup folder with `index.html` and `README.md` on a new branch |
| `/agk:launch` | `scripts/agk/session.py plan`, `scripts/agk/launch.py prompts` | nothing in the repository (after you say yes, one session per planned slot is started through an adapter, or its prompt is printed) |
| `/agk:review-pass` | `scripts/agk/session.py review-queue`, the conductor's protocol, `gh api`, then `scripts/agk/session.py plan --json` and `scripts/agk/launch.py prompts` | one `Verdict:` comment per pull request that needs one (never two on one head), from a conductor session; at the end it prints the plan, and starts the planned sessions through the project's adapter only with `[flow] auto_start = true` |
| `/agk:confirm` | `gh api` (GET), the conductor's protocol | nothing (solo mode: prints the one `Confirmed:` comment for the person to post; a session never posts it) |
| `/agk:spec` | `scripts/agk/new_spec.py`, `scripts/agk/intake.py` | a Draft spec, or a requirement proposal with its ADR draft, or (from one sentence) a requirement, a Draft spec and an ADR stub |
| `/agk:architect` | `scripts/agk/playbook.py architect` | nothing (prints how to start `claude --agent architect`) |
| `/agk:issue` | the issue templates and your own `gh issue create`, after asking | one GitHub issue |
| `/agk:brief` | `scripts/agk/new_spec.py` | one brief |
| `/agk:review` | `review_context.py`, the project's `reviewer` subagent, `check_review_report.py` | local files, never committed |

No command commits, pushes or merges (`/agk:ruleset` and `/agk:issue` write to GitHub only after you say yes, and `/agk:review-pass` writes only `Verdict:` comments, from a conductor session), and none sets a spec `Approved` or an ADR `Accepted`. `/agk:review` is advisory.
GitHub issues are intake only: decisions, requirements, specs and ADRs live in the repository, and an issue decides
nothing (`.github/ISSUE_TEMPLATE/`; a pull request may link one with an optional `Issue: #nnn` line).

To let a team enable the plugin, `agk init` and `agk adopt` print two entries for `.claude/settings.json`
(`extraKnownMarketplaces` and `enabledPlugins`); they merge nothing. What to know before you rely on it:

- A project-scope plugin loads only after the user accepts the workspace trust dialog for the folder, and each
  collaborator installs it on their own machine.
- A cloud session does not add the marketplaces a repository lists under `extraKnownMarketplaces`, so the plugin is
  absent there; the repository's checks do not depend on it.
- A plugin runs with the user's privileges. This one ships no hook, server, monitor or `bin/`, and its scripts are the
  ones in this repository.
- An agent that edits `.claude/settings.json` could point `extraKnownMarketplaces` at another source; the file is a
  protected path class and its edit is an `ask` rule in `.claude/settings.json`.
- Each command may ask for approval once per session. Releases are tags `vX.Y.Z`; a third-party marketplace does not
  auto-update by default, so an installed version changes only when the user updates.

See `docs/specs/0005-distribution.md`, ADR-0019 and `docs/runs/spec-0005-verify-facts.md`.

## Developing the kit

This section is for a developer of the kit repository itself; a project that only installs the kit does not need it.
In strict mode (the default of `agk.toml`) a kit build pull request bumps the three versions (`agk.toml`,
`kit/manifest.json` and the plugin) and regenerates `kit/hashes.json`, as before.

In flow mode (`pr_mode = "flow"`, which this repository uses) a kit build pull request does not bump:

1. Leave the three versions as they are and add one file `changelog.d/<slug>.md` (the pull request number or the branch
   slug, `[a-z0-9-]+`) holding one line, `- <one-line change>`, with no pull request number. The build does not edit
   `CHANGELOG.md`; the shape is `kit/templates/changelog.md`. A fragment is required exactly when a file the installer
   writes changes, and a check fails a build that adds none or more than one. A change that a project switches on by a
   setting ends its line with one marker, `- <one-line change> (opt-in: <setting>)` (a key of `agk.toml`, or `table.key`;
   for a table, its name; several settings are separated by `, `, each once); the release keeps it, and `upgrade.py` lists
   it to each project that upgrades past it, one line per setting. The summary it shows is the change up to its first
   `: `. A line that starts `<version> added ` speaks for that earlier release and is listed to an upgrade that crosses it.
2. The build does not edit `kit/hashes.json` either: the table is a function of the history and the tree, and the release
   regenerates it, so the check of the table leaves the row of the current version to the release.
3. A build never collides with another on `CHANGELOG.md` or `kit/hashes.json`, because it does not touch them; each
   fragment is a file of its own.

One release pull request bumps for all the builds. A session opens it on the maintainers' word. It runs
`python3 scripts/agk/changelog_fragments.py gather --version <new version>`, which moves the lines under `## Unreleased` and
the line of every fragment (as `- #<n> <one-line change>`, `<n>` read from the commit that added it, in pull request
order) under `## <new version> (<date>)` of `CHANGELOG.md` and deletes the fragments; it then raises the three versions
(together, to one greater number) and regenerates the table with `python3 scripts/agk/kit_hashes.py --write`. The pull
request changes only `CHANGELOG.md`, the deleted fragments, the three versions and `kit/hashes.json`.
`scripts/agk/check_release.py` fails a release pull request that changes any other file, leaves a fragment or does not move a
line unchanged; the maintainers merge it and tag it. Tag only the merge commit of a release pull request. In this repository the workflow `agk-tag.yml` (not installed in a project, because its script is kit-only) runs `scripts/agk/check_tag.py` on every pushed tag `v*`: it fails the job, and opens or updates the issue `The tag <tag> is not a release` (a plain issue labelled `agk-release`, for a person, not a brief), when the tagged commit is not a release (no section of the tag in `CHANGELOG.md`, a fragment left, a file that states another version, or a table that does not match). It deletes and moves no tag and makes no release: the fix is to delete the tag and its release by hand and to tag the merge commit.

## Existing scanners

Project-wide scanners (bandit, flake8, pylint, mypy) that read the whole tree also read the kit's code. The kit's
subprocess calls carry justified `# nosec` comments and its type findings are fixed, so what remains for bandit is
the bare `assert` of the kit's tests (rule B101). Init and adopt print the exclusions below after a run and write
none of them (ADR-0010, `docs/runs/scanner-fix.md`):

```
Scanner exclusions (print only; the kit writes none of this). The kit's code under scripts/agk and
.claude/hooks is the kit's, not yours. If a scanner you run reads the whole tree, exclude those paths in your own
configuration:
  bandit:  bandit -r . -x ./scripts/agk,./.claude/hooks
  flake8:  flake8 --extend-exclude scripts/agk,.claude/hooks
  pylint:  [tool.pylint.main] ignore-paths = ['^scripts/agk/.*$'] and ignore = ['.claude']
  mypy:    [tool.mypy] exclude = ['^scripts/agk/', '^\.claude/hooks/']
```

Licence: Apache-2.0.
