# ADR-0303: Add REQ-053: A failing test opens one bug issue, and its fix leaves a record for the next one

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: SPEC-0046, SPEC-0012, SPEC-0042, SPEC-0028, ADR-0299, ADR-0289, ADR-0242, ADR-0297, plan #542
- Requirements: REQ-053

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-06:

> A failing test on the default branch or in a release opens one bug issue with cleaned evidence kept only while it is open, the fix adds a short fix record, and AGK shows the matching past fixes on every new failure, so a known failure is reproduced and fixed fast.

The brief is issue #626. The owner's decisions, quoted as data from the brief (conductor chat,
2026-11-06): "Evidence kept only for open failures , add evidence once it is fixed . These
learnings should help AGK in the project , how to fix different issues reproduct and fix fast
instead of wasting tokens and time . This makes sense to have feature", "Yes , take the intake",
and, on the run folders: "why you need folders , unnecessary disk space and junk". It is a ruled
exception to plan #542's requirement freeze, like REQ-052. The owner then asked, quoted as data from the conductor's field
note on the brief (2026-11-06): "how about local mode and solo, flow - when there is no GitHub CI
run"; decision 7 answers it.

What exists and is reused: the data guard's redacting log reader and `guard.scan_text`
(SPEC-0042 rules 10, 11 and 13), the `found-bug` label of session rule 34, the JUnit setting
`[testing] junit`, the release pull request of SPEC-0028 (`check_release.py`), the full suite on a
push and a release pull request (ADR-0242), the pull request body check (`check_pr_body.py`), and
the run folders of ADR-0299, which this requirement retires.

## Decision

1. REQ-053 is added to `docs/requirements.md` as `planned`, and SPEC-0046 as `Draft`. Merging
   this pull request approves the requirement as a proposal; the spec stays `Draft` until the
   owner's own `Approve:` line approves it.
2. Only the full CI run of a push to the default branch and the run of a release pull request
   report a failure, and only with `[failures] issues = true`; a project that sets nothing sees no
   change (SPEC-0046 rules 1 and 2).
3. One `found-bug` issue per failure signature; evidence is cleaned text in its own comments,
   deleted when the issue closes; screenshots and traces are a 7-day CI artifact, only in a private
   repository with the setting on; no image is uploaded to an issue (SPEC-0046 rules 3 to 6).
4. The fix record is five lines of the fixing pull request's body, checked offline for shape and by
   the data guard; the issue closes on the first full run that runs and passes its test (SPEC-0046
   rules 7 and 8).
5. Past fixes are read only from the project's own closed issues, by signature and then test id;
   nothing moves into the kit (SPEC-0046 rules 9 and 10).
6. The run folders of ADR-0299 are retired: build (f) makes the three `[testing]` keys inert with a
   deprecation line and marks ADR-0299 `Superseded`; build (g) removes them in the release after
   (SPEC-0046 rule 11).
7. Where no CI runs (local mode, `execution = "local"`, personal mode), one person-started run,
   `failures.py run`, stands in for the two CI runs; it runs `project_tests.py`'s full command on a
   clean default-branch or release head and is refused inside an agent session. Its screenshots and
   traces stay in one private folder per open failure under `AGK_HOME`, never in the repository.
   With GitHub reachable it writes issues as on CI; with no GitHub access the failure and the fix
   record are one text file each in the git-ignored `.agk/failures/` (the sidecar in personal
   mode), not committed. The signature and the data guard are the same in every mode
   (SPEC-0046 rules 12 to 14).
8. Per plan #542, this is the one ADR of REQ-053 for the builds of SPEC-0046 rule 15 other than
   (e). The builds will change these protected path classes: `scripts/agk/` (`failures.py`,
   `config.py`, `check_pr_body.py`, `proof.py`, `prepush.py`, `impact.py`, `doctor.py`, builds (b),
   (c), (d), (f), (g), (h) and (i)), `tests/kit/` (their tests), `kit/` (the `.agk/` line of
   `kit/templates/gitignore`, build (i)), `agk.toml` (the `[[testing.map]]` entries,
   builds (b) and (d)) and `config/` (`config/session-rules.md`, the `Fixes-failure:` form, build
   (c)). A build that changes a class named here and no other may cite this ADR with
   `Covered-by: ADR-0303` once it is Accepted (session rule 36). Build (e) changes
   `.github/workflows/governance.yml` and `agk.toml`, so it writes its own ADR, as session rule 36
   requires for a workflow, and it is on the owner's hold list. No build changes `constitution/`,
   `config/reviewers.yaml`, the ruleset (`kit/templates/ruleset.json`), `.github/CODEOWNERS`,
   `.claude/`, `CLAUDE.md`, `Makefile`, `agk.mk`, `pyproject.toml`, `skills/` or `.claude-plugin/`;
   `kit/hashes.json` and the version stay the release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that
runs changes in this pull request; until build (e) lands no CI run opens an issue, until build (h)
lands no run where CI is off reports, and the run folders work as today until build (f).

## Residual

None beyond SPEC-0046's residual. The intake checks cannot tell whether the rules are the right
ones; that is the review of this pull request.
