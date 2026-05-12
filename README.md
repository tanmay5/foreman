<div align="center">

# Foreman

**What actually matters first this morning, across every place your work lives.**

Foreman answers that one question, every day, from a single terminal window. Reads your GitHub, Linear, Jira, and Slack. Synthesizes them into one priority surface. Learns how you actually work. Reviews PRs line by line. Triages tickets. All local, all on your own machine.

[![PyPI](https://img.shields.io/pypi/v/foreman-cli.svg)](https://pypi.org/project/foreman-cli/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)](#roadmap)

![Foreman banner](https://raw.githubusercontent.com/tanmay5/foreman/main/docs/screenshots/01-banner.svg)

</div>

## Why this exists

Senior engineers spend 30 to 60 minutes every morning reconstructing context across GitHub, Linear, Jira, and Slack. What changed overnight, what's blocked on me, what's urgent, what can wait, how much focus time I have before my first meeting. Existing tools either show you everything (notifiers) or show you nothing useful (digest emails). Neither learns your patterns.

Foreman is a small team of specialized AI agents. Each one owns a domain. They share a memory of how you work. They surface only the things you'd actually want surfaced.

It runs locally. Your data never leaves your machine.

## The morning briefing

One command, one answer. Aria reads your live state across every source you've configured and tells you what actually matters today, with a concrete first action.

![Cross-source briefing](https://raw.githubusercontent.com/tanmay5/foreman/main/docs/screenshots/07-cross-source.svg)

The narrative is generated each run from your real state. It's not a templated digest. When a PR, a ticket, and a DM are about the same problem, Aria sees the link and tells you. That cross-source synthesis is the moat.

## Foreman learns how you work

This is the part that makes it not-a-notifier.

Every briefing, PR review, ticket triage, and ad-hoc question logs to a local SQLite. Run `foreman learn` and a synthesis pass extracts patterns about how you actually work. Those patterns feed every future briefing, so the longer you use it, the sharper it gets.

A typical pattern set after a couple weeks of real use:

```
· You review PRs from @sarah within 3 hours on average; longer for other authors.
· You treat labels {security, migration, cve} as drop-everything regardless of priority field.
· You ignore ~80% of #engineering-general mentions but reply to all DMs within an hour.
· You don't close stale PRs until prompted.
· You tend to query for information without acting between queries.
```

Aria then uses these to sharpen the briefing. Instead of *"you have 3 open PRs"* you get something like *"the run-ingestion PR is 61 days old and has no reviewer; the blocker is likely a missing decision, not missing time. Past pattern says you don't close stale PRs without a nudge — close the two abandoned ones now while you're here."*

That's the difference between a tool that lists your inbox and a chief of staff that knows you.

## Real PR reviews

Tony reads the unified diff and produces a focused review with file:line references, prioritized by what actually breaks production. Bugs, missing error handling, security, breaking API changes, missing tests.

![PR Review](https://raw.githubusercontent.com/tanmay5/foreman/main/docs/screenshots/03-review.svg)

You stay in the loop. Tony tees up the context so you're not starting cold.

## Ticket triage with a real plan

Nat reads a Linear or Jira ticket and produces a structured triage: a summary, a concrete plan with verb-and-target steps, and an effort estimate. Security and migration labels get escalated automatically.

![Ticket triage](https://raw.githubusercontent.com/tanmay5/foreman/main/docs/screenshots/05-nat-triage.svg)

## Slack digest, not Slack noise

Nick distinguishes "FYI ping" from "needs your input" from "blocking someone right now." Real Slack OAuth, no cookie scraping.

![Slack digest](https://raw.githubusercontent.com/tanmay5/foreman/main/docs/screenshots/06-nick-slack.svg)

## Ask anything

Steve has read access to your live state across every connector. Senior-engineer voice, no fluff. Gives a recommendation, not options.

![Ask](https://raw.githubusercontent.com/tanmay5/foreman/main/docs/screenshots/04-ask.svg)

## Meet the team

| Agent | Color | Domain |
|-------|-------|--------|
| **Aria** | 🟢 emerald | Daily briefings, standups, cross-source synthesis, memory-aware prioritization |
| **Tony** | 🔴 red | PR reviews with line-specific feedback |
| **Nat** | 🟣 violet | Linear + Jira triage, security and migration escalation |
| **Nick** | 🟡 amber | Slack DMs, mentions, urgency scoring |
| **Steve** | 🔵 blue | Catch-all questions, your fallback engineer |

Each agent has its own scoped tool set, its own memory namespace, and a clear domain it refuses to leave. They are not prompt-prefix personas. They're real specialized agents.

---

## Quick start

```bash
pip install foreman-cli
```

Requires Python 3.11+.

You'll need:

* **Anthropic API key**: [console.anthropic.com](https://console.anthropic.com/settings/keys). $5 lasts roughly 1000 briefings on Sonnet.
* **GitHub Personal Access Token**: [github.com/settings/personal-access-tokens/new](https://github.com/settings/personal-access-tokens/new) with `Contents: Read` and `Pull requests: Read`.
* **Linear API key** (optional): [linear.app/settings/account/security](https://linear.app/settings/account/security).
* **Jira API token + email** (optional): [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens).
* **Slack User OAuth Token** (optional): [api.slack.com/apps](https://api.slack.com/apps) → create app → User Token Scopes: `im:read im:history users:read search:read`.

Create a `.env` in your working directory:

```bash
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=github_pat_...
GITHUB_USER=your-github-username

# Optional connectors below
LINEAR_API_KEY=lin_api_...
JIRA_BASE_URL=https://your-org.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=...
SLACK_USER_TOKEN=xoxp-...
```

Then:

```bash
foreman doctor      # verify config + connectors
foreman run         # always-on REPL with background polling
```

## Commands

```
foreman briefing              Aria's morning briefing across every configured source
foreman standup               standup notes from yesterday's activity
foreman review-pr <n>         Tony reviews a PR (auto-detects repo)
foreman triage <id>           Nat triages a Linear or Jira ticket (auto-detects source)
foreman digest                Nick's Slack DM digest
foreman ask "..."             Steve answers anything
foreman learn                 Synthesize patterns from your activity (memory layer)
foreman history               Recent agent activity
foreman run                   Always-on REPL: type any of the above, or just ask Steve
```

Inside `foreman run`, a background poller checks GitHub every 10 minutes and surfaces new PRs inline plus as macOS notifications.

## How it works

```
┌─────────────────────────────────────────────────────────────┐
│                       foreman process                       │
│                                                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │ GitHub  │ │ Linear  │ │  Jira   │ │  Slack  │ │  ...   │ │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬───┘ │
│       └───────────┴───────────┴───────────┴───────────┘     │
│                            ▼                                │
│            ┌─────────────────────────────┐                  │
│            │    Event Bus (asyncio)      │                  │
│            └──────────────┬──────────────┘                  │
│                           ▼                                 │
│   ┌──────────────────────────────────────────────────┐      │
│   │  Memory (SQLite)  ◄── episodic log + patterns    │      │
│   └────────────────────────┬─────────────────────────┘      │
│                            ▼                                │
│            ┌────────┬─────────┬─────────┬─────────┐         │
│            │  Aria  │  Tony   │  Nat    │  Nick   │ Steve   │
│            └────┬───┴────┬────┴────┬────┴────┬────┴────┬────┘
│                 ▼        ▼         ▼         ▼         ▼    │
│            ┌─────────────────────────────────────────┐      │
│            │      Rich TUI + macOS notifications     │      │
│            └─────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

Architecture rationale (why SQLite not JSONL, why specialized agents not a megaprompt, why local-first) lives in [`docs/architecture.md`](docs/architecture.md).

## Connectors

| Connector | Auth | Status |
|-----------|------|--------|
| GitHub | Personal Access Token | ✅ shipped |
| Linear | API key | ✅ shipped |
| Jira | API token + email | ✅ shipped |
| Slack | User OAuth token | ✅ shipped |
| Google Calendar | OAuth | shipping next |
| Sentry | Auth token | shipping next |

Adding a connector is a single file in `foreman/connectors/` plus registration. Adding an agent is a single file in `foreman/agents/` plus a versioned prompt in `foreman/llm/prompts/`.

## Privacy and local-first

* Every token (GitHub, Linear, Jira, Slack, Anthropic) lives in `.env` on your machine. They never leave.
* All state — briefings, reviews, learned patterns, activity history — is stored in a single SQLite file at `~/Library/Application Support/foreman/foreman.db`.
* LLM calls go directly from your machine to Anthropic. There is no Foreman-operated server in the middle.
* No telemetry. No analytics. No "anonymous usage data."

## Roadmap

- ✅ **v0.1–0.5**: GitHub connector, Aria, Tony, Steve, memory log, daemon mode
- ✅ **v0.6–0.7**: Linear, Slack, PyPI release
- ✅ **v0.8**: Memory synthesis (Foreman starts learning your patterns), Jira connector, cross-source briefings (you are here)
- 🔜 **v0.9**: Google Calendar (time-budget awareness), Sentry (production-risk axis)
- 🔜 **v1.0**: Automatic nightly memory synthesis, prioritization engine with explicit "why this matters" reasons, brew-installable, public-launch ready

## Contributing

Issues and PRs welcome. If you're a senior engineer who wants Foreman to surface things it doesn't currently, open an issue describing the signal and how you'd want it framed. That drives the roadmap more than my guesses.

## License

MIT. See [LICENSE](LICENSE).
