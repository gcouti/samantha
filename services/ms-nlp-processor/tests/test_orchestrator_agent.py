"""Unit tests for OrchestratorAgent JSON parsing functionality."""

from unittest.mock import Mock, patch
from agents.orchestrator_agent import OrchestratorAgent


class TestOrchestratorAgent:
    """Test cases for OrchestratorAgent JSON parsing methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent = OrchestratorAgent(provider=Mock())
    
    def test_parse_json_response_valid_json(self):
        """Test parsing valid JSON content."""
        content = '{"key": "value", "number": 42}'
        response = Mock()
        
        result = self.agent._parse_json_response(content, response)
        
        assert result == {"key": "value", "number": 42}
    
    def test_parse_json_response_with_markdown_code_block(self):
        """Test parsing JSON content wrapped in markdown code blocks."""
        content = '```json\n{"agent": "weather", "confidence": 0.9}\n```'
        response = Mock()
        
        result = self.agent._parse_json_response(content, response)
        
        assert result == {"agent": "weather", "confidence": 0.9}
    
    def test_parse_json_response_with_markdown_no_language(self):
        """Test parsing JSON content wrapped in markdown without language specifier."""
        content = '```\n{"status": "success"}\n```'
        response = Mock()
        
        result = self.agent._parse_json_response(content, response)
        
        assert result == {"status": "success"}
    
    def test_parse_json_response_with_whitespace(self):
        """Test parsing JSON content with extra whitespace."""
        content = '```json\n\n  {"clean": true}  \n\n```'
        response = Mock()
        
        result = self.agent._parse_json_response(content, response)
        
        assert result == {"clean": True}
    
    def test_parse_json_response_invalid_json(self):
        """Test handling of invalid JSON content."""
        content = '{"invalid": json content}'
        response = Mock()
        
        with patch('src.agents.orchestrator_agent.logger') as mock_logger:
            result = self.agent._parse_json_response(content, response)
            
            assert result["success"] is False
            assert "Resposta inválida do modelo" in result["error"]
            mock_logger.error.assert_called()
    
    def test_parse_json_response_empty_string(self):
        """Test handling of empty string content."""
        content = ''
        response = Mock()
        
        with patch('src.agents.orchestrator_agent.logger') as mock_logger:
            result = self.agent._parse_json_response(content, response)
            
            assert result["success"] is False
            assert "Resposta inválida do modelo" in result["error"]
            mock_logger.error.assert_called()
    
    def test_parse_json_response_non_json_content(self):
        """Test handling of non-JSON content."""
        content = 'This is just plain text'
        response = Mock()
        
        with patch('src.agents.orchestrator_agent.logger') as mock_logger:
            result = self.agent._parse_json_response(content, response)
            
            assert result["success"] is False
            assert "Resposta inválida do modelo" in result["error"]
            mock_logger.error.assert_called()
    
    def test_parse_json_response_complex_nested_json(self):
        """Test parsing complex nested JSON structure."""
        content = '''```json
        {
            "agent": "task",
            "metadata": {
                "intent": "create_task",
                "entities": {
                    "task_name": "buy groceries",
                    "priority": "high"
                }
            },
            "confidence": 0.95
        }
        ```'''
        response = Mock()
        
        result = self.agent._parse_json_response(content, response)
        
        expected = {
            "agent": "task",
            "metadata": {
                "intent": "create_task",
                "entities": {
                    "task_name": "buy groceries",
                    "priority": "high"
                }
            },
            "confidence": 0.95
        }
        assert result == expected
    
    def test_parse_json_response_json_with_special_characters(self):
        """Test parsing JSON with special characters and Portuguese text."""
        content = '''```json
        {
            "response": "Olá! Como posso ajudar você hoje?",
            "agent": "general",
            "confidence": 0.88
        }
        ```'''
        response = Mock()
        
        result = self.agent._parse_json_response(content, response)
        
        expected = {
            "response": "Olá! Como posso ajudar você hoje?",
            "agent": "general",
            "confidence": 0.88
        }
        assert result == expected
