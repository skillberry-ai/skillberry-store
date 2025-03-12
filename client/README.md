## Python Client For The Blueberry Tools Service

The client implements several important functions:
1. It mediates between the internal generic tool artifacts stored in the service and the simplified abstractions (e.g., single code module) used by consumers
2. It handles the OpenAPI-based interaction with the service
3. It implements usage scenarios defined in the requirement document

### Client API
The API exposed by the Blueberry Tools Service client is defined in two layers.

#### 1. Core Service API
The core client API is auto-generated from the service OpenAPI specification and wrapped in a very thin layer designed to remove the a few usage issues from the generated code. It is defined and documented in the class `ToolsClientBase` in the file `client/base_client/tools_client_base.py`.

#### 2. RECOMMENDED Client API
A far more convenient client API is defined and documented in the class `ModulesJsonToolsClient` in the file `client/modules_json_client/modules_json_tools_client.py`. Similar to the core service API above, this API also exposes all the core functions of the Blueberry tools service. However, it handles generating manifests internally, so consumers don't need to worry about manifest generation at all - only work with tools.

#### 3. Utility API
Additionally, there are utility functions for generating manifests from code, docstrings, pretty-printing etc. Those functions are designated to assist with engaging the API. There are two sets of utility functions, each defined and documented in a separate file. One set, in the file `client/modules_json_client/json_client_utils.py` handles only processing of JSON documentation. The other, broader set, provides the rest of the functions and is located at `client/base_client/base_client_utils.py`.

The **API demo** (see below) makes exhaustive use of the recommended client API and also uses some utility functions. It is recommended as a reference for consumers.

### Testing the Client
All tests should be run from the root folder of Blueberry-tools-service

#### 1. API Demo
This is a comprehensive demonstration of all the client-facing tools APIs. 
Make sure that `genai_proj_loc` is set correctly in `main` code to the location of the `genai-lakehouse-mapping` codebase in your filesystem.

To run the demo: `python -m client.api_demo`

#### 2. Manifest Generation Utilities
These are utilities for CLI usage the are built using the Utility API (see above).
1. Generate a manifest for a Python function based on a properly-formatted doc string:
```
python -m client.manifest_ds <path to module of function> <function name>
```
2. Generate a manifest for a Python function based on a JSON base of function descriptions (using the format defined by the LakeHouse project):
```
python -m client.manifest_json <path to JSON definitions folder> <path to module of function> <function name>
```
3. Bulk operation - Generate manifests for all the functions in Python modules in a given folder using either a doc string or (if not available) JSON description from accompanying folder:
```
python -m client.manifest_gen <path to JSON definitions folder> <path to folder with Python modules> <path to output folder>
```

## Accessing the Blueberry Tools Service via CURL
Doable just as well. See `client/curl/README.md` for details. 

