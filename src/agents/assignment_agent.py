"""
Assignment Agent Integration Module

This module integrates the assignment agent with the existing intake/classification workflow.
It adapts the assignment agent to use the same Snowflake connection pattern and data structures
as the existing agents.

Author: AutoTask Integration System
Date: 2025-07-04
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
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

class AssignmentError(Exception):
    """Custom exception for assignment issues"""
    pass

class AssignmentAgentIntegration:
    """
    Assignment Agent Integration class that works with the existing Snowflake connection
    and data structures from the intake/classification workflow.
    """

    def __init__(self, db_connection):
        """
        Initialize the Assignment Agent with existing database connection
        
        Args:
            db_connection: Existing SnowflakeConnection instance from intake agent
        """
        self.db_connection = db_connection
        self.max_retries = 3
        self.retry_delay = 2  # seconds

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

        # Default escalation technician
        self.escalation_technician = {
            'technician_name': 'IT Manager',
            'technician_email': 'itmanager@company.com'
        }

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
                'TICKETNUMBER': new_ticket.get('ticket_number', ''),
                'issue_type': classified_data.get('ISSUETYPE', {}).get('Label', ''),
                'sub_issue_type': classified_data.get('SUBISSUETYPE', {}).get('Label', ''),
                'ticket_category': classified_data.get('TICKETCATEGORY', {}).get('Label', ''),
                'priority': classified_data.get('PRIORITY', {}).get('Label', ''),
                'description': new_ticket.get('description', ''),
                'requester_name': new_ticket.get('name', ''),
                'requester_email': new_ticket.get('user_email', ''),
                'due_date': new_ticket.get('due_date', '')
            }
            
            logger.info(f"Mapped intake data to assignment format for ticket: {assignment_input['TICKETNUMBER']}")
            return assignment_input
            
        except Exception as e:
            logger.error(f"Error mapping intake data to assignment format: {str(e)}")
            raise AssignmentError(f"Failed to map intake data: {str(e)}")

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
            logger.warning(f"Priority '{ticket_data['priority']}' not in standard list, proceeding anyway")

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
            if not self.db_connection.conn:
                logger.error("No active Snowflake connection available")
                return self._fallback_skill_analysis(ticket)

            cursor = self.db_connection.conn.cursor()

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
        Retrieve available technicians from Snowflake database

        Returns:
            List[TechnicianData]: List of available technicians
        """
        cursor = None
        try:
            if not self.db_connection.conn:
                logger.error("No active Snowflake connection available")
                return []

            cursor = self.db_connection.conn.cursor()

            # Query to get available technicians from your TECHNICIAN_DUMMY_DATA table
            query = """
            SELECT
                NAME,
                EMAIL,
                ROLE,
                SKILLS
            FROM TECHNICIAN_DUMMY_DATA
            ORDER BY NAME ASC
            """

            cursor.execute(query)
            results = cursor.fetchall()

            technicians = []
            for row in results:
                try:
                    # Parse skills - handle both JSON array and comma-separated string formats
                    skills_raw = str(row[3]) if row[3] else ""
                    if skills_raw.startswith('[') and skills_raw.endswith(']'):
                        # JSON format
                        try:
                            skills = json.loads(skills_raw)
                        except json.JSONDecodeError:
                            skills = [s.strip() for s in skills_raw.strip('[]').replace('"', '').split(',')]
                    else:
                        # Comma-separated format
                        skills = [s.strip() for s in skills_raw.split(',') if s.strip()]

                    # Create technician data with available fields
                    technicians.append(TechnicianData(
                        technician_name=str(row[0]),
                        technician_email=str(row[1]),
                        skills=skills,
                        availability_status='Available',  # Default since not in your table
                        current_workload=0,  # Default since not in your table
                        max_workload=10,  # Default since not in your table
                        specializations=[str(row[2])] if row[2] else []  # Use ROLE as specialization
                    ))
                except Exception as e:
                    logger.warning(f"Error parsing technician data for row {row}: {str(e)}")
                    continue

            logger.info(f"Retrieved {len(technicians)} available technicians from TECHNICIAN_DUMMY_DATA")
            return technicians

        except Exception as e:
            logger.error(f"Error retrieving technicians: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()

    def _assign_best_technician(self, ticket: TicketData, skill_analysis: SkillAnalysis,
                               technicians: List[TechnicianData]) -> tuple:
        """
        Find the best technician match for the ticket

        Args:
            ticket (TicketData): Validated ticket data
            skill_analysis (SkillAnalysis): Required skills analysis
            technicians (List[TechnicianData]): Available technicians

        Returns:
            tuple: (best_technician, match_score, reasoning)
        """
        if not technicians:
            logger.warning("No available technicians found, using escalation")
            return self.escalation_technician, 0.0, "No available technicians"

        best_technician = None
        best_score = 0.0
        best_reasoning = ""

        for technician in technicians:
            score = 0.0
            reasoning_parts = []

            # Skill matching (40% of score)
            skill_matches = 0
            for required_skill in skill_analysis.required_skills:
                if any(required_skill.lower() in tech_skill.lower() for tech_skill in technician.skills):
                    skill_matches += 1

            if skill_analysis.required_skills:
                skill_score = (skill_matches / len(skill_analysis.required_skills)) * 0.4
                score += skill_score
                reasoning_parts.append(f"Skill match: {skill_matches}/{len(skill_analysis.required_skills)}")

            # Role-based matching (30% of score) - Enhanced for your ROLE column
            role_matches = 0
            issue_type_lower = ticket.issue_type.lower()

            # Check if technician's role matches the issue type
            for role, issue_types in self.role_issue_mapping.items():
                if any(role.lower() in spec.lower() for spec in technician.specializations):
                    if any(issue_type.lower() in issue_type_lower for issue_type in issue_types):
                        role_matches += 1
                        break

            # Also check direct role match with issue type
            if any(spec.lower() in issue_type_lower or issue_type_lower in spec.lower()
                   for spec in technician.specializations):
                role_matches += 1

            role_score = min(role_matches, 1) * 0.3  # Cap at 1 for full score
            score += role_score
            reasoning_parts.append(f"Role match: {role_matches > 0} (Role: {', '.join(technician.specializations)})")

            # Specialization matching (20% of score)
            specialization_matches = 0
            for spec_knowledge in skill_analysis.specialized_knowledge:
                if any(spec_knowledge.lower() in spec.lower() for spec in technician.specializations):
                    specialization_matches += 1

            if skill_analysis.specialized_knowledge:
                spec_score = (specialization_matches / len(skill_analysis.specialized_knowledge)) * 0.2
                score += spec_score
                reasoning_parts.append(f"Specialization match: {specialization_matches}/{len(skill_analysis.specialized_knowledge)}")

            # Workload consideration (10% of score) - Reduced since we don't have real workload data
            if technician.max_workload > 0:
                workload_ratio = technician.current_workload / technician.max_workload
                workload_score = (1 - workload_ratio) * 0.1
                score += workload_score
                reasoning_parts.append(f"Workload: {technician.current_workload}/{technician.max_workload}")

            # Priority boost (10% of score)
            if ticket.priority == 'Critical':
                score += 0.1
                reasoning_parts.append("Critical priority boost")

            reasoning = f"{technician.technician_name}: " + ", ".join(reasoning_parts) + f" (Score: {score:.2f})"

            if score > best_score:
                best_score = score
                best_technician = technician
                best_reasoning = reasoning

        if best_technician is None:
            logger.warning("No suitable technician found, using escalation")
            return self.escalation_technician, 0.0, "No suitable match found"

        return best_technician, best_score, best_reasoning

    def _create_assignment_response(self, ticket: TicketData, technician) -> Dict:
        """
        Create the assignment response

        Args:
            ticket (TicketData): Validated ticket data
            technician: Assigned technician (TechnicianData or dict)

        Returns:
            Dict: Assignment response
        """
        if isinstance(technician, TechnicianData):
            tech_name = technician.technician_name
            tech_email = technician.technician_email
        else:
            tech_name = technician.get('technician_name', 'Unknown')
            tech_email = technician.get('technician_email', 'unknown@company.com')

        return {
            'assignment_result': {
                'ticket_number': ticket.ticket_number,
                'assigned_technician': tech_name,
                'technician_email': tech_email,
                'assignment_date': datetime.now().strftime('%Y-%m-%d'),
                'assignment_time': datetime.now().strftime('%H:%M:%S'),
                'priority': ticket.priority,
                'issue_type': ticket.issue_type,
                'sub_issue_type': ticket.sub_issue_type,
                'requester_name': ticket.requester_name,
                'requester_email': ticket.requester_email,
                'due_date': ticket.due_date,
                'status': 'Assigned'
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
            logger.info(f"Processing assignment for ticket: {ticket.ticket_number}")

            # Step 3: Analyze skill requirements
            logger.info("Analyzing skill requirements...")
            skill_analysis = self._analyze_skills_with_cortex(ticket)
            logger.info(f"Required skills: {skill_analysis.required_skills}, "
                       f"Complexity: {skill_analysis.complexity_level}")

            # Step 4: Get available technicians
            logger.info("Retrieving available technicians...")
            technicians = self._get_available_technicians()

            if not technicians:
                logger.warning("No available technicians found")

            # Step 5: Find best technician match
            logger.info("Finding best technician match...")
            best_technician, match_score, reasoning = self._assign_best_technician(
                ticket, skill_analysis, technicians
            )

            # Step 6: Log assignment decision
            logger.info(f"Assignment decision: {reasoning}")

            # Step 7: Create and return response
            assignment_response = self._create_assignment_response(ticket, best_technician)
            logger.info(f"Successfully assigned ticket {ticket.ticket_number} to {best_technician.get('technician_name', 'Unknown') if isinstance(best_technician, dict) else best_technician.technician_name}")

            return assignment_response

        except Exception as e:
            error_msg = f"Assignment process failed: {str(e)}"
            logger.error(error_msg)
            raise AssignmentError(error_msg)
