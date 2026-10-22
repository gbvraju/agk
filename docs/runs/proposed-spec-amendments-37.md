# Proposed spec amendments 37 (SPEC-0013 rules 9, 11 and 29; REQ-030 part a)

Date: 2026-10-22 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0074. The path: `docs/specs/0013-playbook.md`.

1. **SPEC-0013 rule 9, what the role file can enforce.** A second agent file, `.claude/agents/architect-review.md` (tools `Read, Grep, Glob, Bash`), runs the same hook as `architect_guard.py --review`: every write
   is denied, `docs/` included, and `Bash` is judged as for the deciding architect. Both files carry the nine steps of the review protocol (SPEC-0023 rule 3).
2. **SPEC-0013 rule 11, the verdict convention.** After the first line, which is unchanged, a verdict has the lines `Read:`, `Rules:`, `Not proven:`, `Lens:`, `Gaps:` and `Checklist:` (SPEC-0023 rule 4).
3. **SPEC-0013 rule 29, installed files and classes.** `.claude/agents/architect-review.md` and `config/review-checklist.md` are installed verbatim; the class `config/` is touched as well.
