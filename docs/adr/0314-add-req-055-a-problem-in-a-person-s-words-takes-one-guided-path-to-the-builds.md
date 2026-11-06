# ADR-0314: Add REQ-055: A problem in a person's words takes one guided path from discovery to the builds

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: SPEC-0048, SPEC-0012, SPEC-0037, SPEC-0038, SPEC-0042, SPEC-0041, ADR-0251, ADR-0259, ADR-0289, ADR-0303, plan #542, plan #365, tracker #630
- Requirements: REQ-055

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-06:

> A person brings AGK a problem in their own words, and one guided path, the same for every kind of work and drivable by auto-pilot, takes it through discovery, sourced research, a solution design with a review artifact fitted to the kind, the owner's go, and then the intake, specs, briefs and builds that exist today.

The brief is issue #654. The owner's direction, quoted as data from the brief (conductor chat,
2026-11-06): "Discovery is the phase which will help to set techstack, designs and milestones, AI
delivery with AI workforce"; on the examples given (an Istio migration, a data migration pipeline,
an A2A agent and a voice agent on LiveKit or Vapi): "All these are different in nature and build
quality but the way we build is same". It is a ruled exception to plan #542's requirement freeze,
like REQ-052 to REQ-054. The sentence is longer than the 300 characters `intake.py stub` accepts,
so this ADR was written by hand in the shape of ADR-0289 and ADR-0303.

What exists and is reused: `/agk:vision` and its ten discovery topics (`engines.py questions`),
`/agk:stack`, `/agk:design inventory` and `prototype` (SPEC-0037), `/agk:spec` (SPEC-0012),
`/agk:brief`, the playbook format and its check (SPEC-0038 build (a), `playbook_format.py`,
`check_playbooks.py`), the pilot playbook's phases and research record (SPEC-0038 rules 10 and 11,
text only until its build (n)), `session.py plan`, the conductor's assignment loop
(`[flow] assign`), the data guard's `guard.scan_text` (SPEC-0042) and `doctor.py`'s skill lookup
for `[engines]`.

## Decision

1. REQ-055 is added to `docs/requirements.md` as `planned`, and SPEC-0048 as `Draft`. Merging
   this pull request approves the requirement as a proposal; the spec stays `Draft` until the
   owner's own `Approve:` line approves it.
2. A problem enters by an `agk-problem` issue whose first line is `Problem:` (at most 1,500
   characters, data) or by `/agk:vision`; both start one path of seven phases in the same order in
   every work type and every mode (SPEC-0048 rules 1 to 3 and 13).
3. Discovery asks the ten common questions and the playbook's `[[discovery]]` questions once and
   records the answers as data in `docs/discovery/<slug>.md`, open points marked; a session never
   answers, closes a point or declares the work type (SPEC-0048 rules 4 and 5).
4. The research record of SPEC-0038 rule 10 is the kit's for every work type, in
   `docs/research/<slug>.md`, and a source older than 180 days makes it stale for a design
   (SPEC-0048 rule 6).
5. The design is the stack ADR and a text architecture; its review artifact is SPEC-0037's
   prototype for work with screens, or a demo or dry-run record for work without; a recorded
   walkthrough is judgement only and never committed. The go is the owner's `Approve:` line,
   never a session's, and nothing after it changes (SPEC-0048 rules 7 to 11).
6. A playbook may name skills, which `doctor.py` reports present or absent and never installs
   (SPEC-0048 rule 12). The `data-pipeline` work type, the `[[discovery]]` section and the
   `skills` key are proposed by amendment 130 of SPEC-0038, written by build (c), and apply only
   after the owner's `Approve: SPEC-0038` (SPEC-0048 rule 18).
7. Per plan #542, this is the one ADR of REQ-055 for the builds of SPEC-0048 rule 20. The builds
   will change these protected path classes: `scripts/agk/` (`front_door.py`, `playbook_format.py`,
   `engines.py`, `doctor.py`, builds (b) to (h)), `tests/kit/` and `tests/kit_dev/` (their
   tests), `kit/` (`kit/manifest.json`, builds (b) and (g)), `.github/` (the issue form
   `.github/ISSUE_TEMPLATE/problem.md`, build (b); not a workflow), `skills/`
   (`skills/vision/SKILL.md`, build (c)), `.claude/` (`.claude/agents/conductor.md`, builds (e)
   and (f)) and `config/` (`config/session-rules.md`, build (f), and
   `config/playbooks/data-pipeline.toml`, build (g)). A build that changes a class named here and
   no other may cite this ADR with `Covered-by: ADR-0314` once it is Accepted (session rule 36).
   No build changes `constitution/`, `config/reviewers.yaml`, a workflow, the ruleset
   (`kit/templates/ruleset.json`), `.github/CODEOWNERS`, `CLAUDE.md`, `Makefile`, `agk.mk`,
   `agk.toml`, `pyproject.toml` or `.claude-plugin/`; `kit/hashes.json` and the version stay the
   release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that
runs changes in this pull request: until build (b) lands there is no problem issue form, and until
amendment 130 is approved no playbook has discovery questions or skills and `data-pipeline` is
refused as an unknown work type.

## Residual

None beyond SPEC-0048's residual. The intake checks cannot tell whether the rules are the right
ones; that is the review of this pull request.
