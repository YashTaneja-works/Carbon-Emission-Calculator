import os
import hashlib
from datetime import datetime

import sqlite3
import pandas as pd
import streamlit as st
import numpy as np

from session import AppSession
from carbon_emission_db import setup_database, ensure_correct_emission_factors
from updated_queries import updated_queries


DB_PATH = "carbon_emission.db"

APP_TITLE = "Carbon Emission Calculator & Insights"
APP_TAGLINE = "Track activities • Analyze emissions • Get recommendations"


def inject_ui() -> None:
    st.markdown(
        """
        <style>
          .hero {
            padding: 14px 16px;
            border-radius: 14px;
            border: 1px solid rgba(49, 51, 63, 0.18);
            background: rgba(250, 250, 252, 0.60);
            margin-bottom: 12px;
          }
          .hero h2 { margin: 0; padding: 0; }
          .hero p { margin: 4px 0 0 0; opacity: 0.85; }
          .kpi-sub { font-size: 0.9rem; opacity: 0.75; margin-top: -6px; }
          .tiny { font-size: 0.85rem; opacity: 0.85; }
          .muted { opacity: 0.75; }
          .pill {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 999px;
            border: 1px solid rgba(49, 51, 63, 0.22);
            font-size: 0.85rem;
            margin-right: 6px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def invalidate_data_cache() -> None:
    try:
        st.cache_data.clear()
    except Exception:
        pass


def fmt_kg(value: float) -> str:
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return "0.00"


def fmt_pct(value: float) -> str:
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "0.0%"


def ensure_database() -> None:
    """
    Make sure the main database exists.

    Important: we intentionally do NOT call setup_database() if the file
    already exists, because setup_database() recreates the whole DB
    (dropping user data). We only use it on first run.
    """
    if not os.path.exists(DB_PATH):
        setup_database()
        # Fresh DB already has correct emission factors.
        return

    # Basic sanity check: ensure core table exists; if not, recreate once.
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='User_Profile'"
        )
        exists = cur.fetchone() is not None
        conn.close()
        if not exists:
            setup_database()
    except Exception:
        # If anything is badly broken, recreate with demo data.
        setup_database()

    # Always ensure emission factors are up to date, even for existing DBs.
    try:
        ensure_correct_emission_factors(DB_PATH)
    except Exception:
        # If this fails, we still want the app to run; emission factors will just remain as-is.
        pass


# --- Auth helpers (adapted from login.py, but Streamlit-friendly) ---


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _is_valid_email(email: str) -> bool:
    return "@" in email and "." in email.split("@")[-1]


def _is_valid_password(password: str) -> bool:
    if len(password) < 6:
        return False
    return any(ch.isupper() for ch in password)


def _ensure_auth_table(conn: sqlite3.Connection | None = None) -> None:
    close_after = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_after = True
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS User_Auth (
            User_ID INTEGER PRIMARY KEY,
            Email TEXT UNIQUE NOT NULL,
            Password_Hash TEXT NOT NULL,
            Role TEXT NOT NULL,
            FOREIGN KEY (User_ID) REFERENCES User_Profile(User_ID)
        )
        """
    )
    conn.commit()
    if close_after:
        conn.close()


