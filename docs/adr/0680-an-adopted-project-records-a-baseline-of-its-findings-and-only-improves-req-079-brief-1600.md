# ADR-0680: An adopted project records a baseline of its findings and only improves (REQ-079)

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: SPEC-0072, ADR-0666, ADR-0668, ADR-0669, brief #1600, brief #1586, plan #661
- Requirements: REQ-079

Protected classes this pull request changes: `scripts/agk/` (the new `gates/baseline.py`, `run_gates.py`,
`check_protected_changes.py`, `gates/layers.py` and `gates/python_pack.py`), `tests/kit/` (the new
`test_gate_baseline.py`), `kit/` (`kit/manifest.json`) and `agk.toml` (the `[[testing.map]]` entry). In a project it
adds the files of `config/agk-baseline/`, inside the project's protected `config/`. `kit/hashes.json` is not edited by
hand.

## Context

SPEC-0072 (Approved, REQ-079) rule 12 build (g) builds rule 7: an adopted project, and an upgraded one on the owner's
yes (`Q-S0072-5`), records today's findings of each new check as a baseline and stays green; after that only a new
finding or a rising count fails, a fixed one is printed lower, and a baseline line that rises or a new line in a later
pull request is refused by `check_protected_changes.py` unless an ADR names it. On the default branch at d91eb148
(2026-11-21) no step reports findings per file: each returns path classes (ADR-0666), and `config/` is a protected
class of every project template, so even a lowered baseline would need an ADR.

## Decision

1. A step may report per-file counts: `layers` gives `counts(root, playbook)` (one per disallowed import, and one for
   an unreadable file), and the Python pack fills `{step: {file: count}}` for `lint`, `format` and `type` when the
   runner passes a tally. A step without counts (`pins`, the split-order steps, the pack's `floor`) has no baseline and
   fails as before.
2. The helper `scripts/agk/gates/baseline.py` reads and writes `config/agk-baseline/<gate id>.txt`, the gate id with
   every run of other characters as `-` (a pack step's id is `standards <stack> <step>`). One line `<path> <count>` per
   file with findings, paths with forward slashes, sorted bytewise, so two machines write the same file.
3. `run_gates.py`: for a step with counts and a baseline file, the step passes while no file's count exceeds its line
   (`ok <id> (baseline)`), prints `baseline <id>: a count fell in <n> file(s)` when one falls, and otherwise prints the
   step's own failure lines and one `SPEC-0072 rule 7` line naming `config/agk-baseline/`. Without a file, in
   `mode = "adopt"` it writes the file (empty when there is no finding) and passes, printing `written`; in
   `mode = "init"` the baseline is empty and nothing is written. Output names counts and path classes, never a file
   or a finding's text.
4. `run_gates.py --baseline` writes every missing file and lowers existing lines; it never raises a line and never
   adds one. It is the owner's yes on an upgrade (`Q-S0072-5`: nothing changes on upgrade until the owner runs it) and
   the command the next build runs to commit a lowered baseline (the brief's Q-1).
5. `check_protected_changes.py`: a change set whose only change of a baseline file lowers or removes lines is not a
   protected change of `config/`. A line that rises, a new line, a new file or a deleted file is a failure naming
   `SPEC-0072 rule 7` and `config/agk-baseline/`, unless an ADR of the change set names the file's path or the
   folder; the class rule applies as before. In flow mode, two pull requests that lower one line conflict
   mechanically, resolved by the lower count (session rule 15).

## Consequences

An adopted project goes green on its first run with its findings recorded, and only improves. A lowering commit needs
no ADR; a rise needs one. Nothing existing in the project is rewritten, formatted or moved. The runner writes only in
`mode = "adopt"` and only a missing file.

## Residual

- 2026-11-21: the personal floor runs the runner from build (h), and with it the baseline (due 2027-03-31).
