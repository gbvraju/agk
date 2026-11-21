"""Safe logs (brief #1594, ADR-0674): one line per request or run, with its id and no personal value.

An e-mail address or a phone number in a message is replaced before the line is written, and a query
string is never logged.
"""

from __future__ import annotations

import logging
import re
import sys
import uuid
from typing import TextIO

LOG = logging.getLogger("app")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
PHONE = re.compile(r"\+?\d[\d ()-]{7,}\d")


def scrub(value: object) -> str:
    return PHONE.sub("<phone>", EMAIL.sub("<email>", str(value))).replace("\n", " ")


def setup(stream: TextIO | None = None) -> None:
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    LOG.handlers[:] = [handler]
    LOG.setLevel(logging.INFO)
    LOG.propagate = False


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def line(**fields: object) -> None:
    LOG.info(" ".join(f"{key}={scrub(value)}" for key, value in fields.items()))


def error(request_id: str, exc: BaseException) -> None:
    LOG.error(f"request_id={request_id} error={type(exc).__name__}: {scrub(exc)}")
