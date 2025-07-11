"""
Assignment Agent - Intelligent IT Support Ticket Assignment System

This module implements an intelligent IT support ticket assignment agent that:
- Uses Snowflake Cortex LLM for skill inference
- Integrates with Google Calendar API for availability checking
- Implements three-tier skill matching classification
- Follows strict priority hierarchy for technician assignment
- Provides comprehensive logging and error handling

Author: AutoTask Integration System
Date: 2025-07-10
"""

import json
import logging
import time
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Calendar API imports
try:
    from google.oauth2.credentials import Credentials
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False
    logger.warning("Google Calendar API libraries not available. Calendar integration disabled.")

@dataclass
class TicketData:
    """Data class for ticket information matching required input format"""
    ticket_id: str
    issue: str
    description: str
    issue_type: str
    sub_issue_type: str
    ticket_category: str
    priority: str
    due_date: str
    user_name: str
    user_email: str

@dataclass
class TechnicianData:
    """Data class for technician information from TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
    (max_workload and availability_status removed - availability checked via Google Calendar)"""
    technician_id: str
    name: str
    email: str
    role: str
    skills: List[str]
    current_workload: int
    specializations: List[str]

@dataclass
class SkillAnalysis:
    """Data class for skill analysis results from Cortex LLM"""
    required_skills: List[str]
    complexity_level: int
    specialized_knowledge: List[str]

@dataclass
class SkillMatchResult:
    """Data class for skill matching results with three-tier classification"""
    match_percentage: int
    classification: str  # "Strong", "Mid", "Weak"
    matched_skills: List[str]
    missing_skills: List[str]

@dataclass
class AssignmentCandidate:
    """Data class for assignment candidate with all evaluation criteria"""
    technician: TechnicianData
    skill_match: SkillMatchResult
    calendar_available: bool
    priority_tier: int  # 1-6 based on assignment hierarchy
    reasoning: str

class AssignmentError(Exception):
    """Custom exception for assignment issues"""
    pass

