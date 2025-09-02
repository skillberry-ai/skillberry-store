import asyncio
import os
from importlib import resources as impresources
import json
import pytest
import pytest_asyncio

from blueberry_tools_service.client.utils import base_client_utils, json_client_utils
from blueberry_tools_service.modules.manifest import python_manifest_from_json_description
from blueberry_tools_service.tests import resources as resources_package
from blueberry_tools_service.tests.utils import clean_test_tmp_dir, wait_until_server_ready

import blueberry_tools_service_sdk
from blueberry_tools_service_sdk.exceptions import NotFoundException, ServiceException


@pytest_asyncio.fixture(scope="module")
async def run_bts(request):
    """
    This method is responsible for setup and teardown.

    Setup - runs the tools service.
    Teardown - terminates the service and remove its resources.

    """
    print("setup called")
    clean_test_tmp_dir()
    main_proc = await asyncio.create_subprocess_exec(
        "python", "-m", "blueberry_tools_service.main",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=os.path.dirname(
            os.path.abspath(__file__).rstrip("/tests/e2e/test_tools_service_apis.py")),
    )
    await wait_until_server_ready(timeout=60)

    yield

    print("teardown called")
    # Cleanup: kill server process
    main_proc.kill()

    # Read to avoid transport issues
    if main_proc.stdout:
        await main_proc.stdout.read()
    if main_proc.stderr:
        await main_proc.stderr.read()

    clean_test_tmp_dir()


def load_json_resource(resource_name: str) -> dict:
    """
    Load and return a JSON resource from the tests resources package.
    Parameters:
        resource_name (str): The filename of the JSON resource.

    Returns:
        The parsed JSON as a dictionary.
    """
    resource_path = impresources.files(resources_package) / "e2e" / resource_name
    with open(resource_path, "rt") as f:
        return json.load(f)


@pytest.mark.parametrize("func_name", ["GetCurrency", "GetYear", "GetQuarter", "identity"])
@pytest.mark.asyncio
async def test_add_manifest(run_bts, func_name):
    """
    Add manifest from the proper json file and module.

    This function is being called at the beginning of the test. It asserts the tools successfully added.

    """
    json_descriptions = load_json_resource("client-win-functions.json")
    module_path = impresources.files(resources_package) / "e2e" / "transformations.py"
    file_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ManifestApi(api_client)

        manifest = json_client_utils.python_manifest_from_json_base(
            [json_descriptions], module_path, func_name
        )
        assert manifest is not None, f"Manifest could not get created for {func_name}"

        manifest_str = json.dumps(manifest)
        api_response = api_instance.add_manifest_manifests_add_post(
            manifest_str, file=file_blob
        )
        assert api_response.get("uid", None), "Should receive 'uid' key"
        assert api_response["uid"] == func_name, f"Should receive uid: {func_name}"


@pytest.mark.parametrize("func_name", ["GetYear", "GetQuarter"])
@pytest.mark.asyncio
async def test_tools_add(run_bts, func_name):
    """
    Add tools from the proper module.

    This function is being called at the beginning of the test. It asserts the tools successfully added.

    """
    module_path = impresources.files(resources_package) / "e2e" / "client-win-functions.py"
    tool_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ToolsApi(api_client)

        api_response = api_instance.tools_add_tools_add_post(
            "code/python", tool_blob, tool_name=func_name
        )
        assert api_response.get("uid", None), "Should receive 'uid' key"
        assert api_response["uid"] == func_name, f"Should receive uid: {func_name}"


@pytest.mark.asyncio
async def test_tools_add_no_tool_name(run_bts):
    """
    Add tools from the proper module.

    This function is being called at the beginning of the test. It asserts the tools successfully added.

    """
    module_path = impresources.files(resources_package) / "e2e" / "client-win-functions.py"
    tool_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ToolsApi(api_client)

        # tool_name not supplied - first function is added
        api_response = api_instance.tools_add_tools_add_post(
            "code/python", tool_blob
        )
        assert api_response.get("uid", None), "Should receive 'uid' key"
        assert api_response["uid"] == "GetQuarter", "Should receive uid: GetQuarter"


