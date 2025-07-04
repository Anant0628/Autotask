"""
Assignment Agent for TeamLogic-AutoTask Application
Processes classified IT support tickets and assigns them to appropriate technicians
using Snowflake database information and AI-driven skill analysis.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from database import SnowflakeConnection
from notify_agent import NotifyAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AssignmentAgent:
    """
    AI Agent responsible for assigning classified tickets to appropriate technicians
    based on skill requirements, availability, and workload analysis.
    """
    
    def __init__(self, sf_account: str, sf_user: str, sf_password: str, sf_warehouse: str,
                 sf_database: str, sf_schema: str, sf_role: str, sf_passcode: str):
        """
        Initialize the Assignment Agent with Snowflake connection.
        
        Args:
            sf_account (str): Snowflake account identifier
            sf_user (str): Snowflake username
            sf_password (str): Snowflake password
            sf_warehouse (str): Snowflake warehouse
            sf_database (str): Snowflake database
            sf_schema (str): Snowflake schema
            sf_role (str): Snowflake role
            sf_passcode (str): Snowflake MFA passcode
        """
        self.db_connection = SnowflakeConnection(
            sf_account, sf_user, sf_password, sf_warehouse,
            sf_database, sf_schema, sf_role, sf_passcode
        )
        self.notify_agent = NotifyAgent()
        
    def analyze_skill_requirements(self, classified_ticket: Dict) -> Dict:
        """
        Use Snowflake Cortex LLM to analyze ticket and determine required skills.
        
        Args:
            classified_ticket (Dict): Classified ticket data
            
        Returns:
            Dict: Required skills and complexity analysis
        """
        try:
            # Extract classification data
            classified_data = classified_ticket.get('classified_data', {})
            
            # Get issue details
            issue_type = self._extract_label(classified_data.get('ISSUETYPE', {}))
            sub_issue_type = self._extract_label(classified_data.get('SUBISSUETYPE', {}))
            ticket_category = self._extract_label(classified_data.get('TICKETCATEGORY', {}))
            priority = self._extract_label(classified_data.get('PRIORITY', {}))
            description = classified_ticket.get('description', '')
            
            # Create analysis prompt
            analysis_prompt = f"""
            Analyze this IT support ticket and determine the required technical skills:
            
            Issue Type: {issue_type}
            Sub-Issue Type: {sub_issue_type}
            Category: {ticket_category}
            Priority: {priority}
            Description: {description}
            
            Based on this information, provide:
            1. Primary technical skills required (e.g., Network Administration, Hardware Repair, Software Support)
            2. Secondary skills that would be helpful
            3. Complexity level (1-5, where 5 is most complex)
            4. Estimated resolution time in hours
            
            Return as JSON format:
            {{
                "primary_skills": ["skill1", "skill2"],
                "secondary_skills": ["skill3", "skill4"],
                "complexity": 3,
                "estimated_hours": 4,
                "urgency_factor": 1.0
            }}
            """
            
            # Use Snowflake Cortex for analysis
            query = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'mixtral-8x7b',
                '{analysis_prompt}'
            ) as skill_analysis
            """
            
            result = self.db_connection.execute_query(query)
            
            if result and len(result) > 0:
                analysis_text = result[0]['SKILL_ANALYSIS']
                # Parse JSON from LLM response
                try:
                    # Extract JSON from response
                    start_idx = analysis_text.find('{')
                    end_idx = analysis_text.rfind('}') + 1
                    if start_idx != -1 and end_idx != -1:
                        json_str = analysis_text[start_idx:end_idx]
                        skill_analysis = json.loads(json_str)
                        logger.info(f"✅ Skill analysis completed for ticket")
                        return skill_analysis
                except json.JSONDecodeError:
                    logger.warning("Failed to parse LLM response as JSON, using fallback")
            
            # Fallback analysis based on category
            return self._fallback_skill_analysis(ticket_category, priority)
            
        except Exception as e:
            logger.error(f"Error in skill analysis: {str(e)}")
            return self._fallback_skill_analysis(
                classified_ticket.get('classified_data', {}).get('TICKETCATEGORY', {}), 
                classified_ticket.get('classified_data', {}).get('PRIORITY', {})
            )
    
    def _extract_label(self, field_data) -> str:
        """Extract label from classification field data."""
        if isinstance(field_data, dict):
            return field_data.get('Label', 'Unknown')
        return str(field_data) if field_data else 'Unknown'
    
    def _fallback_skill_analysis(self, category_data, priority_data) -> Dict:
        """Fallback skill analysis when LLM fails."""
        category = self._extract_label(category_data)
        priority = self._extract_label(priority_data)
        
        # Skill mapping based on category
        skill_mapping = {
            'Network': {
                'primary_skills': ['Network Administration', 'TCP/IP', 'Router Configuration'],
                'secondary_skills': ['Firewall Management', 'VPN Setup'],
                'complexity': 3,
                'estimated_hours': 4
            },
            'Hardware': {
                'primary_skills': ['Hardware Repair', 'Computer Assembly', 'Diagnostics'],
                'secondary_skills': ['Driver Installation', 'BIOS Configuration'],
                'complexity': 2,
                'estimated_hours': 3
            },
            'Software': {
                'primary_skills': ['Software Installation', 'Application Support', 'Troubleshooting'],
                'secondary_skills': ['Registry Editing', 'System Configuration'],
                'complexity': 2,
                'estimated_hours': 2
            },
            'Security': {
                'primary_skills': ['Security Analysis', 'Malware Removal', 'Access Control'],
                'secondary_skills': ['Encryption', 'Audit Compliance'],
                'complexity': 4,
                'estimated_hours': 6
            }
        }
        
        # Priority urgency factor
        urgency_factors = {
            'Critical': 2.0,
            'High': 1.5,
            'Medium': 1.0,
            'Low': 0.8
        }
        
        analysis = skill_mapping.get(category, skill_mapping['Software'])
        analysis['urgency_factor'] = urgency_factors.get(priority, 1.0)
        
        return analysis
    
    def get_available_technicians(self) -> List[Dict]:
        """
        Query Snowflake to get available technicians with their skills and workload.
        
        Returns:
            List[Dict]: List of available technicians
        """
        try:
            query = """
            SELECT 
                TECHNICIAN_ID,
                NAME,
                EMAIL,
                SKILLS,
                AVAILABILITY_STATUS,
                CURRENT_WORKLOAD,
                MAX_CAPACITY,
                ROLE,
                EXPERIENCE_LEVEL,
                LAST_ASSIGNMENT_DATE
            FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
            WHERE AVAILABILITY_STATUS = 'Available'
            ORDER BY CURRENT_WORKLOAD ASC, EXPERIENCE_LEVEL DESC
            """
            
            result = self.db_connection.execute_query(query)
            
            if result:
                logger.info(f"✅ Retrieved {len(result)} available technicians")
                return result
            else:
                logger.warning("No available technicians found")
                return []
                
        except Exception as e:
            logger.error(f"Error retrieving technicians: {str(e)}")
            return []
    
    def calculate_technician_score(self, technician: Dict, skill_requirements: Dict) -> float:
        """
        Calculate how well a technician matches the skill requirements.
        
        Args:
            technician (Dict): Technician data
            skill_requirements (Dict): Required skills analysis
            
        Returns:
            float: Matching score (0-100)
        """
        try:
            score = 0.0
            
            # Parse technician skills
            tech_skills = technician.get('SKILLS', '').lower().split(',')
            tech_skills = [skill.strip() for skill in tech_skills]
            
            required_primary = [skill.lower() for skill in skill_requirements.get('primary_skills', [])]
            required_secondary = [skill.lower() for skill in skill_requirements.get('secondary_skills', [])]
            
            # Primary skill matching (60% weight)
            primary_matches = 0
            for req_skill in required_primary:
                for tech_skill in tech_skills:
                    if req_skill in tech_skill or tech_skill in req_skill:
                        primary_matches += 1
                        break
            
            if required_primary:
                primary_score = (primary_matches / len(required_primary)) * 60
            else:
                primary_score = 30  # Default if no primary skills specified
            
            # Secondary skill matching (20% weight)
            secondary_matches = 0
            for req_skill in required_secondary:
                for tech_skill in tech_skills:
                    if req_skill in tech_skill or tech_skill in req_skill:
                        secondary_matches += 1
                        break
            
            if required_secondary:
                secondary_score = (secondary_matches / len(required_secondary)) * 20
            else:
                secondary_score = 10  # Default if no secondary skills specified
            
            # Workload factor (15% weight)
            current_workload = technician.get('CURRENT_WORKLOAD', 0)
            max_capacity = technician.get('MAX_CAPACITY', 10)
            workload_ratio = current_workload / max_capacity if max_capacity > 0 else 1
            workload_score = (1 - workload_ratio) * 15
            
            # Experience factor (5% weight)
            experience_level = technician.get('EXPERIENCE_LEVEL', 1)
            experience_score = min(experience_level / 5, 1) * 5
            
            score = primary_score + secondary_score + workload_score + experience_score
            
            logger.debug(f"Technician {technician.get('NAME')} score: {score:.2f}")
            return score
            
        except Exception as e:
            logger.error(f"Error calculating technician score: {str(e)}")
            return 0.0
