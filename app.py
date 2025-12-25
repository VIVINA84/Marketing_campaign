"""Streamlit Dashboard for Email Ops Agent System."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from orchestrator import CampaignOrchestrator
from agents.reporting_agent import ReportingAgent
from agents.ab_testing_agent import ABTestingAgent
from utils.campaign_loader import load_campaign_briefs, get_campaign_brief_by_name, get_audience_csv_path
import json
import os
import config

# Page configuration
st.set_page_config(
    page_title="AI Email Ops Agent",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "campaigns" not in st.session_state:
    st.session_state.campaigns = []
if "current_campaign" not in st.session_state:
    st.session_state.current_campaign = None

def main():
    """Main dashboard application."""
    st.title("📧 AI-Powered Email Ops Agent")
    st.markdown("Automated email campaign management with AI agents")
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Select Page",
            ["Create Campaign", "View Campaigns", "Dashboard", "Reports"]
        )
        
        st.markdown("---")
        st.header("Configuration")
        st.info("Make sure to configure your .env file with API keys and SMTP settings")
    
    # Route to appropriate page
    if page == "Create Campaign":
        create_campaign_page()
    elif page == "View Campaigns":
        view_campaigns_page()
    elif page == "Dashboard":
        dashboard_page()
    elif page == "Reports":
        reports_page()

def create_campaign_page():
    """Page for creating new campaigns."""
    st.header("Create New Campaign")
    
    # Load available campaigns from data folder
    available_campaigns = load_campaign_briefs("data")
    
    with st.form("campaign_form"):
        st.subheader("Select Campaign Brief")
        
        if not available_campaigns:
            st.warning("No campaign briefs found in data folder. Please add campaign brief files (JSON, CSV, or TXT) to the data folder.")
            st.info("Supported formats:\n- JSON: campaign_briefs.json with 'name' and 'brief' fields\n- CSV: campaign_brief.csv with 'campaign_name' and 'brief' columns\n- TXT: Any .txt file with 'brief' in filename")
            brief = None
            selected_campaign_name = None
        else:
            # Create dropdown for campaign selection
            campaign_names = [camp.get('name', 'Unknown') for camp in available_campaigns]
            selected_campaign_name = st.selectbox(
                "Choose a campaign brief:",
                options=campaign_names,
                help="Select a campaign brief from the data folder"
            )
            
            # Get selected campaign brief
            selected_campaign = next(
                (camp for camp in available_campaigns if camp.get('name') == selected_campaign_name),
                None
            )
            
            if selected_campaign:
                brief = selected_campaign.get('brief', '')
                
                # Display campaign details
                with st.expander("📋 View Campaign Brief", expanded=True):
                    st.text_area(
                        "Campaign Brief:",
                        value=brief,
                        height=150,
                        disabled=True,
                        label_visibility="collapsed"
                    )
                    
                    # Show additional info if available
                    if 'campaign_type' in selected_campaign:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.caption(f"**Type:** {selected_campaign.get('campaign_type', 'N/A')}")
                        with col2:
                            st.caption(f"**CTA:** {selected_campaign.get('cta', 'N/A')}")
            else:
                brief = None
        
        st.subheader("Audience Data")
        st.info(f"📁 Audience data will be loaded from: `{get_audience_csv_path('data')}`")
        
        # Check if audience CSV exists
        audience_path = get_audience_csv_path("data")
        if os.path.exists(audience_path):
            try:
                df_audience = pd.read_csv(audience_path)
                st.success(f"✅ Found audience data: {len(df_audience)} contacts")
                with st.expander("👥 Preview Audience Data"):
                    st.dataframe(df_audience.head(10), width='stretch')
                    st.caption(f"Total contacts: {len(df_audience)}")
            except Exception as e:
                st.error(f"Error loading audience data: {str(e)}")
        else:
            st.warning(f"⚠️ Audience CSV not found at {audience_path}")
            st.info("Please ensure audience.csv exists in the data folder with columns: email, name (and optionally: location, interests, engagement_score, purchase_history)")
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("🚀 Launch Campaign", width='stretch')
        with col2:
            clear = st.form_submit_button("Clear", width='stretch')
        
        if submit:
            if not brief:
                st.error("Please select a campaign brief")
            elif not os.path.exists(audience_path):
                st.error(f"Audience CSV not found. Please ensure {audience_path} exists.")
            else:
                with st.spinner("Running campaign... This may take a few minutes."):
                    try:
                        # Initialize orchestrator
                        orchestrator = CampaignOrchestrator()
                        
                        # Run campaign up to content generation
                        result = orchestrator.run_campaign(brief, audience_path)
                        
                        # Store campaign name in result
                        result['campaign_name'] = selected_campaign_name
                        
                        # Store in session state
                        st.session_state.current_campaign = result
                        if result not in st.session_state.campaigns:
                            st.session_state.campaigns.append(result)
                        
                        st.success("✅ Campaign strategy, segmentation, and email content generated!")
                        st.info(f"Campaign ID: {result.get('campaign_id')} | Campaign: {selected_campaign_name}")
                        st.rerun()  # Refresh to show send interface
                        
                    except Exception as e:
                        st.error(f"Campaign failed: {str(e)}")
                        st.exception(e)
    
    # Show email previews and send buttons (outside form)
    current_campaign = st.session_state.get("current_campaign")
    # Always show the send panel if variants exist, regardless of status
    if current_campaign and current_campaign.get("email_variants"):
        st.markdown("---")
        st.subheader("📧 Email Variants Ready to Send")
        st.info("💡 **Note**: Emails will be sent to all segmented recipients regardless of deliverability warnings. Deliverability checks are informational only.")
        
        email_variants = current_campaign.get("email_variants", {})
        ab_groups = current_campaign.get("ab_test_groups", {})
        deliverability = current_campaign.get("deliverability_check", {})
        
        if email_variants:
            orchestrator = CampaignOrchestrator()

            # Controls to send both versions at once
            variants = sorted(email_variants.keys())
            send_both = st.button(
                "🚀 Send Both Versions",
                key=f"send_both_{current_campaign.get('campaign_id')}",
                type="primary"
            )

            if send_both:
                with st.spinner("Sending all versions and starting A/B testing..."):
                    try:
                        state_after = current_campaign
                        for v in variants:
                            if not state_after.get(f"variant_{v}_sent"):
                                state_after = orchestrator.send_variant(state_after, v)
                                # Update session state after each send
                                for i, camp in enumerate(st.session_state.campaigns):
                                    if camp.get("campaign_id") == current_campaign.get("campaign_id"):
                                        st.session_state.campaigns[i] = state_after
                                        st.session_state.current_campaign = state_after
                                        break
                        # After sending both, process A/B test results
                        final_state = orchestrator.process_results(state_after)
                        for i, camp in enumerate(st.session_state.campaigns):
                            if camp.get("campaign_id") == current_campaign.get("campaign_id"):
                                st.session_state.campaigns[i] = final_state
                                st.session_state.current_campaign = final_state
                                break
                        st.success("✅ Both versions sent and A/B testing started.")
                    except Exception as e:
                        st.error(f"Failed to send both versions: {str(e)}")
                        st.exception(e)
            
            for variant in variants:
                with st.container():
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"### Variant {variant}")
                        content = email_variants[variant]
                        
                        # Show email preview
                        with st.expander(f"📄 Preview Email Variant {variant}", expanded=False):
                            st.markdown(f"**Subject:** {content.get('subject', 'No Subject')}")
                            st.markdown("**Content:**")
                            st.text_area(
                                "Email Body",
                                value=content.get('full_content', ''),
                                height=200,
                                disabled=True,
                                label_visibility="collapsed"
                            )
                        
                        # Show deliverability status (informational only - emails will still send)
                        if variant in deliverability:
                            check = deliverability[variant]
                            if check.get("passed"):
                                st.success("✅ Deliverability check passed")
                            else:
                                st.warning("⚠️ Deliverability issues detected (emails will still be sent)")
                                st.info("💡 Note: Emails will be sent regardless of deliverability warnings. These are recommendations only.")
                                for issue in check.get("spam_check", {}).get("warnings", []):
                                    st.caption(f"⚠️ {issue}")
                                for issue in check.get("spam_check", {}).get("issues", []):
                                    st.caption(f"⚠️ {issue}")
                        
                        # Show recipient count
                        recipient_count = len(ab_groups.get(variant, []))
                        st.caption(f"📬 Will send to {recipient_count} recipients")
                    
                    with col2:
                        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
                        
                        # Send button (outside form) - always enabled regardless of deliverability
                        send_key = f"send_{current_campaign.get('campaign_id')}_{variant}"
                        
                        # Check if already sent
                        if current_campaign.get(f"variant_{variant}_sent"):
                            st.success(f"✅ Version {variant} sent")
                            # Show per-variant summary if available
                            send_results = current_campaign.get("send_results", {}).get(variant)
                            if send_results:
                                st.caption(f"Summary: {send_results.get('sent', 0)} sent, {send_results.get('failed', 0)} failed out of {send_results.get('total', 0)}")
                                if send_results.get("sandbox"):
                                    st.warning("SendGrid sandbox mode enabled: emails are accepted but not delivered.")
                                with st.expander("Per-recipient results"):
                                    df = pd.DataFrame(send_results.get("per_recipient", []))
                                    if not df.empty:
                                        st.dataframe(df, width='stretch', height=250)
                        else:
                            send_button = st.button(
                                f"🚀 Send Variant {variant}",
                                key=send_key,
                                width='stretch',
                                type="primary"
                            )
                            
                            if send_button:
                                with st.spinner(f"Sending Variant {variant} to {recipient_count} recipients..."):
                                    try:
                                        # Debug: Show what we're sending
                                        st.write(f"📧 Sending to {recipient_count} recipients...")
                                        
                                        # Send the variant (emails sent regardless of deliverability)
                                        updated_state = orchestrator.send_variant(current_campaign, variant)
                                        
                                        # Update session state immediately to keep UI
                                        for i, camp in enumerate(st.session_state.campaigns):
                                            if camp.get("campaign_id") == current_campaign.get("campaign_id"):
                                                st.session_state.campaigns[i] = updated_state
                                                st.session_state.current_campaign = updated_state
                                                break
                                        
                                        # Show results inline
                                        send_results = updated_state.get("send_results", {}).get(variant)
                                        if send_results:
                                            st.caption(f"Summary: {send_results.get('sent', 0)} sent, {send_results.get('failed', 0)} failed out of {send_results.get('total', 0)}")
                                            if send_results.get("sandbox"):
                                                st.warning("SendGrid sandbox mode enabled: emails are accepted but not delivered.")
                                            with st.expander("Per-recipient results", expanded=True):
                                                df = pd.DataFrame(send_results.get("per_recipient", []))
                                                if not df.empty:
                                                    st.dataframe(df, width='stretch', height=250)
                                        
                                        # Check for errors
                                        if updated_state.get("error"):
                                            st.error(f"❌ Error: {updated_state.get('error')}")
                                        
                                        # Check send results
                                        sendgrid_message_ids = updated_state.get("sendgrid_message_ids", {})
                                        variant_message_ids = sendgrid_message_ids.get(variant, [])
                                        
                                        if variant_message_ids:
                                            st.success(f"✅ Variant {variant} sent successfully! {len(variant_message_ids)} emails accepted by provider.")
                                        elif updated_state.get(f"variant_{variant}_sent"):
                                            st.success(f"✅ Variant {variant} marked as sent. Check results below.")
                                        else:
                                            st.warning(f"⚠️ Variant {variant} sending completed but no message IDs recorded. Check errors below.")
                                        
                                        # No st.rerun() here to keep the current UI visible
                                        
                                    except Exception as e:
                                        st.error(f"Failed to send variant {variant}: {str(e)}")
                                        st.exception(e)
            
            # Show process results section if all available variants are sent
            variants_list = sorted(email_variants.keys())
            all_sent = all(current_campaign.get(f"variant_{v}_sent") for v in variants_list)
            
            if all_sent:
                st.markdown("---")
                st.subheader("📊 Generate Results & Reports")
                
                if not current_campaign.get("ab_results"):
                    st.info("Both variants have been sent! Click below to generate A/B test results and reports.")
                    
                    if st.button(
                        "📊 Generate Results & Report",
                        key=f"process_{current_campaign.get('campaign_id')}",
                        width='stretch',
                        type="primary"
                    ):
                        with st.spinner("Processing results and generating reports..."):
                            try:
                                final_state = orchestrator.process_results(current_campaign)
                                
                                # Update session state
                                for i, camp in enumerate(st.session_state.campaigns):
                                    if camp.get("campaign_id") == current_campaign.get("campaign_id"):
                                        st.session_state.campaigns[i] = final_state
                                        st.session_state.current_campaign = final_state
                                        break
                                
                                st.success("✅ Results and reports generated!")
                                st.balloons()
                                
                                # Show insights
                                insights = final_state.get("campaign_report", {}).get("insights", [])
                                if insights:
                                    st.subheader("Key Insights")
                                    for insight in insights:
                                        st.success(f"💡 {insight}")
                                
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to process results: {str(e)}")
                                st.exception(e)
                else:
                    st.success("✅ Results and reports have been generated!")
                    st.info("View detailed results in the 'View Campaigns' page.")

def view_campaigns_page():
    """Page for viewing all campaigns."""
    st.header("Campaign History")
    
    if not st.session_state.campaigns:
        st.info("No campaigns yet. Create one from the 'Create Campaign' page.")
        return
    
    # Campaign selector with names
    campaign_options = []
    for c in st.session_state.campaigns:
        campaign_id = c.get("campaign_id", "Unknown")
        campaign_name = c.get("campaign_name", "Unnamed Campaign")
        campaign_options.append(f"{campaign_name} ({campaign_id})")
    
    selected_option = st.selectbox("Select Campaign", campaign_options)
    selected_id = selected_option.split("(")[-1].rstrip(")")
    
    selected_campaign = next(
        (c for c in st.session_state.campaigns if c.get("campaign_id") == selected_id),
        None
    )
    
    if selected_campaign:
        display_campaign_details(selected_campaign)

def display_campaign_details(campaign: dict):
    """Display detailed campaign information."""
    campaign_name = campaign.get('campaign_name', 'Unnamed Campaign')
    campaign_id = campaign.get('campaign_id', 'Unknown')
    st.subheader(f"{campaign_name} ({campaign_id})")
    
    # Tabs for different views
    tab1, tab_seg, tab2, tab3, tab4, tab5 = st.tabs(["Strategy", "Segments", "A/B Test Results", "SendGrid Metrics", "Deliverability", "Full Report"])
    
    with tab1:
        st.header("Campaign Strategy")
        strategy = campaign.get("strategy", {})
        if strategy:
            # Friendly rendering instead of raw JSON
            goal = strategy.get('goal') or strategy.get('objective') or strategy.get('mission')
            audience = strategy.get('audience')
            value_prop = strategy.get('value_proposition') or strategy.get('valueProp')
            if goal:
                st.write(f"Goal: {goal}")
            if audience:
                st.write(f"Audience: {audience}" if isinstance(audience, str) else "Audience defined")
            if value_prop:
                st.write(f"Value Proposition: {value_prop}")

            kpis = strategy.get('kpis', {})
            if isinstance(kpis, dict) and kpis:
                st.subheader("KPIs")
                kv = list(kpis.items())
                cols = st.columns(min(4, len(kv)))
                for idx, (k, v) in enumerate(kv):
                    with cols[idx % len(cols)]:
                        st.metric(k.replace('_', ' ').title(), v if isinstance(v, (int, float, str)) else str(v))

            subjects = strategy.get('subject_suggestions') or strategy.get('subject_lines') or []
            if isinstance(subjects, list) and subjects:
                st.subheader("Subject Ideas")
                for s in subjects:
                    st.write(f"- {s}")

            ctas = strategy.get('ctas') or strategy.get('cta') or []
            if isinstance(ctas, list) and ctas:
                st.subheader("Suggested CTAs")
                for c in ctas:
                    st.write(f"- {c}")
            elif isinstance(strategy.get('cta'), str):
                st.subheader("Suggested CTA")
                st.write(f"- {strategy.get('cta')}")

            tone = strategy.get('tone')
            if tone:
                st.write(f"Tone: {tone}")

            key_msgs = strategy.get('key_messages') or strategy.get('keyMessages') or []
            if isinstance(key_msgs, list) and key_msgs:
                st.subheader("Key Messages")
                for m in key_msgs:
                    st.write(f"- {m}")

            remaining = {k: v for k, v in strategy.items() if k not in ['goal', 'objective', 'mission', 'audience', 'value_proposition', 'valueProp', 'kpis', 'subject_suggestions', 'subject_lines', 'cta', 'ctas', 'tone', 'key_messages', 'keyMessages']}
            if remaining:
                st.subheader("Additional Details")
                rows = []
                for k, v in remaining.items():
                    if isinstance(v, (dict, list, tuple, set)):
                        try:
                            safe_v = json.dumps(v, ensure_ascii=False)
                        except Exception:
                            safe_v = str(v)
                    else:
                        safe_v = v if isinstance(v, (str, int, float, bool)) or v is None else str(v)
                    # Ensure all values are strings to avoid PyArrow conversion errors
                    rows.append({"Field": k, "Value": str(safe_v)})
                st.table(pd.DataFrame(rows, columns=["Field", "Value"]))
        else:
            st.info("Strategy not available")
    
    with tab_seg:
        st.header("Segmented Audience")
        segments = campaign.get("segments", {})
        selected_recipients = campaign.get("selected_recipients", [])
        ab_groups = campaign.get("ab_test_groups", {})
        
        if segments:
            # Show overview counts
            total_contacts = segments.get("total_contacts") or segments.get("segments", {}).get("total_contacts") or 0
            segment_counts = segments.get("segment_counts") or {}
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Contacts", total_contacts)
            with col2:
                st.metric("Selected Segment Size", len(selected_recipients))
            
            # Show selected recipients table
            with st.expander("📋 Selected Recipients (primary segment)", expanded=True):
                if selected_recipients:
                    df_sel = pd.DataFrame(selected_recipients)
                    st.dataframe(df_sel, width='stretch', height=300)
                else:
                    st.info("No selected recipients available")
            
            # Show segmentation breakdowns
            seg_detail = segments.get("segments", segments)
            if isinstance(seg_detail, dict):
                for group_name, group_val in seg_detail.items():
                    if isinstance(group_val, dict):
                        with st.expander(f"Segment Group: {group_name}", expanded=False):
                            for seg_name, seg_list in group_val.items():
                                st.caption(f"{seg_name}: {len(seg_list)} recipients")
                                if isinstance(seg_list, list) and seg_list:
                                    st.dataframe(pd.DataFrame(seg_list).head(50), width='stretch')
            
            # Show AB groups mapping
            if ab_groups:
                st.subheader("A/B Groups")
                colA, colB = st.columns(2)
                with colA:
                    st.write(f"Variant A: {len(ab_groups.get('A', []))} recipients")
                    if ab_groups.get('A'):
                        st.dataframe(pd.DataFrame(ab_groups['A']).head(50), width='stretch')
                with colB:
                    st.write(f"Variant B: {len(ab_groups.get('B', []))} recipients")
                    if ab_groups.get('B'):
                        st.dataframe(pd.DataFrame(ab_groups['B']).head(50), width='stretch')
        else:
            st.info("No segmentation data available")
    
    with tab2:
        st.header("A/B Test Performance")
        ab_results = campaign.get("ab_results", {})
        
        if ab_results and "error" not in ab_results:
            # Metrics table
            df_metrics = pd.DataFrame(ab_results).T
            st.dataframe(df_metrics, width='stretch')
            
            # Visualizations
            col1, col2 = st.columns(2)
            
            with col1:
                # Open rate comparison
                fig_open = px.bar(
                    x=list(ab_results.keys()),
                    y=[m.get("open_rate", 0) for m in ab_results.values()],
                    title="Open Rate by Variant",
                    labels={"x": "Variant", "y": "Open Rate (%)"}
                )
                st.plotly_chart(fig_open, width='stretch')
            
            with col2:
                # Click rate comparison
                fig_click = px.bar(
                    x=list(ab_results.keys()),
                    y=[m.get("click_rate", 0) for m in ab_results.values()],
                    title="Click Rate by Variant",
                    labels={"x": "Variant", "y": "Click Rate (%)"}
                )
                st.plotly_chart(fig_click, width='stretch')
            
            # Winner
            winner = campaign.get("status", "").split(":")[-1] if "winner" in campaign.get("status", "") else None
            if winner:
                st.success(f"🏆 Winning Variant: {winner}")
        else:
            st.info("A/B test results not available")
    
    with tab3:
        st.header("SendGrid Email Metrics")
        sendgrid_metrics = campaign.get("sendgrid_metrics", {})
        message_ids = campaign.get("sendgrid_message_ids", {})

        # Global stats controls
        st.subheader("Provider Global Stats")
        col_g1, col_g2, col_g3 = st.columns([2, 2, 1])
        with col_g1:
            start_date = st.date_input("Start date", value=(pd.to_datetime("today") - pd.Timedelta(days=7)).date())
        with col_g2:
            end_date = st.date_input("End date", value=pd.to_datetime("today").date())
        with col_g3:
            aggregated_by = st.selectbox("Aggregate", ["day", "week", "month"], index=0)

        fetch_global = st.button("🔎 Fetch Global Stats", key=f"fetch_global_{campaign_id}")

        if fetch_global:
            try:
                from utils.sendgrid_stats import SendGridStats
                if not getattr(config, "SENDGRID_API_KEY", None):
                    st.error("SENDGRID_API_KEY is not configured.")
                else:
                    sg_stats = SendGridStats(config.SENDGRID_API_KEY)
                    data = sg_stats.get_global_stats(start_date, end_date, aggregated_by=aggregated_by)
                    global_df = sg_stats.to_dataframe(data)
                    if global_df is not None and not global_df.empty:
                        st.success("Fetched global stats from SendGrid")
                        # Summary metrics
                        numeric_cols = [c for c in global_df.columns if c != "date"]
                        if numeric_cols:
                            totals = global_df[numeric_cols].sum()
                            colm = st.columns(min(6, len(numeric_cols)))
                            for idx, col in enumerate(numeric_cols[:len(colm)]):
                                with colm[idx]:
                                    try:
                                        st.metric(col.replace('_', ' ').title(), int(totals[col]))
                                    except Exception:
                                        st.metric(col.replace('_', ' ').title(), str(totals[col]))
                        # Line charts
                        for metric in [
                            "requests",
                            "delivered",
                            "opens",
                            "unique_opens",
                            "clicks",
                            "unique_clicks",
                            "bounces",
                            "blocks",
                            "spam_reports",
                            "unsubscribes",
                        ]:
                            if metric in global_df.columns:
                                fig = px.line(global_df, x="date", y=metric, title=f"{metric.replace('_', ' ').title()} Over Time")
                                st.plotly_chart(fig, width='stretch')
                        # Table
                        with st.expander("View Data Table", expanded=False):
                            st.dataframe(global_df, width='stretch')
                        # CSV export
                        csv_bytes = global_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="⬇️ Download CSV",
                            data=csv_bytes,
                            file_name=f"sendgrid_global_stats_{start_date}_to_{end_date}.csv",
                            mime="text/csv",
                            key=f"dl_global_{campaign_id}"
                        )
                    else:
                        st.info("No global stats available for the selected range.")
            except Exception as e:
                st.error(f"Failed to fetch SendGrid global stats: {e}")
        
        if sendgrid_metrics:
            st.success("✅ Real-time metrics from SendGrid API")
            if st.button("🔄 Refresh Metrics", key=f"refresh_metrics_{campaign_id}"):
                # Trigger a rerun; metrics retrieval happens during send/process steps
                st.rerun()
            
            # Display metrics for each variant
            for variant, metrics in sendgrid_metrics.items():
                with st.expander(f"📊 Variant {variant} - SendGrid Metrics", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Sent", metrics.get("total_sent", 0))
                        st.metric("Delivered", metrics.get("delivered", 0))
                    
                    with col2:
                        st.metric("Opened", metrics.get("opened", 0))
                        st.metric("Open Rate", f"{metrics.get('open_rate', 0):.2f}%")
                    
                    with col3:
                        st.metric("Clicked", metrics.get("clicked", 0))
                        st.metric("Click Rate", f"{metrics.get('click_rate', 0):.2f}%")
                    
                    with col4:
                        st.metric("Bounced", metrics.get("bounced", 0))
                        st.metric("Bounce Rate", f"{metrics.get('bounce_rate', 0):.2f}%")
                    
                    # Additional metrics
                    col5, col6 = st.columns(2)
                    with col5:
                        st.metric("Spam Reports", metrics.get("spam_reports", 0))
                    with col6:
                        st.metric("Unsubscribes", metrics.get("unsubscribes", 0))
                    
                    # Message IDs info
                    if variant in message_ids:
                        st.caption(f"📧 Message IDs tracked: {len(message_ids[variant])}")
                    
                    # Activity breakdown
                    if metrics.get("message_activities"):
                        st.subheader("Message Activity Breakdown")
                        activities_df = pd.DataFrame(metrics["message_activities"]).T
                        st.dataframe(activities_df, width='stretch')
            
            # Comparison chart
            st.subheader("SendGrid Metrics Comparison")
            variants = list(sendgrid_metrics.keys())
            
            col1, col2 = st.columns(2)
            with col1:
                fig_delivered = px.bar(
                    x=variants,
                    y=[sendgrid_metrics[v].get("delivered", 0) for v in variants],
                    title="Delivered Emails by Variant",
                    labels={"x": "Variant", "y": "Delivered"}
                )
                st.plotly_chart(fig_delivered, width='stretch')
            
            with col2:
                fig_opens = px.bar(
                    x=variants,
                    y=[sendgrid_metrics[v].get("opened", 0) for v in variants],
                    title="Opens by Variant",
                    labels={"x": "Variant", "y": "Opens"}
                )
                st.plotly_chart(fig_opens, width='stretch')
            
            # Rate comparison
            col3, col4 = st.columns(2)
            with col3:
                fig_open_rate = px.bar(
                    x=variants,
                    y=[sendgrid_metrics[v].get("open_rate", 0) for v in variants],
                    title="Open Rate by Variant (%)",
                    labels={"x": "Variant", "y": "Open Rate (%)"}
                )
                st.plotly_chart(fig_open_rate, width='stretch')
            
            with col4:
                fig_click_rate = px.bar(
                    x=variants,
                    y=[sendgrid_metrics[v].get("click_rate", 0) for v in variants],
                    title="Click Rate by Variant (%)",
                    labels={"x": "Variant", "y": "Click Rate (%)"}
                )
                st.plotly_chart(fig_click_rate, width='stretch')
            
        elif message_ids:
            st.info("📧 Emails sent via SendGrid. Metrics will be available shortly.")
            st.caption("SendGrid processes email activity in real-time. Refresh the page to see updated metrics.")
            
            # Show message IDs
            for variant, msg_ids in message_ids.items():
                with st.expander(f"Variant {variant} - Message IDs"):
                    st.code("\n".join(msg_ids[:10]))  # Show first 10
                    if len(msg_ids) > 10:
                        st.caption(f"... and {len(msg_ids) - 10} more")
        else:
            st.info("No SendGrid metrics available. Campaign may have been sent via SMTP or metrics are still processing.")
    
    with tab4:
        st.header("Deliverability & Compliance")
        deliverability = campaign.get("deliverability_check", {})
        
        if deliverability:
            for variant, check in deliverability.items():
                with st.expander(f"Variant {variant}"):
                    passed = bool(check.get("passed"))
                    if passed:
                        st.success("Deliverability check passed")
                    else:
                        st.warning("Deliverability warnings detected")

                    spam = check.get("spam_check", {}) if isinstance(check, dict) else {}
                    score = spam.get("score")
                    links = spam.get("links") if isinstance(spam.get("links"), (int, float)) else None
                    images = spam.get("images") if isinstance(spam.get("images"), (int, float)) else None
                    metrics = [("Spam Score", score), ("Links", links), ("Images", images)]
                    metrics = [(k, v) for (k, v) in metrics if v is not None]
                    if metrics:
                        cols = st.columns(len(metrics))
                        for i, (k, v) in enumerate(metrics):
                            with cols[i]:
                                st.metric(k, v)

                    warnings = spam.get("warnings", [])
                    issues = spam.get("issues", [])
                    if warnings:
                        st.subheader("Warnings")
                        for w in warnings:
                            st.caption(f"• {w}")
                    if issues:
                        st.subheader("Issues")
                        for it in issues:
                            st.caption(f"• {it}")
        else:
            st.info("Deliverability check not available")
    
    with tab5:
        st.header("Full Campaign Report")
        report = campaign.get("campaign_report", {})
        
        if report:
            # Insights
            st.subheader("Insights")
            insights = report.get("insights", [])
            for insight in insights:
                st.info(f"💡 {insight}")
            
            # Recommendations
            st.subheader("Recommendations")
            recommendations = report.get("recommendations", [])
            for rec in recommendations:
                st.warning(f"📋 {rec}")
            
            # Next Steps
            st.subheader("Next Steps")
            next_steps = report.get("next_steps", [])
            for step in next_steps:
                st.success(f"✅ {step}")

            # Totals summary (if present)
            totals = report.get("totals", {})
            if isinstance(totals, dict) and totals:
                st.subheader("Totals")
                items = list(totals.items())
                cols = st.columns(min(4, len(items)))
                for idx, (k, v) in enumerate(items):
                    with cols[idx % len(cols)]:
                        st.metric(k.replace('_', ' ').title(), v if isinstance(v, (int, float, str)) else str(v))

            # Variant summary (if present)
            variant_summary = report.get("variants") or {}
            if isinstance(variant_summary, dict) and variant_summary:
                st.subheader("Variant Summary")
                st.dataframe(pd.DataFrame(variant_summary).T, width='stretch')
        else:
            st.info("Report not available")

        st.markdown("---")
        st.subheader("Final PDF Report")
        colr1, colr2 = st.columns([1,3])
        with colr1:
            generate_pdf = st.button("🧠 Generate Final PDF Report", key=f"gen_pdf_{campaign_id}")
        with colr2:
            st.caption("Generates an executive summary and recommendations using the LLM, and exports a styled PDF.")
        if generate_pdf:
            with st.spinner("Building final report (fetching insights and rendering PDF)..."):
                try:
                    # Optional: use global stats if recently fetched from the SendGrid tab
                    global_df = None
                    try:
                        from utils.sendgrid_stats import SendGridStats
                        if getattr(config, "SENDGRID_API_KEY", None):
                            # Default to last 7 days for the campaign window
                            import pandas as _pd
                            start_date = (_pd.to_datetime("today") - _pd.Timedelta(days=7)).date()
                            end_date = _pd.to_datetime("today").date()
                            sg_stats = SendGridStats(config.SENDGRID_API_KEY)
                            data = sg_stats.get_global_stats(start_date, end_date, aggregated_by="day")
                            global_df = sg_stats.to_dataframe(data)
                    except Exception:
                        global_df = None

                    from utils.report_builder import generate_pdf_report
                    output_path = generate_pdf_report(campaign, config.RESULTS_DIR, global_df)
                    if output_path.lower().endswith(".pdf"):
                        with open(output_path, "rb") as f:
                            st.success("Final PDF report generated.")
                            st.download_button(
                                label="⬇️ Download Final Report (PDF)",
                                data=f.read(),
                                file_name=os.path.basename(output_path),
                                mime="application/pdf",
                                key=f"dl_pdf_{campaign_id}"
                            )
                    else:
                        # HTML fallback
                        with open(output_path, "r", encoding="utf-8") as f:
                            st.success("PDF renderer unavailable. Generated HTML instead.")
                            st.download_button(
                                label="⬇️ Download Final Report (HTML)",
                                data=f.read(),
                                file_name=os.path.basename(output_path),
                                mime="text/html",
                                key=f"dl_html_{campaign_id}"
                            )
                except Exception as e:
                    st.error(f"Failed to generate final report: {e}")

def dashboard_page():
    """Main dashboard with overview."""
    st.header("Campaign Dashboard")
    
    if not st.session_state.campaigns:
        st.info("No campaigns to display. Create a campaign to see analytics.")
        return
    
    # Overall statistics
    total_campaigns = len(st.session_state.campaigns)
    completed = sum(1 for c in st.session_state.campaigns if c.get("status") == "completed")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Campaigns", total_campaigns)
    with col2:
        st.metric("Completed", completed)
    with col3:
        st.metric("Success Rate", f"{(completed/total_campaigns*100):.1f}%" if total_campaigns > 0 else "0%")
    with col4:
        if st.session_state.current_campaign:
            st.metric("Current Campaign", st.session_state.current_campaign.get("campaign_id", "N/A"))
    
    # Recent campaigns
    st.subheader("Recent Campaigns")
    if st.session_state.campaigns:
        recent = st.session_state.campaigns[-5:]  # Last 5
        for campaign in reversed(recent):
            with st.expander(f"Campaign {campaign.get('campaign_id')} - {campaign.get('status', 'Unknown')}"):
                display_campaign_summary(campaign)

def display_campaign_summary(campaign: dict):
    """Display a brief summary of a campaign."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Status:**", campaign.get("status", "Unknown"))
        st.write("**Campaign ID:**", campaign.get("campaign_id", "N/A"))
    
    with col2:
        ab_results = campaign.get("ab_results", {})
        if ab_results and "error" not in ab_results:
            total_sent = sum(m.get("sent", 0) for m in ab_results.values())
            avg_open_rate = sum(m.get("open_rate", 0) for m in ab_results.values()) / len(ab_results) if ab_results else 0
            st.write("**Total Sent:**", total_sent)
            st.write("**Avg Open Rate:**", f"{avg_open_rate:.2f}%")

