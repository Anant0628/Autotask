"""
Email processing service for TeamLogic-AutoTask application.
Provides background email processing functionality.
"""

import time
import threading
from datetime import datetime
from typing import List, Dict, Callable
import streamlit as st

from email_processor import EmailProcessor, get_default_email_processor
from intake_agent import IntakeClassificationAgent


class EmailService:
    """
    Background service for processing emails and creating tickets.
    """
    
    def __init__(self, intake_agent: IntakeClassificationAgent, 
                 email_processor: EmailProcessor = None,
                 check_interval_minutes: int = 5):
        """
        Initialize the email service.
        
        Args:
            intake_agent (IntakeClassificationAgent): The intake agent to process tickets
            email_processor (EmailProcessor): Email processor instance
            check_interval_minutes (int): How often to check for emails (in minutes)
        """
        self.intake_agent = intake_agent
        self.email_processor = email_processor or get_default_email_processor()
        self.check_interval_minutes = check_interval_minutes
        self.is_running = False
        self.thread = None
        self.last_check = None
        self.processed_tickets = []
        self.notification_callback = None
        
    def set_notification_callback(self, callback: Callable[[List[Dict]], None]):
        """
        Set a callback function to be called when new tickets are processed.
        
        Args:
            callback: Function that takes a list of processed tickets
        """
        self.notification_callback = callback
    
    def process_emails_once(self) -> List[Dict]:
        """
        Process emails once and return the results.
        Uses Gmail-specific logic to process only unseen emails.

        Returns:
            List[Dict]: List of processed tickets
        """
        try:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking for new unseen emails...")

            # Process recent emails (Gmail-specific: only unseen emails)
            processed_tickets = self.intake_agent.process_recent_emails(
                email_processor=self.email_processor
            )

            if processed_tickets:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processed {len(processed_tickets)} email tickets")

                # Store processed tickets
                self.processed_tickets.extend(processed_tickets)

                # Call notification callback if set
                if self.notification_callback:
                    self.notification_callback(processed_tickets)

            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] No new unseen emails to process")

            self.last_check = datetime.now()
            return processed_tickets

        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error processing emails: {str(e)}")
            return []
    
    def _background_worker(self):
        """Background worker that periodically checks for emails."""
        while self.is_running:
            try:
                self.process_emails_once()
                
                # Wait for the specified interval
                for _ in range(self.check_interval_minutes * 60):
                    if not self.is_running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Background worker error: {str(e)}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def start_background_processing(self):
        """Start background email processing."""
        if self.is_running:
            print("Email service is already running")
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._background_worker, daemon=True)
        self.thread.start()
        print(f"Email service started - checking every {self.check_interval_minutes} minutes")
    
    def stop_background_processing(self):
        """Stop background email processing."""
        if not self.is_running:
            print("Email service is not running")
            return
        
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("Email service stopped")
    
    def get_processed_tickets(self) -> List[Dict]:
        """Get all processed tickets from this session."""
        return self.processed_tickets.copy()
    
    def clear_processed_tickets(self):
        """Clear the processed tickets list."""
        self.processed_tickets.clear()
    
    def get_status(self) -> Dict:
        """Get the current status of the email service."""
        return {
            "is_running": self.is_running,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "processed_tickets_count": len(self.processed_tickets),
            "check_interval_minutes": self.check_interval_minutes
        }


# Streamlit session state management for email service
def get_email_service(intake_agent: IntakeClassificationAgent) -> EmailService:
    """
    Get or create an email service instance in Streamlit session state.
    
    Args:
        intake_agent: The intake agent instance
        
    Returns:
        EmailService: The email service instance
    """
    if 'email_service' not in st.session_state:
        st.session_state.email_service = EmailService(intake_agent)
        
        # Set up notification callback to store notifications in session state
        def notification_callback(processed_tickets):
            if 'email_notifications' not in st.session_state:
                st.session_state.email_notifications = []
            
            for ticket in processed_tickets:
                notification = {
                    'message': f"Ticket successfully raised via email: {ticket.get('title', 'Unknown')}",
                    'ticket_data': ticket,
                    'timestamp': datetime.now().isoformat(),
                    'type': 'email_success'
                }
                st.session_state.email_notifications.append(notification)
        
        st.session_state.email_service.set_notification_callback(notification_callback)
    
    return st.session_state.email_service


def get_email_notifications() -> List[Dict]:
    """Get email notifications from session state."""
    return st.session_state.get('email_notifications', [])


def clear_email_notifications():
    """Clear email notifications from session state."""
    if 'email_notifications' in st.session_state:
        st.session_state.email_notifications.clear()


def mark_notification_as_read(index: int):
    """Mark a specific notification as read."""
    if 'email_notifications' in st.session_state and 0 <= index < len(st.session_state.email_notifications):
        st.session_state.email_notifications[index]['read'] = True
