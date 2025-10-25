---
name: chronicle-assistant-guide
description: Project-agnostic guidance for AI assistants using Chronicle. Provides search-first directives, best practices, and workflow patterns across ALL Chronicle-tracked projects. Auto-loads when Chronicle MCP is configured.
---

# Chronicle Assistant Guide

> **Purpose**: Universal directives for AI assistants using Chronicle
> **Scope**: Works across ALL projects with Chronicle MCP configured
> **Priority**: Load this FIRST when Chronicle is available

---

## ⚡ CRITICAL: Pre-Flight Checklist

**Before starting ANY Chronicle-related task, run through this checklist:**

1. ✅ **SEARCH FIRST**: `mcp__chronicle__search_sessions(query="relevant keywords", limit=5)`
   - Has this been done before?
   - What context exists about this feature/issue?
   - What approaches failed or succeeded?

2. ✅ **Check Skills**: Is there a Chronicle skill for this task?
   - `chronicle-workflow` - Session workflow guidance
   - `chronicle-session-documenter` - Document to Obsidian
   - `chronicle-context-retriever` - Search past work
   - `chronicle-project-tracker` - Roadmap and milestones

3. ✅ **Use MCP, not CLI**: Query database directly with MCP tools
   - Fast (<10ms vs >100ms for CLI)
   - Returns structured JSON
   - No subprocess overhead

4. ✅ **Check roadmap**: `mcp__chronicle__get_roadmap(days=7)`
   - Is this already tracked as a milestone?
   - Are there related next steps?

**Why this matters:** Chronicle dogfoods itself. Every mistake we make is recorded. Learn from history!

---

## 🎯 Core Directives

### 1. ALWAYS Search Chronicle Before Implementing

**The Rule:**
```python
# Before implementing ANY feature:
mcp__chronicle__search_sessions(query="feature name", limit=5)

# Before debugging:
mcp__chronicle__search_sessions(query="error or symptom", limit=5)

# When user questions something:
mcp__chronicle__search_sessions(query="topic keywords", limit=5)
```

**Real examples from Chronicle's own history:**

**Example 1: Session 21 transcript cleaning confusion**
```
User: "I can't believe there's no cleaning to be done on session 21"
❌ Without search: Spent time debugging, confused why 0% reduction
✅ With search: Would have found Session 13 implemented transcript cleaning
→ Result: Immediately understood cleaning happens at storage time
→ Time saved: 15+ minutes of debugging
```

**Example 2: Sessions 30 & 31 - Duplicate MCP optimization**
```
Session 30 (Oct 24): Fixed MCP response size by excluding summaries from get_sessions()
Session 31 (Oct 24): SAME issue - MCP responses too large, same fix needed

❌ What happened: Session 31 didn't search for "MCP response size"
✅ What should have happened: Search finds Session 30's solution immediately
→ Result: Could have referenced Session 30's approach instead of rediscovering
→ Time saved: 10+ minutes of diagnosis and implementation
```

**Example 3: Skill documentation update (Session 32)**
```
Task: Update chronicle-session-documenter skill with MCP tool instructions
❌ What I did: Jumped straight to editing SKILL.md without searching
✅ What I should have done: Search "skill documentation update" first
→ Result: Might have found context about skill format standards
→ Lesson: Even when search finds nothing, the habit prevents future mistakes
```

**Cost Calculator:**
```
Time to search:        <1 second
Time saved (average):  10-20 minutes per incident
Incidents so far:      3+ documented cases
Total time wasted:     ~45+ minutes that could have been saved
Cost of skipping:      45 minutes / 1 second = 2,700x ROI on searching!
```

**Make it a reflex:** The 1-second search is ALWAYS worth it. No exceptions.

---

### 2. ALWAYS Use MCP Tools (Never CLI)

**Priority Order:**
1. ✅ **Chronicle Skills** (best - handles complex workflows)
2. ✅ **MCP tools** (fast, programmatic access)
3. ❌ **CLI commands** (ONLY for user-facing operations - slow, not programmatic)

**Why MCP over CLI:**
- **Speed**: MCP queries database directly (<10ms), CLI spawns subprocess (>100ms)
- **Programmatic**: Returns structured JSON, not formatted text
- **Reliable**: No parsing of human-readable output
- **Efficient**: No terminal formatting overhead

**Examples:**
```python
# ✅ CORRECT (MCP):
roadmap = mcp__chronicle__get_roadmap(days=7)
sessions = mcp__chronicle__search_sessions(query="storage", limit=5)
summary = mcp__chronicle__get_session_summary(session_id=16)

# ❌ WRONG (CLI - slow, hard to parse):
Bash("chronicle roadmap")
Bash("chronicle search 'storage'")
Bash("chronicle session 16")
```

