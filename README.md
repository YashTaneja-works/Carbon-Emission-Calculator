# Carbon Emission Calculator & Insights (Desktop + Web)

This project is a **Carbon Emission Calculator** with:

- A **desktop app** (Tkinter) for local/offline use
- A **web app** (Streamlit) for a more user-friendly browser UI
- A local **SQLite** database (`carbon_emission.db`) storing user profiles and activity data

Both apps use the **same database schema** and the **same emission calculation logic**.

---

## Tech stack

- **Language**: Python 3
- **Database**: SQLite (`sqlite3`)
- **Data processing**: `pandas`
- **Web app UI**: `streamlit`
- **Desktop app UI**: `tkinter` (built-in)
- **Charts**
  - Desktop: `matplotlib` (embedded in Tkinter)
  - Web: Streamlit native charts + optional `matplotlib` for pie chart / histogram

---

## Project files (important)

- **Desktop app entrypoint**: `carbon_emission_app.py`
- **Web app entrypoint**: `web_app.py`
- **Database setup / demo data**: `carbon_emission_db.py`
- **Login + sessions (desktop)**: `login.py`, `session.py`
- **Insert forms (desktop)**: `data_insertion.py`
- **Reports / charts (desktop)**: `reports.py`
- **Recommendations (desktop)**: `recommendations.py`
- **Developer predefined SQL queries**: `updated_queries.py`
- **Web theme**: `.streamlit/config.toml`

---

## How the database is created

The database file is **`carbon_emission.db`**.

- On first run of the web app, if the DB does not exist, it is created by calling:
  - `setup_database()` from `carbon_emission_db.py`
- `setup_database()` creates all tables and inserts **demo data**.

### Important developer note

`setup_database()` **deletes** the existing `carbon_emission.db` file before recreating it.

- The web app (`web_app.py`) is written to call `setup_database()` **only when the DB is missing or invalid**.
- Do **not** run `carbon_emission_db.py` directly if you want to keep existing user data.

---

## Running the Web App (Streamlit)

From the project folder:

```bash
python -m pip install streamlit pandas numpy
python -m streamlit run web_app.py
```

Optional (for pie chart + histogram in web analysis):

```bash
python -m pip install matplotlib
```

Then open the local URL shown in the terminal (usually `http://localhost:8501`).

---

## Running the Desktop App (Tkinter)

```bash
python carbon_emission_app.py
```

If charts don’t work in desktop reports:

```bash
python -m pip install matplotlib pandas
```

---

## App roles and features

### End users

- Create account / sign in (email + password)
- Choose mode:
  - **Individual**
  - **Industry**
- Add data:
  - Transportation
  - Energy consumption
  - Waste management
  - Industrial activity
  - Carbon offset
- Analyze:
  - Summary metrics
  - Category breakdown charts
  - Trends (monthly + daily/weekly in web)
  - Export CSV
- Recommendations:
  - Action plan generated from the user’s largest emission category

### Developer accounts

Developer accounts additionally get:

- **Developer (SQL)** page/tab
- Run predefined SQL queries from `updated_queries.py`
- Run custom queries (SELECT and non-SELECT) against the same SQLite DB
- Export query results to CSV

---

## How carbon emissions are calculated (core logic)

This project calculates emissions by reading activity tables and multiplying by an **emission factor**.

### Emission factors table

Table: `Emission_Factor`

- `Source_Type`: a string like `Car`, `Bus`, `Electricity`, `Natural Gas`, `Waste`, etc.
- `Emission_Per_Unit`: numeric value (factor)

> Units depend on the activity type:
> - Transportation factors are interpreted as **kg CO2e per km**
> - Energy factors are interpreted as **kg CO2e per kWh**
> - Waste factor (`Source_Type='Waste'`) is interpreted as **kg CO2e per kg**

### 1) Transportation emissions

Table: `Transportation`

For each record:

\[
E_{transport} = Distance\_KM \times EF(vehicle\_type)
\]

In SQL (as used in the apps):

- join `Transportation.Vehicle_Type` → `Emission_Factor.Source_Type`
- compute `Emission_Amount = Distance_KM * Emission_Per_Unit`

### 2) Energy consumption emissions

Table: `Energy_Consumption`

\[
E_{energy} = Consumption\_KWH \times EF(energy\_source)
\]

In SQL:

- join `Energy_Consumption.Energy_Source` → `Emission_Factor.Source_Type`
- compute `Emission_Amount = Consumption_KWH * Emission_Per_Unit`

### 3) Waste management emissions

Table: `Waste_Management`

Emissions are now calculated **per waste type** (Plastic, Paper, Glass, Metal, Organic, Electronic, Hazardous):

\[
E_{waste} = Waste\_Weight\_KG \times EF(Waste\_Type)
\]

In SQL (as used in the apps):

- join `Waste_Management.Waste_Type` → `Emission_Factor.Source_Type`

### 4) Industrial activity emissions

Table: `Industrial_Activity`

Industrial emissions are treated as **already measured** values:

\[
E_{industrial} = Emission\_Produced
\]

### 5) Total emissions

\[
E_{total} = E_{transport} + E_{energy} + E_{waste} + E_{industrial}
\]

### 6) Carbon offsets and net emissions

Offsets are stored in `Carbon_Offset.Offset_Amount`.

\[
Offset_{total} = \sum Offset\_Amount
\]

\[
E_{net} = E_{total} - Offset_{total}
\]

---

## Web analysis tools (what’s included)

In `web_app.py` → **Analysis & Charts**:

- **Overview**
  - KPI metrics (total / offset / net)
  - Bar chart + table by emission source
  - Pie chart (if `matplotlib` installed)
  - Data quality check (warns if emission factors are missing for some records)

- **Trends**
  - Monthly trend (total vs net)
  - Monthly stacked area chart (by category)
  - Daily and weekly trend views (when there are enough records)

- **Forecast**
  - Simple linear-trend forecast on monthly history
  - Configurable: forecast months + history window
  - **Note**: This is a lightweight directional forecast (not a scientific model)

- **Benchmark**
  - Compare user against all users in DB for the same date range
  - Rank + percentile
  - Top emitters table
  - Histogram (if `matplotlib` installed)

- **What‑if**
  - Sliders reduce each category by %
  - Shows estimated savings and new net emissions
  - Does **not** modify database (calculation only)

- **Export**
  - Download summary + detail tables as CSV

---

## Developer notes / customization

- **Add or change emission factors**:
  - update records in `Emission_Factor`
  - make sure `Source_Type` matches values used in:
    - `Transportation.Vehicle_Type`
    - `Energy_Consumption.Energy_Source`
    - For waste: keep one row where `Source_Type='Waste'`

- **Adding new activity types**
  - update the UI dropdown lists (web + desktop)
  - update emission factor mappings in `Emission_Factor`
  - extend report queries if needed

- **Security note**
  - Passwords are stored as SHA-256 hashes (see `login.py` and `web_app.py`).
  - For production, use salted hashing (e.g., `bcrypt`) and add proper session/security controls.

---

## Quick start test (developer)

1. Start the web app.
2. Create an account (user or developer).
3. Add some Transportation + Energy records.
4. Open **Analysis & Charts** → generate analysis for the current year.
5. If developer account, open **Developer (SQL)** and try:

```sql
SELECT * FROM Sustainability_Program;
```

