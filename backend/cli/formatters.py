"""Output formatting for CLI commands."""

from datetime import datetime
from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from backend.database.models import Commit, AIInteraction

console = Console()


def format_commit(commit: Commit) -> str:
    """Format a single commit for display.

    Args:
        commit: Commit object to format

    Returns:
        Formatted string
    """
    timestamp = commit.timestamp.strftime("%I:%M %p")
    sha_short = commit.sha[:8]
    message_first_line = commit.message.split('\n')[0][:80]
    files = commit.files_list
    files_count = len(files) if files else 0

    output = f"[bold cyan]{timestamp}[/bold cyan] [{sha_short}] {message_first_line}\n"

    if files and files_count > 0:
        if files_count <= 3:
            for f in files:
                output += f"   [dim]→ {f}[/dim]\n"
        else:
            for f in files[:3]:
                output += f"   [dim]→ {f}[/dim]\n"
            output += f"   [dim]→ ... and {files_count - 3} more files[/dim]\n"

    return output


def format_commits_list(commits: List[Commit], title: str = None) -> None:
    """Format and print a list of commits.

    Args:
        commits: List of Commit objects
        title: Optional title for the output
    """
    if not commits:
        console.print("[yellow]No commits found.[/yellow]")
        return

    if title:
        console.print(f"\n[bold]{title}[/bold]")
        console.print("─" * 60)

    for commit in commits:
        console.print(format_commit(commit))


def format_today_summary(commits: List[Commit]) -> None:
    """Format today's commits with summary statistics.

    Args:
        commits: List of Commit objects from today
    """
    if not commits:
        console.print("\n[yellow]No commits today yet.[/yellow]")
        return

    # Get stats
    total_commits = len(commits)
    all_files = set()
    for commit in commits:
        files = commit.files_list
        if files:
            all_files.update(files)

    repos = set(c.repo_path for c in commits)
    authors = set(c.author for c in commits)

    # Header
    today = datetime.now().strftime("%B %d, %Y")
    console.print(f"\n[bold cyan]Development Session - {today}[/bold cyan]")
    console.print("═" * 60)

    # Stats panel
    stats_text = f"""
[bold]Session Statistics[/bold]
• Commits: {total_commits}
• Files Changed: {len(all_files)}
• Repositories: {len(repos)}
• Authors: {len(authors)}
    """
    console.print(Panel(stats_text.strip(), border_style="cyan"))

    # Commits
    console.print("\n[bold]Commits[/bold]")
    console.print("─" * 60)
    for commit in commits:
        console.print(format_commit(commit))

    # Files changed (if not too many)
    if len(all_files) > 0 and len(all_files) <= 20:
        console.print("\n[bold]Files Changed[/bold]")
        console.print("─" * 60)
        for f in sorted(all_files):
            console.print(f"  • {f}")


def format_search_results(commits: List[Commit], search_term: str) -> None:
    """Format search results.

    Args:
        commits: List of matching Commit objects
        search_term: The search term used
    """
    if not commits:
        console.print(f"\n[yellow]No commits found matching '{search_term}'[/yellow]")
        return

    console.print(f"\n[bold]Search Results for '{search_term}'[/bold]")
    console.print(f"Found {len(commits)} commits")
    console.print("─" * 60)

    for commit in commits:
        console.print(format_commit(commit))


def format_repo_stats(stats: dict) -> None:
    """Format repository statistics.

    Args:
        stats: Dictionary with repository statistics
    """
    if stats["total_commits"] == 0:
        console.print("\n[yellow]No commits tracked for this repository yet.[/yellow]")
        return

    console.print(f"\n[bold cyan]Repository Statistics[/bold cyan]")
    console.print("═" * 60)

    latest = stats["latest_commit"]
    latest_date = latest.timestamp.strftime("%B %d, %Y at %I:%M %p")

    stats_text = f"""
[bold]Repository:[/bold] {stats['repo_path']}
[bold]Total Commits:[/bold] {stats['total_commits']}
[bold]Authors:[/bold] {', '.join(stats['authors'])}
[bold]Latest Commit:[/bold] {latest_date}
  {latest.sha[:8]} - {latest.message.split(chr(10))[0][:60]}
    """

    console.print(Panel(stats_text.strip(), border_style="cyan"))


