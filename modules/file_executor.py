import ast
from importlib.metadata import packages_distributions
import logging
import os
import tempfile
import datetime
from typing import Dict, List, Any, Tuple, AnyStr, Optional

import docker


from fastapi import HTTPException

from mcp import ClientSession
from mcp.client.sse import sse_client

default_mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8080/sse")

logger = logging.getLogger(__name__)


def get_distribution(module_name: str) -> str:
    """
    Return the package that provides the given module.

    Parameters:
        module_name: python module name (e.g. dateutil, yaml, ...)

    Returns:
        str: package name or None if not found

    """
    distributions = packages_distributions()
    package_distribution = distributions.get(module_name)
    # return the first found distro for this package
    return (
        package_distribution[0]
        if (package_distribution and len(package_distribution) > 0)
        else None
    )


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
        parts = arg_str.split(":")
        if len(parts) == 2:
            return datetime.datetime.strptime(arg_str, "%H:%M").time()
        elif len(parts) == 3:
            return datetime.datetime.strptime(arg_str, "%H:%M:%S").time()
    except ValueError:
        pass

    return f'"{arg_str}"'


def extract_function_and_imports(
    content: str, function_name: str
) -> (Tuple)[Optional[str], List[Tuple[str, str, str]], List[Tuple[str, str]]]:
    """
    Extracts the function's name, its parameters with type annotations and whether they are positional or optional,
    and imported modules from Python code.

    Returns:
    - Function name or None
    - List of (parameter name, parameter type, "positional" or "optional") tuples
    - List of (imported name, source module) tuples
    """
    try:
        tree = ast.parse(content)
        first_found_function_name: Optional[str] = None
        parameters: List[
            Tuple[str, str, str]
        ] = []  # (param_name, param_type, "positional"/"optional")
        imports: List[Tuple[str, str]] = []

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and first_found_function_name is None
                and node.name == function_name
            ):
                first_found_function_name = node.name
                defaults_count = len(node.args.defaults)
                positional_count = len(node.args.args) - defaults_count

                for i, arg in enumerate(node.args.args):
                    param_name = arg.arg
                    param_type = (
                        ast.unparse(arg.annotation) if arg.annotation else "None"
                    )
                    param_kind = "positional" if i < positional_count else "optional"
                    parameters.append((param_name, param_type, param_kind))

            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                # imports.extend(alias.name for alias in node.names)
                imports.extend([node.module])

        return function_name, parameters, imports

    except SyntaxError:
        return None, [], []
    except SyntaxError:
        return None, [], []


