"""AI summarization service using Gemini or Ollama."""

import time
from typing import Optional
from backend.core.config import get_config


class Summarizer:
    """Generate summaries using Gemini API or Ollama."""

    def __init__(self):
        """Initialize summarizer based on configured provider."""
        self.config = get_config()
        self.provider = self.config.summarization_provider

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

    def _clean_transcript(self, transcript: str) -> str:
        """Clean transcript by removing ANSI codes and deduplicating lines.

        Args:
            transcript: Raw transcript

        Returns:
            Cleaned transcript
        """
        import re

        # Remove ANSI escape codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', transcript)

        # Remove CSI sequences and other control characters
        cleaned = re.sub(r'\x1B\[[0-9;]*[a-zA-Z]', '', cleaned)
        cleaned = re.sub(r'[\x00-\x1F\x7F]', '', cleaned)  # Remove control chars except newlines
        cleaned = re.sub(r'\n+', '\n', cleaned)  # Collapse multiple newlines

        # Deduplicate consecutive identical lines (like spinner redraws)
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
        transcript = self._clean_transcript(transcript)
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

        # Check for existing chunks (resume capability)
        existing_chunks = (
            db_session.query(SessionSummaryChunk)
            .filter_by(session_id=session_id)
            .order_by(SessionSummaryChunk.chunk_number)
            .all()
        )

        # Split transcript into lines
        lines = session.session_transcript.split('\n')
        total_lines = len(lines)
        print(f"📄 Total lines: {total_lines:,}")
        print(f"📦 Chunk size: {chunk_size_lines:,} lines")

        num_chunks = (total_lines + chunk_size_lines - 1) // chunk_size_lines  # Ceiling division
        print(f"🔢 Total chunks: {num_chunks}")

        # Resume from last chunk if available
        start_chunk = 0
        cumulative_summary = ""
        if existing_chunks:
            last_chunk = existing_chunks[-1]
            start_chunk = last_chunk.chunk_number
            cumulative_summary = last_chunk.cumulative_summary
            print(f"🔄 Resuming from chunk {start_chunk} (found {len(existing_chunks)} existing chunks)")

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
            max_retries = 3
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

            # Save this chunk to database
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

            # Add delay between chunks to avoid rate limits (Gemini free tier: 1M tokens/min)
            # Conservative estimate: ~1000 tokens per chunk (10K lines * ~100 chars/line / 1000)
            # With 10K line chunks, we're safe processing ~5-10 per minute
            # Add 8 second delay = max 7.5 chunks/min = well under 1M tokens/min
            if self.provider == "gemini" and chunk_num < num_chunks - 1:
                delay = 8  # 8 seconds between chunks
                print(f"⏱️  Waiting {delay}s before next chunk (rate limit protection)...")
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
