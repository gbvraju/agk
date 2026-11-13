# ADR-0505: A workflow proposal is applied by one owner command

- Status: Proposed
- Date: 2026-11-13
- Deciders: maintainers
- Related: ADR-0499, ADR-0271, brief #1189, plan #661
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `skills/`, `agk.toml`, `kit/`

## Context

A session never changes a workflow file, and the cloud refuses a push that touches `.github/workflows/`, so each
workflow change of a brief goes out as a `Question: Q-<N>-n for the maintainers:` with a diff or a replacement text,
and the owner pastes the file into GitHub's web editor on the branch. On 2026-11-12/13 that happened at least five
times (#1131, #1167, #1178, #1182 and the governance change of #1126); each needed the full file built from the
branch, a parse check and a byte-for-byte check after the owner's commit, and twice a paste from a phone was cut short.
Projects follow the same rule, so every project's workflow change has the same manual path.

## Decision

1. **The builder's side.** A builder that needs a change to `.github/workflows/<name>.yml` commits the whole proposed
   file at `.agk/workflow-proposals/<name>.yml` on its branch (a path the cloud accepts), then posts its
   `Question: Q-<N>-n for the maintainers:` naming the command `/agk:workflow-apply <pr>`.
2. **The command.** `/agk:workflow-apply <pr>` (`skills/workflow-apply/SKILL.md`) runs the plugin's own
   `scripts/agk/workflow_apply.py --pr <n>` on the owner's machine with the owner's own `git` and `gh`. It reads the
   pull request (GET), refuses one that is not open, comes from a fork or whose head is the default branch, fetches the
   head branch into a temporary worktree, lists each `.agk/workflow-proposals/<name>.yml` with its target
   `.github/workflows/<name>.yml`, refuses a proposal that does not parse or names no `jobs`, prints the diff against
   the branch's current workflow and stops (a dry run). With `--yes` it also needs the newest
   `Question: Q-… for the maintainers` comment that names the command; it moves each proposal into place, deletes the
   proposals folder, commits `workflow: apply the proposal of #<n> (<Q id>)` on the branch, checks the committed files
   byte for byte against the proposals, pushes a fast-forward of the fetched head to the head branch (never a
   force-push, never the default branch; a branch that moved since the pull request was read is refused), and posts
   one comment `Answer: <Q id> done: <commit> applied by /agk:workflow-apply`. What it cannot do it prints and never
   does: a push refused for lack of the workflow permission names `gh auth refresh -s workflow`. In personal mode (a
   `[personal]` table) there are no pull requests: it says so and exits.
3. **The parse check** is the kit's standard library only (ADR-0001 decision 4): a structural check of the YAML
   subset a workflow uses (block mappings and lists, quoted and flow scalars, block scalars, no tab in an indent,
   balanced quotes and brackets) and a top-level `jobs:` mapping with at least one job. It is a guard against a cut or
   broken file, not a full YAML parser; GitHub's own parse on the push remains the last word.
4. **A leftover proposal blocks the merge.** `check_protected_changes.py` fails, on a pull request, while the head
   tracks a file under `.agk/workflow-proposals/`, with `apply it with /agk:workflow-apply <pr>`, whatever ADR the
   change set carries, so a proposal never reaches the default branch. The message names the path class, never a value.
5. `workflow_apply.py` is kit-only: the skill runs the plugin's copy, so it is not installed in projects. The session
   rules and the builder prompts are the owner's text and are unchanged here.

## Consequences

A workflow change reaches the branch without copy and paste: the owner reads one dry run, runs it again with `--yes`,
and the question is answered on the pull request with the commit. The owner's token needs the `workflow` scope; the
command never asks for it, it prints the refresh. Every project gets one more governance refusal.

## Residual

- 2026-11-13: the parse check is a subset check, so a file it accepts can still be refused by GitHub's own parser
  after the push; GitHub then fails the workflow run and the owner sees it on the pull request (due 2027-01-31).
