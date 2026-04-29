"""Command-line entry point for Foreman.

Exposes:
    foreman init          # interactive first-run setup
    foreman run           # start the daemon (polling + UI)
    foreman briefing      # force a briefing now
    foreman review-pr N   # have Tony review a specific PR
    foreman jira KEY      # have Nat analyze a ticket
    foreman doctor        # diagnose config + connector health
"""

from __future__ import annotations

import typer

app = typer.Typer(
    name="foreman",
    help="Personal engineering chief-of-staff. Always on.",
    no_args_is_help=True,
)


@app.command()
def init() -> None:
    """Interactive first-run setup: write .env, init db, verify connectors."""
    raise NotImplementedError("v0.1: implement after config + db modules land")


@app.command()
def run() -> None:
    """Start the foreman daemon (polling + TUI)."""
    raise NotImplementedError("v0.5: implement once daemon module lands")


@app.command()
def briefing() -> None:
    """Force a briefing right now."""
    raise NotImplementedError("v0.1: first end-to-end slice")


@app.command(name="review-pr")
def review_pr(pr_number: int) -> None:
    """Have Tony review a specific PR by number."""
    raise NotImplementedError("v0.2")


@app.command()
def jira(key: str) -> None:
    """Have Nat analyze a Jira ticket by key (e.g. ABC-123)."""
    raise NotImplementedError("v0.2")


@app.command()
def doctor() -> None:
    """Diagnose configuration and connector health."""
    raise NotImplementedError("v0.1")


if __name__ == "__main__":
    app()
