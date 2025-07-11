from .database import execute_query
from typing import List, Dict, Optional
import json
import os

# Load reference data for field mapping
def load_reference_data():
    """Load reference data for mapping numeric IDs to labels"""
    reference_data = {}
    # Try multiple possible paths for the reference data file
    possible_paths = [
        'data/reference_data.txt',
        '../data/reference_data.txt',
        'Autotask-feature-Agent_email/data/reference_data.txt'
    ]

    data_ref_file = None
    for path in possible_paths:
        if os.path.exists(path):
            data_ref_file = path
            break

    if not data_ref_file:
        print(f"Warning: Reference file not found in any of the expected locations: {possible_paths}")
        return reference_data

    try:
        with open(data_ref_file, 'r') as f:
            data = json.load(f)

        employees_data = data.get("Employees", {}).get("Employee", [])

        for item in employees_data:
            field = item.get("Field")
            value = item.get("Value")
            label = item.get("Label")

            if field and value and label:
                if field not in reference_data:
                    reference_data[field] = {}
                reference_data[field][str(value)] = label

        print(f"Successfully loaded reference data from {data_ref_file}")
    except Exception as e:
        print(f"Error loading reference data: {e}")

    return reference_data

# Global reference data
REFERENCE_DATA = load_reference_data()

def transform_ticket_data(raw_ticket: Dict) -> Dict:
    """Transform raw database ticket data to API response format"""
    if not raw_ticket:
        print("DEBUG: transform_ticket_data received None/empty ticket")
        return None

    print(f"DEBUG: Transforming ticket data for ticket: {raw_ticket.get('TICKETNUMBER', 'Unknown')}")
    print(f"DEBUG: Raw ticket keys: {list(raw_ticket.keys())}")
    print(f"DEBUG: Raw ISSUETYPE: {raw_ticket.get('ISSUETYPE')}")
    print(f"DEBUG: Reference data keys: {list(REFERENCE_DATA.keys())}")

    # Map database fields to response model fields
    transformed = {
        "TICKETNUMBER": raw_ticket.get("TICKETNUMBER", ""),  # Use alias expected by Pydantic model
        "issue_type": REFERENCE_DATA.get("issuetype", {}).get(str(raw_ticket.get("ISSUETYPE", "")), "Unknown"),
        "sub_issue_type": REFERENCE_DATA.get("subissuetype", {}).get(str(raw_ticket.get("SUBISSUETYPE", "")), "Unknown"),
        "ticket_category": REFERENCE_DATA.get("ticketcategory", {}).get(str(raw_ticket.get("TICKETCATEGORY", "")), "Unknown"),
        "priority": REFERENCE_DATA.get("priority", {}).get(str(raw_ticket.get("PRIORITY", "")), "Unknown"),
        "description": raw_ticket.get("DESCRIPTION") or "",  # Handle None values
        "status": REFERENCE_DATA.get("status", {}).get(str(raw_ticket.get("STATUS", "")), "Unknown"),
        "due_date": str(raw_ticket.get("DUEDATETIME", "")),
        "CREATEDATE": raw_ticket.get("CREATEDATE", "")
        # "updated_at": None   # Commented out completely
    }

    print(f"DEBUG: Transformed ticket: {transformed}")
    return transformed

# --- Ticket CRUD ---
def get_all_tickets() -> List[Dict]:
    """Get all tickets from the database"""
    print("DEBUG: Starting get_all_tickets()")
    query = """
    SELECT * FROM TEST_DB.PUBLIC.COMPANY_4130_DATA
    ORDER BY CREATEDATE DESC
    LIMIT 100
    """
    print(f"DEBUG: Executing query: {query}")
    raw_tickets = execute_query(query)
    print(f"DEBUG: Raw tickets returned: {len(raw_tickets) if raw_tickets else 0}")

    if raw_tickets:
        print(f"DEBUG: First raw ticket: {raw_tickets[0]}")

    transformed_tickets = []
    for ticket in raw_tickets:
        if ticket:
            transformed = transform_ticket_data(ticket)
            if transformed:
                transformed_tickets.append(transformed)
                print(f"DEBUG: Successfully transformed ticket: {transformed.get('TICKETNUMBER', 'Unknown')}")
            else:
                print(f"DEBUG: Failed to transform ticket: {ticket.get('TICKETNUMBER', 'Unknown')}")

    print(f"DEBUG: Returning {len(transformed_tickets)} transformed tickets")
    return transformed_tickets

def get_ticket_by_number(ticket_number: str) -> Optional[Dict]:
    query = """
    SELECT * FROM TEST_DB.PUBLIC.COMPANY_4130_DATA WHERE TICKETNUMBER = %s
    """
    results = execute_query(query, (ticket_number,))
    if results:
        return transform_ticket_data(results[0])
    return None

def update_ticket_by_number(ticket_number: str, status: Optional[str] = None, priority: Optional[str] = None) -> bool:
    set_clauses = []
    params = []
    if status:
        set_clauses.append("STATUS = %s")
        params.append(status)
    if priority:
        set_clauses.append("PRIORITY = %s")
        params.append(priority)
    if not set_clauses:
        return False
    params.append(ticket_number)
    query = f"""
    UPDATE TEST_DB.PUBLIC.COMPANY_4130_DATA
    SET {', '.join(set_clauses)}
    WHERE TICKETNUMBER = %s
    """
    execute_query(query, tuple(params))
    return True

