# Proposed spec amendments 147 (SPEC-0051; REQ-058)

Date: 2026-11-09 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0381 (brief #762), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0051-a-product-is-accepted-against-its-goals-by-evidence.md`. The number 147 is the one the ruling on
`Q-762-1` assigned. This amendment is not applied to the spec text in this pull request; the owner decides it, and it
needs a person's `Approve: SPEC-0051`; no session posts it.

1. **Rule 11, the one step.** The last sentence reads: "No `constitution/`, `config/reviewers.yaml`, `.github/CODEOWNERS`
   or ruleset change; no required check is added; no workflow changes except one step of
   `.github/workflows/governance.yml`, `check_acceptance`, after `check_runbooks`, in build (b) (`Q-762-1`, ADR-0381), so
   that the workflow keeps one step per command of `agk-governance` (SPEC-0007 rule 13), and as rule 12's build (c) says."
2. **Rule 12 (b), the same step (a consequence of item 1).** The list of build (b) gains "one step of
   `.github/workflows/governance.yml` (rule 11, ADR-0381)" after "its line in `agk.mk`'s governance target".
3. **Not in this amendment.** Rule 12's opening sentence, that a build cites `Covered-by: ADR-0340`, stands for every
   other build; build (b) cites ADR-0381 (its decision 5). ADR-0340 decision 6 stands for every other change (ADR-0381,
   decision 4).
