# Pull Request

## Scope / Changed Boundary

<!-- Describe what this PR changes and what it does NOT change.
     List the specific files and directories modified.
     State the mutation class (standard / governed / privileged). -->

- **Mutation class:**
- **Declared work class:** <!-- XS / S / M / L -->
- **Files changed:**
- **Files explicitly NOT changed:**

## Validation Evidence

<!-- Paste the output of validation commands run locally before opening this PR.
     CI verifies; CI does not ratify.
     A green CI run is evidence, not authorization. -->

```
# paste validation output here
```

- [ ] `git diff --check` clean
- [ ] YAML parse clean for all changed YAML files
- [ ] Creator Engine validator passes on changed artifacts (if applicable)
- [ ] No write permissions or deploy/merge/approve actions introduced in workflow changes
- [ ] Boundary check: only files within the authorized scope are staged

## Privileged Mutation / Source Ratification Notice

<!-- For governed or privileged mutation classes, complete this section.
     Omit only for purely standard changes with no governance impact. -->

**Does this PR contain governed or privileged mutations?** (yes / no / N/A)

If yes:

- **Source ratification envelope reference:**
- **Authorized scope (files/paths):**
- **Dominant mutation class:**
- **Prohibited actions confirmed not taken:** (no live branch-protection mutation, no deploy, no merge, no secrets)

> **IMPORTANT:** CI verifies; CI does not ratify.
>
> A passing CI run, a reviewer approval, or a checked checkbox does NOT constitute
> Source ratification for governed or privileged mutation classes.
> Live GitHub settings, branch-protection application, deploy automation, and
> ratification of privileged governance changes each require a separate,
> explicit Source ratification envelope.

## Notes / Caveats

<!-- Optional: anything reviewers should know that is not captured above. -->
