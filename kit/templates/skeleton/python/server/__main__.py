"""Run the server: `python3 -m <package>`; `--check` asks the health address once and exits."""

from __future__ import annotations

import sys
from wsgiref.simple_server import WSGIRequestHandler, make_server

from . import logs
from .app import make_app
from .settings import load


class QuietHandler(WSGIRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - the base's name
        """The app writes its own safe line; the default line would hold the query string."""


def main(argv: list[str]) -> int:
    settings = load()
    logs.setup()
    app = make_app(settings)
    if "--check" in argv:
        seen: list[str] = []
        request = {"PATH_INFO": "/health", "REQUEST_METHOD": "GET"}
        print(b"".join(app(request, lambda status, headers: seen.append(status))).decode())
        return 0 if seen == ["200 OK"] else 1
    port = int(settings.get("PORT", "8000"))
    with make_server("127.0.0.1", port, app, handler_class=QuietHandler) as server:
        logs.line(event="start", address=f"http://127.0.0.1:{port}/health")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
