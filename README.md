# Chronicle - AI Session Recorder

<p align="center">
  <img src="public/chronicle_paragraph.png" alt="Chronicle - Local-first development session recorder with AI-powered search" width="800">
</p>

> **Give your AI assistants a memory. Track every decision, search past conversations, and never lose context across sessions.**

[![Tests](https://img.shields.io/badge/tests-25%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()
[![MCP](https://img.shields.io/badge/MCP-enabled-purple)]()
[![Phase](https://img.shields.io/badge/phase-5%20complete-success)]()

---

## 💡 Value Proposition

**The Problem:** You spend hours discussing architecture decisions with Claude Code on Monday. On Friday, you switch to a new project and Claude has zero memory of what you decided. You waste time re-explaining context, rediscovering solutions, and repeating conversations across different AI tools.

**Chronicle solves this** by creating a searchable, AI-powered memory system for all your development work:

- 🧠 **Persistent AI Memory** - Your AI assistants can query Chronicle to remember what you discussed last week, last month, or last year
- 🔍 **Cross-Session Intelligence** - "How did I implement authentication in that other project?" → Instant answer from past sessions
- 📊 **Development Insights** - See patterns in your workflow, track time across projects, generate weekly summaries
- 🤝 **Multi-AI Coordination** - Claude, Gemini, and Qwen can all access the same knowledge base
- 🔒 **100% Local** - Everything stays on your machine. No cloud sync, no data sharing, full privacy.

**Perfect for:**
- **Solo Developers** - Never forget why you made that architectural decision 3 months ago
- **Consultants & Contractors** - Track billable hours, generate client reports, document decisions
- **Multi-Project Engineers** - "What did I do on ProjectX last week?" → Instant answer
- **AI Power Users** - Get the most out of Claude, Gemini, Cursor, etc. with persistent context
- **Teams** - Build institutional knowledge from AI-assisted development
- **Open Source Maintainers** - Document discussions and decisions for contributors

---

## 🎬 Quick Demo

```bash
# Day 1: Work on authentication
$ chronicle start claude
> You discuss OAuth2 implementation with Claude for 2 hours
> Make several commits
$ exit

# Day 30: Different project, need to remember
$ chronicle start claude
You: "How did I implement OAuth2 in that other project?"

Claude: [Uses Chronicle MCP server]
        → search_sessions("OAuth2")
        → get_session_summary(session_id=5)

Claude: "In session 5 from last month, you implemented OAuth2 with
         the 'authorization_code' flow. Key decisions:
         - Used Auth0 for identity provider
         - Stored tokens in httpOnly cookies
         - Implemented refresh token rotation
         Files: src/auth/oauth.ts, src/middleware/auth.ts"

You: "Perfect! Do the same thing for this project"
# No time wasted re-explaining context! 🎯
```

---

## 🎯 The Problem (Detailed)

Modern developers use multiple AI coding assistants, but face critical challenges:

**Memory Loss**
- ❌ Each AI session starts from scratch with zero context
- ❌ "What did we decide about authentication 2 weeks ago?" 🤷
- ❌ Repeat the same explanations across different AI tools
- ❌ Lost context when switching between Claude Code, Gemini CLI, Cursor

**Tracking Difficulty**
- ❌ No record of decisions made during AI-assisted development
- ❌ Hard to remember which AI tool helped with which feature
- ❌ Can't search through past AI conversations
- ❌ Lost connection between commits and the AI sessions that created them

**Multi-Project Chaos**
- ❌ Work on 5 different projects? Good luck remembering what you did where
- ❌ Client asks "what did we build last sprint?" → scramble through git logs
- ❌ No easy way to generate weekly summaries or progress reports

## ✨ The Solution

Chronicle is a **local-first development memory system** that gives AI assistants persistent context:

**Core Features:**
- 🎯 **Full Session Recording** - Complete transcripts of Claude Code, Gemini CLI, Qwen Code sessions
- 🔗 **Commit Linking** - Automatically connects git commits to the AI sessions that created them
- 🤖 **AI-Powered Summaries** - Intelligent summaries with key decisions, blockers, and file changes
- 🔍 **Instant Search** - Find past conversations, decisions, and implementations in seconds
- 📊 **Multi-Project Tracking** - Automatically organizes work by repository
- 🔌 **MCP Server** - AI assistants can query Chronicle database directly via Model Context Protocol
- 📝 **Obsidian Integration** - Optional export to markdown vault for knowledge graph visualization
- 🔒 **100% Local** - Everything stored in SQLite on your machine (no cloud required)

---

## 🚀 Quick Start

### Installation

#### Standard Installation (with MCP server support)

```bash
# Clone and install with MCP support
git clone https://github.com/ChandlerHardy/chronicle
cd chronicle
python3 -m pip install -e ".[mcp]"

# Initialize Chronicle
chronicle init

# Configure Gemini API for summarization (interactive)
chronicle setup

# Add a repository to track
chronicle add-repo /path/to/your/project
```

#### Minimal Installation (CLI only, no MCP server)

For environments where you can't install Rust dependencies (e.g., restricted FreeBSD systems), you can install Chronicle without MCP support:

```bash
# Clone and install without MCP dependencies
git clone https://github.com/ChandlerHardy/chronicle
cd chronicle
python3 -m pip install -e .

# All CLI commands work normally
chronicle init
chronicle setup  # Configure API key
chronicle start claude
chronicle sessions
chronicle search "your query"
```

**Note:** Without MCP support, AI assistants cannot query Chronicle directly. All features work via CLI.

### Basic Usage

```bash
# View today's activity (commits + AI interactions)
chronicle show today

# Start an interactive AI session (auto-recorded)
chronicle start claude      # Claude Code
chronicle start gemini      # Gemini CLI
chronicle start qwen        # Qwen Code CLI

# View all sessions
chronicle sessions
chronicle sessions --limit 20                   # Show more sessions
chronicle sessions --repo /path/to/project      # Filter by repository

# View a session with AI-generated summary
chronicle session 5

# AI-powered summaries of your work
chronicle summarize today                       # Today's accomplishments
chronicle summarize week                        # Weekly digest
chronicle summarize today --repo /path/repo     # Per-project summaries

# See combined timeline
chronicle timeline today

# Search history
chronicle search "authentication"
```

### Updating Chronicle

Chronicle includes a built-in update command that handles everything automatically:

```bash
# Check for and install updates
chronicle update

# Check what's available without installing
chronicle update --check-only
```

**What it does:**
- ✅ Checks for new commits from GitHub
- ✅ Shows what's changed (commit log)
- ✅ Pulls latest code
- ✅ Auto-detects if dependencies changed
- ✅ Reinstalls with correct mode (MCP or minimal)
- ✅ Auto-migrates database if schema changed

**Manual update:**
```bash
cd /path/to/chronicle
git pull origin main
pip install -e ".[mcp]"  # Or: pip install -e .
```

---

## 📖 Core Concepts

### Chronicle vs CLAUDE.md

**CLAUDE.md** is static project documentation:
- ✅ Project structure, conventions, tech stack
- ✅ Written manually, read by AI at session start
- ✅ Describes "how this project works"

**Chronicle** is dynamic session recording:
- ✅ Automatic tracking of what you actually did
- ✅ Cross-AI session history (Claude, Gemini, Qwen)
- ✅ Searchable timeline of decisions and changes
- ✅ Describes "what happened and why"

**They're complementary!** CLAUDE.md tells the AI about your project, Chronicle tells YOU what you did.

---

## 🎮 Features

### ✅ Phase 1: Git Commit Tracking (COMPLETE)

Track git commits and link them to development activity:

```bash
chronicle add-repo /path/to/project    # Import commits
chronicle show today                    # View today's commits
chronicle search "bug fix"              # Search commit messages
chronicle stats /path/to/project        # Repository statistics
```

**Features:**
- Auto-scan git repositories for commits
- Store commit metadata (SHA, message, files, author, timestamp)
- Prevent duplicates
- Search by message content
- Filter by date range

---

### ✅ Phase 2: AI Interaction Tracking (COMPLETE)

#### Interactive Session Wrapper

Record full AI coding sessions with transcript capture:

```bash
chronicle start claude      # Start Claude Code session
chronicle start gemini      # Start Gemini CLI session
chronicle start qwen        # Start Qwen Code CLI session

# Work normally in the AI tool...
# Full transcript is recorded automatically

exit                        # Session saved!

chronicle sessions          # List all sessions
chronicle session 5         # View session details
```

**Features:**
- Full terminal transcript capture using Unix `script` command
- Records all input/output from AI conversations
- Automatic timestamp tracking
- Session duration calculation
- Lazy summarization (transcript saved immediately, summary generated on-demand)

#### One-Shot AI Commands

For quick questions to Gemini or Qwen:

```bash
chronicle ask "How do I optimize this query?" --tool gemini
chronicle ask "Review this code for bugs" --tool qwen
chronicle ask "Test question" --tool gemini --log-only
```

#### CLI Commands

```bash
chronicle ai today              # View today's AI interactions
chronicle ai yesterday          # Yesterday's interactions
chronicle ai week               # Last 7 days

chronicle ai-stats              # Usage statistics with charts
chronicle ai-stats --days 30    # Last 30 days

chronicle timeline today        # Combined commits + AI interactions
```

**Features:**
- AI interaction logging (prompt, response, duration)
- Auto-link interactions to commits (30-minute window)
- Multi-tool support (Claude Code, Gemini CLI, Qwen Code)
- Beautiful terminal output with tool-specific emojis (🎯 Claude, ✨ Gemini, 🔮 Qwen)
- Usage statistics with visual charts

---

### 🔧 Configuration System (COMPLETE)

Manage Chronicle settings with YAML config:

```bash
chronicle config --list                          # View all settings
chronicle config ai.gemini_api_key              # View API key (masked)
chronicle config ai.gemini_api_key YOUR_KEY     # Set API key
chronicle config ai.default_model               # View default model
```

**Config file:** `~/.ai-session/config.yaml`

**Available settings:**
- `ai.gemini_api_key` - Gemini API key for summarization
- `ai.default_model` - Default Gemini model (gemini-2.0-flash-exp)
- `ai.summarization_provider` - Summarization provider (gemini or ollama)
- `ai.ollama_model` - Ollama model name (qwen2.5:32b)
- `ai.ollama_host` - Ollama host URL (http://localhost:11434)
- `ai.auto_summarize_sessions` - Auto-summarize on session exit
- `retention.raw_data_days` - How long to keep raw transcripts (7 days)
- `retention.summaries_days` - How long to keep summaries (90 days)

**Security:**
- API keys masked in display
- Environment variable support (`GEMINI_API_KEY`)
- Config file excluded from git (`.gitignore`)

---

### ✅ Phase 3: AI Summarization (COMPLETE)

AI-powered summarization with multiple provider options:

#### Setup

**Option 1: Gemini (Cloud, 1M token context)**
```bash
# Configure Gemini API key
chronicle config ai.gemini_api_key YOUR_KEY
chronicle config ai.summarization_provider gemini
chronicle config ai.default_model gemini-2.0-flash-exp

# Test connection
chronicle test-gemini
```

**Option 2: Ollama (Local, unlimited)**
```bash
# Install and run Ollama first: https://ollama.ai
ollama pull qwen2.5:32b

# Configure Chronicle
chronicle config ai.summarization_provider ollama
chronicle config ai.ollama_model qwen2.5:32b
chronicle config ai.ollama_host http://localhost:11434
```

#### View Session with Auto-Summary

```bash
chronicle sessions              # List all sessions
chronicle session 5             # View session #5

# First time: Automatically generates AI summary
# Subsequent views: Shows cached summary (instant!)
```

#### Summarize Large Sessions with Qwen/Gemini CLI

For large sessions that exceed Gemini API rate limits, use Qwen CLI or Gemini CLI directly:

```bash
chronicle summarize-session 8              # Use Qwen CLI (default, 2000 req/day)
chronicle summarize-session 8 --provider gemini  # Use Gemini CLI
```

This bypasses API token-per-minute limits by calling the CLI tools directly.

#### Generate Daily/Weekly Summaries

```bash
chronicle summarize today       # AI summary of today's work
chronicle summarize week        # AI summary of last 7 days
```

**Features:**
- **Multi-provider support** - Choose between Gemini (cloud, 1M context) or Ollama (local, unlimited)
- **Transcript cleaning** - Removes ANSI codes and duplicates (typically 50-90% size reduction)
- **Lazy summarization** - Summaries generated on-demand, not blocking
- **Auto-caching** - Generate once, view instantly forever
- **Intelligent prompts** - Extracts key decisions, files modified, blockers
- **Markdown formatting** - Beautiful, structured summaries
- **Multi-source analysis** - Analyzes both git commits and AI sessions

**Example Summary:**
```
## What Was Built
- Implemented Phase 3 summarization with Gemini API integration
- Added chronicle session command with auto-summarization

## Key Decisions
- Used lazy loading to avoid blocking session exit
- Cached summaries in database for instant retrieval

## Files/Components Modified
- backend/cli/commands.py
- backend/cli/formatters.py
- backend/services/summarizer.py
```

---

### 🗂️ Multi-Project Organization

Chronicle automatically tracks which repository each session belongs to:

#### Automatic Repository Detection

When you start a session, Chronicle automatically:
- Detects your current working directory
- Finds the git repository root (if in a git repo)
- Associates the session with that project

```bash
cd /Users/you/repos/my-app
chronicle start claude
# Session automatically tagged with "my-app" repository
```

#### Filter by Repository

View sessions, timelines, and summaries for specific projects:

```bash
# View sessions for a specific project
chronicle sessions --repo /Users/you/repos/my-app

# Summarize work on specific project
chronicle summarize today --repo /Users/you/repos/my-app
chronicle summarize week --repo /Users/you/repos/other-project

# Timeline for specific project
chronicle timeline today --repo /Users/you/repos/my-app
```

**Benefits:**
- Track work across multiple projects separately
- "What did I do on project X this week?"
- Organize sessions by codebase
- Perfect for contractors juggling multiple clients

---

### ✅ Phase 4: MCP Server + AI Integration (COMPLETE)

Give your AI assistants the ability to query Chronicle's database directly!

#### Chronicle MCP Server

The Chronicle MCP (Model Context Protocol) server allows **any MCP-compatible AI** (Claude Code, ChatGPT, etc.) to query your Chronicle database and retrieve past sessions, commits, and decisions.

**Setup:**

1. **Install Chronicle with MCP support:**
   ```bash
   pip install -e .
   ```

2. **Configure MCP client** (e.g., `~/.mcp.json`):
   ```json
   {
     "mcpServers": {
       "chronicle": {
         "command": "python3",
         "args": ["/path/to/chronicle/scripts/chronicle-mcp"]
       }
     }
   }
   ```

3. **Restart your AI tool** (Claude Code, etc.)

4. **Verify:** Type `/mcp` to see available servers

**Available MCP Tools:**

The Chronicle MCP server provides 21 tools that AI assistants can use:

**Session & Commit Queries:**
| Tool | Purpose | Example |
|------|---------|---------|
| `get_sessions` | List recent sessions | "Show me sessions from this week" |
| `get_session_summary` | Get session details | "What happened in session 15?" |
| `search_sessions` | Search session content | "Find where we discussed authentication" |
| `get_sessions_summaries` | Batch retrieve summaries | "Get summaries for sessions 5, 6, 7" |
| `get_commits` | List git commits | "Show commits from the my-app repo" |
| `search_commits` | Search commit messages | "Find bug fix commits" |
| `get_timeline` | Combined view | "Show me today's work" |
| `get_stats` | Usage statistics | "How much did I use AI tools this month?" |

**Project Management (CRUD Operations):**
| Tool | Purpose | Example |
|------|---------|---------|
| `get_milestones` | List milestones | "Show in-progress features" |
| `get_milestone` | Get milestone details | "What's milestone 3 about?" |
| `create_milestone` | Create new milestone | "Plan new authentication feature" |
| `update_milestone` | Edit milestone | "Update priority to 1" |
| `delete_milestone` | Remove milestone | "Delete test milestone" |
| `update_milestone_status` | Change status | "Mark as completed" |
| `get_next_steps` | List TODOs | "What should I work on?" |
| `create_next_step` | Add TODO | "Create task to write tests" |
| `update_next_step` | Edit TODO | "Change priority" |
| `delete_next_step` | Remove TODO | "Delete obsolete task" |
| `complete_next_step` | Mark done | "Mark step 5 as done" |
| `uncomplete_next_step` | Reopen TODO | "Reopen completed task" |
| `get_roadmap` | Project overview | "Show current roadmap" |

**Real-World Example:**

```
You: "How did I implement caching in that other project last month?"

Claude: [Uses Chronicle MCP]
         → search_sessions("caching")
         → get_session_summary(session_id=42)

Claude: "In session 42 from September 15th, you implemented Redis
         caching for the API endpoints. Here's what you decided..."
```

**Benefits:**
- 🧠 AI assistants have persistent memory across sessions
- 🔍 Instant context retrieval from past work
- 📊 AI can analyze patterns in your workflow
- 🤝 Works with any MCP-compatible AI tool
- 🔒 100% local (no data leaves your machine)

**Documentation:** See [MCP_SERVER.md](MCP_SERVER.md) for full details.

---

### 🎯 Claude Skills Integration

For Claude Code users, Chronicle provides pre-built **Claude Skills** that automate common workflows:

**Available Skills:**

1. **chronicle-session-documenter**
   - Automatically documents sessions to Obsidian vault
   - Creates structured markdown notes with metadata
   - Links related sessions, commits, and repos

2. **chronicle-context-retriever**
   - Searches past sessions for relevant context
   - Triggered by questions like "how did I..." or "what did we..."
   - Provides summaries of past decisions

3. **chronicle-workflow**
   - Complete Chronicle workflow guidance
   - Best practices for multi-project tracking
   - Helps set up and optimize Chronicle usage

**Installation:**
```bash
# One-time setup in Claude Code
/plugin marketplace add ChandlerHardy/chronicle
/plugin install chronicle-workflow-skills@chronicle-skills
```

**How It Works:**

Skills are "smart prompt templates" that automatically trigger when relevant:

```
You: "Document session 15 to my Obsidian vault"

Claude: [Automatically uses chronicle-session-documenter skill]
        → Retrieves session summary
        → Creates markdown note with frontmatter
        → Adds wikilinks to related sessions
        → Saves to vault at Chronicle/Sessions/Session-15.md
```

**Documentation:** See `chronicle-skills/README.md` for details.

---

### 🤖 Intelligent Agents (Cross-Platform)

Chronicle includes two **specialized agents** that proactively enforce best practices. Unlike skills (Claude Code only), **agent prompts work across platforms** - adaptable for Cursor, Windsurf, and other AI assistants.

**Available Agents:**

1. **Chronicle Advocate Agent**
   - Reminds to search Chronicle before implementing (2,700x ROI!)
   - Checks if session is being tracked
   - Enforces MCP usage over slow CLI commands
   - Suggests organizing sessions with titles/tags
   - Prevents repeating work from past sessions

2. **TDD Advocate Agent**
   - Encourages test-driven development workflow
   - Reminds to write tests before implementation
   - Runs pytest after code changes
   - Ensures all tests pass before commits
   - Celebrates test successes ✅

**Setup (Claude Code):**
```bash
# Use the /agents command in Claude Code
/agents
# Select "Create new agent"
# Copy prompts from AGENTS.md
# Restart Claude Code to activate
```

**Key Advantage:** Agent prompts are portable! The same prompt works in:
- Claude Code (via `/agents`)
- Cursor (via `.cursorrules`)
- Windsurf (via project config)
- Any AI tool with custom instructions

**Documentation:** See **[AGENTS.md](AGENTS.md)** for full prompts and cross-platform setup.

---

### 📝 Obsidian Integration (Optional)

Export Chronicle sessions to Obsidian for visual knowledge graphs and bidirectional linking.

**Setup:**

Configure the Obsidian MCP server in `~/.mcp.json`:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "npx",
      "args": [
        "@mauricio.wolff/mcp-obsidian@latest",
        "/path/to/your/obsidian/vault"
      ]
    }
  }
}
```

**Features:**
- Export sessions as markdown notes with YAML frontmatter
- Wikilinks between related sessions and commits
- Tag-based organization for Obsidian graph view
- Repository-based folder structure
- Search entire vault from Claude Code

**Example Vault Structure:**
```
Chronicle/
├── Repos/
│   ├── my-app/
│   │   ├── Sessions/
│   │   │   ├── Session-15.md
│   │   │   └── Session-16.md
│   │   └── Commits/
│   └── other-project/
│       └── Sessions/
└── Daily/
    └── 2025-10-20.md
```

**Coming Soon:** `chronicle export obsidian` command for batch export.

---

## 📊 Example Outputs

### Daily Summary

```bash
$ chronicle show today

Development Session - October 19, 2025
════════════════════════════════════════════════════════════
╭──────────────────────────────────────────────────────────╮
│ Session Statistics                                       │
│ • Commits: 5                                             │
│ • Files Changed: 12                                      │
│ • Repositories: 2                                        │
│ • Authors: 1                                             │
╰──────────────────────────────────────────────────────────╯

Commits
────────────────────────────────────────────────────────────
10:30 AM [abc1234] Add user authentication
   → src/auth.ts
   → src/middleware.ts

02:15 PM [def5678] Update README with usage examples
   → README.md
```

### AI Interaction Timeline

```bash
$ chronicle ai today

AI Interactions Today
────────────────────────────────────────────────────────────
02:30 PM ✨ Gemini
   "How do I implement caching in Python?"
   → You can use functools.lru_cache decorator...
   ⏱ 2.3s
   ✓ Linked to commit abc1234

01:45 PM 🔮 Qwen
   "Review this authentication code"
   → The code looks good overall. Consider adding rate limiting...
   ⏱ 3.1s
```

### AI Usage Statistics

```bash
$ chronicle ai-stats --days 7

AI Tool Usage (Last 7 days)
════════════════════════════════════════════════════════════
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ AI Tool  ┃  Interactions ┃   Percentage ┃  Avg Duration ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Claude   │            15 │        65.2% │         4.2s  │
│          │               │ █████████░░░ │               │
│ Gemini   │             6 │        26.1% │         2.1s  │
│          │               │ █████░░░░░░░ │               │
│ Qwen     │             2 │         8.7% │         3.5s  │
│          │               │ █░░░░░░░░░░░ │               │
└──────────┴───────────────┴──────────────┴───────────────┘

Total interactions: 23
```

### Combined Timeline

```bash
$ chronicle timeline today

Combined Development Timeline
════════════════════════════════════════════════════════════
02:30 PM ✨ Gemini
   "How do I implement caching in Python?"

02:25 PM [abc1234] Add caching to API endpoints
   → api/cache.py
   → api/endpoints.py

01:45 PM 🎯 Claude (Session, 45m)
   "Built authentication system"
   → src/auth.ts
   → src/middleware.ts
   ✓ Linked to commit def5678

01:30 PM [def5678] Implement JWT authentication
   → auth/jwt.ts
```

---

## 🗂️ Database Schema

Chronicle uses SQLite for local-first storage at `~/.ai-session/sessions.db`:

### Tables

**commits** - Git commit tracking
- timestamp, SHA, message, files_changed (JSON)
- branch, author, repo_path

**ai_interactions** - AI tool interactions
- timestamp, ai_tool, prompt, response_summary
- duration_ms, files_mentioned (JSON)
- is_session, session_transcript, summary_generated
- related_commit_id (foreign key)

**daily_summaries** - Daily development summaries (Phase 3)
- date, summary, topics (JSON), files_affected (JSON)
- commits_count, ai_interactions_count, key_decisions (JSON)

### Data Storage

- **Database:** `~/.ai-session/sessions.db`
- **Session transcripts:** `~/.ai-session/sessions/session_N.log`
- **Session metadata:** `~/.ai-session/sessions/session_N.meta`
- **Configuration:** `~/.ai-session/config.yaml`

---

## 🧪 Testing

Chronicle has comprehensive test coverage:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend tests/

# Current status: 16 passing tests
# - 8 tests for git monitoring
# - 8 tests for AI tracking
```

---

## 🛣️ Roadmap

### ✅ Phase 1: Git Tracking (COMPLETE)
- [x] Git commit monitoring
- [x] CLI query interface
- [x] Search and statistics
- [x] 8 passing tests

### ✅ Phase 2: AI Tracking (COMPLETE)
- [x] AI interaction logging
- [x] Session wrapper for Claude/Gemini/Qwen
- [x] Multi-AI timeline view
- [x] Usage statistics
- [x] Configuration system
- [x] 8 passing tests

### ✅ Phase 3: Summarization (COMPLETE)
- [x] Gemini API integration
- [x] Ollama local LLM support
- [x] `chronicle session` command with auto-summarization
- [x] `chronicle summarize today/week` commands
- [x] Chunked summarization for unlimited session sizes
- [x] Lazy loading with caching
- [x] Intelligent prompt engineering
- [x] Markdown-formatted summaries
- [x] Multi-project tracking and filtering

### ✅ Phase 4: MCP Server + AI Integration (COMPLETE)
- [x] Chronicle MCP server with 21 tools (8 query + 13 project management)
- [x] Full CRUD operations for milestones and next steps
- [x] FastMCP framework integration
- [x] Read/write database access for AI tools
- [x] Support for any MCP-compatible AI (Claude, ChatGPT, etc.)
- [x] Obsidian MCP server integration
- [x] Claude Skills marketplace integration
- [x] 3 pre-built skills (documenter, retriever, workflow)
- [x] Multi-repository session organization
- [x] Comprehensive documentation (MCP_SERVER.md)

### ✅ Phase 5: Project Tracking & Meta-Development (COMPLETE)

**Chronicle now tracks its own development!** Database-backed milestones and next steps eliminate manual documentation updates.

#### The Innovation: Database-Tracked TODOs

Instead of maintaining DEVELOPMENT_HISTORY.md manually, Chronicle tracks project state in its database:

```bash
# Plan a feature
chronicle milestone "Add authentication" \
  --description "Implement OAuth2 with Auth0" \
  --type feature \
  --priority 1 \
  --tags "backend,auth,security"

# Break down into actionable tasks
chronicle next-step "Design auth flow" --priority 1 --effort medium --milestone 1
chronicle next-step "Implement OAuth2 client" --priority 1 --effort large --milestone 1
chronicle next-step "Add token refresh" --priority 2 --effort medium --milestone 1
chronicle next-step "Write integration tests" --priority 2 --effort small --milestone 1
chronicle next-step "Update API documentation" --priority 3 --effort small --milestone 1

# Mark milestone as active
chronicle milestone-status 1 in_progress

# As you work, link sessions to the milestone
chronicle start claude
# ... work on authentication ...
exit
chronicle link-session 18 --milestone 1

# Complete tasks as you finish them
chronicle next-step-complete 1
chronicle next-step-complete 2

# View project progress anytime
chronicle roadmap
```

**Output:**
```
Chronicle Development Roadmap

🚧 In Progress
  • Add authentication (feature, 3 sessions)

🔜 Next Steps
  • [P2] Add token refresh [medium]
  • [P2] Write integration tests [small]
  • [P3] Update API documentation [small]

📊 Milestones: 5/12 completed | Next Steps: 2/5 done
```

#### Why This Is Revolutionary

**Before (manual documentation):**
- ❌ Manually update DEVELOPMENT_HISTORY.md after every feature
- ❌ Forget to document work-in-progress
- ❌ Can't query "what's next?" programmatically
- ❌ No link between sessions and features
- ❌ Documentation becomes stale

**After (database-tracked):**
- ✅ **Queryable by AI** - "What should I work on next?" → Instant answer from database
- ✅ **Auto-linked** - Sessions automatically connect to milestones
- ✅ **Real-time roadmap** - `chronicle roadmap` shows current state
- ✅ **Report generation** - Query completed milestones for weekly summaries
- ✅ **Dogfooding** - Chronicle tracks building Chronicle!

#### CLI Commands

**Milestones:**
```bash
chronicle milestone <title>                    # Create milestone
chronicle milestones                           # List all milestones
chronicle milestones --status in_progress      # Filter by status
chronicle milestones --type feature            # Filter by type
chronicle milestone-show <id>                  # View details
chronicle milestone-status <id> <status>       # Update status
chronicle milestone-complete <id>              # Mark complete
```

**Next Steps:**
```bash
chronicle next-step <description>              # Add TODO
chronicle next-steps                           # List pending
chronicle next-steps --all                     # Include completed
chronicle next-steps --milestone <id>          # Filter by milestone
chronicle next-step-complete <id>              # Mark done
```

**Project Management:**
```bash
chronicle link-session <session_id> --milestone <id>   # Link session
chronicle roadmap                                      # View progress
chronicle roadmap --days 30                            # Last 30 days
```

#### MCP Tools (AI-Queryable)

AI assistants can query and manage project state via Chronicle MCP server:

```python
# Read Operations
milestones = mcp__chronicle__get_milestones(status="in_progress")
roadmap = mcp__chronicle__get_roadmap(days=7)
steps = mcp__chronicle__get_next_steps(milestone_id=1, completed=False)

# Create Operations
new_milestone = mcp__chronicle__create_milestone(
    title="Add export feature",
    description="Export sessions to PDF/Markdown",
    milestone_type="feature",
    priority=2,
    tags="phase-7,export"
)
new_step = mcp__chronicle__create_next_step(
    description="Write export logic",
    priority=1,
    effort="large",
    category="feature",
    milestone_id=4
)

# Update Operations
mcp__chronicle__update_milestone(milestone_id=4, priority=1, tags="urgent,export")
mcp__chronicle__update_next_step(step_id=12, effort="medium", category="optimization")
mcp__chronicle__update_milestone_status(milestone_id=1, new_status="completed")

# Complete/Reopen
mcp__chronicle__complete_next_step(step_id=5)
mcp__chronicle__uncomplete_next_step(step_id=5)  # Reopen if needed

# Delete Operations (with confirmation)
mcp__chronicle__delete_next_step(step_id=99, confirm=True)
mcp__chronicle__delete_milestone(milestone_id=99, confirm=True)
```

**AI Use Cases:**
- "What should I work on next?" → Queries roadmap, suggests highest priority
- "What's the status of authentication work?" → Finds milestone, shows linked sessions
- "Generate a weekly progress report" → Queries completed milestones, summarizes
- "Mark this session as working on feature X" → Auto-links session to milestone

#### Chronicle Skills

**New: chronicle-project-tracker**
- Complete workflow for planning features
- Querying roadmap via MCP
- Linking sessions to milestones
- Generating progress reports
- Auto-documentation patterns

Use: "What's in our roadmap?" or "Plan a new feature" → Skill loads automatically

#### Database Schema

**project_milestones:**
- `id`, `title`, `description`
- `status` - planned, in_progress, completed, archived
- `milestone_type` - feature, bugfix, optimization, documentation
- `priority` - 1 (highest) to 5 (lowest)
- `related_sessions` - JSON array of session IDs
- `related_commits` - JSON array of commit SHAs
- `tags` - JSON array for filtering

**next_steps:**
- `id`, `description`, `priority`
- `estimated_effort` - small, medium, large
- `category` - feature, optimization, fix, docs
- `completed` - boolean
- `related_milestone_id` - FK to milestone

#### Example: Real Meta-Development

Chronicle used itself to build this feature:

```bash
# Created milestone #1
chronicle milestone "Add project tracking to Chronicle" \
  --type feature --priority 1 --tags "phase-5,meta,dogfooding"

# Broke down work
chronicle next-step "Design database schema" --priority 1 --effort medium --milestone 1
chronicle next-step "Add CLI commands" --priority 1 --effort large --milestone 1
chronicle next-step "Add MCP tools" --priority 1 --effort medium --milestone 1
chronicle next-step "Create Chronicle Skills" --priority 2 --effort medium --milestone 1
chronicle next-step "Write tests" --priority 2 --effort small --milestone 1

# Marked in progress
chronicle milestone-status 1 in_progress

# As work completed
chronicle next-step-complete 1  # Schema done
chronicle next-step-complete 2  # CLI done
chronicle next-step-complete 3  # MCP tools done
chronicle next-step-complete 4  # Skills done
chronicle next-step-complete 5  # Tests done (25 passing!)

# Finished!
chronicle milestone-complete 1

# Result
chronicle roadmap
# ✅ Completed (last 7 days)
#   • Add project tracking to Chronicle (Oct 22)
# 📊 Milestones: 1/1 completed | Next Steps: 5/5 done
```

**Chronicle now uses Chronicle to build Chronicle!** 🎯

---

### 🔮 Future Phases
- [ ] Next.js web dashboard with roadmap visualization
- [ ] Timeline UI showing milestones + sessions + commits
- [ ] `chronicle export obsidian` - Batch export with milestone linking
- [ ] Blog post generator from weekly summaries
- [ ] Auto-generate DEVELOPMENT_HISTORY.md from milestones
- [ ] Team features (shared Chronicle databases)
- [ ] VS Code extension
- [ ] GitHub Actions integration for PR descriptions

---

## 🏗️ Architecture

### Local-First Design

Chronicle is designed to be **private and fast**:
- ✅ All data stored in local SQLite database
- ✅ No cloud sync required (optional in future)
- ✅ Works offline
- ✅ Full control over your data

### Lazy Summarization

Sessions are recorded immediately, summaries generated on-demand:

```
Session Start
    ↓
Record full transcript → Save to DB (fast!)
    ↓
On first view → Generate summary with Gemini
    ↓
Cache summary for future views
```

**Benefits:**
- Fast session exit (no waiting for summarization)
- Summaries only generated when needed
- Can work offline (view raw transcripts)

---

## 🤝 Contributing

Chronicle is open source! Contributions welcome.

**Ideas for contributions:**
- Add support for more AI CLIs (Cursor, GitHub Copilot, Windsurf, etc.)
- Build the `chronicle export obsidian` command
- Create the Next.js dashboard (Phase 5)
- Improve test coverage (especially MCP server tests)
- Add MCP resources (expose session transcripts as MCP resources)
- Build prompt templates for common Chronicle queries

---

## 📝 License

MIT License - see [LICENSE](LICENSE)

---

## 🙏 Acknowledgments

**Built with:**
- [Claude Code](https://claude.com/claude-code) - AI coding assistant (and tracked by Chronicle itself! 🎯)
- [Google Gemini](https://ai.google.dev/) - AI summarization
- [FastMCP](https://gofastmcp.com/) - MCP server framework
- [Model Context Protocol](https://modelcontextprotocol.io/) - AI tool integration standard
- Python 3.11+ - Core logic
- SQLite - Local storage
- Click - CLI framework
- Rich - Terminal formatting
- GitPython - Git integration
- SQLAlchemy - ORM

---

## 📚 Documentation

- **[AGENTS.md](AGENTS.md)** - Chronicle Advocate & TDD Advocate agents (cross-platform)
- **[MCP_SERVER.md](MCP_SERVER.md)** - Chronicle MCP server guide (setup, tools, examples)
- **[CLAUDE.md](CLAUDE.md)** - Development context for AI assistants
- [Project Specification](AI_SESSION_RECORDER_SPEC.md) - Full specification and roadmap
- [Changelog](CHANGELOG.md) - Version history
- [Chronicle Skills](chronicle-skills/README.md) - Claude Skills documentation
- [Example Context](example/CLAUDE.md) - Example from Crooked Finger project

---

**Chronicle: Never lose context again.** 🎯

*Track your AI-assisted development journey, compare approaches, and build institutional knowledge across all your AI coding assistants.*
