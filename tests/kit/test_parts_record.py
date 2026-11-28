"""Tests of the parts record's draft (SPEC-0076 rules 3, 4, 6, 7 and 11; REQ-083 AC2 and AC3; brief
#2070, ADR-0860).

`parts_record.py draft --proposal FILE` writes `docs/parts.md` once from `kit/templates/parts.md`:
one `## <runtime>` section per runtime of the Accepted stack record, one row per need the steward's
proposal names, each citing a requirement or `engineering`; `stdlib` adds no version and no health;
a stack with no catalogue marks its rows `catalogue: none`; a candidate that misses the floor
(`[parts]` `max_age_months` and `advisories`, the licence list, a deprecated or archived status) is
dropped and the next kept; the person is asked only rule 7's four kinds, each one plain question
that passes `steward_owner.question_problem`. Every refusal writes nothing and names the rule and the
key, never a value. Health values need the recorded `Setup: web-research: yes`. `rows(text)` reads
the table back. Fixtures in `tmp_path` only: invented data (`example.com`); the socket module is
blocked for the whole file.
"""

from __future__ import annotations

import json
import re
import shutil
import socket
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import steward_owner  # noqa: E402

try:
    import parts_record as pr  # noqa: E402
except ImportError:  # before the module exists every test fails, not the collection
    pr = None

RECORD = "docs/parts.md"
TODAY = "2026-11-28"
SECRET = "zz-never-echoed"

STACK = """# ADR-0003: Stack options

- Status: {status}
- Date: 2026-11-20
- Deciders: maintainers

## Decision

1. **Options**
   - Option A — Booking web app (recommended). Trade-offs: Cost: low; Build speed: quick; Security: usual; Uptime: \
good. Why: the booking page. Parts: {parts}. External services: mail.example.com.
3. **Chosen**: Option A
"""
NODE_PARTS = "Node.js 22.11.0 MIT, PostgreSQL 17.2 PostgreSQL"

CATALOGUE = """format = 1

[[parts]]
need = "web-api"
name = "fastify"
pick = "recommended"
when = "a small JSON service"
trade_offs = "fast, with a smaller plugin set"
licence = "MIT"
source = "https://example.com/catalogue/fastify (accessed 2026-11-20)"
reviewed = "2026-11-20"

[[parts]]
need = "web-api"
name = "express"
pick = "alternative"
when = "a team that knows it already"
trade_offs = "the most known, slower to grow"
licence = "MIT"
source = "https://example.com/catalogue/express (accessed 2026-11-20)"
reviewed = "2026-11-20"
"""

HEALTH = {
    "kind": "runtime",
    "version": "5.1.0",
    "released": "2026-10-02",
    "licence": "MIT",
    "advisories": "none",
    "last_release": "2026-10-02",
    "status": "maintained",
    "adoption": "4 million weekly downloads",
    "scorecard": "7.4",
    "source": "https://example.com/registry/fastify",
    "read": "2026-11-27",
}


def toml_value(value) -> str:
    return json.dumps(value) if not isinstance(value, bool) else str(value).lower()


def proposal_text(needs: list[dict]) -> str:
    out = []
    for need in needs:
        out.append("[[needs]]")
        out += [f"{k} = {toml_value(v)}" for k, v in need.items() if k != "candidates"]
        for cand in need.get("candidates", []):
            out.append("[[needs.candidates]]")
            out += [f"{k} = {toml_value(v)}" for k, v in cand.items()]
        out.append("")
    return "\n".join(out)


def candidate(name: str, **changes) -> dict:
    return {"name": name, **HEALTH, "source": f"https://example.com/registry/{name}", **changes}


def web_api(*cands: dict, **extra) -> dict:
    return {
        "need": "web-api",
        "cites": "REQ-001",
        "business": "Lets the booking page ask for free times.",
        **extra,
        "candidates": list(cands) or [candidate("fastify")],
    }


