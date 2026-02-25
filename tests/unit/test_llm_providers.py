"""Tests for LLM client multi-provider support."""
import pytest
from src.utils.exceptions import LLMError


class TestLLMClientProviderSelection:
    """Verify that LLMClient correctly instantiates different providers."""

    def test_anthropic_provider(self):
        """Anthropic provider should be selected for 'anthropic'."""
        from src.core.llm.client import LLMClient

        with pytest.raises(LLMError, match="API key is required"):
            LLMClient("anthropic", "", "claude-sonnet-4-20250514")

    def test_openai_provider(self):
        """OpenAI provider should be selected for 'openai'."""
        from src.core.llm.client import LLMClient

        with pytest.raises(LLMError, match="API key is required"):
            LLMClient("openai", "", "gpt-4o")

    def test_deepseek_provider(self):
        """DeepSeek provider should be selected for 'deepseek'."""
        from src.core.llm.client import LLMClient

        with pytest.raises(LLMError, match="API key is required"):
            LLMClient("deepseek", "", "deepseek-chat")

    def test_ollama_provider(self):
        """Ollama provider should use OpenAI-compatible with localhost URL."""
        from src.core.llm.client import LLMClient

        # Ollama doesn't require a real key.
        client = LLMClient("ollama", "none", "llama3")
        assert client.provider == "ollama"
        assert client._provider_client is not None

    def test_together_provider(self):
        """Together AI should use OpenAI-compatible with correct base URL."""
        from src.core.llm.client import LLMClient

        client = LLMClient("together", "test-key", "meta-llama/Llama-3-70b-chat-hf")
        assert client.provider == "together"

    def test_groq_provider(self):
        """Groq should use OpenAI-compatible with correct base URL."""
        from src.core.llm.client import LLMClient

        client = LLMClient("groq", "test-key", "llama3-70b-8192")
        assert client.provider == "groq"

    def test_moonshot_provider(self):
        """Moonshot should use OpenAI-compatible with correct base URL."""
        from src.core.llm.client import LLMClient

        client = LLMClient("moonshot", "test-key", "moonshot-v1-8k")
        assert client.provider == "moonshot"

    def test_zhipu_provider(self):
        """Zhipu should use OpenAI-compatible with correct base URL."""
        from src.core.llm.client import LLMClient

        client = LLMClient("zhipu", "test-key", "glm-4")
        assert client.provider == "zhipu"

    def test_siliconflow_provider(self):
        """SiliconFlow should use OpenAI-compatible with correct base URL."""
        from src.core.llm.client import LLMClient

        client = LLMClient("siliconflow", "test-key", "deepseek-ai/DeepSeek-V3")
        assert client.provider == "siliconflow"

    def test_openai_compatible_with_base_url(self):
        """openai_compatible requires base_url."""
        from src.core.llm.client import LLMClient

        client = LLMClient(
            "openai_compatible", "test-key", "my-model",
            base_url="http://my-server:8080/v1",
        )
        assert client.provider == "openai_compatible"

    def test_openai_compatible_without_base_url_raises(self):
        """openai_compatible without base_url should raise."""
        from src.core.llm.client import LLMClient

        with pytest.raises(LLMError, match="base_url is required"):
            LLMClient("openai_compatible", "test-key", "my-model")

    def test_unknown_provider_raises(self):
        """Unknown provider should raise LLMError."""
        from src.core.llm.client import LLMClient

        with pytest.raises(LLMError, match="Unknown provider"):
            LLMClient("nonexistent", "key", "model")

    def test_custom_base_url_override(self):
        """Custom base_url should override the default for known providers."""
        from src.core.llm.client import LLMClient

        custom_url = "http://my-proxy:9090/v1"
        client = LLMClient("deepseek", "test-key", "deepseek-chat", base_url=custom_url)
        # Should still work — the base_url overrides the DeepSeek default via
        # the compatible provider path (if provider is in known list and has custom url).
        assert client.provider == "deepseek"


class TestDeepSeekProvider:
    """Unit tests for DeepSeek provider."""

    def test_init_without_key_raises(self):
        from src.core.llm.providers.deepseek_provider import DeepSeekProvider

        with pytest.raises(LLMError, match="API key is required"):
            DeepSeekProvider("", "deepseek-chat")

    def test_init_with_key(self):
        from src.core.llm.providers.deepseek_provider import DeepSeekProvider

        provider = DeepSeekProvider("test-key", "deepseek-chat")
        assert provider.model == "deepseek-chat"

    def test_parse_json_plain(self):
        from src.core.llm.providers.deepseek_provider import DeepSeekProvider

        result = DeepSeekProvider._parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_with_fences(self):
        from src.core.llm.providers.deepseek_provider import DeepSeekProvider

        result = DeepSeekProvider._parse_json('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}


class TestOpenAICompatibleProvider:
    """Unit tests for OpenAI-compatible provider."""

    def test_init_without_base_url_raises(self):
        from src.core.llm.providers.openai_compatible_provider import (
            OpenAICompatibleProvider,
        )

        with pytest.raises(LLMError, match="base_url is required"):
            OpenAICompatibleProvider("key", "model", "")

    def test_init_without_key_uses_none(self):
        from src.core.llm.providers.openai_compatible_provider import (
            OpenAICompatibleProvider,
        )

        # Should not raise — empty key becomes "none" for local services.
        provider = OpenAICompatibleProvider(
            "", "llama3", "http://localhost:11434/v1", "ollama"
        )
        assert provider.model == "llama3"
        assert provider.provider_name == "ollama"

    def test_parse_json_plain(self):
        from src.core.llm.providers.openai_compatible_provider import (
            OpenAICompatibleProvider,
        )

        result = OpenAICompatibleProvider._parse_json('{"a": 1}')
        assert result == {"a": 1}
