import logging
import os
import tempfile
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


def _default_sbs_dir(subdir: str) -> str:
    """Return a cross-platform default directory under the system temp folder.

    The base directory can be overridden via the SBS_BASE_DIR environment variable.
    If not set, falls back to the OS temp directory.
    """
    base = os.getenv("SBS_BASE_DIR") or os.path.join(
        tempfile.gettempdir(), "skillberry-store"
    )
    return os.path.join(base, subdir)


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
        "RESET": "\033[0m",
    }

    LVL_COLORS = {
        "DEBUG": ANSI_COLORS["CYAN"],  # Cyan
        "INFO": ANSI_COLORS["GREEN"],  # Green
        "WARNING": ANSI_COLORS["YELLOW"],  # Yellow
        "ERROR": ANSI_COLORS["RED"],  # Red
        "CRITICAL": ANSI_COLORS["MAGENTA"],  # Magenta
    }

    def __init__(self, colored=True):
        self.colored = colored

    def format(self, record):
        log_color = self.LVL_COLORS.get(record.levelname, self.ANSI_COLORS["RESET"])
        formatter = None
        if self.colored:
            formatter = logging.Formatter(
                f'{self.ANSI_COLORS["GRAY"]}%(asctime)ss{self.ANSI_COLORS["RESET"]} - {self.ANSI_COLORS["WHITE"]}%(name)s{self.ANSI_COLORS["RESET"]} - {log_color}%(levelname)s - %(message)s{self.ANSI_COLORS["RESET"]} - (%(filename)s:%(lineno)d)'
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(filename)s:%(lineno)d"
            )
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
    2. Default path: "/tmp/skillberry-store/files"

    Returns:
        str: The resolved directory path.
    """
    env_path = os.getenv("SBS_DIRECTORY_PATH")
    if env_path:
        logger.info(f"Using directory path from environment: {env_path}")
        return env_path
    # Commented out: sys.argv[1] is unreliable when running inside pytest
    # as it picks up pytest's test directory argument instead of server config
    # if len(sys.argv) > 1:
    #     logger.info(f"Using directory path from command line: {sys.argv[1]}")
    #     return sys.argv[1]
    default_path = _default_sbs_dir("files")
    logger.info(f"Using default directory path: {default_path}")
    return default_path


def get_tools_descriptions_directory():
    """
    Get the directory path for tool descriptions.
    """
    env_path = os.getenv("SBS_TOOLS_DESCRIPTIONS_DIRECTORY")
    if env_path:
        logger.info(f"Using tools descriptions directory from environment: {env_path}")
        return env_path
    default_path = _default_sbs_dir("tools_descriptions")
    logger.info(f"Using default tools descriptions directory: {default_path}")
    return default_path


def get_metadata_directory():
    """
    Get the directory path for metadata.
    """
    env_path = os.getenv("SBS_METADATA_DIRECTORY")
    if env_path:
        logger.info(f"Using metadata directory from environment: {env_path}")
        return env_path
    default_path = _default_sbs_dir("metadata")
    logger.info(f"Using default metadata directory: {default_path}")
    return default_path


def get_snippets_directory():
    """
    Get the directory path for snippets.
    """
    env_path = os.getenv("SBS_SNIPPETS_DIRECTORY")
    if env_path:
        logger.info(f"Using snippets directory from environment: {env_path}")
        return env_path
    default_path = _default_sbs_dir("snippets")
    logger.info(f"Using default snippets directory: {default_path}")
    return default_path


def get_skills_directory():
    """
    Get the directory path for skills.
    """
    env_path = os.getenv("SBS_SKILLS_DIRECTORY")
    if env_path:
        logger.info(f"Using skills directory from environment: {env_path}")
        return env_path
    default_path = _default_sbs_dir("skills")
    logger.info(f"Using default skills directory: {default_path}")
    return default_path


def get_tools_directory():
    """
    Get the directory path for tools.
    """
    env_path = os.getenv("SBS_TOOLS_DIRECTORY")
    if env_path:
        logger.info(f"Using tools directory from environment: {env_path}")
        return env_path
    default_path = _default_sbs_dir("tools")
    logger.info(f"Using default tools directory: {default_path}")
    return default_path


def get_snippets_descriptions_directory():
    """
    Get the directory path for snippet descriptions.
    """
    env_path = os.getenv("SBS_SNIPPETS_DESCRIPTIONS_DIRECTORY")
    if env_path:
        logger.info(
            f"Using snippets descriptions directory from environment: {env_path}"
        )
        return env_path
    default_path = _default_sbs_dir("snippets_descriptions")
    logger.info(f"Using default snippets descriptions directory: {default_path}")
    return default_path


def get_skills_descriptions_directory():
    """
    Get the directory path for skill descriptions.
    """
    env_path = os.getenv("SBS_SKILLS_DESCRIPTIONS_DIRECTORY")
    if env_path:
        logger.info(f"Using skills descriptions directory from environment: {env_path}")
        return env_path
    default_path = _default_sbs_dir("skills_descriptions")
    logger.info(f"Using default skills descriptions directory: {default_path}")
    return default_path


def get_vmcp_directory():
    """
    Get the directory path for virtual MCP servers.
    """
    env_path = os.getenv("SBS_VMCP_DIRECTORY")
    if env_path:
        logger.info(f"Using vmcp directory from environment: {env_path}")
        return env_path
    default_path = _default_sbs_dir("vmcp")
    logger.info(f"Using default vmcp directory: {default_path}")
    return default_path


def get_vmcp_descriptions_directory():
    """
    Get the directory path for virtual MCP server descriptions.
    """
    env_path = os.getenv("SBS_VMCP_DESCRIPTIONS_DIRECTORY")
    if env_path:
        logger.info(f"Using vmcp descriptions directory from environment: {env_path}")
        return env_path
    default_path = _default_sbs_dir("vmcp_descriptions")
    logger.info(f"Using default vmcp descriptions directory: {default_path}")
    return default_path


def get_vnfs_directory():
    """
    Get the directory path for virtual NFS servers.
    """
    env_path = os.getenv("SBS_VNFS_DIRECTORY")
    if env_path:
        logger.info(f"Using vnfs directory from environment: {env_path}")
        return env_path
    default_path = _default_sbs_dir("vnfs_servers")
    logger.info(f"Using default vnfs directory: {default_path}")
    return default_path


def get_vnfs_descriptions_directory():
    """
    Get the directory path for virtual NFS server descriptions.
    """
    env_path = os.getenv("SBS_VNFS_DESCRIPTIONS_DIRECTORY")
    if env_path:
        logger.info(f"Using vnfs descriptions directory from environment: {env_path}")
        return env_path
    default_path = _default_sbs_dir("vnfs_descriptions")
    logger.info(f"Using default vnfs descriptions directory: {default_path}")
    return default_path


def is_auto_detect_dependencies_enabled():
    """
    Check if automatic tool dependency detection is enabled.

    Returns:
        bool: True if auto-detection is enabled (default), False otherwise.
    """
    env_value = os.getenv("AUTO_DETECT_TOOL_DEPENDENCIES", "true").lower()
    return env_value in ("true", "1", "yes", "on")
