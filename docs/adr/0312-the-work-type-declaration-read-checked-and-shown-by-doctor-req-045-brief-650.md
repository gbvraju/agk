# ADR-0312: The work-type declaration, read, checked and shown by doctor (REQ-045, brief 650)

- Status: Accepted
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0251, ADR-0259, SPEC-0038
- Requirements: REQ-045

Protected classes: `scripts/agk/`, `kit/`, `agk.toml`, `tests/kit/`

## Context

SPEC-0038 rule 12 build (b) builds rule 5: a project declares its work type with one line,
`work_type = "<work type>"`, in the `[delivery]` table of `agk.toml`; `check_playbooks.py` and
`doctor.py` fail an unknown value or one whose playbook is missing, naming the setting `work_type`
and never its value; with no declaration nothing reads a playbook and `doctor.py` prints one line
`work type: none (no playbook)` (REQ-045 AC2). Brief #650 gives the build; ADR-0251 sets the
direction and lists the classes the builds of SPEC-0038 change; ADR-0259 built the format (build
(a)) and ruled that a playbook is read through `scripts/agk/playbook_format.py`, because
`scripts/agk/playbook.py` is the kit-only `/agk:start` helper (Q-513-1). This ADR number was
reserved for brief #650 by the conductor (the field note on #650).

## Decision

1. The reader is `playbook_format.declaration(root)`, in `scripts/agk/playbook_format.py`, not
   `scripts/agk/playbook.py` as rule 12 (b) and the brief name it (ADR-0259 decision 1 and its
   residual). It reads only `agk.toml` of the root, with `tomllib`, and returns the declared work
   type and the problems of the declaration; `playbook_format.selected(root)` returns the path of
   the declared playbook, or none. With no `agk.toml`, no `[delivery]` table or no `work_type` in
   it, there is no declaration and no problem.
2. A problem names rule 5, `agk.toml` and the setting, never a value: `[delivery]` that is not a
   table, or that holds a key other than `work_type` (setting `delivery`); a `work_type` that is
   not one string, so that a second type is refused (`Q-S0038-1`), one outside the list of rule 1,
   or one whose `config/playbooks/<work type>.toml` is missing (setting `work_type`); and an
   `agk.toml` that is not TOML (setting `work_type`), since the declaration cannot then be read.
3. `check_playbooks.py` prints one `FAIL playbooks:` line per problem of the declaration, beside
   those of the playbooks, and exits 1; with no declaration, or a sound one, its output is the
   same as before.
4. `doctor.py` prints one line among the information lines before the summary, which read, in
   order: tidy, deprecation (SPEC-0046 rule 11), secret scan (ADR-0306), work type, and last the
   suite lines of SPEC-0044 (its rule 7's test wants them right before the summary). The line is
   `work type: none (no playbook)`, `work type: <work type> (playbook config/playbooks/<work
   type>.toml)`, or `FAIL work type: <problem>`, which makes the exit code 1; the JSON report
   carries the same line as `work_type`, a key SPEC-0006 rule 11 gains by
   `docs/runs/proposed-spec-amendments-131.md`, and its `tests` key keeps the suite and
   deprecation lines as before. The paused, personal and no-kit reports do not change.
   Two assertions of `tests/kit/test_doctor.py` that list the report's lines and its JSON keys
   name the new line and key.
5. `kit/templates/agk.toml` and this repository's `agk.toml` carry the `[delivery]` table
   commented out; this repository declares no work type (rule 12 (b)). No session writes, changes
   or removes the line (rule 5). `agk.toml`'s test map names the new test file for
   `playbook_format.py`, `check_playbooks.py` and `doctor.py`.
6. `engines.py stack-write`, `playbook.py split` and `session.py plan` are not changed by this
   build, so their outputs without a declaration stay those of the default branch; their readers
   are builds (e), (f) and (g). No playbook file is added, `kit/manifest.json` and
   `kit/hashes.json` are not edited, and nothing under `.github/` changes.

## Consequences

A project that declares no work type sees one new line in `agk doctor` and nothing else. A
declaration that names no shipped playbook fails governance and the doctor until the playbook of
its build lands, so no project can select a work type before its playbook exists.

## Residual

- 2026-11-06: SPEC-0038 rule 5 says that with no declaration every command prints exactly what it
  prints today and that `doctor.py` prints one line; its Tests bullet asks for `doctor.py`'s output
  to be byte for byte that of the default branch. This build reads the rule: the one line is
  added, and the test compares the rest byte for byte (Q-650-1; the next amendment of SPEC-0038
  may word the bullet so, due 2026-12-31).
- 2026-11-06: SPEC-0006 rule 11 gains the `work_type` key by `docs/runs/proposed-spec-amendments-131.md`
  (the conductor's fix list on #653), which needs the owner's `Approve: SPEC-0006`.