TIME = {"need": "time", "cites": "engineering", "business": "Shows times in the customer's zone.",
        "part": "stdlib"}  # fmt: skip


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("parts_record opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


class Memory:
    """A stub of the memory issue: each posted body is kept, nothing leaves the test."""

    def __init__(self) -> None:
        self.posted: list[str] = []

    def __call__(self, method, endpoint, fields=None):
        self.posted.append((fields or {}).get("body", ""))
        return {"id": len(self.posted) + 10, "body": (fields or {}).get("body", ""),
                "created_at": "2026-11-28T00:00:00Z", "number": 7}  # fmt: skip


def project(tmp_path: Path, monkeypatch, *, research: str | None = "yes", parts: str = NODE_PARTS,
            status: str = "Accepted", settings: str = "", catalogue: bool = True) -> Path:  # fmt: skip
    root = tmp_path / "proj"
    write(root, "agk.toml", f'[delivery]\nwork_type = "web-app"\n{settings}')
    write(root, "docs/adr/0003-stack-options.md", STACK.format(status=status, parts=parts))
    write(root, "docs/requirements.md", "# Requirements\n\n- REQ-001: book a time\n- REQ-002: pay\n")
    write(root, "kit/templates/parts.md", (KIT_ROOT / "kit/templates/parts.md").read_text("utf-8"))
    write(root, "config/parts/needs.toml", "")
    shutil.copy(KIT_ROOT / "config/parts/needs.toml", root / "config/parts/needs.toml")
    if catalogue:
        write(root, "config/parts/node.toml", CATALOGUE)
    comments = []
    if research is not None:
        comments.append({"id": 1, "body": f'Setup: web-research: {research} because the person said '
                         f'"{research}" at 2026-11-27T10:00Z', "created_at": "2026-11-27T10:00:00Z"})  # fmt: skip
    cache = tmp_path / "memory.json"
    cache.write_text(json.dumps({"issue": 7, "comments": comments}), encoding="utf-8")
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(cache))
    return root


def draft(root: Path, needs: list[dict], memory: Memory | None = None) -> tuple[int, list[str]]:
    assert pr is not None, "scripts/agk/parts_record.py is missing"
    path = root.parent / "proposal.toml"
    path.write_text(proposal_text(needs), encoding="utf-8")
    return pr.draft(root, path, TODAY, memory or Memory())


def questions(lines: list[str]) -> list[str]:
    return [ln.removeprefix("question: ") for ln in lines if ln.startswith("question: ")]


def section(root: Path, runtime: str = "node") -> list[dict]:
    return pr.rows((root / RECORD).read_text(encoding="utf-8"))[runtime]


# --- the record: needs cited, stdlib, the catalogue -----------------------------------------------


def test_ac2_the_draft_writes_one_row_per_need_cited_with_its_reason(tmp_path, monkeypatch):
    """REQ-083 AC2: SPEC-0076 rules 4 and 7 (the record, its columns, `Confirmed by: none yet`)."""
    root = project(tmp_path, monkeypatch)
    memory = Memory()
    code, lines = draft(root, [web_api(), TIME], memory)
    assert code == 0, lines
    text = (root / RECORD).read_text(encoding="utf-8")
    assert "## node" in text and text.rstrip().endswith("Confirmed by: none yet")
    assert pr.COLUMNS == ("Need", "Part", "Version", "Kind", "Why", "Alternatives considered",
                          "Licence", "Health (date)", "For the business")  # fmt: skip
    rows = section(root)
    assert [r["Need"] for r in rows] == ["web-api", "time"]
    api, time = rows
    assert (api["Part"], api["Version"], api["Kind"], api["Licence"]) == (
        "fastify", "5.1.0", "runtime", "MIT")  # fmt: skip
    assert "a small JSON service" in api["Why"] and "REQ-001" in api["Why"]
    assert "express" in api["Alternatives considered"]
    assert "the most known" in api["Alternatives considered"]
    assert "2026-11-27" in api["Health (date)"] and "scorecard 7.4" in api["Health (date)"]
    assert api["For the business"] == "Lets the booking page ask for free times."
    assert (time["Part"], time["Version"], time["Licence"]) == ("stdlib", "none", "MIT")
    assert "engineering" in time["Why"] and time["Health (date)"] == "none (stdlib)"
    assert "example.com/booking" not in text and "Example rows" not in text
    assert memory.posted and memory.posted[-1].startswith("Setup: parts: drafted 2 needs, 0 questions")
    assert questions(lines) == []


