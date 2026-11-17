# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
PY ?= python3

include agk.mk
-include project.mk

.PHONY: governance test lint traceability

governance: agk-governance

lint: agk-lint

traceability: agk-traceability

# Kit tests, then the project's own tests (agk.toml project_tests).
test: agk-test agk-project-test
