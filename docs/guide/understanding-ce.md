# Understanding Creator Engine

*A plain-language guide to what CE is and the words it uses. Brand new? Start at the [`Welcome / Start Here`](./welcome.md) onboarding front door, then come back here for the workflow tour. If you want the full, precise mapping to the machine underneath, the canonical reference is [`../architecture/stage-vocabulary.md`](../architecture/stage-vocabulary.md).*

## What CE is

Creator Engine runs **your own coding agent — under governance.** You keep chatting with the agent you already use; CE wraps a structured, stateful, artifact-aware workflow around it so that real work is **planned, tracked, checked, and merged on purpose** — not in one undifferentiated blur of edits. The core idea: **the thing that decides whether work is good lives *outside* the agent.** You judge artifacts — a plan, a diff, the evidence, the PR — not a transcript.

## The five stages: Frame → Shape → Build → Review → Ship

CE names where you are with five plain words. They describe **what you're doing right now**, and they work at any size — a one-line fix or a whole project.

1. **Frame** — *understand the problem.* What's being asked, why, and what "done" looks like. This is just thinking; nothing is tracked yet.
2. **Shape** — *turn it into a bet.* You and the agent draft a small, ratifiable unit of work called a **Scope**: what done means, how much you're willing to spend, what kind of change it is. When it's complete, you place the bet.
3. **Build** — *do the work.* The agent executes the bet in one governed, sandboxed run.
4. **Review** — *check it.* The result is graded against what you said "done" was — with evidence, not vibes.
5. **Ship** — *land it.* The governed finish: a merged pull request, delivered research, or a reasoned "no change needed."

You'll see the current stage in the status line as you work, so you're never lost.

## The Scope card: your unit of work

When a chat request turns into real work, CE drafts a **Scope** — a small card with five fields. The agent fills in what it can and asks you only what it must:

| Field | What it means |
| --- | --- |
| **Goal** | what you're trying to do |
| **Done when** | the checks that say it's finished (these are what get graded) |
| **Budget** | how much effort you're willing to spend — a fixed cap you commit, *not* a time estimate |
| **Change type** | what kind of change this is, and how risky (a docs tweak vs. a deploy) |
| **Ready** | a ✓ that appears once the other four are filled in and valid |

Once the card is **Ready**, you place the bet and the agent starts building. A card in progress looks like this:

```
◆ CE · Shape → "rate-limit /api/login"   (Goal ✓ · Done-when 3 · Budget S · Change-type code · Ready ✓)
◆ CE · ratify & dispatch the bet? › yes
```

A few things worth knowing:
- **You set the Budget.** The agent never decides how much you're willing to spend — that's your call.
- **The agent can make a change *safer* on its own, but only you can make it *riskier*.** If a change turns out to be higher-stakes than first drafted, that needs your explicit OK.
- **Nothing is tracked until you say yes.** Plain chat stays plain chat; a Scope only appears when you confirm the bet.

## Seeing the machine under the skin

These friendly words are a **clear skin over a precise state machine.** Under "Ready" is a real Definition-of-Ready check; under "Ship" is a governed, branch-protected merge; under the five stages is a conserved lifecycle that the evidence and governance run on. The skin makes CE approachable; the machine makes it trustworthy — and you can always look underneath.

If you want the full mapping — every user-facing word to its mechanical state, the gates, and how the same five stages scale from a single ticket up to a whole project — read the canon: [`../architecture/stage-vocabulary.md`](../architecture/stage-vocabulary.md).

---

*This is the seed of CE's in-product help; the full interactive guide ships with the product surface.*
