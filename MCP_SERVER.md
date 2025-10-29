# Chronicle MCP Server

The Chronicle MCP (Model Context Protocol) server provides AI tools with direct access to Chronicle's database of development sessions, commits, and summaries.

## What is MCP?

The Model Context Protocol (MCP) is a standardized way for AI assistants to access external data and tools. By running the Chronicle MCP server, any MCP-compatible AI (Claude Code, ChatGPT, etc.) can query your Chronicle database to:

- Search past development sessions
- Find previous decisions and discussions
- Retrieve commit history
- Get usage statistics
- Build a timeline of work across projects

## Installation

### 1. Install Chronicle with MCP Support

```bash
cd /path/to/chronicle
pip install -e ".[mcp]"
```

This installs Chronicle along with the `fastmcp` dependency required for the MCP server.

**Note:** If you previously installed Chronicle without MCP support (`pip install -e .`), you'll need to reinstall with the `[mcp]` extra to enable the MCP server.

### 2. Configure MCP Client

#### Option A: Global Configuration (Recommended)

Create or edit `~/.mcp.json`:

```json
{
  "mcpServers": {
    "chronicle": {
      "command": "python3",
      "args": [
        "/absolute/path/to/chronicle/scripts/chronicle-mcp"
      ]
    }
  }
}
```

**Replace** `/absolute/path/to/chronicle` with your actual Chronicle repository path.

#### Option B: Project-Specific Configuration

Copy the example configuration:

```bash
cd /path/to/your/project
cp /path/to/chronicle/.mcp.json.example .mcp.json
```

Edit `.mcp.json` and update the path to your Chronicle installation.

### 3. Restart Your AI Tool

After updating `.mcp.json`, restart Claude Code or your MCP-compatible AI tool for the changes to take effect.

### 4. Verify Installation

In Claude Code, type `/mcp` to list available MCP servers. You should see:

```
chronicle - Chronicle session recorder
```

## Available Tools

The Chronicle MCP server provides the following tools:

### `get_sessions`

Get recent Chronicle sessions with filtering options.

**Parameters:**
- `limit` (int, optional): Maximum number of sessions (default: 10, max: 100)
- `tool` (str, optional): Filter by AI tool (claude-code, gemini-cli, qwen-cli)
- `repo_path` (str, optional): Filter by repository path
- `days` (int, optional): Only show sessions from last N days
- `include_summaries` (bool, optional): Include full AI summaries (default: false)

**Example:**
```json
{
  "limit": 5,
  "tool": "claude-code",
  "days": 7,
  "include_summaries": false
}
```

**Returns:** JSON array of sessions with metadata and timestamps. Summaries are excluded by default to reduce response size (use `get_session_summary` or `get_sessions_summaries` for summaries).

---

### `get_session_summary`

Get detailed summary of a specific Chronicle session.

**Parameters:**
- `session_id` (int, required): The session ID to retrieve

**Example:**
```json
{
  "session_id": 15
}
```

**Returns:** Full session details including:
- Session metadata (tool, timestamp, duration)
- AI-generated summary
- Transcript path (if available)
- Related commit IDs

---

### `search_sessions`

Search Chronicle sessions by keywords.

**Parameters:**
- `query` (str, required): Search query
- `limit` (int, optional): Maximum results (default: 10, max: 50)
- `search_summaries` (bool, optional): Search in AI summaries (default: true)
- `search_prompts` (bool, optional): Search in session prompts (default: true)

**Example:**
```json
{
  "query": "authentication",
  "limit": 10
}
```

**Returns:** Matching sessions with highlighted search context.

---

### `get_sessions_summaries`

Get summaries for multiple sessions efficiently (batch retrieval).

**Parameters:**
- `session_ids` (list[int], required): List of session IDs to retrieve (max: 20)

**Example:**
```json
{
  "session_ids": [15, 16, 17]
}
```

**Returns:** Minimal JSON with just id, prompt, and summary for each session. Useful when you need summaries for multiple sessions without full metadata.

