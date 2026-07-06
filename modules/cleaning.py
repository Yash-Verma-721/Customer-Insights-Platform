import streamlit as st
import pandas as pd




def show_cleaning():

    st.title("🧹 Data Cleaning")

    if "df" not in st.session_state:
        st.warning("Please upload a dataset first.")
        return

    df = st.session_state["df"]

    if "success_message" in st.session_state:
        st.success(st.session_state["success_message"])
        del st.session_state["success_message"]

    st.subheader("Dataset Summary")

    total_rows = df.shape[0]
    total_columns = df.shape[1]
    missing_values = df.isnull().sum().sum()
    duplicate_rows = df.duplicated().sum()

    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    with col1:
        st.metric("Rows", total_rows)

    with col2:
        st.metric("Columns", total_columns)

    with col3:
        st.metric("Missing Values", missing_values)

    with col4:
        st.metric("Duplicate Rows", duplicate_rows)

    st.subheader("Missing Values")

    missing_df = df.isnull().sum().reset_index()

    missing_df.columns = [
        "Column",
        "Missing Values"
    ]

    st.dataframe(missing_df)
    st.subheader("Data Types")

    dtype_df = df.dtypes.reset_index()

    dtype_df.columns = [
        "Column",
        "Data Type"
    ]

    st.dataframe(dtype_df)    

    st.subheader("Cleaning Actions")

    if st.button("Remove Duplicate Rows"):

        st.session_state["df"] = df.drop_duplicates()

        st.session_state["success_message"] = "Duplicate rows removed."

        st.rerun()

        

    if st.button("Fill Missing Values"):

        numeric_columns = df.select_dtypes(include="number").columns
        text_columns = df.select_dtypes(exclude="number").columns

        df[numeric_columns] = df[numeric_columns].fillna(0)
        df[text_columns] = df[text_columns].fillna("N/A")

        st.session_state["success_message"] = "Missing values filled."

        st.rerun()
    
        