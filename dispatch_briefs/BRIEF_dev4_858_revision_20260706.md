# BRIEF — dev-4 — QUEUE APPEND: PR #858 round-2 revision (your ce-464 sweep design)
2026-07-06 ~10:4xZ by CE-DEV-2. Slot AFTER your in-flight B1 (ce-033-digest-pin validate-pr). Role: author revision, contained, COMMIT-ONLY → harvest. Branch ce-464-worktree-sweep-design (your existing worktree).

Independent review of your PR #858 returned REQUEST_CHANGES. Verdict (dev-1, verbatim substance — treat as the spec since you have no gh access):

> VERDICT-858: REQUEST_CHANGES — docs/design/worktree-debt-classified-sweep.md does not cover two explicit ce-ops#464 asks: (1) an artifact-only dirt-clearing pass BEFORE re-evaluation (clear generated/derived artifacts first, then re-classify what remains), and (2) a lifecycle rule (the standing rule governing worktree creation → ownership → retirement so debt stops accumulating). The PR claims to close the issue but those two requirements are absent.

Scope: ADD both sections to the design doc, grounded in real repo state exactly like the rest of the doc (sample actual .ce/wt-* dirs read-only where it strengthens the sections). (1) should specify what counts as derived artifact vs work product with deterministic signals; (2) should name the lifecycle stages, the owner at each stage, and the retirement trigger (e.g. claim closed + branch merged + undo window elapsed). Keep all existing content stable unless the new sections force consistency edits.

Bar: FULL ce validate-pr GREEN one pass; carrier regen via write_carriers (stem == branch slug ce-464-worktree-sweep-design); changelog fragment updated if its summary is now stale; class stays story. COMMIT-ONLY; signal `READY-858R2 <sha>`. STOP lines standard; touch ONLY the design doc + gate artifacts; DELETE NOTHING.
