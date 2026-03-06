import pandas as pd

# load dataset
df = pd.read_csv("data/raw/County_zori_uc_sfrcondomfr_sm_month.csv")

# keep only important columns
df = df[["RegionID", "RegionName", "State"] + list(df.columns[9:])]

# convert wide → long
df_long = df.melt(
    id_vars=["RegionID", "RegionName", "State"],
    var_name="date",
    value_name="rent"
)

# convert date column
df_long["date"] = pd.to_datetime(df_long["date"])

# remove missing rents
df_long = df_long.dropna(subset=["rent"])

# create region key
df_long["region_key"] = (
    df_long["RegionName"].str.lower().str.replace(" county","")
    + "_" +
    df_long["State"].str.lower()
)

# reorder columns
df_long = df_long[
    ["region_key", "RegionName", "State", "date", "rent"]
]

# save cleaned data
df_long.to_csv("data/cleaned/zori_cleaned.csv", index=False)

print("ZORI cleaned and saved.")