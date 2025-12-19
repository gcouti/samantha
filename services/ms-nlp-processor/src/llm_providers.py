"""
Strategy Pattern for different AI providers Supports OpenAI, Gemini, Claude and other AI APIs.
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from langchain_core.messages import BaseMessage
from enum import Enum

from dotenv import load_dotenv

# Try to import different LLM providers
try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from langchain_anthropic import ChatAnthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

load_dotenv()

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    """Enumeration of supported LLM providers."""
    OPENAI = "openai"
    GEMINI = "gemini"
    CLAUDE = "claude"

class LLMConfig:
    """Configuration for LLM providers."""
    
    def __init__(self, provider: LLMProvider, model: str = None, **kwargs):
        self.provider = provider
        self.model = model or self._get_default_model(provider)
        self.temperature = kwargs.get("temperature", 0.7)
        self.max_tokens = kwargs.get("max_tokens", 2048)
        self.api_key = self._get_api_key(provider)
        self.extra_params = kwargs
    
    def _get_default_model(self, provider: LLMProvider) -> str:
        """Get default model for provider."""
        defaults = {
            LLMProvider.OPENAI: "gpt-3.5-turbo",
            LLMProvider.GEMINI: "gemini-2.0-flash",
            LLMProvider.CLAUDE: "claude-3-sonnet-20240229"
        }
        return defaults.get(provider, "unknown")
    
    def _get_api_key(self, provider: LLMProvider) -> Optional[str]:
        """Get API key for provider."""
        keys = {
            LLMProvider.OPENAI: os.getenv("OPENAI_API_KEY"),
            LLMProvider.GEMINI: os.getenv("GEMINI_API_KEY"),
            LLMProvider.CLAUDE: os.getenv("CLAUDE_API_KEY")
        }
        return keys.get(provider)

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = self._initialize_client()
    
    def execute(self, messages: List[BaseMessage]):
        return self.client.invoke(messages)

    @abstractmethod
    def _initialize_client(self):
        """Initialize the LLM client."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass

class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider implementation."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
    
    def _initialize_client(self):
        """Initialize OpenAI client."""
        if not OPENAI_AVAILABLE:
            raise ImportError("langchain-openai not installed")
        
        return ChatOpenAI(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            openai_api_key=self.config.api_key
        )
    
    
    def is_available(self) -> bool:
        """Check if OpenAI is available."""
        return OPENAI_AVAILABLE and bool(self.config.api_key)

class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider implementation."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
    
    def _initialize_client(self):
        """Initialize Gemini client."""
        if not GEMINI_AVAILABLE:
            raise ImportError("langchain-google-genai not installed")
        
        return ChatGoogleGenerativeAI(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            google_api_key=self.config.api_key
        )
    
    def is_available(self) -> bool:
        """Check if Gemini is available."""
        return GEMINI_AVAILABLE and bool(self.config.api_key)

class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude provider implementation."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
    
    def _initialize_client(self):
        """Initialize Claude client."""
        if not CLAUDE_AVAILABLE:
            raise ImportError("langchain-anthropic not installed")
        
        return ChatAnthropic(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            anthropic_api_key=self.config.api_key
        )
    
    def is_available(self) -> bool:
        """Check if Claude is available."""
        return CLAUDE_AVAILABLE and bool(self.config.api_key)

class LLMProviderFactory:
    """Factory for creating LLM providers."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)

    @staticmethod
    def create_provider(config: LLMConfig) -> BaseLLMProvider:
        """Create LLM provider based on configuration."""
        providers = {
            LLMProvider.OPENAI: OpenAIProvider,
            LLMProvider.GEMINI: GeminiProvider,
            LLMProvider.CLAUDE: ClaudeProvider
        }
        
        provider_class = providers.get(config.provider)
        if not provider_class:
            raise ValueError(f"Unsupported provider: {config.provider}")
        
        return provider_class(config)
    
    @staticmethod
    def get_available_providers() -> List[LLMProvider]:
        """Get list of available providers."""
        available = []
        
        if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            available.append(LLMProvider.OPENAI)
        
        if GEMINI_AVAILABLE and os.getenv("GEMINI_API_KEY"):
            available.append(LLMProvider.GEMINI)
        
        if CLAUDE_AVAILABLE and os.getenv("CLAUDE_API_KEY"):
            available.append(LLMProvider.CLAUDE)
        
        return available