"""
FastAPI application for the NLP Processor service with LLM and LangFlow integration.
"""
from fastapi import FastAPI, HTTPException, Request, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-secret-key")
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uvicorn
import logging
import json
import os

import glob

from processor import NLPProcessor
from src.tools.gmail_tool import iniciar_login, receber_callback
from starlette.requests import Request
from starlette.responses import RedirectResponse
from .auth import oauth
from .database.database import get_db
from .database.models import User
from sqlalchemy.orm import Session
import jwt
import datetime

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

class GmailLoginResponse(BaseModel):
    authorization_url: str
    state: str
    message: str

class GmailCallbackResponse(BaseModel):
    success: bool
    message: strimport os
    credentials_stored: bool = False

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


@app.get("/integrations/gmail", response_model=GmailLoginResponse)
async def gmail_login():
    """
    Inicia o processo de login com Gmail.
    Retorna a URL de autorização para o usuário acessar.
    """
    try:
        # Verifica se o arquivo client_secrets.json existe
        if not os.path.exists('client_secrets.json'):
            return GmailLoginResponse(
                authorization_url="",
                state="",
                message="Arquivo client_secrets.json não encontrado. Configure as credenciais do Gmail."
            )
        
        # Inicia o processo de login
        auth_url, state = iniciar_login()
        
        return GmailLoginResponse(
            authorization_url=auth_url,
            state=state,
            message="URL de autorização gerada com sucesso. Acesse a URL para autorizar o acesso ao Gmail."
        )
    
    except Exception as e:
        logger.error(f"Erro ao iniciar login Gmail: {str(e)}")
        return GmailLoginResponse(
            authorization_url="",
            state="",
            message=f"Erro ao iniciar login: {str(e)}"
        )


@app.get("/integrations/gmail/callback", response_model=GmailCallbackResponse)
async def gmail_callback(code: str = Query(...), state: str = Query(...)):
    """
    Endpoint de callback para o OAuth2 do Gmail.
    O Google redireciona o usuário para esta URL após a autorização.
    """
    try:
        # Constrói a URL completa recebida
        callback_url = f"http://localhost:8000/gmail/callback?code={code}&state={state}"
        
        # Processa o callback e obtém as credenciais
        credentials = receber_callback(callback_url)
        
        if credentials:
            # Armazena as credenciais em um arquivo para uso posterior
            credentials_json = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }
            
            with open('gmail_credentials.json', 'w') as f:
                json.dump(credentials_json, f, indent=2)
            
            return GmailCallbackResponse(
                success=True,
                message="Login com Gmail realizado com sucesso! Credenciais armazenadas.",
                credentials_stored=True
            )
        else:
            return GmailCallbackResponse(
                success=False,
                message="Falha ao obter credenciais do Gmail.",
                credentials_stored=False
            )
    
    except Exception as e:
        logger.error(f"Erro no callback Gmail: {str(e)}")
        return GmailCallbackResponse(
            success=False,
            message=f"Erro no processamento do callback: {str(e)}",
            credentials_stored=False
        )

@app.get("/integrations/gmail/status")
async def gmail_status():
    """
    Verifica o sta", retus da conexão com Gmail.
    """
    try:
        if os.path.exists('gmail_credentials.json'):
            with open('gmail_credentials.json', 'r') as f:
                credentials = json.load(f)
            
            return {
                "connected": True,
                "message": "Conectado ao Gmail",
                "scopes": credentials.get('scopes', []),
                "has_refresh_token": bool(credentials.get('refresh_token'))
            }
        else:
            return {
                "connected": False,
                "message": "Não conectado ao Gmail. Use /gmail/login para autenticar.",
                "scopes": [],
                "has_refresh_token": False
            }
    
    except Exception as e:
        logger.error(f"Erro ao verificar status Gmail: {str(e)}")
        return {
            "connected": False,
            "message": f"Erro ao verificar status: {str(e)}",
            "scopes": [],
            "has_refresh_token": False
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

# --- Auth Routes ---

@app.get('/auth/login/google', tags=["Auth"])
async def login_google(request: Request):
    redirect_uri = request.url_for('auth_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get('/auth/callback/google', name='auth_google', tags=["Auth"])
async def auth_google(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        logger.error(f"Error during Google OAuth callback: {e}")
        raise HTTPException(status_code=400, detail="Could not authorize Google access token")

    user_info = token.get('userinfo')

    if user_info:
        oauth_provider = 'google'
        oauth_id = user_info['sub']
        email = user_info.get('email')

        # Find user by provider and oauth_id
        db_user = db.query(User).filter(User.oauth_provider == oauth_provider, User.oauth_id == oauth_id).first()

        if not db_user:
            # If not found, check if an account with that email already exists
            if email:
                db_user = db.query(User).filter(User.email == email).first()
                if db_user:
                    # Link account
                    db_user.oauth_provider = oauth_provider
                    db_user.oauth_id = oauth_id
                else:
                    # Create new user
                    db_user = User(
                        email=email,
                        oauth_provider=oauth_provider,
                        oauth_id=oauth_id
                    )
                    db.add(db_user)
            else:
                # Create new user without email
                db_user = User(
                    oauth_provider=oauth_provider,
                    oauth_id=oauth_id
                )
                db.add(db_user)
            
            db.commit()
            db.refresh(db_user)

        # Generate JWT
        jwt_payload = {
            "sub": db_user.id,
            "email": db_user.email,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }
        jwt_token = jwt.encode(jwt_payload, JWT_SECRET_KEY, algorithm="HS256")

        return {"access_token": jwt_token, "token_type": "bearer"}

    raise HTTPException(status_code=400, detail="Could not fetch user info from Google")


@app.get('/auth/login/apple', tags=["Auth"])
async def login_apple(request: Request):
    redirect_uri = request.url_for('auth_apple')
    return await oauth.apple.authorize_redirect(request, redirect_uri)


@app.post('/auth/callback/apple', name='auth_apple', tags=["Auth"])
async def auth_apple(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.apple.authorize_access_token(request)
    except Exception as e:
        logger.error(f"Error during Apple OAuth callback: {e}")
        raise HTTPException(status_code=400, detail="Could not authorize Apple access token")

    # O userinfo da Apple está dentro do id_token, que precisa ser decodificado
    user_info = await oauth.apple.parse_id_token(request, token)

    if user_info:
        oauth_provider = 'apple'
        oauth_id = user_info['sub']
        email = user_info.get('email')

        db_user = db.query(User).filter(User.oauth_provider == oauth_provider, User.oauth_id == oauth_id).first()

        if not db_user:
            if email:
                db_user = db.query(User).filter(User.email == email).first()
                if db_user:
                    db_user.oauth_provider = oauth_provider
                    db_user.oauth_id = oauth_id
                else:
                    db_user = User(email=email, oauth_provider=oauth_provider, oauth_id=oauth_id)
                    db.add(db_user)
            else:
                # A Apple só envia o email na primeira vez. Se não veio, o usuário já deve existir.
                # Se não existir, não podemos criar uma conta sem email.
                raise HTTPException(status_code=400, detail="Email not provided by Apple. Please try logging in with another method first.")
            
            db.commit()
            db.refresh(db_user)

        jwt_payload = {
            "sub": db_user.id,
            "email": db_user.email,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }
        jwt_token = jwt.encode(jwt_payload, JWT_SECRET_KEY, algorithm="HS256")

        return {"access_token": jwt_token, "token_type": "bearer"}

    raise HTTPException(status_code=400, detail="Could not fetch user info from Apple")


if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
