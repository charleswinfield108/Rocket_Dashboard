import pandas as pd
from pathlib import Path

INPUT = Path(__file__).parent.parent / "data" / "license.csv"
OUTPUT = Path(__file__).parent / "elevator_fleet.csv"

df = pd.read_csv(INPUT)

df = df[df["LICENSESTATUS"].isin(["ACTIVE", "PENDING_RENEWAL"])]

df["LICENSEEXPIRYDATE"] = pd.to_datetime(
    df["LICENSEEXPIRYDATE"], format="%d-%b-%y"
).dt.strftime("%Y-%m-%d")

df = df[["ElevatingDevicesNumber", "LocationoftheElevatingDevice", "LICENSESTATUS", "LICENSEEXPIRYDATE"]]
df.columns = ["elevator_id", "location", "license_status", "license_expiry"]

df.to_csv(OUTPUT, index=False)
print(f"Written {len(df)} rows to {OUTPUT}")
