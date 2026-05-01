"""Daemon runner — `foreman run`.

Single asyncio loop with two cooperating tasks:
    - poll_loop: periodically polls GitHub, queues alerts for new items
    - repl_loop: reads stdin, dispatches commands, drains alerts inline

On first run, current open PRs are silently marked as "seen" so we don't
blast notifications for the existing backlog.
"""

from __future__ import annotations

import asyncio
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from foreman.agents.aria import Aria
from foreman.agents.steve import Steve
from foreman.agents.tony import Tony
from foreman.config import Settings
from foreman.connectors.github import GitHubConnector, GitHubError, PR
from foreman.core.db import Database
from foreman.llm.client import LLMClient, LLMError
from foreman.ui.notifier import notify
from foreman.ui.theme import AGENT_COLORS, DIM

console = Console()

HELP_TEXT = """
Commands:
  briefing            Aria's morning briefing
  standup             Aria's standup notes
  review-pr <n>       Tony reviews PR #n (auto-detects repo)
  history [n]         Recent agent activity (default 10)
  help                This list
  quit / exit         Stop the daemon

Anything else is treated as a question for Steve.
""".strip()


async def run_daemon(settings: Settings) -> None:
    db = Database(settings.db_path)
    alerts: asyncio.Queue[PR] = asyncio.Queue()

    _print_banner(settings)

    poll_task = asyncio.create_task(_poll_loop(settings, db, alerts))
    try:
        await _repl_loop(settings, db, alerts)
    finally:
        poll_task.cancel()
        try:
            await poll_task
        except (asyncio.CancelledError, Exception):
            pass


# --- poll loop ----------------------------------------------------------------


async def _poll_loop(settings: Settings, db: Database, alerts: asyncio.Queue[PR]) -> None:
    poll_seconds = max(60, settings.foreman_pr_poll_minutes * 60)
    seen = db.load_seen("github_review")
    first_run = len(seen) == 0

    while True:
        try:
            async with GitHubConnector(settings) as gh:
                review = await gh.poll_review_requested()
        except GitHubError:
            await asyncio.sleep(poll_seconds)
            continue

        ids = [str(pr.number) + ":" + pr.repo for pr in review]
        if first_run:
            db.mark_seen("github_review", ids)
            seen.update(ids)
            first_run = False
        else:
            new = [pr for pr in review if (str(pr.number) + ":" + pr.repo) not in seen]
            for pr in new:
                key = str(pr.number) + ":" + pr.repo
                seen.add(key)
                db.mark_seen("github_review", [key])
                await alerts.put(pr)
                notify(
                    "PR needs your review",
                    f"#{pr.number} {pr.title[:60]} · {pr.repo}",
                )
        await asyncio.sleep(poll_seconds)


# --- repl loop ----------------------------------------------------------------


async def _repl_loop(settings: Settings, db: Database, alerts: asyncio.Queue[PR]) -> None:
    while True:
        # Drain alerts before prompting
        while not alerts.empty():
            pr = await alerts.get()
            _render_alert(pr)

        try:
            line = await asyncio.to_thread(_prompt)
        except (EOFError, KeyboardInterrupt):
            console.print()
            return

        cmd = line.strip()
        if not cmd:
            continue
        if cmd in ("quit", "exit", "q"):
            console.print(f"[{DIM}]bye.[/]")
            return
        if cmd in ("help", "?"):
            console.print(HELP_TEXT)
            continue

        await _dispatch(cmd, settings, db)


def _prompt() -> str:
    aria_color = AGENT_COLORS["aria"]
    return input(f"\n\x1b[1;38;2;16;185;129myou ›\x1b[0m ")


# --- dispatch -----------------------------------------------------------------


async def _dispatch(cmd: str, settings: Settings, db: Database) -> None:
    parts = cmd.split()
    head = parts[0].lower()

    if head == "briefing":
        await _run_briefing(settings, db)
    elif head == "standup":
        await _run_standup(settings, db)
    elif head in ("review-pr", "review_pr") and len(parts) >= 2:
        try:
            num = int(parts[1])
        except ValueError:
            console.print(f"[red]Bad PR number: {parts[1]}[/red]")
            return
        await _run_review(settings, db, num)
    elif head == "history":
        n = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
        _show_history(db, n)
    else:
        await _run_ask(settings, db, cmd)


# --- subcommand runners (slim wrappers around agents) -------------------------


async def _run_briefing(settings: Settings, db: Database) -> None:
    async with GitHubConnector(settings) as gh:
        try:
            review, mine = await asyncio.gather(
                gh.poll_review_requested(), gh.poll_my_open_prs()
            )
        except GitHubError as e:
            console.print(f"[red]GitHub error:[/red] {e}")
            return
    async with LLMClient(settings) as llm:
        try:
            text = await Aria(llm).synthesize_briefing(
                user_name=settings.github_user,
                review_prs=review,
                my_open_prs=mine,
            )
        except LLMError as e:
            console.print(f"[red]Aria failed:[/red] {e}")
            return
    _agent_panel("Aria", "BRIEFING", text, AGENT_COLORS["aria"])
    db.log_event(kind="briefing", agent="aria",
                 input_summary=f"review={len(review)} open={len(mine)}",
                 output=text, meta={"model": settings.foreman_llm_model})


