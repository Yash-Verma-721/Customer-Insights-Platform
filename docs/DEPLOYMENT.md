# Deployment & Environment Setup

This document outlines how to initialize and deploy the Customer Insights Platform locally or on a production server.

## Prerequisites
- **Python Version**: Python 3.9+ is strictly required.
- **Operating System**: Windows, macOS, or Linux (Ubuntu recommended for production).

## Environment Setup
1. Clone the repository to your target machine.
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(Ensure `streamlit`, `pandas`, `plotly`, and `pytest` are installed.)*

## Database Initialization
The application utilizes SQLite. You do not need to install an external SQL server.
1. The database initializes automatically upon startup.
2. The `app.py` script automatically runs `create_database()` and `migrate_database()` which provisions the schema inside a local `analytics.db` file.

## Running the Application
To launch the platform, execute the Streamlit runner:
```bash
streamlit run app.py
```
By default, the application will bind to `localhost` on port `8501`.

## Core Folder Structure
- `app.py`: The entry point and main Streamlit router.
- `modules/`: Streamlit UI rendering views (e.g., dashboard, login, checkout).
- `services/`: Business logic orchestration and transaction management.
- `database/`: Repository data access layer and SQLite DDL migrations.
- `core/`: Global logging configurations and custom application exceptions.
- `config/`: Centralized enums (Roles, Statuses) and navigation trees.
- `tests/`: Pytest unit testing suite.
- `datasets/`: Local storage for user-uploaded CSV analytics files.
