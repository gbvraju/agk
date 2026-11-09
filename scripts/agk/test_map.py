"""The generated test map (SPEC-0055 rule 5, build (c); REQ-062 AC3). Installed.

    python3 scripts/agk/test_map.py build [--root DIR]

Reads the tree at the head (never the working tree, and its own `agk.toml` from there) and writes
the git-ignored file `.agk-test-map.toml`: the first line is `# tree <tree id>`, then one
`[[testing.map]]` entry for each file that a test depends on, the shape of `[testing] map`, with no
date or commit id, so one tree gives the same bytes. A test file is what `impact.py` calls one
(`test_dirs`, `test_patterns`).

A test depends on what its imports reach, followed through the files they import: Python by `ast`,
JavaScript or TypeScript by import and require lines read as text, with the `paths` and `baseUrl`
of the nearest `tsconfig.json` and its `extends`, Go by the import lines and `go.mod` at package
granularity. A test in a Gradle module (`settings.gradle`, the `project(...)` dependencies) or an
Xcode target (`project.pbxproj`, read as text) depends on every file of that module or target and
of those it depends on. Where several files could be meant, each counts,
because an entry only adds tests. A file no import reaches falls back on the folder conventions: a
test beside it, in `__tests__/`, or in a module's `src/test/` for its `src/main/`. A file that
cannot be read adds no entries, so what only it reaches stays unmapped. Files and git only.

It also writes one `[[testing.links]]` entry (SPEC-0055 rule 7) for a schema file (`.proto`,
`.graphql`, `.graphqls`, `.gql`, or a YAML or JSON file whose root says `openapi` or `swagger`) that
a file of another `[proof]` area names by a path, an import or a generator's input alike, naming
that area's `contract` level; an area with none adds no link.
"""

from __future__ import annotations

import ast
import json
import os
import posixpath
import re
import subprocess  # nosec B404 - fixed argument list only, no shell
import sys
import tempfile
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, area_levels, git, load_config, proof_areas, repo_root, run
from impact import MAP_FILE, is_doc, is_test_file

NAME = "test_map"
OUT = MAP_FILE
READ_LIMIT = 2 * 1024 * 1024  # a larger file is not read: generated, or minified
JS_SOURCES = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")
JS_TRIED = (".ts", ".tsx", ".mts", ".cts", ".d.ts", ".js", ".jsx", ".mjs", ".cjs", ".json")
TS_FOR_JS = {".js": (".ts", ".tsx"), ".jsx": (".tsx",), ".mjs": (".mts",), ".cjs": (".cts",)}
SPECIFIER = re.compile(
    r"(?:\b(?:from|import)\s*|\b(?:import|require)\s*\(\s*)['\"`]([^'\"`\n]+)['\"`]"
)
NOT_A_GLOB = re.compile(r"[*?\\:\x00-\x1f\x7f]")  # impact.py would refuse or widen such a path
SUBJECT = re.compile(r"(?:test_)?(.+?)(?:[._-](?:test|spec)|Tests?|Spec)?")
STRING = r'"(?:\\.|[^"\\])*"'
COMMENT = re.compile(STRING + r"|//[^\n]*|/\*.*?\*/", re.S)
TRAILING_COMMA = re.compile(STRING + r"|,(?=\s*[}\]])")
STACK_FILES = (
    "go.mod",
    "settings.gradle",
    "settings.gradle.kts",
    "build.gradle",
    "build.gradle.kts",
    "project.pbxproj",
)
SOURCE_COMMENT = re.compile(
    r"""\"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|`[^`]*`|//[^\n]*|/\*.*?\*/""", re.S
)
QUOTED = re.compile(r"""["']([^"'\n]+)["']""")
GRADLE_INCLUDE = re.compile(r"""(?<![\w.])include\s*\(?\s*((?:["'][^"'\n]+["']\s*,?\s*)+)""")
GRADLE_PROJECT = re.compile(r"""\bproject\s*\(\s*(?:path\s*[:=]\s*)?["']([^"'\n]+)["']""")
GRADLE_DIR = re.compile(
    r"""\bproject\s*\(\s*["'](:[^"'\n]+)["']\s*\)\s*\.\s*projectDir\s*=\s*(?:new\s+)?[fF]ile\s*\("""
    r"""\s*(?:\w+\s*,\s*)?["']([^"'\n]+)["']"""
)
GO_STRING = r"""(?:"[^"\n]*"|`[^`]*`)"""
GO_PACKAGE = re.compile(r"\s*package\s+\w+\s*;?")
GO_IMPORT = re.compile(
    rf"""\s*import\s*(?:\(((?:[^()"`]|{GO_STRING})*)\)|((?:[\w.]+\s*)?{GO_STRING}))\s*;?"""
)
GO_PATH = re.compile(r"""["`]([^"`\n]+)["`]""")
GO_MODULE = re.compile(r"""^\s*module\s+\(?\s*"?([^\s"()]+)""", re.M)
GO_REPLACE = re.compile(
    r"""^[ \t]*(?:replace[ \t]+)?"?([^\s"]+)"?(?:[ \t]+v\S+)?[ \t]*=>[ \t]*"""
    r""""?(\.\.?(?:/[^\s"]*)?)"?[ \t]*$""",
    re.M,
)
PLIST_TOKEN = re.compile(r"""/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|[{}()=;,]|[^\s{}()=;,"]+""", re.S)
SCHEMA_SUFFIXES = (".proto", ".graphql", ".graphqls", ".gql")
OPENAPI_SUFFIXES = (".yaml", ".yml", ".json")
OPENAPI_ROOT = re.compile(r"""^\s*["']?(?:openapi|swagger)["']?\s*:\s*["']?[23]\.""", re.M)
PATH_WORD = re.compile(r"[\w./-]+")
UNREADABLE = "test_map: a tsconfig cannot be read and adds nothing (setting: compilerOptions.paths)"


