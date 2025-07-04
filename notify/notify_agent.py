"""
Notify Agent for TeamLogic-AutoTask Application
Sends email notifications to technicians and users when tickets are assigned.

The Notify Agent receives ticket information from the Assignment Agent and sends
tailored email notifications to both the assigned technician and the ticket creator.
"""

import smtplib
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotifyAgent:
    """
    AI Agent responsible for sending email notifications when tickets are assigned.

    Receives ticket information from Assignment Agent and sends notifications to:
    1. Assigned technician - with ticket details
    2. Ticket creator - with assignment confirmation
    """

    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587,
                 email_user: str = None, email_password: str = None):
        """
        Initialize the Notify Agent with email configuration.

        Args:
            smtp_server (str): SMTP server address
            smtp_port (int): SMTP server port
            email_user (str): Email username for sending notifications
            email_password (str): Email password or app password
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_user = email_user or os.getenv('NOTIFY_EMAIL_USER', 'rohankul2017@gmail.com')
        self.email_password = email_password or os.getenv('NOTIFY_EMAIL_PASSWORD')

        if not self.email_password:
            logger.warning("Email password not set. Notifications will be logged but not sent.")

        # Email templates
        self.technician_template = self._load_technician_template()
        self.user_template = self._load_user_template()

    def _load_technician_template(self) -> str:
        """Load email template for technician notifications."""
        return """
        <html>
        <body>
            <h2>🎫 New Ticket Assignment</h2>
            <p>Hello <strong>{technician_name}</strong>,</p>

            <p>A new ticket has been assigned to you:</p>

            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <p><strong>Ticket ID:</strong> {ticket_id}</p>
                <p><strong>Due Date:</strong> {due_date}</p>
                <p><strong>Priority:</strong> {priority}</p>
                <p><strong>Category:</strong> {category}</p>
            </div>

            <h3>Description:</h3>
            <div style="background-color: #e9ecef; padding: 10px; border-radius: 5px;">
                <p>{description}</p>
            </div>

            <p>Please review and begin working on this ticket at your earliest convenience.</p>

            <p>Best regards,<br>
            TeamLogic-AutoTask System</p>
        </body>
        </html>
        """

    def _load_user_template(self) -> str:
        """Load email template for user notifications."""
        return """
        <html>
        <body>
            <h2>✅ Ticket Assignment Confirmation</h2>
            <p>Hello <strong>{user_name}</strong>,</p>

            <p>Your ticket has been successfully assigned to our technician.</p>

            <div style="background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <p><strong>Ticket ID:</strong> {ticket_id}</p>
                <p><strong>Status:</strong> Assigned</p>
                <p><strong>Assigned to:</strong> {technician_name}</p>
                <p><strong>Expected Resolution:</strong> {due_date}</p>
            </div>

            <p>Our technician will begin working on your request and will contact you if any additional information is needed.</p>

            <p>Thank you for using TeamLogic-AutoTask!</p>

            <p>Best regards,<br>
            Support Team</p>
        </body>
        </html>
        """

    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        Send an email notification.

        Args:
            to_email (str): Recipient email address
            subject (str): Email subject
            html_content (str): HTML email content

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.email_password:
            logger.info(f"[MOCK] Email would be sent to {to_email}")
            logger.info(f"[MOCK] Subject: {subject}")
            logger.info(f"[MOCK] Content: {html_content[:200]}...")
            return True

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_user
            msg['To'] = to_email
            msg['Subject'] = subject

            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)

            logger.info(f"✅ Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
            return False

    def notify_technician(self, ticket_data: Dict) -> bool:
        """
        Send notification email to the assigned technician.

        Args:
            ticket_data (Dict): Ticket information from Assignment Agent
                Required fields: ticket_id, issue, description, due_date,
                               technician_email, technician_name

        Returns:
            bool: True if notification sent successfully
        """
        try:
            # Extract required information
            ticket_id = ticket_data.get('ticket_id', 'Unknown')
            due_date = ticket_data.get('due_date', 'Not specified')
            description = ticket_data.get('description', 'No description provided')
            technician_email = ticket_data.get('technician_email')
            technician_name = ticket_data.get('technician_name', 'Technician')
            priority = ticket_data.get('priority', 'Medium')
            category = ticket_data.get('category', 'General')

            if not technician_email:
                logger.error("Technician email not provided")
                return False

            # Format email content
            html_content = self.technician_template.format(
                technician_name=technician_name,
                ticket_id=ticket_id,
                due_date=due_date,
                description=description,
                priority=priority,
                category=category
            )

            subject = f"🎫 New Ticket Assignment - {ticket_id}"

            # Send email
            return self._send_email(technician_email, subject, html_content)

        except Exception as e:
            logger.error(f"Error sending technician notification: {str(e)}")
            return False

    def notify_user(self, ticket_data: Dict) -> bool:
        """
        Send confirmation email to the user who raised the ticket.

        Args:
            ticket_data (Dict): Ticket information from Assignment Agent
                Required fields: ticket_id, user_email, user_name,
                               technician_name, due_date

        Returns:
            bool: True if notification sent successfully
        """
        try:
            # Extract required information
            ticket_id = ticket_data.get('ticket_id', 'Unknown')
            user_email = ticket_data.get('user_email')
            user_name = ticket_data.get('user_name', 'User')
            technician_name = ticket_data.get('technician_name', 'Our technician')
            due_date = ticket_data.get('due_date', 'Soon')

            if not user_email:
                logger.error("User email not provided")
                return False

            # Format email content
            html_content = self.user_template.format(
                user_name=user_name,
                ticket_id=ticket_id,
                technician_name=technician_name,
                due_date=due_date
            )

            subject = f"✅ Ticket Assignment Confirmation - {ticket_id}"

            # Send email
            return self._send_email(user_email, subject, html_content)

        except Exception as e:
            logger.error(f"Error sending user notification: {str(e)}")
            return False

    def process_ticket_assignment(self, ticket_data: Dict) -> Dict:
        """
        Main method to process ticket assignment and send notifications to both
        technician and user.

        Args:
            ticket_data (Dict): Complete ticket information from Assignment Agent
                Required fields: ticket_id, issue, description, due_date,
                               technician_email, technician_name, user_email, user_name

        Returns:
            Dict: Notification results with success/failure status
        """
        logger.info(f"🔔 Processing notifications for ticket: {ticket_data.get('ticket_id', 'Unknown')}")

        results = {
            'ticket_id': ticket_data.get('ticket_id'),
            'timestamp': datetime.now().isoformat(),
            'technician_notification': False,
            'user_notification': False,
            'errors': []
        }

        # Send technician notification
        try:
            results['technician_notification'] = self.notify_technician(ticket_data)
            if results['technician_notification']:
                logger.info("✅ Technician notification sent successfully")
            else:
                logger.error("❌ Failed to send technician notification")
                results['errors'].append("Failed to send technician notification")
        except Exception as e:
            logger.error(f"❌ Error in technician notification: {str(e)}")
            results['errors'].append(f"Technician notification error: {str(e)}")

        # Send user notification
        try:
            results['user_notification'] = self.notify_user(ticket_data)
            if results['user_notification']:
                logger.info("✅ User notification sent successfully")
            else:
                logger.error("❌ Failed to send user notification")
                results['errors'].append("Failed to send user notification")
        except Exception as e:
            logger.error(f"❌ Error in user notification: {str(e)}")
            results['errors'].append(f"User notification error: {str(e)}")

        # Log overall results
        success_count = sum([results['technician_notification'], results['user_notification']])
        logger.info(f"📊 Notification Summary: {success_count}/2 notifications sent successfully")

        return results

    def load_ticket_from_knowledgebase(self, ticket_id: str, knowledgebase_file: str = 'Knowledgebase.json') -> Dict:
        """
        Load ticket data from knowledge base for testing purposes.
        In production, this data will come from the Assignment Agent.

        Args:
            ticket_id (str): ID of the ticket to load
            knowledgebase_file (str): Path to knowledge base file

        Returns:
            Dict: Ticket data formatted for notification processing
        """
        try:
            if not os.path.exists(knowledgebase_file):
                logger.error(f"Knowledge base file not found: {knowledgebase_file}")
                return {}

            with open(knowledgebase_file, 'r') as f:
                kb_data = json.load(f)

            # Find ticket by ID (for testing, we'll use title as ID)
            for ticket in kb_data:
                if ticket.get('title') == ticket_id or str(ticket.get('id', '')) == str(ticket_id):
                    # Transform knowledge base data to notification format
                    return self._transform_kb_to_notification_format(ticket)

            logger.warning(f"Ticket not found in knowledge base: {ticket_id}")
            return {}

        except Exception as e:
            logger.error(f"Error loading ticket from knowledge base: {str(e)}")
            return {}

    def _transform_kb_to_notification_format(self, kb_ticket: Dict) -> Dict:
        """
        Transform knowledge base ticket data to notification format.

        Args:
            kb_ticket (Dict): Ticket data from knowledge base

        Returns:
            Dict: Formatted ticket data for notifications
        """
        # Extract classified data
        classified_data = kb_ticket.get('classified_data', {})

        # Mock technician assignment (since Assignment Agent isn't ready)
        technician_assignments = {
            'Network': {'name': 'John Smith', 'email': 'rohankul2017@gmail.com'},
            'Hardware': {'name': 'Sarah Johnson', 'email': 'rohankul2017@gmail.com'},
            'Software': {'name': 'Mike Davis', 'email': 'rohankul2017@gmail.com'},
            'Security': {'name': 'Lisa Wilson', 'email': 'rohankul2017@gmail.com'},
            'Default': {'name': 'Support Team', 'email': 'rohankul2017@gmail.com'}
        }

        # Determine technician based on category
        category = classified_data.get('TICKETCATEGORY', {}).get('Label', 'Default')
        technician = technician_assignments.get(category, technician_assignments['Default'])

        # Format notification data
        notification_data = {
            'ticket_id': kb_ticket.get('title', 'Unknown'),
            'issue': kb_ticket.get('title', 'No title'),
            'description': kb_ticket.get('description', 'No description provided'),
            'due_date': kb_ticket.get('due_date', 'Not specified'),
            'priority': classified_data.get('PRIORITY', {}).get('Label', 'Medium'),
            'category': category,
            'technician_name': technician['name'],
            'technician_email': technician['email'],
            'user_name': kb_ticket.get('name', 'User'),
            'user_email': kb_ticket.get('email_source', {}).get('sender_email') or 'user@example.com'
        }

        return notification_data


# Utility functions for testing and integration
def create_test_notification_data() -> Dict:
    """Create sample notification data for testing."""
    return {
        'ticket_id': 'TEST-001',
        'issue': 'Network connectivity issue',
        'description': 'User cannot access shared network drive. Error message: "Network path not found". Issue started this morning.',
        'due_date': '2024-01-15',
        'priority': 'High',
        'category': 'Network',
        'technician_name': 'John Smith',
        'technician_email': 'rohankul2017@gmail.com',
        'user_name': 'Jane Doe',
        'user_email': 'rohankul2017@gmail.com'
    }


def main():
    """Main function for testing the Notify Agent."""
    print("🔔 Testing Notify Agent")
    print("=" * 50)

    # Initialize Notify Agent
    notify_agent = NotifyAgent()

    # Test with sample data
    test_data = create_test_notification_data()

    print("📧 Sending test notifications...")
    results = notify_agent.process_ticket_assignment(test_data)

    print("\n📊 Results:")
    print(f"Ticket ID: {results['ticket_id']}")
    print(f"Technician Notification: {'✅ Success' if results['technician_notification'] else '❌ Failed'}")
    print(f"User Notification: {'✅ Success' if results['user_notification'] else '❌ Failed'}")

    if results['errors']:
        print("\n❌ Errors:")
        for error in results['errors']:
            print(f"  - {error}")

    print("\n🎉 Notify Agent test complete!")


if __name__ == "__main__":
    main()