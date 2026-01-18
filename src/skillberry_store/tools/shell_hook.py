import logging
import os
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


class ShellHook:
    """
    A class to execute shell commands with dynamic context.
    """

    def __init__(self):
        pass

    def execute(self, hook_id: str, **context_vars: Any) -> None:
        """
        Executes a shell command with context variables.

        Parameters
        ----------
        hook_id : str
            A unique identifier for the hook location.
        **context_vars : Any
            Arbitrary keyword arguments representing context variables.

        Returns
        -------
        None

        Raises
        ------
        subprocess.CalledProcessError
            If the command execution fails.
        """

        # Get from the configuration the command template if it exists for the hook_id
        command_template = self.get_command_template(hook_id)
        if not command_template:
            # logger.debug(f"[{hook_id}] No command template found for this hook.")
            return

        try:
            command = command_template.format(**context_vars)
        except KeyError as e:
            logger.info(f"[{hook_id}] Missing context variable: {e}")
            return

        logger.info(f"[{hook_id}] Executing command: {command}")

        try:
            # Execute the command
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.info(f"[{hook_id}] Command output:\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"[{hook_id}] Command failed with error:\n{e.stderr}")

    def get_command_template(self, hook_id: str) -> Any | None:
        """
        Retrieves the command template for the given hook ID.

        Parameters
        ----------
        hook_id : str
            A unique identifier for the hook location.

        Returns
        -------
        str
            The command template associated with the hook ID.
        """

        # we will use the environment variables to get the command templates
        environment_variable = f"SBS_{hook_id.upper()}_COMMAND"
        try:
            command_templates = os.environ.get(environment_variable)
            if command_templates is None:
                return None
        except KeyError:
            return None

        return command_templates
