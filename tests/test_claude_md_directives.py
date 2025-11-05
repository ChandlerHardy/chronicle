"""Test improvements to CLAUDE.md directives."""

import pytest
from pathlib import Path


class TestClaudeMDDirectives:
    """Test that CLAUDE.md directives properly defer to skills."""

    def test_universal_claude_md_defers_tdd_to_skills(self):
        """Universal CLAUDE.md should defer TDD guidance to the TDD skill, not contain redundant TDD blocks."""
        claude_md_path = Path.home() / ".claude" / "CLAUDE.md"

        if not claude_md_path.exists():
            pytest.skip("Universal CLAUDE.md not found")

        content = claude_md_path.read_text()

        # This test will fail because CLAUDE.md currently contains redundant TDD guidance
        # instead of deferring to the TDD skill

        # Should NOT contain detailed TDD process (that's what the TDD skill is for)
        tdd_blocks = [
            "WRITE TESTS FIRST",
            "RED-GREEN-REFACTOR",
            "NEVER write implementation code without tests",
            "Watch it fail",
            "Write minimal code to pass"
        ]

        found_tdd_blocks = [block for block in tdd_blocks if block in content]

        # If any TDD blocks are found, the directive should be updated to defer to skills
        if found_tdd_blocks:
            pytest.fail(f"CLAUDE.md contains redundant TDD guidance: {found_tdd_blocks}. "
                       "Should defer TDD to the TDD skill and mention checking for relevant skills first.")

        # Should contain skill-first guidance
        assert "skill" in content.lower(), "CLAUDE.md should mention skills"
        assert "superpowers" in content.lower() or "tdd" in content.lower(), "CLAUDE.md should reference TDD skill"

        # Should be concise - only count non-table TDD content
        tdd_section_lines = []
        in_tdd_section = False
        for line in content.split('\n'):
            if 'USE TDD SKILL' in line:
                in_tdd_section = True
            elif line.startswith('## =🔎') and in_tdd_section:
                in_tdd_section = False
            elif in_tdd_section and line.strip():
                tdd_section_lines.append(line)

        assert len(tdd_section_lines) < 15, f"TDD section should be concise, found {len(tdd_section_lines)} lines"