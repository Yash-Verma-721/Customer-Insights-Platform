import streamlit as st
import pandas as pd


def show_upload():

    st.title("📂 Upload Dataset")

    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=["csv", "xlsx"]
    )

    if uploaded_file is None:
        st.info("Please upload a CSV or Excel file.")
        return

    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.session_state["df"] = df

        st.success("Dataset loaded successfully!")

        st.write(f"**File Name:** {uploaded_file.name}")

        st.subheader("Dataset Information")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Rows", df.shape[0])

        with col2:
            st.metric("Columns", df.shape[1])

        st.subheader("Dataset Preview")
        st.dataframe(df.head())
    
        st.subheader("Column Names")
        st.write(df.columns.tolist())

        st.subheader("Data Types")
        st.dataframe(
            df.dtypes.reset_index().rename(
                columns={
                    "index": "Column",
                    0: "Data Type"
                 }
             )
         )
    except Exception:
        st.error("Unable to read the uploaded file.")
    