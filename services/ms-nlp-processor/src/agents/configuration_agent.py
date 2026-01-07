"""
Configuration Agent module
"""
from typing import Dict, Any
from llm_providers import BaseLLMProvider
from agents.base_agent import BaseAgent, AgentState
from langchain_core.messages import SystemMessage

class ConfigurationAgent(BaseAgent):
    """Agent to manage system configurations."""

    def __init__(self, provider: BaseLLMProvider):
        super().__init__(
            name="configuration_agent",
            description="Agent to manage system configurations"
        )
        self.provider = provider
    
    def can_handle(self, intent: str, entities: Dict[str, Any]) -> bool:
        """Handle any intent that doesn't have a specific agent."""
        # This agent acts as a catch-all for any request
        return True

    async def node(self, state: AgentState) -> AgentState:
        """Generate response or tool calls using the general agent."""
        messages = state["messages"]
        
        # The agent is the LLM with tools bound to it
        response = await self.provider.ainvoke(messages)

        if response.tool_calls:
            for tool_call in response.tool_calls:
                # Parameters are in tool_call['args']
                if not all(tool_call['args'].values()):
                    missing_params = [k for k, v in tool_call['args'].items() if not v]
                    response.content = f"Para usar a ferramenta '{tool_call['name']}', preciso das seguintes informações: {', '.join(missing_params)}. Por favor, forneça os detalhes que faltam."
                    # Clear tool_calls to prevent execution
                    response.tool_calls = [] 
                    break
        
        # Return only the delta for messages
        return {"messages": [response]}
    
    async def handle(self, messages: list) -> Any:
        """Invoke the LLM provider with the given messages."""
        try:
            # The provider is the LLM with tools bound to it from LangGraphManager
            response = await self.provider.ainvoke(messages)
            return response
        except Exception as e:
            logger.error(f"Error in general agent: {str(e)}")
            # Return a message that can be added to the graph state
            return SystemMessage(content=f"Error in general agent: {str(e)}")

    async def process(self, text: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the text and state to manage configurations."""
        if not state.get("notes_path"):
            # If notes_path is not set, ask the user for it.
            return {
                "response": "I need to know the path to your notes repository. Please provide it.",
                "next_step": "await_user_input_for_notes_path"
            }

        # In the future, this agent can be expanded to handle other configurations.
        return {
            "response": "Configuration is already set.",
            "next_step": "continue"
        }
