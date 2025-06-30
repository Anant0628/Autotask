"""
Configuration module for TeamLogic-AutoTask application.
Contains all configuration constants and settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Snowflake Connection Configuration (loaded from .env)
SF_ACCOUNT = os.getenv('SF_ACCOUNT')
SF_USER = os.getenv('SF_USER')
SF_PASSWORD = os.getenv('SF_PASSWORD')
SF_WAREHOUSE = os.getenv('SF_WAREHOUSE')
SF_DATABASE = os.getenv('SF_DATABASE')
SF_SCHEMA = os.getenv('SF_SCHEMA')
SF_ROLE = os.getenv('SF_ROLE')
SF_PASSCODE = os.getenv('SF_PASSCODE')


# File Paths
DATA_REF_FILE = 'data.txt'
KNOWLEDGEBASE_FILE = 'Knowledgebase.json'

# UI Configuration
PAGE_TITLE = "TeamLogic-AutoTask"
PAGE_ICON = "🎫"
LAYOUT = "wide"

# Pagination Settings
TICKETS_PER_PAGE = 10

# LLM Model Configuration
DEFAULT_EXTRACT_MODEL = 'llama3-8b'
DEFAULT_CLASSIFY_MODEL = 'mixtral-8x7b'

# Priority Options
PRIORITY_OPTIONS = ["Low", "Medium", "High", "Critical", "Desktop/User Down"]

# Status Options
STATUS_OPTIONS = ["Open", "In Progress", "Resolved", "Closed"]

# Duration Filter Options
DURATION_OPTIONS = [
    "Last hour",
    "Last 2 hours",
    "Last 6 hours",
    "Last 12 hours",
    "Today",
    "Yesterday",
    "Last 3 days",
    "Last week",
    "Last month",
    "All tickets"
]

# Priority Colors for UI
PRIORITY_COLORS = {
    "Low": "🟢",
    "Medium": "🟡",
    "High": "🟠",
    "Critical": "🔴",
    "Desktop/User Down": "🚨"
}

# Duration Icons
DURATION_ICONS = {
    "Last hour": "🚨",
    "Last 2 hours": "⏰",
    "Last 6 hours": "🕕",
    "Last 12 hours": "🕐",
    "Today": "📅",
    "Yesterday": "📆",
    "Last 3 days": "📊",
    "Last week": "📈",
    "Last month": "📉",
    "All tickets": "📋"
}

# Chart Colors
STATUS_COLORS = {
    "New": "#4e73df",
    "In Progress": "#f6c23e",
    "Resolved": "#36b9cc",
    "Closed": "#e74a3b"
}

CHART_PRIORITY_COLORS = {
    "Low": "#1cc88a",
    "Medium": "#36b9cc",
    "High": "#f6c23e",
    "Critical": "#e74a3b",
    "Desktop/User Down": "#6f42c1"
}

# Contact Information (loaded from .env)
SUPPORT_PHONE = os.getenv('SUPPORT_PHONE', '9723100860')
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'inquire@64-squares.com')