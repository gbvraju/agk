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

## Existing scanners

Project-wide scanners (bandit, flake8, pylint, mypy) that read the whole tree also read the kit's code. The kit's
subprocess calls carry justified `# nosec` comments and its type findings are fixed, so what remains for bandit is
the bare `assert` of the kit's tests (rule B101). Init and adopt print the exclusions below after a run and write
none of them (ADR-0010, `docs/runs/scanner-fix.md`):

```
Scanner exclusions (print only; the kit writes none of this). The kit's code under scripts/agk, tests/kit and
.claude/hooks is the kit's, not yours. If a scanner you run reads the whole tree, exclude those paths in your own
configuration:
  bandit:  bandit -r . -x ./scripts/agk,./tests/kit,./.claude/hooks
  flake8:  flake8 --extend-exclude scripts/agk,tests/kit,.claude/hooks
  pylint:  [tool.pylint.main] ignore-paths = ['^scripts/agk/.*$', '^tests/kit/.*$'] and ignore = ['.claude']
  mypy:    [tool.mypy] exclude = ['^scripts/agk/', '^tests/kit/', '^\.claude/hooks/']
```

Licence: Apache-2.0.
