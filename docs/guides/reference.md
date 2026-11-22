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

Before a push, `python3 scripts/agk/prepush.py [--body FILE] [--base REF] [--quick] [--no-lock]` runs the fast checks CI would
fail on first, in order, and stops at the first failure with its message: the pull request body check (on `FILE`), `make lint`
where the Makefile has the target, `make -f agk.mk agk-governance` (no network; `not run` without `make`), the secret scan over
the branch's commits (a missing `gitleaks` fails the run, naming the tool and the pinned version, also with `--quick`;
ADR-0306), and the tests that `test_plan.py` selects
(`--quick` skips them). It prints `prepush: <step> ok|FAIL|skipped (<s>s)` per step and exits 0 when no step failed, 1 when one
did, 2 on a usage error (session rule 31, ADR-0186). `--no-lock` leaves the heavy-step lock (`lock.py`, name `heavy`) of the
tests step out, for CI. The optional hook `kit/templates/pre-push` calls it; see [getting-started.md](getting-started.md).
`python3 scripts/agk/reviewers.py --codeowners` prints the rendered CODEOWNERS; with `--write` it writes the file (in an
adopted repository only the marked block). `python3 scripts/agk/traceability.py` prints the requirement-to-test matrix to stdout; it is never committed.

## Installing

1. Create the target repository empty (no files).
2. Make one first commit directly on the default branch (a PR needs a base branch); record it in the target's
   ADR-0001.
3. From a checkout of agk, run init as a maintainer-approved step (an agent session blocks running a cloned script
   until a maintainer authorizes it):

       python3 scripts/agk/init.py TARGET [--dry-run] [--unreleased] [--login-from-env] [--solo] [--project-tests CMD] [--layout plugin [--rehearsal]]

   Init never overwrites a differing file (it refuses and lists it) and a second run changes nothing.
   Init installs only the files of a release: run it from a release tag (`git checkout v<version>`). Between two
   releases it refuses, naming the release; `--unreleased` installs the checkout as it is, for the kit's own tests.
4. Apply the printed ruleset and repository settings by hand on GitHub; init configures nothing there.

The setup flags of init and adopt (SPEC-0062 rule 11, ADR-0679), which the steward passes: `--login-from-env` writes the
login in `AGK_SETUP_LOGIN` (read by `gh api user`, never printed) on both `@REPLACE-ME` lines of `config/reviewers.yaml`;
`--solo` writes `review_mode = "solo"` and its line in ADR-0001, refused without one person in the reviewers file;
`--project-tests CMD` writes `project_tests`. Init and adopt themselves still run no command and reach no network.

