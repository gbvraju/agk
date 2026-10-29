# Security: what AGK does with your code, your credentials and your repository

One page. Every statement names the file that makes it true. Where a statement rests on a tool outside AGK, it says so. Nobody has audited
this page from outside the project; it is a description, not a certification.

## What AGK stores

Nothing outside your repository.

- **In the repository:** the files `/agk:init` or `/agk:adopt` install (list them with `init.py --dry-run`; see
  [the reference](reference.md)). AGK has no server, no database and no account.
- **On GitHub:** issues and labels. Three workflows write issues with the label shown: `agk-metrics` (`.github/workflows/metrics.yml`),
  `agk-product-report` (`.github/workflows/product-report.yml`) and `agk-drift-audit` (`.github/workflows/drift-audit.yml`). Each
  creates its own label if it is missing.
- **On your machine:** the plugin, in Claude Code's plugin folder. `/agk:review` writes local files that are never committed
  (the Experimental reviewer section of [the reference](reference.md)).

## Where your code and prompts go

AGK sends nothing anywhere itself.

- The skills and the architect role run inside **your own Claude Code session**. What that session sends to a model, and under which
  deployment, retention terms and settings, is decided by your Claude Code and its settings, not by AGK. AGK does not change
  them. Read your Claude Code and organisation terms for that; this page does not describe them `(verify)`.
- AGK's scripts import no network library. This is tested for three of them: the architect guard
  (`tests/kit/test_architect_guard.py`), the drift audit (`tests/kit/test_drift_audit.py`) and the report renderer
  (`tests/kit/test_product_report.py`, which also checks that no socket is opened). The scripts that read GitHub
  (`scripts/agk/doctor.py`, `metrics.py`, `facts.py`, `ruleset.py`) do it only by running your `gh` with `api --method GET`. Two
  scripts write to GitHub, each in one narrow way: `session.py next` posts the one `taken:` comment, and `route.py` (run by
  `.github/workflows/agk-route.yml` with the job's token) sets the `agk:` labels on pull requests (a fork's pull request gets a read-only token, so it is not labelled). Two skills can, after they show you what they will do and you say yes: `/agk:ruleset` runs the
  `gh api` commands that `scripts/agk/ruleset.py` printed, and `/agk:issue` runs `gh issue create`.
- The GitHub-hosted runner that runs the workflows is GitHub's. The workflows run your repository's checks and, in `proof` and
  `governance`, **your own tests** (`project_tests` in `agk.toml`) on a pull request's code.

## Credentials

AGK asks for none, stores none and prints none.

- **Your logins.** The skills use your own `gh` login and your own Claude login. `/agk:ruleset` says so in its first paragraph
  (`skills/ruleset/SKILL.md`), and `agk doctor` holds no credential (`docs/guides/reference.md`, the Doctor section).
- **The workflows** use only the workflow token that GitHub gives each run, `secrets.GITHUB_TOKEN`. No other secret is referenced in
  `.github/workflows/`.
- **Secrets in the repository.** The step `Secret scan` of the `governance` workflow (`.github/workflows/governance.yml`) downloads
  one pinned release of the open-source gitleaks command-line tool for linux x64 from the project's GitHub releases, checks its
  SHA-256 against the digest written in the workflow (a mismatch fails the step) and scans the commits of the change: on a pull
  request, from the merge base to the head; on a push, the pushed commits; on the first push of a repository, the whole history.
  Any finding fails the step, and the log hides the value found. It needs no licence key and no secret, on a personal or an
  organisation repository alike, and no permission beyond the job's read-only token. The archive is kept in the Actions cache,
  keyed on its version and digest, and checked against the digest on every use, so a GitHub download outage does not stop the
  scan once one run has succeeded; with no cached copy, a failed download fails the step with one line, `could not download the
  secret scanner from GitHub (HTTP <code>); re-run the job`.
- **Secrets in a session.** Principle 9 says there are none in the repository or in an agent session (`constitution/principles.md`).
  That is a rule the checks and the scan look for. It is not a wall: the architect role can read any file in the folder it is started in.

## What each workflow may write

The permissions are the ones in each file; a workflow can do nothing its token does not allow.

