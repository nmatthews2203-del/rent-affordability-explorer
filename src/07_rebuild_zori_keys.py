import pandas as pd
import sqlite3
import os

# Abbrev -> full name (lowercase)
ABBR_TO_STATE = {
    "AL":"alabama","AK":"alaska","AZ":"arizona","AR":"arkansas","CA":"california",
    "CO":"colorado","CT":"connecticut","DE":"delaware","DC":"district of columbia",
    "FL":"florida","GA":"georgia","HI":"hawaii","ID":"idaho","IL":"illinois","IN":"indiana",
    "IA":"iowa","KS":"kansas","KY":"kentucky","LA":"louisiana","ME":"maine","MD":"maryland",
    "MA":"massachusetts","MI":"michigan","MN":"minnesota","MS":"mississippi","MO":"missouri",
    "MT":"montana","NE":"nebraska","NV":"nevada","NH":"new hampshire","NJ":"new jersey",
    "NM":"new mexico","NY":"new york","NC":"north carolina","ND":"north dakota","OH":"ohio",
    "OK":"oklahoma","OR":"oregon","PA":"pennsylvania","RI":"rhode island","SC":"south carolina",
    "SD":"south dakota","TN":"tennessee","TX":"texas","UT":"utah","VT":"vermont","VA":"virginia",
    "WA":"washington","WV":"west virginia","WI":"wisconsin","WY":"wyoming"
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZORI_CLEAN_PATH = os.path.join(BASE_DIR, "data", "cleaned", "zori_cleaned.csv")
DB_PATH = os.path.join(BASE_DIR, "rent.db")

def main():
    df = pd.read_csv(ZORI_CLEAN_PATH)

    # Detect if state values are abbreviations
    sample_states = df["State"].dropna().astype(str).head(50).tolist()
    looks_like_abbr = all(len(s.strip()) == 2 for s in sample_states)

    if looks_like_abbr:
        # map abbreviations -> full names
        df["state_full"] = df["State"].str.upper().map(ABBR_TO_STATE)
        missing = df["state_full"].isna().sum()
        if missing > 0:
            bad = df.loc[df["state_full"].isna(), "State"].value_counts().head(10)
            raise ValueError(f"Unmapped state abbreviations found. Examples:\n{bad}")

        state_for_key = df["state_full"]
    else:
        # already full names
        state_for_key = df["State"].astype(str).str.lower()

    # clean county name
    county_clean = (
        df["RegionName"].astype(str)
        .str.replace(" County", "", regex=False)
        .str.strip()
        .str.lower()
    )

    df["region_key"] = county_clean + "_" + state_for_key

    # rebuild regions + rent tables (overwrite)
    conn = sqlite3.connect(DB_PATH)

    regions = df[["region_key", "RegionName", "State"]].drop_duplicates()
    regions.columns = ["region_key", "county", "state"]  # keep original state display in DB
    regions.to_sql("regions", conn, if_exists="replace", index=False)

    rent = df[["region_key", "date", "rent"]].copy()
    rent.to_sql("rent", conn, if_exists="replace", index=False)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_rent_region_key ON rent(region_key);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rent_date ON rent(date);")
    conn.commit()
    conn.close()

    print("Rebuilt regions + rent with normalized region_key.")

if __name__ == "__main__":
    main()