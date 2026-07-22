"""
Marketplace Dataset Service
============================
Builds clean Pandas DataFrames from the Marketplace transactional database.
These are used as the PRIMARY analytics data source when no uploaded dataset
is active.

Each build_*_dataset() method returns a DataFrame ready for the corresponding
analytics module without duplicating SQL across modules.
"""

import pandas as pd
from database.connection import get_connection
from core.logger import get_logger

logger = get_logger(__name__)


def _query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Internal helper: run a SELECT and return a DataFrame."""
    conn = get_connection()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    except Exception as e:
        logger.error(f"marketplace_dataset_service query error: {e}", exc_info=True)
        return pd.DataFrame()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 1. Sales Dataset
#    Columns: order_date, order_code, order_status, payment_status,
#             total_amount, product_name, category, unit_price, quantity,
#             vendor_name, region, customer_name
# ---------------------------------------------------------------------------

def build_sales_dataset() -> pd.DataFrame:
    """Return a flat sales DataFrame joining orders → order_items → products → vendors."""
    sql = """
        SELECT
            o.order_date        AS order_date,
            o.order_code        AS order_code,
            o.order_status      AS order_status,
            o.payment_status    AS payment_status,
            o.total_amount      AS total_amount,
            o.region            AS region,
            o.customer_name     AS customer_name,
            p.product_name      AS product_name,
            p.category          AS category,
            oi.unit_price       AS unit_price,
            oi.quantity         AS quantity,
            oi.unit_price * oi.quantity AS line_revenue,
            v.vendor_name       AS vendor_name
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        JOIN products p     ON p.id = oi.product_id
        JOIN vendors v      ON v.id = p.vendor_id
        ORDER BY o.order_date DESC
    """
    df = _query(sql)
    if not df.empty and "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# 2. Customer Dataset
#    Columns: customer_name, customer_email, order_date, order_code,
#             total_amount, order_status, region
# ---------------------------------------------------------------------------

def build_customer_dataset() -> pd.DataFrame:
    """Return a customer-centric DataFrame from orders."""
    sql = """
        SELECT
            o.customer_name     AS customer_name,
            o.customer_email    AS customer_email,
            o.customer_phone    AS customer_phone,
            o.order_date        AS order_date,
            o.order_code        AS order_code,
            o.total_amount      AS total_amount,
            o.order_status      AS order_status,
            o.payment_status    AS payment_status,
            o.region            AS region
        FROM orders o
        ORDER BY o.order_date DESC
    """
    df = _query(sql)
    if not df.empty and "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# 3. Vendor Dataset
#    Columns: vendor_name, category, vendor_status, commission_rate,
#             product_name, unit_price, quantity, line_revenue, order_status
# ---------------------------------------------------------------------------

def build_vendor_dataset() -> pd.DataFrame:
    """Return a vendor-centric DataFrame for performance analytics."""
    sql = """
        SELECT
            v.vendor_name       AS vendor_name,
            v.category          AS category,
            v.vendor_status     AS vendor_status,
            v.commission_rate   AS commission_rate,
            v.rating            AS rating,
            p.product_name      AS product_name,
            oi.unit_price       AS unit_price,
            oi.quantity         AS quantity,
            oi.unit_price * oi.quantity AS line_revenue,
            oi.item_status      AS order_status,
            o.order_date        AS order_date
        FROM vendors v
        JOIN products p     ON p.vendor_id = v.id
        JOIN order_items oi ON oi.product_id = p.id
        JOIN orders o       ON o.id = oi.order_id
        ORDER BY o.order_date DESC
    """
    df = _query(sql)
    if not df.empty and "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# 4. Inventory Dataset
#    Columns: product_name, category, vendor_name, current_stock,
#             reorder_level, price, inventory_value, stock_status
# ---------------------------------------------------------------------------

def build_inventory_dataset() -> pd.DataFrame:
    """Return a product/inventory DataFrame including stock levels and valuation."""
    sql = """
        SELECT
            p.product_name          AS product_name,
            p.category              AS category,
            p.price                 AS price,
            p.status                AS product_status,
            p.low_stock_threshold   AS low_stock_threshold,
            v.vendor_name           AS vendor_name,
            COALESCE(i.current_stock, 0)    AS current_stock,
            COALESCE(i.reorder_level, 0)    AS reorder_level,
            COALESCE(i.current_stock, 0) * p.price AS inventory_value
        FROM products p
        JOIN vendors v      ON v.id = p.vendor_id
        LEFT JOIN inventory i ON i.product_id = p.id
        ORDER BY p.product_name
    """
    df = _query(sql)
    if not df.empty:
        df["stock_status"] = df.apply(
            lambda row: "Out of Stock" if row["current_stock"] <= 0
                        else ("Low Stock" if row["current_stock"] <= row["low_stock_threshold"]
                              else "In Stock"),
            axis=1
        )
    return df


# ---------------------------------------------------------------------------
# 5. Order Dataset
#    Columns: order_code, order_date, order_status, payment_status,
#             total_amount, region, customer_name, item_count
# ---------------------------------------------------------------------------

def build_order_dataset() -> pd.DataFrame:
    """Return order-level summary DataFrame."""
    sql = """
        SELECT
            o.order_code        AS order_code,
            o.order_date        AS order_date,
            o.order_status      AS order_status,
            o.payment_status    AS payment_status,
            o.total_amount      AS total_amount,
            o.region            AS region,
            o.customer_name     AS customer_name,
            COUNT(oi.id)        AS item_count
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        GROUP BY o.id
        ORDER BY o.order_date DESC
    """
    df = _query(sql)
    if not df.empty and "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# 6. Payment / Settlement Dataset
#    Columns: order_code, order_date, vendor_name, gross_amount,
#             commission_amount, net_payout, payment_status, settlement_status
# ---------------------------------------------------------------------------

def build_payment_dataset() -> pd.DataFrame:
    """Return payment & settlement summary per order × vendor."""
    sql = """
        SELECT
            o.order_code            AS order_code,
            o.order_date            AS order_date,
            o.payment_status        AS payment_status,
            v.vendor_name           AS vendor_name,
            COALESCE(pay.gross_amount, 0)       AS gross_amount,
            COALESCE(pay.commission_amount, 0)  AS commission_amount,
            COALESCE(pay.net_payout, 0)         AS net_payout,
            COALESCE(pay.status, 'Pending')     AS payout_status,
            COALESCE(s.settlement_status, 'Pending') AS settlement_status,
            COALESCE(s.net_amount, 0)           AS settlement_net
        FROM orders o
        LEFT JOIN payments pay  ON pay.order_id = o.id
        LEFT JOIN vendors v     ON v.id = pay.vendor_id
        LEFT JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN settlements s  ON s.order_item_id = oi.id
        ORDER BY o.order_date DESC
    """
    df = _query(sql)
    if not df.empty and "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# 7. Generic / Data Explorer Dataset
#    A wide flat table suitable for general exploration.
# ---------------------------------------------------------------------------

def build_marketplace_dataset() -> pd.DataFrame:
    """Return a broad marketplace flat table useful for Data Explorer."""
    sql = """
        SELECT
            o.order_code        AS order_code,
            o.order_date        AS order_date,
            o.customer_name     AS customer_name,
            o.customer_email    AS customer_email,
            o.region            AS region,
            o.order_status      AS order_status,
            o.payment_status    AS payment_status,
            o.total_amount      AS total_amount,
            p.product_name      AS product_name,
            p.category          AS category,
            p.price             AS unit_price,
            oi.quantity         AS quantity,
            oi.unit_price * oi.quantity AS line_revenue,
            v.vendor_name       AS vendor_name,
            v.category          AS vendor_category,
            COALESCE(i.current_stock, 0) AS current_stock
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        JOIN products p     ON p.id = oi.product_id
        JOIN vendors v      ON v.id = p.vendor_id
        LEFT JOIN inventory i ON i.product_id = p.id
        ORDER BY o.order_date DESC
    """
    df = _query(sql)
    if not df.empty and "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# 8. Availability Check
# ---------------------------------------------------------------------------

def has_marketplace_data() -> bool:
    """Return True if the marketplace DB has at least one order."""
    df = _query("SELECT COUNT(*) AS cnt FROM orders")
    if df.empty:
        return False
    return int(df["cnt"].iloc[0]) > 0
