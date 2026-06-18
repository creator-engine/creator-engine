---
slug: ce88-apply-driver
date: 2026-06-18
kind: fixed
scope: onboard apply live driver seam
base: 9152727
---

Wire the production live-forge apply driver through `_onboard_apply_driver()`
for existing-repo onboard apply.

The apply path now asks the onboard apply seam for the context-aware driver,
allowing authorized brownfield adoption runs to receive the live adoption
driver while preserving fail-closed base-driver behavior when live forge,
adoption write, or App credentials are absent.
