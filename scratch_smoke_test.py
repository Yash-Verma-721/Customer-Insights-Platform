import pandas as pd
from utils.customer_metrics import detect_marketplace_columns, build_inventory_profile

def trace():
    print("=== 1. Uploaded Dataset ===")
    df = pd.read_csv("datasets/active_dataset.csv", nrows=5)
    print("Columns:", list(df.columns))
    
    # Check if there are other datasets
    import os
    print("Available datasets:", os.listdir("datasets"))
    
    print("\n=== 2. detect_marketplace_columns ===")
    detected = detect_marketplace_columns(df)
    print("Detected 'product' matches:", detected.get("product"))
    from utils.customer_metrics import first_detected
    print("first_detected('product') result:", first_detected(detected, "product"))
    
    print("\n=== 3. build_inventory_profile ===")
    try:
        profile, metrics, columns = build_inventory_profile(df, detected)
        print("Profile columns:", list(profile.columns))
        if not profile.empty:
            print("First row of profile:")
            print(profile.iloc[0])
            print("\nHead of profile['product']:", profile['product'].head().tolist())
    except Exception as e:
        print("Error in build_inventory_profile:", e)

if __name__ == "__main__":
    trace()
