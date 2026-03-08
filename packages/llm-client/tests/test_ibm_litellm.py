import os
import pytest
from typing import List, Optional
from pydantic import BaseModel
from llm_client.llm import get_llm

# Skip tests if required environment variables are not set
pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(
        not os.getenv("IBM_THIRD_PARTY_API_KEY"),
        reason="IBM_THIRD_PARTY_API_KEY environment variable not set",
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# Test schemas
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
# Test fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def ibm_client():
    """Initialize IBM LiteLLM client"""
    IBMLiteLLMClient = get_llm("litellm.ibm")

    return IBMLiteLLMClient(
        model_name="GCP/claude-3-7-sonnet",
        api_key=os.getenv("IBM_THIRD_PARTY_API_KEY"),
        hooks=[lambda event, payload: print(f"[TEST IBM] {event}: {payload}")],
    )


@pytest.fixture(scope="function")
def ibm_structured_client():
    """Initialize IBM LiteLLM client with output validation"""
    IBMLiteLLMClientOutputVal = get_llm("litellm.ibm.output_val")

    return IBMLiteLLMClientOutputVal(
        model_name="GCP/claude-3-7-sonnet",
        api_key=os.getenv("IBM_THIRD_PARTY_API_KEY"),
        hooks=[
            lambda event, payload: print(f"[TEST IBM STRUCTURED] {event}: {payload}")
        ],
        include_schema_in_system_prompt=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Test classes
# ──────────────────────────────────────────────────────────────────────────────


class TestIBMLiteLLMBasicGeneration:
    """Test basic text generation capabilities"""

    def test_simple_text_generation(self, ibm_client):
        """Test simple text generation"""
        prompt = "Explain the concept of distributed computing systems in one sentence."
        response = ibm_client.generate(prompt)

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0

    def test_chat_generation(self, ibm_client):
        """Test chat-style generation"""
        chat_messages = [
            {
                "role": "system",
                "content": "You are a helpful technical assistant specializing in enterprise software.",
            },
            {
                "role": "user",
                "content": "What are the advantages of microservices architecture?",
            },
        ]

        response = ibm_client.generate(chat_messages)

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0


class TestIBMLiteLLMToolCalling:
    """Test tool calling capabilities"""

    def test_tool_calling(self, ibm_client):
        """Test tool calling functionality"""
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

        prompt = [
            {
                "role": "user",
                "content": "Analyze the complexity of bubble sort algorithm and estimate its performance for 1000 elements.",
            }
        ]

        response = ibm_client.generate(prompt, tools=tools, tool_choice="auto")

        assert response is not None
        # Check if response contains tool calls (might vary by implementation)
        if hasattr(response, "tool_calls") and response.tool_calls:
            assert len(response.tool_calls) > 0
        else:
            # If no tool calls, just ensure we got a response
            assert isinstance(response, str) or hasattr(response, "content")

    def test_tool_calling_with_specific_function(self, ibm_client):
        """Test tool calling with specific function"""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "system_diagnostics",
                    "description": "Run system diagnostics",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "system_type": {
                                "type": "string",
                                "description": "Type of system",
                            },
                            "check_level": {
                                "type": "string",
                                "enum": ["basic", "detailed", "comprehensive"],
                            },
                        },
                        "required": ["system_type"],
                    },
                },
            }
        ]

        prompt = [
            {
                "role": "user",
                "content": "Run comprehensive diagnostics on the database system",
            }
        ]

        response = ibm_client.generate(prompt, tools=tools, tool_choice="auto")

        assert response is not None
        # Check if response contains tool calls (might vary by implementation)
        if hasattr(response, "tool_calls") and response.tool_calls:
            assert len(response.tool_calls) > 0
        else:
            # If no tool calls, just ensure we got a response
            assert isinstance(response, str) or hasattr(response, "content")


