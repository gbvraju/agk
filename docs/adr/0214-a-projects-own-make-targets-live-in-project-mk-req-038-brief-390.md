# ADR-0214: a project's own make targets live in project.mk, so an upgrade never refuses over the kit's Makefile (REQ-038, brief 390)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0160
- Requirements: REQ-038

Protected classes: `Makefile`, `scripts/agk/`, `tests/kit/`

## Context

Brief #390 (priority 1): in a pilot on Windows the upgrade from 0.57.x to 0.60.0 was refused, "edited vendored files differ
from every released copy". The project had added its own targets to `Makefile`, which `/agk:init` installs as a kit file
(`kit/manifest.json` lists it; only `adopt` skips it). An init project had no supported place for its own make targets: it
either edited a kit file, which blocks every upgrade, or kept none. The same run found the downloaded kit with CRLF line
endings; `upgrade.py` already reads both sides as LF (`lf()`, ADR-0160), so that part is a documentation gap only. The brief
names no `Measured:` line. The new tests were written first (8 failed, 3 passed at the first checkpoint).

## Decision

1. **`project.mk` (answer 1).** The kit's `Makefile` gains one line, `-include project.mk`, right after `include agk.mk`.
   GNU make reads it when it exists and ignores it when it does not. `project.mk` is never installed, listed in
   `kit/manifest.json`, hashed in `kit/hashes.json` or written by the kit; `/agk:init` writes nothing there.
2. **The refusal says where to go (answer 2).** When `upgrade.py` refuses and `Makefile` is among the conflicts, one more line
   says to move the project's own make targets from `Makefile` to `project.mk` and run again. It names the files, never their
   content. Nothing is written, as before; a conflict on any other file prints no such line.
3. **Windows (answer 3).** `docs/guides/getting-started.md` gains a section on upgrading, with the `project.mk` rule and a
   Windows note: fetch the kit from the release tag with git and no line-ending conversion (`git -c core.autocrlf=false`),
   or use the plugin cache; a CRLF copy is read as LF, so line endings alone never cause a refusal.
4. **Tests (answer 4)** in `tests/kit/test_upgrade_project_mk.py`: the include line and its place, `make` with and without
   `project.mk`, a project target that survives an upgrade untouched and still runs, the refusal naming `project.mk` and not
   the edited content, and a CRLF copy of a released `Makefile` that is replaced, not refused.
5. One changelog fragment, `changelog.d/project-mk.md`: the installed `Makefile` changes.

## Consequences

- An init project keeps its own targets across upgrades by putting them in `project.mk`; the kit's `Makefile` is replaced
  like any other kit file.
- A project that already edited its `Makefile` moves its targets once, guided by the refusal, and upgrades from then on.
- `adopt` is unchanged: it never installs `Makefile`, so the project's own `Makefile` stays the project's.

## Residual

- None (2026-10-30).
