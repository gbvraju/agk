# Proposed spec amendments 47 (SPEC-0002 rule 5; issue #147)

Date: 2026-10-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0090. The path: `docs/specs/0002-agk-adopt.md`.

1. **SPEC-0002 rule 5, the commands in CI.** The governance workflow's `Project tests` step (`make -f agk.mk agk-project-test`) runs only where the kit's own suite is not installed, that is where `kit/agk-kit.mk` is absent
   (`if: ${{ hashFiles('kit/agk-kit.mk') == '' }}`, which reads the tree and not the name of the repository). In a project nothing changes. In the kit repository `Tests of the checks` runs the suite once; the proof
   workflow is not changed and still runs `project_tests`.
