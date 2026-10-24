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
`python3 scripts/agk/reviewers.py --codeowners` prints the rendered CODEOWNERS; with `--write` it writes the file (in an
adopted repository only the marked block). `python3 scripts/agk/traceability.py` prints the requirement-to-test matrix to stdout; it is never committed.

## Installing

1. Create the target repository empty (no files).
2. Make one first commit directly on the default branch (a PR needs a base branch); record it in the target's
   ADR-0001.
3. From a checkout of agk, run init as a maintainer-approved step (an agent session blocks running a cloned script
   until a maintainer authorizes it):

       python3 scripts/agk/init.py TARGET [--dry-run]

   Init never overwrites a differing file (it refuses and lists it) and a second run changes nothing.
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
ok, 1 for an error finding, 4 for a warning or an unchecked item. See `docs/specs/0006-doctor.md` and ADR-0017.

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
name exactly one option.

## Design check

    python3 scripts/agk/check_design.py [--root DIR]

Kit-only (run from the plugin). It reads `docs/design/theme.md` and the mockup folders `docs/design/mockups/<date>-<name>/` and fails, naming the
rule and the path and never a value, on: a script or an event handler, an external request or a loaded resource, a colour that is not a token
(every colour of a mockup is a `var(--token)`), tokens that are not one block with a light and a dark set, a contrast under 4.5:1 (computed from
the hex tokens in both modes, for the pairs the theme lists under `## Contrast`), a brand value with no `source:`, and an evidence line that
points to no mockup folder. Two things it prints without failing: `design: the theme is not approved yet` when the evidence folder's `README.md`
has no line `Approved by <name> on <YYYY-MM-DD>`, and `at risk design: placeholder brand` when a brand value is still a `[bracketed]` placeholder
(SPEC-0029 rule 7). The files it reads are written by the design step (a later part of the same requirement) or by hand.

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
and cannot run without the kit's fixtures, so delete it in your own change. See `docs/specs/0008-upgrade.md` and ADR-0018.

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
| `/agk:ruleset` | `scripts/agk/ruleset.py plan`, then the `gh api` commands it prints, after you say yes | the default branch's ruleset and two repository settings (add-only) |
| `/agk:start` | `scripts/agk/playbook.py start-ids`, `check-start` | `constitution/vision.md` and a project charter ADR on a new branch |
| `/agk:vision` | `scripts/agk/playbook.py start-ids`, `scripts/agk/engines.py vision-write`, `questions`, `vision-check`, `playbook.py check-start` | `constitution/vision.md` (the owner's idea unchanged as its first section) and a project charter ADR on a new branch |
| `/agk:stack` | `scripts/agk/engines.py stack-ids`, `stack-write`, `stack-check` | one Proposed ADR of stack options on a new branch |
| `/agk:spec` | `scripts/agk/new_spec.py`, `scripts/agk/intake.py` | a Draft spec, or a requirement proposal with its ADR draft, or (from one sentence) a requirement, a Draft spec and an ADR stub |
| `/agk:architect` | `scripts/agk/playbook.py architect` | nothing (prints how to start `claude --agent architect`) |
| `/agk:issue` | the issue templates and your own `gh issue create`, after asking | one GitHub issue |
| `/agk:brief` | `scripts/agk/new_spec.py` | one brief |
| `/agk:review` | `review_context.py`, the project's `reviewer` subagent, `check_review_report.py` | local files, never committed |

No command commits, pushes or merges (`/agk:ruleset` and `/agk:issue` write to GitHub only after you say yes), and none sets a spec `Approved` or an ADR `Accepted`. `/agk:review` is advisory.
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

1. Leave the three versions as they are and add one line under `## Unreleased` of `CHANGELOG.md`:
   `- #<n> <one-line change>`, naming the pull request and what it changes. The shape is `kit/templates/changelog.md`.
2. Refresh the table of hashes with `python3 scripts/agk/kit_hashes.py --write` and commit it. The check of the table
   accepts a changed installed file without a bump only when `CHANGELOG.md` gained such a line.
3. If two builds change `kit/hashes.json` at once, merge or rebase the default branch and run the same one command,
   `python3 scripts/agk/kit_hashes.py --write`, then commit. A collision under `## Unreleased` is resolved by keeping both lines.

One release pull request bumps for all the builds. A session opens it on the maintainers' word; it changes only
`CHANGELOG.md` (the Unreleased lines move, unchanged and in order, under `## <new version> (<date>)`, and `## Unreleased`
is left empty), the three versions (raised together to one greater number) and the new row of `kit/hashes.json`.
`scripts/agk/check_release.py` fails a release pull request that changes any other file; the maintainers merge it and tag it.

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
