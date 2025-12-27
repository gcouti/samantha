"""General purpose agent powered by LLM for handling various requests."""
from typing import Dict, Any
import logging
import json

from .base_agent import BaseAgent

# Imports de mensagens e prompts agora vêm do 'langchain_core'
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

class OrchestratorAgent(BaseAgent):
    """
    Agent that decides wich agent will be able to respond the user uterance
    """
    
    def __init__(self, provider):
        super().__init__(
            name="orchestrator_agent",   
            description="General purpose agent for various requests"
        )
        self.provider = provider
    
    def can_handle(self, entities: Dict[str, Any]) -> bool:
        """Handle any intent that doesn't have a specific agent."""
        # This agent acts as a catch-all for any request
        return True


    async def handle(self, text: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Process request using LLM for intelligent response generation."""
        try:
            system_message = """
                Atue como um assistente pessoal para apoiar executivos nas suas tarefas diarias, o melhor secretário executivo do mundo.
                Você tem uma equipe de agentes prontos para ajuda-lo a executar suas tarefas. A seguinte lista de agentes:

                - General Agent: Agente gerais, ele pode responder perguntas gerais que não são coberta pelos demais agentes.            
                - Calendar Agent: Agente que consolida a agenda do executivo. Ele acessa ao google calendar e faz ações como 
                  agendar e cancelar reuniões, consultar e trazer tarefas e reuniões do dia. 
                - WebSearch Agent: Agente de busca na web, ele pode responder perguntas usando a internet para atualizar buscar
                  informações atualizadas. Esse agente pode ser executado após outro agente, para garantir que uma informação 
                  está atualizada

                Dependendo da pergunta realizada pelo nosso exexcutivo, selecione qual o melhor agente que faça mais sentido para resolver 
                a questão demandada. 

                Selecione um dos seguintes agentes:
                - General Agent: general_agent
                - Calendar Agent: calendar_agent
                - WebSearch Agent: websearch_agent

                Retorne um JSON com a seguinte estrutura:
                {
                    "agent": "general_agent"
                }
                """

                # agente para verificar se a resposta final é correta
                # agente para verificar se a resposta precisa ser atualziada, se é uma pergunta que leva em consideração o tempo
                # agente para verificar se precisa de mais informações para completar a resposta

          
            prompt = [
                SystemMessage(content=system_message),
                HumanMessage(content=f"{text}")
            ]

            response = self.provider.execute(prompt)
            content = response.content

            return self._parse_json_response(content)
                        
        except Exception as e:
            logger.error(f"Error in general agent: {str(e)}")
            return {
                "response": "Desculpe, estou com dificuldade para processar sua solicitação. Poderia reformular?",
                "confidence": 1,
                "error": str(e),
                "agent": "orchestrator_agent",
                "metadata": {
                    "intent": intent,
                    "entities": entities
                }
            }
