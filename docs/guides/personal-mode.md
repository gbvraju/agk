<!--
SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
SPDX-License-Identifier: LicenseRef-AGK-Proprietary
AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
-->
# Personal mode: one developer, nothing of AGK in the product repository

Personal mode lets you use AGK on your own, on a project where the team has not adopted it. AGK reads the code, drafts
the decisions already in it for you to confirm, and keeps specs, reviews, gates and evidence in a private folder on your
machine. Nothing of AGK goes into the product repository or onto its GitHub. The rules are SPEC-0041; a recorded walk
of every step below is in [the personal-mode walk](../runs/personal-mode-walk.md).

## When to use it

Use it when you want AGK's tests-first gate and records, and the team does not use AGK, or not yet. When the team wants
AGK too, export your records to team mode (below). If the clone already has AGK installed (an `agk.toml` with a kit
`version`), `attach` refuses and points you to team mode.

## Install at user scope

Personal mode ships in the AGK plugin, installed for your user, not for the project:

```
claude plugin marketplace add gbvraju/agk
claude plugin install agk@agk --scope user
```

(verify: the install command and scope flag.) Every script runs from the plugin's folder, `${CLAUDE_PLUGIN_ROOT}`; the
commands below write `python3 personal.py` for `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/personal.py"`. The state
records the plugin version, never a script.

## Attach

From the product clone:

```
python3 personal_state.py id
python3 personal_state.py attach --person <your login>
```

`personal_state.py id` prints the project id, `<folder>-<12 hex>`. `attach` makes the state folder `AGK_HOME` (default
`~/.agk`, `%USERPROFILE%\.agk` on Windows) and, under `projects/<id>/`, the sidecar: a private git repository with the
kit's layout (`agk.toml`, `constitution/`, `config/`, `docs/`, `forge/`, `records/`, `metrics/`, `test-map.toml`).
Every worktree of one clone finds the same sidecar. When a second clone yields an id already registered, `attach` asks
you to choose, and `--share` (use that sidecar) or `--new` (a new one) answers it. `--clone DIR` names a clone other
than the current folder, for every command here, and `--sidecar DIR` names the sidecar when it is not the clone's.

## Survey and adopt

```
python3 survey.py
```

`survey.py` reads the clone's tracked files without running anything, ranks them and writes the reading list and a
ledger to `cache/inventory.json` in the sidecar; it prints the coverage, `<n> of <m> files read`. Then, in Claude Code,
run `/agk:personal-adopt`: the model reads only the reading list and writes its proposals as JSON in the sidecar's
`cache/`, each claim cited as `path:start-end@blob`. The skill runs `personal_adopt.py check`, and after you agree,
`personal_adopt.py render`, which writes requirements as `planned`, specs as `Draft` and ADRs as `Proposed` in one
sidecar commit. A claim without a citation that exists in the product is refused.

## Confirm at your own terminal

Nothing rendered counts as decided until you confirm it, yourself, at a terminal:

```
python3 personal.py confirm REQ-101
```

`personal.py confirm <REQ-nnn|SPEC-nnnn|ADR-nnnn>` shows three lines and asks yes or no. On yes it moves a spec to
`Approved` or an ADR to `Accepted`, records the confirmation in the sidecar's `forge/` and commits. It is refused in an
agent session (`CLAUDECODE` set) and when standard input is not a terminal: the agent drafts, you decide.

## The levels and the floor

`[personal] level` in the sidecar's `agk.toml` picks what the gate asks for:

- `light` (the default): the floor only.
- `tests-first`: the change's tests fail on the base and pass on the head.
- `spec`: and a spec confirmed at a terminal before the branch's first commit.
- `review`: and a review report by the read-only `personal-reviewer` agent with your terminal verdict on the head.
- `evidence`: and the gate record passes the evidence check.

The floor runs at every level and no setting removes it: the secret scan (gitleaks over the branch's commits; a
missing gitleaks fails) and no test that passed on the base fails on the head. First record the tests already failing:

```
python3 personal.py baseline
python3 personal.py baseline --approve
```

`personal.py baseline` prints the test command it would run (`test_command`, else the one the survey found) and runs it
only with `--approve`, on a copy of the head tree in the sidecar's `cache/trees/`. Put `{junit}` in `test_command` to
judge test by test. `personal.py floor --base REF --approve` runs the floor alone.

## A change from start to finish

On your own branch of the product:

