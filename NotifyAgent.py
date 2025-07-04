import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import Dict

class NotifyAgent:
    def __init__(self, email_settings: Dict):
        """
        Initialize the Notify Agent with email server settings.
        
        Args:
            email_settings (Dict): Dictionary containing email configuration
                - smtp_server: SMTP server address
                - smtp_port: SMTP port number
                - sender_email: Email address sending the notifications
                - sender_password: Password for the sender email
        """
        self.smtp_server = email_settings.get('smtp_server')
        self.smtp_port = email_settings.get('smtp_port')
        self.sender_email = email_settings.get('sender_email')
        self.sender_password = email_settings.get('sender_password')
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def send_email(self, recipient: str, subject: str, body: str) -> bool:
        """
        Send an email to the specified recipient.
        
        Args:
            recipient (str): Email address of the recipient
            subject (str): Subject line of the email
            body (str): Body content of the email
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Create message container
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Attach the body to the email
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            self.logger.info(f"Email sent successfully to {recipient}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email to {recipient}: {str(e)}")
            return False
    
    def notify_technician(self, ticket_info: Dict, technician_email: str) -> bool:
        """
        Send notification email to the assigned technician.
        
        Args:
            ticket_info (Dict): Dictionary containing ticket information
                - ticket_Number: The ticket number
                - issuetype: Type of issue
                - due_date: Due date for resolution
                - description: Description of the issue
            technician_email (str): Email address of the assigned technician
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        subject = f"New Ticket Assigned: {ticket_info['ticket_Number']}"
        
        body = f"""You have been assigned a new ticket with the following details:

Ticket Number: {ticket_info['ticket_Number']}
Issue Type: {ticket_info['issuetype']}
Due Date: {ticket_info['due_date']}
Description: {ticket_info['description']}

Please address this ticket promptly.
"""
        return self.send_email(technician_email, subject, body)
    
    def notify_user(self, ticket_info: Dict, user_email: str) -> bool:
        """
        Send confirmation email to the user who created the ticket.
        
        Args:
            ticket_info (Dict): Dictionary containing ticket information
                - ticket_Number: The ticket number (used in subject line)
            user_email (str): Email address of the ticket creator
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        subject = f"Ticket #{ticket_info['ticket_Number']} - Assignment Confirmation"
        body = "Your ticket has been successfully assigned to our technician. We will contact you with updates."
        
        return self.send_email(user_email, subject, body)
    
    def process_assignment(self, assignment_data: Dict) -> Dict:
        """
        Process ticket assignment and send notifications to both technician and user.
        
        Args:
            assignment_data (Dict): Dictionary containing assignment information
                - ticket_info: Dictionary with ticket details
                - technician_email: Email of assigned technician
                - user_email: Email of ticket creator
                
        Returns:
            Dict: Dictionary with notification results
                - technician_notification: True if sent successfully
                - user_notification: True if sent successfully
        """
        results = {
            'technician_notification': False,
            'user_notification': False
        }
        
        try:
            # Send notification to technician
            if 'technician_email' in assignment_data and assignment_data['technician_email']:
                results['technician_notification'] = self.notify_technician(
                    assignment_data['ticket_info'],
                    assignment_data['technician_email']
                )
            
            # Send notification to user
            if 'user_email' in assignment_data and assignment_data['user_email']:
                results['user_notification'] = self.notify_user(
                    assignment_data['ticket_info'],
                    assignment_data['user_email']
                )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing assignment: {str(e)}")
            return results


# Example Usage
if __name__ == "__main__":
    # Configuration - replace with your actual email settings
    email_config = {
        'smtp_server': 'smtp.example.com',
        'smtp_port': 587,
        'sender_email': 'notifications@example.com',
        'sender_password': 'yourpassword'
    }
    
    # Create Notify Agent instance
    notify_agent = NotifyAgent(email_config)
    
    # Sample assignment data (in production, this would come from Assignment Agent)
    sample_assignment = {
        'ticket_info': {
            'ticket_Number': 'INC-12345',
            'issuetype': 'Hardware Issue',
            'due_date': '2023-12-31',
            'description': 'Laptop not turning on'
        },
        'technician_email': 'technician@example.com',
        'user_email': 'user@example.com'
    }
    
    # Process the assignment
    results = notify_agent.process_assignment(sample_assignment)
    
    print("Notification Results:")
    print(f"Technician notified: {'Success' if results['technician_notification'] else 'Failed'}")
    print(f"User notified: {'Success' if results['user_notification'] else 'Failed'}")