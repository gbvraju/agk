# SPEC-0021: A fix list that names only the final commit clears it in advance

- Status: Approved
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-028

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "When a fix-list verdict's only item is the final commit and it names the exact status lines, the maintainers' clearance covers that commit in advance, and a
deterministic check confirms the commit changes only those lines, so the pull request can merge without another verdict." It is the third item of the lighter-path brief (L3), after L2 (SPEC-0020), which
this check generalises. The maintainers answered 3 questions before it was written: the intake carries only its three files and the size-rule residual (L6) goes in the build pull request; a fix list is
covered when its first line is `Verdict: fix list <reviewed sha>`, it has one or more `Final: <path> <old> -> <new>` lines (with the requirement id for `docs/requirements.md`) and no numbered item, each
`Final:` line is the file's own status line and nothing else, the `Final:` lines are the maintainers' word, and the architect writes verdicts in this form when the final commit is the only item; the
workflow fetches the pull request's comments with a read-only GET using the permission it already has (which permission lists them is to be verified at the build), writes them to a file, and the check takes
`--comments FILE`, printing `skipped` when run locally. They also added a fourth point: a verdict counts only if its author is a listed verdict author, because on a public repository anyone can post a
`Verdict: cleared` or a `Final:` line; the kit reads the allowed authors from `config/reviewers.yaml`, the new check and `merged_head_cleared` both ignore a verdict by anyone else, and the existing
`cleared` reading has the same gap, so it is fixed in the same build, with the facts and report rules it touches named by amendment.

## Rules

1. **The covered fix list.** A verdict comment (SPEC-0007 rule 4, by a listed author, rule 5 below) *covers a final commit* when: its first line is `Verdict: fix list <sha>` with the sha of 4 to 40 lower-case
   hexadecimal characters (the reviewed head); it has one or more lines of the form `Final: <path> <old> -> <new>`; and it has no numbered item, that is no line that starts (after spaces) with digits and a dot.
   Other prose lines are ignored. A fix list that does not meet all three covers nothing and the old path (a `Verdict: cleared <sha>`) applies.
2. **The `Final:` line.** `<path>` is a repository path without spaces. `<old>` and `<new>` are single words. For a file other than `docs/requirements.md` the line means: the file's own line
   `- Status: <old>` becomes `- Status: <new>`. For `docs/requirements.md` the line is `Final: docs/requirements.md REQ-nnn <old> -> <new>` and means: the `- Status:` line inside the section `### REQ-nnn` of
   that file. Nothing else is named, so nothing else may change.
3. **The covered commit.** The head of the pull request is *cleared in advance* when its only parent starts with the reviewed sha of the latest covered fix list (a verdict later than every other verdict by
   listed authors), and the difference from that parent to the head is exactly the named status lines: one file per distinct `<path>`, and in each file one removed and one added line, `- Status: <old>` and
   `- Status: <new>` (rule 2), for each named section, and no other hunk, no other file and no mode or rename change. A head that is the reviewed sha itself, or two or more commits after it, is not covered.
4. **The clearance check, before the merge.** `python3 scripts/agk/check_final_clearance.py --comments FILE [--base REF]` reads the pull request's comments from the file and git alone. When the latest covered fix list
   has a head that is its reviewed sha plus one commit, it fails if that commit is not the covered commit of rule 3, naming the rule and never a value. When no covered fix list exists, or the head is the
   reviewed sha itself, it passes without checking anything. It is a step of `make governance`; without `--comments` it prints `skipped (no comments file)` and passes, so a local run never fails for want of the
   comments. It uses no network and no model.
5. **Listed verdict authors.** A comment counts as a verdict, for the metrics, the facts and the check, only when its author's login is a listed verdict author. The list is, in this order: the
   `verdict_authors` list of `config/reviewers.yaml` (an optional top-level list of GitHub handles, with or without a leading `@`) when present; otherwise the user handle of the team `maintainers`
   (`teams.maintainers.github_team`, when it is a user handle: no `/`). A team handle (`@org/slug`) cannot be expanded without a network call, so with no `verdict_authors` list it lists nobody. Logins are
   compared without regard to case. A comment by anyone else is not a verdict: it clears nothing, is not a review round or a rejection, and `Final:` lines in it are ignored.
6. **Nobody listed is unknown, not zero.** When the list is empty, the verdict-dependent fields (`rejected`, `rejected_verdicts`, `review_rounds`, `merged_head_cleared`, the facts' `verdicts`) are `unknown` (SPEC-0007
   rule 10), and `python3 scripts/agk/reviewers.py --check` fails naming the setting `verdict_authors`. A repository with a user handle for `maintainers`, such as this one, needs no change.
7. **`merged_head_cleared` and the facts.** `merged_head_cleared` is `yes` for a merged pull request when a `Verdict: cleared <sha>` by a listed author names the merged head (as before), or when the merged head is
   the covered commit of rule 3, read from the pull request's commit record (`commits/<head>`: one parent that starts with the reviewed sha, its files and their patches). The facts gain an optional field per pull
   request, `head_cleared` (`"yes"`, `"no"` or `"unknown"`, the same value), with `schema` staying 1; a facts document without it is read as before, and the report's At risk line "merged before its last commit was
   cleared" is not printed for a pull request whose `head_cleared` is `yes`.
