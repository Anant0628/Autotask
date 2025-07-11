import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
from collections import Counter
from typing import List, Dict
import hashlib
import random

# Configuration Constants
PAGE_TITLE = "TeamLogic-AutoTask"
LAYOUT = "wide"
PAGE_ICON = "🎫"
PRIORITY_OPTIONS = ["Low", "Medium", "High", "Critical", "Desktop/User Down"]
STATUS_OPTIONS = ["Open", "In Progress", "Resolved", "Closed"]
DURATION_OPTIONS = [
    "Last hour", "Last 2 hours", "Last 6 hours", "Last 12 hours",
    "Today", "Yesterday", "Last 3 days", "Last week", "Last month", "All tickets"
]
TICKETS_PER_PAGE = 10
SUPPORT_PHONE = "9723100860"
SUPPORT_EMAIL = "inquire@64-squares.com"

# Priority and Status Colors
PRIORITY_COLORS = {
    "Low": "🟢",
    "Medium": "🟡", 
    "High": "🟠",
    "Critical": "🔴",
    "Desktop/User Down": "🚨"
}

STATUS_COLORS = {
    "New": "#4e73df",
    "Open": "#031b61", 
    "In Progress": "#f6c23e", 
    "Resolved": "#36b9cc", 
    "Closed": "#e74a3b"
}

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

def apply_custom_css():
    """Apply custom CSS styling based on selected theme."""
    theme = st.session_state.get('theme', 'dark')
    
    if theme == 'dark':
        css = """
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
            --border-color: #444;
            --input-bg: #23272f;
        }
        """
    else:  # light theme
        css = """
        <style>
        :root {
            --primary: #4e73df;
            --primary-hover: #2e59d9;
            --secondary: #ffffff;
            --accent: #f8f9fa;
            --text-main: #212529;
            --text-secondary: #6c757d;
            --card-bg: #ffffff;
            --sidebar-bg: #f8f9fa;
            --border-color: #dee2e6;
            --input-bg: #ffffff;
        }
        """
    
    css += """
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
        background-color: var(--input-bg) !important;
        color: var(--text-main) !important;
        border: 1px solid var(--border-color) !important;
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
        background-color: var(--accent) !important;
        color: var(--text-main) !important;
        border-radius: 8px;
        border: 1px solid #28a745;
    }
    .card {
        background-color: var(--card-bg);
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.15);
        margin-bottom: 20px;
        color: var(--text-main);
        border: 1px solid var(--border-color);
    }
    .user-info-card {
        background-color: var(--card-bg);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 4px solid var(--primary);
        border: 1px solid var(--border-color);
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
        background-color: var(--accent) !important;
        color: var(--text-main) !important;
        border-radius: 8px;
        border: 1px solid var(--border-color);
    }
    .theme-toggle {
        background-color: var(--card-bg);
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 15px;
        border: 1px solid var(--border-color);
    }
    .basic-info-section {
        background-color: var(--card-bg);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid var(--border-color);
        border-left: 4px solid var(--primary);
    }
    @media (max-width: 768px) {
        .stForm {
            padding: 15px;
        }
    }
    </style>
    """
    
    st.markdown(css, unsafe_allow_html=True)

def get_user_info(username: str) -> Dict:
    """Get user information"""
    return {}

def create_sidebar():
    """Create the navigation sidebar with user info and theme selector."""
    with st.sidebar:
        # Theme selector at the top
        st.markdown("""
        <div class="theme-toggle">
        <h4> Theme Settings</h4>
        </div>
        """, unsafe_allow_html=True)
        
        theme_options = {"Dark": "dark", "Light": "light"}
        current_theme = st.session_state.get('theme', 'dark')
        current_theme_label = "Dark" if current_theme == 'dark' else "Light"
        
        selected_theme = st.selectbox(
            "Select Theme:",
            options=list(theme_options.keys()),
            index=list(theme_options.keys()).index(current_theme_label),
            key="theme_selector"
        )
        
        if theme_options[selected_theme] != current_theme:
            st.session_state.theme = theme_options[selected_theme]
            st.rerun()
        
        st.markdown("---")
        
        # User info section
        user_info = st.session_state.get('user_info', {})
        current_user = st.session_state.get('current_user', '')
        
        
        st.markdown("## Navigation")

        # Simple navigation buttons
        if st.button("🏠 Home", key="nav_main", use_container_width=True):
            st.session_state.page = "main"
            st.rerun()

        if st.button("🕒 My Tickets", key="nav_recent_tickets", use_container_width=True):
            st.session_state.page = "recent_tickets"
            st.rerun()

        if st.button("📊 My Dashboard", key="nav_dashboard", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()

        # Show current page
        current_page = st.session_state.get('page', 'main')
        st.markdown(f"**Current:** {current_page.replace('_', ' ').title()}")

        st.markdown("---")

        # Quick Stats for current user
        st.markdown("### 📈 My Quick Stats")
        user_tickets = get_user_tickets(current_user)
        total_tickets = len(user_tickets)
        open_tickets = len([t for t in user_tickets if t['status'] == 'Open'])
        resolved_tickets = len([t for t in user_tickets if t['status'] == 'Resolved'])
        
        st.metric("My Total Tickets", total_tickets)
        st.metric("Open", open_tickets)
        st.metric("Resolved", resolved_tickets)

        # Contact Information
        st.markdown("---")
        st.markdown("### 📞 Need Help?")
        st.markdown(f"**Phone:** {SUPPORT_PHONE}")
        st.markdown(f"**Email:** {SUPPORT_EMAIL}")

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

def generate_user_tickets(username: str, count=25):
    """Generate mock tickets for a specific user"""
    import random
    
    user_info = st.session_state.get('user_info', {})
    if not user_info:
        return []
    
    mock_titles = [
        "Email not working", "Printer offline", "Network connection issues",
        "Software installation request", "Password reset needed", "Computer running slow",
        "Application crash", "File access denied", "VPN connection problems",
        "Monitor display issues", "Keyboard not responding", "Mouse not working",
        "Internet browser freezing", "Database connection error", "System update required",
        "Outlook calendar sync issues", "Shared drive access problems", "WiFi connectivity drops",
        "Software license expired", "Backup system failure"
    ]
    
    mock_descriptions = [
        "Unable to send or receive emails through Outlook",
        "Printer shows offline status and won't print documents",
        "Cannot connect to company network or internet",
        "Need help installing new software on workstation",
        "Forgot password and need assistance resetting it",
        "Computer performance is very slow, takes long to start",
        "Application keeps crashing when trying to open files",
        "Getting access denied error when trying to open shared files",
        "VPN client won't connect to company servers",
        "Monitor display is flickering or showing wrong colors",
        "Calendar appointments not syncing across devices",
        "Cannot access shared network drives from my computer",
        "WiFi connection keeps dropping every few minutes",
        "Software showing license expired message",
        "Automated backup system is not running properly"
    ]
    
    tickets = []
    for i in range(count):
        created_time = datetime.now() - timedelta(
            hours=random.randint(1, 720),  # Random time in last 30 days
            minutes=random.randint(0, 59)
        )
        
        ticket = {
            "id": f"TKT-{username.upper()}-{1000 + i}",
            "title": random.choice(mock_titles),
            "description": random.choice(mock_descriptions),
            "created_at": created_time.isoformat(),
            "status": random.choice(STATUS_OPTIONS),
            "priority": random.choice(PRIORITY_OPTIONS),
            "category": random.choice(["Hardware", "Software", "Network", "Security", "General"]),
            "requester_name": user_info['name'],
            "requester_email": user_info['email'],
            "requester_phone": user_info['phone'],
            "requester_username": username,
            "company_id": user_info['company_id'],
            
            "device_model": random.choice(["Dell Laptop", "HP Desktop", "MacBook Pro", "Surface Pro"]),
            "os_version": random.choice(["Windows 11", "Windows 10", "macOS 13", "Ubuntu 22.04"]),
            "error_message": f"Error code: {random.randint(1000, 9999)}",
            "updated_at": created_time.isoformat(),
            "assigned_technician": f"TECH-{random.randint(1, 5):03d}",
            "resolution_notes": "",
            "generated_notes": {}
        }
        
        # Add resolution notes for resolved/closed tickets
        if ticket['status'] in ['Resolved', 'Closed']:
            ticket['resolution_notes'] = f"Issue resolved by {ticket['assigned_technician']}. Solution implemented and tested."
        
        tickets.append(ticket)
    
    return sorted(tickets, key=lambda x: x["created_at"], reverse=True)

def get_user_tickets(username: str) -> List[Dict]:
    """Get all tickets for a specific user"""
    if not username:
        return []
    
    # Generate or retrieve user-specific tickets
    if f"user_tickets_{username}" not in st.session_state:
        st.session_state[f"user_tickets_{username}"] = generate_user_tickets(username)
    
    return st.session_state[f"user_tickets_{username}"]

def save_user_ticket(username: str, ticket_data: Dict):
    """Save a new ticket for the user"""
    user_tickets = get_user_tickets(username)
    
    # Create new ticket ID
    ticket_id = f"TKT-{username.upper()}-{len(user_tickets) + 1000}"
    
    # Get user info
    user_info = st.session_state.get('user_info', {})
    
    new_ticket = {
        "id": ticket_id,
        "title": ticket_data['title'],
        "description": ticket_data['description'],
        "created_at": datetime.now().isoformat(),
        "status": "Open",
        "priority": ticket_data["priority"],
        "category": random.choice(["Hardware", "Software", "Network", "Security", "General"]),
        "resolution_notes": "",
        "requester_name": user_info['name'],
        "requester_email": user_info['email'],
        "requester_phone": user_info['phone'],
        "requester_username": username,
        "company_id": user_info['company_id'],
        "device_model": ticket_data.get('device_model', ''),
        "os_version": ticket_data.get('os_version', ''),
        "error_message": ticket_data.get('error_message', ''),
        "updated_at": datetime.now().isoformat(),
        "assigned_technician": "",
        "resolution_notes": "",
        "generated_notes": {}
    }
    
    # Add to user's tickets
    user_tickets.insert(0, new_ticket)  # Add to beginning for newest first
    st.session_state[f"user_tickets_{username}"] = user_tickets
    
    return ticket_id

def get_tickets_by_duration(duration: str, user_tickets: List[Dict]) -> List[Dict]:
    """Get user tickets based on selected duration"""
    now = datetime.now()
    
    if duration == "Last hour":
        cutoff_time = now - timedelta(hours=1)
    elif duration == "Last 2 hours":
        cutoff_time = now - timedelta(hours=2)
    elif duration == "Last 6 hours":
        cutoff_time = now - timedelta(hours=6)
    elif duration == "Last 12 hours":
        cutoff_time = now - timedelta(hours=12)
    elif duration == "Today":
        cutoff_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif duration == "Yesterday":
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        filtered_tickets = []
        for ticket in user_tickets:
            try:
                created_time = datetime.fromisoformat(ticket["created_at"])
                if start_time <= created_time <= end_time:
                    filtered_tickets.append(ticket)
            except:
                continue
        return filtered_tickets
    elif duration == "Last 3 days":
        cutoff_time = now - timedelta(days=3)
    elif duration == "Last week":
        cutoff_time = now - timedelta(weeks=1)
    elif duration == "Last month":
        cutoff_time = now - timedelta(days=30)
    elif duration == "All tickets":
        return user_tickets
    else:
        cutoff_time = now - timedelta(hours=24)  # Default to last 24 hours
    
    filtered_tickets = []
    for ticket in user_tickets:
        try:
            created_time = datetime.fromisoformat(ticket["created_at"])
            if created_time >= cutoff_time:
                filtered_tickets.append(ticket)
        except:
            continue
    
    return filtered_tickets

def get_tickets_by_date_range(start_date: date, end_date: date, user_tickets: List[Dict]) -> List[Dict]:
    """Get user tickets between two dates"""
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    filtered_tickets = []
    for ticket in user_tickets:
        try:
            created_time = datetime.fromisoformat(ticket["created_at"])
            if start_datetime <= created_time <= end_datetime:
                filtered_tickets.append(ticket)
        except:
            continue
    
    return filtered_tickets

def get_tickets_by_specific_date(selected_date: date, user_tickets: List[Dict]) -> List[Dict]:
    """Get user tickets for a specific date"""
    filtered_tickets = []
    for ticket in user_tickets:
        try:
            created_time = datetime.fromisoformat(ticket["created_at"])
            if created_time.date() == selected_date:
                filtered_tickets.append(ticket)
        except:
            continue
    
    return filtered_tickets

def main_page():
    """Main page with ticket submission form for logged-in user."""
    current_user = st.session_state.get('current_user', '')
    user_info = st.session_state.get('user_info', {})
    
    st.title(f"🎫 {PAGE_TITLE} - Welcome {user_info.get('name', 'User')}")
    
    st.markdown(f"""
    <div class="card" style="background-color: var(--accent);">
    Submit a new support ticket and let our AI agent automatically classify it for faster resolution.
    <br><strong>Logged in as:</strong> {user_info.get('name', 'Unknown')} ({current_user})
    </div>
    """, unsafe_allow_html=True)

    # Basic Information Section
    st.markdown("""
    <div class="basic-info-section">
    <h3>📋 Basic Information</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f" Name: {user_info.get('name', 'Unknown')}")
        st.markdown(f"Username: {current_user}")
        st.markdown(f" Email: {user_info.get('email', 'Unknown')}")
      #  st.markdown(f"**🏢 Department:** {user_info.get('department', 'Unknown')}")
    with col2:
        st.markdown(f" Phone: {user_info.get('phone', 'Unknown')}")
        st.markdown(f" Company ID: {user_info.get('company_id', 'Unknown')}")
       

    with st.container():
        st.subheader("📝 New Ticket Submission")
        with st.form("new_ticket_form", clear_on_submit=True):
            col1, col2 = st.columns([1, 1], gap="large")
            with col1:
                ticket_title = st.text_input("Ticket Title*", placeholder="e.g., Network drive inaccessible")
                email = st.text_input("Email*", placeholder="e.g., user@company.com", value=user_info.get("email", ""))
                initial_priority = st.selectbox("Initial Priority*", options=PRIORITY_OPTIONS)
            with col2:
                today = datetime.now().date()
                due_date = st.date_input("Due Date", value=today + timedelta(days=7))
                company_id = st.text_input("Company ID*", placeholder="e.g., COMP-001", value=user_info.get("company_id", ""))
            ticket_description = st.text_area(
                "Description*",
                placeholder="Please describe your issue in detail...",
                height=150
            )
            
            # Additional technical details
            col1, col2 = st.columns(2)
            with col1:
                device_model = st.text_input("Device Model", placeholder="e.g., Dell Laptop")
                error_message = st.text_input("Error Message", placeholder="Any error codes or messages")
            with col2:
                os_version = st.text_input("Operating System", placeholder="e.g., Windows 11")

            submitted = st.form_submit_button("Submit Ticket", type="primary")

            if submitted:
                required_fields = {
                    "Title": ticket_title,
                    "Email": email,
                    "Priority": initial_priority,
                    "Due Date": due_date,
                    "Company ID": company_id,
                    "Description": ticket_description
                }
                missing_fields = [field for field, value in required_fields.items() if not value]

                if missing_fields:
                    st.warning(f"⚠️ Please fill in all required fields: {', '.join(missing_fields)}")
                else:
                    # Save the ticket for the current user
                    ticket_data = {
                        'title': ticket_title,
                        'email': email,
                        'priority': initial_priority,
                        'due_date': due_date.isoformat(),
                        'company_id': company_id,
                        'description': ticket_description,
                        'device_model': device_model,
                        'os_version': os_version,
                        'error_message': error_message,
                        'category': 'Pending Classification',
                        'resolution_notes': 'Pending Resolution'
                    }
                    ticket_id = save_user_ticket(current_user, ticket_data)
                    
                    st.success(f"✅ Ticket {ticket_id} submitted successfully!")
                    
                    # Display all details of the submitted ticket
                    st.subheader("Ticket Submission Summary")
                    st.markdown(f"""
                    <div class="card">
                    <table style="width:100%">
                        <tr><td><strong>Ticket ID</strong></td><td>{ticket_id}</td></tr>
                        <tr><td><strong>Title</strong></td><td>{ticket_title}</td></tr>
                        <tr><td><strong>Email</strong></td><td>{email}</td></tr>
                        <tr><td><strong>Priority</strong></td><td>{initial_priority}</td></tr>
                        <tr><td><strong>Due Date</strong></td><td>{due_date.strftime('%Y-%m-%d')}</td></tr>
                        <tr><td><strong>Company ID</strong></td><td>{company_id}</td></tr>
                        <tr><td><strong>Description</strong></td><td>{ticket_description}</td></tr>
                        <tr><td><strong>Device Model</strong></td><td>{device_model}</td></tr>
                        <tr><td><strong>OS Version</strong></td><td>{os_version}</td></tr>
                        <tr><td><strong>Error Message</strong></td><td>{error_message}</td></tr>
                        <tr><td><strong>Category (Backend Classified)</strong></td><td>Pending Classification</td></tr>
                        <tr><td><strong>Resolution Steps (Backend Provided)</strong></td><td>Pending Resolution</td></tr>
                    </table>
                    </div>
                    """, unsafe_allow_html=True)

                    # Mock classification results (updated to reflect new fields)
                    with st.expander("📋 Ticket Classification Results", expanded=True):
                        cols = st.columns(3)
                        cols[0].metric("Issue Type", "Pending Classification")
                        cols[1].metric("Type", "Support Request")
                        cols[2].metric("Priority", initial_priority)

                        st.markdown(f"""
                        <div class="card">
                        <table style="width:100%">
                            <tr><td><strong>Ticket ID</strong></td><td>{ticket_id}</td></tr>
                            <tr><td><strong>Ticket Title</strong></td><td>{ticket_title}</td></tr>
                            <tr><td><strong>Category</strong></td><td>Pending Classification</td></tr>
                            <tr><td><strong>Priority Level</strong></td><td>{initial_priority}</td></tr>
                            <tr><td><strong>Requester</strong></td><td>{user_info.get("name", "Unknown")}</td></tr>
                            <tr><td><strong>Email</strong></td><td>{email}</td></tr>
                            <tr><td><strong>Company ID</strong></td><td>{company_id}</td></tr>
                        </table>
                        </div>
                        """, unsafe_allow_html=True)
                    # Next steps
                    st.markdown(f"""
                    <div class="card" style="background-color: var(--accent);">
                    <h4>Next Steps</h4>
                    <ol>
                        <li>Your ticket <strong>{ticket_id}</strong> has been submitted successfully</li>
                        <li>The ticket has been assigned to the <strong>Pending Classification</strong> support team</li>
                        <li>You\'ll receive a confirmation email at <strong>{email}</strong></li>
                        <li>A support specialist will contact you within 2 business hours</li>
                        <li>Priority level: <strong>{initial_priority}</strong> - Response time varies accordingly</li>
                        <li>You can track your ticket status in the "My Tickets" section</li>
                    </ol>
                    </div>
                    """, unsafe_allow_html=True)

    # User's recent tickets preview
    st.markdown("---")
    st.subheader("📋 Your Recent Tickets")
    
    user_tickets = get_user_tickets(current_user)
    recent_tickets = user_tickets[:5]  # Show last 5 tickets
    
    if recent_tickets:
        for ticket in recent_tickets:
            with st.expander(f"{ticket['id']} - {ticket['title']} ({ticket['status']})", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Created:** {format_date_display(ticket['created_at'])}")
                    st.markdown(f"**Priority:** {PRIORITY_COLORS[ticket['priority']]} {ticket['priority']}")
                    st.markdown(f"**Category:** {ticket['category']}")
                with col2:
                    st.markdown(f"**Status:** {ticket['status']}")
                    st.markdown(f"**Time Elapsed:** {format_time_elapsed(ticket['created_at'])}")
                    if ticket['assigned_technician']:
                        st.markdown(f"**Assigned to:** {ticket['assigned_technician']}")
                
                st.markdown(f"**Description:** {ticket['description']}")
                
                if ticket['resolution_notes']:
                    st.markdown(f"**Resolution:** {ticket['resolution_notes']}")
    else:
        st.info("You haven't submitted any tickets yet. Use the form above to submit your first ticket!")

def recent_tickets_page():
    """Dynamic recent tickets page showing only current user's tickets"""
    current_user = st.session_state.get('current_user', '')
    user_info = st.session_state.get('user_info', {})
    
    # Get user-specific tickets
    user_tickets = get_user_tickets(current_user)
    
    with st.container():
        if st.button("← Back to Home", key="rt_back"):
            st.session_state.page = "main"
            st.rerun()

        st.title(f"🕑 My Tickets - {user_info.get('name', 'User')}")
        
        st.markdown(f"""
        <div class="card">
        <strong>Showing tickets for:</strong> {user_info.get('name', 'Unknown')} ({current_user})<br>
        <strong>Email:</strong> {user_info.get('email', 'Unknown')}<br>
        <strong>Department:</strong> {user_info.get('department', 'Unknown')}<br>
        <strong>Total Tickets:</strong> {len(user_tickets)}
        </div>
        """, unsafe_allow_html=True)

        # Filter Selection Tabs
        tab1, tab2, tab3 = st.tabs(["⏰ Duration Filter", "📅 Date Range Filter", "📆 Specific Date Filter"])

        tickets_to_display = []
        filter_description = ""

        with tab1:
            st.markdown("### Select Time Duration")
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                selected_duration = st.selectbox(
                    "📅 Select Time Duration:",
                    options=DURATION_OPTIONS,
                    index=0,  # Default to "Last hour"
                    key="duration_selector"
                )

            with col2:
                if st.button("Apply Duration Filter", key="apply_duration"):
                    tickets_to_display = get_tickets_by_duration(selected_duration, user_tickets)
                    filter_description = f"{get_duration_icon(selected_duration)} {selected_duration}"
                    st.session_state.active_filter = "duration"
                    st.session_state.filter_description = filter_description
                    st.session_state.tickets_to_display = tickets_to_display

            with col3:
                st.metric("Tickets Found", len(get_tickets_by_duration(selected_duration, user_tickets)))

        with tab2:
            st.markdown("### Select Date Range")
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

            with col1:
                start_date = st.date_input(
                    "From Date:",
                    value=datetime.now().date() - timedelta(days=7),
                    key="start_date"
                )

            with col2:
                end_date = st.date_input(
                    "To Date:",
                    value=datetime.now().date(),
                    key="end_date"
                )

            with col3:
                if st.button("Apply Date Range", key="apply_date_range"):
                    if start_date <= end_date:
                        tickets_to_display = get_tickets_by_date_range(start_date, end_date, user_tickets)
                        filter_description = f"📅 {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                        st.session_state.active_filter = "date_range"
                        st.session_state.filter_description = filter_description
                        st.session_state.tickets_to_display = tickets_to_display
                    else:
                        st.error("Start date must be before or equal to end date!")

            with col4:
                if 'start_date' in st.session_state and 'end_date' in st.session_state:
                    preview_tickets = get_tickets_by_date_range(
                        st.session_state.start_date, 
                        st.session_state.end_date,
                        user_tickets
                    )
                    st.metric("Tickets Found", len(preview_tickets))

        with tab3:
            st.markdown("### Select Specific Date")
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                specific_date = st.date_input(
                    "Select Date:",
                    value=datetime.now().date(),
                    key="specific_date"
                )

            with col2:
                if st.button("Apply Date Filter", key="apply_specific_date"):
                    tickets_to_display = get_tickets_by_specific_date(specific_date, user_tickets)
                    filter_description = f"📆 {specific_date.strftime('%Y-%m-%d')}"
                    st.session_state.active_filter = "specific_date"
                    st.session_state.filter_description = filter_description
                    st.session_state.tickets_to_display = tickets_to_display

            with col3:
                preview_tickets = get_tickets_by_specific_date(specific_date, user_tickets)
                st.metric("Tickets Found", len(preview_tickets))

        # Use session state to maintain filter results
        if 'tickets_to_display' in st.session_state and 'filter_description' in st.session_state:
            tickets_to_display = st.session_state.tickets_to_display
            filter_description = st.session_state.filter_description
        else:
            # Default to all tickets if no filter applied
            tickets_to_display = user_tickets
            filter_description = "📋 All my tickets"

        # Display current filter and refresh option
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Current Filter:** {filter_description}")
        with col2:
            if st.button("🔄 Refresh", key="refresh_tickets"):
                st.rerun()

        # Display filtered tickets
        st.markdown(f"""
        <div class="card">
        <h3>{filter_description}</h3>
        <p>Showing {len(tickets_to_display)} of {len(user_tickets)} total tickets</p>
        </div>
        """, unsafe_allow_html=True)

        if tickets_to_display:
            # Add pagination for large result sets
            tickets_per_page = TICKETS_PER_PAGE
            total_pages = (len(tickets_to_display) + tickets_per_page - 1) // tickets_per_page

            if total_pages > 1:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    page_number = st.selectbox(
                        f"Page (showing {tickets_per_page} tickets per page):",
                        options=list(range(1, total_pages + 1)),
                        key="page_selector"
                    )

                start_idx = (page_number - 1) * tickets_per_page
                end_idx = start_idx + tickets_per_page
                tickets_to_show = tickets_to_display[start_idx:end_idx]
            else:
                tickets_to_show = tickets_to_display

            # Display tickets
            for i, ticket in enumerate(tickets_to_show):
                time_elapsed = format_time_elapsed(ticket['created_at'])
                date_created = format_date_display(ticket['created_at'])

                # Special highlighting for critical/urgent tickets
                is_urgent = ticket.get('priority') in ['Critical', 'Desktop/User Down']

                with st.expander(
                    f"{'🔥' if is_urgent else '📋'} {ticket['id']} - {ticket['title']} ({time_elapsed})",
                    expanded=False
                ):
                    # Ticket header with date
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"**📅 Created:** {date_created}")
                    with col2:
                        st.markdown(f"**⏰ Time Elapsed:** {time_elapsed}")

                    # Ticket details
                    cols = st.columns([1, 1, 1, 1])
                    cols[0].markdown(f"**Category:** {ticket.get('category', 'General')}")
                    cols[1].markdown(f"**Priority:** {PRIORITY_COLORS[ticket['priority']]} {ticket['priority']}")
                    cols[2].markdown(f"**Status:** {ticket['status']}")
                    cols[3].markdown(f"**Department:** {ticket.get('department', 'Unknown')}")

                    # Description
                    st.markdown(f"**Description:** {ticket['description']}")

                    # Technical details
                    if ticket.get('device_model') or ticket.get('os_version') or ticket.get('error_message'):
                        st.markdown("**Technical Details:**")
                        if ticket.get('device_model'):
                            st.markdown(f"• Device: {ticket['device_model']}")
                        if ticket.get('os_version'):
                            st.markdown(f"• OS: {ticket['os_version']}")
                        if ticket.get('error_message'):
                            st.markdown(f"• Error: {ticket['error_message']}")

                    # Assignment and resolution info
                    if ticket.get('assigned_technician'):
                        st.markdown(f"**👨‍🔧 Assigned Technician:** {ticket['assigned_technician']}")
                    
                    if ticket.get('resolution_notes'):
                        st.markdown("**✅ Resolution Notes:**")
                        st.markdown(ticket['resolution_notes'])

            # Show pagination info
            if total_pages > 1:
                st.info(f"Showing page {page_number} of {total_pages} ({len(tickets_to_display)} total tickets)")

        else:
            st.info(f"No tickets found for the selected filter: {filter_description}")

        # Summary statistics for user's filtered tickets
        if tickets_to_display:
            st.markdown("---")
            st.markdown("### 📊 My Ticket Statistics")

            # Calculate stats for the filtered tickets
            status_counts = {}
            priority_counts = {}
            category_counts = {}

            for ticket in tickets_to_display:
                # Status counts
                status = ticket.get('status', 'Open')
                status_counts[status] = status_counts.get(status, 0) + 1

                # Priority counts
                priority = ticket.get('priority', 'Medium')
                priority_counts[priority] = priority_counts.get(priority, 0) + 1

                # Category counts
                category = ticket.get('category', 'General')
                category_counts[category] = category_counts.get(category, 0) + 1

            # Main metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total", len(tickets_to_display))
            col2.metric("Open", status_counts.get('Open', 0))
            col3.metric("In Progress", status_counts.get('In Progress', 0))
            col4.metric("Resolved", status_counts.get('Resolved', 0))

            # Detailed breakdown
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**📂 My Categories:**")
                for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / len(tickets_to_display)) * 100
                    st.write(f"• {category}: {count} ({percentage:.1f}%)")

            with col2:
                st.markdown("**⚡ My Priorities:**")
                priority_order = ["Critical", "Desktop/User Down", "High", "Medium", "Low"]
                for priority in priority_order:
                    if priority in priority_counts:
                        count = priority_counts[priority]
                        percentage = (count / len(tickets_to_display)) * 100
                        icon = PRIORITY_COLORS.get(priority, "⚪")
                        st.write(f"• {icon} {priority}: {count} ({percentage:.1f}%)")

