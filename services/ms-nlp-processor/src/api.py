"""
FastAPI application for the NLP Processor service with LLM and LangFlow integration.
"""
import os
import jwt
import json
import glob
import uvicorn
import logging
from datetime import datetime, timedelta

from auth import oauth
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, HTTPException, Request, Query, Depends, Header, status, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from security import get_current_user_email, verify_email_in_request
from auth import oauth, create_access_token, JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

from processor import NLPProcessor
from tools.gmail_tool import iniciar_login, receber_callback
from starlette.requests import Request
from starlette.responses import RedirectResponse

from sqlalchemy.orm import Session
from database.models import Account
from database.database import get_db

load_dotenv()
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-secret-key")

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize the FastAPI app
app = FastAPI(
    title="Samantha NLP Processor",
    description="NLP processing service with LLM and LangFlow multi-agent system for Samantha assistant",
    version="2.0.0"
)

# Add Session Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "your-secret-key-change-in-production"),
    session_cookie="session"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
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
    email: Optional[str] = None

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
    message: str
    credentials_stored: bool = False

class HealthResponse(BaseModel):
    status: str
    service: str
    llm_enabled: bool = True
    langflow_available: bool = False
    langgraph_available: bool = False

@app.post("/process", response_model=ProcessResponse)
async def process_text(
    request: Request,
    request_data: ProcessRequest,
    authorization: str = Header(..., description="JWT token"),
    x_user_email: str = Header(..., description="User's email address")
):
    """
    Process natural language text and return a response.
    
    Args:
        request: The request object
        request_data: The request containing the text to process and optional context
        authorization: JWT token in the format 'Bearer <token>'
        x_user_email: User's email address
        
    Returns:
        The processed response with metadata
        
    Raises:
        HTTPException: If authentication fails or email doesn't match
    """
    # Verify JWT token and get the email from it
    token_email = get_current_user_email(request)
    
    # Verify if the email in the token matches the email in the header
    # if not verify_email_in_request(token_email, request):
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Email in token doesn't match the provided email"
    #     )
    
    # Verify if the email in the request body matches the token email
    if request_data.email and request_data.email.lower() != token_email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email in request body doesn't match the authenticated email"
        )
    
    try:
        # Delegate processing method selection to the processor
        result = await nlp_processor.process_text(
            request_data.text, 
            thread_id=request_data.thread_id,
            email=token_email
        )
        
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
                "context": request_data.context
            }
        )
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversation/{thread_id}")
async def get_conversation_history(
    thread_id: str,
    request: Request,
    authorization: str = Header(..., description="JWT token"),
    x_user_email: str = Header(..., description="User's email address")
):
    """
    Get conversation history for a specific thread.
    
    Args:
        thread_id: The ID of the conversation thread
        request: The request object
        authorization: JWT token in the format 'Bearer <token>'
        x_user_email: User's email address
        
    Returns:
        The conversation history for the specified thread
        
    Raises:
        HTTPException: If authentication fails or email doesn't match
    """
    # Verify JWT token and get the email from it
    token_email = get_current_user_email(request)
    
    # Verify if the email in the token matches the email in the header
    if not verify_email_in_request(token_email, request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email in token doesn't match the provided email"
        )
    
    try:
        # Pass the email to ensure the user can only access their own conversations
        history = await nlp_processor.get_conversation_history(thread_id, email=token_email)
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
    """
    Health check endpoint with LLM, LangFlow, and LangGraph status.
    This endpoint does not require authentication.
    """
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
async def list_agents(
    request: Request,
    authorization: str = Header(..., description="JWT token"),
    x_user_email: str = Header(..., description="User's email address")
):
    """
    List available agents in the system by scanning the agents directory.
    
    Args:
        request: The request object
        authorization: JWT token in the format 'Bearer <token>'
        x_user_email: User's email address
        
    Returns:
        List of available agents with their descriptions
        
    Raises:
        HTTPException: If authentication fails or email doesn't match
    """
    # Verify JWT token and get the email from it
    token_email = get_current_user_email(request)
    
    # Verify if the email in the token matches the email in the header
    if not verify_email_in_request(token_email, request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email in token doesn't match the provided email"
        )
    
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

class Token(BaseModel):
    """Token response model for authentication endpoints."""
    access_token: str
    token_type: str
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: dict = Field(..., description="User information")

class UserResponse(BaseModel):
    """User information response model."""
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    is_active: bool = True

