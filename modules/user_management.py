import streamlit as st
from auth.auth_utils import get_all_users, update_user_role
from utils.ui_helpers import render_header, render_help_expander, render_footer, show_smart_notification

def show_user_management():
    if st.session_state.get("role") != "Admin":
        st.error("Access Denied. This page is restricted to Administrators.")
        return

    render_header(
        "User Management",
        "Manage platform access and assign user roles.",
        "Administration"
    )
    
    render_help_expander(
        "View all registered users in the platform. You can change their roles to control what modules and data they can access. "
        "Analysts have full access excluding User Management. Managers can only view the Dashboard and Analytics without making changes."
    )

    st.markdown("### Registered Users")
    
    users = get_all_users()
    if not users:
        st.info("No users found.")
        render_footer("User Management")
        return
        
    for u in users:
        user_id, full_name, username, email, role, created_at = u
        
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            with col1:
                st.markdown(f"**{full_name}**<br><small>{email}</small>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"**Username:** {username}<br><small>Joined: {created_at[:10]}</small>", unsafe_allow_html=True)
            with col3:
                role_options = ["Admin", "Business Analyst", "Manager"]
                safe_index = role_options.index(role) if role in role_options else 2
                
                new_role = st.selectbox(
                    "Role", 
                    options=role_options, 
                    index=safe_index,
                    key=f"role_{user_id}",
                    label_visibility="collapsed",
                    format_func=lambda x: "Analyst" if x == "Business Analyst" else x
                )
            with col4:
                if st.button("Update", key=f"update_{user_id}", use_container_width=True):
                    if new_role != role:
                        update_user_role(user_id, new_role)
                        show_smart_notification("success", f"Updated {full_name}'s role to {new_role}.")
                        st.rerun()
                    else:
                        show_smart_notification("info", "No changes made.")
                        
    render_footer("User Management")
