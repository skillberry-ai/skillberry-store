# MCP Server Experiment Guide

## Steps to Experiment with the MCP Server

Follow these steps to set up and experiment with the MCP server:

### 1. Start an MCP Server
Run the MCP server with an accessible URL. For example, start the **Math Tool Server** located in `contrib/mcp/server`:

```sh
uv run server/server.py
```

This will start the MCP server at the following URL:
**`http://127.0.0.1:8080`**

### 2. Run the  Service Tool
Make sure the **Skillberry Store service** is running by executing the following command in the **skillberry-store** root folder:

```sh
make run
```

### 3. Add single tool from the MCP server

create the manifest, pointing it to the running server

```
cat <<EOF > my-manifest.json
{
    "programming_language": "python",
    "packaging_format": "mcp",
    "version": "0.0.1",
    "mcp_url": "http://localhost:8080/sse",
    "name": "multiply",
    "state": "approved"
}
EOF

```

add the manifest. This will add the tool to the tools service and will embed tool description

```
file_manifest="./my-manifest.json"
manifest=$(cat "$file_manifest")
file_manifest_url=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$manifest'''))")
curl -X POST \
    -H 'accept: application/json' \
    "http://localhost:8000/manifests/add?file_manifest=${file_manifest_url}" | jq .

```

### 4. Execute the tool

```
curl -X POST \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    --data "{\"a\":\"5\", \"b\":\"5\"}" "http://localhost:8000/manifests/execute/multiply" | jq .

```

### 5. Search for the tool

```
curl -X GET \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    "http://localhost:8000/search/manifests?search_term=multiply+numbers" | jq .

```
