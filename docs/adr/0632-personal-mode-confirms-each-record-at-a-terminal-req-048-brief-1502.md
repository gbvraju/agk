# ADR-0632: Personal mode confirms each record at a terminal, and the sidecar's readers accept only that

- Status: Proposed
- Date: 2026-11-18
- Deciders: maintainers
- Related: ADR-0267, ADR-0179, ADR-0426, SPEC-0041, brief #1502
- Requirements: REQ-048

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0041 rules 8 and 15 ask that nothing rendered in a sidecar counts as decided until the person runs
`personal.py confirm <id>` at their own terminal, and that the sidecar's readers accept only that confirmation, never an
agent's. On main `personal.py` offered `baseline`, `floor` and `report` only; `reviewers.confirmed_comments` reads the
solo confirmation of a session (`confirmed by <login> in a session at <time>`, ADR-0179) and nothing else; and
`check_adrs.py` and `check_requirements.py` had no reading of comments for a sidecar. ADR-0267 asks each build of the
spec for its own ADR naming its classes; this is build (g), part 1 (the terminal `confirm` and the readers).

## Decision

1. `personal.py confirm <REQ-nnn|SPEC-nnnn|ADR-nnnn> [--sidecar DIR]` is refused while `CLAUDECODE` is set
   (`local_mode.SESSION_SETTING`), when standard input is not a terminal, and when the sidecar's work tree is not
   clean, each refusal naming the setting or the rule. It shows three lines (the record and its title, its file at
   `<C>`, the status move), asks yes or no, and on anything but yes writes nothing. `<C>` is the sidecar's `HEAD` when
   `confirm` starts.
2. On yes it writes, under the files forge's lock and without its per-write commit, `forge/pulls/<n>.json` (head
   `<C>`, title `confirm <id>`, a body that says what the record proves) and `forge/comments-<n>.json` holding the one
   confirmation of rule 8 in its order, ending `confirmed by <login> at a terminal at <UTC time>`; moves a spec's
   status line to `Approved` or an ADR's to `Accepted` (a requirement's status does not move); runs the kind's reader
   with `--base <C>` and `--comments forge/comments-<n>.json`; and only when the reader exits 0 makes one commit, the
   child of `<C>`, of the status line and the two forge files. Otherwise it restores the work tree to `<C>`, commits
   nothing and exits 1 naming the reader. With `[personal] sign = true` the commit is signed (`git commit -S`) with
   the person's own key; off by default.
3. `reviewers.terminal_confirmations(comments, agent_apps, person)` returns the comments with, after each terminal
   confirmation of rule 8's exact shape by the one listed person and not marked with an app of `agent_apps`, one
   derived comment `Approve: <C> SPEC-nnnn`, `Accept: <C> ADR-nnnn` or `Confirm: <C> REQ-nnn`, only where `Record:`
   and the next line name the same id. `reviewers.confirmed_comments` and its patterns are unchanged, so neither
   reader reads the other's confirmation (ADR-0179 decision 3 stands: an agent-marked comment is never an approval).
4. In a sidecar only (a `[personal]` table in `agk.toml`): `check_specs.py --comments` takes as approvals only the
   derived lines of `terminal_confirmations`, not the plain comments; `check_adrs.py --comments FILE` fails an ADR whose
   status line moves to `Accepted` without an `Accept: <C> ADR-nnnn` line at a `<C>` of the head's history where the
   ADR equals its text apart from its status line; `check_requirements.py --comments FILE` fails a requirement with a
   `- Source: observed in code` line that moves to `done` without a `Confirm: <C> REQ-nnn` line at a `<C>` where its
   entry equals the current one apart from its status line. A team-mode or solo-mode repository takes neither new
   reading and reads exactly as before.
5. `agk.toml` maps `scripts/agk/personal.py` and the three checks to `tests/kit/test_personal_confirm.py`.

## Consequences

A person can confirm a sidecar spec, ADR or code-observed requirement from their own terminal, and a confirmation
written by an agent session, by another login or of another shape is never read as one. The record proves only that
the yes was typed at a terminal with no agent session's mark (`Q-S0041-5`); in the files forge the mark is written by
the kit, so it is a label and not proof (`Q-S0041-16`).

## Residual

- 2026-11-18: rule 23's confirmation event (`metrics/events.jsonl`) is not appended here; it belongs to build (k)'s
  second part.
- 2026-11-18: `personal_adopt.py` and the `/agk:personal-adopt` skill (the rest of build (g)) are not in this part.
