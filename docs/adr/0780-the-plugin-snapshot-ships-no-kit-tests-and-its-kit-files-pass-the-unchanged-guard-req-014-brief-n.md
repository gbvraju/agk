# ADR-0780: The plugin snapshot ships no kit tests, and its kit files pass the unchanged guard (REQ-014, brief 1886)

- Status: Proposed
- Date: 2026-11-24
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1886, amendment 226 (SPEC-0071 rule 2), ADR-0627, ADR-0596, ADR-0616, SPEC-0042 rule 10, brief
  #1476, plan #661
- Requirements: REQ-014

Protected classes: `agk.toml`, `scripts/agk/`, `.claude/`, `config/`, `kit/`, `tests/kit/`

## Context

ADR-0627 builds one plugin snapshot per release and fails it when `guard.scan_text` finds a secret or personal-data
shape in any shipped file; its Residual recorded 54 such files at v0.64.8, and the owner ruled `Q-1476-1` (a): the scan
stays as strict as it is and a follow-up cleans the files. At v0.65.0 the build printed 79 such lines: 47 under
`tests/kit/`, mostly the guard's own true-positive vectors, which must stay detectable for their tests to mean anything,
and 32 kit files whose code or invented fixtures the guard reads as data (a slice `args[::2]` read as the IPv6 address
`::2`, a name after `key ==`, the fixture set's phone numbers, a `.invalid` address). No script reads `tests/kit/` from
the plugin: `setup.proof_rows` runs the project's own copy, `check_kit_tests.py` reads the project's manifest,
`doctor.kit_in_repository_lines` reads only the manifest's `kit_tests` key and `tests/kit/` has not been installed since
0.27.0. The owner's word (2026-11-24 08:45 IST, the steward chat, quoted as data): "Yes, draft the test briefs and post
the runs".

## Decision

1. **The scan stays as it is (`Q-1476-1` (a)).** `guard.py`, `guard_rules.json` and
   `plugin_snapshot.secret_problems` do not change: every shipped file is scanned with `scan_text(text)`; no
   allowance, ignore entry, per-file exemption or `[guard] allow_paths` read is added, and gitleaks does not replace
   the guard.
2. **`tests/kit/` leaves the ship list.** `kit/manifest.json` `snapshot` drops `tests/kit/`; `kit_tests` stays
   `tests/kit`, so doctor's `kit-in-repository` warning and `check_kit_tests.py` are unchanged, and the steward guard's
   `kit_only_folders`, the one other reader of `snapshot`, adds the `kit_tests` folder so a clean product is still
   denied a write under `tests/kit/` or a recursive one over `tests/`. This amends ADR-0627
   decision 1 ("The list is ... `tests/kit/` ..."), and amendment 226 proposes the same change to SPEC-0071 rule 2:
   fewer files reach customers (1,167 fewer at v0.65.0), nothing unscanned ships, and no guard test is rewritten to
   hide its own vectors.
3. **The 32 kit files are rewritten, behaviour unchanged.** One helper `common.option_pairs(args, *, strict)` reads a
   command line two by two, raising `ValueError` on an odd count with `strict=True` and dropping the last item without
   it, as `zip(args[::2], args[1::2], strict=...)` did; the 19 slice files call it, and `test_map` steps
   `package_roots(...)` with `itertools.islice`. Names before a value are reordered or renamed (`"push.followtags" ==
   key`, a multi-line import of `metrics`, `reviewers.VERDICTS`, `config.TOUCHED_SETTING`, `personal.TRAILER_NAME`), two
   tuples and one playbook rule list are split over lines and two docstrings are reworded; no string a script prints
   or compares changes. The fixture set's numbers become `+1 (202) 555-0143` and `+44 (20) 7946 0958`, the same digits,
   which `design_prototype_check` compares, so a project's prototype with the old form still passes rule 7. `batch`'s
   commit identity uses `agk-batch@example.com`.
4. **The class stays closed.** `tests/kit/test_plugin_snapshot.py`, already a whole test, gains a case that scans the
   tracked files of the working tree that its own `snapshot` list allows with `secret_problems` and expects nothing,
   printing path classes only, and asserts that `tests/kit/` is not listed and that `secret_problems` holds no
   exemption. A shipped file that the guard reads as data now fails its own pull request, not the release.
5. **Path classes changed:** `agk.toml` (`test_common_option_pairs.py` joins the `scripts/agk/common.py` map entry),
   `scripts/agk/` (`common.py` and the 28 rewritten scripts), `.claude/` (`hooks/steward_guard.py`: one comparison
   reordered and `kit_only_folders` reading `kit_tests`), `config/`
   (`playbooks/mobile.toml`, `playbooks/web-app.toml`), `kit/` (`manifest.json`,
   `templates/design-prototype/fixtures.json`; `hashes.json` needed no change: `kit_hashes.py` reads `ok kit-hashes`) and `tests/kit/`
   (`test_plugin_snapshot.py`, `test_check_design_prototype.py`, `test_kit_in_repository.py`, the new
   `test_common_option_pairs.py`).

## Consequences

The snapshot of the first tag cut after this merges builds over about 340 files instead of refusing. The strict scan is
unchanged and now runs on every pull request that edits a shipped file. A project using AGK gets the rewritten scripts,
which behave as before, and a plugin without `tests/kit/`; its own `tests/kit/`, where installed, is untouched.

## Residual

- v0.65.0 still cannot build: `allow_list` reads the tag's own manifest and files (`Q-T1-4`); the first release after
  this merges is the first snapshot published.
- Reserved invented shapes (`.invalid` and `.test` addresses, 555-01xx and drama numbers, `0::/8`) stay outside the
  guard's exclusions (`Q-T1-3`); a later brief may propose them as an amendment to SPEC-0042.
- `Q-1476-3` (split the cleaning by folder) stays unanswered; with `tests/kit/` out of the list this pull request is
  the scripts-and-template part of that split and the tests part goes away (`Q-T1-5`).
