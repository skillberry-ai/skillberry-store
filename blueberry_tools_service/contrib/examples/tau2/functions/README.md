# Tau-2 tools

Follow instructions in the below order for setting up Tau-2/Skillberry and running the simulator

The following repositories will be used:

* skillberry-dev-tau2
* skillberry-dev-tools-service
* skillberry-dev-agent

## Load tools into SBS

Clone this repository and run `init.sh` to load the tools into SBS

venv

```
python3 -m venv ~/virtual/skillberry-dev-tools-service
```

clone

```
cd ~
git clone git@github.ibm.com:Blueberry/skillberry-dev-tools-service.git
cd skillberry-dev-tools-service
```

run

```
source ~/virtual/skillberry-dev-tools-service/bin/activate
cd blueberry_tools_service/contrib/examples/tau2/functions
./init.sh
```

The script does the following:

* starts SBS in the background
* resets SBS state (i.e. delete its tools and MCP servers)
* loads the tools
* creates MCP server for these tools
* shutoff SBS

_Tip_: set BTS_HOST, BTS_PORT, BTS_DIRECTORY_PATH, BTS_MANIFEST_DIRECTORY, BTS_DESCRIPTIONS_DIRECTORY,  according to your environment. Refer to SBS env var configurations [here](https://github.ibm.com/Blueberry/blueberry-tools-service/blob/main/docs/config-env-vars.md) for the full list of customizable parameters via env variables

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
git clone git@github.ibm.com:Blueberry/skillberry-dev-tau2.git
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

_Tip_: pass additional environment variables according to your environment. Refer to SBS env var configurations [here](https://github.ibm.com/Blueberry/blueberry-tools-service/blob/main/docs/config-env-vars.md) for the full list of customizable parameters via env variables

### Start BTM

Currently not being used but is a pre-req for SBA

venv

```
python3 -m venv ~/virtual/blueberry-tools-maker
```

clone

```
cd ~
git clone git@github.ibm.com:Blueberry/blueberry-tools-maker.git
cd blueberry-tools-maker
```

run

```
source ~/virtual/blueberry-tools-maker/bin/activate
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
git clone git@github.ibm.com:Blueberry/skillberry-dev-agent.git
cd skillberry-dev-agent
```

run

```
source ~/virtual/skillberry-dev-agent/bin/activate
make run
```

## Simulation

### Tau-2 client

Tau-2 simulator client kicks-off the scenarios (tasks). It "Forwards" agent prompts to SBA via
`/chat/completions` endpoint

run

```
cd ~/skillberry-dev-tau2
source  ~/virtual/tau2-bench/bin/activate
tau2 run --domain airline_skillberry --agent-llm ibm/skillberry-local --user-llm rits/meta-llama/llama-4-maverick-17b-128e-instruct-fp8 --num-trials 1  --task-ids 1 --max-concurrency 1 
```

_notes_: consider saving the file according to a descriptive format name `--save-to vanilla|skillberry-<date>-task-<ids>-<trials>` e.g.

`vanilla-29-10-2025-17-31-task-1-30`, `skillbery-30-10-2025-14-30-task-1_5_2_6-30`

## View Tau-2 simulation result

```
tau2 view
```

follow on screen instructions

_notes:_ to view a specific simulation file pass `--file <file name>.json`
