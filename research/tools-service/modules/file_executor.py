import ast
import logging
import tempfile
import datetime
from typing import Dict, List, Any, Tuple, AnyStr, Optional

import docker
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def arg_convert(arg_name, arg_type):
    arg_str = str(arg_name)  # Ensure the argument is treated as a string
    if arg_type is not None:
        if arg_type == "str":
            return f'"{arg_str}"'
        elif arg_type == "int":
            try:
                int_val = int(arg_str)
                # Check if the string representation matches to avoid float->int conversion
                if str(int_val) == arg_str:
                    return int_val
            except Exception as e:
                raise ValueError(f"Cannot convert '{arg_str}' to int {e}")

    try:
        int_val = int(arg_str)
        # Check if the string representation matches to avoid float->int conversion
        if str(int_val) == arg_str:
            return int_val
    except ValueError:
        pass

    # Try to convert to float
    try:
        float_val = float(arg_str)
        return float_val
    except ValueError:
        pass

    try:
        return float(arg_str)
    except ValueError:
        pass

    try:
        parts = arg_str.split(':')
        if len(parts) == 2:
            return datetime.datetime.strptime(arg_str, '%H:%M').time()
        elif len(parts) == 3:
            return datetime.datetime.strptime(arg_str, '%H:%M:%S').time()
    except ValueError:
        pass

    return f'"{arg_str}"'


def extract_function_and_imports(content: str) -> Tuple[Optional[str], List[Tuple[str, str, str]], List[Tuple[str, str]]]:
    """
    Extracts the first function's name, its parameters with type annotations and whether they are positional or optional,
    and imported modules from Python code.

    Returns:
    - Function name or None
    - List of (parameter name, parameter type, "positional" or "optional") tuples
    - List of (imported name, source module) tuples
    """
    try:
        tree = ast.parse(content)
        function_name: Optional[str] = None
        parameters: List[Tuple[str, str, str]] = []  # (param_name, param_type, "positional"/"optional")
        imports: List[Tuple[str, str]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and function_name is None:
                function_name = node.name
                defaults_count = len(node.args.defaults)
                positional_count = len(node.args.args) - defaults_count

                for i, arg in enumerate(node.args.args):
                    param_name = arg.arg
                    param_type = ast.unparse(arg.annotation) if arg.annotation else "None"
                    param_kind = "positional" if i < positional_count else "optional"
                    parameters.append((param_name, param_type, param_kind))

            elif isinstance(node, ast.Import):
                imports.extend((alias.name, "") for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.extend((alias.name, node.module or "") for alias in node.names)

        return function_name, parameters, imports

    except SyntaxError:
        return None, [], []
    except SyntaxError:
        return None, [], []


class FileExecutor:
    def __init__(self, filename: str, file_content: AnyStr, file_metadata: dict):
        """
        Initialize the PythonExecutor with the directory path.
        """
        self.filename = filename
        self.content = file_content

        try:
            self.metadata = file_metadata
        except Exception as e:
            logger.error(f"Error parsing metadata: {e}")
            raise HTTPException(
                status_code=400, detail=f"Error parsing metadata: {e}")

        self.client = docker.from_env()
        logger.info(
            f"Initialized file file executor for file: {self.filename}")

    def execute_file(self, parameters: Dict[str, Any]) -> dict:
        """
        Executes dynamically based on metadata and parameters.

        Args:
            parameters (Dict): Execution parameters

        Returns:
            dict: A message with the execution result or error message.
        """
        logger.info(
            f"Executing file: {self.filename} with parameters: {parameters}")

        try:
            return self.based_on_programming_language(parameters=parameters)
        except Exception as e:
            logger.error(f"Error executing file: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error executing file: {e}")

    def based_on_programming_language(self, parameters):
        """
        Switches based on the programming_language field in the metadata.
        """
        if self.metadata.get("programming_language") == "python":
            return self.execute_python_file(parameters=parameters)
        elif self.metadata.get("programming_language") == "bash":
            return self.execute_bash_file(parameters=parameters)
        else:
            raise HTTPException(
                status_code=400, detail="Unsupported programming language")

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
            raise HTTPException(
                status_code=400, detail="Unsupported packaging format")

        logger.info(f"Executing python code inside a Docker container")

        try:
            function_name, parameter_definitions, function_imports = extract_function_and_imports(self.content)
            # format docker command from function name and parameters
            if function_name is None:
                raise HTTPException(
                    status_code=400, detail="No function definition found in the file")

            logging.info(f"=== executing function with imports === \n"
                         f"function_name: {function_name}\n"
                         f"parameter_definitions:{parameter_definitions}\n"
                         f"function_imports:{function_imports}\n")
            with tempfile.NamedTemporaryFile(delete=False, mode='w') as temp_file:
                temp_file.write(self.content + f"""

import json
import argparse
import sys
import datetime
import inspect

def parse_arguments(func):
    # Get the signature of the function
    sig = inspect.signature(func)
    parser = argparse.ArgumentParser(description="Use the following parameters to work with {function_name}.")

    # Iterate over the parameters in the function signature
    for param in sig.parameters.values():
        if param.default == inspect.Parameter.empty:
            # Required parameter, add it to argparse
            parser.add_argument(param.name, type=str, help=f"Argument for {{param.name}}")
        else:
            # Optional parameter with default, add it to argparse with default value
            parser.add_argument(f"--{{param.name}}", type=str, default=str(param.default),
                                help=f"Argument for {{param.name}} (default: {{param.default}})")
    
    return parser


def main():
    parser = parse_arguments({function_name})
    args = parser.parse_args()

    # Convert string arguments to their appropriate types (int, float, etc.)
    func_params = inspect.signature({function_name}).parameters
    parsed_args = []
    for param, value in vars(args).items():
        # Convert the argument to the correct type if possible
        if func_params[param].annotation != inspect.Parameter.empty:
            try:
                parsed_args.append(func_params[param].annotation(value))
            except ValueError:
                parsed_args.append(value)
        else:
            parsed_args.append(value)
    
    # Call the function with the parsed arguments
    result = {function_name}(*parsed_args)
    print(json.dumps(result))
    
if __name__ == "__main__":
    main()
        
""")
                temp_file_path = temp_file.name
                logger.info(f"tmp container python file name {temp_file_path}")

            if function_imports:
                command = f"pip install -q --no-cache-dir {' '.join(function_imports)} > /dev/null 2>&1 ; "
            else:
                command = ""
            command += f"python /tmp/function.py "
            for parameter_definition in parameter_definitions:
                parameter_definition_name = parameter_definition[0]
                parameter_definition_type = parameter_definition[1]
                parameter_definition_kind = parameter_definition[2]
                if parameters.get(parameter_definition_name) is None:
                    raise HTTPException(
                        status_code=400, detail=f"Missing parameter: {parameter_definition}")
                converted_arg = arg_convert(parameters.get(parameter_definition_name),
                                            parameter_definition_type)
                if parameter_definition_kind == "positional":
                    command += f"{converted_arg} "
                else:
                    command += f"--{parameter_definition_name}={converted_arg} "

            # Create and run a container to execute the Python file
            container = self.client.containers.run(
                "python:3.10",  # Using the official Python 3.9 image
                command=f"/bin/bash -c '{command}'",
                volumes={temp_file_path: {
                    'bind': f'/tmp/function.py', 'mode': 'ro'}},
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
            logger.error(f"Error executing Python file: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error executing Python file: {e}")