def test_ac2_a_stack_with_no_catalogue_marks_each_row(tmp_path, monkeypatch):
    """REQ-083 AC2: SPEC-0076 rule 11 (`catalogue: none`), and a runtime outside the stacks."""
    root = project(tmp_path, monkeypatch, catalogue=False)
    assert draft(root, [web_api()])[0] == 0
    assert section(root)[0]["Why"].startswith("catalogue: none")
    other = project(tmp_path / "go", monkeypatch, parts="Go 1.23.4 BSD-3-Clause, SQLite 3.47.0 blessing")
    assert draft(other, [web_api()])[0] == 0
    assert section(other, "Go")[0]["Why"].startswith("catalogue: none")


def test_ac2_a_scorecard_not_published_is_said(tmp_path, monkeypatch):
    """REQ-083 AC2: SPEC-0076 rule 6 (the scorecard where published)."""
    root = project(tmp_path, monkeypatch)
    cand = candidate("fastify")
    del cand["scorecard"]
    assert draft(root, [web_api(cand)])[0] == 0
    assert "scorecard: not published" in section(root)[0]["Health (date)"]


def test_ac2_a_second_part_for_one_need_takes_a_decision_line(tmp_path, monkeypatch):
    """REQ-083 AC2: SPEC-0076 rule 7 (one part per need, a second with `Decision:`)."""
    root = project(tmp_path, monkeypatch)
    second = web_api(candidate("express"))
    code, lines = draft(root, [web_api(), second])
    assert code == 1 and "key: decision" in lines[0] and not (root / RECORD).exists()
    code, lines = draft(root, [web_api(), {**second, "decision": "the admin pages need its views"}])
    assert code == 0, lines
    text = (root / RECORD).read_text(encoding="utf-8")
    assert "Decision: web-api: the admin pages need its views" in text
    assert [r["Part"] for r in section(root)] == ["fastify", "express"]


# --- the floor (rule 6) ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("settings", "change", "kept"),
    [
        ("", {"last_release": "2025-10-27"}, "express"),  # 13 months: dropped
        ("", {"last_release": "2025-11-28"}, "fastify"),  # 12 months: kept
        ("[parts]\nmax_age_months = 24\n", {"last_release": "2025-10-27"}, "fastify"),
        ("", {"advisories": "high"}, "express"),
        ('[parts]\nadvisories = "critical"\n', {"advisories": "high"}, "fastify"),
        ('[parts]\nadvisories = "critical"\n', {"advisories": "critical"}, "express"),
        ('[parts]\nadvisories = "any"\n', {"advisories": "low"}, "express"),
        ("", {"advisories": "moderate"}, "fastify"),
        ("", {"status": "deprecated"}, "express"),
        ("", {"status": "archived"}, "express"),
    ],
)
def test_ac3_a_candidate_below_the_floor_is_dropped(tmp_path, monkeypatch, settings, change, kept):
    """REQ-083 AC3: SPEC-0076 rules 6 and 9 (`max_age_months`, `advisories`, the status)."""
    root = project(tmp_path, monkeypatch, settings=settings)
    code, lines = draft(root, [web_api(candidate("fastify", **change), candidate("express"))])
    assert code == 0, lines
    assert section(root)[0]["Part"] == kept
    assert questions(lines) == []


def test_ac3_a_licence_off_the_list_is_dropped_and_asked(tmp_path, monkeypatch):
    """REQ-083 AC3: SPEC-0076 rules 6 and 7 (the licence list, never widened)."""
    root = project(tmp_path, monkeypatch)
    write(root, "config/licences.toml", 'allowed = ["MIT"]\n')
    code, lines = draft(root, [web_api(candidate("fastify", licence="GPL-3.0-only"),
                                       candidate("express"))])  # fmt: skip
    assert code == 0, lines
    assert section(root)[0]["Part"] == "express"
    asked = questions(lines)
    assert len(asked) == 1 and "fastify" in asked[0] and "licence" in asked[0]
    assert (root / "config/licences.toml").read_text(encoding="utf-8") == 'allowed = ["MIT"]\n'


