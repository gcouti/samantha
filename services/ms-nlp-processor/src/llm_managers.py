"""
LLM Managers module
"""
import logging
import aiohttp
import operator
from datetime import datetime

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TypedDict, Annotated

from tools.gmail_tool import GmailTool
from tools.web_search_tool import WebSearchTool
from tools.note_tool import ObsidianGitHubTool
from dotenv import load_dotenv
from agents.base_agent import AgentState, BaseAgent
from agents.general_agent import GeneralAgent
from agents.configuration_agent import ConfigurationAgent
from agents.utils import collect_agent_descriptions, collect_tool_descriptions

# Imports do LangGraph geralmente vêm do sub módulo 'graph'
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from database.database import get_db
from database.crud import get_user_by_email, update_user_notes_path
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


class LangGraphManager(BaseLLMManager):
    """Manages LangGraph workflows for multi-agent coordination."""
    
    def __init__(self, preferred_provider: LLMProvider = LLMProvider.GEMINI):
        super().__init__(preferred_provider)
        
        # Initialize tools
        tools = [
            GmailTool().search_gmail_dynamic,
            WebSearchTool().execute,
            ObsidianGitHubTool().search_notes,
            ObsidianGitHubTool().read_note
        ]

        # Pass the state to the tools so they can access dynamic data like vault_path
        self.tool_node = ToolNode(tools)

        # Bind tools to the LLM client and initialize agents
        self.llm_with_tools = self.current_provider.client.bind_tools(tools)

        self.registred_agents:List[BaseAgent] = [
            GeneralAgent(self.llm_with_tools),
            # ConfigurationAgent(self.llm_with_tools)
        ]

        self.tool_descriptions = collect_tool_descriptions(tools)        
        self.agent_descriptions = collect_agent_descriptions(self.registred_agents)

        self._has_obsidian_note_flow = (
            any("search_notes" in desc["name"] for desc in self.tool_descriptions)
            and any("read_note" in desc["name"] for desc in self.tool_descriptions)
        )

        # Create and compile the workflow
        self.workflow = self._create_workflow()
        self.app = self.workflow.compile(checkpointer=MemorySaver())
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow for multi-agent processing."""
        
        # Define the workflow
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("supervisor_node", self._supervisor_node)
        workflow.add_node("tools_node", self.tool_node)

        for agent in self.registred_agents:
            workflow.add_node(agent.name, agent.node)
        
        # Add edges
        workflow.add_node("check_user_flow", self._check_user_node)
        workflow.add_node("configuration_node", self._configuration_node)
        workflow.add_node("handle_notes_path_update_node", self._handle_notes_path_update_node)
        workflow.add_node("authentication_required_node", self._authentication_required_node)
        workflow.add_node("wait_for_input_node", self._waiting_for_input_node)

        # Add edges
        workflow.set_entry_point("check_user_flow")
        workflow.add_conditional_edges(
            "check_user_flow",
            self._configuration_router,
            {
                "continue": "supervisor_node",
                "configure": "configuration_node",
                "wait_for_input": "wait_for_input_node",
                "auth_flow": "authentication_required_node",
                "update_notes_path": "handle_notes_path_update_node",
            }
        )

        for agent in self.registred_agents:
            workflow.add_edge("supervisor_node", agent.name)
            # workflow.add_edge(agent.name, "supervisor_node")
            workflow.add_edge(agent.name, END)
        
        workflow.add_edge("configuration_node", "supervisor_node")
        workflow.add_edge("authentication_required_node", END)
        workflow.add_edge("handle_notes_path_update_node", END)
        workflow.add_edge("supervisor_node", END)

        # After the general_agent runs, decide if a tool should be called
        workflow.add_conditional_edges(
            "supervisor_node",
            tools_condition, 
            {
                "tools": "tools_node",
                END: END
            }
        )

        # If a tool was called, run the tool and then go back to the general_agent
        # to process the tool's output
        workflow.add_edge("tools_node", "supervisor_node")
        
        return workflow

    def _log_state_snapshot(self, node_name: str, updates: Dict[str, Any]) -> None:
        """Log a concise summary of the state delta returned by a node."""
        try:
            message_delta = updates.get("messages")
            logger.debug(
                "[LangGraph] %s returning updates | keys=%s | text=%r | response=%r | messages_delta=%s",
                node_name,
                list(updates.keys()),
                updates.get("text"),
                updates.get("response"),
                len(message_delta) if isinstance(message_delta, list) else "n/a",
            )
        except Exception:
            logger.exception("Failed to log state snapshot for node %s", node_name)

    def _build_capabilities_prompt(self) -> str:
        """Compose a system prompt describing available agents and tools."""

        def _format_block(title: str, items: List[Dict[str, str]]) -> str:
            lines = "\n".join(f"- {item['name']}: {item['description']}" for item in items)
            return f"{title}\n{lines}"

        intro = (
            "Você é um assistente pessoal de elite para executivos. Sua função é responder perguntas,"
            "executar tarefas e ser proativo."
        )

        sections: List[str] = []
        if self.agent_descriptions:
            sections.append(_format_block("Agentes disponíveis:", self.agent_descriptions))
        if self.tool_descriptions:
            sections.append(_format_block("Ferramentas disponíveis:", self.tool_descriptions))

        closing = (
            "Seja conciso e direto, mas sempre cordial e também tome a decisão se devemos parar de procurar "
            "respostas. Com base nisso, ache a melhor forma de responder a pergunta do usuário."
        )

        prompt_parts = [intro]
        if sections:
            prompt_parts.append("\n\n".join(sections))
        prompt_parts.append(closing)

        return "\n\n".join(part.strip() for part in prompt_parts if part.strip())
    
    async def _supervisor_node(self, state: AgentState) -> AgentState:
        """Injects the system prompt and prepares the state for the general agent."""
        logger.info(f"_supervisor_node preparing state for user: {state.get('user_email')} text: {state.get('text')}")
        
        system_prompt = self._build_capabilities_prompt()
        system_message = SystemMessage(content=system_prompt)
        
        # The user's message is already in the state from process_text
        # We prepend the system message to guide the LLM.

        # IDEAS for agents
          # agente para verificar o tom do usuário e intervir na conversa com um ser humano
          # agente para verificar se a resposta final é correta
          # agente para verificar se a resposta precisa ser atualziada, se é uma pergunta que leva em consideração o tempo
          # agente para verificar se precisa de mais informações para completar a resposta
          # agente para completar a query - Exexmplo temperatura hoje? Contexto de localização 
        ai_message = self.llm_with_tools.invoke(state["messages"] + [system_message])
        updates = {"messages": [system_message, ai_message]}
        
        self._log_state_snapshot("_supervisor_node", updates)
        return updates
        
    async def _basic_configuration_required_node(self, state: AgentState) -> AgentState:
        """Generate a response indicating that note path is required."""
        updates = {
            "response": "Por favor, me passe o caminho do repositório de suas notas.",
            "confidence": 1.0,
            "selected_agent": "system",
        }
        self._log_state_snapshot("_basic_configuration_required_node", updates)
        return updates


    async def _authentication_required_node(self, state: AgentState) -> AgentState:
        """Generate a response indicating that authentication is required."""
        updates = {
            "response": "Por favor, autentique-se para continuar. Use o argumento --email ao iniciar o CLI.",
            "confidence": 1.0,
            "selected_agent": "system",
        }
        self._log_state_snapshot("_authentication_required_node", updates)
        return updates
    
    async def _check_user_node(self, state: AgentState) -> AgentState:
        """Check if the user exists and load their vault path and GitHub config."""
        db = next(get_db())
        user = get_user_by_email(db, state["user_email"])
        updates: Dict[str, Any] = {}
        if user:
            updates["is_authenticated"] = True
            updates["notes_path"] = user.notes_path
            logger.info(f"User {state['user_email']} authenticated.")            
        else:
            updates["is_authenticated"] = False
            updates["notes_path"] = None
            logger.warning(f"User {state['user_email']} not found. Authentication required.")
        self._log_state_snapshot("_check_user_node", updates)
        return updates

    
    def _configuration_router(self, state: AgentState) -> str:
        """Router to decide the next step after the configuration agent."""

        latest_text = state.get("txt")

        if not state["is_authenticated"]:
            return "auth_flow"
        elif not state["notes_path"] or not state["notes_path"].startswith("https://github.com/"):
            if latest_text.startswith("http"):
                return "update_notes_path"
            else:
                return "wait_for_input"
        else:
            return "continue"


    async def _configuration_node(self, state: AgentState) -> AgentState:
        """Node that handles the configuration agent logic."""
        response = await self.configuration_agent.process(self._get_latest_text(state), state)
        updates = {"response": [SystemMessage(content=response['response'])]}
        self._log_state_snapshot("_configuration_node", updates)
        return updates

    async def _waiting_for_input_node(self, state: AgentState) -> AgentState:
        """Node that waits for user input."""
        error_message = "Por favor, forneça o caminho do repositório do GitHub onde as notas serão escritas"
        updates = {"response": [SystemMessage(content=error_message)]}

        self._log_state_snapshot("_waiting_for_input_node", updates)
        return updates


    async def _handle_notes_path_update_node(self, state: AgentState) -> AgentState:
        """Node to update the notes_path in the database."""
        db = next(get_db())
        # simple extraction of the path from the text
        notes_path = self._get_latest_text(state).strip()
        
        # Verify if the path is from GitHub
        if not notes_path.startswith("https://github.com/"):
            error_message = "Erro: O caminho das notas deve ser um repositório do GitHub (começando com 'https://github.com/')."
            updates = {"messages": [HumanMessage(content=error_message)]}
            self._log_state_snapshot("_handle_notes_path_update_node", updates)
            return updates
        
        update_user_notes_path(db, state["user_email"], notes_path)
        response_message = f"Caminho das notas atualizado para: {notes_path}. Agora podemos continuar."
        updates = {
            "notes_path": notes_path,
            "messages": [SystemMessage(content=response_message)],
        }
        self._log_state_snapshot("_handle_notes_path_update_node", updates)
        return updates

    async def process_text(self, text: str, thread_id: str = "default", email: str = None) -> Dict[str, Any]:
        """Process text using the LangGraph workflow."""
        try:
            initial_state = AgentState(
                messages=[HumanMessage(content=text)],  # Add the initial user message
                text=text,
                user_email=email,
                is_authenticated=bool(email),  # Simple auth check
                entities={},
                response=[],
                metadata={"timestamp": datetime.utcnow().isoformat()},
            )

            # The config is passed to all nodes. The vault_path will be populated
            # by the _check_user_node and will be available in the state for subsequent nodes.
            config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 10}
            result = await self.app.ainvoke(initial_state, config)

            # Get the last message content from the state
            message = result.get("response", [])[-1].content

            return {
                "response": message,
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
            logger.error(f"Error in LangGraph processing: {str(e)}", exc_info=True)

            return {
                "response": "Desculpe, ocorreu um erro no processamento com LangGraph.",
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
                        "timestamp": state.get("metadata", {}).get("timestamp")
                    }
                    for state in checkpoint.values.get("messages", [])
                ]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []
