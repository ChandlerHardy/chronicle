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

    # 1. Remove ALL ANSI escape sequences (comprehensive pattern)
    # Matches: ESC [ ... letter, ESC ( ... ), ESC ) ... ), and other ANSI codes
    # This catches color codes, cursor movement, mode changes, etc.
    ansi_pattern = re.compile(r'''
        \x1B  # ESC
        (?:   # Non-capturing group for alternatives
            [@-Z\\-_]  # Single-character CSI
        |
            \[[0-?]*[ -/]*[@-~]  # CSI sequences (most common)
        |
            \][^\x07]*(?:\x07|\x1B\\)  # OSC sequences
        |
            P[^\x1B]*(?:\x1B\\)  # DCS sequences
        |
            _[^\x1B]*(?:\x1B\\)  # APC sequences
        |
            \^[^\x1B]*(?:\x1B\\)  # PM sequences
        )
    ''', re.VERBOSE)
    cleaned = ansi_pattern.sub('', transcript)

    # 2. Remove any remaining control characters (except newlines and tabs)
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

        # Check for prompts (> followed by space OR non-breaking space \xa0)
        if line.startswith('> ') or line.startswith('>\xa0'):
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

                # Check if it's another prompt (> followed by space OR \xa0)
                if lines[j].startswith('> ') or lines[j].startswith('>\xa0'):
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

    # 4. Remove decorator borders and spinner lines
    # These are purely visual and waste massive space (can be 50% of transcript!)
    lines = cleaned.split('\n')
    cleaned_lines = []

    # Claude Code spinner chars (including thinking indicator ∴)
    claude_spinner_chars = ['·', '✢', '✳', '✶', '✻', '✽', '∴']

    # Gemini/Qwen/Droid spinner chars (Unicode Braille patterns)
    gemini_spinner_chars = ['⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    for line in lines:
        stripped = line.strip()

        # Skip decorator borders (long lines of repeated chars like ─────)
        # Common patterns: ─────, ═════, ━━━━━, ▬▬▬▬▬
        if len(stripped) > 20 and len(set(stripped)) <= 2:
            # Line is >20 chars and uses only 1-2 unique characters = decorator
            continue

        # Skip Claude Code header box-drawing characters
        # Patterns: "▐▛███▜▌   Claude Code", "▝▜█████▛▘  Sonnet", "▘▘ ▝▝    /Users/..."
        # These appear thousands of times and add zero value
        if ('Claude Code' in stripped and any(char in stripped for char in ['▐', '▛', '█'])) or \
           ('Sonnet' in stripped and any(char in stripped for char in ['▝', '█'])) or \
           (stripped.count('▘') >= 2 and stripped.count('▝') >= 2) or \
           (any(char in stripped for char in ['▐', '▛', '▜', '▌', '▝', '▘', '█']) and len(stripped) < 80):
            continue

        # Skip Claude Code spinner lines (completely useless for summaries)
        # Format: "· Osmosing… (esc to interrupt)" or "· Osmosing… (esc to interrupt · 6s · ↓ 66 tokens)"
        # Format: "∴ Thinking…" or "∴ Thought for 8s (ctrl+o to show thinking)"
        is_claude_spinner = any(stripped.startswith(spinner + ' ') for spinner in claude_spinner_chars)
        if is_claude_spinner and ('esc to interrupt' in stripped or 'Thinking' in stripped or 'Thought for' in stripped):
            continue

        # Skip Gemini/Qwen/Droid spinner lines
        # Format: "⠙ Initializing..." or "⠦ Connecting to MCP servers... (1/3)"
        is_gemini_spinner = any(stripped.startswith(spinner + ' ') for spinner in gemini_spinner_chars)
        if is_gemini_spinner:
            continue

        # Skip empty prompts (just ">" or "> " with only whitespace after)
        # These are UI artifacts from Claude Code redraws
        if stripped == '>' or (stripped.startswith('> ') and len(stripped) <= 3):
            continue

        # Skip "? for shortcuts" decoration line (may have trailing spaces)
        if stripped.startswith('? for shortcuts'):
            continue

        # Skip tool execution status lines (⎿ Running…, ⎿ Done, etc.)
        if stripped.startswith('⎿'):
            continue

        # Skip edit mode indicators (⏵⏵ accept edits, etc.)
        if stripped.startswith('⏵⏵'):
            continue

        # Skip timeout/duration lines (mostly noise)
        if 'timeout:' in stripped and ('0s' in stripped or 'm' in stripped):
            continue

        # Skip stderr log messages and warnings
        if 'WARNING:' in stripped or 'E0000' in stripped or 'ALTS creds ignored' in stripped:
            continue

        # Skip UI hints (ctrl+b, etc.)
        if stripped.startswith('ctrl+') or 'to run in background' in stripped:
            continue

        # Skip mode indicators
        if stripped.startswith('Mode:'):
            continue

        # Skip duration indicators in parentheses (like "(2s)")
        if stripped.startswith('(') and stripped.endswith(')') and ('s)' in stripped or 'm)' in stripped):
            continue

        # Skip success/completion messages
        if stripped.startswith('✓') or 'Complete!' in stripped:
            continue

        # Skip "view more" indicators (+N more lines)
        if stripped.startswith('+') and 'more lines' in stripped:
            continue

        # Skip CLI usage hints (View summary with:, View chunks:, etc.)
        if stripped.startswith('View ') and (':' in stripped or 'with:' in stripped):
            continue

        # Skip orphaned tool lines (indented Bash/command lines without ⏺ prefix)
        # These are remnants after removing decorations
        if stripped.startswith('Bash(') and not line.startswith('⏺'):
            continue

        # Skip "Using chunked summarization" status messages
        if 'Using chunked summarization' in stripped:
            continue

        # Skip Gemini/Qwen/Droid decorative box borders
        # These repeat thousands of times and add no value
        # Patterns: ╭─────...─╮, ╰─────...─╯, │ ... │, │ ...
        if stripped.startswith('╭') or stripped.startswith('╰'):
            continue

        # Skip lines starting with │ (box borders, even without ending │)
        if stripped.startswith('│'):
            inner = stripped[1:].strip()
            # Skip if it's decorative UI elements
            # Check for spinner inside box: │ ⠋ Waiting...
            if any(inner.startswith(spinner) for spinner in gemini_spinner_chars):
                continue
            # Skip if it's an input prompt (including keystroke-by-keystroke typing)
            # Examples: │ > Type..., │ > /, │ > /m, │ > /mcp
            if inner.startswith('>'):
                # Extract the actual content (remove ending │ if present)
                actual_content = inner
                if stripped.endswith('│'):
                    actual_content = stripped[1:-1].strip()
                # Skip if it's the input prompt template or short keystrokes
                # Short inputs like "> /", "> /m" are keystroke redraws
                if 'Type your message' in actual_content or len(actual_content) <= 50:
                    continue
            # Also skip MCP permission prompts and execution UI (multi-line UI boxes)
            if any(keyword in inner for keyword in [
                'Allow execution of MCP', 'Tool:', 'MCP Server:', 'suggest changes',
                'Yes, allow once', 'Yes, always allow', 'No, suggest changes',
                '?  get_', '⊶  get_', '✓  get_',  # MCP tool execution indicators
                '?  search_', '⊶  search_', '✓  search_',
                '?  mcp__', '⊶  mcp__', '✓  mcp__'
            ]):
                continue
            # Skip autocomplete menus and other UI chrome
            if any(keyword in inner for keyword in ['show version info', 'change the auth method', 'submit a bug report', 'Manage conversation']):
                continue
            # Skip "Waiting for auth" screens
            if 'Waiting for auth' in inner or 'Press ESC or CTRL+C to cancel' in inner:
                continue

        # Skip Gemini status lines (repeat constantly during UI redraws)
        # Format: "Using: N open files (ctrl+g to view) | ..."
        if 'Using:' in stripped and 'open files' in stripped and 'ctrl+' in stripped:
            continue

        # Skip Gemini status bar (repo path, sandbox status, model name)
        # Format: "~/repos/chronicle (main*)    no sandbox (see /docs)    gemini-2.5-pro (100% context left)"
        if '(main' in stripped and 'sandbox' in stripped and '% context left' in stripped:
            continue

        # Skip Droid status bar (mode, model name)
        # Format: "Auto (Low) - edits and read-only commands  shift+tab cycles ... Droid Core (GLM-4.6)"
        if 'Auto (' in stripped and 'shift+tab cycles' in stripped and 'Droid Core' in stripped:
            continue

        # Skip Droid help/status line
        # Format: " ? for help ... IDE ◌ | MCP ◌" or "[⏱ 11s] ? for help ... settings.json •"
        if stripped.startswith('? for help') or '] ? for help' in stripped:
            continue

        # Skip Droid navigation hints
        # Format: "Use ↑↓ to navigate, Tab/Enter to select, Esc to cancel"
        if 'Use ↑↓ to navigate' in stripped or 'Tab/Enter to select' in stripped:
            continue

        cleaned_lines.append(line)
    cleaned = '\n'.join(cleaned_lines)

    # 5. Collapse multiple blank lines (2+ newlines -> 1 newline)
    # This makes the transcript much more compact while still readable
    cleaned = re.sub(r'\n\s*\n+', '\n', cleaned)

    # 5.5. Deduplicate user prompts within a small window (removes UI redraws)
    # Claude Code redraws prompts multiple times (after spinners, thinking messages, etc.)
    # These appear within ~20 lines of each other - much closer than genuine re-asks
    lines = cleaned.split('\n')
    lines_to_skip_prompts = set()

    for i, line in enumerate(lines):
        # Check for prompts (> followed by space OR \xa0)
        if line.strip().startswith('> ') or line.strip().startswith('>\xa0'):
            # Found a prompt - check if same prompt appears within next 25 lines
            prompt_text = line.strip()
            for j in range(i + 1, min(i + 26, len(lines))):
                check_line = lines[j].strip()
                if check_line == prompt_text:
                    # Found duplicate within window - mark the EARLIER one for deletion
                    # (Keep the last occurrence, which is closest to the actual response)
                    lines_to_skip_prompts.add(i)
                    break  # Only need to find one duplicate to mark this for deletion

    # Remove marked prompts
    deduplicated_prompts = []
    for i, line in enumerate(lines):
        if i not in lines_to_skip_prompts:
            deduplicated_prompts.append(line)

    cleaned = '\n'.join(deduplicated_prompts)

    # 6. Deduplicate consecutive identical lines (handles remaining duplicates)
    # Skip blank lines when comparing - they don't break duplication runs
    lines = cleaned.split('\n')
    deduplicated = []
    prev_line = None
    prev_normalized = None
    consecutive_count = 0
    marker_index = None  # Track where we put the marker

    for line in lines:
        stripped = line.strip()

        # Skip blank lines - add them but don't break duplication detection
        if not stripped:
            deduplicated.append(line)
            continue

        # Normalize tool use lines: treat "⏺ tool" and "  tool" as same
        # Claude Code adds/removes ⏺ prefix during redraws
        normalized = stripped
        if stripped.startswith('⏺ '):
            normalized = stripped[2:]  # Remove ⏺ prefix for comparison
        elif stripped.startswith('  ') and not stripped.startswith('   '):
            # Two-space indent = tool use without ⏺
            normalized = stripped.strip()

        if normalized == prev_normalized:
            consecutive_count += 1
            # For tool use duplicates, skip ALL of them (they're noise)
            # For other content, keep first duplicate to show it's repeated
            is_tool_use = normalized.startswith('Bash(') or normalized.startswith('chronicle -') or '(MCP)' in normalized
            if consecutive_count == 1 and not is_tool_use:
                # Keep first duplicate for non-tool content
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
            prev_normalized = normalized

    cleaned = '\n'.join(deduplicated)

    # 6.5. Deduplicate multi-line blocks (MCP responses, AI summaries, etc.)
    # These appear as consecutive line groups that repeat (often 10+ times)
    # Strategy: Use a sliding window to detect repeating 3-5 line patterns
    lines = cleaned.split('\n')
    multiline_deduplicated = []
    skip_until = -1  # Track which lines to skip

    i = 0
    while i < len(lines):
        if i < skip_until:
            i += 1
            continue

        # Try to find a repeating block starting at this line
        # Test with block sizes of 3-5 lines (most MCP responses are 3-4 lines)
        found_repeat = False

        for block_size in [3, 4, 5]:
            if i + block_size * 2 > len(lines):
                continue  # Not enough lines left for 2 blocks

            # Get the candidate block
            block = lines[i:i+block_size]
            block_text = '\n'.join(block)

            # Skip if block is mostly blank lines
            if sum(1 for line in block if line.strip()) < 2:
                continue

            # Check how many times this block repeats consecutively
            repeat_count = 1
            check_pos = i + block_size

            while check_pos + block_size <= len(lines):
                next_block = lines[check_pos:check_pos+block_size]
                next_block_text = '\n'.join(next_block)

                if block_text == next_block_text:
                    repeat_count += 1
                    check_pos += block_size
                else:
                    break

            # If block repeats 3+ times, it's a duplicate pattern
            if repeat_count >= 3:
                # Keep first occurrence only
                multiline_deduplicated.extend(block)
                # Add a marker if it repeats many times
                if repeat_count >= 5:
                    multiline_deduplicated.append(f"[... repeated {repeat_count} times ...]")
                # Skip all the duplicate blocks
                skip_until = i + (block_size * repeat_count)
                found_repeat = True
                break

        if not found_repeat:
            multiline_deduplicated.append(lines[i])

        i += 1

    cleaned = '\n'.join(multiline_deduplicated)

    # 6.6. Global deduplication for large tool outputs (git diff, test results, etc.)
    # These can appear hundreds of times non-consecutively, wasting massive space
    # Strategy: Track large blocks (>500 chars), replace 2nd+ occurrences with marker
    lines = cleaned.split('\n')
    global_deduplicated = []
    seen_blocks = {}  # hash -> (first_index, content_preview, occurrence_count)
    i = 0

    while i < len(lines):
        # Look for tool output start (indented lines after ⏺ commands)
        # Or diff markers (diff --git, index, @@, etc.)
        line = lines[i]

        # Check if this might be start of a large output block
        is_tool_output = (
            line.strip().startswith('diff --git') or
            line.strip().startswith('index ') or
            line.strip().startswith('@@') or
            line.strip().startswith('===') or
            (line.startswith('    ') and len(line.strip()) > 20)  # Indented tool output
        )

        if is_tool_output and i + 10 < len(lines):
            # Try to capture a block (next 10-50 lines)
            # Stop at next prompt or tool command
            block_end = i + 1
            block_lines = [line]

            while block_end < len(lines) and block_end < i + 100:
                next_line = lines[block_end]
                # Stop if we hit a new prompt or tool command
                if next_line.strip().startswith('>') or next_line.strip().startswith('⏺'):
                    break
                block_lines.append(next_line)
                block_end += 1

            # If block is substantial (>500 chars), check if we've seen it
            block_text = '\n'.join(block_lines)
            if len(block_text) > 500:
                block_hash = hash(block_text)

                if block_hash in seen_blocks:
                    # We've seen this before - replace with marker
                    first_idx, preview, count = seen_blocks[block_hash]
                    seen_blocks[block_hash] = (first_idx, preview, count + 1)
                    global_deduplicated.append(f"[... duplicate output, already shown at line {first_idx} (occurrence #{count + 1}) ...]")
                    i = block_end
                    continue
                else:
                    # First time seeing this block - keep it
                    seen_blocks[block_hash] = (len(global_deduplicated), block_text[:100], 1)
                    global_deduplicated.extend(block_lines)
                    i = block_end
                    continue

        # Normal line - keep it
        global_deduplicated.append(line)
        i += 1

    cleaned = '\n'.join(global_deduplicated)

    # 7. Final pass: Remove keystroke-by-keystroke typing that survived earlier steps
    # After removing all decorations, keystrokes end up consecutive
    # Pattern: "> w" followed by "> wh" followed by "> why" etc.
    # Also handles typos/corrections: "> I tihn" → "> I tih" → "> I think"
    lines = cleaned.split('\n')
    final_lines = []
    skip_next = set()

    for i, line in enumerate(lines):
        if i in skip_next:
            continue

        stripped = line.strip()
        if stripped.startswith('> ') or stripped.startswith('>\xa0'):
            # Check if this is a prefix of any following prompts (within next 20 lines)
            # OR if it's very similar (typing with corrections)
            is_keystroke = False
            current_text = stripped[2:].strip() if stripped.startswith('> ') else stripped[1:].strip()

            for j in range(i + 1, min(i + 21, len(lines))):
                next_stripped = lines[j].strip()
                if next_stripped.startswith('> ') or next_stripped.startswith('>\xa0'):
                    next_text = next_stripped[2:].strip() if next_stripped.startswith('> ') else next_stripped[1:].strip()

                    # Strategy 1: Current is a prefix of next (forward typing)
                    # OR next is a prefix of current (backspacing)
                    if (next_text.startswith(current_text) and len(next_text) > len(current_text)) or \
                       (current_text.startswith(next_text) and len(current_text) > len(next_text)):
                        is_keystroke = True
                        skip_next.add(i)
                        break

                    # Strategy 2: Very similar prompts (typos/corrections)
                    # If prompts differ by just a few characters, it's likely typing
                    # Use Levenshtein-like distance: count how many chars are different
                    if abs(len(current_text) - len(next_text)) <= 5:
                        # Count matching prefix length
                        matching = 0
                        for k in range(min(len(current_text), len(next_text))):
                            if current_text[k] == next_text[k]:
                                matching += 1
                            else:
                                break

                        # If >90% of the longer one matches, it's probably typing corrections
                        longer_len = max(len(current_text), len(next_text))
                        if longer_len > 0 and matching / longer_len > 0.9:
                            is_keystroke = True
                            skip_next.add(i)
                            break

            if not is_keystroke:
                final_lines.append(line)
        else:
            # Check for orphaned typing lines (lines that look like keystrokes but without >)
            # Pattern: short lines that are prefixes of each other
            # Example: "r", "re", "rem", "remo", "remov", "remove"
            if len(stripped) > 0 and len(stripped) < 30:
                # Look ahead to see if next few lines are extensions of this
                is_orphaned_typing = False
                for j in range(i + 1, min(i + 10, len(lines))):
                    next_stripped = lines[j].strip()
                    if len(next_stripped) > len(stripped) and next_stripped.startswith(stripped):
                        is_orphaned_typing = True
                        skip_next.add(i)
                        break

                if not is_orphaned_typing:
                    final_lines.append(line)
            else:
                final_lines.append(line)

    return '\n'.join(final_lines)
