"""SendGrid email sender with tracking capabilities."""
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Personalization, CustomArg
from sendgrid.helpers.mail import TrackingSettings, ClickTracking, OpenTracking, MailSettings
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SendGridSender:
    """SendGrid email sender with activity tracking."""
    
    def __init__(self, api_key: str, from_email: str, from_name: str = "Marketing Campaign System", sandbox: bool = False):
        """
        Initialize SendGrid sender.
        
        Args:
            api_key: SendGrid API key
            from_email: Sender email address (must be verified in SendGrid)
            from_name: Sender display name
        """
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name
        self.client = SendGridAPIClient(api_key)
        self.message_ids = {}  # Track message IDs for each recipient
        self.sandbox = sandbox
    
    def send_email(self, recipient_email: str, recipient_name: str, subject: str, 
                   body: str, variant: str = "A", campaign_id: str = "") -> Dict[str, Any]:
        """
        Send a single email via SendGrid.
        
        Args:
            recipient_email: Recipient email address
            recipient_name: Recipient name
            subject: Email subject
            body: Email body (HTML or plain text)
            variant: A/B test variant identifier
            campaign_id: Campaign identifier for tracking
            
        Returns:
            Dictionary with send result and message ID
        """
        try:
            # Create HTML version
            html_body = f"""
            <html>
              <body>
                {body.replace(chr(10), '<br>')}
              </body>
            </html>
            """
            
            # Create email message
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(recipient_email, recipient_name),
                subject=subject,
                html_content=Content("text/html", html_body)
            )

            # Add plain text as alternate part via add_content (Mail already set html)
            message.add_content(Content("text/plain", body))
            
            # Add custom tracking data (use add_custom_arg on the Personalization)
            # Ensure a Personalization exists
            if not message.personalizations:
                personalization = Personalization()
                personalization.add_to(Email(recipient_email, recipient_name))
                message.add_personalization(personalization)
            personalization = message.personalizations[0]
            personalization.add_custom_arg(CustomArg("campaign_id", campaign_id or ""))
            personalization.add_custom_arg(CustomArg("variant", variant or ""))
            personalization.add_custom_arg(CustomArg("recipient_email", recipient_email or ""))
            
            # Enable click and open tracking (use TrackingSettings helper)
            ts = TrackingSettings()
            ts.click_tracking = ClickTracking(enable=True, enable_text=True)
            ts.open_tracking = OpenTracking(enable=True)
            message.tracking_settings = ts

            # Optional: Sandbox mode for testing without real delivery
            if self.sandbox:
                ms = MailSettings()
                # Some sendgrid versions do not expose SandboxMode; use dict form to enable
                try:
                    ms.sandbox_mode = {"enable": True}
                except Exception:
                    # Fallback: attach mail_settings as dict
                    message.mail_settings = {"sandbox_mode": {"enable": True}}
                else:
                    message.mail_settings = ms
            
            # Send email
            logger.info(f"📤 Attempting to send email to {recipient_email} via SendGrid...")
            response = self.client.send(message)
            
            # Extract message ID and status code
            message_id = ""
            status_code = 202  # Default accepted status
            
            # Handle response (SendGrid returns a Response object)
            try:
                # Get status code
                if hasattr(response, 'status_code'):
                    status_code = response.status_code
                elif hasattr(response, 'status'):
                    status_code = response.status
                
                # Get headers and message ID
                headers = getattr(response, 'headers', None)
                if headers:
                    try:
                        # CaseInsensitiveDict supports get directly
                        message_id = headers.get('X-Message-Id') or headers.get('x-message-id') or ""
                    except Exception:
                        try:
                            headers_dict = dict(headers)
                            message_id = headers_dict.get('X-Message-Id') or headers_dict.get('x-message-id') or ""
                        except Exception:
                            message_id = ""
                
                logger.info(f"📬 SendGrid Response - Status: {status_code}, Message ID: {message_id or 'Not provided'}")
                
            except Exception as header_error:
                logger.warning(f"⚠️ Could not extract response details: {str(header_error)}")
                status_code = 202
            
            # Store message ID for tracking
            if message_id:
                key = f"{campaign_id}_{variant}_{recipient_email}"
                self.message_ids[key] = message_id
            
            # Check if send was successful (202 = accepted, 200 = OK)
            # SendGrid typically returns 202 for accepted emails
            if status_code in [200, 202]:
                logger.info(f"✅ Email accepted by SendGrid for {recipient_email} (Status: {status_code})")
                return {
                    "success": True,
                    "message_id": message_id,
                    "status_code": status_code,
                    "recipient": recipient_email,
                    "sandbox": self.sandbox,
                }
            else:
                logger.error(f"❌ SendGrid returned non-success status {status_code} for {recipient_email}")
                return {
                    "success": False,
                    "error": f"SendGrid returned status {status_code}",
                    "status_code": status_code,
                    "recipient": recipient_email,
                    "sandbox": self.sandbox,
                }
            
        except Exception as e:
            logger.error(f"❌ Failed to send email to {recipient_email}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "recipient": recipient_email,
                "sandbox": self.sandbox,
            }
    
    def send_batch(self, recipients: List[Dict[str, str]], email_content: Dict[str, Any],
                   variant: str = "A", campaign_id: str = "") -> Dict[str, Any]:
        """
        Send batch emails via SendGrid.
        
        Args:
            recipients: List of recipient dictionaries
            email_content: Email content dictionary
            variant: A/B test variant
            campaign_id: Campaign identifier
            
        Returns:
            Dictionary with batch send results
        """
        logger.info(f"📦 Starting batch send: {len(recipients)} recipients, variant {variant}")
        
        results = {
            "total": len(recipients),
            "sent": 0,
            "failed": 0,
            "message_ids": [],
            "errors": [],
            "per_recipient": [],
            "sandbox": self.sandbox,
        }
        
        if not recipients:
            logger.error("❌ No recipients provided for batch send")
            return results
        
        # Stronger content fallback
        subject = (email_content.get("subject") or "").strip() or "Update from our team"
        body = (email_content.get("full_content") or email_content.get("body") or email_content.get("content") or "").strip()
        if not body:
            # Provide a minimal safe body
            body = "Hello,\n\nWe wanted to share an update with you.\n\nBest regards,\nTeam"
        
        if not subject or not body:
            logger.error(f"❌ Missing email content - Subject: {bool(subject)}, Body: {bool(body)}")
            results["errors"].append({"error": "Missing email subject or body"})
            return results
        
        logger.info(f"📧 Sending emails with subject: {subject[:50]}...")
        
        for i, recipient in enumerate(recipients):
            email = recipient.get("email", "")
            name = recipient.get("name", "Customer")
            
            if not email:
                logger.warning(f"⚠️ Skipping recipient {i+1}: No email address")
                results["failed"] += 1
                results["errors"].append({"email": "N/A", "error": "No email address"})
                continue
            
            logger.info(f"📨 Sending email {i+1}/{len(recipients)} to {email}")
            result = self.send_email(email, name, subject, body, variant, campaign_id)
            
            results["per_recipient"].append({
                "email": email,
                "success": bool(result.get("success")),
                "message_id": result.get("message_id"),
                "status_code": result.get("status_code"),
                "error": result.get("error"),
            })

            if result.get("success"):
                results["sent"] += 1
                if result.get("message_id"):
                    results["message_ids"].append({
                        "email": email,
                        "message_id": result["message_id"]
                    })
                logger.info(f"✅ Email {i+1} sent successfully to {email}")
            else:
                results["failed"] += 1
                error_msg = result.get("error", "Unknown error")
                results["errors"].append({
                    "email": email,
                    "error": error_msg
                })
                logger.error(f"❌ Email {i+1} failed to {email}: {error_msg}")
        
        logger.info(f"📊 Batch send complete: {results['sent']} sent, {results['failed']} failed out of {results['total']} total")
        return results
    
    def get_message_ids(self, campaign_id: str, variant: str) -> List[str]:
        """Get all message IDs for a campaign variant."""
        message_ids = []
        prefix = f"{campaign_id}_{variant}_"
        for key, msg_id in self.message_ids.items():
            if key.startswith(prefix):
                message_ids.append(msg_id)
        return message_ids

