# ADR-0021: K4 scope and exit criteria: proof of delivery, and the method in the kit

- Status: Proposed
- Date: 2026-10-16
- Deciders: maintainers
- Related: ADR-0002, ADR-0011, ADR-0015, ADR-0016, ADR-0019, ADR-0020
- Amends: ADR-0002 (K4 only), ADR-0015 (decision 4: this is the K4-opening ADR, early)
- Requirements: REQ-003, REQ-012, REQ-015, REQ-016, REQ-017, REQ-018, REQ-019, REQ-020

Protected classes: `docs/requirements.md`

## Context

K3 built the kit's machinery: the plugin, the doctor, per-PR metrics and the upgrade (ADR-0015 criteria a, b, c met live
on 2026-10-16; d pending the scheduled weeks 42 and 43; e not met, so the reviewer agent is experimental, ADR-0020).

What K3 also showed is where the kit's value stops today. The kit proves that **process** happened: protected paths
needed an ADR, tests exist, checks ran, nothing was merged without a person. It does not yet answer the questions the
person who owns the product asks every week:

1. **Delivered:** which of my requirements are done, against which acceptance criteria?
2. **Proven:** is each acceptance criterion backed by a test that would fail if the behaviour broke?
3. **Needs me:** what is waiting for my decision right now?
4. **At risk:** what is overdue, drifting or being reworked?
5. **Cost:** how much rework and waiting did this week take?

Today a reviewer answers these by hand, from PR threads and chat. The data to answer them already lives in the
repository (requirements, acceptance criteria, test markers, verdict comments, spec and ADR states, residuals, metrics,
drift findings); it is not assembled, and two of its foundations are weaker than the questions require:

- Traceability (REQ-003) requires **a** test marker per requirement, not one per acceptance criterion. A requirement
  can be `done` with one of three criteria tested.
- Nothing proves a test **checks** anything. A test that passes on the old code and the new code alike counts as proof
  today. Shadow review 4 showed that a model reviewer cannot be trusted to notice this (0 of 5), so the proof must be
  deterministic.

ADR-0002 defined K4 as "public launch: docs site, handbook, profiles, licence review of adopted components". A launch of
a kit that proves process but not delivery would launch the weaker half. This ADR amends K4 to put proof of delivery
first and keeps the smallest launch set that the proof needs.

## Decision

1. **K4 is "proof of delivery and the method in the kit": the repository answers the product owner's five
   questions, weekly, from derived facts, with no number typed by an agent and no model judging quality; and the
   way this kit was built (an architect session that writes ADRs, specs and briefs and reviews every pull request;
   an implementation session that builds and stops; a person who decides and merges) is packaged so that a new
   product starts the same way on day one.** ADR-0002's K4 line is amended to this. Of
   its launch items, K4 keeps the README rewrite and a product-owner guide (decision 8); the docs site and the licence
   review of adopted components move to a K5 residual.

2. **K4 is delivered as five specs, each Approved before its code, in this order** (a later spec reads what an earlier
   one produces):
   - **SPEC-0009 facts.** One deterministic script, `scripts/agk/facts.py`, reads the repository once (requirements,
     acceptance criteria, test markers, specs, ADRs, residuals, PR verdict comments, metrics and drift issues) and
     writes one JSON document with a schema version and the commit it was read at. Every K4 feature reads this
     document and nothing else; `--today` makes it reproducible. Metrics and the drift audit are not rewritten in K4;
     a residual records their later move onto the facts document.
   - **SPEC-0010 proof checks.** (a) **Every acceptance criterion needs a test:** a requirement may be `done` only when
     each of its criteria `ACn` has at least one test marker `REQ-nnn ACn`; `check_requirements` enforces it. (b)
     **Red-then-green:** for a pull request, the project's own test command (`project_tests` in `agk.toml`) is run
     twice: on the base commit with the pull request's test files (the changed files under `test_dirs` matching
     `test_patterns`) placed onto it, and on the head. The check passes when the first run fails and the second
     passes. It is language-agnostic by construction: it reads nothing but the exit status of the command the
     project already declares, and a test that fails on the base because it cannot compile or import counts as red
     in every language alike. A pull request may declare `Behaviour: unchanged` in its body (refactors, docs); the
     check then reports `skipped`, and the weekly report counts those declarations. A repository with no
     `project_tests`, or whose test files cannot be told from `test_dirs` and `test_patterns`, reports `unknown`,
     never `ok`.
   - **SPEC-0011 inbox and report.** The **decision inbox** is the list of items waiting for a person: Draft specs,
     Proposed ADRs, `Q-` questions not answered in the decisions log, open pull requests without a verdict comment for
     longer than a configurable number of hours, overdue residuals, and `planned` requirements with no spec. The
     **weekly product report** is one GitHub issue per ISO week, labelled `agk-product-report`, with exactly five
     sections in the order of the five questions, written in plain language, every line linking to its evidence (a PR,
     a test file, an issue), and a footer naming the facts commit. It sits on top of the metrics and drift issues and
     links to them; it does not replace them.
   - **SPEC-0012 intake.** `/agk:spec` accepts one plain-language sentence from a product owner and drafts a
     requirement with Given/When/Then acceptance criteria and a Draft spec, as files in a branch. The draft is a
     proposal: a person approves it by merging, and nothing derived treats it as a fact before that. The model writes
     proposal text here and nowhere else in K4.

   - **SPEC-0013 playbook.** The method as files in the kit: `/agk:start`, which takes a plain-language problem
     statement and drafts the vision, the principles and the first ADR (milestones, non-goals, the ruleset) for a
     person to approve by merging; an **architect role** as a session definition (`.claude/agents/architect.md` and a
     skill `/agk:architect`) that writes ADRs, specs and briefs, reviews every pull request against the Approved
     text, posts `Verdict:` lines and rulings, records every decision in the repository, and never writes the code
     it reviews; **templates** for a brief, a rulings table, a verdict, a live-proof plan and a held-out findings
     record; and the lifecycle as deterministic checks where it can be one (an implementation pull request that
     `Advances:` a requirement with no Approved spec fails `check_specs`; a spec set Approved with open `Q-`
     questions fails). The architect is a role for a full session with the repository's context, not a subagent;
     the experimental reviewer (ADR-0020) is unrelated to it and stays experimental. SPEC-0013 is written alongside
     SPEC-0011 and built last, because it packages what the other four prove.

