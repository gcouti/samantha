"""General purpose agent powered by LLM for handling various requests."""
from typing import Dict, Any
import logging
import json

from .base_agent import BaseAgent

# Imports de mensagens e prompts agora vêm do 'langchain_core'
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

class GeneralAgent(BaseAgent):
    """
    General purpose agent that uses LLM for intelligent responses. This agent is 
    used as a catch-all for any request.
    """
    
    def __init__(self, provider):
        super().__init__(
            name="general_agent",
            description="General purpose agent for various requests"
        )
        self.provider = provider
    
    def can_handle(self, intent: str, entities: Dict[str, Any]) -> bool:
        """Handle any intent that doesn't have a specific agent."""
        # This agent acts as a catch-all for any request
        return True
    
    async def handle(self, text: str, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Process request using LLM for intelligent response generation."""
        try:
            system_message = f"""
                Você faz parte de uma equipe de assistentes pessoais, são os melhor. Seu papel na equipe é ser o mais generalista, você é 
                a principal agente que consegue responder perguntas que outros não respondem. Você vai precisar responder perguntas de 
                conhecimento gerais além de fazer a conversação fluir sempre sendo cordial e prezando a resposta correta.
                Você pode e deve falar se não tem muita certeza sobre a resposta.

                A pergunta do nosso contratante é: {text}

                Escreva a resposta no seguinte formato JSON:

                {{
                    "text": Aqui voce coloca a resposta que dará para o nosso contratante,
                    "confidence": Numero de 0 a 1 que representa o quão confiante voce esta na resposta,
                }}

                Exemplos de resposta:
                {{
                    "text": "Olá eu sou o goku",
                    "confidence": 0.95,
                }}
            """

            prompt = [
                SystemMessage(content=system_message),
                HumanMessage(content=f"{text}")
            ]

            response = self.provider.execute(prompt)
            return self._parse_json_response(response.content)
                        
        except Exception as e:
            logger.error(f"Error in general agent: {str(e)}")
            return {
                "response": "Desculpe, estou com dificuldade para processar sua solicitação. Poderia reformular?",
                "confidence": 1,
                "error": str(e),
                "agent": "general_agent",
                "metadata": {
                    "intent": intent,
                    "entities": entities
                }
            }
