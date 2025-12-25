"""
SendGrid Webhook Handler for Email Activity Tracking
Receives webhook events from SendGrid and logs activities to CSV.
"""
from flask import Flask, request, jsonify
from utils.user_activity_tracker import UserActivityTracker
import config
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
activity_tracker = UserActivityTracker(config.DATA_DIR)

@app.route('/webhook/sendgrid', methods=['POST'])
def sendgrid_webhook():
    """
    Handle SendGrid webhook events for email activities.

    Expected events: processed, delivered, open, click, bounce, etc.
    """
    try:
        # Get the raw data
        data = request.get_json(silent=True)
        if not data:
            logger.warning("No JSON data received in webhook")
            return jsonify({"status": "error", "message": "No data"}), 400

        logger.info(f"Received SendGrid webhook: {len(data)} events")

        # Process each event
        for event in data:
            process_sendgrid_event(event)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.error(f"Error processing SendGrid webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def process_sendgrid_event(event):
    """
    Process a single SendGrid event and log to CSV.

    Args:
        event: SendGrid event dictionary
    """
    try:
        event_type = event.get('event')
        email = event.get('email')
        timestamp = event.get('timestamp')

        # Extract custom args (campaign_id, variant, recipient_email)
        custom_args = event.get('custom_args', {})

        campaign_id = custom_args.get('campaign_id', 'unknown')
        variant = custom_args.get('variant', 'unknown')
        recipient_email = custom_args.get('recipient_email', email)  # Fallback to event email

        # Log based on event type
        if event_type in ['open', 'click']:
            # Log the activity
            activity_tracker.log_activity(
                campaign_id=campaign_id,
                variant=variant,
                email=recipient_email,
                action=event_type,
                details=f"SendGrid event: {json.dumps(event)}"
            )

            logger.info(f"Logged {event_type} activity: Campaign {campaign_id}, Variant {variant}, Email {recipient_email}")

        elif event_type == 'delivered':
            # Could log delivery confirmation if needed
            logger.info(f"Email delivered: {recipient_email}")

        elif event_type in ['bounce', 'dropped']:
            # Log bounce/dropped events
            activity_tracker.log_activity(
                campaign_id=campaign_id,
                variant=variant,
                email=recipient_email,
                action='bounce',
                details=f"SendGrid event: {event_type} - {json.dumps(event)}"
            )
            logger.warning(f"Email {event_type}: {recipient_email}")

        else:
            logger.debug(f"Ignored event type: {event_type}")

    except Exception as e:
        logger.error(f"Error processing SendGrid event: {str(e)} - Event: {event}")

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "sendgrid-webhook"}

if __name__ == '__main__':
    # Run the webhook handler
    app.run(
        host='0.0.0.0',
        port=5002,  # Different port from tracking server
        debug=False
    )
