import logging
import os

import docker
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class PythonExecutor:
    def __init__(self, directory_path: str):
        """
        Initialize the PythonExecutor with the directory path.
        """
        self.directory_path = directory_path
        self.client = docker.from_env()
        logger.info("Initialized PythonExecutor with Docker client")

    def execute_python_file(self, filename: str) -> dict:
        """
        Executes a Python file inside a dynamically created Docker container.

        Args:
            filename (str): The Python file to execute.

        Returns:
            dict: A message with the execution result or error message.
        """
        file_path = os.path.join(self.directory_path, filename)
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            raise HTTPException(status_code=404, detail="File not found")

        logger.info(f"Executing file inside Docker container: {file_path}")

        try:
            # Create and run a container to execute the Python file
            container = self.client.containers.run(
                "python:3.9",  # Using the official Python 3.9 image
                f"python /mnt/{filename}",
                volumes={self.directory_path: {'bind': '/mnt', 'mode': 'ro'}},
                remove=True,  # Automatically remove the container after execution
                detach=False,  # Run synchronously to get the result
                stderr=True,  # Capture error output
                stdout=True  # Capture standard output
            )
            logger.info(f"Python code executed successfully: {container.decode()}")
            return {"message": f"Execution result: {container.decode()}"}
        except Exception as e:
            logger.error(f"Error executing Python file: {e}")
            raise HTTPException(status_code=500, detail=f"Error executing file: {str(e)}")
