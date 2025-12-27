"""
LLM Managers module
"""
import logging
import aiohttp
import operator

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TypedDict, Annotated

from dotenv import load_dotenv
from agents.general_agent import GeneralAgent
from agents.orchestrator_agent import OrchestratorAgent

# Imports do LangGraph geralmente vêm do sub módulo 'graph'
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage

from llm_providers import LLMConfig, LLMProviderFactory, LLMProvider, BaseLLMProvider

from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.utils import build_resource_service, get_gmail_credentials


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
    
    def __init__(self, preferred_provider: LLMProvider = LLMProvider.GEMINI, base_url: str = "http://localhost:7860"):
        super().__init__(preferred_provider)

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
    
    def __init__(self, preferred_provider: LLMProvider = LLMProvider.GEMINI):
        super().__init__(preferred_provider)
        
        # Initialize the workflow
        self.orchestrator_agent = OrchestratorAgent(self.current_provider)
        self.general_agent = GeneralAgent(self.current_provider)
        self.workflow = self._create_workflow()

        self.app = self.workflow.compile(checkpointer=MemorySaver())
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow for multi-agent processing."""
        
        # Define the workflow nodes
        workflow = StateGraph(AgentState)
     
        tools = []
        tools.append(GmailTool().search_gmail_dynamic)
        tool_node = ToolNode(tools=tools)

        # Add nodes
        workflow.add_node("orchestrator_agent", self._orchestrator_node)
        workflow.add_node("general_agent", self._general_node)
        workflow.add_node("tools", tool_node)
        
        # Add edges
        workflow.set_entry_point("orchestrator_agent")
        workflow.add_edge("orchestrator_agent", "general_agent")
        
        # --- A MÁGICA ACONTECE AQUI (ARESTAS CONDICIONAIS) ---
        # Se o chatbot retornou uma tool_call -> vá para "tools"
        # Se o chatbot retornou texto normal -> vá para END
        
        workflow.add_conditional_edges(
            "orchestrator_agent",
            tools_condition, 
        )

        # Se a ferramenta rodou, volta para o orchestrator_agent para ele ler o resultado
        workflow.add_edge("tools", "orchestrator_agent")
        workflow.set_finish_point("general_agent")
        
        return workflow
    
    async def _orchestrator_node(self, state: AgentState) -> AgentState:
        """Classify user intent using LLM."""

        try:
            intent_result = await self.orchestrator_agent.handle(state['text'], {})
            state["selected_agent"] = intent_result['agent']

            logger.info(f"Selected agent: {intent_result['agent']}")

            return state
            
        except Exception as e:
            logger.error(f"Error classifying intent: {str(e)}")
            state["selected_agent"] = "unknown"
            return state
    
    async def _general_node(self, state: AgentState) -> AgentState:
        """Generate response using the general agent."""
        try:
            agent_result = await self.general_agent.handle(
                state['text'], 
                state['intent'], 
                state['entities']
            )
            
            state["response"] = agent_result.get("text", "Desculpe, não consegui processar sua solicitação.")
            state["confidence"] = agent_result.get("confidence", 0.5)
            state["selected_agent"] = "general_agent"
            state["metadata"]["agent_selection"] = agent_result
            
            logger.info(f"Response generated by general agent")
            return state
                        
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            state["response"] = "Desculpe, ocorreu um erro ao processar sua solicitação."
            state["confidence"] = 0.0
            state["selected_agent"] = "system"
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
                "response": result.get("response", "Desculpe, não consegui processar sua solicitação."),
                "agent": result.get("selected_agent", "system"),
                "confidence": result.get("confidence", 0.0),
                "processing_method": "langgraph",
                "llm_enhanced": True,
                "thread_id": thread_id,
                "metadata": {
                    "intent": result.get("intent"),
                    "entities": result.get("entities", {}),
                    "langgraph_workflow": True,
                    "thread_id": thread_id,
                    **result.get("metadata", {}),
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
