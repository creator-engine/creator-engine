---
slug: ce271-ringuard-toolchain-selfupdate
date: 2026-06-26
kind: fix
scope: containment
issue: ce-ops#271
---

**ring-1 toolchain self-update block + readonly VPS codex binary mount.**

Add Ring-1 hook patterns that deny toolchain self-update commands (`npm/pnpm/yarn install -g`, `pip install` from index, `apt/apt-get install`, `dpkg -i`, `curl|sh`, `wget|sh`) in governed seats. The `pip install --no-index` invocation used by CE's own VenvSwapper updater is explicitly exempted. Closes the live hole where a contained seat was prompted to `npm install -g`.