def _bytes(root: Path, args: list[str], given: bytes | None = None) -> bytes:
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, input=given, capture_output=True
    )
    if done.returncode != 0:
        raise CheckError(f"git {args[0]} failed (setting: {NAME})")
    return done.stdout


def listing(root: Path) -> dict[str, tuple[str, int]]:
    """Path -> (blob id, size) of each regular file at the head; a non-UTF-8 name is left out."""
    found = {}
    for record in _bytes(root, ["ls-tree", "-r", "-l", "-z", "HEAD"]).split(b"\0"):
        head, _, raw = record.partition(b"\t")
        fields = head.split()
        if len(fields) == 4 and fields[0] in (b"100644", b"100755"):
            try:
                found[raw.decode("utf-8")] = (fields[2].decode(), int(fields[3]))
            except UnicodeDecodeError:
                continue
    return found


def blobs(root: Path, ids: list[str]) -> dict[str, str]:
    asked = "".join(f"{oid}\n" for oid in ids).encode()
    out, at, found = _bytes(root, ["cat-file", "--batch"], asked), 0, {}
    for oid in ids:
        end = out.index(b"\n", at)
        size, at = int(out[at:end].split()[2]), end + 1
        found[oid] = out[at : at + size].decode("utf-8", "replace")
        at += size + 1
    return found


def inside(path: str) -> str | None:
    """PATH normalized, or None when it leaves the repository."""
    path = posixpath.normpath(path)
    return None if path == ".." or path.startswith(("../", "/")) else ("" if path == "." else path)


def package_roots(folder: str) -> list[str]:
    """Where an absolute import can start: the importer's folder, those above, and their `src/`."""
    roots = []
    while True:
        roots += [folder, posixpath.join(folder, "src")]
        if not folder:
            return roots
        folder = posixpath.dirname(folder)


def modules(base: str, parts: list[str], files: set[str]) -> set[str]:
    stems = [posixpath.join(base, *parts[:n]) for n in range(1, len(parts) + 1)]
    return {c for s in stems for c in (s + ".py", s + "/__init__.py") if c in files}


