# CE v3 — Pilot Deployment & Transport Selection

*Curated, redacted design reference (provenance: 2026-06-06 design session). **DESIGNED / pilot-target** — re-ground at the implementing gate. Execution status lives in the project README's **Current Status** section.*

## Transport-selection matrix (the drive/observe channel, per scenario)
The decisive axis is **auth/billing × ToS, NOT vendor.** Authority is ALWAYS CE's external gate regardless of transport.

| Agent + auth | ACP available? | Pilot transport (Tier-A ACP deferred) | Post-pilot ceiling |
|---|---|---|---|
| **Claude Code + subscription** | ❌ Anthropic bans ACP-over-OAuth in 3rd-party tools | **CC-hooks / stream-json** (subprocess; first-class for OAuth) | subprocess only — ACP structurally unavailable on a Claude subscription |
| **Claude Code + API key** | ✅ (adapter, API-billed) | subprocess | ACP (Tier-A) |
| **Codex + subscription** | ✅ via `codex login` / an OpenAI access token (sanctioned automation cred) | Codex approval-mode / sandbox hooks (subprocess) | ACP (via access token) |
| **Codex + API key** | ✅ (App Server / adapter) | subprocess | ACP |
| **Gemini CLI** (sub/API) | ✅ native (`--acp`) | subprocess | ACP (native) |
| Long-tail / un-adapted agent | — | plain subprocess + transcript parse (degraded floor) | — |

**Pilot clamp:** the first pilot runs subprocess-tier uniformly (Tier-A ACP deferred post-pilot). The post-pilot ceiling is the durable differentiator — a **Claude subscription can NEVER reach ACP** (ToS); **Codex subscription, any API key, and Gemini can.**

### Verified facts (current-dated 2026-06-06)
- **Anthropic** disallows OAuth/subscription tokens in the Agent SDK / third-party tools (official Agent SDK docs; the ACP adapter requires an API key) → a Claude subscription cannot legitimately use the ACP path. CC-hooks (`PreToolUse`) + `--output-format stream-json` are the OAuth-compatible, first-class fallback (best-effort gate; diffs not structured).
- **Codex/OpenAI** speaks ACP (OpenAI's Codex App Server + community ACP bridges, e.g. `github.com/cola-io/codex-acp`); the bridge accepts BOTH `codex login` (ChatGPT subscription, inherited session) AND an `OPENAI_API_KEY`. OpenAI *recommends* API keys for programmatic/CI use but does **not** ban subscription-driven use, and offers sanctioned **access tokens** — distinct from raw subscription creds — "intended for trusted scripts, schedulers, private CI runners" (`developers.openai.com/codex/auth`). → **CE auths a Codex ACP drive via an OpenAI access token** (the blessed automation path), not raw subscription scraping. *Residual: OpenAI's subscription-automation fair-use at scale is unverified — low-risk for a single seat; fleets stay API-$.*

## Auto-select logic (at provision / doctor time)
1. **Native ACP?** (Gemini) → ACP.
2. **Else an ACP adapter exists AND auth/ToS permits?** — API key always; subscription only where the vendor permits (Codex via access token YES, Claude NO) → ACP.
3. **Else the subprocess tier** — CC-hooks/stream-json (Claude), Codex approval-mode hooks (Codex), or plain parse (floor).
4. **Pilot override:** Tier-A deferred ⇒ clamp to (3) for the first pilot.
- **Invariant:** the transport is selected per environment; the **binding gate is always CE's external spine + branch protection** — never the in-agent hook / ACP / MCP. The contract is transport-agnostic, so CE never bets on the tier.

## Deployment invariants (identical across every scenario)
- **Plane C box:** gVisor (`runsc`, Systrap — no KVM) + a deny-by-default egress proxy (egress opened only to the agent's LLM endpoint + the repo's git endpoints).
- **Two-credential custody:** *LLM auth* (the agent's subscription/key — in/near the box; blast radius = LLM spend, capped by the tokenomics gate) vs. *repo-write* (the GitHub-App private key → a JIT scoped token; **never in the box**, injected into the child `gh` env only at open/merge, then revoked).
- **Forge identity:** the agent opens/merges as the CE **GitHub App** (a bot identity ≠ the dev). For a **solo dev (N=1)** the **dev is the reviewer/Operator** — no-self-approval = agent (author) ≠ human (reviewer).
- **Install:** two operator-typeless modes (one-liner + signed agent-native spec) + dependency-resolution-with-permission; the operator approves only **sudo** + the **GitHub-App click**.

## Cost regime (tokenomics tie-in)
- **Subscription seats** = **single-seat %-meter** — the dev's own subscription pays the LLM; **cannot be fleeted** (ToS).
- **API-key seats** = **API-$ metered** — fleet-able. (The tokenomics gate enforces the spend envelope either way.)

## Companions
`pilot-roadmap.md` · [`pilot-uiux-model.md`](./pilot-uiux-model.md) · [`v3-secure-runtime.md`](./v3-secure-runtime.md) (Plane C).
