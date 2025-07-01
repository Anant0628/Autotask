"""
Refactored TeamLogic-AutoTask Application
Main entry point that orchestrates all modular components.
"""

import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
from collections import Counter
from typing import List, Dict
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime, parseaddr
import pytz
import re
import dateparser
from dateparser.search import search_dates

# Import modular components
from config import *
from intake_agent import IntakeClassificationAgent
from data_manager import DataManager
from ui_components import apply_custom_css, create_sidebar, format_time_elapsed, format_date_display, get_duration_icon

# Email integration config
EMAIL_ACCOUNT = 'rohankul2017@gmail.com'  # Set to your support email
EMAIL_PASSWORD = os.getenv('SUPPORT_EMAIL_PASSWORD')
IMAP_SERVER = 'imap.gmail.com'
FOLDER = 'inbox'
DEFAULT_TZ = 'Asia/Kolkata'
MAX_EMAILS = 50
MINUTES_BACK = 180
DEFAULT_DUE_OFFSET_HOURS = 48
IST = pytz.timezone(DEFAULT_TZ)
now = datetime.now(IST)
cutoff_time = now - timedelta(minutes=MINUTES_BACK)

@st.cache_resource
def get_agent(account, user, password, warehouse, database, schema, role, passcode, data_ref):
    """Initializes and returns the IntakeClassificationAgent."""
    try:
        agent = IntakeClassificationAgent(
            sf_account=account,
            sf_user=user,
            sf_password=password,
            sf_warehouse=warehouse,
            sf_database=database,
            sf_schema=schema,
            sf_role=role,
            sf_passcode=passcode,
            data_ref_file=data_ref
        )
        if not agent.conn:
            st.error("Failed to establish Snowflake connection. Double-check your credentials and network access.")
            return None
        return agent
    except Exception as e:
        st.error(f"An error occurred during agent initialization: {e}")
        st.exception(e)
        return None

def fetch_and_process_emails(agent):
    """Fetch unseen emails, create tickets, and return a summary."""
    processed = []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        mail.select(FOLDER)
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()
        for email_id in reversed(email_ids[-MAX_EMAILS:]):
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    email_date = msg.get("Date")
                    received_dt = parsedate_to_datetime(email_date).astimezone(IST)
                    if received_dt < cutoff_time:
                        continue
                    subject, encoding = decode_header(msg.get("Subject"))[0]
                    subject = subject.decode(encoding or "utf-8") if isinstance(subject, bytes) else subject
                    from_ = msg.get("From")
                    name, addr = parseaddr(from_)
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")
                    full_text = f"{subject}\n{body}"
                    # --- NLP due date extraction ---
                    def extract_due_date_nlp(text, received_dt):
                        text = text.lower()
                        if "tomorrow" in text:
                            result = received_dt + timedelta(days=1)
                            return result.strftime('%Y-%m-%d')
                        match_next_day = re.search(r'next\\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', text)
                        if match_next_day:
                            weekday_str = match_next_day.group(1)
                            weekday_target = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].index(weekday_str)
                            days_ahead = (weekday_target - received_dt.weekday() + 7) % 7
                            days_ahead = 7 if days_ahead == 0 else days_ahead
                            result = received_dt + timedelta(days=days_ahead)
                            return result.strftime('%Y-%m-%d')
                        match_working = re.search(r'(?:in|within)\\s+(\\d{1,2})\\s+working\\s+days?', text)
                        if match_working:
                            days = int(match_working.group(1))
                            added = 0
                            current = received_dt
                            while added < days:
                                current += timedelta(days=1)
                                if current.weekday() < 5:
                                    added += 1
                            return current.strftime('%Y-%m-%d')
                        parsed_results = search_dates(
                            text,
                            settings={
                                'RELATIVE_BASE': received_dt,
                                'PREFER_DATES_FROM': 'future',
                                'TIMEZONE': DEFAULT_TZ,
                                'RETURN_AS_TIMEZONE_AWARE': True
                            }
                        )
                        if parsed_results:
                            for phrase, dt in parsed_results:
                                if dt > received_dt:
                                    return dt.strftime('%Y-%m-%d')
                        match_window = re.search(r'after\\s+(\\d{1,2})[-/](\\d{1,2})[-/](\\d{4})\\s+and\\s+before\\s+(\\d{1,2})[-/](\\d{1,2})[-/](\\d{4})', text)
                        if match_window:
                            d1, m1, y1, d2, m2, y2 = map(int, match_window.groups())
                            try:
                                start = datetime(y1, m1, d1, tzinfo=received_dt.tzinfo)
                                end = datetime(y2, m2, d2, tzinfo=received_dt.tzinfo)
                                mid = start + (end - start) / 2
                                return mid.strftime('%Y-%m-%d')
                            except:
                                pass
                        fallback = received_dt + timedelta(hours=DEFAULT_DUE_OFFSET_HOURS)
                        return fallback.strftime('%Y-%m-%d')
                    due_date = extract_due_date_nlp(full_text, received_dt)
                    result = agent.process_new_ticket(
                        ticket_name=name or addr,
                        ticket_description=body.strip(),
                        ticket_title=subject.strip(),
                        due_date=due_date,
                        priority_initial='Medium'
                    )
                    processed.append({
                        'from': name or addr,
                        'subject': subject.strip(),
                        'due_date': due_date
                    })
                    mail.store(email_id, '+FLAGS', '\\Seen')
        mail.logout()
    except Exception as e:
        return f"Error: {e}"
    return processed

