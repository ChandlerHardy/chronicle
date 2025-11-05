"""AI summarization service using Gemini or Ollama."""

import time
from typing import Optional
from enum import Enum
from datetime import date, datetime
from backend.core.config import get_config
from backend.utils.transcript_cleaner import clean_transcript


class GeminiModel(Enum):
    """Available Gemini models with their daily limits and characteristics."""
    # PRO removed - 125K TPM limit too restrictive for chunked summarization
    # PRO = {
    #     "name": "gemini-2.5-pro",
    #     "daily_limit": 100,
    #     "priority": 1,
    #     "use_case": "large_sessions"
    # }
    FLASH_2_0 = {
        "name": "gemini-2.0-flash",
        "daily_limit": 200,  # Free tier: 200 RPD
        "priority": 1,
        "use_case": "primary"  # Primary model - 1M TPM, good balance of speed and quality
    }
    FLASH_2_0_LITE = {
        "name": "gemini-2.0-flash-lite",
        "daily_limit": 200,  # Free tier: 200 RPD (same as 2.0-flash)
        "priority": 2,
        "use_case": "first_fallback"  # First fallback - 1M TPM, faster but slightly lower quality
    }
    FLASH_2_5 = {
        "name": "gemini-2.5-flash",
        "daily_limit": 250,
        "priority": 3,
        "use_case": "second_fallback"  # Second fallback - stable 2.5, 250K TPM
    }
    FLASH_PREVIEW = {
        "name": "gemini-2.5-flash-preview-09-2025",
        "daily_limit": 250,
        "priority": 4,
        "use_case": "preview"  # Latest preview features, 250K TPM
    }
    FLASH_LITE = {
        "name": "gemini-2.5-flash-lite",
        "daily_limit": 1000,
        "priority": 5,
        "use_case": "high_volume"  # High quota fallback (250K TPM)
    }


