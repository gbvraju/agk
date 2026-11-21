"""Run the job: `python3 -m <package> <input.csv>`.

It writes one run line with its id and exits non-zero on a failed run; the detail of a failure goes
only to that line, and the person sees a plain message.
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

from . import logs
from .settings import load

PLAIN = "The run failed. Quote run id {id} when you report it."


def run(source: Path) -> int:
    with source.open(encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def main(argv: list[str]) -> int:
    load()
    logs.setup()
    run_id, started = logs.new_id(), time.monotonic()
    try:
        if len(argv) != 1:
            raise ValueError("one input file is needed")
        rows = run(Path(argv[0]))
    except (OSError, ValueError, csv.Error) as exc:
        took = round((time.monotonic() - started) * 1000)
        error = f"{type(exc).__name__}: {exc}"
        logs.line(run_id=run_id, status="failed", ms=took, error=error)
        print(PLAIN.format(id=run_id), file=sys.stderr)
        return 1
    logs.line(run_id=run_id, status="ok", rows=rows, ms=round((time.monotonic() - started) * 1000))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
