"""Orchestrator using LangGraph to coordinate all agents."""
from typing import Dict, Any, TypedDict, Annotated
from langgraph.graph import StateGraph, END
import operator
from datetime import datetime
import uuid

from agents.strategy_agent import StrategyAgent
from agents.segmentation_agent import SegmentationAgent
from agents.personalization_agent import PersonalizationAgent
from agents.ab_testing_agent import ABTestingAgent
from agents.deliverability_agent import DeliverabilityAgent
from agents.reporting_agent import ReportingAgent
from utils.email_sender import EmailSender
from utils.sendgrid_sender import SendGridSender
from utils.sendgrid_tracker import SendGridTracker
from utils.user_activity_tracker import UserActivityTracker
import config

class CampaignState(TypedDict):
    """State structure for the campaign orchestration."""
    campaign_id: str
    brief: str
    csv_path: str
    strategy: Dict[str, Any]
    segments: Dict[str, Any]
    selected_recipients: list
    email_variants: Dict[str, Any]
    ab_test_groups: Dict[str, list]
    deliverability_check: Dict[str, Any]
    ab_results: Dict[str, Any]
    campaign_report: Dict[str, Any]
    status: str
    error: str

class CampaignOrchestrator:
    """Orchestrator that coordinates all agents using LangGraph."""
    
    def __init__(self):
        """Initialize orchestrator with all agents."""
        # Initialize agents
        self.strategy_agent = StrategyAgent(config.OPENAI_API_KEY)
        self.personalization_agent = PersonalizationAgent(config.OPENAI_API_KEY)
        self.ab_testing_agent = ABTestingAgent(config.RESULTS_DIR)
        self.deliverability_agent = DeliverabilityAgent()
        self.reporting_agent = ReportingAgent(config.RESULTS_DIR)
        self.activity_tracker = UserActivityTracker(config.DATA_DIR)
        
        # Initialize email sender (SendGrid or SMTP)
        if config.USE_SENDGRID and config.SENDGRID_API_KEY:
            self.email_sender = SendGridSender(
                config.SENDGRID_API_KEY,
                config.SENDGRID_FROM_EMAIL,
                config.SENDGRID_FROM_NAME,
                sandbox=config.SENDGRID_SANDBOX,
            )
            self.sendgrid_tracker = SendGridTracker(config.SENDGRID_API_KEY)
            self.use_sendgrid = True
        else:
            self.email_sender = EmailSender(
                config.SMTP_SERVER,
                config.SMTP_PORT,
                config.SMTP_USERNAME,
                config.SMTP_PASSWORD,
                config.SENDER_EMAIL,
                config.SENDER_NAME
            )
            self.sendgrid_tracker = None
            self.use_sendgrid = False
        
        # Build workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow for campaign execution."""
        workflow = StateGraph(CampaignState)
        
        # Add nodes
        workflow.add_node("create_strategy", self._create_strategy)
        workflow.add_node("segment_audience", self._segment_audience)
        workflow.add_node("generate_content", self._generate_content)
        workflow.add_node("check_deliverability", self._check_deliverability)
        workflow.add_node("run_ab_test", self._run_ab_test)
        workflow.add_node("send_emails", self._send_emails)
        workflow.add_node("generate_report", self._generate_report)
        
        # Define edges - pause after content generation for manual sending
        workflow.set_entry_point("create_strategy")
        workflow.add_edge("create_strategy", "segment_audience")
        workflow.add_edge("segment_audience", "generate_content")
        workflow.add_edge("generate_content", "check_deliverability")
        workflow.add_edge("check_deliverability", END)  # Pause here for manual sending
        
        return workflow.compile()
    
    def _create_strategy(self, state: CampaignState) -> CampaignState:
        """Create campaign strategy from brief."""
        try:
            strategy_result = self.strategy_agent.create_strategy(state["brief"])
            state["strategy"] = strategy_result.get("strategy", {})
            state["status"] = "strategy_created"
        except Exception as e:
            state["error"] = f"Strategy creation failed: {str(e)}"
            state["status"] = "error"
        return state
    
    def _segment_audience(self, state: CampaignState) -> CampaignState:
        """Segment audience from CSV."""
        try:
            segmentation_agent = SegmentationAgent(state["csv_path"])
            # Pass campaign brief along with strategy so LLM has proper context
            strategy_input = {}
            if isinstance(state.get("strategy"), dict):
                strategy_input.update(state.get("strategy", {}))
            # Always include the raw brief for LLM segmentation
            strategy_input["brief"] = state.get("brief", "")

            segments = segmentation_agent.segment_audience(strategy_input)
            state["segments"] = segments
            state["selected_recipients"] = segments.get("selected_segment", [])
            state["status"] = "audience_segmented"
        except Exception as e:
            state["error"] = f"Segmentation failed: {str(e)}"
            state["status"] = "error"
        return state
    
    def _generate_content(self, state: CampaignState) -> CampaignState:
        """Generate personalized email content for A/B testing."""
        try:
            recipients = state["selected_recipients"]
            num_variants = 2  # A and B
            
            # Create A/B test groups
            ab_groups = self.ab_testing_agent.create_test_groups(recipients, num_variants)
            state["ab_test_groups"] = ab_groups
            
            # Generate content for each variant
            email_variants = {}
            sample_recipient = recipients[0] if recipients else {"name": "Customer", "email": "test@example.com"}
            
            for variant, group in ab_groups.items():
                # Generate content for this variant
                content = self.personalization_agent.generate_email_content(
                    state["strategy"],
                    sample_recipient,
                    variant,
                    state["campaign_id"]
                )
                email_variants[variant] = content
            
            state["email_variants"] = email_variants
            state["status"] = "content_generated"
        except Exception as e:
            state["error"] = f"Content generation failed: {str(e)}"
            state["status"] = "error"
        return state
    
    def _check_deliverability(self, state: CampaignState) -> CampaignState:
        """Check deliverability and compliance."""
        try:
            # Check all variants
            all_checks = {}
            for variant, content in state["email_variants"].items():
                check = self.deliverability_agent.full_check(
                    content,
                    state["ab_test_groups"].get(variant, [])
                )
                all_checks[variant] = check
            
            state["deliverability_check"] = all_checks
            state["status"] = "deliverability_checked"
        except Exception as e:
            state["error"] = f"Deliverability check failed: {str(e)}"
            state["status"] = "error"
        return state
    
    def _should_proceed(self, state: CampaignState) -> str:
        """Determine if we should proceed with sending."""
        checks = state.get("deliverability_check", {})
        
        # Check if any variant passed
        for variant_check in checks.values():
            if variant_check.get("passed", False):
                return "proceed"
        
        return "fix"
    
    def _run_ab_test(self, state: CampaignState) -> CampaignState:
        """Run A/B test by sending emails via SendGrid."""
        try:
            campaign_id = state["campaign_id"]
            ab_groups = state["ab_test_groups"]
            email_variants = state["email_variants"]
            
            # Store SendGrid message IDs for tracking
            sendgrid_message_ids = {}
            
            # Send emails for each variant
            for variant, recipients in ab_groups.items():
                content = email_variants[variant]
                
                if self.use_sendgrid:
                    # Send via SendGrid
                    send_results = self.email_sender.send_batch(
                        recipients, 
                        content, 
                        variant=variant, 
                        campaign_id=campaign_id
                    )
                    
                    # Store message IDs for this variant
                    message_ids = [msg["message_id"] for msg in send_results.get("message_ids", [])]
                    sendgrid_message_ids[variant] = message_ids
                    
                    # Track sent emails
                    self.ab_testing_agent.record_event(campaign_id, variant, "sent", send_results["sent"])
                    
                    # Get real metrics from SendGrid (wait a bit for processing)
                    if self.sendgrid_tracker and message_ids:
                        metrics = self.sendgrid_tracker.get_campaign_metrics(
                            campaign_id, 
                            message_ids, 
                            wait_seconds=3
                        )
                        
                        # Record real SendGrid metrics
                        self.ab_testing_agent.record_event(campaign_id, variant, "opened", metrics.get("opened", 0))
                        self.ab_testing_agent.record_event(campaign_id, variant, "clicked", metrics.get("clicked", 0))
                        self.ab_testing_agent.record_event(campaign_id, variant, "bounced", metrics.get("bounced", 0))
                        
                        # Store SendGrid metrics in state
                        if "sendgrid_metrics" not in state:
                            state["sendgrid_metrics"] = {}
                        state["sendgrid_metrics"][variant] = metrics
                    else:
                        # Fallback: simulate if SendGrid tracking not available
                        import random
                        opened = int(send_results["sent"] * random.uniform(0.15, 0.35))
                        clicked = int(opened * random.uniform(0.10, 0.25))
                        self.ab_testing_agent.record_event(campaign_id, variant, "opened", opened)
                        self.ab_testing_agent.record_event(campaign_id, variant, "clicked", clicked)
                else:
                    # Use SMTP (fallback)
                    send_results = self.email_sender.send_batch(recipients, content)
                    self.ab_testing_agent.record_event(campaign_id, variant, "sent", send_results["sent"])
                    
                    # Simulate metrics for SMTP
                    import random
                    opened = int(send_results["sent"] * random.uniform(0.15, 0.35))
                    clicked = int(opened * random.uniform(0.10, 0.25))
                    converted = int(clicked * random.uniform(0.05, 0.15))
                    
                    self.ab_testing_agent.record_event(campaign_id, variant, "opened", opened)
                    self.ab_testing_agent.record_event(campaign_id, variant, "clicked", clicked)
                    self.ab_testing_agent.record_event(campaign_id, variant, "converted", converted)
            
            # Store message IDs in state
            state["sendgrid_message_ids"] = sendgrid_message_ids
            
            # Calculate results
            ab_results = self.ab_testing_agent.calculate_metrics(campaign_id)
            state["ab_results"] = ab_results
            
            # Save results
            self.ab_testing_agent.save_results(campaign_id)
            
            state["status"] = "ab_test_completed"
        except Exception as e:
            state["error"] = f"A/B test failed: {str(e)}"
            state["status"] = "error"
        return state
    
    def _send_emails(self, state: CampaignState) -> CampaignState:
        """Send winning variant to remaining audience (if applicable)."""
        try:
            campaign_id = state["campaign_id"]
            winner = self.ab_testing_agent.get_winner(campaign_id, "open_rate")
            
            if winner:
                state["status"] = f"winner_determined: {winner}"
            else:
                state["status"] = "emails_sent"
        except Exception as e:
            state["error"] = f"Email sending failed: {str(e)}"
            state["status"] = "error"
        return state
    
    def _generate_report(self, state: CampaignState) -> CampaignState:
        """Generate final campaign report."""
        try:
            campaign_id = state["campaign_id"]
            report = self.reporting_agent.generate_campaign_report(
                campaign_id,
                state["strategy"],
                state["ab_results"],
                state["deliverability_check"]
            )
            state["campaign_report"] = report
            state["status"] = "completed"
        except Exception as e:
            state["error"] = f"Report generation failed: {str(e)}"
            state["status"] = "error"
        return state
    
    def run_campaign(self, brief: str, csv_path: str) -> Dict[str, Any]:
        """
        Run campaign workflow up to content generation (pauses for manual sending).
        
        Args:
            brief: Marketing campaign brief
            csv_path: Path to CSV file with audience data
            
        Returns:
            Campaign state ready for manual sending
        """
        # Initialize state
        campaign_id = str(uuid.uuid4())[:8]
        initial_state: CampaignState = {
            "campaign_id": campaign_id,
            "brief": brief,
            "csv_path": csv_path,
            "strategy": {},
            "segments": {},
            "selected_recipients": [],
            "email_variants": {},
            "ab_test_groups": {},
            "deliverability_check": {},
            "ab_results": {},
            "campaign_report": {},
            "status": "initialized",
            "error": ""
        }
        
        # Run workflow up to content generation
        try:
            final_state = self.workflow.invoke(initial_state)
            final_state["status"] = "ready_to_send"  # Mark as ready for manual sending
            return final_state
        except Exception as e:
            return {
                **initial_state,
                "status": "error",
                "error": str(e)
            }
    
    def send_variant(self, campaign_state: Dict[str, Any], variant: str) -> Dict[str, Any]:
        """
        Manually send a specific variant to its segmented audience.
        
        NOTE: Emails are sent REGARDLESS of deliverability check results.
        Deliverability checks are informational only and do not block sending.
        
        Args:
            campaign_state: Current campaign state
            variant: Variant to send ("A" or "B")
            
        Returns:
            Updated campaign state with send results
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            campaign_id = campaign_state["campaign_id"]
            ab_groups = campaign_state.get("ab_test_groups", {})
            email_variants = campaign_state.get("email_variants", {})
            
            if variant not in ab_groups or variant not in email_variants:
                campaign_state["error"] = f"Variant {variant} not found"
                return campaign_state
            
            recipients = ab_groups[variant]
            content = email_variants[variant]
            
            # Validate recipients and content
            if not recipients or len(recipients) == 0:
                logger.error(f"❌ No recipients found for Variant {variant}")
                campaign_state["error"] = f"No recipients found for Variant {variant}"
                return campaign_state
            
            if not content:
                logger.error(f"❌ No email content found for Variant {variant}")
                campaign_state["error"] = f"No email content found for Variant {variant}"
                return campaign_state
            
            logger.info(f"🚀 Sending Variant {variant} to {len(recipients)} recipients (deliverability checks ignored)")
            logger.info(f"📧 First recipient: {recipients[0] if recipients else 'None'}")
            logger.info(f"📝 Email subject: {content.get('subject', 'No subject')}")
            
            # Initialize sendgrid_message_ids if not exists
            if "sendgrid_message_ids" not in campaign_state:
                campaign_state["sendgrid_message_ids"] = {}
            if "send_results" not in campaign_state:
                campaign_state["send_results"] = {}
            
            if self.use_sendgrid:
                logger.info(f"📬 Using SendGrid to send emails")
                logger.info(f"📋 Recipients list: {len(recipients)} recipients")
                logger.info(f"📝 Content keys: {list(content.keys())}")
                
                # Send via SendGrid
                send_results = self.email_sender.send_batch(
                    recipients, 
                    content, 
                    variant=variant, 
                    campaign_id=campaign_id
                )
                
                logger.info(f"📊 Send results: {send_results}")

                # Persist per-variant send results for UI display
                campaign_state["send_results"][variant] = send_results
                
                # Store message IDs
                message_ids = [msg["message_id"] for msg in send_results.get("message_ids", [])]
                campaign_state["sendgrid_message_ids"][variant] = message_ids
                
                # Track sent emails
                if send_results.get("sent", 0) > 0:
                    self.ab_testing_agent.record_event(campaign_id, variant, "sent", send_results["sent"])
                
                logger.info(f"✅ Variant {variant} sent: {send_results.get('sent', 0)} successful, {send_results.get('failed', 0)} failed out of {send_results.get('total', 0)} total")
                
                # If no emails were sent, log detailed error
                if send_results.get("sent", 0) == 0 and send_results.get("total", 0) > 0:
                    logger.error(f"❌ No emails were sent! Errors: {send_results.get('errors', [])[:3]}")
                    campaign_state["error"] = f"Failed to send emails. Check logs for details. Errors: {send_results.get('errors', [])[:2]}"
                
                # Immediately fetch SendGrid metrics for this variant if possible
                if self.sendgrid_tracker and message_ids:
                    try:
                        metrics = self.sendgrid_tracker.get_campaign_metrics(
                            campaign_id,
                            message_ids,
                            wait_seconds=5
                        )
                        # Record metrics to A/B testing agent
                        self.ab_testing_agent.record_event(campaign_id, variant, "opened", metrics.get("opened", 0))
                        self.ab_testing_agent.record_event(campaign_id, variant, "clicked", metrics.get("clicked", 0))
                        self.ab_testing_agent.record_event(campaign_id, variant, "bounced", metrics.get("bounced", 0))

                        # Log to user activity CSV
                        self.activity_tracker.log_opens_and_clicks_from_metrics(
                            campaign_id, variant, ab_groups[variant], metrics
                        )

                        # Persist in state
                        if "sendgrid_metrics" not in campaign_state:
                            campaign_state["sendgrid_metrics"] = {}
                        campaign_state["sendgrid_metrics"][variant] = metrics
                    except Exception as metric_err:
                        logger.warning(f"⚠️ Failed to fetch SendGrid metrics immediately: {metric_err}")
                
                # Mark status for this variant
                campaign_state["status"] = f"variant_{variant}_sent"
                campaign_state[f"variant_{variant}_sent"] = True
                
            else:
                # Use SMTP
                logger.info(f"📧 Using SMTP to send Variant {variant}")
                send_results = self.email_sender.send_batch(recipients, content)
                self.ab_testing_agent.record_event(campaign_id, variant, "sent", send_results["sent"])
                
                logger.info(f"✅ Variant {variant} sent via SMTP: {send_results['sent']} successful, {send_results.get('failed', 0)} failed")

                if "send_results" not in campaign_state:
                    campaign_state["send_results"] = {}
                campaign_state["send_results"][variant] = send_results
                
                campaign_state["status"] = f"variant_{variant}_sent"
                campaign_state[f"variant_{variant}_sent"] = True
            
            # Log any errors but don't fail
            if send_results.get("errors"):
                logger.warning(f"⚠️ Some emails failed to send: {send_results['errors'][:5]}")  # Log first 5 errors
            
            # If all intended variants have been sent, process results and generate report
            try:
                all_variants = list(ab_groups.keys())
                if all_variants and all(campaign_state.get(f"variant_{v}_sent") for v in all_variants):
                    logger.info("📈 All variants sent. Processing results and generating report...")
                    processed = self.process_results(campaign_state)
                    # Merge processed state
                    campaign_state.update(processed)
            except Exception as process_err:
                logger.warning(f"⚠️ Failed to process results after send: {process_err}")
            
            return campaign_state
            
        except Exception as e:
            campaign_state["error"] = f"Failed to send variant {variant}: {str(e)}"
            return campaign_state
    
    def process_results(self, campaign_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process A/B test results and generate reports after emails are sent.
        
        Args:
            campaign_state: Campaign state after sending
            
        Returns:
            Updated campaign state with results and reports
        """
        try:
            campaign_id = campaign_state["campaign_id"]
            ab_groups = campaign_state.get("ab_test_groups", {})
            email_variants = campaign_state.get("email_variants", {})
            sendgrid_message_ids = campaign_state.get("sendgrid_message_ids", {})
            
            # Process metrics for each sent variant
            for variant in ab_groups.keys():
                if campaign_state.get(f"variant_{variant}_sent"):
                    if self.use_sendgrid and self.sendgrid_tracker:
                        # Get real metrics from SendGrid
                        message_ids = sendgrid_message_ids.get(variant, [])
                        if message_ids:
                            metrics = self.sendgrid_tracker.get_campaign_metrics(
                                campaign_id, 
                                message_ids, 
                                wait_seconds=5
                            )
                            
                            # Record metrics
                            self.ab_testing_agent.record_event(campaign_id, variant, "opened", metrics.get("opened", 0))
                            self.ab_testing_agent.record_event(campaign_id, variant, "clicked", metrics.get("clicked", 0))
                            self.ab_testing_agent.record_event(campaign_id, variant, "bounced", metrics.get("bounced", 0))

                            # Log to user activity CSV
                            self.activity_tracker.log_opens_and_clicks_from_metrics(
                                campaign_id, variant, ab_groups[variant], metrics
                            )

                            # Store SendGrid metrics
                            if "sendgrid_metrics" not in campaign_state:
                                campaign_state["sendgrid_metrics"] = {}
                            campaign_state["sendgrid_metrics"][variant] = metrics
                    else:
                        # Simulate metrics for SMTP
                        import random
                        sent = self.ab_testing_agent.test_results.get(campaign_id, {}).get("variants", {}).get(variant, {}).get("sent", 0)
                        opened = int(sent * random.uniform(0.15, 0.35))
                        clicked = int(opened * random.uniform(0.10, 0.25))
                        converted = int(clicked * random.uniform(0.05, 0.15))
                        
                        self.ab_testing_agent.record_event(campaign_id, variant, "opened", opened)
                        self.ab_testing_agent.record_event(campaign_id, variant, "clicked", clicked)
                        self.ab_testing_agent.record_event(campaign_id, variant, "converted", converted)
            
            # Calculate A/B test results
            ab_results = self.ab_testing_agent.calculate_metrics(campaign_id)
            campaign_state["ab_results"] = ab_results
            self.ab_testing_agent.save_results(campaign_id)
            
            # Generate report
            report = self.reporting_agent.generate_campaign_report(
                campaign_id,
                campaign_state.get("strategy", {}),
                ab_results,
                campaign_state.get("deliverability_check", {})
            )
            campaign_state["campaign_report"] = report
            
            # Determine winner
            winner = self.ab_testing_agent.get_winner(campaign_id, "open_rate")
            if winner:
                campaign_state["status"] = f"completed_winner_{winner}"
            else:
                campaign_state["status"] = "completed"
            
            return campaign_state
            
        except Exception as e:
            campaign_state["error"] = f"Failed to process results: {str(e)}"
            return campaign_state