def python_edges(path: str, text: str, files: set[str]) -> set[str]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return set()
    folder, found = posixpath.dirname(path), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            wanted, bases = [a.name.split(".") for a in node.names], package_roots(folder)
        elif isinstance(node, ast.ImportFrom):
            prefix = node.module.split(".") if node.module else []
            wanted, bases = (
                [prefix, *[[*prefix, a.name] for a in node.names]],
                package_roots(folder),
            )
            if node.level:
                base = inside(posixpath.join(folder, *[".."] * (node.level - 1)))
                if base is None:
                    continue
                bases = [base]
                found |= {c for c in [posixpath.join(base, "__init__.py")] if c in files}
        else:
            continue
        found |= {m for base in bases for parts in wanted for m in modules(base, parts, files)}
    return found


class TsConfigs:
    """The `paths` and `baseUrl` of the config nearest a folder, read from the head."""

    def __init__(self, root: Path, tree: dict[str, tuple[str, int]]) -> None:
        self.root, self.tree, self.nearest_of, self.broken = root, tree, {}, False

    def _load(self, path: str, seen: tuple[str, ...]) -> dict:
        def keep(found: re.Match) -> str:
            return found[0] if found[0][0] == '"' else ""

        folder, merged = posixpath.dirname(path), {}
        oid, size = self.tree[path]
        try:
            if size > READ_LIMIT:
                raise ValueError
            text = COMMENT.sub(keep, blobs(self.root, [oid])[oid])
            data = json.loads(TRAILING_COMMA.sub(keep, text))
            options = data.get("compilerOptions", {})
            paths, base_url = options.get("paths"), options.get("baseUrl")
            parents = data.get("extends", [])
            parents = [parents] if isinstance(parents, str) else list(parents)
            if not (paths is None or all(isinstance(v, list) for v in paths.values())):
                raise ValueError
        except (ValueError, AttributeError, TypeError, RecursionError):
            self.broken = True
            return {}
        for parent in parents:
            base = inside(posixpath.join(folder, parent)) if str(parent).startswith(".") else None
            target = next((c for c in (base, f"{base}.json") if c in self.tree), None)
            if target and target not in (*seen, path):
                merged.update(self._load(target, (*seen, path)))
        if isinstance(base_url, str) and inside(posixpath.join(folder, base_url)) is not None:
            merged["baseUrl"] = inside(posixpath.join(folder, base_url))
        if paths is not None:
            merged.update(paths=paths, paths_folder=folder)
        return merged

    def nearest(self, folder: str) -> dict:
        if folder not in self.nearest_of:
            config = posixpath.join(folder, "tsconfig.json")
            found = self._load(config, ()) if config in self.tree else None
            if found is None:
                found = self.nearest(posixpath.dirname(folder)) if folder else {}
            self.nearest_of[folder] = found
        return self.nearest_of[folder]


def alias_bases(spec: str, config: dict) -> list[str | None]:
    """The paths a bare specifier can mean: under `baseUrl`, and by the one `paths` pattern the
    compiler picks, the exact one or else the longest prefix."""
    paths = config.get("paths", {})
    origin = config.get("baseUrl", config.get("paths_folder", ""))
    bases = [inside(posixpath.join(config["baseUrl"], spec))] if "baseUrl" in config else []
    star, chosen = "", paths.get(spec)
    if chosen is None:
        fits = [p for p in paths if p.count("*") == 1 and _fits(spec, *p.split("*"))]
        if fits:
            prefix, suffix = max(fits, key=lambda p: len(p.split("*")[0])).split("*")
            chosen = paths[f"{prefix}*{suffix}"]
            star = spec[len(prefix) : len(spec) - len(suffix)]
    return bases + [inside(posixpath.join(origin, str(s).replace("*", star))) for s in chosen or []]


def _fits(spec: str, prefix: str, suffix: str) -> bool:
    return spec.startswith(prefix) and spec.endswith(suffix) and len(spec) >= len(prefix + suffix)