@pytest.mark.parametrize("func_name", ["GetCurrency", "GetYear", "GetQuarter", "identity"])
@pytest.mark.asyncio
async def test_tools_add_genai(run_bts, func_name):
    """
    Add tools from the proper json file and module.

    This function is being called at the beginning of the test. It asserts the tools successfully added.

    """
    json_descriptions = load_json_resource("client-win-functions.json")
    json_description = list(filter(lambda d: d["name"] == func_name, json_descriptions))[0]
    module_path = impresources.files(resources_package) / "e2e" / "transformations.py"
    tool_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ToolsApi(api_client)

        json_description_str = json.dumps(json_description)
        api_response = api_instance.tools_add_tools_add_post(
            "json/genai-lh", tool_blob, kwargs=json_description_str
        )
        assert api_response.get("uid", None), "Should receive 'uid' key"
        assert api_response["uid"] == func_name, f"Should receive uid: {func_name}"


@pytest.mark.asyncio
async def test_tools_add(run_bts):
    """
    Add tools from the proper module. Negative test.

    """
    module_path = impresources.files(resources_package) / "e2e" / "client-win-functions.py"
    tool_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ToolsApi(api_client)
        with pytest.raises(ServiceException, match="Missing docstring description"):
            api_instance.tools_add_tools_add_post(
                "code/python", tool_blob, tool_name="DocstringNoDescription"
            )


@pytest.mark.asyncio
async def test_tools_add(run_bts):
    """
    Add tools from the proper module. Negative test.

    """
    module_path = impresources.files(resources_package) / "e2e" / "client-win-functions.py"
    tool_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ToolsApi(api_client)
        with pytest.raises(ServiceException, match="Missing docstring parameters"):
            api_instance.tools_add_tools_add_post(
                "code/python", tool_blob, tool_name="DocstringParameterIndentationError"
            )


def test_search_manifests(run_bts):
    """
    Search manifests.

    """
    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ManifestApi(api_client)

        api_response = api_instance.search_manifest_search_manifests_get(
            "A tool that returns the quarter of the year."
        )

        assert (
                len(api_response) > 0
        ), "Should return at least one manifest for search operation"
        # TODO: asset GetQuarter present and has the smallest score


@pytest.mark.parametrize("uid", ["GetCurrency", "GetYear", "GetQuarter", "identity"])
def test_get_manifest(run_bts, uid: str):
    """
    Retrieve single manifest.

    """
    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ManifestApi(api_client)

        api_response = api_instance.get_manifest_manifests_uid_get(uid)
        assert api_response.get("uid", None), "Should receive 'uid' key"
        assert api_response["uid"] == uid, f"Should receive uid: {uid}"


def test_list_manifests(run_bts, expected: int = 4):
    """
    List manifests.

    Parameters:
        expected (int): the number of expected manifests to assert

    """
    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ManifestApi(api_client)

        api_response = api_instance.get_manifests_manifests_get()
        assert (
                len(api_response) == expected
        ), f"Execution failed: received none empty response"


@pytest.mark.parametrize("uid", ["GetQuarter"])
def test_delete_manifest(run_bts, uid):
    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ManifestApi(api_client)

        api_response = api_instance.delete_manifest_manifests_uid_delete(uid)

        assert api_response.get("message", None), "Should receive 'message' key"
        assert (
                api_response["message"] == f"Manifest '{uid}' deleted."
        ), f"Should receive deletion message for {uid}"


@pytest.mark.parametrize("uid", ["GetQuarter"])
def test_get_manifest2(run_bts, uid: str):
    """
    Retrieve single manifest.

    """
    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        try:
            api_instance = blueberry_tools_service_sdk.ManifestApi(api_client)
            api_instance.get_manifest_manifests_uid_get(uid)
            assert False, f"Should not find uid: {uid}"

        except NotFoundException:
            pass


