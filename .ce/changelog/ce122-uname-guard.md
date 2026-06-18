---
slug: ce122-uname-guard
date: 2026-06-18
kind: fixed
scope: installer platform override guard
base: 51c9dac
---

Hardens the public installer's `CE_TEST_UNAME_S` / `CE_TEST_UNAME_M`
platform-test overrides so they are refused during real installs and only
honored when `CE_INSTALLER_TEST_MODE=1` is set by the test harness.

Installer integration coverage now asserts that real installs fail closed before
network fetches when either test override is present without explicit test mode,
while existing platform-selection tests opt into test mode.