class Summarizer:
    """Generate summaries using Gemini API or Ollama."""

    def __init__(self):
        """Initialize summarizer based on configured provider."""
        self.config = get_config()
        self.provider = self.config.summarization_provider
        # Track recent API requests for adaptive rate limiting
        self.recent_requests = []  # List of (timestamp, estimated_tokens)

        # Import here to avoid circular imports
        from backend.database.models import get_session
        self._get_db_session = get_session

        if self.provider == "gemini":
            try:
                import google.generativeai as genai
            except ImportError:
                raise ImportError(
                    "google-generativeai package not installed. "
                    "Install with: pip install --user google-generativeai\n"
                    "Or switch to Ollama: chronicle config ai.summarization_provider ollama"
                )

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

    def _get_usage_for_date(self, model_name: str, target_date: date) -> int:
        """Get current usage count for a model on a specific date.

        Args:
            model_name: Name of the Gemini model
            target_date: Date to check usage for

        Returns:
            Number of requests made to this model on this date
        """
        from backend.database.models import GeminiModelUsage
        from sqlalchemy import func

        db = self._get_db_session()
        try:
            # Query using DATE() function to compare only the date part
            usage = db.query(GeminiModelUsage).filter(
                GeminiModelUsage.model_name == model_name,
                func.date(GeminiModelUsage.date) == target_date
            ).first()
            return usage.request_count if usage else 0
        finally:
            db.close()

    def _increment_usage(self, model_name: str, input_chars: int = 0, output_chars: int = 0) -> None:
        """Increment usage count for a model today with character/token tracking.

        Args:
            model_name: Name of the Gemini model
            input_chars: Number of input characters
            output_chars: Number of output characters
        """
        from backend.database.models import GeminiModelUsage
        from sqlalchemy import func

        today = date.today()

        # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
        input_tokens = input_chars // 4
        output_tokens = output_chars // 4

        db = self._get_db_session()
        try:
            usage = db.query(GeminiModelUsage).filter(
                GeminiModelUsage.model_name == model_name,
                func.date(GeminiModelUsage.date) == today
            ).first()

            if usage:
                usage.request_count += 1
                usage.total_input_characters += input_chars
                usage.total_output_characters += output_chars
                usage.total_input_tokens += input_tokens
                usage.total_output_tokens += output_tokens
                usage.updated_at = datetime.now()
            else:
                usage = GeminiModelUsage(
                    model_name=model_name,
                    request_count=1,
                    total_input_characters=input_chars,
                    total_output_characters=output_chars,
                    total_input_tokens=input_tokens,
                    total_output_tokens=output_tokens,
                    date=today,
                    updated_at=datetime.now()
                )
                db.add(usage)
            db.commit()
        finally:
            db.close()

    def _select_best_available_model(self, complexity: str = "general") -> Optional[GeminiModel]:
        """Select the best available Gemini model based on complexity and current usage.

        Args:
            complexity: Task complexity - "large" (>50K lines), "medium", or "small"

        Returns:
            Best available GeminiModel or None if all models at limit
        """
        today = date.today()

        # Model selection varies by session size:
        # - Small/medium sessions: Prefer 2.5 models (latest features, 250K TPM sufficient)
        # - Large sessions: Prefer 2.0 models (need 1M TPM for 10K line chunks)

        if complexity == "large":
            # Large sessions (>50K lines): Need 1M TPM for 10K line chunks
            # Fallback to 2.5 models with smaller chunks if 2.0 models exhausted
            preferred_order = [
                GeminiModel.FLASH_2_0,         # 1M TPM - perfect for large chunks
                GeminiModel.FLASH_2_0_LITE,    # 1M TPM - faster fallback
                GeminiModel.FLASH_2_5,         # 250K TPM - will reduce chunk size
                GeminiModel.FLASH_PREVIEW,     # 250K TPM - preview features
                GeminiModel.FLASH_LITE,        # 250K TPM - high volume fallback
            ]
        else:
            # Small/medium sessions: Prefer 2.5 models (latest features)
            # 250K TPM is sufficient for 3-5K line chunks
            preferred_order = [
                GeminiModel.FLASH_2_5,         # Latest stable features, 250K TPM
                GeminiModel.FLASH_PREVIEW,     # Preview features, 250K TPM
                GeminiModel.FLASH_2_0,         # 1M TPM - overkill but available
                GeminiModel.FLASH_2_0_LITE,    # 1M TPM - faster fallback
                GeminiModel.FLASH_LITE,        # High volume fallback
            ]

        # Find first available model with quota remaining
        for model in preferred_order:
            current_usage = self._get_usage_for_date(model.value["name"], today)
            remaining = model.value["daily_limit"] - current_usage
            if remaining > 0:
                print(f"  Selected {model.value['name']} ({current_usage}/{model.value['daily_limit']} used, {remaining} remaining)")
                return model

        # If all models are at limit, return None
        print("  ⚠️  All Gemini models have reached their daily limits!")
        return None

    def get_usage_stats(self) -> dict:
        """Get current usage statistics for all Gemini models.

        Returns:
            Dictionary with usage stats per model
        """
        from backend.database.models import GeminiModelUsage
        from sqlalchemy import func

        today = date.today()
        stats = {}

        db = self._get_db_session()
        try:
            for model in GeminiModel:
                model_name = model.value["name"]
                usage_record = db.query(GeminiModelUsage).filter(
                    GeminiModelUsage.model_name == model_name,
                    func.date(GeminiModelUsage.date) == today
                ).first()

                current_usage = usage_record.request_count if usage_record else 0
                daily_limit = model.value["daily_limit"]

                stats[model_name] = {
                    "current_usage": current_usage,
                    "daily_limit": daily_limit,
                    "remaining": daily_limit - current_usage,
                    "percentage_used": round((current_usage / daily_limit) * 100, 1),
                    "priority": model.value["priority"],
                    "use_case": model.value["use_case"],
                    "total_input_characters": usage_record.total_input_characters if usage_record else 0,
                    "total_output_characters": usage_record.total_output_characters if usage_record else 0,
                    "total_input_tokens": usage_record.total_input_tokens if usage_record else 0,
                    "total_output_tokens": usage_record.total_output_tokens if usage_record else 0,
                }

            return stats
        finally:
            db.close()

    def extract_keywords(self, summary: str) -> list:
        """Extract searchable keywords from a session summary.

        Args:
            summary: The session summary text

        Returns:
            List of 5-15 relevant keywords/phrases
        """
        if not summary or len(summary) < 50:
            return []

        prompt = f"""Extract 5-25 searchable keywords/phrases from this development session summary.

REQUIREMENTS:
- Focus on technical terms, technologies, features, and concepts
- Include both single words and short phrases (2-3 words max)
- Prioritize terms that would help find this session later
- Avoid generic terms like "code", "session", "work", "implementation"
- Include framework names, file types, API names, bug types, etc.

EXAMPLES of good keywords:
- "MCP server", "rate limiting", "Gemini API", "SQLite migration"
- "authentication", "error handling", "database schema", "CSS styling"
- "pytest", "React", "TypeScript", "git hooks", "CI/CD"

Return ONLY a JSON array of strings, nothing else.

Summary:
{summary}

Keywords (JSON array only):"""

        try:
            if self.provider == "gemini":
                response = self.model.generate_content(prompt)
                keywords_json = response.text.strip()
                # Remove markdown code blocks if present
                if keywords_json.startswith("```"):
                    keywords_json = keywords_json.split("```")[1]
                    if keywords_json.startswith("json"):
                        keywords_json = keywords_json[4:]
                keywords_json = keywords_json.strip()

                import json
                keywords = json.loads(keywords_json)

                # Validate and clean
                if isinstance(keywords, list):
                    # Keep only strings, lowercase, limit to 25
                    keywords = [str(k).lower().strip() for k in keywords if k]
                    keywords = [k for k in keywords if len(k) > 2]  # Min 3 chars
                    return keywords[:25]

            elif self.provider == "ollama":
                response = self.ollama_client.generate(
                    model=self.model_name,
                    prompt=prompt,
                )
                keywords_json = response['response'].strip()
                # Remove markdown code blocks if present
                if keywords_json.startswith("```"):
                    keywords_json = keywords_json.split("```")[1]
                    if keywords_json.startswith("json"):
                        keywords_json = keywords_json[4:]
                keywords_json = keywords_json.strip()

                import json
                keywords = json.loads(keywords_json)

                # Validate and clean
                if isinstance(keywords, list):
                    keywords = [str(k).lower().strip() for k in keywords if k]
                    keywords = [k for k in keywords if len(k) > 2]
                    return keywords[:25]

        except Exception as e:
            print(f"⚠️  Keyword extraction failed: {e}")
            return []

        return []

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

