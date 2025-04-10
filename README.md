# Blueberry-tools-service

This service implements a smart tools repository for agentic workflows.

## Quickstart 🚀

### Run the Service with Docker 🐳

For a quick start, use Docker to run the service:

```bash
make docker_run
```
  
### Prerequisites 🛠️
  
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

### Local installation 📦

```bash
git clone git@github.ibm.com:Blueberry/blueberry-tools-service.git
cd blueberry-tools-service
make install_requirements
```

### Start the Service locally 🚀

```bash
make run
```

### Loading example tools into the Service 📂

- Set the home directory and the EXAMPLESPATH for blueberry-tools-service environment Variables 🌐

```bash
export BTS_HOME=$(pwd)
export EXAMPLESPATH=$BTS_HOME/contrib/examples
```

- Load example tools: 

```bash
make ARGS="genai/transformations/client-win-functions.py GetYear GetQuarter GetCurrencySymbol ParseDealSize" load_tools
```

### Engage with the Service via OpenAPI (Swagger) 📜

Open a browser against `http://127.0.0.1:8000/docs`.

### Engage the Service through a Python Client and CURL 🐍

Refer to [client/README.md](client/README.md) for more information on using the service clients, including Python and CURL clients.   
There are also tests and demos available.

### Run BTS in MCP Server Mode 🖥️

To run BTS in MCP server mode, allowing it to connect to any agent framework that supports MCP, set the MCP_MODE variable:

```bash
MCP_MODE=True make run
```

### Examples of using BTS with Agentic Frameworks 🤖

Follow the steps outlined in [Run BTS with Agent Frameworks](./contrib/examples/agent_framework/agent_framework.md).

## Monitoring the Service 📈

- To start a local Prometheus server, open a new browser tab/window and execute:
```bash
echo -e "global:\n  scrape_interval: 5s\nscrape_configs:\n  - job_name: \"blueberry-tools-service\"\n    static_configs:\n      - targets: [\"localhost:9000\"]\n    metric_relabel_configs:\n      - source_labels: [__name__]\n        regex: '.*_created'\n        action: drop" > /tmp/prometheus.yml
docker run --rm --name prometheus --network="host" -p 9090:9090 -v /tmp/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus --config.file=/etc/prometheus/prometheus.yml
```

Metrics are available in Prometheus at http://localhost:9090. Note: Application metrics are prefixed with `bts_`.

- To start a local Jaeger server, open a new browser tab/window and execute:
```bash
docker run --rm --name jaeger --network="host" -p 4317:4317 -p 16686:16686 jaegertracing/all-in-one:latest
```

Traces are available in Jaeger at http://localhost:16686.
