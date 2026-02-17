"""
Unit Tests for LLM Clients

Tests the LLM client wrappers for OpenAI, Gemini, and Anthropic.
"""

import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from prometheus_lib.llm.clients import (
    BaseLLMClient,
    OpenAIClient,
    GeminiClient,
    AnthropicClient,
    OllamaClient,
    LLMResponse,
    get_client,
    is_ollama_model,
)


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_response_creation(self):
        """Test creating an LLM response."""
        response = LLMResponse(
            content="Test content",
            model="gpt-4",
            input_tokens=100,
            output_tokens=50
        )

        assert response.content == "Test content"
        assert response.model == "gpt-4"
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.finish_reason == "stop"

    def test_response_with_raw_response(self):
        """Test response with raw response attached."""
        raw = {"id": "test-123"}
        response = LLMResponse(
            content="Test",
            model="gpt-4",
            input_tokens=10,
            output_tokens=5,
            raw_response=raw
        )

        assert response.raw_response == raw


class TestOpenAIClient:
    """Tests for OpenAI client."""

    def test_initialization(self):
        """Test client initialization."""
        client = OpenAIClient("gpt-4o-mini")
        assert client.model_name == "gpt-4o-mini"
        assert not client._initialized

    def test_token_estimation(self):
        """Test token estimation (uses tiktoken when available, else heuristic)."""
        client = OpenAIClient("gpt-4o-mini")
        text = "This is a test string with some words"
        tokens = client.estimate_tokens(text)
        # tiktoken returns ~11 for this string; heuristic returns ~11 (len/3.3)
        assert tokens > 0
        assert tokens <= len(text)  # tokens should not exceed char count

    @pytest.mark.asyncio
    async def test_raises_without_api_key(self):
        """Test that client raises RuntimeError without API key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=True):
            client = OpenAIClient("gpt-4o-mini")
            client.api_key = None

            with pytest.raises(RuntimeError, match="OPENAI_API_KEY not set"):
                await client.generate("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self):
        """Test generation with system prompt."""
        client = OpenAIClient("gpt-4o-mini")
        client.api_key = None  # No key set

        with pytest.raises(RuntimeError, match="OPENAI_API_KEY not set"):
            await client.generate(
                "User prompt",
                system_prompt="You are a helpful assistant."
            )


class TestGeminiClient:
    """Tests for Gemini client."""

    def test_initialization(self):
        """Test client initialization."""
        client = GeminiClient("gemini-2.0-flash")
        assert client.model_name == "gemini-2.0-flash"

    @pytest.mark.asyncio
    async def test_mock_response_without_api_key(self):
        """Test mock response when API key not set."""
        client = GeminiClient("gemini-2.0-flash")
        client.api_key = None

        response = await client.generate("Test prompt")

        assert isinstance(response, LLMResponse)
        assert "Mock Gemini" in response.content


class TestAnthropicClient:
    """Tests for Anthropic client."""

    def test_initialization(self):
        """Test client initialization."""
        client = AnthropicClient("claude-3-5-sonnet-20241022")
        assert client.model_name == "claude-3-5-sonnet-20241022"

    @pytest.mark.asyncio
    async def test_raises_without_api_key(self):
        """Test that client raises RuntimeError without API key."""
        client = AnthropicClient()
        client.api_key = None

        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY not set"):
            await client.generate("Test prompt")


class TestGetClient:
    """Tests for client factory function."""

    def test_get_openai_client(self):
        """Test getting OpenAI client."""
        client = get_client("gpt-4o-mini")
        assert isinstance(client, OpenAIClient)

    def test_get_gemini_client(self):
        """Test getting Gemini client."""
        client = get_client("gemini-2.0-flash")
        assert isinstance(client, GeminiClient)

    def test_get_anthropic_client(self):
        """Test getting Anthropic client."""
        client = get_client("claude-3-5-sonnet")
        assert isinstance(client, AnthropicClient)

    def test_unknown_model_defaults_to_ollama(self):
        """Test that unknown model defaults to local Ollama."""
        client = get_client("unknown-model")
        assert isinstance(client, OllamaClient)

    def test_get_ollama_client(self):
        """Test getting Ollama client for local models."""
        client = get_client("qwen2.5:7b")
        assert isinstance(client, OllamaClient)
        assert client.model_name == "qwen2.5:7b"

    def test_is_ollama_model(self):
        """Test ollama model detection."""
        assert is_ollama_model("qwen2.5:7b")
        assert is_ollama_model("llama3.2")
        assert is_ollama_model("mistral:7b")
        assert not is_ollama_model("gpt-4o-mini")
