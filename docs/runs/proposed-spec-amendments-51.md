# Proposed spec amendments 51 (SPEC-0030, SPEC-0005; REQ-037)

Date: 2026-10-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0100. The paths: `docs/specs/0030-a-conductor-role-reviews-every-pull-request-posts-the-verdic.md`, `docs/specs/0005-kit-installation.md`.

1. **SPEC-0030 rule 2, a second mode of `watch`.** The verdict on #167 ordered it: `session.py watch --merged N [--interval S] [--timeout S]` waits on another pull request alone and ends with `merged #N` or `closed #N` (or `timeout`, exit 3). It reads no comments, so a verdict never ends it. A `Depends-on` or renumber follow-up of a session resumes on that merge without a message. `--pr` and `--merged` are exclusive.
2. **SPEC-0030 rules 3, 4 and 11, the shape function is built with `next`.** `session.py next` applies the shape of rule 4 to the body it reads, so the function `brief_problems` is built in part (a) inside `session.py`; part (b) adds `check_brief.py`, which imports it and adds nothing else to the shape. The tests of the shape for a saved copy stay in part (b).
3. **SPEC-0005, the installed files.** `config/session-rules.md` joins the verbatim files (the working rule of a session), and `scripts/agk/session.py` joins the installed scripts; `kit/manifest.json` lists both and `kit/hashes.json` carries their digests.
