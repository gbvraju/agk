"""Tests of the knowledge resolver (SPEC-0077 rule 5; REQ-084 AC2; brief #2032, ADR-0839).

`packs.files(root, kind)` gives `agk-core`, then each pack of `[packs] use` in its order, then the
project's own files, and the readers of rule 5 read through it: with no `[packs]` table each gives
today's result; a pack strengthens and never weakens (a weakening names the pack and the key); rows
of signals and stack defaults compose by name. Fixtures in `tmp_path` only: invented data
(`example.com`), no network, no model.
"""

from __future__ import annotations

import hashlib
import inspect
import shutil
import sys
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_domains  # noqa: E402
import check_playbooks  # noqa: E402
import engines  # noqa: E402
import front_door  # noqa: E402
import packs  # noqa: E402
import playbook_format  # noqa: E402

SINGLE = ("standards", "stack-defaults", "stack-signals", "domain-signals")
HEAD = """format = 1
id = "{pid}"
version = "1.0.0"
publisher = "Example Org"
tier = "curated"
licence = "MIT"
source = "https://example.com/packs/{pid}"
kit = ">=0.65"
as_of = "2026-11-20"
reviewed = "2026-11-21 by maintainers"
kinds = {kinds}

[permissions]

[files]
"""
SOURCE = 'source = "https://example.com/rows (accessed 2026-11-20)"\n'


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_pack(root: Path, pid: str, files: dict[str, str], kinds: list[str] | None = None) -> str:
    """A pack under `config/packs/<pid>/` with FILES listed; returns its `use` entry."""
    base = root / "config" / "packs" / pid
    for rel, text in files.items():
        (base / rel).parent.mkdir(parents=True, exist_ok=True)
        (base / rel).write_text(text, encoding="utf-8")
    named = kinds if kinds is not None else sorted({rel.split("/")[0] for rel in files})
    head = HEAD.format(pid=pid, kinds=str(named).replace("'", '"'))
    manifest = head + "".join(f'"{rel}" = "{sha(text)}"\n' for rel, text in files.items())
    (base / "agk-pack.toml").write_text(manifest, encoding="utf-8")
    return f'{{ id = "{pid}", version = "1.0.0", sha256 = "{sha(manifest)}" }}'


def use(root: Path, *entries: str, extra: str = "") -> None:
    text = extra + f"[packs]\nuse = [{', '.join(entries)}]\n"
    (root / "agk.toml").write_text(text, encoding="utf-8")


def clean(root: Path) -> Path:
    """A saved clean-layout project, its plugin the kit itself."""
    (root / "agk.toml").write_text('[kit]\nlayout = "plugin"\n', encoding="utf-8")
    return root


def rows_of(path: Path, key: str) -> list[dict]:
    return tomllib.loads(path.read_text(encoding="utf-8"))[key]


# --- no [packs] table: every reader gives today's result -----------------------------------------


@pytest.mark.parametrize("kind", SINGLE)
def test_ac2_with_no_table_agk_core_is_the_one_layer(kind):
    """REQ-084 AC2: SPEC-0077 rule 5 (no table: the kit's file alone, read once)."""
    assert packs.files(KIT_ROOT, kind) == [(packs.CORE, KIT_ROOT / packs.KIT[kind])]


def test_ac2_with_no_table_each_reader_equals_the_snapshot_on_the_kit_tree():
    """REQ-084 AC2: SPEC-0077 rule 5 (the recorded snapshot of every reader on the kit's tree)."""
    standards = rows_of(KIT_ROOT / "config/standards.toml", "standards")
    assert check_playbooks.standards_file(KIT_ROOT) == (standards, [])
    assert engines.stack_defaults(KIT_ROOT) == rows_of(
        KIT_ROOT / "config/stack-defaults.toml", "default"
    )
    table = tomllib.loads((KIT_ROOT / front_door.SIGNALS).read_text(encoding="utf-8"))
    assert front_door.signal_table(KIT_ROOT, KIT_ROOT) == table
    assert front_door.domain_rows(KIT_ROOT, KIT_ROOT) == rows_of(
        KIT_ROOT / front_door.DOMAIN_SIGNALS, "domain"
    )
    assert playbook_format.folder(KIT_ROOT, "web-app") == KIT_ROOT / "config/playbooks"
    assert playbook_format.playbooks(KIT_ROOT) == sorted(
        (KIT_ROOT / "config/playbooks").glob("*.toml")
    )
    assert check_domains.folders(KIT_ROOT) == [KIT_ROOT / "config/domains"]


