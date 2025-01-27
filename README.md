# **Project blueberry**

## Introduction :sun_with_face:
The **blueberry** project is an AI system designed to automate gradual reprogramming of workflows with both existing and generated tools. 
The goal is to increase the proportion of using high-quality deterministic tools, thereby reducing hallucinations in the workflows.

> To quickly experiance with blueberry-chat use:  [blueberry-chat](https://pages.github.ibm.com/Blueberry/blueberry/)

## Problem Statement :mushroom:
Hallucinations in agentic workflows can be reduced by increasing the proportion of deterministic tools. The system aims to achieve this by:

1. Using deterministic functional tools instead of internal LLM capabilities.
1. Dynamically building missing tools and functions using LLM-as-a-Coder.
1. Generalizing and publishing tools to reuse them in future tasks and activities.

## Buisness value :clock1:

- Improve AI accuracy and correctness (a.k.a performance)
- Reducing AI systems TCO by offloading part of the relevant functionality to CPUs
- Use-case centric diffrentiation for IBM AI

## Architecture :house:
The system consists of the following components:

- Inferencing Runtime System: The core component that executes the agentic workflows.
- API: Handles incoming requests and provides a standardized interface for the system.
- Router: Directs incoming requests to the appropriate component.
- LLM (Intrinsic): The large language model used to reason, orchestrate, generate content, and plan for the usage of deterministic tools.
- Deterministic Tools: A catalog of curated tools that can be used to assist in answering user questions.
- Tools Execution Service: Executes the selected tools and provides the results to the LLM.

## Workflow :arrow_heading_up:
The workflow of the system is as follows:

- User Prompt: The user submits a question or prompt to the system.
- Planner: The planner determines the stages required to answer the user question and identifies the deterministic tools that can assist in answering the question.
- Tools Generator: Generates a list of potential tools that can be used to answer the question.
- Tools Short-Lister: Shortlists the most relevant tools based on the user prompt and the planner's output.
- Tools Execution Service: Executes the selected tools and provides the results to the LLM.
- LLM: Uses the results from the tools to generate a response to the user prompt.

## Research Challenges :eyes:
The main research challenges:

- Code-based AI tools/functions repository: Developing a runtime and repository for code-based (python) tools that provides strong searchability, NL meta-data, and indexing capabilities.
- Tools shortlisting: Building a system that chooses the most relevant subset of available AI tools for a specific task.
- Tools usage: Convincing and encouraging LLMs to use deterministic tools instead of internal capabilities.
- Automatic tools generation: Using LLM-as-a-Coder to build functional tools that can be used for multiple tasks.
- Continuous improvement with Fine-tuned LLMs: Continuously fine-tuning LLMs to provide less hallucinations and more accurate results.


## Conclusion :clipboard:
The 'blueberry' project aims to reduce hallucinations in agentic workflows by increasing the proportion of deterministic tools used. 
The system consists of various components that work together to achieve this goal.
While there are challenges to be addressed, the system has the potential to provide more accurate and reliable results.
