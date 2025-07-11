"""
Data Management Package
Contains data management and knowledge base operations.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.data.data_manager import DataManager

__all__ = ['DataManager']
