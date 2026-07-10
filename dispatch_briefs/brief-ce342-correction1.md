# ce342 CORRECTION 1 — carrier filenames must use the dashed slug

Your #342 implementation is correct and complete (validate.yml `edited` trigger, commit
63c8fd4). The ONLY issue is the carrier filenames: the brief listed them without the dash,
but the carrier slug is derived from the branch name `ce-342-ci-retrigger`, so preflight
expects the **dashed** form. This corrects the allowed-path list accordingly — it is NOT
new scope, just the correct carrier slug.

## Allowed paths (corrected — closed list)
```
.github/workflows/validate.yml
.ce/pr-manifests/ce-342-ci-retrigger.md     # dashed slug (rename from ce342-…)
.ce/changelog/ce-342-ci-retrigger.md        # dashed slug (rename from ce342-…)
```

## Do
1. `git mv .ce/pr-manifests/ce342-ci-retrigger.md .ce/pr-manifests/ce-342-ci-retrigger.md` (and same for changelog) — OR regenerate carriers fresh at the dashed paths and delete the old ones.
2. Regenerate the path-manifest carrier so the hash matches base..HEAD:
   `python -c "from validators... import carrier_gen; carrier_gen.write_carriers(base='origin/main')"` (use the project's carrier_gen API; rm build/egg-info first if stale).
3. Re-run FULL `ce validate-pr` → GREEN in one pass.
4. `git commit` the rename + regen, `echo` the final SHA.
5. Report **READY-FOR-HARVEST** with the SHA. Do NOT push/merge/approve (contained seat — controller harvests).
