from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)

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

    async def process(self, text: str, intent: str, entities: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process the input or pass it to the next agent in the chain."""
        if self.can_handle(intent, entities):
            return await self.handle(text, intent, entities)
        
        if self.next_agent is not None:
            return await self.next_agent.process(text, intent, entities)
            
        return None
