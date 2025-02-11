# tools-agent
## AI agentic service for the blueberry project

This folder holds the code for the agentic-service. 

The service exposes openAI LLM completion rest allowing external usage "LLM like" interfacing.
The service implements an agentic workflow using LangGraph/ LangChain.
The service interfaces with the tools-service to use, create and execute tools.
The service interfaces with LLMs to plan, code and complete responses for user prompts. 

The service performs an agentic workflow that advocates usage of tools 
to help in reduction hallucinations and increase the accuracy of LLMs. 

> Use the Makefile for additional details 

## how to execute
```bash
make start
```

## 