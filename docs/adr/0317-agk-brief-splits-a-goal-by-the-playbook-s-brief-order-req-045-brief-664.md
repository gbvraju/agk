# ADR-0317: /agk:brief splits a goal by the playbook's brief order (REQ-045, brief 664)

- Status: Proposed
- Date: 2026-11-07
- Deciders: maintainers
- Related: ADR-0251, ADR-0259, ADR-0312, SPEC-0038
- Requirements: REQ-045

Protected classes: `scripts/agk/`, `skills/`, `agk.toml`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0038 rule 12 build (f) builds rule 7: with a declared work type, `playbook.py split` prints,
for the owner and the session filling briefs, the proposed brief kinds in the playbook's
`brief_order`, each later kind with the `Depends-on:` line its `depends_on` pairs give, and the
milestone shape; it prints and writes no file, `skills/brief/SKILL.md` tells the session to show it
before filling a brief, and the maintainers still decide each brief's content (REQ-045 AC3). With
no declaration every command prints and writes exactly what it prints and writes today (rule 5,
REQ-045 AC2). Brief #664 gives the build; ADR-0251 sets the direction and lists the classes the
builds of SPEC-0038 change; ADR-0259 built the format and ruled that a playbook is read through
`scripts/agk/playbook_format.py`, because `scripts/agk/playbook.py` is the kit-only `/agk:start`
helper (Q-513-1); ADR-0312 built the declaration that selects the playbook. This ADR number was
reserved for brief #664 by the conductor (the field note on #664).

## Decision

1. The command is `python3 scripts/agk/playbook.py split [--goal TEXT] [--kind KIND] [--root DIR]`,
   the name rule 7 gives it, in the kit-only `playbook.py`, which `/agk:brief` reaches through the
   plugin root as it reaches `new_spec.py`. Its logic is `playbook_format.split(root, goal, kind)`
   in the installed module, which returns the lines to print and the problems that refuse the
   split, so the command reads the declaration and the playbook through `playbook_format`
   (ADR-0259 decision 1, ADR-0312 decision 1) and the brief's name `scripts/agk/playbook.py` is
   right for the command and wrong for the reader (D-664-1).
2. The lines, in order: `work type: <work type> (playbook config/playbooks/<work type>.toml)`;
   `milestone shape: <shape> (batch_by: <batch_by>)` and one indented line with its meaning in
   rule 7's words (`per-brief`: one pull request per brief, as today; `per-phase` and `per-batch`:
   the briefs of a phase or a batch are numbered as one milestone in their titles, one pull request
   per brief, and a milestone groups pull requests and never merges them); then one numbered block
   per kind of `brief_order`, in that order, whose title is `<goal>: <kind>` with a goal and `<kind>`
   without, with the lines `Kind: <kind>`, one `Depends-on: #<earlier kind brief>` for each
   `depends_on` pair of the kind, ordered by `brief_order`, and `lane: <lane name>` for the lane whose
   `kinds` hold it or `lane: none` (`Q-S0038-8`). The number in `Depends-on:` is a placeholder the
   person fills in once the earlier brief is filed, since no brief has a number before it is filed.
   `--kind KIND` prints the header lines and that kind's block alone, for the session filling one
   brief.
3. Refusals, each as one `FAIL playbook:` line with exit 1 and no proposal printed: a declaration
   with a problem (the lines of `playbook_format.declaration`, naming rule 5, `agk.toml` and the
   setting); a playbook with a problem (the lines of `playbook_format.problems`, naming the rule
   and the file); and a `--kind` outside `brief_order`, `rule 7: <file>: the kind is not in
   `brief_order` (key: brief_order)`, which names the key and never the value (brief #664 answer 2).
4. With no declaration (no `agk.toml`, no `[delivery]` table or no `work_type` in it) `split`
   prints nothing and exits 0, so `/agk:brief` prints and writes exactly what it did before:
   `new_spec.py brief` is not changed and creates the same file byte for byte with or without a
   shipped playbook (rule 5, REQ-045 AC2). `split` reads files only, writes nothing and never
   writes `agk.toml` (rule 5, `CLAUDE.md item 1`).
5. `skills/brief/SKILL.md` keeps its `new_spec.py` call first and adds the `split` call after it,
   with `--goal "TITLE"` and `--kind` named, and tells the session to show the output before
   filling the items, that a brief's `Kind:` line names one kind of `brief_order`, that `Depends-on:`
   names the earlier brief once it is filed, and that with no declared work type the command prints
   nothing and the brief is filled as today; the maintainers decide each brief's content.
   `tests/kit_dev/test_distribution.py` lists `playbook` beside `new_spec` as the scripts the brief
   skill names.
6. `agk.toml`'s `[[testing.map]]` entries of `playbook.py` and `playbook_format.py` name the new
   test file (no new script, so no new entry and no manifest change); one `changelog.d` fragment,
   since the installed `playbook_format.py` changes; no version bump; `kit/hashes.json` is not
   edited; nothing under `.github/` changes. Numbering a milestone in the titles, which needs a
   kind-to-phase or kind-to-batch map the format does not hold, is left to the person
   (`Q-664-1`).

## Consequences

A session filling briefs for a project with a declared work type sees the playbook's proposal
before each brief and copies its `Kind:` and `Depends-on:` lines by hand; nothing is filed, numbered
or written for it. A project without a declaration sees nothing new. The two shipped playbook
shapes (web-app, rule 11, and the rag-app shape of build (d)) read through the same code path.

## Residual

- 2026-11-07: SPEC-0038 rule 12 (f) names `scripts/agk/playbook.py` for the reader; the reader is
  `playbook_format.split` and the command is in `playbook.py` (D-664-1, ADR-0259's residual; the
  next amendment of SPEC-0038 corrects the name, due 2026-12-31).
- 2026-11-07: `Q-664-1`, the milestone number in a brief's title is written by the person; a later
  build may map kinds to phases or batches once the format holds that map (due 2026-12-31).
- 2026-11-07: build (d) (`config/playbooks/rag-app.toml`, brief #662) is not on the default branch
  yet; this build reads its shape from a fixture with the phases and kinds of rule 11 and declares
  `Depends-on: #662` (due 2026-12-31).