**Use cases:**
- Fetching summaries after a list query
- Building custom reports from multiple sessions
- Comparing work across several sessions

---

### `get_commits`

Get recent git commits tracked by Chronicle.

**Parameters:**
- `limit` (int, optional): Maximum commits (default: 20, max: 100)
- `repo_path` (str, optional): Filter by repository
- `author` (str, optional): Filter by commit author
- `days` (int, optional): Only show commits from last N days

**Example:**
```json
{
  "limit": 10,
  "repo_path": "chronicle",
  "days": 7
}
```

**Returns:** JSON array of commits with SHA, message, files changed, and author.

---

### `search_commits`

Search git commits by commit message.

**Parameters:**
- `query` (str, required): Search query
- `limit` (int, optional): Maximum results (default: 20, max: 100)

**Example:**
```json
{
  "query": "fix bug",
  "limit": 20
}
```

**Returns:** Matching commits sorted by recency.

---

### `get_timeline`

Get combined timeline of commits and sessions.

**Parameters:**
- `days` (int, optional): Number of days to show (default: 1)
- `repo_path` (str, optional): Filter by repository

**Example:**
```json
{
  "days": 7,
  "repo_path": "my-app"
}
```

**Returns:** Unified timeline with both commits and sessions, sorted by timestamp.

---

### `get_stats`

Get Chronicle usage statistics.

**Parameters:**
- `days` (int, optional): Number of days to analyze (default: 7)

**Example:**
```json
{
  "days": 30
}
```

**Returns:** Statistics including:
- Total sessions and commits
- Duration by tool
- Unique repositories
- Sessions per AI tool

---

### `get_current_session`

Get the currently active (in-progress) Chronicle session.

This helps AI assistants determine if the current conversation is being tracked. A session is considered active if it has no duration set (still running).

**Parameters:**
- `ai_tool` (string, optional): Filter by AI tool ('claude-code', 'gemini-cli', 'qwen-cli', 'claude-session'). If not specified, returns any active session.

**Example:**
```json
{
  "ai_tool": "claude-code"
}
```

**Returns:**
- If active: `{"active": true, "session": {...}}` with session details (id, tool, start_time, elapsed_minutes, working_directory, repo_path, title, tags)
- If not active: `{"active": false, "session": null}`

**Use Case:** Before suggesting the user exit and restart with `chronicle start claude`, check if they're already tracking with this tool.

---

### `get_milestones`

Get project milestones with filtering options.

**Parameters:**
- `status` (str, optional): Filter by status (planned, in_progress, completed, archived)
- `milestone_type` (str, optional): Filter by type (feature, bugfix, optimization, documentation)
- `limit` (int, optional): Maximum number of milestones (default: 20, max: 100)

**Example:**
```json
{
  "status": "in_progress",
  "limit": 10
}
```

**Returns:** JSON array of milestones with titles, descriptions, and related sessions/commits.

---

### `get_milestone`

Get detailed information about a specific milestone.

**Parameters:**
- `milestone_id` (int, required): The milestone ID

**Example:**
```json
{
  "milestone_id": 1
}
```

**Returns:** Milestone details including linked sessions and commits.

---

### `get_next_steps`

Get next steps / TODO items.

**Parameters:**
- `completed` (bool, optional): Filter by completion status (true = completed, false = pending, null = all)
- `milestone_id` (int, optional): Filter by related milestone ID
- `limit` (int, optional): Maximum number of items (default: 20, max: 100)

**Example:**
```json
{
  "completed": false,
  "milestone_id": 1,
  "limit": 10
}
```

**Returns:** JSON array of next steps with priorities and categories.

---

### `get_roadmap`

Get project roadmap showing current progress and planned work.

**Parameters:**
- `days` (int, optional): Number of days to look back for recent completions (default: 7)

**Example:**
```json
{
  "days": 7
}
```

**Returns:** Roadmap summary with in-progress milestones, recently completed items, and pending next steps.

