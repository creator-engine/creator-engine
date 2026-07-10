# WORK CLAIM — ce-p3-rehearsal-s1
claimed: 2026-07-09T04:2xZ (STRANGELOOP-1 pool P3; dev-3 restock; Decisions 14+15)
seat: dev-3
branch: ce-p3-rehearsal-s1
paths: deploy/rehearsal/ (new: run-rehearsal.sh, evidence-format.md, README.md, smoke test) + carrier + changelog
brief: .ce/briefs/BRIEF_dev3_P3_rehearsal_harness_20260709.md (sha256 771599785c0566406b11fffe00bccc38a38a86b3accd88967264a2c99b7fa4aa)
constraints: NO gating flip, NO CI wiring, NO deploy/queue-daemon|singleton-redeploy touches (ce-512 in flight), NO assertions.yaml; COMMIT-ONLY; in-seat targeted tests only
