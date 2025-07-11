"""
AI/LLM processing module for TeamLogic-AutoTask application.
Handles metadata extraction, ticket classification, and resolution generation using LLM.
"""

import json
import re
from typing import Dict, List, Optional
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database import SnowflakeConnection


class AIProcessor:
    """
    Handles AI/LLM operations including metadata extraction, classification, and resolution generation.
    """

    def __init__(self, db_connection: SnowflakeConnection, reference_data: Dict):
        """
        Initialize the AI processor.

        Args:
            db_connection (SnowflakeConnection): Database connection for LLM calls
            reference_data (dict): Reference data for classification mappings
        """
        self.db_connection = db_connection
        self.reference_data = reference_data

    def extract_metadata(self, title: str, description: str, model: str = 'llama3-8b') -> Optional[Dict]:
        """
        Extracts structured metadata from the ticket title and description using LLM.

        Args:
            title (str): Ticket title
            description (str): Ticket description
            model (str): LLM model to use

        Returns:
            dict: Extracted metadata or None if failed
        """
        prompt = f"""
        Analyze the following IT support ticket title and description and extract the specified metadata in JSON format.
        Ensure all fields are present. For urgency_level, analyze the impact and urgency based on the issue described.

        Ticket Title: "{title}"
        Ticket Description: "{description}"

        Guidelines for urgency_level assessment:
        - "Critical": System down, security breach, data loss, business-critical functions unavailable
        - "High": Major functionality impaired, multiple users affected, workarounds difficult
        - "Medium": Single user affected, workarounds available, non-critical functions impaired
        - "Low": Minor issues, cosmetic problems, feature requests, general questions

        Guidelines for error_messages extraction:
        - Look for specific error codes, error numbers, or exact error text in quotes
        - Include popup messages, dialog box text, or system-generated messages
        - Examples: "Error 404", "Connection timeout", "Access denied", "File not found"
        - If no specific error message is mentioned, extract any symptoms or failure descriptions

        JSON Schema:
        {{
            "main_issue": "What is the main issue or problem described?",
            "affected_system": "What system or application is affected?",
            "urgency_level": "Assess urgency based on impact and business criticality (Critical, High, Medium, or Low)",
            "error_messages": "Extract any specific error messages, codes, or failure symptoms mentioned in the ticket",
            "technical_keywords": ["list", "of", "technical", "terms", "separated", "by", "comma"],
            "user_actions": "What actions was the user trying to perform when the issue occurred?",
            "resolution_indicators": "What type of resolution approach or common fix might address this issue?",
            "STATUS": "Open"
        }}
        """
        print("Extracting metadata with LLM...")
        extracted_data = self.db_connection.call_cortex_llm(prompt, model=model)
        if extracted_data:
            extracted_data["STATUS"] = "Open"
        return extracted_data

    def classify_ticket(self, new_ticket_data: Dict, extracted_metadata: Dict,
                       similar_tickets: List[Dict], model: str = 'mixtral-8x7b') -> Optional[Dict]:
        """
        Classifies the new ticket (ISSUETYPE, SUBISSUETYPE, TICKETCATEGORY, TICKETTYPE, PRIORITY)
        based on extracted metadata and similar tickets using LLM.

        Args:
            new_ticket_data (dict): New ticket data
            extracted_metadata (dict): Extracted metadata
            similar_tickets (list): List of similar tickets
            model (str): LLM model to use

        Returns:
            dict: Classification data or None if failed
        """
        from collections import Counter

        # Summarize similar tickets
        summary = {}
        for field in ["ISSUETYPE", "SUBISSUETYPE", "TICKETCATEGORY", "TICKETTYPE", "PRIORITY"]:
            values = [ticket.get(field) for ticket in similar_tickets if ticket.get(field) not in [None, "N/A"]]
            if values:
                most_common, count = Counter(values).most_common(1)[0]
                summary[field] = {"Value": most_common, "Count": count}

        summary_str = "\nMost common classification values among similar tickets:\n"
        for field, info in summary.items():
            label = self.reference_data.get(field.lower(), {}).get(str(info["Value"]), "Unknown")
            summary_str += f"{field}: {info['Value']} (Label: {label}, appeared {info['Count']} times)\n"

        classification_prompt = f"""
        You are an expert IT support ticket classifier. Based on the new ticket details and similar historical tickets,
        classify the new ticket for the following categories: ISSUETYPE, SUBISSUETYPE, TICKETCATEGORY, TICKETTYPE, and PRIORITY.
        The STATUS should be 'Open'.

        New Ticket Title: "{new_ticket_data['title']}"
        New Ticket Description: "{new_ticket_data['description']}"
        New Ticket Extracted Metadata: {json.dumps(extracted_metadata, indent=2)}
        New Ticket Initial Priority: "{new_ticket_data['priority']}"

        Consider the following similar historical tickets for classification context:
        """

        MAX_SIMILAR_TICKETS_FOR_PROMPT = 15
        if similar_tickets:
            for i, ticket in enumerate(similar_tickets[:MAX_SIMILAR_TICKETS_FOR_PROMPT]):
                # Safely handle None values in ticket data
                title = ticket.get('TITLE') or 'N/A'
                title_truncated = title[:100] if isinstance(title, str) else 'N/A'

                classification_prompt += f"""
                --- Similar Ticket {i+1} ---
                Title: {title_truncated}
                ISSUE_TYPE: {ticket.get('ISSUETYPE', 'N/A')}
                SUBISSUE_TYPE: {ticket.get('SUBISSUETYPE', 'N/A')}
                CATEGORY: {ticket.get('TICKETCATEGORY', 'N/A')}
                TYPE: {ticket.get('TICKETTYPE', 'N/A')}
                PRIORITY: {ticket.get('PRIORITY', 'N/A')}
                """
        else:
            classification_prompt += "\nNo similar historical tickets found to provide additional context."

        classification_prompt += summary_str
        classification_prompt += """
\n\nAvailable Classification Options (Field: {Value: Label, ...}):\n"""
        classification_fields = ["issuetype", "subissuetype", "ticketcategory", "tickettype", "priority", "status"]

        for field_name in classification_fields:
            if field_name in self.reference_data:
                options_str = ", ".join([f'"{val}": "{label}"' for val, label in self.reference_data[field_name].items()])
                classification_prompt += f"  {field_name.upper()}: {{{options_str}}}\n"
            else:
                classification_prompt += f"  {field_name.upper()}: No specific options provided.\n"

        classification_prompt += """
\n\nIMPORTANT: For each classification field, especially SUBISSUETYPE, analyze the metadata and values of the similar historical tickets above. If any similar ticket has a clear value for SUBISSUETYPE, use the most relevant one as a strong suggestion for the new ticket. Only use "N/A" if absolutely no similar context or option applies. If unsure, select the closest reasonable option from the available list.\n\nBased on all the provided information and the available options, determine the classification for the New Ticket in JSON format.\nFor each classification field, provide both the `Value` (numerical ID) and the `Label` (descriptive name) from the provided options.\nIf a precise match cannot be determined for a field, choose the closest reasonable option or use "N/A" for the Label and an appropriate default/null for Value.\nThe `PRIORITY` should be re-evaluated based on the issue's urgency and impact, considering the initial priority and the provided priority options.\n\nJSON Schema:\n{{\n    \"ISSUETYPE\": {{ \"Value\": \"numerical_id\", \"Label\": \"Descriptive Label\" }},\n    \"SUBISSUETYPE\": {{ \"Value\": \"numerical_id\", \"Label\": \"Descriptive Label\" }},\n    \"TICKETCATEGORY\": {{ \"Value\": \"numerical_id\", \"Label\": \"Descriptive Label\" }},\n    \"TICKETTYPE\": {{ \"Value\": \"numerical_id\", \"Label\": \"Descriptive Label\" }},\n    \"STATUS\": {{ \"Value\": \"numerical_id\", \"Label\": \"Descriptive Label\" }},\n    \"PRIORITY\": {{ \"Value\": \"numerical_id\", \"Label\": \"Descriptive Label\" }}\n}}\n"""

        print("Classifying ticket with LLM...")
        classified_data = self.db_connection.call_cortex_llm(classification_prompt, model=model)

        # Handle case where LLM returns None
        if not classified_data:
            print("LLM classification failed, using fallback classification based on similar tickets")
            classified_data = {}

            # Use most common values from similar tickets as fallback
            for field in ["ISSUETYPE", "SUBISSUETYPE", "TICKETCATEGORY", "TICKETTYPE", "PRIORITY"]:
                if field in summary:
                    label = self.reference_data.get(field.lower(), {}).get(str(summary[field]["Value"]), "Unknown")
                    classified_data[field] = {"Value": summary[field]["Value"], "Label": label}
                else:
                    # Default fallback values if no similar tickets
                    default_values = {
                        "ISSUETYPE": {"Value": "5", "Label": "Software/SaaS"},
                        "SUBISSUETYPE": {"Value": "73", "Label": "MS Office"},
                        "TICKETCATEGORY": {"Value": "3", "Label": "Standard"},
                        "TICKETTYPE": {"Value": "2", "Label": "Incident"},
                        "PRIORITY": {"Value": "2", "Label": "Medium"}
                    }
                    classified_data[field] = default_values.get(field, {"Value": "N/A", "Label": "Unknown"})

        # Set STATUS field
        if classified_data and "status" in self.reference_data:
            new_status_info = next(((val, label) for val, label in self.reference_data["status"].items() if label == "New"), ("N/A", "New"))
            classified_data["STATUS"] = {"Value": new_status_info[0], "Label": new_status_info[1]}
        elif classified_data:
            classified_data["STATUS"] = {"Value": "N/A", "Label": "Open"}

        # Fallback: For any field, use the most common value from similar tickets if LLM returns N/A
        if classified_data:
            for field in ["ISSUETYPE", "SUBISSUETYPE", "TICKETCATEGORY", "TICKETTYPE", "PRIORITY"]:
                # Safely check if field exists and has a Value
                field_data = classified_data.get(field, {})
                if isinstance(field_data, dict) and field_data.get("Value") in [None, "N/A"] and field in summary:
                    label = self.reference_data.get(field.lower(), {}).get(str(summary[field]["Value"]), "Unknown")
                    classified_data[field] = {"Value": summary[field]["Value"], "Label": label}

        return classified_data

    def generate_resolution_note(self, ticket_data: Dict, classified_data: Dict,
                                extracted_metadata: Dict) -> str:
        """
        Generates a resolution note using Cortex LLM, based solely on the extracted metadata of the ticket.

        Args:
            ticket_data (dict): Original ticket data
            classified_data (dict): Classification results
            extracted_metadata (dict): Extracted metadata

        Returns:
            str: Generated resolution note
        """
        print("Generating resolution using Cortex LLM based on extracted metadata...")

        title = ticket_data.get('title', '')
        description = ticket_data.get('description', '')

        # Prepare a focused prompt for the LLM
        prompt = f'''
        You are an expert IT support analyst. Based on the following extracted metadata from an IT support ticket, generate a concise, actionable resolution note with clear, numbered steps for the end-user to follow. The resolution should directly address the main issue and context provided by the metadata. Do not include any generic or irrelevant steps. Do not reference unavailable information. Do not include any JSON or code formatting in your response—just the step-by-step resolution as plain text.

        Extracted Metadata:
        - Main Issue: {extracted_metadata.get('main_issue', 'N/A')}
        - Affected System: {extracted_metadata.get('affected_system', 'N/A')}
        - Urgency Level: {extracted_metadata.get('urgency_level', 'N/A')}
        - Error Messages: {extracted_metadata.get('error_messages', 'N/A')}
        - Technical Keywords: {', '.join(extracted_metadata.get('technical_keywords', []))}
        - User Actions: {extracted_metadata.get('user_actions', 'N/A')}
        - Suggested Resolution Approach: {extracted_metadata.get('resolution_indicators', 'N/A')}

        Instructions:
        1. Generate a step-by-step resolution plan tailored to the main issue and context above.
        2. The steps should be practical for an end-user to perform.
        3. Do not include any JSON, code blocks, or explanations—just the resolution steps as plain text.
        4. Number each step clearly.
        5. If information is missing, focus only on the available metadata.
        '''

        print("Calling Cortex LLM for resolution generation...")
        llm_response = self.db_connection.call_cortex_llm(prompt, model='mixtral-8x7b', expect_json=False)

        if isinstance(llm_response, str) and llm_response.strip():
            return llm_response.strip()
        else:
            return "Resolution could not be generated at this time. Please try again later."