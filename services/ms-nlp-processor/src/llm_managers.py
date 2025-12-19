"""
LLM Managers module
"""
import os
import json
import logging
import aiohttp
import operator
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TypedDict, Annotated

from dotenv import load_dotenv
from agents.general_agent import GeneralAgent

# Imports do LangGraph geralmente vêm do sub módulo 'graph'
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage
from llm_providers import LLMConfig, LLMProviderFactory, LLMProvider, BaseLLMProvider

load_dotenv()

logger = logging.getLogger(__name__)

class BaseLLMManager:

    def __init__(self, preferred_provider: LLMProvider = LLMProvider.OPENAI):
        
        self.preferred_provider = preferred_provider
        
        self.providers = self._initialize_providers()
        self.current_provider = self._select_best_provider()

    def _initialize_providers(self) -> Dict[LLMProvider, BaseLLMProvider]:
        """Initialize all available providers."""
        providers = {}
        available_providers = LLMProviderFactory.get_available_providers()
        
        for provider in available_providers:
            try:
                config = LLMConfig(provider)
                provider_instance = LLMProviderFactory.create_provider(config)
                providers[provider] = provider_instance
                logger.info(f"Initialized {provider.value} provider")
            except Exception as e:
                logger.warning(f"Failed to initialize {provider.value}: {str(e)}")
        
        return providers


    def _select_best_provider(self) -> Optional[BaseLLMProvider]:
        """Select the best available provider."""
        # Try preferred provider first
        if self.preferred_provider in self.providers:
            return self.providers[self.preferred_provider]
        
        # Fallback to any available provider
        if self.providers:
            first_provider = next(iter(self.providers.values()))
            logger.warning(f"Preferred provider not available, using {first_provider.config.provider.value}")
            return first_provider
        
        logger.error("No LLM providers available")
        return None

    @abstractmethod
    async def process_text(self, text: str, thread_id: str = "default") -> Dict[str, Any]:
        """Process the input text through intelligent engine selection."""
        raise NotImplementedError


class LLMManager(BaseLLMManager):
    """
    Main LLM Manager that handles multiple providers with fallback support.
    """
    
    def __init__(self, preferred_provider: LLMProvider = LLMProvider.GEMINI):
        super().__init__(preferred_provider)
        self.agent = GeneralAgent(self.current_provider)
    
    async def process_text(self, text: str, thread_id: str = "default") -> Dict[str, Any]:
        # Initialize prompts

        response = await self.agent.process(text, "general", {})

        return {
            "response": response.get('text',"Desculpe, estou com dificuldades para entender. Pode reformular?"),
            "agent": "llm",
            "metadata": {
                "provider": self.preferred_provider.value,
                "thread_id": thread_id,
            },
        }


