# ADR-0193: an upgrade from before 0.59.0 lists the opt-in features 0.59.0 shipped (REQ-038, brief 340)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0172, ADR-0177, ADR-0181
- Requirements: REQ-038

Protected classes: `scripts/agk/`, `tests/kit_dev/`

## Context

Brief #340 (priority 2): ADR-0181 added the marker `(opt-in: <setting>)` to changelog lines, and `upgrade.py` lists the
marked entries of the releases between the old and the new version. The features of 0.59.0 shipped before the marker
existed, so an upgrade from 0.58.0 or older never lists them, although a pilot on an older release is exactly the project
that needs them. Released sections are not edited, and the flow-mode rules allow one fragment of one line per build
(SPEC-0031 rules 1 and 2), so one line must carry several settings. The tests were written first
(`tests/kit_dev/test_upgrade_opt_in_several.py` and the updated `tests/kit_dev/test_upgrade_opt_in.py`: 15 failed at the
first checkpoint of the pull request).

## Decision

1. **Several settings in one marker (answer 1).** The marker may name several settings separated by `, `:
   `(opt-in: proof, unused_code, coverage)`. Each is a setting as before (a key, or `table.key`), each at most once. A list
   with an empty item, another separator, no space after a comma, a repeated setting or a value that is not a setting
   offers nothing, like any malformed marker. `check_release.opt_in` returns the settings in their order with the summary,
   and `upgrade.py` prints one line `opt-in: <setting>: <summary>` per setting, each with the entry's summary.
2. **An entry that speaks for an earlier release (answer 3).** An entry whose change starts with `<version> added ` speaks
   for that release. When that version is older than the section that holds the entry, the entry is listed to an upgrade
   whose old version is older than the named one and whose new version includes the section, so an upgrade from 0.58.0
   lists it and an upgrade from 0.59.0 does not list it again. An entry that names its own or a later release is read by
   its section, as before. The kit's `CHANGELOG.md` is still the only source, and `## Unreleased` is not read.
3. **One fragment for the next release (answer 2).** `changelog.d/opt-in-0-59-0.md` starts `0.59.0 added`, names proof
   per test area (`[proof]`, #307) and the drift audit's unused-code and coverage commands (`unused_code`, `coverage`,
   #313), and ends with `(opt-in: proof, unused_code, coverage)`. The released sections are not edited.
4. **Readings taken where the brief leaves a point open** (questions on the pull request): solo mode (`review_mode`,
   #317) is in the brief's example marker, but it merged after the v0.59.0 tag and is still the unreleased fragment
   `changelog.d/solo-mode.md`; naming it in a line that speaks for 0.59.0 would hide it from an upgrade from 0.59.0. The
   line names the three settings 0.59.0 shipped; solo mode is left to its own entry (Q-340-1). The phrase that
   names the release, `<version> added ` at the start of the change, is the kit's reading; the brief gives no form
   (Q-340-2).

## Log

- 2026-10-30, verdict on df7f5f6: Q-340-1 answered: solo mode ships in 0.60.0, and ` (opt-in: review_mode)` was to be
  appended to `changelog.d/solo-mode.md` if the fragment checks accept it. They refuse it: `kit_hashes.py` fails
  `changelog.d/: a build does not remove or edit a fragment; the release does`
  (`tests/kit_dev/test_kit_hashes.py::test_ac1_every_row_is_regenerated_from_history_and_compared`). The fragment is left
  unchanged, as the verdict says; the conductor files solo mode's marker separately.
- 2026-10-30, verdict on df7f5f6: Q-340-2 accepted: `<version> added ` at the start of the change names the release an
  entry speaks for, as built.

## Consequences

- A project on 0.58.0 or older that upgrades to the next release sees `proof`, `unused_code` and `coverage` listed after
  its upgrade, each with one summary line; a project on 0.59.0 sees them no more.
- A later release that needs to list what an older one shipped writes one fragment that starts `<version> added `; no
  released section is edited.
- A changelog line that happens to start with a version followed by ` added ` is read as speaking for that release; only
  a line with an opt-in marker is affected.

## Residual

- Solo mode's own opt-in marker (`review_mode`), which a build cannot add to its fragment; filed by the conductor
  (2026-10-30).
