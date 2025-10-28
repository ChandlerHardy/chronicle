# Chronicle Integration Guide

This guide shows you how to integrate Chronicle into your development projects so AI assistants can leverage your development history.

## Quick Start

Add Chronicle directives to your project's `CLAUDE.md` (or equivalent AI assistant guide) to enable proactive Chronicle usage.

---

## Templates for Your Project's CLAUDE.md

Choose between two enforcement styles:

### Option 1: Friendly Guidance (Recommended for Most Projects)

Copy this section into your project's documentation:

```markdown
## Chronicle Development Memory

**This project uses Chronicle to track development sessions and maintain institutional knowledge.**

### Core Workflow (ALWAYS follow this order)

1. **Search First** - Before implementing ANYTHING:
   - Search Chronicle for similar past work
   - Check if this problem was already solved
   - Review relevant session summaries

   **Why?** Searching takes 1 second. Reinventing solutions takes 10-20 minutes. (2,700x ROI)

2. **Track This Session** - If meaningful work is happening:
   - Remind user if they haven't started a tracked session
   - Suggest: `chronicle start claude`

3. **Check Roadmap** - Before planning new work:
   - Verify the feature isn't already planned
   - Review existing milestones and next steps

4. **After Completion** - Suggest organizing the session:
   - Add descriptive title
   - Tag with relevant keywords (technologies, features, bugs)
   - Link to related sessions or commits

### Chronicle Command Reference (Bash - Works Everywhere)

```bash
chronicle search "query"           # Search all sessions
chronicle sessions                 # List recent sessions
chronicle session <id>             # View session details
chronicle roadmap                  # View planned work
chronicle timeline today           # View today's activity
chronicle show today               # View today's commits
```

### Chronicle MCP Tools (Faster - Requires MCP Server)

If you installed Chronicle with MCP support (`pip install -e ".[mcp]"`):

```python
# Search sessions (10x faster than CLI)
mcp__chronicle__search_sessions(query="feature name", limit=10)

# Get recent sessions with structured JSON
mcp__chronicle__get_sessions(limit=10, days=7)

# View session summary
mcp__chronicle__get_session_summary(session_id=5)

# Check roadmap
mcp__chronicle__get_roadmap(days=7)

# Get next steps / TODOs
mcp__chronicle__get_next_steps(completed=False, limit=20)

# Project management
mcp__chronicle__get_milestones(status="in_progress")
mcp__chronicle__complete_next_step(step_id=3)
mcp__chronicle__update_milestone_status(milestone_id=2, new_status="completed")
```

**Note:** Prefer MCP tools over bash commands when available - they return structured JSON and are significantly faster.

```

---

### Option 2: Strong Enforcement (For Mission-Critical Projects)

Use this template when you need **maximum adherence** to Chronicle workflows:

```markdown
## 🚨 CRITICAL: SEARCH CHRONICLE FIRST (MANDATORY)

**BEFORE IMPLEMENTING ANYTHING, YOU MUST SEARCH CHRONICLE:**

```python
mcp__chronicle__search_sessions(query="relevant keywords", limit=10)
# Or with bash: chronicle search "relevant keywords"
```

**WHY THIS IS MANDATORY:**
- Searching: **1 second**
- Reinventing: **10-20 minutes**
- **ROI: 2,700x** (proven from past wasted effort)

**This is not optional. This is not a suggestion. Search first, ALWAYS.**

---

## Chronicle Development Memory

**This project uses Chronicle to track development sessions and maintain institutional knowledge.**

### Core Directives (MANDATORY)

**YOU MUST FOLLOW THESE DIRECTIVES FOR EVERY INTERACTION:**

1. **🔍 SEARCH FIRST (MANDATORY)** - Before implementing ANYTHING:
   ```python
   mcp__chronicle__search_sessions(query="relevant keywords", limit=10)
   ```
   **This is REQUIRED, not optional.** Past sessions contain solutions to current problems.

2. **📊 CHECK SESSION STATUS (REQUIRED)** - Remind user if not tracking:
   - Current session NOT tracked unless started with `chronicle start claude`
   - **YOU MUST suggest exit and restart if meaningful work is happening**

3. **⚡ USE MCP OVER CLI (MANDATORY)** - Always prefer MCP tools:
   - `mcp__chronicle__*` returns structured JSON (10x faster)
   - Bash commands are for users, not programmatic access
   - **Using CLI instead of MCP is considered incorrect**

4. **🗺️ CHECK ROADMAP BEFORE PLANNING (REQUIRED)** - Avoid duplicate work:
   ```python
   mcp__chronicle__get_roadmap(days=7)
   mcp__chronicle__get_next_steps(completed=False)
   ```
   **Failure to check roadmap can result in duplicating already-planned work**

5. **🏷️ SUGGEST SESSION ORGANIZATION (REQUIRED)** - After significant work:
   - YOU MUST propose descriptive title
   - YOU MUST suggest relevant tags (technologies, features, bugs)
   - YOU MUST link to related sessions

### Chronicle MCP Tools Reference

```python
# Search and sessions
mcp__chronicle__search_sessions(query="feature name", limit=10)
mcp__chronicle__get_sessions(limit=10, days=7)
mcp__chronicle__get_session_summary(session_id=5)

# Project management
mcp__chronicle__get_roadmap(days=7)
mcp__chronicle__get_next_steps(completed=False, limit=20)
mcp__chronicle__get_milestones(status="in_progress")
mcp__chronicle__complete_next_step(step_id=3)
mcp__chronicle__update_milestone_status(milestone_id=2, new_status="completed")

