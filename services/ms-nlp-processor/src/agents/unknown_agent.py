from typing import Dict, Any
from .base_agent import BaseAgent
import random

class UnknownAgent(BaseAgent):
    """Handles any intents that other agents couldn't handle."""
    
    def __init__(self):
        super().__init__(
            name="unknown_agent",
            description="Handles any unhandled intents"
        )
        self.responses = [
            "Desculpe, não entendi completamente. Poderia reformular?",
            "Ainda estou aprendendo. Poderia explicar de outra forma?",
            "Não tenho certeza se entendi. Você poderia tentar de outra maneira?",
            "Ainda não sei responder isso, mas estou sempre aprendendo!"
        ]
    
    def can_handle(self, intent: str, entities: Dict[str, Any]) -> bool:
        # This agent should always be the last in the chain and handle anything
        return True
    
    async def handle(self, text: str, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "response": random.choice(self.responses),
            "agent": self.name,
            "confidence": 0.1
        }
