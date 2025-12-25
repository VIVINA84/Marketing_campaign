#!/usr/bin/env python3
"""
Script to run the SendGrid webhook handler.
This server receives webhook events from SendGrid for email tracking.
"""
import subprocess
import sys
import os

def main():
    """Run the webhook handler server."""
    print("🚀 Starting SendGrid Webhook Handler...")
    print("📡 Server will be available at: http://localhost:5002")
    print("🔗 Webhook endpoint: http://localhost:5002/webhook/sendgrid")
    print("📧 Configure this URL in your SendGrid dashboard")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)

    try:
        # Run the webhook handler
        subprocess.run([
            sys.executable,
            "utils/sendgrid_webhook_handler.py"
        ], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
