"""
Ticket processing module for TeamLogic-AutoTask application.
Handles ticket similarity matching, technical analysis, and processing logic.
"""

import re
import pandas as pd
from typing import List, Dict, Optional
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class TicketProcessor:
    """
    Handles ticket processing operations including similarity matching and technical analysis.
    """

    def __init__(self, reference_data: Dict):
        """
        Initialize the ticket processor.

        Args:
            reference_data (dict): Reference data for classification mappings
        """
        self.reference_data = reference_data

    def find_similar_tickets_conditions(self, extracted_metadata: Dict) -> tuple:
        """
        Build search conditions and parameters for finding similar tickets.

        Args:
            extracted_metadata (dict): Extracted metadata from the ticket

        Returns:
            tuple: (search_conditions, params) for database query
        """
        if not extracted_metadata:
            return [], []

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

        # Combine conditions
        all_conditions = search_conditions.copy()
        if keyword_conditions:
            all_conditions.extend(keyword_conditions)

        return all_conditions, params

    def summarize_similar_tickets(self, similar_tickets: List[Dict]) -> Dict:
        """
        Summarizes the most common values for each classification field among similar tickets.

        Args:
            similar_tickets (list): List of similar tickets

        Returns:
            dict: Summary of most common classification values
        """
        summary = {}
        for field in ["ISSUETYPE", "SUBISSUETYPE", "TICKETCATEGORY", "TICKETTYPE", "PRIORITY"]:
            values = [ticket.get(field) for ticket in similar_tickets if ticket.get(field) not in [None, "N/A"]]
            if values:
                most_common, count = Counter(values).most_common(1)[0]
                summary[field] = {"Value": most_common, "Count": count}
        return summary

    def get_similarity_score(self, new_text: str, historical_texts: List[str]) -> List[float]:
        """
        TF-IDF based similarity comparison for resolution matching.

        Args:
            new_text (str): Text from the new ticket
            historical_texts (list): List of historical ticket texts

        Returns:
            list: Similarity scores
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

    def extract_technical_keywords(self, title: str, description: str) -> Dict:
        """
        Extract technical keywords and components from ticket title and description.

        Args:
            title (str): Ticket title
            description (str): Ticket description

        Returns:
            dict: Dictionary of found technical keywords by category
        """
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