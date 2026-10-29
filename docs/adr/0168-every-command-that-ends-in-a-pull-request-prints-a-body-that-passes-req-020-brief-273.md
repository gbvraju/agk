# ADR-0168: every command that ends in a pull request prints a body that passes (REQ-020, brief 273)

- Status: Accepted
- Date: 2026-10-29
- Deciders: maintainers
- Related: ADR-0039, ADR-0120, ADR-0140, ADR-0163
- Requirements: REQ-020

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `skills/`

## Context

Brief #273 (priority 1). In a project pilot (2026-10-26) the person repaired pull request bodies four times: a `Summary:` over 120
characters from `/agk:stack`, a body that `/agk:start` printed without the `Brief:` line the repository then required, an edit that
dropped two required lines, and a stack body written by the session from scratch. Each spec pull request also failed
`final-clearance` until the person learned to post `Approve: <ID> SPEC-nnnn`, which no command printed. A field note on the brief
adds that design and spec pull requests that answer no brief had no accepted `Brief:` form. The number ADR-0168 was reserved for
this brief. The tests were written first and were red before the code they test (9 of 16 in `tests/kit/test_pr_bodies.py`, 13 of 14 in
`tests/kit_dev/test_pr_bodies_kit.py`, checkpoint 0869634).

## Decision

1. **One builder of bodies** (answer 1): `scripts/agk/pr_body.py` (kit-only, never installed) builds the body from the change,
   cuts the `Summary:` to 120 characters at the last word boundary, writes it to `<git dir>/agk/pr-body.md` (never a tracked
   file) and runs the repository's own `scripts/agk/check_pr_body.py` on it (the kit's copy when the repository has none),
   isolated (`-I`), in the state the command was given. A body that fails is never printed: the command refuses with the check's
   `FAIL` lines, which name the rule and never a value. The commands print `Pull request body file: <path>` and then the text.
2. **The state without network**: SPEC-0005 rule 8 gives `/agk:start` and `/agk:upgrade` no network, so no script reads the
   issues. The command is given the state: `--brief N` (the brief the work answers, written `Brief: #N`), `--brief none` (the
   person says the repository has no open brief; no line), or `--issues FILE` (a saved copy of the open briefs, as the governance
   workflow saves it). With none of them the body is checked as if a brief were open, so it is refused unless it carries a brief
   or a none form; the message names the option. The red-branch brief is an `agk-brief` issue and is covered the same way. No
   printed body has a `Depends-on:` line, so it passes either `pr_mode`.
3. **The commands**: `playbook.py next-steps` and `intake.py next-steps` take `--brief` and `--issues`; `engines.py` gains
   `stack-next-steps` (answer 2: the body of the options pull request, or of the accepting one once the ADR is Accepted, its
   requirement read from the ADR's `Requirements:` line) and `design-next-steps --req REQ-nnn` (after `check_design.py` passes);
   `upgrade.py TARGET --next-steps` prints the body once the upgrade is written and the person wrote its ADR, titled from the
   skeleton the upgrade prints. The skills `start`, `vision`, `spec`, `stack`, `design` and `upgrade` call them and say to use the
   body unchanged; `/agk:stack` no longer carries a body with placeholders (Q-274-1 of ADR-0163).
4. **The Approve line** (answer 3): when the head is the approving commit of an intake (`intake.py check --final` passes),
   `intake.py next-steps` prints the push, the one line `Approve: <full head ID> SPEC-nnnn`, that the spec approver posts it as a
   comment from their own account and not through an agent app or a session, and that a red `final-clearance` before it is
   expected.
5. **The none forms** (the field note, widened by the verdict on Q-273-1): `check_pr_body.py` accepts `Brief: none (design)`
   when a changed file is under `docs/design/`, and `Brief: none (spec)` when a changed file is under `docs/specs/` or is
   `docs/requirements.md`, and every other changed file is one of the documents either form may carry beside it: under
   `docs/adr/`, a `docs/runs/proposed-spec-amendments-*.md` file (by pattern, one folder deep, not by prefix), or
   `docs/runs/decisions-log.md`. Code is never part of either form, and a change of only those shared documents fits neither. The
   changed files are read with git from the base (`AGK_BASE`, set by the workflow's merge-ref step) to the work tree; an empty
   change, any other path, or a base that does not resolve fails with `rule 9` naming the path classes, never a file.
   `pr_body.py` prints a none form whenever the change fits one, since it passes in either state.
6. **Tests and flow mode** (answer 4): the tests of the check are in `tests/kit/test_pr_bodies.py`; the tests of the kit-only
   commands are in `tests/kit_dev/test_pr_bodies_kit.py`, because `tests/kit/` is installed in projects that have no kit-only
   script. Invented repositories only. Fragment `changelog.d/pr-bodies.md`; no version bump, and `kit/hashes.json` is not edited
   (session rule 14).

## Consequences

- A person no longer edits a printed body, and a body the repository would refuse is never printed.
- A command run without the state refuses once and says which option to give; existing callers of `next-steps` add `--brief`.
- An intake pull request (the requirements, a spec, an ADR stub and maybe a decisions-log row) is a `none (spec)` change, so its
  next steps print that form when no brief is given.

## Residual

- 2026-10-29: Q-273-1, answered by the conductor's verdict on 2c9d862: both forms also take `docs/adr/`, the amendments file
  and the decisions log. Reading taken: a change of only those shared documents fits neither form.
- 2026-10-29: Q-273-2, whether a command may read the open briefs itself with a read-only `gh api` (SPEC-0005 rule 8 gives
  `/agk:start` and `/agk:upgrade` no network) is for the maintainers; until then the state is an option (due 2026-12-15).
