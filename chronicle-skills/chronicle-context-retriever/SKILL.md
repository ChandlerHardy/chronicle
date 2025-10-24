---
name: chronicle-context-retriever
description: Search and retrieve context from past development sessions using Chronicle's database. Use when user asks about previous work, wants to recall past decisions, needs to understand codebase history, or wants to avoid repeating past approaches. Searches Chronicle sessions directly from database (fast!) and provides relevant context.
---

# Chronicle Context Retriever

This skill helps you search and retrieve context from past development sessions using Chronicle's database with direct MCP access.

## When to Use This Skill

Use this skill when:
- User asks "what did I do yesterday/last week?"
- Need to recall how a feature was implemented
- Want to understand why a decision was made
- Looking for similar past work or patterns
- Avoiding repeating past mistakes or approaches
- Need context before starting related work

## How It Works

1. **Parse User Query** - Understand what context is needed
2. **Search Chronicle Database** - Use Chronicle MCP `search_sessions` with relevant keywords (fast!)
3. **Get Session Details** - Pull full summaries from matching sessions
4. **Extract Key Information** - Focus on decisions, blockers, solutions
5. **Present Context** - Summarize findings with session IDs for reference

## Search Strategies

### By Topic/Keywords
```python
# Search session summaries and prompts for keywords
mcp__chronicle__search_sessions(query="authentication", limit=10)
mcp__chronicle__search_sessions(query="database migration", limit=5)
```

### By Time Period
```python
# Get sessions from specific time periods
mcp__chronicle__get_sessions(days=7, limit=20)  # Last week
mcp__chronicle__get_timeline(days=1)  # Yesterday with commits
```

### By Repository
```python
# Filter sessions by repository path
mcp__chronicle__get_sessions(repo_path="/Users/.../my-app", limit=20)
```

### By Tool
```python
# Filter by AI tool used
mcp__chronicle__get_sessions(tool="claude-code", limit=10)
mcp__chronicle__get_sessions(tool="gemini-cli", limit=10)
```

## Example Queries

**"How did I implement authentication last time?"**
```python
# Search for authentication-related sessions
sessions = mcp__chronicle__search_sessions(query="authentication", limit=5)
# Get full details of relevant sessions
for session in sessions:
    details = mcp__chronicle__get_session_summary(session_id=session["id"])
# Extract implementation approach and decisions
```

**"What was the blocker we hit with the database migration?"**
```python
# Search for database migration issues
sessions = mcp__chronicle__search_sessions(query="database migration blocker", limit=5)
# Find relevant session and extract problem + solution
```

**"Show me all work on the user-dashboard feature"**
```python
# Search for user-dashboard work
sessions = mcp__chronicle__search_sessions(query="user-dashboard", limit=10)
# List chronological sessions and summarize progress
```

## Response Format

When retrieving context, structure the response like:

```markdown
## Context from Past Sessions

### Session {id} - {date}
**What was done:** {summary}
**Key decision:** {decision and rationale}
**Outcome:** {result}
**Related:** [[Session-{id}]]

### Session {id} - {date}
...

## Relevant for Current Work
- {How this context applies}
- {What to keep in mind}
- {What to avoid based on past experience}
```

## MCP Tools to Use

**Primary (Chronicle Database - Fast!)**
- `mcp__chronicle__search_sessions` - Search session summaries and prompts
- `mcp__chronicle__get_session_summary` - Get full summary for specific session
- `mcp__chronicle__get_sessions` - List sessions with filters (tool, repo, days)
- `mcp__chronicle__get_timeline` - Get sessions + commits for time period
- `mcp__chronicle__search_commits` - Search git commit messages
- `mcp__chronicle__get_commits` - List commits with filters

**Optional (Obsidian - Only if user wants vault notes)**
- `mcp__obsidian__search_notes` - Find documented sessions in vault
- `mcp__obsidian__read_note` - Read Obsidian note for session

## Tips

- **Database first!** - Chronicle MCP is faster than Obsidian search
- Always search broadly first, then narrow down with specific session IDs
- Check multiple related sessions for patterns
- Look at both successful and blocked approaches
- Note dates and repositories to understand context evolution
- Use `search_sessions` for keywords, `get_sessions` for filtering
- Combine with `get_timeline` to see commits + sessions together