def main_page(agent, data_manager):
    """Main page with ticket submission form and quick stats using cached knowledgebase."""
    st.title(PAGE_TITLE)
    st.markdown("""
    <div class="card" style="background-color: var(--accent);">
    Submit a new support ticket and let our AI agent automatically classify it for faster resolution.
    </div>
    """, unsafe_allow_html=True)

    # --- Quick Stats using cached knowledgebase ---
    kb_data = load_kb_data()
    total_tickets = len(kb_data)
    st.markdown(f"**Total Tickets:** {total_tickets}")
    # Optionally, show a preview of the most recent ticket
    if kb_data:
        last_ticket = kb_data[-1]['new_ticket']
        st.markdown(f"**Most Recent Ticket:** {last_ticket.get('title', 'N/A')} ({last_ticket.get('date', 'N/A')} {last_ticket.get('time', 'N/A')})")

    with st.container():
        st.subheader("📝 New Ticket Submission")
        with st.form("new_ticket_form", clear_on_submit=True):
            col1, col2 = st.columns([1, 1], gap="large")
            with col1:
                st.markdown("### Basic Information")
                ticket_name = st.text_input("Your Name*", placeholder="e.g., Jane Doe")
                ticket_title = st.text_input("Ticket Title*", placeholder="e.g., Network drive inaccessible")
            with col2:
                today = datetime.now().date()
                due_date = st.date_input("Due Date", value=today + timedelta(days=7))
                initial_priority = st.selectbox("Initial Priority*", options=PRIORITY_OPTIONS)

            ticket_description = st.text_area(
                "Description*",
                placeholder="Please describe your issue in detail...",
                height=150
            )

            submitted = st.form_submit_button("Submit Ticket", type="primary")

            if submitted:
                required_fields = {
                    "Name": ticket_name,
                    "Title": ticket_title,
                    "Description": ticket_description,
                    "Priority": initial_priority
                }
                missing_fields = [field for field, value in required_fields.items() if not value]

                if missing_fields:
                    st.warning(f"⚠️ Please fill in all required fields: {', '.join(missing_fields)}")
                else:
                    # Check if agent is properly initialized
                    if agent is None:
                        st.error("❌ Database connection failed. Cannot generate proper resolutions without historical data.")
                        st.info("🔑 **Expired MFA Code** - Get a fresh 6-digit code from your authenticator app")
                        st.info("🌐 **Network Issues** - Check your internet connection")
                        st.info("🔐 **Invalid Credentials** - Verify username/password")
                        st.warning("⚠️ **Resolution generation requires database access to historical tickets.**")
                        st.info("💡 Please fix the connection issue and try again for proper resolution generation.")
                        return
                    else:
                        with st.spinner("🔍 Analyzing your ticket..."):
                            try:
                                processed_ticket = agent.process_new_ticket(
                                    ticket_name=ticket_name,
                                    ticket_description=ticket_description,
                                    ticket_title=ticket_title,
                                    due_date=due_date.strftime("%Y-%m-%d"),
                                    priority_initial=initial_priority
                                )

                                if processed_ticket:
                                    st.success("✅ Ticket processed, classified, and resolution generated successfully!")
                                    classified_data = processed_ticket.get('classified_data', {})
                                    extracted_metadata = processed_ticket.get('extracted_metadata', {})
                                    resolution_note = processed_ticket.get('resolution_note', 'No resolution note generated')

                                    # Display ticket summary
                                    with st.expander("📋 Classified Ticket Summary", expanded=True):
                                        cols = st.columns(3)
                                        cols[0].metric("Issue Type", classified_data.get('ISSUETYPE', {}).get('Label', 'N/A'))
                                        cols[1].metric("Type", classified_data.get('TICKETTYPE', {}).get('Label', 'N/A'))
                                        cols[2].metric("Priority", classified_data.get('PRIORITY', {}).get('Label', 'N/A'))

                                        st.markdown(f"""
                                        <div class="card">
                                        <table style="width:100%">
                                            <tr><td><strong>Ticket Title</strong></td><td>{processed_ticket.get('title', 'N/A')}</td></tr>
                                            <tr><td><strong>Main Issue</strong></td><td>{extracted_metadata.get('main_issue', 'N/A')}</td></tr>
                                            <tr><td><strong>Affected System</strong></td><td>{extracted_metadata.get('affected_system', 'N/A')}</td></tr>
                                            <tr><td><strong>Urgency Level</strong></td><td>{extracted_metadata.get('urgency_level', 'N/A')}</td></tr>
                                            <tr><td><strong>Error Messages</strong></td><td>{extracted_metadata.get('error_messages', 'N/A')}</td></tr>
                                        </table>
                                        </div>
                                        """, unsafe_allow_html=True)

                                    # Display full classification details
                                    with st.expander("📊 Full Classification Details", expanded=False):
                                        st.markdown("""
                                        <div class="card">
                                        <h4>Ticket Classification Details</h4>
                                        """, unsafe_allow_html=True)

                                        # Tabular display for classification fields
                                        class_fields = [
                                            ("ISSUETYPE", "Issue Type"),
                                            ("SUBISSUETYPE", "Sub-Issue Type"),
                                            ("TICKETCATEGORY", "Ticket Category"),
                                            ("TICKETTYPE", "Ticket Type"),
                                            ("STATUS", "Status"),
                                            ("PRIORITY", "Priority")
                                        ]
                                        table_data = []
                                        for field, label in class_fields:
                                            val = classified_data.get(field, {})
                                            table_data.append({
                                                "Field": label,
                                                "Label": val.get('Label', 'N/A')
                                            })
                                        df = pd.DataFrame(table_data)
                                        st.table(df)
                                        st.markdown(f"**Ticket Title:** {processed_ticket.get('title', 'N/A')}")
                                        st.markdown(f"**Description:** {processed_ticket.get('description', 'N/A')}")
                                        st.markdown("</div>", unsafe_allow_html=True)

                                    # Display Resolution Note in a prominent section
                                    with st.expander("🔧 Generated Resolution Note", expanded=True):
                                        # Process the resolution note for HTML display
                                        processed_note = resolution_note.replace('**', '<strong>').replace('</strong>', '</strong>').replace('\n', '<br>')
                                        st.markdown(f"""
                                        <div class="card" style="background-color: #1e4620; border-left: 4px solid #28a745;">
                                        <h4 style="color: #d4edda; margin-bottom: 15px;">💡 Recommended Resolution</h4>
                                        <div style="color: #d4edda; line-height: 1.6;">
                                        {processed_note}
                                        </div>
                                        </div>
                                        """, unsafe_allow_html=True)

                                    # Next steps
                                    st.markdown(f"""
                                    <div class="card" style="background-color: var(--accent);">
                                    <h4>Next Steps</h4>
                                    <ol>
                                        <li>Your ticket has been assigned to the <b>{classified_data.get('ISSUETYPE', {}).get('Label', 'N/A')}</b> team</li>
                                        <li>A resolution note has been automatically generated based on similar historical tickets</li>
                                        <li>You'll receive a confirmation email shortly with the resolution steps</li>
                                        <li>A support specialist will contact you within 2 business hours</li>
                                        <li>Priority level: <b>{classified_data.get('PRIORITY', {}).get('Label', 'N/A')}</b> - Response time varies accordingly</li>
                                        <li>Try the suggested resolution steps above before escalating</li>
                                    </ol>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.error("Failed to process the ticket. Please check the logs for details.")
                            except Exception as e:
                                st.error(f"An unexpected error occurred: {e}")

    # About section
    st.markdown("---")
    st.markdown("""
    <div class="card">
    <h3>About This System</h3>
    <p>This AI-powered intake, classification, and resolution system automatically:</p>
    <ul>
        <li>Extracts metadata from new tickets using AI</li>
        <li>Classifies tickets into predefined categories</li>
        <li>Generates resolution notes based on similar historical tickets</li>
        <li>Routes tickets to the appropriate support teams</li>
        <li>Provides confidence-based resolution suggestions</li>
        <li>Stores all data for continuous improvement</li>
    </ul>
    <p><strong>Workflow:</strong> Intake → Classification → Resolution Generation</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Email-to-ticket integration button ---
    with st.expander("📧 Fetch and Process Support Emails", expanded=False):
        if st.button("Fetch New Support Emails and Create Tickets", type="primary"):
            with st.spinner("Checking support inbox and creating tickets..."):
                results = fetch_and_process_emails(agent)
                if isinstance(results, str):
                    st.error(results)
                elif results:
                    st.success(f"Processed {len(results)} new email(s) into tickets.")
                    for r in results:
                        st.write(f"- {r['from']}: {r['subject']} (Due: {r['due_date']})")
                else:
                    st.info("No new support emails found.")

@st.cache_data
def load_kb_data():
    if os.path.exists(KNOWLEDGEBASE_FILE):
        with open(KNOWLEDGEBASE_FILE, 'r') as f:
            return json.load(f)
    return []

def filter_tickets_by_duration(kb_data, duration, now):
    from datetime import timedelta
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
        filtered = []
        for entry in kb_data:
            t = entry['new_ticket']
            try:
                created_time = datetime.fromisoformat(t['date'] + 'T' + t['time'])
                if start_time <= created_time <= end_time:
                    filtered.append(t)
            except:
                continue
        return sorted(filtered, key=lambda x: x["date"] + x["time"], reverse=True)
    elif duration == "Last 3 days":
        cutoff_time = now - timedelta(days=3)
    elif duration == "Last week":
        cutoff_time = now - timedelta(weeks=1)
    elif duration == "Last month":
        cutoff_time = now - timedelta(days=30)
    elif duration == "All tickets":
        return [entry['new_ticket'] for entry in sorted(kb_data, key=lambda x: x['new_ticket']["date"] + x['new_ticket']["time"], reverse=True)]
    else:
        cutoff_time = now - timedelta(hours=24)
    filtered = []
    for entry in kb_data:
        t = entry['new_ticket']
        try:
            created_time = datetime.fromisoformat(t['date'] + 'T' + t['time'])
            if created_time >= cutoff_time:
                filtered.append(t)
        except:
            continue
    return sorted(filtered, key=lambda x: x["date"] + x["time"], reverse=True)

def filter_tickets_by_date_range(kb_data, start_date, end_date):
    from datetime import datetime
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    filtered = []
    for entry in kb_data:
        t = entry['new_ticket']
        try:
            created_time = datetime.fromisoformat(t['date'] + 'T' + t['time'])
            if start_datetime <= created_time <= end_datetime:
                filtered.append(t)
        except:
            continue
    return sorted(filtered, key=lambda x: x["date"] + x["time"], reverse=True)

def filter_tickets_by_specific_date(kb_data, selected_date):
    from datetime import datetime
    filtered = []
    for entry in kb_data:
        t = entry['new_ticket']
        try:
            created_time = datetime.fromisoformat(t['date'] + 'T' + t['time'])
            if created_time.date() == selected_date:
                filtered.append(t)
        except:
            continue
    return sorted(filtered, key=lambda x: x["date"] + x["time"], reverse=True)

def recent_tickets_page(data_manager):
    """Dynamic recent tickets page with multiple filtering options (now optimized)"""
    kb_data = load_kb_data()
    now = datetime.now()
    with st.container():
        if st.button("← Back to Home", key="rt_back"):
            st.session_state.page = "main"
            st.rerun()
        st.title("🕑 Recent Raised Tickets")
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
                    index=0,
                    key="duration_selector"
                )
            with col2:
                if st.button("Apply Duration Filter", key="apply_duration"):
                    tickets_to_display = filter_tickets_by_duration(kb_data, selected_duration, now)
                    filter_description = f"{get_duration_icon(selected_duration)} {selected_duration}"
                    st.session_state.active_filter = "duration"
                    st.session_state.filter_description = filter_description
                    st.session_state.tickets_to_display = tickets_to_display
            with col3:
                preview_tickets = filter_tickets_by_duration(kb_data, selected_duration, now)
                st.metric("Tickets Found", len(preview_tickets))
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
                        tickets_to_display = filter_tickets_by_date_range(kb_data, start_date, end_date)
                        filter_description = f"📅 {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                        st.session_state.active_filter = "date_range"
                        st.session_state.filter_description = filter_description
                        st.session_state.tickets_to_display = tickets_to_display
                    else:
                        st.error("Start date must be before or equal to end date!")
            with col4:
                preview_tickets = filter_tickets_by_date_range(kb_data, st.session_state.get('start_date', datetime.now().date()), st.session_state.get('end_date', datetime.now().date()))
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
                    tickets_to_display = filter_tickets_by_specific_date(kb_data, specific_date)
                    filter_description = f"📆 {specific_date.strftime('%Y-%m-%d')}"
                    st.session_state.active_filter = "specific_date"
                    st.session_state.filter_description = filter_description
                    st.session_state.tickets_to_display = tickets_to_display
            with col3:
                preview_tickets = filter_tickets_by_specific_date(kb_data, specific_date)
                st.metric("Tickets Found", len(preview_tickets))
        if 'tickets_to_display' in st.session_state and 'filter_description' in st.session_state:
            tickets_to_display = st.session_state.tickets_to_display
            filter_description = st.session_state.filter_description
        else:
            tickets_to_display = filter_tickets_by_duration(kb_data, "Last hour", now)
            filter_description = "🚨 Last hour"

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
        </div>
        """, unsafe_allow_html=True)

        if tickets_to_display:
            # Add special styling for urgent tickets
            if "Last hour" in filter_description:
                st.markdown("""
                <div style="
                    background-color: #2d2d2d;
                    border-left: 6px solid #ffcc00;
                    color: #ffe066;
                    border-radius: 8px;
                    padding: 14px 18px;
                    margin-bottom: 18px;
                    font-size: 1.1em;
                    font-weight: 500;
                    display: flex;
                    align-items: center;
                ">
                    <span style="font-size:1.5em; margin-right: 12px;">⚠️</span>
                    <span>
                        <strong>Urgent Attention Required:</strong>
                        These tickets were raised in the last hour and may need immediate response.
                    </span>
                </div>
                """, unsafe_allow_html=True)

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
                # Construct created_at from date and time
                created_at = f"{ticket.get('date', '')}T{ticket.get('time', '')}"
                time_elapsed = format_time_elapsed(created_at)
                date_created = format_date_display(created_at)
                # Construct id if missing
                ticket_id = ticket.get('id') or (ticket.get('title', '') + ticket.get('date', '') + ticket.get('time', ''))

                # Special highlighting for critical/urgent tickets
                is_urgent = (ticket.get('priority') in ['Critical', 'Desktop/User Down'] or
                           "Last hour" in filter_description)

                expand_key = f"ticket_{ticket_id}_{i}"

                with st.expander(
                    f"{'🔥' if is_urgent else '📋'} {ticket_id} - {ticket.get('title', '')} ({time_elapsed})",
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
                    cols[1].markdown(f"**Priority:** {ticket.get('priority', 'Medium')}")
                    cols[2].markdown(f"**Status:** {ticket.get('status', 'Open')}")
                    cols[3].markdown(f"**Requester:** {ticket.get('requester_name', '')}")

                    st.markdown(f"**Email:** {ticket.get('requester_email', '')}")
                    if ticket.get('requester_phone'):
                        st.markdown(f"**Phone:** {ticket.get('requester_phone', '')}")
                    st.markdown(f"**Company ID:** {ticket.get('company_id', '')}")

                    # Description with expand/collapse
                    if len(ticket.get('description', '')) > 200:
                        if st.button(f"Show Full Description", key=f"desc_{ticket_id}_{i}"):
                            st.markdown(f"**Description:** {ticket.get('description', '')}")
                        else:
                            st.markdown(f"**Description:** {ticket.get('description', '')[:200]}...")
                    else:
                        st.markdown(f"**Description:** {ticket.get('description', '')}")

                    # Technical details if available
                    if ticket.get('device_model') or ticket.get('os_version') or ticket.get('error_message'):
                        st.markdown("**Technical Details:**")
                        if ticket.get('device_model'):
                            st.markdown(f"• Device: {ticket.get('device_model', '')}")
                        if ticket.get('os_version'):
                            st.markdown(f"• OS: {ticket.get('os_version', '')}")
                        if ticket.get('error_message'):
                            st.markdown(f"• Error: {ticket.get('error_message', '')}")

                    # Status update section
                    st.markdown("---")
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        new_status = st.selectbox(
                            "Update Status:",
                            ["Open", "In Progress", "Resolved", "Closed"],
                            index=["Open", "In Progress", "Resolved", "Closed"].index(ticket.get('status', 'Open')) if ticket.get('status', 'Open') in ["Open", "In Progress", "Resolved", "Closed"] else 0,
                            key=f"status_{ticket_id}_{i}"
                        )
                    with col2:
                        if st.button("Update Status", key=f"update_{ticket_id}_{i}"):
                            data_manager.update_ticket_status(ticket_id, new_status)
                            st.success(f"Status updated to {new_status}")
                            st.rerun()
                    with col3:
                        # Priority indicator
                        priority_colors = {
                            "Low": "🟢",
                            "Medium": "🟡",
                            "High": "🟠",
                            "Critical": "🔴",
                            "Desktop/User Down": "🚨"
                        }
                        st.markdown(f"**Priority:** {priority_colors.get(ticket.get('priority', 'Medium'), '⚪')} {ticket.get('priority', 'Medium')}")

            # Show pagination info
            if total_pages > 1:
                st.info(f"Showing page {page_number} of {total_pages} ({len(tickets_to_display)} total tickets)")

        else:
            st.info(f"No tickets found for the selected filter: {filter_description}")

        # Summary statistics for filtered tickets
        if tickets_to_display:
            st.markdown("---")
            st.markdown("### 📊 Summary Statistics")

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
                st.markdown("**📂 Categories:**")
                for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / len(tickets_to_display)) * 100
                    st.write(f"• {category}: {count} ({percentage:.1f}%)")

            with col2:
                st.markdown("**⚡ Priorities:**")
                priority_order = ["Critical", "Desktop/User Down", "High", "Medium", "Low"]
                for priority in priority_order:
                    if priority in priority_counts:
                        count = priority_counts[priority]
                        percentage = (count / len(tickets_to_display)) * 100
                        icon = PRIORITY_COLORS.get(priority, "⚪")
                        st.write(f"• {icon} {priority}: {count} ({percentage:.1f}%)")

            # Show urgent tickets alert if any
            urgent_count = priority_counts.get('Critical', 0) + priority_counts.get('Desktop/User Down', 0)
            if urgent_count > 0:
                st.warning(f"⚠️ {urgent_count} urgent ticket(s) require immediate attention!")

def dashboard_page(data_manager):
    """Dashboard page with analytics and charts (now uses caching)"""
    st.title("📊 Dashboard")
    kb_data = load_kb_data()
    if not kb_data:
        st.info("No tickets found in the knowledge base.")
        return
    # --- FILTERS ---
    st.markdown("### Filters")
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        date_min = None
        date_max = None
        dates = []
        for entry in kb_data:
            t = entry['new_ticket']
            try:
                dt = datetime.fromisoformat(t.get('date', '') + 'T' + t.get('time', ''))
                dates.append(dt)
            except:
                continue
        if dates:
            date_min = min(dates).date()
            date_max = max(dates).date()
        else:
            date_min = date_max = datetime.now().date()
        date_range = st.date_input("Date Range", value=(date_min, date_max), min_value=date_min, max_value=date_max)
    with col2:
        all_statuses = sorted(set(entry['new_ticket'].get('classified_data', {}).get('STATUS', {}).get('Label', 'N/A') for entry in kb_data if 'new_ticket' in entry))
        status_filter = st.multiselect("Status", options=["New", "In Progress", "Resolved", "Closed"] + [s for s in all_statuses if s not in ["New", "In Progress", "Resolved", "Closed"]], default=["New", "In Progress", "Resolved", "Closed"])
    with col3:
        all_priorities = sorted(set(entry['new_ticket'].get('classified_data', {}).get('PRIORITY', {}).get('Label', 'N/A') for entry in kb_data if 'new_ticket' in entry))
        priority_filter = st.multiselect("Priority", options=all_priorities, default=all_priorities)
    # --- FILTER DATA ---
    filtered = []
    for entry in kb_data:
        t = entry['new_ticket']
        c = t.get('classified_data', {})
        try:
            dt = datetime.fromisoformat(t.get('date', '') + 'T' + t.get('time', ''))
        except:
            continue
        status = c.get('STATUS', {}).get('Label', 'N/A')
        priority = c.get('PRIORITY', {}).get('Label', 'N/A')
        if (date_range[0] <= dt.date() <= date_range[1]) and (status in status_filter) and (priority in priority_filter):
            filtered.append(entry)
    total_tickets = len(filtered)
    open_tickets = sum(1 for entry in filtered if entry['new_ticket'].get('classified_data', {}).get('STATUS', {}).get('Label', 'N/A').lower() == 'open')
    resolved_tickets = sum(1 for entry in filtered if entry['new_ticket'].get('classified_data', {}).get('STATUS', {}).get('Label', 'N/A').lower() == 'resolved')
    last_24h = 0
    now = datetime.now()
    cutoff_24h = now - timedelta(hours=24)
    for entry in filtered:
        try:
            created_time = datetime.fromisoformat(entry['new_ticket'].get('date', '') + 'T' + entry['new_ticket'].get('time', ''))
            if created_time >= cutoff_24h:
                last_24h += 1
        except:
            continue
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tickets", total_tickets)
    col2.metric("Last 24 Hours", last_24h)
    col3.metric("Open Tickets", open_tickets)
    col4.metric("Resolved", resolved_tickets)
    # --- Prepare data for grouped bar chart ---
    status_counts = Counter()
    priority_counts = Counter()
    category_counts = Counter()
    for entry in filtered:
        classified = entry['new_ticket'].get('classified_data', {})
        status = classified.get('STATUS', {}).get('Label', 'N/A')
        priority = classified.get('PRIORITY', {}).get('Label', 'N/A')
        category = classified.get('TICKETCATEGORY', {}).get('Label', 'N/A')
        status_counts[status] += 1
        priority_counts[priority] += 1
        category_counts[category] += 1
    # Ensure all main statuses are present in order
    status_order = ["New", "In Progress", "Resolved", "Closed"]
    for s in status_order:
        if s not in status_counts:
            status_counts[s] = 0
    # --- Plotly Bar Chart ---
    df_status = pd.DataFrame({"Status": list(status_counts.keys()), "Count": list(status_counts.values())})
    df_priority = pd.DataFrame({"Priority": list(priority_counts.keys()), "Count": list(priority_counts.values())})
    df_category = pd.DataFrame({"Category": list(category_counts.keys()), "Count": list(category_counts.values())})
    # Custom color maps
    status_colors = STATUS_COLORS
    priority_colors = CHART_PRIORITY_COLORS
    category_colors = {cat: px.colors.qualitative.Plotly[i % 10] for i, cat in enumerate(df_category['Category'])}
    # Plot
    st.subheader("Tickets by Status, Priority, and Category")
    fig = px.bar(df_status, x="Status", y="Count", color="Status", category_orders={"Status": status_order}, color_discrete_map=status_colors, barmode="group", title="Status")
    fig.add_bar(x=df_priority['Priority'], y=df_priority['Count'], name="Priority", marker_color=[priority_colors.get(p, '#888') for p in df_priority['Priority']])
    fig.add_bar(x=df_category['Category'], y=df_category['Count'], name="Category", marker_color=[category_colors.get(c, '#888') for c in df_category['Category']])
    fig.update_layout(
        plot_bgcolor="#181818",
        paper_bgcolor="#181818",
        font_color="#f8f9fa",
        legend=dict(bgcolor="#23272f", bordercolor="#444", borderwidth=1),
        xaxis=dict(title="", tickfont=dict(color="#f8f9fa")),
        yaxis=dict(title="", tickfont=dict(color="#f8f9fa")),
        barmode="group",
        bargap=0.18,
        bargroupgap=0.12
    )
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Recent Tickets")
    if filtered:
        recent_rows = []
        for entry in filtered[-10:][::-1]:
            ticket = entry['new_ticket']
            classified = ticket.get('classified_data', {})
            recent_rows.append({
                "Title": ticket.get('title', 'N/A'),
                "Category": classified.get('TICKETCATEGORY', {}).get('Label', 'N/A'),
                "Priority": classified.get('PRIORITY', {}).get('Label', 'N/A'),
                "Status": classified.get('STATUS', {}).get('Label', 'N/A'),
                "Date": ticket.get('date', 'N/A'),
                "Time": ticket.get('time', 'N/A'),
                "ID": ticket.get('title', 'N/A') + ticket.get('date', 'N/A') + ticket.get('time', 'N/A')
            })
        df_recent = pd.DataFrame(recent_rows)
        for entry in filtered[-10:][::-1]:
            ticket = entry['new_ticket']
            classified = ticket.get('classified_data', {})
            ticket_id = ticket.get('title', 'N/A') + ticket.get('date', 'N/A') + ticket.get('time', 'N/A')
            with st.expander(f"{ticket.get('title', 'N/A')} ({ticket.get('date', 'N/A')} {ticket.get('time', 'N/A')})", expanded=False):
                st.markdown(f"**Category:** {classified.get('TICKETCATEGORY', {}).get('Label', 'N/A')}")
                st.markdown(f"**Priority:** {classified.get('PRIORITY', {}).get('Label', 'N/A')}")
                st.markdown(f"**Status:** {classified.get('STATUS', {}).get('Label', 'N/A')}")
                st.markdown(f"**Requester:** {ticket.get('name', 'N/A')}")
                st.markdown(f"**Created At:** {ticket.get('date', 'N/A')} {ticket.get('time', 'N/A')}")
                st.markdown(f"**Description:** {ticket.get('description', 'N/A')}")
    else:
        st.info("No tickets found for the selected filters.")

def resolutions_page():
    """Page for technicians to view tickets and their resolutions."""
    st.title("📝 Ticket Resolutions")
    kb_data = load_kb_data()
    search_query = st.text_input("Search by title, description, or resolution:", "")
    # Filter tickets by search
    filtered = []
    for entry in kb_data:
        t = entry['new_ticket']
        res_note = t.get('resolution_note', '')
        if search_query.strip():
            q = search_query.lower()
            if (q in t.get('title', '').lower() or
                q in t.get('description', '').lower() or
                q in res_note.lower()):
                filtered.append(t)
        else:
            filtered.append(t)
    # Sort by most recent
    filtered = sorted(filtered, key=lambda x: x.get('date', '') + x.get('time', ''), reverse=True)
    st.markdown(f"Showing {len(filtered)} tickets.")
    for i, t in enumerate(filtered):
        with st.expander(f"{t.get('title', 'N/A')} ({t.get('date', 'N/A')} {t.get('time', 'N/A')})", expanded=False):
            st.markdown(f"**Status:** {t.get('classified_data', {}).get('STATUS', {}).get('Label', 'N/A')}")
            st.markdown(f"**Priority:** {t.get('classified_data', {}).get('PRIORITY', {}).get('Label', 'N/A')}")
            st.markdown(f"**Requester:** {t.get('name', 'N/A')}")
            st.markdown(f"**Due Date:** {t.get('due_date', 'N/A')}")
            st.markdown(f"**Description:** {t.get('description', 'N/A')}")
            st.markdown("---")
            st.markdown("**Resolution Note:**")
            st.code(t.get('resolution_note', 'No resolution note generated'), language=None)

# --- Update sidebar navigation ---
def create_sidebar(data_manager):
    with st.sidebar:
        st.markdown("## Navigation")
        nav_options = {
            "🏠 Home": "main",
            "🕒 Recent Tickets": "recent_tickets",
            "📊 Dashboard": "dashboard",
            "📝 Resolutions": "resolutions"
        }
        for option, page in nav_options.items():
            if st.button(option, key=f"nav_{page}", help=page, use_container_width=True):
                st.session_state.page = page
                st.rerun()
        current_page = st.session_state.get('page', 'main')
        st.markdown(f"""
        <div style="margin: 20px 0; padding: 10px; background-color: var(--accent); border-radius: 6px;">
        <small>Current page:</small><br>
        <strong>{current_page.replace('_', ' ').title()}</strong>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("### Quick Stats")
        try:
            if os.path.exists('Knowledgebase.json'):
                with open('Knowledgebase.json', 'r') as f:
                    kb_data = json.load(f)
                total_tickets = len(kb_data)
            else:
                total_tickets = 0
        except:
            total_tickets = 0
        st.metric("Total Tickets", total_tickets)
        st.markdown("---")
        st.markdown("""
        <div style="padding: 10px;">
        <h4>Need Help?</h4>
        <p>Contact IT Support:</p>
        <p>📞 9723100860<br>
        ✉️ inquire@64-squares.com</p>
        </div>
        """, unsafe_allow_html=True)

# --- Main App Logic ---
def main():
    """Main application entry point."""
    # Page configuration
    st.set_page_config(
        page_title=PAGE_TITLE,
        layout=LAYOUT,
        page_icon=PAGE_ICON,
        initial_sidebar_state="expanded"
    )

    # Apply custom CSS
    apply_custom_css()

    # Initialize data manager
    data_manager = DataManager(DATA_REF_FILE, KNOWLEDGEBASE_FILE)

    # Initialize agent
    agent = get_agent(SF_ACCOUNT, SF_USER, SF_PASSWORD, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE, SF_PASSCODE, DATA_REF_FILE)
    # Fetch emails and create tickets on app startup (optional, can comment out if not desired)
    fetch_and_process_emails(agent)

    # Initialize session state
    if "page" not in st.session_state:
        st.session_state.page = "main"

    # Create sidebar
    create_sidebar(data_manager)

    # Route to appropriate page
    if st.session_state.page == "main":
        main_page(agent, data_manager)
    elif st.session_state.page == "recent_tickets":
        recent_tickets_page(data_manager)
    elif st.session_state.page == "dashboard":
        dashboard_page(data_manager)
    elif st.session_state.page == "resolutions":
        resolutions_page()


if __name__ == "__main__":
    main()