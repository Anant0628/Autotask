"""
Email processing module for TeamLogic-AutoTask application.
Extracts ticket data from emails and integrates with the intake system.
"""

import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime, parseaddr
from datetime import datetime, timedelta
import pytz
import re
from typing import List, Dict, Optional

# Optional dateparser import with fallback
try:
    import dateparser
    from dateparser.search import search_dates
    HAS_DATEPARSER = True
except ImportError:
    dateparser = None
    search_dates = None
    HAS_DATEPARSER = False
    print("Warning: dateparser not installed. Advanced date parsing will be limited.")


class EmailProcessor:
    """
    Processes emails to extract ticket information and integrates with intake system.
    """
    
    def __init__(self, email_user: str, email_pass: str, imap_server: str = "imap.gmail.com",
                 folder: str = "inbox", default_tz: str = "Asia/Kolkata",
                 max_emails: int = 50, minutes_back: int = 180,
                 default_due_offset_hours: int = 48):
        """
        Initialize the email processor with configuration.
        
        Args:
            email_user (str): Email username
            email_pass (str): Email password or app password
            imap_server (str): IMAP server address
            folder (str): Email folder to check
            default_tz (str): Default timezone
            max_emails (int): Maximum number of emails to process
            minutes_back (int): How many minutes back to check for emails
            default_due_offset_hours (int): Default due date offset in hours
        """
        self.email_user = email_user
        self.email_pass = email_pass
        self.imap_server = imap_server
        self.folder = folder
        self.default_tz = default_tz
        self.max_emails = max_emails
        self.minutes_back = minutes_back
        self.default_due_offset_hours = default_due_offset_hours
        
        self.tz = pytz.timezone(self.default_tz)
        
    def connect_email(self) -> imaplib.IMAP4_SSL:
        """Connect to the email server and return the connection."""
        mail = imaplib.IMAP4_SSL(self.imap_server)
        mail.login(self.email_user, self.email_pass)
        mail.select(self.folder)
        return mail
    
    def extract_due_date_nlp(self, text: str, received_dt: datetime) -> str:
        """
        Enhanced NLP date extractor: matches both exact and relative phrases like
        'next Friday', 'in 3 working days', 'tomorrow', and falls back correctly.
        """
        text = text.lower()

        print("\n------------------------------")
        print("📨 Text:", text.strip()[:150])
        print("📬 Received:", received_dt.strftime('%Y-%m-%d %H:%M:%S'))

        # 1. Custom Handling: "tomorrow"
        if "tomorrow" in text:
            result = received_dt + timedelta(days=1)
            print(f"✅ Matched: 'tomorrow' → {result.strftime('%Y-%m-%d')}")
            return result.strftime('%Y-%m-%d')

        # 2. Custom Handling: "next <weekday>"
        match_next_day = re.search(r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', text)
        if match_next_day:
            weekday_str = match_next_day.group(1)
            weekday_target = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].index(weekday_str)

            days_ahead = (weekday_target - received_dt.weekday() + 7) % 7
            days_ahead = 7 if days_ahead == 0 else days_ahead  # Ensure "next" always means next week
            result = received_dt + timedelta(days=days_ahead)
            print(f"✅ Matched: 'next {weekday_str}' → {result.strftime('%Y-%m-%d')}")
            return result.strftime('%Y-%m-%d')

        # 3. Custom Handling: "in 3 working days"
        match_working = re.search(r'(?:in|within)\s+(\d{1,2})\s+working\s+days?', text)
        if match_working:
            days = int(match_working.group(1))
            added = 0
            current = received_dt
            while added < days:
                current += timedelta(days=1)
                if current.weekday() < 5:  # Weekdays only
                    added += 1
            print(f"✅ Matched: 'in {days} working days' → {current.strftime('%Y-%m-%d')}")
            return current.strftime('%Y-%m-%d')

        # 4. Fallback to dateparser (best-effort parsing) - only if available
        if HAS_DATEPARSER and search_dates:
            parsed_results = search_dates(
                text,
                settings={
                    'RELATIVE_BASE': received_dt,
                    'PREFER_DATES_FROM': 'future',
                    'TIMEZONE': self.default_tz,
                    'RETURN_AS_TIMEZONE_AWARE': True
                }
            )
            if parsed_results:
                for phrase, dt in parsed_results:
                    if dt > received_dt:
                        print(f"✅ Matched via dateparser: '{phrase}' → {dt.strftime('%Y-%m-%d')}")
                        return dt.strftime('%Y-%m-%d')
        else:
            print("⚠️ Advanced date parsing unavailable (dateparser not installed)")

        # 5. Regex: 'before 4-7-2025' or 'after 2-7-2025'
        match_window = re.search(r'after\s+(\d{1,2})[-/](\d{1,2})[-/](\d{4})\s+and\s+before\s+(\d{1,2})[-/](\d{1,2})[-/](\d{4})', text)
        if match_window:
            d1, m1, y1, d2, m2, y2 = map(int, match_window.groups())
            try:
                start = datetime(y1, m1, d1, tzinfo=received_dt.tzinfo)
                end = datetime(y2, m2, d2, tzinfo=received_dt.tzinfo)
                mid = start + (end - start) / 2
                print(f"✅ Matched: 'after X and before Y' → using midpoint → {mid.strftime('%Y-%m-%d')}")
                return mid.strftime('%Y-%m-%d')
            except:
                pass

        # 6. Final fallback: 48-hour default
        fallback = received_dt + timedelta(hours=self.default_due_offset_hours)
        print(f"⚠️ No pattern matched → fallback → {fallback.strftime('%Y-%m-%d')}")
        return fallback.strftime('%Y-%m-%d')
    
    def process_email(self, msg) -> Dict:
        """
        Process a single email message and extract ticket data.
        
        Args:
            msg: Email message object
            
        Returns:
            dict: Extracted ticket data
        """
        subject, encoding = decode_header(msg["Subject"])[0]
        subject = subject.decode(encoding or "utf-8") if isinstance(subject, bytes) else subject

        from_ = msg.get("From")
        name, addr = parseaddr(from_)

        email_date = msg.get("Date")
        received_dt = parsedate_to_datetime(email_date).astimezone(self.tz)

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        full_text = f"{subject}\n{body}"
        due_date = self.extract_due_date_nlp(full_text, received_dt)

        return {
            "name": name.strip() if name else addr.split('@')[0],
            "email": addr,
            "title": subject.strip(),
            "description": body.strip(),
            "received_time": received_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "due_date": due_date,
            "source": "email"
        }
    
    def get_recent_emails(self, mark_as_seen: bool = True) -> List[Dict]:
        """
        Fetch and process recent unseen emails, returning a list of ticket data.

        Args:
            mark_as_seen (bool): Whether to mark processed emails as seen

        Returns:
            List[Dict]: List of extracted ticket data from emails
        """
        print("[*] Connecting to mail server...")
        mail = self.connect_email()

        now = datetime.now(self.tz)
        cutoff_time = now - timedelta(minutes=self.minutes_back)

        print(f"[*] Fetching recent unseen emails from last {self.minutes_back} minutes...")
        _, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()

        if not email_ids:
            print("[*] No unseen emails found")
            mail.logout()
            return []

        extracted_tickets = []

        for email_id in reversed(email_ids[-self.max_emails:]):
            _, msg_data = mail.fetch(email_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    received_dt = parsedate_to_datetime(msg.get("Date")).astimezone(self.tz)

                    if received_dt < cutoff_time:
                        continue

                    ticket_data = self.process_email(msg)
                    extracted_tickets.append(ticket_data)

                    # Mark email as seen after processing
                    if mark_as_seen:
                        mail.store(email_id, '+FLAGS', '\\Seen')
                        print(f"[*] Marked email as seen: {ticket_data.get('title', 'Unknown')}")

        mail.logout()
        print(f"[✓] Extracted {len(extracted_tickets)} tickets from emails")
        return extracted_tickets


# Default configuration for backward compatibility
def get_default_email_processor() -> EmailProcessor:
    """Get an EmailProcessor with default configuration."""
    import os

    # Use environment variables for security
    email_user = os.getenv('SUPPORT_EMAIL_USER', 'rohankul2017@gmail.com')
    email_pass = os.getenv('SUPPORT_EMAIL_PASSWORD', 'pivw vasd mwyv lqhk')  # Should be set in .env

    return EmailProcessor(
        email_user=email_user,
        email_pass=email_pass,
        imap_server="imap.gmail.com",
        folder="inbox",
        default_tz="Asia/Kolkata",
        max_emails=50,
        minutes_back=180,  # 3 hours back
        default_due_offset_hours=48
    )