8. **The workflow.** `.github/workflows/governance.yml` has a step before the governance step that fetches `repos/<repo>/issues/<n>/comments` with `gh api --method GET` (paged) into a file in the runner's temporary
   directory, on `pull_request` events only, and passes it with `--comments`. It needs read access to pull request comments, which is the `pull-requests: read` permission or the `issues: read` permission
   (verify which at the build, from GitHub's documentation, and quote the page in the pull request). The workflow writes nothing to the pull request.
9. **The verdict form.** `kit/templates/playbook/verdict.md` and `.claude/agents/architect.md` describe the form: `Verdict: fix list <reviewed sha>` followed by the `Final:` lines when the final commit is the only
   item. A verdict that also has other items is written as today, without `Final:` lines.
10. **One status-line reader.** The comparison of rule 3 is one function in `scripts/agk/common.py`, and the final-commit mode of `intake.py` (SPEC-0020 rule 4) calls it, with no change in what that mode accepts or
    prints. `check_final_clearance.py` is installed (verbatim), so a project has it by upgrade.
11. **How it changes.** The Approved specs this touches are changed by `docs/runs/proposed-spec-amendments-N.md`, applied by the build's ADR: SPEC-0007 rule 4 (the author), rule 5 (`review_rounds`), the
    `merged_head_cleared` bullet of rule 8 and rule 10 (unknown); SPEC-0009 rule 14 (the `verdicts` item and the optional `head_cleared`) and the source line for verdict comments; SPEC-0011 rule 5 (a pull
    request without a verdict means by a listed author), rule 10 (the At risk lines for rejected, sent back and merged-before-cleared); SPEC-0012 rule 11 (the shared function); and the specs that describe
    `config/reviewers.yaml` (SPEC-0001 and SPEC-0006, found at the build). The build is a kit change: a bump, the hashes, the plugin and `agk.toml` versions, and an ADR that names the protected classes.
12. **The tests.** Fixtures in `tmp_path` and in `tests/kit/fixtures/`: comments files with a covered fix list and each refusal of rules 1 to 3; the check against a repository built with dated commits; the author
    rules with a listed, an unlisted and a differently-cased login, a `verdict_authors` list, a user handle, a team handle and an empty list; the metrics, the facts and the report on recorded pull requests; the
    workflow file for the step, its permission and the absence of any write. No network and no model.

## Tests

- Rules 1 to 4, 10: a covered fix list and a commit that changes exactly the named lines pass, and `merged_head_cleared` is `yes`; REQ-028 AC1.
- Rules 2 and 3: any other line, another file, another status value, a second commit after the reviewed sha, a hunk outside the named section of `docs/requirements.md` each fail the check and give `no`; REQ-028 AC2.
- Rule 1: a numbered item, no `Final:` line, no sha, a sha that is not the parent of the head, each clears nothing and `merged_head_cleared` follows a `Verdict: cleared` alone; REQ-028 AC3.
- Rule 5: a verdict by an unlisted author is ignored by the metrics, the facts and the check, for `fix list`, `rejected` and `cleared` alike; REQ-028 AC4.
- Rules 5 and 6: the order of the list, a leading `@`, case, a user handle, a team handle with no list, an empty list reading `unknown`, and `reviewers.py --check` naming the setting; REQ-028 AC5.
- Rule 4: no comments file prints `skipped (no comments file)` and passes; the file is read when given; no network import; REQ-028 AC6.
- Rule 7: `head_cleared` in the facts, schema 1, a facts file without the field rendered as before, the At risk line absent for a cleared head; REQ-028 AC7.
- Rule 8: the workflow step, its `GET`, its permission, and no write step; REQ-028 AC8.

## Proof

REQ-028 AC1 and AC2: *a fix list that names only the final commit lets the pull request merge without another verdict, and only the named lines can change.* Rules 1 to 4. REQ-028 AC3: *the old path is
untouched.* Rule 1. REQ-028 AC4 and AC5: *a stranger's comment clears nothing, on a public repository too.* Rules 5 and 6. REQ-028 AC6 and AC8: *the check works offline and the workflow only reads.* Rules 4 and
8. REQ-028 AC7: *the weekly report agrees with the metrics.* Rule 7. The first build pull request merged under this rule, with the number of maintainer actions it took, is recorded by the maintainers in
`docs/runs/method-weight-2.md`.

## Residual

- 2026-10-21: in this repository the implementation session posts the maintainers' verdict lines from the maintainers' own account (SPEC-0007 residual of 2026-10-15), so the author rule cannot tell the session from the maintainers; it protects against strangers, not against a session that writes a `Final:` line itself, which the review of the pull request must catch (due 2026-12-31).
- 2026-10-21: the check does not read the proof; the maintainers read `proof` on the reviewed head before they write the word, and the merge is still gated by the required status checks (due 2026-12-31).
- 2026-10-21: a team handle for `maintainers` is not expanded, so a project that uses one lists its verdict authors in `verdict_authors` by hand (due 2026-12-31).

## Open questions

none
