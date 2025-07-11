# 📋 **Assignment Agent Complete Documentation**

**AutoTask Intelligent IT Support Ticket Assignment System**

---

## 📖 **Table of Contents**

1. [Overview & Architecture](#overview--architecture)
2. [Core Components](#core-components)
3. [Assignment Workflow](#assignment-workflow)
4. [AI-Powered Skill Analysis](#ai-powered-skill-analysis)
5. [Three-Tier Skill Matching](#three-tier-skill-matching)
6. [Real-Time Calendar Integration](#real-time-calendar-integration)
7. [Priority-Based Assignment Logic](#priority-based-assignment-logic)
8. [Database Integration](#database-integration)
9. [Error Handling & Fallbacks](#error-handling--fallbacks)
10. [API Reference](#api-reference)
11. [Configuration Guide](#configuration-guide)
12. [Troubleshooting](#troubleshooting)

---

## 🎯 **Overview & Architecture**

### **System Purpose**
The Assignment Agent is an **intelligent IT support ticket assignment system** that automatically assigns support tickets to the most suitable technicians based on:

- **🧠 AI-powered skill analysis** using Snowflake Cortex LLM
- **📅 Real-time calendar availability** via Google Calendar API
- **🎯 Three-tier skill matching** classification system
- **📊 Six-tier priority hierarchy** for optimal assignment decisions

### **🏗️ Architecture Components**

```
┌─────────────────────────────────────────────────────────────┐
│                    Assignment Agent                         │
├─────────────────────────────────────────────────────────────┤
│  🧠 AI Skill Analysis    │  📅 Calendar Integration        │
│  (Snowflake Cortex LLM)  │  (Google Calendar API)          │
├─────────────────────────────────────────────────────────────┤
│  🎯 Skill Matching       │  📊 Priority Assignment         │
│  (3-Tier Classification) │  (6-Tier Hierarchy)             │
├─────────────────────────────────────────────────────────────┤
│  🗄️ Database Layer       │  🛡️ Error Handling             │
│  (Snowflake)             │  (Graceful Fallbacks)           │
└─────────────────────────────────────────────────────────────┘
```

### **🎯 Design Principles**

1. **Intelligence First**: AI-powered understanding of ticket requirements
2. **Availability Priority**: Available technicians always preferred over unavailable
3. **Objective Scoring**: Mathematical skill matching eliminates bias
4. **Graceful Degradation**: System continues working even when components fail
5. **Complete Audit Trail**: Every decision is logged and traceable

---

## 🔧 **Core Components**

### **📊 Data Structures**

#### **TicketData**
```python
@dataclass
class TicketData:
    ticket_id: str          # Unique ticket identifier
    issue: str              # Brief issue description
    description: str        # Detailed problem description
    issue_type: str         # Category (Hardware, Software, Network, etc.)
    sub_issue_type: str     # Subcategory (Printer, Email, Router, etc.)
    ticket_category: str    # Business category (Support, Incident, etc.)
    priority: str           # Priority level (Low, Medium, High, Critical)
    due_date: str           # ISO format due date
    user_name: str          # Requesting user name
    user_email: str         # Requesting user email
```

#### **SkillMatchResult**
```python
@dataclass
class SkillMatchResult:
    match_percentage: int       # 0-100% skill match score
    classification: str         # "Strong" (≥70%), "Mid" (60-69%), "Weak" (<60%)
    matched_skills: List[str]   # Skills that matched
    missing_skills: List[str]   # Required skills not possessed
```

#### **AssignmentCandidate**
```python
@dataclass
class AssignmentCandidate:
    technician: TechnicianData      # Technician information
    skill_match: SkillMatchResult   # Skill matching results
    calendar_available: bool        # Real-time availability status
    priority_tier: int              # Assignment priority (1-6)
    reasoning: str                  # Human-readable assignment reasoning
```

### **🏆 Priority Tier System**

| Tier | Description | Assignment Logic |
|------|-------------|------------------|
| **1** | Available + Strong match (≥70%) | **Best possible assignment** |
| **2** | Available + Mid match (60-69%) | **Good assignment** |
| **3** | Available + Weak match (<60%) | **Acceptable assignment** |
| **4** | ~~Unavailable + Strong match~~ | **DISABLED** |
| **5** | ~~Unavailable + Mid/Weak match~~ | **DISABLED** |
| **6** | Fallback assignment | **Last resort** |

> **Note**: Tiers 4-5 are commented out per business requirements. Only available technicians are considered for assignment.

---

## 🚀 **Assignment Workflow**

### **📋 7-Step Assignment Process**

```python
def process_ticket_assignment(self, intake_output: Dict) -> Dict:
    """Main assignment workflow"""

    # Step 1: Map intake output to assignment format
    assignment_input = self.map_intake_to_assignment_format(intake_output)

    # Step 2: Validate ticket data
    ticket = self._validate_ticket_data(assignment_input)

    # Step 3: Extract required skills using Cortex LLM
    skill_analysis = self._analyze_skills_with_cortex(ticket)

    # Step 4: Get available technicians from database
    technicians = self._get_available_technicians()

    # Step 5: Evaluate all candidates with priority tiers
    candidates = self._evaluate_candidates(ticket, skill_analysis, technicians)

    # Step 6: Select best candidate using priority hierarchy
    best_candidate = self.select_best_candidate(candidates)

    # Step 7: Create and return assignment response
    return self._create_assignment_response(ticket, best_candidate)
```

### **🔍 Detailed Step Breakdown**

#### **Step 1: Data Mapping**
- Converts intake system output to standardized assignment format
- Handles different input formats and field mappings
- Validates required fields are present

#### **Step 2: Ticket Validation**
- Ensures all required fields are present and valid
- Creates typed TicketData object for type safety
- Validates priority levels and date formats

#### **Step 3: AI Skill Analysis**
- Uses Snowflake Cortex LLM (Mixtral-8x7b model)
- Analyzes ticket content to extract required skills
- Determines complexity level (1-5 scale)
- Falls back to rule-based mapping if LLM unavailable

#### **Step 4: Technician Retrieval**
- Queries Snowflake database for all technicians
- Orders by current workload for load balancing
- Parses skills and specializations from database

#### **Step 5: Candidate Evaluation**
- Calculates skill match for each technician
- Checks real-time calendar availability
- **Filters out unavailable technicians**
- Assigns priority tier based on availability + skill match

#### **Step 6: Best Candidate Selection**
- Sorts candidates by priority tier (lower = better)
- Within same tier, sorts by skill match percentage
- Logs selection reasoning and rejected candidates

#### **Step 7: Response Creation**
- Creates comprehensive assignment response
- Includes all evaluation details for audit trail
- Handles fallback assignment if no suitable candidates

---

## 🧠 **AI-Powered Skill Analysis**

### **🔍 Snowflake Cortex LLM Integration**

The system uses **Snowflake Cortex LLM** with the **Mixtral-8x7b model** for intelligent skill analysis:

```python
def _analyze_skills_with_cortex(self, ticket: TicketData) -> SkillAnalysis:
    """AI-powered ticket analysis"""

    prompt = f"""
    Analyze this IT support ticket and provide:
    1. Required technical skills (comma-separated list)
    2. Complexity level (1-5 scale where 1=basic, 5=expert)
    3. Specialized knowledge areas (comma-separated list)

    Ticket Details:
    - Issue: {ticket.issue}
    - Description: {ticket.description}
    - Issue Type: {ticket.issue_type}
    - Sub Issue Type: {ticket.sub_issue_type}

    Respond in JSON format:
    {{
        "required_skills": ["skill1", "skill2"],
        "complexity_level": 3,
        "specialized_knowledge": ["area1", "area2"]
    }}
    """

    cortex_query = f"""
    SELECT SNOWFLAKE.CORTEX.COMPLETE(
        'mixtral-8x7b',
        '{prompt}'
    ) as analysis_result
    """
```

### **🎯 AI Analysis Benefits**

- **🧠 Context Understanding**: Interprets natural language descriptions
- **📊 Nuanced Analysis**: Understands technical complexity and requirements
- **🔄 Consistent Output**: Structured JSON format for reliable parsing
- **⚡ Single Query**: Gets all analysis data in one LLM call

### **🛡️ Fallback Strategy**

If LLM analysis fails, the system uses **rule-based skill mapping**:

```python
fallback_skill_mapping = {
    'Hardware': ['Hardware troubleshooting', 'Component replacement'],
    'Software': ['Software installation', 'Application support'],
    'Network': ['Network configuration', 'Connectivity troubleshooting'],
    'Email': ['Email server management', 'Exchange administration'],
    'Security': ['Security protocols', 'Access management']
}
```

---

## 🎯 **Three-Tier Skill Matching**

### **📊 Skill Match Calculation**

The system implements a **sophisticated fuzzy matching algorithm** that handles variations in skill naming:

```python
def calculate_skill_match(self, required_skills: List[str], technician_skills: List[str]) -> SkillMatchResult:
    """Three-tier skill matching with fuzzy logic"""

    matched_skills = []
    missing_skills = []

    # Fuzzy matching logic
    for required_skill in required_skills:
        skill_matched = False
        required_lower = required_skill.lower()

        for tech_skill in technician_skills:
            tech_lower = tech_skill.lower()
            # Multiple matching strategies
            if (required_lower in tech_lower or          # Partial match
                tech_lower in required_lower or          # Reverse partial
                required_lower == tech_lower):           # Exact match
                matched_skills.append(required_skill)
                skill_matched = True
                break

        if not skill_matched:
            missing_skills.append(required_skill)

    # Calculate percentage and classify
    match_percentage = int((len(matched_skills) / len(required_skills)) * 100)

    # Three-tier classification
    if match_percentage >= 70:
        classification = "Strong"    # Tier 1 - Excellent match
    elif match_percentage >= 60:
        classification = "Mid"       # Tier 2 - Good match
    else:
        classification = "Weak"      # Tier 3 - Basic match

    return SkillMatchResult(
        match_percentage=match_percentage,
        classification=classification,
        matched_skills=matched_skills,
        missing_skills=missing_skills
    )
```

### **🔍 Matching Examples**

| Required Skill | Technician Skill | Match Type | Result |
|----------------|------------------|------------|---------|
| "Windows troubleshooting" | "Windows Server" | Partial | ✅ Match |
| "Exchange" | "Exchange Server 2019" | Partial | ✅ Match |
| "Network configuration" | "Network" | Reverse partial | ✅ Match |
| "Python scripting" | "Python" | Partial | ✅ Match |
| "VMware" | "Linux administration" | No match | ❌ No match |

### **📊 Classification Thresholds**

- **Strong Match (≥70%)**: Technician has most required skills
- **Mid Match (60-69%)**: Technician has majority of required skills
- **Weak Match (<60%)**: Technician has some required skills

---

## 📅 **Real-Time Calendar Integration**

### **🔍 Google Calendar API Integration**

The system integrates with **Google Calendar API** for real-time availability checking:

```python
def check_calendar_availability(self, technician_email: str, due_date: str) -> bool:
    """Real-time calendar availability checking"""

    # Parse and validate due date
    due_datetime = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)

    # Ensure timezone awareness for global teams
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    if due_datetime.tzinfo is None:
        due_datetime = due_datetime.replace(tzinfo=timezone.utc)

    # Format for Google Calendar API (RFC3339)
    time_min = now.isoformat().replace('+00:00', 'Z')
    time_max = due_datetime.isoformat().replace('+00:00', 'Z')

    # FreeBusy query to check availability
    freebusy_query = {
        'timeMin': time_min,
        'timeMax': time_max,
        'items': [{'id': technician_email}]
    }

    # Execute API call
    freebusy_result = self.calendar_service.freebusy().query(body=freebusy_query).execute()

    # Parse results
    calendars = freebusy_result.get('calendars', {})
    technician_calendar = calendars.get(technician_email, {})
    busy_periods = technician_calendar.get('busy', [])

    if busy_periods:
        logger.info(f"Technician {technician_email} has {len(busy_periods)} busy periods")
        return False  # Unavailable
    else:
        return True   # Available
```

### **🔧 Calendar Setup Requirements**

1. **Service Account**: Google Cloud service account with Calendar API access
2. **Calendar Sharing**: Technician calendars shared with service account email
3. **Permissions**: "See all event details" permission level
4. **Credentials**: Service account JSON key file

### **📊 Calendar Integration Benefits**

- **⏰ Real-Time Data**: Checks actual calendar events, not cached status
- **🌍 Global Support**: Proper timezone handling for distributed teams
- **🔄 Non-Blocking**: If calendar unavailable, assumes available (graceful degradation)
- **📋 Audit Trail**: Logs busy periods for debugging and compliance
- **⚡ Efficient**: Single FreeBusy query checks entire time period

### **🛡️ Error Handling**

```python
try:
    # Calendar API call
    freebusy_result = self.calendar_service.freebusy().query(body=freebusy_query).execute()
    # Process results...
except HttpError as e:
    logger.error(f"Google Calendar API error for {technician_email}: {e}")
    return True  # Assume available on error (non-blocking)
except Exception as e:
    logger.error(f"Calendar availability check failed for {technician_email}: {str(e)}")
    return True  # Graceful fallback
```

---

## 🏆 **Priority-Based Assignment Logic**

### **📊 Six-Tier Priority System**

The assignment logic follows a **strict hierarchy** where availability always takes precedence:

```python
def _determine_priority_tier(self, calendar_available: bool, skill_classification: str) -> int:
    """Determine priority tier based on availability and skill match"""

    if calendar_available:
        if skill_classification == "Strong":
            return 1  # Available + Strong match (≥70%) - BEST
        elif skill_classification == "Mid":
            return 2  # Available + Mid match (60-69%) - GOOD
        else:  # Weak
            return 3  # Available + Weak match (<60%) - ACCEPTABLE
    else:
        # Unavailable technicians are filtered out
        return 6  # Treat as fallback tier (excluded from selection)
```

### **🎯 Selection Algorithm**

```python
def select_best_candidate(self, candidates: List[AssignmentCandidate]) -> Optional[AssignmentCandidate]:
    """Select best candidate using strict priority hierarchy"""

    # Sort by priority tier (lower = higher priority), then by skill match percentage
    sorted_candidates = sorted(candidates,
                             key=lambda c: (c.priority_tier, -c.skill_match.match_percentage))

    best_candidate = sorted_candidates[0]

    # Log selection with complete reasoning
    logger.info(f"Selected candidate: {best_candidate.technician.name} "
               f"(Tier {best_candidate.priority_tier}: {self.priority_tiers[best_candidate.priority_tier]})")

    # Log all rejected candidates for audit trail
    for candidate in sorted_candidates[1:]:
        logger.info(f"Rejected candidate: {candidate.technician.name} - "
                   f"Tier {candidate.priority_tier}, {candidate.skill_match.classification} match "
                   f"({candidate.skill_match.match_percentage}%), Available: {candidate.calendar_available}")

    return best_candidate
```

### **📋 Assignment Decision Examples**

| Scenario | Technician A | Technician B | Winner | Reason |
|----------|--------------|--------------|---------|---------|
| **Availability vs Skill** | Unavailable, 95% match | Available, 45% match | **B** | Availability priority |
| **Same Tier** | Available, 85% match | Available, 72% match | **A** | Higher skill match |
| **Different Tiers** | Available, 65% match | Available, 55% match | **A** | Tier 2 beats Tier 3 |

---

## 🗄️ **Database Integration**

### **📊 Technician Data Retrieval**

The system queries **Snowflake database** for technician information:

```sql
SELECT
    TECHNICIAN_ID,
    NAME,
    EMAIL,
    ROLE,
    SKILLS,
    CURRENT_WORKLOAD,
    SPECIALIZATIONS
FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
ORDER BY CURRENT_WORKLOAD ASC, NAME ASC
```

### **🔧 Data Processing**

```python
def _get_available_technicians(self) -> List[Dict]:
    """Query and process technician data"""

    # Execute query and process results
    for row in results:
        # Parse skills (handles both JSON and CSV formats)
        skills_raw = str(row[4]) if row[4] else ""
        if skills_raw.startswith('[') and skills_raw.endswith(']'):
            skills = json.loads(skills_raw)  # JSON format: ["skill1", "skill2"]
        else:
            skills = [s.strip() for s in skills_raw.split(',')]  # CSV format: "skill1, skill2"

        # Parse specializations similarly
        specializations_raw = str(row[6]) if row[6] else ""
        # ... similar parsing logic

        technician_dict = {
            'technician_id': str(row[0]),
            'name': str(row[1]),
            'email': str(row[2]),
            'role': str(row[3]),
            'skills': skills,
            'current_workload': int(row[5]),
            'specializations': specializations
        }
```

### **📋 Database Schema Changes**

**Removed Columns** (as per requirements):
- `MAX_WORKLOAD` - No longer used for capacity planning
- `AVAILABILITY_STATUS` - Replaced with real-time calendar checking

**Current Schema**:
- `TECHNICIAN_ID` - Unique identifier
- `NAME` - Technician full name
- `EMAIL` - Email address (used for calendar integration)
- `ROLE` - Job role/title
- `SKILLS` - Technical skills (JSON array or CSV)
- `CURRENT_WORKLOAD` - Current number of assigned tickets
- `SPECIALIZATIONS` - Areas of expertise (JSON array or CSV)

---

## 🛡️ **Error Handling & Fallbacks**

### **🔄 Multi-Layer Error Strategy**

The system implements **comprehensive error handling** at every level:

#### **1. Component-Level Fallbacks**

```python
# Calendar API Fallback
try:
    calendar_available = self.check_calendar_availability(email, due_date)
except Exception as e:
    logger.error(f"Calendar check failed: {e}")
    calendar_available = True  # Assume available on error

# LLM Analysis Fallback
try:
    skill_analysis = self._analyze_skills_with_cortex(ticket)
except Exception as e:
    logger.error(f"Cortex analysis failed: {e}")
    skill_analysis = self._fallback_skill_analysis(ticket)  # Rule-based fallback

# Database Query Fallback
try:
    technicians = self._get_available_technicians()
except Exception as e:
    logger.error(f"Database query failed: {e}")
    return self._create_fallback_assignment(ticket)
```

#### **2. System-Level Fallbacks**

```python
# No suitable candidates found
if not candidates:
    logger.warning("No valid candidates found, proceeding with fallback assignment")
    return self._create_assignment_response(ticket, None, is_fallback=True)

# Complete system failure
except Exception as e:
    error_msg = f"Assignment process failed: {str(e)}"
    logger.error(error_msg)
    return {
        'assignment_result': {
            'ticket_id': ticket.ticket_id,
            'assigned_technician': 'Fallback Assignment',
            'technician_email': 'fallback@company.com',
            'status': 'Fallback',
            'error': error_msg
        }
    }
```

### **📊 Error Categories & Responses**

| Error Type | Response Strategy | Business Impact |
|------------|------------------|-----------------|
| **Calendar API Down** | Assume all available | Assignments continue |
| **LLM Unavailable** | Use rule-based skills | Reduced accuracy |
| **Database Error** | Fallback assignment | Tickets still assigned |
| **No Candidates** | Fallback assignment | Manual intervention needed |
| **System Failure** | Error response + fallback | Graceful degradation |

### **🔍 Comprehensive Logging**

```python
# Success logging
logger.info(f"Successfully assigned ticket {ticket.ticket_id} to {technician.name}")
logger.info(f"Selection reasoning: {candidate.reasoning}")

# Error logging with context
logger.error(f"Google Calendar API error for {email}: {error_details}")
logger.warning(f"Technician {name} evaluation failed: {str(e)}")

# Performance logging
logger.info(f"Retrieved {len(technicians)} technicians from database")
logger.info(f"Evaluated {len(candidates)} candidates for ticket {ticket_id}")
```

---

## 📚 **API Reference**

### **🔧 Main Functions**

#### **assign_ticket()**
```python
def assign_ticket(ticket_data: Dict, db_connection,
                 google_calendar_credentials_path: Optional[str] = None) -> Dict:
    """
    Public function to assign a ticket to a technician

    Args:
        ticket_data (Dict): Ticket information in required JSON format
        db_connection: Snowflake database connection
        google_calendar_credentials_path: Path to Google Calendar credentials

    Returns:
        Dict: Complete assignment result with technician details

    Example:
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

        result = assign_ticket(ticket_data, db_connection, calendar_path)
    """
```

#### **process_ticket_assignment()**
```python
def process_ticket_assignment(self, intake_output: Dict) -> Dict:
    """
    Main method to process ticket assignment from intake/classification output

    Args:
        intake_output (Dict): Output from intake and classification process

    Returns:
        Dict: Assignment result with complete technician details

    Raises:
        AssignmentError: If assignment process fails completely
    """
```

### **🔍 Utility Functions**

#### **calculate_skill_match()**
```python
def calculate_skill_match(self, required_skills: List[str],
                         technician_skills: List[str]) -> SkillMatchResult:
    """
    Calculate skill match with three-tier classification

    Args:
        required_skills: Skills required for the ticket
        technician_skills: Skills possessed by the technician

    Returns:
        SkillMatchResult: Match percentage, classification, and skill details
    """
```

#### **check_calendar_availability()**
```python
def check_calendar_availability(self, technician_email: str, due_date: str) -> bool:
    """
    Check technician availability using Google Calendar API

    Args:
        technician_email: Email address of the technician
        due_date: Due date of the ticket (ISO format)

    Returns:
        bool: True if available before due date, False if busy
    """
```

### **📊 Response Format**

```python
{
    'assignment_result': {
        'ticket_id': 'TKT-2024-001',
        'assigned_technician': 'John Smith',
        'technician_email': 'john.smith@company.com',
        'technician_id': 'TECH-001',
        'assignment_date': '2024-07-11',
        'assignment_time': '14:30:15',
        'priority': 'Critical',
        'issue_type': 'Email',
        'sub_issue_type': 'Exchange',
        'ticket_category': 'Infrastructure',
        'user_name': 'Jane Doe',
        'user_email': 'jane.doe@company.com',
        'due_date': '2024-07-15',
        'status': 'Assigned',
        'assignment_tier': 1,
        'skill_match_percentage': 85,
        'skill_match_classification': 'Strong',
        'calendar_available': True,
        'matched_skills': ['Email server management', 'Exchange administration'],
        'missing_skills': [],
        'reasoning': 'Technician: John Smith, Skill Match: Strong (85%), Available: True, Current Workload: 3, Matched Skills: [Email server management, Exchange administration]'
    }
}
```

---

## ⚙️ **Configuration Guide**

### **🔧 Environment Setup**

#### **1. Snowflake Configuration**
```python
# Required environment variables
SNOWFLAKE_ACCOUNT=your_account.region
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=TEST_DB
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_ROLE=your_role
```

#### **2. Google Calendar Setup**

**Step 1: Create Service Account**
1. Go to Google Cloud Console
2. Create new project or select existing
3. Enable Google Calendar API
4. Create service account
5. Download JSON credentials file

**Step 2: Share Calendars**
1. Open Google Calendar
2. Find technician calendar
3. Click Settings and sharing
4. Add service account email
5. Set permission: "See all event details"

**Step 3: Configure Credentials Path**
```python
google_calendar_credentials_path = "/path/to/service-account-key.json"
```

### **📊 Database Schema Setup**

```sql
-- Create technician table
CREATE TABLE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA (
    TECHNICIAN_ID VARCHAR(50) PRIMARY KEY,
    NAME VARCHAR(100) NOT NULL,
    EMAIL VARCHAR(100) NOT NULL UNIQUE,
    ROLE VARCHAR(50),
    SKILLS VARIANT,  -- JSON array or CSV string
    CURRENT_WORKLOAD INTEGER DEFAULT 0,
    SPECIALIZATIONS VARIANT  -- JSON array or CSV string
);

-- Sample data
INSERT INTO TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA VALUES
('TECH-001', 'John Smith', 'john.smith@company.com', 'Senior Technician',
 '["Windows Server", "Exchange", "Active Directory"]', 3,
 '["Email Systems", "Windows Infrastructure"]'),
('TECH-002', 'Jane Doe', 'jane.doe@company.com', 'Network Specialist',
 '["Cisco", "Network Configuration", "Firewall"]', 2,
 '["Network Security", "Routing"]');
```

### **🔍 Logging Configuration**

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('assignment_agent.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('assignment_agent')
```

---

## 🔧 **Troubleshooting**

### **❌ Common Issues & Solutions**

#### **1. Calendar Integration Issues**

**Problem**: `Google Calendar API error: Bad Request`
```
ERROR:src.agents.assignment_agent:Google Calendar API error for user@company.com: <HttpError 400...>
```

**Solutions**:
- ✅ Verify service account has calendar access
- ✅ Check calendar sharing permissions
- ✅ Ensure credentials file path is correct
- ✅ Validate datetime formatting (ISO 8601 with timezone)

**Problem**: `Calendar service not initialized`
```
WARNING:src.agents.assignment_agent:Google Calendar integration not available
```

**Solutions**:
- ✅ Install required packages: `pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client`
- ✅ Verify credentials file exists and is readable
- ✅ Check service account permissions

#### **2. Database Connection Issues**

**Problem**: `No active Snowflake connection available`
```
ERROR:src.agents.assignment_agent:No active Snowflake connection available
```

**Solutions**:
- ✅ Verify Snowflake credentials
- ✅ Check network connectivity
- ✅ Ensure database and schema exist
- ✅ Validate user permissions

**Problem**: `Error retrieving technician data`
```
ERROR:src.agents.assignment_agent:Error retrieving technician data: Table not found
```

**Solutions**:
- ✅ Create TECHNICIAN_DUMMY_DATA table
- ✅ Verify table schema matches expected format
- ✅ Check user has SELECT permissions
- ✅ Ensure data is properly formatted (JSON/CSV)

#### **3. Skill Analysis Issues**

**Problem**: `Cortex analysis failed`
```
ERROR:src.agents.assignment_agent:Cortex analysis failed: Model not available
```

**Solutions**:
- ✅ Verify Snowflake Cortex is enabled
- ✅ Check model availability (mixtral-8x7b)
- ✅ Validate user permissions for Cortex functions
- ✅ System will use fallback rule-based analysis

#### **4. Assignment Logic Issues**

**Problem**: `No valid candidates found`
```
WARNING:src.agents.assignment_agent:No valid candidates found, proceeding with fallback assignment
```

**Solutions**:
- ✅ Check if all technicians are marked unavailable
- ✅ Verify calendar integration is working
- ✅ Review skill matching thresholds
- ✅ Add more technicians to database

### **📊 Debugging Tools**

#### **Enable Debug Logging**
```python
logging.getLogger('assignment_agent').setLevel(logging.DEBUG)
```

#### **Test Individual Components**
```python
# Test calendar integration
agent = AssignmentAgentIntegration(db_connection, calendar_path)
available = agent.check_calendar_availability('test@company.com', '2024-07-15')
print(f"Available: {available}")

# Test skill matching
skills_required = ['Windows', 'Exchange']
skills_tech = ['Windows Server', 'Exchange 2019', 'Active Directory']
match_result = agent.calculate_skill_match(skills_required, skills_tech)
print(f"Match: {match_result.match_percentage}% ({match_result.classification})")
```

#### **Validate Database Connection**
```python
# Test database query
technicians = agent._get_available_technicians()
print(f"Found {len(technicians)} technicians")
for tech in technicians:
    print(f"- {tech['name']}: {tech['skills']}")
```

### **📋 Performance Monitoring**

#### **Key Metrics to Monitor**
- Assignment response time
- Calendar API call success rate
- Database query performance
- LLM analysis success rate
- Fallback assignment frequency

#### **Log Analysis Queries**
```bash
# Count assignments by tier
grep "Selected candidate" assignment_agent.log | grep -o "Tier [0-9]" | sort | uniq -c

# Calendar API errors
grep "Google Calendar API error" assignment_agent.log | wc -l

# Fallback assignments
grep "Fallback assignment" assignment_agent.log | wc -l
```

---

## 🎯 **Best Practices**

### **🔧 Implementation Guidelines**

1. **Always Use Type Hints**: Ensures code reliability and IDE support
2. **Comprehensive Error Handling**: Every external call should have try/catch
3. **Detailed Logging**: Log both success and failure cases with context
4. **Graceful Degradation**: System should continue working when components fail
5. **Single Responsibility**: Each function should have one clear purpose

### **📊 Performance Optimization**

1. **Database Queries**: Order by workload for load balancing
2. **Calendar API**: Use single FreeBusy query instead of multiple calls
3. **Early Filtering**: Remove unavailable technicians before detailed evaluation
4. **Caching**: Consider caching technician data for high-volume scenarios

### **🛡️ Security Considerations**

1. **Credential Management**: Store credentials securely, never in code
2. **API Rate Limits**: Implement rate limiting for external API calls
3. **Data Validation**: Validate all input data before processing
4. **Audit Trail**: Log all assignment decisions for compliance

---

## 📈 **Future Enhancements**

### **🧠 AI/ML Improvements**
- Machine learning model for assignment optimization
- Historical assignment success rate analysis
- Predictive workload balancing
- Natural language processing for ticket similarity

### **📊 Analytics & Reporting**
- Assignment performance dashboards
- Technician utilization reports
- Skill gap analysis
- Customer satisfaction correlation

### **🔧 System Enhancements**
- Multi-tenant support for different organizations
- Real-time assignment notifications
- Integration with additional calendar systems
- Advanced scheduling and resource planning

---

## 📞 **Support & Contact**

For technical support or questions about the Assignment Agent:

- **Documentation**: This comprehensive guide
- **Logs**: Check `assignment_agent.log` for detailed operation logs
- **Testing**: Use provided test scripts to validate functionality
- **Monitoring**: Monitor key metrics for system health

---

**© 2024 AutoTask Assignment Agent - Intelligent IT Support Ticket Assignment System**

*This documentation covers the complete Assignment Agent system. For updates and additional resources, refer to the project repository.*
```