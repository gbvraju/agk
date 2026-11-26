"""The standing ruling on a new kit script's imports (brief #1972, ADR-0824; REQ-037).

Where an Approved spec or a brief says a new `scripts/agk/` script uses the "standard library and
`common.py` only", the words read as the standard library less its network modules plus the kit's
offline set: `rules.KIT_IMPORTS` and every `check_*.py` whose module-level import walk stays within
that set (`rules.kit_imports`). `rules.py imports <script>` prints one line per module outside it.
Invented trees only (example.com), no network.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "scripts" / "agk"
ACCEPTED = "# ADR-0824: invented\n\n- Status: Accepted\n- Date: 2026-11-26\n"
PROPOSED = ACCEPTED.replace("Accepted", "Proposed")
# The checks whose module-level walk stays offline on main at ed342cf1 (11; the brief's 14 was
# read at 6a5acb46, before #1961 gave `check_domains.py` a module-level `domain_model` and #1984
# gave `check_playbooks.py` a module-level `from gates import pins`; both left the set).
OFFLINE = {
    "check_adrs", "check_amendments", "check_build_state", "check_licence_notice",
    "check_neutrality", "check_plan", "check_pr_body", "check_pr_mode",
    "check_requirements", "check_review_report", "check_runbooks",
}  # fmt: skip
LEFT = {"check_domains", "check_playbooks"}  # an outside module-level import leaves the set


def tree(tmp_path: Path, status: str | None = ACCEPTED, files: dict | None = None) -> Path:
    """A project root with the six base modules copied, the ADR in STATUS and FILES added."""
    folder = tmp_path / "scripts" / "agk"
    folder.mkdir(parents=True)
    from rules import KIT_IMPORTS

    for name in KIT_IMPORTS:
        shutil.copy(KIT / f"{name}.py", folder / f"{name}.py")
    for name, text in (files or {}).items():
        (folder / name).write_text(text, encoding="utf-8")
    if status is not None:
        (tmp_path / "docs" / "adr").mkdir(parents=True)
        (tmp_path / "docs" / "adr" / "0824-invented.md").write_text(status, encoding="utf-8")
    return tmp_path


def run(capsys, *args: str) -> tuple[int, list[str]]:
    from rules import main

    code = main(["imports", *args])
    return code, capsys.readouterr().out.splitlines()


def test_req037_the_three_built_scripts_on_main_read_as_the_brief_says(tmp_path, capsys):
    """REQ-037: brief #1972 answer 1 (`grill.py` and `check_runbooks.py` are within; on main
    `check_domains.py` imports `domain_model`, which is outside, Q-1972-1)."""
    root = tree(tmp_path)
    for name in ("grill.py", "check_runbooks.py"):
        code, out = run(capsys, str(KIT / name), "--root", str(root))
        assert (code, out) == (
            0,
            [f"Imports: scripts/agk/{name} within the standing ruling (ADR-0824)"],
        )
    code, out = run(capsys, str(KIT / "check_domains.py"), "--root", str(root))
    assert code == 1
    assert out == [
        "Imports: scripts/agk/check_domains.py imports domain_model outside the standing ruling "
        "(ADR-0824): ask the owner"
    ]


@pytest.mark.parametrize(
    ("text", "module"),
    [
        ("import example_kit\n", "example_kit"),
        ("import urllib.request\n", "urllib"),
        ("import examplepkg\n", "examplepkg"),
        ("import importlib\nm = importlib.import_module('guard')\n", "importlib.import_module"),
        ("def f():\n    import socket\n", "socket"),
    ],
)
def test_req037_each_import_outside_gets_one_line(tmp_path, capsys, text, module):
    """REQ-037: brief #1972 answers 2, 3 and 6 (a kit module outside the set, a network module, a
    third-party name, a dynamic import and a function-level import each get one line)."""
    root = tree(
        tmp_path, files={"example_kit.py": "import json\n", "new_tool.py": "import guard\n" + text}
    )
    code, out = run(capsys, "scripts/agk/new_tool.py", "--root", str(root))
    assert code == 1
    assert out == [
        f"Imports: scripts/agk/new_tool.py imports {module} outside the standing ruling "
        "(ADR-0824): ask the owner"
    ]


def test_req037_a_check_leaves_or_joins_the_set_by_its_own_walk(tmp_path):
    """REQ-037: brief #1972 answer 6 (a check that imports a kit module with a network import
    leaves the set, one that imports `guard` joins it, one through an outside check leaves too;
    a cycle is walked once)."""
    from rules import kit_imports

    root = tree(
        tmp_path,
        files={
            "example_net.py": "import urllib.request\n",
            "check_net.py": "import example_net\n",
            "check_ok.py": "import guard\nimport check_loop\n",
            "check_loop.py": "import check_ok\n",
            "check_via.py": "import check_net\n",
            "check_bad.py": "def (:\n",
        },
    )
    found = kit_imports(root / "scripts" / "agk")
    assert {"check_ok", "check_loop", "guard", "common"} <= found
    assert not {"check_net", "check_via", "check_bad", "example_net"} & found


def test_req037_the_offline_checks_and_the_base_modules_walk_clean_on_main():
    """REQ-037: brief #1972 answer 7 (each base module and each offline check of main stays in
    the set, so a later module-level network import into `guard.py` fails here; the walk of a
    member leaves function bodies out, Q-1972-2)."""
    from rules import KIT_IMPORTS, kit_imports

    found = kit_imports(KIT)
    assert set(KIT_IMPORTS) <= found
    assert OFFLINE <= found
    assert "check_pr_body" in found  # the known case of the module-level walk (Q-1972-2)
    assert not {"check_brief", "check_numbers", "check_acceptance", "session"} & found
    assert not LEFT & found


def test_req037_without_the_accepted_adr_there_is_no_standing_ruling(tmp_path, capsys):
    """REQ-037: brief #1972 answer 3 (Proposed, or withdrawn by an Accepted `- Withdraws:`)."""
    files = {"new_tool.py": "import guard\n", "plain.py": "import json\nimport common\n"}
    proposed = tree(tmp_path / "a", PROPOSED, files)
    code, out = run(capsys, "scripts/agk/new_tool.py", "--root", str(proposed))
    assert (code, out) == (
        1,
        ["Imports: scripts/agk/new_tool.py, no standing ruling: ask the owner"],
    )
    code, out = run(capsys, "scripts/agk/plain.py", "--root", str(proposed))
    assert code == 0 and out == [
        "Imports: scripts/agk/plain.py within the standard library and common.py"
    ]
    withdrawn = tree(tmp_path / "b", ACCEPTED, files)
    (withdrawn / "docs" / "adr" / "0901-invented.md").write_text(
        "- Status: Accepted\n- Withdraws: ADR-0824\n", encoding="utf-8"
    )
    code, out = run(capsys, "scripts/agk/new_tool.py", "--root", str(withdrawn))
    assert (code, out) == (
        1,
        ["Imports: scripts/agk/new_tool.py, no standing ruling: ask the owner"],
    )


