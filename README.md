# Blueberry-tools-service
This service implements a smart tools repository for agentic workflows.

# Design Requirements
See `REQUIREMENTS.md`

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

Next, install prereqs as listed below:   
```
sudo apt-get update
sudo apt-get upgrade
sudo apt install python3-venv python3-pip

python3 -m pip install --user --upgrade pip

# set virtual environment
python3 -m venv ~/virtual/Blueberry-tools-service
```

## 2. Installation

```bash
cd ~
git clone -b api_design_v2 git@github.ibm.com:Blueberry/Blueberry-tools-service.git
cd Blueberry-tools-service
source ~/virtual/Blueberry-tools-service/bin/activate
make install_requirements
```

## 3. Start the service

```bash
cd ~/Blueberry-tools-service
make run
```

## 4. Setup the Python client
When the service is running:
```bash
make gen_client
```
You can now read `client/README.md` to learn more about the service clients, including testing and using the Python APIs and utilities

# Loading Sample Data

This step downloads sample tools and JSON data to play with from the `genai-lakehouse-mapping` repository
```bash
cd ~
git clone git@github.ibm.com:mc-connectors/genai-lakehouse-mapping.git
cd genai-lakehouse-mapping
git checkout 7ff12d99f4533c294a0d978c4a075adda485f02
```

