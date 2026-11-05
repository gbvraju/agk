# Proposed spec amendments 115 (SPEC-0009, SPEC-0011, SPEC-0018, the planning guide; REQ-050)

Date: 2026-11-04 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0269 (brief #539), which stays `Proposed` for the maintainers' decision; SPEC-0043 rule 27 lists the builds that apply
these items. The paths: `docs/specs/0009-facts.md`, `docs/specs/0011-inbox-and-report.md`,
`docs/specs/0018-each-brief-declares-a-size-and-expected-hours-compared-with-actual.md` and `docs/guides/planning.md`
(new). The number 115 is the one the conductor reserved on #539; 113 and 114 are the intakes of #536 and #538. This intake
applies none of the items: each is applied by the build named below, with its own ADR, and an item that changes an Approved
spec needs a person's `Approve:` line for that spec on that build's pull request; no session posts it. No rule changes for a
project without `docs/plan/`, and no safety rule weakens: each item adds the planning case beside the rule as it stands.

1. **SPEC-0009, the facts carry every brief (build (e)) and the optional `plan` key (build (f)).** The flow section's
   `briefs` list (SPEC-0034 rule 10), which today holds the open brief issues with `number`, `title`, `created_at` and
   `advances`, gains the ones closed in the facts' `--weeks` window (rule 14's window) and, for
   each, the optional fields `state` (`open` or `closed`), `closed_at`, `state_reason` (`completed`, `not_planned` or
   `unknown`), `milestone` (the `Milestone:` line, or `null`), `size` and `expected` (the `Size:` and `Expected:` lines read
   as SPEC-0018 rule 2, `unknown` when missing or malformed). `schema` stays 1: a facts document without them reads
   `unknown`, and every existing reader that counts open briefs filters on `state` `open`, so its output is unchanged.
   Rule 3, which fixes the top-level keys, gains one optional key, `plan` (SPEC-0043 rule 19: the `--json` output of
   `plan_status.py`, written only by `plan_status.py --into` and only in a project with `docs/plan/milestones.md`), and
   `kit/facts-schema.json`, whose top level sets `additionalProperties: false`, gains `plan` under `properties` and not
   under `required` (build (f)); `facts.py` itself never writes it. Rule 3's list on the default branch does not name
   `kit_version`, `flow` and `shadow`, which `facts.py` and the schema already carry; this item adds only `plan`.
2. **SPEC-0011, the plan in the report and the inbox (build (f)).** Rule 3, the inbox, gains two kinds after
   `requirement`, each built only from the facts' optional top-level key `plan` (SPEC-0043 rule 19): `scope-change`
   (`Scope change SC-<n> waits for approval`, sorted by number) and `plan` (`The plan of <head12> waits for its
   confirmation`). Rule 10, At risk, gains one line per milestone whose status is `at risk` or `late`, after the existing
   lines: `Milestone M<n> "<title>" is <status>: P85 <date> after target <date>; <cause>`. Rule 8 is unchanged: still
   five sections and no other. Rule 2 is unchanged: the renderer reads one file, which, in a project with a plan, is the
   facts with the `plan` key that `plan_status.py --into` writes; rule 15 gains one step in `product-report.yml`, run
   after `facts.py` and only when `docs/plan/milestones.md` exists, that makes the plan's facts with `facts.py --weeks 12`
   and runs `plan_status.py --facts PLAN --weeks 12 --base IN --into OUT` (SPEC-0043 rules 12 and 19), and rule 57's uploaded file is that one file.
   The SPEC-0022 rules of the file gain the kinds `milestone-at-risk`, `scope-change` and `plan-confirmation` in the
   closed list of rule 70, and `report.json` `schema` rises to 4 (rule 72). A report of facts without `plan` is
   byte-identical to today's in `report.md`, and in `report.json` apart from `schema` (3 to 4), which the goldens of
   build (f) show (SPEC-0043 rule 19).
3. **SPEC-0018 rule 7 (build (f)).** "The kit makes no estimate, applies no buffer and uses no model." becomes "The metrics
   and the product report make no estimate, apply no buffer and use no model; a milestone's range is made only by
   `plan_estimate.py` (SPEC-0043 rules 12 to 16) from the project's measured history, and the report prints it from the
   facts as it is." The rest of rule 7 is unchanged, and so are rules 3 and 6: the Cost line and its `estimate: N of M
   within range` ending do not change. REQ-025 AC7 is not edited (an intake only appends to the requirements file); whether
   it needs a new text is the owner's (`Q-S0043-14`).
4. **`docs/guides/planning.md` (build (j)), new.** The guide says, in plain words: what the sources folder holds and that
   the person converts and cleans the documents; that a design is read only through the person's connector and only the
   named frames; how to run the skill, `validate`, `render`, the confirmation and `publish`; how to read an estimate, its
   inputs and the word `uncalibrated`; the status rule; the scope-change record and its approval; the iteration and the four
   ceremony outputs; and the four limits of SPEC-0043 rule 26. `docs/guides/reference.md` gains the `[plan]` settings and
   the five commands.
5. **Tests.** Build (e): a facts fixture with open and closed briefs gives the new fields, and the flow totals of the
   report are unchanged. Build (f): the report goldens of projects without a plan are byte-identical; a fixture with a plan
   gives the At risk line and the two inbox kinds; `report.json` validates against `kit/report-schema.json` at schema 4;
   the REQ-025 tests of rule 7 still pass (`product_report.py` holds no estimate). Build (j): a test reads the guide for the
   four limits. Their marker is `REQ-050`.
