# Blueberry-tools-service
The service implementing tools repository for agentic workflows.

# Quickstart

## 1. Prerequisites

```
sudo apt-get update
sudo apt-get upgrade
sudo apt install python3-venv python3-pip

python3 -m pip install --user --upgrade pip

# set virtual environment
python3 -m venv ~/virtual/Blueberry-tools-service
```

## 2. Installation

```
cd ~
git clone -b api_design_v2 git@github.ibm.com:Blueberry/Blueberry-tools-service.git
cd Blueberry-tools-service
source ~/virtual/Blueberry-tools-service/bin/activate
make install_requirements
```

## 3. Run the service

```
cd ~/Blueberry-tools-service
make run
```

# Quick usage

Follow these steps to add, execute and search for tools

As a pre-requisite clone genai lakehouse repository

```
cd ~
git clone git@github.ibm.com:mc-connectors/genai-lakehouse-mapping.git
cd genai-lakehouse-mapping
git checkout 7ff12d99f4533c294a0d978c4a075adda485f02
```

```
source ~/virtual/Blueberry-tools-service/bin/activate
```

## 1. Generate manifest

```
cd ~/Blueberry-tools-service
python client/mft_ds.py ~/genai-lakehouse-mapping/transformations/client-win-functions.py GetQuarter > manifest-GetQuarter.json

```

## 2. Add manifest

```
# this is the module that contains the function of the manifest
file=~/genai-lakehouse-mapping/transformations/client-win-functions.py

file_manifest="./manifest-GetQuarter.json"
manifest=$(cat "$file_manifest")
file_manifest_url=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$manifest'''))")
curl -X POST -H 'accept: application/json' -H 'Content-Type: multipart/form-data' -F "file=@$file" "http://localhost:8000/manifests/add?file_manifest=${file_manifest_url}" | jq .

```

## 3. Get manifest

```
curl -X GET -H 'accept: application/json' -H 'Content-Type: application/json' "http://localhost:8000/manifests/GetQuarter" | jq .
```

## 4. Invoke manifest

```
curl -X POST -H 'accept: application/json' -H 'Content-Type: application/json' --data "{\"input_string\":\"2Q2056\"}" "http://localhost:8000/manifests/execute/GetQuarter" | jq .

```

## 5. Search for manifest

```
curl -X GET -H 'accept: application/json' -H 'Content-Type: application/json' "http://localhost:8000/search/manifests?search_term=quarter+of+the+year" | jq .

```

## 6. Delete manifest

```
curl -X DELETE -H 'accept: application/json' -H 'Content-Type: application/json' "http://localhost:8000/manifests/GetQuarter" | jq .

```

For more examples please refer to [this](contrib/gen_manifests-add-search-get.sh) script


## Personas
- Consumer: a human or AI user who can 
    - Search for a _tool artifact_ by semantic description or UID
    - List tool artifacts
    - Fetch tool artifact
    - Execute tool artifact
    - Contributor: a human or AI user who can
    - Contribute a tool artifact
    - Delete a tool artifact
    - **A Note**: a tool artifact added to the service is pending QA assurance process by the Tool Maintainer persona, before it becomes available for execution 
- Repo Admin: a user with special priviliges who configures the Blueberry Tools Service via a specialized admin interface: 
    - Manages permissions for clients 
    - Manages configuration parameters 
- Tool Maintainer: a human or AI user who approves
    - Quality a tool artifact
    - Removal of a tool artifact
**A Note:** the same user can act in any combination of the roles thereof.

## Tool Artifact
A tool artifact is fully defined by a manifest. 
The manifest includes:
- The artifact UID
- Tool semantic description:
    - name, arguments, type of the arguments, return type(s), admissible range of arguments, admissible range of return values, error codes, examples, provenance, license
    - **Note**: the tool semantic description is provided as semi-structured (e.g., JSON) or unstructured data (free form textual description, or standardized docstring, e.g., [Google Style Python docstring](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html))  
    - Tool artifact status:
    - Submitted
    - Tested
    - Approved
    - Deprecated
    - Archived
    - etc.
- Entry point to the tool code
- Telemetric information:
    - Logs
    - Metrics
    - Usage
    - Cost 
    - etc.
    - Test automation code entry point
    - Test data
- History
    - First submission date
    - Versions
    - Status changes
- Build automation
- Run automation
- **Note:**: not all attributes of the manifest will be supported in the first version.

## Usage Stories
### As Contributor, I wish to insert a new tool artifact into the Blueberry tools service

### As Contributor, I wish to upgrade an existing tool to a new version 

### As Consumer, I wish to find a tool artifact with a specified status and whose manifest's semantic description matches the specified semantic description specified as input with required precision

### As Consumer, I wish to find a tool artifact whose manifest's UID matches a UID specified as input

### As Consumer, I wish to list all tool artifacts in the tool service

### As Consumer, I wish to delete a tool artifact with the specified manifest

### As Consumer, I wish to delete all tools in the service 

### As Tool Maintainer, I wish to set status of a tool artifact in the artifact's manifest for a tool with the specified UID
