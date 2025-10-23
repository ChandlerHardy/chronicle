"""AI summarization service using Gemini or Ollama."""

import time
from typing import Optional
from backend.core.config import get_config
from backend.utils.transcript_cleaner import clean_transcript


class Summarizer:
    """Generate summaries using Gemini API or Ollama."""

    def __init__(self):
        """Initialize summarizer based on configured provider."""
        self.config = get_config()
        self.provider = self.config.summarization_provider
        # Track recent API requests for adaptive rate limiting
        self.recent_requests = []  # List of (timestamp, estimated_tokens)

        if self.provider == "gemini":
            import google.generativeai as genai
            self.api_key = self.config.gemini_api_key

            if not self.api_key:
                raise ValueError(
                    "Gemini API key not configured. "
                    "Set it with: chronicle config ai.gemini_api_key YOUR_KEY"
                )

            # Configure Gemini
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.config.default_model)
            self.genai = genai

        elif self.provider == "ollama":
            import ollama
            self.ollama_client = ollama.Client(host=self.config.ollama_host)
            self.model_name = self.config.ollama_model

        else:
            raise ValueError(f"Unknown summarization provider: {self.provider}")

    def test_connection(self) -> dict:
        """Test the summarization provider connection.

        Returns:
            Dictionary with test results
        """
        try:
            if self.provider == "gemini":
                response = self.model.generate_content("Say 'Hello from Chronicle!' in exactly 5 words.")
                response_text = response.text.strip()
                model_name = self.config.default_model
            elif self.provider == "ollama":
                response = self.ollama_client.generate(
                    model=self.model_name,
                    prompt="Say 'Hello from Chronicle!' in exactly 5 words."
                )
                response_text = response['response'].strip()
                model_name = self.model_name
            else:
                return {
                    "success": False,
                    "error": f"Unknown provider: {self.provider}",
                    "message": "Connection test failed"
                }

            return {
                "success": True,
                "provider": self.provider,
                "model": model_name,
                "response": response_text,
                "message": f"{self.provider.title()} connection successful!"
            }
        except Exception as e:
            return {
                "success": False,
                "provider": self.provider,
                "model": self.config.default_model if self.provider == "gemini" else self.model_name,
                "error": str(e),
                "message": f"{self.provider.title()} connection failed"
            }


    def summarize_session(self, transcript: str, max_length: int = 2000) -> Optional[str]:
        """Summarize a session transcript.

        Args:
            transcript: Full session transcript
            max_length: Maximum summary length in characters

        Returns:
            Summary text or None if failed
        """
        if not transcript or len(transcript) < 50:
            return "Session too short to summarize."

        # Clean transcript first - removes ANSI codes and deduplicates
        original_size = len(transcript)
        transcript = clean_transcript(transcript)
        cleaned_size = len(transcript)
        reduction = ((original_size - cleaned_size) / original_size * 100)
        print(f"  Cleaned transcript: {original_size:,} → {cleaned_size:,} chars ({reduction:.1f}% reduction)")

        # Trim very large transcripts for Ollama (smaller context window)
        # Gemini 2.0 Flash has 1M token context, so no trimming needed
        if self.provider == "ollama":
            # Target: ~30k tokens = ~60k characters (fits Qwen 2.5 32k context)
            max_chars = 60000
            if len(transcript) > max_chars:
                # Take evenly from beginning, middle, and end for better coverage
                chunk_size = max_chars // 3
                first_part = transcript[:chunk_size]
                middle_start = len(transcript) // 2 - (chunk_size // 2)
                middle_part = transcript[middle_start:middle_start + chunk_size]
                last_part = transcript[-chunk_size:]
                transcript = f"{first_part}\n\n[... section omitted ...]\n\n{middle_part}\n\n[... section omitted ...]\n\n{last_part}"

        prompt = f"""You are an expert development session analyzer for Chronicle, a tool that tracks AI-assisted coding sessions.

TASK: Analyze this terminal session transcript and create a concise, actionable summary.

REQUIREMENTS:
- Focus on WHAT was built/fixed, not how the conversation went
- Extract key technical decisions and their rationale
- Identify specific files, functions, or components mentioned
- Note any blockers, bugs, or issues encountered
- Keep summary under {max_length} characters
- Use bullet points for clarity
- Be technical and specific (e.g., "Added PostgreSQL support" not "worked on database")

FORMAT:
## What Was Built
- [Main accomplishment 1]
- [Main accomplishment 2]

## Key Decisions
- [Decision and why]

## Files/Components Modified
- [Specific files or modules]

## Issues/Blockers (if any)
- [Any problems encountered]

SESSION TRANSCRIPT:
{transcript}

SUMMARY:"""

        import time

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.provider == "gemini":
                    response = self.model.generate_content(prompt)
                    summary = response.text.strip()
                elif self.provider == "ollama":
                    response = self.ollama_client.generate(
                        model=self.model_name,
                        prompt=prompt
                    )
                    summary = response['response'].strip()
                else:
                    return f"Unknown provider: {self.provider}"

                # Ensure summary isn't too long
                if len(summary) > max_length:
                    summary = summary[:max_length-3] + "..."

                return summary
            except Exception as e:
                error_str = str(e)
                # Check if it's a rate limit error (Gemini only)
                if self.provider == "gemini" and ("429" in error_str or "quota" in error_str.lower()):
                    if attempt < max_retries - 1:
                        # Extract retry delay if available
                        import re
                        match = re.search(r'retry in (\d+\.?\d*)s', error_str)
                        if match:
                            delay = float(match.group(1)) + 1  # Add 1 second buffer
                        else:
                            delay = 10 * (attempt + 1)  # Exponential backoff

                        print(f"  Rate limit hit, retrying in {delay:.1f}s...")
                        time.sleep(delay)
                        continue

                return f"Error generating summary: {error_str}"

        return "Error: Rate limit exceeded after retries"

    def summarize_day(self, commits: list, interactions: list) -> Optional[str]:
        """Summarize a day's worth of development activity.

        Args:
            commits: List of commit messages
            interactions: List of AI interaction prompts

        Returns:
            Summary text or None if failed
        """
        # Build context from commits and interactions
        context = "Daily Development Summary\n\n"

        if commits:
            context += "Git Commits:\n"
            for commit in commits:
                context += f"- {commit}\n"
            context += "\n"

        if interactions:
            context += "AI Interactions:\n"
            for interaction in interactions:
                context += f"- {interaction}\n"

        prompt = f"""Summarize this day of development activity in 200 words or less.

Focus on:
- Main features or bugs worked on
- Important decisions made
- Overall progress

{context}

Summary:"""

        try:
            if self.provider == "gemini":
                response = self.model.generate_content(prompt)
                return response.text.strip()
            elif self.provider == "ollama":
                response = self.ollama_client.generate(
                    model=self.model_name,
                    prompt=prompt
                )
                return response['response'].strip()
            else:
                return f"Unknown provider: {self.provider}"
        except Exception as e:
            return f"Error generating summary: {str(e)}"

    def calculate_adaptive_delay(self, chunk_text: str, cumulative_summary: str) -> float:
        """Calculate delay needed to stay under Gemini rate limits (1M tokens/min).

        Args:
            chunk_text: Text of the current chunk
            cumulative_summary: Current cumulative summary

        Returns:
            Delay in seconds needed before making the next request
        """
        if self.provider != "gemini":
            return 0  # No rate limiting for other providers

        # Estimate tokens for this chunk (rough estimate: 4 chars per token)
        estimated_tokens = (len(chunk_text) + len(cumulative_summary)) / 4

        # Calculate tokens used in last 60 seconds (rolling window)
        now = time.time()
        cutoff = now - 60

        # Remove old requests from tracking
        self.recent_requests = [(ts, tokens) for ts, tokens in self.recent_requests if ts > cutoff]

        # Sum recent usage
        recent_usage = sum(tokens for _, tokens in self.recent_requests)

        # If adding this chunk would exceed 90% of limit, calculate wait time
        # Using 900K instead of 1M for safety buffer
        rate_limit = 900000
        if recent_usage + estimated_tokens > rate_limit:
            # Wait until oldest request expires from the window
            if self.recent_requests:
                oldest_timestamp = self.recent_requests[0][0]
                delay = (oldest_timestamp + 60) - now + 2  # +2s buffer
                return max(delay, 0)

        # Default minimum delay between chunks
        return 8

    def summarize_session_chunked(
        self,
        session_id: int,
        chunk_size_lines: int = 1000,
        db_session = None,
        use_cli: bool = False,
        cli_tool: str = "qwen"
    ) -> str:
        """Summarize a large session incrementally using rolling summaries.

        This breaks a large transcript into chunks, summarizes each chunk,
        and maintains a cumulative summary that gets updated with each new chunk.
        This avoids token limits and works with sessions of any size.

        Args:
            session_id: ID of the session to summarize
            chunk_size_lines: Number of lines per chunk (default: 1000)
            db_session: SQLAlchemy database session (required)
            use_cli: If True, use CLI tools (qwen/gemini) instead of API (bypasses rate limits)
            cli_tool: Which CLI tool to use if use_cli=True ("qwen" or "gemini")

        Returns:
            Final cumulative summary

        Raises:
            ValueError: If session not found or db_session not provided
        """
        from backend.database.models import AIInteraction, SessionSummaryChunk
        from datetime import datetime

        if db_session is None:
            raise ValueError("db_session is required for chunked summarization")

        # Get the session
        session = db_session.query(AIInteraction).filter_by(id=session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if not session.is_session:
            raise ValueError(f"ID {session_id} is not a session")

        if not session.session_transcript:
            raise ValueError(f"Session {session_id} has no transcript")

        # Clean transcript first - removes ANSI codes and deduplicates
        original_size = len(session.session_transcript)
        cleaned_transcript = clean_transcript(session.session_transcript)
        cleaned_size = len(cleaned_transcript)
        reduction = ((original_size - cleaned_size) / original_size * 100)
        print(f"🧹 Cleaned transcript: {original_size:,} → {cleaned_size:,} chars ({reduction:.1f}% reduction)")

        # Check for existing chunks (resume capability)
        existing_chunks = (
            db_session.query(SessionSummaryChunk)
            .filter_by(session_id=session_id)
            .order_by(SessionSummaryChunk.chunk_number)
            .all()
        )

        # Split cleaned transcript into lines
        lines = cleaned_transcript.split('\n')
        total_lines = len(lines)
        print(f"📄 Total lines: {total_lines:,}")
        print(f"📦 Chunk size: {chunk_size_lines:,} lines")

        num_chunks = (total_lines + chunk_size_lines - 1) // chunk_size_lines  # Ceiling division
        print(f"🔢 Total chunks: {num_chunks}")

        # Resume from first missing chunk (detects gaps)
        start_chunk = 0
        cumulative_summary = ""
        if existing_chunks:
            # Find first gap in chunk sequence
            existing_chunk_numbers = {chunk.chunk_number for chunk in existing_chunks}
            expected_chunks = set(range(1, num_chunks + 1))
            missing_chunks = sorted(expected_chunks - existing_chunk_numbers)

            if missing_chunks:
                # Start from first missing chunk
                first_missing = missing_chunks[0]
                start_chunk = first_missing - 1  # Convert to 0-indexed
                # Use cumulative summary from chunk before the gap
                chunk_before_gap = [c for c in existing_chunks if c.chunk_number == first_missing - 1]
                if chunk_before_gap:
                    cumulative_summary = chunk_before_gap[0].cumulative_summary
                print(f"🔄 Resuming from chunk {first_missing} (found gap in chunks, {len(missing_chunks)} chunks missing)")
            else:
                # All chunks complete
                print(f"✅ All {len(existing_chunks)} chunks already completed!")
                return existing_chunks[-1].cumulative_summary

        print()

        for chunk_num in range(start_chunk, num_chunks):
            start_line = chunk_num * chunk_size_lines
            end_line = min(start_line + chunk_size_lines, total_lines)

            chunk_lines = lines[start_line:end_line]
            chunk_text = '\n'.join(chunk_lines)

            print(f"Processing chunk {chunk_num + 1}/{num_chunks} (lines {start_line}-{end_line})...")

            # Generate prompt based on whether this is the first chunk
            if chunk_num == 0:
                # First chunk - just summarize it
                prompt = f"""Summarize this development session transcript chunk. Focus on:
- What was accomplished
- Technical decisions made
- Files created or modified
- Any issues or blockers
- Key discussion points

Keep the summary concise but informative (2-3 paragraphs).

Transcript chunk:
{chunk_text}

Summary:"""
            else:
                # Subsequent chunks - update the cumulative summary
                prompt = f"""You are maintaining a running summary of a development session.

PREVIOUS SUMMARY (everything up to line {start_line}):
{cumulative_summary}

NEW ACTIVITY (lines {start_line}-{end_line}):
{chunk_text}

Update the summary to incorporate this new activity. Keep it cohesive and well-organized.
Focus on the overall narrative and progress. Avoid just appending - integrate the new information.

Updated Summary:"""

            # Generate summary for this chunk with automatic retry
            max_retries = 5  # Increased from 3 to handle rate limits better
            chunk_summary = None

            for attempt in range(max_retries):
                try:
                    if use_cli:
                        # Use CLI tool to bypass API rate limits
                        import subprocess

                        # qwen uses -p/--prompt for non-interactive mode
                        # Prompt can be passed as argument
                        result = subprocess.run(
                            [cli_tool, '-p', prompt],
                            capture_output=True,
                            text=True,
                            timeout=120  # 2 minute timeout per chunk
                        )

                        if result.returncode != 0:
                            raise Exception(f"{cli_tool} CLI failed: {result.stderr}")

                        chunk_summary = result.stdout.strip()

                    elif self.provider == "gemini":
                        # Track this request for adaptive rate limiting
                        estimated_tokens = (len(chunk_text) + len(cumulative_summary)) / 4
                        self.recent_requests.append((time.time(), estimated_tokens))

                        response = self.model.generate_content(prompt)
                        chunk_summary = response.text.strip()
                    elif self.provider == "ollama":
                        response = self.ollama_client.generate(
                            model=self.model_name,
                            prompt=prompt
                        )
                        chunk_summary = response['response'].strip()
                    else:
                        raise ValueError(f"Unknown provider: {self.provider}")

                    # Success - break out of retry loop
                    break

                except Exception as e:
                    error_str = str(e)
                    is_rate_limit = self.provider == "gemini" and ("429" in error_str or "quota" in error_str.lower() or "Resource has been exhausted" in error_str)

                    if attempt < max_retries - 1:  # Still have retries left
                        if is_rate_limit:
                            # Extract retry delay if available
                            import re
                            match = re.search(r'retry in (\d+\.?\d*)s', error_str)
                            if match:
                                delay = float(match.group(1)) + 2  # Add 2 second buffer
                            else:
                                delay = 15 * (attempt + 1)  # 15s, 30s, 45s

                            print(f"  ⚠️  Rate limit hit on chunk {chunk_num + 1}, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})...")
                        else:
                            # Other error - use exponential backoff
                            delay = 5 * (2 ** attempt)  # 5s, 10s, 20s
                            print(f"  ⚠️  Error on chunk {chunk_num + 1}: {error_str[:100]}")
                            print(f"  Retrying in {delay}s (attempt {attempt + 1}/{max_retries})...")

                        time.sleep(delay)
                    else:
                        # Final retry failed
                        error_msg = f"Error summarizing chunk {chunk_num + 1} after {max_retries} attempts: {error_str}"
                        print(f"❌ {error_msg}")
                        # Save what we have so far
                        if cumulative_summary:
                            return cumulative_summary + f"\n\n[Error: Could not complete summarization at chunk {chunk_num + 1} after {max_retries} retries]"
                        else:
                            raise ValueError(error_msg)

            # Check if we got a summary (should always be true if we didn't raise/return)
            if chunk_summary is None:
                raise ValueError(f"Failed to generate summary for chunk {chunk_num + 1}")

            # Update cumulative summary
            if chunk_num == 0:
                cumulative_summary = chunk_summary
            else:
                # The chunk_summary IS the updated cumulative summary
                cumulative_summary = chunk_summary

            # Save this chunk to database (delete existing if present to avoid duplicates)
            db_session.query(SessionSummaryChunk).filter_by(
                session_id=session_id,
                chunk_number=chunk_num + 1
            ).delete()

            chunk_record = SessionSummaryChunk(
                session_id=session_id,
                chunk_number=chunk_num + 1,
                chunk_start_line=start_line,
                chunk_end_line=end_line,
                chunk_summary=chunk_summary,
                cumulative_summary=cumulative_summary,
                timestamp=datetime.now()
            )
            db_session.add(chunk_record)
            db_session.commit()

            print(f"✓ Chunk {chunk_num + 1} summarized ({len(chunk_summary)} chars)")
            print()

            # Adaptive delay between chunks to avoid rate limits
            if chunk_num < num_chunks - 1:
                # Calculate next chunk's text to estimate delay
                next_start = (chunk_num + 1) * chunk_size_lines
                next_end = min(next_start + chunk_size_lines, total_lines)
                next_chunk_text = '\n'.join(lines[next_start:next_end])

                delay = self.calculate_adaptive_delay(next_chunk_text, cumulative_summary)
                if delay > 0:
                    print(f"⏱️  Waiting {delay:.1f}s before next chunk (adaptive rate limit)...")
                    time.sleep(delay)
                    print()

        # Save final summary to the session
        session.response_summary = cumulative_summary
        session.summary_generated = True
        db_session.commit()

        print(f"✅ Session {session_id} fully summarized!")
        print(f"Final summary: {len(cumulative_summary)} characters")
        print(f"Saved {num_chunks} chunks to database")

        return cumulative_summary
