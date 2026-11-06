# AGK's delivery playbook (draft)

Status: draft, documents only. Written 2026-11-06 for brief #596 (owner decision of 2026-11-06, tracked in #595).
It writes down how AGK builds AGK, so the strategy is not lost and can later become a SPEC-0038 playbook. It decides
nothing: a practice is only as binding as the rule, spec or decision it cites. It holds no data from any customer
project, and every example in it is invented.

## How to read it

Each practice has four lines:

- **What:** the practice in one or two plain sentences.
- **Why:** the measured or observed reason. A reason that is only expected is marked `expected`.
- **Source:** the ADR, spec rule, session rule or pull request that made it, checked against the files on main on
  2026-11-06. A source that could not be found there is marked `(verify)`.
- **State:** `in force` (written in a merged rule, spec or ADR) or `conductor routine` (practised by the conductor and
  the owner, not yet written in an AGK rule).

An issue number such as #542 is a plan or brief on GitHub; a pull request number is one that merged unless it says
otherwise.

## 1. Waves and the freeze

**What:** Work is cut into four waves, each ending in a release, and the requirement set is closed at REQ-051. A new
idea goes to a parking list and is not built before the last wave unless it fixes a red default branch or a security
hole. The owner can rule an exception: REQ-052 (each kind of work runs on the model it needs) was added that way.

**Why:** the owner asked for a lighter AGK and faster delivery (plan #542). A closed set lets four builders work in
parallel without the target moving. The plan's wave lengths (5 to 8 working days for four waves) are `expected`: they
are uncalibrated ranges, to be recalibrated after wave 1.

**Source:** plan #542, sections 1, 4 and 6; `docs/requirements.md` (REQ-051, REQ-052); tracker #595, section 2.

**State:** conductor routine. The plan is an issue, not a rule of the kit.

## 2. The queue order

**What:** Work that unblocks other work goes first. A red default branch outranks everything: its fix is priority 0 and
runs first, and it is the one pull request that may merge while the branch is red. A running job is never interrupted.

**Why:** a blocked builder waits for nothing it could not have avoided, and a red branch stops every merge. The owner
ruled the red-branch order on 2026-11-03 (Q-S0040-2).

**Source:** SPEC-0040 rule 5 and amendment 117 (the order of heavy-run jobs; an unblocker goes before others of the
same priority); SPEC-0039 rule 5, amendment 123 (the red-branch fix); SPEC-0034 rule 3 (briefs are taken by `Priority:`
and by `Depends-on` being closed).

**State:** in force for heavy-run jobs and for taking briefs. The "unblockers first" habit for briefs, beyond
`Priority:`, is a conductor routine. This repository keeps the queue itself off (`agk.toml`, `[flow]`).

## 3. Small builds, tests first

**What:** A build is about 400 to 600 changed lines, and a larger one is split into builds that each stand alone.
Every build writes its tests first, and a session never marks anything done.

**Why:** a small change is reviewed in one pass and conflicts less. The specs state their own limits: about 300
(SPEC-0045), about 400 (SPEC-0044) and about 600 (SPEC-0038, SPEC-0034) changed lines. The hours per build in plan #542
(1 to 3 hours from brief to Report) are `expected`.

**Source:** `CLAUDE.md item 4`; principle 10; the "builds, in order" rule of each spec (SPEC-0038 rule 12, SPEC-0044
rule 12, SPEC-0045 rule 10); session rule 7 (checkpoints).

**State:** tests first is in force. The size figure is in force per spec; the single range of 400 to 600 and "split when
larger" are a conductor routine (`(verify)`: no rule states one range).

## 4. One decision record per requirement

**What:** A requirement gets one ADR at intake. Each build of its Approved spec carries a `Covered-by: ADR-nnnn` line
naming that ADR and records its own choices under `Decisions taken:`. A new ADR is written only when a build changes a
decision.

**Why:** the plan expects about a third less document work per build and fewer status commits. That figure is
`expected`, not measured.

**Source:** ADR-0271; session rule 36; `CLAUDE.md item 3` (the build of an Approved spec); plan #542, section 2, rule 2.

**State:** in force.

## 5. The verdict flow

**What:** A reviewer posts a fix list on a head. The builder fixes it and pushes. A `Final` line clears the exact head
it names. A session acts only on a verdict that names its current head, so a new push needs a new verdict. A `Final`
that accepts an ADR is the acceptance itself and no status commit follows.

**Why:** a verdict on one head says nothing about the next. Skipping the status commit removes a push that would
otherwise need its own clearance (#558).

**Source:** session rule 1; SPEC-0021 rule 3a (amendment 118, ADR-0277); #558; `scripts/agk/check_final_clearance.py`.

**State:** in force.

## 6. Merging

**What:** The conductor merges a cleared pull request through one command, `merge_cleared.py`, and nothing else
merges. The command holds, for a person, a release, a spec approval (`Approve:`), a change under `constitution/`,
`config/reviewers.yaml`, the ruleset files or `.github/workflows/`, a hold label, a draft, an unmet `Depends-on`, a
conflict, and everything while the default branch is red or the kit is paused. After a merge it runs governance and
stops on red.

**Why:** the owner's hands are kept for decisions, not for routine merges. The hold list is the set of changes where a
wrong merge is expensive to undo.

**Source:** SPEC-0039 (rules 2 to 6); principle 2; session rule 2; #533 (the command), #535 (auto-merge on for this
repository), #556 (governance after the merge), #572 (a head whose checks still run is held), #577 (the merged body
reaches the after-merge run).

