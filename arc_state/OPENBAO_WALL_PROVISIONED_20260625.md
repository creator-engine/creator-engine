# OpenBao Approval-Wall — PROVISIONED state (2026-06-25, pre-armed-flip)
Stage 1-3 DONE. Stage 4 (flip armed:true + live daemon restart) remaining.

## Daemon token (DGX)
- File: ~/.ce-keys/ce-approval-wall-token (0600, 26 bytes)
- ORPHAN periodic token (period=72h/259200s), policies=[ce-approval-wall-read, default]
- MUST be orphan: child tokens get revoked when the transient generate-root token is revoked (the bug that ate the first two mints).
- Renew before 72h: bao token renew (or re-mint via the window).

## Policy ce-approval-wall-read (on VPS OpenBao)
- path "ce-kv/data/forge/approval-capability/wall" { read }
- path "sys/audit" { read, sudo }   <-- REQUIRED: backend.validate_config() does GET /v1/sys/audit with the DAEMON token (audit preflight). Without it: AuditUnavailable.

## Connection (DGX → VPS OpenBao)
- BAO_ADDR=https://100.72.252.20:8200 ; BAO_CACERT=/usr/local/share/ca-certificates/ce-openbao-ca.crt (installed on DGX this session)
- Audit device 'file' already enabled at /var/log/openbao/audit.log.

## Policy SHAs (operator-chosen consistency pins; MUST match between mint + verify)
- REF_POLICY_SHA=c5de2d359286c1c3160a0ef553ebb2e7c19177bcec0c09c0be75a12d5d3ffa7a  (--approval-wall-secret-ref-policy-sha; sha256 of the read-policy HCL)
- APPROVAL_POLICY_SHA=79b9dc8b429e4af109ecc68af19b26e9b3f647d9fad8dd37309d6f5ead81b3b0  (--approval-wall-policy-sha; sha256 of the approval descriptor)

## Stage 3 round-trip: PROVEN (--once --dry-run read the secret + ran a full pass; #444/#445/#477 -> review_not_approved skip).

## Admin window recipe (no stored root; root revoked each time)
- ce-dev-1 has sudo on VPS (ssh dev1). Bundle is gpg-encrypted to user 'ce' (ssh ce-dev-1 to decrypt). Unseal: 5 shares thr 3 in bundle.
- Decrypt+stage unseal keys as 'ce' -> /dev/shm/ce-uk ; run admin script as root (ssh dev1 sudo). CVE-2026-5807: toggle disable_unauthed_generate_root_endpoints=false in listener -> restart -> generate-root via 3 shares -> revert -> restart. Scripts in scratchpad: stage_unseal.sh, stage2*.sh.

## REMAINING Stage 4 (live arm)
1. (Optional but runbook-advised) mint-on-approval + verify proof on a controlled PR (#477).
2. Flip armed:true at .ce/state/approval-capability-wall/state.json (currently absent=dormant).
3. Restart the LIVE integrator daemon (PID was 1014898) WITH the --approval-wall-* args + BAO env + --authorized-reviewer ce-dev-2.
