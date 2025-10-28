"""Tests for AI summarization service."""

import pytest
from unittest.mock import Mock, patch
from backend.services.summarizer import Summarizer


class TestExtractKeywords:
    """Tests for the extract_keywords method."""

    def test_extract_keywords_with_gemini_returns_5_to_25_keywords(self):
        """Test that keyword extraction returns between 5-25 keywords (updated range)."""
        # Arrange - Create a mock Gemini response with exactly 20 keywords
        mock_response = Mock()
        mock_response.text = '''["pytest", "testing", "TDD", "code coverage", "unit tests",
                                  "integration tests", "mock objects", "fixtures", "assertions",
                                  "test runner", "continuous integration", "CI/CD", "regression testing",
                                  "test-driven development", "automated testing", "quality assurance",
                                  "software testing", "test suite", "test cases", "debugging"]'''

        with patch('backend.core.config.get_config') as mock_config:
            # Mock configuration
            mock_config.return_value.summarization_provider = "gemini"
            mock_config.return_value.gemini_api_key = "test_key"
            mock_config.return_value.default_model = "gemini-2.0-flash"

            summarizer = Summarizer()

            # Mock the model's generate_content method
            with patch.object(summarizer.model, 'generate_content', return_value=mock_response):
                # Act
                summary = """Implemented comprehensive test suite for Chronicle project.
                Added pytest fixtures for database setup, created unit tests for git monitoring,
                and integration tests for AI tracking. Configured CI/CD pipeline with GitHub Actions."""

                keywords = summarizer.extract_keywords(summary)

                # Assert - Should return exactly 20 keywords (all valid)
                assert isinstance(keywords, list)
                assert len(keywords) == 20
                assert all(isinstance(k, str) for k in keywords)
                assert "pytest" in keywords
                assert "tdd" in keywords  # Should be lowercased

    def test_extract_keywords_limits_to_25_maximum(self):
        """Test that keyword extraction limits to maximum 25 keywords."""
        # Arrange - Create a mock response with 30 keywords
        mock_keywords = [f"keyword{i}" for i in range(30)]
        mock_response = Mock()
        mock_response.text = str(mock_keywords).replace("'", '"')

        with patch('backend.core.config.get_config') as mock_config:
            mock_config.return_value.summarization_provider = "gemini"
            mock_config.return_value.gemini_api_key = "test_key"
            mock_config.return_value.default_model = "gemini-2.0-flash"

            summarizer = Summarizer()

            with patch.object(summarizer.model, 'generate_content', return_value=mock_response):
                # Act
                summary = "This is a summary text with many concepts about software development and testing practices."
                keywords = summarizer.extract_keywords(summary)

                # Assert - Should limit to exactly 25 keywords
                assert len(keywords) == 25
                assert keywords[0] == "keyword0"
                assert keywords[24] == "keyword24"
                # Keyword 25+ should be excluded
                assert "keyword25" not in keywords
                assert "keyword29" not in keywords

    def test_extract_keywords_with_empty_summary_returns_empty_list(self):
        """Test that empty summaries return an empty list."""
        with patch('backend.core.config.get_config') as mock_config:
            mock_config.return_value.summarization_provider = "gemini"
            mock_config.return_value.gemini_api_key = "test_key"
            mock_config.return_value.default_model = "gemini-2.0-flash"

            summarizer = Summarizer()

            # Act & Assert
            assert summarizer.extract_keywords("") == []
            assert summarizer.extract_keywords(None) == []
            assert summarizer.extract_keywords("Short") == []  # < 50 chars

    def test_extract_keywords_filters_short_keywords(self):
        """Test that keywords with less than 3 characters are filtered out."""
        # Arrange - Mix of valid and short keywords
        mock_response = Mock()
        mock_response.text = '["py", "a", "pytest", "ok", "testing", "ci", "TDD", "ab"]'

        with patch('backend.core.config.get_config') as mock_config:
            mock_config.return_value.summarization_provider = "gemini"
            mock_config.return_value.gemini_api_key = "test_key"
            mock_config.return_value.default_model = "gemini-2.0-flash"

            summarizer = Summarizer()

            with patch.object(summarizer.model, 'generate_content', return_value=mock_response):
                # Act
                summary = "A comprehensive summary about Python testing practices with CI/CD pipelines and automation tools."
                keywords = summarizer.extract_keywords(summary)

                # Assert - Only keywords with 3+ chars should remain
                assert len(keywords) == 3  # "pytest", "testing", "tdd"
                assert "pytest" in keywords
                assert "testing" in keywords
                assert "tdd" in keywords
                # Short keywords should be filtered
                assert "py" not in keywords
                assert "a" not in keywords
                assert "ok" not in keywords
                assert "ci" not in keywords
                assert "ab" not in keywords

    def test_extract_keywords_handles_markdown_code_blocks(self):
        """Test that keywords wrapped in markdown code blocks are properly extracted."""
        # Arrange - Response wrapped in markdown
        mock_response = Mock()
        mock_response.text = '''```json
["pytest", "testing", "TDD", "fixtures", "mocking"]
```'''

        with patch('backend.core.config.get_config') as mock_config:
            mock_config.return_value.summarization_provider = "gemini"
            mock_config.return_value.gemini_api_key = "test_key"
            mock_config.return_value.default_model = "gemini-2.0-flash"

            summarizer = Summarizer()

            with patch.object(summarizer.model, 'generate_content', return_value=mock_response):
                # Act
                summary = "Summary about testing practices including unit tests, integration tests, and test-driven development."
                keywords = summarizer.extract_keywords(summary)

                # Assert
                assert len(keywords) == 5
                assert "pytest" in keywords
                assert "testing" in keywords

    def test_extract_keywords_handles_api_errors_gracefully(self):
        """Test that API errors return empty list instead of crashing."""
        with patch('backend.core.config.get_config') as mock_config:
            mock_config.return_value.summarization_provider = "gemini"
            mock_config.return_value.gemini_api_key = "test_key"
            mock_config.return_value.default_model = "gemini-2.0-flash"

            summarizer = Summarizer()

            # Mock API error
            with patch.object(summarizer.model, 'generate_content', side_effect=Exception("API Error")):
                # Act
                summary = "Some comprehensive summary text about development work and technical decisions made during the session."
                keywords = summarizer.extract_keywords(summary)

                # Assert - Should return empty list on error
                assert keywords == []

    def test_extract_keywords_lowercases_all_keywords(self):
        """Test that all keywords are converted to lowercase."""
        # Arrange - Mixed case keywords
        mock_response = Mock()
        mock_response.text = '["PyTest", "TESTING", "TdD", "Code Coverage", "Unit Tests"]'

        with patch('backend.core.config.get_config') as mock_config:
            mock_config.return_value.summarization_provider = "gemini"
            mock_config.return_value.gemini_api_key = "test_key"
            mock_config.return_value.default_model = "gemini-2.0-flash"

            summarizer = Summarizer()

            with patch.object(summarizer.model, 'generate_content', return_value=mock_response):
                # Act
                summary = "Summary about testing practices, frameworks, and methodologies used in modern software development."
                keywords = summarizer.extract_keywords(summary)

                # Assert - All should be lowercase
                assert "pytest" in keywords
                assert "testing" in keywords
                assert "tdd" in keywords
                assert "code coverage" in keywords
                assert "unit tests" in keywords
                # Original case should not exist
                assert "PyTest" not in keywords
                assert "TESTING" not in keywords
