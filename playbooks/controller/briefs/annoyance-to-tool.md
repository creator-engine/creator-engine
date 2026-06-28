# Annoyance → Tool

When the controller encounters recurring toil — a step that fires more than once
per week, a manual edit that a seat always requires, or a check that is done by
reading a doc and re-typing the same output — stop and follow this loop:

1. **Name the annoyance.** State what action you are doing manually and how often.
2. **File a ticket.** Open a ce-ops issue with title "Annoyance: <short name>".
   Label it `toil`. Link to the session or PR where you first noticed it.
3. **Scope the tool.** In the ticket, describe the minimal automated form: a
   playbook brief, a `ce` command, a skill, or a validator check. Keep it bounded
   (tiny or story class).
4. **Dispatch the implementation.** Route the ticket to the correct worker role
   (implementer for code, architect_research for scoping). Do not inline the
   implementation in the controller session.
5. **Verify the loop closed.** After the tool lands, confirm the manual step is
   gone. If the same annoyance recurs after the tool lands, it is a regression
   ticket.

## Examples of Annoyances That Become Tools

- Manual PR body edit to add `- **Declared work class:** story` → became the G5
  body-line auto-emit (ce-ops#340, W5 slice of ce-ops#295).
- Repeating dispatch guard rails in every brief → became a populated `AGENTS.md`
  (ce-ops#295 Wave 3.1).
- Checking whether a PR is already landed before dispatch → became the
  `ce-verify-not-already-landed` memory doctrine and a pre-dispatch checklist.

## Halt Conditions

- Do not file an annoyance ticket during a time-critical merge window. Note it in
  memory and file it at the next natural break.
- Do not scope the tool as an epic. If the fix is larger than a story, break it
  into slices and file each slice.
