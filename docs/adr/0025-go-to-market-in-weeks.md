# ADR-0025: go to market in weeks; the portal is built with AGK

- Status: Accepted
- Date: 2026-10-16
- Deciders: maintainers
- Amends: ADR-0021
- Related: ADR-0020, SPEC-0013
- Requirements: REQ-018, REQ-020

## Context

K4 specs were Approved two weeks early and the facts engine merged three weeks early. The maintainers set the goal
that AGK reaches its first outside users in weeks, as a Claude add-on for teams and consulting firms that build with
coding agents, and recorded a positioning review (overlap with spec-driven tools, unproven value, unmeasured cost) and
a portal design. This ADR fixes those decisions so every brief and review follows one plan.

## Decision

1. **Claude only.** AGK is an add-on for Claude Code. Other coding agents are out of scope until a later ADR.
2. **Positioning.** AGK is the governance and proof layer for agent-built software: decisions recorded, checks
   enforced, delivery proven, drift measured, a weekly report for the product owner. It does not compete on
   generating code from specs and should layer on tools that do.
3. **Dates (ADR-0021 decision 7 amended; 2026-12-31 stays the hard limit for K4):**

   | Work | Target |
   |---|---|
   | SPEC-0010 proof checks (C1 #58, C2 red-then-green) merged | 2026-10-24 |
   | SPEC-0011 inbox and weekly report merged; the pilot repository upgraded to it | 2026-10-31 |
   | Pilot report weeks for criterion a (two consecutive ISO weeks) | 2026-11-02 to 2026-11-15 |
   | SPEC-0012 intake and SPEC-0013 playbook (`/agk:start`, architect role, `/agk:ruleset`, templates, lifecycle checks) merged | 2026-11-07 |
   | Criterion g run (decision 6) | from 2026-11-09 |
   | Launch minimum: README, product-owner guide, one-page security posture, existing-codebase playbook path | 2026-11-20 |
   | Friends launch | 2026-11-27 |
   | K4 closed | 2026-11-30 |

   A slipped row moves the rows after it; no row is dropped or shortened to keep a date, and no check, fix list or
   clearance is skipped for speed.
4. **Nothing else before launch.** Only the rows above and the "before launch" residuals are built before the friends
   launch. Every other candidate in the residual register waits for the K5-opening ADR.
5. **The portal (K5 headline).** A light web portal over AGK for consulting firms and their clients: sign in with
   GitHub; create a project (repository, AGK installed, ruleset applied, kickoff drafted); roles are three GitHub teams
   per project; role homes (Needs you, This week, Ask for something, Review queue, All projects); themeable for the firm
   or the client. It reads only the facts document and writes only GitHub actions through a GitHub App; it stores
   nothing but sign-in sessions; the repository stays the only source of truth. The Claude credential belongs to the
   party the statement of work names and is added by that party as a GitHub secret; the portal never holds it. SSO
   (JumpCloud first) comes later, mapped onto the same GitHub teams. Slices: read-only, then actions, then SSO.
6. **The portal is built with AGK, and that run is criterion g.** The portal starts in its own new repository from a
   written problem statement, through `/agk:start`, the architect session, one Approved spec and one brief, to its
   first governed merged pull request. This replaces the "second fresh fork" of ruling Q-K4-100: a new product from
   nothing is the stronger test, and it is a third language (TypeScript). The record lives in the portal's repository;
   this repository records the outcome only and does not name it. Beyond its first merged pull request, the portal
   builds only its read-only slice until criterion a is met.
7. **Model choice by work size** is a K5 item: a fixed table, deterministic, the model recorded per pull request so
   the saving is measured.

## Consequences

- Criterion a now depends on the weekly report reaching the pilot by 2026-11-02; if SPEC-0011 slips, criterion a and the
  launch move with it.
- The maintainers act as product owner for both the pilot and the portal, so "repeatable by someone else" is not proven
  in K4; it is the first ask of the friends launch (residual).
- The positioning risks and K5 candidates live in the residual register with due dates, so the drift audit and the
  weekly report surface them; they are not forgotten and not built early.

## Residual

- 2026-10-16: the comparison with spec-driven tools is not yet written; launch claims wait for it (due 2026-12-31).
- 2026-10-16: the cost of the method is not yet measured against work done without it (due 2027-01-31).