def js_edges(path: str, text: str, files: set[str], configs: TsConfigs) -> set[str]:
    folder, found = posixpath.dirname(path), set()
    for spec in SPECIFIER.findall(text):
        if spec.startswith("."):
            bases = [inside(posixpath.join(folder, spec))]
        else:
            bases = alias_bases(spec, configs.nearest(folder))
        for base in bases:
            if base is None:
                continue
            stem, ext = posixpath.splitext(base)
            tried = [base, *[stem + e for e in TS_FOR_JS.get(ext, ())]]
            tried += [base + e for e in JS_TRIED]
            tried += [posixpath.join(base, "index" + e) for e in JS_TRIED]
            found |= {c for c in tried if c in files}
    return found


def code_only(text: str) -> str:
    """TEXT with its comments blanked and its strings kept."""
    return SOURCE_COMMENT.sub(lambda m: m[0] if m[0][0] in "\"'`" else " ", text)


def go_imports(text: str) -> list[str]:
    """The import paths of a Go file: only its import declarations, right after its package line."""
    text = code_only(text)
    head, found = GO_PACKAGE.match(text), []
    at = head.end() if head else len(text)
    while head and (decl := GO_IMPORT.match(text, at)):
        found += GO_PATH.findall(decl[1] or decl[2] or "")
        at = decl.end()
    return found


class GoModules:
    """The `go.mod` files of the head, and the non-test files of each Go package (a folder)."""

    def __init__(self, tree: dict[str, tuple[str, int]], texts: dict[str, str]) -> None:
        self.readable: dict[str, bool] = {}
        self.named: list[tuple[str, str]] = []
        self.packages: dict[str, set[str]] = {}
        for path in tree:
            folder, name = posixpath.split(path)
            if path.endswith(".go") and not path.endswith("_test.go"):
                self.packages.setdefault(folder, set()).add(path)
            if name != "go.mod":
                continue
            text = code_only(texts.get(path, ""))
            module = GO_MODULE.search(text)
            self.readable[folder] = module is not None
            if module:
                self.named.append((module[1], folder))
                for old, target in GO_REPLACE.findall(text):
                    place = inside(posixpath.join(folder, target))
                    self.named += [] if place is None else [(old, place)]

    def owner(self, folder: str) -> str | None:
        """The folder of the `go.mod` that FOLDER belongs to, or None when it cannot be read."""
        while folder not in self.readable and folder:
            folder = posixpath.dirname(folder)
        return folder if self.readable.get(folder) else None

    def edges(self, path: str, text: str) -> set[str]:
        folder = posixpath.dirname(path)
        if self.owner(folder) is None:
            return set()
        found = set(self.packages.get(folder, ())) if path.endswith("_test.go") else set()
        for spec in go_imports(text):
            for module, place in self.named:
                if spec == module or spec.startswith(f"{module}/"):
                    target = inside(posixpath.join(place, spec[len(module) + 1 :]))
                    if target is not None and self.owner(target) == place:
                        found |= self.packages.get(target, set())
        return found


Units = dict[str, set[str]]


def gradle_units(settings: str, texts: dict[str, str], files: set[str], units: Units, needs: Units):
    """Add the modules of one Gradle build. The root project owns only its `src/`: the other files
    at the root (the wrapper, the settings) concern every module, so they stay unmapped."""
    base, text = posixpath.dirname(settings), code_only(texts[settings])
    dirs: dict[str, str | None] = {":": base}
    for group in GRADLE_INCLUDE.findall(text):
        for name in QUOTED.findall(group):
            dirs[":" + name.strip(":")] = inside(posixpath.join(base, *name.strip(":").split(":")))
    for name, where in GRADLE_DIR.findall(text):
        if name in dirs:
            dirs[name] = inside(posixpath.join(base, where))
    owner = {folder: name for name, folder in dirs.items() if folder is not None}
    for name in owner.values():
        units[settings + name], needs[settings + name] = set(), set()
    for path in files:
        folder = posixpath.dirname(path)
        while folder not in owner and folder:
            folder = posixpath.dirname(folder)
        name = owner.get(folder)
        if name and (name != ":" or path.startswith(posixpath.join(base, "src/"))):
            units[settings + name].add(path)
    for folder, name in owner.items():
        for build in ("build.gradle", "build.gradle.kts"):
            for dep in GRADLE_PROJECT.findall(
                code_only(texts.get(posixpath.join(folder, build), ""))
            ):
                full = dep if dep.startswith(":") else f"{name.rstrip(':')}:{dep}"
                needs[settings + name].add(settings + full)


