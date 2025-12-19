"""
Tool manager for coordinating agent tools.
"""
import logging
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .shell_tool import ShellTool
from .weather_tool import WeatherTool

logger = logging.getLogger(__name__)

class ToolManager:
    """Manages and coordinates all available tools for agents."""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools."""
        self.register_tool(ShellTool())
        self.register_tool(WeatherTool())
    
    def register_tool(self, tool: BaseTool):
        """Register a new tool."""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools with their schemas."""
        tools_list = []
        
        for tool_name, tool in self.tools.items():
            tools_list.append({
                "name": tool.name,
                "description": tool.description,
                "schema": tool.get_schema()
            })
        
        return tools_list
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with given parameters."""
        tool = self.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found",
                "available_tools": list(self.tools.keys())
            }
        
        try:
            result = await tool.execute(parameters)
            result["tool_name"] = tool_name
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name
            }
    
    def get_tool_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Get schemas for all tools."""
        schemas = {}
        for tool_name, tool in self.tools.items():
            schemas[tool_name] = tool.get_schema()
        return schemas
    
    def validate_tool_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """Validate parameters for a specific tool."""
        tool = self.get_tool(tool_name)
        if not tool:
            return False
        
        return tool.validate_parameters(parameters)
