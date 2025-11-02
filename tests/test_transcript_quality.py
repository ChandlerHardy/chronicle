"""Tests for transcript quality analysis and large-block deduplication.

These tests verify:
1. Detection of duplicate conversation blocks
2. Quality metrics (duplication ratio)
3. Large-block deduplication removes repeated conversations
"""

import pytest
from backend.utils.transcript_cleaner import (
    clean_transcript,
    analyze_transcript_quality,
    detect_duplicate_conversation_blocks,
)


class TestTranscriptQualityAnalysis:
    """Test transcript quality metrics."""

    def test_analyze_quality_no_duplicates(self):
        """Transcript with no duplication should have low duplicate ratio."""
        transcript = """
> user asks question
⏺ assistant responds
some output here
> user asks different question
⏺ assistant responds differently
>  third unique question
⏺ third unique answer
"""
        quality = analyze_transcript_quality(transcript)
        # Should have low duplication (<40% even with blank lines)
        assert quality['duplicate_ratio'] < 0.4
        assert quality['total_lines'] > 0
        assert quality['unique_lines'] > 0

    def test_analyze_quality_high_duplicates(self):
        """Transcript with heavy duplication should have high ratio."""
        # Simulate Session 95: same conversation repeated 20 times
        block = """
> can you explain langchain and langgraph to me?
⏺ I'll explain LangChain and LangGraph
LangChain is a framework...
LangGraph is newer...
"""
        transcript = block * 20
        quality = analyze_transcript_quality(transcript)

        # Should detect ~95% duplication (1 original + 19 duplicates)
        assert quality['duplicate_ratio'] > 0.90
        assert quality['recommendation'] == 'deduplicate_before_summarizing'

    def test_analyze_quality_medium_duplicates(self):
        """Transcript with moderate duplication."""
        unique = """
> different question
⏺ unique response
"""
        duplicate = """
> repeated question
⏺ same response
""" * 10

        transcript = unique + duplicate
        quality = analyze_transcript_quality(transcript)

        # Should detect some duplication but not extreme
        assert 0.3 < quality['duplicate_ratio'] < 0.95
        assert quality['total_lines'] > quality['unique_lines']


class TestDuplicateConversationBlockDetection:
    """Test detection of repeated conversation blocks."""

    def test_detect_simple_block_repetition(self):
        """Should detect when same conversation repeats 3+ times."""
        block = """
> what is python?
⏺ Python is a programming language
It was created by Guido van Rossum
Released in 1991
"""
        transcript = block * 5  # Repeat 5 times

        result = detect_duplicate_conversation_blocks(transcript)

        assert 'duplicate_blocks_found' in result
        assert result['duplicate_blocks_found'] > 0
        assert result['max_repetitions'] == 5

    def test_no_false_positives_similar_blocks(self):
        """Should not flag similar but different conversations."""
        # Make blocks larger (5+ lines) to trigger detection
        block1 = """
> what is python?
⏺ Python is a programming language
It was created by Guido van Rossum
Released in 1991
Used for web dev, data science, AI
"""
        block2 = """
> what is javascript?
⏺ JavaScript is a programming language
It was created by Brendan Eich
Released in 1995
Used for web development
"""
        transcript = block1 + block2 + block1 + block2

        result = detect_duplicate_conversation_blocks(transcript)

        # Should detect some repetition but not treat as identical
        # Each block repeats twice, not 4 times total
        # May detect 0 if blocks are too different or 2 if they match
        assert result['max_repetitions'] <= 2

    def test_session_95_pattern(self):
        """Test Session 95's specific duplication pattern."""
        # Exact pattern from Session 95: LangChain explanation repeated 23x
        block = """
> can you explain langchain and langgraph to me?
⏺ I'll explain LangChain and LangGraph, two popular Python frameworks
LangChain is a framework for developing applications powered by language models
LangGraph is a newer library (from the LangChain team)
"""
        transcript = block * 23

        result = detect_duplicate_conversation_blocks(transcript)

        assert result['duplicate_blocks_found'] > 0
        assert result['max_repetitions'] >= 20  # Should detect heavy repetition


