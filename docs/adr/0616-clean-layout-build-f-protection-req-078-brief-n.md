# ADR-0616: Clean layout build (f): the doctor warns of kit files in a clean project and the steward never writes kit code into it

- Status: Proposed
- Date: 2026-11-18
- Deciders: maintainers
- Related: brief #1458, SPEC-0071 rules 2, 7 and 12 (f), ADR-0611, ADR-0613, ADR-0596, Q-S0071-3
- Requirements: REQ-078

Protected classes: `scripts/agk/`, `.claude/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0071 rule 7 limits what a clean project (`[kit] layout = "plugin"`, ADR-0611) exposes: the kit runs from the
plugin, so a kit file found in the product is a leak, the steward must not write one there, and the licence grant's end
date is said at a session's start. Before this build nothing warned of a kit file in a clean project. The steward's
guard did not look at the paths it wrote, and the grant's `valid_until` warning (ADR-0596) was printed only by a
full doctor run, which a session does not make at start.

## Decision

1. `doctor.py` prints one line `warn kit-in-repository: ... (path class: <classes>)` in a clean project when a file of
   the plugin's kit manifest is in it. The manifest's files are the `verbatim` and `experimental` lists, and any file
   under its `kit_tests` folder. Rule 2's kept files do not count: `.gitignore`, `CLAUDE.md`, `LICENSE-AGK`, the pull
   request template and the files under `.github/ISSUE_TEMPLATE/`. A class is the file's folder with a trailing `/`, or
   the file's name at the top level. The line never names a file in a folder and never quotes content. A plugin
   manifest that cannot be read gives one `cannot be checked` line naming `kit/manifest.json`. The manifest is
   `--kit`'s when given, else the one of the plugin `doctor.py` runs from. The line is a warning: no exit code changes.
2. `doctor.py --paused` is a session's first command (session rule 33, ADR-0613 decision 2). When agk.toml holds a
   `[licence]` table, it prints the `valid_until` line of `licence_lines` (ADR-0596) to stderr after the grant ends.
   Its one stdout line and its exit code are unchanged, so it never stops work (Q-S0071-3). With no `[licence]` table
   it adds nothing at start. The full doctor run keeps ADR-0596's warning of a missing grant.
3. In a clean project `steward_guard.py` denies a write of a kit manifest path (decision 1's list) into the product,
   naming `SPEC-0071 rule 7` and the path class. A write is either a write tool (`Edit`, `Write`, `MultiEdit`,
   `NotebookEdit`) or a Bash command that is not a read (`cat`, `ls`, `head`, `tail`, `grep`, `rg`, `wc`, `diff`,
   `stat`, `git`, `gh`) and names such a path as a word or a redirection target. The manifest is the one of the plugin
   the guard runs from. When it cannot be read, the write tools are denied (fail closed) and Bash is not checked
   for this rule.
4. The steward's role file (`.claude/agents/steward.md`) says that the steward never pastes kit code into an issue, a
   pull request, a comment or a file of the product.

## Consequences

An installed project, the kit's own repository and personal mode are unchanged: each part returns at once without
`[kit] layout = "plugin"`. No workflow, ruleset or required check changes, and nothing reads the network. The Bash check
is word based, so a non-read command that only names a kit path, such as `echo Makefile`, is also denied in a clean
project. That costs little, since such a product should hold no kit path. `.claude/settings.json` is not among the kept
files until build (b) shows it is needed (Q-S0071-6), so the doctor warns of it and the guard denies it.

## Residual

- 2026-11-18: the guard's Bash check reads words, not the shell's meaning, so a write through an interpreter's own code
  or a variable that names a kit path is not caught. Rule 7 says this protection limits exposure and does not make it
  impossible. To review with build (g)'s rehearsal (due 2027-01-31).
