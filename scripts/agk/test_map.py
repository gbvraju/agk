"""The generated test map (SPEC-0055 rule 5, build (c); REQ-062 AC3). Installed.

    python3 scripts/agk/test_map.py build [--root DIR]

Reads the tree at the head (never the working tree, and its own `agk.toml` from there) and writes
the git-ignored file `.agk-test-map.toml`: the first line is `# tree <tree id>`, then one
`[[testing.map]]` entry for each file that a test depends on, the shape of `[testing] map`, with no
date or commit id, so one tree gives the same bytes. A test file is what `impact.py` calls one
(`test_dirs`, `test_patterns`).

A test depends on what its imports reach, followed through the files they import: Python by `ast`,
JavaScript or TypeScript by import and require lines read as text, with the `paths` and `baseUrl`
of the nearest `tsconfig.json` and its `extends`. Where several files could be meant, each counts,
because an entry only adds tests. A file no import reaches falls back on the folder conventions: a
test beside it, in `__tests__/`, or in a module's `src/test/` for its `src/main/`. A file that
cannot be read adds no entries, so what only it reaches stays unmapped. Files and git only.
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

from common import CheckError, git, load_config, repo_root, run
from impact import is_doc, is_test_file

NAME = "test_map"
OUT = ".agk-test-map.toml"
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


def subject(test: str) -> tuple[str, str]:
    """(folder, stem) of the file that a test is named for, by the folder conventions."""
    folder, name = posixpath.split(test)
    folder = posixpath.dirname(folder) if posixpath.basename(folder) == "__tests__" else folder
    folder = f"/{folder}/".replace("/src/test/", "/src/main/", 1).strip("/")
    return folder, SUBJECT.fullmatch(posixpath.splitext(name)[0])[1]


def head_settings(root: Path, tree: dict[str, tuple[str, int]]) -> tuple[list[str], list[str]]:
    """`test_dirs` and `test_patterns` as the head's own config files give them."""
    named = [n for n in ("agk.toml", "pyproject.toml") if n in tree]
    texts = blobs(root, [tree[n][0] for n in named])
    with tempfile.TemporaryDirectory() as folder:
        for config in named:
            (Path(folder) / config).write_text(texts[tree[config][0]], encoding="utf-8")
        try:
            settings = load_config(Path(folder))
        except ValueError:
            raise CheckError("agk.toml cannot be read (setting: test_dirs)") from None
    return list(settings["test_dirs"]), list(settings["test_patterns"])


def entries(root: Path, tree: dict[str, tuple[str, int]]) -> tuple[dict[str, set[str]], bool]:
    """Code path -> the tests that guard it, and whether a tsconfig could not be read."""
    dirs, patterns = head_settings(root, tree)
    files, configs = set(tree), TsConfigs(root, tree)
    usable = {p for p in files if p.strip() and not NOT_A_GLOB.search(p)}
    tests = sorted(p for p in usable if is_test_file(p, dirs, patterns))
    read = [p for p, v in tree.items() if v[1] <= READ_LIMIT and p.endswith((".py", *JS_SOURCES))]
    texts = blobs(root, [tree[p][0] for p in read])
    deps: dict[str, set[str]] = {}
    for path in read:
        text = texts[tree[path][0]]
        python = path.endswith(".py")
        deps[path] = (
            python_edges(path, text, files) if python else js_edges(path, text, files, configs)
        )
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
    lines = [f"# tree {git(root, 'rev-parse', 'HEAD^{tree}').strip()}"]
    for code in sorted(covered):
        names = ", ".join(toml_string(t) for t in sorted(covered[code]))
        lines += ["", "[[testing.map]]", f"code = {toml_string(code)}", f"tests = [{names}]"]
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
