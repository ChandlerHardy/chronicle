"""Tests for Chronicle hooks in .claude/hooks/

These tests verify that the UserPromptSubmit hook correctly detects
skill activation triggers and injects appropriate messages.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest


# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture
def hook_env():
    """Environment variables for running hooks."""
    return {
        "CLAUDE_PROJECT_DIR": str(PROJECT_ROOT),
        "PATH": os.environ.get("PATH", "")
    }


def run_hook(prompt: str, hook_path: str, env: dict) -> dict:
    """
    Run a hook script with given prompt and return parsed JSON output.

    Args:
        prompt: User prompt to test
        hook_path: Path to hook script
        env: Environment variables

    Returns:
        dict: Parsed JSON output or empty dict if exit 0 with no output
    """
    input_json = json.dumps({"user_prompt": prompt})

    result = subprocess.run(
        [str(hook_path)],
        input=input_json,
        capture_output=True,
        text=True,
        env=env
    )

    # Exit 0 with no output means no triggers matched
    if result.returncode == 0 and not result.stdout.strip():
        return {}

    # Exit 0 with output means triggers matched
    if result.returncode == 0 and result.stdout.strip():
        return json.loads(result.stdout)

    # Non-zero exit code is an error
    raise RuntimeError(f"Hook failed: {result.stderr}")


class TestUserPromptSubmitHook:
    """Tests for .claude/hooks/user-prompt-submit.sh"""

    @pytest.fixture
    def hook_path(self):
        """Path to user-prompt-submit.sh hook."""
        return PROJECT_ROOT / ".claude" / "hooks" / "user-prompt-submit.sh"

    # ===== Chronicle Session Documenter Tests =====

    def test_documenter_document_session(self, hook_path, hook_env):
        """Test that 'document session' triggers chronicle-session-documenter."""
        result = run_hook("document session 75 to Obsidian", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "chronicle-session-documenter" in context
        assert "SKILL DETECTED" in context

    def test_documenter_export_obsidian(self, hook_path, hook_env):
        """Test that 'export to obsidian' triggers documenter."""
        result = run_hook("export session to obsidian", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "chronicle-session-documenter" in context

    def test_documenter_save_vault(self, hook_path, hook_env):
        """Test that 'save to vault' triggers documenter."""
        result = run_hook("save session 10 to vault", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "chronicle-session-documenter" in context

    def test_documenter_exclusion_document_code(self, hook_path, hook_env):
        """Test that 'document code' does NOT trigger documenter (exclusion)."""
        result = run_hook("how do I document my code properly?", str(hook_path), hook_env)

        # Should return empty (no triggers)
        assert result == {} or "chronicle-session-documenter" not in result.get("hookSpecificOutput", {}).get("additionalContext", "")

    def test_documenter_exclusion_documentation_for(self, hook_path, hook_env):
        """Test that 'documentation for' does NOT trigger documenter."""
        result = run_hook("write documentation for this function", str(hook_path), hook_env)

        assert result == {} or "chronicle-session-documenter" not in result.get("hookSpecificOutput", {}).get("additionalContext", "")

    # ===== Chronicle Context Retriever Tests =====

    def test_context_how_did_i_implement(self, hook_path, hook_env):
        """Test that 'how did I implement' triggers context-retriever."""
        result = run_hook("how did I implement authentication?", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "chronicle-context-retriever" in context

    def test_context_what_did_i_do(self, hook_path, hook_env):
        """Test that 'what did I do yesterday' triggers context-retriever."""
        result = run_hook("what did I do yesterday?", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "chronicle-context-retriever" in context

    def test_context_find_sessions(self, hook_path, hook_env):
        """Test that 'find sessions about' triggers context-retriever."""
        result = run_hook("find sessions about database optimization", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "chronicle-context-retriever" in context

    def test_context_exclusion_mcp_search(self, hook_path, hook_env):
        """Test that existing MCP search calls don't trigger context-retriever."""
        result = run_hook('mcp__chronicle__search_sessions(query="auth")', str(hook_path), hook_env)

        # Should exit early due to search exclusion
        assert result == {}

    # ===== Chronicle Project Tracker Tests =====

    def test_tracker_whats_next(self, hook_path, hook_env):
        """Test that 'what's next' triggers project-tracker."""
        result = run_hook("what's next on the roadmap?", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "chronicle-project-tracker" in context

    def test_tracker_show_roadmap(self, hook_path, hook_env):
        """Test that 'show roadmap' triggers project-tracker."""
        result = run_hook("show me the roadmap", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "chronicle-project-tracker" in context

    def test_tracker_create_milestone(self, hook_path, hook_env):
        """Test that 'create milestone' triggers project-tracker."""
        result = run_hook("create a milestone for the API refactor", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "chronicle-project-tracker" in context

    # ===== Chronicle Workflow Tests =====

    def test_workflow_start_session(self, hook_path, hook_env):
        """Test that 'start session' triggers workflow."""
        result = run_hook("start a new session", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "chronicle-workflow" in context

    def test_workflow_is_tracked(self, hook_path, hook_env):
        """Test that 'is this tracked' triggers workflow."""
        result = run_hook("is this session being tracked?", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "chronicle-workflow" in context

    # ===== Chronicle Remote Summarizer Tests =====

    def test_remote_summarize_freebsd(self, hook_path, hook_env):
        """Test that 'summarize on freebsd' triggers remote-summarizer."""
        result = run_hook("summarize session on freebsd server", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "chronicle-remote-summarizer" in context

    def test_remote_import_session(self, hook_path, hook_env):
        """Test that 'import session from' triggers remote-summarizer."""
        result = run_hook("import session from remote host", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "chronicle-remote-summarizer" in context

    # ===== Test-Driven Development Skill Tests =====

    def test_tdd_lets_implement(self, hook_path, hook_env):
        """Test that 'let's implement' triggers TDD skill."""
        result = run_hook("let's implement the authentication feature", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "test-driven-development" in context
        assert "TDD ENFORCER" in context

    def test_tdd_lets_add(self, hook_path, hook_env):
        """Test that 'let's add' triggers TDD skill."""
        result = run_hook("let's add a new function for validation", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "test-driven-development" in context

    def test_tdd_yeah_lets_build(self, hook_path, hook_env):
        """Test that 'yeah let's build' triggers TDD skill."""
        result = run_hook("yeah let's build that feature", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "test-driven-development" in context

    def test_tdd_i_want_to_create(self, hook_path, hook_env):
        """Test that 'I want to create' triggers TDD skill."""
        result = run_hook("I want to create a new class for handling exports", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "test-driven-development" in context

    def test_tdd_write_function(self, hook_path, hook_env):
        """Test that 'write a function' triggers TDD skill."""
        result = run_hook("write a function that calculates totals", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "test-driven-development" in context

    def test_tdd_exclusion_write_test(self, hook_path, hook_env):
        """Test that 'write a test' does NOT trigger TDD (exclusion)."""
        result = run_hook("let's write a test for the authentication", str(hook_path), hook_env)

        # Should not trigger TDD skill since we're already writing tests
        context = result.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert "test-driven-development" not in context

    def test_tdd_exclusion_what_does(self, hook_path, hook_env):
        """Test that 'what does' does NOT trigger TDD (question)."""
        result = run_hook("what does this function do?", str(hook_path), hook_env)

        # Should not trigger TDD skill (asking about existing code)
        context = result.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert "test-driven-development" not in context

    def test_tdd_exclusion_how_does(self, hook_path, hook_env):
        """Test that 'how does' does NOT trigger TDD (question)."""
        result = run_hook("how does the export feature work?", str(hook_path), hook_env)

        # Should not trigger TDD skill
        context = result.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert "test-driven-development" not in context

    def test_tdd_exclusion_explain(self, hook_path, hook_env):
        """Test that 'explain' does NOT trigger TDD (exclusion)."""
        result = run_hook("explain this code to me", str(hook_path), hook_env)

        # Should not trigger TDD skill
        context = result.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert "test-driven-development" not in context

    def test_tdd_exclusion_show_me(self, hook_path, hook_env):
        """Test that 'show me' does NOT trigger TDD (exclusion)."""
        result = run_hook("show me the implementation", str(hook_path), hook_env)

        # Should not trigger TDD skill
        context = result.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert "test-driven-development" not in context

    # ===== Chronicle Assistant Guide Tests =====

    def test_guide_how_to_use(self, hook_path, hook_env):
        """Test that 'how do I use chronicle' triggers assistant-guide."""
        result = run_hook("how do I use chronicle?", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "chronicle-assistant-guide" in context

    # ===== Priority System Tests =====

    def test_priority_highest_wins(self, hook_path, hook_env):
        """Test that when multiple skills match, highest priority wins."""
        # "document session" matches documenter (90) and might match others
        result = run_hook("document this session", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]

        # Should only show ONE skill (the highest priority one)
        # Count number of "SKILL DETECTED" occurrences
        skill_count = context.count("SKILL DETECTED")
        assert skill_count == 1
        assert "chronicle-session-documenter" in context

    # ===== Chronicle Advocate Integration Tests =====

    def test_advocate_and_skill_combined(self, hook_path, hook_env):
        """Test that Chronicle Advocate + skill trigger can combine."""
        # "implement" triggers Advocate, "how did I implement" triggers context-retriever
        result = run_hook("how did I implement this feature?", str(hook_path), hook_env)

        assert "hookSpecificOutput" in result
        context = result["hookSpecificOutput"]["additionalContext"]

        # Should have BOTH messages
        assert "SEARCH CHRONICLE FIRST" in context
        assert "chronicle-context-retriever" in context
        assert "━━━━━━" in context  # Separator between messages

    def test_advocate_exclusion_view(self, hook_path, hook_env):
        """Test that Chronicle Advocate respects exclusions (view)."""
        result = run_hook("view the session details", str(hook_path), hook_env)

        # "view" is excluded from Chronicle Advocate
        context = result.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert "SEARCH CHRONICLE FIRST" not in context

    # ===== Edge Cases =====

    def test_empty_prompt(self, hook_path, hook_env):
        """Test that empty prompt doesn't crash."""
        result = run_hook("", str(hook_path), hook_env)

        # Should return empty (no triggers)
        assert result == {}

    def test_no_match(self, hook_path, hook_env):
        """Test that prompt with no triggers returns empty."""
        result = run_hook("hello there, how are you?", str(hook_path), hook_env)

        # Should return empty (no triggers)
        assert result == {}

    def test_json_output_valid(self, hook_path, hook_env):
        """Test that all outputs are valid JSON."""
        test_prompts = [
            "document session 5",
            "how did I implement auth",
            "what's next",
            "start session"
        ]

        for prompt in test_prompts:
            result = run_hook(prompt, str(hook_path), hook_env)

            # If not empty, must have correct structure
            if result:
                assert "hookSpecificOutput" in result
                assert "hookEventName" in result["hookSpecificOutput"]
                assert result["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
                assert "additionalContext" in result["hookSpecificOutput"]
                assert isinstance(result["hookSpecificOutput"]["additionalContext"], str)


class TestHookConfiguration:
    """Tests for hook configuration and rules file."""

    def test_skill_rules_file_exists(self):
        """Test that skill-rules.json exists."""
        rules_path = PROJECT_ROOT / ".claude" / "config" / "skill-rules.json"
        assert rules_path.exists()

    def test_skill_rules_valid_json(self):
        """Test that skill-rules.json is valid JSON."""
        rules_path = PROJECT_ROOT / ".claude" / "config" / "skill-rules.json"

        with open(rules_path) as f:
            rules = json.load(f)

        assert isinstance(rules, dict)
        assert "skillActivation" in rules

    def test_all_skills_have_required_fields(self):
        """Test that all skills have required fields."""
        rules_path = PROJECT_ROOT / ".claude" / "config" / "skill-rules.json"

        with open(rules_path) as f:
            rules = json.load(f)

        skills = rules.get("skillActivation", {})

        for skill_name, skill_config in skills.items():
            # Each skill must have these fields
            assert "priority" in skill_config, f"{skill_name} missing priority"
            assert "skillCommand" in skill_config, f"{skill_name} missing skillCommand"
            assert "triggers" in skill_config, f"{skill_name} missing triggers"
            assert "message" in skill_config, f"{skill_name} missing message"

            # Triggers must have these fields
            triggers = skill_config["triggers"]
            assert "keywords" in triggers, f"{skill_name} missing keywords"
            assert "phrases" in triggers, f"{skill_name} missing phrases"
            assert "excludes" in triggers, f"{skill_name} missing excludes"

            # Priority must be a number
            assert isinstance(skill_config["priority"], int)

            # All fields must be lists
            assert isinstance(triggers["keywords"], list)
            assert isinstance(triggers["phrases"], list)
            assert isinstance(triggers["excludes"], list)

    def test_hook_script_executable(self):
        """Test that hook script is executable."""
        hook_path = PROJECT_ROOT / ".claude" / "hooks" / "user-prompt-submit.sh"
        assert hook_path.exists()
        assert os.access(hook_path, os.X_OK), "Hook script is not executable"
