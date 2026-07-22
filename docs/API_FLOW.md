# API & Data Flow

While the application does not run a traditional REST API (it uses Streamlit for direct UI rendering), the internal data flow between modules follows strict API-like contract patterns.

## Flow of Execution

1. **User Action**: A user clicks a button (e.g., "Checkout") in the Streamlit UI (`modules/checkout.py`).
2. **UI Data Gathering**: Streamlit packages the raw input forms into dictionaries or primitives.
3. **Service Invocation**: The UI explicitly imports and calls a Service layer function (e.g., `checkout_service.process_checkout`).
4. **Service Orchestration**:
    - The Service requests a raw DB connection from `get_connection()`.
    - The Service triggers `BEGIN TRANSACTION`.
    - The Service calls multiple Repository layer functions passing the `cursor`.
5. **Repository Execution**: The Repository constructs the parameterized SQL, executes it against SQLite, and returns.
6. **Service Resolution**: The Service catches any `AppError` exceptions. If successful, it commits. If failed, it rolls back. It returns a boolean and a string message `(True, "Order ORD-123 Successful")`.
7. **UI Render**: The Streamlit UI unpacks the tuple and renders `st.success()` or `st.error()` directly to the user.
