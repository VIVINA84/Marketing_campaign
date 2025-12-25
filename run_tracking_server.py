#!/usr/bin/env python3
"""
Script to run the email tracking server.
This server handles click tracking for email campaigns.
"""
import subprocess
import sys
import os

def main():
    """Run the tracking server."""
    print("🚀 Starting Email Tracking Server...")
    print("📡 Server will be available at: http://localhost:5001")
    print("🔗 Health check: http://localhost:5001/health")
    print("📧 Click tracking URLs: http://localhost:5001/track/click/{campaign_id}/{variant}/{email}")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)

    try:
        # Run the tracking server
        subprocess.run([
            sys.executable,
            "tracking_server.py"
        ], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
