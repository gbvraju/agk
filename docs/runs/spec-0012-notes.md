# Notes on SPEC-0012 (intake)

Date: 2026-10-16 (from `date -u`). Overnight brief 4, item A. The spec is written **Draft**; nothing is implemented and no protected path is
changed by this pull request. It is the fourth of the five K4 specs of ADR-0021 (decision 2) and serves REQ-019. Every question below is
raised, not ruled: for each, the spec takes the conservative reading and says so.

## What exists today (read on 2026-10-16, on `main` at 0c19763)

- **The skill.** `skills/spec/SKILL.md` runs `new_spec.py spec TITLE` (a Draft spec from `docs/specs/TEMPLATE.md`) or
  `new_spec.py requirement TITLE` (an ADR draft that carries the proposed requirement text and never edits `docs/requirements.md`), and
  `--from-issue N` (the command reads the issue, read-only, and passes it with `--issue N --issue-text FILE`). It is user-invoked, writes
  new files only, never commits or pushes, and a test fails on any forbidden verb in a skill (SPEC-0005 rules 8 to 10).
- **The protected file.** `docs/requirements.md` is a protected path. `check_protected_changes` accepts any ADR **added or modified in the
  same change** (status is not read) whose text names the class, and exempts a change to `- Status:` lines only. So a Proposed ADR that
  names `docs/requirements.md` covers an added requirement section. (Read in `scripts/agk/check_protected_changes.py`: `is_adr` looks at
  the path and the change status only.)
- **The parsers.** SPEC-0009 (Approved) defines the acceptance grammar (split at `; `), the marker grammar and `questions[].open_in`.
  SPEC-0010 (Approved) reads the same acceptance line. All 20 requirements today have the form `AC1 …; AC2 …`, one line.
- **The spec template.** `docs/specs/TEMPLATE.md` has `Status`, `Owner`, `Requirements`, `## Rules` and `## Tests`. It has no
  `## Proof`, `## Residual` or `## Open questions` section, although every K3 and K4 spec has the first two.
- **Ids.** 21 ADRs, 13 specs and 20 requirements exist; the next free numbers on `main` are ADR-0022, SPEC-0014 and REQ-021 (read; the
  spec says they are never typed in advance).
- **Entry points.** A cloud session does not carry the plugin (SPEC-0005 rule 15).

## Decisions taken in the draft (each is a numbered rule)

- One extra form of an existing skill, not a new skill (rule 1). The forms of SPEC-0005 are unchanged.
- Ids come from a script that reads `origin/<default>`, so the model never invents a number (rule 2); this is lesson 1 of the pilot's
  first day, and SPEC-0013 reuses the function for briefs.
- The ADR stub is rendered by a script from a fixed text (rule 8), so the model's surface is as small as possible: a title, one acceptance
  line, and the spec's own text (rule 9).
- The requirement is written into `docs/requirements.md` in the same pull request, covered by the ADR stub (rules 4, 5, 8), because a
  requirement that exists only in an ADR draft (the `requirement` form of `new_spec.py`) cannot be reviewed as a requirement.
- Nine deterministic checks (rule 11) and the existing `make governance`; a plain statement of what they cannot check (rule 12).
- The skill stops before the commit and prints the commands (rule 13), because SPEC-0005 rules 8 and 10 forbid a skill to commit, push or
  open a pull request; widening that is a question, with the amendment drafted.
- A draft is not a fact because the derived features read the default branch only and read a branch's changes as file names (rule 14).

## Options compared

| Question | Option taken | Not taken, and why |
| --- | --- | --- |
| Where the checks live | a new kit-only `intake.py` (`ids`, `stub`, `check`, `next-steps`) | extending `new_spec.py` (one script with two jobs: templates and a checker of model text); putting the checks in `check_requirements` (they apply only to an intake branch, not to every pull request) |
| Where the requirement goes | straight into `docs/requirements.md` with a Proposed ADR | only into the ADR (the existing `requirement` form): the maintainers then copy it by hand, and its form is never checked |
| Who writes the ADR stub | a script | the model: it would add a second place where model text enters a protected-class record |
| Ambiguity | up to three questions, then `Q-S<spec>-<n>` ids, never a guess | draft and list everything as questions (a draft full of questions is not reviewable); ask without a limit (a conversation, not intake) |
| Negative case | a word list in the `then` part, or a stated reason | require a negative criterion always (the sentence may have none); no check (the criterion form would not be tested for anything but shape) |
| Commit and pull request | printed by the script | the skill commits and opens it (needs an amendment of SPEC-0005, drafted); the person writes the body by hand (the body shape is easy to get wrong) |
| Id source | `origin/<default>` | the work tree (a stale branch allocates a used id); open pull requests too (needs the API in a pre-draft step) |

## Questions

