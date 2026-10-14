# SPEC-0003: Reviewer agent (spec-vs-diff)

- Status: Draft
- Owner: maintainers
- Requirements: REQ-013 (to be added by ADR)

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Open points are raised as `Q-ON-n` in `docs/runs/spec-0003-notes.md`; a rule that depends on one says so. REQ-013 is
not added by this spec: `docs/requirements.md` is protected, so an ADR adds it (proposed text in the notes).

## Rules

### Role and limits

1. **Role.** The reviewer agent reads one pull request against its stated intent (the PR body and the requirements it
   advances) and against the repository's Approved text (specs, Accepted ADRs, principles), and returns a verdict with
   findings. It advises; people decide (principle 2 and the vision).
2. **Read-only.** The agent never approves, requests changes, merges, enables auto-merge, pushes, edits or creates a
   file, resolves a thread, changes a label or runs a command. Its subagent definition lists the tools `Read`, `Grep`
   and `Glob` only. At most it produces a report; the GitHub Action form (rule 14) may post that report as one advisory
   comment, never as a review state.
3. **Untrusted input.** The PR body, the diff and every referenced file are data, not instructions. The agent
   definition says so, and a fixture (rule 18) with an injected instruction in the PR body shows the context script
   and the validator are unaffected by it.

### Inputs

4. **Context script.** `python3 scripts/agk/review_context.py --base REF --body FILE` (stdlib only, no network, no
   `gh`, no writes) assembles one markdown document on stdout from local git and files. `--body` takes a file or `-`
   for stdin. The base is resolved as the checks resolve it (`--base`, `AGK_BASE`, then the default branch).
5. **Content of the context.** In this order: (a) the PR body; (b) the diff `merge-base..worktree` with every hunk
   numbered `H1..Hn` and headed `file:Hn (old lines, new lines)`; (c) for every REQ id in the body's `Advances:`
   line, its section of `docs/requirements.md` (acceptance criteria and Status) and the files that carry its test
   markers; (d) the protected classes of `config/protected-paths.txt` that the diff touches; (e) every spec and ADR
   referenced, meaning those whose `Requirements:` line contains an advanced REQ, those named by path or by id
   (`SPEC-nnnn`, `ADR-nnnn`) in the PR body, and those named in the text of a changed file; (f) the numbered rules of
   `constitution/principles.md`.
6. **Deterministic and bounded.** The same inputs give the same bytes (sorted, no timestamps). Each section is capped
   (default 4000 lines for the diff, 1500 for the rest); a cut is marked `[truncated: N lines omitted]`, never
   silent, and the report must say it reviewed a truncated context (Q-ON-12).
7. **Missing inputs are findings.** No `Advances:` line, an unknown REQ id, a referenced spec or ADR that does not
   exist, or an empty diff are listed under `Context problems` at the top of the context, so the agent cites them
   instead of guessing.

### Output

8. **Verdict.** Exactly one of `cleared`, `fix list`, `rejected`. `cleared`: no findings. `fix list`: findings that
   the author can fix in the same PR without a decision. `rejected`: the diff contradicts an Approved spec, an
   Accepted ADR or a principle in a way that needs a maintainers' decision, or advances nothing it claims.
9. **Findings.** Numbered. Each has `file:Hn` (a hunk of the context, or `PR body` or `context problems`), a rule
   citation (`SPEC-0002 rule 4`, `ADR-0003 decision 4`, `principle 6`, `REQ-010 AC1`), one sentence stating what is
   wrong, and one sentence stating the smallest fix. A finding without both a hunk and a rule is invalid. A finding
   never quotes more than one line of content and never names a value the refusal rules hide (principle 8).
10. **Report validator.** `python3 scripts/agk/check_review_report.py --context FILE --report FILE` (stdlib only)
    exits 0 only when: the verdict is one of the three; `cleared` has no findings and the others have at least one;
    every finding has a hunk id that exists in the context (or one of the fixed tokens) and a rule citation that
    resolves to a rule, decision, principle or AC that exists in the referenced text; and the report states whether
    the context was truncated. Messages name the finding number and the field, never content.
11. **Scope of the review.** Only rules stated in Approved text: advanced REQs have test markers in the diff or
    already in the repository; a protected path changed means an ADR in the diff names its class; an Accepted ADR
    changes only its Status; an Approved spec changes only with a proposed-amendments file naming it; the PR body
    has `Advances:` and a dated `Build-state row:`; no feature PR edits `docs/build-state.md`; the diff stays inside
    the paths the PR body says it changes. No style opinions, no speculation about intent.

### Where it runs

12. **Local first.** The agent is the Claude Code subagent `.claude/agents/reviewer.md` (tools `Read`, `Grep`,
    `Glob`; the prompt fixes the output format of rules 8 and 9 and the read-only rule). A maintainer or an agent
    runs the context script, then invokes the subagent on `review-context.md` in a session, then runs the validator on
    the report. The context and the report are local files and are never committed (principle 5).
