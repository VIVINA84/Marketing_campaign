"""A/B Testing Agent - Manages A/B test variants and tracks performance."""
from typing import Dict, List, Any
import random
from datetime import datetime
import json
import os

class ABTestingAgent:
    """Agent that manages A/B testing for email campaigns."""
    
    def __init__(self, results_dir: str = "results"):
        self.results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)
        self.test_results = {}
    
    def create_test_groups(self, recipients: List[Dict[str, str]], num_variants: int = 2) -> Dict[str, List[Dict[str, str]]]:
        """
        Split recipients into A/B test groups.
        
        Args:
            recipients: List of recipient dictionaries
            num_variants: Number of variants to test (2 or 3)
            
        Returns:
            Dictionary mapping variant labels to recipient lists
        """
        num_variants = min(num_variants, 3)  # Max 3 variants
        random.shuffle(recipients)
        
        # Split evenly
        group_size = len(recipients) // num_variants
        groups = {}
        variant_labels = ["A", "B", "C"][:num_variants]
        
        for i, variant in enumerate(variant_labels):
            start_idx = i * group_size
            if i == len(variant_labels) - 1:
                # Last group gets remaining recipients
                groups[variant] = recipients[start_idx:]
            else:
                groups[variant] = recipients[start_idx:start_idx + group_size]
        
        return groups
    
    def track_metric(self, campaign_id: str, variant: str, metric: str, value: float):
        """
        Track a performance metric for a variant.
        
        Args:
            campaign_id: Unique campaign identifier
            variant: Variant label (A, B, or C)
            metric: Metric name (open_rate, click_rate, conversion_rate)
            value: Metric value
        """
        if campaign_id not in self.test_results:
            self.test_results[campaign_id] = {
                "variants": {},
                "start_time": datetime.now().isoformat()
            }
        
        if variant not in self.test_results[campaign_id]["variants"]:
            self.test_results[campaign_id]["variants"][variant] = {
                "metrics": {},
                "sent": 0,
                "opened": 0,
                "clicked": 0,
                "converted": 0
            }
        
        self.test_results[campaign_id]["variants"][variant]["metrics"][metric] = value
    
    def record_event(self, campaign_id: str, variant: str, event: str, count: int = 1):
        """
        Record an event (sent, opened, clicked, converted).
        
        Args:
            campaign_id: Campaign identifier
            variant: Variant label
            event: Event type (sent, opened, clicked, converted)
            count: Number of events
        """
        if campaign_id not in self.test_results:
            self.test_results[campaign_id] = {
                "variants": {},
                "start_time": datetime.now().isoformat()
            }
        
        if variant not in self.test_results[campaign_id]["variants"]:
            self.test_results[campaign_id]["variants"][variant] = {
                "metrics": {},
                "sent": 0,
                "opened": 0,
                "clicked": 0,
                "converted": 0
            }
        
        if event in self.test_results[campaign_id]["variants"][variant]:
            self.test_results[campaign_id]["variants"][variant][event] += count
    
    def calculate_metrics(self, campaign_id: str) -> Dict[str, Any]:
        """
        Calculate performance metrics for all variants.
        
        Args:
            campaign_id: Campaign identifier
            
        Returns:
            Dictionary with calculated metrics
        """
        if campaign_id not in self.test_results:
            return {"error": "Campaign not found"}
        
        results = {}
        variants = self.test_results[campaign_id]["variants"]
        
        for variant, data in variants.items():
            sent = data.get("sent", 0)
            opened = data.get("opened", 0)
            clicked = data.get("clicked", 0)
            converted = data.get("converted", 0)
            
            open_rate = (opened / sent * 100) if sent > 0 else 0
            click_rate = (clicked / sent * 100) if sent > 0 else 0
            conversion_rate = (converted / sent * 100) if sent > 0 else 0
            ctr = (clicked / opened * 100) if opened > 0 else 0
            
            results[variant] = {
                "sent": sent,
                "opened": opened,
                "clicked": clicked,
                "converted": converted,
                "open_rate": round(open_rate, 2),
                "click_rate": round(click_rate, 2),
                "conversion_rate": round(conversion_rate, 2),
                "click_through_rate": round(ctr, 2)
            }
        
        return results
    
    def get_winner(self, campaign_id: str, primary_metric: str = "open_rate") -> str:
        """
        Determine winning variant based on primary metric.
        
        Args:
            campaign_id: Campaign identifier
            primary_metric: Metric to use for comparison (open_rate, click_rate, conversion_rate)
            
        Returns:
            Winning variant label
        """
        metrics = self.calculate_metrics(campaign_id)
        
        if "error" in metrics:
            return None
        
        winner = None
        best_score = -1
        
        for variant, data in metrics.items():
            score = data.get(primary_metric, 0)
            if score > best_score:
                best_score = score
                winner = variant
        
        return winner
    
    def save_results(self, campaign_id: str):
        """Save test results to file."""
        file_path = os.path.join(self.results_dir, f"{campaign_id}_ab_test.json")
        with open(file_path, "w") as f:
            json.dump(self.test_results.get(campaign_id, {}), f, indent=2)
    
    def load_results(self, campaign_id: str) -> Dict[str, Any]:
        """Load test results from file."""
        file_path = os.path.join(self.results_dir, f"{campaign_id}_ab_test.json")
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
        return {}