def dashboard_page():
    """Dashboard page with analytics and charts for current user."""
    current_user = st.session_state.get('current_user', '')
    user_info = st.session_state.get('user_info', {})
    
    st.title(f"📊 My Dashboard - {user_info.get('name', 'User')}")

    # Get user-specific tickets
    user_tickets = get_user_tickets(current_user)
    
    # --- FILTERS ---
    st.markdown("### Filters")
    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        # Date range filter
        date_min = datetime.now().date() - timedelta(days=30)
        date_max = datetime.now().date()
        date_range = st.date_input("Date Range", value=(date_min, date_max), min_value=date_min, max_value=date_max)

    with col2:
        status_filter = st.multiselect("Status", options=STATUS_OPTIONS, default=STATUS_OPTIONS)

    with col3:
        priority_filter = st.multiselect("Priority", options=PRIORITY_OPTIONS, default=PRIORITY_OPTIONS)

    # Filter user tickets based on selections
    filtered_tickets = []
    for ticket in user_tickets:
        try:
            ticket_date = datetime.fromisoformat(ticket['created_at']).date()
            if (date_range[0] <= ticket_date <= date_range[1] and 
                ticket['status'] in status_filter and 
                ticket['priority'] in priority_filter):
                filtered_tickets.append(ticket)
        except:
            continue

    # Calculate metrics
    total_tickets = len(filtered_tickets)
    open_tickets = sum(1 for t in filtered_tickets if t['status'] == 'Open')
    resolved_tickets = sum(1 for t in filtered_tickets if t['status'] == 'Resolved')
    in_progress_tickets = sum(1 for t in filtered_tickets if t['status'] == 'In Progress')
    
    # Last 24h count
    cutoff_24h = datetime.now() - timedelta(hours=24)
    last_24h = sum(1 for t in filtered_tickets 
                   if datetime.fromisoformat(t['created_at']) >= cutoff_24h)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("My Total Tickets", total_tickets)
    col2.metric("Last 24 Hours", last_24h)
    col3.metric("Open", open_tickets)
    col4.metric("In Progress", in_progress_tickets)
    col5.metric("Resolved", resolved_tickets)

    # --- Prepare data for charts ---
    status_counts = Counter(t['status'] for t in filtered_tickets)
    priority_counts = Counter(t['priority'] for t in filtered_tickets)
    category_counts = Counter(t['category'] for t in filtered_tickets)

    # --- Plotly Charts ---
    st.subheader("My Tickets by Status, Priority, and Category")
    
    # Create charts
    col1, col2, col3 = st.columns(3)
    
    # Get theme for chart styling
    theme = st.session_state.get('theme', 'dark')
    plot_bg = "#181818" if theme == 'dark' else "#ffffff"
    paper_bg = "#181818" if theme == 'dark' else "#ffffff"
    font_color = "#f8f9fa" if theme == 'dark' else "#212529"
    
    with col1:
        if status_counts:
            fig_status = px.bar(
                x=list(status_counts.keys()), 
                y=list(status_counts.values()),
                title="My Tickets by Status",
                color=list(status_counts.keys()),
                color_discrete_map=STATUS_COLORS
            )
            fig_status.update_layout(
                plot_bgcolor=plot_bg,
                paper_bgcolor=paper_bg,
                font_color=font_color,
                showlegend=False
            )
            st.plotly_chart(fig_status, use_container_width=True)
    
    with col2:
        if priority_counts:
            priority_color_map = {
                "Low": "#1cc88a", "Medium": "#36b9cc", "High": "#f6c23e", 
                "Critical": "#e74a3b", "Desktop/User Down": "#6f42c1"
            }
            fig_priority = px.bar(
                x=list(priority_counts.keys()), 
                y=list(priority_counts.values()),
                title="My Tickets by Priority",
                color=list(priority_counts.keys()),
                color_discrete_map=priority_color_map
            )
            fig_priority.update_layout(
                plot_bgcolor=plot_bg,
                paper_bgcolor=paper_bg,
                font_color=font_color,
                showlegend=False
            )
            st.plotly_chart(fig_priority, use_container_width=True)
    
    with col3:
        if category_counts:
            fig_category = px.bar(
                x=list(category_counts.keys()), 
                y=list(category_counts.values()),
                title="My Tickets by Category"
            )
            fig_category.update_layout(
                plot_bgcolor=plot_bg,
                paper_bgcolor=paper_bg,
                font_color=font_color,
                showlegend=False
            )
            st.plotly_chart(fig_category, use_container_width=True)

    # Recent tickets section
    st.subheader("My Recent Tickets")
    if filtered_tickets:
        recent_tickets = sorted(filtered_tickets, key=lambda x: x['created_at'], reverse=True)[:10]
        
        for ticket in recent_tickets:
            with st.expander(f"{ticket['title']} ({format_date_display(ticket['created_at'])})", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Category:** {ticket['category']}")
                    st.markdown(f"**Priority:** {PRIORITY_COLORS[ticket['priority']]} {ticket['priority']}")
                    st.markdown(f"**Status:** {ticket['status']}")
                    st.markdown(f"**Created At:** {format_date_display(ticket['created_at'])}")
                with col2:
                    st.markdown(f"**Department:** {ticket.get('department', 'Unknown')}")
                    st.markdown(f"**Email:** {ticket.get('requester_email', 'Unknown')}")
                    if ticket.get('assigned_technician'):
                        st.markdown(f"**Assigned to:** {ticket['assigned_technician']}")
                    st.markdown(f"**Time Elapsed:** {format_time_elapsed(ticket['created_at'])}")
                
                st.markdown(f"**Description:** {ticket['description']}")
                
                if ticket.get('resolution_notes'):
                    st.markdown(f"**Resolution:** {ticket['resolution_notes']}")
    else:
        st.info("No tickets found for the selected filters.")

def main():
    """Main application entry point."""
    # Page configuration
    st.set_page_config(
        page_title=PAGE_TITLE,
        layout=LAYOUT,
        page_icon=PAGE_ICON,
        initial_sidebar_state="expanded"
    )

    # Initialize session state with default user and theme
    if "page" not in st.session_state:
        st.session_state.page = "main"
    
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"
    
    # Set default user (you can change this or make it configurable)
    if "current_user" not in st.session_state:
        st.session_state.current_user = "user1"
        st.session_state.user_info = {
            "name": "John Doe",
            "email": "john.doe@company.com", 
            "phone": "+1-555-123-4567",
            "company_id": "COMP-001",
            "department": "IT Department"
        }

    # Apply custom CSS based on theme
    apply_custom_css()

    # Create sidebar
    create_sidebar()

    # Route to appropriate page
    if st.session_state.page == "main":
        main_page()
    elif st.session_state.page == "recent_tickets":
        recent_tickets_page()
    elif st.session_state.page == "dashboard":
        dashboard_page()

if __name__ == "__main__":
    main()