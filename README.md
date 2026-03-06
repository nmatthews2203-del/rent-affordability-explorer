# US Rent & Housing Affordability Explorer

An interactive housing analytics dashboard built with **Python, SQL, Streamlit, Altair, and Plotly**.  
This project combines **Zillow ZORI county-level rent data** with **Census ACS median household income** data to analyze housing affordability, rent burden, rent trends, and geographic differences across the United States.

## Project Overview

This dashboard helps answer questions like:

- Which counties have the highest rents?
- Which counties are the least affordable relative to income?
- Which counties have seen the fastest rent growth year-over-year?
- Where could someone potentially afford to live based on their income and number of roommates?
- How do rent and income relate across counties?

## Features

- **County-level rent rankings**
- **US median/mean rent trend over time**
- **Year-over-year rent growth analysis**
- **Affordability analysis using rent-to-income ratio**
- **Personal affordability finder** based on income, roommates, and target rent burden
- **Scatter plot of rent vs. median income**
- **Rent distribution histogram**
- **County comparison tool**
- **US state-level rent choropleth map**

## Tech Stack

- **Python**
- **SQLite**
- **Streamlit**
- **Pandas**
- **Altair**
- **Plotly**

## Data Sources

- **Zillow ZORI (County-level)** for rent data
- **Census ACS B19013** for median household income

## Important Notes

- Zillow ZORI reflects a **typical market rent estimate**, not necessarily the average rent for a 1-bedroom apartment.
- Some suburban or resort counties may appear unusually expensive because listings are dominated by **single-family home rentals**.
- County coverage is limited to counties available in the source datasets and successful joins between rent and income data.

## Dashboard Sections

### Overview
Summary KPIs including:
- counties with rent data
- counties with affordability data
- selected month
- national rent value for the selected month

### Rankings & National Trend
- Most expensive counties for the selected month
- National county-level rent trend over time

### Rent Growth
- Fastest rising counties by year-over-year rent change
- Histogram of YoY rent growth

### Affordability
- Least affordable counties
- Most affordable counties

### Where Could You Live?
- Personal affordability finder based on:
  - annual income
  - roommates
  - target percent of income spent on rent

### Market Structure
- Scatter plot of rent vs. median household income
- Rent distribution histogram

### County Comparison
- Compare rent trends across two counties

### US Rent Map
- State-level choropleth of rent levels

## How to Run Locally

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/rent-affordability-explorer.git
cd rent-affordability-explorer