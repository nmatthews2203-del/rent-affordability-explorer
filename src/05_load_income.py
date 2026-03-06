import pandas as pd
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "rent.db")
INCOME_PATH = os.path.join(BASE_DIR, "data", "cleaned", "income_cleaned.csv")

def main():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Could not find database at {DB_PATH}. Did you create rent.db yet?")

    if not os.path.exists(INCOME_PATH):
        raise FileNotFoundError(
            f"Could not find income file at {INCOME_PATH}. Run src/04_fetch_income.py first."
        )

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_csv(INCOME_PATH)
    df["median_income"] = pd.to_numeric(df["median_income"], errors="coerce")
    df = df.dropna(subset=["median_income"])

    # Replace income table each time (fine for this project)
    df.to_sql("income", conn, if_exists="replace", index=False)

    # Helpful index for faster joins
    conn.execute("CREATE INDEX IF NOT EXISTS idx_income_region_key ON income(region_key);")
    conn.commit()

    # sanity check
    count = conn.execute("SELECT COUNT(*) FROM income;").fetchone()[0]
    sample = conn.execute("SELECT * FROM income LIMIT 5;").fetchall()

    conn.close()

    print(f"Loaded income rows into rent.db: {count:,}")
    print("Sample rows:", sample)

if __name__ == "__main__":
    main()