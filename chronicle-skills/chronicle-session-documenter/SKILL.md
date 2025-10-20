---
name: chronicle-session-documenter
description: Document AI-assisted development sessions to Obsidian vault using Chronicle's MCP integration. Use when completing a coding session, creating development logs, or maintaining a knowledge base of past work. Automatically creates structured notes with metadata, summaries, and wikilinks to related sessions and commits.
---

# Chronicle Session Documenter

This skill helps you document development sessions to your Obsidian vault using Chronicle's database and the chronicle-obsidian MCP server.

## When to Use This Skill

Use this skill when:
- A development session has just completed
- User wants to document what was accomplished in a session
- Creating a development log or journal entry
- Building a searchable knowledge base of past work
- Need to link related sessions, commits, or decisions

## How It Works

1. **Query Chronicle Database** - Get session details from `~/.ai-session/sessions.db`
2. **Retrieve Summary** - Pull AI-generated summary if available, or create one
3. **Create Obsidian Note** - Use MCP server to write structured note to vault
4. **Add Metadata** - Include frontmatter with tags, dates, duration, repo info
5. **Link Related Work** - Create wikilinks to previous sessions, commits, repos

## Note Structure

Create notes in `Chronicle/Sessions/Session-{id}.md` with this format:

```markdown
---
session_id: {id}
date: "{YYYY-MM-DD}"
started: "{HH:MM AM/PM}"
duration_minutes: {minutes}
ai_tool: "{tool}"
repo: "{repo_name}"
tags: ["chronicle-session", "{ai_tool}", "{topics}"]
---

# Session {id} - {Brief Title}

**Duration:** {duration}
**Repository:** [[{repo_name}]]
**Tool:** {AI Tool Name}

## Summary
{AI-generated summary from Chronicle}

## What Was Accomplished
- {Key accomplishment 1}
- {Key accomplishment 2}

## Key Technical Decisions
- {Decision 1 and rationale}

## Files Created or Modified
- `path/to/file.py` - {what changed}

## Issues & Blockers
- {Any problems encountered}

## Related
- Previous: [[Session-{prev_id}]]
- Commits: [[Commit-{sha}]]
- Repository: [[{repo_name}]]
```

## Example Usage

**After completing a session:**
```
User: "Can you document session 10 to my Obsidian vault?"