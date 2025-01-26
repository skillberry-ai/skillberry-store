import logging
import os
import sys

logger = logging.getLogger(__name__)


def configure_logging():
    """
    Configure logging for the application.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logger.info("Configuring logging")


def get_files_directory_path():
    """
    Determine the directory path for file operations.

    Priority:
    1. Environment variable "DIRECTORY_PATH"
    2. Command line argument (first argument after the script name)
    3. Default path: "/tmp/files"

    Returns:
        str: The resolved directory path.
    """
    env_path = os.getenv("DIRECTORY_PATH")
    if env_path:
        logger.info(f"Using directory path from environment: {env_path}")
        return env_path
    if len(sys.argv) > 1:
        logger.info(f"Using directory path from command line: {sys.argv[1]}")
        return sys.argv[1]
    default_path = "/tmp/files"
    logger.info(f"Using default directory path: {default_path}")
    return default_path


def get_descriptions_directory():
    """
    Get the directory path for descriptions.
    """
    env_path = os.getenv("DESCRIPTIONS_DIRECTORY")
    if env_path:
        logger.info(f"Using descriptions directory from environment: {env_path}")
        return env_path
    default_path = "/tmp/descriptions"
    logger.info(f"Using default descriptions directory: {default_path}")
    return default_path


def get_metadata_directory():
    """
    Get the directory path for metadata.
    """
    env_path = os.getenv("METADATA_DIRECTORY")
    if env_path:
        logger.info(f"Using metadata directory from environment: {env_path}")
        return env_path
    default_path = "/tmp/metadata"
    logger.info(f"Using default metadata directory: {default_path}")
    return default_path
