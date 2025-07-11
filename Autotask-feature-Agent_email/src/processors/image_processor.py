"""
Image processing module for TeamLogic-AutoTask application.
Handles image intake, metadata extraction, and classification based on visual content.
Supports various image formats and extracts technical information from screenshots, error dialogs, etc.
"""

import os
import base64
import json
import re
from typing import Dict, List, Optional, Union, Tuple
from PIL import Image, ImageEnhance
import pytesseract
import cv2
import numpy as np
from pathlib import Path
import mimetypes


class ImageProcessor:
    """
    Handles image processing operations including OCR, metadata extraction, 
    and visual analysis for IT support ticket classification.
    """

    def __init__(self, db_connection=None, reference_data: Dict = None):
        """
        Initialize the image processor.

        Args:
            db_connection: Database connection for LLM calls (optional)
            reference_data (dict): Reference data for classification mappings
        """
        self.db_connection = db_connection
        self.reference_data = reference_data or {}
        
        # Supported image formats
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
        
        # Configure Tesseract path if needed (adjust based on your system)
        # Uncomment and modify the path below if Tesseract is not in your PATH
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    def validate_image(self, image_path: str) -> bool:
        """
        Validate if the provided file is a supported image format.

        Args:
            image_path (str): Path to the image file

        Returns:
            bool: True if valid image, False otherwise
        """
        try:
            # Check file extension
            file_ext = Path(image_path).suffix.lower()
            if file_ext not in self.supported_formats:
                print(f"Unsupported image format: {file_ext}")
                return False
            
            # Check if file exists
            if not os.path.exists(image_path):
                print(f"Image file not found: {image_path}")
                return False
            
            # Try to open with PIL to verify it's a valid image
            with Image.open(image_path) as img:
                img.verify()
            
            return True
        except Exception as e:
            print(f"Image validation failed: {e}")
            return False

    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for better OCR results.
        Applies noise reduction, contrast enhancement, and other optimizations.

        Args:
            image_path (str): Path to the image file

        Returns:
            np.ndarray: Preprocessed image array
        """
        try:
            # Load image with OpenCV
            image = cv2.imread(image_path)
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply noise reduction
            denoised = cv2.medianBlur(gray, 3)
            
            # Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            
            # Apply threshold to get binary image
            _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return binary
        except Exception as e:
            print(f"Image preprocessing failed: {e}")
            # Fallback: return original image as grayscale
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            return image

    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from image using OCR (Optical Character Recognition).

        Args:
            image_path (str): Path to the image file

        Returns:
            str: Extracted text from the image
        """
        try:
            # Preprocess image for better OCR
            processed_image = self.preprocess_image(image_path)
            
            # Configure Tesseract for better accuracy
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!@#$%^&*()_+-=[]{}|;:,.<>?/~` '
            
            # Extract text using Tesseract
            extracted_text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            # Clean up the extracted text
            cleaned_text = self._clean_extracted_text(extracted_text)
            
            print(f"Extracted text from image: {len(cleaned_text)} characters")
            return cleaned_text
            
        except Exception as e:
            print(f"OCR text extraction failed: {e}")
            return ""

    def _clean_extracted_text(self, text: str) -> str:
        """
        Clean and normalize extracted text from OCR.

        Args:
            text (str): Raw OCR text

        Returns:
            str: Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace and normalize line breaks
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        cleaned_text = '\n'.join(lines)
        
        # Remove common OCR artifacts
        cleaned_text = cleaned_text.replace('|', 'I')  # Common OCR mistake
        cleaned_text = cleaned_text.replace('0', 'O')  # In some contexts
        
        return cleaned_text

    def detect_error_dialogs(self, image_path: str) -> Dict:
        """
        Detect common error dialog patterns in the image.
        Looks for error windows, dialog boxes, and warning messages.

        Args:
            image_path (str): Path to the image file

        Returns:
            dict: Information about detected error dialogs
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Template matching for common error dialog elements
            error_indicators = {
                'error_icon': False,
                'warning_icon': False,
                'dialog_box': False,
                'error_keywords': []
            }
            
            # Extract text to look for error keywords
            extracted_text = self.extract_text_from_image(image_path)
            
            # Common error keywords to look for
            error_keywords = [
                'error', 'warning', 'exception', 'failed', 'cannot', 'unable',
                'access denied', 'permission', 'timeout', 'connection', 'network',
                'file not found', 'invalid', 'corrupt', 'crash', 'freeze'
            ]
            
            found_keywords = []
            if extracted_text:
                for keyword in error_keywords:
                    if keyword.lower() in extracted_text.lower():
                        found_keywords.append(keyword)
            
            error_indicators['error_keywords'] = found_keywords
            
            # Simple heuristic: if we found error keywords, likely an error dialog
            if found_keywords:
                error_indicators['dialog_box'] = True
            
            return error_indicators
            
        except Exception as e:
            print(f"Error dialog detection failed: {e}")
            return {'error_icon': False, 'warning_icon': False, 'dialog_box': False, 'error_keywords': []}

    def extract_image_metadata(self, image_path: str) -> Dict:
        """
        Extract comprehensive metadata from the image including technical information.

        Args:
            image_path (str): Path to the image file

        Returns:
            dict: Extracted metadata from the image
        """
        try:
            # Basic image information
            with Image.open(image_path) as img:
                image_info = {
                    'filename': os.path.basename(image_path),
                    'format': img.format,
                    'size': img.size,
                    'mode': img.mode,
                    'file_size': os.path.getsize(image_path)
                }
            
            # Extract text using OCR
            extracted_text = self.extract_text_from_image(image_path)
            
            # Detect error dialogs
            error_info = self.detect_error_dialogs(image_path)
            
            # Analyze extracted text for technical keywords
            technical_analysis = self._analyze_technical_content(extracted_text)
            
            # Combine all metadata
            metadata = {
                'image_info': image_info,
                'extracted_text': extracted_text,
                'text_length': len(extracted_text),
                'error_detection': error_info,
                'technical_analysis': technical_analysis,
                'has_text': len(extracted_text.strip()) > 0,
                'likely_error_screenshot': error_info['dialog_box'] or len(error_info['error_keywords']) > 0
            }
            
            return metadata
            
        except Exception as e:
            print(f"Image metadata extraction failed: {e}")
            return {}

    def _analyze_technical_content(self, text: str) -> Dict:
        """
        Analyze extracted text for technical keywords and patterns.

        Args:
            text (str): Extracted text from image

        Returns:
            dict: Technical analysis results
        """
        if not text:
            return {}
        
        text_lower = text.lower()
        
        # Technical keyword categories
        technical_categories = {
            'applications': ['outlook', 'excel', 'word', 'powerpoint', 'teams', 'chrome', 'firefox', 'edge', 'internet explorer'],
            'operating_systems': ['windows', 'mac', 'linux', 'android', 'ios'],
            'error_codes': [],
            'file_paths': [],
            'urls': [],
            'ip_addresses': [],
            'email_addresses': [],
            'system_components': ['registry', 'driver', 'service', 'process', 'dll', 'exe'],
            'network_terms': ['wifi', 'ethernet', 'vpn', 'firewall', 'dns', 'dhcp', 'proxy'],
            'hardware_terms': ['printer', 'monitor', 'keyboard', 'mouse', 'cpu', 'memory', 'disk']
        }
        
        found_categories = {}
        
        # Search for keywords in each category
        for category, keywords in technical_categories.items():
            found_items = [keyword for keyword in keywords if keyword in text_lower]
            if found_items:
                found_categories[category] = found_items
        
        # Extract error codes (pattern: Error followed by numbers)
        error_codes = re.findall(r'error\s*[:\-]?\s*(\d+)', text_lower)
        if error_codes:
            found_categories['error_codes'] = error_codes
        
        # Extract file paths
        file_paths = re.findall(r'[A-Za-z]:\\[^\s]+', text)
        if file_paths:
            found_categories['file_paths'] = file_paths
        
        # Extract URLs
        urls = re.findall(r'https?://[^\s]+', text)
        if urls:
            found_categories['urls'] = urls
        
        return found_categories

    def classify_image_content(self, image_metadata: Dict, model: str = 'mixtral-8x7b') -> Optional[Dict]:
        """
        Classify the image content and extract issue-related information using LLM.

        Args:
            image_metadata (dict): Metadata extracted from the image
            model (str): LLM model to use for classification

        Returns:
            dict: Classification results based on image content
        """
        if not self.db_connection:
            print("No database connection available for LLM classification")
            return None

        try:
            extracted_text = image_metadata.get('extracted_text', '')
            technical_analysis = image_metadata.get('technical_analysis', {})
            error_detection = image_metadata.get('error_detection', {})

            # Build prompt for LLM analysis
            prompt = f"""
            Analyze the following information extracted from an IT support ticket image and provide classification metadata in JSON format.

            Image Information:
            - Filename: {image_metadata.get('image_info', {}).get('filename', 'Unknown')}
            - Has Text Content: {image_metadata.get('has_text', False)}
            - Likely Error Screenshot: {image_metadata.get('likely_error_screenshot', False)}
            - Text Length: {image_metadata.get('text_length', 0)} characters

            Extracted Text from Image:
            "{extracted_text}"

            Technical Analysis Results:
            {json.dumps(technical_analysis, indent=2)}

            Error Detection Results:
            - Error Keywords Found: {error_detection.get('error_keywords', [])}
            - Dialog Box Detected: {error_detection.get('dialog_box', False)}

            Based on this image analysis, extract the following metadata in JSON format:

            Guidelines:
            - Focus on SPECIFIC technical details, not generic terms like "image analysis" or "error screenshot"
            - If the image contains error messages, extract the EXACT error text and codes
            - If it's a screenshot of an application, identify the SPECIFIC application and technical issue
            - Look for system components, file paths, error codes, or technical indicators
            - Assess the urgency based on the type of error or issue shown
            - Avoid generic keywords like "image", "analysis", "screenshot" in technical_keywords

            JSON Schema (provide comprehensive classification data):
            {{
                "main_issue": "Specific technical issue or problem shown (e.g., 'Outlook connection timeout', 'VPN authentication failed')",
                "issue_category": "Category (Technical, Hardware, Software, Network, Security, Access, System, Application)",
                "affected_system": "Specific system, application, or component affected (e.g., 'Microsoft Outlook', 'Windows VPN Client')",
                "error_messages": "Exact error messages, codes, or alerts visible in the image",
                "urgency_level": "Urgency level (Critical, High, Medium, Low)",
                "priority_indicators": "Visual indicators suggesting priority (crash, freeze, access denied, etc.)",
                "business_impact": "Potential business impact (High, Medium, Low, Unknown)",
                "technical_keywords": ["specific", "technical", "terms", "like", "VPN", "DNS", "SMTP", "applications", "protocols"],
                "error_codes": ["specific", "error", "codes", "or", "reference", "numbers"],
                "system_components": ["specific", "hardware", "software", "components", "visible"],
                "applications_involved": ["specific", "applications", "or", "software", "shown"],
                "image_type": "Type (error_dialog, blue_screen, application_screenshot, hardware_photo, network_diagram, etc.)",
                "visual_indicators": "Visual elements indicating problem (red X, warning icons, error dialogs, etc.)",
                "ui_elements": ["specific", "buttons", "menus", "dialogs", "visible", "in", "interface"],
                "resolution_category": "Resolution approach (Application_Restart, System_Reboot, Network_Fix, Hardware_Replace, etc.)",
                "suggested_actions": ["immediate", "actions", "suggested", "by", "visual", "content"],
                "escalation_needed": "Whether escalation needed (Yes, No, Maybe)",
                "confidence_score": "Confidence in analysis (High, Medium, Low)",
                "extraction_quality": "Quality of text extraction (Excellent, Good, Fair, Poor)",
                "additional_context": "Any additional relevant context or observations"
            }}
            """

            print("Classifying image content with LLM...")
            classification_result = self.db_connection.call_cortex_llm(prompt, model=model)

            if classification_result:
                # Clean up LLM results to remove generic terms
                classification_result = self._clean_llm_classification(classification_result)

                # Add image-specific metadata
                classification_result['source'] = 'llm_classification'  # Changed from 'image_analysis'
                classification_result['image_metadata'] = image_metadata

            return classification_result

        except Exception as e:
            print(f"Image classification failed: {e}")
            # Fallback to rule-based classification
            return self._rule_based_classification(image_metadata)

    def _clean_llm_classification(self, classification_result: Dict) -> Dict:
        """
        Clean up LLM classification results to remove generic terms.

        Args:
            classification_result (dict): Raw LLM classification results

        Returns:
            dict: Cleaned classification results
        """
        if not isinstance(classification_result, dict):
            return classification_result

        # Define generic terms to filter out
        generic_terms = [
            'image', 'analysis', 'screenshot', 'error screenshot', 'image analysis',
            'dialog', 'window', 'button', 'click', 'menu', 'tab', 'interface',
            'visual', 'display', 'screen', 'picture', 'photo', 'capture'
        ]

        # Clean technical_keywords if present
        if 'technical_keywords' in classification_result and isinstance(classification_result['technical_keywords'], list):
            cleaned_keywords = []
            for keyword in classification_result['technical_keywords']:
                if isinstance(keyword, str):
                    keyword_lower = keyword.lower().strip()
                    # Skip if it's a generic term or contains generic phrases
                    if (keyword_lower not in generic_terms and
                        not any(generic in keyword_lower for generic in ['image analysis', 'error screenshot', 'screenshot']) and
                        len(keyword.strip()) > 2):
                        cleaned_keywords.append(keyword.strip())

            classification_result['technical_keywords'] = cleaned_keywords[:15]

        # Clean main_issue if it contains generic terms
        if 'main_issue' in classification_result and isinstance(classification_result['main_issue'], str):
            main_issue = classification_result['main_issue'].strip()
            if any(generic in main_issue.lower() for generic in ['image analysis', 'error screenshot', 'screenshot analysis', 'screenshot', 'image']):
                # Replace with more specific description if possible
                if 'error' in main_issue.lower():
                    classification_result['main_issue'] = "Technical error detected"
                else:
                    classification_result['main_issue'] = "Technical issue requiring analysis"

        # Clean affected_system if it contains generic terms
        if 'affected_system' in classification_result and isinstance(classification_result['affected_system'], str):
            affected_system = classification_result['affected_system'].strip()
            if any(generic in affected_system.lower() for generic in ['image analysis', 'screenshot']):
                classification_result['affected_system'] = "System requiring analysis"

        return classification_result

    def _rule_based_classification(self, image_metadata: Dict) -> Dict:
        """
        Rule-based classification when LLM is not available.
        Extracts comprehensive classification data using pattern matching from actual image content.
        """
        extracted_text = image_metadata.get('extracted_text', '') or ''
        original_text = extracted_text  # Keep original case for display
        extracted_text_lower = extracted_text.lower()
        technical_analysis = image_metadata.get('technical_analysis', {}) or {}
        error_detection = image_metadata.get('error_detection', {}) or {}

        # Analyze extracted content quietly

        # Initialize comprehensive classification result - avoid generic responses
        classification = {
            "main_issue": "Unable to determine specific issue",
            "issue_category": "Technical",
            "affected_system": "Unknown System",
            "error_messages": "No clear error messages detected",
            "urgency_level": "Low",
            "priority_indicators": [],
            "business_impact": "Low",
            "technical_keywords": [],
            "error_codes": [],
            "system_components": [],
            "applications_involved": [],
            "image_type": "general_screenshot",
            "visual_indicators": [],
            "ui_elements": [],
            "resolution_category": "General_Support",
            "suggested_actions": ["Review image content manually", "Contact support for assistance"],
            "escalation_needed": "No",
            "confidence_score": "Medium",
            "extraction_quality": "Fair",
            "additional_context": "Processed using rule-based analysis"
        }

        # Extract main issue from actual text content - focus on the real problem, not image analysis
        error_keywords = error_detection.get('error_keywords', []) or []

        if extracted_text.strip():
            # Get meaningful lines from extracted text
            lines = [line.strip() for line in original_text.split('\n') if line.strip() and len(line.strip()) > 3]

            # Look for specific issue patterns in the text
            main_issue = "Unknown issue"

            # Check for network/connection issues
            if any(word in extracted_text_lower for word in ['connection', 'network', 'server', 'timeout', 'connect']):
                if 'cannot connect' in extracted_text_lower:
                    main_issue = "Cannot connect to server"
                elif 'connection failed' in extracted_text_lower or 'connection timeout' in extracted_text_lower:
                    main_issue = "Connection failed"
                elif 'network' in extracted_text_lower:
                    main_issue = "Network connectivity issue"
                else:
                    main_issue = "Connection problem"
                classification["issue_category"] = "Network"
                classification["urgency_level"] = "High"

            # Check for application errors
            elif any(word in extracted_text_lower for word in ['outlook', 'excel', 'word', 'teams', 'office']):
                app_name = next((word.title() for word in ['outlook', 'excel', 'word', 'teams', 'office'] if word in extracted_text_lower), "Application")
                if 'error' in extracted_text_lower:
                    main_issue = f"{app_name} application error"
                elif 'cannot' in extracted_text_lower:
                    main_issue = f"{app_name} functionality issue"
                else:
                    main_issue = f"{app_name} problem"
                classification["issue_category"] = "Software"
                classification["urgency_level"] = "Medium"

            # Check for system errors
            elif any(word in extracted_text_lower for word in ['system', 'windows', 'blue screen', 'crash']):
                if 'blue screen' in extracted_text_lower or 'bsod' in extracted_text_lower:
                    main_issue = "System crash (Blue Screen)"
                    classification["urgency_level"] = "Critical"
                elif 'system' in extracted_text_lower and 'error' in extracted_text_lower:
                    main_issue = "System error"
                    classification["urgency_level"] = "High"
                else:
                    main_issue = "System issue"
                classification["issue_category"] = "System"

            # Check for access/permission issues
            elif any(word in extracted_text_lower for word in ['access denied', 'permission', 'unauthorized', 'login']):
                main_issue = "Access denied or permission issue"
                classification["issue_category"] = "Security"
                classification["urgency_level"] = "Medium"

            # Check for file/data issues
            elif any(word in extracted_text_lower for word in ['file', 'corrupt', 'data', 'document']):
                if 'corrupt' in extracted_text_lower:
                    main_issue = "File corruption issue"
                    classification["urgency_level"] = "High"
                else:
                    main_issue = "File access issue"
                classification["issue_category"] = "Software"

            # Generic error detection
            elif error_keywords:
                # Use the actual error context, not just "error detected"
                error_context = []
                for line in lines:
                    if any(keyword in line.lower() for keyword in error_keywords):
                        error_context.append(line)

                if error_context:
                    main_issue = error_context[0]  # Use the actual error line
                else:
                    main_issue = f"Error: {', '.join(error_keywords[:2])}"

                classification["priority_indicators"] = error_keywords
                classification["urgency_level"] = "High"

            # Use first meaningful line if no specific patterns found
            elif lines:
                main_issue = lines[0]
                # Look for error patterns in the text
                if any(word in extracted_text_lower for word in ['error', 'fail', 'cannot', 'unable', 'problem']):
                    classification["urgency_level"] = "Medium"
                    classification["priority_indicators"] = ["error_text_detected"]

            classification["main_issue"] = main_issue

        else:
            classification["main_issue"] = "Image contains no readable text"
            classification["extraction_quality"] = "Poor"

        # Determine affected system based on actual content, not just technical analysis
        affected_system = "Unknown System"

        if extracted_text.strip():
            # Check for specific systems mentioned in the text
            if any(word in extracted_text_lower for word in ['outlook', 'exchange', 'email', 'mail']):
                affected_system = "Email System (Outlook/Exchange)"
                classification["applications_involved"] = ["Outlook", "Exchange"]
            elif any(word in extracted_text_lower for word in ['network', 'connection', 'server', 'internet', 'wifi']):
                if 'mail server' in extracted_text_lower or 'smtp' in extracted_text_lower:
                    affected_system = "Email Server (SMTP/Exchange)"
                elif 'vpn' in extracted_text_lower:
                    affected_system = "VPN Connection"
                elif 'wifi' in extracted_text_lower or 'wireless' in extracted_text_lower:
                    affected_system = "Wireless Network"
                else:
                    affected_system = "Network Infrastructure"
                classification["system_components"] = ["network", "server", "connection"]
            elif any(word in extracted_text_lower for word in ['excel', 'word', 'powerpoint', 'office']):
                app_name = next((word.title() for word in ['excel', 'word', 'powerpoint', 'office'] if word in extracted_text_lower), "Office")
                affected_system = f"Microsoft {app_name}"
                classification["applications_involved"] = [app_name]
            elif any(word in extracted_text_lower for word in ['teams', 'skype', 'zoom']):
                app_name = next((word.title() for word in ['teams', 'skype', 'zoom'] if word in extracted_text_lower), "Communication")
                affected_system = f"{app_name} Application"
                classification["applications_involved"] = [app_name]
            elif any(word in extracted_text_lower for word in ['windows', 'system', 'computer', 'pc']):
                affected_system = "Windows Operating System"
                classification["system_components"] = ["Windows", "Operating System"]
            elif any(word in extracted_text_lower for word in ['printer', 'print', 'scanner']):
                affected_system = "Printer/Print System"
                classification["system_components"] = ["printer", "print spooler"]
            elif any(word in extracted_text_lower for word in ['file', 'folder', 'document', 'share']):
                affected_system = "File System/Shared Drives"
                classification["system_components"] = ["file system", "shared drives"]
            else:
                # Fallback to technical analysis
                apps = technical_analysis.get('applications', [])
                if apps:
                    affected_system = f"Application: {', '.join(apps[:2])}"
                    classification["applications_involved"] = apps

                network_terms = technical_analysis.get('network_terms', [])
                if network_terms:
                    affected_system = f"Network: {', '.join(network_terms[:2])}"
                    classification["system_components"].extend(network_terms)

                os_systems = technical_analysis.get('operating_systems', [])
                if os_systems:
                    affected_system = f"System: {', '.join(os_systems[:1])}"
                    classification["system_components"].extend(os_systems)

        # Ensure we have the technical analysis data for later use
        apps = technical_analysis.get('applications', [])
        network_terms = technical_analysis.get('network_terms', [])
        hardware_terms = technical_analysis.get('hardware_terms', [])

        classification["affected_system"] = affected_system

        # Collect specific technical keywords from analysis and text - avoid generic terms
        all_keywords = []

        # Get keywords from technical analysis, but filter out generic terms
        generic_terms = [
            'image', 'analysis', 'screenshot', 'error', 'dialog', 'window', 'button', 'click', 'menu',
            'image analysis', 'error screenshot', 'tutors nearby', 'nearby', 'tutors',
            'visual', 'display', 'screen', 'picture', 'photo', 'capture', 'interface', 'tab'
        ]

        for category, items in technical_analysis.items():
            if isinstance(items, list):
                # Filter out generic terms
                specific_items = [item for item in items if item.lower() not in generic_terms and len(item) > 2]
                all_keywords.extend(specific_items)

        # Extract additional technical terms from text
        if extracted_text.strip():
            # Common technical terms to look for - focus on specific technical content
            tech_patterns = [
                r'\b[A-Z]{2,}[0-9]+\b',  # Error codes like HTTP404, DNS53
                r'\b\w+\.exe\b',         # Executable files
                r'\b\w+\.dll\b',         # DLL files
                r'\b\w+\.com\b',         # Domain names
                r'\b\d+\.\d+\.\d+\.\d+\b',  # IP addresses
                r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Application names like "Microsoft Outlook"
                r'\b0x[0-9A-Fa-f]+\b',  # Hexadecimal error codes
                r'\b[A-Z]{3,}\b'         # Acronyms like VPN, DNS, SMTP
            ]

            import re
            for pattern in tech_patterns:
                matches = re.findall(pattern, original_text)
                # Filter out generic matches
                specific_matches = [match for match in matches if match.lower() not in generic_terms]
                all_keywords.extend(specific_matches)

            # Look for specific application and system names in text
            specific_terms = [
                'outlook', 'excel', 'word', 'teams', 'chrome', 'firefox', 'windows', 'office',
                'vpn', 'dns', 'smtp', 'imap', 'pop3', 'exchange', 'sharepoint', 'onedrive',
                'network', 'server', 'database', 'sql', 'oracle', 'mysql', 'printer',
                'wifi', 'ethernet', 'router', 'firewall', 'antivirus', 'backup'
            ]

            for term in specific_terms:
                if term in extracted_text_lower:
                    all_keywords.append(term.upper() if len(term) <= 4 else term.title())

        # Remove duplicates and generic terms, keep only meaningful technical keywords
        filtered_keywords = []
        for keyword in set(all_keywords):
            keyword_lower = keyword.lower().strip()
            # More comprehensive filtering
            if (keyword_lower not in generic_terms and
                len(keyword.strip()) > 2 and
                not any(generic in keyword_lower for generic in ['image analysis', 'error screenshot', 'screenshot', 'tutors nearby', 'nearby']) and
                keyword_lower not in ['error', 'image', 'analysis', 'screenshot', 'tutors', 'nearby']):
                filtered_keywords.append(keyword.strip())

        classification["technical_keywords"] = filtered_keywords[:15]

        # Extract error codes and messages from actual text content
        error_codes = []
        error_messages = []

        if extracted_text.strip():
            # Look for error codes in text
            import re
            code_patterns = [
                r'error\s*[:\-]?\s*(\d+)',
                r'0x[0-9a-fA-F]+',
                r'[A-Z]{2,}\d{3,}',
                r'\b\d{4,}\b'
            ]

            for pattern in code_patterns:
                matches = re.findall(pattern, original_text, re.IGNORECASE)
                error_codes.extend(matches)

            classification["error_codes"] = list(set(error_codes))[:5]

            # Extract actual error messages from text lines
            lines = [line.strip() for line in original_text.split('\n') if line.strip()]

            # Look for lines containing error-related keywords
            error_indicators = ['error', 'fail', 'cannot', 'unable', 'problem', 'exception', 'warning', 'alert']
            error_lines = []

            for line in lines:
                if any(indicator in line.lower() for indicator in error_indicators):
                    error_lines.append(line)

            if error_lines:
                classification["error_messages"] = ' | '.join(error_lines[:3])
                classification["visual_indicators"].append("error_text")
            elif lines:
                # If no explicit error keywords, use meaningful lines
                meaningful_lines = [line for line in lines if len(line) > 5]
                if meaningful_lines:
                    classification["error_messages"] = meaningful_lines[0]

            # If we found error codes, add them to error messages
            if error_codes:
                if classification["error_messages"] == "No error messages found":
                    classification["error_messages"] = f"Error codes found: {', '.join(error_codes[:3])}"
                else:
                    classification["error_messages"] += f" | Codes: {', '.join(error_codes[:3])}"

        # Assess urgency based on keywords
        critical_keywords = ['crash', 'freeze', 'corrupt', 'access denied', 'blue screen', 'fatal']
        high_keywords = ['error', 'fail', 'cannot', 'unable', 'timeout', 'connection']

        if any(keyword in extracted_text for keyword in critical_keywords):
            classification["urgency_level"] = "Critical"
            classification["business_impact"] = "High"
            classification["escalation_needed"] = "Yes"
        elif any(keyword in extracted_text for keyword in high_keywords):
            classification["urgency_level"] = "High"
            classification["business_impact"] = "Medium"
        elif error_keywords:
            classification["urgency_level"] = "Medium"
            classification["business_impact"] = "Medium"
        else:
            classification["urgency_level"] = "Low"
            classification["business_impact"] = "Low"

        # Determine image type
        if image_metadata.get('likely_error_screenshot'):
            classification["image_type"] = "error_dialog"
        elif extracted_text and 'blue screen' in extracted_text_lower:
            classification["image_type"] = "blue_screen"
        elif extracted_text and any(app in extracted_text_lower for app in ['outlook', 'excel', 'word', 'teams']):
            classification["image_type"] = "application_screenshot"

        # Visual indicators
        visual_indicators = []
        if error_detection.get('dialog_box'):
            visual_indicators.append("dialog box")
        if error_keywords:
            visual_indicators.append("error text")
        if extracted_text and 'warning' in extracted_text_lower:
            visual_indicators.append("warning message")

        classification["visual_indicators"] = visual_indicators

        # UI elements detection
        ui_elements = []
        if extracted_text:
            ui_keywords = ['button', 'menu', 'dialog', 'window', 'tab', 'ok', 'cancel', 'close']
            for keyword in ui_keywords:
                if keyword in extracted_text_lower:
                    ui_elements.append(keyword)
        classification["ui_elements"] = list(set(ui_elements))

        # Resolution category
        if apps:
            classification["resolution_category"] = "Application_Troubleshooting"
            classification["suggested_actions"] = ["Restart application", "Check application settings"]
        elif network_terms:
            classification["resolution_category"] = "Network_Troubleshooting"
            classification["suggested_actions"] = ["Check network connection", "Verify network settings"]
        elif hardware_terms:
            classification["resolution_category"] = "Hardware_Diagnostics"
            classification["suggested_actions"] = ["Check hardware connections", "Run hardware diagnostics"]
        elif error_keywords:
            classification["resolution_category"] = "Error_Resolution"
            classification["suggested_actions"] = ["Review error details", "Check system logs"]

        # Assess extraction quality
        text_length = image_metadata.get('text_length', 0)
        if text_length > 100:
            classification["extraction_quality"] = "Excellent"
            classification["confidence_score"] = "High"
        elif text_length > 50:
            classification["extraction_quality"] = "Good"
            classification["confidence_score"] = "Medium"
        elif text_length > 10:
            classification["extraction_quality"] = "Fair"
            classification["confidence_score"] = "Medium"
        else:
            classification["extraction_quality"] = "Poor"
            classification["confidence_score"] = "Low"

        # Additional context - focus on specific technical details
        context_parts = []
        if image_metadata.get('has_text'):
            context_parts.append("Contains readable text")
        if image_metadata.get('likely_error_screenshot'):
            # Be more specific about what type of error
            if any(app in classification.get("applications_involved", []) for app in ["Outlook", "Excel", "Word", "Teams"]):
                context_parts.append("Application error detected")
            elif "network" in classification.get("main_issue", "").lower():
                context_parts.append("Network issue detected")
            else:
                context_parts.append("System error detected")
        if len(classification["technical_keywords"]) > 5:
            context_parts.append("Rich technical content")

        classification["additional_context"] = "; ".join(context_parts)

        return classification

    def process_image(self, image_path: str, model: str = 'mixtral-8x7b') -> Optional[Dict]:
        """
        Complete image processing pipeline: validation, metadata extraction, and classification.

        Args:
            image_path (str): Path to the image file
            model (str): LLM model to use for classification

        Returns:
            dict: Complete image processing results
        """
        # Process image quietly
        if not self.validate_image(image_path):
            return None

        image_metadata = self.extract_image_metadata(image_path)
        if not image_metadata:
            return None

        classification_result = self.classify_image_content(image_metadata, model)

        # Step 4: Combine results
        complete_result = {
            'image_path': image_path,
            'processing_status': 'success',
            'metadata': image_metadata,
            'classification': classification_result,
            'has_useful_content': image_metadata.get('has_text', False) or image_metadata.get('likely_error_screenshot', False)
        }

        return complete_result

    def convert_image_to_base64(self, image_path: str) -> Optional[str]:
        """
        Convert image to base64 string for storage or transmission.

        Args:
            image_path (str): Path to the image file

        Returns:
            str: Base64 encoded image string
        """
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded_string
        except Exception as e:
            print(f"Failed to convert image to base64: {e}")
            return None

    def save_processed_image_data(self, image_result: Dict, output_path: str = None) -> bool:
        """
        Save processed image data to JSON file.

        Args:
            image_result (dict): Complete image processing results
            output_path (str): Path to save the JSON file (optional)

        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            if not output_path:
                image_name = os.path.splitext(os.path.basename(image_result['image_path']))[0]
                output_path = f"processed_image_{image_name}.json"

            # Remove large binary data for JSON storage
            save_data = image_result.copy()
            if 'metadata' in save_data and 'image_info' in save_data['metadata']:
                # Keep only essential image info
                essential_info = {
                    'filename': save_data['metadata']['image_info'].get('filename'),
                    'format': save_data['metadata']['image_info'].get('format'),
                    'size': save_data['metadata']['image_info'].get('size')
                }
                save_data['metadata']['image_info'] = essential_info

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)

            print(f"Processed image data saved to: {output_path}")
            return True

        except Exception as e:
            print(f"Failed to save processed image data: {e}")
            return False
