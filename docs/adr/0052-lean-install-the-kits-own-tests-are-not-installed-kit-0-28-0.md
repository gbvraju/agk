# ADR-0052: lean install: the kit's own tests are not installed in a project, kit 0.28.0

- Status: Proposed
- Date: 2026-10-20
- Deciders: maintainers
- Related: ADR-0014, ADR-0032, ADR-0047, ADR-0048
- Requirements: REQ-009, REQ-010, REQ-014

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`, `agk.toml`, `agk.mk`, `config/`, `CLAUDE.md`, `.claude/`

## Context

The maintainers' brief of 2026-10-20. `/agk:init` installed 611 files (750,024 bytes) into a project; 559 of them (526,467 bytes) were the kit's own tests and fixtures under `tests/kit/`. They test AGK, not the
project. They caused the pilot's `go test` fixture clash, the Python-in-a-Go-repo friction and the first slow test run (Q-K4-199: 118.23 s once and 11.33 s later in an adopted copy). The tests keep running where they
belong: in this repository's CI. Measured with `init.py` on a fresh target, before (`main`, kit 0.27.0) and after (this branch, kit 0.28.0), by top folder (`git ls-files --others` on the target):

| Folder | Before: files, bytes | After: files, bytes |
| --- | --- | --- |
| `tests/kit` | 559, 526,467 | 0, 0 |
| `scripts` | 18, 179,485 | 18, 180,134 |
| `.claude` | 5, 17,280 | 5, 17,280 |
| `.github` | 10, 14,846 | 10, 14,846 |
| `docs` | 8, 5,122 | 8, 5,182 |
| root files | 6, 4,640 | 7, 5,065 (the new `.gitattributes`) |
| `config` | 3, 1,159 | 3, 1,159 |
| `constitution` | 2, 1,025 | 2, 1,025 |
| **Total** | **611, 750,024** | **53, 224,691** |

Adopt on a small project: 51 files, 224,799 bytes. `python3 -m pytest -q` in that adopted copy: 0.34 s (two runs), against 118 s and 11 s before.

## Decision

1. **Install less.** `kit/manifest.json` no longer lists any `tests/kit/` path (verbatim or experimental); `init`, `adopt` and `upgrade` therefore install none. The kit repository keeps `tests/kit/` and runs it as today. What
   each thing does in a target now:
   - `agk.mk` `agk-test`: includes `kit/agk-kit.mk` when that file exists (the kit repository, which defines the target there and runs the suite) and otherwise prints `agk: the kit's own tests are not installed in this
     repository; they run in the kit repository` and succeeds. The file, not a `tests/kit` folder, decides, so an edited kit test that an upgrade keeps (decision 3) does not make a suite, and `agk.mk` itself names no path.
   - `agk.mk` `agk-lint`: lints the `lint_paths` that exist; a path that is absent is skipped (an older `agk.toml` still lists `tests/kit`).
   - `project_tests` default of `kit/templates/agk.toml` (init): `[ -d tests ] || exit 0; python3 -m pytest tests -q --ignore=tests/kit_dev; ...`; a fresh project has no `tests/` and pytest would exit 4. The default
     `lint_paths` of both templates drops `tests/kit`. `agk.adopt.toml`'s `project_tests` stays empty.
   - The `governance` workflow's "Tests of the checks" step: unchanged; it runs `make -f agk.mk agk-test`, which in a target prints the notice, and runs the suite in the kit repository.
   - `check_kit_tests.py`: still installed and a no-op in a target (no `kit/manifest.json`); in the kit repository it now looks for each installed check's test in the folder the manifest names as `kit_tests`
     (`tests/kit`) on disk and no longer requires the test to be in the manifest (its own tests are updated; the case "on disk but not listed" now passes). The folder is a manifest key so that the installed script carries no path.
   - The doctor's comparison with the kit's copy: unchanged code; it covers what the manifest lists, so the kit's tests are no longer compared. For an adopt install it compares the `.gitattributes` block.
   - The metrics' test counts (`tests_before`, `tests_after`) and the facts' markers: in a target they count only the project's tests; they used to include the kit's.
   - `kit_hashes.py`: the 0.28.0 row has no `tests/kit/` entry; the 0.27.0 row still has them (so `upgrade` can recognise them).
2. **Integrity without the tests.** A target's `scripts/agk/` stays a protected class (a change needs an ADR naming it) and the doctor's comparison with the kit's copy (`agk doctor --kit-root`) is the integrity check; `upgrade`
   uses `kit/hashes.json` to tell an edited file from an old one. The security guide says so.
3. **Upgrade cleans up.** `upgrade` from 0.27.0 deletes the `tests/kit/` files of a target that equal a copy the kit shipped (rule E1, ADR-0032) and keeps and reports an edited one as `removed-in-kit <path> (modified, kept)`.
   Tested on a real 0.27.0 install (kit-only tests) and in a live throwaway target (below). A directory the deletions empty is removed, but never one directly under the target root (amendment 26): a project whose only
   `tests/` content was the kit's keeps `tests/`, so its own `pytest tests` still works.
4. **Mark what remains as kit files.** `init` writes `.gitattributes` from `kit/templates/gitattributes` (create-only: an existing file of the project is left alone) and `adopt` adds the same text as one marked block
   (`# >>> agk` ... `# <<< agk`), like `.gitignore`; `upgrade` adds it to an existing file the same way when no release has shipped the block. The content is `scripts/agk/** linguist-generated=true`: GitHub collapses
   those files in pull-request diffs and leaves them out of language statistics. Nothing else is marked. This repository does not carry that file (it would hide its own scripts' diffs): the manifest's
   `adopt.block_sources` names the template as the source of the block, and `doctor.py`, `adopt.py`, `upgrade.py` and `kit_hashes.py` read it.
5. **Specs by amendment.** `docs/runs/proposed-spec-amendments-26.md` is applied to SPEC-0001 (the installed set, rules 18 and 22), SPEC-0002 (rules 4, 6, 9 and 10 and the file table), SPEC-0006 (rule 14) and SPEC-0008
   (rules 7 and 15). SPEC-0005 rule 2 was read and needs no change. Protected classes named above: every one this change touches.
6. **Kit 0.28.0**: manifest, plugin version, this repository's `agk.toml` `version` (ADR-0050 decision 7) and `kit/hashes.json`.
7. **Docs.** `getting-started.md` step 3 gives the measured file count (53 files, 225 KB) and says the kit's own tests are not installed; step 2 says how to pin a release with the release tag (`ref`) in
   `.claude/settings.json` (SPEC-0005 rule 14); the troubleshooting line about a slow first `make test` is replaced by the new measurement (0.05 s). The security, reference and existing-codebase guides follow.

5a. **A fresh install does not mention `tests/kit/`** (ruling on Q-K4-207, 2026-10-20). Changed for new installs, by file: `kit/templates/protected-paths.txt` and `protected-paths.adopt.txt`, `reviewers.yaml` and
   `reviewers.adopt.yaml` (so the rendered `CODEOWNERS` too), `adr-0001.md` and `adr-0001-adopt.md`, `scanner-excludes.txt` (the printed text), `agk.toml` (the `project_tests` no longer ignores `tests/kit_dev`); the
   verbatim `CLAUDE.md` (rule 4 names no path), `.claude/settings.json` (the allow `Bash(python3 -m pytest tests/kit*)` and the asks `Edit(/tests/kit/**)` and `Edit(/tests/kit_dev/**)` are removed), `agk.mk` (above);
   and the installed scripts `common.py` (the default `lint_paths`; the adopt-mode marker exclusion is gone, nothing is installed to exclude), `facts.py` (the same exclusion), `doctor.py` (`KIT_ONLY`) and
   `check_kit_tests.py` (above). This repository keeps `tests/kit/` in its own `config/protected-paths.txt` and `config/reviewers.yaml` as a kit-only entry (the kit list is the installed list plus `tests/kit/`, `kit/`
   and `tests/kit_dev/`) and gets `kit/agk-kit.mk`. Existing installs get the verbatim files through an upgrade; a project's own files (`config/`, `agk.toml`, its ADR-0001) are never rewritten. Confirmed with a fresh
   `init` (53 files) and a fresh `adopt` (51 files): `grep -rn "tests/kit"` over the installed tree and over the printed output finds nothing, and two tests keep it so.

## Validation (also in the pull request body)

- **Before and after:** the table above (`init.py` on a fresh target at `main` and on this branch).
- **End to end:** `tests/kit_dev/test_end_to_end.py` (Python and Go layouts) passes on the lean install and asserts no `tests/kit` path exists in the target.
- **Live throwaway target:** `init`, a handle in `config/reviewers.yaml`, `make -f agk.mk agk-governance` all `ok` (0.52 s), `agk-test` the notice (0.01 s), `agk-project-test` and `make test` succeed (0.06 s, 0.05 s).
- **Upgrade:** a throwaway target at 0.27.0 (611 files), one `tests/kit` file edited, upgraded to this branch: 558 unmodified `tests/kit` files deleted, the edited one kept and reported, `README.md` and `app.py` untouched,
  `.gitattributes` created, 5 files replaced; `make -f agk.mk agk-governance` all `ok` once the upgrade's ADR (which the upgrade asks for, naming the protected classes) is added.
- **No weakening:** every check that ran in a target before still runs there (`make -f agk.mk agk-governance` runs the same nine). The only things that stop running in a target are the kit's own tests, which test the
  kit; they run in this repository's CI. `check_kit_tests` was already a no-op in a target.

## Consequences

- A project receives about 53 files instead of 611; its test folder, its language statistics and its first test run are its own.
- An already-installed project that edited a kit test keeps that file after the upgrade; the project's own `pytest tests` then fails to collect it (it needs the kit's fixtures) until the person deletes it (Q-K4-208).
- The pilot repository is not touched (held until its week W44 is scored on 2026-11-02); it gets this on its next `agk upgrade`.
- The maintainers tag release `v0.28.0` on `main` after this merges.

