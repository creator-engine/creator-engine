# DF-1 B3/D2 Controller State-Root Durability Gate

- Add a fail-closed, descriptor-pinned `.ce/state` probe that enforces the
  ratified owner, private-mode, ACL, ancestor, inode-type, and crash-residue
  policy without repairing state.
- Require live controller launch and brain bootstrap to prove same-filesystem
  nonce create/fsync/read/constant-time-verify/unlink/final-fsync durability
  before their first state mutation.
- Keep takeover and continuity diagnostics strictly read-only with writable
  durability `not-proven`; unsafe state makes continuity RED and no probe result
  grants lease, fencing, promotion, signing, credential, or forge authority.
- Document the offline migration, audited residue removal, fresh-root rollback,
  and pre-provisioning procedure for existing state trees.
