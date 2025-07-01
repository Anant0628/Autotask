import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime, parseaddr
from datetime import datetime, timedelta
import pytz
import re
import os
import dateparser
from dateparser.search import search_dates

from intake_agent import IntakeClassificationAgent
from config import SF_ACCOUNT, SF_USER, SF_PASSWORD, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE, SF_PASSCODE, DATA_REF_FILE

# CONFIGURATION
EMAIL_ACCOUNT = 'rohankul2017@gmail.com'  # Set to your support email
EMAIL_PASSWORD = os.getenv('SUPPORT_EMAIL_PASSWORD')  # Use env variable for security!
IMAP_SERVER = 'imap.gmail.com'
FOLDER = 'inbox'
DEFAULT_TZ = 'Asia/Kolkata'
MAX_EMAILS = 50
MINUTES_BACK = 180  # How far back to look for recent emails
DEFAULT_DUE_OFFSET_HOURS = 48

IST = pytz.timezone(DEFAULT_TZ)
now = datetime.now(IST)
cutoff_time = now - timedelta(minutes=MINUTES_BACK)

def connect_email():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    mail.select(FOLDER)
    return mail

def extract_due_date_nlp(text, received_dt):
    text = text.lower()
    # 1. Custom Handling: "tomorrow"
    if "tomorrow" in text:
        result = received_dt + timedelta(days=1)
        return result.strftime('%Y-%m-%d')
    # 2. Custom Handling: "next <weekday>"
    match_next_day = re.search(r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', text)
    if match_next_day:
        weekday_str = match_next_day.group(1)
        weekday_target = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].index(weekday_str)
        days_ahead = (weekday_target - received_dt.weekday() + 7) % 7
        days_ahead = 7 if days_ahead == 0 else days_ahead
        result = received_dt + timedelta(days=days_ahead)
        return result.strftime('%Y-%m-%d')
    # 3. Custom Handling: "in 3 working days"
    match_working = re.search(r'(?:in|within)\s+(\d{1,2})\s+working\s+days?', text)
    if match_working:
        days = int(match_working.group(1))
        added = 0
        current = received_dt
        while added < days:
            current += timedelta(days=1)
            if current.weekday() < 5:
                added += 1
        return current.strftime('%Y-%m-%d')
    # 4. Fallback to dateparser
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
    # 5. Regex: 'after 4-7-2025 and before 7-7-2025'
    match_window = re.search(r'after\s+(\d{1,2})[-/](\d{1,2})[-/](\d{4})\s+and\s+before\s+(\d{1,2})[-/](\d{1,2})[-/](\d{4})', text)
    if match_window:
        d1, m1, y1, d2, m2, y2 = map(int, match_window.groups())
        try:
            start = datetime(y1, m1, d1, tzinfo=received_dt.tzinfo)
            end = datetime(y2, m2, d2, tzinfo=received_dt.tzinfo)
            mid = start + (end - start) / 2
            return mid.strftime('%Y-%m-%d')
        except:
            pass
    # 6. Final fallback: 48-hour default
    fallback = received_dt + timedelta(hours=DEFAULT_DUE_OFFSET_HOURS)
    return fallback.strftime('%Y-%m-%d')

def process_email(msg, agent):
    subject, encoding = decode_header(msg.get("Subject"))[0]
    subject = subject.decode(encoding or "utf-8") if isinstance(subject, bytes) else subject
    from_ = msg.get("From")
    name, addr = parseaddr(from_)
    email_date = msg.get("Date")
    received_dt = parsedate_to_datetime(email_date).astimezone(IST)
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                body = part.get_payload(decode=True).decode(errors="ignore")
                break
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")
    full_text = f"{subject}\n{body}"
    due_date = extract_due_date_nlp(full_text, received_dt)
    result = agent.process_new_ticket(
        ticket_name=name or addr,
        ticket_description=body.strip(),
        ticket_title=subject.strip(),
        due_date=due_date,
        priority_initial='Medium'
    )
    print(f"Processed ticket for email from {name or addr}: {subject.strip()} (Due: {due_date})")

def main():
    print("[*] Connecting to mail server...")
    mail = connect_email()
    print("[*] Fetching recent unseen emails...")
    status, messages = mail.search(None, 'UNSEEN')
    email_ids = messages[0].split()
    agent = IntakeClassificationAgent(
        sf_account=SF_ACCOUNT,
        sf_user=SF_USER,
        sf_password=SF_PASSWORD,
        sf_warehouse=SF_WAREHOUSE,
        sf_database=SF_DATABASE,
        sf_schema=SF_SCHEMA,
        sf_role=SF_ROLE,
        sf_passcode=SF_PASSCODE,
        data_ref_file=DATA_REF_FILE
    )
    for email_id in reversed(email_ids[-MAX_EMAILS:]):
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                received_dt = parsedate_to_datetime(msg.get("Date")).astimezone(IST)
                if received_dt < cutoff_time:
                    continue
                process_email(msg, agent)
                mail.store(email_id, '+FLAGS', '\\Seen')
    mail.logout()

if __name__ == "__main__":
    main()
