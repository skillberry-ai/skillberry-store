# Tau-2 tools

Follow instructions in the below order for setting up Tau-2/Skillberry and running the simulator

The following repositories will be used:

* skillberry-dev-tau2
* skillberry-dev-tools-service
* skillberry-dev-agent

## Load (primitive) tools into SBS

Clone this repository and run `init.sh` to load the tools into SBS

venv

```
python3 -m venv ~/virtual/skillberry-dev-tools-service
```

clone

```
cd ~
git clone git@github.ibm.com:skillberry/skillberry-dev-tools-service.git
cd skillberry-dev-tools-service
```

run

```
source ~/virtual/skillberry-dev-tools-service/bin/activate
cd skillberry_store/contrib/examples/tau2/functions
./init.sh
```

The script does the following:

* starts SBS in the background
* resets SBS state (i.e. delete its tools and MCP servers)
* loads the primitive tools
* shutoff SBS

_Tip_: pass additional environment variables according to your environment. Refer to SBS env var configurations [here](https://github.ibm.com/skillberry/skillberry-store/blob/main/docs/config-env-vars.md) for the full list of customizable parameters via env variables

## Tau-2 environment server

The environment server exposes domain specific (e.g. airline) tools as API endpoints. Each
of these tools can be invoked via POST API. The state is being maintained by the environment
server itself 

venv

```
python3 -m venv ~/virtual/tau2-bench
```

clone

```
cd ~
git clone git@github.ibm.com:skillberry/skillberry-dev-tau2.git
cd skillberry-dev-tau2
```

install

```
source ~/virtual/tau2-bench/bin/activate
pip install -e .
```

run

```
python scripts/start_tau2_environment_manager.py
```

## Skillberry (SBS, BTM, SBA)

The skillberry services will be used by the Tau-2 simulator

### Start SBS

```
cd ~/skillberry-dev-tools-service
source ~/virtual/skillberry-dev-tools-service/bin/activate
EXECUTE_PYTHON_LOCALLY=True make run
```

_Tip_: pass additional environment variables according to your environment. Refer to SBS env var configurations [here](https://github.ibm.com/skillberry/skillberry-store/blob/main/docs/config-env-vars.md) for the full list of customizable parameters via env variables

### Start BTM

Currently not being used but is a pre-requisite for SBA

venv

```
python3 -m venv ~/virtual/skillberry-maker
```

clone

```
cd ~
git clone git@github.ibm.com:skillberry/skillberry-maker.git
cd skillberry-maker
```

run

```
source ~/virtual/skillberry-maker/bin/activate
make run
```

### Start SBA

This SBA version sends Tau-2 tools to LLM along with the prompt. LLM returns the best tool to
invoke along with slot filling

venv

```
python3 -m venv ~/virtual/skillberry-dev-agent
```

clone

```
cd ~
git clone git@github.ibm.com:skillberry/skillberry-dev-agent.git
cd skillberry-dev-agent
```

run

```
source ~/virtual/skillberry-dev-agent/bin/activate
make run
```

_notes:_ If you wish BTA to use MCP - prefix `BTA_MCP=True` to make run   

## Simulation

### Tau-2 client

Tau-2 simulator client kicks-off the scenarios (tasks). It "Forwards" agent prompts to SBA via
`/chat/completions` endpoint

run

```
cd ~/skillberry-dev-tau2
source  ~/virtual/tau2-bench/bin/activate
tau2 run --domain airline_skillberry --agent-llm ibm/skillberry-local --user-llm meta-llama/llama-4-maverick-17b-128e-instruct-fp8 --num-trials 30  --task-ids 9 --max-concurrency 1 
```

_notes_: consider saving the file according to a descriptive format name `--save-to vanilla|skillberry-<date>-task-<ids>-<trials>` e.g.

`vanilla-29-10-2025-17-31-task-9-30`, `skillbery-30-10-2025-14-30-task-9-30`

## View Tau-2 simulation result

```
tau2 view
```

follow on screen instructions

_note:_ to view a specific simulation file pass `--file <file name>.json`