TASK: Analyze this terminal session transcript and create a narrative summary that tells the story of what was built.

**SUMMARY STRUCTURE (required format):**

1. **Opening (1-2 sentences):** What was accomplished? Start with the main feature/milestone/fix.
   Example: "Implemented Milestone #13: Skill Auto-Activation System. The UserPromptSubmit hook now automatically detects and recommends relevant skills based on prompt analysis."

2. **Implementation Details (bullet points):** List specific files, tests, and code changes.
   - Created/modified files (be specific: "Created skill-rules.json with trigger patterns for 6 skills")
   - Tests written (count them: "27 test cases in test_hooks.py, all passing")
   - Bugs fixed (what and how)
   - Git commit info if visible

3. **Key Decisions (optional, if significant):** Why certain approaches were taken.
   Example: "Gitignored .claude/ directory to keep user configs private."

4. **Future Work (optional, brief):** Only if relevant planning occurred.
   Example: "Created Milestone #22 for Phase 2 enhancements."

**WHAT TO EXTRACT:**
- ✅ Git commit messages (best signal - use verbatim if found)
- ✅ What feature/milestone was completed
- ✅ Specific files created/modified
- ✅ Test counts and results
- ✅ Bug fixes with context
- ⚠️ Skip background discussions unless they led to implementation
- ❌ Ignore repeated content (LangChain explanation repeated 20x → mention once or skip)

