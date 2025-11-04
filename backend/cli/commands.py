"""CLI commands for AI Session Recorder."""

import os
import sys
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table

from backend.database.models import get_session, AIInteraction, ProjectMilestone, NextStep
from backend.services.git_monitor import GitMonitor
from backend.services.ai_tracker import AITracker
from backend.services.claude_provider import ClaudeProviderSwitcher
from backend.core.config import Config
from backend.cli.formatters import (
    format_commits_list,
    format_today_summary,
    format_search_results,
    format_repo_stats,
    format_ai_interactions_list,
    format_ai_stats,
    format_combined_session,
)

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Chronicle - Track your development sessions across AI tools and git commits."""
    pass


@cli.command()
def init():
    """Initialize Chronicle."""
    # Create config directory
    home = Path.home()
    config_dir = home / ".ai-session"
    config_dir.mkdir(exist_ok=True)

    # Initialize database
    db_session = get_session()
    db_session.close()

    console.print("[green]✓[/green] Chronicle initialized!")
    console.print(f"[dim]Config directory: {config_dir}[/dim]")
    console.print(f"[dim]Database: {config_dir / 'sessions.db'}[/dim]")
    console.print("\nNext steps:")
    console.print("  1. Configure API key: [cyan]chronicle setup[/cyan]")
    console.print("  2. Add a repository: [cyan]chronicle add-repo /path/to/repo[/cyan]")
    console.print("  3. View today's activity: [cyan]chronicle show today[/cyan]")


@cli.command()
def setup():
    """Interactive setup wizard for Chronicle configuration."""
    console.print("[bold cyan]Chronicle Setup Wizard[/bold cyan]\n")

    config = Config()

    # Check if already configured
    existing_key = config.get("ai.gemini_api_key")
    if existing_key:
        console.print(f"[yellow]⚠[/yellow]  Gemini API key already configured: {existing_key[:8]}...{existing_key[-4:]}")
        if not click.confirm("Do you want to update it?", default=False):
            console.print("[green]✓[/green] Setup cancelled. Configuration unchanged.")
            return

    # Prompt for API key
    console.print("\n[bold]Gemini API Key Setup[/bold]")
    console.print("Chronicle uses Google's Gemini API for AI summarization.")
    console.print("\nTo get a free API key:")
    console.print("  1. Visit: [cyan]https://aistudio.google.com/app/apikey[/cyan]")
    console.print("  2. Sign in with Google")
    console.print("  3. Click 'Create API Key'")
    console.print("  4. Copy the key (starts with 'AIza...')\n")

    api_key = click.prompt(
        "Enter your Gemini API key",
        type=str,
        hide_input=True,
        confirmation_prompt="Confirm API key"
    )

    if not api_key or len(api_key) < 20:
        console.print("[red]✗[/red] Invalid API key. Setup cancelled.")
        return

    # Save API key
    config.set("ai.gemini_api_key", api_key)
    console.print(f"\n[green]✓[/green] API key saved: {api_key[:8]}...{api_key[-4:]}")

    # Optional: Set default model
    console.print("\n[bold]Summarization Model[/bold]")
    console.print(f"Current model: [cyan]{config.get('ai.default_model')}[/cyan]")

    if click.confirm("Use default model (gemini-2.0-flash)?", default=True):
        console.print("[green]✓[/green] Using default model")
    else:
        custom_model = click.prompt("Enter model name", default="gemini-2.0-flash")
        config.set("ai.default_model", custom_model)
        console.print(f"[green]✓[/green] Model set to: {custom_model}")

    # Summary
    console.print("\n[bold green]Setup Complete![/bold green]")
    console.print("\nNext steps:")
    console.print("  1. Add a repository: [cyan]chronicle add-repo /path/to/repo[/cyan]")
    console.print("  2. Start tracking: [cyan]chronicle start claude[/cyan]")
    console.print("  3. View configuration: [cyan]chronicle config --list[/cyan]")


@cli.command()
@click.option('--check-only', is_flag=True, help='Check for updates without installing')
def update(check_only: bool):
    """Check for and install Chronicle updates."""
    console.print("[bold cyan]Chronicle Update Check[/bold cyan]\n")

    # Find Chronicle installation directory
    try:
        import backend
        chronicle_path = Path(backend.__file__).parent.parent
    except Exception:
        console.print("[red]✗[/red] Could not locate Chronicle installation")
        return

    # Check if it's a git repository
    if not (chronicle_path / ".git").exists():
        console.print("[yellow]⚠[/yellow]  Chronicle is not installed from git")
        console.print("This command only works for git-based installations (pip install -e .)")
        console.print("\nTo update, reinstall from PyPI: [cyan]pip install --upgrade chronicle[/cyan]")
        return

    # Check for updates
    try:
        # Fetch latest from remote
        console.print("Checking for updates...")
        result = subprocess.run(
            ["git", "fetch", "origin"],
            cwd=chronicle_path,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            console.print(f"[red]✗[/red] Failed to fetch updates: {result.stderr}")
            return

        # Get current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=chronicle_path,
            capture_output=True,
            text=True
        )
        current_branch = result.stdout.strip()

        # Check if behind remote
        result = subprocess.run(
            ["git", "rev-list", "--count", f"HEAD..origin/{current_branch}"],
            cwd=chronicle_path,
            capture_output=True,
            text=True
        )
        commits_behind = int(result.stdout.strip())

        if commits_behind == 0:
            console.print("[green]✓[/green] Chronicle is up to date!")
            return

        # Show what's new
        console.print(f"[yellow]⚠[/yellow]  Updates available: {commits_behind} new commit(s)\n")

        result = subprocess.run(
            ["git", "log", "--oneline", f"HEAD..origin/{current_branch}"],
            cwd=chronicle_path,
            capture_output=True,
            text=True
        )

        console.print("[bold]What's new:[/bold]")
        for line in result.stdout.strip().split('\n'):
            console.print(f"  • {line}")

        if check_only:
            console.print("\n[dim]Run [cyan]chronicle update[/cyan] to install updates[/dim]")
            return

        # Confirm update
        console.print("")
        if not click.confirm("Install updates now?", default=True):
            console.print("[yellow]Update cancelled[/yellow]")
            return

        # Pull updates
        console.print("\nPulling updates...")
        result = subprocess.run(
            ["git", "pull", "origin", current_branch],
            cwd=chronicle_path,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            console.print(f"[red]✗[/red] Failed to pull updates: {result.stderr}")
            return

        console.print("[green]✓[/green] Updates downloaded")

        # Check if dependencies changed
        result = subprocess.run(
            ["git", "diff", "HEAD@{1}", "HEAD", "pyproject.toml"],
            cwd=chronicle_path,
            capture_output=True,
            text=True
        )

        if result.stdout.strip():
            console.print("\n[yellow]⚠[/yellow]  Dependencies changed, reinstalling...")

            # Detect current install mode (check if fastmcp is installed)
            try:
                import fastmcp
                install_cmd = [sys.executable, "-m", "pip", "install", "-e", ".[mcp]"]
                console.print("[dim]Reinstalling with MCP support...[/dim]")
            except ImportError:
                install_cmd = [sys.executable, "-m", "pip", "install", "-e", "."]
                console.print("[dim]Reinstalling (minimal)...[/dim]")

            result = subprocess.run(
                install_cmd,
                cwd=chronicle_path,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                console.print(f"[red]✗[/red] Reinstall failed: {result.stderr}")
                console.print("\nPlease reinstall manually:")
                console.print(f"  cd {chronicle_path}")
                console.print(f"  {sys.executable} -m pip install -e .[mcp]  # or: -e .")
                return

            console.print("[green]✓[/green] Dependencies reinstalled")

        # Success
        console.print("\n[bold green]Update Complete![/bold green]")
        console.print("Chronicle is now up to date")

    except subprocess.TimeoutExpired:
        console.print("[red]✗[/red] Update check timed out")
    except Exception as e:
        console.print(f"[red]✗[/red] Update failed: {e}")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.option('--limit', default=50, help='Number of recent commits to import')
def add_repo(repo_path: str, limit: int):
    """Add a git repository to track."""
    db_session = get_session()
    monitor = GitMonitor(db_session)

    try:
        console.print(f"Scanning repository: {repo_path}")
        commits = monitor.scan_repo(repo_path, limit=limit)
        console.print(f"[green]✓[/green] Added {len(commits)} commits from {repo_path}")

        if commits:
            latest = commits[0]
            console.print(f"[dim]Latest commit: {latest.sha[:8]} - {latest.message.split(chr(10))[0][:60]}[/dim]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        db_session.close()
        raise click.Abort()

    db_session.close()


@cli.command()
@click.argument('action', type=click.Choice(['today', 'yesterday', 'week']))
@click.option('--repo', help='Filter by repository path (defaults to current directory)')
@click.option('--all', 'show_all', is_flag=True, help='Show commits from all repositories')
def show(action: str, repo: str = None, show_all: bool = False):
    """Show development activity.

    By default, shows commits from the current repository only.

    Examples:
        chronicle show today                # Current repo, today
        chronicle show week --all           # All repos, last 7 days
        chronicle show today --repo /path   # Specific repo
    """
    db_session = get_session()
    monitor = GitMonitor(db_session)

    # Auto-detect repo from current working directory
    if repo is None and not show_all:
        repo = os.getcwd()

    if action == 'today':
        commits = monitor.get_commits_today(repo_path=repo)
        format_today_summary(commits)

    elif action == 'yesterday':
        yesterday_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        yesterday_end = yesterday_start + timedelta(days=1)
        commits = monitor.get_commits_by_date(yesterday_start, yesterday_end, repo_path=repo)
        format_commits_list(commits, title=f"Commits from Yesterday ({yesterday_start.strftime('%B %d, %Y')})")

    elif action == 'week':
        week_start = datetime.now() - timedelta(days=7)
        commits = monitor.get_commits_by_date(week_start, repo_path=repo)
        format_commits_list(commits, title="Commits from Last 7 Days")

    db_session.close()


@cli.command()
@click.argument('search_term')
def search(search_term: str):
    """Search commits by message content."""
    db_session = get_session()
    monitor = GitMonitor(db_session)

    commits = monitor.search_commits(search_term)
    format_search_results(commits, search_term)

    db_session.close()


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
def stats(repo_path: str):
    """Show statistics for a repository."""
    db_session = get_session()
    monitor = GitMonitor(db_session)

    repo_stats = monitor.get_repo_stats(repo_path)
    format_repo_stats(repo_stats)

    db_session.close()


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.option('--limit', default=50, help='Number of recent commits to scan')
def sync(repo_path: str, limit: int):
    """Sync a repository to capture new commits."""
    db_session = get_session()
    monitor = GitMonitor(db_session)

    try:
        commits = monitor.scan_repo(repo_path, limit=limit)
        if commits:
            console.print(f"[green]✓[/green] Synced {len(commits)} new commits from {repo_path}")
        else:
            console.print("[dim]No new commits found.[/dim]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        db_session.close()
        raise click.Abort()

    db_session.close()


if __name__ == '__main__':
    cli()


@cli.command()
@click.argument('action', type=click.Choice(['today', 'yesterday', 'week']))
@click.option('--tool', help='Filter by AI tool (gemini, qwen, claude)')
def ai(action: str, tool: str = None):
    """Show AI interaction history."""
    db_session = get_session()
    tracker = AITracker(db_session)

    # Normalize tool name
    if tool:
        tool = f"{tool}-cli"

    if action == 'today':
        interactions = tracker.get_interactions_today(ai_tool=tool)
        format_ai_interactions_list(interactions, title="AI Interactions Today")

    elif action == 'yesterday':
        yesterday_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        yesterday_end = yesterday_start + timedelta(days=1)
        interactions = tracker.get_interactions_by_date(yesterday_start, yesterday_end, ai_tool=tool)
        format_ai_interactions_list(interactions, title=f"AI Interactions from Yesterday ({yesterday_start.strftime('%B %d, %Y')})")

    elif action == 'week':
        week_start = datetime.now() - timedelta(days=7)
        interactions = tracker.get_interactions_by_date(week_start, ai_tool=tool)
        format_ai_interactions_list(interactions, title="AI Interactions from Last 7 Days")

    db_session.close()


@cli.command()
@click.option('--days', default=30, help='Number of days to analyze (default: 30)')
def ai_stats(days: int):
    """Show AI tool usage statistics."""
    db_session = get_session()
    tracker = AITracker(db_session)

    stats = tracker.get_ai_tool_stats(days=days)
    format_ai_stats(stats, days=days)

    db_session.close()


@cli.command()
def gemini_stats():
    """Show Gemini model usage statistics (today's quota)."""
    from backend.services.summarizer import Summarizer
    from backend.cli.formatters import format_gemini_usage_stats

    try:
        summarizer = Summarizer()
        stats = summarizer.get_usage_stats()
        format_gemini_usage_stats(stats)
    except Exception as e:
        console.print(f"[red]✗[/red] Error fetching Gemini stats: {e}")
        import traceback
        traceback.print_exc()


@cli.command()
@click.argument('session_id', type=int)
def session(session_id: int):
    """View a session with auto-generated summary.

    This command displays a session's details. If the session hasn't been
    summarized yet, it will automatically generate a summary using Gemini.

    Examples:
        chronicle session 5      # View session #5
        chronicle sessions       # List all sessions first
    """
    from backend.services.summarizer import Summarizer
    from backend.cli.formatters import format_session_detail

    db_session = get_session()

    # Get the session
    interaction = db_session.query(AIInteraction).filter_by(id=session_id).first()

    if not interaction:
        console.print(f"[red]Error:[/red] Session {session_id} not found")
        db_session.close()
        raise click.Abort()

    if not interaction.is_session:
        console.print(f"[yellow]Warning:[/yellow] Interaction {session_id} is not a full session")
        console.print("[dim]Showing details anyway...[/dim]\n")

    # Check if we need to generate a summary
    if interaction.is_session and not interaction.summary_generated:
        console.print(f"[cyan]Generating summary for session {session_id}...[/cyan]")
        console.print(f"[dim]Using chunked summarization (handles sessions of any size)[/dim]\n")

        try:
            summarizer = Summarizer()

            # Use chunked summarization (works for all session sizes)
            # Chunk size is automatically optimized based on session size:
            # - Small (<10K lines): 3K chunks → uses Flash-Preview 2.5
            # - Medium (10-50K lines): 5K chunks → uses Flash-Preview 2.5
            # - Large (>50K lines): 10K chunks → uses Flash 2.0 (1M TPM)
            summary = summarizer.summarize_session_chunked(
                session_id=session_id,
                db_session=db_session,
                use_cli=False  # Use Gemini API (reliable, free tier)
            )

            console.print("[green]✓[/green] Summary generated!\n")

        except ValueError as e:
            console.print(f"[yellow]Warning:[/yellow] {e}")
            console.print("[dim]Showing session without summary...[/dim]\n")
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Failed to generate summary: {e}")
            console.print("[dim]Showing session without summary...[/dim]\n")

    # Display the session
    format_session_detail(interaction)

    db_session.close()


@cli.command()
@click.argument('action', type=click.Choice(['today', 'week']))
@click.option('--repo', help='Filter by repository path')
def summarize(action: str, repo: str = None):
    """Generate AI-powered summaries of your development activity.

    This command uses Gemini to analyze your commits and AI sessions
    and generate concise summaries of what you accomplished.

    Examples:
        chronicle summarize today                    # Summarize today's work
        chronicle summarize week                     # Summarize last 7 days
        chronicle summarize today --repo /path/repo  # Today's work on specific repo
    """
    from backend.services.summarizer import Summarizer

    db_session = get_session()
    monitor = GitMonitor(db_session)
    tracker = AITracker(db_session)

    # Get data based on timeframe
    if action == 'today':
        commits = monitor.get_commits_today(repo_path=repo)
        interactions = tracker.get_interactions_today(repo_path=repo)
        title = f"Summary for {datetime.now().strftime('%B %d, %Y')}"
        if repo:
            from pathlib import Path
            repo_name = Path(repo).name
            title += f" - {repo_name}"

    elif action == 'week':
        week_start = datetime.now() - timedelta(days=7)
        commits = monitor.get_commits_by_date(week_start, repo_path=repo)
        interactions = tracker.get_interactions_by_date(week_start, repo_path=repo)
        title = "Summary for Last 7 Days"
        if repo:
            from pathlib import Path
            repo_name = Path(repo).name
            title += f" - {repo_name}"

    # Check if we have any data
    if not commits and not interactions:
        console.print(f"[yellow]No activity found for {action}[/yellow]")
        db_session.close()
        return

    # Build context for summarization
    commit_messages = [f"{c.message}" for c in commits]
    interaction_prompts = [f"{i.prompt}" for i in interactions if i.prompt]

    console.print(f"[dim]Generating summary for {len(commits)} commits and {len(interactions)} AI interactions...[/dim]\n")

    try:
        summarizer = Summarizer()
        summary = summarizer.summarize_day(commit_messages, interaction_prompts)

        # Display the summary
        console.print(f"[bold cyan]{title}[/bold cyan]")
        console.print("═" * 60)
        console.print()
        console.print(summary)
        console.print()
        console.print("═" * 60)
        console.print(f"[dim]Based on {len(commits)} commits and {len(interactions)} AI interactions[/dim]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("[dim]Make sure you've configured your Gemini API key:[/dim]")
        console.print("[dim]  chronicle config ai.gemini_api_key YOUR_KEY[/dim]")
    except Exception as e:
        console.print(f"[red]Error generating summary:[/red] {e}")

    db_session.close()


@cli.command()
@click.argument('action', type=click.Choice(['today', 'yesterday', 'week']))
@click.option('--repo', help='Filter by repository path (defaults to current directory)')
@click.option('--all', 'show_all', is_flag=True, help='Show timeline from all repositories')
def timeline(action: str, repo: str = None, show_all: bool = False):
    """Show combined timeline of commits and AI interactions.

    By default, shows timeline from the current repository only.

    Examples:
        chronicle timeline today            # Current repo, today
        chronicle timeline week --all       # All repos, last 7 days
        chronicle timeline today --repo /path  # Specific repo
    """
    db_session = get_session()
    monitor = GitMonitor(db_session)
    tracker = AITracker(db_session)

    # Auto-detect repo from current working directory
    if repo is None and not show_all:
        repo = os.getcwd()

    if action == 'today':
        commits = monitor.get_commits_today(repo_path=repo)
        interactions = tracker.get_interactions_today(repo_path=repo)

    elif action == 'yesterday':
        yesterday_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        yesterday_end = yesterday_start + timedelta(days=1)
        commits = monitor.get_commits_by_date(yesterday_start, yesterday_end, repo_path=repo)
        interactions = tracker.get_interactions_by_date(yesterday_start, yesterday_end, repo_path=repo)

    elif action == 'week':
        week_start = datetime.now() - timedelta(days=7)
        commits = monitor.get_commits_by_date(week_start, repo_path=repo)
        interactions = tracker.get_interactions_by_date(week_start, repo_path=repo)

    format_combined_session(commits, interactions)

    db_session.close()


@cli.command()
@click.argument('prompt')
@click.option('--tool', required=True, type=click.Choice(['gemini']), help='AI tool to use')
@click.option('--log-only', is_flag=True, help='Only log, don\'t execute (for testing)')
def ask(prompt: str, tool: str, log_only: bool):
    """Ask Gemini a question via CLI (wrapper for convenience).

    Note: For summarization, use 'chronicle session <id>' instead.
    """
    import subprocess

    db_session = get_session()
    tracker = AITracker(db_session)

    if log_only:
        # Just log without executing
        tracker.log_interaction(
            ai_tool=f"{tool}-cli",
            prompt=prompt,
            response="[Test mode - not executed]",
            duration_ms=0
        )
        console.print(f"[green]✓[/green] Logged test interaction for {tool}")
    else:
        # Use the wrapper script
        wrapper_path = Path(__file__).parent.parent.parent / "scripts" / "chronicle-ai"
        if not wrapper_path.exists():
            console.print(f"[red]Error:[/red] Wrapper script not found at {wrapper_path}")
            console.print("Please ensure scripts/chronicle-ai is installed.")
            db_session.close()
            raise click.Abort()

        try:
            subprocess.run([str(wrapper_path), tool, prompt], check=True)
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error:[/red] AI tool failed with exit code {e.returncode}")
            db_session.close()
            raise click.Abort()

    db_session.close()


@cli.command()
@click.argument('tool', type=click.Choice(['claude', 'gemini', 'qwen', 'droid', 'vim', 'other']))
@click.option('--command', help='Custom command to run (overrides tool name)')
def start(tool: str, command: str = None):
    """Start an interactive session with a tool.

    This launches the tool and records all activity in a session.
    When you exit the tool, Chronicle saves the full transcript.

    Examples:
        chronicle start claude      # Claude Code
        chronicle start gemini      # Gemini CLI
        chronicle start qwen        # Qwen Code
        chronicle start droid       # Droid
        chronicle start vim         # Vim editor
        chronicle start other --command "python -i"
    """
    from backend.services.session_manager import SessionManager

    db_session = get_session()
    manager = SessionManager(db_session)

    # Map tool names to actual commands
    tool_commands = {
        'claude': 'claude',
        'gemini': 'gemini',
        'qwen': 'qwen',
        'droid': 'droid',
        'vim': 'vim',
        'other': command or 'bash'
    }
    
    actual_command = command if command else tool_commands.get(tool)
    
    if not actual_command:
        console.print(f"[red]Error:[/red] No command specified for '{tool}'")
        console.print("Use --command to specify a custom command")
        db_session.close()
        raise click.Abort()
    
    try:
        session_id = manager.start_session(tool, actual_command)
    except KeyboardInterrupt:
        console.print("\n[yellow]Session interrupted[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        import traceback
        traceback.print_exc()
    
    db_session.close()


@cli.command()
@click.option('--repo', help='Filter by repository path (defaults to current directory)')
@click.option('--all', 'show_all', is_flag=True, help='Show sessions from all repositories')
@click.option('--limit', default=10, help='Number of sessions to show (default: 10)')
def sessions(repo: str = None, show_all: bool = False, limit: int = 10):
    """List recent sessions.

    By default, shows sessions from the current repository only.

    Examples:
        chronicle sessions                          # Current repo sessions
        chronicle sessions --all                    # All repos
        chronicle sessions --limit 20               # Current repo, last 20
        chronicle sessions --repo /path/to/project  # Specific repo
    """
    db_session = get_session()

    # Auto-detect repo from current working directory
    if repo is None and not show_all:
        repo = os.getcwd()

    # Get recent sessions (last N)
    from backend.services.ai_tracker import AITracker
    tracker = AITracker(db_session)

    query = db_session.query(AIInteraction).filter_by(is_session=1)

    # Filter by repo if specified (use LIKE for partial matching)
    if repo:
        query = query.filter(AIInteraction.repo_path.like(f"%{repo}%"))

    interactions = query.order_by(
        AIInteraction.timestamp.desc()
    ).limit(limit).all()
    
    if not interactions:
        if repo and not show_all:
            console.print(f"[yellow]No sessions found for repository: {repo}[/yellow]")
            console.print("\nTip: Use [cyan]--all[/cyan] to see sessions from all repositories")
        else:
            console.print("[yellow]No sessions recorded yet.[/yellow]")
            console.print("\nStart a session with: [cyan]chronicle start claude[/cyan]")
        db_session.close()
        return

    # Show which repo is being filtered
    console.print("\n[bold cyan]Recent Sessions[/bold cyan]")
    if show_all:
        console.print("[dim]Showing: All repositories[/dim]")
    elif repo:
        repo_name = Path(repo).name
        console.print(f"[dim]Showing: {repo_name} ({repo})[/dim]")
    console.print("═" * 80)
    
    from rich.table import Table
    table = Table(show_header=True, header_style="bold cyan", show_lines=False)
    table.add_column("ID", width=6)
    table.add_column("Title / Tool", width=35)
    table.add_column("Started", width=16)
    table.add_column("Duration", width=10)
    table.add_column("Tags", width=20)

    for session in interactions:
        session_id = str(session.id)
        tool = session.ai_tool.replace("-session", "").title()
        timestamp = session.timestamp.strftime("%b %d, %I:%M %p")

        # Title (or fallback to tool)
        if session.title:
            title_display = f"[bold]{session.title}[/bold]\n[dim]{tool}[/dim]"
        else:
            title_display = f"[dim]Session {session.id}[/dim]\n{tool}"

        # Duration
        if session.duration_ms:
            duration_min = session.duration_ms / 1000 / 60
            duration = f"{duration_min:.1f}m"
        else:
            duration = "Active"

        # Tags
        tags_list = session.tags_list if session.tags else []
        if tags_list:
            # Show first 3 tags
            tags_display = ", ".join(tags_list[:3])
            if len(tags_list) > 3:
                tags_display += f" +{len(tags_list)-3}"
        else:
            tags_display = "[dim]-[/dim]"

        table.add_row(session_id, title_display, timestamp, duration, tags_display)
    
    console.print(table)
    console.print(f"\n[dim]Use 'chronicle session <id>' to view full details[/dim]")

    db_session.close()


@cli.command(name='search-sessions')
@click.argument('query')
@click.option('--repo', help='Filter by repository path (defaults to current directory)')
@click.option('--all', 'show_all', is_flag=True, help='Search sessions from all repositories')
@click.option('--limit', default=10, help='Number of results to show (default: 10, max: 50)')
@click.option('--summaries-only', is_flag=True, help='Search only in AI-generated summaries')
@click.option('--prompts-only', is_flag=True, help='Search only in session prompts')
@click.option('--keywords-only', is_flag=True, help='Search only in AI-extracted keywords')
def search_sessions(query: str, repo: str = None, show_all: bool = False, limit: int = 10,
                    summaries_only: bool = False, prompts_only: bool = False, keywords_only: bool = False):
    """Search Chronicle sessions using FTS5 full-text search.

    Multi-word searches work intelligently with boolean operators:

    \b
    Basic searches:
        chronicle search-sessions "gemini model fallback"    # Any word (broader results)
        chronicle search-sessions "authentication"           # Single word

    \b
    Boolean operators:
        chronicle search-sessions "gemini AND model"         # Both words required
        chronicle search-sessions "gemini OR claude"         # Either word
        chronicle search-sessions "testing NOT deprecated"   # Exclude word
        chronicle search-sessions '"data corruption"'        # Exact phrase (use quotes)

    \b
    Examples:
        chronicle search-sessions "authentication"               # Current repo
        chronicle search-sessions "authentication" --all         # All repos
        chronicle search-sessions "gemini OR claude" --limit 20  # More results
        chronicle search-sessions "api" --summaries-only         # Search summaries only
    """
    from sqlalchemy import text
    from sqlalchemy.orm import defer

    limit = min(limit, 50)  # Cap at 50

    db_session = get_session()

    # Auto-detect repo from current working directory
    if repo is None and not show_all:
        repo = os.getcwd()

    # Build FTS5 column list based on flags
    fts_columns = []
    if summaries_only:
        fts_columns = ['response_summary']
    elif prompts_only:
        fts_columns = ['prompt']
    elif keywords_only:
        fts_columns = ['keywords']
    else:
        # Default: search all fields
        fts_columns = ['response_summary', 'prompt', 'keywords']

    # Build FTS5 query with OR by default (more user-friendly, broader results)
    # Users can use explicit AND or quotes for precise matching

    # Split query into tokens and OR them (unless already using operators)
    if " OR " in query or " AND " in query or " NOT " in query or '"' in query:
        # User is using explicit operators - pass through as-is
        base_query = query
    else:
        # Split on whitespace and OR the tokens for broader results
        tokens = query.split()
        if len(tokens) > 1:
            base_query = " OR ".join(tokens)
        else:
            base_query = query

    if len(fts_columns) == 3:
        # All columns - search across all columns
        fts_query = base_query
    elif len(fts_columns) == 1:
        # Single column
        fts_query = f"{{{fts_columns[0]}}}: {base_query}"
    else:
        # Multiple columns
        fts_query = " OR ".join(f"{{{col}}}: {base_query}" for col in fts_columns)

    try:
        # Use FTS5 MATCH query with raw SQL
        # SQLAlchemy doesn't have great FTS5 support, so we execute raw SQL
        sql = text("""
            SELECT ai_interactions.*
            FROM ai_interactions
            JOIN sessions_fts ON sessions_fts.rowid = ai_interactions.id
            WHERE sessions_fts MATCH :fts_query
        """)

        if repo:
            sql = text("""
                SELECT ai_interactions.*
                FROM ai_interactions
                JOIN sessions_fts ON sessions_fts.rowid = ai_interactions.id
                WHERE sessions_fts MATCH :fts_query
                  AND ai_interactions.repo_path LIKE :repo_filter
                ORDER BY bm25(sessions_fts) ASC
                LIMIT :limit_val
            """)
            result = db_session.execute(
                sql,
                {"fts_query": fts_query, "repo_filter": f"%{repo}%", "limit_val": limit}
            )
        else:
            sql = text("""
                SELECT ai_interactions.*
                FROM ai_interactions
                JOIN sessions_fts ON sessions_fts.rowid = ai_interactions.id
                WHERE sessions_fts MATCH :fts_query
                ORDER BY bm25(sessions_fts) ASC
                LIMIT :limit_val
            """)
            result = db_session.execute(
                sql,
                {"fts_query": fts_query, "limit_val": limit}
            )

        # Fetch all session IDs from FTS results
        session_ids = [row[0] for row in result.fetchall()]

        # Load full session objects
        if session_ids:
            sessions = db_session.query(AIInteraction).filter(
                AIInteraction.id.in_(session_ids)
            ).all()
            # Sort by original FTS ranking order
            id_order = {id: i for i, id in enumerate(session_ids)}
            sessions = sorted(sessions, key=lambda s: id_order.get(s.id, 999))
        else:
            sessions = []

    except Exception as e:
        # Fallback to old LIKE-based search if FTS5 fails
        console.print(f"[yellow]FTS5 search unavailable, using basic search[/yellow]")
        console.print(f"[dim]Error: {e}[/dim]\n")

        from sqlalchemy import or_

        filters = []
        if 'response_summary' in fts_columns:
            filters.append(AIInteraction.response_summary.like(f"%{query}%"))
        if 'prompt' in fts_columns:
            filters.append(AIInteraction.prompt.like(f"%{query}%"))
        if 'keywords' in fts_columns:
            filters.append(AIInteraction.keywords.like(f"%{query}%"))

        sessions_query = db_session.query(AIInteraction).options(
            defer(AIInteraction.session_transcript)
        ).filter(
            AIInteraction.is_session == 1,
            or_(*filters)
        )

        if repo:
            sessions_query = sessions_query.filter(AIInteraction.repo_path.like(f"%{repo}%"))

        sessions = sessions_query.order_by(AIInteraction.timestamp.desc()).limit(limit).all()

    if not sessions:
        console.print(f"[yellow]No sessions found matching: {query}[/yellow]\n")
        if not show_all:
            console.print("Tip: Use [cyan]--all[/cyan] to search all repositories")
        console.print("\nTry:")
        console.print("  • Using different keywords")
        console.print("  • Using OR operator: [cyan]chronicle search-sessions \"gemini OR claude\"[/cyan]")
        console.print("  • Excluding terms: [cyan]chronicle search-sessions \"testing NOT deprecated\"[/cyan]")
        db_session.close()
        return

    # Show search info
    console.print(f"\n[bold cyan]Search Results: '{query}'[/bold cyan]")
    if show_all:
        console.print("[dim]Searching: All repositories[/dim]")
    elif repo:
        repo_name = Path(repo).name
        console.print(f"[dim]Searching: {repo_name} ({repo})[/dim]")
    console.print(f"[dim]Found: {len(sessions)} session(s)[/dim]")
    console.print("═" * 80)

    # Display results in table
    from rich.table import Table
    table = Table(show_header=True, header_style="bold cyan", show_lines=False)
    table.add_column("ID", width=6)
    table.add_column("Title / Tool", width=35)
    table.add_column("Started", width=16)
    table.add_column("Duration", width=10)
    table.add_column("Tags", width=20)

    for session in sessions:
        session_id = str(session.id)
        tool = session.ai_tool.replace("-session", "").title()
        timestamp = session.timestamp.strftime("%b %d, %I:%M %p")

        # Title (or fallback to tool)
        if session.title:
            title_display = f"[bold]{session.title}[/bold]\n[dim]{tool}[/dim]"
        else:
            title_display = f"[dim]Session {session.id}[/dim]\n{tool}"

        # Duration
        if session.duration_ms:
            duration_min = session.duration_ms / 1000 / 60
            duration = f"{duration_min:.1f}m"
        else:
            duration = "Active"

        # Tags
        tags_list = session.tags_list if session.tags else []
        if tags_list:
            # Show first 3 tags
            tags_display = ", ".join(tags_list[:3])
            if len(tags_list) > 3:
                tags_display += f" +{len(tags_list)-3}"
        else:
            tags_display = "[dim]-[/dim]"

        table.add_row(session_id, title_display, timestamp, duration, tags_display)

    console.print(table)
    console.print(f"\n[dim]Use 'chronicle session <id>' to view full details[/dim]")
    console.print(f"[dim]Results ranked by relevance (BM25 algorithm)[/dim]")

    db_session.close()


@cli.command()
def status():
    """Check if Chronicle is currently tracking an active session.

    This shows whether the current terminal session is being recorded,
    which session ID is active, and how long it's been running.
    """
    from backend.database.models import init_db
    from backend.services.ai_tracker import AITracker
    from backend.cli.formatters import console
    from rich.panel import Panel
    from rich.table import Table

    _, SessionLocal = init_db()
    db_session = SessionLocal()
    tracker = AITracker(db_session)

    # Get active session
    active_session = tracker.get_active_session()

    if not active_session:
        console.print(Panel(
            "[yellow]No active Chronicle session detected[/yellow]\n\n"
            "💡 To start tracking:\n"
            "   • Claude Code: [cyan]chronicle start claude[/cyan]\n"
            "   • Gemini CLI:  [cyan]chronicle start gemini[/cyan]\n"
            "   • Qwen CLI:    [cyan]chronicle start qwen[/cyan]",
            title="[bold]Chronicle Status[/bold]",
            border_style="yellow"
        ))
        db_session.close()
        return

    # Calculate elapsed time
    from datetime import datetime
    elapsed = datetime.now() - active_session.timestamp
    elapsed_minutes = elapsed.total_seconds() / 60

    # Format elapsed time nicely
    if elapsed_minutes < 60:
        elapsed_str = f"{int(elapsed_minutes)} minutes"
    else:
        hours = int(elapsed_minutes / 60)
        minutes = int(elapsed_minutes % 60)
        elapsed_str = f"{hours}h {minutes}m"

    # Build info table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value")

    table.add_row("Session ID", f"[bold cyan]{active_session.id}[/bold cyan]")
    table.add_row("Tool", active_session.ai_tool)
    table.add_row("Started", active_session.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
    table.add_row("Duration", elapsed_str)

    if active_session.working_directory:
        table.add_row("Directory", active_session.working_directory)

    if active_session.repo_path:
        table.add_row("Repository", active_session.repo_path)

    if active_session.title:
        table.add_row("Title", active_session.title)

    if active_session.tags_list:
        table.add_row("Tags", ", ".join(active_session.tags_list))

    console.print(Panel(
        table,
        title="[bold green]✓ Active Chronicle Session[/bold green]",
        border_style="green"
    ))

    db_session.close()


@cli.command("rename-session")
@click.argument('session_id', type=int)
@click.argument('title', type=str)
def rename_session(session_id: int, title: str):
    """Set a descriptive title for a session.

    Examples:
        chronicle rename-session 32 "MCP Response Optimization"
        chronicle rename-session 30 "Fix Chronicle skill documentation"
    """
    db_session = get_session()

    # Find session
    session = db_session.query(AIInteraction).filter_by(id=session_id).first()

    if not session:
        console.print(f"[red]✗[/red] Session {session_id} not found")
        db_session.close()
        return

    # Update title
    old_title = session.title or "(no title)"
    session.title = title
    db_session.commit()

    console.print(f"[green]✓[/green] Updated session {session_id}")
    console.print(f"  [dim]Old:[/dim] {old_title}")
    console.print(f"  [dim]New:[/dim] {title}")

    db_session.close()


@cli.command("tag-session")
@click.argument('session_id', type=int)
@click.argument('tags', type=str)
@click.option('--add', is_flag=True, help='Add tags (instead of replacing)')
@click.option('--remove', is_flag=True, help='Remove tags')
def tag_session(session_id: int, tags: str, add: bool = False, remove: bool = False):
    """Add, remove, or set tags for a session.

    Examples:
        chronicle tag-session 32 documentation,skills           # Set tags (replaces existing)
        chronicle tag-session 32 optimization --add             # Add tag to existing
        chronicle tag-session 32 wip --remove                   # Remove tag
    """
    import json

    db_session = get_session()

    # Find session
    session = db_session.query(AIInteraction).filter_by(id=session_id).first()

    if not session:
        console.print(f"[red]✗[/red] Session {session_id} not found")
        db_session.close()
        return

    # Parse input tags
    new_tags = [t.strip() for t in tags.split(',') if t.strip()]

    # Get current tags
    current_tags = session.tags_list if session.tags else []

    if remove:
        # Remove tags
        updated_tags = [t for t in current_tags if t not in new_tags]
        action = "Removed"
    elif add:
        # Add tags (avoid duplicates)
        updated_tags = current_tags + [t for t in new_tags if t not in current_tags]
        action = "Added"
    else:
        # Replace all tags
        updated_tags = new_tags
        action = "Set"

    # Update session
    session.tags_list = updated_tags
    db_session.commit()

    console.print(f"[green]✓[/green] {action} tags for session {session_id}")
    if session.title:
        console.print(f"  [dim]Title:[/dim] {session.title}")
    console.print(f"  [dim]Tags:[/dim] {', '.join(updated_tags) if updated_tags else '(none)'}")

    db_session.close()


@cli.command("auto-title")
@click.argument('session_id', type=int)
def auto_title(session_id: int):
    """Generate a descriptive title from session summary using AI.

    Examples:
        chronicle auto-title 32                 # Generate title for session 32
    """
    from backend.services.summarizer import Summarizer
    import google.generativeai as genai

    db_session = get_session()

    # Find session
    session = db_session.query(AIInteraction).filter_by(id=session_id).first()

    if not session:
        console.print(f"[red]✗[/red] Session {session_id} not found")
        db_session.close()
        return

    # Check if summary exists
    if not session.summary_generated or not session.response_summary:
        console.print(f"[yellow]Session {session_id} needs to be summarized first[/yellow]")
        console.print(f"Run: [cyan]chronicle session {session_id}[/cyan]")
        db_session.close()
        return

    # Use Gemini to generate title
    console.print(f"[cyan]Generating title for session {session_id}...[/cyan]")

    try:
        from backend.core.config import get_config
        config = get_config()
        api_key = config.get("ai.gemini_api_key")

        if not api_key:
            console.print("[red]✗[/red] Gemini API key not configured")
            console.print("Set it with: [cyan]chronicle config ai.gemini_api_key YOUR_KEY[/cyan]")
            db_session.close()
            return

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        prompt = f"""Based on this development session summary, generate a concise, descriptive title (max 60 characters).

The title should capture the main accomplishment or focus of the session.

Examples of good titles:
- "MCP Response Optimization"
- "Session Organization Feature Implementation"
- "Fix Authentication Bug in Login Flow"
- "Add Markdown Export Functionality"

Session summary:
{session.response_summary[:2000]}

Generate ONLY the title, nothing else:"""

        response = model.generate_content(prompt)
        generated_title = response.text.strip().strip('"').strip("'")

        # Truncate if needed
        if len(generated_title) > 60:
            generated_title = generated_title[:57] + "..."

        # Update session
        old_title = session.title or "(no title)"
        session.title = generated_title
        db_session.commit()

        console.print(f"[green]✓[/green] Generated title for session {session_id}")
        console.print(f"  [dim]Old:[/dim] {old_title}")
        console.print(f"  [dim]New:[/dim] {generated_title}")

    except Exception as e:
        console.print(f"[red]✗[/red] Error generating title: {e}")

    db_session.close()


@cli.command()
@click.option('--sessions', 'session_range', type=str, help='Session range (e.g., "28-32" or "30,31,32")')
@click.option('--repo', type=str, help='Filter by repository')
@click.option('--days', type=int, help='Show sessions from last N days')
def graph(session_range: str = None, repo: str = None, days: int = None):
    """Visualize session relationships and connections.

    Examples:
        chronicle graph --sessions 28-32          # Graph sessions 28 through 32
        chronicle graph --sessions 30,31,32       # Graph specific sessions
        chronicle graph --days 7                  # Graph last week's sessions
        chronicle graph --repo /path/to/project   # Graph sessions for a repo
    """
    from rich.tree import Tree
    from rich.panel import Panel

    db_session = get_session()

    # Determine which sessions to graph
    sessions_query = db_session.query(AIInteraction).filter_by(is_session=1)

    if session_range:
        # Parse range
        if '-' in session_range:
            start, end = map(int, session_range.split('-'))
            session_ids = list(range(start, end + 1))
        else:
            session_ids = [int(sid.strip()) for sid in session_range.split(',')]
        sessions_query = sessions_query.filter(AIInteraction.id.in_(session_ids))
    elif days:
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=days)
        sessions_query = sessions_query.filter(AIInteraction.timestamp >= cutoff)
    elif repo:
        sessions_query = sessions_query.filter(AIInteraction.repo_path == repo)
    else:
        # Default: last 10 sessions
        sessions_query = sessions_query.order_by(AIInteraction.timestamp.desc()).limit(10)

    sessions = sessions_query.order_by(AIInteraction.timestamp).all()

    if not sessions:
        console.print("[yellow]No sessions found[/yellow]")
        db_session.close()
        return

    console.print("\n[bold cyan]Session Relationship Graph[/bold cyan]")
    console.print("═" * 80)

    # Build relationship map
    session_map = {s.id: s for s in sessions}
    roots = []  # Sessions with no parent in this set
    children_map = {}  # parent_id -> [child sessions]

    for session in sessions:
        if session.parent_session_id and session.parent_session_id in session_map:
            if session.parent_session_id not in children_map:
                children_map[session.parent_session_id] = []
            children_map[session.parent_session_id].append(session)
        else:
            roots.append(session)

    def format_session_node(s):
        """Format a session for display in tree."""
        title = s.title or f"Session {s.id}"
        duration = f"{s.duration_ms/60000:.1f}m" if s.duration_ms else "Active"
        tags = s.tags_list if s.tags else []
        tag_str = f" [{', '.join(tags[:2])}]" if tags else ""

        # Check for related sessions
        related = s.related_sessions_list if s.related_session_ids else []
        related_str = ""
        if related:
            related_in_graph = [r for r in related if r in session_map]
            if related_in_graph:
                related_str = f" → Related: {', '.join(map(str, related_in_graph))}"

        return f"[bold]{s.id}:[/bold] {title} [dim]({duration}){tag_str}{related_str}[/dim]"

    def build_tree(parent_session, tree_node):
        """Recursively build tree."""
        if parent_session.id in children_map:
            for child in children_map[parent_session.id]:
                child_node = tree_node.add(format_session_node(child))
                build_tree(child, child_node)

    # Create tree visualization
    if len(roots) == 1:
        # Single root tree
        tree = Tree(format_session_node(roots[0]))
        build_tree(roots[0], tree)
        console.print(tree)
    else:
        # Multiple root trees or flat list
        for root in roots:
            tree = Tree(format_session_node(root))
            build_tree(root, tree)
            console.print(tree)
            console.print()

    # Show summary
    linked_count = sum(1 for s in sessions if s.parent_session_id or s.related_session_ids)
    console.print(f"\n[dim]{len(sessions)} sessions shown, {linked_count} with relationships[/dim]")

    db_session.close()


@cli.command()
@click.argument('key', required=False)
@click.argument('value', required=False)
@click.option('--list', 'show_all', is_flag=True, help='Show all configuration')
def config(key: str = None, value: str = None, show_all: bool = False):
    """Get or set configuration values.

    Examples:
        chronicle config --list                         # Show all config
        chronicle config ai.gemini_api_key              # View current key
        chronicle config ai.gemini_api_key YOUR_KEY     # Set API key
        chronicle config ai.default_model               # View default model
    """
    from backend.core.config import get_config

    cfg = get_config()

    if show_all:
        # Show all configuration
        import yaml
        console.print("\n[bold cyan]Chronicle Configuration[/bold cyan]")
        console.print("═" * 60)
        console.print(yaml.dump(cfg._config, default_flow_style=False, sort_keys=False))
        console.print(f"\n[dim]Config file: {cfg.config_path}[/dim]")
        return

    if key is None:
        console.print("[red]Error:[/red] Please provide a key")
        console.print("\nUsage:")
        console.print("  chronicle config --list                    # Show all")
        console.print("  chronicle config <key>                     # Get value")
        console.print("  chronicle config <key> <value>             # Set value")
        raise click.Abort()

    if value is None:
        # Get value
        current_value = cfg.get(key)
        if current_value is None:
            console.print(f"[yellow]'{key}' is not set[/yellow]")
            console.print(f"\nSet it with: [cyan]chronicle config {key} <value>[/cyan]")
        else:
            # Mask API keys for security
            if "api_key" in key.lower() and isinstance(current_value, str):
                masked = current_value[:8] + "..." + current_value[-4:] if len(current_value) > 12 else "***"
                console.print(f"[bold]{key}:[/bold] {masked}")
            else:
                console.print(f"[bold]{key}:[/bold] {current_value}")
    else:
        # Set value
        cfg.set(key, value)
        console.print(f"[green]✓[/green] Set '{key}' to '{value}'")
        console.print(f"[dim]Config saved to {cfg.config_path}[/dim]")


@cli.command()
def test_gemini():
    """Test Gemini API connection."""
    from backend.services.summarizer import Summarizer
    
    console.print("\n[bold cyan]Testing Gemini API Connection[/bold cyan]")
    console.print("═" * 60)
    
    try:
        summarizer = Summarizer()
        result = summarizer.test_connection()
        
        if result["success"]:
            console.print(f"[green]✓[/green] {result['message']}")
            console.print(f"[bold]Model:[/bold] {result['model']}")
            console.print(f"[bold]Response:[/bold] {result['response']}")
        else:
            console.print(f"[red]✗[/red] {result['message']}")
            console.print(f"[bold]Error:[/bold] {result['error']}")
            console.print("\n[yellow]Troubleshooting:[/yellow]")
            console.print("1. Check your API key: chronicle config ai.gemini_api_key")
            console.print("2. Verify at: https://aistudio.google.com/app/apikey")
            
    except ValueError as e:
        console.print(f"[red]✗[/red] Configuration Error")
        console.print(f"{e}")
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected Error")
        console.print(f"{e}")
        import traceback
        traceback.print_exc()


@cli.command()
@click.argument('session_id', type=int)
@click.option('--chunk-size', default=8000, help='Number of lines per chunk (default: 8000)')
@click.option('--use-cli', is_flag=True, help='Use CLI tool (qwen/gemini) instead of API (bypasses rate limits)')
@click.option('--cli-tool', type=click.Choice(['qwen', 'gemini']), default='qwen', help='Which CLI tool to use with --use-cli')
def summarize_chunked(session_id: int, chunk_size: int, use_cli: bool, cli_tool: str):
    """Summarize a large session using incremental chunked summarization.

    This is designed for very large sessions (> 50,000 lines) that are too big
    for standard summarization. It processes the transcript in chunks, maintaining
    a rolling summary that gets updated with each new chunk.

    Benefits:
    - No token limits - works with sessions of any size
    - Progressive summarization - see intermediate results
    - Resumable - chunks are saved to database
    - Uses Gemini API (200 free requests/day) or local CLI tools

    Examples:
        chronicle summarize-chunked 10                          # Use default 8,000 lines/chunk
        chronicle summarize-chunked 10 --chunk-size 5000        # Smaller chunks
        chronicle summarize-chunked 10 --use-cli --cli-tool qwen # Use Qwen CLI (bypasses rate limits)
    """
    from backend.services.summarizer import Summarizer

    db_session = get_session()

    # Check if session exists
    session = db_session.query(AIInteraction).filter_by(id=session_id).first()
    if not session:
        console.print(f"[red]✗[/red] Session {session_id} not found")
        db_session.close()
        return

    if not session.is_session:
        console.print(f"[red]✗[/red] ID {session_id} is not a session")
        db_session.close()
        return

    console.print(f"\n[bold cyan]Chunked Summarization: Session {session_id}[/bold cyan]")
    console.print("═" * 80)
    mode_str = f"{cli_tool.upper()} CLI (bypasses rate limits)" if use_cli else "Gemini API"
    console.print(f"[yellow]Mode:[/yellow] {mode_str}")
    console.print()

    try:
        summarizer = Summarizer()
        summary = summarizer.summarize_session_chunked(
            session_id=session_id,
            chunk_size_lines=chunk_size,
            db_session=db_session,
            use_cli=use_cli,
            cli_tool=cli_tool
        )

        console.print("\n[bold green]✓ Summarization Complete![/bold green]")
        console.print(f"\nView summary with: [cyan]chronicle session {session_id}[/cyan]")
        console.print(f"View chunks: [cyan]sqlite3 ~/.ai-session/sessions.db \"SELECT * FROM session_summary_chunks WHERE session_id={session_id}\"[/cyan]")

    except ValueError as e:
        console.print(f"[red]✗[/red] Configuration Error: {e}")
        console.print("\n[yellow]Troubleshooting:[/yellow]")
        console.print("1. Check your API key: chronicle config --list")
        console.print("2. Verify provider: chronicle config summarization.provider")

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db_session.close()


@cli.command()
@click.argument('session_id', type=int)
def clean_session(session_id: int):
    """Migrate a session to file-based storage (create .cleaned file).

    This extracts the transcript from the database, cleans it, saves it to a
    .cleaned file, and NULLs out the database entry to save space.

    Use this to prepare old sessions for the v6 migration.

    Examples:
        chronicle clean-session 10
        chronicle clean-session --all    # Clean all sessions
    """
    db_session = get_session()
    from pathlib import Path

    # Get the session
    session = db_session.query(AIInteraction).filter_by(id=session_id).first()

    if not session:
        console.print(f"[red]✗[/red] Session {session_id} not found")
        db_session.close()
        return

    if not session.is_session:
        console.print(f"[red]✗[/red] ID {session_id} is not a session")
        db_session.close()
        return

    if not session.session_transcript:
        console.print(f"[yellow]⚠[/yellow] Session {session_id} has no transcript in database")
        console.print(f"[dim]Checking for .log file...[/dim]")

        # Try reading from .log file instead
        log_path = Path.home() / ".ai-session" / "sessions" / f"session_{session_id}.log"
        if not log_path.exists():
            console.print(f"[red]✗[/red] No .log file found either")
            db_session.close()
            return

        console.print(f"[green]✓[/green] Found .log file, reading...")
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            transcript = f.read()
    else:
        transcript = session.session_transcript

    # Get current size
    original_size = len(transcript)
    console.print(f"\n[cyan]Migrating session {session_id} to file storage...[/cyan]")
    console.print(f"Source size: {original_size:,} chars ({original_size / 1024 / 1024:.2f} MB)")

    # Apply full cleaning
    from backend.utils.transcript_cleaner import clean_transcript
    cleaned = clean_transcript(transcript)

    # Save to .cleaned file
    sessions_dir = Path.home() / ".ai-session" / "sessions"
    cleaned_path = sessions_dir / f"session_{session_id}.cleaned"

    with open(cleaned_path, 'w', encoding='utf-8') as f:
        f.write(cleaned)

    # NULL out database transcript
    session.session_transcript = None
    db_session.commit()

    # Report results
    new_size = len(cleaned)
    reduction = ((original_size - new_size) / original_size * 100)

    console.print(f"[green]✓[/green] Session migrated successfully!")
    console.print(f"File: {cleaned_path.name}")
    console.print(f"Size: {new_size:,} chars ({new_size / 1024 / 1024:.2f} MB)")
    console.print(f"[bold green]Reduction: {reduction:.1f}%[/bold green]")
    console.print(f"[dim]Database transcript cleared (saves space)[/dim]")

    db_session.close()


@cli.command()
@click.argument('session_id', type=int)
@click.option('--summary', help='Summary text (or use stdin if not provided)')
def save_summary(session_id: int, summary: str = None):
    """Save a manually generated summary to a session.

    This is useful for large sessions where you manually run an AI CLI tool
    and want to save the summary back to the database.

    Examples:
        # Option 1: Paste summary interactively
        chronicle save-summary 10
        # (then paste your summary and press Ctrl+D)

        # Option 2: Pipe from file
        cat summary.txt | chronicle save-summary 10

        # Option 3: Provide inline
        chronicle save-summary 10 --summary "This session covered MCP integration..."
    """
    db_session = get_session()

    # Get the session
    session = db_session.query(AIInteraction).filter_by(id=session_id).first()

    if not session:
        console.print(f"[red]✗[/red] Session {session_id} not found")
        db_session.close()
        return

    if not session.is_session:
        console.print(f"[red]✗[/red] ID {session_id} is not a session (it's a one-off AI interaction)")
        db_session.close()
        return

    # Get summary from stdin if not provided via --summary
    if summary is None:
        console.print("[cyan]Paste your summary below, then press Ctrl+D (or Ctrl+Z on Windows):[/cyan]")
        console.print("[dim](Or pipe it in: cat summary.txt | chronicle save-summary {session_id})[/dim]\n")

        import sys
        summary = sys.stdin.read().strip()

        if not summary:
            console.print("[red]✗[/red] No summary provided")
            db_session.close()
            return

    # Save the summary
    session.response_summary = summary
    session.summary_generated = True
    db_session.commit()

    console.print(f"\n[green]✓[/green] Summary saved for session {session_id}")
    console.print(f"[dim]Summary length: {len(summary)} characters[/dim]")
    console.print(f"\nView it with: [cyan]chronicle session {session_id}[/cyan]")

    db_session.close()


@cli.command()
@click.argument('transcript_file', type=click.Path(exists=True))
@click.option('--tool', type=click.Choice(['claude', 'gemini']), default='claude',
              help='Which AI tool generated this session')
@click.option('--timestamp', help='Session start time (YYYY-MM-DD HH:MM), defaults to file mtime')
@click.option('--repo', type=click.Path(), help='Repository path (auto-detected if not provided)')
@click.option('--summarize/--no-summarize', default=True,
              help='Automatically summarize after import (default: yes)')
def import_session(transcript_file, tool, timestamp, repo, summarize):
    """Import a session from a text file retroactively.

    This is useful when you forgot to run 'chronicle start' but still want to
    capture the session. You can export the conversation from Claude Code or
    copy/paste it to a text file and import it.

    Examples:
        # Import with auto-detection
        chronicle import-session transcript.txt

        # Specify tool and timestamp
        chronicle import-session session.txt --tool claude --timestamp "2025-10-20 14:30"

        # Import without summarizing (do it later)
        chronicle import-session large-session.txt --no-summarize
    """
    import sys
    import os
    import git
    from backend.services.session_manager import SessionManager

    db_session = get_session()
    transcript_path = Path(transcript_file)

    # Read transcript
    try:
        with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
            transcript = f.read()
    except Exception as e:
        console.print(f"[red]✗[/red] Could not read file: {e}")
        db_session.close()
        return

    if not transcript.strip():
        console.print(f"[red]✗[/red] Transcript file is empty")
        db_session.close()
        return

    # Parse timestamp
    if timestamp:
        try:
            start_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
        except ValueError:
            console.print(f"[red]✗[/red] Invalid timestamp format. Use: YYYY-MM-DD HH:MM")
            db_session.close()
            return
    else:
        # Use file modification time
        import os
        file_mtime = os.path.getmtime(transcript_path)
        start_time = datetime.fromtimestamp(file_mtime)
        console.print(f"[dim]Using file modification time: {start_time.strftime('%Y-%m-%d %H:%M')}[/dim]")

    # Detect repository
    if not repo:
        # Try to detect from current directory
        import git
        try:
            git_repo = git.Repo(os.getcwd(), search_parent_directories=True)
            repo = git_repo.working_dir
            console.print(f"[dim]Detected repository: {repo}[/dim]")
        except:
            repo = os.getcwd()
            console.print(f"[dim]Not a git repo, using current directory: {repo}[/dim]")

    repo = os.path.abspath(repo)

    # Clean the transcript
    session_manager = SessionManager(db_session)
    clean_transcript = session_manager._clean_ansi(transcript)

    # Calculate duration (estimate based on transcript size - ~1 min per 1000 lines)
    lines = clean_transcript.count('\n')
    estimated_duration_ms = (lines // 10) * 60 * 1000  # ~1 min per 100 lines

    console.print(f"\n[cyan]Importing session...[/cyan]")
    console.print(f"  Tool: {tool}")
    console.print(f"  Lines: {lines:,}")
    console.print(f"  Size: {len(clean_transcript):,} chars ({len(clean_transcript) / 1024 / 1024:.1f} MB)")
    console.print(f"  Start time: {start_time}")
    console.print(f"  Repository: {repo}")

    # Create session record
    tool_name = f"{tool}-session"
    interaction = AIInteraction(
        timestamp=start_time,
        ai_tool=tool_name,
        prompt=f"Imported session ({estimated_duration_ms / 1000 / 60:.0f}m)",
        duration_ms=estimated_duration_ms,
        is_session=True,
        session_transcript=clean_transcript,
        working_directory=repo,
        repo_path=repo if os.path.isdir(os.path.join(repo, '.git')) else None,
        summary_generated=False
    )

    db_session.add(interaction)
    db_session.commit()
    session_id = interaction.id

    console.print(f"\n[green]✓[/green] Session imported as ID {session_id}")

    # Trigger summarization if requested
    if summarize:
        console.print(f"\n[cyan]Starting automatic summarization...[/cyan]")
        console.print(f"[dim](This may take a while for large sessions)[/dim]\n")

        try:
            from backend.services.summarizer import Summarizer
            summarizer = Summarizer()

            # Use chunked summarization for reliability
            # Chunk size auto-optimized: 3K/5K/10K based on session size
            summary = summarizer.summarize_session_chunked(
                session_id=session_id,
                db_session=db_session
            )

            console.print(f"\n[green]✓[/green] Session summarized!")
            console.print(f"[dim]Summary length: {len(summary)} characters[/dim]")
        except Exception as e:
            console.print(f"\n[yellow]⚠[/yellow] Summarization failed: {e}")
            console.print(f"[dim]You can summarize later with: chronicle session {session_id}[/dim]")

    console.print(f"\nView session: [cyan]chronicle session {session_id}[/cyan]")

    db_session.close()


@cli.command()
@click.option('--description', '-d', required=True, help='Description of what was accomplished')
@click.option('--tool', '-t', default='claude-code', help='AI tool used (default: claude-code)')
@click.option('--duration', type=int, help='Duration in minutes (optional)')
@click.option('--repo', help='Repository path (default: auto-detect from current directory)')
def add_manual(description: str, tool: str, duration: int, repo: str):
    """Manually add a session entry for work that wasn't tracked.

    Use this when you forgot to start Chronicle tracking but want to document
    what you accomplished. The session will be added to the database and can
    be summarized later.

    Examples:
        chronicle add-manual -d "Fixed authentication bug in user service"
        chronicle add-manual -d "Implemented dark mode toggle" --tool claude --duration 45
        chronicle add-manual -d "Refactored API endpoints" --repo ~/projects/my-app
    """
    from backend.database.models import get_session, AIInteraction
    from backend.services.summarizer import Summarizer
    import subprocess

    console.print("[bold]📝 Adding Manual Session Entry[/bold]\n")

    # Auto-detect repository if not provided
    if not repo:
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                capture_output=True,
                text=True,
                check=True
            )
            repo = result.stdout.strip()
            console.print(f"[dim]Detected repository: {repo}[/dim]")
        except subprocess.CalledProcessError:
            repo = os.getcwd()
            console.print(f"[dim]No git repo detected, using current directory: {repo}[/dim]")

    # Create database session
    db_session = get_session()

    # Create manual session entry
    session = AIInteraction(
        timestamp=datetime.now(),
        ai_tool=tool,
        prompt=f"Manual entry: {description}",
        response_summary=description,  # Use description as initial summary
        is_session=True,
        session_transcript=None,  # No transcript for manual entries
        summary_generated=False,  # Mark for later AI summarization
        duration_ms=duration * 60000 if duration else None,
        working_directory=os.getcwd(),
        repo_path=repo
    )

    db_session.add(session)
    db_session.commit()

    session_id = session.id

    console.print(f"[green]✓[/green] Manual session entry created: ID {session_id}")
    console.print(f"[dim]Tool: {tool}[/dim]")
    if duration:
        console.print(f"[dim]Duration: {duration} minutes[/dim]")
    console.print(f"[dim]Repository: {repo}[/dim]")

    # Ask if user wants to add more details
    console.print("\n[bold]Optional:[/bold] Add more details?")
    console.print("You can:")
    console.print(f"  1. Let AI generate a better summary: [cyan]chronicle session {session_id}[/cyan]")
    console.print("  2. Manually edit in database or Obsidian vault")
    console.print("  3. Export to Obsidian: [cyan]chronicle export obsidian[/cyan] (coming soon)")

    db_session.close()


# ============================================================================
# PROJECT TRACKING COMMANDS (Milestones & Next Steps)
# ============================================================================

@cli.command()
@click.argument('title')
@click.option('--description', '-d', help='Detailed description of the milestone')
@click.option('--type', 'milestone_type', type=click.Choice(['feature', 'bugfix', 'optimization', 'documentation']), default='feature', help='Type of milestone')
@click.option('--priority', type=int, default=3, help='Priority (1=highest, 5=lowest)')
@click.option('--tags', help='Comma-separated tags (e.g., "phase-4,mcp,obsidian")')
def milestone(title: str, description: str = None, milestone_type: str = 'feature', priority: int = 3, tags: str = None):
    """Create a new project milestone."""
    from rich.table import Table

    db_session = get_session()

    milestone = ProjectMilestone(
        title=title,
        description=description,
        milestone_type=milestone_type,
        priority=priority,
        status='planned'
    )

    if tags:
        milestone.tags_list = [tag.strip() for tag in tags.split(',')]

    db_session.add(milestone)
    db_session.commit()

    milestone_id = milestone.id

    console.print(f"[green]✓[/green] Created milestone #{milestone_id}: {title}")
    console.print(f"[dim]Type: {milestone_type} | Priority: {priority} | Status: planned[/dim]")
    if tags:
        console.print(f"[dim]Tags: {tags}[/dim]")

    console.print(f"\n[bold]Next:[/bold]")
    console.print(f"  - Link a session: [cyan]chronicle link-session <session_id> --milestone {milestone_id}[/cyan]")
    console.print(f"  - Update status: [cyan]chronicle milestone-status {milestone_id} in_progress[/cyan]")
    console.print(f"  - Mark complete: [cyan]chronicle milestone-complete {milestone_id}[/cyan]")

    db_session.close()


@cli.command()
@click.option('--status', type=click.Choice(['all', 'planned', 'in_progress', 'completed', 'archived']), default='all', help='Filter by status')
@click.option('--type', 'milestone_type', type=click.Choice(['feature', 'bugfix', 'optimization', 'documentation']), help='Filter by type')
@click.option('--limit', type=int, default=20, help='Max number of milestones to show')
def milestones(status: str, milestone_type: str = None, limit: int = 20):
    """List project milestones."""
    from rich.table import Table
    from sqlalchemy import desc

    db_session = get_session()

    query = db_session.query(ProjectMilestone)

    if status != 'all':
        query = query.filter(ProjectMilestone.status == status)

    if milestone_type:
        query = query.filter(ProjectMilestone.milestone_type == milestone_type)

    query = query.order_by(
        ProjectMilestone.completed_at.desc().nullsfirst(),
        desc(ProjectMilestone.priority),
        ProjectMilestone.created_at.desc()
    )

    milestones_list = query.limit(limit).all()

    if not milestones_list:
        console.print("[yellow]No milestones found[/yellow]")
        db_session.close()
        return

    table = Table(title=f"Project Milestones ({status})")
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Title", style="bold")
    table.add_column("Type", width=12)
    table.add_column("Status", width=12)
    table.add_column("Priority", width=8)
    table.add_column("Sessions", width=8)
    table.add_column("Tags", style="dim")

    for m in milestones_list:
        status_color = {
            'planned': 'blue',
            'in_progress': 'yellow',
            'completed': 'green',
            'archived': 'dim'
        }.get(m.status, 'white')

        session_count = len(m.sessions_list) if m.sessions_list else 0
        tags_str = ', '.join(m.tags_list[:3]) if m.tags_list else ''

        table.add_row(
            str(m.id),
            m.title[:50],
            m.milestone_type,
            f"[{status_color}]{m.status}[/{status_color}]",
            f"P{m.priority}",
            str(session_count),
            tags_str
        )

    console.print(table)
    console.print(f"\n[dim]Showing {len(milestones_list)} of {query.count()} milestones[/dim]")

    db_session.close()


@cli.command()
@click.argument('milestone_id', type=int)
@click.argument('new_status', type=click.Choice(['planned', 'in_progress', 'completed', 'archived']))
def milestone_status(milestone_id: int, new_status: str):
    """Update milestone status."""
    db_session = get_session()

    milestone = db_session.query(ProjectMilestone).filter_by(id=milestone_id).first()

    if not milestone:
        console.print(f"[red]Error:[/red] Milestone #{milestone_id} not found")
        db_session.close()
        return

    old_status = milestone.status
    milestone.status = new_status

    if new_status == 'completed' and not milestone.completed_at:
        milestone.completed_at = datetime.now()

    db_session.commit()

    console.print(f"[green]✓[/green] Updated milestone #{milestone_id}: {milestone.title}")
    console.print(f"[dim]{old_status} → {new_status}[/dim]")

    db_session.close()


@cli.command()
@click.argument('milestone_id', type=int)
def milestone_complete(milestone_id: int):
    """Mark a milestone as completed."""
    db_session = get_session()

    milestone = db_session.query(ProjectMilestone).filter_by(id=milestone_id).first()

    if not milestone:
        console.print(f"[red]Error:[/red] Milestone #{milestone_id} not found")
        db_session.close()
        return

    milestone.status = 'completed'
    milestone.completed_at = datetime.now()

    db_session.commit()

    # Get related sessions count
    session_count = len(milestone.sessions_list) if milestone.sessions_list else 0

    console.print(f"[green]✓[/green] Completed milestone: {milestone.title}")
    console.print(f"[dim]Type: {milestone.milestone_type} | {session_count} sessions linked[/dim]")

    db_session.close()


@cli.command()
@click.argument('milestone_id', type=int)
def milestone_show(milestone_id: int):
    """Show detailed milestone information."""
    from rich.panel import Panel
    from rich.markdown import Markdown

    db_session = get_session()

    milestone = db_session.query(ProjectMilestone).filter_by(id=milestone_id).first()

    if not milestone:
        console.print(f"[red]Error:[/red] Milestone #{milestone_id} not found")
        db_session.close()
        return

    # Build details
    details = f"# {milestone.title}\n\n"
    details += f"**Type:** {milestone.milestone_type}\n"
    details += f"**Status:** {milestone.status}\n"
    details += f"**Priority:** {milestone.priority}\n"
    details += f"**Created:** {milestone.created_at.strftime('%Y-%m-%d %H:%M')}\n"

    if milestone.completed_at:
        details += f"**Completed:** {milestone.completed_at.strftime('%Y-%m-%d %H:%M')}\n"

    if milestone.description:
        details += f"\n## Description\n{milestone.description}\n"

    if milestone.tags_list:
        details += f"\n**Tags:** {', '.join(milestone.tags_list)}\n"

    if milestone.sessions_list:
        details += f"\n## Linked Sessions ({len(milestone.sessions_list)})\n"
        for session_id in milestone.sessions_list:
            session = db_session.query(AIInteraction).filter_by(id=session_id).first()
            if session:
                details += f"- Session #{session_id}: {session.ai_tool} ({session.timestamp.strftime('%Y-%m-%d')})\n"

    if milestone.commits_list:
        details += f"\n## Linked Commits ({len(milestone.commits_list)})\n"
        for sha in milestone.commits_list[:5]:  # Show first 5
            details += f"- {sha[:8]}\n"

    console.print(Panel(Markdown(details), title=f"Milestone #{milestone_id}", border_style="cyan"))

    db_session.close()


@cli.command()
@click.argument('description')
@click.option('--priority', type=int, default=3, help='Priority (1=highest, 5=lowest)')
@click.option('--effort', type=click.Choice(['small', 'medium', 'large']), help='Estimated effort')
@click.option('--category', type=click.Choice(['feature', 'optimization', 'fix', 'docs']), default='feature', help='Category')
@click.option('--milestone', type=int, help='Link to milestone ID')
def next_step(description: str, priority: int = 3, effort: str = None, category: str = 'feature', milestone: int = None):
    """Add a next step / TODO item."""
    db_session = get_session()

    step = NextStep(
        description=description,
        priority=priority,
        estimated_effort=effort,
        category=category,
        created_by='manual',
        related_milestone_id=milestone
    )

    db_session.add(step)
    db_session.commit()

    step_id = step.id

    console.print(f"[green]✓[/green] Created next step #{step_id}")
    console.print(f"[dim]Priority: {priority} | Category: {category}[/dim]")
    if effort:
        console.print(f"[dim]Effort: {effort}[/dim]")
    if milestone:
        console.print(f"[dim]Linked to milestone #{milestone}[/dim]")

    db_session.close()


@cli.command()
@click.option('--all', 'show_all', is_flag=True, help='Show completed items too')
@click.option('--milestone', type=int, help='Filter by milestone ID')
@click.option('--limit', type=int, default=20, help='Max number of items to show')
def next_steps(show_all: bool = False, milestone: int = None, limit: int = 20):
    """List next steps / TODOs."""
    from rich.table import Table
    from sqlalchemy import desc

    db_session = get_session()

    query = db_session.query(NextStep)

    if not show_all:
        query = query.filter(NextStep.completed == 0)

    if milestone:
        query = query.filter(NextStep.related_milestone_id == milestone)

    query = query.order_by(
        NextStep.completed,
        desc(NextStep.priority),
        NextStep.created_at.desc()
    )

    steps = query.limit(limit).all()

    if not steps:
        console.print("[yellow]No next steps found[/yellow]")
        db_session.close()
        return

    table = Table(title="Next Steps")
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Description", style="bold")
    table.add_column("Priority", width=8)
    table.add_column("Effort", width=8)
    table.add_column("Category", width=12)
    table.add_column("Status", width=10)

    for step in steps:
        status = "[green]✓ Done[/green]" if step.completed else "[yellow]Pending[/yellow]"
        effort = step.estimated_effort or '-'

        table.add_row(
            str(step.id),
            step.description[:60],
            f"P{step.priority}",
            effort,
            step.category,
            status
        )

    console.print(table)
    console.print(f"\n[dim]Showing {len(steps)} items[/dim]")

    db_session.close()


@cli.command()
@click.argument('step_id', type=int)
def next_step_complete(step_id: int):
    """Mark a next step as completed."""
    db_session = get_session()

    step = db_session.query(NextStep).filter_by(id=step_id).first()

    if not step:
        console.print(f"[red]Error:[/red] Next step #{step_id} not found")
        db_session.close()
        return

    step.completed = 1
    step.completed_at = datetime.now()

    db_session.commit()

    console.print(f"[green]✓[/green] Completed: {step.description}")

    db_session.close()


@cli.command()
@click.argument('session_id', type=int)
@click.option('--milestone', type=int, help='Milestone ID to link to')
@click.option('--continues-from', 'parent_id', type=int, help='Mark as continuation of this session')
@click.option('--related-to', 'related_ids', type=str, help='Comma-separated related session IDs')
def link_session(session_id: int, milestone: int = None, parent_id: int = None, related_ids: str = None):
    """Link a session to milestones or other sessions.

    Examples:
        chronicle link-session 32 --milestone 3             # Link to milestone
        chronicle link-session 32 --continues-from 31       # Session 32 continues 31
        chronicle link-session 32 --related-to 30,31        # Related to 30 and 31
        chronicle link-session 32 --milestone 3 --related-to 30   # Multiple links
    """
    db_session = get_session()

    # Get session
    session = db_session.query(AIInteraction).filter_by(id=session_id).first()
    if not session:
        console.print(f"[red]Error:[/red] Session #{session_id} not found")
        db_session.close()
        return

    changes = []

    # Link to milestone
    if milestone is not None:
        milestone_obj = db_session.query(ProjectMilestone).filter_by(id=milestone).first()
        if not milestone_obj:
            console.print(f"[red]Error:[/red] Milestone #{milestone} not found")
            db_session.close()
            return

        # Add session to milestone's sessions list
        sessions = milestone_obj.sessions_list or []
        if session_id not in sessions:
            sessions.append(session_id)
            milestone_obj.sessions_list = sessions
            changes.append(f"Milestone: {milestone_obj.title}")
        else:
            console.print(f"[yellow]Session #{session_id} already linked to milestone #{milestone}[/yellow]")

    # Set parent session
    if parent_id is not None:
        parent = db_session.query(AIInteraction).filter_by(id=parent_id).first()
        if not parent:
            console.print(f"[red]✗[/red] Parent session {parent_id} not found")
            db_session.close()
            return

        session.parent_session_id = parent_id
        parent_title = parent.title or f"Session {parent_id}"
        changes.append(f"Continues from: {parent_title}")

    # Add related sessions
    if related_ids is not None:
        new_related = [int(rid.strip()) for rid in related_ids.split(',') if rid.strip()]

        # Verify all exist
        for rid in new_related:
            related = db_session.query(AIInteraction).filter_by(id=rid).first()
            if not related:
                console.print(f"[red]✗[/red] Related session {rid} not found")
                db_session.close()
                return

        # Merge with existing
        current_related = session.related_sessions_list if session.related_session_ids else []
        updated_related = current_related + [r for r in new_related if r not in current_related]
        session.related_sessions_list = updated_related

        changes.append(f"Related to: Sessions {', '.join(map(str, updated_related))}")

    if not changes:
        console.print("[yellow]No changes specified. Use --milestone, --continues-from, or --related-to[/yellow]")
        db_session.close()
        return

    # Save all changes
    db_session.commit()

    console.print(f"[green]✓[/green] Linked session #{session_id}")
    if session.title:
        console.print(f"  [dim]Title:[/dim] {session.title}")
    for change in changes:
        console.print(f"  [dim]{change}[/dim]")

    db_session.close()


@cli.command()
@click.option('--days', type=int, default=7, help='Number of days to show')
def roadmap(days: int = 7):
    """Show project roadmap and progress."""
    from rich.table import Table
    from rich.panel import Panel

    db_session = get_session()

    # In progress milestones
    in_progress = db_session.query(ProjectMilestone).filter_by(status='in_progress').all()

    # Recent completions
    cutoff = datetime.now() - timedelta(days=days)
    completed = db_session.query(ProjectMilestone).filter(
        ProjectMilestone.status == 'completed',
        ProjectMilestone.completed_at >= cutoff
    ).order_by(ProjectMilestone.completed_at.desc()).limit(10).all()

    # Planned (high priority)
    planned = db_session.query(ProjectMilestone).filter_by(status='planned').order_by(
        ProjectMilestone.priority
    ).limit(5).all()

    # Pending next steps
    pending_steps = db_session.query(NextStep).filter_by(completed=0).order_by(
        NextStep.priority
    ).limit(5).all()

    # Show roadmap
    console.print("\n[bold cyan]Chronicle Development Roadmap[/bold cyan]\n")

    if in_progress:
        console.print("[bold yellow]🚧 In Progress[/bold yellow]")
        for m in in_progress:
            sessions_count = len(m.sessions_list) if m.sessions_list else 0
            console.print(f"  • [bold]{m.title}[/bold] ({m.milestone_type}, {sessions_count} sessions)")
        console.print()

    if completed:
        console.print(f"[bold green]✅ Completed (last {days} days)[/bold green]")
        for m in completed:
            completed_date = m.completed_at.strftime('%b %d')
            console.print(f"  • {m.title} ({completed_date})")
        console.print()

    if planned:
        console.print("[bold blue]📋 Planned (High Priority)[/bold blue]")
        for m in planned:
            console.print(f"  • [P{m.priority}] {m.title} ({m.milestone_type})")
        console.print()

    if pending_steps:
        console.print("[bold magenta]🔜 Next Steps[/bold magenta]")
        for step in pending_steps:
            effort = f" [{step.estimated_effort}]" if step.estimated_effort else ""
            console.print(f"  • [P{step.priority}] {step.description[:60]}{effort}")
        console.print()

    # Stats
    total_milestones = db_session.query(ProjectMilestone).count()
    total_completed = db_session.query(ProjectMilestone).filter_by(status='completed').count()
    total_steps = db_session.query(NextStep).count()
    completed_steps = db_session.query(NextStep).filter_by(completed=1).count()

    console.print(f"[dim]Milestones: {total_completed}/{total_milestones} completed | Next Steps: {completed_steps}/{total_steps} done[/dim]")

    db_session.close()


@cli.command()
def vacuum():
    """Compact the database to reclaim freed space.

    After cleaning sessions and removing transcripts from the database,
    SQLite marks pages as free but doesn't reclaim disk space. This
    command rebuilds the database file to reclaim that space.

    Examples:
        chronicle vacuum           # Compact database

    When to use:
    - After clearing session transcripts (cleanup operations)
    - When database size seems larger than expected
    - As part of regular maintenance
    """
    import sqlite3
    from pathlib import Path

    home = Path.home()
    db_path = home / ".ai-session" / "sessions.db"

    if not db_path.exists():
        console.print(f"[red]✗[/red] Database not found: {db_path}")
        return

    # Get size before
    size_before = db_path.stat().st_size

    console.print(f"\n[cyan]Compacting database...[/cyan]")
    console.print(f"[dim]Path: {db_path}[/dim]")
    console.print(f"[dim]Size before: {size_before / 1024 / 1024:.1f} MB[/dim]")

    try:
        # Connect and vacuum
        conn = sqlite3.connect(str(db_path))
        console.print(f"[dim]Running VACUUM...[/dim]")
        conn.execute("VACUUM")
        conn.close()

        # Get size after
        size_after = db_path.stat().st_size
        reduction = ((size_before - size_after) / size_before * 100) if size_before > 0 else 0

        console.print(f"\n[green]✓[/green] Database compacted successfully!")
        console.print(f"[bold]Size after: {size_after / 1024 / 1024:.1f} MB[/bold]")
        console.print(f"[bold green]Space reclaimed: {(size_before - size_after) / 1024 / 1024:.1f} MB ({reduction:.1f}%)[/bold green]")

    except Exception as e:
        console.print(f"[red]✗[/red] Error during vacuum: {e}")
        import traceback
        traceback.print_exc()


@cli.command()
@click.argument('session_id', type=int)
def export_session(session_id: int):
    """Export a session as JSON (for cross-system summarization).

    Example:
        chronicle export-session 42 > session.json
        chronicle export-session 42 | ssh mac "chronicle import-and-summarize" > summary.json
    """
    db_path = os.getenv('CHRONICLE_DB')  # For testing
    db_session = get_session(db_path)

    try:
        session = db_session.query(AIInteraction).filter_by(id=session_id).first()

        if not session:
            console.print(f"[red]✗[/red] Session {session_id} not found", )
            sys.exit(1)

        if not session.is_session:
            console.print(f"[red]✗[/red] ID {session_id} is not a session (use for full sessions only)", )
            sys.exit(1)

        # Get transcript (fallback chain: database → .cleaned → .log → None)
        transcript = session.session_transcript
        if transcript is None:
            # Try reading from .cleaned file (v6+ sessions after migration)
            home = Path.home()
            cleaned_path = home / ".ai-session" / "sessions" / f"session_{session_id}.cleaned"
            log_path = home / ".ai-session" / "sessions" / f"session_{session_id}.log"

            if cleaned_path.exists():
                transcript = cleaned_path.read_text(encoding='utf-8', errors='ignore')
            elif log_path.exists():
                # Fallback to .log file (raw transcript, not cleaned)
                transcript = log_path.read_text(encoding='utf-8', errors='ignore')

        # Build export JSON
        export_data = {
            "version": "1.0",
            "session": {
                "original_id": session.id,
                "timestamp": session.timestamp.isoformat() if session.timestamp else None,
                "ai_tool": session.ai_tool,
                "is_session": session.is_session,
                "session_transcript": transcript,
                "duration_ms": session.duration_ms,
                "title": session.title,
                "tags": session.tags,
                "keywords": session.keywords,
                "response_summary": session.response_summary,
                "summary_generated": session.summary_generated,
                "files_mentioned": session.files_mentioned,
                "parent_session_id": session.parent_session_id,
                "related_session_ids": session.related_session_ids,
            }
        }

        # Output to stdout (for piping)
        print(json.dumps(export_data, indent=2))

    except Exception as e:
        console.print(f"[red]✗[/red] Export failed: {e}", )
        sys.exit(1)
    finally:
        db_session.close()


@cli.command()
def import_session():
    """Import a session from JSON (stdin) and return new session ID.

    Example:
        cat session.json | chronicle import-session
        chronicle export-session 42 | ssh mac "chronicle import-session"
    """
    db_path = os.getenv('CHRONICLE_DB')  # For testing
    db_session = get_session(db_path)

    try:
        # Read JSON from stdin
        import_data = json.load(sys.stdin)

        if import_data.get("version") != "1.0":
            console.print(f"[red]✗[/red] Unsupported export version: {import_data.get('version')}", )
            sys.exit(1)

        session_data = import_data["session"]

        # JSON-encode files_mentioned if it's a list
        files_mentioned = session_data.get("files_mentioned")
        if isinstance(files_mentioned, list):
            files_mentioned = json.dumps(files_mentioned)

        # Create new session (with new ID)
        new_session = AIInteraction(
            timestamp=datetime.fromisoformat(session_data["timestamp"]) if session_data.get("timestamp") else datetime.now(),
            ai_tool=session_data["ai_tool"],
            prompt="",  # Sessions don't have prompts (full transcript instead)
            is_session=True,
            session_transcript=None,  # v6+: transcripts stored externally in .cleaned files
            duration_ms=session_data.get("duration_ms"),
            title=session_data.get("title"),
            tags=session_data.get("tags"),
            keywords=session_data.get("keywords"),
            response_summary=None,  # Clear summary - will re-generate if needed
            summary_generated=False,  # Mark as not summarized
            files_mentioned=files_mentioned,
            parent_session_id=None,  # Clear relationships (different DB)
            related_session_ids=None,
        )

        db_session.add(new_session)
        db_session.commit()

        # Create external transcript files for v6+ compatibility
        transcript_content = session_data.get("session_transcript")
        if transcript_content:
            from pathlib import Path
            sessions_dir = Path.home() / ".ai-session" / "sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)

            # Create .cleaned file (primary location for v6+ sessions)
            cleaned_path = sessions_dir / f"session_{new_session.id}.cleaned"
            cleaned_path.write_text(transcript_content, encoding='utf-8')

            console.print(f"[green]✓[/green] Session imported as ID {new_session.id}", )
            console.print(f"[dim]Original ID: {session_data.get('original_id')}[/dim]", )
            console.print(f"[dim]Tool: {new_session.ai_tool}[/dim]", )
            console.print(f"[dim]Transcript size: {len(transcript_content)} chars[/dim]", )
            console.print(f"[dim]✓ Transcript saved to {cleaned_path.name}[/dim]", )
        else:
            console.print(f"[green]✓[/green] Session imported as ID {new_session.id}", )
            console.print(f"[dim]Original ID: {session_data.get('original_id')}[/dim]", )
            console.print(f"[dim]Tool: {new_session.ai_tool}[/dim]", )
            console.print(f"[yellow]⚠[/yellow] No transcript data provided[/dim]", )

        # Output just the new ID to stdout (for piping)
        print(new_session.id)

    except json.JSONDecodeError as e:
        console.print(f"[red]✗[/red] Invalid JSON: {e}", )
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Import failed: {e}", )
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db_session.close()


@cli.command()
@click.option('--chunk-size', type=int, default=10000, help='Lines per chunk for large sessions')
@click.option('--quiet', is_flag=True, help='Suppress status messages, output only JSON')
def import_and_summarize(chunk_size: int, quiet: bool):
    """Import session from JSON (stdin) and immediately summarize it.

    Outputs JSON with summary to stdout.

    Example:
        cat session.json | chronicle import-and-summarize > summary.json
        chronicle export-session 42 | ssh mac "chronicle import-and-summarize --quiet" > summary.json
    """
    from backend.services.summarizer import Summarizer

    # Prevent concurrent remote summarization operations (prevents data corruption)
    import os
    import time
    import errno

    lock_file = os.path.expanduser("~/.ai-session/.import_and_summarize.lock")
    lock_dir = os.path.dirname(lock_file)
    os.makedirs(lock_dir, exist_ok=True)

    lock_fd = None
    try:
        # Try to acquire exclusive lock with timeout
        lock_fd = os.open(lock_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
        try:
            # Try to acquire lock, wait up to 60 seconds
            start_time = time.time()
            while time.time() - start_time < 60:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except (OSError, IOError) as e:
                    if e.errno == errno.EWOULDBLOCK:
                        time.sleep(1)
                    else:
                        raise
            else:
                if not quiet:
                    console.print("[red]✗[/red] Another import-and-summarize operation is in progress. Please wait.", )
                sys.exit(1)
        except NameError:
            # fcntl not available (Windows), just continue without locking
            pass
    except OSError as e:
        if not quiet:
            console.print(f"[red]✗[/red] Cannot create lock file: {e}", )
        sys.exit(1)

    db_path = os.getenv('CHRONICLE_DB')  # For testing
    db_session = get_session(db_path)

    try:
        # Read JSON from stdin
        import_data = json.load(sys.stdin)

        if import_data.get("version") != "1.0":
            console.print(f"[red]✗[/red] Unsupported export version: {import_data.get('version')}", )
            sys.exit(1)

        session_data = import_data["session"]

        if not quiet:
            console.print(f"[dim]Importing session from {session_data['ai_tool']}...[/dim]", )

        # JSON-encode files_mentioned if it's a list
        files_mentioned = session_data.get("files_mentioned")
        if isinstance(files_mentioned, list):
            files_mentioned = json.dumps(files_mentioned)

        # Create temporary session with negative ID for cross-system summarization
        # Use atomic query to prevent race conditions in concurrent operations
        try:
            # Atomic operation: find the lowest negative ID in a single query
            result = db_session.execute(
                "SELECT COALESCE(MIN(id), 0) - 1 FROM ai_interactions WHERE id < 0 FOR UPDATE"
            )
            temp_id = result.scalar() or -1
        except Exception:
            # Fallback to sequential search (less safe but compatible)
            temp_id = -1
            while db_session.query(AIInteraction).filter_by(id=temp_id).first():
                temp_id -= 1

        temp_session = AIInteraction(
            id=temp_id,  # Explicit negative ID for temporary session
            timestamp=datetime.fromisoformat(session_data["timestamp"]) if session_data.get("timestamp") else datetime.now(),
            ai_tool=session_data["ai_tool"],
            prompt="",  # Sessions don't have prompts (full transcript instead)
            is_session=True,
            session_transcript=None,  # v6+: transcripts stored externally in .cleaned files
            duration_ms=session_data.get("duration_ms"),
            title=f"[TEMP] {session_data.get('title', 'Remote Session')}",  # Mark as temporary
            tags=session_data.get("tags"),
            keywords=session_data.get("keywords"),
            response_summary=None,
            summary_generated=False,
            files_mentioned=files_mentioned,
            parent_session_id=None,
            related_session_ids=None,
        )

        db_session.add(temp_session)
        db_session.commit()

        # Create external transcript files for v6+ compatibility
        transcript_content = session_data.get("session_transcript")
        cleaned_path = None
        if transcript_content:
            import uuid
            import fcntl
            from pathlib import Path
            sessions_dir = Path.home() / ".ai-session" / "sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)

            # Create unique filename to prevent collisions in concurrent operations
            unique_id = f"{temp_session.id}_{uuid.uuid4().hex[:8]}"
            cleaned_path = sessions_dir / f"session_{unique_id}.cleaned"

            # Use file locking to prevent concurrent writes
            try:
                with open(cleaned_path, 'w', encoding='utf-8') as f:
                    # Apply exclusive lock for write safety
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    f.write(transcript_content)
                # Lock is automatically released when file is closed
            except ImportError:
                # Windows or systems without fcntl
                cleaned_path.write_text(transcript_content, encoding='utf-8')
            except OSError:
                # Fallback if file locking fails
                cleaned_path.write_text(transcript_content, encoding='utf-8')

            # Store the unique filename reference for cleanup
            temp_session.session_transcript = str(cleaned_path.name)

            if not quiet:
                console.print(f"[dim]✓ Transcript saved to {cleaned_path.name}[/dim]", )

        if not quiet:
            console.print(f"[green]✓[/green] Temporary session created (ID: {temp_session.id})", )
            console.print(f"[dim]Summarizing (this may take a while)...[/dim]", )

        summary_data = None
        try:
            # Summarize it
            summarizer = Summarizer()
            summary = summarizer.summarize_session_chunked(
                session_id=temp_session.id,
                chunk_size_lines=chunk_size,
                db_session=db_session,
                quiet=quiet
            )

            if not quiet:
                console.print(f"[green]✓[/green] Summary generated ({len(summary)} chars)", )

            # Refresh session to get updated summary
            db_session.refresh(temp_session)

            # Save summary data before cleanup
            summary_data = {
                "summary": temp_session.response_summary,
                "summary_generated": temp_session.summary_generated,
                "keywords": temp_session.keywords,
            }

        except Exception as e:
            console.print(f"[red]✗[/red] Summarization failed: {e}", )
            raise

        finally:
            # Clean up temporary session and files (always run)
            if not quiet:
                console.print(f"[dim]Cleaning up temporary session...[/dim]", )

            # Delete external file if it exists
            if cleaned_path and cleaned_path.exists():
                cleaned_path.unlink()
                if not quiet:
                    console.print(f"[dim]✓ Deleted {cleaned_path.name}[/dim]", )

            # Delete temporary session from database
            db_session.delete(temp_session)
            db_session.commit()
            if not quiet:
                console.print(f"[dim]✓ Deleted temporary session {temp_session.id}[/dim]", )

        # Output summary JSON to stdout
        output = {
            "version": "1.0",
            "original_id": session_data.get("original_id"),
            "summary": summary_data["summary"] if summary_data else None,
            "summary_generated": summary_data["summary_generated"] if summary_data else False,
            "keywords": summary_data["keywords"] if summary_data else None,
        }

        print(json.dumps(output, indent=2))

    except ImportError as e:
        console.print(f"[red]✗[/red] {e}", )
        console.print("[dim]Install with: pip install --user google-generativeai[/dim]", )
        console.print("[dim]Or use Ollama: chronicle config ai.summarization_provider ollama[/dim]", )
        sys.exit(1)
    except json.JSONDecodeError as e:
        console.print(f"[red]✗[/red] Invalid JSON: {e}", )
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed: {e}", )
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up lock file
        if 'lock_fd' in locals() and lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)  # Release lock
                os.close(lock_fd)
                try:
                    os.unlink(lock_file)  # Remove lock file
                except OSError:
                    pass  # Lock file might not exist
            except (NameError, OSError):
                pass  # fcntl not available or other error

        db_session.close()


@cli.command()
def import_summary():
    """Import a summary from JSON (stdin) and update the original session.

    Example:
        cat summary.json | chronicle import-summary
        ssh mac "chronicle export-session 42 | chronicle import-and-summarize" | chronicle import-summary
    """
    db_path = os.getenv('CHRONICLE_DB')  # For testing
    db_session = get_session(db_path)

    try:
        # Read JSON from stdin
        summary_data = json.load(sys.stdin)

        if summary_data.get("version") != "1.0":
            console.print(f"[red]✗[/red] Unsupported summary version: {summary_data.get('version')}", )
            sys.exit(1)

        original_id = summary_data.get("original_id")
        summary = summary_data.get("summary")
        keywords = summary_data.get("keywords")

        if not original_id:
            console.print(f"[red]✗[/red] No original_id in summary JSON", )
            sys.exit(1)

        # Find the original session
        session = db_session.query(AIInteraction).filter_by(id=original_id).first()

        if not session:
            console.print(f"[red]✗[/red] Session {original_id} not found", )
            sys.exit(1)

        # Data integrity checks
        if summary and len(summary) > 50:
            # Check if session already has a summary
            if session.response_summary and session.summary_generated:
                console.print(f"[yellow]⚠️[/yellow] Session {original_id} already has a summary. Overwriting...", )

                # Warn if summaries are very different (possible corruption)
                existing_summary = session.response_summary
                if len(existing_summary) > 50:
                    # Simple similarity check
                    summary_words = set(summary.lower().split())
                    existing_words = set(existing_summary.lower().split())

                    if summary_words and existing_words:
                        common_words = summary_words.intersection(existing_words)
                        similarity = len(common_words) / min(len(summary_words), len(existing_words))

                        if similarity < 0.3:  # Less than 30% similar
                            console.print(f"[red]⚠️[/red] WARNING: New summary is very different from existing one!")
                            console.print(f"[red]⚠️[/red] Existing: {existing_summary[:100]}...")
                            console.print(f"[red]⚠️[/red] New: {summary[:100]}...")
                            console.print(f"[red]⚠️[/red] This may indicate data corruption or wrong session ID.")

                            response = input("Continue anyway? (y/N): ").strip().lower()
                            if response != 'y':
                                console.print("Import cancelled.")
                                sys.exit(1)

        # Update with summary
        session.response_summary = summary
        session.summary_generated = True
        if keywords:
            session.keywords = keywords

        db_session.commit()

        console.print(f"[green]✓[/green] Summary imported for session {original_id}")
        console.print(f"[dim]Summary length: {len(summary) if summary else 0} chars[/dim]")
        console.print(f"[dim]Keywords: {keywords}[/dim]")

    except json.JSONDecodeError as e:
        console.print(f"[red]✗[/red] Invalid JSON: {e}", )
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Import failed: {e}", )
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db_session.close()


# ============================================================================
# Claude Code Provider Management
# ============================================================================


@cli.group(name="claude-provider")
def claude_provider():
    """Manage Claude Code providers (Anthropic OAuth vs Z.AI proxy)."""
    pass


@claude_provider.command(name="list")
def provider_list():
    """List all available Claude Code providers."""
    config = Config()
    providers = config.list_claude_providers()
    current_provider = config.current_claude_provider

    if not providers:
        console.print("[yellow]⚠[/yellow]  No providers configured")
        return

    table = Table(title="Available Claude Code Providers", show_header=True, header_style="bold cyan")
    table.add_column("Provider", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Description")
    table.add_column("Status", style="green")
    table.add_column("API Key", style="dim")

    for name, config_data in providers.items():
        provider_type = config_data.get("type", "unknown")
        description = config_data.get("description", "")
        is_current = "✓ Active" if name == current_provider else ""

        # Check if API key is configured
        api_key_status = ""
        if provider_type == "api_key":
            api_key = config_data.get("api_key")
            if api_key:
                api_key_status = f"{api_key[:8]}...{api_key[-4:]}"
            else:
                api_key_status = "[red]Not configured[/red]"
        elif provider_type == "oauth":
            api_key_status = "[dim]OAuth (automatic)[/dim]"

        table.add_row(name, provider_type, description, is_current, api_key_status)

    console.print(table)


@claude_provider.command(name="current")
def provider_current():
    """Show current active Claude Code provider."""
    config = Config()
    switcher = ClaudeProviderSwitcher()

    current_provider = config.current_claude_provider
    provider_config = config.get_claude_provider(current_provider)
    settings_info = switcher.get_current_settings_info()

    console.print(f"[bold]Current Provider:[/bold] [cyan]{current_provider}[/cyan]")

    if provider_config:
        console.print(f"[dim]Type: {provider_config.get('type')}[/dim]")
        console.print(f"[dim]Description: {provider_config.get('description')}[/dim]")

    console.print(f"\n[bold]Settings File:[/bold] {settings_info['settings_path']}")
    console.print(f"[dim]Detected provider type: {settings_info['provider_type']}[/dim]")

    if settings_info.get("base_url"):
        console.print(f"[dim]Base URL: {settings_info['base_url']}[/dim]")

    if settings_info.get("has_api_key"):
        console.print("[dim]API Key: Configured ✓[/dim]")

    # Show backup info
    backups = switcher.list_backups()
    if backups:
        console.print(f"\n[dim]Available backups: {len(backups)}[/dim]")


@claude_provider.command(name="use")
@click.argument("provider", type=click.Choice(["anthropic", "zai"]))
def provider_use(provider: str):
    """Switch to a different Claude Code provider.

    PROVIDER: anthropic or zai
    """
    config = Config()
    switcher = ClaudeProviderSwitcher()

    # Check if provider is configured
    provider_config = config.get_claude_provider(provider)
    if not provider_config:
        console.print(f"[red]✗[/red] Unknown provider: {provider}")
        return

    # For Z.AI, check if API key is configured
    if provider == "zai":
        api_key = provider_config.get("api_key")
        if not api_key:
            console.print(f"[red]✗[/red] Z.AI API key not configured")
            console.print(f"[dim]Run: chronicle claude-provider setup zai[/dim]")
            return

        base_url = provider_config.get("base_url", "https://api.z.ai/api/anthropic")
        timeout_ms = provider_config.get("timeout_ms", 3000000)

        # Switch to Z.AI
        try:
            switcher.switch_to_zai(api_key, base_url, timeout_ms)
            config.set_current_claude_provider("zai")
            console.print(f"[green]✓[/green] Switched to Z.AI provider")
            console.print(f"[dim]Base URL: {base_url}[/dim]")
            console.print(f"\n[yellow]⚠[/yellow]  Restart Claude Code for changes to take effect")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to switch provider: {e}")
            return

    elif provider == "anthropic":
        # Switch to Anthropic OAuth
        try:
            switcher.switch_to_anthropic()
            config.set_current_claude_provider("anthropic")
            console.print(f"[green]✓[/green] Switched to Anthropic OAuth provider")
            console.print(f"\n[yellow]⚠[/yellow]  Restart Claude Code for changes to take effect")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to switch provider: {e}")
            return

    # Show backup info
    backups = switcher.list_backups()
    if backups:
        latest_backup = backups[0]
        console.print(f"\n[dim]Previous settings backed up to: {latest_backup.name}[/dim]")


@claude_provider.command(name="setup")
@click.argument("provider", type=click.Choice(["zai"]))
def provider_setup(provider: str):
    """Configure API key for a provider.

    PROVIDER: Currently only 'zai' requires setup
    """
    config = Config()

    if provider == "zai":
        console.print("[bold cyan]Z.AI Provider Setup[/bold cyan]\n")
        console.print("Z.AI provides Claude Code access at 3x usage for lower cost.")
        console.print("\nTo get a Z.AI API key:")
        console.print("  1. Visit: [cyan]https://platform.z.ai[/cyan]")
        console.print("  2. Sign up and navigate to API Keys")
        console.print("  3. Create a new API key")
        console.print("  4. Copy the key\n")

        api_key = click.prompt(
            "Enter your Z.AI API key",
            type=str,
            hide_input=True,
            confirmation_prompt="Confirm API key"
        )

        if not api_key or len(api_key) < 10:
            console.print("[red]✗[/red] Invalid API key. Setup cancelled.")
            return

        # Save API key
        config.set_claude_provider_api_key("zai", api_key)
        console.print(f"\n[green]✓[/green] Z.AI API key saved: {api_key[:8]}...{api_key[-4:]}")
        console.print(f"\n[dim]To switch to Z.AI: chronicle claude-provider use zai[/dim]")


@claude_provider.command(name="backups")
def provider_backups():
    """List available settings backups."""
    switcher = ClaudeProviderSwitcher()
    backups = switcher.list_backups()

    if not backups:
        console.print("[yellow]⚠[/yellow]  No backups found")
        return

    table = Table(title="Settings Backups", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim")
    table.add_column("Backup File", style="cyan")
    table.add_column("Created", style="dim")

    for idx, backup_path in enumerate(backups, 1):
        # Extract timestamp from filename
        # Format: settings_YYYYMMDD_HHMMSS.json
        filename = backup_path.name
        timestamp_str = filename.replace("settings_", "").replace(".json", "")

        try:
            # Parse timestamp
            dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            created = dt.strftime("%Y-%m-%d %I:%M:%S %p")
        except:
            created = timestamp_str

        table.add_row(str(idx), backup_path.name, created)

    console.print(table)
    console.print(f"\n[dim]To restore: chronicle claude-provider restore <backup-file>[/dim]")


@claude_provider.command(name="restore")
@click.argument("backup_file")
def provider_restore(backup_file: str):
    """Restore Claude settings from a backup.

    BACKUP_FILE: Name of backup file (from 'chronicle claude-provider backups')
    """
    switcher = ClaudeProviderSwitcher()

    # Find backup file
    backup_path = switcher.backup_dir / backup_file

    if not backup_path.exists():
        console.print(f"[red]✗[/red] Backup file not found: {backup_file}")
        console.print(f"[dim]Run: chronicle claude-provider backups[/dim]")
        return

    # Confirm restore
    console.print(f"[yellow]⚠[/yellow]  This will restore settings from: [cyan]{backup_file}[/cyan]")
    console.print(f"[dim]Current settings will be backed up first[/dim]\n")

    if not click.confirm("Continue with restore?", default=False):
        console.print("Restore cancelled.")
        return

    try:
        # Backup current settings before restore
        switcher.backup_current_settings()

        # Restore from backup
        switcher.restore_from_backup(backup_path)

        console.print(f"[green]✓[/green] Settings restored from {backup_file}")
        console.print(f"\n[yellow]⚠[/yellow]  Restart Claude Code for changes to take effect")

    except Exception as e:
        console.print(f"[red]✗[/red] Restore failed: {e}")
        return


@cli.command()
@click.option('--force', is_flag=True, help='Overwrite existing hooks and settings')
def setup_hooks(force: bool):
    """Set up Claude Code hooks for Chronicle workflow automation."""
    console.print("[bold cyan]Chronicle Hooks Setup[/bold cyan]\n")

    # Get user's home directory
    home = Path.home()
    claude_dir = home / ".claude"
    hooks_dir = claude_dir / "hooks"
    config_dir = claude_dir / "config"

    console.print(f"Setting up hooks in: [cyan]{claude_dir}[/cyan]\n")

    # Check if already exists
    if claude_dir.exists() and not force:
        console.print("[yellow]⚠[/yellow]  .claude directory already exists")
        if not click.confirm("Continue and potentially overwrite files?", default=False):
            console.print("Setup cancelled.")
            ctx = click.get_current_context()
            ctx.exit(1)

    try:
        # Create directories
        claude_dir.mkdir(exist_ok=True)
        hooks_dir.mkdir(exist_ok=True)
        config_dir.mkdir(exist_ok=True)
        console.print("[green]✓[/green] Created directory structure")

        # Get Chronicle repo path (current working directory should be chronicle repo)
        repo_path = Path.cwd()
        source_hooks_dir = repo_path / ".claude" / "hooks"
        source_config_dir = repo_path / ".claude" / "config"

        if not source_hooks_dir.exists():
            console.print(f"[red]✗[/red] Source hooks directory not found: {source_hooks_dir}")
            console.print("[dim]Make sure you're running this from the Chronicle repository[/dim]")
            return

        # Copy hook scripts
        hook_files = ["user-prompt-submit.sh", "stop.sh", "post-tool-use.sh"]
        for hook_file in hook_files:
            source_path = source_hooks_dir / hook_file
            target_path = hooks_dir / hook_file

            if source_path.exists():
                target_path.write_text(source_path.read_text())
                # Make executable
                os.chmod(target_path, 0o755)
                console.print(f"[green]✓[/green] Installed {hook_file}")
            else:
                console.print(f"[yellow]⚠[/yellow]  {hook_file} not found in source")

        # Copy config files
        config_files = ["skill-rules.json"]
        for config_file in config_files:
            source_path = source_config_dir / config_file
            target_path = config_dir / config_file

            if source_path.exists():
                target_path.write_text(source_path.read_text())
                console.print(f"[green]✓[/green] Installed {config_file}")
            else:
                console.print(f"[yellow]⚠[/yellow]  {config_file} not found in source")

        # Create or update settings.local.json with hooks configuration
        settings_file = claude_dir / "settings.local.json"
        settings = {}

        # Load existing settings if file exists
        if settings_file.exists() and not force:
            try:
                settings = json.loads(settings_file.read_text())
                console.print("[green]✓[/green] Loaded existing settings")
            except Exception as e:
                console.print(f"[yellow]⚠[/yellow]  Could not parse existing settings: {e}")

        # Update hooks configuration
        hooks_config = {
            "UserPromptSubmit": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/user-prompt-submit.sh",
                            "timeout": 5
                        }
                    ]
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/stop.sh",
                            "timeout": 5
                        }
                    ]
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "Edit|Write|NotebookEdit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post-tool-use.sh",
                            "timeout": 5
                        }
                    ]
                }
            ]
        }

        # Merge hooks into settings
        settings["hooks"] = hooks_config

        # Write settings file
        settings_file.write_text(json.dumps(settings, indent=2))
        console.print("[green]✓[/green] Updated settings.local.json")

        # Create universal CLAUDE.md
        universal_claude_md = """# Universal Development Directives

> **=🔍 For Chronicle-Specific Context**: See `~/repos/chronicle/CLAUDE.md`
>
> **This file**: Universal best practices that apply to ALL development work

---

## =🔍 CRITICAL: SEARCH FIRST (MANDATORY)

**BEFORE IMPLEMENTING ANYTHING, YOU MUST SEARCH CHRONICLE:**

```python
# Basic search (multiple words = OR, any order - broader results)
mcp__chronicle__search_sessions(query="relevant keywords", limit=10)

# Use AND for precise searches, NOT to exclude, quotes for exact phrases
mcp__chronicle__search_sessions(query="authentication AND authorization", limit=10)
```

**WHY THIS IS MANDATORY:**
- Searching: **1 second**
- Reinventing: **10-20 minutes**
- **ROI: 2,700x** (proven from Sessions 21, 30, 31 - 45+ minutes wasted)

**This is not optional. This is not a suggestion. Search first, ALWAYS.**

**Trigger phrases that REQUIRE searching:**
- User says "I can't believe..." → Search first!
- User says "why isn't..." → Search first!
- User says "this should work..." → Search first!
- Before adding any feature → Check if it exists
- When debugging → Check past sessions for similar issues

---

## <🎯 Skills (Use These First!)

**BEFORE manually calling MCP tools, check if a skill exists for the task:**

| Task | Use This Skill | Instead of Manual |
|------|----------------|-------------------|
| =📝 Export session to Obsidian | `chronicle-session-documenter` | Manual `mcp__chronicle__get_session_summary()` + `mcp__obsidian__write_note()` calls |
| =🔍 Search past sessions for context | `chronicle-context-retriever` | Manual search and analysis across multiple sessions |
| =🔄 Complete Chronicle workflow guidance | `chronicle-workflow` | Ad-hoc workflow instructions |
| =📊 Manage milestones and roadmap | `chronicle-project-tracker` | Manual milestone/next step operations |
| =💡 Brainstorming and design refinement | `brainstorming` | Ad-hoc ideation |

### How to Invoke Skills

**Method 1: Let skill auto-activate (preferred)**
```
User: "Export session 75 to Obsidian"
→ Skill should auto-activate based on description match
→ Follow skill's guidance
```

**Method 2: Explicit invocation**
```python
Skill(command="chronicle-session-documenter")
→ Skill loads and provides detailed instructions
→ Follow the workflow it describes
```

### Why Use Skills Over Manual MCP Calls?

- ✅ **Complete workflows** - Skills guide through entire process, not just one MCP call
- ✅ **Best practices** - Skills encode correct patterns (formatting, error handling, etc.)
- ✅ **Consistency** - Same structured output every time
- ✅ **Examples** - Skills include usage examples and common patterns
- ✅ **Maintenance** - Update skill once, all uses benefit

---

## ⚡ USE MCP OVER CLI (MANDATORY)

**Always prefer MCP tools, NEVER use CLI for programmatic access:**

```python
# ✅ CORRECT (MCP - fast, structured JSON):
sessions = mcp__chronicle__search_sessions(query="storage", limit=5)
roadmap = mcp__chronicle__get_roadmap(days=7)

# ❌ WRONG (CLI - slow, hard to parse):
Bash("chronicle search 'storage'")
Bash("chronicle roadmap")
```

**Why MCP over CLI:**
- **Speed**: MCP queries DB directly (<10ms), CLI spawns subprocess (>100ms)
- **Programmatic**: Returns structured JSON, not formatted text
- **Reliable**: No parsing of human-readable output

---

## =📋 CHECK ROADMAP BEFORE PLANNING (REQUIRED)

**Avoid duplicate work:**
```python
mcp__chronicle__get_roadmap(days=7)
mcp__chronicle__get_next_steps(completed=False)
```

**Failure to check roadmap can result in duplicating already-planned work**

---

## =🔍 CHECK SESSION STATUS (REQUIRED)

**Verify if current session is being tracked:**
```python
# Check if conversation is being tracked
status = mcp__chronicle__get_current_session()
# Returns: {"active": true, "session": {...}} or {"active": false}
```

**If not tracking:**
- Current session NOT tracked unless started with `chronicle start claude`
- **YOU MUST suggest exit and restart if meaningful work is happening
- User can verify with: `chronicle status` command

---

## =🧪 WRITE TESTS FIRST (MANDATORY - TDD)

**NEVER write implementation code without tests:**

```python
# ❌ WRONG: Writing implementation first
def export_session(session_id):
    # ... implementation ...

# ✅ CORRECT: Writing test first (red-green-refactor)
def test_export_session_with_file_fallback():
    # ... test that fails ...
    # THEN write implementation to make test pass
```

**When you MUST write tests:**
- Before implementing new features
- Before fixing bugs (write failing test that reproduces bug)
- Before refactoring (ensure tests pass before AND after)
- When user asks "why don't you write tests??" (you violated this!)

---

## =🔎 FTS5 Search Tips (Use Boolean Operators!)

**When searching Chronicle, use these patterns:**

- **Multiple words** = implicit OR (finds sessions with ANY word, broader results)
- **AND operator** = require all words ("gemini AND model", "bug AND issue")
- **OR operator** = find either topic ("gemini OR claude", "bug OR issue")
- **NOT operator** = exclude terms ("testing NOT deprecated", "api NOT legacy")
- **Quotes** = exact phrase match ('"data corruption"' vs 'data corruption')
- **Combine** = "(gemini OR claude) AND testing"

**When to use which pattern:**
```python
# User asks about a specific feature/bug → Use AND for precision
mcp__chronicle__search_sessions(query="authentication AND session")

# User asks "did we work on X or Y?" → Use OR for breadth
mcp__chronicle__search_sessions(query="authentication OR authorization")

# User asks "X but not Y" → Use NOT
mcp__chronicle__search_sessions(query="api NOT deprecated")

# User mentions exact error message → Use quotes
mcp__chronicle__search_sessions(query='"OperationalError: database is locked"')

# User asks broad question → Cast wide net with OR
mcp__chronicle__search_sessions(query="bug OR issue OR error OR problem")
```

---

## <📝 SUGGEST SESSION ORGANIZATION (REQUIRED)

**After significant work:**
- YOU MUST propose descriptive title
- YOU MUST suggest relevant tags (technologies, features, bugs)
- YOU MUST link to related sessions

---

## =📋 PRE-FLIGHT CHECKLIST (FOR EVERY TASK)

**Before starting ANY development task, run this checklist:**

1. **SEARCH CHRONICLE** (1 second, saves 10-20 minutes):
   ```python
   mcp__chronicle__search_sessions(query="<your task>", limit=10)
   ```

2. **CHECK ROADMAP** (avoid duplicate planning):
   ```python
   mcp__chronicle__get_roadmap(days=7)
   mcp__chronicle__get_next_steps(completed=False)
   ```

3. **WRITE TESTS FIRST** (TDD red-green-refactor):
   - Write failing test
   - Implement feature to make test pass
   - Refactor

4. **CHECK FOR SKILLS** (use workflows, not manual calls):
   - Check if a skill exists for your task
   - Use Skill tool instead of manual MCP calls

**Violating this checklist wastes time and frustrates the user. Follow it religiously.**

---

## ⚠️ Common Mistakes to Avoid

**Learn from real violations:**

### Mistake #1: Not Searching Chronicle First
**Impact**: Wasted 20+ minutes debugging, user had to remind me
**Solution**: Always search first - ROI is 2,700x

### Mistake #2: Writing Code Without Tests
**Impact**: Had to write 17 tests retroactively, added extra work
**Solution**: TDD red-green-refactor cycle

### Mistake #3: Using CLI Instead of MCP
**Impact**: 10x slower, fragile parsing of human-readable output
**Solution**: Always use MCP tools for programmatic access

### Mistake #4: Not Checking Roadmap
**Impact**: Duplicating already-planned work
**Solution**: Check roadmap before implementing anything

---

## <💡 Final Reminder

**Before you start working on any task:**

1. **SEARCH CHRONICLE FIRST** - `mcp__chronicle__search_sessions(query="...", limit=10)`
2. **CHECK ROADMAP** - `mcp__chronicle__get_roadmap(days=7)`
3. **WRITE TESTS FIRST** - TDD red-green-refactor cycle
4. **CHECK FOR SKILLS** - Use Skill tool for complete workflows
5. **USE MCP OVER CLI** - 10x faster, structured data
6. **VERIFY SESSION TRACKING** - `mcp__chronicle__get_current_session()` to check if active

**This is mandatory. Every single time. No exceptions.**

**If you hear trigger phrases ("I can't believe...", "why isn't..."), STOP and search Chronicle.**

---

**For project-specific context (Chronicle development, architecture, etc.), see:**
- `~/repos/chronicle/CLAUDE.md` - Chronicle project-specific guide
"""

        claude_md_file = claude_dir / "CLAUDE.md"
        claude_md_file.write_text(universal_claude_md)
        console.print("[green]✓[/green] Created universal CLAUDE.md")

        # Check for superpowers skills
        plugins_dir = claude_dir / "plugins"
        installed_plugins_file = plugins_dir / "installed_plugins.json"
        superpowers_available = False

        console.print("\n[cyan]Checking superpowers skills availability...[/cyan]")

        # Check if superpowers marketplace is configured
        marketplaces_dir = plugins_dir / "marketplaces"
        superpowers_marketplace = marketplaces_dir / "superpowers-marketplace"

        if superpowers_marketplace.exists():
            console.print("[green]✓[/green] Superpowers marketplace configured")

            # Check if superpowers skills are installed
            if installed_plugins_file.exists():
                try:
                    installed_data = json.loads(installed_plugins_file.read_text())
                    for plugin_key, plugin_info in installed_data.get("plugins", {}).items():
                        if "superpowers" in plugin_key:
                            superpowers_available = True
                            console.print(f"[green]✓[/green] Superpowers skills installed (v{plugin_info.get('version', 'unknown')})")
                            break
                except Exception as e:
                    console.print(f"[yellow]⚠[/yellow]  Could not check installed skills: {e}")

            if not superpowers_available:
                console.print("[yellow]⚠[/yellow]  Superpowers skills not installed")
                console.print("[dim]TDD skill auto-activation requires superpowers marketplace[/dim]")
                console.print("[dim]Install with: /plugin install superpowers@superpowers-marketplace[/dim]")
        else:
            console.print("[yellow]⚠[/yellow]  Superpowers marketplace not configured")
            console.print("[dim]TDD skill auto-activation requires superpowers marketplace[/dim]")
            console.print("[dim]Install with: /plugin install superpowers-marketplace[/dim]")

        # Success message
        console.print(f"\n[bold green]✓ Hooks setup complete![/bold green]")
        console.print(f"\n[cyan]What was installed:[/cyan]")
        console.print(f"  • Hook scripts in: {hooks_dir}")
        console.print(f"  • Configuration in: {settings_file}")
        console.print(f"  • Universal directives in: {claude_md_file}")

        console.print(f"\n[cyan]Next steps:[/cyan]")
        console.print(f"  1. Restart Claude Code for hooks to take effect")
        console.print(f"  2. If superpowers skills weren't detected, run: /plugin install superpowers@superpowers-marketplace")
        console.print(f"  3. Hooks will automatically remind you to search Chronicle")
        console.print(f"  4. Universal CLAUDE.md provides development best practices")
        console.print(f"  5. TDD skill will auto-activate when you start implementing (requires superpowers)")

        if not force:
            console.print(f"\n[dim]To reinstall later: chronicle setup-hooks --force[/dim]")

    except Exception as e:
        console.print(f"[red]✗[/red] Setup failed: {e}")
        return
