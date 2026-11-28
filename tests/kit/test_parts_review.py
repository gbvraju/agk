"""Kit tests: the reviewer's bundle shows each added or changed library with its parts row
(SPEC-0076 rule 8 and rule 15 build (f); brief #2073, ADR-0863; REQ-083).

On saved git trees (invented names, example.com) `review_bundle.parts_lines` lists each direct
dependency a change adds, removes or moves, with its `docs/parts.md` row fenced or `no row in
docs/parts.md`; with no stack chosen it prints the one not-run line; with nothing changed the one
line; it is cut at `review_other_cap`; the same tree gives the same bytes. No network, no `gh`.
"""

from __future__ import annotations

import json
import shutil
import socket
import sys
from pathlib import Path

import pytest
from test_pins import NODE_PARTS, record
from test_review_bundle import bundle as run_bundle
from test_review_bundle import proj, stub, world  # noqa: F401  (the bundle's fixtures)
from test_session import proj as session_proj  # noqa: F401
from test_session import stub as session_stub  # noqa: F401

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import review_bundle  # noqa: E402
from gates import pins  # noqa: E402

STACK = "docs/adr/0002-stack-options.md"
PY_PARTS = "Parts: python 3.12.7 PSF-2.0, examplelib 1.2.3 MIT (verify)."
HEAD = (
    "| Need | Part | Version | Kind | Why | Alternatives considered | Licence | Health (date) "
    "| For the business |\n|---|---|---|---|---|---|---|---|---|\n"
)
TOML = 'default_branch = "main"\n[delivery]\nwork_type = "web-app"\n'


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the bundle opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    for name in ("AGK_BASE", "GITHUB_BASE_REF", "CI"):
        monkeypatch.delenv(name, raising=False)


def row(part: str, version: str, need: str = "padding") -> str:
    cells = (need, part, version, "runtime", "REQ-001", "none", "MIT", "read 2026-11-20", "Pads.")
    return "| " + " | ".join(cells) + " |\n"


def parts_md(rows: str, section: str = "node") -> str:
    return f"# Parts\n\n## {section}\n\n{HEAD}{rows}\nConfirmed by: architect (2026-11-21)\n"


def package(deps: dict[str, str], dev: dict[str, str] | None = None) -> str:
    data: dict = {"name": "shop", "version": "0.1.0", "dependencies": deps}
    if dev:
        data["devDependencies"] = dev
    return json.dumps(data, indent=2) + "\n"


def playbooks(repo) -> None:
    """The work type's playbook, which `pins.records` reads, as `test_pins.project` copies it."""
    shutil.copytree(KIT_ROOT / "config" / "playbooks", repo.root / "config" / "playbooks")


def node_repo(repo, head: dict[str, str | None], base_extra: dict[str, str] | None = None):
    """main holds a chosen `node` stack and `example-web`; the branch makes HEAD's change."""
    playbooks(repo)
    repo.commit(
        {
            "agk.toml": TOML,
            STACK: record(a_parts=NODE_PARTS, status="Accepted", chosen="Option A"),
            "package.json": package({"example-web": "4.21.1"}),
            **(base_extra or {}),
        },
        "base",
    )
    repo.branch("claude/brief-5")
    repo.commit(head, "the change")
    return repo.root


def lines(root: Path, base: str = "main") -> list[str]:
    return review_bundle.parts_lines(root, base)


ADDED = package({"example-web": "4.21.1", "left-pad-example": "1.0.0"})


def test_req083_an_added_part_without_a_row_says_so(repo) -> None:
    root = node_repo(repo, {"package.json": ADDED})
    assert lines(root) == [
        "## Parts",
        "",
        "- package.json: left-pad-example none -> 1.0.0: no parts record",
        "",
    ]
    root = node_repo_with_record(repo, row("example-web", "4.21.1", "web-api"))
    assert "- no row in docs/parts.md" in lines(root)


def node_repo_with_record(repo, rows: str):
    repo.commit({"docs/parts.md": parts_md(rows), "package.json": ADDED}, "record")
    return repo.root


def test_req083_an_added_part_shows_its_row_fenced(repo) -> None:
    root = node_repo(
        repo, {"package.json": ADDED, "docs/parts.md": parts_md(row("left-pad-example", "1.0.0"))}
    )
    out = lines(root)
    at = out.index("- package.json: left-pad-example none -> 1.0.0")
    assert out[at + 1] == "~~~~"
    assert out[at + 3] == row("left-pad-example", "1.0.0").strip()
    assert out[at + 4] == "~~~~"
    assert "- no row in docs/parts.md" not in out


def test_req083_a_version_change_and_a_removal_show_both_sides(repo) -> None:
    root = node_repo(
        repo,
        {"package.json": package({"example-web": "4.22.0"}, dev={"example-lint": "2.0.0"})},
        base_extra={"package.json": package({"example-web": "4.21.1", "example-old": "0.1.0"})},
    )
    out = lines(root)
    assert "- package.json: example-web 4.21.1 -> 4.22.0: no parts record" in out
    assert "- package.json: example-old 0.1.0 -> none: no parts record" in out
    assert "- package.json: example-lint none -> 2.0.0: no parts record" in out


