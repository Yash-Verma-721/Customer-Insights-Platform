import pandas as pd
import sys
import os

sys.path.append(r"d:\Customer Insights Project")

from utils.customer_metrics import detect_marketplace_columns, build_inventory_profile

dataset_path = r"d:\Customer Insights Project\datasets\active_dataset.csv"
if not os.path.exists(dataset_path):
    print("Dataset not found:", dataset_path)
    sys.exit(1)
    
df = pd.read_csv(dataset_path)

detected = detect_marketplace_columns(df)
print("1. Detected product columns:", detected.get("product", []))

profile, metrics, columns = build_inventory_profile(df, detected)

product_col = columns.get("product")
print("2. Grouping column:", product_col)

print("3. Display column after aggregation:", "product" if "product" in profile.columns else "Not found")

top_products = profile.sort_values("orders", ascending=False).head(10)

print("\n4. First 10 values of the dataframe used by Product Analytics for the chart:")
print(top_products.head(10).to_string())

print("\n5. Confirm whether those values are Product Names or Product IDs.")
print("X-axis values (Product Name / ID):")
print(top_products["product"].tolist())

