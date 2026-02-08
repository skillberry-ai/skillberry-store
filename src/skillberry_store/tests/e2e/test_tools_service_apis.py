import os
from importlib import resources as impresources
import json
import pytest

from skillberry_store.client.utils import base_client_utils, json_client_utils
from skillberry_store.tests import resources as resources_package
from skillberry_store.tests.e2e.fixtures import run_sbs

import skillberry_store_sdk
from skillberry_store_sdk.exceptions import NotFoundException, ServiceException



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
async def test_add_manifest(run_sbs, func_name):
    """
    Add manifest from the proper json file and module.

    This function is being called at the beginning of the test. It asserts the tools successfully added.

    """
    json_descriptions = load_json_resource("client-win-functions.json")
    module_path = impresources.files(resources_package) / "e2e" / "transformations.py"
    file_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ManifestApi(api_client)

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
async def test_tools_add(run_sbs, func_name):
    """
    Add tools from the proper module.

    This function is being called at the beginning of the test. It asserts the tools successfully added.

    """
    module_path = impresources.files(resources_package) / "e2e" / "client-win-functions.py"
    tool_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ToolsApi(api_client)

        api_response = api_instance.tools_add_tools_add_post(
            "code/python", tool_blob, tool_name=func_name
        )
        assert api_response.get("uid", None), "Should receive 'uid' key"
        assert api_response["uid"] == func_name, f"Should receive uid: {func_name}"


@pytest.mark.asyncio
async def test_tools_add_no_tool_name(run_sbs):
    """
    Add tools from the proper module.

    This function is being called at the beginning of the test. It asserts the tools successfully added.

    """
    module_path = impresources.files(resources_package) / "e2e" / "client-win-functions.py"
    tool_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ToolsApi(api_client)

        # tool_name not supplied - first function is added
        api_response = api_instance.tools_add_tools_add_post(
            "code/python", tool_blob
        )
        assert api_response.get("uid", None), "Should receive 'uid' key"
        assert api_response["uid"] == "GetQuarter", "Should receive uid: GetQuarter"


@pytest.mark.parametrize("func_name", ["GetCurrency", "GetYear", "GetQuarter", "identity"])
@pytest.mark.asyncio
async def test_tools_add_genai(run_sbs, func_name):
    """
    Add tools from the proper json file and module.

    This function is being called at the beginning of the test. It asserts the tools successfully added.

    """
    json_descriptions = load_json_resource("client-win-functions.json")
    json_description = list(filter(lambda d: d["name"] == func_name, json_descriptions))[0]
    module_path = impresources.files(resources_package) / "e2e" / "transformations.py"
    tool_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ToolsApi(api_client)

        json_description_str = json.dumps(json_description)
        api_response = api_instance.tools_add_tools_add_post(
            "json/genai-lh", tool_blob, kwargs=json_description_str
        )
        assert api_response.get("uid", None), "Should receive 'uid' key"
        assert api_response["uid"] == func_name, f"Should receive uid: {func_name}"


@pytest.mark.asyncio
async def test_tools_add(run_sbs):
    """
    Add tools from the proper module. Negative test.

    """
    module_path = impresources.files(resources_package) / "e2e" / "client-win-functions.py"
    tool_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ToolsApi(api_client)
        with pytest.raises(ServiceException, match="Missing docstring description"):
            api_instance.tools_add_tools_add_post(
                "code/python", tool_blob, tool_name="DocstringNoDescription"
            )


@pytest.mark.asyncio
async def test_tools_add(run_sbs):
    """
    Add tools from the proper module. Negative test.

    """
    module_path = impresources.files(resources_package) / "e2e" / "client-win-functions.py"
    tool_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ToolsApi(api_client)
        with pytest.raises(ServiceException, match="Missing docstring parameters"):
            api_instance.tools_add_tools_add_post(
                "code/python", tool_blob, tool_name="DocstringParameterIndentationError"
            )


def test_search_manifests(run_sbs):
    """
    Search manifests.

    """
    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ManifestApi(api_client)

        api_response = api_instance.search_manifest_search_manifests_get(
            "A tool that returns the quarter of the year."
        )

        assert (
                len(api_response) > 0
        ), "Should return at least one manifest for search operation"
        # TODO: asset GetQuarter present and has the smallest score


@pytest.mark.parametrize("uid", ["GetCurrency", "GetYear", "GetQuarter", "identity"])
def test_get_manifest(run_sbs, uid: str):
    """
    Retrieve single manifest.

    """
    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ManifestApi(api_client)

        api_response = api_instance.get_manifest_manifests_uid_get(uid)
        assert api_response.get("uid", None), "Should receive 'uid' key"
        assert api_response["uid"] == uid, f"Should receive uid: {uid}"


def test_list_manifests(run_sbs, expected: int = 4):
    """
    List manifests.

    Parameters:
        expected (int): the number of expected manifests to assert

    """
    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ManifestApi(api_client)

        api_response = api_instance.get_manifests_manifests_get()
        assert (
                len(api_response) == expected
        ), f"Execution failed: received none empty response"


@pytest.mark.parametrize("uid", ["GetQuarter"])
def test_delete_manifest(run_sbs, uid):
    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ManifestApi(api_client)

        api_response = api_instance.delete_manifest_manifests_uid_delete(uid)

        assert api_response.get("message", None), "Should receive 'message' key"
        assert (
                api_response["message"] == f"Manifest '{uid}' deleted."
        ), f"Should receive deletion message for {uid}"


