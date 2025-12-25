"""Email sending utility using SMTP."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailSender:
    """Utility class for sending emails via SMTP."""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str, sender_email: str, sender_name: str):
        """
        Initialize email sender with SMTP configuration.
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
            sender_email: Sender email address
            sender_name: Sender display name
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.sender_email = sender_email
        self.sender_name = sender_name
    
    def send_email(self, recipient_email: str, recipient_name: str, subject: str, body: str) -> bool:
        """
        Send a single email.
        
        Args:
            recipient_email: Recipient email address
            recipient_name: Recipient name
            subject: Email subject
            body: Email body (HTML or plain text)
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Create HTML version
            html_body = f"""
            <html>
              <body>
                {body.replace(chr(10), '<br>')}
              </body>
            </html>
            """
            
            # Attach parts
            text_part = MIMEText(body, 'plain')
            html_part = MIMEText(html_body, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False
    
    def send_batch(self, recipients: List[Dict[str, str]], email_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send emails to a batch of recipients.
        
        Args:
            recipients: List of recipient dictionaries with 'email' and 'name' keys
            email_content: Dictionary with email content (subject, full_content, etc.)
            
        Returns:
            Dictionary with sending results
        """
        results = {
            "total": len(recipients),
            "sent": 0,
            "failed": 0,
            "errors": []
        }
        
        subject = email_content.get("subject", "No Subject")
        body = email_content.get("full_content", email_content.get("body", ""))
        
        for recipient in recipients:
            email = recipient.get("email", "")
            name = recipient.get("name", "Customer")
            
            if self.send_email(email, name, subject, body):
                results["sent"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"Failed to send to {email}")
        
        return results