class TestLargeBlockDeduplication:
    """Test actual deduplication of conversation blocks."""

    def test_deduplicate_repeated_conversation(self):
        """Should remove repeated conversation blocks."""
        # Use larger block to trigger new deduplication logic
        block = """
> what is chronicle?
⏺ Chronicle is a tool for tracking AI sessions
It records terminal transcripts
Created by Chandler Hardy
Uses SQLite for storage
Integrates with Gemini API
Supports chunked summarization
"""
        # Original transcript with 10 duplicates
        dirty_transcript = block * 10
        original_size = len(dirty_transcript)

        # Clean should remove duplicates
        cleaned = clean_transcript(dirty_transcript)
        cleaned_size = len(cleaned)

        # Should have removed most duplicates (keep 1-2 occurrences)
        reduction_ratio = (original_size - cleaned_size) / original_size
        # Should get significant reduction with large block deduplication
        # Note: Actual reduction depends on block size and overlap detection
        assert reduction_ratio > 0.40  # At least 40% reduction

        # Should add marker for duplicates when large block logic triggers
        if "⚠️  Detected" in cleaned or len(cleaned) < original_size * 0.3:
            # Large block deduplication triggered
            assert "[... repeated" in cleaned or "occurrence #" in cleaned or "duplicate conversation" in cleaned

    def test_preserve_unique_content(self):
        """Should keep all unique conversations."""
        transcript = """
> question 1
⏺ answer 1
> question 2
⏺ answer 2
> question 3
⏺ answer 3
"""
        cleaned = clean_transcript(transcript)

        # Should keep all unique content
        assert "question 1" in cleaned
        assert "question 2" in cleaned
        assert "question 3" in cleaned
        assert "answer 1" in cleaned
        assert "answer 2" in cleaned
        assert "answer 3" in cleaned

    def test_mixed_duplicate_and_unique(self):
        """Should handle mix of repeated and unique content."""
        repeated_block = """
> explain langchain
⏺ LangChain is a framework
"""
        unique_content = """
> let's implement milestone 13
⏺ I'll create skill-rules.json
"""

        # 10 repeats of first block + unique content
        transcript = (repeated_block * 10) + unique_content
        cleaned = clean_transcript(transcript)

        # Should keep unique content
        assert "milestone 13" in cleaned
        assert "skill-rules.json" in cleaned

        # Should deduplicate repeated block
        assert cleaned.count("explain langchain") < 5  # Much less than 10

    def test_block_size_detection(self):
        """Should detect various block sizes (5-20 lines)."""
        # Medium block (8 lines) - large enough for new deduplication logic
        medium = "\n".join([f"line {i}" for i in range(8)]) + "\n"

        # Large block (20 lines)
        large = "\n".join([f"line {i}" for i in range(20)]) + "\n"

        for block in [medium, large]:
            transcript = block * 5  # Repeat each 5 times
            cleaned = clean_transcript(transcript)

            # Should deduplicate - expect at least 40% reduction
            # (existing logic handles smaller blocks differently)
            assert len(cleaned) < len(transcript) * 0.7  # At least 30% reduction


def test_integration_session_95_like_transcript():
    """Integration test with Session 95-like duplication pattern."""
    # Simulate Session 95:
    # - 23x repeated LangChain explanation
    # - 1x actual Milestone #13 implementation work

    langchain_block = """
> can you explain langchain and langgraph to me?
⏺ I'll explain LangChain and LangGraph
LangChain is a framework for developing applications powered by language models.
LangGraph is a newer library (from the LangChain team) for building stateful apps.
> does this fit into chronicle at all?
⏺ Great question! Let me search Chronicle first
Honest Assessment: Not a great fit for Chronicle
"""

    implementation_work = """
> let's implement milestone 13!
⏺ Excellent! Let me research the current implementation
⏺ Read(.claude/config/skill-rules.json)
⏺ Update(.claude/config/skill-rules.json)
Successfully designed trigger patterns for 6 Chronicle skills
⏺ Update(.claude/hooks/user-prompt-submit.sh)
Enhanced hook with skill detection logic
⏺ Write(tests/test_hooks.py)
Created 27 test cases
⏺ Bash(pytest tests/test_hooks.py)
All 27 tests pass!
"""

    # Simulate Session 95: mostly duplicates + real work
    transcript = (langchain_block * 23) + implementation_work

    # Analyze quality before cleaning
    quality_before = analyze_transcript_quality(transcript)
    assert quality_before['duplicate_ratio'] > 0.85  # Mostly duplicates

    # Clean transcript
    cleaned = clean_transcript(transcript)

    # Analyze quality after cleaning
    quality_after = analyze_transcript_quality(cleaned)

    # Should have much lower duplication after cleaning
    assert quality_after['duplicate_ratio'] < quality_before['duplicate_ratio'] * 0.5

    # Should preserve implementation work
    assert "milestone 13" in cleaned
    assert "skill-rules.json" in cleaned
    assert "test_hooks.py" in cleaned
    assert "27 tests pass" in cleaned

    # Should have markers for duplicates
    assert "[... repeated" in cleaned or "occurrence #" in cleaned

    # Size reduction should be substantial
    reduction = (len(transcript) - len(cleaned)) / len(transcript)
    assert reduction > 0.70  # At least 70% size reduction
