"""
Lightweight compatibility layer for database.py to prevent breaking existing imports.
This module now simply re-exports functions from their respective repositories and services.
"""

from .connection import get_connection, DATABASE_NAME
from .migration import create_database, migrate_database, create_marketplace_tables
from .dataset_repository import (
    update_dataset_metadata, 
    update_report_metadata, 
    get_dataset_metadata, 
    get_all_published_datasets, 
    publish_dataset
)

from services.vendor_service import update_vendor_profile, add_product, update_product, delete_product
from database.vendor_repository import get_vendor_profile
from database.product_repository import get_vendor_products, get_active_marketplace_products
from services.inventory_service import add_inventory, update_inventory
from database.inventory_repository import get_vendor_inventory

from services.checkout_service import process_checkout
from services.payment_service import process_vendor_payouts
from database.payment_repository import get_vendor_payments

if __name__ == "__main__":
    create_database()
    migrate_database()
    print("Database created and migrated successfully!")
