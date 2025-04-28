# Blueberry-tools-service GITHUB support

This document describes how to persist Blueberry tools-service tools to a GitHub repository.
This allows you to use GitHub as a backend for Blueberry tools-service, 
enabling you to store and manage your tools in a version-controlled environment.

## Prerequisites

- A GitHub repository and account.
- Git installed on your local machine.

## Setup

In order to persist and retrieve tools from GitHub, 
you need to set up a GitHub repository and configure the Blueberry tools-service to use it. 
This is done using command line variables in the format `BTS_HOOK_ID_COMMAND"` 
where `HOOK_ID` is the ID of the hook you want to use and `COMMAND` is a fixed.

### Example

Step 1: Define the git directory path where you want to store the tools. Make sure that this repository is a clone
of GitHub repo and that the branch is checked out. In the example we use the `main` branch.

```bash
export BTS_DIRECTORY_BASE="/path/to/your/git/repositroy"

export BTS_DIRECTORY_PATH="$BTS_DIRECTORY_BASE/tools"
export BTS_DESCRIPTIONS_DIRECTORY="$BTS_DIRECTORY_PATH/descriptions"
export BTS_METADATA_DIRECTORY="$BTS_DIRECTORY_PATH/metadata"
export BTS_MANIFEST_DIRECTORY="$BTS_DIRECTORY_PATH/manifest"
```

Step 2: Define hooks that will be called when storing and deleting tools.

```bash
export BTS_POST_WRITE_FILE_COMMAND="git -C $DIRECTORY_PATH add . && git -C $DIRECTORY_PATH commit -m 'Add new tool {filename}' && git -C $DIRECTORY_PATH push origin main"
export BTS_POST_DELETE_FILE_COMMAND="git -C $DIRECTORY_PATH add . && git -C $DIRECTORY_PATH commit -m 'Delete tool {filename}' && git -C $DIRECTORY_PATH push origin main"
```