| Q | Question | Reading taken in the spec |
| --- | --- | --- |
| Q-K4-61 | May the intake skill commit, push and open the pull request? SPEC-0005 rule 8 says a command that writes does not commit, push or merge, and rule 10 makes a test fail on `git push`, `git commit`, `gh pr`. | no; the script prints the commands and the body (rule 13). The amendment that would allow it is in `docs/runs/proposed-spec-amendments-14.md` |
| Q-K4-62 | A new kit-only script `intake.py`, or a new mode of `new_spec.py`? | a new script (rules 2, 8, 11, 18) |
| Q-K4-63 | Ids from `origin/<default>` only; two open intake pull requests allocate the same ids. | accepted; a residual, and the second pull request is renumbered after the conflict (rule 2) |
| Q-K4-64 | The ADR stub is rendered by the script from a fixed text. | yes (rule 8) |
| Q-K4-65 | Ambiguity: ask first, or draft and list questions? | ask at most three questions, then `Q-S<spec>-<n>` ids for what stays open; never a guess (rule 10) |
| Q-K4-66 | The negative-case rule is a word list. | the list in rule 6; weak and said to be weak (Residual) |
| Q-K4-67 | 1 to 8 criteria. | accepted as a conservative limit; a requirement that needs more is split (rule 5) |
| Q-K4-68 | Given/When/Then strictness: the three words in order, case-insensitive, text after each. | rule 5; commas are not required |
| Q-K4-69 | No `; ` inside a criterion, because the grammar of SPEC-0009 rule 8 splits there. | rule 5 and check C3 |
| Q-K4-70 | Open questions of an intake spec live in the spec (`## Open questions`) with ids `Q-S<spec>-<n>`; SPEC-0009 rule 13 defines `open_in` as notes files, Proposed ADRs and `## Open` of notes files, so a `Draft` spec file is not covered. | the id family is built from the allocated spec number; the sibling gap is in `docs/runs/proposed-spec-amendments-14.md` item 3 (an amendment of SPEC-0009), not applied |
| Q-K4-71 | No notes file for an intake spec: three files only. | yes (rule 4); the maintainers write a notes file when they approve the spec |
| Q-K4-72 | Entry points: the session only; the issue form plus `--from-issue N` for a person with a session; no issue-to-pull-request workflow. | rule 15 |
| Q-K4-73 | Does `--from-issue N` supply the sentence (the "What you propose" paragraph), asking for a one-sentence version if it is longer? | yes (rule 15) |
| Q-K4-74 | At most three correction rounds after a failed check, then stop. | rule 11 |
| Q-K4-75 | The commit message, the push command and the pull request body come from `intake.py next-steps`, so no skill text names a forbidden verb. | rule 13 |
| Q-K4-76 | Merging approves the proposal as a proposal; the spec stays `Draft`. | rule 14 |
| Q-K4-77 | Where the pilot's intake is recorded. | the outcome only here, the detail in the pilot's repository (as Q-K4-59 and Q-K4-60 ruled for the report and the hand counts) (rule 17) |
| Q-K4-78 | The sentence: one sentence, at most 300 characters. | rule 1 |
| Q-K4-79 | The existing `requirement` form of `new_spec.py` (an ADR draft that carries the text, no edit of the protected file) coexists with the new form. | yes, unchanged; it is for a requirement the maintainers want to read before it enters `docs/requirements.md` |

## Sibling specs touched (amendments proposed, none applied)

`docs/runs/proposed-spec-amendments-14.md` lists: item 1, SPEC-0005 rule 8 (the `/agk:spec` row gains the sentence form); item 2, only if
Q-K4-61 is ruled yes, SPEC-0005 rules 8 and 10; item 3, SPEC-0009 rule 13 (`open_in` gains a Draft spec's `## Open questions`). The spec
template `docs/specs/TEMPLATE.md` also gains a section (rule 18); it is not an Approved spec. This pull request edits none of those files.

## Proof plan

- REQ-019 AC1: the tests of rule 16 over fixtures, and the two real intakes of rule 17 (this repository; the pilot, by its own session).
- REQ-019 AC2: the test that builds a repository with a default branch and an intake branch and shows that the facts of the default branch
  do not contain the draft (rule 14), and the inbox and report fixtures of SPEC-0011.
- The agent writes no proposal text in the proof: the sentence is the maintainers'; the skill's model drafts; the maintainers review and merge.

## Decisions-log rows (for the maintainers' log; not edited in this pull request)

| Date | Decision | Reason | Recorded in | By |
| --- | --- | --- | --- | --- |
| 2026-10-16 | SPEC-0012 intake drafted: `/agk:spec "<sentence>"` writes a requirement with Given/When/Then criteria in the form SPEC-0010 parses, a Draft spec and a script-rendered ADR stub on a new branch, ids read from the default branch, nine deterministic checks, the skill stops before the commit | REQ-019; ADR-0021 decision 2 | `docs/specs/0012-intake.md` | agent |
