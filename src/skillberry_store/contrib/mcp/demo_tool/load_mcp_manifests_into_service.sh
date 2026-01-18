#!/bin/bash

#
# Script to load mcp tools into tools-service to be used by Skillberry.
#
# Pre-requisite:
#
# Run the MCP server with an accessible URL. For example, start the server located in `contrib/mcp/server`:
#
# uv run server/server.py
#
# Note: update mcp and tools service urls accordingly

SLEEP_TIME=1

bold=$(tput bold)
normal=$(tput sgr0)

echo "${bold}Creating the manifests...${normal}"
# these are the tool names defined inside mcp host
declare -a values=("add" "subtract" "multiply" "divide" "nth_root" "power" "modulo" "log")
for value in "${values[@]}"; do
    echo "${bold}Generating manifest: '$value' file...${normal}"

    manifest=$(cat <<EOF
    {
        "programming_language": "python",
        "packaging_format": "mcp",
        "version": "0.0.1",
        "mcp_url": "http://localhost:8080/sse",
        "name": "${value}",
        "state": "approved"
    }
EOF
    )

    echo "${bold}Adding manifest: '$value'...${normal}"
    file_manifest_url=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$manifest'''))")
    curl -X POST \
        -H 'accept: application/json' \
        "http://localhost:8000/manifests/add?file_manifest=${file_manifest_url}" | jq .

    sleep $SLEEP_TIME
done
