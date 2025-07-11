"""
Main intake classification agent that orchestrates all modules.
This is the main class that provides the same interface as the original monolithic code.
"""

import json
import uuid
import hashlib
import os
from datetime import datetime
from typing import Dict, List, Optional

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database import SnowflakeConnection
from src.data import DataManager
from src.processors import AIProcessor, TicketProcessor
from src.agents.notification_agent import NotificationAgent
from src.agents.assignment_agent import AssignmentAgentIntegration


class IntakeClassificationAgent:
    """
    An AI Agent for intake and classification of support tickets using Snowflake Cortex.
    This class orchestrates all the modular components to maintain the same functionality.
    """

    def __init__(self, sf_account: str, sf_user: str, sf_password: str, sf_warehouse: str,
                 sf_database: str, sf_schema: str, sf_role: str, sf_passcode: str,
                 data_ref_file: str = 'data.txt'):
        """
        Initializes the agent with Snowflake connection details and loads reference data.

        Args:
            sf_account (str): Snowflake account identifier.
            sf_user (str): Snowflake username.
            sf_password (str): Snowflake password.
            sf_warehouse (str): Snowflake warehouse to use.
            sf_database (str): Snowflake database to use.
            sf_schema (str): Snowflake schema to use.
            sf_role (str): Snowflake role to use.
            sf_passcode (str): Snowflake MFA passcode (if applicable).
            data_ref_file (str): Path to the data.txt file containing reference mappings.
        """
        # Initialize database connection
        self.db_connection = SnowflakeConnection(
            sf_account, sf_user, sf_password, sf_warehouse,
            sf_database, sf_schema, sf_role, sf_passcode
        )

        # Initialize data manager
        self.data_manager = DataManager(data_ref_file)

        # Initialize AI processor
        self.ai_processor = AIProcessor(self.db_connection, self.data_manager.reference_data)

        # Initialize ticket processor
        self.ticket_processor = TicketProcessor(self.data_manager.reference_data)

        # Initialize notification agent
        self.notification_agent = NotificationAgent()

        # Initialize assignment agent with Google Calendar integration
        google_calendar_credentials_path = "credentials/google-calendar-credentials.json"
        self.assignment_agent = AssignmentAgentIntegration(
            self.db_connection,
            google_calendar_credentials_path=google_calendar_credentials_path
        )

        # Expose connection and reference data for backward compatibility
        self.conn = self.db_connection.conn
        self.reference_data = self.data_manager.reference_data

    def generate_ticket_number(self, ticket_data: Dict) -> str:
        """
        Generate a unique ticket number in format T20240916.0057

        Args:
            ticket_data (dict): Ticket information

        Returns:
            str: Unique ticket number in format TYYYYMMDD.NNNN
        """
        # Get current timestamp
        now = datetime.now()
        date_part = now.strftime("%Y%m%d")

        # Get next sequential number for today
        sequence_number = self._get_next_sequence_number(date_part)

        # Generate ticket number: TYYYYMMDD.NNNN
        ticket_number = f"T{date_part}.{sequence_number:04d}"

        print(f"Generated ticket number: {ticket_number}")
        return ticket_number

    def _get_next_sequence_number(self, date_part: str) -> int:
        """
        Get the next sequential number for the given date.

        Args:
            date_part (str): Date in YYYYMMDD format

        Returns:
            int: Next sequential number
        """
        sequence_file = "data/ticket_sequence.json"

        # Load existing sequence data
        sequence_data = {}
        if os.path.exists(sequence_file):
            try:
                with open(sequence_file, 'r') as f:
                    sequence_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                sequence_data = {}

        # Get current sequence for this date, default to 0
        current_sequence = sequence_data.get(date_part, 0)

        # Increment sequence
        next_sequence = current_sequence + 1

        # Update sequence data
        sequence_data[date_part] = next_sequence

        # Save updated sequence data
        try:
            with open(sequence_file, 'w') as f:
                json.dump(sequence_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save sequence file: {e}")

        return next_sequence

    def extract_metadata(self, title: str, description: str, model: str = 'llama3-8b') -> Optional[Dict]:
        """
        Extracts structured metadata from the ticket title and description using LLM.
        """
        return self.ai_processor.extract_metadata(title, description, model)

    def find_similar_tickets(self, extracted_metadata: Dict) -> List[Dict]:
        """
        Searches the Snowflake database for similar tickets based on extracted metadata.
        """
        search_conditions, params = self.ticket_processor.find_similar_tickets_conditions(extracted_metadata)
        return self.db_connection.find_similar_tickets(search_conditions, params)

    def classify_ticket(self, new_ticket_data: Dict, extracted_metadata: Dict,
                       similar_tickets: List[Dict], model: str = 'mixtral-8x7b') -> Optional[Dict]:
        """
        Classifies the new ticket based on extracted metadata and similar tickets using LLM.
        """
        return self.ai_processor.classify_ticket(new_ticket_data, extracted_metadata, similar_tickets, model)

    def generate_resolution_note(self, ticket_data: Dict, classified_data: Dict,
                               extracted_metadata: Dict) -> str:
        """
        Generates a resolution note using Cortex LLM.
        """
        return self.ai_processor.generate_resolution_note(ticket_data, classified_data, extracted_metadata)

    def save_to_knowledgebase(self, new_ticket_full_data: Dict, similar_tickets_metadata: List[Dict]):
        """
        Saves the new ticket's full data and similar tickets' metadata to Knowledgebase.json.
        """
        self.data_manager.save_to_knowledgebase(new_ticket_full_data, similar_tickets_metadata)

    def process_new_ticket(self, ticket_name: str, ticket_description: str, ticket_title: str,
                          due_date: str, priority_initial: str, user_email: Optional[str] = None,
                          extract_model: str = 'llama3-8b', classify_model: str = 'mixtral-8x7b') -> Optional[Dict]:
        """
        Orchestrates the entire process for a new incoming ticket.

        Args:
            ticket_name (str): Name of the person raising the ticket.
            ticket_description (str): Description of the issue.
            ticket_title (str): Title of the ticket.
            due_date (str): Due date for the ticket (e.g., "YYYY-MM-DD").
            priority_initial (str): Initial priority set by the user (e.g., "Medium").
            user_email (str, optional): User's email address for notifications.
            extract_model (str): Model to use for metadata extraction.
            classify_model (str): Model to use for classification.

        Returns:
            dict: The classified ticket data, or None if the process fails.
        """
        print(f"\n--- Processing New Ticket: '{ticket_title}' ---")

        creation_time = datetime.now()
        ticket_date = creation_time.strftime("%Y-%m-%d")
        ticket_time = creation_time.strftime("%H:%M:%S")

        new_ticket_raw = {
            "name": ticket_name,
            "description": ticket_description,
            "title": ticket_title,
            "date": ticket_date,
            "time": ticket_time,
            "due_date": due_date,
            "priority": priority_initial
        }

        # Generate unique ticket number
        ticket_number = self.generate_ticket_number(new_ticket_raw)

        # Extract metadata
        extracted_metadata = self.extract_metadata(ticket_title, ticket_description, model=extract_model)
        if not extracted_metadata:
            print("Failed to extract metadata. Aborting ticket processing.")
            return None
        print("Extracted Metadata:")
        print(json.dumps(extracted_metadata, indent=2))

        # Find similar tickets
        similar_tickets = self.find_similar_tickets(extracted_metadata)
        if similar_tickets:
            print(f"\nFound {len(similar_tickets)} similar tickets:")
            for i, ticket in enumerate(similar_tickets):
                issue_type_label = self.reference_data.get('issuetype', {}).get(str(ticket.get('ISSUETYPE')), 'N/A')
                priority_label = self.reference_data.get('priority', {}).get(str(ticket.get('PRIORITY')), 'N/A')
                print(f"  {i+1}. Title: {ticket.get('TITLE', 'N/A')}, Type: {issue_type_label}, Priority: {priority_label}")
        else:
            print("\nNo similar tickets found.")

        # Classify ticket
        classified_data = self.classify_ticket(new_ticket_raw, extracted_metadata, similar_tickets, model=classify_model)
        if not classified_data:
            print("Failed to classify ticket. Aborting ticket processing.")
            return None
        print("\nClassified Ticket Data:")
        print(json.dumps(classified_data, indent=2))

        # Generate resolution note
        print("\n--- Generating Resolution Note ---")
        resolution_note = self.generate_resolution_note(new_ticket_raw, classified_data, extracted_metadata)
        print("Generated Resolution Note:")
        print(resolution_note)

        # Prepare final ticket data
        final_ticket_data = {
            **new_ticket_raw,
            "ticket_number": ticket_number,
            "user_email": user_email if user_email and user_email.strip() else "",
            "extracted_metadata": extracted_metadata,
            "classified_data": classified_data,
            "resolution_note": resolution_note
        }

        # Process assignment after classification
        print("\n--- Processing Ticket Assignment ---")
        try:
            assignment_result = self.assignment_agent.process_ticket_assignment({"new_ticket": final_ticket_data})
            final_ticket_data["assignment_result"] = assignment_result.get("assignment_result", {})
            print("Assignment Result:")
            print(json.dumps(assignment_result, indent=2))
        except Exception as e:
            print(f"❌ Assignment failed: {e}")
            # Continue processing even if assignment fails
            final_ticket_data["assignment_result"] = {
                "status": "Assignment Failed",
                "error": str(e),
                "assigned_technician": "IT Manager",
                "technician_email": "itmanager@company.com"
            }

        # Prepare similar tickets for knowledge base
        similar_tickets_for_kb = []
        for ticket in similar_tickets:
            kb_ticket = {k: v for k, v in ticket.items() if k in ['TITLE', 'DESCRIPTION', 'ISSUETYPE', 'SUBISSUETYPE', 'TICKETCATEGORY', 'TICKETTYPE', 'PRIORITY', 'STATUS']}

            for field in ['ISSUETYPE', 'SUBISSUETYPE', 'TICKETCATEGORY', 'TICKETTYPE', 'PRIORITY', 'STATUS']:
                if field in kb_ticket:
                    ref_field_name = field.lower()
                    if ref_field_name in self.reference_data and str(kb_ticket[field]) in self.reference_data[ref_field_name]:
                        kb_ticket[field] = {
                            "Value": kb_ticket[field],
                            "Label": self.reference_data[ref_field_name][str(kb_ticket[field])]
                        }
                    else:
                        kb_ticket[field] = {"Value": kb_ticket[field], "Label": "Unknown/N/A"}

            similar_tickets_for_kb.append(kb_ticket)

        # Save to knowledge base
        self.save_to_knowledgebase(final_ticket_data, similar_tickets_for_kb)

        # Send notification email if user email is provided
        if user_email and user_email.strip():
            print(f"\n--- Sending Confirmation Email to {user_email} ---")
            email_sent = self.notification_agent.send_ticket_confirmation(
                user_email=user_email,
                ticket_data=final_ticket_data,
                ticket_number=ticket_number
            )
            if email_sent:
                print("✅ Confirmation email sent successfully")
            else:
                print("❌ Failed to send confirmation email")

        print(f"\n--- Ticket Processing Complete (#{ticket_number}) ---")
        return final_ticket_data