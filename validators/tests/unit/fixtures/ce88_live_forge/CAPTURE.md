# ce-ops#88 — Mode-B VERBATIM forge captures (#44 REAL-shape acceptance)

Per ce-ops#44, the live-forge `ApplyDriver` legs are exercised in **Mode B**: a fake
`GhRunner`/transport replays forge responses **captured VERBATIM from the live GitHub REST
API — never invented**. The live Mode-A run (real installation token, real forge reads) is the
clean-room VPS rehearsal DoD, run later by the orchestrator — not these unit tests.

**Capture commands (run 2026-06-15, against the live already-CE repo `creator-engine/creator-engine`,
authenticated as `chmod735`):**

```
gh api repos/creator-engine/creator-engine                                        > repo.json
gh api repos/creator-engine/creator-engine/branches/main/protection               > protection.json
gh api repos/creator-engine/creator-engine/contents/.github/workflows/validate.yml > contents_validate_yml.json
gh api -i user                                                                    > user_response_headers.txt
```

The JSON files are the captured responses (re-serialized with sorted keys / 2-space indent for
review; values are byte-faithful to the API). They are reproducible by re-running the commands.

## Files

- **`repo.json`** — verbatim `GET /repos/{owner}/{repo}`. The driver reads `full_name`,
  `default_branch` (`main`), `private` (`false` → `public`).
- **`protection.json`** — verbatim `GET /repos/.../branches/main/protection`. The driver reads
  `required_status_checks.contexts` (`["Validate governance artifacts"]` — the CE floor IS present,
  so this repo is genuinely already-CE).
- **`contents_validate_yml.json`** — verbatim `GET .../contents/.github/workflows/validate.yml`.
  This is the CE repo's OWN dev workflow (`validate.yml`), whose content does NOT match the
  onboard-installed stub digest — used to exercise the OQ-C `workflow_digest_mismatch` path.
- **`contents_ce_validate_yml_already_ce.json`** — the SAME real GitHub contents envelope, with
  `path`/`name`/`content` set to the canonical `onboard_apply.CE_WORKFLOW_CONTENT` — i.e. the exact
  `ce-validate.yml` a CE-onboarded repo carries at the pinned `CE_WORKFLOW_SHA256`. The envelope
  shape is verbatim-real; the content is the canonical CE workflow from source (not invented). This
  exercises `verify_workflow`'s exact-digest pin against a real-shape response. (The CE repo's live
  workflow is `validate.yml`, not the onboard stub `ce-validate.yml`, so no live capture of the
  matching file exists outside an actually-onboarded repo — that is the Mode-A VPS rehearsal.)
- **`user_response_headers.txt`** — `gh api -i user`: the `X-Oauth-Scopes` header is verbatim
  (`gist, project, read:org, repo, workflow`); the body is reduced to the non-PII identity
  (`login`/`id`/`type`) — private fields (email/name) elided. The driver reads `X-Oauth-Scopes`
  (→ CE bootstrap permissions) and `login`. This is a **classic** PAT (`ghp_`).
- **`user_response_finegrained.txt`** — `gh api -i user` authenticated as a **fine-grained** PAT
  (`github_pat_` prefix), captured **2026-06-16 as a fine-grained
  bootstrap PAT** — the exact token that surfaced ce-ops#94. Capture command:
  `sudo -u ce-dev-3 gh api -i user`. The defining VERBATIM property: a fine-grained PAT emits **NO
  `X-Oauth-Scopes` header** (only `X-Accepted-Github-Permissions: allows_permissionless_access=true`,
  kept verbatim as the genuine fine-grained marker); body reduced to the non-PII identity
  (`login: ce-dev-3` / `id` / `type`), volatile/sensitive headers (Date/Etag/request-id/ratelimit/
  token-expiration) elided. Exercises ce-ops#94: token-type detection (`github_pat_` → fine-grained)
  and the no-`X-Oauth-Scopes` path that the classic-only parser wrongly read as "missing everything".
