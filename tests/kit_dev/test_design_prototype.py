"""Kit-only tests of `design.py prototype`: the click-through version (SPEC-0037 rules 4 to 6).

Brief #457 (REQ-044 AC3, the refusal clause of AC2, rule 12's refusal and theme move): from an
agreed inventory (an `inventory` row of `docs/design/signoffs.md` with its digest) and the theme,
the script writes the next free `docs/design/prototype/v<n>/` with `index.html`, one
`<screen>--<state>.html` per screen and state, `standard.css`, `theme.css`, the kit's runtime
`agk-prototype.js` unchanged, `demo.md` and `README.md`; data comes from the kit's fixture set
alone. Invented data only, in `tmp_path`; files only, no network and no model.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import design_signoff  # noqa: E402
import design_standard  # noqa: E402

SCRIPT = KIT_ROOT / "scripts" / "agk" / "design.py"
MODULE = KIT_ROOT / "scripts" / "agk" / "design_prototype.py"
CHECK = KIT_ROOT / "scripts" / "agk" / "check_design.py"
KIT = KIT_ROOT / "kit" / "templates" / "design-prototype"
RUNTIME = KIT / "agk-prototype.js"
FIXTURES = KIT / "fixtures.json"
STANDARD = KIT_ROOT / "kit" / "templates" / "design-standard.css"
THEME_TEMPLATE = KIT_ROOT / "kit" / "templates" / "design-theme.md"
SIGNOFFS_TEMPLATE = KIT_ROOT / "kit" / "templates" / "design-signoffs.md"
INVENTORY = "docs/design/inventory.md"
THEME = "docs/design/theme.md"
SIGNOFFS = "docs/design/signoffs.md"
PROTOTYPE = "docs/design/prototype"
REQUEST_NAMES = (
    "fetch",
    "XMLHttpRequest",
    "WebSocket",
    "EventSource",
    "import",
    "sendBeacon",
    "Worker",
    "localStorage",
    "sessionStorage",
    "indexedDB",
)
FIXED_FILES = {
    "index.html",
    "standard.css",
    "theme.css",
    "agk-prototype.js",
    "demo.md",
    "README.md",
}
HEAD = "0123456789abcdef0123456789abcdef01234567"
REFUSAL = "rule 3: the inventory has no inventory row in docs/design/signoffs.md for its digest"

REQUIREMENTS = """# Requirements

### REQ-001 — A reader keeps a list of books

- Acceptance: AC1 a reader adds a book; AC2 a reader opens a book
- Status: planned

### REQ-002 — A nightly job tidies the list

- Acceptance: AC1 the job removes duplicates
- Status: planned
"""

ALL_YES = "".join(f"- State {s}: yes\n" for s in design_standard.STATES)

INVENTORY_TEXT = f"""# Design inventory

The screens and states of the product.

## Requirements

### REQ-001 — A reader keeps a list of books

- Specs: SPEC-0001
- Screens: book-list, book-detail, book-form

### REQ-002 — A nightly job tidies the list

- Specs: none
- Screens: no screen: a job with no user interface

## Screens

### book-list

- Flow: Reading
- Pattern: list with filter and sort
- Links to: book-detail, book-form
- State default: yes
- State empty: yes
- State loading: yes
- State error: yes
- State no-permission: n/a: every reader sees their own list
- State long-content: yes
- State success: yes

### book-detail

- Flow: Reading
- Pattern: detail
- Links to: book-list
{ALL_YES}- State archived: yes

### book-form

- Flow: Adding
- Pattern: form with validation
- Links to: none
{ALL_YES}"""

EXPECTED_PAGES = (
    [f"book-list--{s}.html" for s in design_standard.STATES if s != "no-permission"]
    + [f"book-detail--{s}.html" for s in (*design_standard.STATES, "archived")]
    + [f"book-form--{s}.html" for s in design_standard.STATES]
)
STATES_OF = {
    "book-list": [s for s in design_standard.STATES if s != "no-permission"],
    "book-detail": [*design_standard.STATES, "archived"],
    "book-form": list(design_standard.STATES),
}

OLD_THEME = """# Theme

The brand record and the rules of this product's design.

## Brand