def create_ticket(ticket_data) -> Optional[Dict]:
    """Create a new ticket"""
    query = """
    INSERT INTO TEST_DB.PUBLIC.COMPANY_4130_DATA
    (TICKETNUMBER, ISSUETYPE, SUBISSUETYPE, TICKETCATEGORY, PRIORITY, DESCRIPTION, STATUS, DUEDATETIME, CREATEDATE)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    # Map the API field names to database values using reverse lookup in reference data
    issue_type_id = get_reference_id("issuetype", ticket_data.issue_type)
    sub_issue_type_id = get_reference_id("subissuetype", ticket_data.sub_issue_type)
    ticket_category_id = get_reference_id("ticketcategory", ticket_data.ticket_category)
    priority_id = get_reference_id("priority", ticket_data.priority)
    status_id = get_reference_id("status", ticket_data.status)

    params = (
        ticket_data.ticket_number,
        issue_type_id,
        sub_issue_type_id,
        ticket_category_id,
        priority_id,
        ticket_data.description,
        status_id,
        ticket_data.due_date,
        ticket_data.CREATEDATE
    )

    try:
        execute_query(query, params)
        # Return the created ticket
        return get_ticket_by_number(ticket_data.ticket_number)
    except Exception as e:
        print(f"Error creating ticket: {e}")
        return None

def get_reference_id(field_name: str, label: str) -> str:
    """Get the ID for a given label in reference data"""
    field_data = REFERENCE_DATA.get(field_name, {})
    for id_val, label_val in field_data.items():
        if label_val.lower() == label.lower():
            return id_val
    # If not found, return a default or the label itself
    print(f"Warning: Could not find ID for {field_name}='{label}', using '1' as default")
    return "1"

def delete_ticket_by_number(ticket_number: str) -> bool:
    query = """
    DELETE FROM TEST_DB.PUBLIC.COMPANY_4130_DATA WHERE TICKETNUMBER = %s
    """
    execute_query(query, (ticket_number,))
    return True

# --- Technician CRUD ---
def get_all_technicians() -> List[Dict]:
    """Get all technicians"""
    query = """
    SELECT * FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
    ORDER BY NAME
    """
    results = execute_query(query)
    return results if results else []

def get_technician_by_id(technician_id: str) -> Optional[Dict]:
    """Get a technician by ID"""
    query = """
    SELECT * FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA WHERE TECHNICIAN_ID = %s
    """
    results = execute_query(query, (technician_id,))
    return results[0] if results else None

def create_technician(technician_data) -> Optional[Dict]:
    """Create a new technician"""
    query = """
    INSERT INTO TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
    (TECHNICIAN_ID, NAME, EMAIL, ROLE, SKILLS, AVAILABILITY_STATUS, CURRENT_WORKLOAD, SPECIALIZATIONS)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        technician_data.technician_id,
        technician_data.name,
        technician_data.email,
        technician_data.role,
        technician_data.skills,
        technician_data.availability_status,
        technician_data.current_workload,
        technician_data.specializations
    )

    try:
        execute_query(query, params)
        # Return the created technician
        return get_technician_by_id(technician_data.technician_id)
    except Exception as e:
        print(f"Error creating technician: {e}")
        return None

def update_technician_by_id(technician_id: str, technician_update) -> bool:
    """Update a technician by ID"""
    set_clauses = []
    params = []

    # Build dynamic update query based on provided fields
    if technician_update.name is not None:
        set_clauses.append("NAME = %s")
        params.append(technician_update.name)
    if technician_update.email is not None:
        set_clauses.append("EMAIL = %s")
        params.append(technician_update.email)
    if technician_update.role is not None:
        set_clauses.append("ROLE = %s")
        params.append(technician_update.role)
    if technician_update.skills is not None:
        set_clauses.append("SKILLS = %s")
        params.append(technician_update.skills)
    if technician_update.availability_status is not None:
        set_clauses.append("AVAILABILITY_STATUS = %s")
        params.append(technician_update.availability_status)
    if technician_update.current_workload is not None:
        set_clauses.append("CURRENT_WORKLOAD = %s")
        params.append(technician_update.current_workload)
    if technician_update.specializations is not None:
        set_clauses.append("SPECIALIZATIONS = %s")
        params.append(technician_update.specializations)

    if not set_clauses:
        return False

    params.append(technician_id)
    query = f"""
    UPDATE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
    SET {', '.join(set_clauses)}
    WHERE TECHNICIAN_ID = %s
    """

    try:
        execute_query(query, tuple(params))
        return True
    except Exception as e:
        print(f"Error updating technician: {e}")
        return False

def delete_technician_by_id(technician_id: str) -> bool:
    """Delete a technician by ID"""
    query = """
    DELETE FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA WHERE TECHNICIAN_ID = %s
    """
    try:
        execute_query(query, (technician_id,))
        return True
    except Exception as e:
        print(f"Error deleting technician: {e}")
        return False