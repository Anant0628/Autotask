"""
Assignment Agent for IT Support Ticket System

This module processes classified IT support tickets and assigns them to the most
appropriate technician using Snowflake database queries and AI-driven skill analysis.

Author: AutoTask Assignment System
Date: 2025-07-04
"""

import os
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass
import snowflake.connector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('assignment_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TicketData:
    """Data class for ticket information"""
    ticket_number: str
    issue_type: str
    sub_issue_type: str
    ticket_category: str
    priority: str
    description: str
    requester_name: str
    requester_email: str
    due_date: str

@dataclass
class TechnicianData:
    """Data class for technician information"""
    technician_name: str
    technician_email: str
    skills: List[str]
    availability_status: str
    current_workload: int
    max_workload: int
    specializations: List[str]

@dataclass
class SkillAnalysis:
    """Data class for skill analysis results"""
    required_skills: List[str]
    complexity_level: int
    specialized_knowledge: List[str]

class SnowflakeConnectionError(Exception):
    """Custom exception for Snowflake connection issues"""
    pass

class AssignmentError(Exception):
    """Custom exception for assignment issues"""
    pass

class AssignmentAgent:
    """
    Main Assignment Agent class that handles ticket assignment logic
    """

    def __init__(self):
        """Initialize the Assignment Agent with Snowflake connection"""
        self.connection = None
        self.max_retries = 3
        self.retry_delay = 2  # seconds

        # Fallback skill mapping for when Cortex LLM fails
        self.fallback_skill_mapping = {
            'Hardware': ['Hardware Troubleshooting', 'PC Repair', 'Printer Support'],
            'Software': ['Software Installation', 'Application Support', 'Troubleshooting'],
            'Network': ['Network Troubleshooting', 'Router Configuration', 'WiFi Setup'],
            'Security': ['Security Analysis', 'Antivirus Support', 'Access Control'],
            'Database': ['SQL Database', 'Database Administration', 'Data Recovery'],
            'Email': ['Email Configuration', 'Outlook Support', 'Exchange Server'],
            'Server': ['Windows Server', 'Linux Server', 'Server Administration']
        }

        # Default escalation technician
        self.escalation_technician = {
            'technician_name': 'IT Manager',
            'technician_email': 'itmanager@company.com'
        }

    def _get_snowflake_connection(self) -> snowflake.connector.SnowflakeConnection:
        """
        Establish connection to Snowflake database with retry logic

        Returns:
            snowflake.connector.SnowflakeConnection: Active Snowflake connection

        Raises:
            SnowflakeConnectionError: If connection fails after all retries
        """
        for attempt in range(self.max_retries):
            try:
                connection = snowflake.connector.connect(
                    account=os.getenv('SF_ACCOUNT'),
                    user=os.getenv('SF_USER'),
                    password=os.getenv('SF_PASSWORD'),
                    warehouse=os.getenv('SF_WAREHOUSE'),
                    database=os.getenv('SF_DATABASE'),
                    schema=os.getenv('SF_SCHEMA'),
                    role=os.getenv('SF_ROLE')
                )
                logger.info(f"Successfully connected to Snowflake on attempt {attempt + 1}")
                return connection

            except Exception as e:
                logger.error(f"Snowflake connection attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise SnowflakeConnectionError(f"Failed to connect to Snowflake after {self.max_retries} attempts: {str(e)}")

    def _validate_ticket_data(self, ticket_data: Dict) -> TicketData:
        """
        Validate and parse incoming ticket data

        Args:
            ticket_data (Dict): Raw ticket data from classification agent

        Returns:
            TicketData: Validated ticket data object

        Raises:
            ValueError: If required fields are missing or invalid
        """
        required_fields = [
            'TICKETNUMBER', 'issue_type', 'sub_issue_type', 'ticket_category',
            'priority', 'description', 'requester_name', 'requester_email', 'due_date'
        ]

        missing_fields = [field for field in required_fields if field not in ticket_data or not ticket_data[field]]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Validate priority level
        valid_priorities = ['Low', 'Medium', 'High', 'Critical']
        if ticket_data['priority'] not in valid_priorities:
            raise ValueError(f"Invalid priority level: {ticket_data['priority']}. Must be one of {valid_priorities}")

        return TicketData(
            ticket_number=str(ticket_data['TICKETNUMBER']),
            issue_type=str(ticket_data['issue_type']),
            sub_issue_type=str(ticket_data['sub_issue_type']),
            ticket_category=str(ticket_data['ticket_category']),
            priority=str(ticket_data['priority']),
            description=str(ticket_data['description']),
            requester_name=str(ticket_data['requester_name']),
            requester_email=str(ticket_data['requester_email']),
            due_date=str(ticket_data['due_date'])
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
            if not self.connection:
                self.connection = self._get_snowflake_connection()

            cursor = self.connection.cursor()

            # Construct prompt for Cortex LLM
            prompt = f"""
            Analyze this IT support ticket and provide:
            1. Required technical skills (comma-separated list)
            2. Complexity level (1-5 scale where 1=basic, 5=expert)
            3. Specialized knowledge areas (comma-separated list)

            Ticket Details:
            - Issue Type: {ticket.issue_type}
            - Sub Issue Type: {ticket.sub_issue_type}
            - Priority: {ticket.priority}
            - Description: {ticket.description}

            Format your response as JSON:
            {{
                "required_skills": ["skill1", "skill2", "skill3"],
                "complexity_level": 3,
                "specialized_knowledge": ["area1", "area2"]
            }}
            """

            # Use Snowflake Cortex LLM for analysis
            cortex_query = """
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'llama3-8b',
                %s
            ) as analysis_result
            """

            cursor.execute(cortex_query, (prompt,))
            result = cursor.fetchone()

            if result and result[0]:
                # Parse the JSON response from Cortex
                import json
                analysis_data = json.loads(result[0])

                return SkillAnalysis(
                    required_skills=analysis_data.get('required_skills', []),
                    complexity_level=int(analysis_data.get('complexity_level', 3)),
                    specialized_knowledge=analysis_data.get('specialized_knowledge', [])
                )
            else:
                logger.warning("Cortex LLM returned empty result, using fallback analysis")
                return self._fallback_skill_analysis(ticket)

        except Exception as e:
            logger.error(f"Cortex LLM analysis failed: {str(e)}")
            return self._fallback_skill_analysis(ticket)
        finally:
            if cursor:
                cursor.close()

    def _fallback_skill_analysis(self, ticket: TicketData) -> SkillAnalysis:
        """
        Fallback skill analysis when Cortex LLM is unavailable

        Args:
            ticket (TicketData): Validated ticket data

        Returns:
            SkillAnalysis: Basic analysis based on issue type mapping
        """
        # Map issue type to skills
        required_skills = []
        for category, skills in self.fallback_skill_mapping.items():
            if category.lower() in ticket.issue_type.lower() or category.lower() in ticket.sub_issue_type.lower():
                required_skills.extend(skills)

        # If no mapping found, use generic skills
        if not required_skills:
            required_skills = ['General IT Support', 'Troubleshooting']

        # Determine complexity based on priority
        complexity_mapping = {
            'Low': 2,
            'Medium': 3,
            'High': 4,
            'Critical': 5
        }
        complexity_level = complexity_mapping.get(ticket.priority, 3)

        # Basic specialized knowledge based on issue type
        specialized_knowledge = []
        if 'server' in ticket.issue_type.lower() or 'server' in ticket.description.lower():
            specialized_knowledge.append('Server Administration')
        if 'network' in ticket.issue_type.lower() or 'network' in ticket.description.lower():
            specialized_knowledge.append('Network Infrastructure')
        if 'security' in ticket.issue_type.lower() or 'security' in ticket.description.lower():
            specialized_knowledge.append('Cybersecurity')

        return SkillAnalysis(
            required_skills=required_skills,
            complexity_level=complexity_level,
            specialized_knowledge=specialized_knowledge
        )

    def _get_available_technicians(self) -> List[TechnicianData]:
        """
        Query available technicians from Snowflake database

        Returns:
            List[TechnicianData]: List of available technicians

        Raises:
            SnowflakeConnectionError: If database query fails
        """
        cursor = None
        try:
            if not self.connection:
                self.connection = self._get_snowflake_connection()

            cursor = self.connection.cursor()

            # Query available technicians
            query = """
            SELECT
                technician_name,
                technician_email,
                skills,
                availability_status,
                current_workload,
                max_workload,
                specializations
            FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
            WHERE availability_status = 'Available'
            AND current_workload < max_workload
            ORDER BY current_workload ASC
            """

            cursor.execute(query)
            results = cursor.fetchall()

            technicians = []
            for row in results:
                technicians.append(TechnicianData(
                    technician_name=row[0],
                    technician_email=row[1],
                    skills=row[2].split(',') if row[2] else [],
                    availability_status=row[3],
                    current_workload=int(row[4]) if row[4] else 0,
                    max_workload=int(row[5]) if row[5] else 10,
                    specializations=row[6].split(',') if row[6] else []
                ))

            logger.info(f"Retrieved {len(technicians)} available technicians")
            return technicians

        except Exception as e:
            logger.error(f"Failed to query technicians: {str(e)}")
            raise SnowflakeConnectionError(f"Database query failed: {str(e)}")
        finally:
            if cursor:
                cursor.close()

    def _calculate_skill_match_score(self, required_skills: List[str], technician: TechnicianData) -> int:
        """
        Calculate skill match score between required skills and technician skills

        Args:
            required_skills (List[str]): Skills required for the ticket
            technician (TechnicianData): Technician data

        Returns:
            int: Match score from 0-100
        """
        if not required_skills:
            return 50  # Default score if no specific skills required

        # Normalize skills for comparison (lowercase, strip whitespace)
        normalized_required = [skill.lower().strip() for skill in required_skills]
        normalized_tech_skills = [skill.lower().strip() for skill in technician.skills]
        normalized_specializations = [spec.lower().strip() for spec in technician.specializations]

        # Calculate matches
        skill_matches = 0
        specialization_bonus = 0

        for required_skill in normalized_required:
            # Direct skill match
            for tech_skill in normalized_tech_skills:
                if required_skill in tech_skill or tech_skill in required_skill:
                    skill_matches += 1
                    break

            # Specialization bonus
            for specialization in normalized_specializations:
                if required_skill in specialization or specialization in required_skill:
                    specialization_bonus += 1
                    break

        # Calculate score
        skill_match_percentage = (skill_matches / len(normalized_required)) * 70  # 70% weight for skills
        specialization_percentage = min((specialization_bonus / len(normalized_required)) * 30, 30)  # 30% weight for specializations

        total_score = int(skill_match_percentage + specialization_percentage)
        return min(total_score, 100)  # Cap at 100

    def _assign_best_technician(self, ticket: TicketData, skill_analysis: SkillAnalysis,
                               technicians: List[TechnicianData]) -> Tuple[TechnicianData, int, str]:
        """
        Assign ticket to the best matching technician

        Args:
            ticket (TicketData): Ticket information
            skill_analysis (SkillAnalysis): Required skills analysis
            technicians (List[TechnicianData]): Available technicians

        Returns:
            Tuple[TechnicianData, int, str]: Best technician, match score, and reasoning

        Raises:
            AssignmentError: If no suitable technician found
        """
        if not technicians:
            raise AssignmentError("No available technicians found")

        best_technician = None
        best_score = 0
        best_reasoning = ""

        for technician in technicians:
            # Calculate skill match score
            skill_score = self._calculate_skill_match_score(skill_analysis.required_skills, technician)

            # Apply workload penalty (prefer technicians with lower workload)
            workload_factor = 1.0 - (technician.current_workload / technician.max_workload * 0.2)  # Up to 20% penalty
            adjusted_score = int(skill_score * workload_factor)

            # Priority bonus for high complexity tickets
            if skill_analysis.complexity_level >= 4 and any(
                spec.lower() in ['senior', 'expert', 'lead', 'specialist']
                for spec in technician.specializations
            ):
                adjusted_score += 10

            logger.info(f"Technician {technician.technician_name}: "
                       f"Skill Score={skill_score}, Workload Factor={workload_factor:.2f}, "
                       f"Final Score={adjusted_score}")

            if adjusted_score > best_score:
                best_score = adjusted_score
                best_technician = technician
                best_reasoning = (f"Best match with {skill_score}% skill compatibility, "
                                f"current workload: {technician.current_workload}/{technician.max_workload}")

        if not best_technician or best_score < 30:  # Minimum threshold
            raise AssignmentError(f"No technician meets minimum skill requirements (best score: {best_score})")

        return best_technician, best_score, best_reasoning

    def _log_assignment_decision(self, ticket: TicketData, technician: TechnicianData,
                                score: int, reasoning: str) -> None:
        """
        Log assignment decision with detailed information

        Args:
            ticket (TicketData): Ticket information
            technician (TechnicianData): Assigned technician
            score (int): Match score
            reasoning (str): Assignment reasoning
        """
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'ticket_number': ticket.ticket_number,
            'issue_type': f"{ticket.issue_type}: {ticket.sub_issue_type}",
            'priority': ticket.priority,
            'assigned_technician': technician.technician_name,
            'technician_email': technician.technician_email,
            'match_score': score,
            'reasoning': reasoning,
            'technician_workload': f"{technician.current_workload}/{technician.max_workload}"
        }

        logger.info(f"ASSIGNMENT DECISION: {json.dumps(log_entry, indent=2)}")

    def _create_assignment_response(self, ticket: TicketData, technician: TechnicianData) -> Dict:
        """
        Create the final assignment response dictionary

        Args:
            ticket (TicketData): Ticket information
            technician (TechnicianData): Assigned technician

        Returns:
            Dict: Formatted assignment response
        """
        return {
            'TICKETNUMBER': ticket.ticket_number,
            'issue': f"{ticket.issue_type}: {ticket.sub_issue_type}",
            'description': ticket.description,
            'due_date': ticket.due_date,
            'priority': ticket.priority,
            'category': ticket.ticket_category,
            'technician_name': technician.technician_name,
            'technician_email': technician.technician_email,
            'user_name': ticket.requester_name,
            'user_email': ticket.requester_email
        }

    def process_ticket_assignment(self, ticket_data: Dict) -> Dict:
        """
        Main method to process ticket assignment

        Args:
            ticket_data (Dict): Raw ticket data from classification agent

        Returns:
            Dict: Assignment result with technician details

        Raises:
            ValueError: If ticket data is invalid
            SnowflakeConnectionError: If database connection fails
            AssignmentError: If assignment fails
        """
        try:
            # Step 1: Validate ticket data
            logger.info(f"Processing assignment for ticket: {ticket_data.get('TICKETNUMBER', 'Unknown')}")
            ticket = self._validate_ticket_data(ticket_data)

            # Step 2: Analyze skill requirements
            logger.info("Analyzing skill requirements...")
            skill_analysis = self._analyze_skills_with_cortex(ticket)
            logger.info(f"Required skills: {skill_analysis.required_skills}, "
                       f"Complexity: {skill_analysis.complexity_level}")

            # Step 3: Get available technicians
            logger.info("Querying available technicians...")
            technicians = self._get_available_technicians()

            if not technicians:
                logger.warning("No available technicians found, assigning to escalation technician")
                escalation_response = self._create_assignment_response(
                    ticket,
                    TechnicianData(
                        technician_name=self.escalation_technician['technician_name'],
                        technician_email=self.escalation_technician['technician_email'],
                        skills=[],
                        availability_status='Available',
                        current_workload=0,
                        max_workload=100,
                        specializations=[]
                    )
                )
                logger.info(f"Ticket {ticket.ticket_number} assigned to escalation technician")
                return escalation_response

            # Step 4: Find best technician match
            logger.info("Finding best technician match...")
            best_technician, match_score, reasoning = self._assign_best_technician(
                ticket, skill_analysis, technicians
            )

            # Step 5: Log assignment decision
            self._log_assignment_decision(ticket, best_technician, match_score, reasoning)

            # Step 6: Create and return response
            assignment_response = self._create_assignment_response(ticket, best_technician)
            logger.info(f"Successfully assigned ticket {ticket.ticket_number} to {best_technician.technician_name}")

            return assignment_response

        except ValueError as e:
            error_msg = f"Ticket validation failed: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        except SnowflakeConnectionError as e:
            error_msg = f"Database connection failed: {str(e)}"
            logger.error(error_msg)
            raise SnowflakeConnectionError(error_msg)

        except AssignmentError as e:
            # Try to assign to escalation technician
            logger.warning(f"Assignment failed: {str(e)}, assigning to escalation technician")
            try:
                ticket = self._validate_ticket_data(ticket_data)  # Re-validate in case of earlier failure
                escalation_response = self._create_assignment_response(
                    ticket,
                    TechnicianData(
                        technician_name=self.escalation_technician['technician_name'],
                        technician_email=self.escalation_technician['technician_email'],
                        skills=[],
                        availability_status='Available',
                        current_workload=0,
                        max_workload=100,
                        specializations=[]
                    )
                )
                logger.info(f"Ticket {ticket.ticket_number} assigned to escalation technician due to assignment failure")
                return escalation_response
            except Exception as escalation_error:
                error_msg = f"Assignment and escalation both failed: {str(e)}, {str(escalation_error)}"
                logger.error(error_msg)
                raise AssignmentError(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error during assignment: {str(e)}"
            logger.error(error_msg)
            raise AssignmentError(error_msg)

        finally:
            # Clean up connection
            if self.connection:
                try:
                    self.connection.close()
                    self.connection = None
                except Exception as e:
                    logger.warning(f"Failed to close Snowflake connection: {str(e)}")

    def __del__(self):
        """Cleanup method to ensure connection is closed"""
        if hasattr(self, 'connection') and self.connection:
            try:
                self.connection.close()
            except Exception:
                pass  # Ignore cleanup errors


# Public interface functions
def assign_ticket(ticket_data: Dict) -> Dict:
    """
    Public function to assign a ticket to a technician

    Args:
        ticket_data (Dict): Classified ticket data from intake system

    Returns:
        Dict: Assignment result with technician details

    Example:
        ticket_data = {
            'TICKETNUMBER': 'TKT-001',
            'issue_type': 'Hardware',
            'sub_issue_type': 'Printer Issue',
            'ticket_category': 'Support',
            'priority': 'Medium',
            'description': 'Printer not working in office',
            'requester_name': 'John Doe',
            'requester_email': 'john.doe@company.com',
            'due_date': '2025-07-05T10:00:00Z'
        }

        result = assign_ticket(ticket_data)
    """
    agent = AssignmentAgent()
    return agent.process_ticket_assignment(ticket_data)


def main():
    """
    Main function for testing the assignment agent
    """
    # Example ticket data for testing
    test_ticket = {
        'TICKETNUMBER': 'TKT-TEST-001',
        'issue_type': 'Hardware',
        'sub_issue_type': 'Printer Issue',
        'ticket_category': 'Support Request',
        'priority': 'Medium',
        'description': 'Office printer HP LaserJet Pro is not printing. Users report paper jam error but no visible jam found.',
        'requester_name': 'Jane Smith',
        'requester_email': 'jane.smith@company.com',
        'due_date': '2025-07-05T14:00:00Z'
    }

    try:
        print("Testing Assignment Agent...")
        print(f"Input ticket: {test_ticket['TICKETNUMBER']}")

        result = assign_ticket(test_ticket)

        print("\nAssignment Result:")
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"Error during testing: {str(e)}")
        logger.error(f"Test failed: {str(e)}")


if __name__ == "__main__":
    main()