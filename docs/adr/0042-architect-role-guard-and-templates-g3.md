# ADR-0042: the architect role, its guard hook, the playbook templates and the state-of-a-pull-request line (SPEC-0013 rules 6 to 17), kit 0.22.0

- Status: Proposed
- Date: 2026-10-19
- Deciders: maintainers
- Related: ADR-0020, ADR-0021, ADR-0040, ADR-0041
- Requirements: REQ-020

Protected classes: `.claude/`, `CLAUDE.md`, `scripts/agk/`, `skills/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`

## Context

G3 of the four-part build of SPEC-0013 (ADR-0040, ADR-0041). G4 is `/agk:start` and the existing-codebase path (rules 1 to 5). Rule 18 (the weekly report's
"At risk" line for a pull request merged before its head was cleared, an amendment of SPEC-0011) and rule 28 (the proof of criterion g) are not in G1 to G4;
rule 18 is flagged in the pull request body for the maintainers to place.

## Decision

1. **The role** (rules 6, 8, 13): `.claude/agents/architect.md` (installed, verbatim): `tools: Read, Grep, Glob, Edit, Write, Bash`, a `PreToolUse`
   hook in its frontmatter, and the instructions of rule 8 (write decisions as files; review each pull request against the Approved text by reading with
   `gh api` GET and never executing its code; the verdict convention; record every ruling in the notes' `## Rulings`, the decisions log and the changed
   text; never write outside `docs/` and `constitution/vision.md`; never merge; never post `Verdict: cleared` on a pull request it authored; never set `Approved`
   or `Accepted` except in a final commit a person orders; claim nothing about catching defects). It is started with `claude --agent architect`.
   **Verified here:** `claude --help` (version 2.1.303) lists `--agent <agent>` ("Agent for the current session"); the documentation (code.claude.com
   sub-agents and hooks pages, read 2026-10-19) shows `hooks:` in agent frontmatter, that those hooks run when the agent is the main session through
   `--agent`, that a project agent's frontmatter hooks run only after the folder is trusted, and both denial forms of a `PreToolUse` hook. **Still `(verify)`:**
   that the trust rule is worded for the `--agent` main session, and the `tool_input` keys of `Edit` and `Write` beyond `file_path` (the guard reads only
   `file_path`, and `notebook_path` for `NotebookEdit`).
2. **The guard** (rule 9): `.claude/hooks/architect_guard.py` (installed, verbatim; standard library only, no network, no subprocess) denies
   `Edit`, `Write`, `MultiEdit` and `NotebookEdit` outside `docs/` and `constitution/vision.md` (the real path decides: `..`, a symlink out and a prefix such as
   `docsx/` are denied), and `Bash` unless the command is a simple command of: a read-only `git` subcommand (`branch` only to list); `gh api` with `--method GET` or
   no method and no field or input flag, on a `repos/` endpoint; `gh api --method POST` to the comments of an issue or pull request with `-f` fields only;
   `date -u`; `make governance`; or a read-only script of `scripts/agk/` (a listed set; `proof.py`, which runs a checkout's tests, is not on it). Shell operators,
   redirections, substitutions, `$` and backticks are denied. A denial is JSON on stdout (`permissionDecision: deny`) with a reason that names the rule and
   never the command or the path. A broken payload is denied. `tests/kit/test_architect_guard.py` (installed) runs a table of 40 allowed and denied paths and
   about 60 commands.
3. **The skill `/agk:architect`** (rule 7) runs `playbook.py architect`, which prints the start command and checks read-only that `agk.toml` is present, that `gh`
   is logged in and which branch is the default; in a session that cannot be started that way it points to the role file and says the tool list and the guard are not
   enforced there. `SPEC-0005` rule 8 gains its row (`proposed-spec-amendments-24.md` item 2; the `architect` part of item 1 of `-15`).
4. **The templates** (rules 14, 15) in `kit/templates/playbook/` (kit-only): `brief-overnight.md`, `brief-day.md`, `rulings-table.md`, `verdict.md`,
   `live-proof-plan.md`, `held-out-findings.md`, `pilot-week-record.md`; tests check headings in order, table columns, the closed placeholder set, the
   absence of a literal pull request, ADR, requirement or spec number and of the GraphQL command, the three sentences and the state command of the briefs'
   rules block, and that the first line of `verdict.md` matches `metrics.VERDICT`.
5. **`playbook.py brief`** (rule 16, kit-only): prints a brief skeleton with the next requirement, ADR and spec numbers read from `origin/<default branch>`
   (`common.next_free_ids`), the repository from `origin` (or `--repo`), the default branch from `agk.toml`, and branch names `<prefix>/<slug>`; it never writes a
   pull request number (`{{n}}` stays in the printed state command as the placeholder the session fills at run time). It refuses a bad kind or prefix and
   fails when the ref does not resolve.
6. **`CLAUDE.md` gains one line** (rule 17): "Check the state of a pull request with `gh api repos/{owner}/{repo}/pulls/{n}` (a GET); the GraphQL form of the command is
   blocked in cloud sessions." **Amended** (`proposed-spec-amendments-24.md`, applied here): the spec's own wording named the command it forbids in the same file
   (Q-K4-181).
7. **Kit 0.22.0**: manifest (the agent file, the hook and the installed test), hashes, plugin version.

## Consequences

- A repository that installs the kit 0.22.0 gets the role and its guard; a session started with `claude --agent architect` in a trusted folder cannot write code,
  merge or comment outside the verdict convention through the tools it has. A person is still needed for everything in rule 9's second list.
- The playbook templates exist and parse before `/agk:start` (G4) uses the brief skeleton.

## Questions

| Q | Question | Reading taken |
| --- | --- | --- |
| Q-K4-181 | Rule 17 requires a `CLAUDE.md` line that names `gh pr view` and a test that fails when `gh pr view` appears in `CLAUDE.md`. | Keep the test; reword the line so it does not name the command (amendment 24 item 1). |
| Q-K4-182 | Rule 7 says the skill is "user-invoked"; amendment 15 item 1 says it "reads and writes nothing" and keeps it out of rule 9's list of commands with model invocation off. | A reader like `doctor` and `review`: no `disable-model-invocation`. A person types it either way. |
| Q-K4-183 | The exact list of what the guard allows for `Bash` (rule 9 names five forms). | The five forms, plus `date -u` (dates come from it, CLAUDE.md rule 6); `git branch` only to list; the read-only script set in the hook; anything with an operator, substitution or `$` is denied. |
| Q-K4-184 | The brief skeleton keeps `{{n}}` and `{{sha}}` unfilled; rule 16 says no number is written in advance. | Yes: `{{n}}` is the placeholder for the pull request the session opens. |

## Residual

- 2026-10-19: the guard limits writes by path and `Bash` by command pattern; an allowed `gh api` GET can still read anything the login can (SPEC-0013 residual, due 2027-01-31).
- 2026-10-19: the `(verify)` items of Decision 1 (trust rule for `--agent`; `Edit` and `Write` payload keys) are confirmed by a live run of `claude --agent architect` in a
  trusted folder, a maintainers' step with the sessions' help (due 2026-11-30).
- 2026-10-19: rule 18's "At risk" line (amendments-15 item 3, SPEC-0011) is built by none of G1 to G4 (due 2026-11-30).
