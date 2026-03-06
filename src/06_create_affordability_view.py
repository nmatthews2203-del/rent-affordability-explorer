import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "rent.db")

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    DROP VIEW IF EXISTS vw_affordability;

    CREATE VIEW vw_affordability AS
    SELECT
        l.region_key,
        l.county,
        l.state,
        l.rent,
        i.median_income,
        (l.rent * 12.0) AS annual_rent,
        (l.rent * 12.0) / i.median_income AS rent_to_income,
        (i.median_income * 0.30) / 12.0 AS affordable_monthly_rent
    FROM vw_latest_rent l
    JOIN income i
      ON l.region_key = i.region_key
    WHERE i.median_income > 0;
    """)

    conn.commit()
    conn.close()
    print("Created vw_affordability.")
    
if __name__ == "__main__":
    main()