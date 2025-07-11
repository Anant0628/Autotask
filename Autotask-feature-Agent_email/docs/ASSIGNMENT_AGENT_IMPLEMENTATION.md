# Assignment Agent Implementation Guide

## Overview

The Assignment Agent has been completely redesigned to meet the detailed requirements for an intelligent IT support ticket assignment system. This implementation provides:

- **Modular Architecture**: Five required functions as specified
- **Snowflake Cortex LLM Integration**: For intelligent skill inference
- **Google Calendar API Integration**: For real-time availability checking
- **Three-Tier Skill Classification**: Strong (≥70%), Mid (60-69%), Weak (<60%)
- **Strict Priority Hierarchy**: Six-tier assignment system
- **Comprehensive Logging**: Full audit trail of assignment decisions

## Required Input Format

The agent expects ticket data in this exact JSON format:

```json
{
  "ticket_id": "TKT-2024-001",
  "issue": "Email server down",
  "description": "Users cannot send or receive emails...",
  "issue_type": "Email",
  "sub_issue_type": "Exchange",
  "ticket_category": "Infrastructure",
  "priority": "Critical",
  "due_date": "2024-07-15",
  "user_name": "Jane Doe",
  "user_email": "jane.doe@company.com"
}
```

## Modular Functions (As Required)

### 1. `extract_required_skills(ticket_data: Dict) -> List[str]`
- Uses Snowflake Cortex LLM for skill inference
- Analyzes issue_type, sub_issue_type, ticket_category, description, and priority
- Returns array of required technical skills
- Includes fallback mechanism for LLM failures

### 2. `get_technician_data() -> List[Dict]`
- Queries `TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA`
- Returns all required fields: technician_id, name, role, skills, email, current_workload, specializations
- Handles JSON and comma-separated skill formats
- Comprehensive error handling
- **Note**: max_workload and availability_status columns removed from database schema
- **Availability**: Now checked dynamically via Google Calendar API instead of static database field

### 3. `calculate_skill_match(required_skills: List[str], technician_skills: List[str]) -> SkillMatchResult`
- Implements three-tier classification system:
  - **Strong**: ≥70% skill match
  - **Mid**: 60-69% skill match
  - **Weak**: <60% skill match
- Returns detailed match analysis with matched/missing skills

### 4. `check_calendar_availability(technician_email: str, due_date: str) -> bool`
- Integrates with Google Calendar API
- Uses `freeBusy.query` method as specified
- Checks availability from now until ticket due date
- Graceful fallback when calendar service unavailable

### 5. `select_best_candidate(candidates: List[AssignmentCandidate]) -> Optional[AssignmentCandidate]`
- Implements modified priority hierarchy (Tiers 4-5 commented out):
  1. Available + Strong match (≥70%)
  2. Available + Mid match (60-69%)
  3. Available + Weak match (<60%)
  ~~4. Unavailable + Strong match~~ (COMMENTED OUT)
  ~~5. Unavailable + Mid/Weak match~~ (COMMENTED OUT)
  6. Fallback assignment
- Only considers available technicians for assignment
- Logs all assignment decisions and rejected candidates

## Database Schema Requirements

The implementation expects `TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA` with these columns:

```sql
CREATE TABLE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA (
    TECHNICIAN_ID VARCHAR,
    NAME VARCHAR,
    EMAIL VARCHAR,
    ROLE VARCHAR,
    SKILLS VARCHAR,  -- JSON array or comma-separated
    CURRENT_WORKLOAD INTEGER,
    SPECIALIZATIONS VARCHAR  -- JSON array or comma-separated
);
```

**Important Changes**:
- ❌ **`MAX_WORKLOAD`** column removed from schema
- ❌ **`AVAILABILITY_STATUS`** column removed from schema
- ✅ **Availability** now checked dynamically via Google Calendar API
- ✅ **Real-time availability** instead of static database field

## Google Calendar Setup

1. Create a Google Cloud Project
2. Enable Google Calendar API
3. Create a Service Account
4. Download credentials JSON file
5. Share calendars with service account email
6. Pass credentials path to agent initialization

## Assignment Priority Hierarchy (Modified)

The system follows this hierarchy with Tiers 4-5 commented out:

| Tier | Criteria | Description | Status |
|------|----------|-------------|---------|
| 1 | Available + Strong (≥70%) | Best possible match | ✅ Active |
| 2 | Available + Mid (60-69%) | Good match, available | ✅ Active |
| 3 | Available + Weak (<60%) | Available but limited skills | ✅ Active |
| ~~4~~ | ~~Unavailable + Strong~~ | ~~Expert but busy~~ | ❌ Commented Out |
| ~~5~~ | ~~Unavailable + Mid/Weak~~ | ~~Limited availability and skills~~ | ❌ Commented Out |
| 6 | Fallback | No suitable technician found | ✅ Active |

**Note**: Unavailable technicians are now filtered out during candidate evaluation and will not be considered for assignment.

## Output Format

### Successful Assignment
```json
{
  "assignment_result": {
    "ticket_id": "TKT-2024-001",
    "assigned_technician": "John Smith",
    "technician_email": "john.smith@company.com",
    "technician_id": "TECH-001",
    "assignment_date": "2024-07-10",
    "assignment_time": "14:30:00",
    "priority": "Critical",
    "issue_type": "Email",
    "sub_issue_type": "Exchange",
    "ticket_category": "Infrastructure",
    "user_name": "Jane Doe",
    "user_email": "jane.doe@company.com",
    "due_date": "2024-07-15",
    "status": "Assigned",
    "assignment_tier": 1,
    "skill_match_percentage": 85,
    "skill_match_classification": "Strong",
    "calendar_available": true,
    "matched_skills": ["Exchange Server", "Email Configuration"],
    "missing_skills": [],
    "reasoning": "Technician: John Smith, Skill Match: Strong (85%), Available: true..."
  }
}
```

### Fallback Assignment
```json
{
  "assignment_result": {
    "ticket_id": "TKT-2024-001",
    "assigned_technician": "Fallback Support",
    "technician_email": "fallback@company.com",
    "assignment_tier": 6,
    "skill_match_percentage": 0,
    "reasoning": "No suitable technician found, assigned to fallback",
    "status": "Assigned (Fallback)"
  }
}
```

## Usage Example

```python
from src.agents.assignment_agent import assign_ticket

# Ticket data in required format
ticket_data = {
    "ticket_id": "TKT-2024-001",
    "issue": "Email server down",
    "description": "Users cannot send or receive emails...",
    "issue_type": "Email",
    "sub_issue_type": "Exchange",
    "ticket_category": "Infrastructure",
    "priority": "Critical",
    "due_date": "2024-07-15",
    "user_name": "Jane Doe",
    "user_email": "jane.doe@company.com"
}

# Assign ticket
result = assign_ticket(
    ticket_data=ticket_data,
    db_connection=snowflake_connection,
    google_calendar_credentials_path="path/to/credentials.json"
)

print(f"Assigned to: {result['assignment_result']['assigned_technician']}")
```

## Error Handling

The implementation includes comprehensive error handling:

- **Database Connection Failures**: Graceful fallback to escalation
- **LLM Service Failures**: Fallback skill mapping based on issue type
- **Calendar API Failures**: Assumes availability to avoid blocking
- **Invalid Input Data**: Detailed validation with specific error messages
- **Missing Technicians**: Automatic fallback assignment

## Logging and Audit Trail

All assignment decisions are logged with:
- Skill analysis results
- Calendar availability checks
- Candidate evaluation details
- Assignment reasoning
- Rejected candidates with reasons
- Fallback scenarios

## Dependencies Added

The following dependencies have been added to `requirements.txt`:

```
google-auth>=2.0.0
google-auth-oauthlib>=0.5.0
google-auth-httplib2>=0.1.0
google-api-python-client>=2.0.0
```

## Integration Notes

1. **Backward Compatibility**: The agent maintains compatibility with existing intake/classification workflow
2. **Modular Design**: Each required function can be used independently
3. **Extensible**: Easy to add new assignment criteria or modify priority hierarchy
4. **Production Ready**: Includes proper error handling, logging, and fallback mechanisms

## Testing

Run the test function to verify implementation:

```bash
cd Autotask-feature-Agent_email
python -m src.agents.assignment_agent
```

This will display the available modular functions and assignment hierarchy without requiring database connection.