---

### `create_milestone`

Create a new project milestone.

**Parameters:**
- `title` (str, required): Title of the milestone
- `description` (str, optional): Detailed description
- `milestone_type` (str, optional): Type (feature, bugfix, optimization, documentation) - default: "feature"
- `priority` (int, optional): Priority (1=highest, 5=lowest) - default: 3
- `tags` (str, optional): Comma-separated tags (e.g., "phase-4,mcp,obsidian")

**Example:**
```json
{
  "title": "Add export functionality",
  "description": "Export sessions to markdown and PDF formats",
  "milestone_type": "feature",
  "priority": 2,
  "tags": "phase-7,export,documentation"
}
```

**Returns:** JSON with created milestone ID and details.

---

### `create_next_step`

Create a new next step / TODO item.

**Parameters:**
- `description` (str, required): Description of the next step
- `priority` (int, optional): Priority (1=highest, 5=lowest) - default: 3
- `effort` (str, optional): Estimated effort (small, medium, large)
- `category` (str, optional): Category (feature, optimization, fix, docs) - default: "feature"
- `milestone_id` (int, optional): Link to milestone ID

**Example:**
```json
{
  "description": "Add unit tests for MCP export functions",
  "priority": 2,
  "effort": "medium",
  "category": "docs",
  "milestone_id": 4
}
```

**Returns:** JSON with created next step ID and details.

---

### `update_milestone_status`

Update the status of a milestone.

**Parameters:**
- `milestone_id` (int, required): The milestone ID
- `new_status` (str, required): New status (planned, in_progress, completed, archived)

**Example:**
```json
{
  "milestone_id": 1,
  "new_status": "completed"
}
```

**Returns:** JSON with update result.

---

### `complete_next_step`

Mark a next step as completed.

**Parameters:**
- `step_id` (int, required): The next step ID

**Example:**
```json
{
  "step_id": 5
}
```

**Returns:** JSON with completion timestamp and details.

---

### `update_milestone`

Update an existing milestone's details.

**Parameters:**
- `milestone_id` (int, required): The milestone ID to update
- `title` (str, optional): New title
- `description` (str, optional): New description
- `milestone_type` (str, optional): New type (feature, bugfix, optimization, documentation)
- `priority` (int, optional): New priority (1=highest, 5=lowest)
- `tags` (str, optional): New comma-separated tags (replaces existing tags)

**Example:**
```json
{
  "milestone_id": 2,
  "title": "Enhanced Export Functionality",
  "priority": 1,
  "tags": "phase-7,export,high-priority"
}
```

**Returns:** JSON with updated milestone details.

---

### `update_next_step`

Update an existing next step's details.

**Parameters:**
- `step_id` (int, required): The next step ID to update
- `description` (str, optional): New description
- `priority` (int, optional): New priority (1=highest, 5=lowest)
- `effort` (str, optional): New estimated effort (small, medium, large)
- `category` (str, optional): New category (feature, optimization, fix, docs)
- `milestone_id` (int, optional): New milestone ID to link to (use -1 to unlink)

**Example:**
```json
{
  "step_id": 8,
  "priority": 1,
  "effort": "large",
  "milestone_id": 3
}
```

**Returns:** JSON with updated next step details.

---

### `delete_milestone`

Delete a milestone (requires confirmation).

**Parameters:**
- `milestone_id` (int, required): The milestone ID to delete
- `confirm` (bool, required): Must be `true` to confirm deletion (safety check)

**Example:**
```json
{
  "milestone_id": 5,
  "confirm": true
}
```

**Returns:** JSON with deletion confirmation. Related next steps are automatically unlinked.

**Warning:** This action cannot be undone. Related next steps will have their milestone link removed.

---

### `delete_next_step`

Delete a next step (requires confirmation).

**Parameters:**
- `step_id` (int, required): The next step ID to delete
- `confirm` (bool, required): Must be `true` to confirm deletion (safety check)

**Example:**
```json
{
  "step_id": 12,
  "confirm": true
}
```

**Returns:** JSON with deletion confirmation.

**Warning:** This action cannot be undone.

---

### `uncomplete_next_step`

Reopen a completed next step (mark as not completed).

**Parameters:**
- `step_id` (int, required): The next step ID to reopen

**Example:**
```json
{
  "step_id": 7
}
```

**Returns:** JSON with update result.

**Use case:** When a next step was marked complete prematurely or needs to be revisited.

---

## Usage Examples

### Example 1: Finding Past Work

**User**: "How did I implement authentication last week?"

**AI** (using MCP):
1. Calls `search_sessions` with query="authentication" and days=7
2. Retrieves session summaries
3. Calls `get_session_summary` for relevant session IDs
4. Provides context from past sessions

### Example 2: Daily Standup

**User**: "What did I accomplish yesterday?"

**AI** (using MCP):
1. Calls `get_timeline` with days=1
2. Shows commits and sessions from yesterday
3. Summarizes key activities

### Example 3: Project Review

**User**: "Show me all work on the chronicle project this month"

**AI** (using MCP):
1. Calls `get_sessions` with repo_path="chronicle" and days=30
2. Calls `get_commits` with repo_path="chronicle" and days=30
3. Calls `get_stats` with days=30
4. Provides comprehensive project overview

## Architecture

```
Chronicle Database (SQLite)
    ~/.ai-session/sessions.db
           ↓
Chronicle MCP Server (Python)
    scripts/chronicle-mcp
    backend/mcp/server.py
           ↓
MCP Protocol (stdio)
           ↓
AI Client (Claude Code, etc.)
```

The MCP server:
- Reads from Chronicle's SQLite database
- Provides read-only access (no database modifications)
- Returns structured JSON responses
- Runs locally (all data stays on your machine)

## Security & Privacy

- **Local-First**: All data stays on your machine
- **Read-Only**: MCP server cannot modify your Chronicle database
- **No Network**: No data is sent to external servers
- **No API Keys**: No authentication required (local access only)

## Troubleshooting

### MCP Server Not Showing in `/mcp`

**Solution**: Restart Claude Code or your AI tool after updating `.mcp.json`.

### "python3: command not found"

**Solution**: Install Python 3.11+ or update your PATH.

### Database Errors

**Solution**: Ensure Chronicle is initialized:
```bash
chronicle init
```

### Permission Denied

**Solution**: Make the MCP script executable:
```bash
chmod +x /path/to/chronicle/scripts/chronicle-mcp
```

### Import Errors

**Solution**: Reinstall Chronicle with dependencies:
```bash
pip install -e /path/to/chronicle
```

## Development

### Running the Server Manually

```bash
python3 /path/to/chronicle/scripts/chronicle-mcp
```

The server communicates over stdin/stdout using the MCP protocol.

### Adding New Tools

1. Edit `backend/mcp/server.py`
2. Add a new function decorated with `@mcp.tool()`
3. Document parameters in the docstring
4. Return JSON-serializable data
5. Restart Claude Code to load the new tool

### Testing

```bash
# Test that server starts
python3 scripts/chronicle-mcp --help

# Test database access
chronicle sessions --limit 5
```

## Future Enhancements

- [ ] Resource providers (expose session transcripts as MCP resources)
- [ ] Prompt templates (pre-built queries for common tasks)
- [ ] Notifications (watch for new sessions)
- [ ] Multi-user support (team Chronicle databases)
- [ ] Web dashboard integration

## Related Documentation

- [Chronicle README](README.md) - Main Chronicle documentation
- [CLAUDE.md](CLAUDE.md) - Development context for AI assistants
- [MCP Official Docs](https://modelcontextprotocol.io/) - Model Context Protocol specification
- [FastMCP Documentation](https://gofastmcp.com/) - FastMCP framework docs

## Credits

Built with [FastMCP](https://gofastmcp.com/), the Python framework for MCP servers.
