# SEED BRIEF — L1 install-spec doc fix (PREPARE for re-sign) — SEAT: dev-1

**Branch:** `ce-L1-install-doc-fix` off CURRENT origin/main. **Role:** implementer (PREPARE only — do NOT sign; the controller holds ce-root-v1 and signs under Operator R5). **Work class:** declare by floor (likely XS/S).

## Context (from your own clean-room e2e — verdict BROKEN)
The live `docs/llms-install.md` has two new-user-blocking issues you found:
1. **§0 missing prerequisite:** the signature-verification ceremony calls `ssh-keygen`, but a clean Ubuntu 24.04 box lacks it. The docs never tell the user to install `openssh-client`. A strict verbatim new user stops there.
2. **§0.5 stale prose:** references `https://creator-engine.dev/downloads/0.2.0/SHA256SUMS` and `creator-engine-validator==0.2.0`, while the live path is 0.3.1.

## The catch: docs/llms-install.md is a SIGNED install spec
Editing its content invalidates the embedded ce-root-v1 signature → the install-spec guard fails until re-signed. You CANNOT sign (no key). So PREPARE the edit + emit the exact canonical bytes the controller must sign, and STOP.

## Do this
1. **Edit `docs/llms-install.md`:**
   - §0 (before the signature-verify ceremony): add a clear **Prerequisites** note that `openssh-client` (providing `ssh-keygen`) must be installed first — give the apt one-liner (`sudo apt-get install -y openssh-client`) and note it's needed to verify the signed spec. Phrase it product-lens for an external new user.
   - §0.5: update the stale `0.2.0` references (downloads path + `creator-engine-validator==0.2.0`) to the CURRENT version the live path actually installs (you measured `0.3.1+91d20efc` / spec installs 0.3.1). Match whatever the rest of the live spec/manifest uses for 0.3.1.
   - Do NOT change any signed VALUE/payload beyond these doc-content fixes; keep the change minimal + within the signature-covered region as required.
2. **Find the canonical-bytes / re-sign procedure** in the repo (the install-spec signing tooling — search for the spec-signing / apply-spec / canonical-bytes command, e.g. a `ce` subcommand or a script; see how the signature block in docs/llms-install.md is produced/verified). 
3. **Emit for the controller:** the exact canonical bytes (or the exact command the controller runs to regenerate them) that must be signed with `~/.ce-keys/ce-root-v1`, AND the exact command to embed the signature + the verify command (`ce verify-install` / the install-spec guard) to confirm green after signing.
4. **Verify the content fix is correct** by dry-running the documented path in a clean env with `openssh-client` installed (you already proved it succeeds end-to-end once ssh-keygen is present).
5. Commit the CONTENT edits on the branch (the signature will be stale/invalid — that's expected; the controller re-signs). Push the branch (CI will show the install-spec guard RED until the controller adds the signature — note this in your report so it's not mistaken for a real failure).

## Recommend (do NOT build): a follow-up so users don't need to read prereqs
Note in your report whether the install BOOTSTRAP should preflight-check for `ssh-keygen` and emit an actionable error ("install openssh-client") instead of a raw `command not found`. That's a separate ticket/lane — just recommend it, don't build it here.

## Stop line
PREPARE only: content edits + emitted signing bytes/commands + verification evidence. Do NOT sign, do NOT merge. Commit + echo SHA + report: the 2 edits, the exact signing command + canonical bytes for the controller, the verify command, and the bootstrap-preflight recommendation. The controller signs under Operator R5, then ships.
