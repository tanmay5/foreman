# Foreman

> Personal engineering chief-of-staff. Always on.

Foreman is a terminal-native AI assistant for senior engineers drowning in signals. It synthesizes your GitHub, Jira, and Slack into a daily briefing that learns your patterns and tells you what actually matters today — not just what's new.

It is **not** a notifier. Notifiers move noise from one inbox to another. Foreman is a prioritization layer on top of that noise: a small team of specialized agents (PR reviewer, Jira triager, Slack digester, daily synthesizer) that each own a domain, share a memory of how you work, and surface only the things you'd actually want surfaced.

## Status

🚧 **Pre-alpha.** Architecture scaffolded; first connector slice next.

## Why this exists

Senior engineers spend 30–60 minutes every morning context-switching between tabs to reconstruct: *what changed overnight, what's blocked on me, what's urgent, what can wait.* That ritual is identical for everyone, completely unleveraged, and extracts a real cognitive tax before the day's deep work begins.

Existing tools either show you everything (notifiers) or show you nothing useful (digest emails). Neither learns your patterns. Neither knows that you always review Sarah's PRs same-day, that anything labeled `security` is drop-everything for you, or that the migration ticket that's been open three weeks is actually unblocked now.

Foreman is the assistant that closes that gap.

## The four agents

| Agent | Domain | What they do |
|-------|--------|--------------|
| **Aria** | Daily synthesis | Morning briefing. Top 3 priorities. End-of-day rollup. |
| **Tony** | Code review | PR triage, diff analysis, review-readiness assessment. |
| **Nat** | Jira | Ticket triage, security/migration escalation, blocker detection. |
| **Nick** | Slack | DM and mention digest, urgency scoring, reply-needed flagging. |
| **Steve** | General | Fallback for ad-hoc questions that don't fit the others. |

Each agent has its own scoped tool set and memory namespace. They are not prompt-prefix personas — they are real specialized agents using the LLM's tool-use API, with strict domain boundaries.

## Architecture in one paragraph

Single async Python process, internal pub/sub event bus. Pluggable connectors (GitHub, Jira, Slack) poll on independent schedules and publish typed events. A prioritization engine scores each event using your historical engagement patterns from the memory layer (SQLite-backed, episodic + semantic). High-priority events route to the relevant agent for analysis; results surface in the Rich-based TUI and as macOS notifications. Each morning, Aria synthesizes the past 24 hours into a punchy briefing answering one question: *what should you do first today, and why.*

See [`docs/architecture.md`](docs/architecture.md) for the full design.

## Quick start (once v0.1 ships)

```bash
# Install (once published)
pip install foreman

# Or from source
git clone https://github.com/tanmay5/foreman.git
cd foreman
uv sync
cp .env.example .env  # fill in tokens

# First-run setup
foreman init

# Start the daemon
foreman run

# Or one-shot commands
foreman briefing            # force a briefing now
foreman review-pr 123       # have Tony review a specific PR
foreman jira ABC-456        # have Nat analyze a ticket
```

## Roadmap

- **v0.1** — GitHub connector + briefing command. Spine works end-to-end.
- **v0.2** — Jira connector + Tony agent (PR review with tool use).
- **v0.3** — Slack connector (real OAuth app, not cookie scraping) + Nick agent.
- **v0.4** — Memory layer + prioritization engine. The differentiator.
- **v0.5** — Background daemon, scheduling, notifications.
- **v1.0** — Stable, documented, brew-installable.

Beyond v1.0: hosted offering, team intelligence, additional connectors (Linear, PagerDuty, GCal).

## Design principles

1. **Synthesis over surfacing.** Anyone can list your open PRs. Foreman tells you which one matters.
2. **Memory is the moat.** The product gets sharper the longer you use it. Episodic + semantic memory of your patterns.
3. **Specialized agents over a megaprompt.** Each agent has bounded scope and the right tools for its job.
4. **Local-first.** Your data stays on your machine. SQLite, not a cloud database.
5. **Terminal-native.** No web dashboard until users beg for one.
6. **One thing per release.** Ship a working slice; resist the urge to scaffold everything.

## License

MIT. See [LICENSE](LICENSE).
