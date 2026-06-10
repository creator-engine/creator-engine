# PR path manifest — v3.5-E.1+E.2: site onboarding (one-liner + root-served installer + llms.txt + connect-to-repo)

CI passes this to `verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; the
fidelity scan requires the declared count + SHA256 to match the fenced block.

Surfaces the install one-liner on the marketing site, moves the installer artifacts to the
GitHub-Pages root so their printed URLs resolve, adds the agent-native `/llms.txt` discovery
surface, extends the install playbook with the connect-to-repo leg, and archives the outgoing
v5 site per the versioning policy. **Site/docs only — zero validator code, no check-registry or
`V3_RUNTIME` change.**

Per-file purpose:
- **`docs/index.html`** *(M)* — add the `curl … | bash` one-liner + agent-pointer; sync `<title>`↔H1; reconcile the double-headline.
- **`docs/install.sh`** *(R100 from `docs/install/install.sh`)* — moved so `/install.sh` resolves at the Pages root.
- **`docs/llms-install.md`** *(R from `docs/install/llms-install.md`)* — moved + new §6 connect-to-repo (two-mode pattern).
- **`docs/llms.txt`** *(A)* — agent-native discovery index (llmstxt.org format).
- **`docs/contracts/installer.md`** *(M)* — moved-path references only.
- **`site-archive/index-v5-nvidia-ready.html`** *(A)* — verbatim snapshot of the outgoing v5 index ([[ce-website-versioning-policy]]).
- **`site-archive/README.md`** *(M)* — ledger note (v6 = this change).
- **`.ce/pr-path-manifest.md`** *(this carrier)*.

- **base:** `60b5287` (current `main`).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=d7ea82c780cc1fc4ecafa807a79edffa85fbdb9d3b26980001877e4b3b7808b9

```text
.ce/pr-path-manifest.md
docs/contracts/installer.md
docs/index.html
docs/install.sh
docs/llms-install.md
docs/llms.txt
site-archive/README.md
site-archive/index-v5-nvidia-ready.html
```
