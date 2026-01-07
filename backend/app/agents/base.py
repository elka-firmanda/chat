"""Base agent class for simplified agent architecture."""

from abc import ABC, abstractmethod
from typing import Any

from app.config.schema import AgentSettings
from app.config.config_manager import ConfigManager
from app.services.llm import LLMService


class BaseAgent(ABC):
    """Abstract base class for all agents.

    Provides common functionality for LLM-based agents:
    - LLM service initialization
    - Chat methods (simple and with context)
    - System prompt access
    """

    def __init__(
        self,
        name: str,
        agent_config: AgentSettings,
        config_manager: ConfigManager,
    ):
        """Initialize the base agent.

        Args:
            name: The agent's identifier name
            agent_config: Agent-specific settings (model, tokens, prompts)
            config_manager: Global config manager for API keys
        """
        self.name = name
        self.agent_config = agent_config
        self.config_manager = config_manager
        self.llm_service = LLMService(agent_config, config_manager)

    @abstractmethod
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent's main task.

        Args:
            input_data: Input data for the agent

        Returns:
            Output data from the agent
        """
        pass

    async def chat(
        self,
        message: str,
        history: list[dict[str, Any]] | None = None,
    ) -> str:
        """Send a message to the agent and get a response.

        Uses the agent's configured system prompt.

        Args:
            message: The user message
            history: Optional conversation history

        Returns:
            The agent's response
        """
        return await self.llm_service.chat(message, history)

    async def chat_with_context(
        self,
        message: str,
        context: str,
        history: list[dict[str, Any]] | None = None,
    ) -> str:
        """Send a message with additional context.

        The context is prepended to the message in a structured format.

        Args:
            message: The user message
            context: Additional context to include
            history: Optional conversation history

        Returns:
            The agent's response
        """
        full_message = f"Context:\n{context}\n\nQuery:\n{message}"
        return await self.llm_service.chat(full_message, history)

    def get_system_prompt(self) -> str:
        """Get the agent's system prompt."""
        return self.agent_config.system_prompt

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(name={self.name})"
