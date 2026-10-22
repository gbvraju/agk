# SPEC-0023: The architect reviews by one written protocol and its catch rate is measured

- Status: Draft
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-030

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "The architect role reviews every pull request by one written protocol that names what it read, walks the spec's rules, says what the tests do not prove and
where a gap belongs, and its catch rate is measured against a person's before any claim is made." It is generic and project-agnostic: it holds for every project the kit is installed in and names no project and no
reader. The method enforces the process (decide, test first, prove, review, a person merges); the quality of the review is still a person's. What the catch log (`docs/runs/architect-catches-1.md`, 21 rows) shows
made reviews catch things, and the kit's reviewer agent measured 0 of 5 (`docs/runs/shadow-review-4.md`), is writable as files and checks. The claim is not "an expert reviewer": it is that every review follows the
same protocol, names what it read, and that its catch rate is measured. The maintainers answered 3 questions before it was written: the review is a separate read-only agent (`Read`, `Grep`, `Glob`, and `Bash`
limited to read-only `git`, `gh api` GET, `make governance`, `date -u` and one comment POST for the verdict on the pull request it reviews) with a guard that refuses every write, the deciding architect keeps its
`docs/` writes, both files carry the nine steps, the tests pin the review agent's tools, guard and prohibitions, and "never in the building session" stays a written rule; the shadow review is blind both ways: the
shadow session posts nothing on the pull request and may not read its comments (it reads the head, the diff, the specs and the checks), its verdict, whose first line is `Shadow verdict: <kind> <sha>`, stays in
its session output, the maintainers paste both verdicts into `docs/runs/shadow-review-5.md` after the person's verdict is posted, in batches, the counting script reads that file only and totals the findings the
maintainers marked (catch, miss or false) naming a rule or a line, and nothing counts `Shadow verdict:` as a verdict; and the discovery and slice lines are in the charter, checked by `check-start` for projects
started after the upgrade, `not known yet` being an allowed answer.

## Rules

1. **Two agent files, one protocol.** `.claude/agents/architect.md` (the deciding architect) keeps its tools, its guard and its writes under `docs/` and `constitution/vision.md`. A new file
   `.claude/agents/architect-review.md` is the review agent: `tools: Read, Grep, Glob, Bash` and nothing else, with the same `PreToolUse` hook run in review mode. Both files carry the nine steps of rule 3, in
   that order, word for word the same text; a test compares the two texts.
2. **Separation, enforced where it can be.** The review agent never edits a file of the project, never builds, never merges and never enables auto-merge, and never reviews in the session that built the change
   (a written rule; no script can see a session). Its guard, `.claude/hooks/architect_guard.py` with the argument `--review`, denies `Edit`, `Write`, `MultiEdit` and `NotebookEdit` everywhere, and allows `Bash`
   only for the commands the deciding architect's guard allows (a read-only `git` command, `gh api` GET, `gh api --method POST` to the comments of an issue or pull request of this checkout's repository with
   `-f` fields only, `date -u`, `make governance` and the read-only scripts of `scripts/agk/`). The guard cannot tell which pull request a comment goes to; the file says it is the one under review. A test pins
   the tools, the guard's denials and the prohibitions of the file. The verdict is a comment, never a commit. The builder's report is not evidence: the protocol reads the head commit, not the description of it.
3. **The protocol, in this order, every review.**
   1. *Fetch the head* named in the report; the verdict's first line names that sha, and a verdict for another sha is void.
   2. *Read the diff* against the base, file by file; the verdict has a `Read:` line, the files read or `all`.
   3. *Walk the spec's rules* of the requirement the pull request advances, one by one: each is `holds`, `does not hold (where)` or `not testable here`; no rule is skipped silently.
   4. *Run what can be run* (the checks, the tests, a render) and quote the output; a claim with no run is marked `(verify)`, never stated as fact.
   5. *Say what the tests do not prove*: for each criterion, what a passing test would still allow.
   6. *The fixed lens*, in this order: security (credentials, redirects, origins, permissions, what is logged); honesty (nothing hidden, unknown is never zero, a declaration matches the change); portability
      (no host or tool leaks into the core); size (over the limit, split); duplication (logic copied from a kit file that will drift).
   7. *Kit or project?* Every gap is written as a project fix or a kit residual with its generic wording; a project never carries a workaround for a kit gap.
   8. *The verdict form* (SPEC-0007 rule 4, SPEC-0021 rule 1): `Verdict: cleared <sha>`, `Verdict: fix list <sha>` with numbered items or `Final:` lines, or `Verdict: rejected <sha>` with the reason; one
      sentence per finding, each naming a rule or a line.
   9. *Own the misses*: when the builder or the maintainers correct the architect with evidence, the correction is recorded in the decisions log by the architect.
