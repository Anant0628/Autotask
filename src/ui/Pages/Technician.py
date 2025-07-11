import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
from collections import Counter
from typing import List, Dict
import random

# Configuration Constants
PAGE_TITLE = "TechLogic - Technician Dashboard"
LAYOUT = "wide"
PAGE_ICON = "🔧"
PRIORITY_OPTIONS = ["Low", "Medium", "High", "Critical", "Desktop/User Down"]
STATUS_OPTIONS = ["Assigned", "In Progress", "Pending Parts", "Resolved", "Closed"]
TECHNICIAN_STATUS = ["Available", "Busy", "On Break", "Off Duty"]
TICKET_TYPES = ["Hardware", "Software", "Network", "Security", "General"]
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
    "Assigned": "#4e73df",
    "In Progress": "#f6c23e", 
    "Pending Parts": "#fd7e14",
    "Resolved": "#36b9cc", 
    "Closed": "#1cc88a"
}

def apply_custom_css():
    """Apply custom CSS styling with theme support for technician dashboard."""
    
    # Get current theme from session state
    theme = st.session_state.get('theme', 'dark')
    
    if theme == 'dark':
        # Dark Theme Variables
        theme_vars = """
        :root {
            --primary: #28a745;
            --primary-hover: #218838;
            --secondary: #181818;
            --accent: #23272f;
            --text-main: #f8f9fa;
            --text-secondary: #b0b3b8;
            --card-bg: #23272f;
            --sidebar-bg: #111111;
            --tech-accent: #17a2b8;
            --border-color: #444;
            --hover-bg: #2d2d2d;
            --urgent-bg: #2d1b1b;
            --progress-bg: #2d2a1b;
            --success-bg: #1e5f3a;
            --info-bg: #1e3a5f;
        }
        """
    else:
        # Light Theme Variables
        theme_vars = """
        :root {
            --primary: #007bff;
            --primary-hover: #0056b3;
            --secondary: #ffffff;
            --accent: #f8f9fa;
            --text-main: #212529;
            --text-secondary: #6c757d;
            --card-bg: #ffffff;
            --sidebar-bg: #f8f9fa;
            --tech-accent: #17a2b8;
            --border-color: #dee2e6;
            --hover-bg: #f8f9fa;
            --urgent-bg: #fff5f5;
            --progress-bg: #fffbf0;
            --success-bg: #f0fff4;
            --info-bg: #f0f8ff;
        }
        """
    
    st.markdown(f"""
    <style>
    {theme_vars}
    
    .main {{
        background-color: var(--secondary);
        color: var(--text-main);
    }}
    
    body, .stApp, .main, .block-container {{
        background-color: var(--secondary) !important;
        color: var(--text-main) !important;
    }}
    
    .stTextInput input, .stTextArea textarea,
    .stSelectbox select, .stDateInput input {{
        background-color: var(--card-bg) !important;
        color: var(--text-main) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 6px !important;
    }}
    
    .stButton>button {{
        background-color: var(--primary) !important;
        color: white !important;
        border: none;
        padding: 10px 24px;
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.3s ease;
    }}
    
    .stButton>button:hover {{
        background-color: var(--primary-hover) !important;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }}
    
    .tech-card {{
        background-color: var(--card-bg);
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.15);
        margin-bottom: 20px;
        color: var(--text-main);
        border-left: 4px solid var(--tech-accent);
        border: 1px solid var(--border-color);
    }}
    
    .urgent-ticket {{
        border-left: 4px solid #dc3545 !important;
        background-color: var(--urgent-bg) !important;
    }}
    
    .in-progress-ticket {{
        border-left: 4px solid #ffc107 !important;
        background-color: var(--progress-bg) !important;
    }}
    
    .sidebar .sidebar-content, .stSidebar, section[data-testid="stSidebar"] {{
        background-color: var(--sidebar-bg) !important;
        color: var(--text-main) !important;
    }}
    
    .status-badge {{
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8em;
        font-weight: bold;
        text-align: center;
        display: inline-block;
        margin: 2px;
    }}
    
    .status-assigned {{ background-color: #4e73df; color: white; }}
    .status-in-progress {{ background-color: #f6c23e; color: black; }}
    .status-pending {{ background-color: #fd7e14; color: white; }}
    .status-resolved {{ background-color: #36b9cc; color: white; }}
    .status-closed {{ background-color: #1cc88a; color: white; }}
    
    /* Theme Toggle Button Styling */
    .theme-toggle {{
        background-color: var(--accent);
        border: 1px solid var(--border-color);
        border-radius: 20px;
        padding: 5px 15px;
        color: var(--text-main);
        font-size: 0.9em;
        margin-bottom: 10px;
    }}
    
    /* Expander Styling */
    .streamlit-expanderHeader {{
        background-color: var(--card-bg) !important;
        color: var(--text-main) !important;
        border: 1px solid var(--border-color) !important;
    }}
    
    .streamlit-expanderContent {{
        background-color: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
    }}
    
    /* Metric Styling */
    .metric-container {{
        background-color: var(--card-bg);
        padding: 15px;
        border-radius: 8px;
        border: 1px solid var(--border-color);
        text-align: center;
    }}
    
    /* Form Styling */
    .stForm {{
        background-color: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
    }}
    
    /* Selectbox Styling */
    .stSelectbox > div > div {{
        background-color: var(--card-bg) !important;
        color: var(--text-main) !important;
    }}
    
    /* Multiselect Styling */
    .stMultiSelect > div > div {{
        background-color: var(--card-bg) !important;
        color: var(--text-main) !important;
    }}
    
    /* Success/Info/Warning Messages */
    .stSuccess {{
        background-color: var(--success-bg) !important;
        color: var(--text-main) !important;
    }}
    
    .stInfo {{
        background-color: var(--info-bg) !important;
        color: var(--text-main) !important;
    }}
    
    .stWarning {{
        background-color: var(--progress-bg) !important;
        color: var(--text-main) !important;
    }}
    
    /* Chart Background */
    .js-plotly-plot {{
        background-color: var(--card-bg) !important;
    }}
    
    </style>
    """, unsafe_allow_html=True)

