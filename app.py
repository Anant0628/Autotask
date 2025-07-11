"""
TeamLogic-AutoTask Application
Updated to use new login-based UI structure with role-based navigation.
"""

import warnings
warnings.filterwarnings("ignore", message="You have an incompatible version of 'pyarrow' installed")

import streamlit as st
import sys
import os

# Add the src directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import the new UI pages
from src.ui.login import main as login_main
from src.ui.Pages.User import main as user_main
from src.ui.Pages.Technician import main as technician_main
from src.ui.Pages.Admin import main as admin_main


def main():
    """Main application entry point with new login-based UI structure."""
    
    # Initialize session state for role-based navigation
    if "current_role" not in st.session_state:
        st.session_state.current_role = None
    
    # Route based on selected role
    if st.session_state.current_role == "technician":
        # Run technician UI
        technician_main()
    elif st.session_state.current_role == "user":
        # Run user UI
        user_main()
    elif st.session_state.current_role == "admin":
        # Run admin UI
        admin_main()
    else:
        # Show login page
        login_main()


if __name__ == "__main__":
    main()
