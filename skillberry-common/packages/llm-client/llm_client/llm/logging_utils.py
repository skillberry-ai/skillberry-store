"""
Centralized logging utilities for LLM client with Rich formatting support.

This module provides comprehensive logging capabilities including:
- Colored console output with Rich library
- Optional file-based logging with rotation
- Automatic sensitive data filtering
- Configurable log levels and formatting
- Visual formatting for payloads and responses
"""

import logging
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime
from logging.handlers import RotatingFileHandler

try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.tree import Tree
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None  # type: ignore
    RichHandler = None  # type: ignore


# Global configuration
_GLOBAL_CONFIG: Optional["LogConfig"] = None
_LOGGERS: Dict[str, logging.Logger] = {}


@dataclass
class LogConfig:
    """Configuration for LLM client logging."""

    level: str = "INFO"
    output_dir: Optional[Path] = None
    max_payload_size: int = 10000
    truncate_large_payloads: bool = True
    enable_colors: bool = True
    log_raw_responses: bool = True
    log_to_file: bool = False
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    sensitive_keys: Set[str] = field(
        default_factory=lambda: {
            "api_key",
            "authorization",
            "secret",
            "password",
            "token",
            "credentials",
            "key",
            "auth",
        }
    )

    def __post_init__(self):
        """Validate and normalize configuration."""
        self.level = self.level.upper()
        if self.output_dir:
            self.output_dir = Path(self.output_dir)
            self.log_to_file = True


def configure_logging(
    level: str = "INFO",
    output_dir: Optional[Union[str, Path]] = None,
    max_payload_size: int = 10000,
    truncate_large_payloads: bool = True,
    enable_colors: bool = True,
    log_raw_responses: bool = True,
    max_file_size: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    sensitive_keys: Optional[Set[str]] = None,
) -> LogConfig:
    """
    Configure global logging settings for LLM client.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        output_dir: Optional directory for log files
        max_payload_size: Maximum characters to display in payloads
        truncate_large_payloads: Whether to truncate large payloads
        enable_colors: Enable colored console output (requires Rich)
        log_raw_responses: Log full raw responses before parsing
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
        sensitive_keys: Additional sensitive keys to filter

    Returns:
        LogConfig instance
    """
    global _GLOBAL_CONFIG

    config_sensitive_keys = {
        "api_key",
        "authorization",
        "secret",
        "password",
        "token",
        "credentials",
        "key",
        "auth",
    }
    if sensitive_keys:
        config_sensitive_keys.update(sensitive_keys)

    _GLOBAL_CONFIG = LogConfig(
        level=level,
        output_dir=Path(output_dir) if output_dir else None,
        max_payload_size=max_payload_size,
        truncate_large_payloads=truncate_large_payloads,
        enable_colors=enable_colors and RICH_AVAILABLE,
        log_raw_responses=log_raw_responses,
        max_file_size=max_file_size,
        backup_count=backup_count,
        sensitive_keys=config_sensitive_keys,
    )

    # Reset existing loggers to pick up new config
    for logger_name in list(_LOGGERS.keys()):
        _LOGGERS.pop(logger_name)

    return _GLOBAL_CONFIG


def get_config() -> LogConfig:
    """Get current logging configuration."""
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        # Check environment variables
        level = os.getenv("LLM_CLIENT_LOG_LEVEL", "INFO")
        output_dir = os.getenv("LLM_CLIENT_LOG_DIR")
        _GLOBAL_CONFIG = LogConfig(
            level=level,
            output_dir=Path(output_dir) if output_dir else None,
        )
    return _GLOBAL_CONFIG


def get_llm_logger(name: str) -> logging.Logger:
    """
    Get or create a logger for LLM client components.

    Args:
        name: Logger name (typically class name)

    Returns:
        Configured logger instance
    """
    if name in _LOGGERS:
        return _LOGGERS[name]

    config = get_config()
    logger = logging.getLogger(f"llm_client.{name}")
    logger.setLevel(getattr(logging, config.level))
    logger.propagate = False

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler
    if config.enable_colors and RICH_AVAILABLE:
        console_handler = RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=True,
            show_path=False,
        )
    else:
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)

    console_handler.setLevel(getattr(logging, config.level))
    logger.addHandler(console_handler)

    # File handler (if configured)
    if config.log_to_file and config.output_dir:
        config.output_dir.mkdir(parents=True, exist_ok=True)
        log_file = config.output_dir / f"llm_client_{name}.log"

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=config.max_file_size,
            backupCount=config.backup_count,
        )
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(getattr(logging, config.level))
        logger.addHandler(file_handler)

    _LOGGERS[name] = logger
    return logger