def reports_page():
    """Page for viewing detailed reports."""
    st.header("Campaign Reports")
    
    if not st.session_state.campaigns:
        st.info("No campaigns to generate reports for.")
        return
    
    # Load reporting agent
    reporting_agent = ReportingAgent(config.RESULTS_DIR)
    
    # Campaign selector
    campaign_ids = [c.get("campaign_id", "Unknown") for c in st.session_state.campaigns]
    selected_id = st.selectbox("Select Campaign for Report", campaign_ids)
    
    if selected_id:
        summary = reporting_agent.get_campaign_summary(selected_id)
        
        if "error" not in summary:
            st.subheader("Campaign Summary")
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Sent", summary.get("total_sent", 0))
            with col2:
                st.metric("Total Opened", summary.get("total_opened", 0))
            with col3:
                st.metric("Overall Open Rate", f"{summary.get('overall_open_rate', 0):.2f}%")
            with col4:
                st.metric("Best Variant", summary.get("best_variant", "N/A"))
            
            # Detailed metrics
            st.subheader("Detailed Metrics")
            per_variant = summary.get("per_variant") or summary.get("variants") or {}
            if isinstance(per_variant, dict) and per_variant:
                st.dataframe(pd.DataFrame(per_variant).T, use_container_width=True)
            else:
                rows = [(k, v) for k, v in summary.items() if not isinstance(v, (dict, list))]
                if rows:
                    st.table(pd.DataFrame(rows, columns=["Metric", "Value"]))
        else:
            st.error(summary.get("error", "Report not found"))

def create_sample_csv(file_path: str):
    """Create sample CSV data for testing."""
    import random
    
    data = {
        'email': [f'user{i}@example.com' for i in range(1, 101)],
        'name': [f'User {i}' for i in range(1, 101)],
        'age': [random.randint(18, 65) for _ in range(100)],
        'location': [random.choice(['USA', 'UK', 'Canada', 'Australia', 'Germany']) for _ in range(100)],
        'interests': [random.choice(['Technology', 'Sports', 'Travel', 'Food', 'Fashion']) for _ in range(100)],
        'purchase_history': [random.choice(['High', 'Medium', 'Low', 'None']) for _ in range(100)],
        'engagement_score': [random.randint(1, 10) for _ in range(100)]
    }
    
    df = pd.DataFrame(data)
    df.to_csv(file_path, index=False)

if __name__ == "__main__":
    main()

