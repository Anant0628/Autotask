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
from typing import List, Dict, Optional

# ========== CONFIGURATION ==========
EMAIL_USER = "rohankul2017@gmail.com"
EMAIL_PASS = "pivw vasd mwyv lqhk"
IMAP_SERVER = "imap.gmail.com"
FOLDER = "inbox"
DEFAULT_TZ = "Asia/Kolkata"
MAX_EMAILS = 50
MINUTES_BACK = 5
DEFAULT_DUE_OFFSET_HOURS = 48  # Default due if no date found
# ===================================

IST = pytz.timezone(DEFAULT_TZ)

def connect_email():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select(FOLDER)
    return mail

def extract_due_date_nlp(text, received_dt):
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

    # 4. Fallback to dateparser (best-effort parsing)
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
                print(f"✅ Matched via dateparser: '{phrase}' → {dt.strftime('%Y-%m-%d')}")
                return dt.strftime('%Y-%m-%d')

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
    fallback = received_dt + timedelta(hours=48)
    print(f"⚠️ No pattern matched → fallback → {fallback.strftime('%Y-%m-%d')}")
    return fallback.strftime('%Y-%m-%d')

def process_email(msg):
    subject, encoding = decode_header(msg["Subject"])[0]
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

    ws.append([
        name,
        addr,
        subject.strip(),
        body.strip(),
        received_dt.strftime("%Y-%m-%d %H:%M:%S"),
        due_date
    ])

def main():
    print("[*] Connecting to mail server...")
    mail = connect_email()

    print("[*] Fetching recent emails...")
    status, messages = mail.search(None, 'ALL')
    email_ids = messages[0].split()

    for email_id in reversed(email_ids[-MAX_EMAILS:]):
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                received_dt = parsedate_to_datetime(msg.get("Date")).astimezone(IST)

                if received_dt < cutoff_time:
                    continue

                process_email(msg)

    # Save with timestamped filename to specific folder
    output_folder = "G:/AutoTask"
    os.makedirs(output_folder, exist_ok=True)
    filename = f"emails_{now.strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(output_folder, filename)
    wb.save(filepath)
    print(f"[✓] Exported to: {filepath}")
    mail.logout()

if __name__ == "__main__":
    main()
