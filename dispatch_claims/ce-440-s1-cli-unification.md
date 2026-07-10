# WORK CLAIM: ce-440-s1-cli-unification
- Lane: E — CLI unification (ce-ops#440, Operator-ratified; design SSOT CE440_CLI_UNIFICATION_DESIGN_20260704.md)
- Seat: dev-3 (contained; harvest-side push)
- Branch: ce-440-s1-cli-unification
- Paths: ce_cli.py (shim table + pickup re-nest) + v3_cli.py (onboard→install rename) + test_v1_docs_reconciliation.py + test_v3_cli.py + NEW parity test file + README.md (group entries + onboard-flag bug fix) + changelog
- Territory: disjoint from #773 rework (container_launcher/worker_runtime), discovery (new module), portability-guard harvest (checks/ + governance manifest — note: BOTH touch validate-pr-adjacent test files; slug-level disjoint verified: reconciliation test vs aggregate wiring)
- Claimed: 2026-07-04 by CE-DEV-2 controller
- Brief: BRIEF_ce440_s1_cli_unification.md sha256=740280915955296f15e55b847ece1965b538df069dc2518aa29eaf8bf8db43a7
