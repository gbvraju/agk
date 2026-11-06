# Proposed spec amendments 131 (SPEC-0006; REQ-045)

Date: 2026-11-06 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0312 (brief #650), which stays `Proposed` for the maintainers' decision. The path: `docs/specs/0006-doctor.md`. The
number 131 is the one the conductor's fix list on pull request #653 names. This amendment is applied to the spec text in
the same pull request, as amendment 127 was for `secret_scan`. It needs a person's `Approve: SPEC-0006` on the pull
request; no session posts it.

1. **SPEC-0006 rule 11 (`--json`).** The keys of the JSON object gain `work_type`: the same text as the doctor's
   `work type:` line (SPEC-0038 rule 5, ADR-0312 decision 4), present on every run.
