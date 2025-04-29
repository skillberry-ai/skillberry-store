import logging
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


def configure_logging(lvl=logging.INFO):
    """
    Configure logging for the application.
    """
    logging.basicConfig(
        level=lvl,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logger.info("Configuring logging")



class ColoredFormatter(logging.Formatter):
    """A formatter that adds color to log messages."""

    ANSI_COLORS = {
        "BLACK": "\033[30m",
        "RED": "\033[31m",
        "GREEN": "\033[32m",
        "YELLOW": "\033[33m",
        "BLUE": "\033[34m",
        "MAGENTA": "\033[35m",
        "CYAN": "\033[36m",
        "WHITE": "\033[37m",
        "GRAY": "\033[90m",
        "ORANGE": "\033[38;5;208m",
        "BROWN": "\033[38;5;130m",
        "PURPLE": "\033[38;5;93m", 
        "PINK": "\033[38;5;201m",
        "BEIGE": "\033[38;5;230m", 
        "CRIMSON": "\033[38;5;196m", 
        "TURQUOISE": "\033[38;5;81m",
        "RESET": "\033[0m"
    }

    LVL_COLORS = {
        'DEBUG': ANSI_COLORS["CYAN"],  # Cyan
        'INFO': ANSI_COLORS["GREEN"],   # Green
        'WARNING': ANSI_COLORS["YELLOW"],# Yellow
        'ERROR': ANSI_COLORS["RED"],  # Red
        'CRITICAL': ANSI_COLORS["MAGENTA"], # Magenta
    }


    def __init__(self, colored=True):
        self.colored = colored

    def format(self, record):
        log_color = self.LVL_COLORS.get(record.levelname, self.ANSI_COLORS['RESET'])
        formatter = None
        if self.colored:
            formatter = logging.Formatter(f'{self.ANSI_COLORS["GRAY"]}%(asctime)ss{self.ANSI_COLORS["RESET"]} - {self.ANSI_COLORS["WHITE"]}%(name)s{self.ANSI_COLORS["RESET"]} - {log_color}%(levelname)s - %(message)s{self.ANSI_COLORS["RESET"]} - (%(filename)s:%(lineno)d)')
        else:
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(filename)s:%(lineno)d')
        return formatter.format(record)

def configure_logger(logger_name, log_level=logging.INFO, colored=True, log_file=None):
    """
    Configures a custom logger with a custom level and detailed, colored formatting.
    """

    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)  # Set the desired logging level
 
    if log_file:
        handler = logging.FileHandler(log_file)
    else:
        handler = logging.StreamHandler()  # Console output

    handler.setFormatter(ColoredFormatter(colored))
    logger.addHandler(handler)

    return logger


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
    env_path = os.getenv("BTS_DIRECTORY_PATH")
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
    env_path = os.getenv("BTS_DESCRIPTIONS_DIRECTORY")
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
    env_path = os.getenv("BTS_METADATA_DIRECTORY")
    if env_path:
        logger.info(f"Using metadata directory from environment: {env_path}")
        return env_path
    default_path = "/tmp/metadata"
    logger.info(f"Using default metadata directory: {default_path}")
    return default_path


def get_manifest_directory():
    """
    Get the directory path for manifest.
    """
    env_path = os.getenv("BTS_MANIFEST_DIRECTORY")
    if env_path:
        logger.info(f"Using manifest directory from environment: {env_path}")
        return env_path
    default_path = "/tmp/manifest"
    logger.info(f"Using default manifest directory: {default_path}")
    return default_path
