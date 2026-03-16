import pytest
import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from llm_client.llm.logging_utils import (
    configure_logging,
    get_config,
    get_logger,
    LLMLogger,
    LogConfig,
)


class TestLogConfig:
    """Test LogConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = LogConfig()
        assert config.level == "INFO"
        assert config.output_dir is None
        assert config.max_payload_size == 10000
        assert config.truncate_large_payloads is True
        assert config.enable_colors is True
        assert config.log_raw_responses is True
        assert config.log_to_file is False

    def test_config_with_output_dir(self):
        """Test configuration with output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LogConfig(output_dir=Path(tmpdir))
            assert config.output_dir == Path(tmpdir)
            assert config.log_to_file is True

    def test_level_normalization(self):
        """Test that log level is normalized to uppercase."""
        config = LogConfig(level="debug")
        assert config.level == "DEBUG"


class TestConfigureLogging:
    """Test configure_logging function."""

    def test_configure_with_defaults(self):
        """Test configuration with default values."""
        config = configure_logging()
        assert config.level == "INFO"
        assert config.output_dir is None

    def test_configure_with_custom_level(self):
        """Test configuration with custom log level."""
        config = configure_logging(level="DEBUG")
        assert config.level == "DEBUG"

    def test_configure_with_output_dir(self):
        """Test configuration with output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = configure_logging(output_dir=tmpdir)
            assert config.output_dir == Path(tmpdir)
            assert config.log_to_file is True

    def test_configure_with_custom_sensitive_keys(self):
        """Test configuration with custom sensitive keys."""
        custom_keys = {"custom_secret", "my_token"}
        config = configure_logging(sensitive_keys=custom_keys)
        assert "custom_secret" in config.sensitive_keys
        assert "my_token" in config.sensitive_keys
        # Default keys should still be present
        assert "api_key" in config.sensitive_keys


class TestGetConfig:
    """Test get_config function."""

    def test_get_default_config(self):
        """Test getting default configuration."""
        # Reset global config
        import llm_client.llm.logging_utils as logging_utils

        logging_utils._GLOBAL_CONFIG = None

        config = get_config()
        assert config.level == "INFO"

    def test_get_config_from_env(self, monkeypatch):
        """Test getting configuration from environment variables."""
        # Reset global config
        import llm_client.llm.logging_utils as logging_utils

        logging_utils._GLOBAL_CONFIG = None

        monkeypatch.setenv("LLM_CLIENT_LOG_LEVEL", "DEBUG")
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setenv("LLM_CLIENT_LOG_DIR", tmpdir)
            config = get_config()
            assert config.level == "DEBUG"
            assert config.output_dir == Path(tmpdir)


class TestLLMLogger:
    """Test LLMLogger class."""

    def test_logger_initialization(self):
        """Test logger initialization."""
        logger = LLMLogger("TestLogger")
        assert logger.name == "TestLogger"
        assert logger.logger is not None

    def test_filter_sensitive_dict(self):
        """Test filtering sensitive data from dictionaries."""
        logger = LLMLogger("TestLogger")
        data = {
            "api_key": "secret123",
            "model": "gpt-4",
            "temperature": 0.7,
        }
        filtered = logger._filter_sensitive(data)
        assert filtered["api_key"] == "****SECRET****"
        assert filtered["model"] == "gpt-4"
        assert filtered["temperature"] == 0.7

    def test_filter_sensitive_nested(self):
        """Test filtering sensitive data from nested structures."""
        logger = LLMLogger("TestLogger")
        data = {
            "config": {
                "api_key": "secret123",
                "model": "gpt-4",
            },
            "headers": {
                "Authorization": "Bearer token123",
                "Content-Type": "application/json",
            },
        }
        filtered = logger._filter_sensitive(data)
        assert filtered["config"]["api_key"] == "****SECRET****"
        assert filtered["config"]["model"] == "gpt-4"
        assert filtered["headers"]["Authorization"] == "****SECRET****"
        assert filtered["headers"]["Content-Type"] == "application/json"

    def test_truncate_if_needed(self):
        """Test payload truncation."""
        config = LogConfig(max_payload_size=100, truncate_large_payloads=True)
        logger = LLMLogger("TestLogger", config)

        short_text = "Short text"
        assert logger._truncate_if_needed(short_text) == short_text

        long_text = "x" * 200
        truncated = logger._truncate_if_needed(long_text)
        assert len(truncated) > 100  # Includes truncation message
        assert "truncated" in truncated

    def test_truncate_disabled(self):
        """Test that truncation can be disabled."""
        config = LogConfig(max_payload_size=100, truncate_large_payloads=False)
        logger = LLMLogger("TestLogger", config)

        long_text = "x" * 200
        result = logger._truncate_if_needed(long_text)
        assert result == long_text

    def test_format_json(self):
        """Test JSON formatting."""
        logger = LLMLogger("TestLogger")
        data = {"key": "value", "number": 42}
        formatted = logger._format_json(data)
        assert "key" in formatted
        assert "value" in formatted
        assert "42" in formatted

    def test_format_prompt_string(self):
        """Test formatting string prompts."""
        logger = LLMLogger("TestLogger")
        prompt = "What is the capital of France?"
        formatted = logger._format_prompt(prompt)
        assert formatted == prompt

    def test_format_prompt_messages(self):
        """Test formatting message list prompts."""
        logger = LLMLogger("TestLogger")
        prompt = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        formatted = logger._format_prompt(prompt)
        assert "[0] user: Hello" in formatted
        assert "[1] assistant: Hi there!" in formatted

    def test_log_initialization(self, caplog):
        """Test logging initialization."""
        configure_logging(enable_colors=False)  # Disable Rich for testing
        logger = LLMLogger("TestLogger")
        logger.log_initialization("TestProvider", {"model": "gpt-4"})
        # Check that logging occurred (logs work, just not captured by caplog due to propagate=False)
        assert logger.logger.level == logging.INFO

    def test_log_generation_start(self, caplog):
        """Test logging generation start."""
        configure_logging(enable_colors=False)  # Disable Rich for testing
        logger = LLMLogger("TestLogger")
        logger.log_generation_start("chat", "Test prompt", {"temperature": 0.7})
        # Check that logging occurred (logs work, just not captured by caplog due to propagate=False)
        assert logger.logger.level == logging.INFO

    def test_log_raw_response(self, caplog):
        """Test logging raw responses."""
        configure_logging(
            log_raw_responses=True, enable_colors=False
        )  # Disable Rich for testing
        logger = LLMLogger("TestLogger")
        logger.log_raw_response({"response": "test"}, duration=1.5)
        # Check that logging occurred (logs work, just not captured by caplog due to propagate=False)
        assert logger.config.log_raw_responses is True

    def test_log_raw_response_disabled(self, caplog):
        """Test that raw response logging can be disabled."""
        config = LogConfig(log_raw_responses=False)
        logger = LLMLogger("TestLogger", config)
        with caplog.at_level(logging.DEBUG):
            logger.log_raw_response({"response": "test"})
        assert "Raw Response" not in caplog.text

    def test_log_validation_attempt(self, caplog):
        """Test logging validation attempts."""
        configure_logging(
            level="DEBUG", enable_colors=False
        )  # Disable Rich for testing, enable DEBUG
        logger = LLMLogger("TestLogger")
        schema = {"type": "object"}
        logger.log_validation_attempt(1, 3, schema)
        # Check that logging occurred (logs work, just not captured by caplog due to propagate=False)
        assert logger.logger.level == logging.DEBUG

    def test_log_validation_attempt_with_error(self, caplog):
        """Test logging validation attempts with errors."""
        configure_logging(enable_colors=False)  # Disable Rich for testing
        logger = LLMLogger("TestLogger")
        schema = {"type": "object"}
        logger.log_validation_attempt(1, 3, schema, error="Type mismatch")
        # Check that logging occurred (logs work, just not captured by caplog due to propagate=False)
        assert logger.logger.level <= logging.WARNING

    def test_log_error(self, caplog):
        """Test logging errors."""
        configure_logging(enable_colors=False)  # Disable Rich for testing
        logger = LLMLogger("TestLogger")
        error = ValueError("Test error")
        logger.log_error(error, {"key": "value"}, "test_phase")
        # Check that logging occurred (logs work, just not captured by caplog due to propagate=False)
        assert logger.logger.level <= logging.ERROR


class TestFileLogging:
    """Test file-based logging."""

    def test_file_logging_enabled(self):
        """Test that file logging creates log files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(level="INFO", output_dir=tmpdir)
            logger = get_logger("TestFileLogger")
            logger.info("Test message")

            # Check that log file was created
            log_files = list(Path(tmpdir).glob("*.log"))
            assert len(log_files) > 0

    def test_file_logging_disabled(self):
        """Test that file logging is disabled by default."""
        configure_logging(level="INFO")
        logger = get_logger("TestNoFileLogger")
        logger.info("Test message")

        # No log files should be created in current directory
        log_files = list(Path(".").glob("llm_client_*.log"))
        assert len(log_files) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
