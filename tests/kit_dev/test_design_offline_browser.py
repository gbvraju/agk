"""Kit-only tests of the browser flags of the design commands (brief #1828, ADR-0762).

Every browser call the kit builds runs offline: `--host-resolver-rules=MAP * ~NOTFOUND` and
`--no-proxy-server` for a `file:` page, so a machine proxy is never used; the one call that opens
an imported page goes through the comparison's own files server, with only `127.0.0.1` excluded
from the resolver rule. The first test runs a real headless browser where one is on PATH (skipped
otherwise) on an invented page, against a real `FilesServer`, a stand-in service and a stand-in
machine proxy, all on the loopback: no request leaves the machine. The second uses a fake browser.
"""

from __future__ import annotations

import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from conftest import KIT_ROOT
from design_fixture import frozen_version

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import design  # noqa: E402
import design_compare  # noqa: E402
import design_render  # noqa: E402

# An invented page: a coloured background (so an error page cannot pass for it), one heading and
# external references that a browser would fetch if anything let it.
PAGE = """<!doctype html>
<html><head><title>Menu</title>
<link rel="stylesheet" href="https://fonts.example.com/css2?family=Example">
<link rel="stylesheet" href="http://fonts.example.com/x.css">
<link rel="stylesheet" href="http://127.0.0.1:{port}/a.css">
<link rel="stylesheet" href="http://localhost:{port}/b.css">
</head>
<body style="margin:0;background:#33aa66"><h1>Example bakery</h1><p>Bread and rolls</p></body>
</html>
"""


def sandboxless(browser: str, directory) -> tuple[str, object]:
    """The browser behind a wrapper that adds `--no-sandbox` and keeps its stderr: a raw Chromium
    on a CI runner whose kernel refuses unprivileged user namespaces cannot start its sandbox
    (Ubuntu 26.04 runner image), and the sandbox does not change which requests are made."""
    log = directory / "browser-stderr.txt"
    wrapper = directory / "browser"
    wrapper.write_text(f'#!/bin/sh\nexec "{browser}" --no-sandbox "$@" 2>>"{log}"\n', "utf-8")
    wrapper.chmod(0o755)
    return str(wrapper), log


def shot(browser: str, log, url: str, size, target, port=None) -> None:
    try:
        design_compare.shoot_at(browser, url, size, target, port)
    except design_compare.CheckError as exc:
        text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
        raise AssertionError(f"{exc}; browser stderr: {text[-2000:]}") from None


class Counter:
    """A loopback server that counts every request (a stand-in service or machine proxy)."""

    def __init__(self) -> None:
        self.seen: list[str] = []
        seen = self.seen

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                return

            def _any(self) -> None:
                seen.append(f"{self.command} {self.path}")
                try:
                    self.send_error(404)
                except OSError:
                    pass

            do_GET = do_HEAD = do_POST = do_CONNECT = _any

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = int(self.server.server_address[1])
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.mark.skipif(design.find_browser() is None, reason="no headless browser on PATH")
def test_ac6_a_real_browser_opens_the_imported_page_through_the_server_and_nothing_else(
    tmp_path, monkeypatch
):
    """REQ-044 AC6: brief #1828 answers 1, 3 and 6 (the proxied shot is the page, served by the
    files server; neither a loopback service nor a machine proxy sees a request)."""
    service, machine = Counter(), Counter()
    try:
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY"):
            monkeypatch.setenv(name, f"http://127.0.0.1:{machine.port}")
        for name in ("NO_PROXY", "no_proxy"):
            monkeypatch.delenv(name, raising=False)
        files = tmp_path / "files"
        files.mkdir()
        (files / "menu.html").write_text(PAGE.format(port=service.port), encoding="utf-8")
        browser, log = sandboxless(str(design.find_browser()), tmp_path)
        size = (640, 400)
        built, imported = tmp_path / "built.png", tmp_path / "imported.png"
        shot(browser, log, (files / "menu.html").as_uri(), size, built)
        server = design_compare.FilesServer(files)
        with server as port:
            url = f"http://{design_compare.HOST}/menu.html"
            shot(browser, log, url, size, imported, port)
        assert "/menu.html" in server.served
        share = design_render.pixel_share(built, imported)
        assert share <= design_compare.DEFAULT_TOLERANCE, share
        assert service.seen == [] and machine.seen == [], (service.seen, machine.seen)
    finally:
        service.close()
        machine.close()


def test_ac6_every_browser_command_of_the_kit_is_offline_and_only_the_imported_one_proxied(
    tmp_path, monkeypatch
):
    """REQ-044 AC6: brief #1828 answers 1, 2 and 6 (`measure`, `shoot`, `shoot_at` with and without
    a port and `screenshots --folder` all carry the resolver rule; only the proxied call has the
    exclusion and `--proxy-server`, every other call `--no-proxy-server`)."""
    calls: list[list[str]] = []

    class Done:
        returncode, stdout = 0, '<pre id="agk-reflow">ok</pre>'

    def fake(command, **kwargs):
        calls.append(list(command))
        for arg in command:
            if arg.startswith("--screenshot="):
                open(arg.split("=", 1)[1], "wb").close()
        return Done()

    monkeypatch.setattr(design_render.subprocess, "run", fake)
    page = frozen_version(tmp_path) / "home--default.html"
    design_render.measure("chromium", page, 360, "light")
    design_render.shoot("chromium", page, 360, "dark", tmp_path / "a.png")
    design_compare.shoot_at("chromium", page.as_uri(), (2, 1), tmp_path / "b.png")
    proxied = len(calls)
    design_compare.shoot_at("chromium", "http://x.invalid/", (2, 1), tmp_path / "c.png", 4321)
    mockup = tmp_path / "docs" / "design" / "mockups" / "2026-11-01-home"
    mockup.mkdir(parents=True)
    (mockup / "index.html").write_text("<!doctype html><title>x</title>\n", encoding="utf-8")
    monkeypatch.setattr(design, "find_browser", lambda: "chromium")
    assert design.cmd_screenshots(tmp_path, {"folder": mockup.name}) == 0
    assert len(calls) == proxied + 1 + 4
    for i, call in enumerate(calls):
        text = " ".join(call)
        assert "--headless" in call and "MAP * ~NOTFOUND" in text, call
        if i == proxied:
            assert "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1" in call
            assert "--proxy-server=http://127.0.0.1:4321" in call
            assert "--proxy-bypass-list=<-loopback>" in call
            assert "--no-proxy-server" not in call
        else:
            assert "EXCLUDE" not in text and "--proxy-server=" not in text, call
            assert "--no-proxy-server" in call, call


def test_ac6_the_offline_flags_have_one_definition():
    """REQ-044 AC6: brief #1828 answer 2 (`design_render.OFFLINE` is `design.OFFLINE`)."""
    assert design_render.OFFLINE is design.OFFLINE
    assert "--no-proxy-server" in design.OFFLINE
