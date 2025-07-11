"""
Processors Package
Contains data processors for AI, tickets, and images.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.processors.ai_processor import AIProcessor
from src.processors.ticket_processor import TicketProcessor
from src.processors.image_processor import ImageProcessor

__all__ = [
    'AIProcessor',
    'TicketProcessor',
    'ImageProcessor'
]
