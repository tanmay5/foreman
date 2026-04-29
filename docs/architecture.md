# Foreman — Architecture

This document captures the V2 design decisions for Foreman. It is the source of truth for *why* the code is shaped the way it is.

## Product thesis

Foreman is a **prioritization and synthesis layer** on top of the engineering tools you already use. The connectors are commodity. The differentiation is:

1. **Memory** of how you actually work — who you respond to fast, what labels you treat as urgent, which repos you own.
2. **Prioritization** that scores every signal against that memory and explains *why* it matters.
3. **Specialized agents** that each own a domain and use the LLM's tool-use API to actually look at the data, not just summarize titles.

If we lose any of those three, we are a notifier and the product is uninteresting. The architecture protects all three.

## High-level shape

```
┌─────────────────────────────────────────────────────────────┐
│                       foreman process                       │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  GitHub      │    │  Jira        │    │  Slack       │   │
│  │  connector   │    │  connector   │    │  connector   │   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘   │
│         │                   │                   │           │
│         └─────────┬─────────┴─────────┬─────────┘           │
│                   ▼                   ▼                     │
│            ┌─────────────────────────────┐                  │
│            │       Event Bus (asyncio)   │                  │
│            └──────────────┬──────────────┘                  │
│                           ▼                                 │
│   ┌──────────────────────────────────────────────────┐      │
│   │  Prioritizer ◄── reads ── Memory (SQLite)        │      │
│   └──────────────────────────────────────────────────┘      │
│                           ▼                                 │
│            ┌────────┬─────────┬─────────┬─────────┐         │
│            │  Aria  │  Tony   │  Nat    │  Nick   │ Steve   │
│            └────┬───┴────┬────┴────┬────┴────┬────┴────┬────┘
│                 ▼        ▼         ▼         ▼         ▼    │
│            ┌─────────────────────────────────────────┐      │
│            │  Routing (dedup, escalation, rate-lim)  │      │
│            └─────────────────┬───────────────────────┘      │
│                              ▼                              │
│                    ┌─────────────────┐                      │
│                    │  TUI + Notifier │                      │
│                    └─────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

## Core decisions

### 1. Single async process, internal pub/sub

V1 split a daemon (writing JSONL queue) from the UI (tailing it). That worked but it's fragile — file-based IPC has races, no backpressure, no schema. V2 is a single Python process with an asyncio event loop and an in-memory pub/sub bus. Background pollers, prioritizer, agents, and UI are all subscribers/publishers on that bus.

Tradeoff accepted: if the process crashes, in-flight events are lost. That is fine — connectors re-poll on restart and dedup against the SQLite seen-items store.

### 2. SQLite for all state

Single file at `~/Library/Application Support/foreman/foreman.db` (macOS) or platform equivalent. Tables:

- `events` — every alert ever produced (immutable log)
- `seen_items` — connector dedup keys
- `actions` — what the user did with each event (replied, ignored, snoozed, opened)
- `memory_episodic` — derived facts: response latency by sender, engagement by repo, etc.
- `memory_semantic` — synthesized patterns: "user treats `security` label as P0", maintained by a nightly job
- `agent_traces` — every agent invocation, for debugging and quality eval

JSONL files are fine for logs, terrible for state. SQLite gives us atomicity, queryability, and a single backup target.

### 3. Pluggable connectors via Protocol

```python
class Connector(Protocol):
    name: str
    async def poll(self) -> list[Event]: ...
    async def fetch_detail(self, item_id: str) -> dict: ...
    async def health_check(self) -> HealthStatus: ...