def format_ai_interaction(interaction: AIInteraction, show_commit: bool = True) -> str:
    """Format a single AI interaction for display.

    Args:
        interaction: AIInteraction object to format
        show_commit: Whether to show related commit info

    Returns:
        Formatted string
    """
    timestamp = interaction.timestamp.strftime("%I:%M %p")
    tool_name = interaction.ai_tool.replace("-cli", "").title()

    # Emoji for tool
    tool_emoji = "🤖"
    if "gemini" in interaction.ai_tool.lower():
        tool_emoji = "✨"
    elif "qwen" in interaction.ai_tool.lower():
        tool_emoji = "🔮"
    elif "claude" in interaction.ai_tool.lower():
        tool_emoji = "🎯"

    prompt_preview = interaction.prompt[:100]
    if len(interaction.prompt) > 100:
        prompt_preview += "..."

    output = f"[bold cyan]{timestamp}[/bold cyan] {tool_emoji} [bold]{tool_name}[/bold]\n"
    output += f"   [italic]\"{prompt_preview}\"[/italic]\n"

    if interaction.response_summary:
        response_preview = interaction.response_summary[:150]
        if len(interaction.response_summary) > 150:
            response_preview += "..."
        output += f"   [dim]→ {response_preview}[/dim]\n"

    if interaction.duration_ms:
        duration_sec = interaction.duration_ms / 1000.0
        output += f"   [dim]⏱ {duration_sec:.1f}s[/dim]\n"

    if show_commit and interaction.commit:
        commit = interaction.commit
        output += f"   [green]✓ Linked to commit {commit.sha[:8]}[/green]\n"

    return output


def format_ai_interactions_list(interactions: List[AIInteraction], title: str = None) -> None:
    """Format and print a list of AI interactions.

    Args:
        interactions: List of AIInteraction objects
        title: Optional title for the output
    """
    if not interactions:
        console.print("[yellow]No AI interactions found.[/yellow]")
        return

    if title:
        console.print(f"\n[bold]{title}[/bold]")
        console.print("─" * 60)

    for interaction in interactions:
        console.print(format_ai_interaction(interaction))


def format_ai_stats(stats: dict, days: int = 30) -> None:
    """Format AI tool usage statistics.

    Args:
        stats: Dictionary with AI tool stats
        days: Number of days the stats cover
    """
    if not stats:
        console.print("[yellow]No AI interactions recorded yet.[/yellow]")
        return

    console.print(f"\n[bold cyan]AI Tool Usage (Last {days} days)[/bold cyan]")
    console.print("═" * 60)

    # Sort by count
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True)

    total_interactions = sum(s["count"] for _, s in sorted_stats)

    # Create table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("AI Tool", style="cyan", width=20)
    table.add_column("Interactions", justify="right", width=15)
    table.add_column("Percentage", justify="right", width=12)
    table.add_column("Avg Duration", justify="right", width=15)

    for tool, data in sorted_stats:
        count = data["count"]
        percentage = (count / total_interactions * 100) if total_interactions > 0 else 0

        avg_duration = "N/A"
        if data["total_duration_ms"] > 0:
            avg_ms = data["total_duration_ms"] / count
            avg_duration = f"{avg_ms / 1000:.1f}s"

        # Visual bar
        bar_length = int(percentage / 5)  # Max 20 chars
        bar = "█" * bar_length + "░" * (20 - bar_length)

        tool_display = tool.replace("-cli", "").title()

        table.add_row(
            tool_display,
            str(count),
            f"{percentage:.1f}% {bar}",
            avg_duration
        )

    console.print(table)
    console.print(f"\n[dim]Total interactions: {total_interactions}[/dim]")


def format_gemini_usage_stats(stats: dict) -> None:
    """Format Gemini model usage statistics with quota tracking.

    Args:
        stats: Dictionary with Gemini model usage stats
    """
    if not stats:
        console.print("[yellow]No Gemini model usage data available.[/yellow]")
        return

    console.print("\n[bold cyan]Gemini Model Usage (Today)[/bold cyan]")
    console.print("═" * 80)

    # Create table
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Model", style="cyan", width=30)
    table.add_column("Requests", justify="right", width=12)
    table.add_column("Daily Limit", justify="right", width=12)
    table.add_column("Remaining", justify="right", width=12)
    table.add_column("Usage", justify="left", width=20)

    # Sort by priority
    sorted_models = sorted(stats.items(), key=lambda x: x[1]["priority"])

    total_requests = sum(s["current_usage"] for _, s in sorted_models)
    total_limit = sum(s["daily_limit"] for _, s in sorted_models)

    for model_name, data in sorted_models:
        current = data["current_usage"]
        limit = data["daily_limit"]
        remaining = data["remaining"]
        percentage = data["percentage_used"]

        # Visual bar (max 15 chars)
        bar_length = int(percentage / 100 * 15)
        if percentage >= 90:
            bar_color = "red"
        elif percentage >= 70:
            bar_color = "yellow"
        else:
            bar_color = "green"

        bar = f"[{bar_color}]" + "█" * bar_length + "░" * (15 - bar_length) + "[/]"

        # Model name with emoji indicator
        if percentage >= 90:
            model_display = f"⚠️  {model_name}"
        elif remaining > 0:
            model_display = f"✓ {model_name}"
        else:
            model_display = f"✗ {model_name}"

        table.add_row(
            model_display,
            str(current),
            str(limit),
            str(remaining),
            f"{bar} {percentage:.1f}%"
        )

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {total_requests}/{total_limit} requests used today ({(total_requests/total_limit*100):.1f}%)")
    console.print(f"[dim]Remaining: {total_limit - total_requests} requests across all models[/dim]\n")


