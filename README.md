# Blueberry-tools-service (a.k.a., BTS)

This service implements a smart tools repository for agentic workflows.

## Features ✨

- **Manage tools for agentic workloads**: Add (Persist), Remove, Update, and Delete tools.
- **Tools Execution**: Invoke tools (with parameters) using Docker (sand-boxing).
- **Tools Search and list**: Shortlist tools using semantic and classic search.
- **Tools Life Cycle Management**: Provides tools life cycle management (state, visability, etc.).
- **Observability**: Provide metrics and traces for operational and behivioural analysis of tools usage.
- **OpenAPI frontend**: FastAPI endpoint to interact and manage tools (using tools-manifest artifacts)
- **MCP frontend**: Expose the tools in [MCP](https://github.com/modelcontextprotocol) format.
- **Support Multiple MCP backends**: Consume and route additional tools from multiple backend MCP servers.
- **Agentic Framework Integration**: Connect to different agentic frameworks via the MCP frontend.


## Quickstart 🚀

### Run the Service with Docker 🐳

For a quick start, use Docker to run the service:

```bash
make docker_run
```

> Note: use `make help` for a complete list of options


### Interacting with the UI 👨‍💻

To interact with the UI, navigate to [http://localhost:8000/docs](http://localhost:8000/docs).
This will open the documentation interface where you can explore the available endpoints and test them directly.

### Using the blueberry SDK 🔌

For more detailed information and programmatic usage, refer to the [Blueberry SDK](https://github.ibm.com/Blueberry/blueberry-sdk).

## Prerequisites 🛠️

- Docker is installed on your machine.

Additional requisites for local deployment:
- Your user has Docker permissions (i.e., is a member of the `docker` group).
- The Docker logging driver is set to either `json-file` or `journald`.

> Check the logging driver with the following command:
> ```bash
> docker info --format '{{.LoggingDriver}}'
> ```
> If the response is not `json-file` or `journald`, configure your Docker logging as documented [here](https://docs.docker.com/engine/logging/configure/#configure-the-default-logging-driver).

## Design Requirements

See [DESIGN_REQUIREMENTS.md](DESIGN_REQUIREMENTS.md)

## Local installation 📦

```bash
git clone git@github.ibm.com:Blueberry/blueberry-tools-service.git
cd blueberry-tools-service
make install_requirements
```

## Start the Service locally (alternative to docker) 🚀

```bash
make run
```

## Loading example tools into the Service 📂

- Set the home directory and the EXAMPLESPATH for blueberry-tools-service environment Variables 🌐

```bash
export BTS_HOME=$(pwd)
export EXAMPLESPATH=$BTS_HOME/contrib/examples
```

- Load example tools:

```bash
make ARGS="genai/transformations/client-win-functions.py GetYear GetQuarter GetCurrencySymbol ParseDealSize" load_tools
```

- Alternatively load the example tools using json schema: 

```bash
make ARGS="ClientWinMVP/json ClientWinMVP/functions/transformations.py GetYear GetQuarter GetCurrency GetDealAmount identity" load_tools_json
```


## Engage with the Service via OpenAPI 📜

Open a browser against `http://127.0.0.1:8000/docs` .

## Engage with the Service through a Python Client 🐍

The service can be consumed via blueberry tools service sdk. Refer to [blueberry-sdk](https://github.ibm.com/Blueberry/blueberry-sdk) for installation and usage.

## Run BTS in MCP Server Mode 🖥️

To run BTS in MCP server mode, allowing it to connect to any agent framework that supports MCP, set the MCP_MODE variable:

```bash
MCP_MODE=True make run
```

## Examples of using BTS with Agentic Frameworks 🤖

Follow the steps outlined in [Run BTS with Agent Frameworks](./contrib/examples/agent_framework/agent_framework.md).
> Note: the example makes use of BTS in MCP mode

## Support Multiple MCP Backends

Follow the steps outlined in [Connecting MCP as a backend](contrib/mcp/README.md).

## Monitoring the Service 📈

### To start a local Prometheus server execute:
```bash
echo -e "global:\n  scrape_interval: 5s\nscrape_configs:\n  - job_name: \"blueberry-tools-service\"\n    static_configs:\n      - targets: [\"localhost:9090\"]\n    metric_relabel_configs:\n      - source_labels: [__name__]\n        regex: '.*_created'\n        action: drop" > /tmp/prometheus.yml
docker run --rm --name prometheus --network="host" -p 9090:9090 -v /tmp/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus --config.file=/etc/prometheus/prometheus.yml
```

Metrics are available in Prometheus at http://localhost:9090.
> Note: Application metrics are prefixed with `bts_`.

### To start a local Jaeger server execute:
```bash
docker run --rm --name jaeger --network="host" -p 4317:4317 -p 16686:16686 jaegertracing/all-in-one:latest
```

Traces are available in Jaeger at http://localhost:16686.
