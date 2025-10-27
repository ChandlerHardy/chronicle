# Chronicle Agents

> **Cross-Platform Solution**: Unlike skills (Claude Code only), agent prompts can be adapted for Cursor, Windsurf, and other AI coding assistants.

Chronicle includes two specialized agents to improve development workflow. These agents proactively remind you to follow best practices without requiring manual intervention.

---

## 🎯 Chronicle Advocate Agent

**Purpose:** Ensures Chronicle is used effectively by enforcing search-first behavior and session tracking.

**When it helps:**
- Before implementing features (reminds to search Chronicle first)
- When starting work (checks if session is being tracked)
- When using CLI commands (suggests faster MCP alternatives)
- Before creating new work (checks existing roadmap)
- After completing work (suggests organizing with titles/tags)

**Key behaviors:**
- **Search First**: Cites the 2,700x ROI (1 second to search vs 10-20 minutes wasted)
- **Session Tracking**: Reminds to run `chronicle start claude` if not tracked
- **MCP Over CLI**: Stops Bash("chronicle ...") and suggests MCP tools
- **Roadmap Awareness**: Checks for existing milestones before new work
- **Session Organization**: Suggests titles, tags, and linking after significant work

**Real impact:**
- Prevents repeating work from Sessions 21, 30, 31 (45+ minutes wasted)
- Ensures development history is captured
- Enforces fast MCP access over slow CLI calls

---

## ✅ TDD Advocate Agent

**Purpose:** Champions Test-Driven Development by encouraging red-green-refactor workflow.

**When it helps:**
- Before writing implementation code (reminds to write test first)
- After adding new functions (suggests test cases)
- Before commits (ensures tests pass)
- During debugging (suggests test coverage for bug fixes)

**Key behaviors:**
- **Red-Green-Refactor**: Guides through TDD cycle
- **Test Coverage**: Stops untested code, suggests specific test cases
- **Run Tests Frequently**: Reminds to run pytest after changes
- **Pre-Commit Checks**: Verifies all tests pass before commits
- **Test Patterns**: Recommends appropriate testing approaches (unit, integration, fixtures, mocks)

**Real impact:**
- Chronicle has 25 passing tests - agent helps maintain this
- Catches regressions early
- Prevents shipping untested code

---

## Installation

### For Claude Code (Current Project)

Agents are stored in `.claude/agents/`:
```
.claude/agents/chronicle-advocate.md
.claude/agents/tdd-advocate.md
```

**To create:**
1. Use `/agents` command in Claude Code
2. Select "Create new agent"
3. Copy prompt from this document
4. Restart Claude Code to activate

**To modify:**
1. Edit agent file directly in `.claude/agents/`
2. Or use `/agents` → "Edit existing agent"
3. Restart Claude Code to reload

### For Other Platforms

**Cursor:** Add to `.cursorrules` or workspace settings
**Windsurf:** Add to project configuration
**Generic:** Copy prompt to system instructions or project context

**Key insight:** Agent prompts are just specialized instructions. While the mechanics differ per platform, the PROMPT is portable!

---

## Agent Prompts

### Chronicle Advocate

```markdown
You are the Chronicle Advocate - an agent that ensures Chronicle is being used effectively.

CRITICAL RESPONSIBILITIES:
1. **Search First**: Before ANY implementation, remind the user to search Chronicle:
   - Run: mcp__chronicle__search_sessions(query="relevant keywords")
   - Cite the 2,700x ROI: "1 second to search vs 10-20 minutes wasted"
   - Show examples from Sessions 21, 30, 31 where not searching cost time

2. **Track Sessions**: Check if current work is being tracked:
   - If not in a Chronicle session, suggest: "chronicle start claude"
   - Remind: "You're making progress - let's record it!"

3. **Use MCP, Not CLI**: When you see Bash("chronicle ..."), stop and say:
   - "Use mcp__chronicle__[tool] instead - 10x faster, returns JSON"

4. **Check Roadmap**: Before creating new work, run:
   - mcp__chronicle__get_roadmap(days=7)
   - Check if this is already planned

5. **Organize Sessions**: After significant work, suggest:
   - "Want to add a title/tags to this session?"
   - "Should we link this to related sessions?"

TONE: Friendly but firm. You're saving the user time by enforcing good habits.

REMEMBER: Chronicle tracks its own development. Every mistake is in the database. Learn from it!
```

### TDD Advocate

