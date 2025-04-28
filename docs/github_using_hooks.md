# Blueberry-tools-service GITHUB support

This document describes how to persist Blueberry tools-service tools using git into a GitHub repository.
This allows you to use GitHub as a backend for Blueberry tools-service, 
allowing to store and manage your tools in a version-controlled environment.

## Prerequisites

- A GitHub repository and account.
- Git installed on your local machine.

## Setup

In order to persist and retrieve tools from GitHub, 
you need to set up a GitHub repository and configure the Blueberry tools-service to use it. 
This is done using environment variables in the format `BTS_HOOK_ID_COMMAND` 
where `HOOK_ID` is the ID of the hook you want to use and `COMMAND` is a fixed.

Following is the list of available Hook IDs and their explanations:

```bash

```markdown
| Hook ID                          | Explanation                                                                 |
|----------------------------------|-----------------------------------------------------------------------------|
| post___init__                    | Executed after initialization of the files module.                          |
| pre_list_files                   | Executed before listing files in the directory.                             |
| post_list_files                  | Executed after successfully listing files in the directory.                 |
| post_fail_list_files             | Executed if listing files in the directory fails.                           |
| pre_read_file                    | Executed before reading a file from the directory.                          |
| post_read_file                   | Executed after successfully reading a file from the directory.              |
| post_fail_read_file              | Executed if reading a file from the directory fails.                        |
| post_raw_content_read_file       | Executed after successfully reading raw content of a file from the directory.|
| post_raw_content_fail_read_file  | Executed if reading raw content of a file from the directory fails.         |
| pre_write_file                   | Executed before writing a file to the directory.                            |
| post_write_file                  | Executed after successfully writing a file to the directory.                |
| post_fail_write_file             | Executed if writing a file to the directory fails.                          |
| pre_write_file_content           | Executed before writing content to a file in the directory.                 |
| post_write_file_content          | Executed after successfully writing content to a file in the directory.     |
| post_fail_write_file_content     | Executed if writing content to a file in the directory fails.               |
| pre_delete_file                  | Executed before deleting a file from the directory.                         |
| post_delete_file                 | Executed after successfully deleting a file from the directory.             |
| post_fail_delete_file            | Executed if deleting a file from the directory fails.                       |
```

If you need anything else, just let me know!

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
export GITHUB_REPO="your_github_username/your_repository_name"
export BTS_POST___INIT___COMMAND='if [ -d "$BTS_DIRECTORY_PATH" ]; then \
    git -C "$BTS_DIRECTORY_PATH" pull origin main; \
else \
    git clone "$GITHUB_REPO" "$BTS_DIRECTORY_PATH"; \
    git -C "$BTS_DIRECTORY_PATH" checkout main; \
fi'
export BTS_POST_WRITE_FILE_COMMAND="git -C $BTS_DIRECTORY_BASE add . && git -C $BTS_DIRECTORY_BASE commit -m 'Add new tool {filename}' && git -C $BTS_DIRECTORY_BASE push origin main"
export BTS_POST_DELETE_FILE_COMMAND="git -C $BTS_DIRECTORY_BASE add . && git -C $BTS_DIRECTORY_BASE commit -m 'Delete tool {filename}' && git -C $BTS_DIRECTORY_BASE push origin main"
```

For a complete end to end example refer [here](../contrib/examples/github/end2end.sh)