@pytest.mark.parametrize("uid", ["GetQuarter"])
def test_get_manifest2(run_sbs, uid: str):
    """
    Retrieve single manifest.

    """
    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        try:
            api_instance = skillberry_store_sdk.ManifestApi(api_client)
            api_instance.get_manifest_manifests_uid_get(uid)
            assert False, f"Should not find uid: {uid}"

        except NotFoundException:
            pass


def test_delete_manifests_wildcard(run_sbs):
    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ManifestApi(api_client)

        api_response = api_instance.delete_manifests_manifests_delete(manifest_filter="name:Get*")

        assert api_response.get("message", None), "Should receive 'message' key"
        actual = api_response["message"]
        expected1 = f"Manifests ['GetCurrency', 'GetYear'] deleted."
        expected2 = f"Manifests ['GetYear', 'GetCurrency'] deleted."
        assert actual in (expected1, expected2), f"Should receive deletion message for GetCurrency and GetYear"


def test_get_manifests(run_sbs):
    """
    Retrieve single manifest.

    """
    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ManifestApi(api_client)

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
async def test_add_tool_add_subtract(run_sbs, func_name, file_name):
    """
    Add tools 'add' and 'subtract'.

    """
    module_path = impresources.files(resources_package) / "e2e" / "example_functions" / file_name
    tool_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ToolsApi(api_client)

        api_response = api_instance.tools_add_tools_add_post(
            "code/python", tool_blob, tool_name=func_name
        )
        assert api_response.get("uid", None), "Should receive 'uid' key"
        assert api_response["uid"] == func_name, f"Should receive uid: {func_name}"


@pytest.mark.parametrize(
        "func_name, file_name, dependent_manifest_uids", 
        [
            ("calc_add_subtract", "calc_add_subtract.py", ["add", "subtract"])
        ]
)
@pytest.mark.asyncio
async def test_add_tool_calc_add_subtract(run_sbs, func_name, file_name, dependent_manifest_uids):
    """
    Add manifest from the proper module.

    """
    module_path = impresources.files(resources_package) / "e2e" / "example_functions" / file_name
    file_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ManifestApi(api_client)

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


@pytest.mark.parametrize(
        "func_name, file_name, dependent_manifest_uids", 
        [
            ("calc", "calc.py", ["calc_add_subtract"]),

            # for a negative test were we look for module not found error
            ("calc_import_typo", "calc_import_typo.py", ["calc_add_subtract"]),
        ]
)
@pytest.mark.asyncio
async def test_add_tool_calc(run_sbs, func_name, file_name, dependent_manifest_uids):
    """
    Add manifest from the proper module.

    """
    module_path = impresources.files(resources_package) / "e2e" / "example_functions" / file_name
    file_blob = base_client_utils.read_file_to_bytes(module_path)

    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ManifestApi(api_client)

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


@pytest.mark.parametrize("uid, operation, num1, num2, expected",
                         [
                             ("calc", "+", 5, 8, '13'),
                             ("calc", "*", 5, 8, '40.0'),
                        ]
                        ) 
@pytest.mark.asyncio
async def test_execute_calc(run_sbs, uid, operation, num1, num2, expected):
    """
    Execute a manifest that is dependant on others.

    """
    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ManifestApi(api_client)
        arguments = {"operation": operation, "num1": num1, "num2": num2}
        api_response = api_instance.execute_manifest_manifests_execute_uid_post(
            uid, arguments
        )
        assert api_response.get("return value", None) == expected, f"Should get {expected}"


@pytest.mark.parametrize("uid", ["calc_import_typo"]) 
@pytest.mark.asyncio
async def test_execute_calc_negative(run_sbs, uid):
    """
    Execute a manifest that is dependant on others.

    """
    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ManifestApi(api_client)
        arguments = {"operation": "+", "num1": 5, "num2": 8}
        with pytest.raises(ServiceException, match=".*ModuleNotFoundError.*"):
            api_response = api_instance.execute_manifest_manifests_execute_uid_post(
                uid, arguments
            )
            assert api_response.get("return value", None) == '13', "Should get 13"


@pytest.mark.parametrize("uid", ["subtract"])
def test_delete_subtract(run_sbs, uid):
    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ManifestApi(api_client)

        api_response = api_instance.delete_manifest_manifests_uid_delete(uid)

        assert api_response.get("message", None), "Should receive 'message' key"
        assert (
                api_response["message"] == f"Manifest '{uid}' deleted."
        ), f"Should receive deletion message for {uid}"


@pytest.mark.parametrize("uid", ["calc"]) 
@pytest.mark.asyncio
async def test_execute_calc_negative2(run_sbs, uid):
    """
    Execute a manifest that is dependant on others. Negative test.

    """
    configuration = skillberry_store_sdk.Configuration(
        host="http://localhost:8000"
    )
    with skillberry_store_sdk.ApiClient(configuration) as api_client:
        api_instance = skillberry_store_sdk.ManifestApi(api_client)
        arguments = {"operation": "+", "num1": 5, "num2": 8}
        with pytest.raises(NotFoundException, match="Manifest.*subtract.*not found"):
            api_instance.execute_manifest_manifests_execute_uid_post(
                uid, arguments
            )