4. **The shape of a verdict.** After its first line a verdict has, in this order: `Read:`; `Rules:` with one line per rule of the spec (rule 3.3); `Not proven:` with one line per criterion (3.5); `Lens:` with
   five lines (3.6); `Gaps:` with each gap as `project:` or `kit:` (3.7); `Checklist:` with one answer per question of rule 5, with evidence or `n/a`; then the findings. The first line keeps the form the metrics
   read, so nothing in SPEC-0007 changes. No governance check reads a posted verdict: the shape is pinned in the two agent files and in `kit/templates/playbook/verdict.md` by tests, and the counting script of
   rule 8 reports it.
5. **The checklist.** `config/review-checklist.md` (installed verbatim, protected by the class `config/`) has at most fifteen numbered questions, one for every kind of the catch log (`architect-catches-N.md`,
   the list of kinds in its header) and none without a kind; each question names its kind. It states that it changes only by a pull request whose decision record cites a new row of a catch log; no question is
   added from opinion. A test pins the shape, the limit, and that every kind of the latest catch log has a line.
6. **Discovery before design.** `/agk:start` asks the product owner, before the charter, about six topics, named `users` (who the users are and who pays), `existing` (what they already have: repositories,
   hosting, identity, data; which of it is private), `runs` (where it runs and whether it must be portable), `data` (what is stored and for how long), `scale` (expected scale) and `compliance`. It asks only
   about a topic that the problem statement leaves open, at most three questions per round. The charter's Decision has the numbered item `Discovery` with one bullet `- <topic>: <answer or not known yet>` for
   each of the six topics, in the order above, and the numbered item `Slice` with one bullet `- <topic>: <one sentence saying what breaks if it is wrong>` for each topic whose answer is `not known yet` (and
   for any other topic the first slice leaves out).
7. **The check applies to a start, once.** `playbook.py check-start` refuses a charter that lacks the `Discovery` item, one of the six topics, an answer, or the `Slice` bullet of a topic answered `not known yet`.
   It runs on the start pull request only, so a project whose charter was written before this change is not checked again and no check of the project fails because of it (the check runs on the difference of
   a start, SPEC-0013).
8. **Measurement before any claim.** For the next ten pull requests of this repository the review agent runs as a *shadow* in a separate session on the same head the person reviews: blind both ways. The shadow
   session posts nothing on the pull request and does not read its comments (its `gh api` GET reads the head, the diff, the specs and the checks); its verdict, whose first line is
   `Shadow verdict: <kind> <sha>`, stays in its session output. After the person's verdict is posted the maintainers paste both verdicts into `docs/runs/shadow-review-5.md`, in batches, in the shape of
   `kit/templates/playbook/shadow-record.md`: for each pull request, the two verdicts, and one line per finding `- <by> <mark> <where>: <text>` with `<by>` one of `both`, `person` or `shadow`, `<mark>` one of
   `catch` or `false`, and `<where>` the rule or line the finding names. `python3 scripts/agk/shadow_count.py FILE` reads that file only and prints the totals: catches by both, by the person only and by the
   shadow only, false findings by each, and the number of findings with no `<where>`, which count for nothing. It is kit-only, uses no network and no model, and nothing counts `Shadow verdict:` as a verdict
   (`metrics.VERDICT` does not match it).
9. **What the numbers may say.** The launch documents state the measured rate and nothing more. Below the person's rate the review agent is "a second reader", not "an architect". No model judges quality; a person
   reads both verdicts and merges.
10. **What is not built.** No scoring model, no automatic approval, no merge by any agent, no "AI reviewed" badge, no natural-language rubric the model grades itself against. The protocol is steps and evidence;
    the checklist is questions with answers; the rate is a number from a record.
