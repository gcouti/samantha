import json
import logging
import operator

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """State for the LangGraph workflow."""

    text: str  # Main utterance from user
    next: str  # next agent to be call
    response: str  # final response from agent

    messages: Annotated[List[BaseMessage], add_messages]

    name: Optional[str]  # user name
    user_email: Optional[str]
    notes_path: Optional[str]
    is_authenticated: bool

    metadata: Dict[str, Any]
    entities: Dict[str, Any]


class BaseAgent(ABC):
    """Base class for all agents in the multi-agent system."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        
    @abstractmethod
    def can_handle(self, state: AgentState) -> bool:
        """Determine if this agent can handle the given intent and entities."""
        pass
    
    @abstractmethod
    async def handle(self, state: AgentState) -> Dict[str, Any]:
        """Process the input and return a response."""
        pass

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON content from LLM response, handling markdown code blocks."""
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        
        try:                                
            return json.loads(content)

        except json.JSONDecodeError as json_error:
            logger.error(f"JSON decode error: {str(json_error)}")
            logger.error(f"Content that failed to parse: {content}")
            return {
                "success": False,
                "error": f"Resposta inválida do modelo: {str(json_error)}"
            }

    async def process(self, state: AgentState) -> Optional[Dict[str, Any]]:
        """Process the input or pass it to the next agent in the chain."""
        if self.can_handle(state):
            return await self.handle(state)
                 
        return None
