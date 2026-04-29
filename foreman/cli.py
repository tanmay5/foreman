"""Command-line entry point for Foreman.

v0.1 surface:
    foreman briefing      # force a briefing now (GitHub-only)
    foreman doctor        # verify config + GitHub auth

Other commands are stubbed and raise NotImplementedError until later
versions land them.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from foreman import __version__
from foreman.config import Settings, load_settings
from foreman.connectors.github import GitHubConnector, GitHubError, PR
from foreman.ui.theme import AGENT_COLORS, DIM

app = typer.Typer(
    name="foreman",
    help="Personal engineering chief-of-staff. Always on.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


# --- briefing -----------------------------------------------------------------


@app.command()
def briefing() -> None:
    """Force a briefing right now (v0.1: GitHub-only)."""
    try:
        settings = load_settings()
    except Exception as e:
        console.print(f"[red]Config error:[/red] {e}")
        console.print(f"[{DIM}]Tip: copy .env.example to .env and fill at minimum GITHUB_TOKEN + GITHUB_USER.[/]")
        raise typer.Exit(code=2)

    asyncio.run(_briefing(settings))


async def _briefing(settings: Settings) -> None:
    _render_header()

    console.print(f"\n[bold]Good morning, {settings.github_user}.[/bold]\n")

    async with GitHubConnector(settings) as gh:
        try:
            review_prs, my_prs = await asyncio.gather(
                gh.poll_review_requested(),
                gh.poll_my_open_prs(),
            )
        except GitHubError as e:
            console.print(f"[red]GitHub error:[/red] {e}")
            console.print(f"[{DIM}]Run `foreman doctor` to verify your token.[/]")
            raise typer.Exit(code=1) from e

    color_tony = AGENT_COLORS["tony"]
    color_aria = AGENT_COLORS["aria"]

    if review_prs:
        console.print(_pr_table(f"PRs awaiting your review ({len(review_prs)})", review_prs, color_tony))
    else:
        console.print(f"[{DIM}]No PRs awaiting your review.[/{DIM}]")

    console.print()

    if my_prs:
        console.print(_pr_table(f"Your open PRs ({len(my_prs)})", my_prs, color_aria))
    else:
        console.print(f"[{DIM}]You have no open PRs.[/{DIM}]")

    # One-line summary at the bottom
    urgent = len(review_prs)
    console.print()
    if urgent == 0:
        console.print(f"[bold {color_aria}]Nothing urgent. Good day for deep work.[/]")
    else:
        first = review_prs[0]
        console.print(
            f"[bold {color_aria}]Suggested first action:[/] review PR "
            f"[bold]#{first.number}[/] in {first.repo} — {first.title}"
        )


def _render_header() -> None:
    title = Text()
    title.append("FOREMAN  ", style=f"bold {AGENT_COLORS['aria']}")
    title.append(f"v{__version__}", style=f"{DIM}")
    console.print(
        Panel(
            title,
            border_style=AGENT_COLORS["aria"],
            box=box.ROUNDED,
            padding=(0, 2),
        )
    )


def _pr_table(title: str, prs: list[PR], color: str) -> Table:
    table = Table(
        title=title,
        title_style=f"bold {color}",
        title_justify="left",
        show_header=True,
        header_style=f"bold {DIM}",
        box=box.SIMPLE,
        padding=(0, 1),
    )
    table.add_column("PR", style="bold", no_wrap=True)
    table.add_column("Repo", style=DIM, no_wrap=True)
    table.add_column("Title", overflow="fold")
    table.add_column("Age", style=DIM, no_wrap=True)
    table.add_column("By", style=DIM, no_wrap=True)

    for pr in prs:
        table.add_row(
            f"#{pr.number}",
            pr.repo,
            pr.title,
            _humanize_age(pr.updated_at),
            f"@{pr.author}",
        )
    return table


def _humanize_age(iso_ts: str) -> str:
    """ISO 8601 -> '3d' / '5h' / 'now'."""
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return ""
    delta = datetime.now(timezone.utc) - dt
    if delta.days >= 1:
        return f"{delta.days}d"
    hours = delta.seconds // 3600
    if hours >= 1:
        return f"{hours}h"
    return "now"


# --- doctor -------------------------------------------------------------------


@app.command()
def doctor() -> None:
    """Diagnose configuration and connector health."""
    try:
        settings = load_settings()
    except Exception as e:
        console.print(f"[red]Config error:[/red] {e}")
        console.print(f"[{DIM}]Copy .env.example to .env and fill at minimum GITHUB_TOKEN + GITHUB_USER.[/]")
        raise typer.Exit(code=2)

    asyncio.run(_doctor(settings))


async def _doctor(settings: Settings) -> None:
    _render_header()
    console.print(f"\n[bold]Configuration[/bold]")
    console.print(f"  github_user      = {settings.github_user}")
    console.print(f"  github_host      = {settings.github_host}")
    console.print(f"  data_dir         = {settings.data_dir}")
    console.print(f"  llm_model        = {settings.foreman_llm_model}")
    console.print(f"  briefing_time    = {settings.foreman_briefing_time} ({settings.foreman_briefing_timezone})")
    console.print()

    console.print("[bold]Connectors[/bold]")
    async with GitHubConnector(settings) as gh:
        result = await gh.health_check()
    if result.get("ok"):
        scopes = result.get("scopes") or "(fine-grained PAT)"
        console.print(f"  [green]✓[/] github  user={result.get('user')}  scopes={scopes}")
    else:
        console.print(f"  [red]✗[/] github  status={result.get('status_code')}  error={result.get('error', '')}")
        console.print(f"  [{DIM}]Verify GITHUB_TOKEN is valid and has repo + pull-request read scopes.[/]")

    if settings.anthropic_api_key is None:
        console.print(f"  [{DIM}]· anthropic   not configured (required from v0.2)[/]")
    else:
        console.print(f"  [green]✓[/] anthropic key configured")

    if settings.jira_api_token is None:
        console.print(f"  [{DIM}]· jira        not configured (required from v0.2)[/]")
    if settings.slack_bot_token is None:
        console.print(f"  [{DIM}]· slack       not configured (required from v0.3)[/]")


# --- stubs (later versions) ---------------------------------------------------


@app.command()
def init() -> None:
    """Interactive first-run setup."""
    console.print(f"[{DIM}]Not implemented yet (v0.5). For now: copy .env.example -> .env and edit.[/]")
    raise typer.Exit(code=1)


@app.command()
def run() -> None:
    """Start the foreman daemon (polling + TUI)."""
    console.print(f"[{DIM}]Not implemented yet (v0.5). For now: run `foreman briefing`.[/]")
    raise typer.Exit(code=1)


@app.command(name="review-pr")
def review_pr(pr_number: int) -> None:
    """Have Tony review a specific PR by number."""
    console.print(f"[{DIM}]Not implemented yet (v0.2).[/]")
    raise typer.Exit(code=1)


@app.command()
def jira(key: str) -> None:
    """Have Nat analyze a Jira ticket by key."""
    console.print(f"[{DIM}]Not implemented yet (v0.2).[/]")
    raise typer.Exit(code=1)


# --- entrypoint ---------------------------------------------------------------


def main() -> None:
    """Module entry-point used by `python -m foreman` and the console script."""
    app()


if __name__ == "__main__":
    main()
