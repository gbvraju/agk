# Proposed spec amendments 146 (SPEC-0056; REQ-063)

Date: 2026-11-08 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0375 (brief #802), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0056-runbooks-for-a-red-default-branch-blocked-actions-and-a-leaked-secret.md`. The number 146 is the one the
ruling on `Q-802-1` assigned. This amendment is not applied to the spec text in this pull request; the owner decides it,
and it needs a person's `Approve: SPEC-0056`; no session posts it.

1. **Rule 14, the one step.** The first sentence reads: "One step is added to `.github/workflows/governance.yml`:
   `check_runbooks`, after `check_playbooks`, in build (a) (`Q-802-1`, ADR-0375), so that the workflow keeps one step per
   command of `agk-governance` (SPEC-0007 rule 13). No other workflow change, and no ruleset or required check change,
   is made." The last sentence keeps its rule for every other build and step.
2. **Rule 13, the same words (a consequence of item 1).** "The step of `governance.yml` is a workflow and does not change
   (rule 14)" names the step `Secret scan`, which still does not change.
3. **Tests and Proof, the same words (a consequence of item 1).** Under `## Tests`, "no workflow file changes in any
   build" reads "no workflow file changes in any build, apart from the one step of rule 14"; under `## Proof`, the words
   "with no workflow changed" are read the same way.
4. **Not in this amendment.** REQ-063 AC5 (`docs/requirements.md`) is not changed: it reads on the reporting of builds
   (c) and (d). ADR-0372 decision 6 stands for every other change (ADR-0375, decision 3).