def test_delete_manifests_wildcard(run_bts):
    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ManifestApi(api_client)

        api_response = api_instance.delete_manifests_manifests_delete(manifest_filter="name:Get*")

        assert api_response.get("message", None), "Should receive 'message' key"
        actual = api_response["message"]
        expected1 = f"Manifests ['GetCurrency', 'GetYear'] deleted."
        expected2 = f"Manifests ['GetYear', 'GetCurrency'] deleted."
        assert actual in (expected1, expected2), f"Should receive deletion message for GetCurrency and GetYear"


def test_get_manifests(run_bts):
    """
    Retrieve single manifest.

    """
    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ManifestApi(api_client)

        api_response = api_instance.get_manifests_manifests_get()
        assert len(api_response) == 1, "Should receive exactly one manifest"
        assert api_response[0]["uid"] == "identity", "Manifest 'identity' does not exist"


###################### Composite tests #############################################


@pytest.mark.parametrize(
    "func_name, file_name",
        [
            ("add", "add.py"),
            ("subtract", "subtract.py")
        ]
)
@pytest.mark.asyncio
async def test_tools_add_and_subtract(run_bts, func_name, file_name):
    """
    Add tools 'add' and 'subtract'.

    """
    module_path = impresources.files(resources_package) / "e2e" / "example_functions" / file_name
    tool_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ToolsApi(api_client)

        api_response = api_instance.tools_add_tools_add_post(
            "code/python", tool_blob, tool_name=func_name
        )
        assert api_response.get("uid", None), "Should receive 'uid' key"
        assert api_response["uid"] == func_name, f"Should receive uid: {func_name}"


@pytest.mark.parametrize(
        "func_name, file_name, dependent_manifest_uids", 
        [
            ("calc", "calc.py", ["add", "subtract"])
        ]
)
@pytest.mark.asyncio
async def test_tools_add_calc(run_bts, func_name, file_name, dependent_manifest_uids):
    """
    Add manifest from the proper module.

    """
    module_path = impresources.files(resources_package) / "e2e" / "example_functions" / file_name
    file_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ManifestApi(api_client)

        docstring = base_client_utils.extract_docstring(module_path, func_name)
        manifest = base_client_utils.python_manifest_from_function_docstring(
            module_path, func_name, docstring
        )
        assert manifest is not None, f"Manifest could not get created for {func_name}"

        manifest["dependent_manifest_uids"] = dependent_manifest_uids

        manifest_str = json.dumps(manifest)
        api_response = api_instance.add_manifest_manifests_add_post(
            manifest_str, file=file_blob
        )
        assert api_response.get("uid", None), "Should receive 'uid' key"
        assert api_response["uid"] == func_name, f"Should receive uid: {func_name}"


@pytest.mark.asyncio
async def test_execute_calc(run_bts):
    """
    Execute a manifest that is dependant on others.

    """
    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ManifestApi(api_client)
        arguments = {"operation": "+", "num1": 5, "num2": 8}
        api_response = api_instance.execute_manifest_manifests_execute_uid_post(
            "calc", arguments
        )
        assert api_response.get("return value", None) == '13', "Should get 13"


@pytest.mark.parametrize("uid", ["subtract"])
def test_delete_subtract(run_bts, uid):
    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ManifestApi(api_client)

        api_response = api_instance.delete_manifest_manifests_uid_delete(uid)

        assert api_response.get("message", None), "Should receive 'message' key"
        assert (
                api_response["message"] == f"Manifest '{uid}' deleted."
        ), f"Should receive deletion message for {uid}"


@pytest.mark.asyncio
async def test_execute_calc_negative(run_bts):
    """
    Execute a manifest that is dependant on others. Negative test.

    """
    configuration = blueberry_tools_service_sdk.Configuration(
        host="http://localhost:8000"
    )
    with blueberry_tools_service_sdk.ApiClient(configuration) as api_client:
        api_instance = blueberry_tools_service_sdk.ManifestApi(api_client)
        arguments = {"operation": "+", "num1": 5, "num2": 8}
        with pytest.raises(NotFoundException, match="Manifest.*subtract.*not found"):
            api_instance.execute_manifest_manifests_execute_uid_post(
                "calc", arguments
            )
