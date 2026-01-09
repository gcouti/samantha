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
            description="General purpose agent, if there are no other agent, this one will help to make a generic response"
        )
        self.provider = provider
    
    def can_handle(self, state: AgentState) -> bool:
        """Handle any intent that doesn't have a specific agent."""
        # This agent acts as a catch-all for any request
        return True
    
    async def handle(self, state: AgentState) -> Dict[str, Any]:
        """Generate response or tool calls using the general agent."""
        
        try:
            system_message = """
                Você faz parte de um conjunto de agentes que trabalham para responder às perguntas dos usuários. 
                Temos agentes com vários objetivos, e o seu é ser mais generalista, muitas vezes não teremos todas 
                as ferramentas necessárias para as respostas, e você é o responsável por cobrir essa lacuna. Por isso, 
                tente responder ao máximo as informações, mesmo que não tenha todas as ferramentas necessárias. Caso 
                precise de mais informações realize perguntas para completar a tarefa
            """
            messages = state["messages"] + [SystemMessage(content=system_message)]
            
            # The agent is the LLM with tools bound to it
            response = await self.provider.client.ainvoke(messages)

            # Return only the delta for messages
            return {"messages": response}
            
        except Exception as e:
            logger.error(f"Error in general agent: {str(e)}")
            return {
                "response": SystemMessage(content=f"Error in GeneralAgent: {str(e)}")
            }