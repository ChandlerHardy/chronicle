# Chronicle Development History

> This document tracks Chronicle's evolution, completed features, and historical context.
> For current development guidance, see [CLAUDE.md](./CLAUDE.md)

**Last Updated**: October 22, 2025
**Current Status**: Phase 4 Complete - MCP Server + Obsidian Integration + Claude Skills
**Database Version**: 1.0
**Tests**: 16 passing (8 git + 8 AI tracking)

---

## Completed Phases

### Phase 1: Git Tracking ✅ (October 2025)

**Goal**: Track git commits across multiple repositories

**Features Implemented**:
- `chronicle init` - Initialize database
- `chronicle add-repo <path>` - Track a git repository
- `chronicle sync` - Sync commits from all tracked repos
- `chronicle show <today|yesterday|week>` - View commits
- `chronicle search <query>` - Search commit messages
- `chronicle stats <repo>` - Repository statistics

**Tests**: 8 passing tests for git monitoring

---

### Phase 2: AI Tracking ✅ (October 2025)

**Goal**: Capture and track AI coding assistant sessions

**Features Implemented**:

**Interactive Sessions** (full transcript capture):
- `chronicle start claude` - Start Claude Code session with recording
- `chronicle start gemini` - Start Gemini CLI session
- `chronicle sessions` - List all recorded sessions
- `chronicle session <id>` - View session details

**One-Shot Commands**:
- `chronicle ask "question" --tool gemini` - Ask and log

**Retroactive Capture** (October 22, 2025):
- `chronicle add-manual -d "description"` - Add untracked work retroactively
- Auto-detects repository, supports custom duration

**Viewing & Statistics**:
- `chronicle ai <today|yesterday|week>` - View AI interactions
- `chronicle ai-stats [--days N]` - Usage statistics with charts
- `chronicle timeline <today|yesterday|week>` - Combined commits + AI

**Tests**: 8 passing tests for AI tracking

**Architecture**:
- Uses Unix `script` command for full terminal capture
- Full I/O recorded to `~/.ai-session/sessions/session_N.log`
- Metadata stored in SQLite database

---

### Phase 3: AI Summarization ✅ (October 2025)

**Goal**: AI-powered summarization of sessions using Gemini

**Features Implemented**:

**Configuration**:
- `chronicle config --list` - View all settings
- `chronicle config <key> [value]` - Get/set config values
- Environment variable support: `GEMINI_API_KEY`
- API keys masked in display

**Summarization**:
- `chronicle session <id>` - Auto-generates summary on first view
- `chronicle summarize-chunked <id>` - Manual chunked summarization
- `chronicle summarize today` - AI summary of today's work
- `chronicle summarize week` - AI summary of last 7 days

**Chunked Summarization** (handles unlimited session sizes):
- Breaks large sessions into chunks (default: 10,000 lines)
- Maintains rolling summary across chunks
- Tested with 88,000+ line sessions
- Saves intermediate chunks to database
- Resumes from last chunk if interrupted

**Automatic Retry Logic** (October 22, 2025):
- 3 retry attempts per chunk with exponential backoff
- Smart rate limit detection (waits 15-45s)
- Handles transient network errors automatically
- No manual intervention needed

**Gemini Integration**:
- Uses `google-generativeai` Python SDK
- Default model: `gemini-2.0-flash`
- 1M token context window
- Free tier: 200 requests/day

**Lazy Loading**:
- Summaries generated on-demand
- Cached forever once generated
- Can work offline (view raw transcripts)

---

### Phase 4: MCP Server + Obsidian Integration ✅ (October 2025)

**Goal**: Make Chronicle data accessible to AI tools via MCP protocol

**Chronicle MCP Server**:
- Built with FastMCP framework
- Provides 7 tools for querying Chronicle database:
  - `get_sessions` - List and filter sessions
  - `get_session_summary` - Get detailed session info
  - `search_sessions` - Search session content
  - `get_commits` - List git commits
  - `search_commits` - Search commit messages
  - `get_timeline` - Combined commits + sessions
  - `get_stats` - Usage statistics
- Deployed as `scripts/chronicle-mcp` executable
- Returns structured JSON responses
- Configured in `.mcp.json`

**Obsidian MCP Integration**:
- Integrated bitbonsai/mcp-obsidian server
- Provides vault access for AI tools
- Read, write, search notes
- Configured globally in `~/.mcp.json`
- Renamed from `chronicle-obsidian` to `obsidian` (Oct 22, 2025)

**Multi-Repository Support**:
- Sessions auto-detect git repository
- Filter by repo: `chronicle sessions --repo my-app`
- Stores `repo_path` and `working_directory`

**Claude Skills** (published to marketplace):
- `chronicle-workflow` - Complete workflow guidance
- `chronicle-session-documenter` - Export sessions to Obsidian
- `chronicle-context-retriever` - Search past work
- Published as `chronicle-workflow-skills@chronicle-skills`

---

## Database Schema Evolution

### Current Schema (v1.0)

**commits**:
```sql
id, timestamp, sha, message, files_changed (JSON),
branch, author, repo_path
```

