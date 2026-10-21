# Proposed spec amendments 32 (SPEC-0012 rules 8, 11, 13, 14 and the Tests list)

Date: 2026-10-21 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0066. The path: `docs/specs/0012-intake.md`.

1. **SPEC-0012 rule 8, the stub.** The ADR stub's Decision text says the spec "stays `Draft` until it is approved, by a later pull request or by this intake's own final commit" (Q-K4-218, ruled in
   `docs/specs/0020-when-the-maintainers-answer-every-intake-question-before-the.md`); the earlier wording ("until its open questions are ruled and a later change sets it `Approved`") was true on one path only.
2. **SPEC-0012 rule 11, the checks.** `check --final` (SPEC-0020 rules 1 to 6) checks the approving last commit of an intake pull request; without `--final`, C6 and every other check are unchanged.
3. **SPEC-0012 rule 13, the next steps.** `next-steps` prints one closing paragraph that names the final-commit mode and the two status lines, as text.
4. **SPEC-0012 rule 14, what the merge approves.** When the maintainers answered every question before the files were written, the pull request's own final commit may set the spec `Approved` and the ADR
   `Accepted` on their word (SPEC-0020); in every other case the rule is as before.
5. **SPEC-0012 Tests.** The list gains a line for `tests/kit_dev/test_intake_final.py` (markers `REQ-027 AC1` to `REQ-027 AC6`).
