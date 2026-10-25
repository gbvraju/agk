"""kit/pipeline-schema.json defines schema 1 of the pipeline document (SPEC-0036 rule 2)."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema_lite import errors

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "kit" / "pipeline-schema.json").read_text(encoding="utf-8"))
HEAD = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
URL = "https://github.com/acme/widgets/pull/7"
GOOD = {
    "schema": 1,
    "as_of": "2026-10-25T10:00:00Z",
    "ready": [{"number": 7, "summary": "A person can see the queue.", "url": URL}],
    "approve": [
        {"number": 8, "spec": "SPEC-0036", "spec_title": "A plain title", "url": URL},
        {"number": 9, "spec": "unknown", "spec_title": "unknown", "url": URL},
    ],
    "counts": {"review": 1, "fix": 0, "ci-red": 0, "conflict": 0, "approve": 2, "ready": "unknown"},
}


def test_a_good_document_validates():
    assert errors(GOOD, SCHEMA) == []


def test_schema_one_has_no_sha_and_no_extra_field():
    for mutate in (
        lambda d: d.update(sha=HEAD),
        lambda d: d["counts"].update(extra=1),
        lambda d: d["counts"].pop("fix"),
        lambda d: d["ready"][0].update(sha=HEAD),
        lambda d: d["approve"][0].update(verdict="x"),
        lambda d: d.update(schema=2),
        lambda d: d["counts"].update(fix="many"),
        lambda d: d["ready"][0].update(summary=""),
    ):
        bad = json.loads(json.dumps(GOOD))
        mutate(bad)
        assert errors(bad, SCHEMA), bad


def test_the_schema_is_not_installed_verbatim():
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "kit/pipeline-schema.json" not in json.dumps(manifest.get("verbatim", []))