3. **Requirements added by this ADR** (text in `docs/requirements.md`; all `planned`):
   - **REQ-015** Every acceptance criterion is proven by a test.
   - **REQ-016** New tests prove behaviour (red-then-green).
   - **REQ-017** Decision inbox: every item waiting for a person is listed, none is missed.
   - **REQ-018** Weekly product report answers the five questions from derived facts.
   - **REQ-019** Plain-language intake: a sentence becomes a Draft requirement with acceptance criteria.
   - **REQ-020** Playbook: a new repository is started and run from a problem statement to a governed merge using
     only the kit's own commands, roles and templates.
   REQ-003's acceptance text gains AC4, "every acceptance criterion of a `done` requirement has a test marker", when
   SPEC-0010 is Approved (by the amendment mechanism, as REQ-012 was widened in ADR-0016).

4. **The pilot.** A fork of a small, active, permissively licensed public repository **in a language other than the
   kit's own**, so that K4 proves the kit does not depend on the product's language (the kit itself runs on
   `python3`, which every CI runner has; the product need not be Python). The fork adopts the kit (`agk adopt`, in
   its own sessions) at the start of K4 so that metrics and drift history accumulate while K4 is built, and real
   changes are shipped under the installed rules, as on the K2 fork. The upstream repository is never touched. The
   maintainer acts as the product owner; a product owner from outside the kit's build is the stronger proof and is
   the first ask of the friends launch (residual). In this repository it is called **the pilot repository** and never named (REQ-007,
   neutrality). The kit's maintainers never read the pilot's product code in the kit's sessions; they judge the
   pilot only by the reports it produces and by checking those reports against the pilot repository's own records.

5. **Exit criteria for K4, measurable.** K4 is closed when all seven hold:
   a. **Pilot:** for two consecutive ISO weeks the weekly product report is created on schedule in the pilot
      repository, and for each week the product owner writes answers to the five questions **from the report alone**;
      the maintainers check each answer against the repository and record 5 of 5 correct both weeks. An answer the
      report could not give counts as wrong.
   b. **Acceptance-criterion coverage:** the check fails a fixture with a `done` requirement whose second criterion
      has no test, passes on this repository's default branch and on the sandbox, and this repository's own `done`
      requirements all comply (their criteria are tested or their status is set back).
   c. **Red-then-green:** the check flags a seeded pull request whose new test passes on the base commit, in this
      repository and in the pilot repository (a different language); over two consecutive weeks of this repository's
      real pull requests it reports no unresolved false flag; a repository with no `project_tests` reports
      `unknown`, never `ok`.
   d. **Inbox:** on two weekly hand counts in this repository and two in the pilot, the inbox misses zero items (an
      extra item is a finding, not a failure).
   e. **No typed numbers:** a test shows every number and every status in the report is computed from the facts
      document, and the report names the facts commit; no field is read from a PR body except the `Behaviour:` and
      `Verdict:` lines, which are declarations and are counted as such.
   f. **Launch minimum:** the README says in plain words what the kit does and for whom, with the measured results and
      their limits (including the experimental reviewer), and a product-owner guide explains the weekly report and
      the inbox in one page.
   g. **Playbook:** the pilot fork is set up and run **using only the playbook**: from a written problem statement,
      through `/agk:start`, the architect session, `/agk:init` or `/agk:adopt`, one Approved spec and one brief, to
      its first governed merged pull request with a `Verdict: cleared` line, with every decision recorded in the
      pilot's own repository and no step taken from memory or from this repository's chat history. The record
      names each step and the file or comment it produced.

