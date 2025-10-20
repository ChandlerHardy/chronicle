---
name: chronicle-context-retriever
description: Search and retrieve context from past development sessions stored in Obsidian vault. Use when user asks about previous work, wants to recall past decisions, needs to understand codebase history, or wants to avoid repeating past approaches. Searches Chronicle session notes and provides relevant context.
---

# Chronicle Context Retriever

This skill helps you search and retrieve context from past development sessions documented in your Obsidian vault.

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
2. **Search Obsidian Vault** - Use MCP `search_notes` with relevant keywords
3. **Read Relevant Sessions** - Pull full content from matching session notes
4. **Extract Key Information** - Focus on decisions, blockers, solutions
5. **Present Context** - Summarize findings with links to full notes

## Search Strategies

### By Topic/Keywords
```
Search for: "authentication", "database migration", "API integration"
Location: Chronicle/Sessions/*.md
```

### By Time Period
```
Check frontmatter date field in session notes
Filter to specific date ranges
```

### By Repository
```
Search for: repo: "my-app"
Find all sessions related to specific project
```

### By Technology/Tool
```
Search tags: ["react", "postgresql", "docker"]
Find sessions using specific technologies
```

## Example Queries

**"How did I implement authentication last time?"**
- Search vault for "authentication" in Chronicle/Sessions/
- Read matching session notes
- Extract implementation approach and decisions
- Highlight any issues encountered

**"What was the blocker we hit with the database migration?"**
- Search for "database migration" + "blocker" or "issue"
- Find relevant session
- Extract problem description and solution

**"Show me all work on the user-dashboard feature"**
- Search for "user-dashboard" across sessions
- List chronological sessions
- Summarize progress and current state

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

- `mcp__chronicle-obsidian__search_notes` - Find relevant sessions
- `mcp__chronicle-obsidian__read_note` - Read full session content
- `mcp__chronicle-obsidian__list_directory` - Browse session notes by date

## Tips

- Always search broadly first, then narrow down
- Check multiple related sessions for patterns
- Look at both successful and blocked approaches
- Note dates to understand context evolution
- Use wikilinks to navigate related sessions
