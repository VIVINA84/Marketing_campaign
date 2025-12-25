"""Reporting and Optimization Agent - Generates insights and learns from campaigns."""
from typing import Dict, List, Any
from datetime import datetime
import json
import os

class ReportingAgent:
    """Agent that generates campaign reports and optimization insights."""
    
    def __init__(self, results_dir: str = "results"):
        self.results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)
    
    def generate_campaign_report(self, campaign_id: str, strategy: Dict[str, Any], 
                                 ab_results: Dict[str, Any], deliverability: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive campaign report.
        
        Args:
            campaign_id: Campaign identifier
            strategy: Campaign strategy
            ab_results: A/B test results
            deliverability: Deliverability check results
            
        Returns:
            Complete campaign report
        """
        report = {
            "campaign_id": campaign_id,
            "generated_at": datetime.now().isoformat(),
            "strategy_summary": {
                "objectives": strategy.get("objectives", "N/A"),
                "target_audience": strategy.get("target_audience", "N/A"),
                "key_messages": strategy.get("key_messages", "N/A")
            },
            "performance": ab_results,
            "deliverability": deliverability,
            "insights": self._generate_insights(ab_results, deliverability),
            "recommendations": self._generate_recommendations(ab_results, deliverability),
            "next_steps": self._suggest_next_steps(ab_results)
        }
        
        # Save report
        self.save_report(campaign_id, report)
        
        return report
    
    def _generate_insights(self, ab_results: Dict[str, Any], deliverability: Dict[str, Any]) -> List[str]:
        """Generate insights from campaign data."""
        insights = []
        
        if "error" not in ab_results:
            # Find best performing variant
            best_variant = None
            best_open_rate = 0
            
            for variant, metrics in ab_results.items():
                open_rate = metrics.get("open_rate", 0)
                if open_rate > best_open_rate:
                    best_open_rate = open_rate
                    best_variant = variant
            
            if best_variant:
                insights.append(f"Variant {best_variant} performed best with {best_open_rate}% open rate")
            
            # Compare variants
            if len(ab_results) > 1:
                variants = list(ab_results.keys())
                if len(variants) >= 2:
                    var_a = ab_results.get(variants[0], {})
                    var_b = ab_results.get(variants[1], {})
                    
                    if var_a.get("open_rate", 0) > var_b.get("open_rate", 0):
                        diff = var_a.get("open_rate", 0) - var_b.get("open_rate", 0)
                        insights.append(f"{variants[0]} outperformed {variants[1]} by {diff:.1f}% in open rate")
        
        # Deliverability insights
        if deliverability:
            spam_score = deliverability.get("spam_check", {}).get("spam_score", 0)
            if spam_score < 10:
                insights.append("Email content passed spam filters with low risk score")
            elif spam_score >= 20:
                insights.append("Email content has high spam risk - consider revising")
        
        return insights
    
    def _generate_recommendations(self, ab_results: Dict[str, Any], deliverability: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []
        
        if "error" not in ab_results:
            # Analyze performance
            for variant, metrics in ab_results.items():
                open_rate = metrics.get("open_rate", 0)
                click_rate = metrics.get("click_rate", 0)
                
                if open_rate < 20:
                    recommendations.append(f"Variant {variant}: Low open rate - consider improving subject line")
                
                if click_rate < 2:
                    recommendations.append(f"Variant {variant}: Low click rate - strengthen call-to-action")
        
        # Deliverability recommendations
        if deliverability:
            recs = deliverability.get("recommendations", [])
            recommendations.extend(recs)
        
        if not recommendations:
            recommendations.append("Campaign is performing well. Continue monitoring and optimize based on results.")
        
        return recommendations
    
    def _suggest_next_steps(self, ab_results: Dict[str, Any]) -> List[str]:
        """Suggest next steps for campaign optimization."""
        next_steps = []
        
        if "error" not in ab_results and len(ab_results) > 0:
            # Find winner
            best_variant = None
            best_score = 0
            
            for variant, metrics in ab_results.items():
                score = metrics.get("open_rate", 0) + metrics.get("click_rate", 0)
                if score > best_score:
                    best_score = score
                    best_variant = variant
            
            if best_variant:
                next_steps.append(f"Scale winning variant {best_variant} to full audience")
                next_steps.append("Run follow-up campaign with optimized content")
                next_steps.append("A/B test new subject lines based on learnings")
        
        next_steps.append("Monitor deliverability and engagement metrics")
        next_steps.append("Gather feedback and iterate on messaging")
        
        return next_steps
    
    def save_report(self, campaign_id: str, report: Dict[str, Any]):
        """Save campaign report to file."""
        file_path = os.path.join(self.results_dir, f"{campaign_id}_report.json")
        with open(file_path, "w") as f:
            json.dump(report, f, indent=2)
    
    def load_report(self, campaign_id: str) -> Dict[str, Any]:
        """Load campaign report from file."""
        file_path = os.path.join(self.results_dir, f"{campaign_id}_report.json")
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
        return {}
    
    def get_campaign_summary(self, campaign_id: str) -> Dict[str, Any]:
        """Get summary statistics for a campaign."""
        report = self.load_report(campaign_id)
        
        if not report:
            return {"error": "Campaign report not found"}
        
        performance = report.get("performance", {})
        
        summary = {
            "campaign_id": campaign_id,
            "total_variants": len(performance),
            "best_variant": None,
            "best_open_rate": 0,
            "total_sent": 0,
            "total_opened": 0,
            "total_clicked": 0
        }
        
        for variant, metrics in performance.items():
            sent = metrics.get("sent", 0)
            opened = metrics.get("opened", 0)
            clicked = metrics.get("clicked", 0)
            open_rate = metrics.get("open_rate", 0)
            
            summary["total_sent"] += sent
            summary["total_opened"] += opened
            summary["total_clicked"] += clicked
            
            if open_rate > summary["best_open_rate"]:
                summary["best_open_rate"] = open_rate
                summary["best_variant"] = variant
        
        if summary["total_sent"] > 0:
            summary["overall_open_rate"] = round((summary["total_opened"] / summary["total_sent"]) * 100, 2)
            summary["overall_click_rate"] = round((summary["total_clicked"] / summary["total_sent"]) * 100, 2)
        
        return summary

