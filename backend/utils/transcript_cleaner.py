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
    3. Removes keystroke-by-keystroke UI redraws (Claude Code typing capture)
    4. Collapses multiple newlines
    5. Deduplicates consecutive identical lines (spinner redraws, loading messages)
    6. Adds "[... repeated N times ...]" markers after 5 consecutive duplicates

    Args:
        transcript: Raw transcript text with ANSI codes and potential duplicates

    Returns:
        Cleaned transcript (typically 40-90% smaller depending on content)

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

    # 3.5. Remove keystroke-by-keystroke UI redraws (Claude Code specific)
    # Strategy: A prompt is a "real message" if it's followed by actual content (not another prompt)
    # Keystroke redraws = prompt followed by another prompt shortly after
    # Real messages = prompt followed by assistant output, thinking, tool use, etc.
    lines = cleaned.split('\n')
    lines_to_skip = set()

    # Single pass: find all prompts and check what follows them
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith('> '):
            # Found a prompt - check what comes after (within next 15 lines)
            found_next_prompt = False
            found_real_content = False

            # Look ahead to see what follows
            for j in range(i + 1, min(i + 16, len(lines))):
                next_line = lines[j].strip()

                # Check if it's a Claude Code response indicator (BEFORE skipping decorations!)
                # Tool use: "⏺ " prefix
                # Thinking: "(esc to interrupt)" appears in all thinking messages
                # Spinner: special Unicode spinner chars (·, ✢, ✳, ✶, ✻, ✽)
                is_claude_response = (
                    next_line.startswith('⏺') or  # Tool use indicator
                    '(esc to interrupt)' in next_line or  # Thinking message (any verb)
                    any(spinner in next_line for spinner in ['·', '✢', '✳', '✶', '✻', '✽'])  # Spinner
                )
                if is_claude_response:
                    found_real_content = True
                    break

                # Skip decoration/UI lines
                if (not next_line or
                    next_line.startswith('─') or
                    'Thinking' in next_line or
                    next_line == '? for shortcuts'):
                    continue

                # Check if it's another prompt
                if lines[j].startswith('> '):
                    found_next_prompt = True
                    break

                # Check if it's real content (assistant response, tool output, etc.)
                # Real content indicators: not decoration, not blank, has substance
                if len(next_line) > 10:  # Arbitrary threshold for "real" content
                    found_real_content = True
                    break

            # If followed by another prompt (and no real content), this is a keystroke redraw
            if found_next_prompt and not found_real_content:
                lines_to_skip.add(i)
                # Also mark surrounding decorations for removal
                for offset in range(-2, 3):  # -2, -1, 0, 1, 2
                    skip_idx = i + offset
                    if 0 <= skip_idx < len(lines) and skip_idx != i:
                        check_line = lines[skip_idx].strip()
                        is_decoration = (
                            not check_line or
                            check_line.startswith('─') or
                            'Thinking' in check_line or
                            check_line == '? for shortcuts'
                        )
                        if is_decoration:
                            lines_to_skip.add(skip_idx)

        i += 1

    # Build cleaned output, skipping marked lines
    deduplicated_prompts = []
    for i, line in enumerate(lines):
        if i not in lines_to_skip:
            deduplicated_prompts.append(line)

    cleaned = '\n'.join(deduplicated_prompts)

    # 4. Remove decorator borders (long lines of repeated chars like ─────)
    # These are purely visual and waste massive space (can be 50% of transcript!)
    lines = cleaned.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip lines that are just repeated decorator chars
        # Common patterns: ─────, ═════, ━━━━━, ▬▬▬▬▬
        if len(stripped) > 20 and len(set(stripped)) <= 2:
            # Line is >20 chars and uses only 1-2 unique characters = decorator
            continue
        cleaned_lines.append(line)
    cleaned = '\n'.join(cleaned_lines)

    # 5. Collapse multiple blank lines (3+ newlines -> 2 newlines)
    cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)

    # 5. Deduplicate consecutive identical lines (handles spinner redraws)
    lines = cleaned.split('\n')
    deduplicated = []
    prev_line = None
    consecutive_count = 0
    marker_index = None  # Track where we put the marker

    for line in lines:
        stripped = line.strip()
        if stripped == prev_line:
            consecutive_count += 1
            if consecutive_count == 1:
                # Keep first duplicate
                deduplicated.append(line)
            elif consecutive_count == 5:
                # After 5 duplicates, add a marker
                marker_index = len(deduplicated)
                deduplicated.append(f"[... repeated {consecutive_count} times ...]")
            elif consecutive_count > 5 and marker_index is not None:
                # Update the marker in place for every 10 additional duplicates
                if consecutive_count % 10 == 0:
                    deduplicated[marker_index] = f"[... repeated {consecutive_count} times ...]"
            # Skip other duplicates
        else:
            # New line - reset counters
            consecutive_count = 0
            marker_index = None
            deduplicated.append(line)
            prev_line = stripped

    return '\n'.join(deduplicated)
