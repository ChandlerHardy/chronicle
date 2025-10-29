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


class TestModelSelection:
    """Tests for Gemini model selection and fallback logic."""

    def test_select_best_available_model_prefers_2_5_flash_for_small_medium(self):
        """Test that gemini-2.5-flash is selected first for small/medium sessions when available."""
        from backend.services.summarizer import GeminiModel
        from backend.database.models import GeminiModelUsage
        from datetime import date

        with patch('backend.core.config.get_config') as mock_config:
            mock_config.return_value.summarization_provider = "gemini"
            mock_config.return_value.gemini_api_key = "test_key"
            mock_config.return_value.default_model = "gemini-2.0-flash"

            summarizer = Summarizer()

            # Mock database to return zero usage for all models
            with patch.object(summarizer, '_get_usage_for_date', return_value=0):
                # Act - select model for general/small/medium complexity
                model = summarizer._select_best_available_model(complexity="general")

                # Assert - should return FLASH_2_5 (gemini-2.5-flash) for small/medium
                assert model is not None
                assert model.value["name"] == "gemini-2.5-flash"

    def test_select_best_available_model_small_medium_falls_back_to_preview(self):
        """Test fallback to gemini-2.5-flash-preview when 2.5-flash is exhausted (small/medium)."""
        from backend.services.summarizer import GeminiModel

        with patch('backend.core.config.get_config') as mock_config:
            mock_config.return_value.summarization_provider = "gemini"
            mock_config.return_value.gemini_api_key = "test_key"
            mock_config.return_value.default_model = "gemini-2.0-flash"

            summarizer = Summarizer()

            # Mock: 2.5-flash is at limit, others available
            def mock_usage(model_name, date):
                if model_name == "gemini-2.5-flash":
                    return 250  # At daily limit
                return 0

            with patch.object(summarizer, '_get_usage_for_date', side_effect=mock_usage):
                # Act - small/medium sessions prefer 2.5 models
                model = summarizer._select_best_available_model(complexity="general")

                # Assert - should fallback to FLASH_PREVIEW (next 2.5 model)
                assert model is not None
                assert model.value["name"] == "gemini-2.5-flash-preview-09-2025"

    def test_select_best_available_model_large_falls_back_to_2_0_flash_lite(self):
        """Test fallback to gemini-2.0-flash-lite when 2.0-flash is exhausted (large sessions)."""
        from backend.services.summarizer import GeminiModel

        with patch('backend.core.config.get_config') as mock_config:
            mock_config.return_value.summarization_provider = "gemini"
            mock_config.return_value.gemini_api_key = "test_key"
            mock_config.return_value.default_model = "gemini-2.0-flash"

            summarizer = Summarizer()

            # Mock: 2.0-flash exhausted, others available
            def mock_usage(model_name, date):
                if model_name == "gemini-2.0-flash":
                    return 200  # At limit
                return 0

            with patch.object(summarizer, '_get_usage_for_date', side_effect=mock_usage):
                # Act - large sessions prefer 2.0 models
                model = summarizer._select_best_available_model(complexity="large")

                # Assert - should fallback to FLASH_2_0_LITE (next 2.0 model)
                assert model is not None
                assert model.value["name"] == "gemini-2.0-flash-lite"

    def test_select_best_available_model_large_falls_back_to_2_5_flash(self):
        """Test fallback to gemini-2.5-flash when both 2.0 models are exhausted (large sessions)."""
        from backend.services.summarizer import GeminiModel

        with patch('backend.core.config.get_config') as mock_config:
            mock_config.return_value.summarization_provider = "gemini"
            mock_config.return_value.gemini_api_key = "test_key"
            mock_config.return_value.default_model = "gemini-2.0-flash"

            summarizer = Summarizer()

            # Mock: both 2.0 models exhausted
            def mock_usage(model_name, date):
                if model_name == "gemini-2.0-flash":
                    return 200  # At limit
                if model_name == "gemini-2.0-flash-lite":
                    return 200  # At limit
                return 0

            with patch.object(summarizer, '_get_usage_for_date', side_effect=mock_usage):
                # Act - large sessions
                model = summarizer._select_best_available_model(complexity="large")

                # Assert - should fallback to FLASH_2_5 (first 2.5 model)
                assert model is not None
                assert model.value["name"] == "gemini-2.5-flash"

    def test_select_best_available_model_returns_none_when_all_exhausted(self):
        """Test that None is returned when all models are at their daily limits."""
        with patch('backend.core.config.get_config') as mock_config:
            mock_config.return_value.summarization_provider = "gemini"
            mock_config.return_value.gemini_api_key = "test_key"
            mock_config.return_value.default_model = "gemini-2.0-flash"

            summarizer = Summarizer()

            # Mock: all models at their limits
            def mock_usage(model_name, date):
                # Return usage equal to each model's daily limit
                if model_name == "gemini-2.0-flash":
                    return 200
                if model_name == "gemini-2.0-flash-lite":
                    return 200
                if model_name == "gemini-2.5-flash":
                    return 250
                if model_name == "gemini-2.5-flash-preview-09-2025":
                    return 250
                if model_name == "gemini-2.5-flash-lite":
                    return 1000
                return 0

            with patch.object(summarizer, '_get_usage_for_date', side_effect=mock_usage):
                # Act
                model = summarizer._select_best_available_model(complexity="general")

                # Assert - should return None
                assert model is None

    def test_select_best_available_model_for_large_sessions_prefers_2_0_flash(self):
        """Test that large sessions (>50K lines) prefer gemini-2.0-flash for 1M TPM."""
        from backend.services.summarizer import GeminiModel

        with patch('backend.core.config.get_config') as mock_config:
            mock_config.return_value.summarization_provider = "gemini"
            mock_config.return_value.gemini_api_key = "test_key"
            mock_config.return_value.default_model = "gemini-2.0-flash"

            summarizer = Summarizer()

            # Mock database to return zero usage for all models
            with patch.object(summarizer, '_get_usage_for_date', return_value=0):
                # Act - select model for large complexity (>50K lines)
                model = summarizer._select_best_available_model(complexity="large")

                # Assert - should prefer FLASH_2_0 for 1M TPM
                assert model is not None
                assert model.value["name"] == "gemini-2.0-flash"

    def test_increment_usage_creates_new_record_for_model(self):
        """Test that _increment_usage creates a new usage record if none exists."""
        from backend.database.models import GeminiModelUsage
        from datetime import date

        with patch('backend.core.config.get_config') as mock_config:
            mock_config.return_value.summarization_provider = "gemini"
            mock_config.return_value.gemini_api_key = "test_key"
            mock_config.return_value.default_model = "gemini-2.0-flash"

            summarizer = Summarizer()

            # Mock database session
            mock_db = Mock()
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = None  # No existing record

            mock_db.query.return_value = mock_query

            with patch.object(summarizer, '_get_db_session', return_value=mock_db):
                # Act - increment usage for a model
                summarizer._increment_usage("gemini-2.0-flash", input_chars=1000, output_chars=500)

                # Assert - should create new record
                mock_db.add.assert_called_once()
                mock_db.commit.assert_called_once()

    def test_increment_usage_updates_existing_record(self):
        """Test that _increment_usage updates an existing usage record."""
        from backend.database.models import GeminiModelUsage
        from datetime import date

        with patch('backend.core.config.get_config') as mock_config:
            mock_config.return_value.summarization_provider = "gemini"
            mock_config.return_value.gemini_api_key = "test_key"
            mock_config.return_value.default_model = "gemini-2.0-flash"

            summarizer = Summarizer()

            # Mock existing usage record
            existing_usage = Mock(spec=GeminiModelUsage)
            existing_usage.request_count = 5
            existing_usage.total_input_characters = 5000
            existing_usage.total_output_characters = 2500
            existing_usage.total_input_tokens = 1250
            existing_usage.total_output_tokens = 625

            # Mock database session
            mock_db = Mock()
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = existing_usage

            mock_db.query.return_value = mock_query

            with patch.object(summarizer, '_get_db_session', return_value=mock_db):
                # Act - increment usage
                summarizer._increment_usage("gemini-2.0-flash", input_chars=1000, output_chars=500)

                # Assert - should update existing record
                assert existing_usage.request_count == 6
                assert existing_usage.total_input_characters == 6000
                assert existing_usage.total_output_characters == 3000
                mock_db.commit.assert_called_once()
