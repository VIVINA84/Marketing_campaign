# AI Email Ops Agent - Copilot Instructions

## Architecture Overview

This is an AI-powered email marketing automation system using **LangGraph orchestration** with 6 modular agents:

- **Strategy Agent** (`agents/strategy_agent.py`): Analyzes briefs, creates campaign objectives/targets
- **Segmentation Agent** (`agents/segmentation_agent.py`): Processes CSV audience data, segments by criteria
- **Personalization Agent** (`agents/personalization_agent.py`): Generates GPT-4 powered email variants
- **A/B Testing Agent** (`agents/ab_testing_agent.py`): Manages test groups, tracks performance metrics
- **Deliverability Agent** (`agents/deliverability_agent.py`): Validates emails, checks spam compliance
- **Reporting Agent** (`agents/reporting_agent.py`): Generates insights and optimization recommendations

**Workflow**: Brief → Strategy → Segmentation → Content Generation → Deliverability Check → A/B Testing → Email Sending → Reporting

## Key Patterns & Conventions

### Agent Communication
- Agents communicate via shared `CampaignState` TypedDict in `orchestrator.py`
- Each agent updates specific state fields (e.g., `strategy`, `segments`, `email_variants`)
- State flows through LangGraph workflow with conditional routing

### Data Flow
- Campaign briefs loaded from `data/campaign_briefs.json` or CSV files
- Audience data from `data/audience.csv` (required: `email`, `name`; optional: `location`, `interests`, `engagement_score`, `purchase_history`)
- Results stored as JSON in `results/{uuid}/` directories with campaign artifacts

### Configuration
- Environment variables in `.env` file (API keys, SMTP/SendGrid settings)
- `config.py` centralizes all configuration with defaults
- Supports both SMTP and SendGrid email sending (auto-detects based on API key presence)

### LLM Integration
- Use `langchain_openai.ChatOpenAI` with `gpt-4-turbo-preview` for content generation
- Prompts defined as `ChatPromptTemplate.from_messages()` with system/user roles
- Temperature 0.7 for creative content, 0.0 for analysis tasks

### Email Infrastructure
- Dual sending support: SMTP fallback or SendGrid preferred
- `utils/sendgrid_sender.py` for transactional sending with tracking
- `utils/email_sender.py` for SMTP with basic delivery
- Sandbox mode available for SendGrid testing

## Development Workflows

### Running the System
```bash
# Install dependencies
pip install -r requirements.txt

# Verify setup
python test_setup.py

# Launch dashboard
streamlit run app.py
```

### Adding New Agents
1. Create agent class in `agents/` following pattern from existing agents
2. Add agent initialization in `orchestrator.py` `__init__`
3. Add workflow node in `_build_workflow()` method
4. Update `CampaignState` TypedDict with new state fields
5. Add edges connecting the new agent to workflow

### Campaign Data Management
- Add campaign briefs to `data/campaign_briefs.json` with `name` and `brief` fields
- Audience CSV must have `email` and `name` columns minimum
- Campaign results auto-saved with UUID in `results/` directory

### Testing Campaigns
- Use sample data in `data/` folder for development
- Campaigns run through full pipeline: strategy → segmentation → content → validation
- A/B testing splits audience 50/50 by default (configurable in `config.py`)

## Code Patterns

### Agent Implementation
```python
class NewAgent:
    def __init__(self, api_key: str):
        self.llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.7, openai_api_key=api_key)
    
    def process_method(self, state: CampaignState) -> Dict[str, Any]:
        # Process state data
        # Return updated state fields
        return {"new_field": result}
```

### State Updates
```python
def _agent_node(self, state: CampaignState) -> CampaignState:
    try:
        result = self.agent.process_method(state)
        state.update(result)
        state["status"] = "completed"
    except Exception as e:
        state["error"] = str(e)
        state["status"] = "error"
    return state
```

### Error Handling
- Agents catch exceptions and set `state["error"]` and `state["status"] = "error"`
- Orchestrator handles error states in workflow routing
- Dashboard displays errors to users via Streamlit

## Key Files Reference

- `orchestrator.py`: LangGraph workflow definition and state management
- `app.py`: Streamlit dashboard with campaign creation/management
- `config.py`: Centralized configuration management
- `models.py`: Pydantic models for data validation
- `utils/campaign_loader.py`: Data loading utilities for briefs/audience
- `results/`: JSON artifacts from completed campaigns