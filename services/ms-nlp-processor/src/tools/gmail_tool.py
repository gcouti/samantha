"""
Gmail tool for reading meeting notes from Gmail emails.
"""
import os
from langchain_core.tools import tool
from typing import Annotated, TypedDict, List
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_google_community.gmail.utils import build_resource_service
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from .base_tool import BaseTool

logger = logging.getLogger(__name__)


from google_auth_oauthlib.flow import Flow

# 1. Configuração inicial
# O arquivo client_secrets.json é o que você baixa do Google Cloud
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def iniciar_login():
    # Cria o objeto de fluxo
    flow = Flow.from_client_secrets_file(
        'client_secrets.json',
        scopes=SCOPES
    )
    
    # --- AQUI ESTÁ A RESPOSTA PARA SUA PERGUNTA ---
    # Você define explicitamente para onde o Google deve mandar o usuário de volta.
    # Esta string DEVE ser idêntica à cadastrada no Google Cloud Console.
    flow.redirect_uri = 'http://localhost:8000/callback'
    
    # Gera a URL que você vai mostrar para o usuário clicar
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    return authorization_url, state

def receber_callback(url_completa_recebida):
    """
    Esta função roda na rota '/callback' do seu servidor
    quando o usuário volta do Google.
    """
    flow = Flow.from_client_secrets_file(
        'client_secrets.json',
        scopes=SCOPES
    )
    
    # Precisamos reafirmar a redirect_uri aqui para validação
    flow.redirect_uri = 'http://localhost:8000/callback'
    
    # Troca o código (que veio na URL) pelo Token real
    # A url_completa_recebida seria algo como: "http://localhost:8000/callback?code=4/0Ad..."
    flow.fetch_token(authorization_response=url_completa_recebida)
    
    # PRONTO! Agora você tem as credenciais
    creds = flow.credentials
    
    return creds


class GmailTool(BaseTool):
    """Tool for reading meeting notes from Gmail emails."""
    
    def __init__(self):
        super().__init__(
            name="gmail_tool",
            description="Read meeting notes from Gmail emails based on search criteria"
        )
        
        # Gmail API configuration
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
        self.credentials_path = os.getenv('GMAIL_CREDENTIALS_PATH', 'credentials.json')
        self.token_path = os.getenv('GMAIL_TOKEN_PATH', 'token.json')
        self.service = None
        
    @tool
    def search_gmail_dynamic(query: str, config: RunnableConfig) -> str:
        """
        Busca emails no Gmail do usuário atual.
        Use esta ferramenta para encontrar informações em emails.
        """
        # A MÁGICA ACONTECE AQUI:
        # Recuperamos as credenciais que foram passadas no .invoke()
        # O 'configurable' é um dicionário reservado para dados de tempo de execução
        user_creds = config.get("configurable", {}).get("gmail_credentials")
        
        if not user_creds:
            return "Erro: Credenciais do Gmail não fornecidas na execução."

        try:
            # Montamos o serviço do Gmail AGORA, usando a credencial do usuário
            api_resource = build_resource_service(credentials=user_creds)
            
            # Lógica simplificada de busca usando a API do Google
            # (Aqui estou replicando o que o Toolkit faz por baixo dos panos)
            results = api_resource.users().messages().list(
                userId="me", q=query, maxResults=3
            ).execute()
            
            messages = results.get("messages", [])
            if not messages:
                return "Nenhum email encontrado."
                
            # Pega o snippet do primeiro email para simplificar o exemplo
            first_msg_id = messages[0]['id']
            msg_detail = api_resource.users().messages().get(
                userId="me", id=first_msg_id
            ).execute()
            
            return f"Email encontrado: {msg_detail.get('snippet')}"

        except Exception as e:
            return f"Erro ao acessar Gmail: {str(e)}"