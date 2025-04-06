# Blueberry-tools-service
This service implements a smart tools repository for agentic workflows.

# Design Requirements
See [DESIGN_REQUIREMENTS.md](DESIGN_REQUIREMENTS.md)

# Quickstart

## 1. Prerequisites

Prior to installing, make sure that:
1. Your machine has Docker installed
2. Your user has Docker permissions (i.e., is a member of the `docker` group)
3. Docker logging driver must be set to either `json-file` or `journald`. You can check which logging is enabled by running the following command:
```bash
docker info --format '{{.LoggingDriver}}'
```
If the response is not `json-file` or `journald`, fix your Docker logging as documented [here](https://docs.docker.com/engine/logging/configure/#configure-the-default-logging-driver)

Set virtual environment

```bash
python3 -m venv ~/virtual/blueberry-tools-service
```

## 2. Installation

```bash
cd ~
git clone git@github.ibm.com:Blueberry/blueberry-tools-service.git
cd blueberry-tools-service
source ~/virtual/blueberry-tools-service/bin/activate
make install_requirements
```

## 3. Environment Variables

### Set blueberry-tools-service home directory

```bash
cd ~/blueberry-tools-service
export BTS_HOME=$(pwd)
```
### Set blueberry-tools-service EXAMPLESPATH to default enclosed examples

```bash
cd ~/blueberry-tools-service
export EXAMPLESPATH=$BTS_HOME/contrib/examples
```

## 4. Start the service

```bash
cd ~/blueberry-tools-service
make run
```

## 5. Load examples into the service
```bash
cd ~/blueberry-tools-service
make ARGS="genai/transformations/client-win-functions.py GetYear GetQuarter GetCurrencySymbol ParseDealSize" load_tools
```

## 6. Engage with the service via OpenAPI (Swagger)
Open a new browser tab/window
Copy `0.0.0.0:8000/docs` into the browser search bar and press `Enter`

## 7. Engage the service through a Python client and CURL
You can now read [client/README.md](client/README.md) to learn more about the service clients - both Python client and CURL client. There are also tests and demos you can use.

## 8. Run BTS in MCP Server Mode

Run BTS in MCP server mode to allow it to connect to any agent framework that supports MCP. Set the MCP_MODE variable:

```bash
MCP_MODE=True make run
```

### 9. Run BTS with Agent Frameworks

To connect BTS to different agent frameworks, follow the steps outlined in [Run BTS with Agent Frameworks](./contrib/examples/agent_framework/agent_framework.md).


## Loading Sample Data

This step downloads sample tools and JSON data to play with from the `genai-lakehouse-mapping` repository
```bash
cd ~
git clone git@github.ibm.com:mc-connectors/genai-lakehouse-mapping.git
cd genai-lakehouse-mapping
git checkout 7ff12d99f4533c294a0d978c4a075adda485f02
```

## Monitoring the service

- Open a new browser tab/window and execute: (to start a local prometheus server)
```bash
echo -e "global:\n  scrape_interval: 5s\nscrape_configs:\n  - job_name: \"blueberry-tools-service\"\n    static_configs:\n      - targets: [\"localhost:9000\"]\n    metric_relabel_configs:\n      - source_labels: [__name__]\n        regex: '.*_created'\n        action: drop" > /tmp/prometheus.yml
docker run --rm --name prometheus --network="host" -p 9090:9090 -v /tmp/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus --config.file=/etc/prometheus/prometheus.yml
```

Metrics are available in prometheus: http://localhost:9090
Note: Application metrics are prefix with `bts_`

- Open a new browser tab/window and execute: (to start a local jaeger server)
```bash
docker run --rm --name jaeger --network="host" -p 4317:4317 -p 16686:16686 jaegertracing/all-in-one:latest
```

Trace are available in jaeger: http://localhost:16686