**ai_interactions**:
```sql
id, timestamp, ai_tool, prompt, response_summary,
duration_ms, files_mentioned (JSON), is_session (bool),
session_transcript (TEXT), summary_generated (bool),
related_commit_id (FK), working_directory, repo_path
```

**session_summary_chunks**:
```sql
id, session_id (FK), chunk_number, chunk_start_line,
chunk_end_line, chunk_summary, cumulative_summary, timestamp
```

**daily_summaries**:
```sql
id, date, summary, topics (JSON), files_affected (JSON),
commits_count, ai_interactions_count, key_decisions (JSON)
```

### Known Issues

**Database Size** (October 22, 2025):
- Current: ~110MB for 13 sessions
- Issue: Transcripts stored inline in `session_transcript` column
- Impact: 47MB of transcript data in database
- Proposed: Move transcripts to external files (future optimization)

**Transcript Cleaning** (October 20, 2025):
- ANSI codes, CSI sequences removed
- Duplicate lines collapsed
- 50-90% size reduction
- New sessions automatically cleaned
- Old sessions: use `chronicle clean-session <id>`

---

## Configuration System

### Storage Locations

- **Database**: `~/.ai-session/sessions.db`
- **Session transcripts**: `~/.ai-session/sessions/session_N.log`
- **Session metadata**: `~/.ai-session/sessions/session_N.meta`
- **Configuration**: `~/.ai-session/config.yaml`
- **MCP config**: `~/.mcp.json` (global) or `.mcp.json` (project)

### Config Priority

1. Environment variables (e.g., `GEMINI_API_KEY`)
2. Config file (`~/.ai-session/config.yaml`)
3. Defaults (in `backend/core/config.py`)

---

## Success Criteria

Chronicle is successful if it:
- ✅ Captures 95%+ of git commits (ACHIEVED)
- ✅ Logs AI interactions with <100ms overhead (ACHIEVED)
- ✅ Can answer "what did I do yesterday?" in <5 seconds (ACHIEVED)
- ✅ Finds specific past decisions in <10 seconds (ACHIEVED)
- ✅ Provides context across AI sessions (ACHIEVED)
- ✅ Generates useful summaries automatically (ACHIEVED - Phase 3)
- ⏳ Database size stays under 50MB/year (IN PROGRESS - currently 110MB/13 sessions)

---

## Known Limitations

1. **Platform Support**:
   - ✅ Linux, macOS (uses `script` command)
   - ❌ Windows (could use PowerShell transcript in future)

2. **Dependencies**:
   - Gemini API required for summarization (free tier available)
   - Git required for commit tracking
   - Node.js required for Obsidian MCP server

3. **Performance**:
   - Database size grows with transcript storage
   - Large sessions (88K+ lines) take 3-5 minutes to summarize
   - Chunked summarization required for sessions >50K lines

---

## Future Enhancements

### Planned (Phase 5+)

**Export & Sync**:
- [ ] `chronicle export obsidian` - Export sessions to markdown vault
- [ ] `chronicle import obsidian` - Rebuild database from vault
- [ ] Repository-organized vault structure
- [ ] Periodic backup command

**Optimization**:
- [ ] Move transcripts to external files (reduce DB from 110MB → ~10MB)
- [ ] Incremental summarization (summarize as session runs)
- [ ] Better session status tracking

**Features**:
- [ ] Next.js web dashboard
- [ ] Timeline visualization
- [ ] Blog post generator from weekly summaries
- [ ] Auto-update CLAUDE.md from sessions
- [ ] Team collaboration features

**Platform**:
- [ ] Windows support (PowerShell transcripts)
- [ ] VS Code extension
- [ ] GitHub action for PR descriptions
- [ ] Slack bot for daily summaries

---

## Migration Guide

### From Pre-Chunked Summarization

If you have sessions created before chunked summarization (pre-October 2025):

```bash
# Re-summarize with new chunked approach
chronicle summarize-chunked <session-id>

# Clean old transcripts
chronicle clean-session <session-id>
```

### From `chronicle-obsidian` to `obsidian` MCP

If you configured the Obsidian MCP server before October 22, 2025:

1. Edit `~/.mcp.json`:
   ```json
   {
     "mcpServers": {
       "obsidian": {  // Changed from "chronicle-obsidian"
         "command": "npx",
         "args": ["@mauricio.wolff/mcp-obsidian@latest", "/path/to/vault"]
       }
     }
   }
   ```

2. Restart Claude Code to pick up the change

---

## Project Metrics

**Code**:
- Language: Python 3.11+
- Lines of Code: ~5,000 (backend + CLI)
- Test Coverage: Core services covered (16 tests)

**Usage** (as of October 22, 2025):
- Sessions tracked: 17
- Repositories: 1 (chronicle itself)
- Database size: 110MB
- Longest session: 2,752 minutes (session 16)
- Largest transcript: 88,604 lines (session 16)

---

## References

- [CLAUDE.md](./CLAUDE.md) - Development guidance for AI assistants
- [README.md](./README.md) - User-facing documentation
- [MCP_SERVER.md](./MCP_SERVER.md) - Chronicle MCP server documentation
- [chronicle-skills/](./chronicle-skills/) - Claude Skills for Chronicle workflows

---

**This document is maintained as a historical record. For current development guidance, always refer to CLAUDE.md.**
