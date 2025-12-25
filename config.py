"""Configuration settings for the Email Ops Agent system."""
import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

# Segmentation Configuration
USE_LLM_SEGMENTATION = os.getenv("USE_LLM_SEGMENTATION", "true").lower() in ("1", "true", "yes")
SEGMENTATION_SAMPLE_SIZE = int(os.getenv("SEGMENTATION_SAMPLE_SIZE", "200"))
MAX_SEGMENTS = int(os.getenv("MAX_SEGMENTS", "5"))

# Email Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_NAME = os.getenv("SENDER_NAME", "Marketing Campaign System")

# SendGrid Configuration
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "")
SENDGRID_FROM_NAME = os.getenv("SENDGRID_FROM_NAME", SENDER_NAME)
SENDGRID_SANDBOX = os.getenv("SENDGRID_SANDBOX", "false").lower() in ("1", "true", "yes")
USE_SENDGRID = bool(SENDGRID_API_KEY)  # Use SendGrid if API key is provided

# Campaign Configuration
DATA_DIR = "data"
RESULTS_DIR = "results"
MAX_AB_TEST_VARIANTS = 3
AB_TEST_SPLIT_RATIO = 0.5  # 50/50 split for A/B testing

