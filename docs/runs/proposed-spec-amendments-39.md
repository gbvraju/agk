# Proposed spec amendments 39 (SPEC-0003 rule 23; REQ-030 part c)

Date: 2026-10-22 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0076. The path: `docs/specs/0003-reviewer-agent.md`.

1. **SPEC-0003 rule 23, the shadow record.** The shadow record of the reviewer agent (`docs/runs/shadow-review-template.md`) is not the one of the review agent of the architect role: that one is
   `kit/templates/playbook/shadow-record.md`, counted by `python3 scripts/agk/shadow_count.py FILE` (SPEC-0023 rule 8), and `Shadow verdict:` is never counted as a verdict.
