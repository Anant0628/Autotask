"""
UI components module for TeamLogic-AutoTask application.
Contains Streamlit UI components, styling, and utility functions.
"""

import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
from collections import Counter
from typing import List, Dict

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from config import *
from src.data import DataManager


def apply_custom_css():
    """Apply custom dark theme CSS styling."""
    st.markdown("""
    <style>
    :root {
        --primary: #4e73df;
        --primary-hover: #2e59d9;
        --secondary: #181818;
        --accent: #23272f;
        --text-main: #f8f9fa;
        --text-secondary: #b0b3b8;
        --card-bg: #23272f;
        --sidebar-bg: #111111;
    }
    .main {
        background-color: var(--secondary);
        color: var(--text-main);
    }
    body, .stApp, .main, .block-container {
        background-color: var(--secondary) !important;
        color: var(--text-main) !important;
    }
    .stTextInput input, .stTextArea textarea,
    .stSelectbox select, .stDateInput input {
        background-color: #23272f !important;
        color: var(--text-main) !important;
        border: 1px solid #444 !important;
        border-radius: 6px !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder,
    .stSelectbox select:invalid, .stDateInput input::placeholder {
        color: var(--text-secondary) !important;
    }
    .stButton>button {
        background-color: var(--primary) !important;
        color: white !important;
        border: none;
        padding: 10px 24px;
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: var(--primary-hover) !important;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: var(--primary);
    }
    .stSuccess {
        background-color: #1e4620 !important;
        color: #d4edda !important;
        border-radius: 8px;
    }
    .card {
        background-color: var(--card-bg);
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.15);
        margin-bottom: 20px;
        color: var(--text-main);
    }
    .sidebar .sidebar-content, .stSidebar, section[data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
        color: var(--text-main) !important;
    }
    .stMetric {
        color: var(--text-main) !important;
    }
    .stExpanderHeader {
        color: var(--text-main) !important;
        background-color: var(--card-bg) !important;
    }
    .stExpanderContent {
        background-color: var(--card-bg) !important;
        color: var(--text-main) !important;
    }
    .stAlert, .stInfo, .stWarning {
        background-color: #23272f !important;
        color: #f8f9fa !important;
        border-radius: 8px;
    }
    @media (max-width: 768px) {
        .stForm {
            padding: 15px;
        }
    }
    </style>
    """, unsafe_allow_html=True)


def create_sidebar(data_manager: DataManager):
    """Create the navigation sidebar."""
    with st.sidebar:
        st.markdown("## Navigation")

        # Simple navigation buttons
        if st.button("🏠 Home", key="nav_main", use_container_width=True):
            st.session_state.page = "main"
            st.rerun()

        if st.button("🕒 Recent Tickets", key="nav_recent_tickets", use_container_width=True):
            st.session_state.page = "recent_tickets"
            st.rerun()

        if st.button("📊 Dashboard", key="nav_dashboard", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()

        # Show current page
        current_page = st.session_state.get('page', 'main')
        st.markdown(f"**Current:** {current_page.replace('_', ' ').title()}")

        st.markdown("---")

        # Quick Stats
        st.markdown("### Quick Stats")
        try:
            if os.path.exists(KNOWLEDGEBASE_FILE):
                with open(KNOWLEDGEBASE_FILE, 'r') as f:
                    kb_data = json.load(f)
                total_tickets = len(kb_data)
            else:
                total_tickets = 0
        except:
            total_tickets = 0
        st.metric("Total Tickets", total_tickets)

        # Contact Information
        st.markdown("---")
        st.markdown("### Need Help?")
        st.markdown(f"📞 **Phone:** {SUPPORT_PHONE}")
        st.markdown(f"✉️ **Email:** {SUPPORT_EMAIL}")


def format_time_elapsed(created_at):
    """Calculate and format time elapsed"""
    try:
        if isinstance(created_at, str):
            ticket_time = datetime.fromisoformat(created_at)
        else:
            ticket_time = created_at

        now = datetime.now()
        diff = now - ticket_time

        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            minutes = max(1, diff.seconds // 60)
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    except:
        return "Unknown"


def format_date_display(created_at):
    """Format date for display"""
    try:
        if isinstance(created_at, str):
            ticket_time = datetime.fromisoformat(created_at)
        else:
            ticket_time = created_at
        return ticket_time.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "Unknown"


def get_duration_icon(duration: str) -> str:
    """Get appropriate icon for duration"""
    return DURATION_ICONS.get(duration, "📅")