def create_user(name: str, email: str, location: str, password: str, role: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    _ensure_auth_table(conn)

    cur.execute(
        "SELECT COUNT(*) FROM User_Profile WHERE lower(Email) = lower(?)", (email,)
    )
    exists = cur.fetchone()[0] > 0
    if exists:
        conn.close()
        raise ValueError("An account with this email already exists. Please sign in instead.")

    # Create profile
    cur.execute(
        "INSERT INTO User_Profile (Full_Name, Email, Location) VALUES (?, ?, ?)",
        (name, email, location),
    )
    user_id = cur.lastrowid

    password_hash = _hash_password(password)
    role_norm = "developer" if role == "developer" else "user"

    cur.execute(
        """
        INSERT INTO User_Auth (User_ID, Email, Password_Hash, Role)
        VALUES (?, lower(?), ?, ?)
        """,
        (user_id, email, password_hash, role_norm),
    )

    conn.commit()
    conn.close()


def load_session(email: str, password: str, mode: str) -> AppSession:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    _ensure_auth_table(conn)

    cur.execute(
        """
        SELECT ua.User_ID, ua.Password_Hash, ua.Role
        FROM User_Auth ua
        WHERE ua.Email = lower(?)
        """,
        (email,),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError("No account found for this email. Please create an account first.")

    user_id, stored_hash, role = row
    if stored_hash != _hash_password(password):
        conn.close()
        raise ValueError("Incorrect password.")

    cur.execute(
        "SELECT Full_Name, Email, Location FROM User_Profile WHERE User_ID = ?",
        (user_id,),
    )
    profile = cur.fetchone()
    conn.close()

    if not profile:
        raise ValueError("User profile not found for this account.")

    full_name, email_db, location = profile

    if mode not in ("Individual", "Industry"):
        mode = "Individual"
    role_norm = role if role in ("user", "developer") else "user"

    return AppSession(
        user_id=int(user_id),
        full_name=str(full_name),
        email=str(email_db),
        location=str(location),
        mode=mode,
        role=role_norm,
    )


# --- Shared data access helpers (reused from reports/recommendations) ---


@st.cache_data(show_spinner=False)
def get_user_emission_data(user_id: int, date_from: str, date_to: str) -> dict:
    conn = sqlite3.connect(DB_PATH)

    df_user = pd.read_sql_query(
        "SELECT * FROM User_Profile WHERE User_ID = ?",
        conn,
        params=(user_id,),
    )

    df_transport = pd.read_sql_query(
        """
        SELECT t.*, ef.Emission_Per_Unit,
               (t.Distance_KM * ef.Emission_Per_Unit) as Emission_Amount
        FROM Transportation t
        LEFT JOIN Emission_Factor ef ON t.Vehicle_Type = ef.Source_Type
        WHERE t.User_ID = ? AND t.Date BETWEEN ? AND ?
        """,
        conn,
        params=(user_id, date_from, date_to),
    )

    df_energy = pd.read_sql_query(
        """
        SELECT ec.*, ef.Emission_Per_Unit,
               (ec.Consumption_KWH * ef.Emission_Per_Unit) as Emission_Amount
        FROM Energy_Consumption ec
        LEFT JOIN Emission_Factor ef ON ec.Energy_Source = ef.Source_Type
        WHERE ec.User_ID = ? AND ec.Date BETWEEN ? AND ?
        """,
        conn,
        params=(user_id, date_from, date_to),
    )

    df_waste = pd.read_sql_query(
        """
        SELECT wm.*, ef.Emission_Per_Unit,
               (wm.Waste_Weight_KG * ef.Emission_Per_Unit) as Emission_Amount
        FROM Waste_Management wm
        LEFT JOIN Emission_Factor ef ON wm.Waste_Type = ef.Source_Type
        WHERE wm.User_ID = ? AND wm.Date BETWEEN ? AND ?
        """,
        conn,
        params=(user_id, date_from, date_to),
    )

    df_industrial = pd.read_sql_query(
        """
        SELECT * FROM Industrial_Activity
        WHERE User_ID = ? AND Date BETWEEN ? AND ?
        """,
        conn,
        params=(user_id, date_from, date_to),
    )

    df_offset = pd.read_sql_query(
        """
        SELECT * FROM Carbon_Offset
        WHERE User_ID = ? AND Date BETWEEN ? AND ?
        """,
        conn,
        params=(user_id, date_from, date_to),
    )

    # If emission factors are missing, Emission_Amount becomes NaN. Keep numbers stable.
    for df in (df_transport, df_energy, df_waste):
        if not df.empty and "Emission_Amount" in df.columns:
            df["Emission_Amount"] = pd.to_numeric(df["Emission_Amount"], errors="coerce").fillna(0.0)
        if not df.empty and "Emission_Per_Unit" in df.columns:
            df["Emission_Per_Unit"] = pd.to_numeric(df["Emission_Per_Unit"], errors="coerce")

    if not df_industrial.empty and "Emission_Produced" in df_industrial.columns:
        df_industrial["Emission_Produced"] = pd.to_numeric(
            df_industrial["Emission_Produced"], errors="coerce"
        ).fillna(0.0)

    if not df_offset.empty and "Offset_Amount" in df_offset.columns:
        df_offset["Offset_Amount"] = pd.to_numeric(df_offset["Offset_Amount"], errors="coerce").fillna(0.0)

    transport_emissions = float(
        df_transport["Emission_Amount"].sum() if not df_transport.empty else 0
    )
    energy_emissions = float(
        df_energy["Emission_Amount"].sum() if not df_energy.empty else 0
    )
    waste_emissions = float(
        df_waste["Emission_Amount"].sum() if not df_waste.empty else 0
    )
    industrial_emissions = float(
        df_industrial["Emission_Produced"].sum() if not df_industrial.empty else 0
    )

    total_emissions = transport_emissions + energy_emissions + waste_emissions + industrial_emissions
    total_offset = float(df_offset["Offset_Amount"].sum() if not df_offset.empty else 0)
    net_emissions = total_emissions - total_offset

    conn.close()

    return {
        "user": df_user,
        "transport": df_transport,
        "energy": df_energy,
        "waste": df_waste,
        "industrial": df_industrial,
        "offset": df_offset,
        "summary": {
            "transport_emissions": transport_emissions,
            "energy_emissions": energy_emissions,
            "waste_emissions": waste_emissions,
            "industrial_emissions": industrial_emissions,
            "total_emissions": total_emissions,
            "total_offset": total_offset,
            "net_emissions": net_emissions,
        },
    }


def to_monthly_series(df: pd.DataFrame, date_col: str, value_col: str) -> pd.Series | None:
    if df is None or df.empty or date_col not in df.columns or value_col not in df.columns:
        return None
    tmp = df[[date_col, value_col]].copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
    tmp[value_col] = pd.to_numeric(tmp[value_col], errors="coerce").fillna(0.0)
    tmp = tmp.dropna(subset=[date_col])
    if tmp.empty:
        return None
    tmp["Month"] = tmp[date_col].dt.to_period("M").dt.to_timestamp()
    return tmp.groupby("Month")[value_col].sum().sort_index()


def to_daily_series(df: pd.DataFrame, date_col: str, value_col: str) -> pd.Series | None:
    if df is None or df.empty or date_col not in df.columns or value_col not in df.columns:
        return None
    tmp = df[[date_col, value_col]].copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
    tmp[value_col] = pd.to_numeric(tmp[value_col], errors="coerce").fillna(0.0)
    tmp = tmp.dropna(subset=[date_col])
    if tmp.empty:
        return None
    tmp["Day"] = tmp[date_col].dt.floor("D")
    return tmp.groupby("Day")[value_col].sum().sort_index()


def to_weekly_series(df: pd.DataFrame, date_col: str, value_col: str) -> pd.Series | None:
    if df is None or df.empty or date_col not in df.columns or value_col not in df.columns:
        return None
    tmp = df[[date_col, value_col]].copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
    tmp[value_col] = pd.to_numeric(tmp[value_col], errors="coerce").fillna(0.0)
    tmp = tmp.dropna(subset=[date_col])
    if tmp.empty:
        return None
    # Week starts on Monday
    tmp["Week"] = tmp[date_col].dt.to_period("W-MON").dt.start_time
    return tmp.groupby("Week")[value_col].sum().sort_index()


def _fit_linear_forecast(series: pd.Series, periods: int = 3, min_points: int = 3) -> pd.DataFrame | None:
    """
    Simple linear trend forecast on a time-indexed series.
    Returns a dataframe with history + forecast values.
    """
    if series is None or series.empty:
        return None
    s = series.copy()
    s = pd.to_numeric(s, errors="coerce").fillna(0.0)
    s = s[s.index.notna()]
    if len(s) < min_points:
        return None

    # Use equally spaced steps (0..n-1) for stability.
    x = np.arange(len(s), dtype=float)
    y = s.values.astype(float)

    try:
        slope, intercept = np.polyfit(x, y, deg=1)
    except Exception:
        return None

    x_future = np.arange(len(s), len(s) + periods, dtype=float)
    y_future = intercept + slope * x_future
    y_future = np.maximum(y_future, 0.0)  # no negative emissions

    # Extend time index by month if series appears monthly, else by day.
    idx = s.index
    if len(idx) >= 2 and isinstance(idx[0], (pd.Timestamp,)):
        inferred = pd.infer_freq(idx)
    else:
        inferred = None

    if inferred and "M" in inferred:
        last = pd.Timestamp(idx[-1])
        future_index = pd.date_range(last + pd.offsets.MonthBegin(1), periods=periods, freq="MS")
    else:
        last = pd.Timestamp(idx[-1])
        future_index = pd.date_range(last + pd.Timedelta(days=1), periods=periods, freq="D")

    hist_df = pd.DataFrame({"Value": s.values}, index=s.index)
    fc_df = pd.DataFrame({"Value": y_future}, index=future_index)
    hist_df["Type"] = "History"
    fc_df["Type"] = "Forecast"
    out = pd.concat([hist_df, fc_df], axis=0)
    out.index.name = "Date"
    return out.reset_index()


def render_pie_chart(labels: list[str], values: list[float], title: str) -> None:
    """
    Render a pie chart if matplotlib is available; otherwise show a helpful message.
    """
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        st.info("Pie chart needs `matplotlib`. Install with: `pip install matplotlib`")
        return

    cleaned = [(l, float(v)) for l, v in zip(labels, values) if float(v) > 0]
    if not cleaned:
        st.info("No data available for a pie chart in this range.")
        return
    l2, v2 = zip(*cleaned)
    fig, ax = plt.subplots(figsize=(6, 4.2), dpi=120)
    ax.pie(v2, labels=l2, autopct="%1.1f%%", startangle=90)
    ax.axis("equal")
    ax.set_title(title)
    st.pyplot(fig, use_container_width=True)


@st.cache_data(show_spinner=False)
def get_population_emissions(date_from: str, date_to: str) -> pd.DataFrame:
    """
    Per-user totals for a date range (benchmarking).
    Missing emission factors are treated as 0 via COALESCE.
    """
    conn = sqlite3.connect(DB_PATH)

    # Transport (distance * factor)
    df_t = pd.read_sql_query(
        """
        SELECT
          up.User_ID,
          up.Full_Name,
          COALESCE(SUM(t.Distance_KM * COALESCE(ef.Emission_Per_Unit, 0)), 0) AS Transport_Emissions
        FROM User_Profile up
        LEFT JOIN Transportation t
          ON up.User_ID = t.User_ID AND t.Date BETWEEN ? AND ?
        LEFT JOIN Emission_Factor ef
          ON t.Vehicle_Type = ef.Source_Type
        GROUP BY up.User_ID, up.Full_Name
        """,
        conn,
        params=(date_from, date_to),
    )

    # Energy (kwh * factor)
    df_e = pd.read_sql_query(
        """
        SELECT
          up.User_ID,
          up.Full_Name,
          COALESCE(SUM(ec.Consumption_KWH * COALESCE(ef.Emission_Per_Unit, 0)), 0) AS Energy_Emissions
        FROM User_Profile up
        LEFT JOIN Energy_Consumption ec
          ON up.User_ID = ec.User_ID AND ec.Date BETWEEN ? AND ?
        LEFT JOIN Emission_Factor ef
          ON ec.Energy_Source = ef.Source_Type
        GROUP BY up.User_ID, up.Full_Name
        """,
        conn,
        params=(date_from, date_to),
    )

    # Waste (kg * waste factor)
    df_w = pd.read_sql_query(
        """
        SELECT
          up.User_ID,
          up.Full_Name,
          COALESCE(SUM(wm.Waste_Weight_KG * COALESCE(ef.Emission_Per_Unit, 0)), 0) AS Waste_Emissions
        FROM User_Profile up
        LEFT JOIN Waste_Management wm
          ON up.User_ID = wm.User_ID AND wm.Date BETWEEN ? AND ?
        LEFT JOIN Emission_Factor ef
          ON wm.Waste_Type = ef.Source_Type
        GROUP BY up.User_ID, up.Full_Name
        """,
        conn,
        params=(date_from, date_to),
    )

    # Industrial (Emission_Produced directly)
    df_i = pd.read_sql_query(
        """
        SELECT
          up.User_ID,
          up.Full_Name,
          COALESCE(SUM(ia.Emission_Produced), 0) AS Industrial_Emissions
        FROM User_Profile up
        LEFT JOIN Industrial_Activity ia
          ON up.User_ID = ia.User_ID AND ia.Date BETWEEN ? AND ?
        GROUP BY up.User_ID, up.Full_Name
        """,
        conn,
        params=(date_from, date_to),
    )

    # Offset
    df_o = pd.read_sql_query(
        """
        SELECT
          up.User_ID,
          up.Full_Name,
          COALESCE(SUM(co.Offset_Amount), 0) AS Total_Offset
        FROM User_Profile up
        LEFT JOIN Carbon_Offset co
          ON up.User_ID = co.User_ID AND co.Date BETWEEN ? AND ?
        GROUP BY up.User_ID, up.Full_Name
        """,
        conn,
        params=(date_from, date_to),
    )

    conn.close()

    out = df_t.merge(df_e, on=["User_ID", "Full_Name"], how="outer")
    out = out.merge(df_w, on=["User_ID", "Full_Name"], how="outer")
    out = out.merge(df_i, on=["User_ID", "Full_Name"], how="outer")
    out = out.merge(df_o, on=["User_ID", "Full_Name"], how="outer")

    for c in [
        "Transport_Emissions",
        "Energy_Emissions",
        "Waste_Emissions",
        "Industrial_Emissions",
        "Total_Offset",
    ]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)

    out["Total_Emissions"] = (
        out["Transport_Emissions"]
        + out["Energy_Emissions"]
        + out["Waste_Emissions"]
        + out["Industrial_Emissions"]
    )
    out["Net_Emissions"] = out["Total_Emissions"] - out["Total_Offset"]

    return out.sort_values("Net_Emissions", ascending=False).reset_index(drop=True)


def build_overview_insights(summary: dict) -> dict:
    breakdown = {
        "Transportation": float(summary.get("transport_emissions", 0.0)),
        "Energy Consumption": float(summary.get("energy_emissions", 0.0)),
        "Waste Management": float(summary.get("waste_emissions", 0.0)),
        "Industrial Activity": float(summary.get("industrial_emissions", 0.0)),
    }
    total = float(summary.get("total_emissions", 0.0))
    top = max(breakdown, key=breakdown.get) if breakdown else "Transportation"
    top_value = breakdown.get(top, 0.0)
    top_share = (top_value / total * 100.0) if total > 0 else 0.0
    return {
        "breakdown": breakdown,
        "total": total,
        "top_category": top,
        "top_value": top_value,
        "top_share_pct": top_share,
    }


# --- Page: Auth (login / signup) ---


def page_auth() -> None:
    inject_ui()
    st.markdown(
        f"""
        <div class="hero">
          <h2>{APP_TITLE}</h2>
          <p class="muted">{APP_TAGLINE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("Sign in to add data, analyze your emissions, and get personalized recommendations.")

    tab_signin, tab_signup = st.tabs(["Sign in", "Create account"])

    with tab_signin:
        email = st.text_input("Email", key="signin_email")
        password = st.text_input("Password", type="password", key="signin_password")
        mode = st.selectbox(
            "Mode",
            options=["Individual", "Industry"],
            index=0,
            key="signin_mode",
        )
        if st.button("Sign in"):
            if not email or not password:
                st.warning("Please enter both email and password.")
            elif not _is_valid_email(email):
                st.warning("Please enter a valid email address.")
            else:
                try:
                    session = load_session(email=email, password=password, mode=mode)
                    st.session_state.session = session
                    st.success("Signed in successfully.")
                    st.rerun()
                except ValueError as e:
                    st.warning(str(e))
                except Exception as e:
                    st.error(f"Failed to sign in: {e}")

    with tab_signup:
        name = st.text_input("Full name", key="signup_name")
        email_su = st.text_input("Email", key="signup_email")
        location = st.text_input("Location / City", key="signup_location")
        mode_su = st.selectbox(
            "Mode",
            options=["Individual", "Industry"],
            index=0,
            key="signup_mode",
        )
        password_su = st.text_input("Password", type="password", key="signup_password")
        role = st.radio(
            "Account type",
            options=[("End user", "user"), ("Developer (advanced)", "developer")],
            format_func=lambda x: x[0],
            key="signup_role",
        )[1]

        if st.button("Create account"):
            if not name or not email_su or not location or not password_su:
                st.warning("Please fill in name, email, location and password.")
            elif not _is_valid_email(email_su):
                st.warning("Please enter a valid email address.")
            elif not _is_valid_password(password_su):
                st.warning(
                    "Password must be at least 6 characters and contain at least one uppercase letter."
                )
            else:
                try:
                    create_user(
                        name=name,
                        email=email_su,
                        location=location,
                        password=password_su,
                        role=role,
                    )
                    session = load_session(
                        email=email_su, password=password_su, mode=mode_su
                    )
                    st.session_state.session = session
                    st.success("Account created and signed in.")
                    st.rerun()
                except ValueError as e:
                    st.warning(str(e))
                except Exception as e:
                    st.error(f"Failed to create account: {e}")


# --- Page: Home ---


def page_home(session: AppSession) -> None:
    inject_ui()
    st.markdown(
        f"""
        <div class="hero">
          <h2>Dashboard</h2>
          <p class="muted">Welcome back, {session.full_name}.</p>
          <div style="margin-top:8px;">
            <span class="pill">Mode: <b>{session.mode}</b></span>
            <span class="pill">Role: <b>{session.role}</b></span>
            <span class="pill">Location: <b>{session.location}</b></span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
1. **Add your latest data** – transportation, energy use, waste, or industrial activity.
2. **Generate your carbon report** – see breakdowns, charts, and trends.
3. **Follow recommendations** – get a prioritized action plan and suggested programs.
        """
    )


# --- Page: Add Data ---


def get_categories_for_session(session: AppSession | None) -> list[str]:
    if session is None:
        return [
            "Transportation",
            "Energy Consumption",
            "Waste Management",
            "Industrial Activity",
            "Carbon Offset",
        ]
    if session.mode == "Industry":
        return [
            "Industrial Activity",
            "Energy Consumption",
            "Transportation",
            "Carbon Offset",
        ]
    return [
        "Transportation",
        "Energy Consumption",
        "Waste Management",
        "Carbon Offset",
    ]


def insert_transportation(session: AppSession, user_id: int | None = None) -> None:
    st.subheader("Transportation")

    vehicle_type = st.selectbox(
        "Vehicle type",
        options=[
            "Car",
            "Bus",
            "Train",
            "Airplane",
            "Bicycle",
            "Electric Car",
            "Motorcycle",
            "Walking",
        ],
    )
    distance = st.number_input("Distance (km)", min_value=0.0, step=1.0)
    date = st.date_input("Date", value=datetime.now().date())

    if st.button("Save transportation record"):
        uid = session.user_id if session is not None else user_id
        if not uid:
            st.warning("User is not selected.")
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO Transportation (User_ID, Vehicle_Type, Distance_KM, Date) "
                "VALUES (?, ?, ?, ?)",
                (uid, vehicle_type, float(distance), date.isoformat()),
            )
            conn.commit()
            conn.close()
            invalidate_data_cache()
            st.success("Transportation data added successfully.")
        except Exception as e:
            st.error(f"Error inserting data: {e}")


def insert_energy(session: AppSession, user_id: int | None = None) -> None:
    st.subheader("Energy Consumption")
    source = st.selectbox(
        "Energy source",
        options=[
            "Electricity",
            "Natural Gas",
            "Solar",
            "Wind",
            "Coal",
            "Biomass",
            "Geothermal",
        ],
    )
    kwh = st.number_input("Consumption (kWh)", min_value=0.0, step=1.0)
    date = st.date_input("Date", value=datetime.now().date(), key="energy_date")

    if st.button("Save energy record"):
        uid = session.user_id if session is not None else user_id
        if not uid:
            st.warning("User is not selected.")
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO Energy_Consumption (User_ID, Energy_Source, Consumption_KWH, Date) "
                "VALUES (?, ?, ?, ?)",
                (uid, source, float(kwh), date.isoformat()),
            )
            conn.commit()
            conn.close()
            invalidate_data_cache()
            st.success("Energy consumption data added successfully.")
        except Exception as e:
            st.error(f"Error inserting data: {e}")


def insert_waste(session: AppSession, user_id: int | None = None) -> None:
    st.subheader("Waste Management")
    wtype = st.selectbox(
        "Waste type",
        options=["Plastic", "Paper", "Glass", "Metal", "Organic", "Electronic", "Hazardous"],
    )
    weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1)
    date = st.date_input("Date", value=datetime.now().date(), key="waste_date")

    if st.button("Save waste record"):
        uid = session.user_id if session is not None else user_id
        if not uid:
            st.warning("User is not selected.")
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO Waste_Management (User_ID, Waste_Type, Waste_Weight_KG, Date) "
                "VALUES (?, ?, ?, ?)",
                (uid, wtype, float(weight), date.isoformat()),
            )
            conn.commit()
            conn.close()
            invalidate_data_cache()
            st.success("Waste management data added successfully.")
        except Exception as e:
            st.error(f"Error inserting data: {e}")


def insert_industrial(session: AppSession, user_id: int | None = None) -> None:
    st.subheader("Industrial Activity")
    atype = st.selectbox(
        "Activity type",
        options=[
            "Manufacturing",
            "Construction",
            "Chemical Processing",
            "Food Processing",
            "Textile Production",
            "Mining",
            "Agriculture",
        ],
    )
    emission = st.number_input("Emission produced (kg CO2e)", min_value=0.0, step=1.0)
    date = st.date_input("Date", value=datetime.now().date(), key="industrial_date")

    if st.button("Save industrial activity"):
        uid = session.user_id if session is not None else user_id
        if not uid:
            st.warning("User is not selected.")
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO Industrial_Activity (User_ID, Activity_Type, Emission_Produced, Date) "
                "VALUES (?, ?, ?, ?)",
                (uid, atype, float(emission), date.isoformat()),
            )
            conn.commit()
            conn.close()
            invalidate_data_cache()
            st.success("Industrial activity data added successfully.")
        except Exception as e:
            st.error(f"Error inserting data: {e}")


def insert_offset(session: AppSession, user_id: int | None = None) -> None:
    st.subheader("Carbon Offset")
    otype = st.selectbox(
        "Offset type",
        options=[
            "Tree Planting",
            "Renewable Energy Credits",
            "Methane Capture",
            "Carbon Sequestration",
            "Energy Efficiency",
        ],
    )
    amount = st.number_input("Offset amount (kg CO2e)", min_value=0.0, step=1.0)
    date = st.date_input("Date", value=datetime.now().date(), key="offset_date")

    if st.button("Save offset"):
        uid = session.user_id if session is not None else user_id
        if not uid:
            st.warning("User is not selected.")
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO Carbon_Offset (User_ID, Offset_Type, Offset_Amount, Date) "
                "VALUES (?, ?, ?, ?)",
                (uid, otype, float(amount), date.isoformat()),
            )
            conn.commit()
            conn.close()
            invalidate_data_cache()
            st.success("Carbon offset data added successfully.")
        except Exception as e:
            st.error(f"Error inserting data: {e}")


def page_add_data(session: AppSession) -> None:
    inject_ui()
    st.markdown(
        """
        <div class="hero">
          <h2>Add Data</h2>
          <p class="muted">Add your latest activities so analysis stays up to date.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    categories = get_categories_for_session(session)
    category = st.selectbox("Category", options=categories)

    # Only logged-in user is used (no arbitrary user switching in web UI).
    if category == "Transportation":
        insert_transportation(session)
    elif category == "Energy Consumption":
        insert_energy(session)
    elif category == "Waste Management":
        insert_waste(session)
    elif category == "Industrial Activity":
        insert_industrial(session)
    elif category == "Carbon Offset":
        insert_offset(session)


# --- Page: Analysis & Charts ---


def page_analysis(session: AppSession) -> None:
    inject_ui()
    st.markdown(
        """
        <div class="hero">
          <h2>Analysis & Charts</h2>
          <p class="muted">Explore totals, trends, breakdowns, and run simple what‑if scenarios.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("analysis_form"):
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            date_from = st.date_input(
                "From date", value=datetime.now().replace(month=1, day=1).date()
            )
        with col2:
            date_to = st.date_input("To date", value=datetime.now().date())
        with col3:
            st.write("")
            st.write("")
            submitted = st.form_submit_button("Generate analysis")

    if submitted:
        st.session_state.analysis_range = (date_from.isoformat(), date_to.isoformat())

    if "analysis_range" not in st.session_state:
        st.info("Pick a date range and click **Generate analysis**.")
        return

    date_from_s, date_to_s = st.session_state.analysis_range

    try:
        data = get_user_emission_data(session.user_id, date_from_s, date_to_s)
    except Exception as e:
        st.error(f"Error generating analysis: {e}")
        return

    summary = data["summary"]
    insights = build_overview_insights(summary)

    st.subheader("Key metrics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total emissions (kg CO2e)", fmt_kg(summary["total_emissions"]))
    c2.metric("Carbon offset (kg CO2e)", fmt_kg(summary["total_offset"]))
    c3.metric("Net emissions (kg CO2e)", fmt_kg(summary["net_emissions"]))
    c4.metric("Top source", insights["top_category"])
    st.markdown(
        f"<div class='kpi-sub'>Top source contributes <b>{fmt_pct(insights['top_share_pct'])}</b> "
        f"({fmt_kg(insights['top_value'])} kg CO2e) of your total in this period.</div>",
        unsafe_allow_html=True,
    )

    tab_overview, tab_trends, tab_forecast, tab_benchmark, tab_breakdowns, tab_whatif, tab_export = st.tabs(
        ["Overview", "Trends", "Forecast", "Benchmark", "Breakdowns", "What‑if", "Export"]
    )

    with tab_overview:
        st.markdown("#### Emissions by source")
        breakdown_df = pd.DataFrame(
            {
                "Source": list(insights["breakdown"].keys()),
                "Emissions (kg CO2e)": list(insights["breakdown"].values()),
            }
        )
        breakdown_df["Share (%)"] = (
            breakdown_df["Emissions (kg CO2e)"] / insights["total"] * 100.0
            if insights["total"] > 0
            else 0.0
        )
        breakdown_df = breakdown_df.sort_values("Emissions (kg CO2e)", ascending=False)

        st.bar_chart(
            breakdown_df.set_index("Source")["Emissions (kg CO2e)"],
            use_container_width=True,
        )

        st.markdown("#### Share (pie chart)")
        render_pie_chart(
            labels=list(insights["breakdown"].keys()),
            values=list(insights["breakdown"].values()),
            title="Emissions share by source",
        )

        st.dataframe(
            breakdown_df,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### Data quality checks")
        missing_factor_transport = (
            int(data["transport"]["Emission_Per_Unit"].isna().sum())
            if not data["transport"].empty and "Emission_Per_Unit" in data["transport"].columns
            else 0
        )
        missing_factor_energy = (
            int(data["energy"]["Emission_Per_Unit"].isna().sum())
            if not data["energy"].empty and "Emission_Per_Unit" in data["energy"].columns
            else 0
        )
        if missing_factor_transport or missing_factor_energy:
            st.warning(
                f"Some records are missing emission factors (transport: {missing_factor_transport}, "
                f"energy: {missing_factor_energy}). Their calculated emissions are treated as 0 until a factor exists."
            )
        else:
            st.success("All transport/energy records in this range have emission factors.")

    with tab_trends:
        st.markdown("#### Monthly trend (total vs net)")
        transport_m = to_monthly_series(data["transport"], "Date", "Emission_Amount")
        energy_m = to_monthly_series(data["energy"], "Date", "Emission_Amount")
        waste_m = to_monthly_series(data["waste"], "Date", "Emission_Amount")
        industrial_m = to_monthly_series(data["industrial"], "Date", "Emission_Produced")
        offset_m = to_monthly_series(data["offset"], "Date", "Offset_Amount")

        series_list = [s for s in [transport_m, energy_m, waste_m, industrial_m, offset_m] if s is not None]
        if not series_list:
            st.info("No dated data available to build trends for this period.")
        else:
            all_months = pd.Index([])
            for s in series_list:
                all_months = all_months.union(s.index)
            all_months = all_months.sort_values()

            def reindex(s):
                return s.reindex(all_months, fill_value=0.0) if s is not None else pd.Series(0.0, index=all_months)

            t = reindex(transport_m)
            e = reindex(energy_m)
            w = reindex(waste_m)
            i = reindex(industrial_m)
            o = reindex(offset_m)

            total = t + e + w + i
            net = total - o

            trend_df = pd.DataFrame(
                {
                    "Total emissions": total,
                    "Net emissions": net,
                    "Offset": o,
                }
            )
            st.line_chart(trend_df, use_container_width=True)

            st.markdown("#### Monthly breakdown (stacked)")
            stacked = pd.DataFrame(
                {
                    "Transportation": t,
                    "Energy": e,
                    "Waste": w,
                    "Industrial": i,
                }
            )
            st.area_chart(stacked, use_container_width=True)

        st.markdown("#### Daily / weekly views")

        # --- Daily ---
        t_d = to_daily_series(data["transport"], "Date", "Emission_Amount")
        e_d = to_daily_series(data["energy"], "Date", "Emission_Amount")
        w_d = to_daily_series(data["waste"], "Date", "Emission_Amount")
        i_d = to_daily_series(data["industrial"], "Date", "Emission_Produced")
        o_d = to_daily_series(data["offset"], "Date", "Offset_Amount")

        daily_series_list = [s for s in [t_d, e_d, w_d, i_d, o_d] if s is not None]
        if daily_series_list:
            all_days = pd.Index([])
            for s in daily_series_list:
                all_days = all_days.union(s.index)
            all_days = all_days.sort_values()

            def reindex_daily(s):
                return s.reindex(all_days, fill_value=0.0) if s is not None else pd.Series(0.0, index=all_days)

            total_daily = reindex_daily(t_d) + reindex_daily(e_d) + reindex_daily(w_d) + reindex_daily(i_d)
            offset_daily = reindex_daily(o_d)

            dd = pd.DataFrame(
                {
                    "Total emissions": total_daily,
                    "Net emissions": total_daily - offset_daily,
                }
            )
            st.line_chart(dd, use_container_width=True)
        else:
            st.info("Not enough dated records to show daily trend.")

        # --- Weekly ---
        t_w = to_weekly_series(data["transport"], "Date", "Emission_Amount")
        e_w = to_weekly_series(data["energy"], "Date", "Emission_Amount")
        w_w = to_weekly_series(data["waste"], "Date", "Emission_Amount")
        i_w = to_weekly_series(data["industrial"], "Date", "Emission_Produced")
        o_w = to_weekly_series(data["offset"], "Date", "Offset_Amount")

        weekly_series_list = [s for s in [t_w, e_w, w_w, i_w, o_w] if s is not None]
        if weekly_series_list:
            all_weeks = pd.Index([])
            for s in weekly_series_list:
                all_weeks = all_weeks.union(s.index)
            all_weeks = all_weeks.sort_values()

            def reindex_weekly(s):
                return s.reindex(all_weeks, fill_value=0.0) if s is not None else pd.Series(0.0, index=all_weeks)

            total_weekly = reindex_weekly(t_w) + reindex_weekly(e_w) + reindex_weekly(w_w) + reindex_weekly(i_w)
            offset_weekly = reindex_weekly(o_w)

            wd = pd.DataFrame(
                {
                    "Weekly total emissions": total_weekly,
                    "Weekly net emissions": total_weekly - offset_weekly,
                }
            )
            st.line_chart(wd, use_container_width=True)
        else:
            st.info("Not enough dated records to show weekly trend.")

    with tab_forecast:
        st.markdown("#### Forecast (simple trend)")
        st.write(
            "This forecast uses a simple linear trend on your historical monthly totals. "
            "It’s best-effort (not a scientific model) and is mainly useful for seeing direction."
        )

        # Build monthly net series from category + offset.
        transport_m = to_monthly_series(data["transport"], "Date", "Emission_Amount")
        energy_m = to_monthly_series(data["energy"], "Date", "Emission_Amount")
        waste_m = to_monthly_series(data["waste"], "Date", "Emission_Amount")
        industrial_m = to_monthly_series(data["industrial"], "Date", "Emission_Produced")
        offset_m = to_monthly_series(data["offset"], "Date", "Offset_Amount")

        series_list = [s for s in [transport_m, energy_m, waste_m, industrial_m, offset_m] if s is not None]
        if not series_list:
            st.info("No monthly history available to build a forecast.")
        else:
            all_months = pd.Index([])
            for s in series_list:
                all_months = all_months.union(s.index)
            all_months = all_months.sort_values()

            def reindex(s):
                return s.reindex(all_months, fill_value=0.0) if s is not None else pd.Series(0.0, index=all_months)

            total_m = reindex(transport_m) + reindex(energy_m) + reindex(waste_m) + reindex(industrial_m)
            net_m = total_m - reindex(offset_m)

            periods = st.slider("Forecast months", 1, 12, 3)
            hist_window = st.slider("Use last N months of history", 3, max(3, len(total_m)), min(12, len(total_m)))

            total_in = total_m.iloc[-hist_window:] if len(total_m) >= hist_window else total_m
            net_in = net_m.iloc[-hist_window:] if len(net_m) >= hist_window else net_m

            fc_total = _fit_linear_forecast(total_in, periods=periods, min_points=3)
            fc_net = _fit_linear_forecast(net_in, periods=periods, min_points=3)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Total emissions forecast**")
                if fc_total is None:
                    st.info("Not enough monthly points to forecast total emissions.")
                else:
                    chart_df = fc_total.pivot(index="Date", columns="Type", values="Value")
                    st.line_chart(chart_df, use_container_width=True)
                    st.dataframe(fc_total, use_container_width=True, hide_index=True)
            with c2:
                st.markdown("**Net emissions forecast**")
                if fc_net is None:
                    st.info("Not enough monthly points to forecast net emissions.")
                else:
                    chart_df = fc_net.pivot(index="Date", columns="Type", values="Value")
                    st.line_chart(chart_df, use_container_width=True)
                    st.dataframe(fc_net, use_container_width=True, hide_index=True)

            st.markdown("#### Tips to improve forecast quality")
            st.markdown(
                "- Add data consistently across weeks/months.\n"
                "- Ensure emission factors exist for your vehicle/energy sources.\n"
                "- Use a longer history window if your behavior is stable."
            )

    with tab_benchmark:
        st.markdown("#### Benchmark vs other users")
        st.write(
            "This compares your totals to all users in the database for the same date range. "
            "It’s useful for context (where you stand), not for judgement."
        )
        pop = get_population_emissions(date_from_s, date_to_s)
        if pop.empty:
            st.info("No users found in the database.")
        else:
            # Locate current user
            row = pop[pop["User_ID"] == session.user_id]
            if row.empty:
                st.info("Current user not found in population table.")
            else:
                net = float(row.iloc[0]["Net_Emissions"])
                total = float(row.iloc[0]["Total_Emissions"])
                rank = int(pop["Net_Emissions"].rank(method="min", ascending=False)[pop["User_ID"] == session.user_id].iloc[0])
                n = len(pop)
                percentile = float((pop["Net_Emissions"] <= net).mean() * 100.0) if n > 0 else 0.0

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Your net emissions", fmt_kg(net))
                c2.metric("Your total emissions", fmt_kg(total))
                c3.metric("Rank (net)", f"{rank} / {n}")
                c4.metric("Percentile (net)", fmt_pct(percentile))

            st.markdown("**Top emitters (net emissions)**")
            st.dataframe(
                pop[["User_ID", "Full_Name", "Total_Emissions", "Total_Offset", "Net_Emissions"]].head(10),
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("**Distribution (net emissions)**")
            try:
                import matplotlib.pyplot as plt  # type: ignore

                fig, ax = plt.subplots(figsize=(7, 3.2), dpi=120)
                ax.hist(pop["Net_Emissions"].values, bins=10, color="#2E7D32", alpha=0.85)
                ax.set_title("Net emissions distribution")
                ax.set_xlabel("kg CO2e")
                ax.set_ylabel("Users")
                st.pyplot(fig, use_container_width=True)
            except Exception:
                st.info("Histogram needs `matplotlib`. Install with: `pip install matplotlib`")

            with st.expander("Show all users (table)"):
                st.dataframe(pop, use_container_width=True, hide_index=True)

    with tab_breakdowns:
        st.markdown("#### Deep dives")
        sub_transport, sub_energy, sub_waste, sub_industrial, sub_offset = st.tabs(
            ["Transportation", "Energy", "Waste", "Industrial", "Offset"]
        )

        with sub_transport:
            df = data["transport"]
            if df.empty:
                st.info("No transportation data for this period.")
            else:
                st.markdown("**By vehicle type (emissions)**")
                by_type = (
                    df.groupby("Vehicle_Type", dropna=False)["Emission_Amount"]
                    .sum()
                    .sort_values(ascending=False)
                )
                st.bar_chart(by_type, use_container_width=True)
                st.markdown("**By vehicle type (distance)**")
                by_dist = (
                    df.groupby("Vehicle_Type", dropna=False)["Distance_KM"]
                    .sum()
                    .sort_values(ascending=False)
                )
                st.bar_chart(by_dist, use_container_width=True)
                st.dataframe(df, use_container_width=True)

        with sub_energy:
            df = data["energy"]
            if df.empty:
                st.info("No energy data for this period.")
            else:
                st.markdown("**By energy source (emissions)**")
                by_src = (
                    df.groupby("Energy_Source", dropna=False)["Emission_Amount"]
                    .sum()
                    .sort_values(ascending=False)
                )
                st.bar_chart(by_src, use_container_width=True)
                st.markdown("**By energy source (kWh)**")
                by_kwh = (
                    df.groupby("Energy_Source", dropna=False)["Consumption_KWH"]
                    .sum()
                    .sort_values(ascending=False)
                )
                st.bar_chart(by_kwh, use_container_width=True)
                st.dataframe(df, use_container_width=True)

        with sub_waste:
            df = data["waste"]
            if df.empty:
                st.info("No waste data for this period.")
            else:
                st.markdown("**By waste type (emissions)**")
                by_type = (
                    df.groupby("Waste_Type", dropna=False)["Emission_Amount"]
                    .sum()
                    .sort_values(ascending=False)
                )
                st.bar_chart(by_type, use_container_width=True)
                st.markdown("**By waste type (kg)**")
                by_kg = (
                    df.groupby("Waste_Type", dropna=False)["Waste_Weight_KG"]
                    .sum()
                    .sort_values(ascending=False)
                )
                st.bar_chart(by_kg, use_container_width=True)
                st.dataframe(df, use_container_width=True)

        with sub_industrial:
            df = data["industrial"]
            if df.empty:
                st.info("No industrial data for this period.")
            else:
                st.markdown("**By activity type (emissions)**")
                by_act = (
                    df.groupby("Activity_Type", dropna=False)["Emission_Produced"]
                    .sum()
                    .sort_values(ascending=False)
                )
                st.bar_chart(by_act, use_container_width=True)
                st.dataframe(df, use_container_width=True)

        with sub_offset:
            df = data["offset"]
            if df.empty:
                st.info("No offset data for this period.")
            else:
                st.markdown("**Offset by type (kg CO2e)**")
                by_type = (
                    df.groupby("Offset_Type", dropna=False)["Offset_Amount"]
                    .sum()
                    .sort_values(ascending=False)
                )
                st.bar_chart(by_type, use_container_width=True)
                st.dataframe(df, use_container_width=True)

    with tab_whatif:
        st.markdown("#### What‑if simulator")
        st.write(
            "Move the sliders to see how reductions in each category would change your totals. "
            "This does not modify your data — it’s just a calculation."
        )
        base = insights["breakdown"]
        total_base = float(summary.get("total_emissions", 0.0))
        offset_base = float(summary.get("total_offset", 0.0))

        colA, colB = st.columns(2)
        with colA:
            r_transport = st.slider("Reduce Transportation (%)", 0, 100, 0)
            r_energy = st.slider("Reduce Energy Consumption (%)", 0, 100, 0)
        with colB:
            r_waste = st.slider("Reduce Waste Management (%)", 0, 100, 0)
            r_ind = st.slider("Reduce Industrial Activity (%)", 0, 100, 0)

        def apply_reduction(v: float, pct: int) -> float:
            return float(v) * (1.0 - pct / 100.0)

        new_breakdown = {
            "Transportation": apply_reduction(base["Transportation"], r_transport),
            "Energy Consumption": apply_reduction(base["Energy Consumption"], r_energy),
            "Waste Management": apply_reduction(base["Waste Management"], r_waste),
            "Industrial Activity": apply_reduction(base["Industrial Activity"], r_ind),
        }
        new_total = sum(new_breakdown.values())
        new_net = new_total - offset_base
        savings = total_base - new_total

        c1, c2, c3 = st.columns(3)
        c1.metric("New total emissions", fmt_kg(new_total))
        c2.metric("Estimated savings", fmt_kg(savings))
        c3.metric("New net emissions", fmt_kg(new_net))

        sim_df = pd.DataFrame(
            {"Source": list(new_breakdown.keys()), "Emissions (kg CO2e)": list(new_breakdown.values())}
        ).sort_values("Emissions (kg CO2e)", ascending=False)
        st.bar_chart(sim_df.set_index("Source")["Emissions (kg CO2e)"], use_container_width=True)

    with tab_export:
        st.markdown("#### Export")
        st.write("Download summary and detail tables for the currently selected period.")

        summary_export = pd.DataFrame(
            [
                {
                    "From": date_from_s,
                    "To": date_to_s,
                    "Transport_Emissions": summary["transport_emissions"],
                    "Energy_Emissions": summary["energy_emissions"],
                    "Waste_Emissions": summary["waste_emissions"],
                    "Industrial_Emissions": summary["industrial_emissions"],
                    "Total_Emissions": summary["total_emissions"],
                    "Total_Offset": summary["total_offset"],
                    "Net_Emissions": summary["net_emissions"],
                }
            ]
        )
        st.download_button(
            "Download summary (CSV)",
            data=summary_export.to_csv(index=False).encode("utf-8"),
            file_name="carbon_summary.csv",
            mime="text/csv",
        )

        st.write("Detail tables:")
        for label, df in [
            ("Transportation", data["transport"]),
            ("Energy", data["energy"]),
            ("Waste", data["waste"]),
            ("Industrial", data["industrial"]),
            ("Offset", data["offset"]),
        ]:
            if df is None or df.empty:
                continue
            st.download_button(
                f"Download {label} (CSV)",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name=f"{label.lower()}_details.csv".replace(" ", "_"),
                mime="text/csv",
            )


# --- Page: Recommendations (text action plan) ---


def build_action_plan(summary: dict, session: AppSession, date_from: str, date_to: str) -> str:
    emissions = {
        "Transportation": summary["transport_emissions"],
        "Energy": summary["energy_emissions"],
        "Waste": summary["waste_emissions"],
        "Industrial": summary["industrial_emissions"],
    }

    highest = max(emissions, key=emissions.get)
    total = summary["total_emissions"]
    offset = summary["total_offset"]
    net = summary["net_emissions"]

    def pct(x: float) -> float:
        return (x / total * 100.0) if total > 0 else 0.0

    lines: list[str] = []
    lines.append(f"User: {session.full_name} ({session.email})")
    lines.append(f"Location: {session.location}")
    lines.append(f"Period: {date_from} to {date_to}")
    lines.append("")
    lines.append("Your emissions summary (kg CO2e):")
    lines.append(
        f"- Transportation: {emissions['Transportation']:.2f} ({pct(emissions['Transportation']):.1f}%)"
    )
    lines.append(
        f"- Energy: {emissions['Energy']:.2f} ({pct(emissions['Energy']):.1f}%)"
    )
    lines.append(
        f"- Waste: {emissions['Waste']:.2f} ({pct(emissions['Waste']):.1f}%)"
    )
    lines.append(
        f"- Industrial: {emissions['Industrial']:.2f} ({pct(emissions['Industrial']):.1f}%)"
    )
    lines.append(f"- Total: {total:.2f}")
    lines.append(f"- Offset: {offset:.2f}")
    lines.append(f"- Net: {net:.2f}")
    lines.append("")

    if session.mode in ("Individual", "Industry"):
        lines.append(f"Mode: {session.mode}")
    lines.append(f"Priority focus: {highest} (largest share of your emissions).")
    lines.append("")
    lines.append("Top tasks you can do (start with 2–3 this week):")
    lines.extend(category_tasks(highest, mode=session.mode))
    lines.append("")
    lines.append("Extra quick wins (low effort):")
    lines.extend(quick_wins(emissions))
    lines.append("")

    if total > 0 and offset < total * 0.1:
        lines.append("Offset note:")
        lines.append(
            "- Your offset is relatively low compared to your total emissions. "
            "Consider adding verified offsets after reducing emissions first."
        )
        lines.append("")

    return "\n".join(lines)


def category_tasks(category: str, mode: str | None = None) -> list[str]:
    if category == "Transportation":
        return [
            "- Replace 1–2 car trips/week with public transport, cycling, or walking.",
            "- Combine errands into a single trip and avoid peak traffic when possible.",
            "- Carpool for commuting or switch to a more fuel‑efficient / electric vehicle when feasible.",
            "- If you fly often: reduce short flights; prefer trains for shorter routes.",
        ]
    if category == "Energy":
        return [
            "- Switch to LED bulbs and set AC/heating 1–2°C closer to ambient.",
            "- Use energy‑efficient appliances and unplug standby devices (or use smart power strips).",
            "- Improve insulation (doors/windows) to reduce heating/cooling demand.",
            "- Consider renewable electricity (solar/wind) if available in your area.",
        ]
    if category == "Waste":
        return [
            "- Separate recyclables and start composting organic waste if possible.",
            "- Reduce single‑use plastics (carry bottle/bag/containers).",
            "- Buy in bulk / choose minimal packaging.",
            "- Repair, donate, or resell items before disposing.",
        ]
    # Industrial
    base = [
        "- Review process hotspots: target the highest-emitting activity first.",
        "- Reduce energy intensity (maintenance, optimization, efficient equipment).",
        "- Switch to cleaner energy sources where possible.",
        "- Track emissions monthly and set a reduction target (e.g., 5–10%).",
    ]
    if mode == "Industry":
        base.insert(
            1,
            "- Implement monitoring: measure emissions per unit output to find efficiency opportunities.",
        )
    return base


def quick_wins(emissions: dict) -> list[str]:
    tasks: list[str] = []
    tasks.append(
        "- Track emissions monthly (same categories) and aim for a small steady reduction."
    )
    if emissions.get("Transportation", 0) > 0:
        tasks.append("- Keep tires properly inflated and drive smoothly to reduce fuel use.")
    if emissions.get("Energy", 0) > 0:
        tasks.append("- Wash clothes in cold water and air-dry when possible.")
    if emissions.get("Waste", 0) > 0:
        tasks.append("- Plan meals to cut food waste (a hidden emissions source).")
    return tasks


def page_recommendations(session: AppSession) -> None:
    inject_ui()
    st.markdown(
        """
        <div class="hero">
          <h2>Recommendations</h2>
          <p class="muted">Get a prioritized plan based on your biggest emission sources.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input(
            "From date", value=datetime.now().replace(month=1, day=1).date(), key="rec_from"
        )
    with col2:
        date_to = st.date_input(
            "To date", value=datetime.now().date(), key="rec_to"
        )

    if st.button("Generate recommendations"):
        try:
            data = get_user_emission_data(
                session.user_id,
                date_from.isoformat(),
                date_to.isoformat(),
            )
        except Exception as e:
            st.error(f"Failed to generate recommendations: {e}")
            return

        summary = data["summary"]
        plan = build_action_plan(
            summary=summary,
            session=session,
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat(),
        )

        st.subheader("Action plan")
        st.text(plan)


# --- Page: Developer SQL tools ---


def page_developer_sql() -> None:
    inject_ui()
    st.markdown(
        """
        <div class="hero">
          <h2>Developer (SQL)</h2>
          <p class="muted">Advanced query runner for the database (developer accounts only).</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write(
        "Run advanced SQL queries directly on the `carbon_emission.db` database. "
        "Use `SELECT` for read-only exploration; `INSERT`/`UPDATE`/`DELETE` will modify data."
    )

    col_left, col_right = st.columns([2, 3])

    with col_left:
        st.markdown("**Predefined queries**")
        query_names = sorted(updated_queries.keys())
        selected_name = st.selectbox("Pick a predefined query", options=[""] + query_names)
        if selected_name:
            st.session_state.sql_text = updated_queries[selected_name]

    default_sql = st.session_state.get(
        "sql_text", "SELECT * FROM User_Profile LIMIT 10;"
    )
    sql_text = st.text_area(
        "SQL editor",
        value=default_sql,
        height=200,
        key="sql_text",
    )

    run_btn = st.button("Run query")

    if run_btn:
        query = sql_text.strip()
        if not query:
            st.warning("Please enter an SQL query to run.")
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            is_select = query.upper().lstrip().startswith("SELECT")

            if is_select:
                df = pd.read_sql_query(query, conn)
                conn.close()
                st.success(f"Query ran successfully. {len(df)} rows.")
                st.dataframe(df)

                if not df.empty:
                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Download results as CSV",
                        data=csv,
                        file_name="query_results.csv",
                        mime="text/csv",
                    )
            else:
                cur = conn.cursor()
                cur.execute(query)
                conn.commit()
                affected = cur.rowcount
                conn.close()
                st.success(f"Query executed successfully. {affected} rows affected.")
        except Exception as e:
            st.error(f"Query error: {e}")


# --- Main app ---


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        layout="wide",
    )

    ensure_database()

    session: AppSession | None = st.session_state.get("session")

    if session is None:
        page_auth()
        return

    with st.sidebar:
        st.markdown("### Navigation")
        page = st.radio(
            "Go to",
            options=[
                "Home",
                "Add Data",
                "Analysis & Charts",
                "Recommendations",
            ]
            + (["Developer (SQL)"] if session.role == "developer" else []),
        )
        st.markdown("---")
        st.write(f"Signed in as **{session.full_name}**")
        if st.button("Logout"):
            st.session_state.pop("session", None)
            st.rerun()

    if page == "Home":
        page_home(session)
    elif page == "Add Data":
        page_add_data(session)
    elif page == "Analysis & Charts":
        page_analysis(session)
    elif page == "Recommendations":
        page_recommendations(session)
    elif page == "Developer (SQL)":
        page_developer_sql()


if __name__ == "__main__":
    main()

