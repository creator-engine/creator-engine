# WORK CLAIM — ce-s1b-seat-image
claimed: 2026-07-05T07:35Z (parallel thread on dev-1, concurrent with #414/#417 docs units)
seat: dev-1
ticket: day-arc S1 unit B (canonical seat image; ce-ops ticket to be filed by triage)
branch: ce-s1b-seat-image
paths:
  - deploy/seat-image/ (new: Dockerfile, README.md)
  - .github/workflows/publish-seat-image.yml (or extension of publish-runtime-image.yml)
  - surfaces/manifest.yaml (seat-image pin entry)
  - validators/tests/unit/ (static seat-image tests)
  - .ce/changelog/ce-s1b-seat-image.md · .ce/pr-manifests/ce-s1b-seat-image.md
brief: .ce/briefs/BRIEF_ce_s1b_seat_image.md
