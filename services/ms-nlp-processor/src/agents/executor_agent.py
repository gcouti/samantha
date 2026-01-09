"""
Configuration Agent module
"""
import logging

from typing import Dict, Any
from llm_providers import BaseLLMProvider
from agents.base_agent import BaseAgent, AgentState
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

class ExecutorAgent(BaseAgent):
    """Agent to manage system configurations."""

    AGENT_NAME = "executor_agent"

    def __init__(self, provider: BaseLLMProvider, tools: list):
        super().__init__(
            name=ExecutorAgent.AGENT_NAME,
            description=(
                "Agent to execute tools, it responsabilities is to execute tools."
                "The possible tools are: " + ", ".join([tool.description for tool in tools])
            )
        )
        self.tools = tools
        self.provider = provider
    
    def can_handle(self, intent: str, entities: Dict[str, Any]) -> bool:
        """Handle any intent that doesn't have a specific agent."""
        # This agent acts as a catch-all for any request
        return True
    
    async def handle(self, state: AgentState) -> Dict[str, Any]:
        """Invoke the LLM provider with the given messages."""
        try:

            prompt = "You have the following tools:"

            prompt += "\n\n".join([f"- {tool.name}: {tool.description.replace('\n', ' ')}" for tool in self.tools])
            
            prompt += """
                You will recieve the instructions and you need to select the tool format the parameters and execut it
            """

            filtered_messages = [
                message for message in state["messages"] if not isinstance(message, HumanMessage)
            ]

            response = await self.provider.ainvoke(filtered_messages + [SystemMessage(content=prompt)])

            return {
                "messages": response
            }

        except Exception as e:
            logger.error(f"Error in general agent: {str(e)}")
            return {
                "response": SystemMessage(content=f"System Error in ExecutorAgent: {str(e)}")
            }