| Workflow | Token permissions | What it may write |
| --- | --- | --- |
| `governance.yml` | `contents: read`; `issues: read`, `pull-requests: read` and `actions: read` | nothing; it runs the checks and the secret scan, and reads the comments of the pull request with one `gh api` GET |
| `proof.yml` | `contents: read`; `checks: read` | nothing; it runs your tests on the base and on the head (event `pull_request`, never `pull_request_target`); with one read of the checks of the parent commit it skips the suite for a commit that changes only `- Status:` lines |
| `metrics.yml` | read of contents, pull requests, checks and actions; `issues: write` | one issue a week with the label `agk-metrics`, and that label |
| `product-report.yml` | read of contents, pull requests, checks and actions; `issues: write` | one issue a week with the label `agk-product-report`, and that label; then one workflow artifact, `agk-facts-<week>`, the facts file the report was rendered from and `report.json`, the same report as data, kept 90 days and readable by anyone who can read the repository's workflow runs (no anonymous download, no other place) |
| `drift-audit.yml` | `contents: read`; the `report` job, which runs the project's optional `unused_code` and `coverage` commands, `issues: read` only and no stored credentials; the `file` job, which checks nothing out and runs no project code, `issues: write` | at most one issue labelled `agk-drift-audit`, and that label |
| `agk-route.yml` | `contents: read`; `checks: read`; `statuses: read`; `pull-requests: write`; `issues: write` | one label of seven (`agk:ci-running`, `agk:ci-red`, `agk:conflict`, `agk:review`, `agk:fix`, `agk:approve`, `agk:ready`) on each pull request, and those labels if missing; no review, no merge, and no comment but one reply, `Correction needed:`, to a verdict whose `Final:` line it cannot read; it runs from a checkout of the default branch and never runs code of a pull request |
| `agk-tag.yml` | `contents: read`; `issues: write` | this kit repository's own workflow, not installed in a project: on the push of a tag `v*`, at most one plain issue `The tag <tag> is not a release` (label `agk-release`, created if missing) when the tagged commit is not a release; it deletes and moves no tag, makes no release and no commit |

To forbid issue writing, delete the three workflow files that need `issues: write` (`init.py` and `adopt.py` print this notice). Issues
must be on for those workflows to work, which `agk doctor` checks.

## Integrity of the installed checks

The checks are files in your repository: `scripts/agk/` is a protected class, so a change to one needs an ADR in the same
pull request that names it (`config/protected-paths.txt`). `agk doctor --kit-root` compares every installed file with the
kit's copy and reports a file that differs (`scripts/agk/doctor.py`), and `agk upgrade` uses `kit/hashes.json`, which holds
the SHA-256 of every file of every release, to tell a file you edited from one that is only old. Since kit 0.28.0 the
kit's own tests are not installed (a project cannot re-run them); they run in the kit's CI, and the comparison above is
what tells you your copy is the kit's.

## The architect guard, and what it cannot prevent

The architect role (`.claude/agents/architect.md`) is a Claude Code session with a short tool list and a hook
(`.claude/hooks/architect_guard.py`). The hook allows writes only under `docs/` and `constitution/vision.md`, and `Bash` only for
read-only `git` commands, `gh api` reads, one kind of comment post to the repository of the checkout, `date -u`, `make governance`
and the read-only scripts of `scripts/agk/`. It denies git options that run a program. It never merges. The review agent (`.claude/agents/architect-review.md`) has no write tool and runs the same hook as `architect_guard.py --review`, which denies every write, `docs/` included; it posts its verdict as a comment. It cannot tell which pull request a comment goes to.

It cannot prevent:

- **A session started without it.** If you start `claude` and tell it to follow the role file, only the rules of the file bind it, not
  the tool list or the hook (`skills/architect/SKILL.md` says so).
- **That the hook is active at all.** Whether the hook of a project agent runs for `claude --agent architect`, and in which folders,
  is marked `(verify)` in the files and has not yet been shown in a live run.
- **A wrong verdict or a missed finding.** The role posts what a supervised session concluded. It is not measured here and makes no
  claim to catch defects.
- **Anything you do yourself.** The permission rules in `.claude/settings.json` (no force-push, no merge command, an `ask` before
  editing protected paths) bind a Claude Code session that loads that file. They do not bind your own `git` or `gh`, another program,
  or a repository administrator, who can edit the ruleset.

## One account for every role, and what an approval proves

Many people run AGK alone, on one GitHub account that their agent sessions also use. The approver lists name logins, so on one
account an agent's `Approve:` would look like the person's. GitHub records the difference itself: a comment posted through a
GitHub App carries `performed_via_github_app`, and an agent that posts through the app can neither remove nor forge it.
`agent_apps` in `agk.toml` (a list of app slugs, default `["claude"]`; a change needs an ADR) names the apps an agent posts
through. A comment posted through a listed app never counts as a person's approval, in the router, in `check_specs.py` and in
`check_final_clearance.py`, whether a project uses one account or a separate account for each role; the router answers it once with
`Correction needed:`. A review record shows no app, so while `agent_apps` is not empty a review never counts either, and the router
asks the person once to post `Approve: SPEC-<n>` as a comment from their own account; with `agent_apps = []` reviews count as
before. The limit, stated plainly: the field exists when an agent posts through an app, as cloud sessions do. A session on a
person's own machine that uses that person's `gh` login posts with no field and looks like the person. With one account, run agents
as cloud sessions, or never give them a personal token. The first-line markers (`Verdict:`, `Report:`, `Request:`, `Assign:`) and
the session names keep roles readable; they are not proof.

## What is not covered here

Which Claude deployment options suit your organisation, data residency, and the hosting of GitHub itself are outside AGK. Report a gap in
this page with the [I got stuck form](../../.github/ISSUE_TEMPLATE/stuck.md) or `/agk:issue`.