6. **Rules carried from K2 and K3, restated for K4.** No model judges code or test quality; a recurring human
   finding becomes a deterministic check; every check has fixtures with known defects and a live proof; approved text
   changes only by proposed amendment; held-out human findings are recorded before any automated reviewer sees
   them. The experimental reviewer (ADR-0020) is not used to produce any K4 fact.

7. **Dates.** K4 target 2026-12-31 (unchanged). Planned order: specs Approved by 2026-11-02; facts engine by
   2026-11-09; proof checks by 2026-11-16; inbox and report by 2026-11-23; intake and playbook by 2026-11-30; pilot
   weeks 2026-12-01 to 2026-12-14 (criterion g is run first, in the pilot's first week); slack to 2026-12-31. The
   pilot repository adopts the kit by 2026-11-02 for the metrics and drift baseline; criterion g is then proven on a
   second fresh fork, or on the same fork reset to upstream, so that the playbook run starts from nothing.

8. **Launch items kept and deferred.** Kept in K4 (criterion f): the README rewrite and the product-owner guide,
   both in this repository. Deferred to a K5-opening ADR: the docs site, the licence review of adopted components,
   and adoption profiles beyond the flags that exist (`experimental_reviewer`, `distribution`).

9. **Non-goals of K4.** No UI. No issue tracker integration. No hosted service. No model-based judgement of code,
   tests or business value: the report says what is proven and what is waiting; whether it was worth building stays
   the product owner's call.

## Consequences

- The kit's promise changes from "agents could not bypass the rules" to "here is what was delivered, what is proven,
  and what needs you"; the first stays true and becomes the foundation of the second.
- Criterion b will likely find `done` requirements in this repository whose criteria are not all tested; fixing them,
  or honestly setting them back to `in-progress`, is K4 work and is recorded.
- Red-then-green proves that a test can fail; it does not prove that a test checks the right thing. Mutation testing,
  which would, is a K5 candidate (residual), not a K4 promise. The `Behaviour: unchanged` declaration is a reported
  escape hatch, counted weekly, so that overuse is visible.
- One facts document means one parser; a disagreement between the report and the metrics issue becomes a bug in one
  place. Metrics and the drift audit keep their own readers until the residual below is closed.
- The weekly report adds a third weekly issue. Criterion a is the test of whether it is signal: if a product owner
  cannot answer the five questions from it, K4 does not close.
- The playbook packages judgement as a role and written forms, not as an automated reviewer; what it cannot
  package is the attention of the person running the architect session. Criterion g measures the package, not the
  person, which is why it demands a start from nothing and a record of every step.
- Criterion a depends on a person outside the kit's build. If the pilot repository is unavailable, K4 cannot close on
  the sandbox alone; the maintainers record the gap rather than substitute a self-judged pilot.
- The pilot's language is deliberately not the kit's, so criterion c is proven in two languages. What stays
  Python-specific after K4 is one supporting metric, `tests_before` and `tests_after` (a `def test_` count), which
  reports `unknown` elsewhere until the residual below is closed.

## Residual

- 2026-10-16: metrics (SPEC-0007) and the drift audit (SPEC-0004) read the repository with their own parsers; moving
  them onto the facts document is a later change by amendment (due 2027-01-31).
- 2026-10-16: mutation testing as a stronger proof than red-then-green is a K5 candidate (due 2027-01-31).
- 2026-10-16: the docs site, the licence review of adopted components and further adoption profiles are deferred to a
  K5-opening ADR (due 2026-12-31).
- 2026-10-16: the metrics fields `tests_before` and `tests_after` count `def test_` lines and are Python-specific;
  a per-language pattern table in `agk.toml`, or a count of files matching `test_patterns`, replaces it (due
  2026-11-30).
- 2026-10-16: the pilot's product owner is the kit's maintainer; the friends launch supplies a product owner who did
  not build the kit, and criterion a is repeated with that person before any public launch claim (due 2027-01-31).
- 2026-10-16: the pilot fork is chosen and adopted by 2026-11-02; the choice (language, licence, test command) is
  recorded in `docs/runs/` (due 2026-11-02).
