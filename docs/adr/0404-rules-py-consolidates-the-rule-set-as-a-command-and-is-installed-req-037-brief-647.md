# ADR-0404: rules.py consolidates the rule set as a command, and is installed (REQ-037, brief 647)

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: ADR-0052, ADR-0243, ADR-0310
- Requirements: REQ-037

Protected classes: `config/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `agk.toml`

## Context

Build (a) of brief #647 (ADR-0310) gave the instruction files a budget that only shrinks and a
weekly count of the rules agents drop (`rules.py dropped`). Build (b) was a one-time cut of
`config/session-rules.md`. The owner amended it on 2026-11-10: the cut is a command, built now and
run later, and it is for projects too, not only AGK. No existing ADR covers installing `rules.py`;
ADR-0310 made it kit-only.

## Decision

1. **The plan.** `python3 scripts/agk/rules.py consolidate --plan [--root DIR] [--since DATE]
   [--repo O/R] [--api-dir DIR]` changes no file. For each rule line of the instruction files it
   prints `<file>:<line> <n> <verdict> [<check>] <count>`: `<n>` is the number of a numbered line
   (`-` for a bullet), the verdict is `keep`, `retire <check>` or `guide`, and the count is the
   number of fix-list items tagged `(rule: <file> <n>)` since DATE, read as `rules.py dropped`
   reads them (`-` without `--since`: never 0 for unread). It ends with `before:` and `after:`
   (words and rule lines of the files, and the rules in force) and `plan: <hash>`.
2. **Where the verdicts come from.** The command does not judge a rule. A verdict other than
   `keep` comes from a line of `config/rule-plan.txt`: `<file> <n> retire <check>` or
   `<file> <n> guide`. A `retire` names its check as a path that must exist under the root
   (verified by name); a line that names a missing check, a file outside the list, a number that
   is not one numbered line of its file, or another verdict is refused naming the plan file, and
   `--plan` exits 1. The plan file is under `config/`, so filling it is a reviewed, protected
   change. This build ships it with no entries: no rule is retired or moved by the build itself.
3. **The apply.** `rules.py consolidate --apply --hash <hash> [--root DIR]` writes that plan into
   the working tree: a retired line becomes `<n>. Retired: enforced by `<check>` (rules.py
   consolidate).`, a guide line becomes `<n>. Moved to `docs/guides/session-how-to.md` (rules.py
   consolidate).` and its text is appended to that guide under a heading naming the file and
   number, each retired rule appends one line to the catch log `docs/runs/rules-retired.md`
   naming its check, and the lines of `config/rule-budget.txt` are rewritten to the new counts.
   Numbers are kept (a pointer line, as `config/session-rules.md` already does for merged rules),
   so a `(rule: <file> <n>)` tag keeps its meaning. It refuses, naming the rule, when the hash is
   not the plan's hash now ("the plan has changed since --plan") or when `git status --porcelain`
   prints anything ("the working tree is dirty"). It never commits, pushes or opens a pull request;
   the change reaches the default branch through an ordinary pull request.
4. **The list of files.** `[rules] files` in `agk.toml` lists the instruction files as paths or
   globs (`.claude/agents/*.md`), in order; without it, AGK's list of ADR-0310 decision 1. A value
   that is not a list of strings is refused naming the setting. `budget`, `dropped` and
   `consolidate` read the same list.
5. **Installed.** `scripts/agk/rules.py` joins the verbatim set of `kit/manifest.json` and leaves
   `KIT_ONLY`; its imports (`common.py`, `metrics.py`, `reviewers.py`) are already installed. The
   kit's tests stay kit-only (ADR-0052, lean install), so the budget test is not installed; a
   project runs `rules.py budget --check` after writing its own `config/rule-budget.txt` from
   `rules.py budget`. The template `agk.toml` carries the `[rules]` table commented out.
6. **When it runs.** Q-647-3 stands: on AGK, `--apply` is run only after 2026-11-13T13:22Z and only
   on the owner's word. No rule's meaning changes here.

## Consequences

A project cuts its own rule set by the same command, from its own counts. Filling the plan file is
the decision, reviewed like any `config/` change; the command only carries it out and keeps the
budget, the guide and the catch log in step.

## Residual

- 2026-11-10: the must-list is the pointer form of decision 3, not a rewrite of each kept rule into
  one sentence; a shorter wording of a kept rule changes its text, so it is its own brief (due
  2026-12-31).
