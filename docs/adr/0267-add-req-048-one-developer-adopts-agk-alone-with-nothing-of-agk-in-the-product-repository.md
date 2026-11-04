# ADR-0267: Add REQ-048: One developer adopts AGK alone with nothing of AGK in the product repository

- Status: Accepted
- Date: 2026-11-04
- Deciders: maintainers
- Related: SPEC-0041, SPEC-0002, SPEC-0003, SPEC-0005, SPEC-0007, SPEC-0010, SPEC-0012, ADR-0179, ADR-0186, ADR-0208, ADR-0213
- Requirements: REQ-048

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-04:

> One developer adopts AGK alone, on any project, with nothing of AGK in the product repository or on its GitHub: AGK reads the code, drafts the decisions already in it for the developer to confirm, and keeps specs, reviews, gates and evidence in the developer's own private state, until the team chooses team mode.

The brief is issue #536; the conductor reserved REQ-048, SPEC-0041, this ADR number and proposed
spec amendment 113 for it (the field note on #536). The owner's direction of 2026-11-04, quoted as
data and recorded as one row of `docs/runs/decisions-log.md`: "In a 10 member team, if I would
like to use locally instead of pushing to GitHub or not forcing everybody to use, how can I use
... This will be the one to adopt by reading all code and create required decisions locally and
work personally. Anybody, any project adoption by single developer ... we need to build this with
great quality and perfection." The brief adds that the customer allows Claude and Claude plugins,
and that AI use is never hidden: attribution follows the project's policy, visibly, and AGK never
strips it.

Today every route into AGK writes into the product repository: `/agk:init` and `/agk:adopt`
install about 50 files (SPEC-0001, SPEC-0002), the law lives vendored in the repository
(SPEC-0005 rule 1), tests carry `REQ-nnn` markers (principle 10), and reviews, verdicts and
approvals are GitHub comments read by `metrics.py`, `facts.py`, `check_specs.py` and
`check_final_clearance.py`. A developer in a team that has not chosen AGK cannot use it without
asking the team to accept those files. "Local mode" (`docs/guides/local-mode.md`, ADR-0213) and
`execution = "local"` already mean something else: GitHub Actions is blocked and the checks run
on a machine instead.

## Decision

1. REQ-048 is added to `docs/requirements.md` as `planned`. SPEC-0041 is added as `Draft`. Merging
   this pull request approves the requirement as a proposal; it does not approve the spec, which
   stays `Draft` until the owner's own `Approve:` line approves it (SPEC-0032 rule 5).
2. The mode is named "personal mode", with a file-backed forge, `forge = "files"`. Neither name
   reuses "local" (SPEC-0041 rule 1).
3. Personal state lives outside the product, in a private sidecar git repository under
   `AGK_HOME` with the kit's own layout, so the existing file checks run on it unchanged; nothing
   is written in the clone, not even under `.git/`, except the one opt-in pre-push hook that the
   person installs by name (SPEC-0041 rules 2 to 5 and 19).
4. GitHub's role is played by files: `scripts/agk/forge.py` puts the existing GitHub readers behind
   one interface and adds a file-backed one, and `personal.py api-view` renders the file names
   that the existing `--api-dir` readers already read, so `facts.py`, `metrics.py` and
   `check_final_clearance.py` read personal state without change. A comment that an agent session
   writes is marked as an agent app's, so the existing `agent_apps` rule (ADR-0179 decision 3)
   refuses it as an approval, and the person's confirmation is refused inside an agent session
   (SPEC-0041 rules 6 to 9).
5. Adoption reads the code without running it, drafts the decisions already in it only with
   citations that exist, and lets the person confirm each from their own terminal; nothing is
   written into the customer's tests (SPEC-0041 rules 10 to 16).
6. Five governance levels share one floor that no setting lowers: the secret scan, and no test that
   passed on the base fails on the head (SPEC-0041 rules 17 to 19).
7. The agent never pushes to the customer's remote, commits carry nothing of AGK unless the
   developer opts in, and AI use is disclosed by the project's policy with no `none` value and no
   stripping (SPEC-0041 rules 20 to 22).
8. Personal mode measures itself on demand and exports losslessly to team mode (SPEC-0041 rules 23
   to 25); it is packaged as a user-scope plugin whose scripts are never stored in state
   (SPEC-0041 rules 26 and 27), with the security rules of SPEC-0041 rule 28.
9. The rules that conflict with personal mode change only through
   `docs/runs/proposed-spec-amendments-113.md` and the builds that apply it: principle 10, SPEC-0005
   rules 1, 2, 7 and 8 (rule 8: a personal-mode command commits only to the sidecar, and only the
   person's own terminal `confirm` sets a sidecar spec `Approved` or ADR `Accepted`, never in the
   product repository; amendment item 6), two guides and a new session rule (SPEC-0041 rule 29).
   This pull request applies none of them.
10. The builds (b) to (n) of SPEC-0041 rule 30 will change these protected path classes:
    `constitution/` (principle 10, build (b)), `config/` (the new session rule 36 and one line of
    `config/core-rules.md` in build (b); `config/protected-paths.txt` and `config/reviewers.yaml`
    only if build (i) adds a new plugin folder to the protected list), `scripts/agk/`
    (`personal_state.py`, `forge.py`, `personal.py`, `survey.py`, `personal_adopt.py`, new, and
    `common.py`, `reviewers.py` (`terminal_confirmations`, build (g)), `check_specs.py`,
    `check_adrs.py` and `check_requirements.py` (their sidecar `--comments` readings, build (g)),
    `prepush.py`, `proof.py`, `metrics.py`, `doctor.py` and `upgrade.py`), `kit/`
    (`kit/templates/personal.toml` and the other sidecar templates, and `kit/manifest.json`; never
    `kit/hashes.json`, session rule 14), `skills/` (`/agk:personal` and `/agk:personal-adopt`),
    `.claude-plugin/` (user-scope packaging, build (l)), `.claude/` (only if the personal reviewer
    agent is placed under `.claude/agents/`, build (i)), `tests/kit/` and `tests/kit_dev/` (their
    tests). Each build adds its own ADR naming the classes it changes and citing this one, because
    the protected-path check counts only an ADR added or changed in the same pull request. No build
    changes `.github/`, `agk.mk`, `Makefile`, `pyproject.toml`, `CLAUDE.md` or the ruleset files
    unless its own ADR says why, and no build bumps the version (flow mode, SPEC-0028).
11. Builds (b), (i) and (l) are merged by the owner by hand: (b) changes `constitution/`, (i) ships
    a reviewer agent in the plugin, and (l) changes what a user installs.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. No check, flow,
setting or installed file changes in this pull request, and a project that never attaches personal
mode sees no change from any build: team mode, local mode and solo mode keep every rule they have.
A developer who attaches personal mode gets AGK's discipline without asking the team for anything,
and the team can later take the records over by export.

## Residual

None beyond SPEC-0041's residual. The intake checks cannot tell whether the rules, the levels or the
floor are the right ones; that is the review of this pull request.
