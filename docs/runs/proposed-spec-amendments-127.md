# Proposed spec amendments 127 (SPEC-0006; REQ-049)

Date: 2026-11-06 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0306 (brief #632), which stays `Proposed` for the maintainers' decision. The path: `docs/specs/0006-doctor.md`. The
number 127 is the one the conductor's fix list on pull request #640 names. This amendment is applied to the spec text in
the same pull request. It needs a person's `Approve: SPEC-0006` on the pull request; no session posts it.

1. **SPEC-0006 rule 11 (`--json`).** The keys of the JSON object gain `secret_scan`: the same text as the doctor's
   `secret scan:` information line (ADR-0306 decision 5), present on every run.