```

Adding a fourth source (Linear, Notion, PagerDuty, GCal) is one new file in `connectors/` plus registration. No surgery elsewhere.

### 4. LLM via SDK abstraction, not subprocess

V1 shelled out to the local Claude CLI. Clever for a prototype, but it ties the product to a desktop install and kills portability. V2 uses the Anthropic Python SDK directly, behind an `LLMClient` interface that can swap providers (OpenAI, local Llama, etc.).

### 5. Agents are real, not prompt prefixes

Each agent in `foreman/agents/` is:
- A `system_prompt` (versioned in `llm/prompts/`)
- A bounded `tool_registry` (only the tools its domain needs)
- A `memory_namespace` (it reads/writes facts scoped to its domain)
- A clear `domain` it refuses to leave (Tony does not triage Jira)

Agents communicate only through the event bus and shared memory, never by calling each other directly. This keeps domain boundaries clean and makes each agent independently testable.

### 6. Memory layer (the moat)

**Episodic** — every event + your action against it. Plain SQL. Cheap, deterministic.

**Semantic** — patterns synthesized from episodic data by a nightly job. Examples of facts the system should converge on:

- "User responds to PRs from @sarah within 3 hours on average."
- "User treats Jira labels {`security`, `migration`, `cve`} as drop-everything."
- "User ignores 80% of #engineering-general mentions but replies to all DMs within an hour."

The semantic layer is what separates Foreman from a notifier. We synthesize it with an LLM and store it as a versioned `memory_semantic` table, with the source episodic events kept as evidence so a user can ever ask "why does Foreman think that?"

### 7. Prioritizer

Every event coming off the bus passes through the prioritizer before reaching agents. Output is `(score: float, reason: str)`. Inputs:

- Source urgency (security ticket > random Jira > PR comment > random Slack)
- Keyword/label matches against semantic memory
- Engagement history with the actor (sender, PR author, ticket assignee)
- Blocking signals (is someone waiting on this?)
- Deadlines (sprint end, due date)
- User-defined rules from `routing/rules.py`

The `reason` is generated, not templated. The briefing's killer line is "PR #123 — Sarah's blocked on this, you usually review hers same-day, sprint ends Thursday." That comes from this layer.

### 8. Routing

Dedup, rate-limit, escalation. Rules live in `routing/rules.py` as plain Python. Examples:

- Don't notify the same PR twice within 4 hours.
- Don't show Slack pings during a calendar meeting.
- Escalate any security ticket immediately, even outside polling cadence.

### 9. Auth, done right

- **GitHub:** PAT (fine-grained) for v0.1; GitHub App for v1.0 distribution.
- **Jira:** API token + email. Standard.
- **Slack:** Real Slack app with OAuth, Bot/User tokens. **No cookie scraping.** This is non-negotiable. The cookie + xoxc approach in V1 violates ToS, breaks weekly, and is unshippable. v0.3 ships the proper Slack app.

### 10. Config

`pydantic-settings` reading `.env`. Zero module-level secrets, zero hardcoded hostnames, zero hardcoded usernames. The repo ships only `.env.example`.

### 11. UI

- **TUI** (Rich) is primary. Personas color-coded, inline diffs, panels.
- **macOS notifications** for high-priority events when terminal isn't focused.
- **Web dashboard** is explicitly out-of-scope for v1.0. Add when 10 users ask.

### 12. Distribution

- Phase 1: `pip install foreman` from PyPI.
- Phase 2: `brew tap tanmayshah96/foreman` for a one-line macOS install.
- Phase 3: Hosted offering for teams (separate codebase, this one stays local-first).

## Explicit non-goals (V1.0)

- Multi-user / team features.
- Web UI.
- Any cloud component (no servers, no telemetry-by-default).
- Linear, Notion, PagerDuty, GCal connectors. These come post-1.0.
- Mobile app. Terminal users do not need one.

## Open questions to resolve in v0.x

- Should the briefing be daily-only, or is an end-of-day "what got done" rollup also valuable?
- How does the user correct the prioritizer when it's wrong? (Inline thumbs-up/down? Chat-based?)
- What's the right cadence for the semantic memory synthesis job? Nightly feels right but might be too lossy.
- Do agents share a memory namespace, or are they fully siloed? Leaning siloed with explicit cross-references.

## Things V1 did right that V2 keeps

- The four-agent UX as an information architecture.
- Morning briefing as the daily anchor.
- Terminal as the primary surface.
- Proactive polling, not on-demand-only.

## Things V1 did that V2 explicitly rejects

- File-based JSONL queue between processes.
- Subprocess to local Claude CLI.
- Slack auth via cookie + xoxc token.
- Module-level credential constants.
- Single 500-line files mixing fetching, scheduling, formatting, and IO.
- Hardcoded company-specific identifiers.