class FileExecutor:
    def __init__(self, name: str, file_content: AnyStr, file_manifest: dict):
        """
        Initialize the PythonExecutor with the directory path.
        The executor runtime is determined by the environment variable CODE_EXEC_RUNTIME.
        If the variable is set to "podman", the executor will use Podman.
        If the variable is set to "docker", the executor will use Docker.
        If the variable is not set or has an invalid value, an HTTPException will be raised.
        """
        self.name = name
        self.content = file_content

        try:
            self.manifest = file_manifest
        except Exception as e:
            logger.error(f"Error parsing manifest: {e}")
            raise HTTPException(status_code=400, detail=f"Error parsing manifest: {e}")

        self.client = docker.from_env() 
        
        try:
            self.client = docker.from_env()    
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail=f"Docker SDK for Python not found. Please install the Docker SDK for Python.",
            )

    async def execute_file(self, parameters: Dict[str, Any]) -> dict:
        """
        Executes dynamically based on manifest and parameters.

        Args:
            parameters (Dict): Execution parameters

        Returns:
            dict: A message with the execution result or error message.
        """
        logger.info(f"Executing: {self.name} with parameters: {parameters}")

        try:
            return await self.based_on_programming_language(parameters=parameters)
        except Exception as e:
            logger.error(f"Error executing file: {e}")
            raise HTTPException(status_code=500, detail=f"Error executing file: {e}")

    def based_on_programming_language(self, parameters):
        """
        Switches based on the programming_language field in the manifest.
        """
        if self.manifest.get("programming_language") == "python":
            return self.execute_python_file(parameters=parameters)
        elif self.manifest.get("programming_language") == "bash":
            return self.execute_bash_file(parameters=parameters)
        else:
            raise HTTPException(
                status_code=400, detail="Unsupported programming language"
            )

    def execute_bash_file(self, parameters):
        """
        Executes a Bash file.
        """
        raise HTTPException(status_code=400, detail="Not implemented")

    async def execute_python_file(self, parameters):

        if self.manifest.get("packaging_format") == "code":
            return_value = self.execute_python_file_using_docker(parameters)
        elif self.manifest.get("packaging_format") == "mcp":
            return_value = await self.execute_python_file_in_mcp_server(parameters)
        else:
            raise HTTPException(status_code=400, detail="Unsupported packaging format")

        return return_value

    async def execute_python_file_in_mcp_server(self, parameters):
        """
        Executes a Python file using MCP server
        """

        # To experiment with the MCP server, see the instructions in the `contrib/mcp/README.md` file.

        async def execute_mcp_tool(
            _url: str, _function_name: str, _mcp_args_dict: dict
        ):
            async with sse_client(_url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    tools = await session.list_tools()

                    for tool in tools.tools:
                        logging.info(f"tool: {tool.name}")
                        if _function_name == tool.name:
                            logging.info(f"tool found: {tool.name}")
                            _return_value = await session.call_tool(
                                tool.name, arguments=_mcp_args_dict
                            )
                            return _return_value.content[0].text

                    return None

        logger.info(f"Executing python code using a MCP server")

        try:
            (
                function_name,
                parameter_definitions,
                function_imports,
            ) = extract_function_and_imports(
                content=self.content, function_name=self.manifest["name"]
            )
            if function_name is None:
                raise HTTPException(
                    status_code=400, detail="No function definition found in the file"
                )

            logging.info(
                f"=== executing function with imports === \n"
                f"function_name: {function_name}\n"
                f"parameter_definitions:{parameter_definitions}\n"
                f"function_imports:{function_imports}\n"
            )

            mcp_args_dict = {}
            for parameter_definition in parameter_definitions:
                parameter_definition_name = parameter_definition[0]
                parameter_definition_type = parameter_definition[1]
                parameter_definition_kind = parameter_definition[2]
                if parameters.get(parameter_definition_name) is None:
                    if parameter_definition_kind == "positional":
                        raise HTTPException(
                            status_code=400,
                            detail=f"Missing parameter: "
                            f"name:{parameter_definition_name}, "
                            f"type:{parameter_definition_type}",
                        )
                    else:
                        continue

                converted_arg = arg_convert(
                    parameters.get(parameter_definition_name), parameter_definition_type
                )
                if parameter_definition_kind == "positional":
                    mcp_args_dict[parameter_definition_name] = converted_arg
                else:
                    mcp_args_dict[parameter_definition_name] = converted_arg
            mcp_server_url = self.manifest.get("mcp_url") or default_mcp_server_url
            return_value = await execute_mcp_tool(
                mcp_server_url, function_name, mcp_args_dict
            )

            if return_value is None:
                raise HTTPException(
                    status_code=400, detail="No return value from the function"
                )

            logger.info(f"Python code executed successfully: {return_value}")
            return {"return value": f"{return_value}"}
        except Exception as e:
            logger.error(f"Error executing Python file: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error executing Python file: {e}"
            )

    def execute_python_file_using_docker(self, parameters):
        """
        Executes a Python file using docker
        """

        logger.info(f"Executing python code using a Docker container")

        try:
            (
                function_name,
                parameter_definitions,
                function_imports,
            ) = extract_function_and_imports(
                content=self.content, function_name=self.manifest["name"]
            )
            # format docker command from function name and parameters
            if function_name is None:
                raise HTTPException(
                    status_code=400, detail="No function definition found in the file"
                )

            logging.info(
                f"=== executing function with imports === \n"
                f"function_name: {function_name}\n"
                f"parameter_definitions:{parameter_definitions}\n"
                f"function_imports:{function_imports}\n"
            )
            with tempfile.NamedTemporaryFile(delete=False, mode="w") as temp_file:
                temp_file.write(
                    self.content
                    + f"""

from typing import get_origin, get_args
import json
import argparse
import sys
import datetime
import inspect

def convert_value(value: str, annotation):
    origin = get_origin(annotation) or annotation
    args   = get_args(annotation)

    if origin in (list, tuple):
        subtype = args[0] if args else str
        items = [item.strip().strip('[]()') for item in value.split(',')]
        parsed = [subtype(item) for item in items]
        return parsed if origin is list else tuple(parsed)

    if origin is dict:
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for dict: {{e}}")

    if annotation is datetime.date:
        try:
            return datetime.date.fromisoformat(value)
        except Exception as e:
            raise ValueError(f"Invalid date (YYYY-MM-DD): {{e}}")
    if annotation is datetime.datetime:
        try:
            return datetime.datetime.fromisoformat(value)
        except Exception as e:
            raise ValueError(f"Invalid datetime (ISO 8601): {{e}}")

    if annotation is int:
        return int(value)
    if annotation is float:
        return float(value)
    if annotation is bool:
        return value.lower() in ("true", "1", "yes")
    if annotation is str:
        return value

    return value

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
            parser.add_argument(f"--{{param.name}}", type=str, default=param.default,
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
        if func_params[param].annotation != inspect.Parameter.empty and value is not None:
            try:
                parsed_args.append(convert_value(value,func_params[param].annotation))
            except ValueError:
                parsed_args.append(value)
        else:
            parsed_args.append(value)

    # Call the function with the parsed arguments
    result = {function_name}(*parsed_args)
    if isinstance(result, str):
        print(result)
    else:
        print(json.dumps(result))

if __name__ == "__main__":
    main()

"""
                )
                temp_file_path = temp_file.name
                logger.info(f"tmp container python file name {temp_file_path}")

            if function_imports:
                packages_to_install = []
                # (1) transform to a list of main module names (e.g. in case
                #     of nested - the first element prior to '.')
                function_imports = [fi.split(".")[0] for fi in function_imports]
                for fi in function_imports:
                    # (2) attempt to resolve package name via packages_distributions
                    package_name = get_distribution(fi)
                    if package_name:
                        # (3a) succeed: append to list of packages to be installed
                        packages_to_install.append(package_name)
                    else:
                        # (3b) not found: append module name as is plus same one
                        #      prefixed with "python".
                        #      Note: pip install error is silently ignored (e.g. in case
                        #      of a none-existing/illegal package names (see below)
                        packages_to_install.append(fi)
                        packages_to_install.append(f"python-{fi}")

                command = ""
                for p in packages_to_install:
                    # (4) individual pip install commands so that a failure does not
                    #     affect the rest
                    command += f"pip install -q --no-cache-dir {p} > /dev/null 2>&1 ; "
            else:
                command = ""
            command += f"python /tmp/function.py "
            for parameter_definition in parameter_definitions:
                parameter_definition_name = parameter_definition[0]
                parameter_definition_type = parameter_definition[1]
                parameter_definition_kind = parameter_definition[2]
                if parameters.get(parameter_definition_name) is None:
                    if parameter_definition_kind == "positional":
                        raise HTTPException(
                            status_code=400,
                            detail=f"Missing parameter: "
                            f"name:{parameter_definition_name}, "
                            f"type:{parameter_definition_type}",
                        )
                    else:
                        continue

                converted_arg = arg_convert(
                    parameters.get(parameter_definition_name), parameter_definition_type
                )
                # attempt to escape $ signs with `\` so that bash does
                # not treat it as a variable
                try:
                    converted_arg = converted_arg.replace("$", "\\$")
                except:
                    # ignore none string, any error
                    pass
                if parameter_definition_kind == "positional":
                    command += f"{converted_arg} "
                else:
                    command += f"--{parameter_definition_name}={converted_arg} "

            # Create and run a container to execute the Python file
            
            container = self.client.containers.run(
                    "python:3.11",  # Using the official Python 3.11 image
                    command=f"/bin/bash -c '{command}'",
                    volumes={temp_file_path: {"bind": f"/tmp/function.py", "mode": "ro"}},
                    remove=True,
                    detach=False,
                    stderr=True,
                    stdout=True,
                    environment={"PYTHONUNBUFFERED": "1"},
            )
            
            return_value = container.decode().replace("\n", "")
            logger.info(f"Python code executed successfully: {return_value}")
            return {"return value": f"{return_value}"}
        except Exception as e:
            logger.error(f"Error executing Python file: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error executing Python file: {e}"
            )
