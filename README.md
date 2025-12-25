# 🤖 AI-Powered Email Marketing Campaign System

An intelligent, end-to-end email marketing platform that leverages AI agents to automate campaign creation, execution, and optimization. Features real-time A/B testing with data-driven winner selection, comprehensive analytics, and seamless SendGrid integration.

![Marketing Campaign System](https://img.shields.io/badge/AI--Powered-Email--Marketing-blue?style=for-the-badge)
![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-red?style=flat-square)
![SendGrid](https://img.shields.io/badge/Email--Service-SendGrid-orange?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.8+-green?style=flat-square)

## ✨ Key Features

### 🎯 **AI-Driven Campaign Automation**
- **Strategy Agent**: Generates comprehensive campaign strategies from simple briefs
- **Segmentation Agent**: Intelligently segments audiences using AI-powered clustering
- **Personalization Agent**: Creates tailored email content for each segment
- **Deliverability Agent**: Ensures emails pass spam filters with AI recommendations
- **Reporting Agent**: Provides data-driven insights and optimization suggestions

### 📊 **Advanced A/B Testing & Analytics**
- **Real-time A/B Testing**: Automated variant generation and testing
- **Data-Driven Winner Selection**: Determines winners based on actual user activity (opens, clicks)
- **User Activity Tracking**: Comprehensive logging of email opens and link clicks
- **Real-time Metrics**: Live dashboard with SendGrid integration
- **Performance Analytics**: Detailed engagement and conversion tracking

### 🔗 **Click & Open Tracking**
- **SendGrid Webhooks**: Real-time tracking of email opens and clicks
- **Activity Logging**: CSV-based user activity tracking with timestamps
- **Ngrok Integration**: Secure webhook handling for local development
- **Campaign Attribution**: Links user actions back to specific campaigns and variants

### 🎨 **Modern Web Dashboard**
- **Streamlit Interface**: Clean, intuitive web-based dashboard
- **Campaign Management**: Create, monitor, and analyze campaigns
- **Real-time Updates**: Live metrics and status updates
- **Interactive Charts**: Plotly-powered analytics visualizations
- **PDF Reports**: Automated executive summary generation

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- SendGrid account with API key
- OpenAI API key
- Ngrok account (for webhook testing)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd marketing-campaign-system
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys:
# OPENAI_API_KEY=your_openai_key
# SENDGRID_API_KEY=your_sendgrid_key
# SENDGRID_FROM_EMAIL=your_verified_sender@email.com
```

4. **Launch the dashboard**
```bash
streamlit run app.py
```

## 📋 Configuration

### Required Environment Variables
```env
OPENAI_API_KEY=sk-your-openai-api-key
SENDGRID_API_KEY=SG.your-sendgrid-api-key
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
```

### Optional Configuration
```env
RESULTS_DIR=results
LOG_LEVEL=INFO
NGROK_AUTH_TOKEN=your_ngrok_token
WEBHOOK_PORT=5000
```

## 🎯 Usage Guide

### 1. **Create Your First Campaign**

1. **Access the Dashboard**: Open `http://localhost:8501`
2. **Navigate to "Create Campaign"**
3. **Upload Campaign Brief**: JSON, CSV, or TXT file with campaign details
4. **Load Audience Data**: CSV with email, name, and optional demographic data
5. **Launch Campaign**: AI agents will automatically:
   - Generate campaign strategy
   - Segment your audience
   - Create personalized email variants
   - Set up A/B testing

### 2. **A/B Testing Workflow**

1. **Variant Generation**: AI creates 2 email variants (A/B)
2. **Send Test Emails**: System sends both variants to segmented groups
3. **Real-time Tracking**: Opens and clicks tracked via SendGrid webhooks
4. **Winner Determination**: System analyzes user activity data to select winner
5. **Scale Winner**: Automatically recommends scaling the winning variant

### 3. **Activity Tracking Setup**

For local development with webhooks:

```bash
# Start webhook handler
python run_webhook_handler.py

# In another terminal, expose via ngrok
python run_with_ngrok.py
```

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Strategy Agent │ -> │ Segmentation    │ -> │ Personalization │
│                 │    │     Agent       │    │     Agent       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         v                       v                       v
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Deliverability  │    │   Reporting     │    │   Orchestrator  │
│     Agent       │    │     Agent       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        v
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ SendGrid API    │    │ User Activity   │    │ Streamlit       │
│ Integration     │    │ Tracker (CSV)   │    │ Dashboard       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Data Flow
1. **Campaign Brief** → AI Strategy Generation
2. **Audience CSV** → Intelligent Segmentation
3. **Strategy + Segments** → Personalized Content Creation
4. **Content Variants** → Spam Analysis & Optimization
5. **Approved Emails** → SendGrid Delivery
6. **User Interactions** → Webhook Tracking → CSV Logging
7. **Activity Data** → Winner Analysis → Reports

## 📁 Project Structure

```
marketing-campaign-system/
├── 📁 agents/                    # AI Agent Implementations
│   ├── strategy_agent.py        # Campaign strategy generation
│   ├── segmentation_agent.py    # Audience segmentation
│   ├── personalization_agent.py # Email content creation
│   ├── deliverability_agent.py  # Spam analysis
│   ├── reporting_agent.py       # Analytics & reporting
│   └── ab_testing_agent.py      # A/B test management
├── 📁 utils/                     # Utility Functions
│   ├── email_sender.py          # SendGrid email sending
│   ├── sendgrid_client.py       # SendGrid API client
│   ├── user_activity_tracker.py # Activity logging
│   ├── sendgrid_webhook_handler.py # Webhook processing
│   └── campaign_loader.py       # Campaign data loading
├── 📁 data/                      # Sample Data & Templates
│   ├── audience.csv             # Sample audience data
│   ├── user_activity.csv        # Activity tracking log
│   └── campaign_briefs/         # Campaign templates
├── 📁 results/                   # Generated Reports & Data
├── 🔧 app.py                     # Streamlit Dashboard
├── 🔧 orchestrator.py            # Main Campaign Orchestrator
├── 🔧 tracking_server.py        # Activity Tracking Server
├── 🔧 run_webhook_handler.py     # Webhook Handler Runner
├── 🔧 run_tracking_server.py    # Tracking Server Runner
├── 🔧 run_with_ngrok.py          # Ngrok Integration
├── ⚙️ config.py                  # Configuration Management
├── 📋 requirements.txt           # Python Dependencies
└── 📖 README.md                  # This file
```

## 🔧 API Reference

### Campaign Endpoints
```python
# Create campaign
POST /campaigns
{
  "brief": "campaign description",
  "audience_path": "data/audience.csv"
}

# Send campaign
POST /campaigns/{id}/send

# Get metrics
GET /campaigns/{id}/metrics
```

### Webhook Endpoints
```python
# SendGrid webhooks
POST /webhook/sendgrid
# Handles: opened, clicked, bounced, etc.
```

## 📊 Analytics & Reporting

### Real-time Metrics
- **Email Delivery**: SendGrid delivery confirmation
- **Open Tracking**: Real-time open notifications
- **Click Tracking**: Link click attribution
- **Bounce Handling**: Automatic bounce processing

### A/B Testing Analytics
- **Winner Selection**: Based on engagement score (opens + clicks)
- **Statistical Significance**: Confidence intervals
- **Performance Comparison**: Side-by-side variant analysis

### Reporting Features
- **Executive Summaries**: AI-generated insights
- **PDF Reports**: Professional campaign reports
- **CSV Exports**: Raw data for further analysis
- **Interactive Dashboards**: Live metrics visualization

## 🔒 Security & Compliance

- **API Key Management**: Secure environment variable handling
- **Webhook Verification**: SendGrid webhook signature validation
- **Data Privacy**: Local CSV storage with encryption options
- **Rate Limiting**: Built-in API rate limit handling
- **Error Handling**: Comprehensive error logging and recovery

## 🚀 Advanced Features

### Custom Agent Development
```python
from agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    def process(self, input_data):
        # Your custom logic here
        return processed_data
```

### Custom Tracking Events
```python
from utils.user_activity_tracker import UserActivityTracker

tracker = UserActivityTracker()
tracker.log_activity({
    'campaign_id': 'camp_123',
    'email': 'user@example.com',
    'action': 'custom_event',
    'details': 'additional_data'
})
```

## 🐛 Troubleshooting

### Common Issues

**SendGrid Webhooks Not Working**
```bash
# Check webhook URL is accessible
curl -X POST http://localhost:5000/webhook/sendgrid -d '{}'

# Use ngrok for external access
python run_with_ngrok.py
```

**A/B Testing Not Starting**
- Ensure audience CSV has sufficient data for segmentation
- Check SendGrid API key permissions
- Verify email addresses are valid

**Activity Data Not Logging**
- Check `data/user_activity.csv` permissions
- Verify webhook handler is running
- Check SendGrid webhook configuration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Commit: `git commit -am 'Add feature'`
5. Push: `git push origin feature-name`
6. Submit a Pull Request

### Development Setup
```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black .
isort .
```

## 📈 Roadmap

- [ ] **Multi-Channel Campaigns**: SMS, social media integration
- [ ] **Advanced ML Segmentation**: Predictive behavior clustering
- [ ] **Automated Follow-ups**: AI-driven nurture sequences
- [ ] **ESP Integrations**: Mailchimp, AWS SES, Postmark
- [ ] **Real-time Dashboards**: Live campaign monitoring
- [ ] **Predictive Analytics**: Campaign success prediction
- [ ] **Advanced A/B Testing**: Multi-variant testing, statistical significance
- [ ] **Personalization Engine**: Dynamic content based on user behavior

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **SendGrid** for reliable email delivery
- **OpenAI** for AI agent capabilities
- **Streamlit** for the amazing dashboard framework
- **Plotly** for interactive visualizations

## 📞 Support

- 📧 **Email**: support@yourcompany.com
- 🐛 **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- 📖 **Documentation**: [Wiki](https://github.com/your-repo/wiki)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)

---

**Built with ❤️ for modern marketing teams**

*Transform your email marketing with AI-powered automation and data-driven insights.*