```markdown
You are the TDD Advocate - an agent that champions Test-Driven Development.

CRITICAL RESPONSIBILITIES:
1. **Red-Green-Refactor**: Before writing implementation code, ask:
   - "Have we written a failing test for this yet?"
   - Guide: Write test → Watch it fail → Implement → Watch it pass

2. **Test Coverage Check**: When code is written without tests:
   - STOP and say: "Let's write tests for this first"
   - Suggest specific test cases based on the code

3. **Run Tests Frequently**: After ANY code change:
   - Suggest: "Let's run pytest to verify nothing broke"
   - Celebrate when tests pass ✅

4. **Test Patterns**: Recommend appropriate testing approaches:
   - Unit tests for logic
   - Integration tests for database/API calls
   - Fixtures for setup/teardown
   - Mocks for external dependencies

5. **Pre-Commit Verification**: Before commits, ensure:
   - All tests pass: pytest -xvs
   - New code has test coverage
   - No skipped tests without good reason

TONE: Encouraging but insistent. TDD saves time in the long run.

EXAMPLES:
- "I see you're adding a new function - let's write a test that calls it first!"
- "Before we commit, let's run pytest to make sure we didn't break anything"
- "Great! Now let's write the minimal code to make this test pass"

Remember: Test failures are GOOD during development - they guide implementation!
```

---

## Usage Tips

### Start with Project-Level

**Recommended approach:**
1. Create agents in Chronicle project first (test ground)
2. Iterate on prompts based on real usage
3. Once proven valuable → make global (all projects)

**Why:**
- Easy to modify/disable if annoying
- Chronicle dogfoods itself (perfect testing ground)
- Can measure actual impact before going global

### When to Use Each Agent

**Chronicle Advocate:**
- Use in ANY Chronicle-tracked project
- Especially valuable in multi-project setups
- Most useful during feature planning and implementation

**TDD Advocate:**
- Use in ALL coding projects (not Chronicle-specific!)
- Particularly valuable for greenfield projects
- Helps maintain discipline in fast-paced development

### Making Agents Global

**For Claude Code:**
```bash
# Move agent files to global location
mv .claude/agents/tdd-advocate.md ~/.claude/agents/
```

**For other platforms:** Consult platform-specific documentation for global agent/context configuration.

---

## Skills vs Agents vs MCP

Understanding the differences helps choose the right tool:

| Feature | Skills | Agents | MCP |
|---------|--------|--------|-----|
| **Platform** | Claude Code only | Adaptable across platforms | Universal |
| **Activation** | Auto-loads by description match | Always active (proactive) | Tool calls only |
| **Purpose** | Detailed workflows & examples | Enforce behaviors & remind | Programmatic data access |
| **Location** | `chronicle-skills/` directory | `.claude/agents/` or platform config | `~/.mcp.json` |
| **Best for** | Complex multi-step tasks | Habit enforcement & reminders | Fast database queries |

**When to use what:**

- **Skill**: "How do I document a session to Obsidian?" (workflow guidance)
- **Agent**: "Did you search Chronicle first?" (behavior enforcement)
- **MCP**: `mcp__chronicle__search_sessions()` (data retrieval)

---

## Cross-Platform Strategy

**The Vision:** Chronicle works everywhere, regardless of AI tool.

**Current State:**
- ✅ **MCP Server**: Works with any MCP-compatible tool (Claude Code, Cursor, Windsurf)
- ✅ **Agents**: Prompts are portable (adapt per platform)
- ⚠️ **Skills**: Claude Code only (but agents can replace much of this)

**Recommendation:**
1. Use **MCP** for all data access (universal)
2. Use **Agents** for behavior enforcement (adaptable)
3. Use **Skills** for Claude Code-specific complex workflows (when no agent exists)

**Why this matters:** Users may switch between tools (Claude Code for exploration, Cursor for speed, Windsurf for features). Chronicle should work seamlessly everywhere.

---

## Contributing

Found ways to improve these agents?

1. Edit the agent prompt in `.claude/agents/`
2. Test the changes
3. Update this documentation
4. Submit a PR with your improvements

**Particularly valuable:**
- Trigger phrases that work better
- Examples that demonstrate value clearly
- Prompts optimized for other platforms (Cursor, Windsurf, etc.)

---

## Learn More

- **Chronicle Skills**: See `chronicle-skills/README.md`
- **MCP Integration**: See `MCP_SERVER.md`
- **Development Guide**: See `CLAUDE.md`

---

**Remember:** Agents enforce habits that save time. The 1 second to search Chronicle vs 10-20 minutes of rediscovering = **2,700x ROI**. Let the agents help!
