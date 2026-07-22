# config/demo_seed.py

DEMO_SEED = 42
DEMO_PREFIX = "demo_"
DEMO_EMAIL_DOMAIN = "demo.marketplace.com"

# Accounts
NUM_VENDORS = 5
NUM_CUSTOMERS = 10

# Products
PRODUCTS_PER_VENDOR = 10

# Orders
TOTAL_ORDERS = 100

# Order Status Distribution (Percentage out of 100)
ORDER_STATUS_DISTRIBUTION = {
    "Pending": 15,
    "Processing": 0,
    "Confirmed": 10,
    "Packed": 15,
    "Shipped": 20,
    "Delivered": 35,
    "Cancelled": 5,
}

# Inventory Distribution
INVENTORY_LEVELS = [0, 3, 8, 50, 100]

# Settlement Status Distribution
SETTLEMENT_STATUS_DISTRIBUTION = {
    "Pending": 40,
    "Paid": 60,
}
