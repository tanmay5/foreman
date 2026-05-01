<div align="center">

# Foreman

**Personal engineering chief-of-staff. Always on.**

Synthesizes your GitHub into a daily briefing, reviews PRs with line-specific feedback, and answers questions about your engineering state. From one terminal window.

[![PyPI](https://img.shields.io/pypi/v/foreman-cli.svg)](https://pypi.org/project/foreman-cli/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)](#roadmap)

![Foreman banner](docs/screenshots/01-banner.svg)

</div>

## Why this exists

Senior engineers spend 30 to 60 minutes every morning reconstructing context across GitHub, Jira, and Slack: what changed overnight, what's blocked on me, what's urgent, what can wait. Existing tools either show you everything (notifiers) or show you nothing useful (digest emails). Neither learns your patterns.

Foreman is a small team of specialized AI agents. Each one owns a domain, shares a memory of how you work, and surfaces only the things you'd actually want surfaced. All from a single terminal.

It runs locally. Your data never leaves your machine.

## The morning briefing

Every time you start your day, ask once. Aria reads your live GitHub state and tells you what actually matters today, with a concrete first action.

![Briefing](docs/screenshots/02-briefing.svg)

This isn't a templated digest. The narrative is generated each run from your real state: PRs awaiting your review, your own open work, ages, blocking signals.

## Real PR reviews, not summaries

Tony reads the unified diff and produces a focused review with file:line references, prioritized by what actually breaks production. Bugs, missing error handling, security, breaking API changes, missing tests.

![PR Review](docs/screenshots/03-review.svg)

You stay in the loop. Tony tees up the context so you're not starting cold.

## Ask anything

Steve has read access to your live GitHub state. Senior-engineer voice, no fluff. Gives a recommendation, not options.

![Ask](docs/screenshots/04-ask.svg)

## Meet the team

| Agent | Color | Domain |
|-------|-------|--------|
| **Aria** | 🟢 emerald | Daily briefings, standups, synthesis |
| **Tony** | 🔴 red | PR reviews, line-specific feedback |
| **Nat** | 🟣 violet | Jira / Linear triage, security, migration tickets *(v0.6)* |
| **Nick** | 🟡 amber | Slack digests, DMs, mentions *(v0.7)* |
| **Steve** | 🔵 blue | Catch-all questions, your fallback engineer |

Each agent has its own scoped tool set, its own memory namespace, and a clear domain it refuses to leave. They are not prompt-prefix personas. They're real specialized agents.

---

## Quick start

```bash
pip install foreman-cli
```

You'll need:

* **Anthropic API key**: [console.anthropic.com](https://console.anthropic.com/settings/keys). $5 lasts roughly 1000 briefings on Sonnet.
* **GitHub Personal Access Token**: [github.com/settings/personal-access-tokens/new](https://github.com/settings/personal-access-tokens/new) with `Contents: Read` and `Pull requests: Read`.

Create a `.env` in your working directory:

```bash
GITHUB_TOKEN=github_pat_...
GITHUB_USER=your-github-username
ANTHROPIC_API_KEY=sk-ant-...
```

Then:

```bash
foreman doctor      # verify config + connectors
foreman run         # always-on REPL with background polling
```

Or use one-shot commands:

```bash
foreman briefing             # Aria's morning briefing
foreman standup              # standup notes from yesterday's activity
foreman review-pr 312        # Tony reviews a PR
foreman ask "..."            # Steve answers anything
foreman history              # recent agent activity
```

## Commands inside `foreman run`

```
briefing              Aria's morning briefing
standup               Aria's standup notes
review-pr <n>         Tony reviews PR #n (auto-detects repo)
history [n]           Recent agent activity (default 10)
help                  This list
quit / exit           Stop the daemon
<anything else>       Treated as a question for Steve
```

When `foreman run` is going, a background poller checks GitHub every 10 minutes. New PRs assigned to you surface inline plus as a macOS notification. First run silently registers your existing review queue so you don't get a notification storm.

## How it works

```
┌─────────────────────────────────────────────────────────────┐
│                       foreman process                       │
│                                                             │
│  ┌──────────────┐                                           │
│  │  GitHub      │   ← polls every N min                     │
│  │  connector   │                                           │
│  └──────┬───────┘                                           │
│         │                                                   │
│         ▼                                                   │
│   ┌─────────────────────────────────┐                       │
│   │       Event Bus (asyncio)       │                       │
│   └─────────────────┬───────────────┘                       │
│                     ▼                                       │
│         ┌───────────────────────┐                           │
│         │  Memory (SQLite)      │  ← every event persists   │
│         └───────────┬───────────┘                           │
│                     ▼                                       │
│   ┌────────┬────────┬────────┬────────┬────────┐            │
│   │  Aria  │  Tony  │  Nat   │  Nick  │ Steve  │            │
│   └────┬───┴────┬───┴────┬───┴────┬───┴────┬───┘            │
│        ▼        ▼        ▼        ▼        ▼                │
│   ┌─────────────────────────────────────────┐               │
│   │   Rich TUI + macOS Notifications        │               │
│   └─────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

See [`docs/architecture.md`](docs/architecture.md) for the full design rationale. Why SQLite (not JSONL queues), why specialized agents (not a megaprompt), why local-first (privacy plus zero procurement friction).

## Roadmap

* ✅ **v0.1**: GitHub connector and briefing
* ✅ **v0.2**: Aria comes online (LLM-synthesized briefings)
* ✅ **v0.2.1**: Standup generator
* ✅ **v0.3**: Tony comes online (line-specific PR review)
* ✅ **v0.3.1**: Steve comes online (ad-hoc Q&A)
* ✅ **v0.4**: Memory layer (SQLite), `foreman history`
* ✅ **v0.5**: `foreman run` always-on daemon (you are here)
* 🔜 **v0.6**: Linear and Jira connectors plus Nat agent (security and migration triage)
* 🔜 **v0.7**: Slack connector plus Nick agent (real OAuth, not cookie scraping)
* 🔜 **v0.8**: Memory synthesis. Foreman starts learning your patterns ("you always review @maria's PRs same-day")
* 🔜 **v0.9**: Prioritization engine. "Why this matters" reasons on every alert
* 🔜 **v1.0**: Stable, brew-installable, public-launch ready

## Privacy and local-first

* Your GitHub token, Linear token, Jira token, and Anthropic key live in `.env` on your machine. They never leave.
* All state (briefings, reviews, history) is stored in a single SQLite file at `~/Library/Application Support/foreman/foreman.db`.
* LLM calls go directly from your machine to Anthropic. No Foreman-operated server in the middle.
* No telemetry. No analytics. No "anonymous usage data."

## Contributing

Issues and PRs welcome. The architecture is intentionally pluggable: adding a connector (Linear, Notion, PagerDuty) is one new file in `foreman/connectors/`. Adding an agent is one new file in `foreman/agents/` plus a versioned prompt in `foreman/llm/prompts/`.

If you're a senior engineer who wants Foreman to surface things it doesn't currently, open an issue describing the signal and how you'd want it framed. That drives the roadmap.

## License

MIT. See [LICENSE](LICENSE).