def create_theme_toggle():
    """Create theme toggle in sidebar"""
    current_theme = st.session_state.get('theme', 'dark')
    
    st.markdown("### 🎨 Theme")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🌙 Dark", key="dark_theme", use_container_width=True, 
                    type="primary" if current_theme == 'dark' else "secondary"):
            st.session_state.theme = 'dark'
            st.rerun()
    
    with col2:
        if st.button("☀️ Light", key="light_theme", use_container_width=True,
                    type="primary" if current_theme == 'light' else "secondary"):
            st.session_state.theme = 'light'
            st.rerun()
    
    st.markdown(f"**Current:** {current_theme.title()} Mode")

def create_technician_sidebar():
    """Create the technician navigation sidebar."""
    with st.sidebar:
        # Theme Toggle at the top
        create_theme_toggle()
        
        st.markdown("---")
        
        # Technician Profile Section
        st.markdown("## 👨‍🔧 Technician Profile")
        
        # Mock technician info
        tech_name = st.session_state.get('tech_name', 'John Smith')
        tech_id = st.session_state.get('tech_id', 'TECH-001')
        
        st.markdown(f"**Name:** {tech_name}")
        st.markdown(f"**ID:** {tech_id}")
        
        # Status selector
        current_status = st.selectbox(
            "Status:",
            TECHNICIAN_STATUS,
            index=0,
            key="tech_status"
        )
        
        st.markdown("---")
        
        # Navigation
        st.markdown("## 🧭 Navigation")

        if st.button("🏠 My Dashboard", key="nav_dashboard", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()

        if st.button("📋 My Tickets", key="nav_my_tickets", use_container_width=True):
            st.session_state.page = "my_tickets"
            st.rerun()

        if st.button("⚡ Urgent Tickets", key="nav_urgent", use_container_width=True):
            st.session_state.page = "urgent_tickets"
            st.rerun()

        if st.button("📊 Work Analytics", key="nav_analytics", use_container_width=True):
            st.session_state.page = "analytics"
            st.rerun()

        # Show current page
        current_page = st.session_state.get('page', 'dashboard')
        st.markdown(f"**Current:** {current_page.replace('_', ' ').title()}")

        st.markdown("---")

        # Quick Stats for Technician
        st.markdown("### 📈 Today's Stats")
        
        # Mock stats
        assigned_today = random.randint(3, 8)
        completed_today = random.randint(1, 5)
        in_progress = random.randint(1, 3)
        
        st.metric("Assigned Today", assigned_today)
        st.metric("Completed", completed_today)
        st.metric("In Progress", in_progress)
        
        # Performance indicator
        completion_rate = (completed_today / max(assigned_today, 1)) * 100
        st.metric("Completion Rate", f"{completion_rate:.1f}%")

        st.markdown("---")
        
        # Quick Actions
        st.markdown("### ⚡ Quick Actions")
        if st.button("🔄 Refresh Data", key="refresh_data", use_container_width=True):
            st.rerun()
        
        if st.button("📝 Add Work Note", key="add_note", use_container_width=True):
            st.session_state.show_note_modal = True

        # Contact Information
        st.markdown("---")
        st.markdown("### 📞 Support")
        st.markdown(f"**Phone:** {SUPPORT_PHONE}")
        st.markdown(f"**Email:** {SUPPORT_EMAIL}")

def generate_technician_tickets(tech_id="TECH-001", count=25):
    """Generate mock tickets assigned to technician with enhanced details"""
    
    mock_issues = [
        {
            "title": "Computer won't start - power button not responding",
            "description": "User reports that when pressing the power button, nothing happens. No lights, no fans, no display. Issue started this morning after a power outage last night.",
            "category": "Hardware", # Backend classified
            "resolution_steps": [
                "1. Check power cable connection to both computer and wall outlet",
                "2. Test wall outlet with another device to verify power",
                "3. Try different power cable if available",
                "4. Check for loose internal power connections",
                "5. Test power supply unit with multimeter",
                "6. If PSU failed, replace with compatible unit"
            ]
        },
        {
            "title": "Printer showing paper jam error but no paper stuck",
            "description": "HP LaserJet Pro showing persistent paper jam error message. User has checked all paper paths and found no stuck paper. Printer worked fine yesterday.",
            "category": "Hardware",
            "resolution_steps": [
                "1. Power cycle the printer (off for 30 seconds, then on)",
                "2. Open all printer doors and check for small paper fragments",
                "3. Check paper sensors for dust or debris",
                "4. Clean paper path with compressed air",
                "5. Reset printer to factory defaults if issue persists",
                "6. Update printer firmware if available"
            ]
        },
        {
            "title": "Network drive mapping issues - cannot access shared folders",
            "description": "User cannot access network shared folders that were working yesterday. Getting 'Network path not found' error when trying to connect to \\\\server\\shared.",
            "category": "Network",
            "resolution_steps": [
                "1. Verify network connectivity with ping test to server",
                "2. Check if user credentials are still valid",
                "3. Test access from another computer on same network",
                "4. Clear cached credentials in Windows Credential Manager",
                "5. Re-map network drive with current credentials",
                "6. Check server-side permissions and share settings"
            ]
        },
        {
            "title": "Email client crashes when opening attachments",
            "description": "Outlook 2019 crashes immediately when user tries to open any email attachment. Error occurs with all file types. Started after Windows update last week.",
            "category": "Software",
            "resolution_steps": [
                "1. Start Outlook in Safe Mode to test functionality",
                "2. Disable all Outlook add-ins temporarily",
                "3. Run Outlook repair tool from Control Panel",
                "4. Check for and install latest Outlook updates",
                "5. Create new Outlook profile if issue persists",
                "6. Reinstall Outlook if other solutions fail"
            ]
        },
        {
            "title": "Monitor display flickering and showing color distortion",
            "description": "Dell 24-inch monitor showing intermittent flickering and color distortion, particularly red tint on left side of screen. Issue is getting progressively worse.",
            "category": "Hardware",
            "resolution_steps": [
                "1. Check and reseat video cable connections",
                "2. Test with different video cable (HDMI/DisplayPort)",
                "3. Connect monitor to different computer to isolate issue",
                "4. Update graphics drivers on computer",
                "5. Check monitor settings and reset to factory defaults",
                "6. If hardware failure confirmed, arrange monitor replacement"
            ]
        }
    ]
    
    mock_locations = [
        "Building A - Floor 2", "Building B - Floor 1", "Building A - Floor 3",
        "Building C - Reception", "Building B - Floor 2", "Remote Location",
        "Building A - IT Room", "Building C - IT Room", "Building B - Floor 3"
    ]
    
    mock_requesters = [
        {"name": "Alice Johnson", "email": "alice.johnson@company.com"},
        {"name": "Bob Wilson", "email": "bob.wilson@company.com"},
        {"name": "Carol Davis", "email": "carol.davis@company.com"},
        {"name": "David Brown", "email": "david.brown@company.com"},
        {"name": "Emma Taylor", "email": "emma.taylor@company.com"},
        {"name": "Frank Miller", "email": "frank.miller@company.com"},
        {"name": "Grace Lee", "email": "grace.lee@company.com"},
        {"name": "Henry Clark", "email": "henry.clark@company.com"},
        {"name": "Ivy Martinez", "email": "ivy.martinez@company.com"},
        {"name": "Jack Anderson", "email": "jack.anderson@company.com"}
    ]
    
    tickets = []
    for i in range(count):
        created_time = datetime.now() - timedelta(
            hours=random.randint(1, 168),  # Last week
            minutes=random.randint(0, 59)
        )
        
        # Assign status based on time (newer tickets more likely to be assigned/in progress)
        hours_old = (datetime.now() - created_time).total_seconds() / 3600
        if hours_old < 2:
            status = random.choice(["Assigned", "In Progress"])
        elif hours_old < 24:
            status = random.choice(["Assigned", "In Progress", "Pending Parts"])
        else:
            status = random.choice(["In Progress", "Pending Parts", "Resolved", "Closed"])
        
        issue_data = random.choice(mock_issues)
        requester_data = random.choice(mock_requesters)
        
        ticket = {
            "id": f"TKT-{2000 + i}",
            "title": issue_data["title"],
            "description": issue_data["description"],
            "created_at": created_time.isoformat(),
            "assigned_at": (created_time + timedelta(minutes=random.randint(5, 60))).isoformat(),
            "status": status,
            "priority": random.choice(PRIORITY_OPTIONS),
            "category": issue_data["category"],  # Backend classified
            "requester_name": requester_data["name"],
            "requester_email": requester_data["email"],
            "requester_phone": f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
            "location": random.choice(mock_locations),
            "assigned_technician": tech_id,
            "estimated_hours": random.randint(1, 8),
            "actual_hours": random.randint(1, 6) if status in ["Resolved", "Closed"] else None,
            "parts_needed": random.choice([None, "RAM Module", "Hard Drive", "Network Cable", "Power Supply"]),
            "resolution_steps": issue_data["resolution_steps"],  # Backend generated
            "work_notes": [],
            "updated_at": created_time.isoformat()
        }
        
        # Add work notes for tickets in progress or completed
        if status in ["In Progress", "Resolved", "Closed"]:
            ticket["work_notes"] = [
                {
                    "timestamp": (created_time + timedelta(hours=1)).isoformat(),
                    "note": "Initial diagnosis completed. Issue identified.",
                    "technician": tech_id
                }
            ]
            
        if status in ["Resolved", "Closed"]:
            ticket["work_notes"].append({
                "timestamp": (created_time + timedelta(hours=2)).isoformat(),
                "note": "Solution implemented and tested. Issue resolved.",
                "technician": tech_id
            })
        
        tickets.append(ticket)
    
    return sorted(tickets, key=lambda x: x["created_at"], reverse=True)

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

def get_chart_theme():
    """Get chart theme based on current theme"""
    theme = st.session_state.get('theme', 'dark')
    
    if theme == 'dark':
        return {
            "plot_bgcolor": "#181818",
            "paper_bgcolor": "#23272f",
            "font_color": "#f8f9fa"
        }
    else:
        return {
            "plot_bgcolor": "#ffffff",
            "paper_bgcolor": "#ffffff", 
            "font_color": "#212529"
        }

def dashboard_page():
    """Main technician dashboard page with enhanced ticket details and dropdowns"""
    st.title("🔧 Technician Dashboard")
    
    # Generate mock data (In production, this would be API calls)
    tech_tickets = generate_technician_tickets()
    
    # Welcome message
    tech_name = st.session_state.get('tech_name', 'John Smith')
    current_time = datetime.now().strftime("%H:%M")
    current_theme = st.session_state.get('theme', 'dark')
    theme_icon = "🌙" if current_theme == 'dark' else "☀️"
    
    st.markdown(f"""
    <div class="tech-card">
    <h3>Welcome back, {tech_name}! 👋</h3>
    <p>Current time: {current_time} | Status: {st.session_state.get('tech_status', 'Available')} | Theme: {theme_icon} {current_theme.title()}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    assigned_tickets = [t for t in tech_tickets if t['status'] == 'Assigned']
    in_progress_tickets = [t for t in tech_tickets if t['status'] == 'In Progress']
    urgent_tickets = [t for t in tech_tickets if t['priority'] in ['Critical', 'Desktop/User Down']]
    today_tickets = [t for t in tech_tickets if datetime.fromisoformat(t['created_at']).date() == datetime.now().date()]
    resolved_today = [t for t in today_tickets if t['status'] == 'Resolved']
    
    col1.metric("🎯 Assigned", len(assigned_tickets))
    col2.metric("⚡ In Progress", len(in_progress_tickets))
    col3.metric("🚨 Urgent", len(urgent_tickets))
    col4.metric("📅 Today's Tickets", len(today_tickets))
    col5.metric("✅ Resolved Today", len(resolved_today))
    
    # Dropdown sections for different ticket categories
    
    # 1. Urgent Tickets Section
    if urgent_tickets:
        with st.expander(f"🚨 Urgent Tickets Requiring Immediate Attention ({len(urgent_tickets)})", expanded=False):
            for ticket in urgent_tickets[:5]:  # Show top 5 urgent
                display_enhanced_ticket_card(ticket, is_urgent=True, section="urgent")

    # 2. Assigned Tickets Section  
    if assigned_tickets:
        with st.expander(f"📋 Assigned Tickets ({len(assigned_tickets)})", expanded=False):
            for ticket in assigned_tickets[:5]:  # Show top 5 assigned
                display_enhanced_ticket_card(ticket, section="assigned")

    # 3. In Progress Tickets Section
    if in_progress_tickets:
        with st.expander(f"⚡ In Progress Tickets ({len(in_progress_tickets)})", expanded=False):
            for ticket in in_progress_tickets:
                display_enhanced_ticket_card(ticket, is_in_progress=True, section="in_progress")

def display_enhanced_ticket_card(ticket, is_urgent=False, is_in_progress=False, section="default"):
    """Display enhanced ticket card with all required details"""
    
    # Determine card styling
    card_class = "tech-card"
    if is_urgent:
        card_class += " urgent-ticket"
    elif is_in_progress:
        card_class += " in-progress-ticket"
    
    priority_icon = PRIORITY_COLORS.get(ticket['priority'], '⚪')
    
    # Create expandable ticket card
    with st.expander(f"{priority_icon} {ticket['id']} - {ticket['title']}", expanded=False):
        
        # Ticket Header Information
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown("### 👤 Requester Information")
            st.markdown(f"**Name:** {ticket['requester_name']}")
            st.markdown(f"**Email:** {ticket['requester_email']}")
            st.markdown(f"**Phone:** {ticket['requester_phone']}")
            st.markdown(f"**Location:** {ticket['location']}")
        
        with col2:
            st.markdown("### 🏷️ Ticket Details")
            st.markdown(f"**Category:** {ticket['category']}")
            st.markdown(f"**Priority:** {priority_icon} {ticket['priority']}")
            st.markdown(f"**Status:** {ticket['status']}")
            st.markdown(f"**Estimated Time:** {ticket['estimated_hours']}h")
        
        with col3:
            st.markdown("### ⏰ Timeline")
            st.markdown(f"**Created:** {format_time_elapsed(ticket['created_at'])}")
            st.markdown(f"**Assigned:** {format_time_elapsed(ticket['assigned_at'])}")
            if ticket['actual_hours']:
                st.markdown(f"**Actual Time:** {ticket['actual_hours']}h")
            if ticket['parts_needed']:
                st.markdown(f"**Parts Needed:** {ticket['parts_needed']}")
        
        st.markdown("---")
        
        # Issue Details Section
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 📝 Issue Details")
            st.markdown(f"**Title:** {ticket['title']}")
            st.markdown("**Description:**")
            st.markdown(f"*{ticket['description']}*")
        
        with col2:
            st.markdown("### 🔧 Resolution Steps")
            st.markdown("*Generated by AI Assistant:*")
            for i, step in enumerate(ticket['resolution_steps'], 1):
                st.markdown(f"{i}. {step}")
        
        st.markdown("---")
        
        # Work Notes Section (if any)
        if ticket['work_notes']:
            st.markdown("### 📋 Work Notes")
            for note in ticket['work_notes']:
                note_time = datetime.fromisoformat(note['timestamp']).strftime("%Y-%m-%d %H:%M")
                st.markdown(f"• **{note_time}**: {note['note']}")
            st.markdown("---")
        
        # Action Buttons Section - UPDATE ALL KEYS WITH SECTION PREFIX
        st.markdown("### ⚡ Actions")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if ticket['status'] == 'Assigned':
                if st.button("▶️ Start Work", key=f"{section}_start_{ticket['id']}", use_container_width=True):
                    st.success("Status updated to 'In Progress'")
                    # In production: API call to update ticket status
            elif ticket['status'] == 'In Progress':
                if st.button("✅ Mark Resolved", key=f"{section}_resolve_{ticket['id']}", use_container_width=True):
                    st.success("Status updated to 'Resolved'")
                    # In production: API call to update ticket status
        
        with col2:
            if st.button("📝 Add Note", key=f"{section}_note_{ticket['id']}", use_container_width=True):
                st.session_state[f"show_note_{section}_{ticket['id']}"] = True
        
        with col3:
            if st.button("📞 Call User", key=f"{section}_call_{ticket['id']}", use_container_width=True):
                st.info(f"Calling {ticket['requester_phone']}...")
                # In production: Integrate with phone system
        
        with col4:
            if st.button("✉️ Email User", key=f"{section}_email_{ticket['id']}", use_container_width=True):
                st.info(f"Opening email to {ticket['requester_email']}...")
                # In production: Open email client or send via API
        
        with col5:
            # Priority change dropdown
            new_priority = st.selectbox(
                "Change Priority:",
                PRIORITY_OPTIONS,
                index=PRIORITY_OPTIONS.index(ticket['priority']),
                key=f"{section}_priority_update_{ticket['id']}"
            )
            if new_priority != ticket['priority']:
                if st.button("Update", key=f"{section}_update_priority_{ticket['id']}", use_container_width=True):
                    st.success(f"Priority updated to {new_priority}")
                    # In production: API call to update priority
        
        # Add note modal (simplified) - UPDATE SESSION STATE KEY
        if st.session_state.get(f"show_note_{section}_{ticket['id']}", False):
            st.markdown("---")
            st.markdown("### 📝 Add Work Note")
            with st.form(f"{section}_note_form_{ticket['id']}"):
                note_text = st.text_area("Work Note:", height=100, placeholder="Enter your work note here...")
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Save Note", use_container_width=True):
                        if note_text.strip():
                            st.success("Work note added successfully!")
                            st.session_state[f"show_note_{section}_{ticket['id']}"] = False
                            # In production: API call to save note
                        else:
                            st.error("Please enter a note")
                with col2:
                    if st.form_submit_button("❌ Cancel", use_container_width=True):
                        st.session_state[f"show_note_{section}_{ticket['id']}"] = False

# Backend Integration Helper Functions (Ready for API integration)
def update_ticket_status(ticket_id, new_status, technician_id):
    """Update ticket status - Ready for backend API integration"""
    # In production, this would make an API call
    # Example: requests.put(f"/api/tickets/{ticket_id}/status", {"status": new_status, "technician": technician_id})
    pass

def update_ticket_priority(ticket_id, new_priority, technician_id):
    """Update ticket priority - Ready for backend API integration"""
    # In production, this would make an API call
    # Example: requests.put(f"/api/tickets/{ticket_id}/priority", {"priority": new_priority, "technician": technician_id})
    pass

def add_work_note(ticket_id, note_text, technician_id):
    """Add work note to ticket - Ready for backend API integration"""
    # In production, this would make an API call
    # Example: requests.post(f"/api/tickets/{ticket_id}/notes", {"note": note_text, "technician": technician_id})
    pass

def get_technician_tickets(technician_id):
    """Fetch tickets from backend - Ready for API integration"""
    # In production, this would make an API call
    # Example: response = requests.get(f"/api/technicians/{technician_id}/tickets")
    # return response.json()
    return generate_technician_tickets(technician_id)  # Mock data for now

def my_tickets_page():
    """Page showing all tickets assigned to technician"""
    st.title("📋 My Assigned Tickets")
    
    tech_tickets = generate_technician_tickets()
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.multiselect("Status", STATUS_OPTIONS, default=STATUS_OPTIONS)
    with col2:
        priority_filter = st.multiselect("Priority", PRIORITY_OPTIONS, default=PRIORITY_OPTIONS)
    with col3:
        category_filter = st.multiselect("Category", TICKET_TYPES, default=TICKET_TYPES)
    with col4:
        sort_by = st.selectbox("Sort by", ["Created Date", "Priority", "Status", "Location"])
    
    # Filter tickets
    filtered_tickets = [
        t for t in tech_tickets 
        if t['status'] in status_filter 
        and t['priority'] in priority_filter 
        and t['category'] in category_filter
    ]
    
    # Sort tickets
    if sort_by == "Priority":
        priority_order = {"Critical": 0, "Desktop/User Down": 1, "High": 2, "Medium": 3, "Low": 4}
        filtered_tickets.sort(key=lambda x: priority_order.get(x['priority'], 5))
    elif sort_by == "Status":
        filtered_tickets.sort(key=lambda x: x['status'])
    elif sort_by == "Location":
        filtered_tickets.sort(key=lambda x: x['location'])
    else:  # Created Date
        filtered_tickets.sort(key=lambda x: x['created_at'], reverse=True)
    
    st.markdown(f"**Showing {len(filtered_tickets)} tickets**")
    
    # Display tickets
    for ticket in filtered_tickets:
        is_urgent = ticket['priority'] in ['Critical', 'Desktop/User Down']
        card_class = "urgent-ticket" if is_urgent else "tech-card"
        
        with st.expander(f"{PRIORITY_COLORS[ticket['priority']]} {ticket['id']} - {ticket['title']}", expanded=False):
            # Ticket header
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"**📍 Location:** {ticket['location']}")
                st.markdown(f"**👤 Requester:** {ticket['requester_name']}")
                st.markdown(f"**📞 Phone:** {ticket['requester_phone']}")
                st.markdown(f"**✉️ Email:** {ticket['requester_email']}")
            with col2:
                st.markdown(f"**🏷️ Category:** {ticket['category']}")
                st.markdown(f"**⚡ Priority:** {ticket['priority']}")
                st.markdown(f"**📊 Status:** {ticket['status']}")
                st.markdown(f"**⏱️ Estimated:** {ticket['estimated_hours']}h")
            with col3:
                st.markdown(f"**📅 Created:** {format_time_elapsed(ticket['created_at'])}")
                st.markdown(f"**🔄 Assigned:** {format_time_elapsed(ticket['assigned_at'])}")
                if ticket['actual_hours']:
                    st.markdown(f"**⏰ Actual:** {ticket['actual_hours']}h")
                if ticket['parts_needed']:
                    st.markdown(f"**🔧 Parts:** {ticket['parts_needed']}")
            
            # Description
            st.markdown("**📝 Description:**")
            st.markdown(ticket['description'])
            
            # Work notes
            if ticket['work_notes']:
                st.markdown("**📋 Work Notes:**")
                for note in ticket['work_notes']:
                    note_time = datetime.fromisoformat(note['timestamp']).strftime("%Y-%m-%d %H:%M")
                    st.markdown(f"• *{note_time}*: {note['note']}")
            
            # Action buttons
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if ticket['status'] == 'Assigned':
                    if st.button("▶️ Start Work", key=f"start_{ticket['id']}"):
                        st.success("Status updated to 'In Progress'")
                elif ticket['status'] == 'In Progress':
                    if st.button("✅ Mark Resolved", key=f"resolve_{ticket['id']}"):
                        st.success("Status updated to 'Resolved'")
            
            with col2:
                if st.button("📝 Add Note", key=f"note_{ticket['id']}"):
                    st.session_state[f"show_note_{ticket['id']}"] = True
            
            with col3:
                if st.button("📞 Call Customer", key=f"call_{ticket['id']}"):
                    st.info(f"Calling {ticket['requester_phone']}...")
            
            with col4:
                new_status = st.selectbox(
                    "Update Status:",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(ticket['status']),
                    key=f"status_update_{ticket['id']}"
                )
            
            # Add note modal (simplified)
            if st.session_state.get(f"show_note_{ticket['id']}", False):
                with st.form(f"note_form_{ticket['id']}"):
                    note_text = st.text_area("Work Note:", height=100)
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Add Note"):
                            st.success("Work note added successfully!")
                            st.session_state[f"show_note_{ticket['id']}"] = False
                    with col2:
                        if st.form_submit_button("Cancel"):
                            st.session_state[f"show_note_{ticket['id']}"] = False

def urgent_tickets_page():
    """Page showing only urgent/critical tickets"""
    st.title("🚨 Urgent Tickets")
    
    tech_tickets = generate_technician_tickets()
    urgent_tickets = [t for t in tech_tickets if t['priority'] in ['Critical', 'Desktop/User Down']]
    
    if not urgent_tickets:
        st.success("🎉 No urgent tickets at the moment!")
        return
    
    st.warning(f"⚠️ {len(urgent_tickets)} urgent tickets require immediate attention!")
    
    # Sort by creation time (newest first)
    urgent_tickets.sort(key=lambda x: x['created_at'], reverse=True)
    
    for i, ticket in enumerate(urgent_tickets):
        with st.container():
            st.markdown(f"""
            <div class="tech-card urgent-ticket">
            <h4>🔥 URGENT #{i+1}: {ticket['id']} - {ticket['title']}</h4>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"**📍 Location:** {ticket['location']}")
                st.markdown(f"**👤 Requester:** {ticket['requester_name']}")
                st.markdown(f"**📞 Phone:** {ticket['requester_phone']}")
                st.markdown(f"**📝 Issue:** {ticket['description']}")
            
            with col2:
                st.markdown(f"**⚡ Priority:** {PRIORITY_COLORS[ticket['priority']]} {ticket['priority']}")
                st.markdown(f"**📊 Status:** {ticket['status']}")
                st.markdown(f"**🏷️ Category:** {ticket['category']}")
                st.markdown(f"**⏱️ Estimated:** {ticket['estimated_hours']}h")
            
            with col3:
                st.markdown(f"**📅 Created:** {format_time_elapsed(ticket['created_at'])}")
                st.markdown(f"**🔄 Assigned:** {format_time_elapsed(ticket['assigned_at'])}")
                
                if ticket['status'] == 'Assigned':
                    if st.button(f"🚀 Start Immediately", key=f"urgent_start_{ticket['id']}"):
                        st.success("Started working on urgent ticket!")
                elif ticket['status'] == 'In Progress':
                    if st.button(f"✅ Mark Resolved", key=f"urgent_resolve_{ticket['id']}"):
                        st.success("Urgent ticket resolved!")
            
            st.markdown("---")

def analytics_page():
    """Work analytics and performance page"""
    st.title("📊 Work Analytics & Performance")
    
    tech_tickets = generate_technician_tickets(count=50)
    
    # Time period selector
    col1, col2 = st.columns([1, 3])
    with col1:
        time_period = st.selectbox("Time Period", ["Last 7 days", "Last 30 days", "Last 3 months"])
    
    # Calculate analytics
    total_tickets = len(tech_tickets)
    resolved_tickets = len([t for t in tech_tickets if t['status'] == 'Resolved'])
    avg_resolution_time = sum([t['actual_hours'] for t in tech_tickets if t['actual_hours']]) / max(resolved_tickets, 1)
    
    # Performance metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tickets", total_tickets)
    col2.metric("Resolved", resolved_tickets)
    col3.metric("Resolution Rate", f"{(resolved_tickets/total_tickets)*100:.1f}%")
    col4.metric("Avg Resolution Time", f"{avg_resolution_time:.1f}h")
    
    # Charts
    st.subheader("📈 Performance Charts")
    
    # Get theme for charts
    chart_theme = get_chart_theme()
    
    # Tickets by status
    status_counts = Counter(t['status'] for t in tech_tickets)
    col1, col2 = st.columns(2)
    
    with col1:
        fig_status = px.pie(
            values=list(status_counts.values()),
            names=list(status_counts.keys()),
            title="Tickets by Status"
        )
        fig_status.update_layout(**chart_theme)
        st.plotly_chart(fig_status, use_container_width=True)
    
    with col2:
        # Tickets by priority
        priority_counts = Counter(t['priority'] for t in tech_tickets)
        fig_priority = px.bar(
            x=list(priority_counts.keys()),
            y=list(priority_counts.values()),
            title="Tickets by Priority"
        )
        fig_priority.update_layout(**chart_theme)
        st.plotly_chart(fig_priority, use_container_width=True)
    
    # Performance trends (mock data)
    st.subheader("📈 Performance Trends")
    dates = [datetime.now().date() - timedelta(days=i) for i in range(7, 0, -1)]
    tickets_per_day = [random.randint(2, 8) for _ in dates]
    resolved_per_day = [random.randint(1, 6) for _ in dates]
    
    trend_df = pd.DataFrame({
        'Date': dates,
        'Assigned': tickets_per_day,
        'Resolved': resolved_per_day
    })
    
    fig_trend = px.line(
        trend_df, 
        x='Date', 
        y=['Assigned', 'Resolved'],
        title="Daily Ticket Trends"
    )
    fig_trend.update_layout(**chart_theme)
    st.plotly_chart(fig_trend, use_container_width=True)

def main():
    """Main application entry point for technician dashboard."""
    st.set_page_config(
        page_title=PAGE_TITLE,
        layout=LAYOUT,
        page_icon=PAGE_ICON,
        initial_sidebar_state="expanded"
    )

    # Initialize session state
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"
    if "tech_name" not in st.session_state:
        st.session_state.tech_name = "John Smith"
    if "tech_id" not in st.session_state:
        st.session_state.tech_id = "TECH-001"
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"

    # Apply custom CSS (must be called after theme is set)
    apply_custom_css()

    # Create sidebar
    create_technician_sidebar()

    # Route to appropriate page
    if st.session_state.page == "dashboard":
        dashboard_page()
    elif st.session_state.page == "my_tickets":
        my_tickets_page()
    elif st.session_state.page == "urgent_tickets":
        urgent_tickets_page()
    elif st.session_state.page == "analytics":
        analytics_page()

if __name__ == "__main__":
    main()
