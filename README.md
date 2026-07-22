# Customer Insights Platform

## Project Overview
The **Customer Insights Platform** is an enterprise-grade analytics and multi-vendor marketplace application. Built entirely on Python and Streamlit, it allows data analysts to upload, clean, and visualize massive CSV datasets, while simultaneously providing a fully functional marketplace where verified vendors can manage inventory, process orders, and track automated commission payouts.

## Features
- **Role-Based Access Control**: Discrete interfaces and authorizations for Admins, Managers, Analysts, Vendors, and Guests.
- **Dataset Management**: Upload, clean, and dynamically analyze raw CSV data with auto-calculated health scoring.
- **Advanced Analytics**: Dedicated modules for Sales, Customers, Vendors, Products, Inventory, Orders, and Payments.
- **Vendor Marketplace**: A complete multi-tenant marketplace catalog supporting guest checkout and transactional inventory deduction.
- **Automated Payouts**: Settlement engine that calculates vendor commission and net payouts dynamically from historical orders.
- **Enterprise Architecture**: Strict layered separation of concerns (UI -> Services -> Repositories) ensuring ACID compliance and maximum testability.

## Folder Structure
```
Customer Insights Platform/
├── app.py                  # Main Streamlit application entry point
├── requirements.txt        # Python dependency manifest
├── assets/                 # Custom CSS and branding assets
├── config/                 # Centralized configuration (Roles, Statuses, Navigation)
├── core/                   # Application-wide exceptions and logging configurations
├── database/               # Repository layer (Pure SQL execution)
├── datasets/               # Local storage for active and published user CSVs
├── docs/                   # Extended architectural and deployment documentation
├── logs/                   # System runtime logs (application.log)
├── modules/                # Presentation layer (Streamlit UI views and forms)
├── services/               # Business logic layer (Transactions, Math, Validation)
├── tests/                  # Pytest unit testing suite (100% mocked database)
└── utils/                  # Helper utilities for UI formatting and caching
```

## Architecture Diagram
```ascii
[ Streamlit UI ] (app.py & modules/)
       |
       v
[ Service Layer ] (services/)
       |
       v
[ Repository Layer ] (database/)
       |
       v
[ SQLite Database ] (analytics.db)
```
*(For a deeper dive into the marketplace workflow, refer to `docs/ARCHITECTURE.md`)*

## Installation
1. Ensure Python 3.9+ is installed.
2. Clone this repository.
3. Open a terminal and navigate to the project directory.
4. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration
All application state, UI routes, and authorization constraints are driven dynamically. No `.env` configuration is required out of the box. 
- Logging outputs can be found at `logs/application.log`.
- SQLite database migrations run automatically on startup.

## Running the Application
Launch the platform using the Streamlit CLI:
```bash
streamlit run app.py
```
The application will be accessible at `http://localhost:8501`.

## Testing
The application features an entirely isolated unit testing suite validating the core Service layer without physical database writes.
To run the tests:
```bash
pytest tests/
```
*(Refer to `docs/TESTING.md` for information on our mock strategy and repository isolation).*

## Screenshots
*(Placeholder: Insert application screenshots here showing the Dashboard, Dataset Analytics, and Vendor Marketplace).*

## Future Enhancements
- **Async Processing**: Offload heavy dataset cleaning operations to Celery/Redis workers.
- **Payment Gateway**: Integrate Stripe or Razorpay APIs to replace the simulated checkout flows.
- **External Database**: Migrate from SQLite to PostgreSQL for horizontal scaling in production environments.