def test_req037_a_path_outside_scripts_agk_or_a_broken_file_is_refused(tmp_path, capsys):
    """REQ-037: brief #1972 answers 3 and 6 (the class is named, never the path or the text)."""
    root = tree(tmp_path, files={"broken.py": "def (:\n"})
    (root / "elsewhere.py").write_text("import json\n", encoding="utf-8")
    code, out = run(capsys, "elsewhere.py", "--root", str(root))
    assert (code, out) == (2, ["Imports: refused: the script is outside scripts/agk/"])
    assert "elsewhere" not in out[0]
    (root / "scripts" / "agk" / "gates").mkdir()
    (root / "scripts" / "agk" / "gates" / "x.py").write_text("import json\n", encoding="utf-8")
    code, out = run(capsys, "scripts/agk/gates/x.py", "--root", str(root))
    assert (code, out) == (
        2,
        ["Imports: refused: the script is in a package under scripts/agk/, not a script of it"],
    )
    (root / "scripts" / "agk" / "notes.txt").write_text("invented\n", encoding="utf-8")
    for given, cause in (
        ("scripts/agk/grl.py", "no such script in scripts/agk/"),
        ("scripts/agk/notes.txt", "the script is not a .py file of scripts/agk/"),
    ):
        assert run(capsys, given, "--root", str(root)) == (2, [f"Imports: refused: {cause}"])
    code, out = run(capsys, "scripts/agk/broken.py", "--root", str(root))
    assert (code, out) == (2, ["Imports: refused: a file of scripts/agk/ does not parse"])
    code, out = run(capsys, "--root", str(root))
    assert code == 2 and out[0].startswith("usage:")


def test_req037_a_plugin_layout_gives_the_same_set(tmp_path):
    """REQ-037: brief #1972 answer 5 (`[kit] layout = "plugin"`: the walk reads the folder that
    holds the scripts, so the plugin's copy gives the same set)."""
    from rules import kit_imports

    plugin = tmp_path / "plugin" / "scripts" / "agk"
    plugin.mkdir(parents=True)
    for path in KIT.glob("*.py"):
        shutil.copy(path, plugin / path.name)
    shutil.copytree(KIT / "gates", plugin / "gates")
    assert kit_imports(plugin) == kit_imports(KIT)


def test_req037_check_brief_warns_on_the_phrase_and_is_silent_without_it():
    """REQ-037: brief #1972 answer 4 (one warning, never a failure)."""
    from check_brief import phrase_warnings
    from rules import IMPORTS_WARNING

    assert phrase_warnings("Uses the standard library and `common.py` only.") == [IMPORTS_WARNING]
    assert phrase_warnings("Uses the standard library and common.py only.") == [IMPORTS_WARNING]
    assert phrase_warnings("Uses only the standard library and common.py.") == [IMPORTS_WARNING]
    assert phrase_warnings("Only standard library and `common.py`.") == [IMPORTS_WARNING]
    assert phrase_warnings("STANDARD LIBRARY AND COMMON.PY ONLY") == [IMPORTS_WARNING]
    assert phrase_warnings("Uses the standard library only.") == []
    assert IMPORTS_WARNING.startswith("ADR-0824: ")


def test_req037_the_conductor_file_and_the_adr_name_the_ruling():
    """REQ-037: brief #1972 answer 4 (the conductor's standing-rulings line names the command)."""
    conductor = (ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    assert "rules.py imports <script>" in conductor and "(ADR-0824)" in conductor
    adr = next((ROOT / "docs" / "adr").glob("0824-*.md")).read_text(encoding="utf-8")
    assert "- Status: " in adr and '"Maintainer answer: Q-1935-2 accept the imports"' in adr
    assert "`check_pr_body` is a member" in adr  # Q-1972-2, answered on #1985
