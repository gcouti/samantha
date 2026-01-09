"""General purpose agent powered by LLM for handling various requests."""
from typing import Dict, Any
import logging
import json

from .base_agent import BaseAgent, AgentState

# Imports de mensagens e prompts agora vêm do 'langchain_core'
from llm_providers import BaseLLMProvider
from langchain_core.messages import SystemMessage

logger = logging.getLogger(__name__)

class SynthesizerAgent(BaseAgent):
    """
    Agent to synthesize responses from multiple agents and write it to final user. 
    """
    
    AGENT_NAME = "synthesizer_agent"

    def __init__(self, provider: BaseLLMProvider):
        super().__init__(
            name=SynthesizerAgent.AGENT_NAME,
            description=(
                "Agent to synthesize responses multiple resposes from agents and tools "
                "and write the final answer to the user. "
                "Call it when you want to finish and alwready know what answer to the client"
            )
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
                Atue como o melhor Secretário Executivo do mundo. Você é altamente organizado, discreto, proativo, diplomaticamente assertivo e focado em resultados. Você trabalha para [SEU NOME], que atua como [SEU CARGO/PROFISSÃO]. O objetivo principal do executivo no momento é [INSERIR SEU GRANDE OBJETIVO ATUAL, EX: expandir a empresa, ter mais tempo livre, finalizar um projeto].

                Suas 5 Diretrizes de Ouro:
                
                Proteção do Tempo: Sempre questione se uma reunião é necessária. Se for, exija uma pauta. Priorize blocos de trabalho focado.
                Síntese Extrema: A não ser que seja pedido, nunca me dê textos longos. Use bullet points. Dê-me o contexto, o problema e a sugestão de solução (C-P-S).
                Tom de Voz: Profissional, conciso, mas empático.

                Comandos de Ação:

                Sempre que eu inserir dados (como uma lista de e-mails, uma agenda bagunçada ou notas soltas), você deve processar a informação seguindo a estrutura abaixo:

                🔴 Urgente/Crítico: O que vai explodir se eu não olhar agora.
                📅 Agenda Otimizada: Sugestão de como organizar o dia/semana.
                📝 Tarefas Prontas: Rascunhos de e-mails ou mensagens para eu apenas copiar e enviar.
                💡 Insight Proativo: Uma sugestão extra que você notou (ex: "Vi que você tem 3 reuniões seguidas, sugiro mover a do meio para amanhã").

                Selecione do conjunto de mensanges o que faz sentido para responder as dúvidas do nosso cliente
            """
            messages = state["messages"] + [SystemMessage(content=system_message)]
            
            # The agent is the LLM with tools bound to it
            response = await self.provider.client.ainvoke(messages)

            # Return only the delta for messages
            return {
                "messages": response,
                "response": response
            }
            
        except Exception as e:
            logger.error(f"Error in sythesizer agent: {str(e)}")
            return {
                "response": SystemMessage(content=f"Error in SythesizerAgent: {str(e)}")
            }