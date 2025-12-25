"""Email Strategy Agent - Understands campaign brief and creates strategic plan."""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import json

class StrategyAgent:
    """Agent that analyzes marketing brief and creates campaign strategy."""
    
    def __init__(self, api_key: str):
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.7,
            openai_api_key=api_key
        )
    
    def create_strategy(self, brief: str) -> Dict[str, Any]:
        """
        Analyze marketing brief and create comprehensive campaign strategy.
        
        Args:
            brief: Marketing campaign brief text
            
        Returns:
            Dictionary containing campaign strategy
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert email marketing strategist. Analyze the marketing brief and create a comprehensive campaign strategy.
            
            Your strategy should include:
            1. Campaign Objectives - What are the main goals?
            2. Target Audience Profile - Who should receive these emails?
            3. Key Messages - What are the core messages to communicate?
            4. Email Sequence - How many emails and what's the cadence?
            5. Call-to-Actions - What actions should recipients take?
            6. Success Metrics - How will we measure success?
            
            Return your response as a structured JSON with these sections."""),
            ("user", "Marketing Brief:\n{brief}")
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({"brief": brief})
        
        # Parse the response and structure it
        strategy_text = response.content
        
        # Try to extract JSON if present, otherwise structure the text
        try:
            # Look for JSON in the response
            if "```json" in strategy_text:
                json_str = strategy_text.split("```json")[1].split("```")[0].strip()
                strategy = json.loads(json_str)
            elif "{" in strategy_text:
                # Try to find JSON object
                start = strategy_text.find("{")
                end = strategy_text.rfind("}") + 1
                json_str = strategy_text[start:end]
                strategy = json.loads(json_str)
            else:
                # Create structured response from text
                strategy = self._parse_strategy_text(strategy_text)
        except:
            strategy = self._parse_strategy_text(strategy_text)
        
        return {
            "raw_response": strategy_text,
            "strategy": strategy,
            "status": "completed"
        }
    
    def _parse_strategy_text(self, text: str) -> Dict[str, Any]:
        """Parse strategy text into structured format."""
        return {
            "objectives": self._extract_section(text, "objectives", "goals"),
            "target_audience": self._extract_section(text, "audience", "target"),
            "key_messages": self._extract_section(text, "messages", "message"),
            "email_sequence": self._extract_section(text, "sequence", "cadence"),
            "call_to_actions": self._extract_section(text, "cta", "call-to-action"),
            "success_metrics": self._extract_section(text, "metrics", "success")
        }
    
    def _extract_section(self, text: str, *keywords: str) -> str:
        """Extract section from text based on keywords."""
        text_lower = text.lower()
        for keyword in keywords:
            if keyword in text_lower:
                # Find the section
                idx = text_lower.find(keyword)
                # Get next 200 characters or until next section
                section = text[idx:idx+300]
                return section.strip()
        return "Not specified"

