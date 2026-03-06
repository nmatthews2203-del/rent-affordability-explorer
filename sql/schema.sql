CREATE TABLE regions (
    region_key TEXT PRIMARY KEY,
    county TEXT,
    state TEXT
);

CREATE TABLE rent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_key TEXT,
    date DATE,
    rent REAL,
    FOREIGN KEY(region_key) REFERENCES regions(region_key)
);