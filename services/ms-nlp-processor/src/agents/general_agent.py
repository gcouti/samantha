"""General purpose agent powered by LLM for handling various requests."""
from typing import Dict, Any
import logging
import json

from .base_agent import BaseAgent, AgentState

# Imports de mensagens e prompts agora vêm do 'langchain_core'
from llm_providers import BaseLLMProvider
from langchain_core.messages import SystemMessage

logger = logging.getLogger(__name__)

class GeneralAgent(BaseAgent):
    """
    General purpose agent that uses LLM for intelligent responses. This agent is 
    used as a catch-all for any request.
    """
    
    def __init__(self, provider: BaseLLMProvider):
        super().__init__(
            name="general_agent",
            description="General purpose agent for various requests"
        )
        self.provider = provider
    
    def can_handle(self, intent: str, entities: Dict[str, Any]) -> bool:
        """Handle any intent that doesn't have a specific agent."""
        # This agent acts as a catch-all for any request
        return True
    
    async def handle(self, messages: list) -> Any:
        """Invoke the LLM provider with the given messages."""
        try:
            # The provider is the LLM with tools bound to it from LangGraphManager
            response = await self.provider.ainvoke(messages)
            return response
        except Exception as e:
            logger.error(f"Error in general agent: {str(e)}")
            return SystemMessage(content=f"Error in general agent: {str(e)}")

    def _describe_tool_call(self, tool_call: Dict[str, Any]) -> str:
        """Return a readable summary for a tool call entry."""
        name = getattr(tool_call, "name", None)
        if name is None and isinstance(tool_call, dict):
            name = tool_call.get("name")

        args = getattr(tool_call, "args", None)
        if args is None and isinstance(tool_call, dict):
            args = tool_call.get("args", {})

        if isinstance(args, str):
            args_preview = args
        else:
            try:
                args_preview = json.dumps(args, ensure_ascii=False)
            except (TypeError, ValueError):
                args_preview = str(args)

        return f"{name or 'tool'}: {args_preview}"

    async def node(self, state: AgentState) -> AgentState:
        """Generate response or tool calls using the general agent."""
        messages = state["messages"]
        
        # The agent is the LLM with tools bound to it
        response = await self.provider.ainvoke(messages)

        # Return only the delta for messages
        return {"response": response}