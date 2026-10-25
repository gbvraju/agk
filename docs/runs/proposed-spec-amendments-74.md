# Proposed spec amendments 74 (SPEC-0035; REQ-042)

Date: 2026-10-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0138. The path: `docs/specs/0035-a-second-reviewer-reviews-the-same-pull-request-heads-as-the.md`.

1. **SPEC-0035 rules 4, 5 and 9, the name.** The count script is `scripts/agk/shadow_rate.py`, not `shadow_count.py`: that name is the script of SPEC-0023 rule 8 (the architect's shadow record), which stays.
2. **SPEC-0035 rule 4, the input and the authors.** The script reads recorded GitHub responses in `--api-dir` (`pulls.json`, `comments-<n>.json`, as in SPEC-0007 rule 20) and counts only comments of a listed verdict author, and `Marks:` comments also of the pull request's own author, so that a stranger cannot skew the rate.
3. **SPEC-0035 rule 4, the cases.** Only heads reviewed by both are counted; a finding without a mark in a pull request that has a `Marks:` comment is an `unmarked finding`, counted neither right nor wrong; `both` is counted once per pair, from the mark on the conductor's finding; a `Shadow:` comment that matches no verdict head is `unpaired`, and a pull request whose comments are missing is `unread`.
