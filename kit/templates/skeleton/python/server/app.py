"""The server's routes (brief #1594, ADR-0674).

`/health` answers ok while the app and its database are up. Every request writes one log line with
its id. An error shows the user a plain message with the request id; its detail goes only to the
log.
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Callable, Iterable

from . import logs

Handler = Callable[[dict, dict], tuple[str, dict]]
PLAIN = "Something went wrong. Please try again, and quote request id {id} if you contact us."


def health(settings: dict, request: dict) -> tuple[str, dict]:
    try:
        with sqlite3.connect(settings["DATABASE_PATH"]) as db:
            db.execute("SELECT 1")
    except sqlite3.Error:
        return "503 Service Unavailable", {"status": "down", "database": "down"}
    return "200 OK", {"status": "ok", "database": "ok"}


def make_app(settings: dict, routes: dict[str, Handler] | None = None) -> Callable:
    table: dict[str, Handler] = {"/health": health, **(routes or {})}

    def app(request: dict, start_response: Callable) -> Iterable[bytes]:
        request_id, started = logs.new_id(), time.monotonic()
        path = request.get("PATH_INFO", "/")
        try:
            handler = table.get(path)
            status, body = handler(settings, request) if handler else ("404 Not Found", {})
        except Exception as exc:  # the user sees a plain message; the detail goes to the log
            logs.error(request_id, exc)
            status, body = "500 Internal Server Error", {"error": PLAIN.format(id=request_id)}
        took = round((time.monotonic() - started) * 1000)
        method = request.get("REQUEST_METHOD", "GET")
        logs.line(request_id=request_id, method=method, path=path, status=status[:3], ms=took)
        data = json.dumps(body).encode("utf-8")
        start_response(status, [("Content-Type", "application/json"), ("X-Request-Id", request_id)])
        return [data]

    return app
