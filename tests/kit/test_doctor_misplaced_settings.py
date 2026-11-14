"""Brief #1245 (REQ-039, ADR-0527): a setting written in the wrong table of agk.toml is reported.

The kit reads each of its table settings from one table (`config.TABLE_KEYS`); the doctor's
`misplaced-settings` check names any such key found at the top level or in another table, with the
table it is in and the table it belongs to, never its value. The settings are invented.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

import doctor
import impact
import launch
from test_doctor import checks_of, run_case
from test_doctor import doctor as run_doctor

import config

KIT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = KIT_ROOT / "kit" / "templates" / "agk.toml"
FLOW_KEYS = ("auto_start", "launch_adapter", "min_free_memory_mb")


def found(text: str) -> list[tuple[str, str, tuple[str, ...]]]:
    return config.misplaced_settings(tomllib.loads(text))


# --- answer 2: the known keys, listed once ----------------------------------------------------


def test_the_list_names_the_six_tables():
    """REQ-039: brief #1245 answer 2."""
    assert set(config.TABLE_KEYS) == {"flow", "testing", "capacity", "plan", "design", "delivery"}
    assert {"auto_start", "launch_adapter", "min_free_memory_mb"} <= config.TABLE_KEYS["flow"]
    assert config.TABLE_KEYS["delivery"] == frozenset({"work_type"})


def test_the_list_agrees_with_the_readers_of_each_table():
    """REQ-039: brief #1245 answer 2 (one list: a reader's own key set is the same one)."""
    assert config.TABLE_KEYS["testing"] == frozenset(impact.KEYS)
    assert config.TABLE_KEYS["capacity"] == frozenset(
        {"profile", "builders_run", *config.CAPACITY_NUMBERS}
    )


def test_the_repository_own_settings_are_all_in_their_tables():
    """REQ-039: brief #1245 answer 2 (the kit's own agk.toml reads clean)."""
    assert found((KIT_ROOT / "agk.toml").read_text(encoding="utf-8")) == []


# --- answers 1 and 4: the check ---------------------------------------------------------------


def test_a_flow_key_in_another_table_names_both_tables():
    """REQ-039: brief #1245 answers 1 and 4."""
    text = '[design]\nrender = "make page"\nauto_start = true\n'
    assert found(text) == [("auto_start", "design", ("flow",))]
    res = doctor.misplaced_settings_result(tomllib.loads(text))
    assert res.status == "fail"
    assert "auto_start" in res.message and "[design]" in res.message and "[flow]" in res.message
    assert "true" not in res.message and "make page" not in res.message


def test_the_same_key_in_flow_passes():
    """REQ-039: brief #1245 answer 4."""
    text = '[design]\nrender = "make page"\n\n[flow]\nauto_start = true\n'
    assert found(text) == []
    assert doctor.misplaced_settings_result(tomllib.loads(text)).status == "ok"


def test_a_key_at_the_top_level_is_named_as_the_top_level():
    """REQ-039: brief #1245 answer 1."""
    text = 'mode = "init"\nmin_free_memory_mb = 2048\nlaunch_adapter = "sh run.sh"\n'
    assert found(text) == [
        ("launch_adapter", "top level", ("flow",)),
        ("min_free_memory_mb", "top level", ("flow",)),
    ]
    res = doctor.misplaced_settings_result(tomllib.loads(text))
    assert res.status == "fail" and "the top level" in res.message
    assert "2048" not in res.message and "run.sh" not in res.message


def test_a_key_of_two_tables_is_at_home_in_either():
    """REQ-039: brief #1245 answer 1 (`max_builders` is read from `[flow]` and `[capacity]`)."""
    assert found("[capacity]\nmax_builders = 2\n\n[flow]\nmax_builders = 3\n") == []
    assert found("[testing]\nmax_builders = 2\n") == [
        ("max_builders", "testing", ("capacity", "flow"))
    ]


def test_each_table_key_out_of_place_is_reported():
    """REQ-039: brief #1245 answer 1 (every table of the list, not only `[flow]`)."""
    text = (
        "[engines]\n"
        'work_type = "web-app"\n'
        "iteration_days = 5\n"
        "ui_paths = []\n"
        'pr_tests = "full"\n'
        'builders_run = "here"\n'
    )
    assert {(k, w) for k, w, _ in found(text)} == {
        ("work_type", "engines"),
        ("iteration_days", "engines"),
        ("ui_paths", "engines"),
        ("pr_tests", "engines"),
        ("builders_run", "engines"),
    }


