# ce342 CORRECTION 2 — authorize the brain-assertion hash update for validate.yml

Your #342 change (adding `edited` to validate.yml `pull_request` types) is correct. It trips
the brain drift-CI (ce-ops#177): `.ce/brain/assertions.yaml` pins a sha256 of
`.github/workflows/validate.yml`, and any AUTHORIZED change to that workflow must update the
pinned hash. This correction authorizes that update — it is the expected coupling, not new
feature scope.

## Updated allowed paths (closed list)
```
.github/workflows/validate.yml
.ce/brain/assertions.yaml                     # NEW — update the pinned validate.yml hash
.ce/pr-manifests/ce-342-ci-retrigger.md       # dashed slug
.ce/changelog/ce-342-ci-retrigger.md          # dashed slug
```

## Do
1. In `.ce/brain/assertions.yaml`, update the assertion entry for `.github/workflows/validate.yml`
   so its expected sha256 matches the NEW file content. Use the brain/drift tooling's canonical
   regeneration path if one exists (look for a `brain assertions` / drift-update command or the
   helper that ce177 added); otherwise set the hash to the actual `sha256sum .github/workflows/validate.yml`
   value. Do NOT alter any OTHER assertion entry — only the validate.yml one.
2. Ensure the carrier filenames use the DASHED branch slug `ce-342-ci-retrigger` (rename if the
   prior correction left them as `ce342-`).
3. Regenerate the path-manifest carrier via `carrier_gen.write_carriers(base=<merge-base>)` so the
   hash matches the full path set (now 4 paths incl. `.ce/brain/assertions.yaml`).
4. Re-run FULL `ce validate-pr` GREEN in one pass (the brain-drift gate must now pass).
5. `git commit`, `echo` the final SHA, report **READY-FOR-HARVEST** with the SHA. Do NOT push
   (contained seat — controller harvests).

## Stop-line
If updating the validate.yml assertion requires touching any file outside the closed list above,
STOP and report it. Do not update unrelated assertions.
