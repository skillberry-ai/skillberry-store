"""Root conftest.py for pytest configuration."""
import os


def pytest_configure(config):
    """Configure pytest based on environment variables."""
    # Enable debug logging if SBS_TEST_DEBUG is set to true
    if os.getenv("SBS_TEST_DEBUG", "").lower() == "true":
        config.option.log_cli = True
        config.option.log_cli_level = "DEBUG"
    else:
        # Explicitly disable CLI logging when not in debug mode
        config.option.log_cli = False

# Made with Bob
