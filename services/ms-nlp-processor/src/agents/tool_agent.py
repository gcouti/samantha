"""Tool-enabled agent that can execute system commands and other tools."""
from typing import Dict, Any, List
import logging
import json
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class ToolAgent(BaseAgent):
    """Agent that can execute various tools including shell commands."""
    
    def __init__(self):
        super().__init__(
            name="tool_agent",
            description="Agent capable of executing system tools and commands"
        )
        self.tool_manager = ToolManager()
        self.llm_manager = LLMManager()
    
    def can_handle(self, intent: str, entities: Dict[str, Any]) -> bool:
        """Handle requests that require tool execution."""
        tool_keywords = [
            "executar", "rodar", "comando", "shell", "terminal",
            "sistema", "arquivo", "diretório", "lista", "procurar",
            "buscar", "encontrar", "informações", "status", "processo"
        ]
        
        text_lower = " ".join(entities.values()).lower() if entities else ""
        
        # Check if intent or entities contain tool-related keywords
        if any(keyword in intent.lower() for keyword in tool_keywords):
            return True
        
        if any(keyword in text_lower for keyword in tool_keywords):
            return True
        
        # Check for specific tool requests
        if "command" in entities or "tool" in entities:
            return True
        
        return False
    
    async def handle(self, text: str, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Process request using available tools."""
        try:
            # Step 1: Use LLM to determine which tool to use and parameters
            tool_selection = await self._select_tool_and_parameters(text, intent, entities)
            
            if not tool_selection["success"]:
                return {
                    "response": tool_selection["error"],
                    "agent": self.name,
                    "confidence": 0.3
                }
            
            tool_name = tool_selection["tool_name"]
            parameters = tool_selection["parameters"]
            
            # Step 2: Execute the tool
            result = await self.tool_manager.execute_tool(tool_name, parameters)
            
            # Step 3: Generate natural language response from tool result
            response = await self._generate_response_from_result(
                text, tool_name, parameters, result
            )
            
            return {
                "response": response,
                "agent": self.name,
                "confidence": 0.8 if result["success"] else 0.4,
                "metadata": {
                    "tool_used": tool_name,
                    "parameters": parameters,
                    "tool_result": result,
                    "tool_execution": True
                }
            }
            
        except Exception as e:
            logger.error(f"Error in tool agent: {str(e)}")
            return {
                "response": f"Desculpe, ocorreu um erro ao executar a ferramenta: {str(e)}",
                "agent": self.name,
                "confidence": 0.2,
                "error": str(e)
            }
    
    async def _select_tool_and_parameters(self, text: str, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to select appropriate tool and extract parameters."""
        try:
            # Get available tools
            available_tools = self.tool_manager.list_tools()
            tools_info = json.dumps(available_tools, indent=2)
            
            prompt = f"""
            Analise a solicitação do usuário e selecione a ferramenta apropriada.
            
            Solicitação: {text}
            Intenção: {intent}
            Entidades: {entities}
            
            Ferramentas disponíveis:
            {tools_info}
            
            Retorne um JSON com:
            {{
                "tool_name": "nome_da_ferramenta",
                "parameters": {{"param1": "valor1", "param2": "valor2"}},
                "reasoning": "motivo da escolha"
            }}
            
            Se nenhuma ferramenta for apropriada, retorne:
            {{
                "success": false,
                "error": "Nenhuma ferramenta apropriada encontrada"
            }}
            """
            
            messages = [
                SystemMessage(content="Você é um especialista em selecionar ferramentas para executar comandos do sistema."),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm_manager.llm.ainvoke(messages)
            content = response.content
            
            # Parse JSON response
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            try:
                result = json.loads(content)
                
                # Validate tool exists
                if "tool_name" in result:
                    tool = self.tool_manager.get_tool(result["tool_name"])
                    if not tool:
                        return {
                            "success": False,
                            "error": f"Ferramenta '{result['tool_name']}' não encontrada"
                        }
                
                return result
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse tool selection JSON: {content}")
                return {
                    "success": False,
                    "error": "Erro ao analisar seleção de ferramenta"
                }
                
        except Exception as e:
            logger.error(f"Error selecting tool: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao selecionar ferramenta: {str(e)}"
            }
    
    async def _generate_response_from_result(self, text: str, tool_name: str, parameters: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Generate natural language response from tool execution result."""
        try:
            if not result["success"]:
                return f"Não foi possível executar o comando. Erro: {result.get('error', 'Erro desconhecido')}"
            
            # Format the result for better presentation
            output = result.get("output", "")
            if len(output) > 500:
                output = output[:500] + "...\n[Output truncated]"
            
            prompt = f"""
            Formule uma resposta natural para o usuário baseada no resultado da ferramenta.
            
            Solicitação original: {text}
            Ferramenta usada: {tool_name}
            Parâmetros: {parameters}
            Resultado: {output}
            Código de saída: {result.get('exit_code', 'N/A')}
            
            Responda em português de forma clara e útil. Se o resultado for muito longo,
            summarize as informações mais importantes.
            """
            
            messages = [
                SystemMessage(content="Você é um assistente que interpreta resultados de ferramentas do sistema."),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm_manager.llm.ainvoke(messages)
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            # Fallback response
            if result["success"]:
                return f"Comando executado com sucesso. Saída: {result.get('output', '')[:200]}..."
            else:
                return f"Falha ao executar comando: {result.get('error', 'Erro desconhecido')}"
    
    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """List all available tools."""
        return self.tool_manager.list_tools()
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status using shell tool."""
        shell_tool = self.tool_manager.get_tool("shell_tool")
        if shell_tool:
            return await shell_tool.get_system_info()
        return {}
