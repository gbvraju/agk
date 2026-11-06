"""The fake plugin's hooks under the module name of a real pytest-xdist entry point.

With autoload off, pytest resolves `-p xdist` through an installed distribution's entry point
(`xdist.plugin`) when one exists; the fixture's own `xdist` package is found first on its path, so
this module gives the same fake hooks there (brief #631: the rule 6 test with the real plugin
installed).
"""

from xdist import pytest_addoption, pytest_cmdline_main

__all__ = ["pytest_addoption", "pytest_cmdline_main"]
