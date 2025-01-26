import json
import logging
import re
import tempfile
from typing import Dict, Any, AnyStr

import docker
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def extract_python_function_name_and_parameters(content: str) -> (str, str):
    """
    Extracts the function name and parameters from python code content
    """
    match = re.match(r"def\s+([a-zA-Z_][a-zA-Z_0-9]*)\s*\((.*?)\)", content)
    if match:
        _name = match.group(1) if match else None
        param_string = match.group(2).strip()
        _parameters = [param.split(":")[0].strip() for param in param_string.split(",") if param.strip()]

    return _name, _parameters

class FileExecutor:
    def __init__(self, filename: str, file_content: AnyStr, file_metadata: str):
        """
        Initialize the PythonExecutor with the directory path.
        """
        self.filename = filename
        self.content = file_content

        try:
            self.metadata = json.loads(file_metadata)
        except Exception as e:
            logger.error(f"Error parsing metadata: {e}")
            raise HTTPException(status_code=400, detail=f"Error parsing metadata: {e}")

        self.client = docker.from_env()
        logger.info(f"Initialized file file executor for file: {self.filename}")

    def execute_file(self, parameters: Dict[str, Any]) -> dict:
        """
        Executes dynamically based on metadata and parameters.

        Args:
            parameters (Dict): Execution parameters

        Returns:
            dict: A message with the execution result or error message.
        """
        logger.info(f"Executing file: {self.filename} with parameters: {parameters}")

        try:
            return self.based_on_programming_language(parameters=parameters)
        except Exception as e:
            logger.error(f"Error executing file: {e.detail}")
            raise HTTPException(status_code=500, detail=f"Error executing file: {e.detail}")

    def based_on_programming_language(self, parameters):
        """
        Switches based on the programming_language field in the metadata.
        """
        if self.metadata.get("programming_language") == "python":
            return self.execute_python_file(parameters=parameters)
        elif self.metadata.get("programming_language") == "bash":
            return self.execute_bash_file(parameters=parameters)
        else:
            raise HTTPException(status_code=400, detail="Unsupported programming language")

    def execute_bash_file(self, parameters):
        """
        Executes a Bash file.
        """
        raise HTTPException(status_code=400, detail="Not implemented")

    def execute_python_file(self, parameters):
        """
        Executes a Python file
        """

        if self.metadata.get("packaging_format") != "code":
            raise HTTPException(status_code=400, detail="Unsupported packaging format")

        logger.info(f"Executing python code inside a Docker container")

        try:
            function_name, parameter_definitions = extract_python_function_name_and_parameters(self.content)
            # format docker command from function name and parameters
            if function_name is None:
                raise HTTPException(status_code=400, detail="No function definition found in the file")

            with tempfile.NamedTemporaryFile(delete=False, mode='w') as temp_file:
                temp_file.write(self.content + f"""

import json
import argparse
import sys

parser = argparse.ArgumentParser(description="Run a function with arguments")
parser.add_argument('args', nargs=argparse.REMAINDER, help="Arguments to pass to the function")
args = parser.parse_args()
def try_convert(arg):
    return (int(arg) if arg.isdigit() else (float(arg) if arg.replace('.', '', 1).isdigit() else (datetime.datetime.strptime(arg, '%H:%M').time() if len(arg.split(':')) == 2 else (datetime.datetime.strptime(arg, '%H:%M:%S').time() if len(arg.split(':')) == 3 else arg))))
converted_args = [try_convert(arg) for arg in args.args]
result = {function_name}(*converted_args)
print(json.dumps(result))
""")
                temp_file_path = temp_file.name
                logger.info(f"tmp container file name {temp_file_path}")

            command = f"python /tmp/function.py "
            for parameter_definition in parameter_definitions:
                if parameters.get(parameter_definition) is None:
                    raise HTTPException(status_code=400, detail=f"Missing parameter: {parameter_definition}")
                command += f" {parameters[parameter_definition]}"

            # Create and run a container to execute the Python file
            container = self.client.containers.run(
                "python:3.9",  # Using the official Python 3.9 image
                command=command,
                volumes={temp_file_path: {'bind': f'/tmp/function.py', 'mode': 'ro'}},
                remove=True,
                detach=False,
                stderr=True,
                stdout=True,
                environment={"PYTHONUNBUFFERED": "1"},
            )

            return_value = container.decode().replace('\n', '')
            logger.info(f"Python code executed successfully: {return_value}")
            return {"return value": f"{return_value}"}
        except Exception as e:
            logger.error(f"Error executing Python file: {e.detail}")
            raise HTTPException(status_code=500, detail=f"Error executing Python file: {e.detail}")
