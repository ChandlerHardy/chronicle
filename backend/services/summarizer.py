"""AI summarization service using Gemini or Ollama."""

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
