## ce-ops#344 slice 3 - skill-ify ce-dispatch + ce-harvest

- Added `playbooks/controller/briefs/harvest.md` as the in-tree SSOT for the
  harvest sequence and thin-pointer target for the new `ce-harvest` skill.
- Added `.claude/skills/ce-harvest/SKILL.md` as a thin-pointer CE action skill
  asserting preflight-GREEN, changelog collection, carrier generation, and
  controller-held merge gate.
- Tightened `.claude/skills/ce-dispatch/SKILL.md` so territory-check is now a
  REQUIRED hard-stop step with exact artifact paths named.
- Extended `test_shipped_pilot_skills_pass_the_guard` to assert `ce-harvest`
  exists and all shipped CE skills are antidrift-clean.