def test_ac3_no_healthy_candidate_asks_and_writes_no_row(tmp_path, monkeypatch):
    """REQ-083 AC3: SPEC-0076 rule 6 (when no candidate meets the floor, ask the person)."""
    root = project(tmp_path, monkeypatch)
    code, lines = draft(root, [web_api(candidate("fastify", status="archived")), TIME])
    assert code == 0, lines
    assert [r["Need"] for r in section(root)] == ["time"]
    asked = questions(lines)
    assert len(asked) == 1 and "Serve requests from other programs" in asked[0]


# --- the person's four kinds of question (rule 7) -------------------------------------------------


@pytest.mark.parametrize(
    "change",
    [{"licence": "LicenseRef-Payco-Commercial"}, {"commercial": True}, {"service": "paid"},
     {"service": "data-out"}],  # fmt: skip
)
def test_ac2_each_kind_prints_one_plain_question(tmp_path, monkeypatch, change):
    """REQ-083 AC2: SPEC-0076 rule 7 (paid or commercial, an outside service)."""
    root = project(tmp_path, monkeypatch)
    write(root, "config/licences.toml", 'allowed = ["MIT", "LicenseRef-Payco-Commercial"]\n')
    pay = {"need": "payments", "cites": "REQ-002", "business": "Takes card payments.",
           "candidates": [candidate("payco-sdk", **change)]}  # fmt: skip
    memory = Memory()
    code, lines = draft(root, [web_api(), pay], memory)
    assert code == 0, lines
    asked = questions(lines)
    assert len(asked) == 1 and "payco-sdk" in asked[0]
    assert all(steward_owner.question_problem(q) is None for q in asked)
    assert "1 questions" in memory.posted[-1]
    assert [r["Part"] for r in section(root)] == ["fastify", "payco-sdk"]


def test_ac2_every_question_kind_passes_the_plain_question_check(tmp_path, monkeypatch):
    """REQ-083 AC2: SPEC-0076 rule 7 (one line, a `?`, `I recommend`, no kit term)."""
    assert pr is not None, "scripts/agk/parts_record.py is missing"
    for kind in pr.QUESTIONS:
        text = pr.question(kind, "payco-sdk", "Take card payments")
        assert steward_owner.question_problem(text) is None, kind


# --- refusals: nothing written, no value named ----------------------------------------------------


@pytest.mark.parametrize(
    ("needs", "key"),
    [
        ([{**web_api(), "need": "teleport"}], "need"),
        ([{**web_api(), "cites": "REQ-999"}], "cites"),
        ([{**web_api(), "cites": SECRET}], "cites"),
        ([{k: v for k, v in web_api().items() if k != "business"}], "business"),
        ([web_api(candidate("fastify", source=""))], "source"),
        ([web_api({k: v for k, v in candidate("fastify").items() if k != "read"})], "read"),
        ([web_api(candidate("fastify", read="2026-12-01"))], "read"),
        ([web_api(candidate("fastify", released="2027-01-01"))], "released"),
        ([web_api(candidate("fastify", advisories=SECRET))], "advisories"),
        ([web_api(candidate("fastify", status=SECRET))], "status"),
        ([web_api(candidate("fastify", kind=SECRET))], "kind"),
        ([web_api(candidate("fastify", extra=SECRET))], "extra"),
    ],
)
def test_ac2_a_wrong_proposal_is_refused_writing_nothing(tmp_path, monkeypatch, needs, key):
    """REQ-083 AC2: SPEC-0076 rules 4, 6 and 7 (each refusal names the key, never a value)."""
    root = project(tmp_path, monkeypatch)
    memory = Memory()
    code, lines = draft(root, needs, memory)
    assert code == 1 and len(lines) == 1, lines
    assert f"key: {key}" in lines[0] and SECRET not in lines[0] and "rule" in lines[0]
    assert not (root / RECORD).exists() and memory.posted == []


