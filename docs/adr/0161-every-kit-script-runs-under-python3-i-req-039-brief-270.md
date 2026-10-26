# ADR-0161: every kit script runs under `python3 -I` (REQ-039, brief 270)

- Status: Proposed
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0160
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #270 (priority 0). The conductor guard allows Python only as `python3 -I <scratch>/scripts/agk/<name>.py`. Isolated
mode keeps the environment and the current folder from injecting code, and it also leaves the script's own folder off the
import path. So every kit script that imports another (`from common import ...`) failed on its first such import. A project's
conductor met this on 2026-10-27 with `check_brief.py`. The cause was reproduced first, as the brief's `Measured:` line says:
`python3 -I scripts/agk/check_brief.py <the brief's own text>` in the kit repository ended with
`ModuleNotFoundError: No module named 'common'`. The tests were written first (`tests/kit/test_isolated_mode.py`); 42 of them
failed on the unchanged tree.

## Decision

1. **The path line** (answer 1). Each of the 41 scripts under `scripts/agk/` that imports another kit script, at module level or
   inside a function, has one line `sys.path.insert(0, str(Path(__file__).resolve().parent))` before its first kit import. That
   line puts the script's own resolved folder first on the import path, and nothing else: not the current folder, not an
   environment variable, not a relative path. Isolated mode keeps its protection for everything else. `import sys` and
   `from pathlib import Path` are added where a script lacked them. The line is a `sys.path` change between imports, which the
   linter allows (E402).
2. **The tests** (answer 2). Every script with a `main` is run as `python3 -I <script> --help` from an unrelated temporary folder,
   with no standard input, and fails on any import error. A static test checks that each importing script has exactly one path
   line, before every kit import, and that no script changes `sys.path` any other way. The measured `check_brief.py` call runs
   under `-I` and gives its own `ok brief` or `FAIL brief` line.
3. **What does not change** (answer 3). The conductor guard and its allowed forms, the scripts' behaviour when run without
   `-I`, and `.claude/hooks/`, which the brief does not name. `kit/hashes.json` is a release file and is not edited here (session
   rule 14); the next release regenerates it. Flow mode: fragment `changelog.d/isolated-mode.md`, no version bump.

## Consequences

- A conductor, or any session confined to `python3 -I`, can run every kit script from a scratch copy without a hand workaround.
- A new kit script that imports another needs the same line; the static test fails until it has it.

## Residual

- 2026-10-26: the after measurement on the project's conductor (its own `check_brief.py` calls under `-I`) is to be taken
  there; this session can reach no project (due 2026-12-31).
