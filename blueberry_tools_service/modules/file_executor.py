import ast
import textwrap
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
) -> Tuple[Optional[str], List[Tuple[str, str, str]], List[Tuple[str, str]]]:
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
    def __init__(
        self,
        name: str,
        file_content: AnyStr,
        file_manifest: dict,
        dependent_file_contents: List[str] = None,
        dependent_manifests_as_dict: List[Dict] = None,
        execute_python_locally: bool = None,
    ):
        """
        Initialize the PythonExecutor with the directory path.

        The executor runtime is determined by the environment variable CODE_EXEC_RUNTIME.
        If the variable is set to "podman", the executor will use Podman.
        If the variable is set to "docker", the executor will use Docker.
        If the variable is not set or has an invalid value, an HTTPException will be raised.

        Args:
            name (str): the name of the execution
            file_content (str): the code of the tool
            file_manifest (str): the manifest of the tool
            dependent_file_contents (list): list of dependant (if any) tools code
            dependent_manifests_as_dict (list): list of dependant (if any) tools manifests
            execute_python_locally (bool): Should execute using local mode

        """
        self.name = name
        self.content = file_content
        self.dependent_file_contents = dependent_file_contents or []
        self.dependent_manifests_as_dict = dependent_manifests_as_dict or []
        self.execute_python_locally = (
            execute_python_locally
            if execute_python_locally is not None
            else bool(os.getenv("EXECUTE_PYTHON_LOCALLY"))
        )

        try:
            self.manifest = file_manifest
        except Exception as e:
            logger.error(f"Error parsing manifest: {e}")
            raise HTTPException(status_code=400, detail=f"Error parsing manifest: {e}")

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
            # Check environment variable dynamically
            if self.execute_python_locally:
                return_value = self.execute_python_file_locally(parameters)
            else:
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

    def _prepare_python_execution(self, parameters):
        """
        Common preparation for Python execution (both local and Docker)
        """
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

        # Handle dependent manifests
        for i, _ in enumerate(self.dependent_manifests_as_dict):
            dm_name = self.dependent_manifests_as_dict[i]["name"]
            (df_name, _, df_imports,) = extract_function_and_imports(
                content=self.dependent_file_contents[i],
                function_name=dm_name,
            )
            if df_name is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"No function definition {dm_name} found in the file",
                )
            function_imports.extend(df_imports)

        # Generate wrapper code
        wrapper_code = generate_wrapper_any_types(
            str(self.content),
            str(function_name),
            dict(parameters),
            dependent_codes_str=self.dependent_file_contents,
        )

        return function_name, function_imports, wrapper_code

    def execute_python_file_using_docker(self, parameters):
        """
        Executes a Python file using docker
        """
        logger.info(f"Executing python code using a Docker container")

        try:
            (
                function_name,
                function_imports,
                wrapper_code,
            ) = self._prepare_python_execution(parameters)

            # Log the wrapper code for debugging
            logger.info(f"Generated wrapper code for Docker:\n{wrapper_code}")

            with tempfile.NamedTemporaryFile(delete=False, mode="w") as temp_file:
                temp_file.write(wrapper_code)
                temp_file_path = temp_file.name
                logger.info(f"tmp container python file name {temp_file_path}")
                logger.info(f"Wrapper code length: {len(wrapper_code)}")

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

            # Create and run a container to execute the Python file
            container = self.client.containers.run(
                "public.ecr.aws/docker/library/python:3.11",  # Python 3.11 image from AWS (no rate limits)
                command=f"/bin/bash -c '{command}'",
                volumes={temp_file_path: {"bind": f"/tmp/function.py", "mode": "ro"}},
                remove=True,
                detach=False,
                stderr=True,
                stdout=True,
                environment={"PYTHONUNBUFFERED": "1"},
            )

            return_value = container.decode().replace("\n", "")
            logger.info(
                f"Function '{function_name}' executed using docker successfully: {return_value}"
            )
            return {"return value": f"{return_value}"}
        except Exception as e:
            logger.error(f"Error executing Python file: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error executing Python file: {e}"
            )

    def execute_python_file_locally(self, parameters):
        """
        Executes a Python file using exec() in the same process
        """
        import io
        import sys
        import subprocess
        from contextlib import redirect_stdout, redirect_stderr

        logger.info(f"Executing python code using exec() in current process")

        try:
            (
                function_name,
                function_imports,
                wrapper_code,
            ) = self._prepare_python_execution(parameters)

            # Try to install missing packages
            if function_imports:
                self._ensure_packages_installed(function_imports)

            # Log the wrapper code for debugging
            logger.info(f"Generated wrapper code:\n{wrapper_code}")
            logger.info(f"Parameters passed: {parameters}")

            # Capture stdout and stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            execution_success = False
            exec_result = None

            try:
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    exec_globals = {}
                    try:
                        exec(wrapper_code, exec_globals)
                        execution_success = True
                    except Exception as exec_inner_error:
                        logger.error(f"Inner exec error: {exec_inner_error}")
                        raise exec_inner_error

                return_value = stdout_capture.getvalue().strip()
                error_output = stderr_capture.getvalue().strip()

                logger.info(f"Execution success: {execution_success}")
                logger.info(f"Return value: '{return_value}'")
                logger.info(f"Error output: '{error_output}'")

                if error_output:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Python execution failed: {error_output}",
                    )

                # If no output but execution succeeded, this might indicate a silent failure
                if not return_value and execution_success:
                    logger.warning(
                        "Function executed but produced no output - this might indicate a silent error"
                    )
                    return_value = "Function executed successfully (no output)"

                logger.info(
                    f"Function '{function_name}' executed locally successfully: {return_value}"
                )
                return {"return value": return_value}

            except Exception as exec_error:
                error_output = stderr_capture.getvalue().strip()
                logger.error(f"Execution failed: {str(exec_error)}")
                logger.error(f"Error output: '{error_output}'")
                raise HTTPException(
                    status_code=500,
                    detail=f"Python execution failed: {str(exec_error)} | stderr: {error_output}",
                )

        except Exception as e:
            logger.error(f"Error executing Python file locally: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error executing Python file locally: {e}"
            )

    def _ensure_packages_installed(self, function_imports):
        """
        Try to ensure required packages are installed
        """
        import subprocess
        import sys

        function_imports = [fi.split(".")[0] for fi in function_imports if fi]

        for module_name in function_imports:
            try:
                __import__(module_name)
            except ImportError:
                logger.info(f"Attempting to install missing package: {module_name}")
                package_name = get_distribution(module_name) or module_name
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", package_name],
                        check=True,
                        capture_output=True,
                        timeout=30,
                    )
                    logger.info(f"Successfully installed: {package_name}")
                except Exception as e:
                    logger.warning(f"Failed to install {package_name}: {e}")


def generate_wrapper_any_types(
    code_str: str, func_name: str, parameters: dict, dependent_codes_str: list[str]
) -> str:
    # Parse the main code to find the function definition
    tree = ast.parse(code_str)

    func_def = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            func_def = node
            break

    if func_def is None:
        raise ValueError("No function definition found in the code.")

    # Prepare the function call string
    arg_str = ", ".join(f"{key}={repr(value)}" for key, value in parameters.items())
    func_name_call_code = f"{func_name}({arg_str})"

    # Main wrapper code
    main_code = f"""
import json

def main():
    try:
        result = {func_name_call_code}
        if isinstance(result, str):
            print(result)
        else:
            print(json.dumps(result))
    except Exception as e:
        print(f"EXCEPTION: {{e}}")
        raise e

if __name__ == "__main__":
    main()
    exit(0)
    
main()
"""

    # Combine all dependency code strings
    dependent_code_combined = "\n\n".join(
        textwrap.dedent(dep.strip()) for dep in dependent_codes_str
    )

    # Final full code
    full_code = (
        "\n"
        + dependent_code_combined
        + "\n\n"
        + code_str.strip()
        + "\n\n"
        + textwrap.dedent(main_code)
    )
    return full_code
