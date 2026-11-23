"""Kit-only tests of the theme filled from discovery (brief #1840, REQ-044 AC1 and AC3).

`design_brand.py` reads the given `brand` answers of `docs/discovery/*.md` and fills the brand
record of a new `docs/design/theme.md`, proposing a compliant shade of a low-contrast brand colour
(SPEC-0037 rule 2, rule 7's contrast); `design.py theme` writes the theme on the import path with
the Evidence line naming the imported version (rules 12 and 15), and `design.py prototype` fills a
new theme the same way. Invented data only (example.com), in `tmp_path`; no network, no model.
"""

from __future__ import annotations

import ast
import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env

AGK = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(AGK))
import check_design  # noqa: E402
import design  # noqa: E402
import design_signoff  # noqa: E402
import design_standard  # noqa: E402
import kit_root  # noqa: E402

try:
    import design_brand  # noqa: E402
except ImportError:  # before the module exists every test fails, not the collection
    design_brand = None

SCRIPT = AGK / "design.py"
CHECK = AGK / "check_design.py"
THEME = "docs/design/theme.md"
SIGNOFFS_TEMPLATE = KIT_ROOT / "kit" / "templates" / "design-signoffs.md"
TEMPLATE = (KIT_ROOT / "kit" / "templates" / "design-theme.md").read_text(encoding="utf-8")
HEAD = "0123456789abcdef0123456789abcdef01234567"
WHERE = "in session 2026-11-23"
IB08 = "Example Studio; sage green #6B8F71"
SOURCE = f"source: docs/discovery/reading-list.md (brand, given: {WHERE})"
PROPOSAL = "/* a shade of the brand primary for 4.5:1 (proposed; the person's sign-off confirms it) */"
ASK = (
    "ask the person: The brand colour is too light to read as text on the page; the theme uses a "
    "shade of it that reads at 4.5:1. Keep that shade? Yes or not yet; I recommend yes."
)
NOTE = (
    "note: discovery documents give different brand answers; the brand record keeps its "
    "placeholders"
)

REQUIREMENTS = """# Requirements

### REQ-001 — A reader keeps a list of books

- Acceptance: AC1 a reader adds a book
- Status: planned
"""
INVENTORY = """# Design inventory

The screens and states of the product, from the requirements and specs only.

## Requirements

### REQ-001 — A reader keeps a list of books

- Specs: SPEC-0001
- Screens: books

## Screens

### books

- Flow: keep a list
- Pattern: list with filter and sort
- Links to: none
- State default: yes
- State empty: n/a: the list is never empty
- State loading: n/a: the list is read at once
- State error: n/a: nothing can fail
- State no-permission: n/a: every reader may see their own list
- State long-content: n/a: the list is short
- State success: n/a: nothing is saved
"""
PAGE = (
    "<!doctype html><title>Imported Name</title>"
    "<style>p { color: #ff00aa }</style><p>Imported Name</p>\n"
)


def put(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def discovery(answer: str | None, where: str = WHERE) -> str:
    """A discovery document's Answers part: the brand answer between its markers, or open."""
    if answer is None:
        brand = "- brand: open\n"
    else:
        sha = hashlib.sha256(answer.encode("utf-8")).hexdigest()
        brand = (
            f"- brand: (given: {where})\n<!-- agk:answer sha256={sha} -->\n{answer}\n"
            "<!-- agk:answer-end -->\n"
        )
    return f"# A reader keeps a list\n\n## Answers\n\n- users: open\n{brand}- scale: open\n"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - a fixed argument list, no shell
        [sys.executable, *args], capture_output=True, text=True, env=clean_env(), check=False
    )


def imported(root: Path, answer: str | None = IB08, name: str = "reading-list") -> Path:
    """A project on the import path: an imported version i1 with its map, and discovery."""
    put(root, "docs/requirements.md", REQUIREMENTS)
    put(root, "docs/design/inventory.md", INVENTORY)
    source = put(root.parent / f"{root.name}-customer", "index.html", PAGE).parent
    proc = run(str(SCRIPT), "import", str(source), "--root", str(root))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    put(root, "docs/design/imported/i1/map.md", "# Screen map of i1\n\n- index.html -> books/default\n")
    put(root, f"docs/discovery/{name}.md", discovery(answer))
    return root