def test_ac2_with_no_table_a_clean_project_reads_the_plugin_then_its_own(tmp_path):
    """REQ-084 AC2: SPEC-0077 rule 5 (`[kit] layout = "plugin"`: core from the plugin)."""
    root = clean(tmp_path)
    assert playbook_format.folder(root, "web-app") == KIT_ROOT / "config/playbooks"
    assert playbook_format.playbooks(root) == []
    assert check_domains.folders(root) == [root / "config/domains", KIT_ROOT / "config/domains"]
    assert packs.files(root, "standards") == [(packs.CORE, KIT_ROOT / "config/standards.toml")]
    own = root / "config/playbooks/web-app.toml"
    own.parent.mkdir(parents=True)
    shutil.copy(KIT_ROOT / "config/playbooks/web-app.toml", own)
    assert playbook_format.folder(root, "web-app") == own.parent
    assert playbook_format.playbooks(root) == [own]
    shutil.copy(KIT_ROOT / "config/standards.toml", root / "config/standards.toml")
    assert [layer for layer, _ in packs.files(root, "standards")] == [packs.CORE, packs.PROJECT]


def test_ac2_an_empty_use_is_no_table(tmp_path):
    """REQ-084 AC2: SPEC-0077 rule 5 (`use = []`: only `agk-core`)."""
    root = clean(tmp_path)
    (root / "agk.toml").write_text('[kit]\nlayout = "plugin"\n[packs]\nuse = []\n', "utf-8")
    assert packs.files(root, "stack-signals") == [(packs.CORE, KIT_ROOT / front_door.SIGNALS)]


# --- packs in use: one order -----------------------------------------------------------------------


def signals(name: str) -> str:
    return f'[[stack]]\nname = "{name}"\nmanifests = ["zz.toml"]\nlocks = []\n{SOURCE}'


def test_ac2_two_packs_are_read_in_the_listed_order_before_the_project(tmp_path):
    """REQ-084 AC2: SPEC-0077 rule 5 (`agk-core`, the packs in `use` order, the project's)."""
    root = clean(tmp_path)
    first = write_pack(root, "zz-b", {"stack-signals/b.toml": signals("zz-b-stack")})
    second = write_pack(root, "zz-a", {"stack-signals/a.toml": signals("zz-a-stack")})
    use(root, first, second, extra='[kit]\nlayout = "plugin"\n')
    (root / front_door.SIGNALS).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(KIT_ROOT / front_door.SIGNALS, root / front_door.SIGNALS)
    found = packs.files(root, "stack-signals")
    assert [layer for layer, _ in found] == [packs.CORE, "zz-b", "zz-a", packs.PROJECT]
    assert found[1][1] == root / "config/packs/zz-b/stack-signals/b.toml"


def test_ac2_a_declared_kind_with_no_file_reads_nothing(tmp_path):
    """REQ-084 AC2: SPEC-0077 rule 5 (a kind the pack declares but holds no file of)."""
    root = clean(tmp_path)
    use(root, write_pack(root, "zz-a", {}, kinds=["standards"]), extra='[kit]\nlayout = "plugin"\n')
    assert [layer for layer, _ in packs.files(root, "standards")] == [packs.CORE]


def test_ac2_a_refused_use_entry_stops_every_reader_with_one_line(tmp_path):
    """REQ-084 AC2: SPEC-0077 rule 5 (a use entry build (a) refuses: one line, no partial read)."""
    root = clean(tmp_path)
    entry = write_pack(root, "zz-a", {"stack-signals/a.toml": signals("zz-a-stack")})
    use(root, entry.replace('"1.0.0"', '"9.9.9"'), extra='[kit]\nlayout = "plugin"\n')
    for read in (
        lambda: packs.files(root, "standards"),
        lambda: engines.stack_defaults(root),
        lambda: check_playbooks.standards_file(root),
        lambda: playbook_format.folder(root, "web-app"),
    ):
        with pytest.raises(packs.Refused) as caught:
            read()
        assert str(caught.value) == "packs: the [packs] table is refused (setting: packs.use)"


def test_ac2_a_pack_file_of_an_undeclared_kind_is_never_read(tmp_path):
    """REQ-084 AC2: SPEC-0077 rule 5 (build (a) fails it, so the pack is refused, never read)."""
    root = clean(tmp_path)
    entry = write_pack(root, "zz-a", {"standards/s.toml": "standards = []\n"}, kinds=["domains"])
    use(root, entry, extra='[kit]\nlayout = "plugin"\n')
    with pytest.raises(packs.Refused) as caught:
        packs.files(root, "standards")
    assert str(caught.value).startswith("packs: rule 3: config/packs/zz-a: ")
    assert "(key: kinds)" in str(caught.value)


# --- composition: strengthen, never weaken ---------------------------------------------------------


def standard(codes: list[str]) -> str:
    quoted = ", ".join(f'"{c}"' for c in codes)
    return (
        '[[standards]]\nstack = "python-pyproject"\nruntime = "python"\nlint = "python-lint"\n'
        'format = "python-format"\ntype = "python-type"\nconfig = "pyproject.toml"\n'
        f'rules = {{ tool = "ruff", version = "0.17.4", codes = [{quoted}] }}\n{SOURCE}'
    )


