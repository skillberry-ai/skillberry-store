from agents.remote_tools_wrapper import define_tool_dynamically, generate_function_arguments_from_metadata
from agents.tools_service_api import execute_tool, get_tool_metadata
from config.config_ui import config


class TestExecuteToolsWithParameters:

    def test_define_tool_dynamically_with_tools_repo(self):
        """
        Test define_tool_dynamically with a tool against the tools_repo
        """

        scope = {}
        tool_name = "add_two_numbers.py"
        tools_repo_base_url = config.get("tools_repo_base_url")
        metadata = get_tool_metadata(tools_repo_base_url, tool_name)
        arguments_string = generate_function_arguments_from_metadata(metadata)
        tool = define_tool_dynamically(tool_name, arguments_string, scope, tools_repo_base_url)
        assert tool.__name__ == "add_two_numbers_py"
        parameters = {"a": 1, "b": 2}
        _sum = tool(**parameters)
        assert _sum == "3"
