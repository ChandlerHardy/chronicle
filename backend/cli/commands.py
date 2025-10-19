"""CLI commands for AI Session Recorder."""

import os
from datetime import datetime, timedelta
from pathlib import Path
import click
from rich.console import Console

from backend.database.models import get_session, AIInteraction
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
@click.option('--tool', required=True, type=click.Choice(['gemini', 'qwen']), help='AI tool to use')
@click.option('--log-only', is_flag=True, help='Only log, don\'t execute (for testing)')
def ask(prompt: str, tool: str, log_only: bool):
    """Ask an AI tool a question (wrapper for convenience)."""
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
@click.argument('tool', type=click.Choice(['claude', 'gemini', 'qwen', 'vim', 'other']))
@click.option('--command', help='Custom command to run (overrides tool name)')
def start(tool: str, command: str = None):
    """Start an interactive session with a tool.

    This launches the tool and records all activity in a session.
    When you exit the tool, Chronicle saves the full transcript.

    Examples:
        chronicle start claude      # Claude Code
        chronicle start gemini      # Gemini CLI
        chronicle start qwen        # Qwen Code CLI
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
        'qwen': 'qwen-code',
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
def sessions():
    """List recent sessions."""
    db_session = get_session()
    
    # Get recent sessions (last 10)
    from backend.services.ai_tracker import AITracker
    tracker = AITracker(db_session)
    
    interactions = db_session.query(AIInteraction).filter_by(is_session=1).order_by(
        AIInteraction.timestamp.desc()
    ).limit(10).all()
    
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
@click.argument('session_id', type=int)
def session(session_id: int):
    """View details of a specific session."""
    db_session = get_session()
    
    interaction = db_session.query(AIInteraction).filter_by(id=session_id).first()
    
    if not interaction or not interaction.is_session:
        console.print(f"[red]Error:[/red] Session #{session_id} not found")
        db_session.close()
        raise click.Abort()
    
    # Display session info
    console.print(f"\n[bold cyan]Session #{session_id}[/bold cyan]")
    console.print("═" * 80)
    
    tool = interaction.ai_tool.replace("-session", "").title()
    console.print(f"[bold]Tool:[/bold] {tool}")
    console.print(f"[bold]Started:[/bold] {interaction.timestamp.strftime('%B %d, %Y at %I:%M %p')}")
    
    if interaction.duration_ms:
        duration_min = interaction.duration_ms / 1000 / 60
        console.print(f"[bold]Duration:[/bold] {duration_min:.1f} minutes")
    
    if interaction.related_commit_id:
        console.print(f"[bold]Linked Commit:[/bold] Yes (#{interaction.related_commit_id})")
    
    console.print()
    
    # Show summary if available
    if interaction.response_summary:
        console.print("[bold]Summary:[/bold]")
        console.print(interaction.response_summary)
    elif interaction.session_transcript:
        console.print("[yellow]⏳ No summary yet - generating...[/yellow]")
        console.print()
        console.print("[bold]Transcript Preview:[/bold]")
        # Show first 1000 chars of transcript
        preview = interaction.session_transcript[:1000]
        console.print(f"[dim]{preview}...[/dim]")
        console.print()
        console.print("[dim]Full transcript stored. Use 'chronicle summarize' to generate summary.[/dim]")
    else:
        console.print("[yellow]Session still active or transcript not available[/yellow]")
    
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
