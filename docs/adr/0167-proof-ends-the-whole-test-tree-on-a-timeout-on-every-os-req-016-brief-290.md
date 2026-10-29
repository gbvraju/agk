# ADR-0167: proof ends the whole test tree on a timeout, on every OS (REQ-016, brief 290)

- Status: Proposed
- Date: 2026-10-29
- Deciders: maintainers
- Related: ADR-0021
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #290 (priority 0). `scripts/agk/proof.py` started the test command with `start_new_session=True` and, on a timeout,
called `os.killpg(proc.pid, signal.SIGKILL)`. Native Windows Python has neither `os.killpg` nor `signal.SIGKILL`, so on a
Windows pilot (Windows 11, Git Bash, Python 3.13) the timeout handler itself raised an AttributeError: the test tree kept
running and the run never reported `unknown`. Windows is a supported platform (#263). The tests were written first
(checkpoint on this pull request): 12 of `tests/kit/test_proof_timeout.py` failed on the unchanged tree.

## Decision

1. **Process group (answer 1).** On POSIX the run starts a new session and a timeout sends SIGKILL to its process group, as
   before. On Windows the run starts with the `CREATE_NEW_PROCESS_GROUP` creation flag and a timeout runs
   `taskkill /T /F /PID <pid>`, which ends the shell and its descendants; when taskkill fails, is missing or does not answer
   within 30 s, the shell itself is killed. Standard library only. The output left after the kill is read with a 30 s bound,
   so a process outside the tree that holds the output open cannot hang proof. The OS is read once (`os.name == "nt"`) and
   passed in, so both branches are tested on any OS with a fake process and a fake `taskkill`; no test sleeps over 1 s.
2. **The message (answer 2).** The one output line of a timeout reads `proof: unknown (timeout after N s, setting:
   proof_timeout)`, where N is the whole seconds the run took, and a note on standard error says the run was ended at the
   limit set by `proof_timeout` in `agk.toml` and that the tests did not fail, they did not finish. The `reason` of
   `--json` stays `timeout` (SPEC-0010 rule 17), so the `outcome: unknown (timeout)` step name, `facts.py` and the product
   report read it as before.
3. **The guide (answer 3).** The existing-codebase guide says to run proof alone when it nears its limit on a busy machine,
   that raising `proof_timeout` is a protected change, and that a slow suite is better fixed (#289).

## Consequences

- A proof that times out reports `unknown` on Windows too, and leaves no test process of its tree running.
- A process that leaves the tree on purpose (a daemon that detaches, or a container that a client started and that a
  container engine runs) is not ended by either branch; the brief's "no orphaned containers" holds only for containers the
  tree itself runs as its processes.

## Residual

- 2026-10-29: the Windows branch is tested with fakes only; a run on native Windows is the pilot's to confirm.
- 2026-10-29: Q-290-1 (on the pull request): whether SPEC-0010 rule 13 needs an amendment for the timeout line's wording.
