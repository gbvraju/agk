# ADR-0596: Every kit file names its owner and licence (REQ-014, brief 1419)

- Status: Proposed
- Date: 2026-11-16
- Deciders: maintainers
- Related: brief #1419, ADR-0433, plan #661
- Requirements: REQ-014

Protected classes: `constitution/`, `config/`, `.claude/`, `CLAUDE.md`, `scripts/agk/`, `Makefile`, `pyproject.toml`,
`agk.mk`, `tests/kit/`, `kit/`, `tests/kit_dev/`, `.claude-plugin/`, `skills/`

## Context

ADR-0433 made AGK all rights reserved: `LICENSE` holds three lines and the package and plugin metadata name
`LicenseRef-Proprietary`, and it added no source file header. A project receives the verbatim kit files of
`kit/manifest.json` and none of them says who owns it or on what terms it is used, and `LICENSE` is not installed. The
owner's direction (2026-11-16, quoted as data in brief #1419) is that every file says it is built and owned by
Balavardhi Raju Gangula, that no user of any repository may use it in another repository without the owner's
permission, and that it is removed when the project is delivered. Every open-source licence, and the source-available
ones, grant some use to anyone; what the owner asks for is a proprietary licence with a written grant per project. The
standard way to mark files with such a licence is SPDX, laid out as the REUSE specification describes `(verify: the
REUSE specification version)`.

## Decision

1. `LICENSE` holds the AGK Proprietary Licence, with the text of brief #1419 answer 1 exactly; its SPDX identifier is
   `LicenseRef-AGK-Proprietary`, which `pyproject.toml` and `.claude-plugin/plugin.json` name. Only the owner edits that
   text.
2. Every kit file carries one header of three lines, after any line that must come first (a `#!` line, an encoding
   line, YAML or TOML front matter): `SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula`,
   `SPDX-License-Identifier: LicenseRef-AGK-Proprietary` and the one notice line of the brief. The comment form is `#`
   for Python, shell, PowerShell, YAML, TOML, make and plain lists, and one `<!-- -->` block for Markdown and HTML. The
   kit files are the files of `kit/manifest.json` (`verbatim` and `experimental`), every file under `scripts/agk/`,
   `.claude/`, `skills/` and `.claude-plugin/`, and `LICENSE` itself is the licence and carries none.
3. A file that cannot hold a comment (JSON, a generated file such as `kit/hashes.json`) and every file under `.github/`
   are covered by one annotation in `REUSE.toml` at the repository root. `.github/` is annotated and not edited because
   a builder never changes a workflow file, and the issue and pull request templates would otherwise copy the header into
   every issue and pull request body. A project carries the same annotation as the last section of its `LICENSE-AGK`,
   since a project's own `REUSE.toml` is not the kit's to write.
4. `kit/manifest.json` copies `LICENSE` verbatim to the project as `LICENSE-AGK` (`init` and `upgrade`); the project's
   own `LICENSE` is never written.
5. A project names its grant in a `[licence]` table of `agk.toml` with `grant`, `repository` and `valid_until`.
   `doctor.py` warns, and never blocks, when the table is missing, when `repository` differs from the `origin` remote,
   and after `valid_until`, where it names the uninstall step. There is no network call and no licence server.
6. `rules.py` does not count the header block (the `SPDX-` lines and the notice line, with the comment markers around
   them) toward an instruction file's word budget, so `config/rule-budget.txt` is unchanged.
7. `scripts/agk/check_licence_notice.py` fails when a kit file lacks the header, or, for a file that cannot hold one,
   the annotation, naming the path class and never a value. It runs in `make governance` and in `prepush.py`.
8. Templates under `kit/templates/` become a project's own files (its `agk.toml`, its requirements) and carry no header.

## Consequences

Every installed kit file says who owns it and on what terms, and every project holds the licence as `LICENSE-AGK`. The
header adds three lines to each kit file, which the kit hashes record; the rule budgets do not move. A project whose
`agk.toml` names no grant sees one doctor warning until it does. The licence text is the owner's to have reviewed.

## Residual

- The owner has the licence text reviewed by his legal counsel before the release (2026-11-16).
- Whether `.github/` files should carry the header in place once a person may edit workflows (2026-11-16, Q-1419-1).