```
python3 personal.py change start <name> --advances REQ-101 --base main
python3 personal.py change review --report <file> --base main
python3 personal.py change confirm
python3 personal.py change finish --base main --approve
```

`personal.py change start` records the branch in the sidecar (refused on the default branch) and, at `spec` and above,
drafts the change's spec. Write the tests first, then the code, and commit as you always do. `personal.py change review`
writes the context for the `personal-reviewer` agent and, with `--report`, keeps its report. `personal.py change
confirm` is your verdict on the head, at a terminal. `personal.py change finish` runs the gate; `personal.py gate --base
REF --approve` runs it alone. On a pass it prints `git push origin <branch>` for you: the agent never pushes. An opt-in
hook runs the gate before each of your pushes:

```
python3 personal.py hook install
python3 personal.py hook remove
```

`personal.py hook install` writes `.git/hooks/pre-push`, the one file personal mode ever writes under `.git/`, and only
when you ask; `personal.py hook remove` removes it only when it is unedited.

## pr-summary and disclosure

`personal.py pr-summary` prints, and never posts, a plain description for the team's pull request: the secret scan, the
tests, the proof and the review as the gate record says, with no REQ, SPEC or ADR id unless `team_refs = true`.
`personal.py status` prints the mode line and the disclosure in force. AI use is always disclosed: `ai_disclosure` is
`commit-trailer` (the gate warns of a commit without a `Co-Authored-By:` trailer), `pr-note` (the summary ends with a
disclosure line) or `both`, the default. There is no value that hides it, and AGK never strips or rewrites a trailer.

## Report

`personal.py report` prints, for one ISO week (`--week YYYY-Www`, else this week), the defects the floor caught before
a push and each local branch pushed with no gate record. The figures not yet measured print `unknown`, never a guess,
and the report says that they show correlation, not causation.

## Export to team mode

```
python3 personal.py export --target ../team-clone
python3 personal.py export --target ../team-clone --write
python3 personal.py export --check
```

`personal.py export --target CLONE` is a dry run that prints each record's new id. With `--write` it writes, on a new
branch of the target (`--branch NAME`, default `agk/personal-export`; never the default branch), the records renumbered
past the target's ids with statuses reset to `planned`, `Draft` and `Proposed`, and a second branch of test markers.
Field notes stay out unless `--with-notes`. Nothing is pushed; the `gh issue create` lines are printed for you.
`personal.py export --check` fails unless every record is mapped or withheld with a reason.

## Upgrade and detach

`personal.py upgrade` raises the sidecar's `schema` to the plugin's, one commit per step, and refuses a newer one.
`personal_state.py detach` removes the registry entry and the unedited hook and keeps the state; `--delete-state`
deletes the sidecar too, after you type its id at a terminal. Run `export` first if the team should keep the records.

## Settings

The `[personal]` table of the sidecar's `agk.toml`; a key not listed here is refused, naming the key.

| Key | Meaning |
| --- | --- |
| `forge` | Must be `"files"`: records are files in the sidecar's `forge/`, never on GitHub. |
| `level` | The gate's level, above; `light` by default. |
| `ai_disclosure` | `commit-trailer`, `pr-note` or `both` (the default). |
| `survey_budget` | Files the survey reads a pass, 1 to 1000; 40 by default. |
| `quote_lines` | Lines of code a record may quote, 0 to 20; 0 by default, so no excerpt is kept. |
| `sync_remote` | Accepted and not yet used: no command sends the state anywhere. |
| `test_command` | The test command of the baseline, the floor and the gate; `{junit}` marks a JUnit report path. |
| `sign` | `true` signs the sidecar's commits with your own key and git identity. |
| `team_refs` | `true` lets AGK ids appear in your commits and the summary; off, the gate warns of them. |
| `schema` | The state's schema, raised only by `upgrade`. |
| `plugin_version` | Written by `attach`; the version whose pinned law the sidecar is checked against. |

## Limits

- Nothing in the clone: no command but `hook install` and `export --write` (on the target) writes in a clone or under its
  `.git/`, and the walk checks it by path, size and SHA-256.
- No conductor, router, workflows, ruleset, CODEOWNERS or scheduled report: each is a team-mode tool.
- The agent never pushes to a remote of the product, never confirms and never strips attribution.
- There is no `sync`: the state stays on this machine, and `/agk:personal push` is not a command yet; use
  `personal.py gate` or the hook.
- In the files forge the agent mark on a comment is written by the kit, so it is a label, not proof.
- Security: what stays on the machine is in [the security guide](security.md).