**TONE:**
- Tell a story, not a file list
- "Built X" not "Modified Y"
- "Fixed false positive in trigger detection" not "Modified .claude/config/file.json"
- Technical but readable

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

    def chunk_transcript(self, transcript: str, ideal_chunk_length: int = 10000) -> list:
        """Split a transcript into chunks for processing.

        Args:
            transcript: The full transcript text
            ideal_chunk_length: Target length for each chunk in characters

        Returns:
            List of transcript chunks
        """
        if not transcript or not transcript.strip():
            return [""]

        lines = transcript.split('\n')
        chunks = []
        current_chunk = []
        current_length = 0

        for line in lines:
            line_length = len(line) + 1  # +1 for newline

            # Handle single very long lines by splitting them
            if len(line) > ideal_chunk_length:
                # Finish current chunk if it has content
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # Split the long line into multiple chunks
                for i in range(0, len(line), ideal_chunk_length):
                    long_chunk = line[i:i + ideal_chunk_length]
                    if i + ideal_chunk_length < len(line):
                        long_chunk += '\n'  # Add newline back if not last chunk
                    chunks.append(long_chunk)
            else:
                # If adding this line would exceed ideal length and we have content, start new chunk
                if current_length + line_length > ideal_chunk_length and current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = [line]
                    current_length = line_length
                else:
                    current_chunk.append(line)
                    current_length += line_length

        # Add the last chunk if it has content
        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

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

    def summarize_session_smart(
        self,
        session_id: int,
        db_session = None,
        use_cli: bool = False,
        cli_tool: str = "qwen",
        quiet: bool = False,
        force_chunked: bool = False
    ) -> str:
        """Smart summarization that chooses the best method based on session size.

        Args:
            session_id: ID of the session to summarize
            db_session: SQLAlchemy database session (required)
            use_cli: If True, use CLI tools instead of API
            cli_tool: Which CLI tool to use if use_cli=True
            quiet: If True, suppress status messages
            force_chunked: Force use of chunked summarization regardless of size

        Returns:
            Summary text
        """
        from backend.database.models import AIInteraction
        from pathlib import Path

        def qprint(*args, **kwargs):
            if not quiet:
                print(*args, **kwargs)

        if db_session is None:
            raise ValueError("db_session is required for smart summarization")

        # Get the session and transcript size
        session = db_session.query(AIInteraction).filter_by(id=session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Check transcript size to determine summarization method
        cleaned_path = Path.home() / ".ai-session" / "sessions" / f"session_{session_id}.cleaned"
        log_path = Path.home() / ".ai-session" / "sessions" / f"session_{session_id}.log"

        if cleaned_path.exists():
            with open(cleaned_path, 'r', encoding='utf-8', errors='ignore') as f:
                transcript = f.read()
        elif log_path.exists():
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_transcript = f.read()
            transcript = clean_transcript(raw_transcript)
        elif session.session_transcript:
            transcript = session.session_transcript
        else:
            raise ValueError(f"Session {session_id} has no transcript")

        total_lines = len(transcript.split('\n'))
        qprint(f"📄 Session {session_id}: {total_lines:,} lines")

        # Choose summarization method based on size
        if force_chunked:
            qprint(f"🔧 Using chunked summarization (forced)")
            return self.summarize_session_chunked(
                session_id=session_id,
                db_session=db_session,
                use_cli=use_cli,
                cli_tool=cli_tool,
                quiet=quiet
            )
        elif total_lines <= 8000:  # Small sessions - use regular summarization
            qprint(f"🚀 Using regular summarization (small session)")
            # Set adaptive max_length based on session size
            if total_lines <= 2000:
                max_length = 2500  # Very small sessions
            elif total_lines <= 5000:
                max_length = 3500  # Small sessions
            else:
                max_length = 4500  # Upper end of small sessions

            summary = self.summarize_session(transcript, max_length=max_length)

            # Extract keywords and update session
            keywords = self.extract_keywords(summary)
            session.response_summary = summary
            session.keywords_list = keywords
            session.summary_generated = True
            db_session.commit()

            qprint(f"✅ Session summarized: {len(summary)} characters")
            qprint(f"📌 Keywords: {', '.join(keywords[:5])}...")
            return summary

        else:
            qprint(f"🔧 Using chunked summarization (large session)")
            return self.summarize_session_chunked(
                session_id=session_id,
                db_session=db_session,
                use_cli=use_cli,
                cli_tool=cli_tool,
                quiet=quiet
            )

    def summarize_session_chunked(
        self,
        session_id: int,
        chunk_size_lines: int = 3000,
        db_session = None,
        use_cli: bool = False,
        cli_tool: str = "qwen",
        quiet: bool = False
    ) -> str:
        """Summarize a large session incrementally using rolling summaries.

        This breaks a large transcript into chunks, summarizes each chunk,
        and maintains a cumulative summary that gets updated with each new chunk.
        This avoids token limits and works with sessions of any size.

        Chunk size is automatically optimized based on session size:
        - Small (<10K lines): 3K line chunks (safe for all models)
        - Medium (10K-50K lines): 5K line chunks (balanced)
        - Large (>50K lines): 10K line chunks (leverages 2.0 Flash's 1M TPM)

        Args:
            session_id: ID of the session to summarize
            chunk_size_lines: Default chunk size (auto-adjusted based on session size)
            db_session: SQLAlchemy database session (required)
            use_cli: If True, use CLI tools (qwen/gemini) instead of API (bypasses rate limits)
            cli_tool: Which CLI tool to use if use_cli=True ("qwen" or "gemini")
            quiet: If True, suppress all status messages

        Returns:
            Final cumulative summary

        Raises:
            ValueError: If session not found or db_session not provided
        """
        from backend.database.models import AIInteraction, SessionSummaryChunk
        from datetime import datetime

        # Helper function for conditional printing
        def qprint(*args, **kwargs):
            if not quiet:
                print(*args, **kwargs)

        if db_session is None:
            raise ValueError("db_session is required for chunked summarization")

        # Get the session
        session = db_session.query(AIInteraction).filter_by(id=session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if not session.is_session:
            raise ValueError(f"ID {session_id} is not a session")

        # Read from .cleaned file (100x faster than SQLite!)
        # Cleaned files have ANSI codes removed and deduplication applied
        qprint("  Retrieving transcript...")
        from pathlib import Path

        cleaned_path = Path.home() / ".ai-session" / "sessions" / f"session_{session_id}.cleaned"
        log_path = Path.home() / ".ai-session" / "sessions" / f"session_{session_id}.log"

        if cleaned_path.exists():
            # Read from .cleaned file (FASTEST - already cleaned!)
            qprint(f"  📁 Reading from {cleaned_path.name}...")
            with open(cleaned_path, 'r', encoding='utf-8', errors='ignore') as f:
                transcript = f.read()
            qprint(f"  📄 Transcript size: {len(transcript):,} chars ({len(transcript) / 1024 / 1024:.2f} MB)")
        elif log_path.exists():
            # Fallback to .log file (needs cleaning)
            qprint(f"  📁 Reading from {log_path.name} (will clean)...")
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_transcript = f.read()
            qprint(f"  🧹 Cleaning transcript...")
            transcript = clean_transcript(raw_transcript)
            qprint(f"  📄 Transcript size: {len(transcript):,} chars ({len(transcript) / 1024 / 1024:.2f} MB)")
        elif session.session_transcript:
            # Fallback to database (SLOW but backward compatible with old sessions)
            qprint(f"  ⚠️  Reading from database (legacy session, slow)...")
            transcript = session.session_transcript
            qprint(f"  📄 Transcript size: {len(transcript):,} chars ({len(transcript) / 1024 / 1024:.2f} MB)")
        else:
            raise ValueError(f"Session {session_id} has no transcript (no .cleaned, .log, or database entry)")

        # Check for existing chunks (resume capability)
        qprint("  Checking for existing chunks...")
        existing_chunks = (
            db_session.query(SessionSummaryChunk)
            .filter_by(session_id=session_id)
            .order_by(SessionSummaryChunk.chunk_number)
            .all()
        )

        # Split transcript into lines
        lines = transcript.split('\n')
        total_lines = len(lines)
        qprint(f"📄 Total lines: {total_lines:,}")

        # Determine complexity and optimize chunk size based on session size
        if total_lines > 50000:
            complexity = "large"
            # Large sessions: use 10K chunks to leverage 2.0 Flash's 1M TPM
            # Math: 10K lines × 80 chars × 0.25 tokens/char ≈ 200K tokens (20% of 1M TPM)
            chunk_size_lines = 10000
        elif total_lines > 10000:
            complexity = "medium"
            # Medium sessions: 5K chunks balance speed and safety
            chunk_size_lines = 5000
        else:
            complexity = "small"
            # Small sessions: 3K chunks (provided default)
            # Already safe for all models

        # Check which model we'll likely use and adjust chunk size if needed
        # This ensures large sessions use smaller chunks when falling back to 2.5 models (250K TPM)
        if complexity == "large" and self.provider == "gemini":
            test_model = self._select_best_available_model(complexity)
            if test_model:
                # Check if it's a 2.5 model (has 250K TPM instead of 1M TPM)
                is_2_5_model = test_model in [GeminiModel.FLASH_2_5, GeminiModel.FLASH_PREVIEW, GeminiModel.FLASH_LITE]
                if is_2_5_model:
                    # Reduce chunk size for 2.5 models (250K TPM)
                    # Math: 5K lines × 80 chars × 0.25 tokens/char ≈ 100K tokens (40% of 250K TPM - safe margin)
                    chunk_size_lines = 5000
                    qprint(f"⚠️  Using 2.5 model ({test_model.value['name']}) - reducing chunk size for 250K TPM limit")

        qprint(f"📦 Chunk size: {chunk_size_lines:,} lines (optimized for {complexity} session)")

        # Adaptive summary length targets based on session complexity
        target_summary_lengths = {
            "small": 3500,   # Good detail for quick sessions
            "medium": 5000,  # Balanced detail with more narrative depth
            "large": 6500    # Comprehensive for complex sessions
        }
        target_length = target_summary_lengths[complexity]
        qprint(f"📏 Target summary length: {target_length:,} characters")

        num_chunks = (total_lines + chunk_size_lines - 1) // chunk_size_lines  # Ceiling division
        qprint(f"🔢 Total chunks: {num_chunks}")

        # Resume from first missing chunk (detects gaps)
        start_chunk = 0
        cumulative_summary = ""
        if existing_chunks:
            # Find first gap in chunk sequence
            existing_chunk_numbers = {chunk.chunk_number for chunk in existing_chunks}
            expected_chunks = set(range(1, num_chunks + 1))
            missing_chunks = sorted(expected_chunks - existing_chunk_numbers)

            if missing_chunks:
                # Start from first missing chunk (1-indexed display)
                first_missing = missing_chunks[0]
                start_chunk = first_missing - 1  # Convert to 0-indexed for loop

                # Use cumulative summary from chunk before the gap (if exists)
                if first_missing > 1:
                    chunk_before_gap = [c for c in existing_chunks if c.chunk_number == first_missing - 1]
                    if chunk_before_gap:
                        cumulative_summary = chunk_before_gap[0].cumulative_summary
                        qprint(f"🔄 Resuming from chunk {first_missing}/{num_chunks} ({len(missing_chunks)} chunks remaining)")
                    else:
                        qprint(f"⚠️  Gap detected: chunk {first_missing - 1} missing, starting from chunk {first_missing} without prior context")
                else:
                    qprint(f"🔄 Starting from chunk 1/{num_chunks} (no previous chunks found)")
            else:
                # All chunks complete - update session record if not already done
                qprint(f"✅ All {len(existing_chunks)} chunks already completed!")
                cumulative_summary = existing_chunks[-1].cumulative_summary

                # Update session record with final summary and keywords
                if not session.summary_generated:
                    qprint("  Extracting keywords from summary...")
                    keywords = self.extract_keywords(cumulative_summary)
                    qprint(f"  📌 Extracted {len(keywords)} keywords: {', '.join(keywords[:5])}...")

                    session.response_summary = cumulative_summary
                    session.keywords_list = keywords
                    session.summary_generated = True
                    db_session.commit()
                    qprint(f"✓ Updated session record with final summary and keywords")

                return cumulative_summary

        qprint()

        # Complexity and chunk size already determined above
        # Now process chunks using the optimized settings

        for chunk_num in range(start_chunk, num_chunks):
            start_line = chunk_num * chunk_size_lines
            end_line = min(start_line + chunk_size_lines, total_lines)

            chunk_lines = lines[start_line:end_line]
            chunk_text = '\n'.join(chunk_lines)

            qprint(f"Processing chunk {chunk_num + 1}/{num_chunks} (lines {start_line}-{end_line})...")

            # Generate prompt based on whether this is the first chunk
            if chunk_num == 0:
                # First chunk - just summarize it
                prompt = f"""Summarize this development session transcript chunk in exactly {target_length} characters. Tell the story of what was built - what problems were encountered, how they were solved, what was implemented, and what decisions were made.

🎯 TARGET LENGTH: ~{target_length} characters (flexible within 25%)
- Target range: {int(target_length * 0.75)} to {int(target_length * 1.25)} characters
- Prioritize completeness and structure over strict length limits
- If naturally shorter, that's fine - don't pad unnecessarily
- If naturally longer, include the detail - truncation only at 25% over target

FOCUS ON (in priority order):
1. **Implementation work**: What code/features were actually built
2. **Specific files created/modified** (with details)
3. **Tests written** (count them!)
4. **Git commits** (reference by hash and short title only, e.g., "Commit abc1234: Fix bug in...")
5. **Technical decisions and why**

IGNORE:
- Repeated conversations (if same explanation appears 20x, mention once)
- Background Q&A that didn't lead to implementation
- UI chrome and decorations

Keep the summary narrative and technical while respecting the target length.

Transcript chunk:
{chunk_text}

Summary (EXACTLY {target_length} characters):"""
            else:
                # Subsequent chunks - update the cumulative summary
                prompt = f"""You are maintaining a running summary of a development session. Your task is to integrate new activity into the existing narrative while keeping the TOTAL updated summary around {target_length} characters.

🎯 TARGET LENGTH: ~{target_length} characters (flexible within 25%)
- Current summary length: {len(cumulative_summary)} characters
- Target total length: {target_length} characters
- Acceptable range: {int(target_length * 0.75)} to {int(target_length * 1.25)} characters
- Only condense if you exceed {int(target_length * 1.25)} characters (25% grace period)

STRUCTURE PRESERVATION (CRITICAL):
- PRESERVE all structured sections from previous summary (bullets, headings, numbered lists)
- PRESERVE all technical details: file paths, line numbers, function names, test counts
- Add new work as additional sections/bullets, maintaining the organizational structure
- Only condense prose/narrative if you exceed the 25% grace period

PREVIOUS SUMMARY (everything up to line {start_line}):
{cumulative_summary}

NEW ACTIVITY (lines {start_line}-{end_line}):
{chunk_text}

INSTRUCTIONS:
- Tell the story - integrate new info into narrative, don't just append
- Prioritize implementation work (code, tests, commits) over discussion
- Skip repeated conversations (if LangChain explained 10x, you already summarized it once)
- Reference git commits by hash and short title only (e.g., "Commit abc1234: Fix bug"), NOT verbatim
- Keep it cohesive and well-organized
- Maintain structure quality: if previous summary had bullets/headers, keep them

Updated Summary (MUST be {target_length} characters +/- 5%):"""

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
                        # Select best available model based on quota
                        selected_model = self._select_best_available_model(complexity)
                        if not selected_model:
                            # All models at daily limit - try CLI fallback if available
                            if use_cli:
                                import subprocess
                                result = subprocess.run(
                                    [cli_tool, '-p', prompt],
                                    capture_output=True,
                                    text=True,
                                    timeout=120
                                )
                                if result.returncode != 0:
                                    raise Exception(f"All Gemini models at limit, {cli_tool} CLI also failed")
                                chunk_summary = result.stdout.strip()
                                break  # Skip retry loop if CLI works
                            else:
                                raise ValueError("All Gemini models have reached their daily limits. Try again tomorrow or use --use-cli option.")

                        model_name = selected_model.value["name"]

                        # Track this request for adaptive rate limiting
                        estimated_tokens = (len(chunk_text) + len(cumulative_summary)) / 4
                        self.recent_requests.append((time.time(), estimated_tokens))

                        # Create a temporary client for this specific model
                        temp_model = self.genai.GenerativeModel(model_name)
                        response = temp_model.generate_content(prompt)
                        chunk_summary = response.text.strip()

                        # Track usage for this model
                        input_chars = len(prompt)
                        output_chars = len(chunk_summary)
                        self._increment_usage(model_name, input_chars, output_chars)
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

                            qprint(f"  ⚠️  Rate limit hit on chunk {chunk_num + 1}, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})...")
                        else:
                            # Other error - use exponential backoff
                            delay = 5 * (2 ** attempt)  # 5s, 10s, 20s
                            qprint(f"  ⚠️  Error on chunk {chunk_num + 1}: {error_str[:100]}")
                            qprint(f"  Retrying in {delay}s (attempt {attempt + 1}/{max_retries})...")

                        time.sleep(delay)
                    else:
                        # Final retry failed
                        error_msg = f"Error summarizing chunk {chunk_num + 1} after {max_retries} attempts: {error_str}"
                        qprint(f"❌ {error_msg}")
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

            # Enforce length constraints with 25% grace period
            min_length = int(target_length * 0.75)
            max_length = int(target_length * 1.25)

            if len(cumulative_summary) > max_length:
                # Truncate to max_length, but try to end at sentence boundary
                truncated = cumulative_summary[:max_length]
                # Try to end at last sentence boundary
                last_sentence_end = max(
                    truncated.rfind('. '),
                    truncated.rfind('! '),
                    truncated.rfind('? '),
                    truncated.rfind('\n')
                )
                if last_sentence_end > max_length * 0.8:  # Only if we get a good cut point
                    cumulative_summary = truncated[:last_sentence_end + 1]
                else:
                    cumulative_summary = truncated + "..."

                qprint(f"  📏 Length enforcement: truncated from {len(chunk_summary)} to {len(cumulative_summary)} chars")
            elif len(cumulative_summary) < min_length and chunk_num == 0:
                # Only warn for short summaries on first chunk (subsequent chunks are updates)
                qprint(f"  ⚠️  Summary shorter than expected: {len(cumulative_summary)} chars (target: {target_length})")

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
                chunk_summary=chunk_summary,  # Original (pre-enforcement) summary
                cumulative_summary=cumulative_summary,  # Length-enforced summary
                timestamp=datetime.now()
            )
            db_session.add(chunk_record)
            db_session.commit()

            # Show original and final lengths if different
            if len(cumulative_summary) != len(chunk_summary):
                qprint(f"✓ Chunk {chunk_num + 1} summarized: {len(chunk_summary)} → {len(cumulative_summary)} chars")
            else:
                qprint(f"✓ Chunk {chunk_num + 1} summarized ({len(cumulative_summary)} chars)")
            qprint()

            # Adaptive delay between chunks to avoid rate limits
            if chunk_num < num_chunks - 1:
                # Calculate next chunk's text to estimate delay
                next_start = (chunk_num + 1) * chunk_size_lines
                next_end = min(next_start + chunk_size_lines, total_lines)
                next_chunk_text = '\n'.join(lines[next_start:next_end])

                delay = self.calculate_adaptive_delay(next_chunk_text, cumulative_summary)
                if delay > 0:
                    qprint(f"⏱️  Waiting {delay:.1f}s before next chunk (adaptive rate limit)...")
                    time.sleep(delay)
                    qprint()

        # Check if summary exceeded target length
        final_length = len(cumulative_summary)
        if final_length > target_length * 1.2:  # 20% buffer
            qprint(f"⚠️  Summary length ({final_length} chars) exceeds target ({target_length} chars) by {((final_length/target_length - 1) * 100):.1f}%")
        else:
            qprint(f"✅ Summary length: {final_length} chars (target: {target_length})")

        # Extract keywords from final summary
        qprint()
        qprint("  Extracting keywords from summary...")
        keywords = self.extract_keywords(cumulative_summary)
        qprint(f"  📌 Extracted {len(keywords)} keywords: {', '.join(keywords[:5])}...")

        # Save final summary and keywords to the session
        session.response_summary = cumulative_summary
        session.keywords_list = keywords
        session.summary_generated = True
        db_session.commit()

        qprint(f"✅ Session {session_id} fully summarized!")
        qprint(f"Final summary: {len(cumulative_summary)} characters")
        qprint(f"Keywords: {', '.join(keywords)}")
        qprint(f"Saved {num_chunks} chunks to database")

        return cumulative_summary
