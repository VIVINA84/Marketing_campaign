"""SendGrid client for fetching email statistics."""
from sendgrid import SendGridAPIClient
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_email_stats(start_date: str, end_date: str, api_key: str = None) -> List[Dict[str, Any]]:
    """
    Fetch email statistics from SendGrid API.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        api_key: SendGrid API key (if None, will try to get from env)
        
    Returns:
        List of statistics dictionaries
    """
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if not api_key:
        api_key = os.getenv("SENDGRID_API_KEY")
    
    if not api_key:
        logger.error("SENDGRID_API_KEY not found")
        return []
    
    try:
        sg = SendGridAPIClient(api_key=api_key)
        
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Get stats
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "aggregated_by": "day"
        }
        
        response = sg.client.stats.get(query_params=params)
        
        if response.status_code == 200:
            stats_data = response.body
            
            # Handle bytes response
            if isinstance(stats_data, bytes):
                try:
                    stats_data = json.loads(stats_data.decode('utf-8'))
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON from bytes response: {e}")
                    return []
            
            # Ensure stats_data is a list
            if not isinstance(stats_data, list):
                logger.error(f"Unexpected response format: expected list, got {type(stats_data)}")
                return []
            
            # Parse SendGrid stats response
            result = []
            for stat in stats_data:
                if not isinstance(stat, dict):
                    logger.warning(f"Skipping non-dict stat entry: {stat}")
                    continue
                    
                date_str = stat.get("date", "")
                stats_entry = stat.get("stats")
                if isinstance(stats_entry, list) and len(stats_entry) > 0 and isinstance(stats_entry[0], dict):
                    metrics = stats_entry[0].get("metrics", {})
                else:
                    metrics = {}
                
                result.append({
                    "date": date_str,
                    "requests": metrics.get("blocks", 0) + metrics.get("bounce_drops", 0) + metrics.get("deferred", 0) + metrics.get("delivered", 0) + metrics.get("invalid_emails", 0) + metrics.get("processed", 0) + metrics.get("requests", 0) + metrics.get("spam_report_drops", 0) + metrics.get("spam_reports", 0) + metrics.get("unsubscribe_drops", 0) + metrics.get("unsubscribes", 0),
                    "delivered": metrics.get("delivered", 0),
                    "opens": metrics.get("opens", 0),
                    "unique_opens": metrics.get("unique_opens", 0),
                    "clicks": metrics.get("clicks", 0),
                    "unique_clicks": metrics.get("unique_clicks", 0),
                    "bounces": metrics.get("bounces", 0),
                    "spam_reports": metrics.get("spam_reports", 0),
                    "blocks": metrics.get("blocks", 0),
                    "unsubscribes": metrics.get("unsubscribes", 0)
                })
            
            return result
        else:
            logger.warning(f"SendGrid API returned status {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching SendGrid stats: {str(e)}")
        return []

