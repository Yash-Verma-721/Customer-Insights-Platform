# Application Architecture

This document outlines the high-level architecture of the Customer Insights Platform.

## Core Architectural Pattern

The application utilizes a **layered architecture** to strictly separate concerns, improve maintainability, and enable isolated testing.

```ascii
[ Streamlit UI ]
       |
       v
[ Service Layer ]
       |
       v
[ Repository Layer ]
       |
       v
[ SQLite Database ]
```

### 1. Presentation Layer (Streamlit UI)
- **Responsibility**: Rendering UI components, managing session state (`st.session_state`), and capturing user input.
- **Constraints**: Contains absolutely **no** business logic or direct database connections. It purely passes data down to the services and renders what is returned.

### 2. Service Layer (Business Logic)
- **Responsibility**: Orchestrating workflows, applying mathematical/business rules (e.g., commission calculation), validating inventory, and managing ACID database transactions (`BEGIN TRANSACTION`, `COMMIT`, `ROLLBACK`).
- **Constraints**: Interacts with the Repository layer for all data persistence. Raises and catches domain-specific custom exceptions (e.g., `InventoryError`).

### 3. Repository Layer (Data Access)
- **Responsibility**: Executing pure SQL queries (`SELECT`, `INSERT`, `UPDATE`, `DELETE`).
- **Constraints**: Contains no business orchestration. Functions typically accept a raw `cursor` object or simple primitives, parameterize the SQL, and return raw tuples or integer rowcounts.

### 4. Database (SQLite)
- **Responsibility**: Relational data persistence with strictly enforced foreign key constraints to ensure referential integrity between vendors, products, inventory, orders, and payments.

---

## Marketplace Workflow

The following visualizes the exact sequence of events when a customer purchases an item from the marketplace:

```ascii
[ Marketplace ]
      | (Customer browses active products with stock > 0)
      v
[ Shopping Cart ]
      | (Customer adds items to session-based cart)
      v
[ Checkout Service ]
      | (Customer submits shipping details)
      v
[ Inventory Constraint Check ] -> IF INSUFFICIENT STOCK -> [ Rollback & Error ]
      | (Verify stock exists, decrement stock levels)
      v
[ Order Creation ]
      | (Generate unique ORD- ID, insert into 'orders')
      v
[ Order Items Creation ]
      | (Insert into 'order_items' mapping to Product ID)
      v
[ Payment Service ]
      | (On-demand/Async loop calculates commission & vendor payout)
      v
[ Database Commit ]
```
