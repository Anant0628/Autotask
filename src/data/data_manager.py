"""
Data management module for TeamLogic-AutoTask application.
Handles data loading, saving, and knowledge base management.
"""

import json
import os
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
from collections import Counter


class DataManager:
    """
    Manages data operations including reference data loading and knowledge base management.
    """

    def __init__(self, data_ref_file: str = 'data/reference_data.txt', knowledgebase_file: str = 'data/knowledgebase.json'):
        """
        Initialize the data manager.

        Args:
            data_ref_file (str): Path to the reference data file
            knowledgebase_file (str): Path to the knowledge base file
        """
        self.data_ref_file = data_ref_file
        self.knowledgebase_file = knowledgebase_file
        self.reference_data = {}
        self._load_reference_data()

    def _load_reference_data(self):
        """
        Loads and parses the data.txt file to get reference mappings for classification fields.
        Stores it in self.reference_data as:
        {
            "ISSUETYPE": {"4": "Hardware", "5": "Software/SaaS", ...},
            "SUBISSUETYPE": {"11": "Equipment Move", ...},
            ...
        }
        """
        if not os.path.exists(self.data_ref_file):
            print(f"Warning: Reference file '{self.data_ref_file}' not found. Classification might be less accurate.")
            return

        try:
            with open(self.data_ref_file, 'r') as f:
                data = json.load(f)

            employees_data = data.get("Employees", {}).get("Employee", [])

            for item in employees_data:
                field = item.get("Field")
                value = item.get("Value")
                label = item.get("Label")

                if field and value and label:
                    if field not in self.reference_data:
                        self.reference_data[field] = {}
                    self.reference_data[field][str(value)] = label

            print(f"Successfully loaded reference data from {self.data_ref_file}")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {self.data_ref_file}: {e}")
        except Exception as e:
            print(f"Error loading reference data: {e}")

    def save_to_knowledgebase(self, new_ticket_full_data: Dict, similar_tickets_metadata: List[Dict]):
        """
        Saves the new ticket's full data and similar tickets' metadata to Knowledgebase.json.

        Args:
            new_ticket_full_data (dict): The complete data of the new ticket including classification
            similar_tickets_metadata (list): List of metadata for similar tickets found
        """
        data_to_save = {
            "new_ticket": new_ticket_full_data,
            "similar_tickets_found": similar_tickets_metadata
        }

        existing_data = []
        if os.path.exists(self.knowledgebase_file):
            try:
                with open(self.knowledgebase_file, 'r') as f:
                    existing_data = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: {self.knowledgebase_file} is corrupted or empty. Starting with a new file.")
                existing_data = []

        existing_data.append(data_to_save)

        try:
            with open(self.knowledgebase_file, 'w') as f:
                json.dump(existing_data, f, indent=4)
            print(f"Successfully saved data to {self.knowledgebase_file}")
        except Exception as e:
            print(f"Error saving to {self.knowledgebase_file}: {e}")

    def load_tickets(self) -> Dict:
        """Load and adapt tickets from Knowledgebase.json to a flat list with required fields."""
        if not os.path.exists(self.knowledgebase_file):
            return {"tickets": []}

        with open(self.knowledgebase_file, 'r') as f:
            kb_data = json.load(f)

        tickets = []
        for entry in kb_data:
            t = entry.get('new_ticket', {})
            c = t.get('classified_data', {})
            ticket = {
                "id": t.get('ticket_number', t.get('title', '') + t.get('date', '') + t.get('time', '')),
                "ticket_number": t.get('ticket_number', 'N/A'),
                "title": t.get('title', ''),
                "description": t.get('description', ''),
                "created_at": f"{t.get('date', '')}T{t.get('time', '')}",
                "status": c.get('STATUS', {}).get('Label', 'Open'),
                "priority": c.get('PRIORITY', {}).get('Label', 'Medium'),
                "category": c.get('TICKETCATEGORY', {}).get('Label', 'General'),
                "requester_name": t.get('name', ''),
                "requester_email": t.get('user_email', ''),
                "requester_phone": "",  # Add if available
                "company_id": "",       # Add if available
                "device_model": "",     # Add if available
                "os_version": "",       # Add if available
                "error_message": "",    # Add if available
                "updated_at": t.get('updated_at', f"{t.get('date', '')}T{t.get('time', '')}")
            }
            tickets.append(ticket)
        return {"tickets": tickets}

    def save_tickets(self, data: Dict):
        """Save the adapted tickets back to Knowledgebase.json (only updates status/priority)."""
        if not os.path.exists(self.knowledgebase_file):
            return

        with open(self.knowledgebase_file, 'r') as f:
            kb_data = json.load(f)

        id_to_ticket = {t["id"]: t for t in data["tickets"]}

        for entry in kb_data:
            t = entry.get('new_ticket', {})
            c = t.get('classified_data', {})
            ticket_id = t.get('title', '') + t.get('date', '') + t.get('time', '')

            if ticket_id in id_to_ticket:
                updated = id_to_ticket[ticket_id]
                c['STATUS']['Label'] = updated['status']
                c['PRIORITY']['Label'] = updated['priority']
                t['updated_at'] = updated.get('updated_at', t.get('updated_at', f"{t.get('date', '')}T{t.get('time', '')}"))

        with open(self.knowledgebase_file, 'w') as f:
            json.dump(kb_data, f, indent=4)

    def get_recent_tickets(self, hours: int = 1) -> List[Dict]:
        """Get tickets created within specified hours"""
        data = self.load_tickets()
        cutoff_time = datetime.now() - timedelta(hours=hours)

        recent = []
        for ticket in data["tickets"]:
            try:
                created_time = datetime.fromisoformat(ticket["created_at"])
                if created_time >= cutoff_time:
                    recent.append(ticket)
            except:
                continue

        return sorted(recent, key=lambda x: x["created_at"], reverse=True)

    def get_today_tickets(self) -> List[Dict]:
        """Get all tickets created today"""
        data = self.load_tickets()
        today = datetime.now().date()

        today_tickets = []
        for ticket in data["tickets"]:
            try:
                created_time = datetime.fromisoformat(ticket["created_at"])
                if created_time.date() == today:
                    today_tickets.append(ticket)
            except:
                continue

        return sorted(today_tickets, key=lambda x: x["created_at"], reverse=True)

    def get_ticket_stats(self) -> Dict:
        """Get ticket statistics"""
        data = self.load_tickets()
        tickets = data["tickets"]

        stats = {
            "total_tickets": len(tickets),
            "by_status": {},
            "by_priority": {},
            "by_category": {},
            "last_24h": 0
        }

        cutoff_24h = datetime.now() - timedelta(hours=24)

        for ticket in tickets:
            # Status stats
            status = ticket.get("status", "Open")
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # Priority stats
            priority = ticket.get("priority", "Medium")
            stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1

            # Category stats
            category = ticket.get("category", "General")
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

            # Last 24h count
            try:
                created_time = datetime.fromisoformat(ticket["created_at"])
                if created_time >= cutoff_24h:
                    stats["last_24h"] += 1
            except:
                continue

        return stats

    def update_ticket_status(self, ticket_id: str, new_status: str):
        """Update ticket status"""
        data = self.load_tickets()
        for ticket in data["tickets"]:
            if ticket["id"] == ticket_id:
                ticket["status"] = new_status
                ticket["updated_at"] = datetime.now().isoformat()
                break
        self.save_tickets(data)

    def get_tickets_by_duration(self, duration: str) -> List[Dict]:
        """Get tickets based on selected duration"""
        data = self.load_tickets()
        now = datetime.now()

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
            filtered_tickets = []
            for ticket in data["tickets"]:
                try:
                    created_time = datetime.fromisoformat(ticket["created_at"])
                    if start_time <= created_time <= end_time:
                        filtered_tickets.append(ticket)
                except:
                    continue
            return sorted(filtered_tickets, key=lambda x: x["created_at"], reverse=True)
        elif duration == "Last 3 days":
            cutoff_time = now - timedelta(days=3)
        elif duration == "Last week":
            cutoff_time = now - timedelta(weeks=1)
        elif duration == "Last month":
            cutoff_time = now - timedelta(days=30)
        elif duration == "All tickets":
            return sorted(data["tickets"], key=lambda x: x["created_at"], reverse=True)
        else:
            cutoff_time = now - timedelta(hours=24)  # Default to last 24 hours

        filtered_tickets = []
        for ticket in data["tickets"]:
            try:
                created_time = datetime.fromisoformat(ticket["created_at"])
                if created_time >= cutoff_time:
                    filtered_tickets.append(ticket)
            except:
                continue

        return sorted(filtered_tickets, key=lambda x: x["created_at"], reverse=True)

    def get_tickets_by_date_range(self, start_date: date, end_date: date) -> List[Dict]:
        """Get tickets between two dates"""
        data = self.load_tickets()

        # Convert dates to datetime for comparison
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        filtered_tickets = []
        for ticket in data["tickets"]:
            try:
                created_time = datetime.fromisoformat(ticket["created_at"])
                if start_datetime <= created_time <= end_datetime:
                    filtered_tickets.append(ticket)
            except:
                continue

        return sorted(filtered_tickets, key=lambda x: x["created_at"], reverse=True)

    def get_tickets_by_specific_date(self, selected_date: date) -> List[Dict]:
        """Get tickets for a specific date"""
        data = self.load_tickets()

        filtered_tickets = []
        for ticket in data["tickets"]:
            try:
                created_time = datetime.fromisoformat(ticket["created_at"])
                if created_time.date() == selected_date:
                    filtered_tickets.append(ticket)
            except:
                continue

        return sorted(filtered_tickets, key=lambda x: x["created_at"], reverse=True)