"""
Simplified image processing utilities for support ticket emails.
Main functionality moved to app_refactored.py for better integration.
"""

import os
import json
from image_processor import ImageProcessor


def process_single_image(image_path):
    """
    Process a single image and return comprehensive classification data in JSON format.
    Used by app_refactored.py for email image processing.

    Returns all necessary fields for ticket classification.
    """
    try:
        processor = ImageProcessor(db_connection=None)
        result = processor.process_image(image_path)

        if not result:
            # Try to extract basic metadata even if processing failed
            try:
                metadata = processor.extract_image_metadata(image_path)
                if metadata and metadata.get('extracted_text'):
                    return processor._rule_based_classification(metadata)
            except:
                pass
            return _get_default_classification("No readable content found in image")

        # Check if we have classification data from the enhanced processor
        if 'classification' in result and result['classification']:
            classification = result['classification']
            # Ensure all required fields are present
            return _ensure_complete_classification(classification)

        # Fallback: extract from metadata using rule-based classification
        metadata = result.get('metadata', {})
        if metadata:
            # Use the enhanced rule-based classification directly
            return processor._rule_based_classification(metadata)
        else:
            return _extract_from_metadata(metadata)

    except Exception as e:
        # Even on error, try to extract basic content
        try:
            processor = ImageProcessor(db_connection=None)
            metadata = processor.extract_image_metadata(image_path)
            if metadata and metadata.get('extracted_text'):
                return processor._rule_based_classification(metadata)
        except:
            pass

        print(f"Error processing image {image_path}: {e}")
        return _get_default_classification("Unable to process image content")

def _get_default_classification(error_message="Unknown issue"):
    """Return default classification structure with all required fields."""
    return {
        "main_issue": error_message if error_message != "Unknown" else "Unable to determine issue from image",
        "issue_category": "Technical",
        "affected_system": "Unknown System",
        "error_messages": error_message if error_message != "Unknown" else "No error details available",
        "urgency_level": "Low",
        "priority_indicators": [],
        "business_impact": "Unknown",
        "technical_keywords": [],
        "error_codes": [],
        "system_components": [],
        "applications_involved": [],
        "image_type": "Unknown",
        "visual_indicators": [],
        "ui_elements": [],
        "resolution_category": "General_Support",
        "suggested_actions": ["Review image manually", "Contact support for assistance"],
        "escalation_needed": "No",
        "confidence_score": "Low",
        "extraction_quality": "Poor",
        "additional_context": "Image processing encountered issues"
    }

def _ensure_complete_classification(classification):
    """Ensure classification has all required fields."""
    default = _get_default_classification()

    # Merge with defaults to ensure all fields are present
    for key, default_value in default.items():
        if key not in classification:
            classification[key] = default_value

    return classification

def _extract_from_metadata(metadata):
    """Extract classification from metadata (legacy support)."""
    extracted_text = metadata.get('extracted_text', '')
    technical_analysis = metadata.get('technical_analysis', {})
    error_detection = metadata.get('error_detection', {})

    # Build comprehensive classification from metadata
    classification = _get_default_classification()

    # Update with extracted information
    classification.update({
        "main_issue": _extract_main_issue(extracted_text, error_detection),
        "affected_system": _extract_affected_system(technical_analysis),
        "urgency_level": _assess_urgency(error_detection, technical_analysis),
        "error_messages": _extract_error_messages(extracted_text, error_detection),
        "technical_keywords": _extract_technical_keywords(technical_analysis),
        "image_type": _determine_image_type(metadata),
        "visual_indicators": _describe_visual_indicators(error_detection),
        "resolution_category": _suggest_resolution_approach(technical_analysis, error_detection),
        "confidence_score": _assess_confidence(metadata)
    })

    return classification

# Helper functions (private)
def _extract_main_issue(text, error_detection):
    error_keywords = error_detection.get('error_keywords', [])
    if error_keywords:
        return f"Error detected: {', '.join(error_keywords[:3])}"
    elif text:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return lines[0] if lines else "Unknown"
    return "Unknown"

def _extract_affected_system(technical_analysis):
    if 'applications' in technical_analysis and technical_analysis['applications']:
        return f"Application: {', '.join(technical_analysis['applications'][:2])}"
    elif 'operating_systems' in technical_analysis and technical_analysis['operating_systems']:
        return f"OS: {', '.join(technical_analysis['operating_systems'][:1])}"
    elif 'system_components' in technical_analysis and technical_analysis['system_components']:
        return f"System: {', '.join(technical_analysis['system_components'][:2])}"
    return "Unknown"

def _assess_urgency(error_detection, technical_analysis):
    error_keywords = error_detection.get('error_keywords', [])
    critical_keywords = ['crash', 'freeze', 'corrupt', 'access denied']
    if any(keyword in error_keywords for keyword in critical_keywords):
        return "Critical"
    elif error_keywords:
        return "High"
    elif technical_analysis:
        return "Medium"
    return "Low"

def _extract_error_messages(text, error_detection):
    error_keywords = error_detection.get('error_keywords', [])
    if error_keywords:
        lines = text.split('\n')
        error_lines = [line.strip() for line in lines
                      if any(keyword in line.lower() for keyword in error_keywords)]
        return '; '.join(error_lines[:2]) if error_lines else "Error detected"
    return "Unknown"

def _extract_technical_keywords(technical_analysis):
    keywords = []
    for category, items in technical_analysis.items():
        if isinstance(items, list):
            keywords.extend(items)
    return keywords[:10]

def _determine_image_type(metadata):
    if metadata.get('likely_error_screenshot'):
        return "error_dialog"
    elif metadata.get('has_text'):
        return "application_screenshot"
    return "Unknown"

def _describe_visual_indicators(error_detection):
    indicators = []
    if error_detection.get('dialog_box'):
        indicators.append("dialog box")
    if error_detection.get('error_keywords'):
        indicators.append("error text")
    return ', '.join(indicators) if indicators else "Unknown"

def _suggest_resolution_approach(technical_analysis, error_detection):
    if 'applications' in technical_analysis and technical_analysis['applications']:
        return "Application troubleshooting"
    elif 'network_terms' in technical_analysis and technical_analysis['network_terms']:
        return "Network connectivity check"
    elif 'hardware_terms' in technical_analysis and technical_analysis['hardware_terms']:
        return "Hardware diagnostics"
    elif error_detection.get('error_keywords'):
        return "Error-specific troubleshooting"
    return "General IT support"

def _assess_confidence(metadata):
    text_length = metadata.get('text_length', 0)
    has_technical = bool(metadata.get('technical_analysis'))
    has_errors = metadata.get('likely_error_screenshot', False)
    if text_length > 50 and (has_technical or has_errors):
        return "High"
    elif text_length > 10 or has_technical:
        return "Medium"
    return "Low"