`--layout plugin` on init or adopt (SPEC-0071 rule 2 as amendment 211 proposes, brief #1603, ADR-0683) starts the
project in the clean layout: it writes only the files the migration of `upgrade.py --clean-repo` keeps (the project's
records and settings, the short `CLAUDE.md`, `LICENSE-AGK`, `.gitignore` and the `.github/` templates) and `agk.toml`
with `execution = "local"` and the `[kit]` table, and no kit script, hook, agent, workflow or guide. It refuses, naming
the setting, in personal mode and with another `execution`, and, naming the proof, until the rehearsal's figures are
accepted (SPEC-0071 rule 11) unless `--rehearsal` on the sample project.

See `docs/specs/0001-agk-init.md` and `docs/runs/k1-live-proof.md`.

## Adopting an existing repository

    python3 scripts/agk/adopt.py TARGET [--dry-run] [--login-from-env] [--solo] [--project-tests CMD] [--layout plugin [--rehearsal]]

Run from a checkout of agk as a maintainer-approved step. TARGET is an existing git work tree. Adopt touches no
product file: it creates its own files (`agk.mk`, `agk.toml`, `scripts/agk/`, `.claude/`, `config/`,
`constitution/`, `docs/`, `.github/workflows/governance.yml`), appends one marked block to `.gitignore` and `.gitattributes`
(`scripts/agk/** linguist-generated=true`, so GitHub collapses the kit's scripts in diffs) and, when they
exist, to `CLAUDE.md`, `.github/CODEOWNERS` and `.github/PULL_REQUEST_TEMPLATE.md`, and refuses rather than overwrite.
The project's `Makefile`, `pyproject.toml` and tests are untouched. See `docs/specs/0002-agk-adopt.md`.

`python3 scripts/agk/survey.py [--clone DIR] [--sidecar DIR] [--today YYYY-MM-DD]` lists a codebase for personal mode and never runs it (ADR-0386).

`scripts/agk/forge.py` is the one record interface of personal mode and has no command: a script imports it and calls `get(name, endpoint)`, `create_issue`, `comment` or `record_pull`. `GithubForge` reads GitHub's records and refuses every write; `FilesForge` keeps GitHub-shaped records under `forge/` of the sidecar, with `git` only and no connection (SPEC-0041 rule 6, ADR-0397).

`python3 scripts/agk/personal.py baseline [--clone DIR] [--sidecar DIR] [--approve]` prints the test command of personal mode and, only with `--approve`, runs it once on the head tree in the sidecar and records the tests already failing in `records/baseline.json` (SPEC-0041 rule 16, ADR-0400).

`python3 scripts/agk/personal.py export --target CLONE [--write] [--branch NAME] [--with-notes]` prints what it would write to a target clone and, only with `--write`, writes on two new branches of the target (never its default branch, never pushed): the adopt plan when AGK is not installed there, the requirements, specs, ADRs, briefs and decisions-log rows renumbered past the target's ids with statuses reset to `planned`, `Draft` and `Proposed`, the test map as markers in the tests on `<branch>-tests`, and `export-map.json`; it prints, never runs, a `gh issue create` command per open brief. `personal.py export --check` fails unless every record of the sidecar is in `records/export-map.json`, mapped or withheld with a reason, naming the count and the first unmapped id (SPEC-0041 rules 24 and 25, ADR-0638).

`python3 scripts/agk/personal.py upgrade [--clone DIR] [--sidecar DIR]` raises the sidecar's `[personal] schema` one step and one sidecar commit at a time to the plugin's, and refuses a newer schema; `personal.py hook install|remove [--clone DIR]` writes or removes the opt-in `pre-push` hook that runs `gate --approve`, the one write under the clone's `.git/`; `personal_state.py detach` removes that hook only when it is unedited, and `doctor.py` on a sidecar checks its pinned copies against `kit/hashes.json` for the recorded `plugin_version` (SPEC-0041 rules 19, 26 and 27, ADR-0637). Personal mode runs from the plugin installed at user scope: `claude plugin install agk --scope user` (verify: the install command and scope flag).

`python3 scripts/agk/personal_adopt.py check|render FILE [--clone DIR] [--sidecar DIR] [--today YYYY-MM-DD]` checks the model's proposals of `/agk:personal-adopt`, refusing each claim whose citation does not exist, and `render` writes the claims left into the sidecar as Draft and Proposed records for the person to confirm (SPEC-0041 rules 13 and 14, ADR-0633).

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

## Measures for a date range

    python3 scripts/agk/measures.py --from YYYY-MM-DD --to YYYY-MM-DD [--json] [--trial] [--repo OWNER/REPO] [--api-dir DIR | --sidecar DIR]

Reads the GitHub REST API (`gh api`, GET only), saved responses (`--api-dir`) or, in personal mode, the sidecar's
`forge/` files (`--sidecar`), and local git objects; it writes no file and posts nothing. The range is UTC days, both
included, at most 92. It prints one row per feature, a brief whose finishing pull request (`Finishes: #n`, else the last
merged one once the brief is closed) merged in the range: its pull requests, the hours from brief to merge (queue, build
and the builder's own turns), rework (fix rounds, rejections, corrections, reopens, follow-ups, first-review pass), backstop
escapes, tokens, Actions minutes and the owner's part (hand and guarded merges, owner lines, owner questions and their
wait). Then the range totals and one row for the merged pull requests tied to no brief. The output holds numbers only,
never a title, a login, a branch or a host; a figure whose input is missing is `unknown`, never 0, and local or personal
mode prints `none (local mode)` or `none (personal mode)` for what it does not keep. `--json` gives the same rows. See
ADR-0659 and amendment 191 (SPEC-0007).

`--trial` adds one `trial` row, a solo trial of the range: speed (pull requests merged, brief to merge median and 90th
percentile, the owner's items and wait including the conductor's `Owner needed:`, park minutes, cleared to merge),
quality (fix rounds per merged pull request, red spells of the default branch and their hours, reverts, a solo person's
confirmations) and cost (tokens per merged pull request, and by the configured tier of the brief's kind). No cost is
estimated. See ADR-0687 and amendment 213 (SPEC-0007).

## The operations checklist

    python3 scripts/agk/metrics.py --save-checklist [--to FILE] [--days N]
    python3 scripts/agk/checklist.py [--root DIR] [--days N] [--saved FILE]

The first command saves one file with GET requests only: the document of `facts.py`, the window's comments with their authors and
Actions runs, the briefs, the listed verdict authors, the open `agk-conductor` issues, the newest weekly `pr tests:`, `pr tests
median:` and `full suite:` lines and, when no weekly line counts a run and the project is not in local mode, the same figures for
the pull requests closed in the window (ADR-0420). By default it is `agk-checklist.json` in the checkout's git directory, which git
never tracks. The second reads that file, writes nothing and makes no network call, and prints nine lines `<n>. <name>:
<yes|partly|no|unknown> <measure>`: machine capacity, conductor runs builders, test optimization, parallel runs, auto-merge,
model selection, conflict planning, smart assignment and cost per pull request. A point it cannot measure prints `unknown` with
the reason, never 0; personal mode prints that for the records it does not keep, and local mode for those that need Actions runs.
The owner's word `AGK-NINE-CHECKLIST` in chat means: run these and give the lines.

A point is `yes` only past its threshold in the optional `[checklist]` table of `agk.toml`: `capacity_use`, `conductor_share`,
`selected_share` and `usage_share` (shares from 0 to 1), `parallel_peak`, `merge_late`, `merge_failed_runs`, `false_hold_rate`
and `idle_minutes`. The defaults are in `scripts/agk/checklist.py` and marked (verify) until measured for four weeks. An
unknown key or a wrong value is refused, naming the setting. See ADR-0374.

## The token figure of a session

    python3 scripts/agk/usage.py [--transcript FILE] [--since YYYY-MM-DDTHH:MM:SSZ]
    python3 scripts/agk/metrics.py --usage-by-kind FACTS [--before YYYY-MM-DD] [--after YYYY-MM-DD]

The first prints `Usage: <n> tokens` from the running session's own transcript, each message counted once over its input,
cache and output counts, or `Usage: not shown`; it writes no file, posts nothing and makes no network call, and prints no
text of the transcript. A builder passes `--since` with the time of its previous `Report:` and ends its `Report:` and
`Progress:` lines with the line it prints. The second prints, per kind, the merged pull requests with their tokens, one
line per pull request and, with an optional `[models.prices]` table in `agk.toml` (a tier to a price per million tokens),
one cost line. See SPEC-0045 rules 8 and 9 and ADR-0419.

## The day's model spend

    python3 scripts/agk/metrics.py --cost [--day YYYY-MM-DD] [--days N] [--records DIR] [--save]

Reads the local session records of this clone's sessions (by default `<CLAUDE_CONFIG_DIR or ~/.claude>/projects`, or
`--records DIR`; a reply whose working folder is not the clone or one of its worktrees is skipped and counted) and of
each reply only its usage fields: model, input, output, cache write and cache read tokens, time, branch and session.
It never reads or prints a message's text, and makes no network call. It prints one table per day (`--day`, today in
UTC by default; `--days N` ends there), one row per session, role, brief and model, the day's total, the top five
sessions and briefs, and the share of cache reads against fresh input. With an optional `[cost.prices.<model>]` table
in `agk.toml` (`input`, `output`, `cache_write`, `cache_read`: USD per million tokens; no price ships with the kit) it
adds an estimate in USD; without one it prints tokens only. A figure it cannot read is `unknown`, never 0, and a record file it cannot read is counted and marks the total as a lower
bound. `--save`
writes the day's figures to `docs/runs/cost/<date>.json`. See ADR-0544.

## Release pack

    python3 scripts/agk/release_pack.py check <out>/<tag>

Checks one release's evidence pack: a folder named by its tag with exactly `tests.json`, `scans.json`, `coverage.json`,
`bom.json`, `decisions.json` and the index `pack.json`. It reads the folder and git only, with no network, and prints
`ok pack`, or one `FAIL pack: <part> <reason>` line per problem and exits 1, naming the part and never a value. A failed or unknown
check or scan is a `warn pack:` line and passes. A tag that is not a release, or a repository with no release test, is one
`refused:` line. No governance step runs it. See `docs/specs/0052-every-release-carries-one-evidence-pack-named-by-its-tag.md`.

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
Four warnings say when the start settings do not fit how the project runs (brief #1617, ADR-0686), information only:
`tier-use` (each tier's count of the open briefs, and a tier a brief kind uses that gets none), the `launch-adapter` lines
for a cloud session with `auto_start` on (`not run here`) and a `.ps1` adapter off Windows, `review-ceiling`
(`reviews_in_flight` under `max_builders`) and `slot-use` (with `builder_start = "assign"`, slots whose newest marker is
over 24 hours old and the runs of the last 24 hours that decided `none`).

## Stalls

    python3 scripts/agk/stalls.py [--json]

Lists every place where the project's pull requests or sessions have stopped, each with its cause and its fix in one line:
`stall <kind> #<n>: <cause>; fix: <one plain step>`, or `no stall`. The kinds are `stale-label` (green checks, `agk:ci-running`
still on after 10 minutes), `no-verdict` (`agk:review` for 30 minutes with no verdict naming the head), `stuck-run` (a required
run queued or in progress for 60 minutes, or cancelled with no newer run), `red-default` (the issue "The default branch is
red" is open), `idle-capacity` (the plan names sessions to start and no brief was taken for 15 minutes) and `claim-no-pr` (a
live take with no pull request and no post by its session for 2 hours). `--json` gives the same. It reads with `gh api` (GET
only) and writes nothing; exit 0 with no stall, 3 with any, 1 when the repository cannot be read (ADR-0205).

## Steward memory

    python3 scripts/agk/steward.py start --session ID
    python3 scripts/agk/steward.py refresh --session ID [--since UTC-TIME]
    python3 scripts/agk/steward.py record --kind KIND (--text TEXT | --file FILE)
    python3 scripts/agk/steward.py end --session ID [--calls N] [--tokens N]
    python3 scripts/agk/steward.py setup [--adopted] [--detect FILE] [--answer TEXT]
    python3 scripts/agk/steward.py first-run [--folder DIR]

Outside a git repository each command of `steward.py`, `steward_daily.py`, `steward_evidence.py`, `steward_onboard.py`
and `steward_owner.py` prints `outside: no project here`, exit 3, and writes nothing (SPEC-0066 rule 8, ADR-0663).
`first-run` prints `first-run: <step>` for the folder (default the working one): `kit`, `project`, `adopt`, `greet` or
`greeted`; only `greet` writes, one line of a hash of the folder's path and the date in `agk-greeted.txt` of the person's
Claude folder (`CLAUDE_CONFIG_DIR`, else `~/.claude`), never in the folder itself.

## Day zero

    python3 scripts/agk/day_zero.py offer [--folder DIR]
    python3 scripts/agk/day_zero.py keep --yes --id TOPIC --answer-file FILE [--who NAME] [--folder DIR]
    python3 scripts/agk/day_zero.py commands --name NAME [--shell posix|powershell] [--step N] [--public]
    python3 scripts/agk/day_zero.py write --root DIR [--folder DIR] [--answers FILE]

Before a repository exists (brief #1584, ADR-0664). `offer` prints `offer: github` for a folder that is not a git
repository with `origin` and not a personal-mode project, else `offer: none`. `keep` writes one answer, quoted as given
with its UTC time, to `agk-day-zero/<hash>.json` of the person's Claude folder, the hash being the greeting mark's, and
only with `--yes` (else exit 2, nothing written). `commands` prints step N of seven commands for the person to run (the
README in PowerShell with `Set-Content -Encoding utf8`), private unless `--public`, the next only after an exit of 0,
and `done:` after the seventh; a name outside letters, digits, `.`, `_` and `-` is refused (exit 2). `write` writes `docs/sources/day-zero.md`
(`Kind: other`, SPEC-0043 rule 1) and with `--answers` the `vision` skill's answers file, removes the kept file, and
never overwrites a source (exit 1).

The steward's notes (SPEC-0059 rule 8, ADR-0557): one open issue labelled `agk-steward`, created when none is open, one
comment per note under a fixed first word (`Decision`, `Ranking`, `Term`, `Persona`, `Person`, `Pattern`, `Gap`, `Risk`, `Lesson`,
`Owner question`, `Triage`, `Override`, `Onboarded`, `Setup`). `start` reads the notes first, with `since=` from the last one seen,
prints the newest of each kind, posts `Started: steward <session> <UTC time>` and exits 1, writing nothing, while another
steward's marker is live (60 minutes, no `Ended:`); at 500 comments it opens a new issue that carries the open owner
questions and closes the old one. `record` refuses an unknown kind or a text the data guard matches (exit 2). `setup`
(SPEC-0062 rules 9 and 11, ADR-0679) prints one `Setup: <matter>: <choice> because <reason>` line per AGK matter, the
plain questions left and, with `--answer`, the `run:` install command; after the install `--answer` is refused (exit 2). A failed
GitHub call exits 4. In personal mode the notes are `docs/runs/steward/memory.md` of the sidecar and nothing is posted.
In solo mode (SPEC-0062 rule 4) a start with no `Person:` note prints `ask:` with the one question to the person, and a
`Person` note is `<business|technical>: <their words>`, ending `Who: ProductOwner` (else exit 2).
`end` writes the pass's counted calls and tokens on its `Ended:` marker, `not shown` for a figure not given, never 0.

## Steward evidence

    python3 scripts/agk/steward_evidence.py stage [--date YYYY-MM-DD]
    python3 scripts/agk/steward_evidence.py settle --question FILE [--stage STAGE]
    python3 scripts/agk/steward_evidence.py answer --question FILE --number N [--recheck FILE]
    python3 scripts/agk/steward_evidence.py triage --finding FILE
    python3 scripts/agk/steward_evidence.py skill --step STEP

The steward's evidence rule, answer form and triage (SPEC-0059 rules 2, 3, 4, 6, 7, 12 and 19, ADR-0558). `stage` names
the stage in the owner's words from the files (`docs/discovery/`, `docs/plan/scope.md`, a `*-stack-options.md` ADR,
`docs/plan/milestones.md` or `scope-lock.md`) and one GET of the open `agk-conductor` issue, which makes it `build`. A
question file is JSON: `id`, `class` (`technical`, `requirement`, `business`, `scope`, `date`, `cost` or `signoff`),
optional `changes`, `reverses` and `ranking`, and `findings`, each `source` (1 owner decision, 2 Approved spec or
requirement, 3 signed-off prototype, 4 source document, 5 AGK rule or code), `answer`, `place` and `rule`. `settle` prints
the comment `Answer: Q-<id> <answer> (evidence: <source and place>; rule: <rule>)` (exit 0) or `owner: <reason>` with the
recommendation and a `Gap:` to record (exit 3); `answer` posts that one comment, with a `Class:` second line, and nothing
on an owner question. A requirement answer is posted only when `--recheck` (JSON `answer`, the fresh reviewer's) agrees;
otherwise both answers go to the owner, as does a class the owner overrode twice in seven days. A finding file is JSON: `id`,
`triage` (`kit brief`, `kit correction`, `kit question`, `project brief` or `owner question`), `why`, `text`, optional
`cause` and `reproduced`; `triage` prints `file`, `draft` (a kit filing from a project, until build (e)) or `ask` and the
`Triage:` note, or refuses (exit 2) a text without its `Modes:` line, failing the brief shape or the neutrality list, an
unreproduced cause, or a filing above `[steward] auto_file` without an `Owner said` line. `skill` prints the step's skill
from the agent file's table, or `no skill:` (exit 3). A failed GitHub call exits 4.

## Steward daily list

    python3 scripts/agk/steward_daily.py daily
    python3 scripts/agk/steward_daily.py bundle --question FILE

The steward's measured quality (SPEC-0059 rules 3 and 13, ADR-0560). `daily`, run after `steward.py start`, posts at the
first start of a UTC day one `Daily: <date>` comment on the memory issue for each day since the last list (the days
missed are listed; no scheduler): each steward `Answer:` with its comment id and evidence, each pass's calls and tokens,
each brief filed without an `Owner said` line with its priority, the owner questions asked and answered, the override
share (owner overrides over steward answers) and any warning (two overrides of one class in seven days, until a
`Decision:` names `class <class>`). It first posts one `Override: Q-<id> class <class>: ...` note per new override. It
reads the repository's comments and issues once each with `since=`; a figure it cannot read is `unknown`, never 0. In
personal mode it prints the list. `bundle` prints what the fresh reviewer is given: the question and its cited evidence,
never the steward's answer (ADR-0430's form). A failed GitHub call exits 4.

## Steward onboarding

    python3 scripts/agk/steward.py onboard [--again]
    python3 scripts/agk/steward_onboard.py onboard [--again]

The steward's first start (SPEC-0059 rule 20, ADR-0562). With no `Onboarded:` note in the memory it names the entry
point: `day 0` (no Approved spec, no `agk-brief` issue; stage `start`, nothing harvested), `execution` (an open
`agk-conductor` issue, or `docs/plan/scope-lock.md` and a closed brief) or `planning` (the stage of `steward_evidence.py
stage`). Planning and execution harvest, by list pages only: the first lines of the repository's comments
(`Maintainer answer:`, `Answer:`, `Question:`, `Owner needed:`; an answer or `Owner needed:` only from a listed verdict
author or spec approver of `config/reviewers.yaml`), the open `agk:parked` issues, Accepted ADRs,
`docs/runs/decisions/`, Approved specs, `docs/requirements.md` statuses, `docs/design/signoffs.md` and the last line of
`check_plan.py --trace`. The notes are marked `harvested`, each line with its source: `Decision:` (at most 50 lines a
note), one `Owner question:` per open question and per question whose answers disagree, `Risk:` for parked work and
`Gap:` for a source that cannot be read. A line the data guard matches is withheld, naming the class. It ends with
`Onboarded: <stage> <date>, <n> decisions, <n> gaps, <n> open questions` and prints the summary. Onboarded already, it
writes nothing; `--again` writes only lines no note holds. Personal mode reads the files only and writes the sidecar
file. Exit 4: the memory or the stage cannot be read.

## Outbound data guard

    python3 scripts/agk/steward_outbound.py check (--text TEXT | --file FILE) [--root DIR]

Checks a text bound for the kit repository from a project (SPEC-0059 rule 6, ADR-0561), fail closed: the tokens of
`config/neutrality.txt` (and `kit/templates/neutrality.txt` where present), the data guard's detectors with the
`[guard] patterns`, URLs and names of the hosts of the project's git remotes, and repository names other than the
kit's. A match prints one line per class naming the setting, never the value, and exits 2; so does a list or the
remotes that cannot be read. A clean text prints `ok outbound` (exit 0). The steward's guard denies a post to the kit
repository that this check refuses.

## Steward and the owner

    python3 scripts/agk/steward_owner.py ask --qid Q --on N --file FILE
    python3 scripts/agk/steward_owner.py ask --target pr:N --qid Q --file FILE --line FILE
    python3 scripts/agk/steward_owner.py approve --ask Q --said FILE --at TIME [--by LOGIN]
    python3 scripts/agk/steward_owner.py relay --qid Q --on N --answer TEXT --said FILE --at TIME [--conductor ID]
    python3 scripts/agk/steward_owner.py park --pr N [--conductor ID]
    python3 scripts/agk/steward_owner.py ready --plan FILE --trace FILE --session ID [--start]
    python3 scripts/agk/steward_owner.py defect --title TEXT --file FILE [--refusals N] [--post]
    python3 scripts/agk/steward_owner.py defects
    python3 scripts/agk/steward_owner.py reads [--session ID] [--refused]
    python3 scripts/agk/steward_owner.py standard [--playbook SLUG]
    python3 scripts/agk/steward_owner.py confirm --said FILE --at TIME [--by LOGIN]
    python3 scripts/agk/steward_owner.py research --said FILE --at TIME --describe TEXT
    python3 scripts/agk/steward_owner.py draft --slug SLUG
    python3 scripts/agk/launch.py role --role steward|conductor --session ID [--adapter COMMAND]

The owner's question and its relay (SPEC-0059 rules 2, 5, 10 and 14, ADR-0559). `ask` takes one plain business sentence
with its choices and `I recommend` and no kit term, records it as an `Owner question:` note, prints it for the chat and
posts `Question: <Q> for the maintainers: <sentence>`. `relay` posts the owner's reply as `Maintainer answer:`, `Owner
said (<UTC time>): "<words>"` and `Who: ProductOwner`, refuses it without a well-formed quote, then removes the owner
wait's `agk:parked` and tells the conductor `parked #<n> answered <Q>`. `park` is the steward's pass of the owner wait on
one pull request. `ready` starts the conductor through `launch.py role` only when the plan check's trace ends `ok plan`,
no brief is malformed, the scope is locked and no open owner question blocks the first milestone; else `not ready:`
lines, exit 1. In personal mode everything is printed and nothing is parked. `defect` drafts a kit-defect report (kit version, machine, reason codes, redacted refusal lines, what should happen), checks it with the outbound guard and, with `--post`, files it labelled `agk-kit-defect`, which the plan never offers; `defects` lists the open ones one line each; `reads` checks `gh api rate_limit` and, once per session, names the setting that refuses it and the step that restores it (brief #1411, ADR-0594). `launch.py role` prints a role's prompt or
calls the adapter once; a refused start prints `stuck: <role> <session> not started (<why>)`, exit 1.

The one-yes approval (SPEC-0062 rules 13, 14 and 16, brief #1690, ADR-0703). `ask --target pr:<n> --line FILE`
reads the pull request's full head with one GET, refuses a closed one and a line this command never writes (`Merge:`,
`Verdict:`, `Final:`, `Correction:`, another head, another Q id; `Confirmed:` in team mode), records the ask with its
head, link and session (`AGK_SESSION`, else the memory's newest open `Started: steward <id>`), keeps it as the session's one open ask (a newer ask closes the older) and posts today's `Question:`
line. `approve --ask <Q> --said FILE --at TIME` takes the person's one-line reply to that latest open ask: it refuses an ask of
another or an ended session, a moved head, a closed target, an older ask, a reply time before the ask or after now, an ask older than four times `[flow] owner_wait_minutes` (24 hours when unset
or 0), a supervisor-started steward, a data-guard match, a question mark or a condition word, and in team mode a `--by`
outside `spec_approvers`; `Not yet` is recorded and posts nothing. On a yes it records a `Decision:` first (a memory
that cannot be written posts nothing), then posts a `Maintainer answer:` form with `Owner said`, `Asked` and
`Who: ProductOwner` lines by `-F body=@<file>`; it reads the form again from the stored line and prints an
`Approve:` or `Confirmed:` body ready to paste, never posting it; in personal mode (a `REQ-nnn`, `SPEC-nnnn` or `ADR-nnnn`
target) it prints the `personal.py confirm` command and posts nothing.

The standard (SPEC-0072 rule 8, brief #1601, ADR-0681; `docs/guides/engineering-standard.md`). `standard` prints the
composed standard of the declared work type, or of `--playbook`: one plain screen in solo mode, the full list in team
mode, or the work-type question when there is none. `confirm` records one `Setup: standard: confirmed` entry only on an
explicit yes (in team mode `--by` a spec approver), else `not confirmed: nothing applied`, exit 1; `ready` is not ready
without it while a work type is declared. `research` records the web-research permission and, only on a yes, prints
`search: <TEXT>` for a generic description. `draft` writes the project playbook on `default.toml` and its Proposed ADR,
never `[delivery] work_type`.

## Autopilot status

    python3 scripts/agk/autopilot.py status [--week] [--root DIR]

`agk status` (SPEC-0064 rules 3, 5 and 10, ADR-0584): the running jobs of this machine from their records (kind, item,
head, since, last event), each `claude` process with no record as `unrecorded: process <pid> (not adopted)`, the
queue, the owner's waits, the held jobs and one `quiet:` reason, from the reads of one pass; it posts nothing. A
`refusals today:` line counts the hooks' refusals of the UTC day by reason (brief #1410, ADR-0593). `--week` prints the week of `agk-autopilot.jsonl` in the temp folder and the tokens per merged pull request, `unknown`
where a figure cannot be read.

    python3 scripts/agk/autopilot.py on|off|budget on|budget off [--today]|retry N [--root DIR]

`agk autopilot` (SPEC-0064 rules 7, 8 and 11, ADR-0587): `on` installs the one scheduler entry (a tagged crontab line
or the Windows task `agk-autopilot`, every `[autopilot] interval_minutes`) and runs the machine checks, each `ok:` or
`warn:` naming its setting, changing no power setting; `off` removes the entry. Both print, never write, the protected
`agk.toml` change of `[autopilot] mode`. `budget off [--today]` relaxes `daily_budget`, `budget on` ends that, and
`retry N` lifts a hold, each kept in `<git dir>/agk/autopilot.json`; `status` starts with the mode and the budget line.

    python3 scripts/agk/autopilot.py jobs [--claim] | next [--brief N] [--root DIR]

`agk next` (SPEC-0064 rule 13, ADR-0589): `next` runs one job in the foreground (the next review, fix or build job by
the supervisor's rules, or the build of brief N), waits for its end and posts nothing; in personal mode it reads the
files forge. `jobs` prints the pass's `job:`, `held:` and `not started:` lines from GitHub, and `--claim` posts one
`Started:` claim per build or fix job first: CI mode's launcher task reads them and starts one cloud session per job.

## Steward voice

    python3 scripts/agk/steward_voice.py check FILE
    python3 scripts/agk/steward_voice.py choose FILE
    python3 scripts/agk/steward_voice.py form FILE
    python3 scripts/agk/steward_voice.py confirm FILE --answers FILE
    python3 scripts/agk/steward_voice.py shortened --rules N[,N]
    python3 scripts/agk/steward_voice.py explained FILE
    python3 scripts/agk/steward_voice.py playback FILE --reply TEXT
    python3 scripts/agk/steward_voice.py offtopic --product TEXT

The steward's voice (ADR-0582, brief #1382). `check` reads a reply to a person and prints one `voice: rule <n>:` line per
broken rule, naming the rule and never the text (exit 1), or `voice: ok`: the first line is an ask or an answer; at most
5 bullets, 12 lines and 100 characters a line; more than three choices only with a "more"; a decision names its
recommendation; a status is three lines (`Done:`, `In progress:`, `Waiting on you:`); no kit term of SPEC-0059 rule 5's
list. `choose` renders a decision JSON (`decision`, `options` of `label` with optional `score`, `group` or `ruled_out`,
`recommend`, `because`, optional `ask`) as `Decision: · Options: A / B / C · I recommend · Reply`, dropping what the
evidence rules out, grouping kinds, keeping the best three by score with `say more for N other options`, or asking the
one sharper question. `form` renders 1 to 5 inputs (`name`, `default`, optional `choices`) as one form with each default;
`confirm` plays the answers back in at most three lines. `shortened` records one `Shortened:` marker, counted in the
daily list. In `check`, a term of the guide's `Kit terms` list passes only with its one sentence in the sentence that
first names it, and only once: `explained` records each term a reply explains for the first time as one `Term: kit:`
entry, and a later reply that explains it again fails (SPEC-0062 rule 5). `playback` exits 0 (`go on`) only when the
play-back is three sentences or fewer and `--reply` is a plain yes, else 1 (`play back again`); `offtopic` prints the one
line back to the product. Exit 2: a refused input; exit 4: the memory cannot be written.

## Conductor routines

    python3 scripts/agk/conductor.py watch [--since 2026-11-06T10:00:00Z] [--once]
    python3 scripts/agk/conductor.py sweep
    python3 scripts/agk/conductor.py merge-queue [--dry-run] [--max-batch N]
    python3 scripts/agk/conductor.py rerun --pr N [--apply]
    python3 scripts/agk/conductor.py check-verdict FILE [--pr N] [--root DIR] [--open-briefs FILE]
    python3 scripts/agk/conductor.py lease (--show | --take NAME | --release NAME)
    python3 scripts/agk/conductor.py watchdog [--session NAME] [--install] [--pass] [--conductor-only]
    python3 scripts/agk/conductor.py review --pr N [--start]
    python3 scripts/agk/session.py prompt --brief N [--session ID] [--follow-up TEXT]
    python3 scripts/agk/session.py slot (--take | --renew | --release | --next) SLOT
    python3 scripts/agk/session.py summary --pr N --file FILE

Waits that cost no model turns (brief #1310, ADR-0554). `session.py watch --pr N` and `watch --assign ID` take
`--until-event`: they return only on an event, printing every event line of one read, or after `[flow] wake_minutes` (110
by default) with `renew: no event`, renewing a slot's lease every 240 s themselves. `session.py summary --pr N --file FILE`
posts the pull request's one working summary (`Summary: <head>` and the file, at most `[flow] summary_lines` lines, 25 by
default) and edits it in place on the next run; `resume --pr N` prints it with the `git diff` since its head. `conductor.py
watchdog --pass` runs the review queue's fingerprint, the plan and the sweep as scripts and starts one conductor job only when
they changed since the last job, the plan starts a brief, or no job ran for 24 hours; `--install --pass` prints the line that
runs it every 10 minutes.

The conductor's watch and sweep (brief #643, ADR-0308). `watch` ends on the first poll that finds a comment created after
`--since` (default: the start) whose first line starts `Question:` or `Report:`, or is an owner's answer or approval (an
`Answer: Q-…` or `Maintainer answer: Q-…`, or an `Approve:` by a listed spec approver; brief #1112, ADR-0475), on an open
issue labelled `agk-brief` or an open pull request, and prints `<number> <first line>` for each; on a poll with none it also prints, at most once per 5 minutes, `HELD VERDICT #<n>` for each open, ready pull request that `sweep` would print it for, the same one again only after a further 15 minutes (its marks in the git directory; brief #1125, ADR-0482); `--once` reads once and prints `nothing new` when there is none.
`sweep` prints `#<n> <head7> <state> <age>` per open pull request (`draft`, `ready: no verdict`, `fix list on <head7>`,
`cleared on <head7>`, `cleared, head moved`, `waiting: Approve SPEC-nnnn at <head7>`, `blocked: Question Q-n unanswered <age>`,
`checks pending`, `red`), then the latest run of the default branch and any open red-branch issue; a `Question:` or `Report:`
that no listed verdict author answered within `conductor_late_minutes` (30 by default) is marked `LATE`. Then a taken brief with no
branch `claude/brief-<n>`, no pull request and no `Progress:`, `Report:` or `Question:` after its take, older than
`silent_minutes` (30 by default), is listed as `SILENT <brief> <session> <minutes>` with the line to re-fire it; a brief with a
`Report: ... escalate` never is (brief #669, ADR-0322). The poll interval is
`conductor_poll_seconds` (60 by default), all of the `[flow]` table of agk.toml. Both read with `gh api` (GET only) and write
nothing; the conductor guard allows exactly these forms.

`merge-queue` (brief #643 build (b), ADR-0329) is the batched merge: with `auto_merge` on, it judges every open pull request by
`merge_cleared.py`'s own holds (a cleared head, green required checks, every hold of SPEC-0039 rule 5, the clearing verdict by a
listed verdict author), prints `not queued: #<n> <sha12>: <reason>` for a cleared one that is held, and merges the rest in the
order of their verdicts, at most `--max-batch N` of them (5 by default), each through
`python3 scripts/agk/merge_cleared.py --pr <n> --sha <head>` with its line printed in full and no wait for the default branch's
run in between. It stops at the first run that is not a merge (`merge-queue: stopped at #<n> (exit <code>); merged: ...`), then
waits once for the default branch's run on the last merge (`full_run.covered`, polled every `conductor_poll_seconds` for at most
`merge_queue_wait_minutes`, 60 by default) and prints `<branch> green at <sha12> after the batch #a #b`, or
`stopped: <branch> red at <sha12> after the batch #a #b` (exit 1); in local mode there is no run to wait for. `--dry-run` prints
the order and merges nothing. It posts nothing; the guard allows the dry run always and a run that merges only with `auto_merge`
on in the checkout and on the default branch, and builders are asked first (`.claude/settings.json`).

`watchdog` (brief #1237, ADR-0525) is one pass, for local mode: when no live conductor holds the lease on the plan issue, `auto_start` and `launch_adapter` are set in the checkout and on the default branch, the project is not paused and the machine's free memory holds one builder (`builder_memory_gb`), it starts one conductor through the adapter (`conductor-local`, or `--session NAME`), which takes the lease itself; otherwise it prints why and starts nothing. It posts nothing. `--install` prints the one scheduler line that runs it every 30 minutes (`schtasks` on Windows, a crontab line elsewhere) and runs nothing; the person runs that line. It is not a command of the conductor's session, and its guard does not allow it. [Local mode, "Running unattended"](local-mode.md#running-unattended) says how to set it up.

`review --pr N [--start]` (brief #1248, ADR-0528) puts a fresh reviewer at the gate when `[flow] reviewer_slots` is 1 or more
(0, the default, prints `review: off` and changes nothing). It reads the pull request, its comments and the `Review:` lines on the
conductor issue and prints one line: the head has its verdict; a slot has it, and the conductor gives no verdict until
`review_minutes` pass (`[flow]`, else `[capacity]`, else 15); the fallback is due; no slot is free; or `review: ask Review: r<k>
#<n> <head>` for the conductor to post. In local mode `--start` posts that line and starts one reviewer session through
`launch_adapter`, as `launch.py` starts a builder (`auto_start` and the adapter set in the checkout and on the default branch,
not paused, `[flow] min_free_memory_mb` held). With slots counted, `check-verdict --pr N` refuses a verdict without the slot's
marker lines (`agent: architect-review`, `tier: strongest`, `session: r<k>`) unless it ends `(conductor fallback)`, and refuses a
fallback before `review_minutes`, after the reviewer's verdict, or with no `Review:` line for the head. The conductor guard
allows both forms, `--start` only with the adapter configured.

The last private routines (brief #700, ADR-0330). `rerun --pr N` reads the pull request and the `pull_request` runs of its head and
prints one line per cancelled run; `--apply` reruns them (catch log row 18). When every run of the head skipped (a push to a ready
pull request, row 19) it prints the one step that starts them, converting the pull request to a draft and back through the
runtime's `ccr/convert_to_draft` and `ccr/ready_for_review` routes `(verify)`, and takes it only with `--apply`; a draft is left
alone. `check-verdict FILE` prints `ok`, or the problem of the verdict's `Final:` lines by the router's own reading
(`common.verdict_problem`), or that its first line is not a verdict or a `Correction:` with text; exit 1 on a problem, nothing
read on GitHub. With `--pr N` it also refuses a verdict on another head, a `Final:` path the head does not have and a fix list
with no item on a pull request with no Proposed ADR, and a read that fails is an error (brief #854, ADR-0388). A fix item or `MALFORMED:` line written
`rename <old> to <new>` whose new name the tree, another open brief or an open pull request holds is refused, naming the item,
the holder and a free name; the open briefs come from `--open-briefs FILE` or the read cache, `--root DIR` names the
checkout (brief #1441, ADR-0602). `lease` is the active-conductor marker: one comment `Conductor: active <time> <name>` on the plan issue that
`plan_issue` of the `[flow]` table names (absent: the lease is off), valid 10 minutes, renewed at every `watch` pass (`watch` returns within 5 minutes with `tick` and any `STALL` lines; ADR-0368, ADR-0402); `--take NAME` posts or edits it in place
unless another name holds a valid lease (exit 3, naming the setting) and keeps the name in the git directory, `--release NAME`
marks it released, `--show` prints `held by <name> until <time>` or `free`; `merge-queue` refuses to run while another name holds a
valid lease. `session.py slot` runs a builder slot when `[flow] builder_start = "assign"` (brief #776, ADR-0362): `--take`, `--renew` and
`--release` keep the slot's 10-minute lease on the assignments issue (a held slot exits 3), and `--next` renews it and prints one
next step; `watch --assign <slot>` renews it too and returns within 5 minutes with `no event` (ADR-0368). With `assign`, every router run keeps the plain issues
`No live conductor` and `Builder pool down` (label `agk-health`) in step with the leases; a slot counts toward `Builder pool down` only when it ran within `slot_active_days` of the `[flow]` table (7 by default), and one never seen or older is listed as retired (ADR-0498); `route.py --health [--dry-run]` is that check alone, for local mode. `doctor.py` prints each slot's four scheduled minutes and warns of a slot with no run in the last hour (`slot-schedule`, ADR-0402). Each scheduled start runs `session.py slot --take <slot>` and ends on exit 3; then `slot --next <slot>` for each step, `slot --renew <slot>` before a build step that may pass 10 minutes, and `slot --release <slot>` before it ends. `session.py prompt --brief N` prints the builder's standing prompt from the kit's files, GET only: the item line with
the brief's reserved numbers (its `Reserved:` lines and the `reserves` of its takes) and the session name when given, the files to
read first, the secret-scan deferral line of `prepush.py`, the body lines of CLAUDE.md item 7 read from `config/core-rules.md`, and
the session rules that bind a builder quoted from `config/session-rules.md`; `--follow-up TEXT` (one line, never a verdict)
replaces the stop on an existing pull request with the follow-up for it. The guard allows exactly these forms.

## Playbook evidence

With a declared work type (`[delivery] work_type` in `agk.toml`, SPEC-0038 rule 5), a clearing verdict on a pull request of the
project carries one `Playbook evidence:` line, after `Checklist:` and before the findings, with one item per entry of `evidence` in
`config/playbooks/<work type>.toml`, in the playbook's order and in its words (SPEC-0038 rule 9, ADR-0319; brief #666):

    Playbook evidence: <item> (<where>); <item> (<where>); <item> (not applicable: <reason>)

`<where>` is where the conductor read the item. For a `judgement` gate it is a person's line, `comment <id>` (a comment on the
pull request or on the brief), or a run record, `docs/runs/<file>` of the repository; for a `check` gate it is the governance
step, `step <name>`, green on the reviewed head; an item that does not apply to the brief reads `not applicable: <reason>`. The
form of `<where>` says which kind of gate the item evidences; the shipped playbooks list their evidence in their gates' order.
For example, on a `web-app` project whose brief adds no screen:

    Playbook evidence: the contract test output (step contract-tests); the mock parity output (step mock-parity); the e2e smoke run record of the merge batch (docs/runs/e2e-smoke-batch-3.md); the accessibility review (not applicable: the brief adds no screen)

The line is read by the conductor and by a person, never by a check: `check_pr_body.py`, `proof.py` and the proof job do not
read it (Q-S0038-10). A missing item, or a missing line, on a project with a declared work type is a fix item, never a clearing
verdict, so nothing merges on a missing line; without a declaration no verdict carries the line and nothing changes.

## Playbook gates

`python3 scripts/agk/run_gates.py [--baseline] [--root DIR]` runs, from `check_playbooks.py` once the playbooks pass (so inside
`make governance` and the `governance` job, with no workflow change; Q-1586-3), the `step` of each
`kind = "check"` gate of the playbook that `[delivery] work_type` names, composed with `default.toml` (or `default.toml` alone
with no work type) (SPEC-0072 rule 3, ADR-0666; brief #1586). Each step is one module of the registry `scripts/agk/gates/`
(`__init__.py`; `cut_over_order.py` and `rollback_order.py`, which read the playbook's split; `committed_secrets.py` and
`environment_settings.py`, the `secrets` and `environment-settings` checks of `default.toml`, brief #1593, ADR-0673), offline on
the project's files. `committed-secrets` fails on a tracked secret file, an environment file that `.gitignore` does not ignore, a tracked
secret shape or `[guard] patterns` match, and a value in `.env.example`; `environment-settings` fails on a setting the
project's Python code reads that `.env.example` does not list, or a required one given a default elsewhere. With
`mode = "adopt"` both hold their findings.
`tests_floor.py`, the `tests-floor` step of `default.toml`'s `tests-first` check (brief #1590, ADR-0670), runs in a project
with a `[delivery] work_type` whose architecture record exists, and fails when the `test_dirs` hold no test file, when the
integration folder (`<first test_dirs entry>/integration/`) holds none, or when the change adds or changes a layer's code file
and no test file; a deletion only is green, `mode = "adopt"` holds the first two, and it prints `not run tests-first: no work
type` (the kit's own repository), `no foundation yet` or `no reader for <stack>`.
It prints `ok <gate id>` per gate that passes and `FAIL gates: <gate id>: <rule> (path class: <class>)` per failure, never a
value; a step with no module is refused naming the gate id. It ends `ok gates (<n> check gates)` or `ok gates (no check gate)`.
A step that cannot read the project prints `not run <gate id>: <reason>`, never `ok`, and the last line adds
`; not run: <ids>` (brief #1588, ADR-0668).

The contract steps (brief #1597, ADR-0677; web-app and api-service) read `contracts/openapi.json`, OpenAPI 3.1 in JSON
written from `kit/templates/contract-openapi.json`. `contract_tests.py` (gate `contract-tests`) fails a contract that does
not parse and an operation whose `operationId` no file under `test_dirs` names; `mock_parity.py` (gate `mock-parity`) fails
an operation with no JSON mock under `mocks/` (`{"operationId": ..., "response": {...}}`) of the same response keys. With
no contract, or in `mode = "adopt"` one in another format, both print `not run`. The data model is `docs/data-model.md`
from `kit/templates/data-model.md`, and `check_plan.py` refuses a `Kind: back-end` brief that does not depend on the
`Kind: contract` brief while either file is missing.

    python3 scripts/agk/basics.py write [--root DIR]

The foundation's basics (brief #1594, ADR-0674; SPEC-0072 rule 4 as amendment 202 proposes). By `[delivery] work_type`
(web-app and api-service a server, data-pipeline a report job) and for a chosen Python stack, `write` adds the `.env` line to
`.gitignore` and writes, never over an existing file, `.env.example` (names and `<placeholder>`s only), the package's
startup settings check and safe log, the health address `/health` (servers), `README.md` and `docs/deploy.md` ("local only"
until a hosting option is chosen; a deploy is the person's own act). With `mode = "adopt"` it writes nothing and prints one
`proposed: <path>: <question>` per missing part. A tracked `.env` is named, never removed. Another work type or stack prints
`not written: basics: ...`; no work type prints `basics: not run`. `check_plan.py` refuses a foundation milestone with no
`Kind: slice` brief, the first working slice.

    python3 scripts/agk/gates/layers.py [--root DIR] [--write-record]

The `layers` step (SPEC-0072 rule 5; `default.toml`'s gate `layers`) reads each Python file of a layer of the composed
`[architecture]` and fails on an `import` or `from` line, relative ones included, that lands in another layer with no
`allow` entry from the first to the second, naming the rule, both layers and the layer's glob, never a file or a module.
One layer (`default.toml`'s `src`, a project with no work type) constrains nothing; an Accepted stack record whose runtime
is not Python gives `not run: no reader for <stack>`. `--write-record` is the foundation's: it writes
`docs/architecture.md` (a protected path of every project) from `kit/templates/architecture.md` once, with the layers,
their paths, the allowed directions and the stack record's ADR, and is refused with no work type (setting: `work_type`).

    python3 scripts/agk/gates/architecture_record.py

The `architecture-record` step (brief #1595, amendment 204) is a module of the runner, never run by itself: where
`docs/architecture.md` exists `run_gates.py` runs `front_door.py`'s record check through it (see "Front door").
A build brief of a work-type project other than its foundation carries one line `Layer: <layer>, ...` naming every layer
its `Touches:` meets; `check_brief.py --root` refuses one without it or with an unknown layer (SPEC-0072 rule 8).

After the gates it runs the standards pack of the chosen stack (SPEC-0072 rule 6, ADR-0669; brief #1589):
`scripts/agk/gates/python_pack.py`, for the `python-pyproject` and `python-pip` entries of `[[standards]]`, only when the
Accepted stack record chose Python. Over the product files of `project_lint_paths` (top level of `agk.toml`; unset: the
paths of `[architecture] layers`; any other form than a list of relative globs is refused naming the setting) it checks
that the pack's `config` file enables every pinned rule code (the `floor`, rule 8), then runs `python -m ruff check`,
`python -m ruff format --check` and `python -m mypy`, never through a shell. A finding prints `FAIL gates: standards
<stack> <step>: <rule> (path class: <glob>)`, a missing tool names the tool and the setting, and a passing pack prints
`ok standards <stack>`. `lint_paths` and `agk-lint` are unchanged.

The baseline of an adopted project (SPEC-0072 rule 7, ADR-0680; brief #1600): `scripts/agk/gates/baseline.py` keeps
`config/agk-baseline/<gate id>.txt`, one line `<path> <count>` per file with findings (forward slashes, sorted bytewise),
for each step that reports per-file counts (`layers`, and the pack's `lint`, `format` and `type`). With the file, the step
passes while no count exceeds its line (`ok <id> (baseline)`), prints `baseline <id>: a count fell in <n> file(s)` when one
falls, and fails with one `SPEC-0072 rule 7` line on a new finding or a rising count. Without it, `mode = "adopt"` writes it
from today's tree and passes; `mode = "init"` writes nothing. `--baseline` writes the missing files and lowers lines, never
raising one: the owner's yes on an upgrade and the next build's lowering commit. `check_protected_changes.py` lets a
lowering pass with no ADR and refuses a rise, a new line, a new file or a deleted one unless an ADR names it.

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

    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/uninstall.py" TARGET [--write] [--remove-docs] [--agreed PATH ...]
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/uninstall.py" TARGET --pause [--write]

`/agk:uninstall` runs `scripts/agk/uninstall.py` from the plugin (or a kit checkout), never the copy in the repository, since
the removal deletes it. Without `--write` it is a dry run and writes nothing. With `--write` it refuses a work tree with
changes, makes one new branch (`agk-uninstall`, or `agk-pause` for `--pause`) and writes the change there, uncommitted: you
review it, commit it, push it and open one pull request, which git can revert. The report lists the lines left in your own files that still name a removed kit path,
settings to tidy by hand first, then records, which stay as written.

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

- **In a clean project** (`[kit] layout = "plugin"`, SPEC-0071 rule 9): `LICENSE-AGK` and the short `CLAUDE.md` go too,
  and each record named with `--agreed PATH` (a file or folder of the project's records that the owner and the customer
  agreed to remove); the specs and decisions stay unless named. The report then prints, never runs, the history
  clean-up: every kit path of every release row of `kit/hashes.json` that `git log --all` finds, the `git filter-repo`
  command for that list `(verify)` and its checklist (the customer's audit and retention choice, the written agreement,
  branch protections paused and restored by the administrator, every clone made again). `--agreed` outside the clean
  layout is refused, naming `layout`.

The output names the protected classes the branch changes and prints an ADR skeleton; write the ADR yourself. After the
removal merges, `agk doctor` reports `no kit installed` (exit 0) instead of failing: in a git work tree with no `agk.toml`,
no `[tool.agk]` stamp in `pyproject.toml`, and none of `agk.mk`, `scripts/agk/`, `tests/kit/`, the governance, proof and
router workflows and the stop hook (brief #348 build (b), ADR-0203).

## Local mode

When GitHub Actions is blocked (minutes exhausted, billing blocked, an outage), follow [local-mode.md](local-mode.md): how to
disable and re-enable the workflows with `gh workflow`, what a builder runs and pastes as its `Local evidence:` line, what the
conductor runs instead of reading CI, what is lost, and the one issue that records every merge (session rule 30, ADR-0182).

## Runbooks

`docs/runbooks/` holds one short checked page each for a red default branch, blocked Actions and a leaked secret. A real
secret-scan finding goes straight to [the leaked-secret page](../runbooks/leaked-secret.md): revoke first.

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
machine. A holder that still runs on this machine is never cleared by age; a lock of another host is cleared only when its
heartbeat, written about once a minute, is older than `lock_stale_minutes` (120 by default, ADR-0295). The lock is a folder in the
user's temp folder, or `lock_dir` in `agk.toml`. `python3 scripts/agk/lock.py status --name heavy` prints the holder, its age and
the heartbeat's age, or `free` (ADR-0191).

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

A builder in local mode records its run with `python3 scripts/agk/prepush.py --record` (ADR-0208; with no FILE the record goes
to `<git common dir>/agk-evidence/<head>.json`, the clone's shared folder, ADR-0536), and the conductor checks that record
before its verdict with `python3 scripts/agk/evidence.py check --head SHA [--sample N] [--body FILE] [--json]` (`--body`: the pull request body for governance, brief #1566), or `check RECORD [--head SHA]`
for a record file passed from another machine: `stale`,
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

## Where checks run

    python3 scripts/agk/execution.py [--json] [--repo OWNER/REPO] [--api-dir DIR]

`execution` in `agk.toml` names, in one top-level line, where the heavy checks run: `hosted` (the default, also when unset),
`hybrid` (the required light checks on GitHub-hosted runners, the heavy checks on a pool or locally), `pool` or `local`; any
other value is refused, naming the setting. The command prints one line, `execution: <set> (recommended: <profile>:
<reason>)`, from a fixed table: Actions disabled for the repository or its included minutes used up gives `local` (see
[local-mode.md](local-mode.md)); a public repository gives `hosted`; a private one past half of its included minutes, or past
`minutes_warn`, gives `hybrid`; more than half left, or a billing reading that is unknown, gives `hosted` with that reason.
With `pool` or `hybrid` set and no repository variable `AGK_HEAVY_RUNNER`, a second line points to
[self-hosted-runner.md](self-hosted-runner.md). It reads through `minutes.py` (GET only), changes no workflow and writes
nothing (ADR-0237).

## Draft state at run time

    python3 scripts/agk/pr_state.py --pull FILE [--event-draft true|false]

Prints `true` when the pull request is a draft at the time the governance job runs, else `false`: `FILE` holds the answer
of the one GET of the pull request that the job makes, and the payload's draft state, when given, can only turn a draft
into `false`. A read that failed, or an answer without a true or false `draft`, prints `false`, so the heavy steps run. It
reads a file only, with no network. See ADR-0499.

## CI tools

    python3 scripts/agk/ci_tools.py check [--upstream] [--responses DIR]

The governance workflow's `Install tooling` step installs the CI test tools from `config/ci-tools.txt`, one exact
`<name>==<version>` pin per line in name order, so a tool update changes that file only. `check` prints the pins and fails,
naming the path, on a line that is not an exact pin, a repeated tool or a tool out of order; it makes no network call. With
`--upstream` it reads the package index's JSON once per pin and prints which pins are behind, the gap in days and `unknown`
for an upstream it cannot read; a person opens the update pull request from that output (ADR-0328).

## Bill of materials

    python3 scripts/agk/sbom.py make [--ref REF] --out FILE
    python3 scripts/agk/sbom.py check FILE [--ref REF]

`make` writes one CycloneDX JSON bill of what the repository's files declare at the commit (default `HEAD`): the Python
requirements, the CI tools, the pinned scanners, the actions and, in the kit, the installed files. It reads the commit with
local `git` only, and the same commit gives the same bytes. A requirement or `uses:` that is not pinned exactly is listed
as `unpinned` with no version. `FILE` inside the repository must be ignored by git, because a bill is never committed.
`check` prints `ok bom`, or one `FAIL bom: <class> <reason>` line per problem and exits 1, naming the component class and
never a value. No governance step runs it (SPEC-0054, ADR-0370).

## Test plan

    python3 scripts/agk/test_plan.py [--base REF] [--head REF] [--json] [ROOT]

Shows, before anything runs, which tests proof will run for a change and why. For each `[proof]` area it lists the added or
changed test files, the command line with `{files}` filled in and its folder, then the areas with nothing to run and the test
files in no area as "not run by proof"; without the table it prints `project_tests` and the files it selects. It reads git and
files only and runs no test. See [existing-codebase.md](existing-codebase.md#step-4-tell-the-proof-check-how-to-run-your-tests)
and ADR-0185.

## Smoke run after a merge

    python3 scripts/agk/smoke.py [--base REF] [--head REF] [--run]

Chooses the smoke run after a merge from what changed (by default the last merge on the default branch, read from local git)
and prints one line, `smoke: <choice>: <reason>`: the `frontend` or `contract` kind of `[testing] smoke` when every changed
file outside documentation matches its `code`, `none` for documentation only, and `full` (the `project_tests` run) for
anything else or without the list. `--run` runs the choice under the heavy-step lock. It is never a gate. See SPEC-0044
rule 8.

## Test map

    python3 scripts/agk/test_map.py build [--root DIR]

Writes the git-ignored file `.agk-test-map.toml` from the tree at the head: which tests cover which files, read from Python
imports and the JavaScript or TypeScript import graph, with folder conventions as the fallback. The same tree gives the same
bytes, and nothing reads the file yet. It reads git and files only and runs no test. See ADR-0379 and SPEC-0055 rule 5.

## Requirement status

    python3 scripts/agk/req_status.py report [--json] [--req REQ-nnn ...] [ROOT]
    python3 scripts/agk/req_status.py apply [--req REQ-nnn ...] [ROOT]

`report` prints each requirement whose status disagrees with its proof: `REQ-nnn planned -> done (proof: <n> tests pass)`,
`REQ-nnn done but proof fails (<test file>)`, `REQ-nnn proof unknown (<test file> timed out)` and `REQ-nnn: no proof
mapped`, then a summary line, and changes nothing. The proof is SPEC-0010 rule 1 (a `REQ-nnn ACn` marker for every
criterion); it passes when each test file holding those markers passes when its `[proof]` area's command runs it alone.
It runs every proving test file once, so a whole report is a heavy step. `apply` sets only the `- Status:` lines of the
`-> done` requirements to `done`, in the one pull request the conductor opens for it. Exit 1 on a `done` whose proof
fails, 4 on an unknown proof. See [existing-codebase.md](existing-codebase.md#step-4-tell-the-proof-check-how-to-run-your-tests)
and ADR-0321.

## Reading a log

    python3 scripts/agk/guard_logs.py [--max-lines N] FILE|-|--refusals

`agk logs`: prints the last `N` lines (default 2000) of a log, or of standard input with `-`, with every secret and every
piece of personal data that the data guard's detectors find replaced by a label such as `[EMAIL-1]`, `[CARD-1]` or
`[TOKEN-1]`; the same value keeps the same label in one run, and the rest of each line is unchanged. The last line holds
the counts per kind only. It opens no socket, writes no file and keeps the values in memory only. A custom kind is added
with `patterns` in the `[guard]` table of `agk.toml`, which can only add to the built-in detectors; a refused table, a bad
option or a file it cannot read exits 2 naming the setting or option. See SPEC-0042 rules 10 and 11 and ADR-0268.
`agk logs --refusals` prints the hooks' refusal log (`refusals.log` in the `agk` folder of the git common dir, and its one
older file first) the same way, or `agk logs: no refusals recorded` (brief #1410, ADR-0593).

## The guard ladder

    python3 scripts/agk/lessons.py ladder [--root DIR] [--today YYYY-MM-DD]

Reads the catch logs (`docs/runs/*-catches-*.md`) and prints each row's guard level (`lesson`, `rule`, `test`, `check`,
`workflow`), every row due to climb and the rule it meets, every guard whose file is missing or has no line citing its row,
every malformed guard, and one count line. It reads files only; it exits 1 on a missing line or file or a malformed guard,
and the due list never blocks. See [guard-ladder.md](guard-ladder.md) and ADR-0309.

## Flake ledger

    python3 scripts/agk/flakes.py [--today YYYY-MM-DD] [--json]

Reads `docs/runs/flakes.md`, the one table of flaky tests with their owner, strikes, status and expiry, and lists each
quarantine past its expiry (`expired`), each test with two strikes or more and no issue (`brief due`) and each malformed row
with its line number. Exit 0 when nothing is listed, 1 otherwise. It is not a governance step and blocks nothing. See
[testing.md](testing.md#the-flake-ledger) and ADR-0234.

## Front door

    python3 scripts/agk/front_door.py check-issue --issue FILE
    python3 scripts/agk/front_door.py discovery-write (--issue FILE | --vision FILE) --answers FILE [--root DIR]
    python3 scripts/agk/front_door.py check-discovery [FILE ...] [--root DIR]
    python3 scripts/agk/front_door.py check-research --date YYYY-MM-DD [FILE ...] [--root DIR]
    python3 scripts/agk/front_door.py check-design --date YYYY-MM-DD [FILE ...] [--root DIR]
    python3 scripts/agk/front_door.py status --date YYYY-MM-DD [SLUG ...] [--root DIR]

`check-issue` reads a saved problem issue (the JSON of one GET) and refuses one without the `agk-problem` label, without a
first line `Problem: <words>`, with an empty problem or one over 1,500 characters, or with anything the data guard finds.
`discovery-write` writes `docs/discovery/<slug>.md` from the problem and a JSON file of the person's answers, never over an
existing one; `check-discovery` checks each such document. Files only, no network; every refusal names the rule and the
file, never a value. See SPEC-0048 rules 3 and 5.

`check-research` checks each `docs/research/<slug>.md`: at least two `## Option: <name>` sections, each with a source line
`- Source: <URL> (accessed YYYY-MM-DD)`, a `## Criteria` table with a row for capability fit, cost, licence, data handling
and residency, maturity, integration effort and lock-in, and a `## Recommendation` marked `(proposal)`. A record that a
design cites fails when any source was accessed more than 180 days before `--date` (pass `date -u +%F`); reading the
sources again and changing their access dates makes it fresh. `check-design` checks each
`docs/design/architecture/<slug>.md`: a fenced plain-text or Mermaid diagram, no image, and exactly one line
`Research: docs/research/<slug>.md` naming a record of the same slug that passes and is fresh. See SPEC-0048 rules 6
and 7.

`check-design` also checks the design's one review artifact, chosen by the `- Screens:` line of
`docs/discovery/<slug>.md` (SPEC-0048 rule 8). With `no` (a pipeline, a migration, an agent, a service) the design has
exactly one line `Demo: docs/runs/<file>` naming the run record of a demo or a dry run on invented data; the check reads
only that the file exists and never opens or runs it. With `yes`, and with `open` or no discovery document (read as
`yes`, the artifact with more to review), a prototype version folder `docs/design/prototype/v<n>/` exists, which
`check_design.py` checks (SPEC-0037). A `Walkthrough: <where it is kept>` line may name a recorded walkthrough: it is
judgement, noted and never opened, never printed and never committed, and it never stands in for the artifact. The
conductor reads the same rule: a design without its artifact is a fix item, never a clearing verdict.

`docs/architecture.md` is the product's one architecture record (brief #1595, amendments 204 and 205). A design is a
slice of it and carries one line `Architecture: docs/architecture.md`: `check-design` refuses a design named on its
command line without it, and warns, until its next edit, about one read with the whole folder. Where the record exists
`check-design` also checks it, as the `architecture-record` step of `run_gates.py` does: `## Context`, `## Parts`,
`## Data stores`, `## Outside services` (each service of the chosen stack option), `## Needs` (`- Busiest hour:`,
`- Downtime:`, `- Cost:`, `- Recovery time:`, `- Logged:`, the first three's numbers those of the quoted `scale` answer
of the charter or a discovery document), `## Diagram` (a fenced block that draws each outside service) and
`## Layers`. Each failure names the rule and the section, never a value; a record with none of these sections, written
before them, is `not run` until its next edit.

`status` prints one line per problem, `<slug>: phase <n> <name>; waits for <what>`, for the slugs named or else for each
`docs/discovery/*.md`, from the files only, and writes nothing: phase 2 discovery until the discovery document passes
`check-discovery`, phase 3 research until the record passes `check-research` and is fresh, phase 4 design until the
design passes `check-design` with its artifact, then `phase 5 the go; waits for the go`. The entry and the go are lines
on the problem issue and the pull request (`Approve:` by an account in `spec_approvers`, never a session's), which
`status` does not read from files (SPEC-0048 rules 1 and 9).

## Failure signature and evidence

    python3 scripts/agk/failures.py signature --output FILE [--step NAME]
    python3 scripts/agk/failures.py evidence --output FILE [--test ID]
    python3 scripts/agk/failures.py issue-body --signature SIG --test ID [--issues FILE]
    python3 scripts/agk/failures.py seen --signature SIG --test ID

`signature` prints `<signature> <test id>` for each failed test of a run's output (the `[testing] junit` report when it is
readable, else the `FAILED <id>` lines; `step:NAME` when there is no test id). `evidence` prints the cleaned last 200 lines
of that test's output, or only `evidence withheld: ...`. `issue-body` prints whether a failure needs a new `found-bug` issue
or a comment on an open one, from a saved issue list; with `[failures] issues` off (the default) it prints `action: none`.
It reads files, prints and writes nothing. `seen` reads the project's own closed `found-bug` issues that hold a fix record
and the merged pull requests that name them (GET only, writes nothing) and prints at most three lines
`seen before: #<issue> <symptom>; fixed by #<pull request>`, the exact signature first, then the same test id, newest
first; a read that fails says so in one line and exits 4. See SPEC-0046 rules 2, 3, 5 and 9 and ADR-0303.

## Scorecard

    python3 scripts/agk/scorecard.py [--today YYYY-MM-DD] [--repo OWNER/REPO] [--api-dir DIR]

Prints one table of the week before the run date: each level metric of SPEC-0047 rule 1, its value and its line (the
`[scorecard]` table of `agk.toml`, else the kit default). A value that cannot be read is `unknown`, never 0. It reads
with `gh api` GET only, or saved responses, and writes nothing; no check runs it. See SPEC-0047 rules 1 to 3 and ADR-0311.

## Parity

    python3 scripts/agk/parity.py report [--root DIR]
    python3 scripts/agk/parity.py check [--root DIR]

Lists every discipline the kit applies to itself (each `scripts/agk/*.py`, each `.claude/agents/*.md`, each file directly
under `config/` and each `docs/runs/` log an agent file names) with how a project gets it: `installed` (`kit/manifest.json`),
`plugin` (a skill runs it from the plugin root, or a script the plugin runs imports it) or `kit-only (<reason>)` from
`config/kit-only.txt`. `check` exits 1 naming each discipline in none of the three and each stale, unreasoned, repeated or
empty line of the list; the list may only shrink (`tests/kit/test_parity.py`). A tree without `kit/manifest.json` has nothing
to check. It reads files only. See ADR-0326.

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

For a business person (brief #1591, ADR-0671, amendment 199), a Proposed stack ADR gives each option its `Cost:`,
`Build speed:`, `Security:` and `Uptime:` in plain words and marks one option `(recommended)` with a `Why:`; `stack-check`
refuses each gap naming the option letter, and an Accepted record is checked as before. `stack-write` writes the
recommended stack of the declared shape from `config/stack-defaults.toml` as Option A, and
`engines.py stack-accept --option X --reason TEXT` makes the accepting change in its two ordinary commits after the
person's one plain yes.

Pinned parts (brief #1592, ADR-0672, amendments 200 and 201): in a Proposed stack ADR each option names its `Parts:`, each
`<name> <exact version> <licence id>` (an SPDX id such as `MIT` or `BSD-3-Clause`, marked `(verify)` until the foundation's
build installs them), and `stack-check` refuses a range, a missing version or a missing licence naming the option and the
part's place. `engines.py stack-files` writes the chosen stack's build file from `kit/templates/stacks/` (Python:
`pyproject.toml`; `node`: `package.json`) and never rewrites a project's own; the lock is made by the stack's own tool on
the builder's machine and committed.

    python3 scripts/agk/gates/pins.py [--root DIR]

The `pins` step reads the chosen stack's build file and its lock (`requirements.lock` or `package-lock.json`), offline,
and fails on a direct dependency not pinned exactly or not in the lock, on a missing lock and on a part of the Accepted
stack record whose version differs from the lock's, each line naming the rule and the component class, never a name or a
version. With no `[delivery] work_type` or no Accepted stack record it prints `pins: not run: no stack chosen`.
It is one module of the step registry `scripts/agk/gates/` (`__init__.py`, the registry's helpers, as brief #1586 names
them), with the runner's interface.

    python3 scripts/agk/gates/licences.py [--root DIR]

The product's own dependencies (brief #1596, ADR-0676, amendment 206): with a chosen stack, `sbom.py make` also lists each
package of the committed lock (class `python` or `node`) with its version and its licence, from the lock where it states
one, else the stack record's `Parts:`. The `licences` step fails on a licence outside `allowed` of `config/licences.toml`
(absent: the list of `kit/templates/licences.toml`, which `engines.py stack-files` writes once) and on a package whose
licence it cannot read, as `unknown`, naming the rule and the component class only; a list of another form is refused
naming the setting. With no stack or no lock it prints `licences: not run: no lock`. `run_gates.py` runs it and the `bom`
step (the bill of `HEAD`, made and checked in memory) where a stack is chosen and its lock is read; with
`mode = "adopt"` the licence findings are held until the baseline. The list is a project policy, not legal advice.

## Design check

    python3 scripts/agk/check_design.py [--root DIR]

An installed check, a step of `make governance` and of the governance workflow (SPEC-0029 rules 7 and 9). It reads `docs/design/theme.md` and the mockup folders `docs/design/mockups/<date>-<name>/` and fails, naming the
rule and the path and never a value, on: a script or an event handler, an external request or a loaded resource, a colour that is not a token
(every colour of a mockup is a `var(--token)`), tokens that are not one block with a light and a dark set, a contrast under 4.5:1 (computed from
the hex tokens in both modes, for the pairs the theme lists under `## Contrast`), a brand value with no `source:`, and an evidence line that
points to no mockup folder. Two things it prints without failing: `design: the theme is not approved yet` when the evidence folder's `README.md`
has no line `Approved by <name> on <YYYY-MM-DD>`, and `at risk design: placeholder brand` when a brand value is still a `[bracketed]` placeholder
(SPEC-0029 rule 7). The files it reads are written by `/agk:design` (the theme from the engine named by `design` in `[engines]` or from the kit's template, a mockup folder with `Approved: not yet` in its `README.md`, and four screenshots, 360 and 1280 px wide, light and dark, when a headless browser is found) or by hand. The approval line is the owner's: the session never writes `Approved by`. With no `docs/design/` it prints `ok design (no design record)`.

## Design screenshots and comparison

    python3 scripts/agk/design.py screenshots --version v<n> [--root DIR]
    python3 scripts/agk/design_compare.py --version v<n> --screens "<screen>/<state>, ..." [--root DIR]

Two kit-only commands of SPEC-0037 rules 8 and 11 (brief #461, ADR-0350), never run by CI. `design.py screenshots --version`
opens each `<screen>--<state>.html` page of a prototype version from the files, offline, at each breakpoint of the standard
(360, 600, 900, 1200 and 1440 px) in light and dark, with a headless browser found on PATH, and writes one screenshot of each
into the version's `screenshots/` folder and `screenshots/reflow.json`, one entry per page, breakpoint and mode (which `check_design.py` reads), `ok` or
`sideways` (the page is wider than the viewport). Without a browser it prints `design: no headless browser found; reflow not run`,
writes every entry as `not run` and succeeds. `screenshots/` is written only by this command and is outside the signed-off
digest. `--folder FOLDER` still takes the four pictures of an old mockup folder.

`design_compare.py` is the builder's step before a UI build is marked ready: for each screen and state of the brief's `Screens:`
line (`<screen>/*` is every state, a bare `*` every page of the version) it runs the project's `render` command with
`AGK_DESIGN_SCREEN`, `AGK_DESIGN_STATE` and `AGK_DESIGN_OUT` set, reads `<out>/<screen>--<state>.html` and compares it with
the frozen page: the structure (landmarks, heading outline, controls with their labels, link texts in order; the prototype's
state bar, demo bar and runtime are left out), the standard's tokens it uses, and, with a browser, the share of differing
pixels at each breakpoint and mode. It prints `<screen>/<state> match` or `<screen>/<state> drift: structure, tokens, pixels`
(the kinds found), ending `; pixels: not run` without a browser, and exits 0 on drift; the conductor judges each drift. It
exits 1 only on a usage error, an unset or failing `render`, a bad `pixel_tolerance`, a version without a `design` row in
`docs/design/signoffs.md` or a screen the version lacks, naming the setting or the rule.

The `[design]` table of `agk.toml` (off when absent): `ui_paths`, the globs of the project's UI files (a brief whose
`Touches:` meets one needs a `Screens:` line); `render`, the project's command that writes the built
page of a screen and state into `AGK_DESIGN_OUT`; and `pixel_tolerance`, the share of a screenshot's pixels that may differ
before pixels are reported as drift (0.01 by default; it only reports, never fails).

## Plan intake

    python3 scripts/agk/plan_intake.py validate --proposals FILE [--root DIR]
    python3 scripts/agk/plan_intake.py states [--root DIR]
    python3 scripts/agk/plan_intake.py render --proposals FILE [--again] [--root DIR]
    python3 scripts/agk/plan_intake.py publish --comments FILE --head SHA [--numbers FILE] [--root DIR]

Validates the plan's proposals file: `validate` prints `ok proposals` or one line per problem naming the rule and the item's
`key` or `id`, never its text; `states` prints the inventory's `yes` states that no design source covers. Every command runs
the data guard over each source first and stops with exit 2 when the guard is not installed. It reads files only, with no
network and no model. `validate` and `states` write nothing. See SPEC-0043 rules 3 to 6. `render` validates first, prints
the conflicts and the open questions, and writes once, as new files only, the scope, the milestones, the proposed
requirements, one Draft spec per feature area and one brief per brief under `docs/plan/` (rule 7). `publish` exits 2 without
`Approve: plan <--head>` by an account of `spec_approvers` in the saved comments, and prints one `gh api` command per
milestone and per brief, briefs in dependency order, each withheld until `--numbers` names its milestone and its
dependences; it runs none (rules 8 and 25). Questions of one kind about one feature area are one question for business, a
cross-reference gap is a `Note:` of its requirement, and `validate` warns above `[plan] max_questions` (60 by default).
`render --again` rewrites only the files the last render wrote whose bytes are unchanged since (the digests in
`docs/plan/render-digests.json`), creates new ones and names each edited file it leaves (ADR-0520). Once nothing is withheld its last line ends `; next: /agk:board --yes`.

    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/board.py" [--title TEXT] [--owner LOGIN] [--project N] [--yes]
        [--template OWNER/NUMBER]

`/agk:board` (the plugin's copy, run with your own `gh` and its `project` scope) makes the plan's GitHub Project board and
keeps it in step (ADR-0506). Without `--yes` it prints the steps and changes nothing. With `--yes` it creates the board
once (`<repository> plan`, under the repository's owner) and prints `board = <n>` for you to add under `[plan]` of
`agk.toml` and commit. With `--template OWNER/NUMBER` (or `[plan] board_template = "<owner>/<number>"`) that first run
copies your template board with its views and columns instead (ADR-0507); without one it prints the three views to make
once. Every run links the repository, adds the `Size`, `Expected hours`, `Persona`, `Requirement`, `Screens` and
`Sign-off` fields when missing and adds each open `agk-brief` issue not yet on the board with its size, the high end of
its hours, its `Persona:`, `Advances:` and `Screens:` lines and `Sign-off` Pending. It never removes or edits an item
already there (a field the run added to the board is filled on it once), and ends `ok board: <a> added, <b> already
there`. A missing scope prints
`gh auth refresh -s project` (exit 2); in a cloud session it prints one `board: needs a machine ...` line and exits 0.

    python3 scripts/agk/design_import.py source --version i<n> --slug <slug> [--root DIR]
    python3 scripts/agk/design_import.py source --version v<n> --slug <slug> [--root DIR]
    python3 scripts/agk/plan_sources.py vision|architecture [--root DIR]
    python3 scripts/agk/check_plan.py [--root DIR] [--trace] [--facts FILE] [--numbers FILE]

`design_import.py source` writes once `docs/sources/<slug>-prototype-i<n>.md`, a `Kind: design` source with one
`## <screen>/<state>` heading per mapped row of an imported version and the page's visible text under it (SPEC-0043 rule
2a); it refuses a version whose import or map check fails and an existing file. With `--version v<n>` it writes
`docs/sources/<slug>-prototype-v<n>.md` from a kit version, one heading per page `<screen>--<state>.html`, and refuses a
version that is not signed off with the digest its folder has now (brief #1216, ADR-0515). `plan_sources.py vision`
writes once `docs/sources/vision.md` (`Kind: charter`) from `constitution/vision.md` and the Accepted charter ADR, and
`plan_sources.py architecture` writes once `docs/sources/architecture.md` (`Kind: other`) from the Accepted stack ADR,
each text unchanged; each refuses an ADR that is not Accepted, a missing file and an existing target. `check_plan.py` is a governance check: the
source headers and design links (rules 1 and 2), the plan's checks (rule 10) and the coverage line `ok plan: <a> of <b> ...`
(rule 11); `--trace` first prints the matrix from source location to requirement, spec rule, brief, pull request and test
(rule 9). The whole path, with a recorded walk, is in `docs/guides/planning.md`.

## Plan names

    python3 scripts/agk/plan_names.py next --base PATH [--root DIR] [--issues FILE] [--pulls FILE]
    python3 scripts/agk/plan_names.py batch FILE [--root DIR] [--issues FILE] [--pulls FILE]
    python3 scripts/agk/plan_names.py impact PATH [--root DIR] [--issues FILE] [--pulls FILE]

One owner per new path (brief #1425, ADR-0598). `next` prints the base when no file of the default branch, no open brief's
`Adds:` or `Touches:` and no open pull request's added file holds it, else the base with `-2`, `-3` and so on; paths are
compared ignoring case, `./`, a trailing `/` and backslashes. Name a new folder `<feature>-m<milestone>-<part>`
(`access-control-m7-api`). `batch` names one base per line of FILE in one pass, so a batch never clashes with itself.
`impact` lists every open brief and pull request that names a path and who renames it: the steward edits a brief not yet
taken, a taken one gets a fix list. `--issues` and `--pulls` read saved lists (`[{"number", "brief", "added"}]` for pull
requests) instead of one listing each. The brief check with `--root DIR [--open-briefs FILE] [--number N]` refuses an `Adds:`
entry another open brief or pull request holds, naming it and a free name, and `session.py plan` prints
`CLASH: #a and #b both add <path>; rename in the one not taken (#n, free: <name>)` and starts neither until one is renamed.

## Plan ceremony

    python3 scripts/agk/plan_ceremony.py planning|daily|review|retro --facts FILE [--plan DIR] [--today YYYY-MM-DD] [--weeks N] [--stalls FILE] [--matches FILE]

Prints the text of one ceremony of the plan's iteration of `[plan] iteration_days` working days, numbered from the
baseline's date: `planning` the open briefs up to the measured capacity with the forecast, `daily` at most ten lines of
what finished, runs and is blocked (with a saved `stalls.py --json` output), `review` each touched milestone's evidence,
design version and `Demo:` screens with their `Design match:` lines (a saved JSON file), and `retro` measured facts with
at most three candidate briefs. It posts nothing, files nothing and runs no other program. See SPEC-0043 rules 23 and 24.

## Plan estimate

    python3 scripts/agk/plan_estimate.py --facts FILE [--plan DIR] [--today YYYY-MM-DD] [--weeks N]

Estimates each milestone of `docs/plan/milestones.md` from facts made with `facts.py --weeks N` for the same `N` (12 by
default, 4 to 52): the hours and finish dates as P50 and P85 of a seeded simulation over the project's merged pull
requests and its weekly throughput of closed briefs, each followed by its `inputs:` line, or `uncalibrated` with the
reason and the briefs' declared ranges while the history is below `[plan] calibration_min` (10). It reads files only,
with no network and no model, and writes nothing. See SPEC-0043 rules 12 to 16.

## Plan status

    python3 scripts/agk/plan_status.py --facts FILE [--plan DIR] [--today YYYY-MM-DD] [--weeks N] [--json | --base IN --into OUT]

Prints, for each milestone of `docs/plan/milestones.md`, its briefs done and open, the hours spent against the P50 and
P85 of `plan_estimate.py`, the forecast finish, the target, the status (`late`, `unknown`, `at risk` or `on track`), the
trend of the P85 finish since the start of the report's week and at most three measured causes; then the plan or scope
changes that wait for the person. `--json` prints the same as data, and `--base IN --into OUT` writes a copy of the
report's facts `IN` with that data as the key `plan`, from which the weekly report lists the milestones at risk or late
and what waits for you. An input it cannot read prints `unknown`. Files only, no network. See SPEC-0043 rules 17 to 19.

## Upgrade

    python3 scripts/agk/upgrade.py TARGET [--dry-run] [--write-adr [--date D]]

Run from the kit checkout or the plugin root (not installed into targets). Brings an init or adopt target from the kit
version in its `agk.toml` to this kit: a file that equals the kit's copy is skipped, a file that is an old released copy is
replaced, a new file is created; a file the user edited stops the whole run and nothing is written; a file removed from
the kit is reported, never deleted. `kit/hashes.json` (a committed generated file, regenerated by
`python3 scripts/agk/kit_hashes.py --write`) says what each file was at each version. User-owned files are never
rewritten; changed templates and new `agk.toml` keys are printed; only the `version` line of `agk.toml` is set, last. It
prints the target's protected classes and an ADR skeleton for the upgrade pull request; with `--write-adr` it writes that
ADR itself, `docs/adr/<next>-upgrade-agk-to-<version>.md` with every section `check_adrs.py` requires, the protected
classes it changed and `Status: Proposed`, keeps one already titled for the version, and writes none when nothing
changed (ADR-0521). An install stamped only in
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

## Rehearsal proof

    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/rehearsal.py" check [--root KIT_ROOT]

Kit-only, run from the plugin. Checks the rehearsal record (`### Rehearsal record`) in SPEC-0071's proof: an `installed` and a `clean` run of the
same five briefs, each with its dates and four figures (lead time per brief, tokens per merged pull request, first-review
pass rate, failed checks). It fails, naming the figure and never a value, when one is missing or the clean run is worse
by more than 10%. `upgrade.py --clean-repo` refuses without `--rehearsal` until the check passes and the record's
`Accepted:` line carries the maintainers' date. Reads one file, writes nothing, no network. See ADR-0617.

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

## The kit resolver

    python3 scripts/agk/kit_root.py [--form | governance]

Where the kit's scripts are for the project of the working directory (SPEC-0071 rules 2 and 3, ADR-0611). It prints the
folder: the project's own `scripts/agk/`, or the plugin's in a clean project (`[kit] layout = "plugin"` in `agk.toml`).
`--form` prints the command prefix the session prompts call `<kit>`: `scripts/agk` or `"${CLAUDE_PLUGIN_ROOT}/scripts/agk"`,
or the plugin's folder itself, quoted, when that variable is unset.
`governance` runs the gate: `make -f agk.mk agk-governance` as today, or in a clean project the same checks from the
plugin against the project, stopping at the first that fails; `prepush.py` and `evidence.py` find the gate through it.
With no plugin root, or another `layout`, it refuses naming the setting (exit 1). The clean layout is not offered yet.

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
| `/agk:stack` | `scripts/agk/engines.py stack-ids`, `stack-write`, `stack-check`, `stack-files` | one Proposed ADR of stack options on a new branch |
| `/agk:design` | `scripts/agk/design.py write`, `screenshots`, `scripts/agk/check_design.py` | `docs/design/theme.md` (when absent) and a mockup folder with `index.html` and `README.md` on a new branch |
| `/agk:launch` | `scripts/agk/session.py plan`, `scripts/agk/launch.py prompts` | nothing in the repository (after you say yes, one session per planned slot is started through an adapter, or its prompt is printed) |
| `/agk:review-pass` | `scripts/agk/session.py review-queue`, the conductor's protocol, `gh api`, then `scripts/agk/session.py plan --json` and `scripts/agk/launch.py prompts` | one `Verdict:` comment per pull request that needs one (never two on one head), from a conductor session; at the end it prints the plan, and starts the planned sessions through the project's adapter only with `[flow] auto_start = true` |
| `/agk:confirm` | `gh api` (GET), the conductor's protocol | nothing (solo mode: prints the one `Confirmed:` comment for the person to post; a session never posts it) |
| `/agk:spec` | `scripts/agk/new_spec.py`, `scripts/agk/intake.py` | a Draft spec, or a requirement proposal with its ADR draft, or (from one sentence) a requirement, a Draft spec and an ADR stub |
| `/agk:architect` | `scripts/agk/playbook.py architect` | nothing (prints how to start `claude --agent architect`) |
| `/agk:issue` | the issue templates and your own `gh issue create`, after asking | one GitHub issue |
| `/agk:brief` | `scripts/agk/new_spec.py` | one brief |
| `/agk:review` | `review_context.py`, the project's `reviewer` subagent, `check_review_report.py` | local files, never committed |
| `/agk:board` | `scripts/agk/board.py` (a dry run; `--yes` after you say yes), your own `gh project` | the plan's GitHub Project board: copied once from your template board (or created), linked, its fields, and each open brief issue added with its size, hours, persona, requirement, screens and Sign-off Pending (add-only, ADR-0506, ADR-0507) |
| `/agk:scope-lock` | `scripts/agk/check_plan.py` | `docs/plan/scope-lock.md`, the plan's scope lock in plain business words (each milestone's screens, dates and hours, go-live, after go-live, not included, decisions, questions with their dates, risks); it prints the text of a scope lock issue and creates no issue (ADR-0518) |
| `/agk:workflow-apply` | `scripts/agk/workflow_apply.py --pr <n>` (a dry run; `--yes --head <sha>` of that dry run after you say yes) | the pull request's branch: each `.agk/workflow-proposals/<name>.yml` moved to `.github/workflows/<name>.yml` in one commit, pushed (never forced, never to the default branch), and one `Answer:` comment (ADR-0505) |

No command merges, and none commits or pushes but `/agk:workflow-apply`, which, only after you say yes, commits a builder's proposed workflow file to its pull request's branch and pushes that branch with your own credentials (`/agk:ruleset` and `/agk:issue` write to GitHub only after you say yes, and `/agk:review-pass` writes only `Verdict:` comments, from a conductor session), and none sets a spec `Approved` or an ADR `Accepted`. `/agk:review` is advisory.
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

## The licence and its grant

AGK is under the AGK Proprietary Licence (`LicenseRef-AGK-Proprietary`, ADR-0596): `LICENSE` in the kit, copied into
every project as `LICENSE-AGK`; the project's own `LICENSE` is never written. Every kit file carries a three-part
header after any line that must come first (a `#!` line, an encoding line, front matter): the `SPDX-FileCopyrightText`
line, the `SPDX-License-Identifier` line and the notice, as `#` comments or as one `<!-- -->` block. Files that cannot
hold a comment (JSON), the files under `.github/` and the document templates are covered by the annotation of
`REUSE.toml`, which `LICENSE-AGK` repeats. `scripts/agk/check_licence_notice.py` fails on a kit file with neither,
naming its path class; `make governance` and the governance workflow run it; `python3 scripts/agk/check_licence_notice.py --write` adds the
missing headers. `rules.py budget` does not count the header.

A project names its written grant in `agk.toml`:

```toml
[licence]
grant = "G-2026-001"
repository = "example/app"
valid_until = 2027-06-30
```

`doctor.py` warns, and never blocks, when the table is missing, when `repository` is not the `origin` remote, and after
`valid_until`, when it names the uninstall step (`/agk:uninstall`). It reads no network and no licence server.

### The release repository

Customers install AGK from a second, private release repository, never from the development repository, so they never
see its history, briefs or decisions (ADR-0627). Each release is one plugin snapshot of the tag, holding only the paths of
`snapshot` in the tag's `kit/manifest.json` and `LICENSE` and `LICENSE-AGK`; the release repository holds one commit `Release vX.Y.Z` per
release on top of the last. Its name is `[release] repository` in `agk.toml`.

    python3 scripts/agk/plugin_snapshot.py build --tag vX.Y.Z --out DIR
    python3 scripts/agk/plugin_snapshot.py publish --tag vX.Y.Z --dir DIR
    python3 scripts/agk/plugin_snapshot.py verify --tag vX.Y.Z --clone DIR

`build` writes the snapshot from `git archive` of the tag with its own `marketplace.json` (one plugin, `"source": "."`,
the tag's version) and prints its digest; two builds of one tag give one digest. It fails, naming the path class and
writing nothing, on a kit file (as `check_licence_notice.py` defines them) without the licence header (the other files,
such as `tests/kit/`, carry none and are covered by the two licence files), on a `--tag` that is not a tag or a tag
without the `snapshot` list, on a secret or personal-data shape (`guard.scan_text`) and when
`kit_hashes.py --check` fails at the tag; `kit/hashes.json` keeps every release row. `publish` only prints the owner's
commands: commit, tag and push to the release repository, and grant or revoke one person's read access. After the push
the owner clones the release repository at the tag and runs `verify`, which fails naming the first path that differs.
A session never creates the repository, pushes, tags or grants access.

A customer installs a release with their own GitHub sign-in (Claude Code reads a private marketplace with the person's
git credentials (verify)):

    gh auth login
    gh auth setup-git
    /plugin marketplace add <owner>/<release repository>#vX.Y.Z
    /plugin install agk@agk

The owner grants and revokes one person's read access:

    gh api --method PUT repos/<owner>/<release repository>/collaborators/<login> -f permission=pull
    gh api --method DELETE repos/<owner>/<release repository>/collaborators/<login>

A revoked person keeps the copy already on their machine; the licence and the written grant cover that copy, and
revoking stops only new releases. Every mode (hosted, local, personal) installs the plugin from the release repository;
CI mode still installs the kit files into the project (SPEC-0071 rule 5), and the development repository keeps its own
marketplace for the maintainers.

Licence: proprietary, all rights reserved (see LICENSE).