def test_ac2_a_later_pack_with_a_stronger_rules_replaces_the_entry(tmp_path):
    """REQ-084 AC2: SPEC-0077 rule 5 (a restated standard holds when the same or stronger)."""
    root = clean(tmp_path)
    codes = ["E", "F", "I", "B", "UP", "S"]
    use(root, write_pack(root, "zz-a", {"standards/s.toml": standard(codes)}),
        extra='[kit]\nlayout = "plugin"\n')  # fmt: skip
    found, problems = check_playbooks.standards_file(root)
    assert problems == []
    entry = next(e for e in found if e["stack"] == "python-pyproject")
    assert entry["rules"]["codes"] == codes and "source" not in entry
    assert [e["stack"] for e in found] == [
        e["stack"] for e in rows_of(KIT_ROOT / "config/standards.toml", "standards")
    ]


def test_ac2_a_pack_that_drops_a_rule_code_is_refused_naming_the_pack(tmp_path):
    """REQ-084 AC2: SPEC-0077 rule 5 (a weakening names the pack id and the key)."""
    root = clean(tmp_path)
    use(root, write_pack(root, "zz-a", {"standards/s.toml": standard(["E"])}),
        extra='[kit]\nlayout = "plugin"\n')  # fmt: skip
    found, problems = check_playbooks.standards_file(root)
    assert problems == [
        "SPEC-0072 rule 2: config/packs/zz-a: a pack's `rules` drops a rule code "
        "(key: standards.rules)"
    ]
    entry = next(e for e in found if e["stack"] == "python-pyproject")
    assert "UP" in entry["rules"]["codes"]  # the stronger one held


def weakened_playbook() -> str:
    text = (KIT_ROOT / "config/playbooks/web-app.toml").read_text(encoding="utf-8")
    return text.replace(
        'id = "contract-tests"\nkind = "check"', 'id = "contract-tests"\nkind = "judgement"'
    )


def test_ac2_a_pack_playbook_that_weakens_a_gate_is_refused_naming_the_pack(tmp_path):
    """REQ-084 AC2: SPEC-0077 rule 5 (a gate restated weaker by a pack: the pack id and key)."""
    root = clean(tmp_path)
    use(root, write_pack(root, "zz-a", {"playbooks/web-app.toml": weakened_playbook()}),
        extra='[kit]\nlayout = "plugin"\n')  # fmt: skip
    path = playbook_format.path(root, "web-app")
    assert path == root / "config/packs/zz-a/playbooks/web-app.toml"
    gates, _, problems = check_playbooks.composed(path, root)
    assert "rule 21: config/packs/zz-a: a gate is restated weaker (key: kind)" in problems
    held = next(g for g in gates if g["id"] == "contract-tests")
    assert held["kind"] == "check"


def test_ac2_a_pack_playbook_that_restates_the_same_gates_composes_cleanly(tmp_path):
    """REQ-084 AC2: SPEC-0077 rule 5 (the same gate is never a weakening)."""
    root = clean(tmp_path)
    text = (KIT_ROOT / "config/playbooks/web-app.toml").read_text(encoding="utf-8")
    use(root, write_pack(root, "zz-a", {"playbooks/web-app.toml": text}),
        extra='[kit]\nlayout = "plugin"\n')  # fmt: skip
    _, _, problems = check_playbooks.composed(playbook_format.path(root, "web-app"), root)
    assert not [p for p in problems if "config/packs" in p]


def test_ac2_signal_rows_compose_by_name_and_stay_proposals(tmp_path):
    """REQ-084 AC2: SPEC-0077 rule 5, `Q-PB-1` (a later layer's rows of a name replace)."""
    root = clean(tmp_path)
    text = (
        '[[stack]]\nname = "node"\nmanifests = ["zz-package.json"]\nlocks = []\n' + SOURCE
        + '[[work_type]]\nname = "zz-kiosk"\nsignal = "dependency"\nfile = "zz.json"\n'
        + 'contains = "zz-kiosk"\n' + SOURCE
    )  # fmt: skip
    use(root, write_pack(root, "zz-a", {"stack-signals/a.toml": text}),
        extra='[kit]\nlayout = "plugin"\n')  # fmt: skip
    table = front_door.signal_table(KIT_ROOT, root)
    kit = tomllib.loads((KIT_ROOT / front_door.SIGNALS).read_text(encoding="utf-8"))
    node = [r for r in table["stack"] if r["name"] == "node"]
    assert node == [{"name": "node", "manifests": ["zz-package.json"], "locks": []}]
    assert [r["name"] for r in table["stack"]] == [r["name"] for r in kit["stack"]]
    assert table["work_type"][-1]["name"] == "zz-kiosk"
    assert table["ignore"] == kit["ignore"] and table["no_signal"] == kit["no_signal"]