def unquoted(token: str) -> str:
    return re.sub(r"\\(.)", r"\1", token[1:-1], flags=re.S) if token[0] == '"' else token


def plist(tokens: list[str], at: int) -> tuple[object, int]:
    """The old-style property list value at token AT, and the position after it."""
    if tokens[at] == "{":
        table, at = {}, at + 1
        while tokens[at] != "}":
            if tokens[at + 1] != "=":
                raise ValueError
            key = unquoted(tokens[at])
            table[key], at = plist(tokens, at + 2)
            if tokens[at] != ";":
                raise ValueError
            at += 1
        return table, at + 1
    if tokens[at] == "(":
        items, at = [], at + 1
        while tokens[at] != ")":
            value, at = plist(tokens, at)
            items.append(value)
            if tokens[at] not in (",", ")"):
                raise ValueError
            at += tokens[at] == ","
        return items, at + 1
    if tokens[at] in tuple("{}()=;,"):
        raise ValueError
    return unquoted(tokens[at]), at + 1


def xcode_targets(path: str, text: str, files: set[str]) -> tuple[Units, Units]:
    """The files of each target of a `project.pbxproj`, and the targets each depends on."""
    tokens = [t for t in PLIST_TOKEN.findall(text) if not t.startswith(("/*", "//"))]
    data = plist(tokens, 0)[0]
    objects, project = data["objects"], data["objects"][data["rootObject"]]
    base = inside(
        posixpath.join(
            posixpath.dirname(posixpath.dirname(path)), project.get("projectDirPath", "")
        )
    )
    if base is None:
        return {}, {}
    found: dict[str, list[str]] = {}

    def walk(oid: str, folder: str) -> list[str]:
        if oid not in found:
            found[oid] = []
            node = objects.get(oid, {})
            start = {"<group>": folder, "SOURCE_ROOT": base}.get(node.get("sourceTree", "<group>"))
            place = None if start is None else inside(posixpath.join(start, node.get("path", "")))
            if place is not None:
                kids = node.get("children")
                found[oid] = [place] if kids is None else [p for k in kids for p in walk(k, place)]
        return found[oid]

    walk(project["mainGroup"], base)
    units: Units = {}
    needs: Units = {}
    for target in project["targets"]:
        node, members = objects.get(target, {}), set()
        for phase in node.get("buildPhases", []):
            for built_file in objects.get(phase, {}).get("files", []):
                members.update(found.get(objects.get(built_file, {}).get("fileRef"), []))
        for group in node.get("fileSystemSynchronizedGroups", []):  # Xcode 16: a whole folder
            for folder in found.get(group, []):
                members.update(f for f in files if folder and f.startswith(f"{folder}/"))
        units[f"{path}#{target}"] = members & files
        wanted = [objects.get(d, {}).get("target") for d in node.get("dependencies", [])]
        needs[f"{path}#{target}"] = {f"{path}#{t}" for t in wanted}
    return units, needs


def unit_edges(
    files: set[str], tests: set[str], texts: dict[str, str], deps: dict[str, set[str]]
) -> None:
    """Add to DEPS, for each test of a Gradle module or Xcode target, what that unit reaches."""
    units: Units = {}
    needs: Units = {}
    for path, text in texts.items():
        name = posixpath.basename(path)
        if name in ("settings.gradle", "settings.gradle.kts"):
            gradle_units(path, texts, files, units, needs)
        elif name == "project.pbxproj" and posixpath.dirname(path).endswith(".xcodeproj"):
            try:
                found, wanted = xcode_targets(path, text, files)
            except (ValueError, IndexError, KeyError, TypeError, AttributeError, RecursionError):
                continue  # a stack that cannot be read adds no entries
            units.update(found)
            needs.update(wanted)
    for unit, members in units.items():
        if members & tests:
            reach, stack = {unit}, [unit]
            while stack:
                for other in needs.get(stack.pop(), ()):
                    if other in units and other not in reach:
                        reach.add(other)
                        stack.append(other)
            code = set().union(*(units[u] for u in reach)) - tests
            for test in members & tests:
                deps.setdefault(test, set()).update(code)