- name: Reading List — source: the owner's brief of 2026-10-20
- primary: #1d4ed8 — source: the brand guide, page 2
- font: system-ui — source: the kit's default, a system font with no download

## Tokens

```css
:root {
  --bg: #fdfdfb;
  --fg: #121212;
  --muted: #4a4a4a;
  --accent: #1d4ed8;
  --accent-fg: #ffffff;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f1216;
    --fg: #f4f4f4;
    --muted: #b8b8b8;
    --accent: #93b4fd;
    --accent-fg: #0f1115;
  }
}
```

## Contrast

- --fg on --bg
- --muted on --bg
- --accent-fg on --accent

## Rules

1. One token block, light and dark; every colour of a page is a token.

## Evidence

Evidence: docs/design/mockups/2026-10-24-home/
"""
OLD_LIGHT = {
    "--bg": "#fdfdfb",
    "--fg": "#121212",
    "--muted": "#4a4a4a",
    "--accent": "#1d4ed8",
    "--accent-fg": "#ffffff",
}
OLD_DARK = {
    "--bg": "#0f1216",
    "--fg": "#f4f4f4",
    "--muted": "#b8b8b8",
    "--accent": "#93b4fd",
    "--accent-fg": "#0f1115",
}


# --- helpers -----------------------------------------------------------------------------------


def put(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def agree(root: Path) -> None:
    """Append the `inventory` row of the current inventory's digest (the person's agreement)."""
    path = root / SIGNOFFS
    if not path.is_file():
        put(root, SIGNOFFS, SIGNOFFS_TEMPLATE.read_text(encoding="utf-8"))
    row = (
        f"| inventory | - | {design_signoff.inventory_digest(root)} | {HEAD} | 2026-11-02 "
        "| https://example.com/review/1 |\n"
    )
    path.write_text(path.read_text(encoding="utf-8") + row, encoding="utf-8")


def project(root: Path, *, agreed: bool = True) -> Path:
    put(root, "docs/requirements.md", REQUIREMENTS)
    put(root, INVENTORY, INVENTORY_TEXT)
    if agreed:
        agree(root)
    return root


def design(root: Path, *args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--root", str(root)],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def check(root: Path):
    return subprocess.run(
        [sys.executable, str(CHECK), "--root", str(root)],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def prototype(root: Path) -> Path:
    proc = design(root, "prototype")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return root / PROTOTYPE / "v1"


def files(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


class Page(HTMLParser):
    """The parts of a page these tests read: elements, links, scripts, stylesheets, headings."""

    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.navs: list[dict] = []
        self._nav: dict | None = None
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        found = {k: v or "" for k, v in attrs}
        self.tags.append((tag, found))
        if tag == "nav":
            self._nav = {"attrs": found, "links": []}
            self.navs.append(self._nav)
        elif tag == "a" and self._nav is not None and "href" in found:
            self._nav["links"].append(found)

    def handle_endtag(self, tag):
        if tag == "nav":
            self._nav = None

    def handle_data(self, data):
        self.text.append(data)

    def all(self, tag: str) -> list[dict[str, str]]:
        return [attrs for name, attrs in self.tags if name == tag]


def parse(path: Path) -> Page:
    page = Page()
    page.feed(path.read_text(encoding="utf-8"))
    return page


def nav(page: Page, label: str) -> dict:
    found = [n for n in page.navs if n["attrs"].get("aria-label", "").startswith(label)]
    assert len(found) == 1, (label, [n["attrs"] for n in page.navs])
    return found[0]


def strings(value) -> list[str]:
    if isinstance(value, dict):
        return [s for v in value.values() for s in strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in strings(v)]
    return [str(value)]


EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
HOST = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://([^/\s\"'<>:]+)")
PHONE = re.compile(r"\+\d[\d ()-]{6,}\d")


# --- answer 3: the folder ---------------------------------------------------------------------


def test_ac3_prototype_writes_one_page_per_screen_and_state_and_the_fixed_files(tmp_path):
    """REQ-044 AC3: SPEC-0037 rule 4 (one `<screen>--<state>.html` per screen and state)."""
    project(tmp_path)
    proc = design(tmp_path, "prototype")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"wrote {PROTOTYPE}/v1/" in proc.stdout
    folder = tmp_path / PROTOTYPE / "v1"
    names = {p.name for p in folder.iterdir()}
    assert names == FIXED_FILES | set(EXPECTED_PAGES)
    assert all(p.is_file() for p in folder.iterdir())
    # a state that is `n/a: <reason>` has no page
    assert not (folder / "book-list--no-permission.html").exists()


def test_ac3_each_page_has_lang_viewport_one_h1_the_two_stylesheets_and_the_script_last(tmp_path):
    """REQ-044 AC3: SPEC-0037 rules 4 and 5 (brief #457 answer 3)."""
    folder = prototype(project(tmp_path))
    for name in [*EXPECTED_PAGES, "index.html"]:
        text = (folder / name).read_text(encoding="utf-8")
        page = parse(folder / name)
        html = page.all("html")
        assert len(html) == 1 and html[0].get("lang"), name
        assert any(
            m.get("name") == "viewport" and "width=device-width" in m.get("content", "")
            for m in page.all("meta")
        ), name
        assert len(page.all("h1")) == 1, name
        links = page.all("link")
        assert [(lk.get("rel"), lk.get("href")) for lk in links] == [
            ("stylesheet", "standard.css"),
            ("stylesheet", "theme.css"),
        ], name
        scripts = page.all("script")
        assert scripts == [{"src": "agk-prototype.js"}], name
        assert text.count('<script src="agk-prototype.js"></script>') == 1, name
        after = text.split('<script src="agk-prototype.js"></script>', 1)[1]
        assert re.fullmatch(r"\s*</body>\s*</html>\s*", after), name
        assert not re.search(r"\son[a-z]+\s*=|javascript\s*:|\sstyle\s*=|<style", text, re.I)


def test_ac3_every_page_has_a_state_bar_of_plain_links_to_every_state_of_its_screen(tmp_path):
    """REQ-044 AC3: SPEC-0037 rule 4 (the state bar), with the current state marked."""
    folder = prototype(project(tmp_path))
    for screen, states in STATES_OF.items():
        for state in states:
            page = parse(folder / f"{screen}--{state}.html")
            bar = nav(page, "States")
            hrefs = [a["href"] for a in bar["links"]]
            assert hrefs == [f"{screen}--{s}.html" for s in states], (screen, state)
            current = [a["href"] for a in bar["links"] if a.get("aria-current") == "page"]
            assert current == [f"{screen}--{state}.html"]


def test_ac3_every_link_resolves_to_a_file_of_the_folder(tmp_path):
    """REQ-044 AC3: SPEC-0037 rule 4 (plain relative links; opened from the files, no server)."""
    folder = prototype(project(tmp_path))
    pages = [p for p in folder.iterdir() if p.suffix == ".html"]
    for path in pages:
        page = parse(path)
        hrefs = [a["href"] for a in page.all("a")]
        assert hrefs, path.name
        for href in hrefs:
            assert "://" not in href and not href.startswith(("/", "#")), (path.name, href)
            target = href.split("#", 1)[0]
            assert "/" not in target and (folder / target).is_file(), (path.name, href)


def test_ac3_the_links_to_line_becomes_plain_links_to_each_linked_screen(tmp_path):
    """REQ-044 AC3: SPEC-0037 rule 4 (pages link to one another as the flows link)."""
    folder = prototype(project(tmp_path))
    for state in STATES_OF["book-list"]:
        page = parse(folder / f"book-list--{state}.html")
        hrefs = [a["href"] for a in nav(page, "Links")["links"]]
        assert hrefs == ["book-detail--default.html", "book-form--default.html"], state
    page = parse(folder / "book-detail--archived.html")
    assert [a["href"] for a in nav(page, "Links")["links"]] == ["book-list--default.html"]
    page = parse(folder / "book-form--default.html")
    assert not [n for n in page.navs if n["attrs"].get("aria-label", "").startswith("Links")]


def test_ac3_index_lists_the_flows_and_starts_each_demo_path(tmp_path):
    """REQ-044 AC3: SPEC-0037 rule 4 (`index.html`: the flows and the start of each demo path)."""
    folder = prototype(project(tmp_path))
    text = (folder / "index.html").read_text(encoding="utf-8")
    assert "Reading" in text and "Adding" in text
    hrefs = [a["href"] for a in parse(folder / "index.html").all("a")]
    assert "book-list--default.html#demo" in hrefs
    assert "book-form--default.html#demo" in hrefs
    for page in EXPECTED_PAGES:
        assert page in hrefs, page


def test_ac3_demo_md_has_one_sentence_per_step_of_each_flow(tmp_path):
    """REQ-044 AC3: SPEC-0037 rule 4 (`demo.md`: one sentence for the presenter per step)."""
    folder = prototype(project(tmp_path))
    text = (folder / "demo.md").read_text(encoding="utf-8")
    flows: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = flows.setdefault(line[3:].strip(), [])
        elif current is not None and re.match(r"^\d+\. ", line):
            current.append(line)
    assert list(flows) == ["Reading", "Adding"]
    assert len(flows["Reading"]) == 2 and len(flows["Adding"]) == 1
    for steps in flows.values():
        for number, step in enumerate(steps, 1):
            assert step.startswith(f"{number}. `"), step
            sentence = step.split("`: ", 1)[1]
            assert sentence.endswith(".") and sentence[0].isupper(), step
            assert sentence.count(". ") == 0 and sentence.count(".") == 1, step
    assert flows["Reading"][0].startswith("1. `book-list--default.html`: ")
    assert flows["Reading"][1].startswith("2. `book-detail--default.html`: ")


def test_ac3_each_step_page_carries_its_sentence_and_plain_links_to_the_next_and_previous(tmp_path):
    """REQ-044 AC3: SPEC-0037 rule 5 (demo mode reads only links and `data-demo`)."""
    folder = prototype(project(tmp_path))
    demo = (folder / "demo.md").read_text(encoding="utf-8")
    sentences = dict(re.findall(r"(?m)^\d+\. `([^`]+)`: (.*)$", demo))
    first = nav(parse(folder / "book-list--default.html"), "Demo")
    assert first["attrs"]["data-demo"] == sentences["book-list--default.html"]
    assert {a.get("rel"): a["href"] for a in first["links"]} == {
        "prev": "index.html",
        "next": "book-detail--default.html",
    }
    last = nav(parse(folder / "book-detail--default.html"), "Demo")
    assert {a.get("rel"): a["href"] for a in last["links"]} == {
        "prev": "book-list--default.html",
        "next": "index.html",
    }
    page = parse(folder / "book-list--empty.html")
    assert not [n for n in page.navs if "data-demo" in n["attrs"]]


# --- answer 1: the runtime --------------------------------------------------------------------


def test_ac3_the_runtime_is_copied_byte_equal_and_is_versioned(tmp_path):
    """REQ-044 AC3: SPEC-0037 rule 5 (the kit's runtime, unchanged, `// agk-prototype <n>`)."""
    folder = prototype(project(tmp_path))
    assert (folder / "agk-prototype.js").read_bytes() == RUNTIME.read_bytes()
    first = RUNTIME.read_text(encoding="utf-8").splitlines()[0]
    assert re.fullmatch(r"// agk-prototype [1-9]\d*", first)
    assert (folder / "standard.css").read_bytes() == STANDARD.read_bytes()


@pytest.mark.parametrize("name", REQUEST_NAMES)
def test_ac3_the_runtime_holds_no_request_name(name):
    """REQ-044 AC3: SPEC-0037 rule 5 (no request of any kind, no storage, no worker)."""
    assert name.lower() not in RUNTIME.read_text(encoding="utf-8").lower()


def test_ac3_the_runtime_adds_keyboard_access_and_a_demo_mode_from_links_and_data_demo():
    """REQ-044 AC3: SPEC-0037 rule 5 (keyboard access to the state bar; step through a flow)."""
    text = RUNTIME.read_text(encoding="utf-8")
    assert "keydown" in text and "data-demo" in text
    assert 'rel="next"' in text and 'rel="prev"' in text
    assert "eval(" not in text and "innerHTML" not in text
    assert "document.cookie" not in text and "http" not in text


# --- answer 2: the fixtures -------------------------------------------------------------------


def test_ac3_the_fixtures_are_invented_and_on_the_example_domains_only():
    """REQ-044 AC3: SPEC-0037 rule 6 (example.com, example.org or example.net only)."""
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    values = strings(data)
    emails = [e for v in values for e in EMAIL.findall(v)]
    hosts = [h for v in values for h in HOST.findall(v)]
    assert emails and hosts
    for found in [e.split("@", 1)[1] for e in emails] + hosts:
        assert re.fullmatch(r"(?:[\w-]+\.)*example\.(?:com|org|net)", found), found
    for key in ("person", "organisation", "address", "amount", "item", "phone"):
        assert any(key in k for k in flat_keys(data)), key
    assert [v for v in values if len(v) >= 120], "long values for long-content"
    for value in values:
        assert not re.search(r"\[[^\]]*\]|lorem ipsum|\bTODO\b|\bTBD\b", value, re.I), value


def flat_keys(data, prefix=""):
    for key, value in data.items():
        name = f"{prefix}{key}"
        yield name
        if isinstance(value, dict):
            yield from flat_keys(value, f"{name}.")


def test_ac3_every_email_host_and_phone_on_the_pages_is_in_the_fixtures(tmp_path):
    """REQ-044 AC3: SPEC-0037 rule 6 (a page's data comes from the fixture set alone)."""
    folder = prototype(project(tmp_path))
    known = strings(json.loads(FIXTURES.read_text(encoding="utf-8")))
    emails = {e for v in known for e in EMAIL.findall(v)}
    hosts = {h for v in known for h in HOST.findall(v)}
    phones = {p for v in known for p in PHONE.findall(v)}
    seen_email = False
    for path in folder.glob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert "{{" not in text and "}}" not in text, path.name
        assert not re.search(r"lorem ipsum|\bTODO\b|\bTBD\b", text, re.I), path.name
        body = "".join(parse(path).text)
        assert not re.search(r"\[[^\]]*\]", body), path.name
        for email in EMAIL.findall(text):
            seen_email = True
            assert email in emails, path.name
        for host in HOST.findall(text):
            assert host in hosts, path.name
        for phone in PHONE.findall(text):
            assert phone in phones, path.name
    assert seen_email


# --- versions, refusals and the theme --------------------------------------------------------


def test_ac3_v2_is_written_when_v1_exists_and_v1_is_never_touched(tmp_path):
    """REQ-044 AC3: SPEC-0037 rule 4 (`Q-S0037-4`: the next free `v<n>`; never overwritten)."""
    v1 = prototype(project(tmp_path))
    before = files(v1)
    proc = design(tmp_path, "prototype")
    assert proc.returncode == 0, proc.stdout
    assert f"wrote {PROTOTYPE}/v2/" in proc.stdout
    assert files(v1) == before
    assert {p.name for p in (tmp_path / PROTOTYPE / "v2").iterdir()} == FIXED_FILES | set(
        EXPECTED_PAGES
    )
    (tmp_path / PROTOTYPE / "v7").mkdir()
    assert "wrote docs/design/prototype/v8/" in design(tmp_path, "prototype").stdout


def test_ac2_prototype_refuses_an_inventory_without_its_row_and_writes_nothing(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (nothing is drawn before the person's agreement)."""
    project(tmp_path, agreed=False)
    before = files(tmp_path)
    proc = design(tmp_path, "prototype")
    assert proc.returncode == 1
    assert proc.stdout == f"FAIL design: {REFUSAL}\n"
    assert files(tmp_path) == before


def test_ac2_a_row_for_an_earlier_inventory_does_not_count(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (a row names a digest; a changed inventory is not agreed)."""
    project(tmp_path)
    put(tmp_path, INVENTORY, INVENTORY_TEXT.replace("Flow: Adding", "Flow: Writing"))
    proc = design(tmp_path, "prototype")
    assert (proc.returncode, proc.stdout) == (1, f"FAIL design: {REFUSAL}\n")
    digest = design_signoff.inventory_digest(tmp_path)
    assert digest not in proc.stdout
    assert not (tmp_path / PROTOTYPE).exists()


def test_ac2_a_design_row_with_the_inventory_digest_does_not_count(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (only an `inventory` row agrees the inventory)."""
    project(tmp_path, agreed=False)
    put(tmp_path, SIGNOFFS, SIGNOFFS_TEMPLATE.read_text(encoding="utf-8"))
    row = (
        f"| design | v1 | {design_signoff.inventory_digest(tmp_path)} | {HEAD} | 2026-11-02 "
        "| https://example.com/review/1 |\n"
    )
    path = tmp_path / SIGNOFFS
    path.write_text(path.read_text(encoding="utf-8") + row, encoding="utf-8")
    proc = design(tmp_path, "prototype")
    assert (proc.returncode, proc.stdout) == (1, f"FAIL design: {REFUSAL}\n")


def test_ac2_prototype_refuses_without_an_inventory(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (an inventory comes first)."""
    put(tmp_path, "docs/requirements.md", REQUIREMENTS)
    proc = design(tmp_path, "prototype")
    assert proc.returncode == 1 and "FAIL design: rule 3:" in proc.stdout
    assert not (tmp_path / "docs" / "design").exists()


def test_ac2_prototype_takes_no_other_option(tmp_path):
    """REQ-044 AC3: brief #457 answer 3 (the command takes only --root)."""
    project(tmp_path)
    proc = design(tmp_path, "prototype", "--name", "home")
    assert proc.returncode == 2
    assert not (tmp_path / PROTOTYPE).exists()


def test_ac3_with_no_theme_one_is_written_from_the_standard_template(tmp_path):
    """REQ-044 AC3: SPEC-0037 rule 12 (brief #457 answer 5: the evidence is the version)."""
    folder = prototype(project(tmp_path))
    theme = (tmp_path / THEME).read_text(encoding="utf-8")
    assert theme == THEME_TEMPLATE.read_text(encoding="utf-8").replace(
        "{{evidence}}", f"{PROTOTYPE}/v1/"
    )
    assert design_standard.theme_format(theme) == "standard"
    assert design_standard.standard_theme_problems(theme) == []
    css = (folder / "theme.css").read_text(encoding="utf-8")
    block = re.findall(r"```css\n(.*?)```", theme, re.S)[0]
    assert block in css
    proc = check(tmp_path)
    assert proc.returncode == 0, proc.stdout
    assert "FAIL" not in proc.stdout


def test_ac3_the_layout_block_sets_density_and_alignment_on_each_page(tmp_path):
    """REQ-044 AC3: SPEC-0037 rule 2 (density and alignment of the theme's layout block)."""
    project(tmp_path)
    text = THEME_TEMPLATE.read_text(encoding="utf-8").replace("{{evidence}}", f"{PROTOTYPE}/v1/")
    text = re.sub(r"(?m)^- density: .*$", "- density: compact", text)
    text = re.sub(r"(?m)^- alignment: .*$", "- alignment: centre", text)
    put(tmp_path, THEME, text)
    folder = prototype(tmp_path)
    html = parse(folder / "book-list--default.html").all("html")[0]
    assert (html.get("data-density"), html.get("data-align")) == ("compact", "centre")
    assert (tmp_path / THEME).read_text(encoding="utf-8") == text


def test_ac3_a_theme_on_the_standard_is_left_as_it_is(tmp_path):
    """REQ-044 AC3: SPEC-0037 rule 2 (a theme is the owner's once written)."""
    project(tmp_path)
    text = THEME_TEMPLATE.read_text(encoding="utf-8").replace("{{evidence}}", "docs/x/")
    put(tmp_path, THEME, text)
    prototype(tmp_path)
    assert (tmp_path / THEME).read_text(encoding="utf-8") == text


def test_ac3_an_old_theme_moves_its_five_tokens_unchanged_in_value_in_light_and_dark(tmp_path):
    """REQ-044 AC3: SPEC-0037 rules 2 and 12 (brief #457 answer 5)."""
    project(tmp_path)
    put(tmp_path, THEME, OLD_THEME)
    (tmp_path / "docs/design/mockups/2026-10-24-home").mkdir(parents=True)
    proc = design(tmp_path, "prototype")
    assert proc.returncode == 0, proc.stdout
    assert f"moved {THEME} to agk design standard {design_standard.STANDARD}" in proc.stdout
    theme = (tmp_path / THEME).read_text(encoding="utf-8")
    assert design_standard.theme_format(theme) == "standard"
    assert re.search(rf"(?m)^Standard: agk design standard {design_standard.STANDARD}$", theme)
    light, dark = design_standard.theme_colours(theme)
    for old, role in design_standard.OLD_TOKENS.items():
        assert light[role] == OLD_LIGHT[old], old
        assert dark[role] == OLD_DARK[old], old
    block = re.findall(r"```css\n(.*?)```", theme, re.S)
    assert len(block) == 1
    assert "--bg" not in block[0] and "--accent-fg" not in block[0]


def test_ac3_an_old_theme_keeps_its_brand_record_source_lines_and_evidence_line(tmp_path):
    """REQ-044 AC3: SPEC-0037 rule 12 (the brand record is carried over unchanged)."""
    project(tmp_path)
    put(tmp_path, THEME, OLD_THEME)
    (tmp_path / "docs/design/mockups/2026-10-24-home").mkdir(parents=True)
    prototype(tmp_path)
    theme = (tmp_path / THEME).read_text(encoding="utf-8")
    for line in OLD_THEME.splitlines():
        if line.startswith("- ") and " — source: " in line:
            assert line in theme.splitlines(), line
    assert "Evidence: docs/design/mockups/2026-10-24-home/" in theme.splitlines()
    assert design_standard.standard_theme_problems(theme) == []
    proc = check(tmp_path)  # the empty mockup folder fails on its own; the theme does not
    assert f"{THEME}:" not in proc.stdout, proc.stdout


def test_ac3_an_old_theme_with_a_token_the_standard_has_no_role_for_is_refused(tmp_path):
    """REQ-044 AC3: SPEC-0037 rule 2 (only the five old tokens map; nothing is guessed)."""
    project(tmp_path)
    extra = "  --accent-fg: #ffffff;\n  --card: #abcdef;\n"
    put(tmp_path, THEME, OLD_THEME.replace("  --accent-fg: #ffffff;\n", extra, 1))
    before = files(tmp_path)
    proc = design(tmp_path, "prototype")
    assert proc.returncode == 1 and "FAIL design: rule 2:" in proc.stdout
    assert "#abcdef" not in proc.stdout and "--card" not in proc.stdout
    assert files(tmp_path) == before


# --- answer 6: no new mockup folder -----------------------------------------------------------


def test_ac4_write_refuses_a_new_mockup_folder_and_writes_nothing(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 12 (`Q-S0037-10`: `/agk:design <name>` refuses)."""
    proc = design(tmp_path, "write", "--name", "home", "--date", "2026-10-24")
    assert proc.returncode == 1
    assert proc.stdout == (
        "FAIL design: rule 12: a new mockup folder is not written; use /agk:design prototype\n"
    )
    assert not (tmp_path / "docs").exists()


# --- the skill and the script -----------------------------------------------------------------


def test_ac3_the_skill_has_the_prototype_step_and_no_write_step():
    """REQ-044 AC3: brief #457 answer 6 (the skill's write step becomes the prototype step)."""
    text = (KIT_ROOT / "skills" / "design" / "SKILL.md").read_text(encoding="utf-8")
    assert 'design.py" prototype' in text
    assert 'design.py" write' not in text
    hint = re.search(r'(?m)^argument-hint: "(.*)"$', text)
    assert hint and "prototype" in hint.group(1) and "mockup name" not in hint.group(1)
    assert "Approve: design" in text and "never posts" in text
    assert "screenshots/" in text


def test_ac3_the_writer_reads_files_only_and_runs_nothing():
    """REQ-044 AC3: SPEC-0037 rule 13 (no network request from a design command)."""
    source = MODULE.read_text(encoding="utf-8")
    assert not re.search(
        r"^\s*(?:import|from)\s+(?:socket|urllib|http|requests|ssl|subprocess)\b", source, re.M
    )
    assert "shell=True" not in source and "os.system" not in source


def test_ac3_the_kit_folder_has_the_files_of_answer_1():
    """REQ-044 AC3: brief #457 answer 1."""
    names = {p.name for p in KIT.iterdir()}
    assert names == {"index.html", "page.html", "agk-prototype.js", "fixtures.json", "README.md"}
