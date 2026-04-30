"""Command-line entry point for Foreman.

v0.2 surface:
    foreman briefing      # Aria synthesizes a real briefing (LLM)
    foreman doctor        # verify config + GitHub auth + Anthropic key

Other commands are stubbed and raise NotImplementedError until later
versions land them.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from foreman import __version__
from foreman.agents.aria import Aria
from foreman.config import Settings, load_settings
from foreman.connectors.github import GitHubConnector, GitHubError, PR
from foreman.llm.client import LLMClient, LLMError
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
    """Force a briefing right now. Aria synthesizes if ANTHROPIC_API_KEY is set."""
    try:
        settings = load_settings()
    except Exception as e:
        console.print(f"[red]Config error:[/red] {e}")
        console.print(f"[{DIM}]Tip: copy .env.example to .env and fill at minimum GITHUB_TOKEN + GITHUB_USER.[/]")
        raise typer.Exit(code=2)

    asyncio.run(_briefing(settings))


async def _briefing(settings: Settings) -> None:
    _render_header()

    # 1. Fetch GitHub state
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

    aria_color = AGENT_COLORS["aria"]
    tony_color = AGENT_COLORS["tony"]

    # 2. Aria synthesizes (if LLM is configured); else fall back to a templated line.
    if settings.anthropic_api_key is not None:
        try:
            async with LLMClient(settings) as llm:
                aria = Aria(llm)
                narrative = await aria.synthesize_briefing(
                    user_name=settings.github_user,
                    review_prs=review_prs,
                    my_open_prs=my_prs,
                )
            _render_aria_panel(narrative, aria_color)
        except LLMError as e:
            console.print(f"[{DIM}]Aria unavailable ({e}). Falling back to templated briefing.[/]")
            _render_templated_lead(settings, review_prs, aria_color)
    else:
        _render_templated_lead(settings, review_prs, aria_color)

    # 3. Always render the structured panels — Aria narrates, the tables back her up.
    if review_prs:
        console.print(_pr_table(f"PRs awaiting your review ({len(review_prs)})", review_prs, tony_color))
    else:
        console.print(f"[{DIM}]No PRs awaiting your review.[/{DIM}]")

    console.print()

    if my_prs:
        console.print(_pr_table(f"Your open PRs ({len(my_prs)})", my_prs, aria_color))
    else:
        console.print(f"[{DIM}]You have no open PRs.[/{DIM}]")

    console.print()


def _render_aria_panel(narrative: str, color: str) -> None:
    title = Text()
    title.append("Aria", style=f"bold {color}")
    title.append("  ·  ", style=DIM)
    title.append("BRIEFING", style=DIM)
    console.print(
        Panel(
            narrative.strip(),
            title=title,
            title_align="left",
            border_style=color,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
    console.print()


def _render_templated_lead(settings: Settings, review_prs: list[PR], color: str) -> None:
    """Fallback when Aria isn't available — keeps v0.1 behavior intact."""
    console.print(f"\n[bold]Good morning, {settings.github_user}.[/bold]\n")
    if not review_prs:
        console.print(f"[bold {color}]Nothing urgent. Good day for deep work.[/]\n")
    else:
        first = review_prs[0]
        console.print(
            f"[bold {color}]Suggested first action:[/] review PR "
            f"[bold]#{first.number}[/] in {first.repo} — {first.title}\n"
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
    console.print("\n[bold]Configuration[/bold]")
    console.print(f"  github_user      = {settings.github_user}")
    console.print(f"  github_host      = {settings.github_host}")
    console.print(f"  data_dir         = {settings.data_dir}")
    console.print(f"  llm_model        = {settings.foreman_llm_model}")
    console.print(f"  briefing_time    = {settings.foreman_briefing_time} ({settings.foreman_briefing_timezone})")
    console.print()

    console.print("[bold]Connectors[/bold]")

    # GitHub
    async with GitHubConnector(settings) as gh:
        gh_result = await gh.health_check()
    if gh_result.get("ok"):
        scopes = gh_result.get("scopes") or "(fine-grained PAT)"
        console.print(f"  [green]✓[/] github     user={gh_result.get('user')}  scopes={scopes}")
    else:
        console.print(
            f"  [red]✗[/] github     status={gh_result.get('status_code')}  "
            f"error={gh_result.get('error', '')}"
        )

    # Anthropic
    if settings.anthropic_api_key is None:
        console.print(f"  [{DIM}]· anthropic  not configured (briefing will use templated fallback)[/]")
    else:
        try:
            async with LLMClient(settings) as llm:
                # Tiny ping — cheap roundtrip just to verify the key works.
                await llm.ask(
                    system="Reply with the single word: ok",
                    user="ping",
                    max_tokens=10,
                )
            console.print(f"  [green]✓[/] anthropic  model={settings.foreman_llm_model}")
        except LLMError as e:
            console.print(f"  [red]✗[/] anthropic  {e}")

    if settings.jira_api_token is None:
        console.print(f"  [{DIM}]· jira       not configured (required from v0.3)[/]")
    if settings.slack_bot_token is None:
        console.print(f"  [{DIM}]· slack      not configured (required from v0.3)[/]")


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
    console.print(f"[{DIM}]Not implemented yet (v0.3 — Tony comes online).[/]")
    raise typer.Exit(code=1)


@app.command()
def jira(key: str) -> None:
    """Have Nat analyze a Jira ticket by key."""
    console.print(f"[{DIM}]Not implemented yet (v0.3 — Nat comes online).[/]")
    raise typer.Exit(code=1)


@app.command()
def standup() -> None:
    """Auto-generate today's standup from yesterday's activity."""
    console.print(f"[{DIM}]Not implemented yet (v0.3 — needs Jira + Slack).[/]")
    raise typer.Exit(code=1)


# --- entrypoint ---------------------------------------------------------------


def main() -> None:
    """Module entry-point used by `python -m foreman` and the console script."""
    app()


if __name__ == "__main__":
    main()
