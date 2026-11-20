# ADR-0635: A personal change runs start, review, confirm and finish, with a read-only personal reviewer

- Status: Proposed
- Date: 2026-11-19
- Deciders: maintainers
- Related: ADR-0267, ADR-0612, ADR-0632, ADR-0634, SPEC-0041, SPEC-0005, brief #1507
- Requirements: REQ-048

Protected classes: `scripts/agk/`, `.claude/`, `.claude-plugin/`, `kit/`, `config/`, `agk.toml`, `tests/kit/`

## Context

SPEC-0041 rule 17 gives the levels per-change records: at `spec` a short spec or brief per change, confirmed at a
terminal before the change's first code commit; at `review` the review context, the reviewer agent,
`check_review_report.py` and a confirmed verdict naming the head. The gate of build (h) (ADR-0634) reads these
records, but no command makes them. Rule 29, through item 5 of amendment 113, lets the plugin ship one reviewer agent
for personal mode, advisory and experimental. ADR-0267 asks each build of the spec for its own ADR naming its
classes; this is build (i).

## Decision

1. `personal.py change start <name> [--advances REQ-nnn]` records, through `FilesForge.record_pull`, a files-forge
   pull record `forge/pulls/<n>.json` titled `change <name>` for the clone's current branch: its head from git, its
   base the default branch (`refs/remotes/origin/HEAD`, else `--base`), read-only. It is refused on the default
   branch, on a detached head and on a branch that already has a started change, each naming the rule. At the
   `spec` level and above it drafts `docs/specs/<nnnn>-<name>.md` as `Draft` in the sidecar, numbered by
   `common.next_free_ids` on the sidecar's head, commits it, and prints the `personal.py confirm SPEC-nnnn` command for
   the person.
2. `personal.py change review [--report FILE]` needs a started change. Without `--report` it builds the review
   context of the branch from the merge base to the head with the section builders of `review_context.py`: the diff
   and the changed files from the clone (read-only, the head tree written with `git archive` into the sidecar's
   `cache/trees/`), the requirements, specs, ADRs and principles from the sidecar; it writes
   `records/reviews/<head>.context.md`, commits it, and names the `personal-reviewer` agent. With `--report FILE`
   (the agent's answer) it runs `check_review_report.validate` against that context and, only when the report holds,
   writes `records/reviews/<head>.report.md`, commits it, and writes the report as a files-forge comment on the
   change's pull, always marked as an agent's (`performed_via_github_app` `claude`, rule 8), so no reader takes it as
   an approval. The review is advisory (rule 17).
3. `personal.py change confirm` is the person's verdict at a terminal: refused while `CLAUDECODE` is set and when
   standard input is not a terminal, and refused with no review report for the head. It shows three lines, asks yes
   or no, and on yes writes one files-forge comment whose lines are `Confirmed: <head>`, `Verdict: cleared <head>`,
   `Shown:` with the three lines, and `confirmed by <login> at a terminal at <time>`, the shape the gate's review step
   (ADR-0634) reads; `<head>` is the product head the gate judges. It has no `Record:` line, so
   `reviewers.terminal_confirmations` never reads it as a record's confirmation.
4. `personal.py change finish [--base REF] [--approve]` needs a started change, runs the gate of ADR-0634 unchanged
   and, only on a pass, prints the gate's `git push` line and the optional `personal.py pr-summary` command. It never
   pushes; a failing gate prints no push command.
5. `.claude/agents/personal-reviewer.md` has the tools `Read`, `Grep` and `Glob` only, names the sidecar as its root,
   never writes in the product clone or anywhere else and never confirms. It is listed in `kit/manifest.json`
   `verbatim` and in `.claude-plugin/plugin.json` `agents`, which list the same agents; `config/rule-budget.txt` gains
   its line (no rule lines). The team-mode `reviewer` is unchanged.
6. Every change command writes only in the sidecar; the product's `git status --porcelain` and every file under its
   `.git/` stay unchanged, which a test checks by path and SHA-256.

## Consequences

A developer can take one change through the steps of the level alone, and every record of it lives in the sidecar.
The reviewer agent cannot write, so the script writes its report; the kit, not GitHub, writes the agent mark, so the
mark is a label and not proof (`Q-S0041-16`).

## Residual

- 2026-11-19: item 5 of amendment 113 (SPEC-0005 rule 7: the plugin ships one reviewer agent for personal mode) is
  not applied here: an amended Approved spec needs a `## Contexts` section (amendment 142), which SPEC-0005 lacks and
  no amendment supplies, and writing one is the reviewer group's (principle 6) (`Q-1507-1`).
- 2026-11-19: where a plugin's agents live in its layout is read from the existing `plugin.json` `agents` list
  (ADR-0612 decision 1), not from the Claude Code documentation `(verify)`.
