# ADR-0755: The kit retires `every_script_tests` for `whole_tests`, and a project that still sets it is told (REQ-062)

- Status: Accepted
- Date: 2026-11-23
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1812, ADR-0698 (superseded here: brief #1651, the key), ADR-0650 and SPEC-0055 rule 6a (the whole
  tests), brief #1798 (Q-F7-1), SPEC-0046 rule 11 and ADR-0303 (the retired run-folder keys and their line), plan #661
- Requirements: REQ-062

Protected classes: `agk.toml`, `scripts/agk/`, `tests/kit/`, `docs/adr/`

## Context

`[testing] every_script_tests` (ADR-0698) runs its files when a `balanced` change adds a non-documentation file under
`scripts/agk/`. `whole_tests` (ADR-0650, SPEC-0055 rule 6a) runs its files on every change that is not documentation
only, under every profile and on the merge check, so for the same files it only adds runs. The kit's three
every-script files are all in its `whole_tests` since #1808, so the key adds nothing there: on 24c7b1c8 the plan
selects 210 files with or without it. In a project the key fires almost only on a kit upgrade that adds a script.
The owner's word (2026-11-23, the steward chat, quoted as data): "Yes, brief retiring every_script_tests". The
precedent, SPEC-0046 rule 11, kept its retired keys working for one release with one deprecation line; its removal
build was never filed.

## Decision

1. The kit's `agk.toml` drops `every_script_tests`; its three files stay in `whole_tests`. `check_kit_tests.py`
   fails the kit repository (`kit/agk-kit.mk` marks it) when its `[testing]` sets the key again, an empty list too:
   `the kit sets a retired key (setting: testing.every_script_tests)`.
2. For one release a project's key keeps today's meaning exactly: the same checks and refusal, the same trigger and
   the same `(new script)` reason. It is never read as `whole_tests` (Q-F10-1, the conservative reading).
3. `impact.run_folder_deprecation` also returns `deprecated: testing.every_script_tests (ADR-0755): list its files in
   testing.whole_tests, or remove it; the next release refuses it` when the key is set, an empty list too; with a
   run-folder key as well the two parts are one line joined by `; `, run-folder first. `doctor.py` and `prepush.py`
   (and the record's `notes`) print it unchanged; `project_tests.plan` prints it among its lines, so a project's CI
   `Project tests` step shows it. A malformed table gives no line; the readers refuse it naming the setting.
4. The release after the one that ships this refuses the key (Q-F10-2); that removal is a second brief, filed beside
   this one with `Depends-on:` it.
5. No Approved spec text changes (Q-F10-3): rule 6a already states `whole_tests`, and this record holds the
   retirement.
6. Path classes changed: `agk.toml` (the key and its comment removed), `scripts/agk/` (`impact.py`,
   `project_tests.py`, `check_kit_tests.py`), `tests/kit/` (the tests of answers 1 to 8 of the brief) and `docs/adr/`
   (this record).

## Consequences

The kit has one list for a test that reads every file of a class. Its test plans print `whole:` where they printed
`(new script)`; the selected files, the merge check and the full run are unchanged. A project that set the key runs as
before and sees one line in doctor, prepush and its CI step until it moves its files.

## Residual

ADR-0698's `- Status:` line is left as it is: a builder never changes an ADR's status line, so the supersession is
recorded here and the maintainers mark ADR-0698 (Q-1812-1). Whether any project sets the key is not readable from here
(verify).
