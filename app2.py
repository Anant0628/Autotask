import streamlit as st
import json
import snowflake.connector
from datetime import datetime, timedelta, date
import os
from collections import Counter
import pandas as pd
from typing import List, Dict
import plotly.express as px
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class IntakeClassificationAgent:
    """
    An AI Agent for intake and classification of support tickets using Snowflake Cortex.
    """
    def __init__(self, sf_account, sf_user, sf_password, sf_warehouse, sf_database, sf_schema, sf_role, sf_passcode, data_ref_file='data.txt'):
        """
        Initializes the agent with Snowflake connection details and loads reference data.

        Args:
            sf_account (str): Snowflake account identifier.
            sf_user (str): Snowflake username.
            sf_password (str): Snowflake password.
            sf_warehouse (str): Snowflake warehouse to use.
            sf_database (str): Snowflake database to use.
            sf_schema (str): Snowflake schema to use.
            sf_role (str): Snowflake role to use.
            sf_passcode (str): Snowflake MFA passcode (if applicable).
            data_ref_file (str): Path to the data.txt file containing reference mappings.
        """
        self.sf_account = sf_account
        self.sf_user = sf_user
        self.sf_password = sf_password
        self.sf_warehouse = sf_warehouse
        self.sf_database = sf_database
        self.sf_schema = sf_schema
        self.sf_role = sf_role 
        self.sf_passcode = sf_passcode 
        self.conn = None
        self.data_ref_file = data_ref_file
        self.reference_data = {}
        
        self._connect_to_snowflake()
        self._load_reference_data()

    def _connect_to_snowflake(self):
        """Establishes a connection to Snowflake."""
        try:
            self.conn = snowflake.connector.connect(
                user=self.sf_user,
                password=self.sf_password,
                account=self.sf_account,
                warehouse=self.sf_warehouse,
                database=self.sf_database,
                schema=self.sf_schema,
                role=self.sf_role,      
                passcode=self.sf_passcode 
            )
            print("Successfully connected to Snowflake.")
        except Exception as e:
            print(f"Error connecting to Snowflake: {e}")
            self.conn = None

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

    def _execute_snowflake_query(self, query, params=None):
        """
        Executes a SQL query on Snowflake and returns the results.

        Args:
            query (str): The SQL query string.
            params (tuple, optional): Parameters to pass to the query. Defaults to None.

        Returns:
            list: A list of dictionaries, where each dictionary represents a row.
                  Returns an empty list on error or no results.
        """
        if not self.conn:
            print("Not connected to Snowflake. Please check connection.")
            return []

        try:
            with self.conn.cursor(snowflake.connector.DictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()
        except Exception as e:
            print(f"Error executing Snowflake query: {e}")
            return []

    def _call_snowflake_cortex_llm(self, prompt_text, model='mixtral-8x7b'):
        """
        Calls the Snowflake Cortex LLM (CORTEX_COMPLETE) with the given prompt.
        """
        if not self.conn:
            print("Cannot call LLM: Not connected to Snowflake.")
            return None

        import re
        escaped_prompt_text = prompt_text.replace("'", "''")
        query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE('{model}', '{escaped_prompt_text}') AS LLM_RESPONSE;
        """
        print(f"Calling Snowflake Cortex LLM with model: {model}...")
        results = self._execute_snowflake_query(query)

        if results and results[0]['LLM_RESPONSE']:
            try:
                response_str = results[0]['LLM_RESPONSE']
                # Extract JSON block from LLM response
                match = re.search(r'```json\\s*(\\{[\\s\\S]*?\\})\\s*```', response_str)
                if not match:
                    match = re.search(r'```\\s*(\\{[\\s\\S]*?\\})\\s*```', response_str)
                if match:
                    response_str = match.group(1)
                else:
                    # Try to find the first { ... } block
                    match = re.search(r'(\{[\s\S]*\})', response_str)
                    if match:
                        response_str = match.group(1)
                return json.loads(response_str)
            except json.JSONDecodeError as e:
                print(f"Error decoding LLM response JSON: {e}")
                print(f"Raw LLM response: {results[0]['LLM_RESPONSE']}")
                return None
        return None

    def extract_metadata(self, title, description, model='llama3-8b'):
        """
        Extracts structured metadata from the ticket title and description using LLM.
        """
        prompt = f"""
        Analyze the following IT support ticket title and description and extract the specified metadata in JSON format.
        Ensure all fields are present. If a field cannot be determined, use "N/A" for strings or empty list for arrays.

        Ticket Title: "{title}"
        Ticket Description: "{description}"

        JSON Schema:
        {{
            "main_issue": "What is the main issue or problem described?",
            "affected_system": "What system or application is affected?",
            "urgency_level": "What is the urgency level of this issue? (e.g., Low, Medium, High, Critical)",
            "error_messages": "Are there any exact error messages mentioned?",
            "technical_keywords": ["list", "of", "technical", "terms", "separated", "by", "comma"],
            "user_actions": "What actions was the user trying to perform when the issue occurred?",
            "resolution_indicators": "What type of resolution approach or common fix might address this issue?",
            "STATUS": "Open"
        }}
        """
        print("Extracting metadata with LLM...")
        extracted_data = self._call_snowflake_cortex_llm(prompt, model=model)
        if extracted_data:
            extracted_data["STATUS"] = "Open" 
        return extracted_data

    def find_similar_tickets(self, extracted_metadata):
        """
        Searches the Snowflake database for similar tickets based on extracted metadata.
        Uses AND for main fields and OR for keywords for more relevant results.
        """
        if not extracted_metadata:
            return []

        search_conditions = []
        params = []

        main_issue = extracted_metadata.get("main_issue")
        affected_system = extracted_metadata.get("affected_system")
        # Ensure affected_system is a string
        if isinstance(affected_system, list):
            affected_system = affected_system[0] if affected_system else None
        error_messages = extracted_metadata.get("error_messages")
        technical_keywords = extracted_metadata.get("technical_keywords", [])

        # Use OR for all main fields to increase match chance
        if main_issue and main_issue != "N/A":
            search_conditions.append("(TITLE ILIKE %s OR DESCRIPTION ILIKE %s)")
            params.extend([f"%{main_issue}%", f"%{main_issue}%"])
        if affected_system and affected_system != "N/A":
            search_conditions.append("(TITLE ILIKE %s OR DESCRIPTION ILIKE %s)")
            params.extend([f"%{affected_system}%", f"%{affected_system}%"])
        if error_messages and error_messages != "N/A":
            search_conditions.append("(DESCRIPTION ILIKE %s)")
            params.append(f"%{error_messages}%")

        # Use OR for keywords
        keyword_conditions = []
        for keyword in technical_keywords:
            if keyword and keyword != "N/A":
                keyword_conditions.append("(TITLE ILIKE %s OR DESCRIPTION ILIKE %s)")
                params.extend([f"%{keyword}%", f"%{keyword}%"])

        where_clause = ""
        if search_conditions:
            where_clause = "WHERE " + " OR ".join(search_conditions)
        if keyword_conditions:
            if where_clause:
                where_clause += " OR (" + " OR ".join(keyword_conditions) + ")"
            else:
                where_clause = "WHERE " + " OR ".join(keyword_conditions)

        query = f"""
        SELECT
            TITLE,
            DESCRIPTION,
            ISSUETYPE,
            SUBISSUETYPE,
            TICKETCATEGORY,
            TICKETTYPE,
            PRIORITY,
            STATUS
        FROM TEST_DB.PUBLIC.COMPANY_4130_DATA
        {where_clause}
        LIMIT 50; -- Limit to top 50 similar tickets for context
        """
        print(f"Searching for similar tickets with query: {query.strip().splitlines()[0]}...")
        similar_tickets = self._execute_snowflake_query(query, tuple(params))
        return similar_tickets

    def _summarize_similar_tickets(self, similar_tickets):
        """
        Summarizes the most common values for each classification field among similar tickets.
        """
        summary = {}
        for field in ["ISSUETYPE", "SUBISSUETYPE", "TICKETCATEGORY", "TICKETTYPE", "PRIORITY"]:
            values = [ticket.get(field) for ticket in similar_tickets if ticket.get(field) not in [None, "N/A"]]
            if values:
                most_common, count = Counter(values).most_common(1)[0]
                summary[field] = {"Value": most_common, "Count": count}
        return summary

    def classify_ticket(self, new_ticket_data, extracted_metadata, similar_tickets, model='mixtral-8x7b'):
        """
        Classifies the new ticket (ISSUETYPE, SUBISSUETYPE, TICKETCATEGORY, TICKETTYPE, PRIORITY)
        based on extracted metadata and similar tickets using LLM.
        Uses the loaded reference data to guide the LLM to output valid numerical values and labels.
        """
        summary = self._summarize_similar_tickets(similar_tickets)
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
                classification_prompt += f"""
                --- Similar Ticket {i+1} ---
                Title: {ticket.get('TITLE', 'N/A')[:100]}
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
\n\nIMPORTANT: For each classification field, especially SUBISSUETYPE, analyze the metadata and values of the similar historical tickets above. If any similar ticket has a clear value for SUBISSUETYPE, use the most relevant one as a strong suggestion for the new ticket. Only use \"N/A\" if absolutely no similar context or option applies. If unsure, select the closest reasonable option from the available list.\n\nBased on all the provided information and the available options, determine the classification for the New Ticket in JSON format.\nFor each classification field, provide both the `Value` (numerical ID) and the `Label` (descriptive name) from the provided options.\nIf a precise match cannot be determined for a field, choose the closest reasonable option or use \"N/A\" for the Label and an appropriate default/null for Value.\nThe `PRIORITY` should be re-evaluated based on the issue's urgency and impact, considering the initial priority and the provided priority options.\n\nJSON Schema:\n{{\n    \"ISSUETYPE\": {{ \"Value\": \"numerical_id\", \"Label\": \"Descriptive Label\" }},\n    \"SUBISSUETYPE\": {{ \"Value\": \"numerical_id\", \"Label\": \"Descriptive Label\" }},\n    \"TICKETCATEGORY\": {{ \"Value\": \"numerical_id\", \"Label\": \"Descriptive Label\" }},\n    \"TICKETTYPE\": {{ \"Value\": \"numerical_id\", \"Label\": \"Descriptive Label\" }},\n    \"STATUS\": {{ \"Value\": \"numerical_id\", \"Label\": \"Descriptive Label\" }},\n    \"PRIORITY\": {{ \"Value\": \"numerical_id\", \"Label\": \"Descriptive Label\" }}\n}}\n"""
        print("Classifying ticket with LLM...")
        classified_data = self._call_snowflake_cortex_llm(classification_prompt, model=model)
        
        if classified_data and "status" in self.reference_data: 
            new_status_info = next(((val, label) for val, label in self.reference_data["status"].items() if label == "New"), ("N/A", "New"))
            classified_data["STATUS"] = {"Value": new_status_info[0], "Label": new_status_info[1]}
        elif classified_data:
            classified_data["STATUS"] = {"Value": "N/A", "Label": "Open"}

        # Fallback: For any field, use the most common value from similar tickets if LLM returns N/A
        if classified_data:
            for field in ["ISSUETYPE", "SUBISSUETYPE", "TICKETCATEGORY", "TICKETTYPE", "PRIORITY"]:
                if classified_data.get(field, {}).get("Value") in [None, "N/A"] and field in summary:
                    label = self.reference_data.get(field.lower(), {}).get(str(summary[field]["Value"]), "Unknown")
                    classified_data[field] = {"Value": summary[field]["Value"], "Label": label}

        return classified_data

    def fetch_reference_tickets(self):
        """
        Fetches actual historical tickets with real, detailed resolutions.
        """
        query = """
            SELECT TITLE, DESCRIPTION, ISSUETYPE, SUBISSUETYPE, PRIORITY, RESOLUTION
            FROM TEST_DB.PUBLIC.COMPANY_4130_DATA
            WHERE RESOLUTION IS NOT NULL
            AND RESOLUTION != ''
            AND RESOLUTION != 'N/A'
            AND RESOLUTION != 'None'
            AND RESOLUTION NOT LIKE '%contact%'
            AND RESOLUTION NOT LIKE '%escalate%'
            AND RESOLUTION NOT LIKE '%call%'
            AND LENGTH(RESOLUTION) > 50
            AND TITLE IS NOT NULL
            AND DESCRIPTION IS NOT NULL
            AND LENGTH(TITLE) > 10
            AND LENGTH(DESCRIPTION) > 20
            ORDER BY LENGTH(RESOLUTION) DESC, RANDOM()
            LIMIT 200
        """
        print("Fetching actual historical tickets with real resolutions...")
        results = self._execute_snowflake_query(query)

        if results:
            df = pd.DataFrame(results)
            print(f"Fetched {len(df)} historical tickets")

            # Additional filtering for actual technical resolutions
            df = df[df['RESOLUTION'].str.len() > 50]  # Ensure substantial resolutions

            # Filter out generic responses
            generic_patterns = [
                'please try', 'contact support', 'escalate to', 'call helpdesk',
                'generic solution', 'standard procedure', 'follow up with'
            ]

            for pattern in generic_patterns:
                df = df[~df['RESOLUTION'].str.contains(pattern, case=False, na=False)]

            # Keep only resolutions with actual technical content
            technical_indicators = [
                'restart', 'configure', 'install', 'update', 'check', 'verify',
                'run', 'execute', 'open', 'close', 'delete', 'create', 'modify',
                'setting', 'option', 'parameter', 'file', 'folder', 'registry',
                'service', 'process', 'application', 'system'
            ]

            technical_mask = df['RESOLUTION'].str.contains('|'.join(technical_indicators), case=False, na=False)
            df = df[technical_mask]

            print(f"After filtering for actual technical resolutions: {len(df)} tickets available")

            # Show sample data for verification
            if len(df) > 0:
                print("Sample actual resolution data:")
                for i, row in df.head(2).iterrows():
                    print(f"  Title: {str(row.get('TITLE', 'N/A'))[:60]}...")
                    print(f"  Issue Type: {str(row.get('ISSUETYPE', 'N/A'))}")
                    print(f"  Resolution Length: {len(str(row.get('RESOLUTION', '')))} characters")
                    print(f"  Resolution Preview: {str(row.get('RESOLUTION', 'N/A'))[:150]}...")
                    print("  ---")

            return df
        else:
            print("No historical tickets found")
            return pd.DataFrame()

    def get_similarity_score(self, new_text, historical_texts):
        """
        TF-IDF based similarity comparison for resolution matching.
        """
        if not historical_texts or len(historical_texts) == 0:
            print("No historical texts provided for similarity calculation")
            return []

        # Clean and validate texts
        new_text = str(new_text).strip()
        historical_texts = [str(text).strip() for text in historical_texts if str(text).strip()]

        if not new_text or len(historical_texts) == 0:
            print("Empty texts after cleaning")
            return []

        try:
            # Use more flexible TF-IDF parameters
            tfidf = TfidfVectorizer(
                stop_words='english',
                max_features=1000,
                min_df=1,  # Include terms that appear in at least 1 document
                max_df=0.95,  # Exclude terms that appear in more than 95% of documents
                ngram_range=(1, 2)  # Include both unigrams and bigrams
            )

            all_texts = [new_text] + historical_texts
            print(f"Processing {len(all_texts)} texts for similarity calculation")

            vectors = tfidf.fit_transform(all_texts)
            cosine_sim = cosine_similarity(vectors[0:1], vectors[1:])

            similarities = cosine_sim[0]
            print(f"Calculated {len(similarities)} similarity scores")

            return similarities
        except Exception as e:
            print(f"Error calculating similarity: {e}")
            import traceback
            traceback.print_exc()
            return []

    def extract_technical_keywords(self, title, description):
        """
        Extract technical keywords and components from ticket title and description.
        """
        import re

        text = f"{title} {description}".lower()

        # Define technical keyword categories
        keywords = {
            'applications': ['outlook', 'excel', 'word', 'powerpoint', 'teams', 'chrome', 'firefox', 'safari', 'edge'],
            'systems': ['windows', 'mac', 'linux', 'server', 'database', 'sql', 'oracle', 'mysql'],
            'network': ['wifi', 'ethernet', 'vpn', 'firewall', 'router', 'switch', 'dns', 'dhcp'],
            'hardware': ['printer', 'monitor', 'keyboard', 'mouse', 'laptop', 'desktop', 'hard drive', 'memory'],
            'errors': ['error', 'crash', 'freeze', 'slow', 'timeout', 'connection', 'failed', 'denied'],
            'actions': ['login', 'password', 'access', 'install', 'update', 'backup', 'restore', 'sync']
        }

        found_keywords = {}
        for category, words in keywords.items():
            found = [word for word in words if word in text]
            if found:
                found_keywords[category] = found

        # Extract error codes (pattern: numbers/letters)
        error_codes = re.findall(r'\b(?:error|code)\s*[:\-]?\s*([a-z0-9\-]+)\b', text)
        if error_codes:
            found_keywords['error_codes'] = error_codes

        return found_keywords

    def generate_resolution_note(self, ticket_data, classified_data, extracted_metadata):
        """
        Generates a resolution note using Cortex LLM, based solely on the extracted metadata of the ticket.
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
        llm_response = self._call_snowflake_cortex_llm(prompt, model='mixtral-8x7b')

        if isinstance(llm_response, str):
            # If the LLM returns a plain string
            return llm_response.strip()
        elif isinstance(llm_response, dict) and 'resolution_note' in llm_response:
            return str(llm_response['resolution_note']).strip()
        elif llm_response:
            # If LLM returns something else, try to extract a string
            return str(llm_response).strip()
        else:
            return "Resolution could not be generated at this time. Please try again later."

    def _analyze_historical_patterns(self, df, ticket_data, technical_keywords):
        """
        Deep analysis of historical data to find patterns and extract technical solutions.
        """
        title = ticket_data.get('title', '').lower()
        description = ticket_data.get('description', '').lower()
        current_text = f"{title} {description}"

        print(f"Analyzing {len(df)} historical tickets for patterns...")

        # Group tickets by issue type and sub-issue type for pattern analysis
        pattern_groups = {}
        technical_solutions = {}

        for idx, row in df.iterrows():
            hist_title = str(row.get('TITLE', '')).lower()
            hist_desc = str(row.get('DESCRIPTION', '')).lower()
            hist_resolution = str(row.get('RESOLUTION', ''))
            issue_type = str(row.get('ISSUETYPE', ''))
            sub_issue_type = str(row.get('SUBISSUETYPE', ''))

            if not hist_resolution or len(hist_resolution.strip()) < 20:
                continue

            # Create pattern key
            pattern_key = f"{issue_type}_{sub_issue_type}"
            if pattern_key not in pattern_groups:
                pattern_groups[pattern_key] = []

            # Extract technical elements from historical resolution
            tech_elements = self._extract_technical_elements(hist_resolution)

            pattern_groups[pattern_key].append({
                'title': hist_title,
                'description': hist_desc,
                'resolution': hist_resolution,
                'tech_elements': tech_elements,
                'original_row': row
            })

        print(f"Found {len(pattern_groups)} different issue patterns")

        # Find best matching patterns
        best_matches = self._find_pattern_matches(pattern_groups, current_text, technical_keywords)

        return best_matches

        

    def _extract_technical_elements(self, resolution_text):
        """
        Extract technical elements, steps, and solutions from resolution text.
        """
        import re

        resolution_lower = resolution_text.lower()
        tech_elements = {
            'steps': [],
            'commands': [],
            'tools': [],
            'files': [],
            'settings': [],
            'errors': []
        }

        # Extract numbered steps
        steps = re.findall(r'\d+\.\s*([^.\n]+)', resolution_text)
        tech_elements['steps'] = [step.strip() for step in steps if len(step.strip()) > 5]

        # Extract commands (common patterns)
        commands = re.findall(r'(ipconfig|ping|netstat|restart|reboot|reset|clear|delete|install|update|run|execute)\s+[^\n.]*', resolution_lower)
        tech_elements['commands'] = list(set(commands))

        # Extract file paths and extensions
        files = re.findall(r'[a-zA-Z]:\\[^\s]+|[^\s]+\.[a-zA-Z]{2,4}', resolution_text)
        tech_elements['files'] = list(set(files))

        # Extract settings and configurations
        settings = re.findall(r'(setting|config|option|preference|parameter)[s]?\s*[:\-]?\s*([^\n.]+)', resolution_lower)
        tech_elements['settings'] = [setting[1].strip() for setting in settings if len(setting[1].strip()) > 3]

        # Extract error codes and messages
        errors = re.findall(r'error\s*[:\-]?\s*([^\n.]+)', resolution_lower)
        tech_elements['errors'] = [error.strip() for error in errors if len(error.strip()) > 3]

        return tech_elements

    def _find_pattern_matches(self, pattern_groups, current_text, technical_keywords):
        """
        Find the best matching patterns based on technical similarity.
        """
        matches = []

        for pattern_key, tickets in pattern_groups.items():
            if len(tickets) == 0:
                continue

            pattern_score = 0
            pattern_reasons = []
            best_ticket = None

            # Analyze each ticket in this pattern
            for ticket in tickets:
                ticket_score = 0
                ticket_reasons = []

                # Check for technical keyword matches
                hist_text = f"{ticket['title']} {ticket['description']} {ticket['resolution']}".lower()

                for category, keywords in technical_keywords.items():
                    for keyword in keywords:
                        if keyword in hist_text:
                            ticket_score += 3
                            ticket_reasons.append(f"tech_{category}: {keyword}")

                # Check for common technical elements
                tech_elements = ticket['tech_elements']
                if tech_elements['steps']:
                    ticket_score += len(tech_elements['steps']) * 0.5
                    ticket_reasons.append(f"has_steps: {len(tech_elements['steps'])}")

                if tech_elements['commands']:
                    ticket_score += len(tech_elements['commands']) * 2
                    ticket_reasons.append(f"has_commands: {tech_elements['commands'][:2]}")

                # Check for text similarity
                common_words = set(current_text.split()).intersection(set(hist_text.split()))
                if len(common_words) >= 3:
                    ticket_score += len(common_words) * 0.3
                    ticket_reasons.append(f"word_overlap: {len(common_words)}")

                if ticket_score > pattern_score:
                    pattern_score = ticket_score
                    pattern_reasons = ticket_reasons
                    best_ticket = ticket

            if pattern_score >= 3 and best_ticket:  # Minimum threshold for technical relevance
                matches.append({
                    'score': pattern_score,
                    'pattern': pattern_key,
                    'ticket': best_ticket,
                    'reasons': pattern_reasons,
                    'tech_elements': best_ticket['tech_elements']
                })

        # Sort by score and return top matches
        matches.sort(key=lambda x: x['score'], reverse=True)
        print(f"Found {len(matches)} technical pattern matches")

        return matches[:5]  # Top 5 technical matches

    def _create_technical_resolution(self, matches, ticket_data, technical_keywords):
        """
        Generate intelligent LLM-based resolution using technical insights from historical data.
        """
        best_match = matches[0]
        score = best_match['score']
        pattern = best_match['pattern']
        ticket = best_match['ticket']
        tech_elements = best_match['tech_elements']

        historical_resolution = ticket['resolution']
        similar_title = ticket['title']

        print(f"Analyzing technical patterns from: {similar_title[:50]}...")
        print(f"Generating LLM-based resolution using technical insights")

        # Extract technical insights from historical data
        technical_insights = self._extract_technical_insights(matches, technical_keywords)

        # Generate LLM-based resolution
        current_issue = f"{ticket_data.get('title', '')} - {ticket_data.get('description', '')}"

        llm_resolution = self._generate_llm_resolution(
            current_issue=current_issue,
            technical_insights=technical_insights,
            technical_keywords=technical_keywords,
            confidence_score=score,
            pattern=pattern
        )

        return llm_resolution

    def _extract_technical_insights(self, matches, technical_keywords):
        """
        Extract ONLY technical patterns and insights from historical matches, filtering out non-technical actions.
        """
        insights = {
            'technical_actions': [],
            'technical_steps': [],
            'tools_used': [],
            'configurations': [],
            'hardware_actions': [],
            'software_actions': []
        }

        # Non-technical patterns to filter out
        non_technical_patterns = [
            'call', 'contact', 'escalate', 'email', 'notify', 'inform', 'report',
            'schedule', 'appointment', 'meeting', 'discuss', 'consult', 'refer',
            'forward', 'transfer', 'assign', 'delegate', 'follow up', 'check back'
        ]

        for match in matches[:3]:  # Analyze top 3 matches
            resolution = match['ticket']['resolution'].lower()
            tech_elements = match['tech_elements']

            # Extract ONLY technical solution patterns
            technical_actions = []

            if 'restart' in resolution and not any(pattern in resolution for pattern in non_technical_patterns):
                technical_actions.append('restart')
            if 'update' in resolution and not any(pattern in resolution for pattern in non_technical_patterns):
                technical_actions.append('update')
            if 'install' in resolution and not any(pattern in resolution for pattern in non_technical_patterns):
                technical_actions.append('install')
            if 'configure' in resolution and not any(pattern in resolution for pattern in non_technical_patterns):
                technical_actions.append('configure')
            if 'replace' in resolution and not any(pattern in resolution for pattern in non_technical_patterns):
                technical_actions.append('replace')
            if 'repair' in resolution and not any(pattern in resolution for pattern in non_technical_patterns):
                technical_actions.append('repair')
            if 'reset' in resolution and not any(pattern in resolution for pattern in non_technical_patterns):
                technical_actions.append('reset')
            if 'clean' in resolution and not any(pattern in resolution for pattern in non_technical_patterns):
                technical_actions.append('clean')

            insights['technical_actions'].extend(technical_actions)

            # Extract technical steps (filter out non-technical ones)
            if tech_elements['steps']:
                for step in tech_elements['steps'][:5]:
                    step_lower = step.lower()
                    if not any(pattern in step_lower for pattern in non_technical_patterns):
                        # Only include if it contains technical keywords
                        if any(tech_word in step_lower for tech_word in [
                            'restart', 'update', 'install', 'configure', 'check', 'verify',
                            'run', 'execute', 'open', 'close', 'delete', 'create', 'modify',
                            'setting', 'driver', 'service', 'registry', 'file', 'folder'
                        ]):
                            insights['technical_steps'].append(step)

            # Extract tools and commands (filter out non-technical)
            if tech_elements['commands']:
                for cmd in tech_elements['commands']:
                    cmd_lower = cmd.lower()
                    if not any(pattern in cmd_lower for pattern in non_technical_patterns):
                        insights['tools_used'].append(cmd)

            # Extract configuration elements
            if tech_elements['settings']:
                for setting in tech_elements['settings']:
                    setting_lower = setting.lower()
                    if not any(pattern in setting_lower for pattern in non_technical_patterns):
                        insights['configurations'].append(setting)

        # Remove duplicates and limit items
        for key in insights:
            insights[key] = list(set(insights[key]))[:5]  # Max 5 items per category

        # Categorize actions into hardware vs software
        for action in insights['technical_actions']:
            if action in ['replace', 'repair', 'clean', 'connect']:
                insights['hardware_actions'].append(action)
            else:
                insights['software_actions'].append(action)

        return insights

    def _generate_llm_resolution(self, current_issue, technical_insights, technical_keywords, confidence_score, pattern):
        """
        Generate professional resolution in the exact format requested.
        """
        # Analyze the current issue to generate specific steps
        title = current_issue.split(' - ')[0] if ' - ' in current_issue else current_issue
        description = current_issue.split(' - ')[1] if ' - ' in current_issue else ""

        # Generate professional resolution steps
        resolution_steps = self._generate_professional_steps(title, description, technical_keywords, technical_insights)

        # Format in the exact style requested
        resolution = "To resolve this issue, the following steps will be taken:\n\n"

        for i, step in enumerate(resolution_steps, 1):
            resolution += f"{i}. {step}\n"

        return resolution.strip()

    def _generate_professional_steps(self, title, description, technical_keywords, technical_insights):
        """
        Generate professional resolution steps based on technical analysis from historical data or LLM generation.
        """
        issue_lower = f"{title} {description}".lower()

        # Check if we have technical insights from historical data
        has_technical_data = (
            technical_insights and
            (technical_insights.get('technical_actions') or
             technical_insights.get('technical_steps') or
             technical_insights.get('tools_used'))
        )

        if has_technical_data:
            print("Using technical insights from historical data")
            return self._generate_steps_from_technical_data(issue_lower, technical_keywords, technical_insights)
        else:
            print("No technical data found, generating LLM-based resolution")
            return self._generate_steps_from_llm_analysis(issue_lower, technical_keywords)

    def _generate_steps_from_technical_data(self, issue_lower, technical_keywords, technical_insights):
        """
        Generate actionable steps based on actual technical data from historical resolutions.
        """
        steps = []

        # Step 1: User diagnosis based on historical patterns
        component = self._identify_main_component(issue_lower, technical_keywords)
        steps.append(f"Check the {component} status and note any error messages or unusual behavior you observe.")

        # Step 2: Primary technical action based on historical data
        primary_action = self._determine_primary_action(technical_insights)
        if primary_action == 'restart':
            if 'service' in component.lower() or 'application' in component.lower():
                steps.append(f"Close and restart the {component}, or restart the related service through Services.msc.")
            else:
                steps.append(f"Restart your computer to reset the {component} and clear any temporary issues.")
        elif primary_action == 'update':
            steps.append(f"Download and install the latest drivers or updates for your {component} from the manufacturer's website.")
        elif primary_action == 'replace':
            steps.append(f"If the {component} is faulty, contact your IT support to arrange replacement with a compatible component.")
        elif primary_action == 'configure':
            steps.append(f"Access the {component} settings and reconfigure them according to your organization's standard parameters.")
        elif primary_action == 'repair':
            if 'application' in component.lower():
                steps.append(f"Uninstall and reinstall the {component} to repair any corrupted files.")
            else:
                steps.append(f"Run the built-in repair tools for your {component} or use System File Checker (sfc /scannow).")
        else:
            steps.append(f"Apply the appropriate technical solution for your {component} based on the specific symptoms.")

        # Step 3: Secondary action based on technical insights
        secondary_action = self._determine_secondary_action(technical_insights, primary_action)
        if secondary_action:
            if secondary_action == 'clean':
                steps.append(f"Clean any dust or debris from your {component} and clear temporary files or cache.")
            elif secondary_action == 'reset':
                steps.append(f"Reset the {component} settings to default values through its configuration panel.")
            elif secondary_action == 'install':
                steps.append(f"Install any additional software or drivers required for your {component} to function properly.")
            else:
                steps.append(f"Perform additional maintenance steps as recommended for your specific {component}.")
        else:
            steps.append(f"Optimize the {component} settings and perform any recommended maintenance to ensure stable operation.")

        # Step 4: User verification based on historical success patterns
        steps.append(f"Test the {component} thoroughly to confirm the issue is resolved and everything is working correctly.")

        return steps

    def _generate_steps_from_llm_analysis(self, issue_lower, technical_keywords):
        """
        Generate actionable steps that the user can perform to solve the issue.
        """
        # Determine the type of issue and generate appropriate actionable steps
        if any(keyword in issue_lower for keyword in ['fan', 'cooling', 'temperature', 'overheating']):
            return [
                "Check if the laptop fan is running by listening for fan noise or feeling for air flow from vents.",
                "Clean the laptop vents and fan using compressed air to remove dust and debris.",
                "Update the laptop's BIOS and thermal management drivers from the manufacturer's website.",
                "Test the laptop under normal usage to verify the fan operates correctly and temperatures are stable."
            ]

        elif any(keyword in issue_lower for keyword in ['network', 'internet', 'connection', 'wifi']):
            return [
                "Restart your router/modem by unplugging it for 30 seconds, then plugging it back in.",
                "Update your network adapter drivers through Device Manager or download from manufacturer's website.",
                "Reset your network settings by running 'ipconfig /flushdns' and 'netsh int ip reset' in Command Prompt as administrator.",
                "Test your internet connection by trying to access different websites or running a speed test."
            ]

        elif any(keyword in issue_lower for keyword in ['application', 'software', 'program', 'app']):
            app_name = self._extract_application_name(technical_keywords)
            return [
                f"Close {app_name} completely and restart it as an administrator (right-click > Run as administrator).",
                f"Uninstall and reinstall {app_name} using the latest version from the official website.",
                f"Check for and install any available updates for {app_name} through its settings or help menu.",
                f"Test {app_name} with a simple task to verify it's working correctly without errors."
            ]

        elif any(keyword in issue_lower for keyword in ['cloud', 'azure', 'aws', 'office365', 'sharepoint', 'onedrive']):
            return [
                "Check your internet connection and try accessing the cloud service from a different browser or incognito mode.",
                "Clear your browser cache and cookies, then sign out completely and sign back in to the cloud service.",
                "Verify your account credentials and check if multi-factor authentication (MFA) is working properly.",
                "Test accessing the cloud service from a different device or network to isolate connectivity issues."
            ]

        elif any(keyword in issue_lower for keyword in ['login', 'password', 'access', 'authentication']):
            return [
                "Try logging in with a different user account to determine if the issue is account-specific.",
                "Reset your password through your organization's password reset portal or contact your administrator.",
                "Clear your browser cache and cookies, then try logging in again using an incognito/private window.",
                "Verify your account hasn't been locked by checking with your system administrator or IT support."
            ]

        elif any(keyword in issue_lower for keyword in ['printer', 'printing', 'print']):
            return [
                "Check that your printer is powered on, connected properly, and has paper and ink/toner.",
                "Remove and reinstall your printer drivers by going to Settings > Printers & Scanners.",
                "Clear the print queue by opening Services, stopping 'Print Spooler', deleting files in C:\\Windows\\System32\\spool\\PRINTERS, then restarting the service.",
                "Print a test page from your printer's properties to verify it's working correctly."
            ]

        elif any(keyword in issue_lower for keyword in ['email', 'outlook', 'mail']):
            return [
                "Check your internet connection and verify your email server settings (IMAP/POP3/SMTP) are correct.",
                "Remove and re-add your email account in your email client with the correct server settings.",
                "Create a new Outlook profile by going to Control Panel > Mail > Show Profiles > Add.",
                "Test sending and receiving emails to confirm your email client is functioning properly."
            ]

        elif any(keyword in issue_lower for keyword in ['slow', 'performance', 'speed', 'lag']):
            return [
                "Open Task Manager (Ctrl+Shift+Esc) to identify and close any programs using high CPU or memory.",
                "Run Disk Cleanup to remove temporary files and free up disk space on your system drive.",
                "Disable unnecessary startup programs through Task Manager > Startup tab.",
                "Restart your computer and monitor performance to see if the issue is resolved."
            ]

        elif any(keyword in issue_lower for keyword in ['error', 'crash', 'freeze', 'hang']):
            return [
                "Note the exact error message and when it occurs, then search for the specific error code online.",
                "Update all your software and Windows through Settings > Update & Security > Windows Update.",
                "Run System File Checker by opening Command Prompt as administrator and typing 'sfc /scannow'.",
                "Test your system in Safe Mode to determine if the issue is caused by third-party software."
            ]

        elif any(keyword in issue_lower for keyword in ['hardware', 'device', 'driver']):
            device_name = self._extract_hardware_name(technical_keywords)
            return [
                f"Check that your {device_name} is properly connected and powered on.",
                f"Update your {device_name} drivers through Device Manager or download from the manufacturer's website.",
                f"Try connecting your {device_name} to a different port or computer to test if it's working.",
                f"Test your {device_name} functionality with its built-in diagnostic tools or software."
            ]

        else:
            # Generic actionable steps for unspecified issues
            return [
                "Document the exact error message, when it occurs, and what you were doing when it happened.",
                "Restart your computer and try to reproduce the issue to see if it persists.",
                "Check for and install any available Windows updates through Settings > Update & Security.",
                "Test the issue in Safe Mode or with a different user account to isolate the problem."
            ]

    def _identify_main_component(self, issue_lower, technical_keywords):
        """Identify the main component from the issue description."""
        if 'cloud' in technical_keywords and technical_keywords['cloud']:
            return f"{technical_keywords['cloud'][0]} service"
        elif 'applications' in technical_keywords and technical_keywords['applications']:
            return technical_keywords['applications'][0]
        elif 'hardware' in technical_keywords and technical_keywords['hardware']:
            return technical_keywords['hardware'][0]
        elif any(word in issue_lower for word in ['cloud', 'azure', 'aws', 'office365']):
            return "cloud service"
        elif any(word in issue_lower for word in ['network', 'internet', 'wifi']):
            return "network component"
        elif any(word in issue_lower for word in ['printer', 'print']):
            return "printer"
        elif any(word in issue_lower for word in ['email', 'outlook']):
            return "email system"
        else:
            return "system component"

    def _determine_primary_action(self, technical_insights):
        """Determine the primary technical action from historical data."""
        actions = technical_insights.get('technical_actions', [])
        if not actions:
            return None

        # Priority order for actions
        priority_actions = ['replace', 'repair', 'update', 'restart', 'configure', 'install']
        for action in priority_actions:
            if action in actions:
                return action

        return actions[0] if actions else None

    def _determine_secondary_action(self, technical_insights, primary_action):
        """Determine secondary action that's different from primary."""
        actions = technical_insights.get('technical_actions', [])
        for action in ['clean', 'reset', 'install', 'configure']:
            if action in actions and action != primary_action:
                return action
        return None

    def _extract_application_name(self, technical_keywords):
        """Extract application name from technical keywords or return generic term."""
        if 'applications' in technical_keywords and technical_keywords['applications']:
            return technical_keywords['applications'][0]
        return "application"

    def _extract_hardware_name(self, technical_keywords):
        """Extract hardware name from technical keywords or return generic term."""
        if 'hardware' in technical_keywords and technical_keywords['hardware']:
            return technical_keywords['hardware'][0]
        return "hardware component"

    def _generate_content_based_resolution(self, ticket_data, classified_data, technical_keywords):
        """
        Generate professional resolution in the exact format requested for new issues.
        """
        title = ticket_data.get('title', '')
        description = ticket_data.get('description', '')

        print(f"Generating professional resolution for new issue: {title}")
        print(f"Technical analysis: {technical_keywords}")

        # Generate professional resolution steps using the same method
        resolution_steps = self._generate_professional_steps(title, description, technical_keywords, {})

        # Format in the exact style requested
        resolution = "To resolve this issue, the following steps will be taken:\n\n"

        for i, step in enumerate(resolution_steps, 1):
            resolution += f"{i}. {step}\n"

        return resolution.strip()

    def _generate_classification_based_resolution(self, ticket_data, classified_data, technical_keywords):
        """
        Generate resolution based purely on the classified issue type, not database patterns.
        """
        # Get classification information
        issue_type = classified_data.get('ISSUETYPE', {}).get('Label', 'General')
        sub_issue_type = classified_data.get('SUBISSUETYPE', {}).get('Label', 'General')
        ticket_category = classified_data.get('TICKETCATEGORY', {}).get('Label', 'General')

        print(f"Generating resolution for: {issue_type} - {sub_issue_type} - {ticket_category}")

        # Generate steps based on classification
        resolution_steps = self._get_steps_by_classification(issue_type, sub_issue_type, ticket_category, technical_keywords)

        # Format in the standard style
        resolution = "To resolve this issue, the following steps will be taken:\n\n"

        for i, step in enumerate(resolution_steps, 1):
            resolution += f"{i}. {step}\n"

        return resolution.strip()

    def _get_steps_by_classification(self, issue_type, sub_issue_type, ticket_category, technical_keywords):
        """
        Generate specific steps based on the classified issue type.
        """
        # Hardware Issues
        if 'hardware' in issue_type.lower():
            if 'printer' in sub_issue_type.lower():
                return [
                    "Check that the printer is powered on, has paper, and ink/toner cartridges are properly installed.",
                    "Remove and reinstall the printer drivers through Settings > Printers & Scanners.",
                    "Clear the print queue by restarting the Print Spooler service in Services.msc.",
                    "Test printing with a simple document to verify the printer is functioning correctly."
                ]
            elif 'monitor' in sub_issue_type.lower() or 'display' in sub_issue_type.lower():
                return [
                    "Check all cable connections between the monitor and computer, ensuring they are secure.",
                    "Update your graphics drivers through Device Manager or download from manufacturer's website.",
                    "Test the monitor with a different cable or computer to isolate the hardware issue.",
                    "Adjust display settings in Windows Display Settings to ensure proper resolution and refresh rate."
                ]
            else:
                return [
                    "Inspect the hardware component for physical damage, loose connections, or power issues.",
                    "Update the device drivers through Device Manager or manufacturer's website.",
                    "Run built-in hardware diagnostics or manufacturer-provided diagnostic tools.",
                    "Test the hardware component in a different system or replace if confirmed faulty."
                ]

        # Software/Application Issues
        elif 'software' in issue_type.lower() or 'application' in issue_type.lower():
            if 'email' in sub_issue_type.lower() or 'outlook' in sub_issue_type.lower():
                return [
                    "Close Outlook completely and restart it, checking if the issue persists.",
                    "Create a new Outlook profile through Control Panel > Mail > Show Profiles.",
                    "Remove and re-add your email account with the correct server settings.",
                    "Test sending and receiving emails to confirm Outlook is working properly."
                ]
            elif 'office' in sub_issue_type.lower():
                return [
                    "Close all Office applications and restart them as administrator.",
                    "Run Office Quick Repair through Control Panel > Programs > Microsoft Office.",
                    "Check for and install Office updates through File > Account > Update Options.",
                    "Test the Office application with a new document to verify functionality."
                ]
            else:
                return [
                    "Close the application completely and restart it as administrator.",
                    "Check for and install any available software updates.",
                    "Uninstall and reinstall the application using the latest version.",
                    "Test the application with basic functions to ensure it's working correctly."
                ]

        # Network Issues
        elif 'network' in issue_type.lower():
            if 'internet' in sub_issue_type.lower() or 'connectivity' in sub_issue_type.lower():
                return [
                    "Restart your router/modem by unplugging for 30 seconds, then reconnecting.",
                    "Update network adapter drivers through Device Manager.",
                    "Reset network settings by running 'ipconfig /flushdns' and 'netsh int ip reset' as administrator.",
                    "Test internet connectivity by accessing different websites or running a speed test."
                ]
            elif 'vpn' in sub_issue_type.lower():
                return [
                    "Disconnect and reconnect to the VPN, trying different server locations if available.",
                    "Check your internet connection without VPN to ensure basic connectivity works.",
                    "Update your VPN client software to the latest version.",
                    "Contact your VPN provider or IT administrator to verify account status and server availability."
                ]
            else:
                return [
                    "Check all network cable connections and ensure they are properly seated.",
                    "Restart network services through Services.msc or reboot your computer.",
                    "Update network drivers and check Windows Network Troubleshooter.",
                    "Test network connectivity with different devices to isolate the issue."
                ]

        # Access/Security Issues
        elif 'access' in issue_type.lower() or 'security' in issue_type.lower():
            return [
                "Verify your username and password are correct, trying to log in from a different device.",
                "Check if your account is locked by contacting your system administrator.",
                "Clear browser cache and cookies, then try logging in using incognito/private mode.",
                "Reset your password through your organization's self-service portal if available."
            ]

        # Performance Issues
        elif 'performance' in issue_type.lower():
            return [
                "Open Task Manager to identify programs using high CPU, memory, or disk resources.",
                "Close unnecessary programs and disable startup items through Task Manager > Startup.",
                "Run Disk Cleanup to free up disk space and clear temporary files.",
                "Restart your computer and monitor performance to see if the issue is resolved."
            ]

        # General/Other Issues
        else:
            return [
                "Document the exact error message and steps that reproduce the issue.",
                "Restart your computer and test if the issue persists after reboot.",
                "Check for and install Windows updates through Settings > Update & Security.",
                "Run Windows built-in troubleshooters relevant to the type of issue you're experiencing."
            ]

    def _analyze_content_for_insights(self, title, description, technical_keywords):
        """
        Analyze content to extract intelligent insights for resolution generation.
        """
        insights = {
            'issue_patterns': [],
            'technical_components': [],
            'urgency_indicators': [],
            'complexity_factors': []
        }

        content = f"{title} {description}".lower()

        # Detect issue patterns
        if any(word in content for word in ['error', 'failed', 'exception', 'crash']):
            insights['issue_patterns'].append('error')
        if any(word in content for word in ['slow', 'performance', 'lag', 'timeout']):
            insights['issue_patterns'].append('performance')
        if any(word in content for word in ['cannot', 'unable', 'access', 'login']):
            insights['issue_patterns'].append('access')
        if any(word in content for word in ['freeze', 'hang', 'stuck', 'unresponsive']):
            insights['issue_patterns'].append('stability')

        # Extract technical components
        if technical_keywords:
            for category, keywords in technical_keywords.items():
                if keywords:
                    insights['technical_components'].append(category)

        # Detect urgency indicators
        if any(word in content for word in ['urgent', 'critical', 'production', 'down']):
            insights['urgency_indicators'].append('high_priority')
        if any(word in content for word in ['multiple', 'all', 'everyone', 'system-wide']):
            insights['urgency_indicators'].append('widespread_impact')

        return insights

    def _assess_complexity_level(self, technical_keywords, content_insights):
        """
        Assess the complexity level of the issue.
        """
        complexity_score = 0

        # Add complexity based on technical components
        complexity_score += len(technical_keywords)

        # Add complexity based on issue patterns
        if 'error' in content_insights['issue_patterns']:
            complexity_score += 2
        if 'performance' in content_insights['issue_patterns']:
            complexity_score += 3
        if len(content_insights['technical_components']) > 2:
            complexity_score += 2

        if complexity_score <= 3:
            return "Low (Basic troubleshooting)"
        elif complexity_score <= 6:
            return "Medium (Intermediate analysis required)"
        else:
            return "High (Advanced technical expertise needed)"

    def _estimate_resolution_time(self, technical_keywords, priority):
        """
        Estimate resolution time based on complexity and priority.
        """
        base_time = 30  # minutes

        # Adjust based on technical components
        base_time += len(technical_keywords) * 15

        # Adjust based on priority
        if priority in ['High', 'Critical']:
            return f"{base_time}-{base_time + 30} minutes (Priority: {priority})"
        else:
            return f"{base_time}-{base_time + 60} minutes (Standard priority)"



    def save_to_knowledgebase(self, new_ticket_full_data, similar_tickets_metadata):
        """
        Saves the new ticket's full data and similar tickets' metadata to Knowledgebase.json.

        Args:
            new_ticket_full_data (dict): The complete data of the new ticket including classification.
            similar_tickets_metadata (list): List of metadata for similar tickets found.
        """
        knowledgebase_file = 'Knowledgebase.json'
        data_to_save = {
            "new_ticket": new_ticket_full_data,
            "similar_tickets_found": similar_tickets_metadata
        }

        existing_data = []
        if os.path.exists(knowledgebase_file):
            try:
                with open(knowledgebase_file, 'r') as f:
                    existing_data = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: {knowledgebase_file} is corrupted or empty. Starting with a new file.")
                existing_data = []
        
        existing_data.append(data_to_save)

        try:
            with open(knowledgebase_file, 'w') as f:
                json.dump(existing_data, f, indent=4)
            print(f"Successfully saved data to {knowledgebase_file}")
        except Exception as e:
            print(f"Error saving to Knowledgebase.json: {e}")

    def process_new_ticket(self, ticket_name, ticket_description, ticket_title, due_date, priority_initial, extract_model='llama3-8b', classify_model='mixtral-8x7b'):
        """
        Orchestrates the entire process for a new incoming ticket.

        Args:
            ticket_name (str): Name of the person raising the ticket.
            ticket_description (str): Description of the issue.
            ticket_title (str): Title of the ticket.
            due_date (str): Due date for the ticket (e.g., "YYYY-MM-DD").
            priority_initial (str): Initial priority set by the user (e.g., "Medium").

        Returns:
            dict: The classified ticket data, or None if the process fails.
        """
        print(f"\n--- Processing New Ticket: '{ticket_title}' ---")

        creation_time = datetime.now()
        ticket_date = creation_time.strftime("%Y-%m-%d")
        ticket_time = creation_time.strftime("%H:%M:%S")

        new_ticket_raw = {
            "name": ticket_name,
            "description": ticket_description,
            "title": ticket_title,
            "date": ticket_date,
            "time": ticket_time,
            "due_date": due_date,
            "priority": priority_initial 
        }

        extracted_metadata = self.extract_metadata(ticket_title, ticket_description, model=extract_model)
        if not extracted_metadata:
            print("Failed to extract metadata. Aborting ticket processing.")
            return None
        print("Extracted Metadata:")
        print(json.dumps(extracted_metadata, indent=2))

        similar_tickets = self.find_similar_tickets(extracted_metadata)
        if similar_tickets:
            print(f"\nFound {len(similar_tickets)} similar tickets:")
            for i, ticket in enumerate(similar_tickets):
                issue_type_label = self.reference_data.get('issuetype', {}).get(str(ticket.get('ISSUETYPE')), 'N/A')
                priority_label = self.reference_data.get('priority', {}).get(str(ticket.get('PRIORITY')), 'N/A')
                print(f"  {i+1}. Title: {ticket.get('TITLE', 'N/A')}, Type: {issue_type_label}, Priority: {priority_label}")
        else:
            print("\nNo similar tickets found.")

        classified_data = self.classify_ticket(new_ticket_raw, extracted_metadata, similar_tickets, model=classify_model)
        if not classified_data:
            print("Failed to classify ticket. Aborting ticket processing.")
            return None
        print("\nClassified Ticket Data:")
        print(json.dumps(classified_data, indent=2))

        # Generate resolution note using real historical data
        print("\n--- Generating Resolution Note ---")
        resolution_note = self.generate_resolution_note(new_ticket_raw, classified_data, extracted_metadata)
        print("Generated Resolution Note:")
        print(resolution_note)

        final_ticket_data = {
            **new_ticket_raw,
            "extracted_metadata": extracted_metadata,
            "classified_data": classified_data,
            "resolution_note": resolution_note
        }

        similar_tickets_for_kb = []
        for ticket in similar_tickets:
            kb_ticket = {k: v for k, v in ticket.items() if k in ['TITLE', 'DESCRIPTION', 'ISSUETYPE', 'SUBISSUETYPE', 'TICKETCATEGORY', 'TICKETTYPE', 'PRIORITY', 'STATUS']}
            
            for field in ['ISSUETYPE', 'SUBISSUETYPE', 'TICKETCATEGORY', 'TICKETTYPE', 'PRIORITY', 'STATUS']:
                if field in kb_ticket:
                    ref_field_name = field.lower()
                    if ref_field_name in self.reference_data and str(kb_ticket[field]) in self.reference_data[ref_field_name]:
                        kb_ticket[field] = {
                            "Value": kb_ticket[field],
                            "Label": self.reference_data[ref_field_name][str(kb_ticket[field])]
                        }
                    else:
                        kb_ticket[field] = {"Value": kb_ticket[field], "Label": "Unknown/N/A"} 

            similar_tickets_for_kb.append(kb_ticket)

        self.save_to_knowledgebase(final_ticket_data, similar_tickets_for_kb)

        print("\n--- Ticket Processing Complete ---")
        return final_ticket_data

# UI
SF_ACCOUNT = 'FOQUKCW-AITEAM_64SQUARES'
SF_USER = 'AnantL'
SF_PASSWORD = 'Autotask@123456'
SF_WAREHOUSE = 'S_WHH'
SF_DATABASE = 'TEST_DB'
SF_SCHEMA = 'PUBLIC'
SF_ROLE = 'ACCOUNTADMIN' 
SF_PASSCODE = '206109'                                                  
DATA_REF_FILE = 'data.txt' 

@st.cache_resource
def get_agent(account, user, password, warehouse, database, schema, role, passcode, data_ref):
    """Initializes and returns the IntakeClassificationAgent."""
    try:
        agent = IntakeClassificationAgent(
            sf_account=account,
            sf_user=user,
            sf_password=password,
            sf_warehouse=warehouse,
            sf_database=database,
            sf_schema=schema,
            sf_role=role,      
            sf_passcode=passcode, 
            data_ref_file=data_ref
        )
        if not agent.conn:
            st.error("Failed to establish Snowflake connection. Double-check your credentials and network access.")
            return None
        return agent
    except Exception as e:
        st.error(f"An error occurred during agent initialization: {e}")
        st.exception(e) 
        return None

agent = get_agent(SF_ACCOUNT, SF_USER, SF_PASSWORD, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE, SF_PASSCODE, DATA_REF_FILE)

# --- Page Configuration ---
st.set_page_config(
    page_title="TeamLogic-AutoTask",
    layout="wide",
    page_icon="🎫",
    initial_sidebar_state="expanded"
)

# --- Custom Dark Theme CSS ---
st.markdown("""
    <style>
    :root {
        --primary: #4e73df;
        --primary-hover: #2e59d9;
        --secondary: #181818;
        --accent: #23272f;
        --text-main: #f8f9fa;
        --text-secondary: #b0b3b8;
        --card-bg: #23272f;
        --sidebar-bg: #111111;
    }
    .main {
        background-color: var(--secondary);
        color: var(--text-main);
    }
    body, .stApp, .main, .block-container {
        background-color: var(--secondary) !important;
        color: var(--text-main) !important;
    }
    .stTextInput input, .stTextArea textarea, 
    .stSelectbox select, .stDateInput input {
        background-color: #23272f !important;
        color: var(--text-main) !important;
        border: 1px solid #444 !important;
        border-radius: 6px !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder, 
    .stSelectbox select:invalid, .stDateInput input::placeholder {
        color: var(--text-secondary) !important;
    }
    .stButton>button {
        background-color: var(--primary) !important;
        color: white !important;
        border: none;
        padding: 10px 24px;
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: var(--primary-hover) !important;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: var(--primary);
    }
    .stSuccess {
        background-color: #1e4620 !important;
        color: #d4edda !important;
        border-radius: 8px;
    }
    .card {
        background-color: var(--card-bg);
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.15);
        margin-bottom: 20px;
        color: var(--text-main);
    }
    .sidebar .sidebar-content, .stSidebar, section[data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
        color: var(--text-main) !important;
    }
    .stMetric {
        color: var(--text-main) !important;
    }
    .stExpanderHeader {
        color: var(--text-main) !important;
        background-color: var(--card-bg) !important;
    }
    .stExpanderContent {
        background-color: var(--card-bg) !important;
        color: var(--text-main) !important;
    }
    .stAlert, .stInfo, .stWarning {
        background-color: #23272f !important;
        color: #f8f9fa !important;
        border-radius: 8px;
    }
    @media (max-width: 768px) {
        .stForm {
            padding: 15px;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar Navigation ---
def sidebar():
    with st.sidebar:
        st.markdown("<style> .nav-btn { display: flex; align-items: center; gap: 10px; font-weight: 600; font-size: 1.1em; border-radius: 8px; padding: 8px 18px; margin-bottom: 10px; background: linear-gradient(90deg, #4e73df 60%, #36b9cc 100%); color: #fff !important; border: none; transition: box-shadow 0.2s; box-shadow: 0 2px 8px rgba(78,115,223,0.08); } .nav-btn:hover { box-shadow: 0 4px 16px rgba(54,185,204,0.18); background: linear-gradient(90deg, #36b9cc 60%, #4e73df 100%); } .nav-emoji { font-size: 1.3em; border-radius: 50%; background: #fff2; padding: 4px 8px; margin-right: 6px; } </style>", unsafe_allow_html=True)
        st.markdown("## Navigation")
        nav_options = {
            "<span class='nav-emoji'>🏠</span> <span>Home</span>": "main",
            "<span class='nav-emoji'>🕒</span> <span>Recent Tickets</span>": "recent_tickets",
            "<span class='nav-emoji'>📊</span> <span>Dashboard</span>": "dashboard"
        }
        for option, page in nav_options.items():
            if st.button(option, key=f"nav_{page}", help=page, use_container_width=True):
                st.session_state.page = page
                st.rerun()
        current_page = st.session_state.get('page', 'main')
        st.markdown(f"""
        <div style="margin: 20px 0; padding: 10px; background-color: var(--accent); border-radius: 6px;">
        <small>Current page:</small><br>
        <strong>{current_page.replace('_', ' ').title()}</strong>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("### Quick Stats")
        try:
            if os.path.exists('Knowledgebase.json'):
                with open('Knowledgebase.json', 'r') as f:
                    kb_data = json.load(f)
                total_tickets = len(kb_data)
            else:
                total_tickets = 0
        except:
            total_tickets = 0
        st.metric("Total Tickets", total_tickets)
        st.markdown("---")
        st.markdown("""
        <div style="padding: 10px;">
        <h4>Need Help?</h4>
        <p>Contact IT Support:</p>
        <p>📞 9723100860<br>
        ✉️ inquire@64-squares.com</p>
        </div>
        """, unsafe_allow_html=True)

# --- Main Page ---
def main_page():
    st.title("TeamLogic-AutoTask")
    st.markdown("""
    <div class="card" style="background-color: var(--accent);">
    Submit a new support ticket and let our AI agent automatically classify it for faster resolution.
    </div>
    """, unsafe_allow_html=True)
    with st.container():
        st.subheader("📝 New Ticket Submission")
        with st.form("new_ticket_form", clear_on_submit=True):
            col1, col2 = st.columns([1, 1], gap="large")
            with col1:
                st.markdown("### Basic Information")
                ticket_name = st.text_input("Your Name*", placeholder="e.g., Jane Doe")
                ticket_title = st.text_input("Ticket Title*", placeholder="e.g., Network drive inaccessible")
            with col2:
                today = datetime.now().date()
                due_date = st.date_input("Due Date", value=today + timedelta(days=7))
                priority_options = ["Low", "Medium", "High", "Critical", "Desktop/User Down"]
                initial_priority = st.selectbox("Initial Priority*", options=priority_options)
            ticket_description = st.text_area(
                "Description*",
                placeholder="Please describe your issue in detail...",
                height=150
            )
            submitted = st.form_submit_button("Submit Ticket", type="primary")
            if submitted:
                required_fields = {
                    "Name": ticket_name,
                    "Title": ticket_title,
                    "Description": ticket_description,
                    "Priority": initial_priority
                }
                missing_fields = [field for field, value in required_fields.items() if not value]
                if missing_fields:
                    st.warning(f"⚠️ Please fill in all required fields: {', '.join(missing_fields)}")
                else:
                    # Check if agent is properly initialized
                    if agent is None:
                        st.error("❌ Database connection failed. Cannot generate proper resolutions without historical data.")
                        st.info("🔑 **Expired MFA Code** - Get a fresh 6-digit code from your authenticator app")
                        st.info("🌐 **Network Issues** - Check your internet connection")
                        st.info("🔐 **Invalid Credentials** - Verify username/password")
                        st.warning("⚠️ **Resolution generation requires database access to historical tickets.**")
                        st.info("💡 Please fix the connection issue and try again for proper resolution generation.")
                        return
                    else:
                        with st.spinner("🔍 Analyzing your ticket..."):
                            try:
                                processed_ticket = agent.process_new_ticket(
                                    ticket_name=ticket_name,
                                    ticket_description=ticket_description,
                                    ticket_title=ticket_title,
                                    due_date=due_date.strftime("%Y-%m-%d"),
                                    priority_initial=initial_priority
                                )
                                if processed_ticket:
                                    st.success("✅ Ticket processed, classified, and resolution generated successfully!")
                                    classified_data = processed_ticket.get('classified_data', {})
                                    extracted_metadata = processed_ticket.get('extracted_metadata', {})
                                    resolution_note = processed_ticket.get('resolution_note', 'No resolution note generated')
                                    with st.expander("📋 Classified Ticket Summary", expanded=True):
                                        cols = st.columns(3)
                                        cols[0].metric("Issue Type", classified_data.get('ISSUETYPE', {}).get('Label', 'N/A'))
                                        cols[1].metric("Type", classified_data.get('TICKETTYPE', {}).get('Label', 'N/A'))
                                        cols[2].metric("Priority", classified_data.get('PRIORITY', {}).get('Label', 'N/A'))
                                        st.markdown(f"""
                                        <div class="card">
                                        <table style="width:100%">
                                            <tr><td><strong>Ticket Title</strong></td><td>{processed_ticket.get('title', 'N/A')}</td></tr>
                                            <tr><td><strong>Main Issue</strong></td><td>{extracted_metadata.get('main_issue', 'N/A')}</td></tr>
                                            <tr><td><strong>Affected System</strong></td><td>{extracted_metadata.get('affected_system', 'N/A')}</td></tr>
                                            <tr><td><strong>Urgency Level</strong></td><td>{extracted_metadata.get('urgency_level', 'N/A')}</td></tr>
                                            <tr><td><strong>Error Messages</strong></td><td>{extracted_metadata.get('error_messages', 'N/A')}</td></tr>
                                        </table>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    with st.expander("📊 Full Classification Details", expanded=False):
                                        st.markdown("""
                                        <div class="card">
                                        <h4>Ticket Classification Details</h4>
                                        """, unsafe_allow_html=True)
                                        # Tabular display for classification fields
                                        class_fields = [
                                            ("ISSUETYPE", "Issue Type"),
                                            ("SUBISSUETYPE", "Sub-Issue Type"),
                                            ("TICKETCATEGORY", "Ticket Category"),
                                            ("TICKETTYPE", "Ticket Type"),
                                            ("STATUS", "Status"),
                                            ("PRIORITY", "Priority")
                                        ]
                                        table_data = []
                                        for field, label in class_fields:
                                            val = classified_data.get(field, {})
                                            table_data.append({
                                                "Field": label,
                                                "Value": val.get('Value', 'N/A'),
                                                "Label": val.get('Label', 'N/A')
                                            })
                                        df = pd.DataFrame(table_data)
                                        st.table(df)
                                        st.markdown(f"**Ticket Title:** {processed_ticket.get('title', 'N/A')}")
                                        st.markdown(f"**Description:** {processed_ticket.get('description', 'N/A')}")
                                        st.markdown("---")
                                        st.markdown("**Generated Resolution Note:**")
                                        st.markdown(f"```\n{resolution_note}\n```")
                                        st.markdown("</div>", unsafe_allow_html=True)

                                    # Display Resolution Note in a prominent section
                                    with st.expander("🔧 Generated Resolution Note", expanded=True):
                                        # Process the resolution note for HTML display
                                        processed_note = resolution_note.replace('**', '<strong>').replace('</strong>', '</strong>').replace('\n', '<br>')
                                        st.markdown(f"""
                                        <div class="card" style="background-color: #1e4620; border-left: 4px solid #28a745;">
                                        <h4 style="color: #d4edda; margin-bottom: 15px;">💡 Recommended Resolution</h4>
                                        <div style="color: #d4edda; line-height: 1.6;">
                                        {processed_note}
                                        </div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    st.markdown(f"""
                                    <div class="card" style="background-color: var(--accent);">
                                    <h4>Next Steps</h4>
                                    <ol>
                                        <li>Your ticket has been assigned to the <b>{classified_data.get('ISSUETYPE', {}).get('Label', 'N/A')}</b> team</li>
                                        <li>A resolution note has been automatically generated based on similar historical tickets</li>
                                        <li>You'll receive a confirmation email shortly with the resolution steps</li>
                                        <li>A support specialist will contact you within 2 business hours</li>
                                        <li>Priority level: <b>{classified_data.get('PRIORITY', {}).get('Label', 'N/A')}</b> - Response time varies accordingly</li>
                                        <li>Try the suggested resolution steps above before escalating</li>
                                    </ol>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.error("Failed to process the ticket. Please check the logs for details.")
                            except Exception as e:
                                st.error(f"An unexpected error occurred: {e}")
    st.markdown("---")
    st.markdown("""
    <div class="card">
    <h3>About This System</h3>
    <p>This AI-powered intake, classification, and resolution system automatically:</p>
    <ul>
        <li>Extracts metadata from new tickets using AI</li>
        <li>Classifies tickets into predefined categories</li>
        <li>Generates resolution notes based on similar historical tickets</li>
        <li>Routes tickets to the appropriate support teams</li>
        <li>Provides confidence-based resolution suggestions</li>
        <li>Stores all data for continuous improvement</li>
    </ul>
    <p><strong>Workflow:</strong> Intake → Classification → Resolution Generation</p>
    </div>
    """, unsafe_allow_html=True)

# --- Recent Tickets Loader/Adapter ---
def load_tickets():
    """Load and adapt tickets from Knowledgebase.json to a flat list with required fields."""
    if not os.path.exists('Knowledgebase.json'):
        return {"tickets": []}
    with open('Knowledgebase.json', 'r') as f:
        kb_data = json.load(f)
    tickets = []
    for entry in kb_data:
        t = entry.get('new_ticket', {})
        c = t.get('classified_data', {})
        ticket = {
            "id": t.get('title', '') + t.get('date', '') + t.get('time', ''),
            "title": t.get('title', ''),
            "description": t.get('description', ''),
            "created_at": f"{t.get('date', '')}T{t.get('time', '')}",
            "status": c.get('STATUS', {}).get('Label', 'Open'),
            "priority": c.get('PRIORITY', {}).get('Label', 'Medium'),
            "category": c.get('TICKETCATEGORY', {}).get('Label', 'General'),
            "requester_name": t.get('name', ''),
            "requester_email": "",  # Add if available
            "requester_phone": "",  # Add if available
            "company_id": "",       # Add if available
            "device_model": "",     # Add if available
            "os_version": "",       # Add if available
            "error_message": "",    # Add if available
            "updated_at": t.get('updated_at', f"{t.get('date', '')}T{t.get('time', '')}")
        }
        tickets.append(ticket)
    return {"tickets": tickets}

def save_tickets(data):
    """Save the adapted tickets back to Knowledgebase.json (only updates status/priority)."""
    if not os.path.exists('Knowledgebase.json'):
        return
    with open('Knowledgebase.json', 'r') as f:
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
    with open('Knowledgebase.json', 'w') as f:
        json.dump(kb_data, f, indent=4)

def get_recent_tickets(hours: int = 1) -> List[Dict]:
    """Get tickets created within specified hours"""
    data = load_tickets()
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

def get_today_tickets() -> List[Dict]:
    """Get all tickets created today"""
    data = load_tickets()
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

def get_ticket_stats() -> Dict:
    """Get ticket statistics"""
    data = load_tickets()
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

def format_time_elapsed(created_at):
    """Calculate and format time elapsed"""
    try:
        if isinstance(created_at, str):
            ticket_time = datetime.fromisoformat(created_at)
        else:
            ticket_time = created_at
        
        now = datetime.now()
        diff = now - ticket_time
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            minutes = max(1, diff.seconds // 60)
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    except:
        return "Unknown"

def format_date_display(created_at):
    """Format date for display"""
    try:
        if isinstance(created_at, str):
            ticket_time = datetime.fromisoformat(created_at)
        else:
            ticket_time = created_at
        return ticket_time.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "Unknown"

def update_ticket_status(ticket_id: str, new_status: str):
    """Update ticket status"""
    data = load_tickets()
    for ticket in data["tickets"]:
        if ticket["id"] == ticket_id:
            ticket["status"] = new_status
            ticket["updated_at"] = datetime.now().isoformat()
            break
    save_tickets(data)

def get_tickets_by_duration(duration: str) -> List[Dict]:
    """Get tickets based on selected duration"""
    data = load_tickets()
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

def get_tickets_by_date_range(start_date: date, end_date: date) -> List[Dict]:
    """Get tickets between two dates"""
    data = load_tickets()
    
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

def get_tickets_by_specific_date(selected_date: date) -> List[Dict]:
    """Get tickets for a specific date"""
    data = load_tickets()
    
    filtered_tickets = []
    for ticket in data["tickets"]:
        try:
            created_time = datetime.fromisoformat(ticket["created_at"])
            if created_time.date() == selected_date:
                filtered_tickets.append(ticket)
        except:
            continue
    
    return sorted(filtered_tickets, key=lambda x: x["created_at"], reverse=True)

def get_duration_icon(duration: str) -> str:
    """Get appropriate icon for duration"""
    icons = {
        "Last hour": "🚨",
        "Last 2 hours": "⏰",
        "Last 6 hours": "🕕",
        "Last 12 hours": "🕐",
        "Today": "📅",
        "Yesterday": "📆",
        "Last 3 days": "📊",
        "Last week": "📈",
        "Last month": "📉",
        "All tickets": "📋"
    }
    return icons.get(duration, "📅")

# --- Recent Tickets Page (New UI) ---
def recent_tickets_page():
    """Dynamic recent tickets page with multiple filtering options"""
    with st.container():
        if st.button("\u2190 Back to Home", key="rt_back"):
            st.session_state.page = "main"
            st.rerun()
        
        st.title("\U0001F551 Recent Raised Tickets")
        
        # Filter Selection Tabs
        tab1, tab2, tab3 = st.tabs(["\u23F0 Duration Filter", "\U0001F4C5 Date Range Filter", "\U0001F4C6 Specific Date Filter"])
        
        tickets_to_display = []
        filter_description = ""
        
        with tab1:
            st.markdown("### Select Time Duration")
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                duration_options = [
                    "Last hour",
                    "Last 2 hours",
                    "Last 6 hours", 
                    "Last 12 hours",
                    "Today",
                    "Yesterday",
                    "Last 3 days",
                    "Last week",
                    "Last month",
                    "All tickets"
                ]
                
                selected_duration = st.selectbox(
                    "\U0001F4C5 Select Time Duration:",
                    options=duration_options,
                    index=0,  # Default to "Last hour"
                    key="duration_selector"
                )
            
            with col2:
                if st.button("Apply Duration Filter", key="apply_duration"):
                    tickets_to_display = get_tickets_by_duration(selected_duration)
                    filter_description = f"{get_duration_icon(selected_duration)} {selected_duration}"
                    st.session_state.active_filter = "duration"
                    st.session_state.filter_description = filter_description
                    st.session_state.tickets_to_display = tickets_to_display
            
            with col3:
                st.metric("Tickets Found", len(get_tickets_by_duration(selected_duration)))
        
        with tab2:
            st.markdown("### Select Date Range")
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
                start_date = st.date_input(
                    "From Date:",
                    value=datetime.now().date() - timedelta(days=7),
                    key="start_date"
                )
            
            with col2:
                end_date = st.date_input(
                    "To Date:",
                    value=datetime.now().date(),
                    key="end_date"
                )
            
            with col3:
                if st.button("Apply Date Range", key="apply_date_range"):
                    if start_date <= end_date:
                        tickets_to_display = get_tickets_by_date_range(start_date, end_date)
                        filter_description = f"\U0001F4C5 {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                        st.session_state.active_filter = "date_range"
                        st.session_state.filter_description = filter_description
                        st.session_state.tickets_to_display = tickets_to_display
                    else:
                        st.error("Start date must be before or equal to end date!")
            
            with col4:
                if 'start_date' in st.session_state and 'end_date' in st.session_state:
                    preview_tickets = get_tickets_by_date_range(
                        st.session_state.start_date, 
                        st.session_state.end_date
                    )
                    st.metric("Tickets Found", len(preview_tickets))
        
        with tab3:
            st.markdown("### Select Specific Date")
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                specific_date = st.date_input(
                    "Select Date:",
                    value=datetime.now().date(),
                    key="specific_date"
                )
            
            with col2:
                if st.button("Apply Date Filter", key="apply_specific_date"):
                    tickets_to_display = get_tickets_by_specific_date(specific_date)
                    filter_description = f"\U0001F4C6 {specific_date.strftime('%Y-%m-%d')}"
                    st.session_state.active_filter = "specific_date"
                    st.session_state.filter_description = filter_description
                    st.session_state.tickets_to_display = tickets_to_display
            
            with col3:
                preview_tickets = get_tickets_by_specific_date(specific_date)
                st.metric("Tickets Found", len(preview_tickets))
        
        # Use session state to maintain filter results
        if 'tickets_to_display' in st.session_state and 'filter_description' in st.session_state:
            tickets_to_display = st.session_state.tickets_to_display
            filter_description = st.session_state.filter_description
        else:
            # Default to last hour if no filter applied
            tickets_to_display = get_tickets_by_duration("Last hour")
            filter_description = "\U0001F6A8 Last hour"
        
        # Display current filter and refresh option
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Current Filter:** {filter_description}")
        with col2:
            if st.button("\U0001F504 Refresh", key="refresh_tickets"):
                st.rerun()
        
        # Display filtered tickets
        st.markdown(f"""
        <div class="card">
        <h3>{filter_description}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if tickets_to_display:
            # Add special styling for urgent tickets
            if "Last hour" in filter_description:
                st.markdown("""
                <div style="
                    background-color: #2d2d2d;
                    border-left: 6px solid #ffcc00;
                    color: #ffe066;
                    border-radius: 8px;
                    padding: 14px 18px;
                    margin-bottom: 18px;
                    font-size: 1.1em;
                    font-weight: 500;
                    display: flex;
                    align-items: center;
                ">
                    <span style="font-size:1.5em; margin-right: 12px;">⚠️</span>
                    <span>
                        <strong>Urgent Attention Required:</strong>
                        These tickets were raised in the last hour and may need immediate response.
                    </span>
                </div>
                """, unsafe_allow_html=True)
            
            # Add pagination for large result sets
            tickets_per_page = 10
            total_pages = (len(tickets_to_display) + tickets_per_page - 1) // tickets_per_page
            
            if total_pages > 1:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    page_number = st.selectbox(
                        f"Page (showing {tickets_per_page} tickets per page):",
                        options=list(range(1, total_pages + 1)),
                        key="page_selector"
                    )
                
                start_idx = (page_number - 1) * tickets_per_page
                end_idx = start_idx + tickets_per_page
                tickets_to_show = tickets_to_display[start_idx:end_idx]
            else:
                tickets_to_show = tickets_to_display
            
            # Display tickets
            for i, ticket in enumerate(tickets_to_show):
                time_elapsed = format_time_elapsed(ticket['created_at'])
                date_created = format_date_display(ticket['created_at'])
                
                # Special highlighting for critical/urgent tickets
                is_urgent = (ticket.get('priority') in ['Critical', 'Desktop/User Down'] or 
                           "Last hour" in filter_description)
                
                expand_key = f"ticket_{ticket['id']}_{i}"
                
                with st.expander(
                    f"{'🔥' if is_urgent else '📋'} {ticket['id']} - {ticket['title']} ({time_elapsed})", 
                    expanded=False
                ):
                    # Ticket header with date
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"**📅 Created:** {date_created}")
                    with col2:
                        st.markdown(f"**⏰ Time Elapsed:** {time_elapsed}")
                    
                    # Ticket details
                    cols = st.columns([1, 1, 1, 1])
                    cols[0].markdown(f"**Category:** {ticket.get('category', 'General')}")
                    cols[1].markdown(f"**Priority:** {ticket['priority']}")
                    cols[2].markdown(f"**Status:** {ticket['status']}")
                    cols[3].markdown(f"**Requester:** {ticket['requester_name']}")
                    
                    st.markdown(f"**Email:** {ticket['requester_email']}")
                    if ticket.get('requester_phone'):
                        st.markdown(f"**Phone:** {ticket['requester_phone']}")
                    st.markdown(f"**Company ID:** {ticket['company_id']}")
                    
                    # Description with expand/collapse
                    if len(ticket['description']) > 200:
                        if st.button(f"Show Full Description", key=f"desc_{ticket['id']}_{i}"):
                            st.markdown(f"**Description:** {ticket['description']}")
                        else:
                            st.markdown(f"**Description:** {ticket['description'][:200]}...")
                    else:
                        st.markdown(f"**Description:** {ticket['description']}")
                    
                    # Technical details if available
                    if ticket.get('device_model') or ticket.get('os_version') or ticket.get('error_message'):
                        st.markdown("**Technical Details:**")
                        if ticket.get('device_model'):
                            st.markdown(f"• Device: {ticket['device_model']}")
                        if ticket.get('os_version'):
                            st.markdown(f"• OS: {ticket['os_version']}")
                        if ticket.get('error_message'):
                            st.markdown(f"• Error: {ticket['error_message']}")
                    
                    # Status update section
                    st.markdown("---")
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        new_status = st.selectbox(
                            "Update Status:", 
                            ["Open", "In Progress", "Resolved", "Closed"],
                            index=["Open", "In Progress", "Resolved", "Closed"].index(ticket['status']) if ticket['status'] in ["Open", "In Progress", "Resolved", "Closed"] else 0,
                            key=f"status_{ticket['id']}_{i}"
                        )
                    with col2:
                        if st.button("Update Status", key=f"update_{ticket['id']}_{i}"):
                            update_ticket_status(ticket['id'], new_status)
                            st.success(f"Status updated to {new_status}")
                            st.rerun()
                    with col3:
                        # Priority indicator
                        priority_colors = {
                            "Low": "🟢",
                            "Medium": "🟡", 
                            "High": "🟠",
                            "Critical": "🔴",
                            "Desktop/User Down": "🚨"
                        }
                        st.markdown(f"**Priority:** {priority_colors.get(ticket['priority'], '⚪')} {ticket['priority']}")
            
            # Show pagination info
            if total_pages > 1:
                st.info(f"Showing page {page_number} of {total_pages} ({len(tickets_to_display)} total tickets)")
                
        else:
            st.info(f"No tickets found for the selected filter: {filter_description}")
        
        # Summary statistics for filtered tickets
        if tickets_to_display:
            st.markdown("---")
            st.markdown("### \U0001F4CA Summary Statistics")
            
            # Calculate stats for the filtered tickets
            status_counts = {}
            priority_counts = {}
            category_counts = {}
            
            for ticket in tickets_to_display:
                # Status counts
                status = ticket.get('status', 'Open')
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Priority counts  
                priority = ticket.get('priority', 'Medium')
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
                
                # Category counts
                category = ticket.get('category', 'General')
                category_counts[category] = category_counts.get(category, 0) + 1
            
            # Main metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total", len(tickets_to_display))
            col2.metric("Open", status_counts.get('Open', 0))
            col3.metric("In Progress", status_counts.get('In Progress', 0))
            col4.metric("Resolved", status_counts.get('Resolved', 0))
            
            # Detailed breakdown
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**\U0001F4C2 Categories:**")
                for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / len(tickets_to_display)) * 100
                    st.write(f"• {category}: {count} ({percentage:.1f}%)")
            
            with col2:
                st.markdown("**\u26A1 Priorities:**")
                priority_order = ["Critical", "Desktop/User Down", "High", "Medium", "Low"]
                for priority in priority_order:
                    if priority in priority_counts:
                        count = priority_counts[priority]
                        percentage = (count / len(tickets_to_display)) * 100
                        icon = {"Critical": "🔴", "Desktop/User Down": "🚨", "High": "🟠", "Medium": "🟡", "Low": "🟢"}.get(priority, "⚪")
                        st.write(f"• {icon} {priority}: {count} ({percentage:.1f}%)")
            
            # Show urgent tickets alert if any
            urgent_count = priority_counts.get('Critical', 0) + priority_counts.get('Desktop/User Down', 0)
            if urgent_count > 0:
                st.warning(f"⚠️ {urgent_count} urgent ticket(s) require immediate attention!")

# --- Dashboard Page ---
def dashboard_page():
    st.title("\U0001F4CA Dashboard")
    # Load from Knowledgebase.json
    if os.path.exists('Knowledgebase.json'):
        with open('Knowledgebase.json', 'r') as f:
            kb_data = json.load(f)
    else:
        kb_data = []
    # --- FILTERS ---
    st.markdown("### Filters")
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        date_min = None
        date_max = None
        dates = []
        for entry in kb_data:
            t = entry['new_ticket']
            try:
                dt = datetime.fromisoformat(t['date'] + 'T' + t['time'])
                dates.append(dt)
            except:
                continue
        if dates:
            date_min = min(dates).date()
            date_max = max(dates).date()
        else:
            date_min = date_max = datetime.now().date()
        date_range = st.date_input("Date Range", value=(date_min, date_max), min_value=date_min, max_value=date_max)
    with col2:
        all_statuses = sorted(set(entry['new_ticket'].get('classified_data', {}).get('STATUS', {}).get('Label', 'N/A') for entry in kb_data if 'new_ticket' in entry))
        status_filter = st.multiselect("Status", options=["New", "In Progress", "Resolved", "Closed"] + [s for s in all_statuses if s not in ["New", "In Progress", "Resolved", "Closed"]], default=["New", "In Progress", "Resolved", "Closed"])
    with col3:
        all_priorities = sorted(set(entry['new_ticket'].get('classified_data', {}).get('PRIORITY', {}).get('Label', 'N/A') for entry in kb_data if 'new_ticket' in entry))
        priority_filter = st.multiselect("Priority", options=all_priorities, default=all_priorities)
    # --- FILTER DATA ---
    filtered = []
    for entry in kb_data:
        t = entry['new_ticket']
        c = t.get('classified_data', {})
        try:
            dt = datetime.fromisoformat(t['date'] + 'T' + t['time'])
        except:
            continue
        status = c.get('STATUS', {}).get('Label', 'N/A')
        priority = c.get('PRIORITY', {}).get('Label', 'N/A')
        if (date_range[0] <= dt.date() <= date_range[1]) and (status in status_filter) and (priority in priority_filter):
            filtered.append(entry)
    total_tickets = len(filtered)
    open_tickets = sum(1 for entry in filtered if entry['new_ticket'].get('classified_data', {}).get('STATUS', {}).get('Label', 'N/A').lower() == 'open')
    resolved_tickets = sum(1 for entry in filtered if entry['new_ticket'].get('classified_data', {}).get('STATUS', {}).get('Label', 'N/A').lower() == 'resolved')
    last_24h = 0
    now = datetime.now()
    cutoff_24h = now - timedelta(hours=24)
    for entry in filtered:
        try:
            created_time = datetime.fromisoformat(entry['new_ticket']['date'] + 'T' + entry['new_ticket']['time'])
            if created_time >= cutoff_24h:
                last_24h += 1
        except:
            continue
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tickets", total_tickets)
    col2.metric("Last 24 Hours", last_24h)
    col3.metric("Open Tickets", open_tickets)
    col4.metric("Resolved", resolved_tickets)
    # --- Prepare data for grouped bar chart ---
    status_counts = Counter()
    priority_counts = Counter()
    category_counts = Counter()
    for entry in filtered:
        classified = entry['new_ticket'].get('classified_data', {})
        status = classified.get('STATUS', {}).get('Label', 'N/A')
        priority = classified.get('PRIORITY', {}).get('Label', 'N/A')
        category = classified.get('TICKETCATEGORY', {}).get('Label', 'N/A')
        status_counts[status] += 1
        priority_counts[priority] += 1
        category_counts[category] += 1
    # Ensure all main statuses are present in order
    status_order = ["New", "In Progress", "Resolved", "Closed"]
    for s in status_order:
        if s not in status_counts:
            status_counts[s] = 0
    # --- Plotly Bar Chart ---
    df_status = pd.DataFrame({"Status": list(status_counts.keys()), "Count": list(status_counts.values())})
    df_priority = pd.DataFrame({"Priority": list(priority_counts.keys()), "Count": list(priority_counts.values())})
    df_category = pd.DataFrame({"Category": list(category_counts.keys()), "Count": list(category_counts.values())})
    # Custom color maps
    status_colors = {"New": "#4e73df", "In Progress": "#f6c23e", "Resolved": "#36b9cc", "Closed": "#e74a3b"}
    priority_colors = {"Low": "#1cc88a", "Medium": "#36b9cc", "High": "#f6c23e", "Critical": "#e74a3b", "Desktop/User Down": "#6f42c1"}
    category_colors = {cat: px.colors.qualitative.Plotly[i % 10] for i, cat in enumerate(df_category['Category'])}
    # Plot
    st.subheader("Tickets by Status, Priority, and Category")
    fig = px.bar(df_status, x="Status", y="Count", color="Status", category_orders={"Status": status_order}, color_discrete_map=status_colors, barmode="group", title="Status")
    fig.add_bar(x=df_priority['Priority'], y=df_priority['Count'], name="Priority", marker_color=[priority_colors.get(p, '#888') for p in df_priority['Priority']])
    fig.add_bar(x=df_category['Category'], y=df_category['Count'], name="Category", marker_color=[category_colors.get(c, '#888') for c in df_category['Category']])
    fig.update_layout(
        plot_bgcolor="#181818",
        paper_bgcolor="#181818",
        font_color="#f8f9fa",
        legend=dict(bgcolor="#23272f", bordercolor="#444", borderwidth=1),
        xaxis=dict(title="", tickfont=dict(color="#f8f9fa")),
        yaxis=dict(title="", tickfont=dict(color="#f8f9fa")),
        barmode="group",
        bargap=0.18,
        bargroupgap=0.12
    )
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Recent Tickets")
    if filtered:
        recent_rows = []
        for entry in filtered[-10:][::-1]:
            ticket = entry['new_ticket']
            classified = ticket.get('classified_data', {})
            recent_rows.append({
                "Title": ticket.get('title', 'N/A'),
                "Category": classified.get('TICKETCATEGORY', {}).get('Label', 'N/A'),
                "Priority": classified.get('PRIORITY', {}).get('Label', 'N/A'),
                "Status": classified.get('STATUS', {}).get('Label', 'N/A'),
                "Date": ticket.get('date', 'N/A'),
                "Time": ticket.get('time', 'N/A'),
                "ID": ticket.get('title', 'N/A') + ticket.get('date', 'N/A') + ticket.get('time', 'N/A')
            })
        df_recent = pd.DataFrame(recent_rows)
        for entry in filtered[-10:][::-1]:
            ticket = entry['new_ticket']
            classified = ticket.get('classified_data', {})
            ticket_id = ticket.get('title', 'N/A') + ticket.get('date', 'N/A') + ticket.get('time', 'N/A')
            with st.expander(f"{ticket.get('title', 'N/A')} ({ticket.get('date', 'N/A')} {ticket.get('time', 'N/A')})", expanded=False):
                st.markdown(f"**Category:** {classified.get('TICKETCATEGORY', {}).get('Label', 'N/A')}")
                st.markdown(f"**Priority:** {classified.get('PRIORITY', {}).get('Label', 'N/A')}")
                st.markdown(f"**Status:** {classified.get('STATUS', {}).get('Label', 'N/A')}")
                st.markdown(f"**Requester:** {ticket.get('name', 'N/A')}")
                st.markdown(f"**Created At:** {ticket.get('date', 'N/A')} {ticket.get('time', 'N/A')}")
                st.markdown(f"**Description:** {ticket.get('description', 'N/A')}")
    else:
        st.info("No tickets found for the selected filters.")

# --- Main App Logic ---
if "page" not in st.session_state:
    st.session_state.page = "main"

sidebar()

if st.session_state.page == "main":
    main_page()
elif st.session_state.page == "recent_tickets":
    recent_tickets_page()
elif st.session_state.page == "dashboard":
    dashboard_page()

