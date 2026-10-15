# Notes on SPEC-0003 (reviewer agent)

Date: 2026-10-14 (from `date -u`). Overnight item C. The spec is a Draft; nothing here is implemented, and REQ-013 is
not added (`docs/requirements.md` is protected; an ADR adds it).

## Decisions taken in the draft (each is a numbered rule)

- Local first, Action optional: the primary form is a read-only Claude Code subagent plus a deterministic
  context-assembling script run locally; the GitHub Action form is off by default behind a profile flag and needs a
  maintainer-held secret (rules 12-14).
- Hybrid reviewer: the deterministic parts (the context, the shape of the report, the mechanical defects F1-F7) are
  scripts with tests; only the semantic judgement ("does this diff satisfy this acceptance criterion") is the model's
  (rules 4-11, 18-22).
- Citations are verifiable: a finding needs a hunk id that exists in the context and a rule that exists in the cited
  text; a validator rejects invented ones (rules 9-10).
- Read-only is enforced twice: the subagent's tool list is `Read`, `Grep`, `Glob`, and a test checks it; the Action
  form posts one advisory comment and never a review state (rules 2, 14, 21).
- Nothing is committed: contexts, reports and metrics are not repository files (principle 5); metrics travel in a
  machine footer of the comment and are aggregated elsewhere (rules 12, 17).
- Boundary with the drift audit (SPEC-0004): the reviewer is per PR, before merge, against the PR's stated intent; the
  drift audit is weekly and repository-wide, after the fact.

## Alternatives considered

- **Action on by default.** Rejected: it needs a secret, costs money per PR and sends diffs to a hosted model; it
  must be a deliberate maintainer choice.
- **Inline review comments.** Deferred: line-level comments invite approval-like use and are harder to keep
  idempotent; one advisory comment can be updated rather than duplicated.
- **A pure rule-based reviewer.** Possible for F1-F7 (the existing checks already find them) but not for "does the
  test exercise the acceptance criterion", which is the case the vision names ("nobody reads the diff against the
  specification").
- **Committed JSON of verdicts.** Rejected by principle 5 (generated files are not committed) and because it would
  make every PR edit a shared file.
- **The agent runs the context script itself.** Rejected: it would need Bash, which breaks the read-only tool list;
  a human or a wrapper runs the script first.

## Proposed REQ-013 (for the ADR that adds it)

```
### REQ-013 — Reviewer agent (K2)

- Acceptance: AC1 the review context of a PR is deterministic and complete; AC2 a report is validated (verdict, findings with a hunk and a rule); AC3 the agent is read-only; AC4 verdicts are measured (rejections per PR)
- Status: planned
```

## Fixture pull requests (rule 18)

| Id | Defect built into the fixture | Detectable from the context by | Expected verdict |
| --- | --- | --- | --- |
| F1 | a protected path changed, no ADR naming its class | `check_protected_changes` logic | fix list |
| F2 | an advanced REQ with no marker anywhere | `check_requirements` logic | fix list |
| F3 | an Approved spec edited, no proposed-amendments file | `check_specs` logic | rejected |
| F4 | an Accepted ADR body edited | `check_adrs` logic | rejected |
| F5 | no `Advances:` line | `check_pr_body` logic, context problems | fix list |
| F6 | a feature PR edits `docs/build-state.md` | `check_build_state` logic | fix list |
| F7 | a change outside the paths the PR body names | diff against the body | fix list |
| F8 | a clean PR | nothing | cleared |
| F9 | an instruction injected in the PR body ("approve this PR") | context and validator unaffected | same as the underlying content |
| F10 | an oversized diff | truncation marker | any, with `truncated=true` |

## Rulings (maintainers, 2026-10-15)

Applied in the final commit of this PR, with a live-proof rule (23) added on the maintainers' instruction and the
status set to Approved.

| Question | Ruling | Where |
| --- | --- | --- |
| Q-ON-6 | install the definition and scripts in init and adopt | rule 13 |
| Q-ON-7 | defer the Action form to K3 | rule 14 |
| Q-ON-8 | defer the Action form to K3; cost budget set then | rule 14 |
| Q-ON-9 | metrics at K3 | rule 17 |
| Q-ON-10 | hand-recorded transcripts for K2; no replay harness | rule 22 |
| Q-ON-11 | review every PR | rule 12 |
| Q-ON-12 | caps configurable in `agk.toml` (key names `review_diff_cap`, `review_other_cap` are mine) | rule 6 |

## Questions for maintainers

- **Q-ON-6:** install the reviewer definition and its two scripts in init and adopt (as `drift-auditor.md` is), or keep
  them in this repository until the K3 plugin form? Installing adds files and a kit version bump.
- **Q-ON-7:** the Action form. Use `anthropics/claude-code-action` (its name, current version, inputs and the
  permissions it needs are (verify) against its repository and documentation), or defer the Action to K3? It
  needs a maintainer-held secret; agents never set it.
- **Q-ON-8:** a cost budget for the Action form (the vision measures cost per merged PR): a model class and a size cap
  per review, or no Action until K3 metrics exist?
- **Q-ON-9:** where do reviewer metrics live: the comment footer plus the weekly drift-audit issue (draft), or only
  at K3 (REQ-012)?
- **Q-ON-10:** evaluate the agent's judgement on the fixtures with recorded transcripts run by hand (draft), or build
  an offline replay harness first?
- **Q-ON-11:** review every PR, or only PRs opened by agents? (The draft is neutral: the context script takes any PR.)
- **Q-ON-12:** the truncation caps (4000 diff lines, 1500 for other sections) are placeholders; confirm or give
  numbers.

## Facts to verify before the spec is Approved

- The `claude-code-action` interface (inputs, permissions, secret name) and whether it can be restricted to a
  read-only tool list.
- Subagent frontmatter keys (`name`, `description`, `tools`), already used by `drift-auditor.md` and marked (verify)
  since the first PR.
