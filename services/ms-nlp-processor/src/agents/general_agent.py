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
            system_message = """
                Você é um assistente pessoal, que tem uma equipe de agentes prontos para ajuda-lo. A seguinte lista de agentes:

                - General Agent: Agente gerais, ele pode responder perguntas gerais que não são coberta pelos demais agentes.
                - Weather Agent: Agente de clima, ele pode responder perguntas sobre clima, temperatura local etc. 
                - Task Agent: Agente de tarefas, ele pode responder perguntas sobre tarefas, ser cordial com o nosso contratante e também é responsável por garantir a resposta correta.
                - Tool Agent: Agente de ferramentas, ele pode responder perguntas sobre ferramentas, ser cordial com o nosso contratante e também é responsável por garantir a resposta correta.
                - WebSearch Agent: Agente de busca na web, ele pode responder perguntas sobre busca na web, ser cordial com o nosso contratante e também é responsável por garantir a resposta correta.

                Dependendo da pergunta realizada pelo nosso contratante, selecione qual o melhor modelo que faça mais sentido para resolver 
                o problema.
                """

                # agente para verificar se a resposta final é correta
                # agente para verificar se a resposta precisa ser atualziada, se é uma pergunta que leva em consideração o tempo
                # agente para verificar se precisa de mais informações para completar a resposta

            system_message = f"""
                Você faz parte de uma equipe de agentes, cada um com uma especialidade. Sua especialidade é ser mais generalista, você é 
                a principal agente que consegue responder perguntas que outros não respondem. Você vai precisar responder perguntas de 
                conhecimento gerais além de fazer a conversação fluir ser cordial com o nosso contratante e também é responsável por 
                garantir a resposta correta. Você pode e deve falar se não tem muita certeza sobre a resposta.

                A pergunta do contratante é: {text}

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
            content = response.content

            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            try:                                
                return json.loads(content)

            except json.JSONDecodeError as json_error:
                logger.error(f"JSON decode error: {str(json_error)}")
                logger.error(f"Content that failed to parse: {content}")
                logger.error(f"Full response: {response}")
                return {
                    "success": False,
                    "error": f"Resposta inválida do modelo: {str(json_error)}"
                }
                        
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