class LangFlowManager(BaseLLMManager):
    """Manages LangFlow integration for complex multi-agent workflows."""
    
    def __init__(self, base_url: str = "http://localhost:7860"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def run_flow(self, flow_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a LangFlow workflow."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            url = f"{self.base_url}/api/v1/run/{flow_id}"
            
            async with self.session.post(url, json=inputs) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    logger.error(f"LangFlow error: {response.status}")
                    return {"error": f"LangFlow returned status {response.status}"}
                    
        except Exception as e:
            logger.error(f"Error running LangFlow: {str(e)}")
            return {"error": str(e)}
    
    async def get_available_flows(self) -> List[Dict[str, Any]]:
        """Get list of available LangFlow workflows."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            url = f"{self.base_url}/api/v1/flows"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    flows = await response.json()
                    return flows
                else:
                    logger.error(f"Error getting flows: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting flows: {str(e)}")
            return []

    async def process_text(self, text: str, thread_id: str = "default") -> Dict[str, Any]:
        """Process text using LangFlow for complex multi-agent workflows."""
        try:
            flows = await self.get_available_flows()
            if not flows:
                logger.warning("No LangFlow flows available for processing")
                return {
                    "response": "Nenhum fluxo LangFlow disponível para processamento.",
                    "agent": "langflow",
                    "confidence": 0.0,
                    "metadata": {
                        "processing_type": "langflow",
                        "processing_method": "langflow",
                        "flows_available": False,
                        "thread_id": thread_id,
                    },
                }

            flow_id = flows[0].get("id")

            inputs = {
                "text": text,
                "user_context": {},
                "session_id": thread_id,
            }

            async with self as manager:
                result = await manager.run_flow(flow_id, inputs)

            if "error" in result:
                logger.error(f"LangFlow error: {result['error']}")
                return {
                    "response": "Ocorreu um erro ao processar com LangFlow.",
                    "agent": "langflow",
                    "confidence": 0.0,
                    "metadata": {
                        "flow_id": flow_id,
                        "langflow_result": result,
                        "processing_type": "langflow",
                        "processing_method": "langflow",
                        "thread_id": thread_id,
                        "error": result["error"],
                    },
                }

            response_data = result.get("outputs", {})

            return {
                "response": response_data.get("response", "Processamento LangFlow concluído."),
                "agent": "langflow",
                "confidence": response_data.get("confidence", 0.8),
                "metadata": {
                    "flow_id": flow_id,
                    "langflow_result": result,
                    "processing_type": "langflow",
                    "processing_method": "langflow",
                    "thread_id": thread_id,
                },
            }

        except Exception as e:
            logger.error(f"Error in LangFlow processing: {str(e)}")
            return {
                "response": "Ocorreu um erro ao processar com LangFlow.",
                "agent": "langflow",
                "confidence": 0.0,
                "metadata": {
                    "processing_type": "langflow",
                    "processing_method": "langflow",
                    "thread_id": thread_id,
                    "error": str(e),
                },
            }


class AgentState(TypedDict):
    """State for the LangGraph workflow."""
    messages: Annotated[List[BaseMessage], operator.add]
    text: str
    intent: Optional[str]
    entities: Dict[str, Any]
    selected_agent: Optional[str]
    response: Optional[str]
    confidence: float
    metadata: Dict[str, Any]

class LangGraphManager(BaseLLMManager):
    """Manages LangGraph workflows for multi-agent coordination."""
    
    def __init__(self, llm_manager: LLMManager = None):
        self.llm_manager = llm_manager or LLMManager()
        
        # Initialize the workflow
        self.workflow = self._create_workflow()
        self.app = self.workflow.compile(checkpointer=MemorySaver())
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow for multi-agent processing."""
        
        # Define the workflow nodes
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("classify_intent", self._classify_intent_node)
        workflow.add_node("select_agent", self._select_agent_node)
        workflow.add_node("process_with_agent", self._process_with_agent_node)
        workflow.add_node("generate_response", self._generate_response_node)
        
        # Add edges
        workflow.set_entry_point("classify_intent")
        workflow.add_edge("classify_intent", "select_agent")
        workflow.add_edge("select_agent", "process_with_agent")
        workflow.add_edge("process_with_agent", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow
    
    async def _classify_intent_node(self, state: AgentState) -> AgentState:
        """Classify user intent using LLM."""
        try:
            intent_result = await self.llm_manager.classify_intent(state['text'])
            
            state["intent"] = intent_result.get("intent", "unknown")
            state["entities"] = intent_result.get("entities", {})
            state["metadata"]["intent_classification"] = intent_result
            
            logger.info(f"Intent classified: {state['intent']}")
            return state
            
        except Exception as e:
            logger.error(f"Error classifying intent: {str(e)}")
            state["intent"] = "unknown"
            state["entities"] = {}
            return state
    
    async def _select_agent_node(self, state: AgentState) -> AgentState:
        """Select the appropriate agent using LLM."""
        try:
            agent_result = await self.llm_manager.select_agent(
                state['text'], 
                state['intent'], 
                state['entities']
            )
            
            state["selected_agent"] = agent_result.get("agent", "general_agent")
            state["metadata"]["agent_selection"] = agent_result
            
            logger.info(f"Agent selected: {state['selected_agent']}")
            return state
                        
        except Exception as e:
            logger.error(f"Error selecting agent: {str(e)}")

            return state
    
    async def _process_with_agent_node(self, state: AgentState) -> AgentState:
        """Process the request with the selected agent."""
        try:
            from agents import GeneralAgent, LangFlowAgent, ToolAgent
            
            # Get the appropriate agent
            agent_map = {
                "tool_agent": ToolAgent(),
                "general_agent": GeneralAgent(),
                "langflow_agent": LangFlowAgent()
            }
            
            agent = agent_map.get(state["selected_agent"], GeneralAgent())
            
            # Process with the agent
            result = await agent.handle(
                state["text"], 
                state["intent"], 
                state["entities"]
            )
            
            state["response"] = result.get("response", "Processamento concluído.")
            state["confidence"] = result.get("confidence", 0.5)
            state["metadata"]["agent_result"] = result
            
            logger.info(f"Agent {state['selected_agent']} processed request")
            return state
            
        except Exception as e:
            logger.error(f"Error processing with agent: {str(e)}")
            state["response"] = "Desculpe, ocorreu um erro durante o processamento."
            state["confidence"] = 0.0
            return state
    
    async def _generate_response_node(self, state: AgentState) -> AgentState:
        """Generate final response using LLM for enhancement."""
        try:
            if state["confidence"] < 0.7:
                # Enhance response with LLM if confidence is low
                enhancement_prompt = f"""
                Melhore a seguinte resposta do assistente virtual Samantha:
                
                Resposta original: {state['response']}
                Intenção: {state['intent']}
                Agente usado: {state['selected_agent']}
                
                Torne a resposta mais natural, prestativa e em português.
                Mantenha o significado original mas melhore a formulação.
                """
                
                response = await self.llm_manager.generate_response([
                    {"role": "system", "content": "Você é um assistente virtual chamado Samantha."},
                    {"role": "user", "content": enhancement_prompt}
                ])
                
                state["response"] = response
                state["confidence"] = min(state["confidence"] + 0.2, 1.0)
                state["metadata"]["llm_enhanced"] = True
            
            state["metadata"]["final_response"] = True
            return state
            
        except Exception as e:
            logger.error(f"Error generating final response: {str(e)}")
            return state
    
    async def process_text(self, text: str, thread_id: str = "default") -> Dict[str, Any]:
        """Process text using the LangGraph workflow."""
        try:
            initial_state = AgentState(
                messages=[],
                text=text,
                intent=None,
                entities={},
                selected_agent=None,
                response=None,
                confidence=0.0,
                metadata={},
            )

            config = {"configurable": {"thread_id": thread_id}}
            result = await self.app.ainvoke(initial_state, config)

            return {
                "response": result["response"],
                "agent": result["selected_agent"],
                "confidence": result["confidence"],
                "processing_method": "langgraph",
                "llm_enhanced": True,
                "thread_id": thread_id,
                "metadata": {
                    "intent": result["intent"],
                    "entities": result["entities"],
                    "langgraph_workflow": True,
                    "thread_id": thread_id,
                    **result["metadata"],
                },
            }

        except Exception as e:
            logger.error(f"Error in LangGraph processing: {str(e)}")
            return {
                "response": "Desculpe, ocorreu um erro no processamento com LangGraph.",
                "agent": "system",
                "confidence": 0.0,
                "processing_method": "langgraph",
                "llm_enhanced": False,
                "thread_id": thread_id,
                "error": str(e),
            }
    
    async def get_conversation_history(self, thread_id: str = "default") -> List[Dict[str, Any]]:
        """Get conversation history for a thread."""
        try:
            config = {"configurable": {"thread_id": thread_id}}
            checkpoint = self.app.get_state(config)
            
            if checkpoint and checkpoint.values:
                return [
                    {
                        "text": state.get("text"),
                        "response": state.get("response"),
                        "agent": state.get("selected_agent"),
                        "timestamp": state.get("metadata", {}).get("timestamp")
                    }
                    for state in checkpoint.values.get("messages", [])
                ]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []
