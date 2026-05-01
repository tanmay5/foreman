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
from foreman.core.db import Database
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
    narrative: str | None = None
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

    # 2b. Log to memory.
    if narrative is not None:
        Database(settings.db_path).log_event(
            kind="briefing",
            agent="aria",
            input_summary=f"review={len(review_prs)} open={len(my_prs)}",
            output=narrative,
            meta={"model": settings.foreman_llm_model},
        )

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
    """Start the always-on daemon: background GitHub polling + interactive REPL."""
    try:
        settings = load_settings()
    except Exception as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise typer.Exit(code=2)
    if settings.anthropic_api_key is None:
        console.print(f"[red]foreman run needs ANTHROPIC_API_KEY.[/red]")
        raise typer.Exit(code=2)

    from foreman.daemon.runner import run_daemon
    try:
        asyncio.run(run_daemon(settings))
    except KeyboardInterrupt:
        console.print(f"\n[{DIM}]bye.[/]")


@app.command(name="review-pr")
def review_pr(
    number: int = typer.Argument(..., help="PR number"),
    repo: str | None = typer.Option(None, "--repo", "-r", help="owner/name (auto-detected if omitted)"),
) -> None:
    """Have Tony review a specific PR. Auto-detects repo from your queue if not specified."""
    try:
        settings = load_settings()
    except Exception as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise typer.Exit(code=2)
    if settings.anthropic_api_key is None:
        console.print(f"[red]review-pr needs ANTHROPIC_API_KEY.[/red]")
        raise typer.Exit(code=2)
    asyncio.run(_review_pr(settings, number, repo))


async def _review_pr(settings: Settings, number: int, repo: str | None) -> None:
    from foreman.agents.tony import Tony
    _render_header()

    async with GitHubConnector(settings) as gh:
        if repo is None:
            repo = await gh.find_pr_repo(number)
            if repo is None:
                console.print(
                    f"[red]PR #{number} not found in your review queue or open PRs.[/red]\n"
                    f"[{DIM}]Try: foreman review-pr {number} --repo owner/name[/]"
                )
                raise typer.Exit(code=1)
        try:
            detail = await gh.get_pr_detail(repo, number)
            diff = await gh.get_pr_diff(repo, number)
        except GitHubError as e:
            console.print(f"[red]GitHub error:[/red] {e}")
            raise typer.Exit(code=1) from e

    console.print(f"[{DIM}]Tony reviewing {repo}#{number}...[/]\n")

    async with LLMClient(settings) as llm:
        try:
            text = await Tony(llm).review_pr(pr_detail=detail, diff=diff)
        except LLMError as e:
            console.print(f"[red]Tony failed:[/red] {e}")
            raise typer.Exit(code=1) from e

    color = AGENT_COLORS["tony"]
    title = Text()
    title.append("Tony", style=f"bold {color}")
    title.append("  ·  ", style=DIM)
    title.append("PR REVIEW", style=DIM)
    console.print(
        Panel(
            text.strip(),
            title=title,
            title_align="left",
            border_style=color,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    Database(settings.db_path).log_event(
        kind="review",
        agent="tony",
        input_summary=f"{repo}#{number}",
        output=text,
        meta={"model": settings.foreman_llm_model, "additions": detail.get("additions"), "deletions": detail.get("deletions")},
    )


@app.command()
def jira(key: str) -> None:
    """Have Nat analyze a Jira ticket by key."""
    console.print(f"[{DIM}]Not implemented yet (v0.3 — Nat comes online).[/]")
    raise typer.Exit(code=1)


@app.command()
def standup() -> None:
    """Auto-generate today's standup from yesterday's GitHub activity."""
    try:
        settings = load_settings()
    except Exception as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise typer.Exit(code=2)
    if settings.anthropic_api_key is None:
        console.print(f"[red]Standup needs ANTHROPIC_API_KEY.[/red] Add it to .env.")
        raise typer.Exit(code=2)
    asyncio.run(_standup(settings))


async def _standup(settings: Settings) -> None:
    _render_header()
    async with GitHubConnector(settings) as gh:
        try:
            merged, review, open_ = await asyncio.gather(
                gh.poll_recently_merged(hours=24),
                gh.poll_review_requested(),
                gh.poll_my_open_prs(),
            )
        except GitHubError as e:
            console.print(f"[red]GitHub error:[/red] {e}")
            raise typer.Exit(code=1) from e

    async with LLMClient(settings) as llm:
        aria = Aria(llm)
        try:
            text = await aria.synthesize_standup(
                user_name=settings.github_user,
                yesterday_merged=merged,
                today_review=review,
                today_open=open_,
            )
        except LLMError as e:
            console.print(f"[red]Aria failed:[/red] {e}")
            raise typer.Exit(code=1) from e

    color = AGENT_COLORS["aria"]
    title = Text()
    title.append("Aria", style=f"bold {color}")
    title.append("  ·  ", style=DIM)
    title.append("STANDUP", style=DIM)
    console.print(
        Panel(
            text.strip(),
            title=title,
            title_align="left",
            border_style=color,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    Database(settings.db_path).log_event(
        kind="standup",
        agent="aria",
        input_summary=f"merged={len(merged)} review={len(review)} open={len(open_)}",
        output=text,
        meta={"model": settings.foreman_llm_model},
    )


@app.command()
def ask(question: str = typer.Argument(..., help="Your question, in quotes")) -> None:
    """Ask Steve anything — he sees your live GitHub state."""
    try:
        settings = load_settings()
    except Exception as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise typer.Exit(code=2)
    if settings.anthropic_api_key is None:
        console.print(f"[red]ask needs ANTHROPIC_API_KEY.[/red]")
        raise typer.Exit(code=2)
    asyncio.run(_ask(settings, question))


async def _ask(settings: Settings, question: str) -> None:
    from foreman.agents.steve import Steve
    _render_header()
    async with GitHubConnector(settings) as gh:
        try:
            review, open_, merged = await asyncio.gather(
                gh.poll_review_requested(),
                gh.poll_my_open_prs(),
                gh.poll_recently_merged(hours=24),
            )
        except GitHubError as e:
            console.print(f"[red]GitHub error:[/red] {e}")
            raise typer.Exit(code=1) from e

    async with LLMClient(settings) as llm:
        try:
            text = await Steve(llm).ask(
                question=question,
                review_prs=review,
                my_open_prs=open_,
                recent_merged=merged,
            )
        except LLMError as e:
            console.print(f"[red]Steve failed:[/red] {e}")
            raise typer.Exit(code=1) from e

    color = AGENT_COLORS["steve"]
    title = Text()
    title.append("Steve", style=f"bold {color}")
    title.append("  ·  ", style=DIM)
    title.append(question[:60] + ("..." if len(question) > 60 else ""), style=DIM)
    console.print(
        Panel(
            text.strip(),
            title=title,
            title_align="left",
            border_style=color,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    Database(settings.db_path).log_event(
        kind="ask",
        agent="steve",
        input_summary=question,
        output=text,
        meta={"model": settings.foreman_llm_model},
    )


@app.command()
def history(limit: int = typer.Option(10, "--limit", "-n", help="How many recent events")) -> None:
    """Show recent agent invocations from the local memory log."""
    try:
        settings = load_settings()
    except Exception as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise typer.Exit(code=2)

    db = Database(settings.db_path)
    rows = db.recent(limit=limit)
    total = db.count()

    _render_header()
    console.print(f"\n[bold]Memory[/bold]  {total} events stored at {settings.db_path}\n")

    if not rows:
        console.print(f"[{DIM}](no events yet — run briefing/standup/review-pr/ask)[/]")
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style=f"bold {DIM}", padding=(0, 1))
    table.add_column("When", style=DIM, no_wrap=True)
    table.add_column("Kind", no_wrap=True)
    table.add_column("Agent", no_wrap=True)
    table.add_column("Summary", overflow="fold")
    for r in rows:
        agent = r.get("agent") or ""
        agent_color = AGENT_COLORS.get(agent, "")
        agent_cell = f"[{agent_color}]{agent}[/]" if agent_color else agent
        table.add_row(
            (r["ts"] or "")[:19].replace("T", " "),
            r["kind"],
            agent_cell,
            (r.get("input_summary") or "")[:80],
        )
    console.print(table)


# --- entrypoint ---------------------------------------------------------------


def main() -> None:
    """Module entry-point used by `python -m foreman` and the console script."""
    app()


if __name__ == "__main__":
    main()
