"""This repository's `proof_timeout` keeps headroom over its measured full suite (ADR-0282).

Brief #568. Kit-only: an adopter keeps the default of `common.DEFAULT_CONFIG` until `doctor.py`
suggests otherwise (SPEC-0044 rule 9), so this test reads only the kit repository's `agk.toml`.
"""

from __future__ import annotations

import math
import sys
import tomllib

from conftest import KIT_ROOT

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import common  # noqa: E402

# The slowest full suite measured on a builder's machine on 2026-11-05 (#565, #567), in seconds.
MEASURED_FULL_SUITE = 1161


def headroom(seconds: int) -> int:
    """SPEC-0044 rule 9 and ADR-0258: ceil(n x 1.5 / 60) x 60."""
    return math.ceil(seconds * 1.5 / 60) * 60


def test_req051_ac5_the_repository_sets_proof_timeout_with_headroom_over_the_measured_suite():
    """REQ-051 AC5: a later lowering below the headroom of the measured suite is caught."""
    data = tomllib.loads((KIT_ROOT / "agk.toml").read_text(encoding="utf-8"))
    assert "proof_timeout" in data, "agk.toml sets no top-level proof_timeout"
    assert data["proof_timeout"] >= headroom(MEASURED_FULL_SUITE) == 1800
    assert common.proof_timeout(KIT_ROOT) == data["proof_timeout"]


def test_req051_ac5_the_default_for_adopters_is_unchanged():
    """REQ-051 AC5: brief #568 answer 1, no default in code and no kit template changes."""
    assert common.DEFAULT_CONFIG["proof_timeout"] == 900
    template = (KIT_ROOT / "kit" / "templates" / "agk.toml").read_text(encoding="utf-8")
    assert "proof_timeout = 1800" not in template
