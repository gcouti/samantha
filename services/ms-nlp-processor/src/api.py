"""
FastAPI application for the NLP Processor service with LLM and LangFlow integration.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uvicorn
import logging

from processor import NLPProcessor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the FastAPI app
app = FastAPI(
    title="Samantha NLP Processor",
    description="NLP processing service with LLM and LangFlow multi-agent system for Samantha assistant",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the NLP processor
nlp_processor = NLPProcessor()

class ProcessRequest(BaseModel):
    text: str
    context: Dict[str, Any] = {}
    thread_id: str = "default"

class ProcessResponse(BaseModel):
    response: str
    agent: str
    confidence: float
    metadata: Dict[str, Any] = {}

class HealthResponse(BaseModel):
    status: str
    service: str
    llm_enabled: bool = True
    langflow_available: bool = False
    langgraph_available: bool = False

@app.post("/process", response_model=ProcessResponse)
async def process_text(request: ProcessRequest):
    """
    Process natural language text and return a response.
    
    Args:
        request: The request containing the text to process and optional context
        
    Returns:
        The processed response with metadata
    """
    try:
        # Delegate processing method selection to the processor
        result = await nlp_processor.process_text(request.text, thread_id=request.thread_id)
        
        return ProcessResponse(
            response=result.get("response", "Desculpe, não consegui processar sua solicitação."),
            agent=result.get("agent", "unknown"),
            confidence=result.get("confidence", 0.0),
            metadata={
                "intent": result.get("intent"),
                "entities": result.get("entities", {}),
                "intent_confidence": result.get("intent_confidence"),
                "selected_agent": result.get("selected_agent"),
                "agent_reasoning": result.get("agent_reasoning"),
                "llm_enhanced": result.get("llm_enhanced", False),
                "processing_method": result.get("processing_method", "standard"),
                "thread_id": result.get("thread_id"),
                "context": request.context
            }
        )
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversation/{thread_id}")
async def get_conversation_history(thread_id: str):
    """Get conversation history for a specific thread."""
    try:
        history = await nlp_processor.get_conversation_history(thread_id)
        return {
            "thread_id": thread_id,
            "history": history,
            "total_messages": len(history)
        }
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with LLM, LangFlow, and LangGraph status."""
    try:
        # Check if LangFlow is available
        from llm_integration import LangFlowManager
        langflow_manager = LangFlowManager()
        flows = await langflow_manager.get_available_flows()
        langflow_available = len(flows) > 0
    except Exception as e:
        logger.warning(f"LangFlow health check failed: {str(e)}")
        langflow_available = False
    
    try:
        # Check if LangGraph is available
        from langgraph_integration import LangGraphManager
        langgraph_manager = LangGraphManager()
        langgraph_available = langgraph_manager is not None
    except Exception as e:
        logger.warning(f"LangGraph health check failed: {str(e)}")
        langgraph_available = False
    
    return HealthResponse(
        status="ok",
        service="nlp-processor",
        llm_enabled=True,
        langflow_available=langflow_available,
        langgraph_available=langgraph_available
    )

@app.get("/agents")
async def list_agents():
    """List available agents in the system by scanning the agents directory."""
    import os
    import glob
    
    agents_dir = os.path.join(os.path.dirname(__file__), "agents")
    agent_files = glob.glob(os.path.join(agents_dir, "*_agent.py"))
    
    # Filter out __init__.py and base_agent.py
    excluded_files = ["__init__.py", "base_agent.py"]
    agent_files = [f for f in agent_files if os.path.basename(f) not in excluded_files]
    
    agents = []
    for file_path in agent_files:
        filename = os.path.basename(file_path)
        agent_name = filename.replace(".py", "")
        
        # Try to get description from the agent class
        try:
            # Import the agent module dynamically
            module_name = f"agents.{agent_name}"
            module = __import__(module_name, fromlist=[agent_name])
            
            # Get the agent class (assumes class name follows CamelCase convention)
            class_name = ''.join(word.capitalize() for word in agent_name.split('_'))
            agent_class = getattr(module, class_name)
            
            # Create instance to get description
            agent_instance = agent_class()
            description = agent_instance.description
            
            # Determine agent type based on name or description
            agent_type = "unknown"
            if "tool" in agent_name.lower() or "tool" in description.lower():
                agent_type = "tool_enabled"
            elif "llm" in description.lower() or "general" in agent_name.lower():
                agent_type = "llm_powered"
            elif "langflow" in agent_name.lower():
                agent_type = "langflow"
            elif "langgraph" in agent_name.lower():
                agent_type = "langgraph"
            elif "unknown" in agent_name.lower():
                agent_type = "fallback"
            
        except Exception as e:
            logger.warning(f"Could not load agent {agent_name}: {str(e)}")
            description = f"Agent from {filename}"
            agent_type = "unknown"
        
        agents.append({
            "name": agent_name,
            "description": description,
            "type": agent_type,
            "file": filename
        })
    
    return {
        "agents": agents,
        "total_agents": len(agents),
        "scanned_from": agents_dir
    }

@app.get("/flows")
async def list_langflow_flows():
    """List available LangFlow workflows."""
    try:
        from llm_integration import LangFlowManager
        langflow_manager = LangFlowManager()
        flows = await langflow_manager.get_available_flows()
        return {
            "flows": flows,
            "total_flows": len(flows),
            "langflow_available": len(flows) > 0
        }
    except Exception as e:
        logger.error(f"Error listing flows: {str(e)}")
        return {
            "flows": [],
            "total_flows": 0,
            "langflow_available": False,
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
