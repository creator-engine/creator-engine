# BRIEF — dev-1 — F5 verification: does `ce onboard` block real users? (REPORT, not a PR)

Non-contained, VPS. This is a VERIFICATION lane → produce a REPORT. Do NOT push code.

## The open question
In the Mac smoke test, `ce onboard` failed with `ok:false, reason:"doctor refused (ungoverned host)", refused_clauses:["RED-G-6"]`. RED-G-6 = packaging-contract drift: it looked for `validators/pyproject.toml`, `validators/wheelhouse`, `validators/uv.lock` relative to CWD. Those are CE *source-tree developer* artifacts — a normal user's project repo would never have them. BUT the smoke ran in a non-git `/workspace`, which is non-standard.

WE MUST KNOW: does `ce onboard` fire RED-G-6 (and thus fail) for a REAL first-time user running it in their OWN git repo? If yes, `ce onboard` is unusable for every new user and `welcome.md`'s "First run: ce onboard" guidance is wrong — they'd need `ce brain init` + `ce launch` instead.

## Test (linux/amd64 container, mirrors the Mac-via-container path)
1. `docker info` to confirm a runtime (you have Docker 29.x). If none, STOP and report.
2. In a fresh `ubuntu:24.04` linux/amd64 container, install CE via the public one-liner (same as the prior smoke — see `/tmp/ce-mac-smoke-dev1-20260629T075220Z/03-real-installer-oneliner.txt` for the exact command you used).
3. Create a REAL user project repo: `mkdir /tmp/myproj && cd /tmp/myproj && git init && echo "# my project" > README.md && git add -A && git commit -m init`.
4. From inside `/tmp/myproj`, run `ce onboard --json` and `ce doctor --json` (capture both).
5. Report: does RED-G-6 fire in a real git repo? Capture the exact `refused_clauses` + the `doctor` packaging-check detail. Also try `ce brain init` + `ce launch --json` from `/tmp/myproj` and report whether THAT path works for a user repo.

## Deliver
A short REPORT: (a) RED-G-6 fires in a real user git repo? y/n + evidence; (b) if yes, is it a hard block on `ce onboard` for users; (c) does `ce brain init` + `ce launch` work as the alternative first-run path. Save transcripts under a `/tmp/ce-f5-onboard-verify-*` dir. Report FIRST; do not "fix" anything.
