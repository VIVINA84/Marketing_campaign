"""Deliverability and Compliance Agent - Ensures emails are valid, compliant, and not spam."""
from typing import Dict, List, Any
import re
from email_validator import validate_email, EmailNotValidError
import dns.resolver

class DeliverabilityAgent:
    """Agent that validates emails and checks spam compliance."""
    
    def __init__(self):
        self.spam_keywords = [
            "free", "urgent", "act now", "limited time", "click here",
            "buy now", "guarantee", "winner", "congratulations", "prize"
        ]
        self.compliance_checks = {
            "unsubscribe_required": True,
            "sender_info_required": True,
            "can_spam_compliant": True
        }
    
    def validate_email_address(self, email: str) -> Dict[str, Any]:
        """
        Validate email address format and domain.
        
        Args:
            email: Email address to validate
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "email": email,
            "valid": False,
            "errors": []
        }
        
        # Basic format check
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            result["errors"].append("Invalid email format")
            return result
        
        # Use email-validator for more thorough check
        try:
            validation = validate_email(email, check_deliverability=False)
            result["valid"] = True
            result["normalized"] = validation.normalized
        except EmailNotValidError as e:
            result["errors"].append(str(e))
        
        return result
    
    def check_spam_score(self, email_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check email content for spam indicators.
        
        Args:
            email_content: Dictionary with email content (subject, body, etc.)
            
        Returns:
            Dictionary with spam score and warnings
        """
        spam_score = 0
        warnings = []
        issues = []
        
        subject = email_content.get("subject", "").lower()
        body = email_content.get("body", "").lower()
        full_text = f"{subject} {body}"
        
        # Check for spam keywords
        found_keywords = [kw for kw in self.spam_keywords if kw in full_text]
        if found_keywords:
            spam_score += len(found_keywords) * 5
            warnings.append(f"Spam keywords detected: {', '.join(found_keywords)}")
        
        # Check for excessive capitalization
        caps_ratio = sum(1 for c in subject if c.isupper()) / len(subject) if subject else 0
        if caps_ratio > 0.5:
            spam_score += 10
            issues.append("Excessive capitalization in subject")
        
        # Check for excessive exclamation marks
        exclamation_count = subject.count("!") + body.count("!")
        if exclamation_count > 3:
            spam_score += 5
            issues.append("Too many exclamation marks")
        
        # Check subject length
        if len(email_content.get("subject", "")) > 50:
            spam_score += 3
            warnings.append("Subject line is too long (recommended: <50 characters)")
        
        # Check for links (too many links can be spammy)
        link_count = body.count("http://") + body.count("https://")
        if link_count > 3:
            spam_score += 5
            warnings.append("Too many links in email body")
        
        # Determine risk level
        if spam_score < 10:
            risk_level = "Low"
        elif spam_score < 20:
            risk_level = "Medium"
        else:
            risk_level = "High"
        
        return {
            "spam_score": spam_score,
            "risk_level": risk_level,
            "warnings": warnings,
            "issues": issues,
            "passed": spam_score < 20
        }
    
    def check_compliance(self, email_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check email for compliance with regulations (CAN-SPAM, etc.).
        
        Args:
            email_content: Dictionary with email content
            
        Returns:
            Dictionary with compliance check results
        """
        compliance_issues = []
        passed = True
        
        # Check for unsubscribe link
        body = email_content.get("body", "").lower()
        footer = email_content.get("footer", "").lower()
        full_text = f"{body} {footer}"
        
        unsubscribe_keywords = ["unsubscribe", "opt-out", "opt out", "remove"]
        has_unsubscribe = any(kw in full_text for kw in unsubscribe_keywords)
        
        if not has_unsubscribe and self.compliance_checks["unsubscribe_required"]:
            compliance_issues.append("Missing unsubscribe link/option")
            passed = False
        
        # Check for sender information
        if not email_content.get("footer", ""):
            compliance_issues.append("Missing sender information in footer")
            passed = False
        
        # Check for misleading subject
        subject = email_content.get("subject", "")
        if subject.startswith("Re:") or subject.startswith("Fwd:"):
            compliance_issues.append("Subject line may be misleading (starts with Re: or Fwd:)")
        
        return {
            "compliant": passed,
            "issues": compliance_issues,
            "checks_performed": {
                "unsubscribe_present": has_unsubscribe,
                "sender_info_present": bool(email_content.get("footer")),
                "subject_clear": not subject.startswith(("Re:", "Fwd:"))
            }
        }
    
    def validate_recipient_list(self, recipients: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Validate a list of email recipients.
        
        Args:
            recipients: List of recipient dictionaries with 'email' key
            
        Returns:
            Dictionary with validation summary
        """
        valid_emails = []
        invalid_emails = []
        
        for recipient in recipients:
            email = recipient.get("email", "")
            validation = self.validate_email_address(email)
            
            if validation["valid"]:
                valid_emails.append(recipient)
            else:
                invalid_emails.append({
                    "email": email,
                    "errors": validation["errors"]
                })
        
        return {
            "total": len(recipients),
            "valid": len(valid_emails),
            "invalid": len(invalid_emails),
            "valid_emails": valid_emails,
            "invalid_emails": invalid_emails,
            "validation_rate": (len(valid_emails) / len(recipients) * 100) if recipients else 0
        }
    
    def full_check(self, email_content: Dict[str, Any], recipients: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Perform full deliverability and compliance check.
        
        Args:
            email_content: Email content to check
            recipients: List of recipients to validate
            
        Returns:
            Comprehensive check results
        """
        spam_check = self.check_spam_score(email_content)
        compliance_check = self.check_compliance(email_content)
        validation_check = self.validate_recipient_list(recipients)
        
        all_passed = (
            spam_check["passed"] and
            compliance_check["compliant"] and
            validation_check["validation_rate"] > 90
        )
        
        return {
            "passed": all_passed,
            "spam_check": spam_check,
            "compliance_check": compliance_check,
            "validation_check": validation_check,
            "recommendations": self._generate_recommendations(spam_check, compliance_check, validation_check)
        }
    
    def _generate_recommendations(self, spam_check: Dict, compliance_check: Dict, validation_check: Dict) -> List[str]:
        """Generate recommendations based on check results."""
        recommendations = []
        
        if not spam_check["passed"]:
            recommendations.append("Reduce spam keywords and improve content quality")
        
        if spam_check["spam_score"] > 10:
            recommendations.append("Consider simplifying subject line and reducing promotional language")
        
        if not compliance_check["compliant"]:
            recommendations.append("Add unsubscribe link and ensure sender information is present")
        
        if validation_check["validation_rate"] < 95:
            recommendations.append("Review and clean invalid email addresses")
        
        if not recommendations:
            recommendations.append("Email is ready to send!")
        
        return recommendations