def format_combined_session(commits: List[Commit], interactions: List[AIInteraction]) -> None:
    """Format a combined view of commits and AI interactions.

    Args:
        commits: List of Commit objects
        interactions: List of AIInteraction objects
    """
    if not commits and not interactions:
        console.print("[yellow]No activity found.[/yellow]")
        return

    # Combine and sort by timestamp
    combined = []
    for commit in commits:
        combined.append(("commit", commit.timestamp, commit))
    for interaction in interactions:
        combined.append(("ai", interaction.timestamp, interaction))

    combined.sort(key=lambda x: x[1], reverse=True)

    # Display
    console.print("\n[bold cyan]Combined Development Timeline[/bold cyan]")
    console.print("═" * 60)

    for item_type, _, item in combined:
        if item_type == "commit":
            console.print(format_commit(item))
        else:
            console.print(format_ai_interaction(item, show_commit=False))


def format_session_detail(interaction: AIInteraction) -> None:
    """Format detailed view of a session.

    Args:
        interaction: AIInteraction object to display
    """
    timestamp = interaction.timestamp.strftime("%B %d, %Y at %I:%M %p")
    tool_name = interaction.ai_tool.replace("-cli", "").replace("-session", "").title()

    # Emoji for tool
    tool_emoji = "🤖"
    if "gemini" in interaction.ai_tool.lower():
        tool_emoji = "✨"
    elif "qwen" in interaction.ai_tool.lower():
        tool_emoji = "🔮"
    elif "claude" in interaction.ai_tool.lower():
        tool_emoji = "🎯"

    # Header
    console.print(f"\n[bold cyan]{tool_emoji} {tool_name} Session #{interaction.id}[/bold cyan]")
    console.print("═" * 60)

    # Session metadata
    metadata_text = f"""
[bold]Started:[/bold] {timestamp}
[bold]Tool:[/bold] {tool_name}
[bold]Session Type:[/bold] {"Full Session" if interaction.is_session else "Single Interaction"}
    """

    if interaction.duration_ms:
        duration_min = interaction.duration_ms / 1000.0 / 60.0
        metadata_text += f"[bold]Duration:[/bold] {duration_min:.1f} minutes\n"

    if interaction.repo_path:
        from pathlib import Path
        repo_name = Path(interaction.repo_path).name
        metadata_text += f"[bold]Repository:[/bold] {repo_name}\n"
        metadata_text += f"[dim]   {interaction.repo_path}[/dim]\n"
    elif interaction.working_directory:
        metadata_text += f"[bold]Working Directory:[/bold] {interaction.working_directory}\n"

    if interaction.commit:
        commit = interaction.commit
        metadata_text += f"[bold]Linked Commit:[/bold] {commit.sha[:8]} - {commit.message.split(chr(10))[0][:50]}\n"

    console.print(Panel(metadata_text.strip(), border_style="cyan", title="Session Info"))

    # Prompt/Description
    if interaction.prompt:
        console.print(f"\n[bold]Description:[/bold]")
        console.print(f"[italic]{interaction.prompt}[/italic]")

    # Summary
    if interaction.response_summary and interaction.summary_generated:
        console.print(f"\n[bold cyan]Summary[/bold cyan]")
        console.print("─" * 60)

        # Render as markdown for better formatting
        md = Markdown(interaction.response_summary)
        console.print(md)
    elif interaction.is_session:
        console.print(f"\n[dim]No summary generated yet. Run this command again to generate one.[/dim]")

    # Files mentioned
    files = interaction.files_list
    if files and len(files) > 0:
        console.print(f"\n[bold]Files Mentioned:[/bold]")
        for f in files[:10]:
            console.print(f"  • {f}")
        if len(files) > 10:
            console.print(f"  [dim]... and {len(files) - 10} more files[/dim]")

    console.print()
