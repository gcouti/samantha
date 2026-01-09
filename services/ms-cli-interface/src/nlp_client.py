"""
Client for interacting with the NLP Processor service.
"""
import httpx
from typing import Dict, Any, Optional
import logging
from .config import config

logger = logging.getLogger(__name__)

class NLPClient:
    """Client for the NLP Processor service."""
    
    def __init__(self, base_url: Optional[str] = None, access_token: Optional[str] = None):
        self.base_url = (base_url or config.get_nlp_service_url()).rstrip('/')
        self.client = httpx.AsyncClient()
        self.timeout = config.get_cli_timeout()
        self.access_token = access_token
        
    async def process_text(
        self,
        text: str,
        email: Optional[str] = None,
        thread_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Send text to the NLP processor and get a response.
        
        Args:
            text: The text to process
            email: The user's email for authentication
            
        Returns:
            Dictionary containing the response and metadata
        """
        try:
            payload = {
                "text": text,
                "thread_id": thread_id or "default"  # Default thread_id as per API's ProcessRequest model
            }
            if email:
                payload["email"] = email

            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            if email:
                headers["X-User-Email"] = email

            try:
                response = await self.client.post(
                    f"{self.base_url}/process",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code in [401,403]:
                    # Authentication required
                    auth_url = f"{self.base_url}/auth/google/login"
                    print("\n❌ Authentication required!")
                    print(f"🔗 Please log in using Google: {auth_url}")
                    print("\nAfter logging in, you'll be redirected to a page with an error (this is normal).")
                    print("Copy the URL you're redirected to and run the following command:")
                    print(f"\n  python -m ms_cli_interface.cli auth --callback-url <redirected-url>\n")
                    return {"error": "Authentication required. Please log in using the provided URL."}
                raise e

        except httpx.HTTPStatusError as e:
            error_detail = ""
            if e.response.status_code == 401:
                error_detail = "Token de acesso inválido ou expirado. Por favor, faça login novamente."
            elif e.response.status_code == 403:
                error_detail = "Acesso negado. Verifique suas credenciais e tente novamente."
            elif e.response.status_code == 422:
                error_detail = "Dados inválidos na requisição."
            else:
                error_detail = f"Erro HTTP {e.response.status_code}"
                
            # Try to get more details from the response if available
            try:
                error_data = e.response.json()
                if 'detail' in error_data:
                    if isinstance(error_data['detail'], str):
                        error_detail = error_data['detail']
                    elif isinstance(error_data['detail'], list):
                        error_detail = "; ".join([str(d.get('msg', '')) for d in error_data['detail'] if 'msg' in d])
            except:
                pass
                
            logger.error("HTTP error %s: %s", e.response.status_code, error_detail)
            return {
                "response": f"Erro de autenticação: {error_detail}",
                "agent": "system",
                "confidence": 0.0,
                "requires_auth": e.response.status_code in (401, 403)
            }
        except httpx.RequestError as e:
            logger.error("Request error: %s", e)
            return {
                "response": "Não foi possível conectar ao serviço de processamento. Tente novamente mais tarde.",
                "agent": "system",
                "confidence": 0.0
            }
        except Exception as e:
            logger.error("Error processing text: %s", e, exc_info=True)
            return {
                "response": "Ocorreu um erro inesperado. Por favor, tente novamente.",
                "agent": "system",
                "confidence": 0.0
            }
    
    async def close(self) -> None:
        """Close the HTTP client."""
        try:
            await self.client.aclose()
        except Exception as e:
            logger.warning("Error closing HTTP client: %s", e)