def test_req083_a_move_between_groups_is_listed(repo) -> None:
    root = node_repo(repo, {"package.json": package({}, dev={"example-web": "4.21.1"})})
    assert (
        "- package.json: example-web 4.21.1 -> 4.21.1 (dependencies -> devDependencies): "
        "no parts record"
    ) in lines(root)


def test_req083_nothing_changed_is_one_line(repo) -> None:
    root = node_repo(repo, {"src/app.js": "export const x = 1;\n"})
    assert lines(root) == ["## Parts", "", "- no build file or parts record changed", ""]


def test_req083_a_row_changed_alone_is_listed(repo) -> None:
    root = node_repo(
        repo,
        {"docs/parts.md": parts_md(row("example-web", "4.21.1", "web-api"))},
    )
    out = lines(root)
    assert "- docs/parts.md: example-web 4.21.1" in out
    assert row("example-web", "4.21.1", "web-api").strip() in out


def test_req083_no_stack_chosen_is_the_not_run_line(repo) -> None:
    repo.commit({"agk.toml": 'default_branch = "main"\n', "package.json": package({})}, "base")
    repo.branch()
    repo.commit({"package.json": ADDED})
    assert lines(repo.root) == ["## Parts", "", "- not run parts: no stack chosen", ""]


def test_req083_the_kits_own_tree_is_not_run() -> None:
    """The kit's own repository declares no work type (`pins.skipped`)."""
    assert pins.skipped(KIT_ROOT) == pins.NO_STACK


def test_req083_a_refused_parts_table_names_the_setting(repo) -> None:
    root = node_repo(repo, {"package.json": ADDED, "agk.toml": TOML + '[parts]\nrecord = "x"\n'})
    assert lines(root)[2] == "- not run parts: the [parts] table is refused (setting: parts.record)"


def test_req083_an_unreadable_build_file_is_named_and_the_rest_printed(repo) -> None:
    root = node_repo(
        repo,
        {"package.json": "{ not json", "docs/parts.md": parts_md(row("example-web", "4.21.1"))},
    )
    out = lines(root)
    assert "- package.json: cannot be read" in out
    assert "- docs/parts.md: example-web 4.21.1" in out


def test_req083_a_deleted_build_file_lists_each_dependency_as_none(repo) -> None:
    root = node_repo(repo, {"package.json": None})
    assert "- package.json: example-web 4.21.1 -> none: no parts record" in lines(root)


def test_req083_the_section_is_cut_at_review_other_cap(repo) -> None:
    many = package({f"example-p{i}": "1.0.0" for i in range(9)})  # and example-web removed
    root = node_repo(repo, {"package.json": many, "agk.toml": "review_other_cap = 3\n" + TOML})
    out = lines(root)
    body = out[2:-1]
    added = "none -> 1.0.0: no parts record"
    assert body[:3] == [f"- package.json: example-p{i} {added}" for i in (0, 1, 2)]
    assert body[3] == "[truncated: 7 lines omitted]"


def test_req083_the_same_tree_gives_the_same_bytes(repo) -> None:
    root = node_repo(repo, {"package.json": ADDED, "docs/parts.md": parts_md(row("x", "1"))})
    assert lines(root) == lines(root)


@pytest.mark.parametrize("stack", sorted(pins.STACKS))
def test_req083_every_stack_build_file_yields_a_parts_line(repo, stack: str) -> None:
    """Rule 17 (the class stays closed): a changed build file of each `pins.STACKS` row is shown."""
    build = pins.STACKS[stack][1]
    if stack == "node":
        base, head = package({}), ADDED
        parts = NODE_PARTS
    else:
        base = '[project]\nname = "s"\nversion = "0"\ndependencies = []\n'
        head = base.replace("[]", '["left-pad-example==1.0.0"]')
        parts = PY_PARTS
    playbooks(repo)
    repo.commit(
        {"agk.toml": TOML, STACK: record(a_parts=parts, status="Accepted", chosen="Option A"),
         build: base},
        "base",
    )  # fmt: skip
    repo.branch()
    repo.commit({build: head})
    assert f"- {build}: left-pad-example none -> 1.0.0: no parts record" in lines(repo.root)


def test_req083_the_bundle_puts_parts_after_the_context_and_before_the_brief(request) -> None:
    """The bundle is the gating reviewer's only document (ADR-0430 decision 2)."""
    proj_, stub_, sha = request.getfixturevalue("world")
    out = run_bundle(proj_, stub_, sha)
    assert out.returncode == 0, out.stdout + out.stderr
    text = out.stdout
    at = text.index("## Parts\n\n- not run parts: no stack chosen\n")
    assert text.index("## Operating rules") < at < text.index("## Brief #5")
