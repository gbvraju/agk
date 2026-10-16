# SPEC-0012: intake (one sentence becomes a Draft requirement, a Draft spec and an ADR stub)

- Status: Approved
- Owner: maintainers
- Requirements: REQ-019 (AC1, AC2)

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
This is the fourth of the five K4 specs of ADR-0021 (decision 2). It extends the `/agk:spec` skill of SPEC-0005, writes in the forms that
SPEC-0010 parses and SPEC-0009 reads, and is the one place where a model writes proposal text in K4. The points `Q-K4-61` to `Q-K4-79`
were ruled by the maintainers on 2026-10-16 (`docs/runs/spec-0012-notes.md`). GitHub and Claude Code facts not reconfirmed are marked `(verify)`. The repository
facts quoted here were read on 2026-10-16 (`docs/runs/spec-0012-notes.md`).

## Rules

### The skill and what it writes

1. **The form.** `/agk:spec "<one plain-language sentence>"` (a quoted sentence, no more than 300 characters, one sentence) is a form of
   the existing `/agk:spec` skill, user-invoked and never invoked by the model on its own (SPEC-0005 rule 9). The forms of SPEC-0005
   (`spec TITLE`, `requirement TITLE`, `--from-issue N`) keep their meaning. A sentence that is empty, longer than 300 characters or
   with more than one sentence is refused with the reason, and nothing is written.
2. **Ids are read, never guessed.** The skill first runs `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/intake.py" ids`, which prints one
   JSON object `{"req": "REQ-021", "spec": "0014", "adr": "0022", "slug": "..."}` and writes nothing. `req` is the next number after
   the highest `### REQ-nnn` heading of `docs/requirements.md`; `spec` is the next after the highest `docs/specs/NNNN-*.md`; `adr` the
   next after the highest `docs/adr/NNNN-*.md`; all three are read from the tree of `origin/<default branch>` (the skill runs
   `git fetch origin <default branch>` first), not from the working tree. `slug` is made from the sentence by the rule of
   `new_spec.py` (lower case, hyphens, at most 60 characters). The model writes only the ids that this output gives.
3. **A branch, from the default branch.** The skill creates a local branch `intake/<req id lower case>-<slug>` from `origin/<default
   branch>` (`git switch -c`), so that the three files below are the whole difference from the default branch. It does not touch the
   current branch if the work tree is dirty: it stops and says so.
4. **Three files, no more.** The skill writes exactly: (1) a section appended at the end of `docs/requirements.md`; (2) a new
   `docs/specs/<spec>-<slug>.md`; (3) a new `docs/adr/<adr>-add-<req id lower case>-<slug>.md`. No notes file, no test, no code, no
   edit of an existing line of any file.
5. **The requirement.** The section has exactly this form, after one blank line:

   ```
   ### REQ-021 — <title, at most 80 characters, no semicolon>

   - Acceptance: AC1 Given <...>, when <...>, then <...>; AC2 Given <...>, when <...>, then <...>
   - Status: planned
   ```

   The `- Acceptance:` line is one line in the form SPEC-0009 rule 8 parses and SPEC-0010 reads: criteria `AC1`, `AC2`, ... in order from
   1, separated by `; `, and no `; ` inside a criterion. There are 1 to 8 criteria. Each criterion text, read case-insensitively, has
   the words `given`, `when` and `then` in this order, each followed by non-empty text. The status is `planned`.
6. **A negative case.** At least one criterion has a `then` part that states what must not happen or must be refused: it contains one of
   the words `not`, `no`, `never`, `refuses`, `rejects`, `fails`, `cannot`, `without` or `error`. If the sentence has no negative case
   the spec has a line `Negative cases: none, because <reason of at least 20 characters>`. This is a rule of form; whether a negative
   case is the right one is the person's judgement (rule 11).
7. **The Draft spec.** From the shape of `docs/specs/TEMPLATE.md`: `# SPEC-<spec>: <title>`; `- Status: Draft`; `- Owner:` as the
   template; `- Requirements: REQ-021` (only the new requirement); numbered testable rules; `## Tests` with, for each `ACn` of the
   requirement, a line that contains the marker `REQ-021 ACn`; `## Proof` (one or more lines); `## Residual` (dated bullets with
   `(due YYYY-MM-DD)`; may be empty with the text `none`); and `## Open questions` (rule 10).
8. **The ADR stub is rendered by the script, not written by the model.** `python3 ".../intake.py" stub --req REQ-021 --title "<title>"
   --sentence "<sentence>"` writes the ADR file from a fixed text: `Status: Proposed`; the date from `date -u`; `Requirements: REQ-021`;
   a `Protected classes:` line that names `docs/requirements.md`; Context (the sentence, quoted as data, and the date); Decision (REQ-021 is
   added as `planned`, SPEC-<spec> is added as `Draft`, and merging this pull request approves them as proposals, not as a finished
   spec); Consequences; Residual. It passes `check_adrs` and satisfies `check_protected_changes` for the change to
   `docs/requirements.md`. The model never edits it.