def subject(test: str) -> tuple[str, str]:
    """(folder, stem) of the file that a test is named for, by the folder conventions."""
    folder, name = posixpath.split(test)
    folder = posixpath.dirname(folder) if posixpath.basename(folder) == "__tests__" else folder
    folder = f"/{folder}/".replace("/src/test/", "/src/main/", 1).strip("/")
    return folder, SUBJECT.fullmatch(posixpath.splitext(name)[0])[1]


def head_config(root: Path, tree: dict[str, tuple[str, int]], read):
    """What READ makes of a folder holding the head's own config files."""
    named = [n for n in ("agk.toml", "pyproject.toml") if n in tree]
    texts = blobs(root, [tree[n][0] for n in named])
    with tempfile.TemporaryDirectory() as folder:
        for config in named:
            (Path(folder) / config).write_text(texts[tree[config][0]], encoding="utf-8")
        return read(Path(folder))


def head_settings(root: Path, tree: dict[str, tuple[str, int]]) -> tuple[list[str], list[str]]:
    """`test_dirs` and `test_patterns` as the head's own config files give them."""
    try:
        settings = head_config(root, tree, load_config)
    except ValueError:
        raise CheckError("agk.toml cannot be read (setting: test_dirs)") from None
    return list(settings["test_dirs"]), list(settings["test_patterns"])


def area_folders(area: dict) -> list[str]:
    """The folders that make a file part of AREA: its `cwd` and `dirs`, and its levels'."""
    levels = area.get("levels", [])
    named = [area["cwd"], *area["dirs"], *[d for x in levels for d in (x["cwd"], *x["dirs"])]]
    return [d.strip("/") + "/" for d in named if d.strip("/") not in ("", ".")]


def schema_links(root: Path, tree: dict[str, tuple[str, int]]) -> dict[str, set[str]]:
    """Schema file -> the `contract` levels of the other areas with a file that names it."""
    try:
        areas = head_config(root, tree, proof_areas) or []
    except (ValueError, CheckError):
        return {}  # every other reader refuses a bad `[proof]`
    folders = {a["name"]: tuple(area_folders(a)) for a in areas}
    contract = {
        a["name"]: f"{a['name']}:contract"
        for a in areas
        if any(x["name"] == "contract" for x in area_levels(a))
    }
    readable = [p for p, v in tree.items() if v[1] <= READ_LIMIT and not NOT_A_GLOB.search(p)]
    importers = [p for p in readable if any(p.startswith(folders[a]) for a in contract)]
    maybe = [p for p in readable if p.endswith(OPENAPI_SUFFIXES)]
    found = blobs(root, sorted({tree[p][0] for p in [*importers, *maybe]}))
    schemas = {p for p in readable if p.endswith(SCHEMA_SUFFIXES)}
    schemas |= {p for p in maybe if OPENAPI_ROOT.search(found[tree[p][0]])}
    by_end: dict[str, set[str]] = {}
    for schema in schemas:
        parts = schema.split("/")
        for n in range(len(parts)):
            if n == 0 or n < len(parts) - 1:  # never a bare file name of a deeper path
                by_end.setdefault("/".join(parts[n:]), set()).add(schema)
    links: dict[str, set[str]] = {}
    for path in importers:
        named: set[str] = set()
        for word in set(PATH_WORD.findall(found[tree[path][0]])):
            word = word.rstrip(".")
            local = inside(posixpath.join(posixpath.dirname(path), word))
            named |= {local} & schemas if local else set()
            parts = word.split("/")
            for n in range(len(parts) if "/" in word else 1):
                if n == 0 or n < len(parts) - 1:
                    named |= by_end.get("/".join(parts[n:]), set())
        for schema in named - {path}:
            own = {a for a, f in folders.items() if f and schema.startswith(f)}
            links.setdefault(schema, set()).update(
                level
                for a, level in contract.items()
                if path.startswith(folders[a]) and a not in own
            )
    return {s: levels for s, levels in links.items() if levels}


