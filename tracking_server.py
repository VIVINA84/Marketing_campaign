"""
Tracking Server for Email Click Tracking
Runs a Flask server to handle click tracking and log activities to CSV.
"""
from flask import Flask, redirect, request
from utils.user_activity_tracker import UserActivityTracker
import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
activity_tracker = UserActivityTracker(config.DATA_DIR)

@app.route('/track/click/<campaign_id>/<variant>/<encoded_email>')
def track_click(campaign_id, variant, encoded_email):
    """
    Track email clicks and redirect to offer page.

    Args:
        campaign_id: Campaign identifier
        variant: A/B test variant (A, B, etc.)
        encoded_email: Email address with @ and . replaced for URL safety
    """
    try:
        # Decode email
        email = encoded_email.replace('_at_', '@').replace('_dot_', '.')

        # Log the click activity
        activity_tracker.log_activity(
            campaign_id=campaign_id,
            variant=variant,
            email=email,
            action='click',
            details=f'IP: {request.remote_addr}, User-Agent: {request.headers.get("User-Agent", "")}'
        )

        logger.info(f"Tracked click: Campaign {campaign_id}, Variant {variant}, Email {email}")

        # Redirect to the actual offer page
        # You can customize this URL based on your needs
        # For now, redirect to a placeholder offer page
        offer_url = f"https://yourapp.com/offer?campaign={campaign_id}&variant={variant}"

        return redirect(offer_url, code=302)

    except Exception as e:
        logger.error(f"Error tracking click: {str(e)}")
        # Still redirect even if logging fails
        return redirect("https://yourapp.com/offer", code=302)

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "email-tracking"}

if __name__ == '__main__':
    # Run the tracking server
    app.run(
        host='0.0.0.0',
        port=5001,  # Use a different port than Streamlit (which typically uses 8501)
        debug=False
    )
