# Clients For The Blueberry Tools Service

The clients implement several important functions:
1. They mediate between the internal generic tool artifacts stored in the service and the simplified abstractions (e.g., single code module) used by consumers
2. It handles the OpenAPI-based interaction with the service
3. It implements usage scenarios defined in the requirement document

## A. Python Client
The Python API exposed by the Blueberry Tools Service client is defined in several parts. All API functions (incl. utility API functions) are well-documented in the Python code with doc strings, so look in the indicated files for the detailed API documentation. Additionally, the `API demo` (see below) contains a usage example for each API function - so be sure to try it and read its code. 

### 1. RECOMMENDED Python Client API
The most convenient client API is defined and documented in the class `ModulesJsonToolsClient` in the file `client/modules_json_tools_client.py`. Similar to the core service API below, this API also exposes all the core functions of the Blueberry tools service. However, it handles generating manifests internally, so consumers don't need to worry about manifest generation at all - only work with tools.

### 2. Core Python API
The core Python API is auto-generated from the service OpenAPI specification and wrapped in a very thin layer designed to remove the a few usage issues from the generated code. It is defined and documented in the class `ToolsClientBase` in the file `client/base_client/tools_client_base.py`. Working with this API requires understanding and generating manifests.

### 3. Utility Python API
Additionally, there are utility functions for generating manifests from code, docstrings, pretty-printing etc. Those functions are designated to assist with engaging the API. There are two sets of utility functions, each defined and documented in a separate file. One set, in the file `client/utils/json_client_utils.py` handles only processing of JSON documentation. The other, broader set, provides the rest of the functions and is located at `client/utils/base_client_utils.py`.

### Using/Testing the Python Client
All tests should be run from the root folder of Blueberry-tools-service

#### 1. API Demo
This is a comprehensive demonstration of all the client-facing tools APIs. 
Make sure that `genai_proj_loc` is set correctly in `main` code to the location of the `genai-lakehouse-mapping` codebase in your filesystem.

To run the demo: `python -m client.demo.api_demo`

#### 2. Manifest Generation Utilities
These are utilities for CLI usage the are built using the Utility API (see above).
1. Generate (on stdout) a manifest for a Python function based on a properly-formatted doc string:
```bash
python -m client.util.manifest_ds <path to module of function> <function name>
```
For example:
```bash
python -m client.utils.manifest_ds ~/genai-lakehouse-mapping/transformations/client-win-functions.py GetQuarter > manifest-GetQuarter.json
```
2. Generate a manifest for a Python function based on a JSON base of function descriptions (using the format defined by the LakeHouse project):
```bash
python -m client.utils.manifest_json <path to JSON definitions folder> <path to module of function> <function name>
```
For example:
```bash
python -m client.utils.manifest_json  ~/genai-lakehouse-mapping/examples ~/genai-lakehouse-mapping/transformations/client-win-functions.py GetQuarter > manifest-GetQuarter.json
```
3. Bulk operation - Generate manifests for all the functions in Python modules in a given folder using either a doc string or (if not available) JSON description from accompanying folder:
```bash
python -m client.utils.manifest_gen <path to JSON definitions folder> <path to folder with Python modules> <path to output folder>
```
For example:
```bash
python -m client.utils.manifest_gen  ~/genai-lakehouse-mapping/examples ~/genai-lakehouse-mapping/transformations ./manifests
```

## B. CLI Client - TOM (TOol Manager)
TOM is a CLI utility that can be used to directly engage the Blueberry Tools Service by users. To install TOM, just run `pip install .` from the root folder when in your virtual env. To launch TOM, simply type `tom`. This will show you the top level help screen describing all available commands as well as how to get more detailed help for each command.
When using TOM for the first time, type `tom config` to generate an initial default configuration profile that will allow you to interact with a locally-installed service. Then you can go on to use all the other TOM commands. If you wish to connect to a remote service, or change the logging level etc, you can create a custom configuration profile (or customize the default profile) - run `tom config --help` for details.
For example: create a new config profile `myremote` for connecting with a remote service in `myserver.example.com:8000` and set logging to CRITICAL (effectively disabling it):
```bash
tom -p myremote config --url http://myserver.example.com:8000 --log_level critical
```  
Now, to use the profile to list the stored tools:
```bash
tom -p myremote list
```

## C. Accessing the Blueberry Tools Service via CURL
Engaging the Blueberry Tools Service core service API by CURL requires some additional processing of manifests using utilities. See `client/curl/README.md` for details. 

