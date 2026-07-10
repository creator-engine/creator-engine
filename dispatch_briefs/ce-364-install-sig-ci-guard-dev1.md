# BRIEF — dev-1 — ce-ops#364: CI guard blocking a placeholder/invalid install-spec signature

Non-contained, SELF-PUSH as ce-dev-1. Fresh branch `ce-364-install-sig-ci-guard` off CURRENT origin/main (`git fetch origin main` first). Drive to a GREEN PR; self-push, do NOT merge.

## Why (this exact incident, tonight)
PR #654 changed `docs/llms-install.md` (the signed public install spec). That invalidated its detached ce-root-v1 SSHSIG and the spec shipped to main + production with the placeholder `value: <RESIGN-REQUIRED-ce-root-v1>` → the public install one-liner now FAIL-CLOSES for every user (`INSTALL_REFUSED signature_refused: signature value is not valid base64`). NO CI gate caught it. Build the gate so main can NEVER again contain an unsigned/placeholder install spec.

## Deliverable — a fail-closed CI gate (+ the check it runs)
1. **A validator check** (extend the CE validator / add a check function — match the existing check-registration pattern; read how other `ce validate-pr` checks are wired) that FAILS if `docs/llms-install.md` (and any served mirror, e.g. `docs/downloads/<ver>/llms-install.md` if present) has a signature `value:` that is EITHER (a) the `<RESIGN-REQUIRED-...>` / any `<...>` placeholder, OR (b) not valid base64, OR (c) does not VERIFY as a real SSHSIG against the trust root over the spec's canonical bytes. Prefer the strongest check you can implement cleanly; at minimum (a)+(b) (placeholder + base64), and (c) if the verification primitives are readily available in-repo (reuse the installer's own verify logic if importable — do NOT reinvent crypto).
2. **Wire it into CI** as a required gate (the "Validate governance artifacts" workflow or the appropriate validate-pr surface) so a PR touching the spec can't merge with a broken signature. Fail-closed (gate failure = block).
3. **Tests:** prove the check FAILS on a placeholder value, FAILS on invalid-base64, and PASSES on a well-formed signed spec (use a fixture; for the verify path use a known-good or mocked-verify fixture — do NOT commit real secrets). Cover the mirror paths if you gate them.

## Do NOT
- Do NOT re-sign or modify `docs/llms-install.md` itself (the re-sign is a separate controller action). You build the GUARD only.
- Do NOT touch support files, os_native, broker, or the adapters (other lanes).
- Do NOT weaken any existing gate.

## Gates
- FULL `ce validate-pr` GREEN in ONE pass (`TMPDIR=/var/tmp`). Note: your OWN new gate must PASS on current main only AFTER the spec is re-signed — since main currently has the placeholder, your gate would (correctly) FAIL on main right now. Handle this: make the gate's CI wiring active, but ensure the PR itself is green by NOT having the gate fail your own branch — e.g. gate runs on the PR diff/spec and the controller will re-sign before/with enabling it. CLARIFY in your PR description how you avoided a chicken-and-egg (e.g. gate is added but the spec re-sign lands first/together). If you cannot make validate-pr green because the placeholder is still on main, STOP and report that ordering dependency rather than forcing it.
- Carriers (manifest slug == branch + work-class line), changelog. Report PR # + head SHA.
