# WORK CLAIM — ce-p5-seatwatch-s1
claimed: 2026-07-09T04:5xZ (STRANGELOOP-1 pool P5; dev-3 restock post-compact)
seat: dev-3
branch: ce-p5-seatwatch-s1
paths: deploy/seat-watch/ (new) + validators seat_watch_daemon.py/seat_watch_runner.py (new) + tests + DESIGN.md + carrier + changelog
brief: .ce/briefs/BRIEF_dev3_P5_seatwatch_20260709.md (sha256 498944bbb9b751dcd433ca0da2cb711463cc4a154c1b001325a26972bc8ac598)
constraints: observe-only slice (no dispatch authority, no herdr writes); reuse conveyor_discovery probe machinery by IMPORT; no deploy/queue-daemon|singleton-redeploy touches; NO assertions.yaml; COMMIT-ONLY; targeted tests in-seat