class LLMLogger:
    """
    Enhanced logger for LLM client with Rich formatting and utilities.
    """

    def __init__(self, name: str, config: Optional[LogConfig] = None):
        """
        Initialize LLM logger.

        Args:
            name: Logger name
            config: Optional configuration (uses global if not provided)
        """
        self.name = name
        self.config = config or get_config()
        self.logger = get_llm_logger(name)
        self.console = (
            Console()
            if RICH_AVAILABLE and self.config.enable_colors and Console is not None
            else None
        )

    def _filter_sensitive(self, data: Any) -> Any:
        """
        Recursively filter sensitive data from dictionaries.

        Args:
            data: Data to filter

        Returns:
            Filtered data with sensitive values masked
        """
        if isinstance(data, dict):
            filtered = {}
            for key, value in data.items():
                key_lower = key.lower()
                if any(
                    sensitive in key_lower for sensitive in self.config.sensitive_keys
                ):
                    filtered[key] = "****SECRET****"
                elif isinstance(value, (dict, list)):
                    filtered[key] = self._filter_sensitive(value)
                else:
                    filtered[key] = value
            return filtered
        elif isinstance(data, list):
            return [self._filter_sensitive(item) for item in data]
        else:
            return data

    def _truncate_if_needed(self, text: str) -> str:
        """
        Truncate text if it exceeds max payload size.

        Args:
            text: Text to potentially truncate

        Returns:
            Original or truncated text
        """
        if not self.config.truncate_large_payloads:
            return text

        if len(text) > self.config.max_payload_size:
            truncated_chars = len(text) - self.config.max_payload_size
            return (
                text[: self.config.max_payload_size]
                + f"\n... (truncated {truncated_chars} characters)"
            )
        return text

    def _format_json(self, data: Any) -> str:
        """
        Format data as JSON string.

        Args:
            data: Data to format

        Returns:
            JSON formatted string
        """
        try:
            return json.dumps(data, indent=2, default=str)
        except Exception:
            return str(data)

    def _format_prompt(self, prompt: Union[str, List[Dict[str, Any]]]) -> str:
        """
        Format prompt for logging.

        Args:
            prompt: Prompt (string or messages list)

        Returns:
            Formatted prompt string
        """
        if isinstance(prompt, str):
            return self._truncate_if_needed(prompt)
        elif isinstance(prompt, list):
            formatted_messages = []
            for i, msg in enumerate(prompt):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                formatted_messages.append(f"[{i}] {role}: {content}")
            return self._truncate_if_needed("\n".join(formatted_messages))
        else:
            return str(prompt)

    def log_initialization(self, provider_class: str, config: Dict[str, Any]):
        """
        Log client initialization.

        Args:
            provider_class: Name of provider class
            config: Configuration parameters (will be filtered)
        """
        filtered_config = self._filter_sensitive(config)
        self.logger.info(f"🚀 Initializing {self.name}")
        self.logger.debug(f"Provider class: {provider_class}")
        self.logger.debug(f"Configuration: {self._format_json(filtered_config)}")

    def log_method_registration(self, methods: Dict[str, str]):
        """
        Log method registration.

        Args:
            methods: Dictionary of mode -> method path
        """
        self.logger.debug(f"Registered methods: {self._format_json(methods)}")

    def log_generation_start(
        self,
        mode: str,
        prompt: Union[str, List[Dict[str, Any]]],
        params: Dict[str, Any],
    ):
        """
        Log start of generation.

        Args:
            mode: Generation mode
            prompt: Input prompt
            params: Generation parameters
        """
        self.logger.info(f"🚀 Starting generation - Mode: {mode}")

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"📝 Prompt:\n{self._format_prompt(prompt)}")
            filtered_params = self._filter_sensitive(params)
            self.logger.debug(f"⚙️  Parameters: {self._format_json(filtered_params)}")

    def log_raw_response(self, response: Any, duration: Optional[float] = None):
        """
        Log raw response from LLM before parsing.

        Args:
            response: Raw response object
            duration: Optional duration in seconds
        """
        if not self.config.log_raw_responses:
            return

        if self.logger.isEnabledFor(logging.DEBUG):
            response_str = self._format_json(response)
            response_str = self._truncate_if_needed(response_str)

            duration_str = f" (Duration: {duration:.2f}s)" if duration else ""
            self.logger.debug(f"📦 Raw Response{duration_str}:\n{response_str}")

    def log_parsed_response(self, parsed: Any, length: Optional[int] = None):
        """
        Log parsed response.

        Args:
            parsed: Parsed response
            length: Optional length of response
        """
        if self.logger.isEnabledFor(logging.DEBUG):
            parsed_str = str(parsed)
            if length and length > 500:
                parsed_str = parsed_str[:500] + f"... ({length - 500} more chars)"
            self.logger.debug(f"📄 Parsed Response: {parsed_str}")

    def log_generation_complete(
        self,
        duration: Optional[float] = None,
        tokens: Optional[int] = None,
        length: Optional[int] = None,
    ):
        """
        Log completion of generation.

        Args:
            duration: Duration in seconds
            tokens: Token count
            length: Response length
        """
        parts = ["✅ Generation complete"]
        if duration:
            parts.append(f"Duration: {duration:.2f}s")
        if tokens:
            parts.append(f"Tokens: {tokens}")
        if length:
            parts.append(f"Length: {length} chars")

        self.logger.info(" | ".join(parts))

    def log_validation_attempt(
        self,
        attempt: int,
        max_attempts: int,
        schema: Any,
        error: Optional[str] = None,
    ):
        """
        Log validation attempt.

        Args:
            attempt: Current attempt number
            max_attempts: Maximum attempts
            schema: Schema being validated against
            error: Optional error message
        """
        if error:
            self.logger.warning(
                f"⚠️  Validation failed (Attempt {attempt}/{max_attempts}): {error}"
            )
        else:
            self.logger.debug(f"🔍 Validation attempt {attempt}/{max_attempts}")
            if self.logger.isEnabledFor(logging.DEBUG):
                schema_str = self._format_json(schema)
                self.logger.debug(f"Schema: {schema_str}")

    def log_validation_success(self, attempts: int):
        """
        Log successful validation.

        Args:
            attempts: Number of attempts taken
        """
        if attempts > 1:
            self.logger.info(f"✅ Validation successful (after {attempts} attempts)")
        else:
            self.logger.debug("✅ Validation successful")

    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        phase: str = "unknown",
    ):
        """
        Log error with context.

        Args:
            error: Exception that occurred
            context: Optional context information
            phase: Phase where error occurred
        """
        self.logger.error(f"❌ Error in {phase}: {type(error).__name__}: {str(error)}")

        if context and self.logger.isEnabledFor(logging.DEBUG):
            filtered_context = self._filter_sensitive(context)
            self.logger.debug(f"Context: {self._format_json(filtered_context)}")

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.exception("Full traceback:")

    def log_retry(self, attempt: int, max_attempts: int, reason: str):
        """
        Log retry attempt.

        Args:
            attempt: Current attempt number
            max_attempts: Maximum attempts
            reason: Reason for retry
        """
        self.logger.warning(f"🔄 Retrying (Attempt {attempt}/{max_attempts}): {reason}")

    def log_parameter_mapping(
        self, generic_args: Dict[str, Any], mapped_args: Dict[str, Any]
    ):
        """
        Log parameter mapping from generic to provider-specific.

        Args:
            generic_args: Generic arguments
            mapped_args: Mapped provider-specific arguments
        """
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                f"🔀 Parameter mapping:\n"
                f"  Generic: {self._format_json(generic_args)}\n"
                f"  Mapped: {self._format_json(mapped_args)}"
            )

    # Convenience methods for different log levels
    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)

    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)

    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False):
        """Log error message."""
        self.logger.error(message, exc_info=exc_info)


# Convenience function to get logger
def get_logger(name: str) -> LLMLogger:
    """
    Get an LLMLogger instance.

    Args:
        name: Logger name

    Returns:
        LLMLogger instance
    """
    return LLMLogger(name)
