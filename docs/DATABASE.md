# Database Schema

This document details the SQLite database schema utilized by the Customer Insights Platform.

## Tables Overview

### 1. `users`
Core authentication table containing all registered accounts across all roles (Admin, Manager, Analyst, Vendor, Guest).
- **Primary Key**: `id`
- **Fields**: `username`, `password_hash`, `role`, `created_at`

### 2. `vendors`
Holds the business profile details for users with the 'Vendor' role.
- **Primary Key**: `id`
- **Foreign Key**: `user_id` references `users(id)`
- **Fields**: `vendor_name`, `owner_name`, `phone_number`, `gst_number`, `address`, `city`, `state`, `commission_rate`

### 3. `products`
The marketplace catalog. Every product is strictly owned by one vendor.
- **Primary Key**: `id`
- **Foreign Key**: `vendor_id` references `vendors(id)`
- **Fields**: `product_name`, `category`, `price`, `description`, `status` (Active/Inactive)

### 4. `inventory`
Tracks stock levels and reorder thresholds for specific products.
- **Primary Key**: `id`
- **Foreign Key**: `product_id` references `products(id)`
- **Fields**: `current_stock`, `reorder_level`, `updated_at`

### 5. `orders`
Represents a finalized customer checkout event.
- **Primary Key**: `id`
- **Fields**: `order_code` (UUID), `customer_name`, `customer_email`, `customer_phone`, `region`, `total_amount`, `payment_status`, `order_status`, `order_date`

### 6. `order_items`
Maps multiple products to a single order.
- **Primary Key**: `id`
- **Foreign Keys**: 
  - `order_id` references `orders(id)`
  - `product_id` references `products(id)`
- **Fields**: `quantity`, `unit_price`

### 7. `payments`
Tracks financial settlements and commission deductions generated from finalized orders.
- **Primary Key**: `id`
- **Foreign Keys**:
  - `order_id` references `orders(id)`
  - `vendor_id` references `vendors(id)`
- **Fields**: `gross_amount`, `commission_amount`, `net_payout`, `status`, `settlement_date`

### 8. `datasets` & `dataset_metadata`
Tracks uploaded raw CSV datasets and their analytical health scores used by internal Analysts/Managers.
- **Primary Key**: `id`
- **Fields**: `dataset_name`, `uploaded_by`, `total_rows`, `total_columns`, `dataset_health`, `dataset_status`