async def _run_standup(settings: Settings, db: Database) -> None:
    async with GitHubConnector(settings) as gh:
        try:
            merged, review, mine = await asyncio.gather(
                gh.poll_recently_merged(hours=24),
                gh.poll_review_requested(),
                gh.poll_my_open_prs(),
            )
        except GitHubError as e:
            console.print(f"[red]GitHub error:[/red] {e}")
            return
    async with LLMClient(settings) as llm:
        try:
            text = await Aria(llm).synthesize_standup(
                user_name=settings.github_user,
                yesterday_merged=merged,
                today_review=review,
                today_open=mine,
            )
        except LLMError as e:
            console.print(f"[red]Aria failed:[/red] {e}")
            return
    _agent_panel("Aria", "STANDUP", text, AGENT_COLORS["aria"])
    db.log_event(kind="standup", agent="aria",
                 input_summary=f"merged={len(merged)} review={len(review)} open={len(mine)}",
                 output=text, meta={"model": settings.foreman_llm_model})


async def _run_review(settings: Settings, db: Database, number: int) -> None:
    async with GitHubConnector(settings) as gh:
        repo = await gh.find_pr_repo(number)
        if repo is None:
            console.print(f"[red]PR #{number} not in your queue.[/red]")
            return
        try:
            detail = await gh.get_pr_detail(repo, number)
            diff = await gh.get_pr_diff(repo, number)
        except GitHubError as e:
            console.print(f"[red]GitHub error:[/red] {e}")
            return
    console.print(f"[{DIM}]Tony reviewing {repo}#{number}...[/]")
    async with LLMClient(settings) as llm:
        try:
            text = await Tony(llm).review_pr(pr_detail=detail, diff=diff)
        except LLMError as e:
            console.print(f"[red]Tony failed:[/red] {e}")
            return
    _agent_panel("Tony", "PR REVIEW", text, AGENT_COLORS["tony"])
    db.log_event(kind="review", agent="tony",
                 input_summary=f"{repo}#{number}", output=text,
                 meta={"model": settings.foreman_llm_model})


async def _run_ask(settings: Settings, db: Database, question: str) -> None:
    async with GitHubConnector(settings) as gh:
        try:
            review, mine, merged = await asyncio.gather(
                gh.poll_review_requested(),
                gh.poll_my_open_prs(),
                gh.poll_recently_merged(hours=24),
            )
        except GitHubError as e:
            console.print(f"[red]GitHub error:[/red] {e}")
            return
    async with LLMClient(settings) as llm:
        try:
            text = await Steve(llm).ask(
                question=question, review_prs=review,
                my_open_prs=mine, recent_merged=merged,
            )
        except LLMError as e:
            console.print(f"[red]Steve failed:[/red] {e}")
            return
    _agent_panel("Steve", question[:60], text, AGENT_COLORS["steve"])
    db.log_event(kind="ask", agent="steve",
                 input_summary=question, output=text,
                 meta={"model": settings.foreman_llm_model})


# --- rendering ----------------------------------------------------------------


def _print_banner(settings: Settings) -> None:
    aria = AGENT_COLORS["aria"]
    lines = [
        f"[bold {aria}]FOREMAN[/]  [{DIM}]· always-on chief-of-staff[/]",
        "",
        f"  [{aria}]Aria[/]   morning briefings & standups",
        f"  [{AGENT_COLORS['tony']}]Tony[/]   PR reviews",
        f"  [{AGENT_COLORS['steve']}]Steve[/]  ad-hoc questions",
        "",
        f"  Polling GitHub every {settings.foreman_pr_poll_minutes} min · type [bold]help[/] for commands · [bold]quit[/] to exit",
    ]
    console.print(
        Panel(
            "\n".join(lines),
            border_style=aria,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def _render_alert(pr: PR) -> None:
    color = AGENT_COLORS["tony"]
    body = Text()
    body.append(f"#{pr.number}  ", style=f"bold {color}")
    body.append(f"{pr.title}\n", style="white")
    body.append(f"{pr.repo}  ·  by @{pr.author}", style=DIM)
    title = Text()
    title.append("PR needs your review", style=f"bold {color}")
    console.print(
        Panel(body, title=title, title_align="left",
              border_style=color, box=box.ROUNDED, padding=(0, 2))
    )


def _agent_panel(agent: str, subtitle: str, body: str, color: str) -> None:
    title = Text()
    title.append(agent, style=f"bold {color}")
    title.append("  ·  ", style=DIM)
    title.append(subtitle, style=DIM)
    console.print(
        Panel(body.strip(), title=title, title_align="left",
              border_style=color, box=box.ROUNDED, padding=(1, 2))
    )


def _show_history(db: Database, limit: int) -> None:
    rows = db.recent(limit=limit)
    if not rows:
        console.print(f"[{DIM}](no events yet)[/]")
        return
    for r in rows:
        agent = r.get("agent") or ""
        c = AGENT_COLORS.get(agent, "")
        agent_cell = f"[{c}]{agent}[/]" if c else agent
        ts = (r["ts"] or "")[:19].replace("T", " ")
        console.print(f"  [{DIM}]{ts}[/]  {r['kind']:9}  {agent_cell:18}  {(r.get('input_summary') or '')[:80]}")


def _ignore(_: Any) -> None:
    pass
