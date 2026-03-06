import pandas as pd
import requests
import time
import os

YEAR = 2023  # ACS 5-year year
OUT_PATH = "data/cleaned/income_cleaned.csv"

STATE_FIPS_TO_NAME = {
    "01": "alabama", "02": "alaska", "04": "arizona", "05": "arkansas", "06": "california",
    "08": "colorado", "09": "connecticut", "10": "delaware", "11": "district of columbia",
    "12": "florida", "13": "georgia", "15": "hawaii", "16": "idaho", "17": "illinois",
    "18": "indiana", "19": "iowa", "20": "kansas", "21": "kentucky", "22": "louisiana",
    "23": "maine", "24": "maryland", "25": "massachusetts", "26": "michigan",
    "27": "minnesota", "28": "mississippi", "29": "missouri", "30": "montana",
    "31": "nebraska", "32": "nevada", "33": "new hampshire", "34": "new jersey",
    "35": "new mexico", "36": "new york", "37": "north carolina", "38": "north dakota",
    "39": "ohio", "40": "oklahoma", "41": "oregon", "42": "pennsylvania",
    "44": "rhode island", "45": "south carolina", "46": "south dakota",
    "47": "tennessee", "48": "texas", "49": "utah", "50": "vermont",
    "51": "virginia", "53": "washington", "54": "west virginia",
    "55": "wisconsin", "56": "wyoming"
}

def fetch_state_counties_income(state_fips: str) -> pd.DataFrame:
    url = f"https://api.census.gov/data/{YEAR}/acs/acs5"
    params = {
        "get": "NAME,B19013_001E",
        "for": "county:*",
        "in": f"state:{state_fips}",
    }
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()

    cols = data[0]
    rows = data[1:]
    df = pd.DataFrame(rows, columns=cols)

    df["B19013_001E"] = pd.to_numeric(df["B19013_001E"], errors="coerce")

    df["county"] = df["NAME"].str.split(",").str[0]
    df["state"] = STATE_FIPS_TO_NAME[state_fips]

    # match the cleaning style we used for Zillow keys
    df["county_clean"] = (
        df["county"]
        .str.replace(" County", "", regex=False)
        .str.replace(" Parish", "", regex=False)
        .str.replace(" Census Area", "", regex=False)
        .str.replace(" Borough", "", regex=False)
        .str.replace(" Municipio", "", regex=False)
        .str.strip()
        .str.lower()
    )

    df["region_key"] = df["county_clean"] + "_" + df["state"]

    out = df[["region_key", "B19013_001E"]].rename(columns={"B19013_001E": "median_income"})
    out = out.dropna(subset=["median_income"])
    return out

def main():
    os.makedirs("data/cleaned", exist_ok=True)

    frames = []
    for i, state_fips in enumerate(STATE_FIPS_TO_NAME.keys(), start=1):
        print(f"[{i}/51] Fetching income for state FIPS {state_fips}...")
        frames.append(fetch_state_counties_income(state_fips))
        time.sleep(0.15)  # be polite

    income = pd.concat(frames, ignore_index=True)
    income.to_csv(OUT_PATH, index=False)
    print(f"Saved {OUT_PATH} with {len(income):,} rows")

if __name__ == "__main__":
    main()