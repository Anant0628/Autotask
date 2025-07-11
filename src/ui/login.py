import streamlit as st
from PIL import Image

def main():
    """Main login page function."""
    st.set_page_config(page_title="Login Panel", page_icon="🔐", layout="centered")

    # ----- Styling -----
    st.markdown("""
        <style>
        .title {
            font-size: 40px;
            font-weight: 700;
            color: #4CAF50;
            text-align: center;
            margin-bottom: 20px;
        }
        .subtitle {
            font-size: 20px;
            color: #555;
            text-align: center;
            margin-bottom: 30px;
        }
        .button-container {
            display: flex;
            justify-content: center;
            gap: 50px;
        }
        .stButton button {
            width: 200px;
            height: 60px;
            font-size: 20px;
            border-radius: 12px;
        }
        </style>
    """, unsafe_allow_html=True)

    # ----- Title and Subtitle -----
    st.markdown('<div class="title">Welcome to the Panel</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Please select your role to proceed</div>', unsafe_allow_html=True)

    # ----- Buttons for Technician and User -----
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        technician = st.button("👨‍🔧 Technician", use_container_width=True)
        user = st.button("🧑‍💻 User", use_container_width=True)

    # ----- Routing based on selection -----
    if technician:
        st.success("Redirecting to Technician UI...")
        st.session_state.current_role = "technician"
        st.rerun()

    if user:
        st.success("Redirecting to User UI...")
        st.session_state.current_role = "user"
        st.rerun()

    # ----- Footer -----
    st.markdown("---")
    st.markdown("<p style='text-align: center; color: gray;'>© 2025 Your Company. All rights reserved.</p>", unsafe_allow_html=True)
