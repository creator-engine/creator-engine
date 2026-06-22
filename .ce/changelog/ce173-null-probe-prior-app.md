---
slug: ce173-null-probe-prior-app
ticket: ce-ops#173
type: fix
scope: reinstall convergence
---

Follow-up to PR #334: preserve the prior GitHub App installation identity when
reinstall convergence receives a live probe with a null `app_installation_id`.

- Filters null probe values before merging live GitHub probe data with prior
  reinstall state.
- Adds a regression where answers omit `github.app.installation_id` and the
  live probe reports no installation, ensuring reruns still skip the App click.
