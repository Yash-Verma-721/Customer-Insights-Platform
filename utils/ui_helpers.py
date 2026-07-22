import streamlit as st
import datetime
import pandas as pd

def render_header(title, description, current_step_name):
    """Renders the standard page header."""
    st.title(title)
    st.markdown(f"**{description}**")
    st.caption(f"Current Workflow Step: {current_step_name}")
    st.divider()

def render_empty_state(message="No customer dataset available. Please import a CSV or Excel file to begin analysis."):
    """Renders a standard empty state when no dataset is present."""
    st.warning(message)
    role = st.session_state.get('role', 'Manager')
    if role in ["Admin", "Business Analyst"]:
        if st.button("Go to Dataset Workspace"):
            st.session_state.current_nav = "Dataset Workspace"
            st.rerun()

def show_smart_notification(type, message):
    """Displays a standardized smart notification."""
    if type == "success":
        st.success(message)
    elif type == "warning":
        st.warning(message)
    elif type == "error":
        st.error(message)
    elif type == "info":
        st.info(message)

def render_help_expander(text):
    """Renders the 'About This Page' help section."""
    with st.expander("About This Page"):
        st.markdown(text)

def render_footer(module_name):
    """Renders the standard page footer."""
    st.divider()
    st.markdown(f"""
    <div style='text-align: center; color: gray; font-size: 12px;'>
        <p><strong>Customer Insights Platform</strong> | Version 1.0</p>
        <p>Built with Python, Streamlit, Pandas, and Plotly</p>
        <p>Infosys Internship Project</p>
        <p>Current Module: {module_name} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    """, unsafe_allow_html=True)

def calculate_readiness_score(df):
    """Calculates a Customer Data Readiness Score (0-100) based on data quality."""
    score = 100
    total_rows = len(df)
    total_cols = len(df.columns)
    
    if total_rows == 0 or total_cols == 0:
        return 0
        
    missing_ratio = df.isnull().sum().sum() / (total_rows * total_cols)
    duplicate_ratio = df.duplicated().sum() / total_rows if total_rows > 0 else 0
    
    # Deductions
    if missing_ratio > 0:
        score -= min(50, missing_ratio * 100 * 2) # max 50 points deduction
    if duplicate_ratio > 0:
        score -= min(30, duplicate_ratio * 100 * 2) # max 30 points deduction
        
    if total_rows < 100:
        score -= 10 # Small dataset penalty
        
    return max(0, int(score))

def get_color_badge(score):
    if score >= 90:
        return "Excellent"
    elif score >= 70:
        return "Good"
    else:
        return "Needs Attention"

def add_session_log(action):
    """Adds an action to the session log."""
    if "activity_log" not in st.session_state:
        st.session_state.activity_log = []
    
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.activity_log.append(f"[{timestamp}] {action}")



def display_session_log():
    """Displays the activity log in the sidebar or a designated section."""
    if "activity_log" in st.session_state and st.session_state.activity_log:
        with st.expander("Session Activity Log"):
            for log in reversed(st.session_state.activity_log):
                st.markdown(f"`{log}`")

import contextlib

@contextlib.contextmanager
def branded_spinner(message="Loading..."):
    placeholder = st.empty()
    spans = "".join([
        f"<span style='animation-delay: {i*0.1}s' class='brand-letter'>{char if char != ' ' else '&nbsp;'}</span>"
        for i, char in enumerate(message)
    ])
    html = f"<div class='branded-spinner'>{spans}</div>"
    placeholder.markdown(html, unsafe_allow_html=True)
    try:
        yield
    finally:
        placeholder.empty()
