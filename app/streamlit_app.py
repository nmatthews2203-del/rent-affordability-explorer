import os
import sqlite3
import pandas as pd
import streamlit as st
import altair as alt
import plotly.express as px

# -----------------------------
# Visual theme constants
# -----------------------------
PRIMARY = "#2563EB"   # blue
GOOD = "#16A34A"      # green
WARN = "#F59E0B"      # amber
BAD = "#DC2626"       # red
NEUTRAL = "#6B7280"   # gray

CHART_HEIGHT_SMALL = 320
CHART_HEIGHT_MED = 380
TABLE_HEIGHT = 420

st.set_page_config(page_title="Rent & Affordability Explorer", layout="wide")

# Small CSS polish
st.markdown(
    """
    <style>
      .block-container { padding-top: 2rem; padding-bottom: 2rem; }
      h1 { letter-spacing: -0.5px; }
      h2, h3 { letter-spacing: -0.25px; }
      [data-testid="stSidebar"] { border-right: 1px solid rgba(255,255,255,0.06); }
      [data-testid="stMetricValue"] { font-size: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("# US Rent & Housing Affordability Explorer")
st.caption(
    "County-level Zillow ZORI rent data combined with Census ACS median household income "
    "(B19013) to analyze affordability, rent burden, and market trends."
)

# -----------------------------
# DB connection
# -----------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "rent.db")


@st.cache_resource
def get_conn():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Could not find rent.db at: {DB_PATH}")
    return sqlite3.connect(DB_PATH, check_same_thread=False)


conn = get_conn()


def safe_read_sql(query: str) -> pd.DataFrame:
    try:
        return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"SQL error: {e}\n\nQuery:\n{query}")
        return pd.DataFrame()


def money(x):
    if pd.isna(x):
        return None
    try:
        return f"${int(round(float(x), 0)):,}"
    except Exception:
        return x


def pct(x, digits=3):
    if pd.isna(x):
        return None
    try:
        return round(float(x), digits)
    except Exception:
        return x


def county_state(county, state):
    return f"{county}, {state}"


def prev_year_month(date_str: str) -> str:
    """Given YYYY-MM-DD, return date - 12 months as YYYY-MM-DD."""
    d = pd.to_datetime(date_str)
    return (d - pd.DateOffset(years=1)).strftime("%Y-%m-%d")


# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Controls")

states_df = safe_read_sql("SELECT DISTINCT state FROM regions ORDER BY state;")
states = states_df["state"].tolist() if not states_df.empty else []
selected_states = st.sidebar.multiselect("State (optional filter)", states, default=[])

top_n = st.sidebar.slider("Top N rows", min_value=10, max_value=100, value=20, step=10)
trend_metric = st.sidebar.radio("Trend metric", ["Median (recommended)", "Mean"], index=0)

months_df = safe_read_sql("SELECT DISTINCT date FROM rent ORDER BY date;")
if months_df.empty:
    st.error("No dates found in rent table.")
    st.stop()

months_df["date"] = pd.to_datetime(months_df["date"])
available_months = months_df["date"].dt.strftime("%Y-%m-%d").tolist()
selected_month = st.sidebar.selectbox("Month for rankings", available_months, index=len(available_months) - 1)

st.sidebar.divider()
exclude_outliers = st.sidebar.checkbox("Exclude extreme outliers", value=True)
outlier_cap = st.sidebar.number_input(
    "Outlier cap (monthly rent $)", min_value=2000, max_value=50000, value=10000, step=500
)

state_filter_regions = ""
state_filter_aff = ""
if selected_states:
    quoted = ",".join([f"'{s}'" for s in selected_states])
    state_filter_regions = f" AND reg.state IN ({quoted}) "
    state_filter_aff = f" AND state IN ({quoted}) "

outlier_filter_rent = f" AND r.rent <= {outlier_cap} " if exclude_outliers else ""
outlier_filter_aff = f" AND rent <= {outlier_cap} " if exclude_outliers else ""

# -----------------------------
# KPIs
# -----------------------------
st.markdown("### Overview")

k1, k2, k3, k4 = st.columns(4)

coverage_latest_df = safe_read_sql("SELECT COUNT(*) AS n FROM vw_latest_rent;")
coverage_latest = int(coverage_latest_df["n"].iloc[0]) if not coverage_latest_df.empty else 0

aff_coverage_df = safe_read_sql(f"""
SELECT COUNT(*) AS n
FROM rent r
JOIN income inc ON inc.region_key = r.region_key
WHERE r.date = '{selected_month}';
""")
aff_coverage = int(aff_coverage_df["n"].iloc[0]) if not aff_coverage_df.empty else 0

selected_month_rent_df = safe_read_sql(f"""
SELECT rent
FROM rent
WHERE date = '{selected_month}'
{'' if not exclude_outliers else f'AND rent <= {outlier_cap}'}
""")

if not selected_month_rent_df.empty:
    month_median_rent = float(selected_month_rent_df["rent"].median())
    month_mean_rent = float(selected_month_rent_df["rent"].mean())
else:
    month_median_rent = None
    month_mean_rent = None

k1.metric("Counties with rent data", f"{coverage_latest:,}")
k2.metric("Counties with affordability", f"{aff_coverage:,}")
k3.metric("Selected month", selected_month)
k4.metric("US rent (selected month)", money(month_median_rent if trend_metric.startswith("Median") else month_mean_rent))

st.divider()

# -----------------------------
# Row 1: Most expensive + US trend
# -----------------------------
st.markdown("## Rankings & National Trend")
left, right = st.columns([1, 1])

with left:
    st.subheader("Most Expensive Counties (Selected Month)")

    expensive_query = f"""
    SELECT reg.county, reg.state, r.rent, r.date
    FROM rent r
    JOIN regions reg ON r.region_key = reg.region_key
    WHERE r.date = '{selected_month}'
    {state_filter_regions}
    {outlier_filter_rent}
    ORDER BY r.rent DESC
    LIMIT {top_n};
    """
    expensive = safe_read_sql(expensive_query)

    if not expensive.empty:
        expensive["County"] = [county_state(c, s) for c, s in zip(expensive["county"], expensive["state"])]
        expensive["Rent"] = expensive["rent"].apply(money)
        expensive["Month"] = pd.to_datetime(expensive["date"]).dt.strftime("%Y-%m")

        st.dataframe(
            expensive[["County", "Rent", "Month"]],
            use_container_width=True,
            hide_index=True,
            height=TABLE_HEIGHT,
        )

        st.caption("Resort markets (Aspen/Pitkin County, CO) can be extreme outliers. Use the outlier toggle if needed.")
    else:
        st.info("No results for the selected month/filter.")

with right:
    title_metric = "Median" if trend_metric.startswith("Median") else "Mean"
    st.subheader(f"US {title_metric} Rent Trend (County Level)")

    trend_df = safe_read_sql(f"""
    SELECT date, rent
    FROM rent
    WHERE 1=1
    {'' if not exclude_outliers else f'AND rent <= {outlier_cap}'}
    """)

    if not trend_df.empty:
        trend_df["date"] = pd.to_datetime(trend_df["date"])
        series = (
            trend_df.groupby("date")["rent"].median()
            if trend_metric.startswith("Median")
            else trend_df.groupby("date")["rent"].mean()
        )
        chart_df = series.reset_index()

        chart = (
            alt.Chart(chart_df)
            .mark_line(color=PRIMARY, strokeWidth=3, interpolate="monotone")
            .encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("rent:Q", title="Monthly rent ($)"),
                tooltip=[alt.Tooltip("date:T", title="Date"), alt.Tooltip("rent:Q", title="Rent", format=",.0f")],
            )
            .properties(height=CHART_HEIGHT_SMALL)
        )

        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No trend data found.")

# -----------------------------
# Fastest rising counties (YoY)
# -----------------------------
st.divider()
st.markdown("### Rent Growth")

st.subheader("Fastest Rising Counties (YoY Rent Change)")
prev_month = prev_year_month(selected_month)
st.caption(f"YoY compares **{selected_month}** vs **{prev_month}**.")

yoy_query_top = f"""
SELECT
  reg.county,
  reg.state,
  r_now.rent AS rent_now,
  r_prev.rent AS rent_prev,
  ((r_now.rent - r_prev.rent) / r_prev.rent) AS yoy_pct
FROM rent r_now
JOIN rent r_prev
  ON r_now.region_key = r_prev.region_key
 AND r_prev.date = '{prev_month}'
JOIN regions reg
  ON r_now.region_key = reg.region_key
WHERE r_now.date = '{selected_month}'
  AND r_prev.rent IS NOT NULL
  AND r_prev.rent > 0
{state_filter_regions}
{'' if not exclude_outliers else f'AND r_now.rent <= {outlier_cap}'}
{'' if not exclude_outliers else f'AND r_prev.rent <= {outlier_cap}'}
ORDER BY yoy_pct DESC
LIMIT {top_n};
"""
yoy_top = safe_read_sql(yoy_query_top)

y1, y2 = st.columns([1, 1])

with y1:
    st.markdown("**Top YoY Increases**")
    if not yoy_top.empty:
        df = yoy_top.copy()
        df["County"] = [county_state(c, s) for c, s in zip(df["county"], df["state"])]
        df["Rent now"] = df["rent_now"].apply(money)
        df["Rent prev"] = df["rent_prev"].apply(money)
        df["YoY %"] = (df["yoy_pct"] * 100).round(1).astype(str) + "%"
        st.dataframe(
            df[["County", "Rent now", "Rent prev", "YoY %"]],
            use_container_width=True,
            hide_index=True,
            height=TABLE_HEIGHT
        )
    else:
        st.info("No YoY rows found for this month (need data for the same month last year).")

with y2:
    st.markdown("**YoY Change Distribution**")
    yoy_all = safe_read_sql(yoy_query_top.replace(f"LIMIT {top_n}", "LIMIT 1200"))
    if not yoy_all.empty:
        yoy_all["yoy_pct"] = yoy_all["yoy_pct"] * 100.0
        yoy_hist = (
            alt.Chart(yoy_all)
            .mark_bar(opacity=0.85, color=PRIMARY, cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=alt.X("yoy_pct:Q", bin=alt.Bin(maxbins=30), title="YoY % change"),
                y=alt.Y("count():Q", title="Number of counties"),
                tooltip=[alt.Tooltip("count():Q", title="Count")],
            )
            .properties(height=CHART_HEIGHT_MED)
        )
        st.altair_chart(yoy_hist, use_container_width=True)
    else:
        st.info("YoY distribution unavailable.")

# -----------------------------
# Affordability tables
# -----------------------------
st.divider()
st.markdown("### Affordability")

st.subheader("Affordability (Rent-to-Income)")
st.caption(f"Affordability is calculated using rent from **{selected_month}** and ACS median household income.")

a1, a2 = st.columns([1, 1])

aff_base = f"""
SELECT
  reg.county,
  reg.state,
  r.rent,
  inc.median_income,
  (r.rent * 12.0) / inc.median_income AS rent_to_income,
  (inc.median_income * 0.30) / 12.0 AS affordable_monthly_rent
FROM rent r
JOIN regions reg ON r.region_key = reg.region_key
JOIN income inc ON inc.region_key = r.region_key
WHERE r.date = '{selected_month}'
{state_filter_regions}
{outlier_filter_rent}
AND inc.median_income IS NOT NULL
AND inc.median_income > 0
"""

with a1:
    st.markdown("**Least Affordable Counties** (highest rent-to-income)")
    least_aff = safe_read_sql(f"""
    {aff_base}
    ORDER BY rent_to_income DESC
    LIMIT {top_n};
    """)
    if not least_aff.empty:
        least_aff["County"] = [county_state(c, s) for c, s in zip(least_aff["county"], least_aff["state"])]
        least_aff["Rent"] = least_aff["rent"].apply(money)
        least_aff["Median income"] = least_aff["median_income"].apply(money)
        least_aff["Rent-to-income"] = least_aff["rent_to_income"].apply(lambda x: pct(x, 3))
        least_aff["Affordable (30%)"] = least_aff["affordable_monthly_rent"].apply(money)
        st.dataframe(
            least_aff[["County", "Rent", "Median income", "Rent-to-income", "Affordable (30%)"]],
            use_container_width=True, hide_index=True, height=TABLE_HEIGHT
        )
    else:
        st.info("No affordability rows found for this month (income coverage may be limited).")

with a2:
    st.markdown("**Most Affordable Counties** (lowest rent-to-income)")
    most_aff = safe_read_sql(f"""
    {aff_base}
    ORDER BY rent_to_income ASC
    LIMIT {top_n};
    """)
    if not most_aff.empty:
        most_aff["County"] = [county_state(c, s) for c, s in zip(most_aff["county"], most_aff["state"])]
        most_aff["Rent"] = most_aff["rent"].apply(money)
        most_aff["Median income"] = most_aff["median_income"].apply(money)
        most_aff["Rent-to-income"] = most_aff["rent_to_income"].apply(lambda x: pct(x, 3))
        most_aff["Affordable (30%)"] = most_aff["affordable_monthly_rent"].apply(money)
        st.dataframe(
            most_aff[["County", "Rent", "Median income", "Rent-to-income", "Affordable (30%)"]],
            use_container_width=True, hide_index=True, height=TABLE_HEIGHT
        )
    else:
        st.info("No affordability rows found for this month.")

# -----------------------------
# Where could you live? (Personal affordability finder)
# -----------------------------
st.divider()
st.markdown("### Where Could You Live? (Based on Your Situation)")
st.caption("Uses the 30% rule by default. Adjust roommates to see how the affordable set changes.")

c1, c2, c3, c4 = st.columns([1, 1, 1, 1])

with c1:
    user_income = st.number_input("Your annual income ($)", min_value=0, value=60000, step=5000)
with c2:
    roommates = st.number_input("People splitting rent", min_value=1, max_value=10, value=1, step=1)
with c3:
    rent_rule = st.slider("Target % of income for rent", min_value=10, max_value=50, value=30, step=5)
with c4:
    show_n = st.slider("Show top results", min_value=10, max_value=100, value=25, step=5)

max_rent_per_person = (user_income * (rent_rule / 100.0)) / 12.0

st.write(
    f"**Max affordable rent per person:** {money(max_rent_per_person)} / month"
)

if user_income <= 0:
    st.info("Enter an income above $0 to see affordable counties.")
else:
    affordable_query = f"""
    SELECT
      reg.county,
      reg.state,
      r.rent,
      inc.median_income,
      (r.rent / {roommates}) AS rent_per_person,
      (r.rent * 12.0) / inc.median_income AS rent_to_income_county
    FROM rent r
    JOIN regions reg ON r.region_key = reg.region_key
    JOIN income inc ON inc.region_key = r.region_key
    WHERE r.date = '{selected_month}'
      AND inc.median_income IS NOT NULL
      AND inc.median_income > 0
      {state_filter_regions}
      {outlier_filter_rent}
      AND (r.rent / {roommates}) <= {max_rent_per_person}
    ORDER BY rent_per_person ASC
    LIMIT {show_n};
    """

    affordable_df = safe_read_sql(affordable_query)

    if affordable_df.empty:
        st.warning("No counties match your inputs for the selected month. Try more roommates, higher % rule, or remove state filter.")
    else:
        affordable_df["County"] = [
            county_state(c, s) for c, s in zip(affordable_df["county"], affordable_df["state"])
        ]
        affordable_df["Rent (total)"] = affordable_df["rent"].apply(money)
        affordable_df["Rent per person"] = affordable_df["rent_per_person"].apply(money)
        affordable_df["County median income"] = affordable_df["median_income"].apply(money)
        affordable_df["County rent-to-income"] = affordable_df["rent_to_income_county"].apply(lambda x: pct(x, 3))

        st.dataframe(
            affordable_df[["County", "Rent (total)", "Rent per person", "County median income", "County rent-to-income"]],
            use_container_width=True,
            hide_index=True,
            height=420
        )

        chart_df = affordable_df.copy().head(20)
        chart_df["rent_per_person"] = chart_df["rent_per_person"].astype(float)

# -----------------------------
# Market structure visuals (FIXED: define s1/s2)
# -----------------------------
st.divider()
st.markdown("### Market Structure")

s1, s2 = st.columns([1.35, 0.65])

with s1:
    st.markdown("**Rent vs Median Income (County Level)**")

    scatter_df = safe_read_sql(f"""
    SELECT
      reg.county,
      reg.state,
      r.rent,
      inc.median_income,
      (r.rent * 12.0) / inc.median_income AS rent_to_income
    FROM rent r
    JOIN regions reg ON r.region_key = reg.region_key
    JOIN income inc ON inc.region_key = r.region_key
    WHERE r.date = '{selected_month}'
    {state_filter_regions}
    {outlier_filter_rent}
    AND inc.median_income IS NOT NULL
    AND inc.median_income > 0
    """)

    if not scatter_df.empty:
        scatter_df["County"] = scatter_df["county"] + ", " + scatter_df["state"]

        scatter_chart = (
            alt.Chart(scatter_df)
            .mark_circle(size=90, opacity=0.75)
            .encode(
                x=alt.X("median_income:Q", title="Median Household Income ($)"),
                y=alt.Y("rent:Q", title="Monthly Rent ($)"),
                color=alt.Color(
                    "rent_to_income:Q",
                    title="Rent-to-Income",
                    scale=alt.Scale(
                        domain=[0.2, 0.3, 0.5],
                        range=[GOOD, WARN, BAD],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("County:N"),
                    alt.Tooltip("rent:Q", title="Rent", format=",.0f"),
                    alt.Tooltip("median_income:Q", title="Income", format=",.0f"),
                    alt.Tooltip("rent_to_income:Q", title="Rent/Income", format=".3f"),
                ],
            )
            .interactive()
            .properties(height=CHART_HEIGHT_MED)
        )

        st.altair_chart(scatter_chart, use_container_width=True)
        st.caption("Each point is a county for the selected month. Color indicates rent burden (rent-to-income).")
    else:
        st.info("No scatter data available for this month (income join coverage may be limited).")

with s2:
    st.markdown("**Rent Distribution Across Counties**")

    dist_df = safe_read_sql(f"""
    SELECT rent
    FROM vw_latest_rent
    WHERE 1=1
    {state_filter_aff}
    {'' if not exclude_outliers else f'AND rent <= {outlier_cap}'}
    """)

    if not dist_df.empty:
        hist = (
            alt.Chart(dist_df)
            .mark_bar(opacity=0.85, color=PRIMARY, cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=alt.X("rent:Q", bin=alt.Bin(maxbins=30), title="Monthly Rent ($)"),
                y=alt.Y("count():Q", title="Number of Counties"),
                tooltip=[alt.Tooltip("count():Q", title="Count")],
            )
            .properties(height=CHART_HEIGHT_MED)
        )

        st.altair_chart(hist, use_container_width=True)
        st.caption("Distribution updates with the state filter. Outlier cap removes extreme markets.")
    else:
        st.info("No distribution data found.")

# -----------------------------
# County Compare Tool
# -----------------------------
st.divider()
st.markdown("### County Comparison")

st.subheader("Compare Two Counties")

county_list_df = safe_read_sql(f"""
SELECT region_key, county, state
FROM regions
WHERE 1=1
{state_filter_aff.replace("state", "state")}
ORDER BY state, county;
""")

if county_list_df.empty:
    st.info("No counties available to compare.")
else:
    county_list_df["label"] = [county_state(c, s) for c, s in zip(county_list_df["county"], county_list_df["state"])]
    labels = county_list_df["label"].tolist()

    cA, cB = st.columns(2)
    with cA:
        pick_a = st.selectbox("County A", labels, index=0)
    with cB:
        pick_b = st.selectbox("County B", labels, index=min(1, len(labels) - 1))

    key_a = county_list_df.loc[county_list_df["label"] == pick_a, "region_key"].iloc[0]
    key_b = county_list_df.loc[county_list_df["label"] == pick_b, "region_key"].iloc[0]

    compare_df = safe_read_sql(f"""
    SELECT r.date, r.rent, reg.county, reg.state
    FROM rent r
    JOIN regions reg ON r.region_key = reg.region_key
    WHERE r.region_key IN ('{key_a}', '{key_b}')
    {'' if not exclude_outliers else f'AND r.rent <= {outlier_cap}'}
    ORDER BY r.date;
    """)

    if not compare_df.empty:
        compare_df["date"] = pd.to_datetime(compare_df["date"])
        compare_df["County"] = [county_state(c, s) for c, s in zip(compare_df["county"], compare_df["state"])]

        comp_chart = (
            alt.Chart(compare_df)
            .mark_line(strokeWidth=3, interpolate="monotone")
            .encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("rent:Q", title="Monthly rent ($)"),
                color=alt.Color("County:N", title="County"),
                tooltip=[
                    "County",
                    alt.Tooltip("date:T", title="Date"),
                    alt.Tooltip("rent:Q", title="Rent", format=",.0f")
                ],
            )
            .properties(height=350)
        )

        st.altair_chart(comp_chart, use_container_width=True)
        st.caption("Compare shows rent trends across two counties.")
    else:
        st.info("No comparison data found.")

# -----------------------------
# US Rent Map (State Level)
# -----------------------------
st.divider()
st.subheader("US Rent Map (State Level)")
st.caption("State values are the county-level median/mean rent aggregated to the state (selected month).")

map_metric = st.radio(
    "Map metric",
    ["Median rent", "Mean rent"],
    horizontal=True,
    index=0
)

state_map_df = safe_read_sql(f"""
SELECT
  reg.state AS state,
  {"median(r.rent)" if map_metric.startswith("Median") else "avg(r.rent)"} AS rent
FROM rent r
JOIN regions reg ON r.region_key = reg.region_key
WHERE r.date = '{selected_month}'
{state_filter_regions}
{outlier_filter_rent}
GROUP BY reg.state
ORDER BY rent DESC;
""")

if state_map_df.empty:
    st.info("No data available to draw the map for the selected filters.")
else:
    state_map_df["rent"] = state_map_df["rent"].astype(float)

    fig = px.choropleth(
        state_map_df,
        locations="state",
        locationmode="USA-states",
        color="rent",
        scope="usa",
        labels={"rent": "Monthly rent ($)"},
        hover_data={"state": True, "rent": ":,.0f"},
    )

    fig.update_layout(
        height=560,
        margin=dict(l=0, r=0, t=0, b=0),
    )

    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Diagnostics
# -----------------------------
with st.expander("Diagnostics"):
    diag = safe_read_sql("""
    SELECT 'regions' AS name, COUNT(*) AS rows FROM regions
    UNION ALL SELECT 'rent', COUNT(*) FROM rent
    UNION ALL SELECT 'income', COUNT(*) FROM income
    UNION ALL SELECT 'vw_latest_rent', COUNT(*) FROM vw_latest_rent
    UNION ALL SELECT 'vw_affordability', COUNT(*) FROM vw_affordability;
    """)
    if not diag.empty:
        st.dataframe(diag, use_container_width=True)