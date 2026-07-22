# Testing Strategy

This document outlines the testing methodology applied to the Customer Insights Platform.

## 1. Unit Testing Strategy
The application utilizes `pytest` to execute unit tests. The primary objective is to test the **Service Layer**—the orchestration, mathematics, constraints, and error handling of the business logic.

## 2. Mock Strategy
The platform is designed to be tested **without a physical database**. 
- Using `unittest.mock.patch`, the core `database.connection.get_connection` module is intercepted and replaced with a `MagicMock()`.
- Tests never write to disk, ensuring zero side-effects and lightning-fast execution.

## 3. Repository Isolation
Because the Service layer relies on Repositories for data access, tests mock the underlying repository functions entirely. 
For example, in `test_checkout.py`:
```python
@patch('services.checkout_service.get_inventory_stock')
```
This forces the repository to return a predetermined stock integer, allowing the test to strictly validate the Service's mathematical logic (e.g., triggering an `InventoryError` when requested quantity exceeds the mocked integer).

## 4. Service Testing
Tests heavily cover specific domain outcomes:
- **Math**: Verifying that `process_vendor_payouts` correctly applies the percentage commission rate to extract the correct net payout amount.
- **Security**: Verifying that `add_inventory` explicitly blocks a user if the mocked `check_product_ownership` hook returns `False`.

## 5. Rollback Testing
A critical component of the platform is transactional integrity. Tests simulate random failures by injecting `Exception` side-effects into mocked database functions. The tests subsequently `assert mock_conn.rollback.assert_called_once()` to guarantee that partial data corruption is impossible during catastrophic failures.