@app.get("/auth/google/login", tags=["Authentication"])
async def login_google(request: Request):
    """
    Iniciar autenticação com Google.
    
    Redireciona para a página de login do Google e depois para o callback.
    """
    try:
        # Get the base URL from the request
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/auth/google/callback"
        
        # Configure the OAuth client with the dynamic redirect_uri
        oauth.google.client_kwargs['redirect_uri'] = redirect_uri
        
        # Generate the authorization URL and redirect
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        logger.error(f"Error in Google login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Google login"
        )

@app.get("/auth/google/callback", response_model=Token, tags=["Authentication"])
async def auth_google_callback(
    request: Request, 
    db: Session = Depends(get_db)
):
    """
    Callback para autenticação com Google.
    
    Processa a resposta do Google após o login e retorna um JWT token.
    """
    try:
        # Get the token from Google
        token = await oauth.google.authorize_access_token(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not get token from Google"
            )
        
        # Get user info from Google
        user_info = token.get('userinfo')
        if not user_info or 'email' not in user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not get user email from Google"
            )
        
        # Get or create user in database
        user = db.query(Account).filter(Account.email == user_info['email']).first()
        if not user:
            # Create new user if not exists
            user = Account(
                email=user_info['email'],
                name=user_info.get('name', user_info['email'].split('@')[0]),
                picture=user_info.get('picture'),
                is_active=True,
                oauth_provider='google',
                oauth_id=user_info.get('sub')
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Create JWT token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "email": user.email},
            expires_delta=access_token_expires
        )
        
        # Prepare user data for response
        user_data = {
            "email": user.email,
            "name": user.name,
            "is_active": user.is_active
        }
        if user.picture:
            user_data["picture"] = user.picture
        
        # Return the token and user info
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds()),
            "user": user_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Google auth callback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during authentication"
        )

@app.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
async def get_current_user(
    request: Request,
    authorization: str = Header(..., description="JWT token in format 'Bearer <token>'"),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user information.
    
    Returns the user information for the authenticated user based on the JWT token.
    """
    try:
        # Get token from Authorization header
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = authorization.split(" ")[1]
        
        # Verify token and get user email
        payload = verify_jwt_token(token)
        if not payload or "email" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        user = db.query(Account).filter(Account.email == payload["email"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Return user data
        user_data = {
            "email": user.email,
            "name": user.name,
            "is_active": user.is_active
        }
        if user.picture:
            user_data["picture"] = user.picture
            
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching user information"
        )

# Apple OAuth Routes

@app.get('/auth/apple/login', tags=["Authentication"])
async def login_apple(request: Request):
    """
    Iniciar autenticação com Apple.
    
    Redireciona para a página de login da Apple e depois para o callback.
    """
    try:
        # Get the base URL from the request
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/auth/apple/callback"
        
        # Configure the OAuth client with the dynamic redirect_uri
        oauth.apple.client_kwargs['redirect_uri'] = redirect_uri
        
        # Generate the authorization URL and redirect
        return await oauth.apple.authorize_redirect(request, redirect_uri)
    except Exception as e:
        logger.error(f"Error in Apple login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Apple login"
        )

@app.post('/auth/apple/callback', response_model=Token, tags=["Authentication"])
async def auth_apple_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Callback para autenticação com Apple.
    
    Processa a resposta da Apple após o login e retorna um JWT token.
    """
    try:
        # Get the token from Apple
        token = await oauth.apple.authorize_access_token(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not get token from Apple"
            )
        
        # Get user info from Apple
        user_info = await oauth.apple.parse_id_token(request, token)
        if not user_info or 'sub' not in user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not get user info from Apple"
            )
        
        email = user_info.get('email')
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required but not provided by Apple"
            )
        
        # Get or create user in database
        user = db.query(Account).filter(Account.email == email).first()
        if not user:
            # Create new user if not exists
            user = Account(
                email=email,
                name=user_info.get('name', email.split('@')[0]),
                picture=user_info.get('picture'),
                is_active=True,
                oauth_provider='apple',
                oauth_id=user_info['sub']
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Create JWT token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "email": user.email},
            expires_delta=access_token_expires
        )
        
        # Prepare user data for response
        user_data = {
            "email": user.email,
            "name": user.name,
            "is_active": user.is_active
        }
        if user.picture:
            user_data["picture"] = user.picture
        
        # Return the token and user info
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds()),
            "user": user_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Apple auth callback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during authentication"
        )


@app.get("/test-token/{email}", tags=["Testing"])
async def get_test_token(email: str):
    """
    Generate a test JWT token for development.
    WARNING: This is for development use only! Remove in production.
    """
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": email, "email": email},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "email": email,
        "expires_in": int(access_token_expires.total_seconds())
    }


if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
