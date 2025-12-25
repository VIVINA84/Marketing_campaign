"""Personalization Agent - Uses GenAI to generate personalized email content."""
from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import json

class PersonalizationAgent:
    """Agent that generates personalized email content using GenAI."""
    
    def __init__(self, api_key: str):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.8,
            openai_api_key=api_key
        )
    
    def generate_email_content(self, strategy: Dict[str, Any], recipient: Dict[str, str] = None, variant: str = "A", campaign_id: str = None) -> Dict[str, Any]:
        """
        Generate personalized email content based on strategy and recipient.

        Args:
            strategy: Campaign strategy from StrategyAgent
            recipient: Recipient information (name, email, etc.)
            variant: A/B test variant identifier
            campaign_id: Campaign ID for tracking

        Returns:
            Dictionary containing email content (subject, body, etc.)
        """
        recipient_name = recipient.get("name", "Valued Customer") if recipient else "Valued Customer"
        recipient_email = recipient.get("email", "") if recipient else ""
        recipient_context = f"Recipient: {recipient_name}" if recipient else ""

        # Create variant-specific instructions
        variant_instructions = {
            "A": "Write a professional, direct email with clear call-to-action.",
            "B": "Write a friendly, conversational email with engaging storytelling.",
            "C": "Write a concise, benefit-focused email with urgency."
        }
        variant_instruction = variant_instructions.get(variant, variant_instructions["A"])

        # Use SendGrid's built-in click tracking - no custom tracking link needed
        # SendGrid will automatically track clicks and send webhooks
        tracking_link = "https://yourapp.com/offer"  # Placeholder - SendGrid handles tracking
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert email copywriter specializing in personalized, engaging email campaigns.
            
            Create a compelling marketing email that:
            1. Has a catchy, personalized subject line
            2. Includes a personalized greeting
            3. Delivers the key messages from the campaign strategy
            4. Has a clear, compelling call-to-action
            5. Is optimized for email deliverability (not spammy)
            
            Style: {variant_instruction}
            
            Return your response as JSON with: subject, greeting, body, cta, footer"""),
            ("user", """Campaign Strategy:
{strategy}

{recipient_context}

Generate a personalized email for variant {variant}.""")
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({
            "strategy": json.dumps(strategy, indent=2),
            "recipient_context": recipient_context,
            "variant": variant,
            "variant_instruction": variant_instruction,
            "tracking_link": tracking_link
        })
        
        content_text = response.content
        
        # Parse response
        try:
            if "```json" in content_text:
                json_str = content_text.split("```json")[1].split("```")[0].strip()
                email_content = json.loads(json_str)
            elif "{" in content_text:
                start = content_text.find("{")
                end = content_text.rfind("}") + 1
                json_str = content_text[start:end]
                email_content = json.loads(json_str)
            else:
                email_content = self._parse_email_text(content_text, recipient_name)
        except:
            email_content = self._parse_email_text(content_text, recipient_name)
        
        # Ensure all required fields with strong fallbacks
        subject = (email_content.get("subject") or "").strip()
        body = (email_content.get("body") or "").strip()
        greeting = (email_content.get("greeting") or f"Hello {recipient_name},").strip()
        cta = (email_content.get("cta") or f"Click here to learn more: {tracking_link}").strip()
        footer = (email_content.get("footer") or "Best regards,\nMarketing Team").strip()

        if not subject:
            subject = f"Special offer for {recipient_name}".strip()
        if not body:
            # fallback to the raw LLM text minus obvious JSON fences
            cleaned = content_text.replace("```json", "").replace("```", "").strip() if content_text else ""
            # if still empty, provide a generic body based on strategy
            strategy_hint = ""
            try:
                if isinstance(strategy, dict):
                    strategy_hint = json.dumps(strategy.get("key_messages") or strategy, indent=0)[:300]
            except Exception:
                strategy_hint = ""
            body = cleaned or (f"We're excited to share this update with you.\n\n{strategy_hint}".strip())
        
        full_content = self._assemble_email({
            "greeting": greeting,
            "body": body,
            "cta": cta,
            "footer": footer
        }, recipient_name)

        return {
            "variant": variant,
            "subject": subject,
            "greeting": greeting,
            "body": body,
            "cta": cta,
            "footer": footer,
            "full_content": full_content
        }
    
    def _parse_email_text(self, text: str, recipient_name: str) -> Dict[str, Any]:
        """Parse email text into structured format."""
        lines = text.split("\n")
        subject = ""
        body = ""
        cta = "Learn More"
        
        for i, line in enumerate(lines):
            if "subject" in line.lower() or "subject:" in line.lower():
                subject = line.split(":")[-1].strip() if ":" in line else lines[i+1].strip()
            elif "cta" in line.lower() or "call" in line.lower():
                cta = line.split(":")[-1].strip() if ":" in line else "Learn More"
        
        body = "\n".join([l for l in lines if l.strip() and "subject" not in l.lower()])
        
        return {
            "subject": subject or f"Special Offer for {recipient_name}",
            "body": body or text,
            "cta": cta
        }
    
    def _assemble_email(self, content: Dict[str, Any], recipient_name: str) -> str:
        """Assemble full email from components."""
        greeting = content.get("greeting", f"Hello {recipient_name},")
        body = content.get("body", "")
        cta = content.get("cta", "Learn More")
        footer = content.get("footer", "Best regards,\nMarketing Team")
        
        return f"""{greeting}

{body}

{cta}

{footer}"""

    def generate_ab_variants(self, strategy: Dict[str, Any], recipient: Dict[str, str], num_variants: int = 2) -> List[Dict[str, Any]]:
        """Generate multiple A/B test variants for a recipient."""
        variants = []
        variant_labels = ["A", "B", "C"][:num_variants]
        
        for variant in variant_labels:
            content = self.generate_email_content(strategy, recipient, variant)
            variants.append(content)
        
        return variants

