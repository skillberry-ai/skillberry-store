## Client For the Tools Service

The client implements several important functions:
1. It mediates between the internal generic tool artifacts stored in the service and the simplified abstractions (e.g., single code module) used by consumers
2. It handles the OpenAPI-based interaction with the service
3. It implements the usage scenarios defined in the requirement document

### Client API
Currently, we have one class of client API - `ModulesJsonToolsClient`. This is a client exposes all the core functions of the Blueberry tools service in a convenient manner. Specifically, it handles generating manifests from function docstrings or (if docstring not available) from an optional JSON base that is provided externally. The documented client API is found in the file `client/modules_json_client/modules_json_tools_client.py`.

Additionally, there are utility functions for extracting manifests, docstrings, pretty-printing etc. Those functions are beyond the designated API, but may be helpful as well. There are two sets of utility functions. One set, in the file `client/modules_json_client/json_client_utils.py` handles only processing of JSON documentation. The other, broader set, provides the rest of the functions and is located at `client/base_client/base_client_utils.py`.

The API demo (see below) makes exhaustive use of the client API and also uses some utility functions. Thus, it can be used as a reference for exploiters.

### Client Setup
If you're installing the tools service locally using the `Makefile`, then that should be enough for the client as well. NOTE: it's *highly* recommended to use a virtual environment to install Python dependencies. 

If you cloned this repo to install just the client to interact with the tools service remotely, then just run `make install_requirements`

### Testing the Client
All tests should be run from the root folder of Blueberry-tools-service

#### Manifest generation
1. Generate a manifest for a Python function based on a properly-formatted doc string:
```
python -m client.manifest_ds <path to module of function> <function name>
```
2. Generate a manifest for a Python function based on a JSON base of function descriptions (using the format defined by the LakeHouse project):
```
python -m client.manifest_json <path to JSON definitions folder> <path to module of function> <function name>
```
3. Generate manifests for all the functions in Python modules in a given folder using either a doc string or (if not available) JSON description from accompanying folder:
```
python -m client.manifest_gen <path to JSON definitions folder> <path to folder with Python modules> <path to output folder>
```

#### Demo of client API
Make sure that `genai_proj_loc` is set correctly in `main` code to the location of the `genai-lakehouse-mapping` codebase in your filesystem.

To run the demo: `python -m client.api_demo`

