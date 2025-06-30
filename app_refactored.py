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

# Import modular components
from config import *
from intake_agent import IntakeClassificationAgent
from data_manager import DataManager
from ui_components import apply_custom_css, create_sidebar, format_time_elapsed, format_date_display, get_duration_icon


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


def main_page(agent, data_manager):
    """Main page with ticket submission form."""
    st.title(PAGE_TITLE)
    st.markdown("""
    <div class="card" style="background-color: var(--accent);">
    Submit a new support ticket and let our AI agent automatically classify it for faster resolution.
    </div>
    """, unsafe_allow_html=True)

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


def recent_tickets_page(data_manager):
    """Dynamic recent tickets page with multiple filtering options"""
    with st.container():
        if st.button("← Back to Home", key="rt_back"):
            st.session_state.page = "main"
            st.rerun()

        st.title("🕑 Recent Raised Tickets")

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
                    tickets_to_display = data_manager.get_tickets_by_duration(selected_duration)
                    filter_description = f"{get_duration_icon(selected_duration)} {selected_duration}"
                    st.session_state.active_filter = "duration"
                    st.session_state.filter_description = filter_description
                    st.session_state.tickets_to_display = tickets_to_display

            with col3:
                st.metric("Tickets Found", len(data_manager.get_tickets_by_duration(selected_duration)))

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
                        tickets_to_display = data_manager.get_tickets_by_date_range(start_date, end_date)
                        filter_description = f"📅 {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                        st.session_state.active_filter = "date_range"
                        st.session_state.filter_description = filter_description
                        st.session_state.tickets_to_display = tickets_to_display
                    else:
                        st.error("Start date must be before or equal to end date!")

            with col4:
                if 'start_date' in st.session_state and 'end_date' in st.session_state:
                    preview_tickets = data_manager.get_tickets_by_date_range(
                        st.session_state.start_date,
                        st.session_state.end_date
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
                    tickets_to_display = data_manager.get_tickets_by_specific_date(specific_date)
                    filter_description = f"📆 {specific_date.strftime('%Y-%m-%d')}"
                    st.session_state.active_filter = "specific_date"
                    st.session_state.filter_description = filter_description
                    st.session_state.tickets_to_display = tickets_to_display

            with col3:
                preview_tickets = data_manager.get_tickets_by_specific_date(specific_date)
                st.metric("Tickets Found", len(preview_tickets))

        # Use session state to maintain filter results
        if 'tickets_to_display' in st.session_state and 'filter_description' in st.session_state:
            tickets_to_display = st.session_state.tickets_to_display
            filter_description = st.session_state.filter_description
        else:
            # Default to last hour if no filter applied
            tickets_to_display = data_manager.get_tickets_by_duration("Last hour")
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
                time_elapsed = format_time_elapsed(ticket['created_at'])
                date_created = format_date_display(ticket['created_at'])

                # Special highlighting for critical/urgent tickets
                is_urgent = (ticket.get('priority') in ['Critical', 'Desktop/User Down'] or
                           "Last hour" in filter_description)

                expand_key = f"ticket_{ticket['id']}_{i}"

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
                    cols[1].markdown(f"**Priority:** {ticket['priority']}")
                    cols[2].markdown(f"**Status:** {ticket['status']}")
                    cols[3].markdown(f"**Requester:** {ticket['requester_name']}")

                    st.markdown(f"**Email:** {ticket['requester_email']}")
                    if ticket.get('requester_phone'):
                        st.markdown(f"**Phone:** {ticket['requester_phone']}")
                    st.markdown(f"**Company ID:** {ticket['company_id']}")

                    # Description with expand/collapse
                    if len(ticket['description']) > 200:
                        if st.button(f"Show Full Description", key=f"desc_{ticket['id']}_{i}"):
                            st.markdown(f"**Description:** {ticket['description']}")
                        else:
                            st.markdown(f"**Description:** {ticket['description'][:200]}...")
                    else:
                        st.markdown(f"**Description:** {ticket['description']}")

                    # Technical details if available
                    if ticket.get('device_model') or ticket.get('os_version') or ticket.get('error_message'):
                        st.markdown("**Technical Details:**")
                        if ticket.get('device_model'):
                            st.markdown(f"• Device: {ticket['device_model']}")
                        if ticket.get('os_version'):
                            st.markdown(f"• OS: {ticket['os_version']}")
                        if ticket.get('error_message'):
                            st.markdown(f"• Error: {ticket['error_message']}")

                    # Status update section
                    st.markdown("---")
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        new_status = st.selectbox(
                            "Update Status:",
                            STATUS_OPTIONS,
                            index=STATUS_OPTIONS.index(ticket['status']) if ticket['status'] in STATUS_OPTIONS else 0,
                            key=f"status_{ticket['id']}_{i}"
                        )
                    with col2:
                        if st.button("Update Status", key=f"update_{ticket['id']}_{i}"):
                            data_manager.update_ticket_status(ticket['id'], new_status)
                            st.success(f"Status updated to {new_status}")
                            st.rerun()
                    with col3:
                        # Priority indicator
                        st.markdown(f"**Priority:** {PRIORITY_COLORS.get(ticket['priority'], '⚪')} {ticket['priority']}")

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
    """Dashboard page with analytics and charts."""
    st.title("📊 Dashboard")

    # Load from Knowledgebase.json
    if os.path.exists(KNOWLEDGEBASE_FILE):
        with open(KNOWLEDGEBASE_FILE, 'r') as f:
            kb_data = json.load(f)
    else:
        kb_data = []

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
                dt = datetime.fromisoformat(t['date'] + 'T' + t['time'])
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
            dt = datetime.fromisoformat(t['date'] + 'T' + t['time'])
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
            created_time = datetime.fromisoformat(entry['new_ticket']['date'] + 'T' + entry['new_ticket']['time'])
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
    category_colors = {cat: px.colors.qualitative.Plotly[i % 10] for i, cat in enumerate(df_category['Category'])}

    # Plot
    st.subheader("Tickets by Status, Priority, and Category")
    fig = px.bar(df_status, x="Status", y="Count", color="Status", category_orders={"Status": status_order}, color_discrete_map=STATUS_COLORS, barmode="group", title="Status")
    fig.add_bar(x=df_priority['Priority'], y=df_priority['Count'], name="Priority", marker_color=[CHART_PRIORITY_COLORS.get(p, '#888') for p in df_priority['Priority']])
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


if __name__ == "__main__":
    main()