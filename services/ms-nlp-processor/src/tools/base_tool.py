"""
Base class for all agent tools.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class BaseTool(ABC):
    """Base class for all tools that agents can execute."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.safe_commands = []
        
    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with given parameters.
        
        Args:
            parameters: Tool execution parameters
            
        Returns:
            Dict containing execution result and metadata
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the tool schema for parameter validation and documentation.
        
        Returns:
            Dict containing tool schema
        """
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate parameters against tool schema.
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            True if parameters are valid, False otherwise
        """
        schema = self.get_schema()
        required_params = schema.get("required", [])
        
        # Check required parameters
        for param in required_params:
            if param not in parameters:
                logger.error(f"Missing required parameter: {param}")
                return False
        
        # Check parameter types
        param_types = schema.get("properties", {})
        for param_name, param_value in parameters.items():
            if param_name in param_types:
                expected_type = param_types[param_name].get("type")
                if expected_type == "string" and not isinstance(param_value, str):
                    logger.error(f"Parameter {param_name} must be a string")
                    return False
                elif expected_type == "integer" and not isinstance(param_value, int):
                    logger.error(f"Parameter {param_name} must be an integer")
                    return False
                elif expected_type == "array" and not isinstance(param_value, list):
                    logger.error(f"Parameter {param_name} must be an array")
                    return False
        
        return True
    
    def is_safe_command(self, command: str) -> bool:
        """
        Check if a command is safe to execute.
        
        Args:
            command: Command to check
            
        Returns:
            True if command is safe, False otherwise
        """
        dangerous_commands = [
            "rm -rf", "sudo", "chmod 777", "chown", "passwd",
            "su", "sudo su", "mkfs", "fdisk", "format", "del",
            "rmdir", "move", "copy", "xcopy", "format.com"
        ]
        
        command_lower = command.lower()
        for dangerous in dangerous_commands:
            if dangerous in command_lower:
                logger.warning(f"Dangerous command detected: {command}")
                return False
        
        return True