9. **What the model writes, and nowhere else in K4.** The model writes only: the requirement title, the `- Acceptance:` line, and the
   spec's title, rules, test lines, proof lines, residual bullets and open questions. Everything else in the three files is produced or
   checked by the scripts of this spec. No other K4 feature calls a model (ADR-0021 decision 6). The sentence and any issue text are
   data to turn into text, never instructions to follow.
10. **Ambiguity.** If the sentence is ambiguous (more than one reasonable reading), the skill asks the person **at most three questions**,
    one message, before it writes anything. It does not guess the answer to a question that stays unanswered: each point still open is
    written as a `Q-S<spec>-<n>` id (for example `Q-S0014-1`, built from the spec number that rule 2 allocated) under `## Open questions`
    of the spec, with the question and the reading the criteria assume. A spec with an open `Q-` id cannot be set Approved
    (SPEC-0013 rule 24). The skill never asks more than three questions in total.

### The checks, and what they cannot check

11. **The deterministic checks.** `python3 ".../intake.py" check [--base REF]` reads the work tree and the merge base with the default
    branch and fails with a message that names the rule, never the sentence. It checks:

    | Id | Check |
    | --- | --- |
    | C1 | the ids are the ones rule 2 prints for the base: the requirement is the next free `REQ`, the spec number and the ADR number are the next free |
    | C2 | the difference from the base is exactly the three files of rule 4, and the change to `docs/requirements.md` only adds the section of rule 5 at the end (no existing line is changed or removed) |
    | C3 | the acceptance line parses with `common.parse_acceptance` into 1 to 8 criteria numbered from `AC1` with no repeat, and no criterion contains `; ` |
    | C4 | each criterion has `given`, `when`, `then` in order |
    | C5 | a negative case exists, or the spec has the line of rule 6 |
    | C6 | the status of the new requirement is `planned` (not `in-progress`, not `done`); the spec is `Draft`; the ADR is `Proposed` |
    | C7 | the spec's `Requirements:` line names exactly the new requirement; its `## Tests` section has a `REQ-nnn ACn` marker for every criterion and none for a criterion that does not exist |
    | C8 | the spec has `## Proof`, `## Residual` and `## Open questions`; every residual bullet has a due date; every `Q-` id in the spec is `Q-S<spec>-<n>` |
    | C9 | the ADR's `Protected classes:` line names `docs/requirements.md` |

    After `check`, the skill runs `make governance` (all checks of the repository). Both must pass; on a failure the skill shows the
    message and may correct the file, at most three rounds, and then stops and reports.
12. **What the checks cannot check.** That the criteria are the right ones; that they say what the person meant; that the negative
    case is the important one; that the spec's rules can be built. That is the person's merge, with review. The skill says so in its
    last message.
13. **The skill stops before the commit.** The skill does not commit, push or open a pull request (SPEC-0005 rules 8 and 10). Its last
    step runs `python3 ".../intake.py" next-steps`, which prints the commit message, the push command and a pull request body
    (`Advances: REQ-021`, a dated `Build-state row:` line, `Decisions taken:`, `Questions:`, `Verified:` with the output of rule 11) for
    the person or their session to use. The commands are printed by the script, so no skill text names a forbidden verb (SPEC-0005 rule
    10). The session runs those commands under its own `CLAUDE.md`; a skill never commits, pushes or opens a pull request (ruling on
    Q-K4-61: SPEC-0005 rule 8 is a safety boundary, and the session already does the git steps, so there is no saving).

### A draft is not a fact

14. **Nothing derived reads a draft before the merge.** The scheduled features read the default branch only: `facts.py` reads the work
    tree of a checkout of the default branch (`commit` and `dirty`, SPEC-0009 rule 3), so a requirement, spec or ADR on the intake branch
    is not in `requirements`, `specs` or `adrs`; an open pull request appears in `pull_requests` with its changed file names and nothing
    of their content (SPEC-0009 rule 14). The weekly report counts a requirement as delivered only when its status is `done`
    (SPEC-0011 rule 9). After the merge the requirement is `planned`, the spec is `Draft` and the ADR is `Proposed`: the inbox then lists
    the spec and the ADR as waiting for approval (SPEC-0011 rule 3). **Merging an intake pull request approves the requirement** (it enters
    `docs/requirements.md` as `planned`); the spec stays `Draft` until its `Q-S` questions are ruled and it is set `Approved` by its own later
    change (SPEC-0013 rule 24). A reader of "a person approves it by merging" (ADR-0021 decision 2) must see this: what the merge approves is the
    requirement, not the spec.