def test_a_top_level_setting_and_an_unknown_key_are_not_this_check():
    """REQ-039: brief #1245 answer 1 (only the kit's table keys; other refusals stay theirs)."""
    assert found('default_branch = "main"\npr_mode = "strict"\nsomething_else = 1\n') == []
    assert found("[flow]\nnot_a_kit_key = 1\n") == []


def test_no_misplaced_key_is_ok():
    """REQ-039: brief #1245 answer 1."""
    res = doctor.misplaced_settings_result({})
    assert res.status == "ok"


def test_the_check_is_a_line_of_the_doctor_report(tmp_path):
    """REQ-039: brief #1245 answer 1 (one `misplaced-settings` line in the report)."""
    assert "misplaced-settings" in doctor.CHECKS
    proc, _, dirs = run_case("ok", tmp_path, "--json")
    assert checks_of(proc.stdout)["misplaced-settings"]["status"] == "ok"
    toml = dirs["root"] / "agk.toml"
    toml.write_text("auto_start = true\n" + toml.read_text(encoding="utf-8"), encoding="utf-8")
    args = ["--api-dir", str(dirs["api"]), "--repo", "example-owner/example-repo", "--json"]
    proc = run_doctor(*args, "--kit-root", str(dirs["kit"]), str(dirs["root"]),
                      path=f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}")  # fmt: skip
    entry = checks_of(proc.stdout)["misplaced-settings"]
    assert entry["status"] == "fail" and entry["severity"] == "warn"
    assert "auto_start" in entry["message"] and "[flow]" in entry["message"]
    assert "true" not in entry["message"]
    assert proc.returncode != 0


# --- answer 3: the template -------------------------------------------------------------------


def uncommented_flow(text: str, header: bool = True) -> str:
    """The template with the lines of its commented flow block uncommented where they stand: each
    `# <key> = <value>` line of a flow key after the `# [flow]` line, and that line with HEADER."""
    keys = config.TABLE_KEYS["flow"]
    out, block = [], False
    for line in text.splitlines():
        if line == "# [flow]":
            block = True
            out.append("[flow]" if header else line)
            continue
        body = line[2:] if block and line.startswith("# ") else None
        if body is not None and body.split(" = ", 1)[0] in keys and " = " in body:
            out.append(body)
        else:
            block = False
            out.append(line)
    return "\n".join(out) + "\n"


def template_text() -> str:
    return TEMPLATE.read_text(encoding="utf-8").replace("{{", "").replace("}}", "")


def test_the_template_says_where_the_flow_keys_go_and_sets_nothing():
    """REQ-039: brief #1245 answer 3 (the comment block says the keys go in the [flow] table)."""
    text = template_text()
    lines = text.splitlines()
    note = lines[lines.index("# [flow]") - 1]
    assert "[flow] table" in note and "misplaced-settings" in note
    assert "flow" not in tomllib.loads(text)
    assert found(text) == []


def test_the_template_flow_block_uncommented_in_place_reads_from_flow(tmp_path):
    """REQ-039: brief #1245 answer 4 (uncommenting the flow block puts its keys in `[flow]`)."""
    text = uncommented_flow(template_text())
    data = tomllib.loads(text)
    assert "auto_start" in data["flow"] and "launch_adapter" in data["flow"]
    assert found(text) == []
    text = text.replace('launch_adapter = ""', 'launch_adapter = "sh scripts/run.sh"')
    text = text.replace("auto_start = false", "auto_start = true")
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    assert launch.launch_settings(tmp_path) == (True, "sh scripts/run.sh")


def test_the_flow_keys_uncommented_without_the_table_line_are_reported():
    """REQ-039: brief #1245 answers 1 and 4 (the rehearsal: the keys alone, never silent)."""
    text = uncommented_flow(template_text(), header=False)
    named = {key for key, where, homes in found(text)}
    assert {"auto_start", "launch_adapter"} <= named
    assert all("flow" in homes for _, _, homes in found(text))
    res = doctor.misplaced_settings_result(tomllib.loads(text))
    assert res.status == "fail" and "auto_start is at the top level" in res.message