**State:** in force. Auto-merge is on for this repository (`agk.toml`, `[flow] auto_merge = true`).

## 7. Conflicts

**What:** Each log entry is its own file, so two builds rarely touch the same lines. A builder runs
`session.py push-check` before a push; on a conflict it merges the default branch, never rebases or force-pushes, and
keeps both sides of an appended line. It resolves only a mechanical conflict; any other conflict ends the work with
one comment. It runs governance before it pushes.

**Why:** the old single decisions log was the most common shared file. #558 gave each new row its own file under
`docs/runs/decisions/`.

**Source:** #558; session rules 15 and 31; `CLAUDE.md` (compaction recovery).

**State:** in force.

## 8. Testing

**What:** Before a push, a builder runs the change's own tests and the tests it can affect. The full suite runs on the
default branch and on every release. A full run has a time limit of 1800 seconds, per-file timing is recorded, and
parallel workers are available but off by default.

**Why:** the measured full suite outgrew the old 900-second limit (#571). The tracker records the pre-push tests step
at 41 seconds on a one-script change, against a 900-second cut-off before the change (#581, tracker #595, section 3).

**Source:** ADR-0285 and #581 (own and affected tests); #571 (the limit); #564 (timing); #585 (workers); SPEC-0044;
plan #542, REQ-051.

**State:** in force. The smoke run by change kind and the suggested time limit are SPEC-0044 builds still queued.

## 9. The heavy-run queue

**What:** A builder hands a heavy run (governance, a full suite) to a first-in, first-out queue and keeps developing
instead of waiting on the heavy lock. The queue's order is a setting, and batching never lowers a gate.

**Why:** waiting on the lock idles a builder (intake #520). The plan keeps only the runner and the `--queue` option,
and parks the rest until the test-time work has shown how much waiting is left.

**Source:** SPEC-0040 rules 1, 4 and 5; #520 (intake), #552 (runner); plan #542, section 3.

**State:** in force as a kit feature. This repository has it switched off (`agk.toml`, `[flow]`); `(verify)` whether
`--queue` on `prepush` and `proof` is on main (not read in full for this draft).

## 10. Model by task

**What:** The strongest model does design, security, merge-path, intake and every review. A mid-tier model does small
or mechanical follow-ups. A session moves up a tier when the same check fails twice or a conflict cannot be resolved.
Lean prompts and a usage line in every `Report:` come with SPEC-0045.

**Why:** cost falls without any loss of speed or quality, because a tier never removes a check, test, review or gate.
The saving is to be measured one week after the SPEC-0045 builds land (`expected` until then).

**Source:** SPEC-0045 rules 1, 2, 5 to 9 (intake #592, ADR-0289); tracker #595, section 2.

**State:** SPEC-0045 is Approved on main, but its builds (b) to (d) are not built. Until then the tier rule is a
conductor routine (the interim policy in use since 2026-11-06).

## 11. The `Flow:` line

**What:** Every pull request body names the design criteria it serves on a `Flow:` line, one or more of `fast`,
`governed`, `secured`, `quality`.

**Why:** it makes each change answer the plan's north star: faster, safer, better in quality or better governed,
without adding waiting.

**Source:** `(verify)`. The north star and its drift test are in plan #542; no rule, spec or check on main names a
`Flow:` line (SPEC-0034's `[flow]` is the unrelated flow-mode setting). Brief #596 asks for the line.

**State:** conductor routine.

## 12. Security

**What:** A session never touches a secret. Nothing in a check calls the network, and no scanner's ignore list grows.
The data guard keeps secrets and personal data out of agent sessions. The secret scan reads every commit of the branch,
so a secret removed in a later commit is still found; the cure is to rebuild the branch as one clean commit. Examples,
fixtures and guides use invented data only.

**Why:** a secret in history stays in history. A scan of the final tree would miss it.

**Source:** principle 9; session rules 2 and 31 (secret scan over the branch's commits); `CLAUDE.md item 5`; SPEC-0042
(layer 2, the redacting log reader, `guard_logs.py`, is on main; the other layers are wave 2 builds).

**State:** in force. The "rebuild as one commit" step is a conductor routine `(verify)`: no file on main states it.

## 13. Weekend cleanup

**What:** After each Saturday drift audit, one cleanup brief removes unused code and tests, on the mid-tier model with
all tests still passing. Removing a file or a public function needs the owner's OK in that pull request. The audit
itself never deletes anything. A test is removed only when it is proven covered elsewhere.

**Why:** the audit could list unused code, but it was switched off for this repository, so nothing was found
(`unused_code = ""`, `coverage = ""` in `agk.toml` today).

**Source:** SPEC-0004 (the drift audit, D9); tracker #595, section 1; #593 and #594 (both open issues, not yet built).

**State:** conductor routine, from 2026-11-07. Not yet in AGK.

## 14. Owner touchpoints

**What:** The owner does four things: posts `Approve:` lines for specs, hand-merges the hold list of practice 6, tags
releases, and takes decisions. Everything else flows without a person. In solo mode the person also posts the
`Confirmed:` comment.

**Why:** these are the steps where an error costs most, and each is, by rule, closed to a session.

**Source:** session rules 2 and 29; SPEC-0039 rule 5; `CLAUDE.md item 1` (a session implements and never decides).

**State:** in force.

## 15. Known lessons

**What:**

- Never reuse a verdict across heads. A verdict names one head.
- Wait on a process id, never on a name match: a name can match a different process.
- A rerun replays the old pull request body, so a corrected body needs a new run.

**Why:** each was seen in practice. They are written here so they are not learned twice.

**Source:** the first is session rule 1 and SPEC-0021. The second and third: `(verify)`, no file on main states them.

**State:** the first is in force. The second and third are conductor routine.

## Becoming a SPEC-0038 playbook

SPEC-0038 rule 2 gives a playbook these parts. The right-hand column is where each practice would go.

| Part of rule 2 | What it holds | Practices of this guide |
|---|---|---|
| `phases` | ordered stages with `after` | 1 (the waves, in order), 5 (fix list, Final, cleared) |
| `split` (`brief_order`, `depends_on`) | the briefs in filing order, with their dependences | 3 (small builds, intake then builds), 4 (one record per requirement), 2 (order of work) |
| `lanes` | brief kinds run in parallel lanes | 10 (kinds: design, review, build, small) |
| `testing` | profile, `always_full`, a code-to-tests `map` | 8 (own and affected tests; the full suite on main) |
| `heavy_steps` | steps run under the heavy lock | 9 (governance, full suite) |
| `gates` | checks and judgements, `owner_only` where only the owner acts | 5, 6, 11, 12, 14 (the hold list as `owner_only`) |
| `evidence` | what a verdict cites | 5, 8 |
| `milestones` (the batching) | `per-brief`, `per-phase` or `per-batch` | 3 (today `per-brief`) |
| `claims` | `measured` needs a record under `docs/runs/`, else `expected` | 1, 3, 4, 10: all `expected` today |

Three limits apply, because a playbook only adds gates and never relaxes one (rule 4):

- Practices 6, 12 and 14 (merging, security and the owner's touchpoints) are governance. They would appear in a
  playbook only as gates, never as settings it controls.
- Practices 1, 11, 13 and 15 stay outside it: the freeze and the parking list are a plan, the `Flow:` line and the
  lessons are working habits, and the weekend cleanup belongs to the drift audit (SPEC-0004).
- Practice 10 stays outside it: the `[models]` table of `agk.toml` (SPEC-0045) is a protected setting, and a playbook
  cannot write it.

Two things block it today. SPEC-0038 rule 1 fixes the work types (`web-app`, `mobile`, `cloud-migration`, `rag-app`,
`mcp-server`, `multi-agent`, `voice-agent`, `pilot`), and none is "AGK building AGK". Also no `config/playbooks/` file
exists on main yet: SPEC-0038 build (a) (the format and its check) is merged, and the playbook builds resume after
wave 4. The step after that is the owner's call.
