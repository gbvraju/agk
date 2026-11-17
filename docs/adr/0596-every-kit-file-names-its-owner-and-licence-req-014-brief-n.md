# ADR-0596: Every kit file names its owner and licence (REQ-014, brief 1419)

- Status: Proposed
- Date: 2026-11-16
- Deciders: maintainers
- Related: brief #1419, ADR-0433, plan #661
- Requirements: REQ-014

Protected classes: `constitution/`, `config/`, `.claude/`, `.github/`, `CLAUDE.md`, `scripts/agk/`, `Makefile`,
`pyproject.toml`, `agk.mk`, `agk.toml`, `tests/kit/`, `kit/`, `tests/kit_dev/`, `.claude-plugin/`, `skills/`

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
2. Every kit file carries one header of three parts, after any line that must come first (a `#!` line, an encoding
   line, front matter): `SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula`,
   `SPDX-License-Identifier: LicenseRef-AGK-Proprietary` and the notice of the brief. The comment form is `#` for
   Python, shell, PowerShell, YAML, TOML, make and plain lists, and one `<!-- -->` block for Markdown and HTML. In the
   `#` form the notice is wrapped at word boundaries so that no line passes 100 characters, the lint's limit; the HTML
   form keeps it on one line. The kit files are the files of `kit/manifest.json` (`verbatim`, `experimental`,
   `rendered`) and every tracked file under `scripts/agk/`, `.claude/`, `skills/`, `.claude-plugin/` and `kit/`, so the
   plugin's command files (`skills/<name>/SKILL.md`, after their front matter) carry it too (Q-1419-2 (a));
   `LICENSE` and `LICENSE-AGK` are the licence and carry none.
3. A file that cannot hold a comment (JSON, a generated file such as `kit/hashes.json`), every file under `.github/`
   and the three document templates (`docs/adr/TEMPLATE.md`, `docs/specs/TEMPLATE.md`, `docs/briefs/TEMPLATE.md`) are
   covered by one annotation in `REUSE.toml` at the repository root. The issue and pull request templates are
   annotated because a header in them would be copied into every issue and pull request body. Each workflow file
   carries the `#` header as its first comment lines as well, with no other change to what it does (Q-1419-1 (a),
   the conductor's verdict of 2026-11-16): a builder never changes a workflow file, so the headed workflows were
   proposed under `.agk/workflow-proposals/` and the owner applied them with `/agk:workflow-apply` (ADR-0505) at
   5a3ee53 (2026-11-17, Q-1419-4). The
   document templates are copied by `new_spec.py` into a project's own
   ADRs, specs and briefs, which are not the kit's. `.gitignore` is annotated too: its text is the marked block of a
   project's own `.gitignore` (the extendable file of ADR-0164).
4. The kit carries `LICENSE-AGK`: the text of `LICENSE` verbatim, then the annotation of decision 3, since a project's
   own `REUSE.toml` is not the kit's to write. `kit/manifest.json` lists it as a verbatim file, so `init`, `adopt` and
   `upgrade` write it to the project root and `uninstall` removes an unedited copy; the project's own `LICENSE` is
   never written.
5. A project names its grant in a `[licence]` table of `agk.toml` with `grant`, `repository` and `valid_until`.
   `doctor.py` warns, and never blocks, when the table is missing, when `repository` differs from the `origin` remote,
   and after `valid_until`, where it names the uninstall step. The warning is its own text line and its own `licence`
   key of the JSON report. The kit's own repository needs no grant. There is no network call and no licence server.
6. `rules.py` does not count the header toward an instruction file's words or rule lines, so `config/rule-budget.txt`
   is unchanged; `check_runbooks.py` and the tests that measure a page read it without the header.
7. `scripts/agk/check_licence_notice.py` fails when a kit file lacks the header, or, for a file that cannot hold one,
   the annotation, naming the path class and never a value; in a project it needs `LICENSE-AGK` and the header in each
   file under `scripts/agk/`, and its `--write` adds the missing headers. It is a step of `agk-governance` (so of
   `prepush.py`), of `governance_map.py` (run for every change) and of `.github/workflows/governance.yml`, right
   after `check_neutrality` (SPEC-0007 rule 13). A builder never changes a workflow file, so the workflow step was
   proposed as `.agk/workflow-proposals/governance.yml` and the owner applied it at 3277662 (ADR-0505; the owner's
   answer to Q-1419-3, 2026-11-16).
8. Templates under `kit/templates/` become a project's own files (its `agk.toml`, its requirements) and carry no
   header.

## Consequences

Every installed kit file says who owns it and on what terms, and every project holds the licence as `LICENSE-AGK`. The
header adds three lines to each kit file, which the kit hashes record; the rule budgets do not move. A project whose
`agk.toml` names no grant sees one doctor warning until it does. The licence text is the owner's to have reviewed.

## Residual

- The owner has the licence text reviewed by his legal counsel before the release (2026-11-16).
- The headed workflows waited for the owner's `/agk:workflow-apply 1423` (Q-1419-4); he applied the workflow step at
  3277662 (2026-11-16) and the nine headed workflows at 5a3ee53 (2026-11-17), so nothing of this is left.
