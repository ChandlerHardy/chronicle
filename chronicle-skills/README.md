# Chronicle Skills for Claude

This directory contains [Claude Skills](https://support.claude.com/en/articles/12512176-what-are-skills) that teach Claude how to work effectively with Chronicle - a local-first development session recorder.

## Available Skills

### 📝 chronicle-session-documenter
**Purpose:** Document development sessions to Obsidian vault

Automatically creates structured Obsidian notes from Chronicle sessions, including:
- AI-generated summaries
- Metadata (date, duration, repo, tags)
- Wikilinks to related sessions and commits
- Organized in `Chronicle/Sessions/` directory

**Use when:** Completing a session and want to build a searchable knowledge base.

### 🔍 chronicle-context-retriever
**Purpose:** Search and retrieve context from past work

Searches your Obsidian vault to find:
- Past approaches to similar problems
- Previous decisions and rationale
- Blockers encountered and solutions
- Related sessions by topic, time, or repository

**Use when:** Need context before starting work or want to recall past decisions.

### 🔄 chronicle-workflow
**Purpose:** Complete Chronicle workflow guidance

End-to-end workflow for:
- Starting Chronicle-tracked sessions
- Best practices during development
- Post-session summarization and documentation
- Multi-project tracking
- Integration with Obsidian knowledge base

**Use when:** Starting a new session or want comprehensive project tracking.

### 🎯 chronicle-project-tracker
**Purpose:** Manage project development with database-tracked milestones and roadmap

Use Chronicle's built-in project tracking to:
- Plan features with milestones
- Break down work into next steps
- Link sessions to milestones automatically
- View project roadmap and progress
- Generate development reports
- Eliminate manual documentation updates

**Use when:** Planning features, tracking progress, viewing roadmap, or managing meta-development.

## Installation

### Option 1: Local Directory (Recommended for Development)

1. Clone this repository or copy the `chronicle-skills/` directory
2. In Claude Code, load a skill:
   ```
   /skill add /path/to/chronicle/chronicle-skills/chronicle-workflow
   ```

### Option 2: Individual Skills

Load specific skills as needed:
```
/skill add /path/to/chronicle/chronicle-skills/chronicle-session-documenter
/skill add /path/to/chronicle/chronicle-skills/chronicle-context-retriever
/skill add /path/to/chronicle/chronicle-skills/chronicle-workflow
/skill add /path/to/chronicle/chronicle-skills/chronicle-project-tracker
```

## Prerequisites

### Required

1. **Chronicle installed:**
   ```bash
   pip install -e .  # From chronicle repo root
   ```

2. **Obsidian MCP Server configured** (for session documenter & context retriever):
   - Global config at `~/.mcp.json`:
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
   - Restart Claude Code after adding MCP config

3. **Gemini API Key** (for AI summarization):
   ```bash
   chronicle config ai.gemini_api_key YOUR_KEY
   ```

### Optional

- Git repository (for commit tracking)
- Obsidian vault (for knowledge base features)

## Usage Examples

### Example 1: Document a Completed Session

```
User: "Document session 15 to my Obsidian vault"

Claude: [Loads chronicle-session-documenter skill]
- Queries Chronicle database for session 15
- Retrieves AI summary if available
- Creates structured note at Chronicle/Sessions/Session-15.md
- Includes metadata, summary, files modified, and wikilinks
```

### Example 2: Retrieve Context Before Starting Work

```
User: "How did I implement authentication last time?"

Claude: [Loads chronicle-context-retriever skill]
- Searches Obsidian vault for "authentication" sessions
- Reads relevant session notes
- Extracts implementation approach and decisions
- Presents summary with links to full notes
```

### Example 3: Start a New Tracked Session

```
User: "I'm starting work on the API refactor"

Claude: [Loads chronicle-workflow skill]
- Checks if current session is tracked (likely not)
- Guides: "Exit and run: chronicle start claude"
- Explains workflow and best practices
- Reminds about commit linking and documentation
```

## Skill Design Philosophy

These skills follow Chronicle's core principles:

1. **Local-First** - All data stays on your machine
2. **Non-Intrusive** - Work naturally, Chronicle tracks passively
3. **Context-Aware** - Understand multi-project development
4. **Knowledge Building** - Create searchable development history
5. **AI-Assisted** - Automatic summarization and context retrieval

## How Skills Work

Each skill is a directory containing a `SKILL.md` file with:
- **YAML Frontmatter** - Name and description
- **Markdown Instructions** - What Claude should do when skill is active
- **Examples & Guidelines** - Patterns and best practices

Claude loads skills dynamically when their description matches the current task.

## Contributing

Want to improve these skills?

1. Edit the `SKILL.md` file in the relevant skill directory
2. Test with Claude Code: `/skill reload`
3. Submit a PR with your improvements

## Learn More

- [Chronicle Documentation](../CLAUDE.md)
- [What are Claude Skills?](https://support.claude.com/en/articles/12512176-what-are-skills)
- [Creating Custom Skills](https://support.claude.com/en/articles/12512198-creating-custom-skills)
- [Chronicle + Obsidian Integration Guide](../CLAUDE.md#-current-work-phase-4---obsidian-integration)

## License

Apache 2.0 (same as Chronicle project)