def test_ac2_stack_default_rows_compose_by_work_type(tmp_path):
    """REQ-084 AC2: SPEC-0077 rule 5 (a pack's stack default is a proposal, keyed by work type)."""
    root = clean(tmp_path)
    row = rows_of(KIT_ROOT / "config/stack-defaults.toml", "default")[0]
    text = "[[default]]\n" + "".join(
        f'{k} = "{v}"\n' for k, v in {**row, "reason": "an invented reason"}.items()
    ) + SOURCE  # fmt: skip
    use(root, write_pack(root, "zz-a", {"stack-defaults/d.toml": text}),
        extra='[kit]\nlayout = "plugin"\n')  # fmt: skip
    found = engines.stack_defaults(root)
    assert found[0] == {**row, "reason": "an invented reason"}
    assert len(found) == len(rows_of(KIT_ROOT / "config/stack-defaults.toml", "default"))


def test_ac2_a_bad_pack_signal_row_proposes_nothing_from_it(tmp_path):
    """REQ-084 AC2: SPEC-0077 rule 5 (a pack's row of another form is refused as the kit's is)."""
    root = clean(tmp_path)
    text = '[[stack]]\nname = "zz"\nmanifests = []\nlocks = []\n' + SOURCE
    use(root, write_pack(root, "zz-a", {"stack-signals/a.toml": text}),
        extra='[kit]\nlayout = "plugin"\n')  # fmt: skip
    with pytest.raises(front_door.Refusal) as caught:
        front_door.signal_table(KIT_ROOT, root)
    assert caught.value.problems == ["detect: config/packs/zz-a cannot be read"]


def test_ac2_domain_files_of_a_pack_wait_for_build_j(tmp_path):
    """REQ-084 AC2: SPEC-0077 rule 5, `Q-2032-2` (a pack's domain pack is not read before (j))."""
    root = clean(tmp_path)
    text = '[[terms]]\nterm = "zz-basket"\n' + SOURCE
    use(root, write_pack(root, "zz-a", {"domains/zz-shop.toml": text}),
        extra='[kit]\nlayout = "plugin"\n')  # fmt: skip
    assert check_domains.folders(root) == [root / "config/domains", KIT_ROOT / "config/domains"]
    assert check_domains.pack_path(root, "zz-shop") is None


def test_ac2_a_derived_playbook_stays_the_projects_alone(tmp_path):
    """REQ-084 AC2: SPEC-0048 rule 22 (`is_derived`: the project's folder in both layouts)."""
    root = clean(tmp_path)
    use(root, write_pack(root, "zz-a", {}, kinds=["playbooks"]), extra='[kit]\nlayout = "plugin"\n')
    record = root / playbook_format.RESEARCH / "zz-own.md"
    record.parent.mkdir(parents=True)
    record.write_text("# An invented research record\n", encoding="utf-8")
    assert playbook_format.is_derived("zz-own", root)
    assert playbook_format.folder(root, "zz-own") == root / "config/playbooks"


# --- the class stays closed --------------------------------------------------------------------------


READERS = (
    (playbook_format, "folder"),
    (playbook_format, "playbooks"),
    (check_domains, "folders"),
    (check_playbooks, "standards_file"),
    (engines, "stack_defaults"),
    (front_door, "signal_table"),
    (front_door, "domain_rows"),
)


@pytest.mark.parametrize(("module", "name"), READERS)
def test_ac2_each_reader_of_rule_5_reads_through_the_resolver(module, name):
    """REQ-084 AC2: SPEC-0077 rule 16 (each reader of rule 5 calls `packs.files`)."""
    assert "packs.files(" in inspect.getsource(getattr(module, name))


def test_ac2_no_other_kit_module_opens_a_knowledge_file_by_a_literal_path():
    """REQ-084 AC2: SPEC-0077 rule 16 (a knowledge path is named only where it is known today)."""
    known = {
        "packs.py", "check_playbooks.py", "front_door.py", "playbook_format.py", "adopt.py",
        "survey.py", "governance_map.py", "engines.py", "domain_ask.py", "run_gates.py",
        "check_domains.py",
    }  # fmt: skip
    paths = [rel for rel in packs.KIT.values() if rel and rel.endswith(".toml")]
    named = {
        path.name
        for path in (KIT_ROOT / "scripts" / "agk").glob("*.py")
        if any(rel in path.read_text(encoding="utf-8") for rel in paths)
        or '"stack-signals.toml"' in path.read_text(encoding="utf-8")
    }
    assert named <= known, sorted(named - known)
    assert "stack-defaults.toml\"\n" not in (KIT_ROOT / "scripts/agk/engines.py").read_text("utf-8")
