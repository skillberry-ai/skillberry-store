# Evaluating Blueberry using Leaderboards

The goal of this document is to help the Blueberry team to narrow down a list of LLM leaderboards suitable for Agentic AI evaluation.

# The Scope

This document is not a comprehensive survey. Rather it assesses the _most popular_ LLM leaderboards w.r.t. the _main_ envisioned contribution of the Blueberry project -- reduction of LLM hallucinations via a gradual deterministic workflow distillation process that replaces intrinsically stochastic generative capabilities by deterministic tools for highly specific tasks.

# Leaderboards

With respect to this document's scope, there are four types of leaderboards: (1) evaluating specific skills using standard benchmarks, (2) evaluating overall performance of LLM using crowdsourcing, (3) evaluating "augmented LLMs" (i.e., agentic systems) using benchmarks aspiring to standarization, and (4) evaluating agentic AI systems using crowdsourcing. 

## _Leaderboards measuring LLM performance using standard benchmarks_

### _Open LLM_
The most popular leaderboard in this category is [Open LLM](https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard#/)
The leaderboard provides the training data sets for the following benchmarks comprising the leaderboard's evaluation process. The leaderboard uses six benchmarks [described here](https://huggingface.co/docs/leaderboards/en/open_llm_leaderboard/about).
The following table summarizes each benchmark and discusses whether Blueberry can achieve higher performance on them than SOTA.
- Fast forward: Open LLM appears to hold potential for Blueberry to improve the SOTA score on some key benchmarks.


|Benchmark|Description|Can Blueberry excel (0-10) |Explanations|Recommendation|
|---------|-----------|------------------------|-----------|-------------|
|[IFEval](https://arxiv.org/abs/2311.07911)| Ability to follow explicit instructions, e.g. "use format f". Focuses on format, not on content|5 |The envisioned QA component of Blueberry can improve ability to follow specific instructions for code generation |There is a potential for Blueberry to improve the score on this benchmark by using open source linters with auto-correction for the code QA component of the architecture. Initially optional (?)|
|[Big Bench Hard (BBH)](https://arxiv.org/abs/2210.09261)|Difficult multi-step arithmetic, algorithmic reasoning, factual knowledge, disambiguation |6-7(?)| Improves correctness of the answers |There is a potential to improve this score by linking search APIs and deterministic arithmetic tools. Provided the multi-step reasoning is good, the overall quality should improve thanks to Blueberry.|
|[MATH](https://arxiv.org/abs/2103.03874)|High school level competition problems | 4(?) | These are problems that might not require much computations, but rather reasoning | Introducing deterministic tools can marginally help wherever explicit computations are required|
|[GPQA (Graduate-Level Google-Proof Q&A Benchmark)](https://arxiv.org/abs/2311.12022)|Factual knowledge in Ph.D. level domains, s.a., chemistry, biology, physics, etc.| 1-2 (?) | The data set is not available to prevent contamination | Apparently, using Web search tools should help, but it won't, because QA of the data brought from the Internet is absent. We might think about some deterministic sub-flow for search that maximizes chances of getting high quality information. For example, there can be site white/black listing, etc. |
|[Multistep Soft Reasoning (MuSR)](https://arxiv.org/abs/2310.16049)|New benchmark on which no LLM performs really well | 0 | The hardness of this benchmark is not related to deterministic tools | Blueberry should ignore this one initially and benefit from an LLM that will become most advanced on this score |
|[Massive Multitask Language Understanding - Professional (MMLU-PRO)](https://arxiv.org/abs/2406.01574) | A new dataset superceding MMLU. LLMs with good reasoning capabilities tend to perform better on MMLU-PRO | 5 | Calculation errors amount to 12% of errors | Introducing deterministic tools will help reducing the calculations errors |

#### _Process of training and submission to Open LLM_
The process is very orderly and clear. To submit a model for evaluation, one has to fill in a model card. 

### _Hallucinations Leaderboard_

The [Halluciantions Leaderboard](https://huggingface.co/blog/leaderboard-hallucinations) is a new effort in an open effort in Hugging Face. The goal is to develop 
> a comprehensive platform that evaluates a wide array of LLMs against benchmarks specifically designed to assess hallucination-related issues via in-context learning.

There are a few benchmarks in the [awesome-hallucination-detection](https://github.com/EdinburghNLP/awesome-hallucination-detection) repo. The intersection between Open LLM and Hallucinations leaderboard is [IFEval](https://huggingface.co/datasets/wis-k/instruction-following-eval). It seems that this effort misses the potential of deterministic tools. This represents an opportunity for Blueberry to contribute its own benchmark to this effort or participate in another way.

### _Leaderboards measuring LLM performance using crowdsourcing_

The most popular leaderboard is [Chatbot Arena LLM Leaderboard](https://huggingface.co/spaces/lmarena-ai/chatbot-arena-leaderboard) (renamed to lmarena). The leaderboard originated in Berkeley. The leaderboard uses randomized double blind pairwise evaluation by humans and assigns the non-biased [Elo rating](https://medium.com/purple-theory/what-is-elo-rating-c4eb7a9061e0) to Models based on who "won the battle" on the same prompt according the opinion of a user. Millions of such pair-wise battles aggregate to form a current rating of a model similarly to rating of a pro chess player. 

While there is a recent work explaining that [Chat Bot Arena rating can be rigged in favor of an attacker](https://arxiv.org/abs/2501.17858), the crowdsourced evaluation is very attractive idea. This leaderboard is directly relevant to Blueberry. The users just have to prefer Blueberry outputs over others. There are no data sets to train on except the data sets that the owners of the model decide to train on. These data sets can be reused from Open LLM or other benchmarks or a combination thereof can be used. However, one has to remember that it is human who judges and human preferences do not align with automated benchmarks always.

The leaderboard provides very large data sets on conversations that users had with the model. Potentially, these data sets can be used for fine tuning of an LLM by Reinforcement Learning (RL). It is assumed that the owners have integrity not to do that.  

#### _Process of submission for evaluation_
The process is not documented. It appears that to be included, one has to contact the owners of the leaderboard. I could not find an automated process of submission similar to that of Open LLM.

### _Leaderboards measuring agentic AI system performance using standard benchmarks_

The more prominent leaderboard is [GAIA](https://huggingface.co/spaces/gaia-benchmark/leaderboard). It was started by the prominent [Yann LeCun](https://en.wikipedia.org/wiki/Yann_LeCun) et. al. This is a benchmark for general AI Assistants. Thus, it is directly relevant to Blueberry.

### _Leaderboards measuring agentic AI system performance using crowdsourcing_

Similarly to ChatBot Arena, Berkeley also created [Agent Arena](https://www.agent-arena.com/) based on the same crowdsourcing rating mechanism. This arena and the correspondiing [leaderboard](https://www.agent-arena.com/leaderboard) are directly relevant to Blueberry.

#### _Process of submission for evaluation_
The process is not documented. It appears that to be included, one has to contact the owners of the leaderboard. I could not find an automated process of submission similar to that of Open LLM.

# Additional Benchmarks (WiP)

# Useful Tools (WiP)

## General Considerations (WiP)

## Sources
TBA
