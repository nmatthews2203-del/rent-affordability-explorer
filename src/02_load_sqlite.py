import pandas as pd
import sqlite3

# connect to database
conn = sqlite3.connect("rent.db")

# load cleaned data
df = pd.read_csv("data/cleaned/zori_cleaned.csv")

# create regions table
regions = df[["region_key", "RegionName", "State"]].drop_duplicates()
regions.columns = ["region_key", "county", "state"]

regions.to_sql("regions", conn, if_exists="replace", index=False)

# create rent table
rent = df[["region_key", "date", "rent"]]

rent.to_sql("rent", conn, if_exists="replace", index=False)

conn.close()

print("Database created.")