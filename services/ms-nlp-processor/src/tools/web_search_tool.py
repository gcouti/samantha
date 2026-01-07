"""
Web search tool for performing internet searches.
"""
import logging
from typing import Dict, Any
from .base_tool import BaseTool
from duckduckgo_search import DDGS
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

class WebSearchTool(BaseTool):
    """Tool for performing web searches using DuckDuckGo."""

    def __init__(self):
        super().__init__(
            name="web_search",
            description="Perform a web search using DuckDuckGo to find information on the internet."
        )

    @tool
    async def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a web search.

        Args:
            parameters: Dict containing 'query' (the search query).

        Returns:
            Dict containing search results.
        """
        query = parameters.get("query")
        if not query:
            return {
                "success": False,
                "error": "Query parameter is required",
                "data": None
            }

        try:
            with DDGS() as ddgs:
                results = [r for r in ddgs.text(query, max_results=5)]
            
            return {
                "success": True,
                "data": results,
                "query": query,
                "source": "duckduckgo"
            }
        except Exception as e:
            logger.error(f"Error performing web search: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    def get_schema(self) -> Dict[str, Any]:
        """Get the tool schema."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find information on the internet."
                }
            },
            "required": ["query"]
        }