**CLI commands are ONLY for:**
- User-facing operations (`chronicle start`, `chronicle config`)
- When user explicitly requests CLI output
- When testing CLI functionality

---

## 📚 Available MCP Tools

**Session & Commit Tracking:**
```python
# List sessions (summaries excluded by default for performance)
mcp__chronicle__get_sessions(limit=10, tool="claude-code", repo_path="/path", days=7)
mcp__chronicle__get_sessions(limit=10, include_summaries=True)  # Optional: include summaries

# Get single session details with full summary
mcp__chronicle__get_session_summary(session_id=16)

# Batch retrieve summaries for multiple sessions
mcp__chronicle__get_sessions_summaries(session_ids=[15, 16, 17])

# Search and other queries
mcp__chronicle__search_sessions(query="MCP server", limit=10)
mcp__chronicle__get_commits(limit=20, repo_path="/path", days=7)
mcp__chronicle__search_commits(query="retry logic", limit=20)
mcp__chronicle__get_timeline(days=1, repo_path="/path")
mcp__chronicle__get_stats(days=7)
```

**Project Tracking:**
```python
mcp__chronicle__get_milestones(status="in_progress", milestone_type="feature", limit=20)
mcp__chronicle__get_milestone(milestone_id=1)
mcp__chronicle__get_next_steps(completed=False, milestone_id=1, limit=20)
mcp__chronicle__get_roadmap(days=7)
mcp__chronicle__update_milestone_status(milestone_id=1, new_status="completed")
mcp__chronicle__complete_next_step(step_id=1)
```

---

## 🔄 Typical Workflows

### Starting a New Task

```python
# 1. Search for related past work
results = mcp__chronicle__search_sessions(query="authentication", limit=5)

# 2. Check roadmap
roadmap = mcp__chronicle__get_roadmap(days=7)

# 3. If needed, check specific session
if results:
    session = mcp__chronicle__get_session_summary(session_id=results[0]["id"])

# 4. Now implement with full context
```

### Debugging an Issue

```python
# 1. Search for error message or symptom
results = mcp__chronicle__search_sessions(query="hang freeze stuck", limit=5)

# 2. Get full context from relevant session
if results:
    session = mcp__chronicle__get_session_summary(session_id=results[0]["id"])
    # Read how it was solved before
```

### Understanding Project History

```python
# Get overview
stats = mcp__chronicle__get_stats(days=30)
timeline = mcp__chronicle__get_timeline(days=7)

# Find specific work
sessions = mcp__chronicle__search_sessions(query="optimization", limit=10)
```

---

## 🚫 Common Mistakes to Avoid

**❌ DON'T:**
- Jump straight to implementing without searching
- Use CLI commands for querying data
- Forget to check the roadmap
- Ignore related sessions in search results

**✅ DO:**
- Search first, implement second
- Use MCP tools for all data queries
- Check roadmap before creating new milestones
- Read summaries of related sessions for context

---

## 🎓 Chronicle Quick Reference

**Session Organization (Phase 6):**
```bash
# Organize sessions (use CLI for these)
chronicle rename-session 32 "Feature Implementation"
chronicle tag-session 32 optimization,phase-6
chronicle link-session 32 --related-to 30,31
chronicle auto-title 31  # AI-generated title
chronicle graph --sessions 28-32  # Visualize relationships
```

**Current State:**
- Database: `~/.ai-session/sessions.db` (SQLite)
- Transcripts: `~/.ai-session/sessions/*.cleaned` (file-based)
- Configuration: `~/.ai-session/config.yaml`
- MCP Server: Provides 15+ tools for querying Chronicle

**Storage:**
- Summaries: Generated automatically in background after session ends
- Titles: Can be set manually or AI-generated
- Tags: JSON array for categorization
- Relationships: parent_session_id, related_session_ids

---

## 💡 Pro Tips

1. **Always search before implementing** - Chronicle has 100+ hours of documented work
2. **Use batch operations** - `get_sessions_summaries()` for multiple sessions at once
3. **Filter aggressively** - Use repo_path, days, tool filters to narrow results
4. **Check session organization** - Look for titles/tags to understand session purpose
5. **Follow the graph** - Use `chronicle graph` to see session relationships
6. **Trust the summaries** - They're generated by AI and usually accurate
7. **Update roadmap** - Complete next steps and milestones as you work

---

## 🔗 Related Resources

- **Project CLAUDE.md**: May have project-specific directives
- **Chronicle Skills**: Use `chronicle-workflow`, `chronicle-context-retriever`, etc.
- **MCP Documentation**: See `MCP_SERVER.md` in Chronicle repo

---

**Remember:** This skill applies to ALL projects using Chronicle. The directives here are universal best practices for AI assistants.