def theme(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return run(str(SCRIPT), "theme", *extra, "--root", str(root))


def text(root: Path) -> str:
    return (root / THEME).read_text(encoding="utf-8")


def values(answer: str, tmp_path: Path) -> dict[str, str]:
    """The brand values read from one discovery document holding ANSWER."""
    assert design_brand is not None, "scripts/agk/design_brand.py is missing"
    put(tmp_path, "docs/discovery/reading-list.md", discovery(answer))
    found, notes = design_brand.brand(tmp_path)
    assert notes == []
    return {k: v for k, (v, _) in found.items()}


def block(theme_text: str) -> tuple[dict[str, str], dict[str, str]]:
    light, dark, problems = design_standard._theme_block(theme_text)
    assert problems == []
    return light, dark


# --- answer 1 and 2: the IB-08 answer, filled and shaded -----------------------------------------


def test_ac1_the_ib08_answer_fills_name_and_primary_with_a_compliant_light_shade(tmp_path):
    """REQ-044 AC1: SPEC-0037 rule 2 (brief #1840 answers 1 to 3)."""
    root = imported(tmp_path / "proj")
    proc = theme(root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines() == [f"wrote {THEME}", ASK]
    written = text(root)
    assert f"- name: Example Studio — {SOURCE}" in written
    assert f"- primary: #6B8F71 — {SOURCE}" in written
    assert "- logo: [logo file] — source: [where the owner wrote it down]" in written
    light, dark = block(written)
    assert (light["--color-accent"], light["--color-on-accent"]) == ("#5a785f", "#ffffff")
    assert dark["--color-accent"].lower() == "#6b8f71"
    assert written.count(PROPOSAL) == 1
    assert "Evidence: docs/design/imported/i1/" in written
    check = run(str(CHECK), "--root", str(root))
    assert check.returncode == 0, check.stdout
    assert "design: the theme is not approved yet" in check.stdout
    assert "at risk design: placeholder brand" in check.stdout  # the logo is still the owner's


def test_ac1_the_shade_is_the_first_step_that_passes_in_each_mode():
    """REQ-044 AC1: SPEC-0037 rule 7 (one per cent steps; PB-05's colour in both modes)."""
    assert design_brand is not None, "scripts/agk/design_brand.py is missing"
    assert design_brand.shade("#6B8F71", "light") == "#5a785f"
    assert design_brand.shade("#6B8F71", "dark") == "#6B8F71"
    assert design_brand.shade("#b5562b", "dark") == "#c2734f"
    light = design_brand.shade("#b5562b", "light")
    assert light != "#b5562b" and design_brand.passes(light, "light")
    assert not design_brand.passes(design_brand.mix("#b5562b", "dark", 16), "dark")


def test_ac1_a_colour_that_passes_is_written_as_given_with_no_proposal(tmp_path):
    """REQ-044 AC1: SPEC-0037 rule 2 (a shade only when the colour fails)."""
    root = imported(tmp_path / "proj", answer="name: Example Studio; primary: #1a56db")
    proc = theme(root)
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.splitlines() == [f"wrote {THEME}"]
    light, _ = block(text(root))
    assert light["--color-accent"] == "#1a56db"
    assert PROPOSAL not in text(root)


def test_ac1_a_colour_no_shade_can_pass_is_written_and_the_check_still_fails(
    tmp_path, monkeypatch, capsys
):
    """REQ-044 AC1: SPEC-0037 rule 7 (answer 8: the check is unchanged, the line names the rule)."""
    assert design_brand is not None, "scripts/agk/design_brand.py is missing"
    root = imported(tmp_path / "proj")
    monkeypatch.setattr(design_brand, "passes", lambda colour, mode: False)
    assert design.main(["theme", "--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "ask the person:" in out and "rule 7" in out
    light, _ = block(text(root))
    assert light["--color-accent"] == "#6B8F71"
    check = run(str(CHECK), "--root", str(root))
    assert "contrast below 4.5:1 in light for accent on background" in check.stdout


def test_ac1_a_labelled_font_is_the_body_and_heading_stack(tmp_path):
    """REQ-044 AC1: SPEC-0037 rule 2 (the font stacks; no download)."""
    root = imported(tmp_path / "proj", answer="name: Example Studio\nfont: Example Sans")
    assert theme(root).returncode == 0
    light, _ = block(text(root))
    stack = '"Example Sans", system-ui, sans-serif'
    assert (light["--font-body"], light["--font-heading"]) == (stack, stack)
    assert f"- font: Example Sans — {SOURCE}" in text(root)
    assert run(str(CHECK), "--root", str(root)).returncode == 0


# --- answer 8: the readings of an answer ----------------------------------------------------------


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (IB08, {"name": "Example Studio", "primary": "#6B8F71"}),
        ("name: Example Studio; primary: #6B8F71; font: Example Sans",
         {"name": "Example Studio", "primary": "#6B8F71", "font": "Example Sans"}),
        ("name: Example Studio\r\nprimary: #6B8F71", {"name": "Example Studio", "primary": "#6B8F71"}),
        ("Example Studio; #abc", {"name": "Example Studio", "primary": "#aabbcc"}),
        ("Example Studio; #111111 and #222222", {"name": "Example Studio"}),
        ("name: Example Studio; primary: sage green", {"name": "Example Studio"}),
        ("Example — Studio; #6B8F71", {"primary": "#6B8F71"}),
        ("Example [Studio]; #6B8F71", {"primary": "#6B8F71"}),
        ("E" * 61 + "; #6B8F71", {"primary": "#6B8F71"}),
        ("sage green #6B8F71", {"primary": "#6B8F71"}),
        ("colours: sage green", {}),
        ("font: Example/Sans", {}),
        ("font: Example\"Sans", {}),
    ],
)
def test_ac1_each_reading_of_an_answer_fills_only_what_it_reads_without_guessing(
    tmp_path, answer, expected
):
    """REQ-044 AC1: SPEC-0037 rule 2 (brief #1840 answers 1 and 8)."""
    assert values(answer, tmp_path) == expected


def test_ac1_no_discovery_an_open_answer_or_differing_answers_keep_the_template(tmp_path):
    """REQ-044 AC1: SPEC-0037 rule 2 (answer 8; the differing note names no value)."""
    assert design_brand is not None, "scripts/agk/design_brand.py is missing"
    evidence = "docs/design/imported/i1/"
    expected = TEMPLATE.replace("{{evidence}}", evidence)
    assert design_brand.theme_text(tmp_path, evidence) == (expected, [])
    put(tmp_path, "docs/discovery/a.md", discovery(None))
    assert design_brand.theme_text(tmp_path, evidence) == (expected, [])
    put(tmp_path, "docs/discovery/b.md", discovery(IB08))
    put(tmp_path, "docs/discovery/c.md", discovery("Other Example; #1a56db"))
    assert design_brand.theme_text(tmp_path, evidence) == (expected, [NOTE])
    put(tmp_path, "docs/discovery/c.md", discovery(IB08, where="https://example.com/issues/1"))
    found, notes = design_brand.brand(tmp_path)
    assert notes == [] and found["name"][1] == "docs/discovery/b.md (brand, given: in session 2026-11-23)"


# --- answer 3: the two writers --------------------------------------------------------------------


def test_ac1_design_theme_on_the_import_path_copies_nothing_of_the_imported_files(tmp_path):
    """REQ-044 AC1: SPEC-0037 rule 13 (only the version's folder name reaches the theme)."""
    root = imported(tmp_path / "proj")
    assert theme(root).returncode == 0
    written = text(root)
    assert "Imported Name" not in written and "ff00aa" not in written.lower()


def test_ac1_design_theme_refuses_an_existing_theme_and_a_project_with_no_version(tmp_path):
    """REQ-044 AC1: SPEC-0037 rules 2 and 7 (answer 3: nothing is written)."""
    root = imported(tmp_path / "proj")
    put(root, THEME, TEMPLATE)
    proc = theme(root)
    assert proc.returncode == 1
    assert f"rule 2: {THEME} exists; it is never overwritten" in proc.stdout
    assert text(root) == TEMPLATE
    bare = tmp_path / "bare"
    put(bare, "docs/discovery/reading-list.md", discovery(IB08))
    proc = theme(bare)
    assert proc.returncode == 1
    assert "rule 7: no prototype or imported version for the evidence line (path class docs/design/)" in proc.stdout
    assert not (bare / THEME).exists()


def test_ac1_design_theme_names_the_kit_version_when_both_kinds_exist(tmp_path):
    """REQ-044 AC1: SPEC-0037 rule 12 (answer 8)."""
    root = imported(tmp_path / "proj")
    put(root, "docs/design/prototype/v2/index.html", "<!doctype html>\n")
    assert theme(root).returncode == 0
    assert "Evidence: docs/design/prototype/v2/" in text(root)


def test_ac1_design_theme_takes_only_root(tmp_path):
    """REQ-044 AC1: brief #1840 answer 7 (another option is the usage text, exit 2)."""
    root = imported(tmp_path / "proj")
    proc = run(str(SCRIPT), "theme", "--folder", "x", "--root", str(root))
    assert proc.returncode == 2 and "usage:" in proc.stderr
    assert not (root / THEME).exists()


def test_ac1_a_flagged_theme_is_refused_naming_rule_14_and_nothing_is_written(
    tmp_path, monkeypatch, capsys
):
    """REQ-044 AC1: brief #1840 answer 8 (the data guard reads the theme before it is written)."""
    assert design_brand is not None, "scripts/agk/design_brand.py is missing"
    root = imported(tmp_path / "proj")
    monkeypatch.setattr(design_brand.guard, "scan_text", lambda text: ["a finding"])
    assert design.main(["theme", "--root", str(root)]) == 1
    assert f"rule 14: {THEME}" in capsys.readouterr().out
    assert not (root / THEME).exists()


def test_ac3_design_prototype_on_an_agreed_inventory_fills_the_new_theme(tmp_path):
    """REQ-044 AC3: SPEC-0037 rules 2 and 12 (answer 3: the prototype writer uses it too)."""
    root = tmp_path / "proj"
    put(root, "docs/requirements.md", REQUIREMENTS)
    put(root, "docs/design/inventory.md", INVENTORY)
    put(root, "docs/design/signoffs.md", SIGNOFFS_TEMPLATE.read_text(encoding="utf-8")
        + f"| inventory | - | {design_signoff.inventory_digest(root)} | {HEAD} | 2026-11-02 "
        "| https://example.com/review/1 |\n")
    put(root, "docs/discovery/reading-list.md", discovery(IB08))
    proc = run(str(SCRIPT), "prototype", "--root", str(root))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines()[-2:] == [f"wrote {THEME}", ASK]
    written = text(root)
    assert f"- name: Example Studio — {SOURCE}" in written
    assert "Evidence: docs/design/prototype/v1/" in written
    css = (root / "docs/design/prototype/v1/theme.css").read_text(encoding="utf-8")
    assert "--color-accent: #5a785f;" in css
    assert run(str(CHECK), "--root", str(root)).returncode == 0
    before = text(root)
    assert run(str(SCRIPT), "prototype", "--root", str(root)).returncode == 0
    assert text(root) == before  # an existing theme is never rewritten


def test_ac3_an_existing_placeholder_theme_is_not_filled_by_the_prototype(tmp_path):
    """REQ-044 AC3: SPEC-0037 rule 12 (answer 3: a placeholder theme stays as it is)."""
    root = tmp_path / "proj"
    put(root, "docs/requirements.md", REQUIREMENTS)
    put(root, "docs/design/inventory.md", INVENTORY)
    put(root, "docs/design/signoffs.md", SIGNOFFS_TEMPLATE.read_text(encoding="utf-8")
        + f"| inventory | - | {design_signoff.inventory_digest(root)} | {HEAD} | 2026-11-02 "
        "| https://example.com/review/1 |\n")
    placeholder = TEMPLATE.replace("{{evidence}}", "docs/design/prototype/v1/")
    put(root, THEME, placeholder)
    put(root, "docs/discovery/reading-list.md", discovery(IB08))
    assert run(str(SCRIPT), "prototype", "--root", str(root)).returncode == 0
    assert text(root) == placeholder


# --- answer 7: the settings -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "toml",
    [
        "",
        '[engines]\ndesign = "example-design"\n',
        '[design]\nui_paths = ["web/"]\nrender = "off"\npixel_tolerance = 2\n',
        '[kit]\nlayout = "plugin"\n',
        '[kit]\nlayout = "installed"\n',
        'review_mode = "solo"\npr_mode = "flow"\n',
        'review_mode = "team"\npr_mode = "strict"\n',
        *(f'execution = "{e}"\n' for e in ("hosted", "local", "hybrid", "pool")),
        '[delivery]\nwork_type = "pilot"\n',
        '[personal]\nforge = "files"\n',
        'mode = "adopt"\n',
    ],
)
def test_ac1_no_setting_changes_the_written_theme(tmp_path, toml):
    """REQ-044 AC1: brief #1840 answer 7 (the writer reads discovery and the versions only)."""
    plain = imported(tmp_path / "plain")
    set_ = imported(tmp_path / "set")
    put(set_, "agk.toml", toml)
    assert theme(plain).returncode == 0 and theme(set_).returncode == 0
    assert text(plain) == text(set_)


def test_ac1_a_layout_other_than_installed_or_plugin_is_refused_naming_the_setting(tmp_path):
    """REQ-044 AC1: brief #1840 answer 7 (`kit_root.layout` refuses it, naming `layout`)."""
    put(tmp_path, "agk.toml", '[kit]\nlayout = "elsewhere"\n')
    with pytest.raises(kit_root.Refused, match=r"\(setting: layout\)"):
        kit_root.layout(tmp_path)


def test_ac1_screens_of_discovery_is_not_read_by_the_theme(tmp_path):
    """REQ-044 AC1: brief #1840 answer 7 (a discovery document's `Screens` line)."""
    outs = []
    for screens in ("yes", "no", "open"):
        root = imported(tmp_path / screens)
        path = root / "docs/discovery/reading-list.md"
        path.write_text(path.read_text(encoding="utf-8") + f"\n## Screens\n\n{screens}\n", "utf-8")
        assert theme(root).returncode == 0
        outs.append(text(root))
    assert outs[0] == outs[1] == outs[2]


# --- answer 5: the class stays closed -------------------------------------------------------------


def theme_writes() -> set[str]:
    """`<module>.<function>` of every write in scripts/agk/*.py whose target names the theme."""
    found = set()
    for path in sorted(AGK.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for node in ast.walk(fn):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                    continue
                if node.func.attr not in ("write_text", "write_bytes", "open"):
                    continue
                target = ast.unparse(node.func.value)
                if re.search(r"\bTHEME\b|theme\.md", target):
                    found.add(f"{path.stem}.{fn.name}")
    return found


def test_ac1_only_the_two_writers_write_the_theme_and_both_fill_it_from_discovery():
    """REQ-044 AC1: brief #1840 answer 5 (a new theme writer cannot skip discovery)."""
    assert theme_writes() == {"design_prototype.write", "design.cmd_theme"}
    for path, name in ((AGK / "design_prototype.py", "theme_for"), (AGK / "design.py", "cmd_theme")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
        assert "design_brand." in ast.unparse(fn), f"{path.name}:{name} skips design_brand"


def test_ac1_every_kind_of_signed_off_version_is_accepted_as_evidence():
    """REQ-044 AC1: brief #1840 answer 5 (`EVIDENCE` and `folder_of` know the same kinds)."""
    accepted = set(re.findall(r"(\w+)/\(", check_design.EVIDENCE.pattern)) - {"mockups"}
    kinds = {design_signoff.folder_of(v).split("/")[-2] for v in ("v1", "i1")}
    assert accepted == kinds
    for version in ("v1", "i1"):
        assert check_design.EVIDENCE.search(f"Evidence: {design_signoff.folder_of(version)}/")
