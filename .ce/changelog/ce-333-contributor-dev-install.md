---
slug: ce-333-contributor-dev-install
date: 2026-06-27
kind: docs
scope: contributor editable install
issue: ce-ops#333
---

Documented the public contributor path for installing the validator package from
source in editable mode with Python 3.14, uv, and `validators/.venv`. The guide
now covers console-script verification and calls out the offline editable-install
build-backend gap, including the dev wheelhouse workaround when `setuptools` is
not otherwise available.
