# Tau-2 tools

Follow instructions below for setting up tau2/skillberry and running the simulator.

An updated BTA is being used as the agent. It sends all tau-2 tools to LLM on every prompt it receives

## Load tools into SBS

Clone this repository and run `init.sh` to load the tools into SBS

**Note:** ensure to use this repository for the SBS/BTS

```
cd ~
git clone git@github.ibm.com:Blueberry/skillberry-dev-tools-service.git
cd skillberry-dev-tools-service/blueberry_tools_service/contrib/examples/tau2/functions
./init.sh
```

The script does the following:

* starts SBS in the background
* resets SBS state (i.e. delete its tools and MCP servers)
* loads the tools
* creates MCP server for these tools
* shutoff SBS

_Tip_: set BTS_HOST, BTS_PORT according to your environment

## Tau2 environment server

The environment server exposes domain specific (e.g. airline) tools as API endpoints. Each
of these tools can be invoked via POST API. The state is being maintained by the environment
server itself 

### venv

```
python3 -m venv ~/virtual/tau2-bench
```


### Clone

```
cd ~
git clone https://github.com/sierra-research/tau2-bench.git
cd tau2-bench
git checkout 5ba9e3e56db57c5e4114bf7f901291f09b2c5619
```

### Install

```
source  ~/virtual/tau2-bench/bin/activate
pip install -e .
```

### Run

```
tau2 domain airline
```

## Blueberry (BTS, BTM, BTA)

### Start BTS

Stores tau-2 tools and invoke them

```
EXECUTE_PYTHON_LOCALLY=True make run
```

### Start BTM

Currently not being used but is a pre-req for BTA

```
make run
```

### Start BTA

This BTA version sends all tau-2 tools to LLM along with the prompt. LLM returns the best tool to
invoke along with slot filling

* Clone

  ```
  cd ~
  git clone git@github.ibm.com:WEIT/blueberry-tools-agent.git
  cd blueberry-tools-agent
  git checkout tau-2
  ```

* Run

  ```
  make run
  ```

## Simulation

### Tau2 client

Tau2 client kicks-off the scenarios (tasks). It "Forwards" agent prompts to BTA via
`/chat/completions` endpoint

* venv

  ```
  python3 -m venv ~/virtual/tau2-bench-client
  ```

* clone

  ```
  cd ~
  git clone git@github.ibm.com:WEIT/tau2-bench.git tau2-bench-client
  cd tau2-bench-client
  git checkout f0860fa3095985bfd884107ddb35fa322166edf5
  ```


* install

  ```
  source  ~/virtual/tau2-bench-client/bin/activate
  pip install -e .
  ```

* run

  ```
  tau2 run --domain airline --agent-llm ibm/skillberry-local --user-llm rits/meta-llama/llama-4-maverick-17b-128e-instruct-fp8 --num-trials 1 --num-tasks 1 --agent llm_agent
  ```

  Tip: use `task-ids` to trigger specific tasks e.g `--task-ids 2` 

## View tau-2 simulation result

In "Tau2 client" terminal run

```
tau2 view
```

and follow on screen instructions
