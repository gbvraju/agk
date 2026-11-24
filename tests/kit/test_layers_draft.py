"""Tests of the layers drafted from an adopted tree (brief #1842, ADR-0767; SPEC-0072 rules 5
and 9; REQ-079).

`layers.py --draft` proposes an adopted project's layers from its own folders, the import
directions used today and a `[testing] map` that fits them, and writes nothing; in `mode = "init"`
it proposes nothing. Answer 6's table holds every writer and reader of the record and of
`[architecture]` under `scripts/agk/`: on an adopted sample whose playbook layers match no file and
whose record holds a marker each refuses or fails, never `ok`, and a new one fails this test.
Fixtures in `tmp_path` only: invented data (example.com), no network (a socket stub raises).
"""

from __future__ import annotations

import re
import shutil
import socket
import subprocess  # nosec B404 - a fixed `git init` and `git status` in a temporary folder, no shell
import sys
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
AGK = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(AGK))

import front_door  # noqa: E402
import playbook_format  # noqa: E402
import run_gates  # noqa: E402
from gates import architecture_record, layers  # noqa: E402

PLAYBOOKS = KIT_ROOT / "config" / "playbooks"
KEY = "(key: architecture.layers)"
TREE = {  # the brief's invented service: one crossing import, core to reports
    "app/__init__.py": "",
    "app/main.py": "from app.core import orders\n",
    "app/core/__init__.py": "",
    "app/core/orders.py": "from app.reports import totals\nSITE = 'https://example.com'\n",
    "app/reports/__init__.py": "",
    "app/reports/totals.py": "import json\n",
    "tests/test_orders.py": "from app.reports import totals\n",
    "docs/tool.py": "",
    "config/tool.py": "",
    ".hidden/tool.py": "",
}
NODE_RECORD = (
    "# ADR-0003: Stack options\n\n- Status: Accepted\n\n"
    "1. **Options**:\n   - Option A — Parts: node 22.11.0 MIT. Why: invented.\n"
    "3. **Chosen**: Option A\n"
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the draft opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def project(
    tmp_path: Path,
    mode: str | None = "adopt",
    work_type: str | None = "api-service",
    tree: dict[str, str] | None = None,
    extra: str = "",
) -> Path:
    root = tmp_path / "svc"
    shutil.copytree(PLAYBOOKS, root / "config" / "playbooks")
    text = f'mode = "{mode}"\n' if mode else ""
    text += extra
    if work_type:
        text += f'\n[delivery]\nwork_type = "{work_type}"\n'
    (root / "agk.toml").write_text(text, encoding="utf-8")
    for rel, body in (TREE if tree is None else tree).items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    return root


def drafted(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = layers.main(["--root", str(root), "--draft"])
    return code, capsys.readouterr().out


def tables(out: str) -> dict:
    return tomllib.loads("\n".join(ln for ln in out.splitlines() if not ln.startswith("draft ")))


# --- answer 1: the draft ------------------------------------------------------------------------


def test_req079_the_draft_of_the_invented_tree_gives_its_three_parts(tmp_path, capsys) -> None:
    """REQ-079: `app` (its loose files), `core` and `reports`; the directions used today."""
    code, out = drafted(project(tmp_path), capsys)
    assert code == 0, out
    assert out.splitlines()[0] == "draft layers: proposal only; a person confirms it"
    data = tables(out)
    got = [(x["name"], x["paths"]) for x in data["architecture"]["layers"]]
    assert got == [
        ("app", ["app/__init__.py", "app/main.py"]),
        ("core", ["app/core/**"]),
        ("reports", ["app/reports/**"]),
    ]
    ends = [(e["from"], e["to"]) for e in data["architecture"]["allow"]]
    assert ends == [("app", "core"), ("core", "reports")]
    codes = [e["code"] for e in data["testing"]["map"]]
    assert codes == ["app/__init__.py", "app/main.py", "app/core/**", "app/reports/**"]
    assert {e["tests"] for e in data["testing"]["map"]} == {"tests/**"}


def test_req079_the_drafted_tables_pass_the_playbook_format_together(tmp_path, capsys) -> None:
    """REQ-079: in a derived playbook the two tables fit each other (`_architecture`)."""
    root = project(tmp_path)
    _, out = drafted(root, capsys)
    data = tables(out)
    data["work_type"] = "svc-example"
    (root / "docs/research").mkdir(parents=True)
    (root / "docs/research/svc-example.md").write_text("# Research\n", encoding="utf-8")
    assert playbook_format.is_derived("svc-example", root)
    assert playbook_format._architecture("config/playbooks/svc-example.toml", data, root) == []


def test_req079_the_draft_writes_nothing(tmp_path, capsys) -> None:
    """REQ-079: `git status` is clean after the draft."""
    root = project(tmp_path)
    git = ["git", "-C", str(root)]
    subprocess.run([*git, "init", "-q"], check=True)  # nosec B603 - fixed list

    def status() -> str:
        return subprocess.run(  # nosec B603 - fixed list
            [*git, "status", "--porcelain", "--untracked-files=all"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    before = status()
    drafted(root, capsys)
    assert status() == before


def test_req079_init_proposes_nothing(tmp_path, capsys) -> None:
    """REQ-079: a new project takes the playbook's layers."""
    code, out = drafted(project(tmp_path, mode="init"), capsys)
    assert code == 0 and out == "draft layers: a new project takes the playbook's layers\n"


@pytest.mark.parametrize("mode", [None, "personal-example"])
def test_req079_no_mode_or_another_mode_still_prints_the_draft(mode, tmp_path, capsys) -> None:
    """REQ-079: any mode but `init` prints it (another value is `upgrade.py`'s to refuse)."""
    code, out = drafted(project(tmp_path, mode=mode), capsys)
    assert code == 0 and "[architecture]" in out


def test_req079_no_work_type_still_prints_the_draft(tmp_path, capsys) -> None:
    code, out = drafted(project(tmp_path, work_type=None), capsys)
    assert code == 0 and "[architecture]" in out


@pytest.mark.parametrize(
    "tree",
    [
        {"main.py": "import os\n"},  # the root only: one group
        {"app/__init__.py": "", "app/main.py": ""},  # one package, no split below it
        {},
    ],
)
def test_req079_one_part_only_proposes_nothing(tree, tmp_path, capsys) -> None:
    code, out = drafted(project(tmp_path, tree=tree), capsys)
    assert code == 0 and out == "draft layers: one part only; the playbook's layers are kept\n"


def test_req079_a_monorepo_folder_is_descended_once(tmp_path, capsys) -> None:
    tree = {"services/a/run.py": "", "services/b/run.py": "from services.a import run\n"}
    _, out = drafted(project(tmp_path, tree=tree), capsys)
    data = tables(out)
    got = [(x["name"], x["paths"]) for x in data["architecture"]["layers"]]
    assert got == [("a", ["services/a/**"]), ("b", ["services/b/**"])]
    assert [(e["from"], e["to"]) for e in data["architecture"]["allow"]] == [("b", "a")]


def test_req079_a_folder_named_like_a_shipped_layer_is_its_own(tmp_path, capsys) -> None:
    tree = {"api/routes.py": "", "jobs/run.py": ""}
    data = tables(drafted(project(tmp_path, tree=tree), capsys)[1])
    got = [(x["name"], x["paths"]) for x in data["architecture"]["layers"]]
    assert got == [("api", ["api/**"]), ("jobs", ["jobs/**"])]


def test_req079_a_circular_import_proposes_both_directions(tmp_path, capsys) -> None:
    tree = {"one/a.py": "from two import b\n", "two/b.py": "from one import a\n"}
    data = tables(drafted(project(tmp_path, tree=tree), capsys)[1])
    ends = [(e["from"], e["to"]) for e in data["architecture"]["allow"]]
    assert ends == [("one", "two"), ("two", "one")]


def test_req079_names_that_are_no_slug_or_repeat_are_made_one(tmp_path, capsys) -> None:
    tree = {"Core_Utils/a.py": "", "core-utils/b.py": "", "lib/c.py": ""}
    data = tables(drafted(project(tmp_path, tree=tree), capsys)[1])
    names = [x["name"] for x in data["architecture"]["layers"]]
    assert names == ["core-utils", "core-utils-2", "lib"]
    assert all(playbook_format.SLUG.match(n) for n in names)


def test_req079_windows_line_ends_are_read(tmp_path, capsys) -> None:
    tree = {"one/a.py": "import os\r\nfrom two import b\r\n", "two/b.py": ""}
    data = tables(drafted(project(tmp_path, tree=tree), capsys)[1])
    assert [(e["from"], e["to"]) for e in data["architecture"]["allow"]] == [("one", "two")]


# --- answer 7: the settings the draft reads -----------------------------------------------------


def test_req079_test_dirs_are_left_out_and_name_the_map_glob(tmp_path, capsys) -> None:
    tree = {"check/test_a.py": "", "one/a.py": "", "two/b.py": "", "spec/x.py": ""}
    root = project(tmp_path, tree=tree, extra='test_dirs = ["check", "spec"]\n')
    data = tables(drafted(root, capsys)[1])
    assert [x["name"] for x in data["architecture"]["layers"]] == ["one", "two"]
    assert {e["tests"] for e in data["testing"]["map"]} == {"check/**"}


def test_req079_lint_paths_are_left_out(tmp_path, capsys) -> None:
    tree = {"tools/kit/a.py": "", "one/a.py": "", "two/b.py": ""}
    root = project(tmp_path, tree=tree, extra='lint_paths = ["tools/kit"]\n')
    data = tables(drafted(root, capsys)[1])
    assert [x["name"] for x in data["architecture"]["layers"]] == ["one", "two"]


def test_req079_a_node_stack_drafts_folders_and_no_direction(tmp_path, capsys) -> None:
    tree = {"web/a.ts": "import { b } from '../lib/b';\n", "lib/b.js": "", "one/c.py": ""}
    root = project(tmp_path, tree=tree)
    (root / "docs/adr").mkdir(parents=True)
    (root / "docs/adr/0003-stack-options.md").write_text(NODE_RECORD, encoding="utf-8")
    code, out = drafted(root, capsys)
    assert code == 0 and "draft layers: no reader for node\n" in out
    data = tables(out)
    assert [x["name"] for x in data["architecture"]["layers"]] == ["lib", "web"]
    assert data["architecture"]["allow"] == []


def test_req079_the_usage_is_refused_for_an_unknown_word(tmp_path, capsys) -> None:
    root = project(tmp_path)
    assert layers.main(["--root", str(root), "--draft", "--more"]) == 2
    assert "--draft" in capsys.readouterr().err


# --- answer 6: the class stays closed -----------------------------------------------------------

# Every writer and reader of the record or of `[architecture]` the brief names, each run on the
# adopted sample: (file, what runs, what it must name).
TABLE = {
    "scripts/agk/gates/layers.py": ("--write-record and check", "architecture.layers"),
    "scripts/agk/front_door.py": ("derive-write --layers and check-design", "section: Context"),
    "scripts/agk/gates/architecture_record.py": ("the architecture-record step", "section: Parts"),
}
# The other files under scripts/agk/ that name the record or read `[architecture]`, each with why
# it is neither a writer nor a check of what the record or the layers hold.
OTHERS = {
    "scripts/agk/basics.py": "names the layer folders in a comment",
    "scripts/agk/check_brief.py": "checks a brief's `Layer:` line against the layer names",
    "scripts/agk/check_playbooks.py": "composes `[architecture]` for the step and the writers",
    "scripts/agk/config.py": "documents the layer paths as the packs' default scope",
    "scripts/agk/gates/injection_set.py": "is not run until the record exists",
    "scripts/agk/gates/node_pack.py": "reads the layer paths as its default scope",
    "scripts/agk/gates/pins.py": "reads whether the record exists, for its wait (brief #1909)",
    "scripts/agk/gates/python_pack.py": "reads the layer paths as its default scope",
    "scripts/agk/gates/tests_floor.py": "reads whether the record exists and the files in a layer",
    "scripts/agk/plan_sources.py": "its `architecture` source is docs/sources/, not the record",
    "scripts/agk/playbook_format.py": "checks the form of `[architecture]`",
    "scripts/agk/run_gates.py": "runs the layers and architecture-record steps",
    "scripts/agk/steward_owner.py": "shows the draft and passes it to derive-write (answer 2)",
}
NAMES = re.compile(r"docs/architecture\.md|[\"']architecture[\"']|\[architecture\]")


def test_req079_every_writer_and_reader_is_in_the_table() -> None:
    """REQ-079: a new writer or reader of the record or `[architecture]` fails, naming the file."""
    found = {
        p.relative_to(KIT_ROOT).as_posix()
        for p in sorted(AGK.rglob("*.py"))
        if "__pycache__" not in p.parts and NAMES.search(p.read_text(encoding="utf-8"))
    }
    new = sorted(found - set(TABLE) - set(OTHERS))
    assert new == [], f"not in answer 6's table: {new}"
    gone = sorted((set(TABLE) | set(OTHERS)) - found)
    assert gone == [], f"in the table, no longer a writer or reader: {gone}"


MARKED = """# Architecture

## Context

TODO(architect): what the product is for.

## Parts

TODO(architect): each part.

## Data stores

- none

## Outside services

None named by the chosen option.

## Needs

- Busiest hour: none
- Downtime: none
- Cost: none
- Recovery time: none
- Logged: none

## Diagram

```text
app
```

## Layers

| Layer | Paths |
"""


def test_req079_each_writer_and_reader_refuses_the_adopted_sample(tmp_path, capsys) -> None:
    """REQ-079: playbook layers matching no file and a record with a marker: never `ok`."""
    root = project(tmp_path)
    assert layers.main(["--root", str(root), "--write-record"]) == 1
    out = capsys.readouterr().out
    assert "architecture.layers" in out and not (root / "docs/architecture.md").exists()
    assert layers.main(["--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert f"FAIL layers: SPEC-0072 rule 5: no source file is in any layer {KEY}" in out
    assert "ok layers" not in out
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs/architecture.md").write_text(MARKED, encoding="utf-8")
    rows = architecture_record.check(root, {})
    assert {c for _, c in rows} >= {
        "docs/architecture.md; section: Context",
        "docs/architecture.md; section: Parts",
    }
    assert run_gates.main(["--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert "ok layers" not in out and "ok architecture-record" not in out
    assert front_door.main(["check-design", "--root", str(root), "--date", "2026-11-23"]) == 1
    out = capsys.readouterr().out
    assert "section: Context" in out and "TODO(architect): what" not in out
    draft = tmp_path / "draft.toml"
    draft.write_text("[architecture]\nlayers = []\n", encoding="utf-8")
    (root / "docs/research").mkdir()
    (root / "docs/research/svc-example.md").write_text("# Research\n", encoding="utf-8")
    code = front_door.main(
        ["derive-write", "--slug", "svc-example", "--layers", str(draft), "--root", str(root)]
    )
    assert code == 1 and "architecture.layers" in capsys.readouterr().out
    assert not (root / "config/playbooks/svc-example.toml").exists()
