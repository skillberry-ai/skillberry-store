## Basic Client For the Tools Service

The client implements several important functions:
1. It mediates between the internal generic tool artifacts stored in the service and the simplified abstractions (e.g., single code module) used by consumers
2. It handles the OpenAPI-based interaction with the service
3. It implements the usage scenarios defined in the requirement document

### Client Setup
If you're installing the tools service locally using the `Makefile`, then that should be enough for the client as well. NOTE: it's *highly* recommended to use a virtual environment to install Python dependencies. 

If you cloned this repo to install just the client to interact with the tools service remotely, then just run `make install_requirements`

### Testing the Client

#### Manifest generation
1. Generate a manifest for a Python function based on a properly-formatted doc string:
```
python mft_ds.py <path to module of function> <function name>
```
2. Generate a manifest for a Python function based on a JSON base of function descriptions (using the format defined by the LakeHouse project):
```
python mft_json.py <path to JSON definitions folder> <path to module of function> <function name>
```
3. Generate manifests for all the functions in Python modules in a given folder using either a doc string or (if not available) JSON decription from accompanying folder:
```
python mft_gen.py <path to JSON definitions folder> <path to folder with Python modules> <path to output folder>
```