def entries(root: Path, tree: dict[str, tuple[str, int]]) -> tuple[dict[str, set[str]], bool]:
    """Code path -> the tests that guard it, and whether a tsconfig could not be read."""
    dirs, patterns = head_settings(root, tree)
    files, configs = set(tree), TsConfigs(root, tree)
    usable = {p for p in files if p.strip() and not NOT_A_GLOB.search(p)}
    tests = sorted(p for p in usable if is_test_file(p, dirs, patterns))
    read = [
        p
        for p, v in tree.items()
        if v[1] <= READ_LIMIT
        and (p.endswith((".py", ".go", *JS_SOURCES)) or posixpath.basename(p) in STACK_FILES)
    ]
    found = blobs(root, [tree[p][0] for p in read])
    texts = {p: found[tree[p][0]] for p in read}
    deps: dict[str, set[str]] = {}
    go = GoModules(tree, texts)
    for path, text in texts.items():
        if path.endswith(".py"):
            deps[path] = python_edges(path, text, files)
        elif path.endswith(".go"):
            deps[path] = go.edges(path, text)
        elif path.endswith(JS_SOURCES):
            deps[path] = js_edges(path, text, files, configs)
    unit_edges(files, set(tests), texts, deps)
    for test in (t for t in tests if t.endswith(".py")):  # pytest loads each conftest above a test
        above = package_roots(posixpath.dirname(test))[::2]
        deps.setdefault(test, set()).update(
            c for c in (posixpath.join(d, "conftest.py") for d in above) if c in files
        )
    covered: dict[str, set[str]] = {}
    for test in tests:
        seen, stack = {test}, [test]
        while stack:
            for dep in deps.get(stack.pop(), ()):
                if dep not in seen:
                    seen.add(dep)
                    stack.append(dep)
        for code in seen - {test}:
            covered.setdefault(code, set()).add(test)
    by_subject: dict[tuple[str, str], set[str]] = {}
    for test in tests:
        by_subject.setdefault(subject(test), set()).add(test)
    for code in usable - set(tests) - set(covered):
        folder, name = posixpath.split(code)
        if (folder, posixpath.splitext(name)[0]) in by_subject:
            covered[code] = by_subject[(folder, posixpath.splitext(name)[0])]
    return {c: t for c, t in covered.items() if c in usable and not is_doc(c)}, configs.broken


def toml_string(path: str) -> str:
    return json.dumps(path, ensure_ascii=False)  # no control character reaches it: NOT_A_GLOB


def build(root: Path) -> int:
    tree = listing(root)
    if OUT in tree:
        raise CheckError(f"the generated map is committed; principle 5 forbids it (setting: {OUT})")
    covered, broken = entries(root, tree)
    links = schema_links(root, tree)
    lines = [f"# tree {git(root, 'rev-parse', 'HEAD^{tree}').strip()}"]
    for code in sorted(covered):
        names = ", ".join(toml_string(t) for t in sorted(covered[code]))
        lines += ["", "[[testing.map]]", f"code = {toml_string(code)}", f"tests = [{names}]"]
    for schema in sorted(links):
        run_names = ", ".join(toml_string(r) for r in sorted(links[schema]))
        lines += [
            "",
            "[[testing.links]]",
            f"code = [{toml_string(schema)}]",
            f"run = [{run_names}]",
        ]
    temporary = root / f"{OUT}.{os.getpid()}"
    try:
        temporary.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
        os.replace(temporary, root / OUT)
    except OSError:
        raise CheckError(f"the map cannot be written (setting: {OUT})") from None
    if broken:
        print(UNREADABLE)
    print(f"ok {NAME}: {len(covered)} entries")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    given = len(args) == 3 and args[:2] == ["build", "--root"]
    if args != ["build"] and not (given and Path(args[2]).is_dir()):
        print("usage: test_map.py build [--root DIR]", file=sys.stderr)
        return 2
    return run(NAME, lambda: build(Path(args[2]) if given else repo_root()))


if __name__ == "__main__":
    sys.exit(main())
