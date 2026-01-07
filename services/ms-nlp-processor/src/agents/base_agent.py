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

    text: str  # mantém histórico de textos

    messages: Annotated[List[BaseMessage], add_messages]

    user_email: Optional[str]
    is_authenticated: bool
    notes_path: Optional[str]

    metadata: Dict[str, Any]
    entities: Dict[str, Any]
    
    response: Annotated[List[BaseMessage], add_messages]


class BaseAgent(ABC):
    """Base class for all agents in the multi-agent system."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.next_agent = None
    
    def set_next(self, agent: 'BaseAgent') -> 'BaseAgent':
        """Set the next agent in the chain."""
        self.next_agent = agent
        return agent
    
    @abstractmethod
    def can_handle(self, intent: str, entities: Dict[str, Any]) -> bool:
        """Determine if this agent can handle the given intent and entities."""
        pass
    
    @abstractmethod
    async def handle(self, text: str, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Process the input and return a response."""
        pass

    @abstractmethod
    async def node(self, state: AgentState) -> AgentState:
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

    def _describe_tool_call(self, tool_call: Any) -> str:
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

    def _ensure_message_content(self, response: Any) -> None:
        """Guarantee that a response object includes textual content."""
        if getattr(response, "content", None):
            return

        tool_calls = getattr(response, "tool_calls", None)
        if tool_calls:
            descriptions = ", ".join(
                self._describe_tool_call(call) for call in tool_calls
            )
            response.content = f"Sinalizando chamada de ferramenta -> {descriptions}"
        else:
            response.content = "Sem conteúdo fornecido pelo modelo."

    async def process(self, text: str, intent: str, entities: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process the input or pass it to the next agent in the chain."""
        if self.can_handle(intent, entities):
            return await self.handle(text, intent, entities)
        
        if self.next_agent is not None:
            return await self.next_agent.process(text, intent, entities)
            
        return None
