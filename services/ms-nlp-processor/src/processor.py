"""
NLP Processor Service

This module implements the main NLP processing logic and coordinates the agents
using LLM, LangFlow, and LangGraph for intelligent multi-agent decision making.
"""

import logging

from typing import Dict, Any, List
from llm_managers import LLMManager, LangGraphManager

logger = logging.getLogger(__name__)

class NLPProcessor:
    """Main NLP processor that coordinates different agents using LLM, LangFlow, and LangGraph."""
    
    def __init__(self):
        self.llm_manager = LLMManager()
        self.langgraph_manager = LangGraphManager()
        
    
    async def process_text(self, text: str, thread_id: str = "default", email: str = None) -> Dict[str, Any]:
        """
        Process the input text through intelligent engine selection.
        
        Args:
            text: The input text to process
            thread_id: Thread ID for conversation continuity
            email: The user's email for authentication

        Returns:
            Dict containing the response and metadata
        """
        try:
            # Use LLM to determine the best processing method
            # processing_method = await self._select_processing_method(text, thread_id)
            
            # TODO: Force to be simplier first, and then we will introduce more complex code here
            processing_method = "langgraph"

            # Execute using the selected method
            if processing_method == "langgraph":
                return await self.langgraph_manager.process_text(text, thread_id, email)
            else:
                return await self.llm_manager.process_text(text, thread_id)
                
        except Exception as e:
            logger.error(f"Error processing text: {str(e)}", exc_info=True)
            return {
                "response": "Ocorreu um erro inesperado. Por favor, tente novamente mais tarde.",
                "agent": "system",
                "confidence": 0.0,
                "error": str(e),
                "processing_method": "error"
            }
    
    async def _select_processing_method(self, text: str, thread_id: str) -> str:
        """Use LLM to select the best processing method."""
        try:
            from langchain.schema import HumanMessage, SystemMessage
            
            prompt = f"""
            Analise a solicitação do usuário e selecione o melhor método de processamento:
            
            Texto: {text}
            Thread ID: {thread_id}
            
            Métodos disponíveis:
            - llm_agents: Para solicitações gerais usando cadeia de agentes com LLM
            - langgraph: Para conversas com estado e workflows baseados em estado
            
            Considere:
            1. Complexidade da solicitação
            2. Necessidade de contexto/histórico
            3. Requisitos de workflow complexo
            4. Interações conversacionais
            
            Responda apenas com o nome do método: llm_agents ou langgraph
            """
            
            messages = [
                SystemMessage(content="Você é um especialista em selecionar métodos de processamento para NLP."),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm_manager.llm.ainvoke(messages)
            selected_method = response.content.strip().lower()
            
            # Validate selected method
            valid_methods = ["llm_agents", "langgraph"]
            if selected_method in valid_methods:
                logger.info(f"Selected processing method: {selected_method}")
                return selected_method
            else:
                logger.warning(f"Invalid method '{selected_method}', defaulting to llm_agents")
                return "llm_agents"
                
        except Exception as e:
            logger.error(f"Error selecting processing method: {str(e)}")
            return "llm_agents"  # Default fallback
    
    async def _process_with_llm_agents(self, text: str) -> Dict[str, Any]:
        """Process text using LLM agents (original method)."""
        try:        
            # Step 2: Use LLM to select the best agent for this request
            agent_selection = await self.llm_manager.select_agent(text, intent, entities)
            selected_agent = agent_selection.get("agent", "general_agent")
            reasoning = agent_selection.get("reasoning", "no reasoning provided")
            
            logger.info(f"LLM selected agent: {selected_agent} - {reasoning}")
            
            # Step 3: Process through the agent chain (agents will self-select)
            response = await self.agents.process(text, intent, entities)
            
            # If no agent handled the request, use LLM as fallback
            if not response:
                logger.warning("No agent handled the request, using LLM fallback")
                llm_response = await self.llm_manager.generate_response(
                    text, 
                    {"intent": intent, "entities": entities, "agent": "llm_fallback"}
                )
                response = {
                    "response": llm_response,
                    "agent": "llm_fallback",
                    "confidence": 0.5
                }
            
            # Enhance response with LLM metadata
            response.update({
                "intent": intent,
                "entities": entities,
                "intent_confidence": confidence,
                "selected_agent": selected_agent,
                "agent_reasoning": reasoning,
                "llm_enhanced": True,
                "processing_method": "llm_agents"
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Error in LLM agents processing: {str(e)}")
            raise
    
    async def get_conversation_history(self, thread_id: str = "default") -> List[Dict[str, Any]]:
        """Get conversation history for a given thread."""
        try:
            return await self.langgraph_manager.get_conversation_history(thread_id)
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []
