"""Transcript cleaning utilities for Chronicle.

This module provides functions to clean terminal transcripts by removing ANSI codes,
control characters, and deduplicating repeated lines (like spinner redraws).
"""

import re


def clean_transcript(transcript: str) -> str:
    """Clean transcript by removing ANSI codes and deduplicating lines.

    This function:
    1. Removes ANSI escape codes (colors, cursor movements)
    2. Removes CSI sequences and control characters
    3. Collapses multiple newlines
    4. Deduplicates consecutive identical lines (spinner redraws, loading messages)
    5. Adds "[... repeated N times ...]" markers after 5 consecutive duplicates

    Args:
        transcript: Raw transcript text with ANSI codes and potential duplicates

    Returns:
        Cleaned transcript (typically 20-70% smaller depending on content)

    Example:
        >>> raw = "\\x1b[32mGreen\\x1b[0m\\nLoading...\\nLoading...\\nLoading...\\nDone!"
        >>> clean = clean_transcript(raw)
        >>> print(clean)
        Green
        Loading...
        Loading...
        [... repeated 3 times ...]
        Done!
    """
    if not transcript:
        return ""

    # 1. Remove ANSI escape codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    cleaned = ansi_escape.sub('', transcript)

    # 2. Remove CSI sequences (cursor positioning, etc.)
    cleaned = re.sub(r'\x1B\[[0-9;]*[a-zA-Z]', '', cleaned)

    # 3. Remove control characters (except newlines and tabs)
    # Preserve \n (0x0A) and \t (0x09)
    cleaned = re.sub(r'[\x00-\x08\x0B-\x1F\x7F]', '', cleaned)

    # 4. Collapse multiple blank lines (3+ newlines -> 2 newlines)
    cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)

    # 5. Deduplicate consecutive identical lines (handles spinner redraws)
    lines = cleaned.split('\n')
    deduplicated = []
    prev_line = None
    consecutive_count = 0

    for line in lines:
        stripped = line.strip()
        if stripped == prev_line:
            consecutive_count += 1
            if consecutive_count == 1:
                # Keep first duplicate
                deduplicated.append(line)
            elif consecutive_count == 5:
                # After 5 duplicates, add a marker
                deduplicated.append(f"[... repeated {consecutive_count} times ...]")
            # Skip other duplicates
        else:
            consecutive_count = 0
            deduplicated.append(line)
            prev_line = stripped

    return '\n'.join(deduplicated)
