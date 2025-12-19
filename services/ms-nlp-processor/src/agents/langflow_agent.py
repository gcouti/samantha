"""
LangFlow-based agent for complex multi-agent workflows.
"""
from typing import Dict, Any, Optional
import logging
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class LangFlowAgent(BaseAgent):
    """Agent that uses LangFlow for complex decision making and workflows."""
    
    def __init__(self, flow_id: Optional[str] = None):
        super().__init__(
            name="langflow_agent",
            description="Complex multi-agent workflows using LangFlow"
        )
        self.flow_id = flow_id
        self.langflow_manager = LangFlowManager()
    
    def can_handle(self, intent: str, entities: Dict[str, Any]) -> bool:
        """Handle complex intents that require multi-agent coordination."""
        complex_intents = [
            "general_question",
            "complex_task",
            "multi_step_request"
        ]
        return intent in complex_intents or len(entities) > 2
    
    async def handle(self, text: str, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Process request using LangFlow workflow."""
        try:
            if not self.flow_id:
                # Fallback to simple processing if no flow specified
                return await self._fallback_processing(text, intent, entities)
            
            # Prepare inputs for LangFlow
            inputs = {
                "text": text,
                "intent": intent,
                "entities": entities,
                "user_context": {}
            }
            
            # Run LangFlow workflow
            async with self.langflow_manager as manager:
                result = await manager.run_flow(self.flow_id, inputs)
                
                if "error" in result:
                    logger.error(f"LangFlow error: {result['error']}")
                    return await self._fallback_processing(text, intent, entities)
                
                # Extract response from LangFlow result
                response = result.get("outputs", {}).get("response", "Processamento concluído.")
                confidence = result.get("outputs", {}).get("confidence", 0.8)
                
                return {
                    "response": response,
                    "agent": self.name,
                    "confidence": confidence,
                    "metadata": {
                        "flow_id": self.flow_id,
                        "langflow_result": result
                    }
                }
                
        except Exception as e:
            logger.error(f"Error in LangFlow agent: {str(e)}")
            return await self._fallback_processing(text, intent, entities)
    
    async def _fallback_processing(self, text: str, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback processing when LangFlow is not available."""
        from ..llm_integration import LLMManager
        
        llm_manager = LLMManager()
        response = await llm_manager.generate_response(
            text, 
            {"intent": intent, "entities": entities, "agent": self.name}
        )
        
        return {
            "response": response,
            "agent": self.name,
            "confidence": 0.7,
            "metadata": {"fallback": True}
        }
