import os
import pytest
import subprocess
import threading
import time

from skillberry_store.fast_api.server import SBS
from skillberry_store.tests.utils import clean_test_tmp_dir


def run_sbs_server():
    clean_test_tmp_dir()
    app = SBS()
    app.run()

@pytest.fixture(scope="function")
def sbs_server():
    thread = threading.Thread(target=run_sbs_server, daemon=True)
    thread.start()
    time.sleep(2)
    yield

def test_load_tools(sbs_server):
    """Test that the health endpoint returns the expected response."""

    # run the load_tools script
    cwd = os.getcwd()
    base_dir = cwd.removesuffix("/src/skillberry_store/client/curl")

    my_env = os.environ.copy()
    my_env["SBS_HOME"] = base_dir
    examples_path = base_dir + "/src/skillberry_store/contrib/examples/tools"
    my_env["EXAMPLESPATH"] = examples_path

    load_tools_command = cwd + "/src/skillberry_store/client/curl/load_tools.sh"

    command = ["sh", load_tools_command, "genai/transformations/client-win-functions.py", "GetQuarter", "GetYear", "GetCurrencySymbol", "ParseDealSize"]
    # The variables are "exported" to this specific command
    result = subprocess.run(command, env = my_env, capture_output=True)
    assert result.returncode == 0

    command = [ "curl", "-X", "GET", "http://localhost:8000/tools/", "-H", "accept: application/json"]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0
    assert len(result.stdout) != 0

