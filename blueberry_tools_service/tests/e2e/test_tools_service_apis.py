import asyncio
import os
from importlib import resources as impresources
import json
import pytest
import pytest_asyncio

from blueberry_tools_service.client.utils import base_client_utils, json_client_utils
from blueberry_tools_service.tests import resources as resources_package
from blueberry_tools_service.tests.utils import clean_test_tmp_dir, wait_until_server_ready

import blueberry_tools_service_sdk
from blueberry_tools_service_sdk.exceptions import NotFoundException


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
        assert (
                api_response["message"] == f"Manifests ['GetCurrency', 'GetYear'] deleted."
        ), f"Should receive deletion message for GetCurrency and GetYear"


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
