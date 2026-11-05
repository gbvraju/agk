"""A fake pytest-xdist of a kit fixture (SPEC-0044 rule 6), invented and never installed.

With `-n N` (N above 1) it runs the fixture's `check_*.py` files in N child pytest processes,
split by file, prints their summed counts and returns the worst exit code; without it pytest runs
as usual. It lies on the fixture's own path, so `import xdist` succeeds there with no install.
"""

from __future__ import annotations

import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

COUNT = re.compile(r"(\d+) (passed|failed|skipped)")
KINDS = ("failed", "passed", "skipped")


def pytest_addoption(parser):
    parser.getgroup("xdist")._addoption("-n", "--numprocesses", dest="numprocesses", type=int)


def counts(output: str) -> dict[str, int]:
    lines = [line for line in output.splitlines() if COUNT.search(line)]
    found = dict.fromkeys(KINDS, 0)
    for number, kind in COUNT.findall(lines[-1] if lines else ""):
        found[kind] = int(number)
    return found


def pytest_cmdline_main(config):
    workers = config.getoption("numprocesses")
    if not workers or workers < 2:
        return None
    files = sorted(str(p) for p in Path(config.rootpath).glob("check_*.py"))
    groups = [files[i::workers] for i in range(workers) if files[i::workers]]
    children = [
        subprocess.Popen(  # nosec B603 - fixed argument list, no shell
            [sys.executable, "-m", "pytest", "-q", *group],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for group in groups
    ]
    total = dict.fromkeys(KINDS, 0)
    codes = []
    for child in children:
        output, _ = child.communicate()
        for kind, number in counts(output).items():
            total[kind] += number
        codes.append(child.returncode)
    shown = ", ".join(f"{total[kind]} {kind}" for kind in KINDS if total[kind])
    print(f"{shown} (fake xdist, {len(groups)} workers)")
    return max(codes)
