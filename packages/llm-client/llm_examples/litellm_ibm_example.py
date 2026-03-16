import asyncio
from typing import List, Optional
from pydantic import BaseModel

from llm_client import configure_logging
from llm_client.llm import get_llm
from llm_client.llm.types import GenerationArgs

# ──────────────────────────────────────────────────────────────────────────────
# Configure Rich Logging (with visual formatting)
# ──────────────────────────────────────────────────────────────────────────────
configure_logging(level="DEBUG")  # Set to INFO, DEBUG, WARNING, ERROR as needed


# ──────────────────────────────────────────────────────────────────────────────
# 1. Define schemas for structured output
# ──────────────────────────────────────────────────────────────────────────────


class Person(BaseModel):
    name: str
    age: int
    occupation: Optional[str] = None


class TechnicalAnalysis(BaseModel):
    topic: str
    complexity_level: str
    key_points: List[str]
    confidence_score: float


# ──────────────────────────────────────────────────────────────────────────────
# 2. Initialize IBM LiteLLM clients
# ──────────────────────────────────────────────────────────────────────────────

try:
    # Basic IBM LiteLLM clients
    IBMLiteLLMClient = get_llm("litellm.ibm")
    IBMLiteLLMClientOutputVal = get_llm("litellm.ibm.output_val")

    ibm_client = IBMLiteLLMClient(
        model_name="GCP/claude-3-7-sonnet",
        hooks=[lambda event, payload: print(f"[IBM] {event}: {payload}")],
    )

    ibm_structured_client = IBMLiteLLMClientOutputVal(
        model_name="GCP/claude-3-7-sonnet",
        hooks=[lambda event, payload: print(f"[IBM STRUCTURED] {event}: {payload}")],
        include_schema_in_system_prompt=True,
    )

    print("✅ IBM LiteLLM clients initialized successfully")

except Exception as e:
    print(f"❌ Failed to initialize IBM clients: {e}")
    print("Make sure to install: pip install toolkit-core[litellm]")
    print("And set your IBM_THIRD_PARTY_API_KEY environment variable.")
    exit(1)


# ──────────────────────────────────────────────────────────────────────────────
# 3. Basic generation examples (without output validation)
# ──────────────────────────────────────────────────────────────────────────────


def demo_basic_generation():
    """Demonstrate basic text generation without output validation"""
    print("\n" + "=" * 60)
    print("BASIC GENERATION EXAMPLES (No Output Validation)")
    print("=" * 60)

    # Simple text generation
    print("\n--- Simple Text Generation ---")
    text_prompt = "Explain the concept of distributed computing systems."

    # Create generation arguments for controlling the output
    gen_args = GenerationArgs(
        max_tokens=150, temperature=0.7, top_p=0.9, stop_sequences=["<END>", "---"]
    )

    try:
        response = ibm_client.generate(text_prompt, generation_args=gen_args)
        print(f"Prompt: {text_prompt}")
        print(f"Response: {response}")
        print(f"Generation Args: {gen_args}")
    except Exception as e:
        print(f"Error: {e}")

    # Chat messages
    print("\n--- Chat Messages ---")
    chat_prompt = [
        {
            "role": "system",
            "content": "You are a helpful technical assistant specializing in enterprise software.",
        },
        {
            "role": "user",
            "content": "What are the advantages of microservices architecture?",
        },
    ]

    # Create different generation arguments for chat
    chat_gen_args = GenerationArgs(
        max_tokens=200,
        temperature=0.3,
        presence_penalty=0.1,
        frequency_penalty=0.1,
    )

    try:
        response = ibm_client.generate(chat_prompt, generation_args=chat_gen_args)
        print(f"Prompt: {chat_prompt}")
        print(f"Response: {response}")
        print(f"Generation Args: {chat_gen_args}")
    except Exception as e:
        print(f"Error: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# 4. Tool calling examples (without output validation)
# ──────────────────────────────────────────────────────────────────────────────


def demo_tool_calling():
    """Demonstrate tool calling without output validation"""
    print("\n" + "=" * 60)
    print("TOOL CALLING EXAMPLES (No Output Validation)")
    print("=" * 60)

    # Define tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "analyze_code_complexity",
                "description": "Analyze code complexity metrics",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code_snippet": {
                            "type": "string",
                            "description": "Code to analyze",
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language",
                        },
                    },
                    "required": ["code_snippet"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "estimate_performance",
                "description": "Estimate algorithm performance",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "algorithm": {
                            "type": "string",
                            "description": "Algorithm description",
                        },
                        "input_size": {
                            "type": "number",
                            "description": "Expected input size",
                        },
                    },
                    "required": ["algorithm"],
                },
            },
        },
    ]

    # Tool calling example
    print("\n--- Tool Calling ---")
    prompt = [
        {
            "role": "user",
            "content": "Analyze the complexity of bubble sort algorithm and estimate its performance for 1000 elements.",
        }
    ]

    try:
        response = ibm_client.generate(prompt, tools=tools, tool_choice="auto")

        print(f"Prompt: {prompt[0]['content']}")

        if hasattr(response, "tool_calls") and response.tool_calls:
            print(f"Content: {response.content}")
            print("Tool calls:")
            for tool_call in response.tool_calls:
                print(
                    f"  - {tool_call['function']['name']}: {tool_call['function']['arguments']}"
                )
        else:
            print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# 5. Structured output validation examples
# ──────────────────────────────────────────────────────────────────────────────


