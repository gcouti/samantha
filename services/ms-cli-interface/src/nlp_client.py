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
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or config.get_nlp_service_url()).rstrip('/')
        self.client = httpx.AsyncClient()
        self.timeout = config.get_cli_timeout()
        
    async def process_text(self, text: str) -> Dict[str, Any]:
        """
        Send text to the NLP processor and get a response.
        
        Args:
            text: The text to process
            
        Returns:
            Dictionary containing the response and metadata
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/process",
                json={"text": text},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error: %s", e)
            return {
                "response": "Desculpe, ocorreu um erro ao processar sua mensagem.",
                "agent": "system",
                "confidence": 0.0
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
