"""AI summarization service using Gemini."""

import google.generativeai as genai
from typing import Optional
from backend.core.config import get_config


class Summarizer:
    """Generate summaries using Gemini API."""

    def __init__(self):
        """Initialize summarizer with API key from config."""
        self.config = get_config()
        self.api_key = self.config.gemini_api_key

        if not self.api_key:
            raise ValueError(
                "Gemini API key not configured. "
                "Set it with: chronicle config ai.gemini_api_key YOUR_KEY"
            )

        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.config.default_model)

    def test_connection(self) -> dict:
        """Test the Gemini API connection.

        Returns:
            Dictionary with test results
        """
        try:
            response = self.model.generate_content("Say 'Hello from Chronicle!' in exactly 5 words.")

            return {
                "success": True,
                "model": self.config.default_model,
                "response": response.text.strip(),
                "message": "API connection successful!"
            }
        except Exception as e:
            return {
                "success": False,
                "model": self.config.default_model,
                "error": str(e),
                "message": "API connection failed"
            }

    def summarize_session(self, transcript: str, max_length: int = 500) -> Optional[str]:
        """Summarize a session transcript.

        Args:
            transcript: Full session transcript
            max_length: Maximum summary length in characters

        Returns:
            Summary text or None if failed
        """
        if not transcript or len(transcript) < 50:
            return "Session too short to summarize."

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

        try:
            response = self.model.generate_content(prompt)
            summary = response.text.strip()

            # Ensure summary isn't too long
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."

            return summary
        except Exception as e:
            return f"Error generating summary: {str(e)}"

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
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error generating summary: {str(e)}"