def demo_output_validation():
    """Demonstrate output validation with Pydantic models and JSON schemas"""
    print("\n" + "=" * 60)
    print("OUTPUT VALIDATION EXAMPLES")
    print("=" * 60)

    # Example 1: Pydantic model validation
    print("\n--- Pydantic Model Validation ---")
    person_prompt = (
        "Generate details for a software engineer named Alice who is 30 years old."
    )

    try:
        validated_person = ibm_structured_client.generate(
            person_prompt,
            schema=Person,
            retries=3,
            generation_args=GenerationArgs(temperature=0.1),
        )
        print(f"Prompt: {person_prompt}")
        print(f"Response (Person): {validated_person}")
        print(f"Type: {type(validated_person)}")
    except Exception as e:
        print(f"Error: {e}")

    # Example 2: Complex Pydantic model validation
    print("\n--- Complex Pydantic Model Validation ---")
    analysis_prompt = "Provide a technical analysis of REST API architecture, including key points and a confidence score between 0 and 1."

    try:
        validated_analysis = ibm_structured_client.generate(
            analysis_prompt,
            schema=TechnicalAnalysis,
            retries=3,
            generation_args=GenerationArgs(temperature=0.3, max_tokens=300),
        )
        print(f"Prompt: {analysis_prompt}")
        print(f"Response (TechnicalAnalysis): {validated_analysis}")
        print(f"Type: {type(validated_analysis)}")
    except Exception as e:
        print(f"Error: {e}")

    # Example 3: JSON Schema validation
    print("\n--- JSON Schema Validation ---")
    json_schema = {
        "type": "object",
        "properties": {
            "task": {"type": "string"},
            "priority": {"type": "string", "enum": ["high", "medium", "low"]},
            "estimated_hours": {"type": "number"},
        },
        "required": ["task", "priority"],
    }

    task_prompt = "Create a task to implement a caching layer with high priority and estimate 8 hours."

    try:
        validated_task = ibm_structured_client.generate(
            task_prompt,
            schema=json_schema,
            retries=3,
            generation_args=GenerationArgs(temperature=0.1, max_tokens=100),
        )
        print(f"Prompt: {task_prompt}")
        print(f"Response (JSON Schema): {validated_task}")
    except Exception as e:
        print(f"Error: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# 6. Batch generation examples
# ──────────────────────────────────────────────────────────────────────────────


def demo_batch_generation():
    """Demonstrate batch generation with and without validation"""
    print("\n" + "=" * 60)
    print("BATCH GENERATION EXAMPLES")
    print("=" * 60)

    # Batch without validation using loop
    print("\n--- Batch Generation (No Validation) ---")
    batch_prompts = [
        "What is Kubernetes in one sentence?",
        "Explain Docker containers in one sentence.",
        "What is continuous integration in one sentence?",
    ]

    try:
        batch_responses = []
        for prompt in batch_prompts:
            response = ibm_client.generate(
                prompt, generation_args=GenerationArgs(max_tokens=100, temperature=0.5)
            )
            batch_responses.append(response)

        for prompt, response in zip(batch_prompts, batch_responses):
            print(f"\nPrompt: {prompt}")
            print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")

    # Batch with validation using loop
    print("\n--- Batch Generation (With Validation) ---")
    batch_person_prompts = [
        "Create a profile for a DevOps engineer named Bob, age 28.",
        "Create a profile for a data scientist named Carol, age 35, working in analytics.",
        "Create a profile for a project manager named Dave, age 40.",
    ]

    try:
        validated_batch = []
        for prompt in batch_person_prompts:
            person = ibm_structured_client.generate(
                prompt,
                schema=Person,
                retries=3,
                generation_args=GenerationArgs(temperature=0.1, max_tokens=100),
            )
            validated_batch.append(person)

        for prompt, person in zip(batch_person_prompts, validated_batch):
            print(f"\nPrompt: {prompt}")
            print(f"Response: {person}")
    except Exception as e:
        print(f"Error: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# 7. Async generation examples
# ──────────────────────────────────────────────────────────────────────────────


async def demo_async_generation():
    """Demonstrate asynchronous generation"""
    print("\n" + "=" * 60)
    print("ASYNC GENERATION EXAMPLES")
    print("=" * 60)

    # Async without validation
    print("\n--- Async Generation (No Validation) ---")
    async_prompt = "Explain the benefits of event-driven architecture."

    try:
        async_response = await ibm_client.generate_async(
            async_prompt,
            generation_args=GenerationArgs(max_tokens=150, temperature=0.7),
        )
        print(f"Prompt: {async_prompt}")
        print(f"Response: {async_response}")
    except Exception as e:
        print(f"Error: {e}")

    # Async with validation
    print("\n--- Async Generation (With Validation) ---")
    async_person_prompt = (
        "Generate a profile for a security engineer named Eve, age 32."
    )

    try:
        validated_async_person = await ibm_structured_client.generate_async(
            async_person_prompt,
            schema=Person,
            retries=3,
            generation_args=GenerationArgs(temperature=0.1, max_tokens=100),
        )
        print(f"Prompt: {async_person_prompt}")
        print(f"Response: {validated_async_person}")
    except Exception as e:
        print(f"Error: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# 8. Main execution
# ──────────────────────────────────────────────────────────────────────────────


def main():
    """Run all demo functions"""
    print("\n🚀 IBM LITELLM CLIENT EXAMPLES")
    print("=" * 60)

    # Run synchronous examples
    demo_basic_generation()
    demo_tool_calling()
    demo_output_validation()
    demo_batch_generation()

    # Run async examples
    print("\n🔄 Running async examples...")
    asyncio.run(demo_async_generation())

    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