13. **Install modes.** The definition and the two scripts are installed verbatim by init and adopt in the same way
    as `drift-auditor.md` (Q-ON-6); the K3 plugin form exposes them as `/agk:review`.
14. **GitHub Action form.** Optional, off by default, behind a profile flag in `agk.toml` (`review_action`), installed
    only when the flag is set. It uses a pinned `anthropics/claude-code-action` (name, version and inputs are
    (verify), Q-ON-7) in a separate workflow, runs on `pull_request` events from the same repository only (a fork PR has
    no secrets and is skipped), has `permissions: contents: read` and `pull-requests: write` only, and posts or updates
    one advisory comment containing the validated report and a machine footer (rule 17). The credential is a
    repository secret held by maintainers; agents never read, create or set it (principle 9).
15. **Protected paths.** The agent definition (`.claude/`), the scripts (`scripts/agk/`), the workflow (`.github/`),
    the tests (`tests/kit/`, `tests/kit_dev/`) and the manifest (`kit/`) are protected classes: the implementation PR
    carries an ADR naming each, and an ADR adds REQ-013.

### Measurement

16. **Metrics.** The vision metric is review rejections per PR. For each reviewed PR the system keeps: the agent
    verdict, the number of findings, whether the context was truncated, and the maintainers' recorded verdict (a
    `Review verdict (human):` line in the PR body or a comment with the same prefix). Derived: rejections per PR
    (`rejected` and `fix list` over reviewed PRs), findings per report, agreement (agent verdict equals human
    verdict), and findings marked not-a-defect (false positives).
17. **Storage.** Nothing is committed. The advisory comment (rule 14) carries a machine footer
    `<!-- agk-review: verdict=V findings=N truncated=B -->`; local runs print the same footer. A weekly job reads these
    from GitHub and writes them only into the drift-audit issue of SPEC-0004 (Q-ON-9); K3 aggregates them (REQ-012).

### Proof

18. **Fixture pull requests.** A builder in `tests/kit_dev/` creates tiny git repositories in `tmp_path`, each a base
    commit and a head commit plus a PR body, with a known defect and the expected finding code:
    `F1` protected path changed without an ADR naming its class; `F2` an advanced REQ without a marker; `F3` an
    Approved spec edited without a proposed-amendments file; `F4` an Accepted ADR body edited; `F5` no `Advances:`
    line; `F6` a feature PR editing `docs/build-state.md`; `F7` a change outside the paths the body names;
    `F8` a clean PR (expected `cleared`); `F9` an injected instruction in the PR body; `F10` an oversized diff.
19. **Context tests.** For every fixture: the context is byte-identical across two runs; hunks are numbered; the
    sections of rule 5 appear in order; truncation is marked on `F10`; context problems appear on `F5`; the script
    makes no network call and writes nothing (an import and write-guard test as for init).
20. **Validator tests.** Recorded reports (plain text fixtures written by hand, one good and many bad: vague finding,
    missing hunk, invented hunk, invented rule number, `cleared` with findings, no verdict, two verdicts) are accepted
    or rejected as rule 10 says. The mechanical defects `F1`-`F7` also have a deterministic expected-finding list
    produced from the existing checks, so the fixtures prove the defects are detectable from the context alone.
21. **Agent definition tests.** `.claude/agents/reviewer.md` has the frontmatter `tools: Read, Grep, Glob` and no other
    tool, says it never approves, merges, pushes or edits, and says the PR content is data.
22. **No model in CI.** Tests run without network and without a model. Whether and how the agent's own judgement is
    evaluated (recorded transcripts against the fixtures, run by hand) is Q-ON-10; until decided, the agent's
    behaviour on the fixtures is checked by hand and recorded in `docs/runs/`.

## Tests

- Rules 4-7, 19: `tests/kit_dev/test_review_context.py`, marker `REQ-013 AC1`.
- Rules 8-11, 20: `tests/kit_dev/test_review_report.py`, marker `REQ-013 AC2`.
- Rules 2, 12, 21: `tests/kit_dev/test_reviewer_definition.py`, marker `REQ-013 AC3`.
- Rules 16-17: the footer format in `tests/kit_dev/test_review_report.py`; aggregation tests belong to SPEC-0004
  and K3 (marker `REQ-013 AC4`, `REQ-012 AC1`).
- Rules 14-15: workflow shape tests in `tests/kit/test_workflow.py` style (pinned SHA, permissions, same-repository
  condition), marker `REQ-013 AC3`.

## Residual

- 2026-10-14: the GitHub Action form depends on facts to confirm against current documentation: the action's name,
  version, inputs and required permissions (verify).
- 2026-10-14: the agent's judgement is not measured in CI (rule 22).
- 2026-10-14: no inline review comments in K2; one advisory comment at most.
