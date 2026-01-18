# Overall Configuration Variable Overrides

This table lists the default ports, host URLs and overall service configuration used by SBS service, along with the environment variables that can be used to override them.

| Configuration            | Default value | Environment Variables Override   | Notes
|--------------------------|---------------|----------------------------------|-------------------------------------------------------------|
| FastAPI Service host     | "0.0.0.0"     | `SBS_HOST`                       |                                                             |
| FastAPI Service port     | 8000          | `SBS_PORT`                       |                                                             |
| MCP service Mode         | False         | `MCP_MODE`                       | If True - start SBS as an MCP server                        |
| Prometheus metric port   | 8090          | `PROMETHEUS_METRICS_PORT`        | SBS prometheus endpoint (used for scraping metrics)         |
| Open telemetric port     | None          | `OTEL_TRACES_PORT`               | Must be set for OpenTelemetry tracing to work               |
| Observability enablement | True          | `OBSERVABILITY`                  | If False - disable observability (telemetry and prometheus) |
| Python execution mode    | False         | `EXECUTE_PYTHON_LOCALLY`         | If True - use local exec() instead of Docker |

> You can override the default values by setting the corresponding environment variables in your deployment configuration.


This table lists persistency configuration used by SBS service, along with the environment variables that can be used to override them.

| Configuration             | Default value          | Environment Variables Override   | Notes
|---------------------------|------------------------|----------------------------------|-------------------------------------|
| Files folder (tools blob) | /tmp/files             | `SBS_DIRECTORY_PATH`             | Stores tool blobs (e.g. tools code) |
| Manifests folder          | /tmp/manifest          | `SBS_MANIFEST_DIRECTORY`         | Stores tool manifests               |
| Descriptions folder       | /tmp/descriptions      | `SBS_DESCRIPTIONS_DIRECTORY`     | Stores tool embeddings information  |
| virtual mcp servers list  | /tmp/vmcp_servers.json | `VMCP_SERVERS_FILE`              | Stores virtual mcp servers          |


> You can override the default values by setting the corresponding environment variables in your deployment configuration.


This table lists embedding configuration used by SBS service, along with the environment variables that can be used to override them.

| Configuration   | Default value                                     | Environment Variables Override | 
|-----------------|---------------------------------------------------|--------------------------------|
| Model diemnsion | 384                                               | `EMBEDDING_MODEL_DIMENSION`    |
| Model search k  | 5                                                 | `EMBEDDING_MODEL_SEARCH_K`     |

> You can override the default values by setting the corresponding environment variables in your deployment configuration.