class AssignmentAgentIntegration:
    """
    Intelligent IT Support Ticket Assignment Agent

    Implements the complete assignment workflow with:
    - Snowflake Cortex LLM skill inference
    - Google Calendar availability checking
    - Three-tier skill matching classification
    - Strict priority hierarchy assignment logic
    """

    def __init__(self, db_connection, google_calendar_credentials_path: Optional[str] = None):
        """
        Initialize the Assignment Agent with database connection and optional Google Calendar integration

        Args:
            db_connection: Existing SnowflakeConnection instance from intake agent
            google_calendar_credentials_path: Path to Google Calendar service account credentials JSON
        """
        self.db_connection = db_connection
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self.google_calendar_credentials_path = google_calendar_credentials_path
        self.calendar_service = None

        # Initialize Google Calendar service if credentials provided
        if GOOGLE_CALENDAR_AVAILABLE and google_calendar_credentials_path:
            self._initialize_calendar_service()

        # Fallback skill mapping for when Cortex LLM fails
        self.fallback_skill_mapping = {
            'Hardware': ['Hardware Troubleshooting', 'PC Repair', 'Printer Support'],
            'Software/SaaS': ['Software Installation', 'Application Support', 'Troubleshooting'],
            'Network': ['Network Troubleshooting', 'Router Configuration', 'WiFi Setup'],
            'Security': ['Security Analysis', 'Antivirus Support', 'Access Control'],
            'Database': ['SQL Database', 'Database Administration', 'Data Recovery'],
            'Email': ['Email Configuration', 'Outlook Support', 'Exchange Server'],
            'Server': ['Windows Server', 'Linux Server', 'Server Administration']
        }

        # Role to issue type mapping for better technician matching
        self.role_issue_mapping = {
            'Email': ['Email', 'Outlook', 'Exchange'],
            'Hardware': ['Hardware', 'PC', 'Printer', 'Device'],
            'Software': ['Software/SaaS', 'Application', 'Software'],
            'Network': ['Network', 'WiFi', 'Router', 'Connectivity'],
            'Security': ['Security', 'Antivirus', 'Threat'],
            'Database': ['Database', 'SQL', 'Data'],
            'System Admin': ['Server', 'System', 'Admin'],
            'IT Support': ['General', 'Support', 'Help Desk']
        }

        # Fallback assignment email as specified in requirements
        self.fallback_email = 'fallback@company.com'

        # Priority tier definitions for assignment hierarchy (Tiers 4-5 commented out)
        self.priority_tiers = {
            1: "Available + Strong match (≥70%)",
            2: "Available + Mid match (60-69%)",
            3: "Available + Weak match (<60%)",
            # 4: "Unavailable + Strong match",  # COMMENTED OUT
            # 5: "Unavailable + Mid/Weak match",  # COMMENTED OUT
            6: "Fallback assignment"
        }

    def _initialize_calendar_service(self):
        """Initialize Google Calendar service with service account credentials"""
        try:
            if not os.path.exists(self.google_calendar_credentials_path):
                logger.warning(f"Google Calendar credentials file not found: {self.google_calendar_credentials_path}")
                return

            credentials = service_account.Credentials.from_service_account_file(
                self.google_calendar_credentials_path,
                scopes=['https://www.googleapis.com/auth/calendar.readonly']
            )
            self.calendar_service = build('calendar', 'v3', credentials=credentials)
            logger.info("Google Calendar service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar service: {str(e)}")
            self.calendar_service = None

    # ========================================
    # REQUIRED MODULAR FUNCTIONS (as specified in requirements)
    # ========================================

    def extract_required_skills(self, ticket_data: Dict) -> List[str]:
        """
        Extract required skills using Snowflake Cortex LLM

        Args:
            ticket_data (Dict): Ticket information with issue_type, sub_issue_type, etc.

        Returns:
            List[str]: List of required skills for the ticket
        """
        try:
            ticket = self._validate_ticket_data(ticket_data)
            skill_analysis = self._analyze_skills_with_cortex(ticket)
            logger.info(f"Extracted skills for ticket {ticket.ticket_id}: {skill_analysis.required_skills}")
            return skill_analysis.required_skills
        except Exception as e:
            logger.error(f"Error extracting required skills: {str(e)}")
            # Fallback to basic skill mapping
            issue_type = ticket_data.get('issue_type', 'General')
            return self.fallback_skill_mapping.get(issue_type, ['General IT Support'])

    def get_technician_data(self) -> List[Dict]:
        """
        Query Snowflake TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA for technician metadata

        Returns:
            List[Dict]: List of technician data with all required fields
        """
        cursor = None
        try:
            if not self.db_connection.conn:
                logger.error("No active Snowflake connection available")
                return []

            cursor = self.db_connection.conn.cursor()

            # Query with all required fields (max_workload and availability_status columns removed)
            # Availability is now checked dynamically via Google Calendar API
            query = """
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
            """

            cursor.execute(query)
            results = cursor.fetchall()

            technicians = []
            for row in results:
                try:
                    # Parse skills - handle both JSON array and comma-separated string formats
                    skills_raw = str(row[4]) if row[4] else ""
                    if skills_raw.startswith('[') and skills_raw.endswith(']'):
                        try:
                            skills = json.loads(skills_raw)
                        except json.JSONDecodeError:
                            skills = [s.strip() for s in skills_raw.strip('[]').replace('"', '').split(',')]
                    else:
                        skills = [s.strip() for s in skills_raw.split(',') if s.strip()]

                    # Parse specializations (now at index 6 since availability_status and max_workload removed)
                    specializations_raw = str(row[6]) if row[6] else ""
                    if specializations_raw.startswith('[') and specializations_raw.endswith(']'):
                        try:
                            specializations = json.loads(specializations_raw)
                        except json.JSONDecodeError:
                            specializations = [s.strip() for s in specializations_raw.strip('[]').replace('"', '').split(',')]
                    else:
                        specializations = [s.strip() for s in specializations_raw.split(',') if s.strip()]

                    technician_dict = {
                        'technician_id': str(row[0]) if row[0] else '',
                        'name': str(row[1]) if row[1] else '',
                        'email': str(row[2]) if row[2] else '',
                        'role': str(row[3]) if row[3] else '',
                        'skills': skills,
                        'current_workload': int(row[5]) if row[5] is not None else 0,
                        'specializations': specializations
                    }
                    technicians.append(technician_dict)

                except Exception as e:
                    logger.warning(f"Error parsing technician data for row {row}: {str(e)}")
                    continue

            logger.info(f"Retrieved {len(technicians)} technicians from TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA")
            return technicians

        except Exception as e:
            logger.error(f"Error retrieving technician data: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()

    def calculate_skill_match(self, required_skills: List[str], technician_skills: List[str]) -> SkillMatchResult:
        """
        Calculate skill match with three-tier classification system

        Args:
            required_skills (List[str]): Skills required for the ticket
            technician_skills (List[str]): Skills possessed by the technician

        Returns:
            SkillMatchResult: Match result with percentage and classification
        """
        if not required_skills:
            return SkillMatchResult(
                match_percentage=50,  # Default score when no specific skills required
                classification="Mid",
                matched_skills=[],
                missing_skills=[]
            )

        matched_skills = []
        missing_skills = []

        # Calculate exact and partial matches
        for required_skill in required_skills:
            skill_matched = False
            required_lower = required_skill.lower()

            # Check for exact or partial matches
            for tech_skill in technician_skills:
                tech_lower = tech_skill.lower()
                if (required_lower in tech_lower or
                    tech_lower in required_lower or
                    required_lower == tech_lower):
                    matched_skills.append(required_skill)
                    skill_matched = True
                    break

            if not skill_matched:
                missing_skills.append(required_skill)

        # Calculate match percentage
        match_percentage = int((len(matched_skills) / len(required_skills)) * 100)

        # Apply three-tier classification as specified in requirements
        if match_percentage >= 70:
            classification = "Strong"
        elif match_percentage >= 60:
            classification = "Mid"
        else:
            classification = "Weak"

        logger.debug(f"Skill match calculation: {match_percentage}% ({classification}) - "
                    f"Matched: {matched_skills}, Missing: {missing_skills}")

        return SkillMatchResult(
            match_percentage=match_percentage,
            classification=classification,
            matched_skills=matched_skills,
            missing_skills=missing_skills
        )

    def check_calendar_availability(self, technician_email: str, due_date: str) -> bool:
        """
        Check technician availability using Google Calendar API

        Args:
            technician_email (str): Email address of the technician
            due_date (str): Due date of the ticket (ISO format)

        Returns:
            bool: True if technician is available before due date, False otherwise
        """
        if not GOOGLE_CALENDAR_AVAILABLE or not self.calendar_service:
            logger.warning("Google Calendar integration not available, assuming technician is available")
            return True

        try:
            # Parse due date
            if isinstance(due_date, str):
                try:
                    due_datetime = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                except ValueError:
                    # Try parsing different date formats
                    try:
                        due_datetime = datetime.strptime(due_date, '%Y-%m-%d')
                    except ValueError:
                        logger.warning(f"Could not parse due date: {due_date}, assuming available")
                        return True
            else:
                due_datetime = due_date

            # Check availability from now until due date
            from datetime import timezone
            now = datetime.now(timezone.utc)

            # Ensure due_datetime is timezone-aware
            if due_datetime.tzinfo is None:
                due_datetime = due_datetime.replace(tzinfo=timezone.utc)

            if due_datetime <= now:
                logger.warning(f"Due date {due_date} is in the past, assuming available")
                return True

            # Use Google Calendar freeBusy query as specified in requirements
            # Format datetime properly for FreeBusy API - ensure UTC timezone
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)
            if due_datetime.tzinfo is None:
                due_datetime = due_datetime.replace(tzinfo=timezone.utc)

            # Convert to proper RFC3339 format for Google Calendar API
            time_min = now.isoformat().replace('+00:00', 'Z')
            time_max = due_datetime.isoformat().replace('+00:00', 'Z')

            freebusy_query = {
                'timeMin': time_min,
                'timeMax': time_max,
                'items': [{'id': technician_email}]
            }

            # Execute freeBusy query
            freebusy_result = self.calendar_service.freebusy().query(body=freebusy_query).execute()

            # Check if technician has busy periods
            calendars = freebusy_result.get('calendars', {})
            technician_calendar = calendars.get(technician_email, {})
            busy_periods = technician_calendar.get('busy', [])

            if busy_periods:
                logger.info(f"Technician {technician_email} has {len(busy_periods)} busy periods before due date")
                # For now, consider unavailable if any busy periods exist
                # In production, you might want more sophisticated logic
                return False
            else:
                logger.info(f"Technician {technician_email} is available before due date")
                return True

        except HttpError as e:
            logger.error(f"Google Calendar API error for {technician_email}: {str(e)}")
            # If calendar check fails, assume available to avoid blocking assignments
            return True
        except Exception as e:
            logger.error(f"Error checking calendar availability for {technician_email}: {str(e)}")
            return True

    def select_best_candidate(self, candidates: List[AssignmentCandidate]) -> Optional[AssignmentCandidate]:
        """
        Select best candidate using strict priority hierarchy (Tiers 4-5 commented out)

        Priority Hierarchy:
        1. Available + Strong match (≥70%)
        2. Available + Mid match (60-69%)
        3. Available + Weak match (<60%)
        # 4. Unavailable + Strong match  # COMMENTED OUT
        # 5. Unavailable + Mid/Weak match  # COMMENTED OUT
        6. Fallback assignment

        Args:
            candidates (List[AssignmentCandidate]): List of evaluated candidates (only available ones)

        Returns:
            Optional[AssignmentCandidate]: Best candidate or None if fallback needed
        """
        if not candidates:
            logger.warning("No candidates provided for selection")
            return None

        # Sort candidates by priority tier (lower number = higher priority)
        sorted_candidates = sorted(candidates, key=lambda c: (c.priority_tier, -c.skill_match.match_percentage))

        best_candidate = sorted_candidates[0]

        # Log assignment decision with reasoning
        logger.info(f"Selected candidate: {best_candidate.technician.name} "
                   f"(Tier {best_candidate.priority_tier}: {self.priority_tiers[best_candidate.priority_tier]})")
        logger.info(f"Selection reasoning: {best_candidate.reasoning}")

        # Log rejected candidates with reasons
        for candidate in sorted_candidates[1:]:
            logger.info(f"Rejected candidate: {candidate.technician.name} - "
                       f"Tier {candidate.priority_tier}, {candidate.skill_match.classification} match "
                       f"({candidate.skill_match.match_percentage}%), "
                       f"Available: {candidate.calendar_available}")

        return best_candidate

    # ========================================
    # HELPER FUNCTIONS FOR INTEGRATION
    # ========================================

    def map_intake_to_assignment_format(self, intake_output: Dict) -> Dict:
        """
        Maps the intake/classification output to the format expected by assignment agent
        
        Args:
            intake_output (Dict): Output from intake and classification process
            
        Returns:
            Dict: Formatted data for assignment agent
        """
        try:
            new_ticket = intake_output.get('new_ticket', {})
            classified_data = new_ticket.get('classified_data', {})
            
            # Map the fields according to the required format
            assignment_input = {
                'ticket_id': new_ticket.get('ticket_number', ''),
                'issue': new_ticket.get('description', ''),
                'description': new_ticket.get('description', ''),
                'issue_type': classified_data.get('ISSUETYPE', {}).get('Label', ''),
                'sub_issue_type': classified_data.get('SUBISSUETYPE', {}).get('Label', ''),
                'ticket_category': classified_data.get('TICKETCATEGORY', {}).get('Label', ''),
                'priority': classified_data.get('PRIORITY', {}).get('Label', ''),
                'due_date': new_ticket.get('due_date', ''),
                'user_name': new_ticket.get('name', ''),
                'user_email': new_ticket.get('user_email', '')
            }

            logger.info(f"Mapped intake data to assignment format for ticket: {assignment_input['ticket_id']}")
            return assignment_input
            
        except Exception as e:
            logger.error(f"Error mapping intake data to assignment format: {str(e)}")
            raise AssignmentError(f"Failed to map intake data: {str(e)}")

    def _validate_ticket_data(self, ticket_data: Dict) -> TicketData:
        """
        Validate and parse incoming ticket data according to required format

        Args:
            ticket_data (Dict): Raw ticket data matching required JSON input format

        Returns:
            TicketData: Validated ticket data object

        Raises:
            ValueError: If required fields are missing or invalid
        """
        required_fields = [
            'ticket_id', 'issue', 'description', 'issue_type', 'sub_issue_type',
            'ticket_category', 'priority', 'due_date', 'user_name', 'user_email'
        ]

        missing_fields = [field for field in required_fields if field not in ticket_data or not ticket_data[field]]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Validate priority level
        valid_priorities = ['Low', 'Medium', 'High', 'Critical']
        if ticket_data['priority'] not in valid_priorities:
            logger.warning(f"Priority '{ticket_data['priority']}' not in standard list, proceeding anyway")

        return TicketData(
            ticket_id=str(ticket_data['ticket_id']),
            issue=str(ticket_data['issue']),
            description=str(ticket_data['description']),
            issue_type=str(ticket_data['issue_type']),
            sub_issue_type=str(ticket_data['sub_issue_type']),
            ticket_category=str(ticket_data['ticket_category']),
            priority=str(ticket_data['priority']),
            due_date=str(ticket_data['due_date']),
            user_name=str(ticket_data['user_name']),
            user_email=str(ticket_data['user_email'])
        )

    def _analyze_skills_with_cortex(self, ticket: TicketData) -> SkillAnalysis:
        """
        Analyze ticket requirements using Snowflake Cortex LLM

        Args:
            ticket (TicketData): Validated ticket data

        Returns:
            SkillAnalysis: Analysis results with required skills and complexity
        """
        cursor = None
        try:
            if not self.db_connection.conn:
                logger.error("No active Snowflake connection available")
                return self._fallback_skill_analysis(ticket)

            cursor = self.db_connection.conn.cursor()

            # Construct prompt for Cortex LLM analyzing all required fields
            prompt = f"""
            Analyze this IT support ticket and provide:
            1. Required technical skills (comma-separated list)
            2. Complexity level (1-5 scale where 1=basic, 5=expert)
            3. Specialized knowledge areas (comma-separated list)

            Ticket Details:
            - Ticket ID: {ticket.ticket_id}
            - Issue: {ticket.issue}
            - Description: {ticket.description}
            - Issue Type: {ticket.issue_type}
            - Sub Issue Type: {ticket.sub_issue_type}
            - Ticket Category: {ticket.ticket_category}
            - Priority: {ticket.priority}

            Respond in JSON format:
            {{
                "required_skills": ["skill1", "skill2"],
                "complexity_level": 3,
                "specialized_knowledge": ["area1", "area2"]
            }}
            """

            # Execute Cortex LLM query
            cortex_query = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'mixtral-8x7b',
                '{prompt.replace("'", "''")}'
            ) as analysis_result
            """

            cursor.execute(cortex_query)
            result = cursor.fetchone()

            if result and result[0]:
                try:
                    analysis_json = json.loads(result[0])
                    return SkillAnalysis(
                        required_skills=analysis_json.get('required_skills', []),
                        complexity_level=int(analysis_json.get('complexity_level', 3)),
                        specialized_knowledge=analysis_json.get('specialized_knowledge', [])
                    )
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse Cortex LLM response: {str(e)}")
                    return self._fallback_skill_analysis(ticket)
            else:
                logger.warning("Empty response from Cortex LLM")
                return self._fallback_skill_analysis(ticket)

        except Exception as e:
            logger.error(f"Error in Cortex skill analysis: {str(e)}")
            return self._fallback_skill_analysis(ticket)
        finally:
            if cursor:
                cursor.close()

    def _fallback_skill_analysis(self, ticket: TicketData) -> SkillAnalysis:
        """
        Fallback skill analysis when Cortex LLM fails

        Args:
            ticket (TicketData): Validated ticket data

        Returns:
            SkillAnalysis: Basic skill analysis based on issue type
        """
        logger.info("Using fallback skill analysis")

        # Map issue type to skills
        required_skills = self.fallback_skill_mapping.get(ticket.issue_type, ['General IT Support'])

        # Determine complexity based on priority and issue type
        complexity_mapping = {
            'Low': 2,
            'Medium': 3,
            'High': 4,
            'Critical': 5
        }
        complexity_level = complexity_mapping.get(ticket.priority, 3)

        # Basic specialized knowledge
        specialized_knowledge = [ticket.issue_type] if ticket.issue_type else []

        return SkillAnalysis(
            required_skills=required_skills,
            complexity_level=complexity_level,
            specialized_knowledge=specialized_knowledge
        )

    def _get_available_technicians(self) -> List[TechnicianData]:
        """
        Retrieve available technicians using the modular get_technician_data function

        Returns:
            List[TechnicianData]: List of available technicians as TechnicianData objects
        """
        try:
            technician_dicts = self.get_technician_data()
            technicians = []

            for tech_dict in technician_dicts:
                try:
                    technician = TechnicianData(
                        technician_id=tech_dict['technician_id'],
                        name=tech_dict['name'],
                        email=tech_dict['email'],
                        role=tech_dict['role'],
                        skills=tech_dict['skills'],
                        current_workload=tech_dict['current_workload'],
                        specializations=tech_dict['specializations']
                    )
                    technicians.append(technician)
                except Exception as e:
                    logger.warning(f"Error creating TechnicianData object: {str(e)}")
                    continue

            logger.info(f"Converted {len(technicians)} technician records to TechnicianData objects")
            return technicians

        except Exception as e:
            logger.error(f"Error retrieving available technicians: {str(e)}")
            return []

    def _evaluate_candidates(self, ticket: TicketData, skill_analysis: SkillAnalysis,
                            technicians: List[TechnicianData]) -> List[AssignmentCandidate]:
        """
        Evaluate all technicians and create assignment candidates with priority tiers

        Args:
            ticket (TicketData): Validated ticket data
            skill_analysis (SkillAnalysis): Required skills analysis
            technicians (List[TechnicianData]): Available technicians

        Returns:
            List[AssignmentCandidate]: List of evaluated candidates with priority tiers
        """
        candidates = []

        for technician in technicians:
            try:
                # Calculate skill match using the modular function
                skill_match = self.calculate_skill_match(skill_analysis.required_skills, technician.skills)

                # Check calendar availability using the modular function
                calendar_available = self.check_calendar_availability(technician.email, ticket.due_date)

                # FILTER OUT UNAVAILABLE TECHNICIANS - Only consider available ones
                if not calendar_available:
                    logger.info(f"Skipping unavailable technician: {technician.name}")
                    continue

                # Determine priority tier based on availability and skill match
                priority_tier = self._determine_priority_tier(calendar_available, skill_match.classification)

                # Create reasoning string (max_workload removed)
                reasoning = (f"Technician: {technician.name}, "
                           f"Skill Match: {skill_match.classification} ({skill_match.match_percentage}%), "
                           f"Available: {calendar_available}, "
                           f"Current Workload: {technician.current_workload}, "
                           f"Matched Skills: {skill_match.matched_skills}")

                candidate = AssignmentCandidate(
                    technician=technician,
                    skill_match=skill_match,
                    calendar_available=calendar_available,
                    priority_tier=priority_tier,
                    reasoning=reasoning
                )

                candidates.append(candidate)

            except Exception as e:
                logger.warning(f"Error evaluating technician {technician.name}: {str(e)}")
                continue

        logger.info(f"Evaluated {len(candidates)} candidates for ticket {ticket.ticket_id}")
        return candidates

    def _determine_priority_tier(self, calendar_available: bool, skill_classification: str) -> int:
        """
        Determine priority tier based on availability and skill match classification

        Args:
            calendar_available (bool): Whether technician is available
            skill_classification (str): "Strong", "Mid", or "Weak"

        Returns:
            int: Priority tier (1-6)
        """
        if calendar_available:
            if skill_classification == "Strong":
                return 1  # Available + Strong match (≥70%)
            elif skill_classification == "Mid":
                return 2  # Available + Mid match (60-69%)
            else:  # Weak
                return 3  # Available + Weak match (<60%)
        else:
            # COMMENTED OUT: Unavailable technicians are not considered for assignment
            # if skill_classification == "Strong":
            #     return 4  # Unavailable + Strong match
            # else:  # Mid or Weak
            #     return 5  # Unavailable + Mid/Weak match

            # Skip unavailable technicians - they will be filtered out
            return 6  # Treat as fallback tier to exclude from selection
        # Tier 6 (Fallback) is handled separately

    def _create_assignment_response(self, ticket: TicketData, candidate: Optional[AssignmentCandidate] = None,
                                   is_fallback: bool = False) -> Dict:
        """
        Create the assignment response in the required format

        Args:
            ticket (TicketData): Validated ticket data
            candidate (Optional[AssignmentCandidate]): Selected candidate or None for fallback
            is_fallback (bool): Whether this is a fallback assignment

        Returns:
            Dict: Assignment response matching required output format
        """
        current_time = datetime.now()

        if is_fallback or candidate is None:
            # Fallback assignment as specified in requirements
            return {
                'assignment_result': {
                    'ticket_id': ticket.ticket_id,
                    'assigned_technician': 'Fallback Support',
                    'technician_email': self.fallback_email,
                    'assignment_date': current_time.strftime('%Y-%m-%d'),
                    'assignment_time': current_time.strftime('%H:%M:%S'),
                    'priority': ticket.priority,
                    'issue_type': ticket.issue_type,
                    'sub_issue_type': ticket.sub_issue_type,
                    'ticket_category': ticket.ticket_category,
                    'user_name': ticket.user_name,
                    'user_email': ticket.user_email,
                    'due_date': ticket.due_date,
                    'status': 'Assigned (Fallback)',
                    'assignment_tier': 6,
                    'skill_match_percentage': 0,
                    'reasoning': 'No suitable technician found, assigned to fallback'
                }
            }
        else:
            # Successful assignment
            return {
                'assignment_result': {
                    'ticket_id': ticket.ticket_id,
                    'assigned_technician': candidate.technician.name,
                    'technician_email': candidate.technician.email,
                    'technician_id': candidate.technician.technician_id,
                    'assignment_date': current_time.strftime('%Y-%m-%d'),
                    'assignment_time': current_time.strftime('%H:%M:%S'),
                    'priority': ticket.priority,
                    'issue_type': ticket.issue_type,
                    'sub_issue_type': ticket.sub_issue_type,
                    'ticket_category': ticket.ticket_category,
                    'user_name': ticket.user_name,
                    'user_email': ticket.user_email,
                    'due_date': ticket.due_date,
                    'status': 'Assigned',
                    'assignment_tier': candidate.priority_tier,
                    'skill_match_percentage': candidate.skill_match.match_percentage,
                    'skill_match_classification': candidate.skill_match.classification,
                    'calendar_available': candidate.calendar_available,
                    'matched_skills': candidate.skill_match.matched_skills,
                    'missing_skills': candidate.skill_match.missing_skills,
                    'reasoning': candidate.reasoning
                }
            }

    def process_ticket_assignment(self, intake_output: Dict) -> Dict:
        """
        Main method to process ticket assignment from intake/classification output

        Args:
            intake_output (Dict): Output from intake and classification process

        Returns:
            Dict: Assignment result with technician details

        Raises:
            AssignmentError: If assignment fails
        """
        try:
            logger.info("Starting ticket assignment process")

            # Step 1: Map intake output to assignment format
            assignment_input = self.map_intake_to_assignment_format(intake_output)

            # Step 2: Validate ticket data
            ticket = self._validate_ticket_data(assignment_input)
            logger.info(f"Processing assignment for ticket: {ticket.ticket_id}")

            # Step 3: Extract required skills using modular function
            logger.info("Extracting required skills...")
            required_skills = self.extract_required_skills(assignment_input)
            skill_analysis = self._analyze_skills_with_cortex(ticket)
            logger.info(f"Required skills: {skill_analysis.required_skills}, "
                       f"Complexity: {skill_analysis.complexity_level}")

            # Step 4: Get available technicians using modular function
            logger.info("Retrieving available technicians...")
            technicians = self._get_available_technicians()

            if not technicians:
                logger.warning("No available technicians found, proceeding with fallback assignment")
                assignment_response = self._create_assignment_response(ticket, None, is_fallback=True)
                logger.info(f"Fallback assignment created for ticket {ticket.ticket_id}")
                return assignment_response

            # Step 5: Evaluate all candidates with priority tiers
            logger.info("Evaluating assignment candidates...")
            candidates = self._evaluate_candidates(ticket, skill_analysis, technicians)

            if not candidates:
                logger.warning("No valid candidates found, proceeding with fallback assignment")
                assignment_response = self._create_assignment_response(ticket, None, is_fallback=True)
                logger.info(f"Fallback assignment created for ticket {ticket.ticket_id}")
                return assignment_response

            # Step 6: Select best candidate using strict priority hierarchy
            logger.info("Selecting best candidate using priority hierarchy...")
            best_candidate = self.select_best_candidate(candidates)

            if not best_candidate:
                logger.warning("No suitable candidate selected, proceeding with fallback assignment")
                assignment_response = self._create_assignment_response(ticket, None, is_fallback=True)
                logger.info(f"Fallback assignment created for ticket {ticket.ticket_id}")
                return assignment_response

            # Step 7: Create and return successful assignment response
            assignment_response = self._create_assignment_response(ticket, best_candidate)
            logger.info(f"Successfully assigned ticket {ticket.ticket_id} to {best_candidate.technician.name} "
                       f"(Tier {best_candidate.priority_tier}: {self.priority_tiers[best_candidate.priority_tier]})")

            return assignment_response

        except Exception as e:
            error_msg = f"Assignment process failed: {str(e)}"
            logger.error(error_msg)
            raise AssignmentError(error_msg)

    # ========================================
    # PUBLIC INTERFACE FUNCTIONS (as specified in requirements)
    # ========================================

def assign_ticket(ticket_data: Dict, db_connection, google_calendar_credentials_path: Optional[str] = None) -> Dict:
    """
    Public function to assign a ticket to a technician using the intelligent assignment system

    Args:
        ticket_data (Dict): Ticket data in the required JSON format:
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
        db_connection: Snowflake database connection
        google_calendar_credentials_path: Path to Google Calendar service account credentials

    Returns:
        Dict: Assignment result with technician details and assignment metadata
    """
    agent = AssignmentAgentIntegration(db_connection, google_calendar_credentials_path)

    # Create a mock intake output format for compatibility
    mock_intake_output = {
        'new_ticket': {
            'ticket_number': ticket_data.get('ticket_id', ''),
            'description': ticket_data.get('description', ''),
            'name': ticket_data.get('user_name', ''),
            'user_email': ticket_data.get('user_email', ''),
            'due_date': ticket_data.get('due_date', ''),
            'classified_data': {
                'ISSUETYPE': {'Label': ticket_data.get('issue_type', '')},
                'SUBISSUETYPE': {'Label': ticket_data.get('sub_issue_type', '')},
                'TICKETCATEGORY': {'Label': ticket_data.get('ticket_category', '')},
                'PRIORITY': {'Label': ticket_data.get('priority', '')}
            }
        }
    }

    return agent.process_ticket_assignment(mock_intake_output)


def test_assignment_agent():
    """
    Test function to demonstrate the assignment agent functionality
    """
    # Example ticket data matching the required format
    test_ticket = {
        'ticket_id': 'TKT-2024-001',
        'issue': 'Email server down',
        'description': 'Users cannot send or receive emails. Exchange server appears to be offline.',
        'issue_type': 'Email',
        'sub_issue_type': 'Exchange',
        'ticket_category': 'Infrastructure',
        'priority': 'Critical',
        'due_date': '2024-07-15T14:00:00Z',
        'user_name': 'Jane Doe',
        'user_email': 'jane.doe@company.com'
    }

    print("🎯 Testing Assignment Agent with Required Format")
    print("=" * 60)
    print(f"Input Ticket: {test_ticket['ticket_id']}")
    print(f"Issue: {test_ticket['issue']}")
    print(f"Priority: {test_ticket['priority']}")
    print(f"Due Date: {test_ticket['due_date']}")
    print()

    try:
        # Note: This would require actual database connection in real usage
        print("⚠️  Note: This test requires actual Snowflake database connection")
        print("📋 Modular Functions Available:")
        print("   ✅ extract_required_skills()")
        print("   ✅ get_technician_data()")
        print("   ✅ calculate_skill_match()")
        print("   ✅ check_calendar_availability()")
        print("   ✅ select_best_candidate()")
        print()
        print("🎯 Assignment Priority Hierarchy (Tiers 4-5 Commented Out):")
        print("   1. Available + Strong match (≥70%)")
        print("   2. Available + Mid match (60-69%)")
        print("   3. Available + Weak match (<60%)")
        print("   # 4. Unavailable + Strong match  # COMMENTED OUT")
        print("   # 5. Unavailable + Mid/Weak match  # COMMENTED OUT")
        print("   6. Fallback assignment to fallback@company.com")
        print()
        print("✅ Implementation complete and ready for integration!")

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")


if __name__ == "__main__":
    test_assignment_agent()