def test_ac3_health_without_the_research_yes_is_refused(tmp_path, monkeypatch):
    """REQ-083 AC3: SPEC-0076 rule 6 (the person's research permission first)."""
    for research in (None, "no"):
        root = project(tmp_path / str(research), monkeypatch, research=research)
        code, lines = draft(root, [web_api()])
        assert code == 1 and "web-research" in lines[0] and not (root / RECORD).exists()
        assert draft(root, [TIME])[0] == 0  # stdlib reads no health


def test_ac2_the_stack_and_the_record_must_be_ready(tmp_path, monkeypatch):
    """REQ-083 AC2: SPEC-0076 rule 3 (after the stack is Accepted; written once)."""
    root = project(tmp_path, monkeypatch, status="Proposed")
    code, lines = draft(root, [web_api()])
    assert code == 1 and "stack" in lines[0] and not (root / RECORD).exists()
    root = project(tmp_path / "b", monkeypatch)
    write(root, "agk.toml", "[flow]\n")
    code, lines = draft(root, [web_api()])
    assert code == 1 and "delivery.work_type" in lines[0]
    root = project(tmp_path / "c", monkeypatch)
    assert draft(root, [web_api()])[0] == 0
    before = (root / RECORD).read_text(encoding="utf-8")
    code, lines = draft(root, [TIME])
    assert code == 1 and RECORD in lines[0]
    assert (root / RECORD).read_text(encoding="utf-8") == before


def test_ac2_a_refused_parts_table_or_a_proposal_not_toml_writes_nothing(tmp_path, monkeypatch):
    """REQ-083 AC2: SPEC-0076 rule 9 (`parts.record`), and the proposal's form."""
    root = project(tmp_path, monkeypatch, settings='[parts]\nrecord = "always"\n')
    code, lines = draft(root, [web_api()])
    assert code == 1 and "setting: parts.record" in lines[0] and "always" not in lines[0]
    root = project(tmp_path / "b", monkeypatch)
    bad = root.parent / "proposal.toml"
    bad.write_text(f"[[needs]\n{SECRET}\n", encoding="utf-8")
    code, lines = pr.draft(root, bad, TODAY, Memory())
    assert code == 1 and SECRET not in lines[0] and "proposal" in lines[0]
    inside = root / "docs/proposal.toml"
    inside.write_text(proposal_text([TIME]), encoding="utf-8")
    code, lines = pr.draft(root, inside, TODAY, Memory())
    assert code == 1 and "docs/" in lines[0]
    assert not (root / RECORD).exists()


def test_the_usage_exits_2(tmp_path):
    """REQ-083 AC2: SPEC-0076 rule 7 (one command, `draft`)."""
    assert pr is not None, "scripts/agk/parts_record.py is missing"
    assert pr.main([]) == 2
    assert pr.main(["draft"]) == 2
    assert pr.main(["other", "--proposal", "x"]) == 2


# --- the class stays closed (answer 10) -----------------------------------------------------------


def test_only_parts_record_writes_the_record_and_it_imports_no_network_module():
    """REQ-083 AC2: SPEC-0076 rule 6 (files only; one writer of `docs/parts.md`)."""
    writers = [
        p.name
        for p in (KIT_ROOT / "scripts/agk").rglob("*.py")
        if re.search(r"""["']docs/parts\.md["']""", p.read_text(encoding="utf-8"))
    ]
    assert writers == ["parts_record.py"]
    text = (KIT_ROOT / "scripts/agk/parts_record.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(?:import|from)\s+(?:socket|urllib|http\b|requests|ssl)\b", text, re.M)


def test_the_template_holds_the_columns_and_the_last_line():
    """REQ-083 AC2: SPEC-0076 rule 7 (`kit/templates/parts.md`)."""
    assert pr is not None, "scripts/agk/parts_record.py is missing"
    text = (KIT_ROOT / "kit/templates/parts.md").read_text(encoding="utf-8")
    assert "| " + " | ".join(pr.COLUMNS) + " |" in text
    assert "example.com" in text and "Questions for the person:" in text
    assert text.rstrip().splitlines()[-1] == "Confirmed by: none yet"
    assert len(pr.rows(text)["example-runtime"]) == 2
