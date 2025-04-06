# Agent Framework
## 1. Set Environment Variables

First, make sure that `$BTS_HOME` and  `EXAMPLESPATH` are set as defined in the project [README](../../../README.md)

## 2. Configure the `.env` File

To connect BTS to different agent frameworks, set the following parameters in the `.env` file:

```bash
MODEL_NAME=rits/meta-llama/llama-3-3-70b-instruct
BASE_URL=http://blueberry.sl.cloud9.ibm.com:4000
OPENAI_API_KEY=<RITS_API_KEY>
```

## 3. Run BTS in MCP Server Mode

Run BTS in MCP server mode. The server is blocking, so it's recommended to run it in a separate terminal:

```bash
cd $BTS_HOME
MCP_MODE=True make run
```

## 4. Upload Tools to BTS Server

Upload the calculator functions to the BTS server by running:

```bash
cd $BTS_HOME
make ARGS="genai/calculator/calculator-functions.py add subtract multiply nth_root power modulo" load_tools
```

## 5. Run the Agent Framework

Run the agent framework that connects to the BTS server. For example:

```bash
python contrib/examples/agent_framework/connect_langgraph_client.py
```

