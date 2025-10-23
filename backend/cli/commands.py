"""CLI commands for AI Session Recorder."""

import os
from datetime import datetime, timedelta
from pathlib import Path
import click
from rich.console import Console

from backend.database.models import get_session, AIInteraction, ProjectMilestone, NextStep
from backend.services.git_monitor import GitMonitor
from backend.services.ai_tracker import AITracker
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
    console.print("  1. Add a repository: [cyan]chronicle add-repo /path/to/repo[/cyan]")
    console.print("  2. View today's activity: [cyan]chronicle show today[/cyan]")


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
@click.option('--repo', help='Filter by repository path')
def show(action: str, repo: str = None):
    """Show development activity."""
    db_session = get_session()
    monitor = GitMonitor(db_session)

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
            # Default chunk size: 10,000 lines
            summary = summarizer.summarize_session_chunked(
                session_id=session_id,
                chunk_size_lines=10000,
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
@click.option('--repo', help='Filter by repository path')
def timeline(action: str, repo: str = None):
    """Show combined timeline of commits and AI interactions."""
    db_session = get_session()
    monitor = GitMonitor(db_session)
    tracker = AITracker(db_session)

    if action == 'today':
        commits = monitor.get_commits_today(repo_path=repo)
        interactions = tracker.get_interactions_today()

    elif action == 'yesterday':
        yesterday_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        yesterday_end = yesterday_start + timedelta(days=1)
        commits = monitor.get_commits_by_date(yesterday_start, yesterday_end, repo_path=repo)
        interactions = tracker.get_interactions_by_date(yesterday_start, yesterday_end)

    elif action == 'week':
        week_start = datetime.now() - timedelta(days=7)
        commits = monitor.get_commits_by_date(week_start, repo_path=repo)
        interactions = tracker.get_interactions_by_date(week_start)

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
@click.argument('tool', type=click.Choice(['claude', 'gemini', 'vim', 'other']))
@click.option('--command', help='Custom command to run (overrides tool name)')
def start(tool: str, command: str = None):
    """Start an interactive session with a tool.

    This launches the tool and records all activity in a session.
    When you exit the tool, Chronicle saves the full transcript.

    Examples:
        chronicle start claude      # Claude Code
        chronicle start gemini      # Gemini CLI
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
@click.option('--repo', help='Filter by repository path')
@click.option('--limit', default=10, help='Number of sessions to show (default: 10)')
def sessions(repo: str = None, limit: int = 10):
    """List recent sessions.

    Examples:
        chronicle sessions                          # Last 10 sessions
        chronicle sessions --limit 20               # Last 20 sessions
        chronicle sessions --repo /path/to/project  # Sessions for specific repo
    """
    db_session = get_session()

    # Get recent sessions (last N)
    from backend.services.ai_tracker import AITracker
    tracker = AITracker(db_session)

    query = db_session.query(AIInteraction).filter_by(is_session=1)

    # Filter by repo if specified
    if repo:
        query = query.filter(AIInteraction.repo_path == repo)

    interactions = query.order_by(
        AIInteraction.timestamp.desc()
    ).limit(limit).all()
    
    if not interactions:
        console.print("[yellow]No sessions recorded yet.[/yellow]")
        console.print("\nStart a session with: [cyan]chronicle start claude[/cyan]")
        db_session.close()
        return
    
    console.print("\n[bold cyan]Recent Sessions[/bold cyan]")
    console.print("═" * 80)
    
    from rich.table import Table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("ID", width=6)
    table.add_column("Tool", width=15)
    table.add_column("Started", width=18)
    table.add_column("Duration", width=12)
    table.add_column("Status", width=15)
    table.add_column("Summary", width=20)
    
    for session in interactions:
        session_id = str(session.id)
        tool = session.ai_tool.replace("-session", "").title()
        timestamp = session.timestamp.strftime("%b %d, %I:%M %p")
        
        # Duration
        if session.duration_ms:
            duration_min = session.duration_ms / 1000 / 60
            duration = f"{duration_min:.1f}m"
        else:
            duration = "Active"
        
        # Status
        if session.session_transcript is None:
            status = "🟡 Active"
        elif session.summary_generated:
            status = "✅ Summarized"
        else:
            status = "⏳ Needs summary"
        
        # Summary preview
        if session.response_summary:
            summary = session.response_summary[:30] + "..."
        else:
            summary = "-"
        
        table.add_row(session_id, tool, timestamp, duration, status, summary)
    
    console.print(table)
    console.print(f"\n[dim]Use 'chronicle session <id>' to view full details[/dim]")
    
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
@click.option('--chunk-size', default=10000, help='Number of lines per chunk (default: 10000)')
def summarize_chunked(session_id: int, chunk_size: int):
    """Summarize a large session using incremental chunked summarization.

    This is designed for very large sessions (> 50,000 lines) that are too big
    for standard summarization. It processes the transcript in chunks, maintaining
    a rolling summary that gets updated with each new chunk.

    Benefits:
    - No token limits - works with sessions of any size
    - Progressive summarization - see intermediate results
    - Resumable - chunks are saved to database
    - Uses Gemini API (200 free requests/day)

    Examples:
        chronicle summarize-chunked 10                   # Use default 10,000 lines/chunk
        chronicle summarize-chunked 10 --chunk-size 5000 # Smaller chunks
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
    console.print(f"[yellow]Mode:[/yellow] Gemini API")
    console.print()

    try:
        summarizer = Summarizer()
        summary = summarizer.summarize_session_chunked(
            session_id=session_id,
            chunk_size_lines=chunk_size,
            db_session=db_session
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
    """Clean a session transcript to reduce database size.

    This retroactively applies full cleaning to a session that was captured
    before the improved cleaning was implemented. Removes ANSI codes, control
    characters, and deduplicates spinner lines.

    Typical reduction: 50-90% file size

    Examples:
        chronicle clean-session 10
    """
    db_session = get_session()

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
        console.print(f"[red]✗[/red] Session {session_id} has no transcript")
        db_session.close()
        return

    # Get current size
    original_size = len(session.session_transcript)
    console.print(f"\n[cyan]Cleaning session {session_id}...[/cyan]")
    console.print(f"Original size: {original_size:,} chars ({original_size / 1024 / 1024:.2f} MB)")

    # Apply full cleaning (same as session_manager._clean_ansi with deduplication)
    from backend.services.session_manager import SessionManager
    manager = SessionManager(db_session)
    cleaned = manager._clean_ansi(session.session_transcript)

    # Update session
    session.session_transcript = cleaned
    db_session.commit()

    # Report results
    new_size = len(cleaned)
    reduction = ((original_size - new_size) / original_size * 100)

    console.print(f"[green]✓[/green] Session cleaned successfully!")
    console.print(f"New size: {new_size:,} chars ({new_size / 1024 / 1024:.2f} MB)")
    console.print(f"[bold green]Reduction: {reduction:.1f}%[/bold green]")
    console.print(f"\n[dim]The transcript is now much smaller and ready for summarization.[/dim]")

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
            summary = summarizer.summarize_session_chunked(
                session_id=session_id,
                chunk_size_lines=10000,
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
@click.option('--milestone', type=int, required=True, help='Milestone ID to link to')
def link_session(session_id: int, milestone: int):
    """Link a session to a milestone."""
    db_session = get_session()

    # Get session
    session = db_session.query(AIInteraction).filter_by(id=session_id).first()
    if not session:
        console.print(f"[red]Error:[/red] Session #{session_id} not found")
        db_session.close()
        return

    # Get milestone
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
        db_session.commit()

        console.print(f"[green]✓[/green] Linked session #{session_id} to milestone: {milestone_obj.title}")
    else:
        console.print(f"[yellow]Session #{session_id} already linked to milestone #{milestone}[/yellow]")

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