11. **How it changes.** The Approved specs this touches are changed by `docs/runs/proposed-spec-amendments-N.md`, applied by the build's ADR: SPEC-0013 (the architect role file and its guard, `/agk:start`, the
    charter and `check-start`), SPEC-0021 rule 1 (the verdict the protocol writes) and SPEC-0003 rule 23 (the shadow record of the reviewer agent is not the one of the architect). The build is split as measured, each
    part a kit change (a bump, the hashes, the plugin and `agk.toml` versions, an ADR that names the protected classes): (a) the agent files, the guard mode and the checklist; (b) `/agk:start` discovery and the
    slicing rule with `check-start`; (c) the shadow record template and the counting script.
12. **The tests.** Fixtures in `tmp_path`: the two agent files compared; the review agent's tools and the guard's denials and allowances; the verdict template and the agent files for the shape of rule 4; the
    checklist against the catch log; a start with each topic present, missing, unanswered and `not known yet` with and without its slice line, and a charter from before this change; the counting script on a
    record with each case of rule 8; the shadow instructions for what they forbid. No network and no model.

## Tests

- Rules 1 and 2: the review agent's tools are exactly `Read, Grep, Glob, Bash`; its guard denies each write tool and each Bash command outside the allowed set and allows the comment POST; the file forbids editing,
  building and merging; REQ-030 AC1.
- Rules 1 and 3: the two files carry the nine steps in order, word for word; the review agent states the separation; the deciding architect's guard and writes are unchanged; REQ-030 AC2.
- Rules 3 and 4: the agent files and the verdict template name the first line, `Read:`, `Rules:`, `Not proven:`, `Lens:` (five lines), `Gaps:` (`project:` or `kit:`), `Checklist:` and the void rule for another sha;
  REQ-030 AC3.
- Rule 5: the checklist has at most fifteen questions, one per kind of the catch log and none without a kind, and the change rule; REQ-030 AC4.
- Rules 6 and 7: the skill asks at most three questions per round and only about open topics; the charter's Discovery and Slice items; `check-start` refuses a missing item, topic or answer and a `not known yet`
  without its slice line, and accepts `not known yet` with it; REQ-030 AC5.
- Rule 7: a charter without Discovery lines on a project that upgrades fails no check; `check-start` is the check of a start and is not run on it again; REQ-030 AC6.
- Rule 8: the counting script on a record: totals by both, person only and shadow only, false findings, findings with no `<where>` counted for nothing, no other file read, no network or model import, and no
  match of `Shadow verdict:` by `metrics.VERDICT`; REQ-030 AC7.
- Rules 8 and 9: the shadow instructions forbid posting and reading the pull request's comments; the launch documents state the rate and nothing more; REQ-030 AC8.

## Proof

REQ-030 AC1 and AC2: *the review is done by a read-only agent that follows the same nine steps as the deciding architect.* Rules 1 to 3. REQ-030 AC3 and AC4: *a verdict names what it read, walks every rule,
says what the tests do not prove and answers the checklist built from evidence.* Rules 3 to 5. REQ-030 AC5 and AC6: *a new project's charter says what was asked and what is not known yet, and no old project is
disturbed.* Rules 6 and 7. REQ-030 AC7 and AC8: *the catch rate is a number from a record, measured blind, and the claims stay below it.* Rules 8 and 9. The ten shadowed pull requests, with the totals, are
recorded by the maintainers in `docs/runs/shadow-review-5.md`.

## Residual

- 2026-10-22: "never in the session that built the change" is a written rule; no script can see a session, and the guard cannot tell which pull request a comment goes to (due 2026-12-31).
- 2026-10-22: no governance check reads a posted verdict, so a verdict that skips a line of the shape is caught only by the person who reads it and by the counting script's report (due 2026-12-31).
- 2026-10-22: the catch kinds of the checklist come from one catch log of two repositories' history; the log grows by rows, and a question is added only from a new row (due 2026-12-31).
- 2026-10-22: ten pull requests are a small sample; the measured rate says so in the launch documents and nothing more (due 2026-12-31).

## Open questions

none
