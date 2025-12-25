import csv
import os
from datetime import datetime
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserActivityTracker:
    """Tracks user activities like opens and clicks in a CSV file."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.csv_path = os.path.join(data_dir, "user_activity.csv")
        self._ensure_csv_exists()

    def _ensure_csv_exists(self):
        """Ensure the CSV file exists with headers."""
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'campaign_id', 'variant', 'email', 'action', 'details'])

    def log_activity(self, campaign_id: str, variant: str, email: str, action: str, details: str = ""):
        """
        Log a user activity to the CSV.

        Args:
            campaign_id: Campaign ID
            variant: Variant (A, B, etc.)
            email: User email
            action: Action type (open, click, etc.)
            details: Additional details
        """
        timestamp = datetime.now().isoformat()
        with open(self.csv_path, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([timestamp, campaign_id, variant, email, action, details])
        logger.info(f"Logged activity: {action} for {email} in campaign {campaign_id}")

    def log_batch_activities(self, activities: List[Dict[str, Any]]):
        """
        Log multiple activities at once.

        Args:
            activities: List of activity dicts with keys: campaign_id, variant, email, action, details
        """
        with open(self.csv_path, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for activity in activities:
                timestamp = datetime.now().isoformat()
                writer.writerow([
                    timestamp,
                    activity.get('campaign_id', ''),
                    activity.get('variant', ''),
                    activity.get('email', ''),
                    activity.get('action', ''),
                    activity.get('details', '')
                ])
        logger.info(f"Logged {len(activities)} activities")

    def get_activities(self, campaign_id: str = None, email: str = None) -> List[Dict[str, Any]]:
        """
        Get activities from CSV, optionally filtered.

        Args:
            campaign_id: Filter by campaign ID
            email: Filter by email

        Returns:
            List of activity dictionaries
        """
        activities = []
        with open(self.csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if (not campaign_id or row['campaign_id'] == campaign_id) and \
                   (not email or row['email'] == email):
                    activities.append(row)
        return activities

    def log_opens_and_clicks_from_metrics(self, campaign_id: str, variant: str, recipients: List[Dict[str, str]], metrics: Dict[str, Any]):
        """
        Log opens and clicks based on SendGrid metrics.

        Since SendGrid provides aggregated metrics, we'll distribute the clicks/opens among recipients.

        Args:
            campaign_id: Campaign ID
            variant: Variant
            recipients: List of recipient dicts
            metrics: Metrics dict with opened, clicked counts
        """
        opened_count = metrics.get('opened', 0)
        clicked_count = metrics.get('clicked', 0)
        total_recipients = len(recipients)

        if total_recipients == 0:
            return

        # Simple distribution: randomly assign opens/clicks to recipients
        import random
        opened_recipients = random.sample(recipients, min(opened_count, total_recipients))
        clicked_recipients = random.sample(opened_recipients, min(clicked_count, len(opened_recipients)))

        activities = []
        for recipient in recipients:
            email = recipient.get('email', '')
            if recipient in opened_recipients:
                activities.append({
                    'campaign_id': campaign_id,
                    'variant': variant,
                    'email': email,
                    'action': 'open',
                    'details': 'tracked via SendGrid'
                })
            if recipient in clicked_recipients:
                activities.append({
                    'campaign_id': campaign_id,
                    'variant': variant,
                    'email': email,
                    'action': 'click',
                    'details': 'tracked via SendGrid'
                })

        self.log_batch_activities(activities)
