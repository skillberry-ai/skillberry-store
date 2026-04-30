# Overall Configuration Variable Overrides

This table lists the default ports, host URLs and overall service configuration used by SBS service, along with the environment variables that can be used to override them.

| Configuration            | Default value | Environment Variables Override   | Notes
|--------------------------|---------------|----------------------------------|-------------------------------------------------------------|
| FastAPI Service host     | "0.0.0.0"     | `SBS_HOST`                       |                                                             |
| FastAPI Service port     | 8000          | `SBS_PORT`                       |                                                             |
| UI port                  | 8002          | `SBS_UI_PORT`                    | Port for the web UI server                                  |
| UI enablement            | True          | `ENABLE_UI`                      | If False - disable the UI and run only the backend          |
| Prometheus metric port   | 8090          | `PROMETHEUS_METRICS_PORT`        | SBS prometheus endpoint (used for scraping metrics)         |
| Open telemetric port     | None          | `OTEL_TRACES_PORT`               | Must be set for OpenTelemetry tracing to work               |
| Observability enablement | True          | `OBSERVABILITY`                  | If False - disable observability (telemetry and prometheus) |
| Python execution mode    | False         | `EXECUTE_PYTHON_LOCALLY`         | If True - use local exec() instead of Docker                |
| Auto-detect dependencies | True          | `AUTO_DETECT_TOOL_DEPENDENCIES`  | If False - disable automatic tool dependency detection      |

> You can override the default values by setting the corresponding environment variables in your deployment configuration.


This table lists persistency configuration used by SBS service, along with the environment variables that can be used to override them.

| Configuration                      | Default value                                  | Environment Variables Override          | Notes
|------------------------------------|------------------------------------------------|-----------------------------------------|-------------------------------------|
| Base directory                     | {system_temp}/skillberry-store                 | `SBS_BASE_DIR`                          | Parent directory for all SBS storage |
| Files folder (tools blob)          | {SBS_BASE_DIR}/files                           | `SBS_DIRECTORY_PATH`                    | Stores tool blobs (e.g. tools code) |
| Tools directory                    | {SBS_BASE_DIR}/tools                           | `SBS_TOOLS_DIRECTORY`                   | Stores tool files                   |
| Tools descriptions folder          | {SBS_BASE_DIR}/tools_descriptions              | `SBS_TOOLS_DESCRIPTIONS_DIRECTORY`      | Stores tool embeddings information  |
| Snippets directory                 | {SBS_BASE_DIR}/snippets                        | `SBS_SNIPPETS_DIRECTORY`                | Stores snippet files                |
| Snippets descriptions folder       | {SBS_BASE_DIR}/snippets_descriptions           | `SBS_SNIPPETS_DESCRIPTIONS_DIRECTORY`   | Stores snippet embeddings           |
| Skills directory                   | {SBS_BASE_DIR}/skills                          | `SBS_SKILLS_DIRECTORY`                  | Stores skill files                  |
| Skills descriptions folder         | {SBS_BASE_DIR}/skills_descriptions             | `SBS_SKILLS_DESCRIPTIONS_DIRECTORY`     | Stores skill embeddings             |
| Metadata directory                 | {SBS_BASE_DIR}/metadata                        | `SBS_METADATA_DIRECTORY`                | Stores metadata files               |
| VMCP directory                     | {SBS_BASE_DIR}/vmcp                            | `SBS_VMCP_DIRECTORY`                    | Stores virtual MCP server files     |
| VMCP descriptions folder           | {SBS_BASE_DIR}/vmcp_descriptions               | `SBS_VMCP_DESCRIPTIONS_DIRECTORY`       | Stores VMCP embeddings              |
| Virtual MCP servers list           | {system_temp}/skillberry-store/vmcp_servers.json | `VMCP_SERVERS_FILE`                   | Stores virtual MCP servers list     |

> **Note:** `{system_temp}` refers to the operating system's temporary directory.
> All directory paths default to subdirectories under `SBS_BASE_DIR`. You can override individual directories or set `SBS_BASE_DIR` to change the base location for all directories.


This table lists embedding configuration used by SBS service, along with the environment variables that can be used to override them.

| Configuration   | Default value                                     | Environment Variables Override | 
|-----------------|---------------------------------------------------|--------------------------------|
| Vector database | "faiss"                                           | `SBS_VDB`                      |
| Model dimension | 384                                               | `EMBEDDING_MODEL_DIMENSION`    |
| Model search k  | 5                                                 | `EMBEDDING_MODEL_SEARCH_K`     |

> You can override the default values by setting the corresponding environment variables in your deployment configuration.


This table lists MCP (Model Context Protocol) configuration used by SBS service, along with the environment variables that can be used to override them.

| Configuration          | Default value                  | Environment Variables Override | Notes                                    |
|------------------------|--------------------------------|--------------------------------|------------------------------------------|
| MCP server URL         | "http://localhost:8080/sse"    | `MCP_SERVER_URL`               | MCP server URL for SSE connections       |
| VMCP servers start port| 10000                          | `VMCP_SERVERS_START_PORT`      | Starting port for virtual MCP servers    |

> You can override the default values by setting the corresponding environment variables in your deployment configuration.


This table lists test configuration used by SBS service, along with the environment variables that can be used to override them.

| Configuration   | Default value | Environment Variables Override | Notes                                    |
|-----------------|---------------|--------------------------------|------------------------------------------|
| Test debug mode | False         | `SBS_TEST_DEBUG`               | If True - enable debug logging for tests |

> You can override the default values by setting the corresponding environment variables in your deployment configuration.

### Example: Running tests with debug logs enabled

To enable debug logging when running tests with make:

```bash
SBS_TEST_DEBUG=true make test
