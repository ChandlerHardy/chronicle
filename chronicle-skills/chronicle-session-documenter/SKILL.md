---
name: chronicle-session-documenter
description: Document AI-assisted development sessions to Obsidian vault using Chronicle's MCP integration. Use when completing a coding session, creating development logs, or maintaining a knowledge base of past work. Automatically creates structured notes with metadata, summaries, and wikilinks to related sessions and commits.
---

# Chronicle Session Documenter

This skill helps you document development sessions to your Obsidian vault using Chronicle's database and the Obsidian MCP server.

## When to Use This Skill

Use this skill when:
- A development session has just completed
- User wants to document what was accomplished in a session
- Creating a development log or journal entry
- Building a searchable knowledge base of past work
- Need to link related sessions, commits, or decisions

## How It Works

1. **Query Chronicle Database** - Use `mcp__chronicle__get_session_summary(session_id)` to get session details with AI summary
2. **Retrieve Summary** - Summary is automatically generated in background when session ends (may still be processing for recent sessions)
3. **Create Obsidian Note** - Use `mcp__obsidian__write_note(path, content, frontmatter)` to write to vault
4. **Add Metadata** - Include frontmatter with tags, dates, duration, repo info extracted from session data
5. **Link Related Work** - Create wikilinks to previous sessions, commits, repos using session relationships

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

## Workflow Example

**After completing a session:**

```python
# Step 1: Get session data from Chronicle
session_data = mcp__chronicle__get_session_summary(session_id=10)

# Step 2: Extract key information
session_id = session_data["id"]
timestamp = session_data["timestamp"]  # "2025-10-24T14:30:00"
tool = session_data["tool"]  # "claude-code"
duration = session_data["duration_minutes"]  # 45
repo_path = session_data["repo_path"]  # "/Users/.../my-project"
summary = session_data["summary"]  # AI-generated summary (multi-paragraph)

# Step 3: Format note content
note_content = f"""# Session {session_id} - {brief_title}

**Duration:** {duration} minutes
**Repository:** [[{repo_name}]]
**Tool:** {tool_emoji} {tool_name}

## Summary
{summary}

## What Was Accomplished
- {extracted_accomplishments}

## Key Technical Decisions
- {extracted_decisions}

## Files Created or Modified
- {extracted_files}

## Issues & Blockers
- {extracted_blockers}

## Related
- Previous: [[Session-{prev_id}]]
"""

# Step 4: Prepare frontmatter
frontmatter = {
    "session_id": session_id,
    "date": "2025-10-24",
    "started": "14:30",
    "duration_minutes": duration,
    "ai_tool": tool,
    "repo": repo_name,
    "tags": ["chronicle-session", tool, "feature-work"]
}

# Step 5: Write to Obsidian vault
mcp__obsidian__write_note(
    path="Chronicle/Sessions/Session-10.md",
    content=note_content,
    frontmatter=frontmatter,
    mode="overwrite"
)
```

## Example Usage

**User:** "Can you document session 10 to my Obsidian vault?"

**Assistant:**
1. Calls `mcp__chronicle__get_session_summary(session_id=10)`
2. Parses summary to extract accomplishments, decisions, files, blockers
3. Creates structured Markdown content with wikilinks
4. Calls `mcp__obsidian__write_note(...)` to save to vault
5. Confirms: "Documented Session 10 to Chronicle/Sessions/Session-10.md"

## MCP Tools to Use

**Chronicle Database (Required)**
- `mcp__chronicle__get_session_summary(session_id)` - Get full session details with AI summary
- `mcp__chronicle__get_sessions(limit, days, tool, repo_path)` - List recent sessions to find session ID
- `mcp__chronicle__search_sessions(query, limit)` - Search for sessions by keyword
- `mcp__chronicle__get_commits(repo_path, days, limit)` - Get related commits for linking

**Obsidian Vault (Required)**
- `mcp__obsidian__write_note(path, content, frontmatter, mode)` - Write note to vault
- `mcp__obsidian__read_note(path)` - Check if note already exists (optional)
- `mcp__obsidian__list_directory(path)` - List existing session notes (optional)

**Batch Operations (For multiple sessions)**
- `mcp__chronicle__get_sessions_summaries(session_ids)` - Get summaries for up to 20 sessions at once
- `mcp__obsidian__write_note(...)` - Call in loop for each session

## Tips

- **Summary generation is automatic** - Summarization starts in background immediately when session ends (may take a few minutes for large sessions)
- **Parse summaries intelligently** - AI summaries often have sections like "Accomplishments:", "Technical Decisions:", "Issues/Blockers:"
- **Use wikilinks** - Link to `[[Session-{id}]]`, `[[{repo_name}]]`, `[[Commit-{short_sha}]]` for navigation
- **Extract repo name** - Parse from `repo_path`: `/Users/.../my-app` → `my-app`
- **Handle missing data** - Some sessions may not have summaries yet (still processing in background), or durations (still running)
- **Batch document** - Use `get_sessions()` to find recent sessions, then document each in loop
- **Check existing notes** - Use `read_note()` to avoid overwriting manually edited notes (ask user first)
- **Tool emojis** - Use 🎯 for claude-code, ✨ for gemini-cli, 🔮 for qwen-cli
- **Frontmatter tags** - Always include `["chronicle-session", "{tool}", ...]` for filtering in Obsidian
- **Date formatting** - Parse ISO timestamp `2025-10-24T14:30:00` → date: "2025-10-24", started: "14:30"

## Common Patterns

**Document today's sessions:**
```python
# Get today's sessions
sessions = mcp__chronicle__get_sessions(days=1, limit=20)
# Document each to vault
for session in sessions:
    if session["is_session"]:  # Only full sessions, not one-shots
        document_to_vault(session["id"])
```

**Document specific session by number:**
```python
# Direct documentation
session = mcp__chronicle__get_session_summary(session_id=10)
# Create note...
```

**Find and document sessions about a topic:**
```python
# Search first
results = mcp__chronicle__search_sessions(query="authentication", limit=5)
# Document each match
for result in results:
    document_to_vault(result["id"])
```