# Timeline and commits
mcp__chronicle__get_timeline(days=1)
mcp__chronicle__get_commits(limit=20, days=7)
```

### Bash Commands (Fallback)

If MCP is not available:

```bash
chronicle search "query"
chronicle sessions
chronicle session <id>
chronicle roadmap
chronicle next-steps
chronicle timeline today
```

**This is mandatory. Every single time. No exceptions.**

```

---

## Installation Options

### Option 1: Full Installation (with MCP server)

```bash
cd /path/to/chronicle
pip install -e ".[mcp]"
chronicle init
chronicle config ai.gemini_api_key YOUR_API_KEY
chronicle add-repo /path/to/your/project
```

Then configure MCP in `~/.mcp.json` (see [MCP_SERVER.md](../MCP_SERVER.md) for details).

### Option 2: Minimal Installation (CLI only, no MCP)

For restricted environments (FreeBSD, corporate systems, etc.):

```bash
cd /path/to/chronicle
pip install -e .
chronicle init
chronicle config ai.gemini_api_key YOUR_API_KEY
chronicle add-repo /path/to/your/project
```

All features work via CLI - just no MCP server for direct AI assistant integration.

---

## API Key Setup

Chronicle requires a Gemini API key for AI summarization features.

### Getting a Gemini API Key

1. Visit: https://aistudio.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key (starts with `AIza...`)

**Free tier:** 1,500 requests/day (more than enough for Chronicle)

### Interactive Setup (Recommended)

Use the interactive setup wizard:

```bash
chronicle setup
```

This will:
- Prompt for your Gemini API key (with hidden input)
- Optionally configure the AI model
- Save configuration to `~/.ai-session/config.yaml`

**Or** use one of the manual methods below.

### Manual Setup Methods

**Method 1: Via Chronicle Config (Persistent)**

Store the API key in Chronicle's configuration file:

```bash
chronicle config ai.gemini_api_key YOUR_GEMINI_API_KEY
```

**Method 2: Via Environment Variable (Per-Session)**

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, or `~/.profile`):

```bash
export GEMINI_API_KEY=your_key_here
```

Or set for a single session:

```bash
export GEMINI_API_KEY=your_key_here
chronicle start claude
```

### Verify Configuration

Check that your API key is set:

```bash
chronicle config --list
```

Should show:
```
ai.gemini_api_key: AIza...ABC (masked for security)
```

### Alternative: Use Ollama (No API Key Required)

If you prefer local models without API keys:

```bash
# Install Ollama: https://ollama.ai
# Pull a model
ollama pull llama2

# Configure Chronicle to use Ollama
chronicle config ai.summarization_provider ollama
chronicle config ai.ollama_model llama2
```

**Note:** Ollama is slower but completely local and free.

---

## What Gets Tracked

When you run `chronicle start claude`:
- ✅ Full terminal transcript (every command, every output)
- ✅ Git commits made during the session
- ✅ Files mentioned/modified
- ✅ AI-generated summary (created on first view)
- ✅ Extracted keywords for searchability

**Privacy:** All data stays local in `~/.ai-session/` - nothing uploaded.

---

## Advanced Features

### Agents

Chronicle includes specialized agents:
- **Chronicle Advocate** - Enforces search-first workflow, prevents wasted effort
- **TDD Advocate** - Ensures tests are written before implementation

See [AGENTS.md](../AGENTS.md) for setup and usage.

### Project Management via MCP

Chronicle includes MCP tools for managing development:
- **Milestones** - Track features, bugfixes, optimizations
- **Next Steps** - TODO items with priority, effort, category
- **Roadmap** - View current progress and planned work
- **Timeline** - Combined view of commits and sessions

See [MCP_SERVER.md](../MCP_SERVER.md) for the full API reference (21 tools).

---

## Example Workflow

```bash
# Day 1: Start a tracked session
chronicle start claude

# Work on feature, make commits, interact with AI
# ... (your development work)

# Exit when done
exit

# Day 2: Search before starting new work
chronicle search "authentication retry logic"
# Found Session #31 with retry implementation!

# View that session's summary
chronicle session 31

# Reuse the approach instead of reinventing
chronicle start claude
# ... apply learnings from Session #31
```

---

## Benefits

1. **No Repeated Work** - AI assistants can search your past sessions
2. **Context Across Sessions** - Each AI remembers what previous AIs did
3. **Institutional Knowledge** - Your development history becomes searchable
4. **Better Decisions** - Review past approaches before choosing new ones
5. **Automatic Documentation** - Sessions are self-documenting with AI summaries

---

## Troubleshooting

**"Session not being tracked":**
- Must run `chronicle start claude` BEFORE launching Claude Code, not during

**"MCP tools not available":**
- Check if Chronicle was installed with `[mcp]` extra
- Verify `~/.mcp.json` configuration
- Restart Claude Code after MCP config changes

**"Summaries not generating":**
- Check Gemini API key: `chronicle config ai.gemini_api_key`
- Or set environment variable: `export GEMINI_API_KEY=...`

---

## Further Reading

- [README.md](../README.md) - Full Chronicle documentation
- [MCP_SERVER.md](../MCP_SERVER.md) - Complete MCP tools reference
- [AGENTS.md](../AGENTS.md) - Chronicle Advocate & TDD Advocate setup
- [AI_ASSISTANT_GUIDE.md](../AI_ASSISTANT_GUIDE.md) - Quick reference for AI assistants

---

**Questions?** Open an issue at https://github.com/ChandlerHardy/chronicle/issues