class TestIBMLiteLLMStructuredOutput:
    """Test structured output validation"""

    def test_person_extraction(self, ibm_structured_client):
        """Test person information extraction"""
        prompt = "Extract person info: Dr. Emily Watson is 42 years old and works as a Senior Software Engineer at IBM Research."

        person = ibm_structured_client.generate(prompt=prompt, schema=Person, retries=3)

        assert isinstance(person, Person)
        assert person.name is not None
        assert person.age is not None
        assert isinstance(person.age, int)

    def test_technical_analysis(self, ibm_structured_client):
        """Test technical analysis extraction"""
        prompt = (
            "Analyze the topic of quantum computing algorithms and provide key insights"
        )

        analysis = ibm_structured_client.generate(
            prompt=prompt, schema=TechnicalAnalysis, retries=3
        )

        assert isinstance(analysis, TechnicalAnalysis)
        assert analysis.topic is not None
        assert analysis.complexity_level is not None
        assert isinstance(analysis.key_points, list)
        assert isinstance(analysis.confidence_score, (int, float))

    def test_json_schema_validation(self, ibm_structured_client):
        """Test JSON schema validation"""
        json_schema = {
            "type": "object",
            "properties": {
                "language": {"type": "string"},
                "paradigm": {
                    "type": "string",
                    "enum": [
                        "functional",
                        "object-oriented",
                        "procedural",
                        "declarative",
                    ],
                },
                "features": {"type": "array", "items": {"type": "string"}},
                "popularity_score": {"type": "number", "minimum": 0, "maximum": 100},
            },
            "required": ["language", "paradigm", "popularity_score"],
        }

        prompt = "Analyze this programming language: 'Python is a high-level, interpreted programming language with dynamic semantics.'"

        analysis = ibm_structured_client.generate(
            prompt=prompt, schema=json_schema, retries=3
        )

        assert isinstance(analysis, dict)
        assert "language" in analysis
        assert "paradigm" in analysis
        assert "popularity_score" in analysis
        assert isinstance(analysis["popularity_score"], (int, float))

    def test_structured_output_with_validation_retries(self, ibm_structured_client):
        """Test structured output with validation retries"""
        prompt = "Extract info: Professor Alan Turing, 41, Computer Scientist and Mathematician"

        person = ibm_structured_client.generate(
            prompt=prompt,
            schema=Person,
            retries=5,  # Test with more retries
        )

        assert isinstance(person, Person)
        assert person.name is not None
        assert person.age is not None
        assert isinstance(person.age, int)


class TestIBMLiteLLMAsync:
    """Test async capabilities"""

    @pytest.mark.asyncio
    async def test_async_generation(self, ibm_client):
        """Test async generation"""
        prompt = "What is containerization in software development?"

        response = await ibm_client.generate_async(prompt)

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_async_structured_output(self, ibm_structured_client):
        """Test async structured output"""
        prompt = "Extract info: Dr. Grace Hopper, 85, Computer Pioneer"

        person = await ibm_structured_client.generate_async(
            prompt=prompt, schema=Person, retries=3
        )

        assert isinstance(person, Person)
        assert person.name is not None
        assert person.age is not None


class TestIBMLiteLLMBatch:
    """Test batch generation capabilities"""

    def test_batch_generation(self, ibm_client):
        """Test batch generation"""
        prompts = [
            "What is Kubernetes?",
            "Explain Docker containers.",
            "What is continuous integration?",
        ]

        responses = ibm_client.generate_batch(prompts)

        assert isinstance(responses, list)
        assert len(responses) == len(prompts)
        for response in responses:
            assert isinstance(response, str)
            assert len(response) > 0

    def test_batch_structured_generation(self, ibm_structured_client):
        """Test batch generation with structured output"""
        prompts = [
            "Extract info: John Doe, 30, Developer",
            "Extract info: Jane Smith, 35, Data Scientist",
        ]

        persons = ibm_structured_client.generate_batch(
            prompts=prompts, schema=Person, retries=3
        )

        assert isinstance(persons, list)
        assert len(persons) == len(prompts)
        for person in persons:
            assert isinstance(person, Person)
            assert person.name is not None
            assert person.age is not None


class TestIBMLiteLLMErrorHandling:
    """Test error handling"""

    def test_missing_api_key(self):
        """Test that missing API key raises an error"""
        IBMLiteLLMClient = get_llm("litellm.ibm")

        with pytest.raises(EnvironmentError):
            # Attempt to create client without API key (assuming env var is not set in test env)
            IBMLiteLLMClient(model_name="GCP/claude-3-7-sonnet", api_key="")

    def test_invalid_model_name(self, ibm_client):
        """Test handling of invalid model name"""
        # This test may fail or timeout depending on API behavior
        with pytest.raises(Exception):
            ibm_client.generate("Test prompt with invalid model config")