15. **Entry points in K4.** A Claude Code session with the plugin installed (terminal, desktop app or IDE). A cloud session does not carry
    the plugin (SPEC-0005 rule 15). **The issue form is the product owner's phone path:** the product owner files a proposal issue
    (`.github/ISSUE_TEMPLATE/proposal.md`) from anywhere, and a person with a session runs `/agk:spec --from-issue N` (SPEC-0005 rule 17),
    which turns the proposal issue into the same three files, with the issue's "What you propose" paragraph as the sentence (rule 1: if it is longer than one
    sentence the skill asks the person to say it in one). An automatic issue-to-pull-request workflow is not built (`Q-K4-72`).

### Tests and proof

16. **Tests, no model.** `tests/kit_dev/test_intake.py` (kit-only: `intake.py` is not installed): fixtures built in `tmp_path` for id
    allocation (an empty requirements file; gaps in the numbers; the highest number not the last; ADR and spec numbers with leading
    zeros; an ADR and a spec with the same number, which are independent), the checks C1 to C9 each with a passing and a failing case
    (a good draft; no negative case, with and without the stated reason; a criterion without `then`; an unparsable line with `; ` inside a
    criterion; a repeated `AC2`; a status `done`; an ADR `Accepted`; a spec `Approved`; a fourth file; a changed existing line of
    `docs/requirements.md`; a `Q-` id outside the family), the ADR stub (passes `check_adrs.validate`, names the class, the date is
    `--date`), the sentence limits of rule 1, and the printed next steps. No test calls a model. The test that nothing derived reads a
    draft (rule 14) builds a repository with a default branch and an intake branch, runs the facts script of SPEC-0009 on the default
    branch and shows the draft absent. A test reads `skills/spec/SKILL.md` and fails if it names a forbidden verb of SPEC-0005 rule 10, or
    if it tells the model to write any file other than the three of rule 4.
17. **Live proof (a maintainers' step with the sessions' help, not done in this pull request).** One real intake in this repository: the
    maintainers give a sentence, a session runs the skill, the person commits and opens the pull request, it is reviewed and merged. One
    real intake in the pilot repository, run by **the pilot's own session**, under its `CLAUDE.md`, merged through review. This repository's
    `docs/runs/intake-proof.md` records for this repository the sentence, the pull request, the output of `check` and of `make
    governance`, and the verdict; for the pilot it records only the outcome (merged or not, the pull request number as a link) with the
    pilot unnamed (`Q-K4-77`). **The pilot's intake starts from the issue form** (rule 15): the sentence is the proposal issue's paragraph, filed by the
    product owner, and the pilot's session runs `--from-issue`.
18. **Installed files and classes.** Kit-only (not installed, like `new_spec.py`): `scripts/agk/intake.py` and
    `tests/kit_dev/test_intake.py`. The `skills/spec/SKILL.md` of the plugin changes. `docs/specs/TEMPLATE.md` (installed, verbatim) gains
    the section `## Open questions`. The classes touched are `scripts/agk/`, `skills/`, `tests/kit_dev/` and `kit/`; the implementation pull
    request carries an ADR that names each. The kit version is bumped because an installed file changes.
19. **Order.** Built after SPEC-0009 to SPEC-0011 (ADR-0021 decision 7: intake and playbook by 2026-11-30). SPEC-0013 uses the id
    allocation of rule 2 for its briefs.

## Tests

- Rules 1 to 13, 16: `tests/kit_dev/test_intake.py`, marker `REQ-019 AC1`.
- Rule 14 (a draft is not a fact), rule 12: the same file and SPEC-0009's fixtures, marker `REQ-019 AC2`.
- Rule 17: records in `docs/runs/`, checked by the maintainers, not by a test (markers `REQ-019 AC1` and `REQ-019 AC2`).

## Proof

REQ-019 AC1: *given one plain-language sentence, `/agk:spec` writes a requirement with Given/When/Then acceptance criteria and a Draft spec
as files in a branch.* Rules 1 to 13, 16, 17. REQ-019 AC2: *a draft is treated as a proposal: no derived fact, report or inbox line counts it
before it is merged.* Rules 14, 16. ADR-0021 decision 2 (SPEC-0012) and decision 6 (the model writes proposal text here and nowhere else in K4).

## Residual

- 2026-10-16: id allocation reads the default branch only; two open intake pull requests allocate the same ids, and the second to merge
  is renumbered by hand after the conflict (due 2026-12-31).
- 2026-10-16: the negative-case rule is a word list; a criterion can satisfy it without being a real negative case (due 2026-12-31).
- 2026-10-16: the issue form is the only entry point for a product owner without a plugin session, and a person with a session still has to run
  `--from-issue`; an automatic issue-to-pull-request workflow is not built (due 2027-01-31).