## Questions

| Q | Question | Reading taken (conservative) |
| --- | --- | --- |
| Q-K4-207 | Words that still name `tests/kit/` in installed or printed text | ruled (maintainers, 2026-10-20): a fresh install must not mention it; done in decision 5a |
| Q-K4-208 (ruled as read) | An edited `tests/kit/` file that the upgrade keeps makes the project's own `pytest tests` fail to collect | as the brief says (kept and reported); the report line names the file and the reference guide says to delete it; nothing is deleted without the project's word |
| Q-K4-209 (ruled as read) | The brief says the doctor's "hash comparison against `kit/hashes.json`"; the doctor compares bytes with the kit's copy (`--kit-root`), and `upgrade` uses `hashes.json` | stated as it is in the security guide and in decision 2; no code change |
| Q-K4-210 (ruled as read) | An upgraded project's `agk.toml` still lists `tests/kit` in `lint_paths` and its `project_tests` has no guard for a missing `tests/` | `agk-lint` skips missing paths and `upgrade` keeps `tests/` (decision 3), so both still work; `agk.toml` is the project's and is not rewritten |
| Q-K4-211 | `.claude/settings.json` is verbatim and shared: removing its three `tests/kit` patterns also removes them from this repository (the `ask` before editing `tests/kit` and `tests/kit_dev`, the allow to run pytest there) | removed, as ruled; the governance check still requires an ADR for those paths (protected classes) and CODEOWNERS still lists them; the maintainers rule whether this repository wants them back in an uncommitted local settings file |

## Residual

- 2026-10-20: the pilot repository is upgraded to 0.28.0 after its week W44 is scored (2026-11-02). (due 2026-11-30)
- Closed on 2026-10-20 by the maintainers: Q-K4-199 (the slow first test run in an adopted copy) is explained by the measurement: `python3 -m pytest -q` takes 0.34 s without the installed kit tests (118.23 s and 11.33 s
  with them). The residual of ADR-0048 is closed.
