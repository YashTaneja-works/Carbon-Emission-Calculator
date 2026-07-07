import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sqlite3
from datetime import datetime
import pandas as pd


class RecommendationsFrame(ttk.Frame):
    """
    A user-focused tab that provides an actionable plan to reduce emissions.
    It does NOT change any emission calculations; it only reads the same data
    and presents recommendations more clearly.
    """

    def __init__(self, parent, session=None):
        super().__init__(parent)
        self.parent = parent
        self.session = session
        self.create_widgets()

    def create_widgets(self):
        header = ttk.Label(
            self,
            text="Personalized Recommendations",
            font=("Arial", 14, "bold"),
        )
        header.pack(anchor="w", padx=10, pady=(10, 2))

        subtitle_text = (
            "Select a date range to get a prioritized action plan to reduce carbon emissions."
            if self.session is not None
            else "Select a user and date range to get a prioritized action plan to reduce carbon emissions."
        )
        subtitle = ttk.Label(self, text=subtitle_text)
        subtitle.pack(anchor="w", padx=10, pady=(0, 10))

        # Controls
        controls = ttk.LabelFrame(self, text="Inputs")
        controls.pack(fill=tk.X, padx=10, pady=5)

        self.user_var = tk.StringVar()
        row0 = 0
        if self.session is None:
            users = self.get_users()
            ttk.Label(controls, text="User:").grid(row=row0, column=0, padx=6, pady=6, sticky="w")
            self.user_combo = ttk.Combobox(
                controls,
                textvariable=self.user_var,
                values=users,
                state="readonly",
                width=34,
            )
            self.user_combo.grid(row=row0, column=1, padx=6, pady=6, sticky="w")

            refresh_btn = ttk.Button(
                controls, text="Refresh", command=lambda: self.refresh_users(show_message=True)
            )
            refresh_btn.grid(row=row0, column=2, padx=6, pady=6)
            row0 += 1
        else:
            self.user_var.set(f"{self.session.user_id} - {self.session.full_name}")
            ttk.Label(controls, text="User:").grid(row=row0, column=0, padx=6, pady=6, sticky="w")
            ttk.Label(controls, text=f"{self.session.full_name} ({self.session.email})").grid(
                row=row0, column=1, padx=6, pady=6, sticky="w"
            )
            row0 += 1

        self.date_from_var = tk.StringVar(
            value=datetime.now().replace(month=1, day=1).strftime("%Y-%m-%d")
        )
        self.date_to_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))

        ttk.Label(controls, text="From (YYYY-MM-DD):").grid(
            row=row0, column=0, padx=6, pady=6, sticky="w"
        )
        ttk.Entry(controls, textvariable=self.date_from_var, width=18).grid(
            row=row0, column=1, padx=6, pady=6, sticky="w"
        )

        ttk.Label(controls, text="To (YYYY-MM-DD):").grid(
            row=row0 + 1, column=0, padx=6, pady=6, sticky="w"
        )
        ttk.Entry(controls, textvariable=self.date_to_var, width=18).grid(
            row=row0 + 1, column=1, padx=6, pady=6, sticky="w"
        )

        generate_btn = ttk.Button(controls, text="Generate Recommendations", command=self.generate)
        generate_btn.grid(row=row0 + 2, column=0, columnspan=2, padx=6, pady=(6, 10), sticky="w")

        copy_btn = ttk.Button(controls, text="Copy to Clipboard", command=self.copy_to_clipboard)
        copy_btn.grid(row=row0 + 2, column=2, padx=6, pady=(6, 10))

        controls.columnconfigure(1, weight=1)

        # Output
        output = ttk.LabelFrame(self, text="Action Plan")
        output.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.output_text = scrolledtext.ScrolledText(output, height=18, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.output_text.insert(
            "1.0",
            "Choose a user and date range, then click 'Generate Recommendations'.\n",
        )
        self.output_text.configure(state="disabled")

        # Programs (read-only suggestions)
        programs = ttk.LabelFrame(self, text="Suggested Sustainability Programs (Optional)")
        programs.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))

        self.programs_text = scrolledtext.ScrolledText(programs, height=8, wrap=tk.WORD)
        self.programs_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.programs_text.insert(
            "1.0",
            "These are optional programs from your database that match your main emission sources.\n",
        )
        self.programs_text.configure(state="disabled")

    def set_output(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def get_users(self):
        try:
            conn = sqlite3.connect("carbon_emission.db")
            cursor = conn.cursor()
            cursor.execute("SELECT User_ID, Full_Name FROM User_Profile")
            users = cursor.fetchall()
            conn.close()
            return [f"{u[0]} - {u[1]}" for u in users]
        except Exception as e:
            messagebox.showerror("Database Error", f"Error fetching users: {str(e)}")
            return []

    def refresh_users(self, show_message=False):
        users = self.get_users()
        self.user_combo["values"] = users
        if show_message:
            messagebox.showinfo("Refresh Complete", "User list has been refreshed.")

    def extract_user_id(self, user_string):
        if not user_string:
            return None
        try:
            return int(user_string.split(" - ")[0])
        except Exception:
            return None

    def generate(self):
        if self.session is not None:
            user_id = self.session.user_id
            user_string = f"{self.session.user_id} - {self.session.full_name}"
        else:
            user_string = self.user_var.get()
            user_id = self.extract_user_id(user_string)
            if not user_id:
                messagebox.showwarning("Selection Error", "Please select a user.")
                return

        date_from = self.date_from_var.get().strip()
        date_to = self.date_to_var.get().strip()
        try:
            datetime.strptime(date_from, "%Y-%m-%d")
            datetime.strptime(date_to, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Date Error", "Please enter valid dates in YYYY-MM-DD format.")
            return

        try:
            data = self.get_user_emission_data(user_id, date_from, date_to)
            summary = data["summary"]

            mode = getattr(self.session, "mode", None) if self.session is not None else None
            action_plan = self.build_action_plan(summary, user_string, date_from, date_to, mode=mode)
            self.set_output(self.output_text, action_plan)

            programs = self.build_program_suggestions(summary)
            self.set_output(self.programs_text, programs)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate recommendations: {str(e)}")

    def copy_to_clipboard(self):
        try:
            text = self.output_text.get("1.0", tk.END).strip()
            if not text:
                return
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("Copied", "Recommendations copied to clipboard.")
        except Exception as e:
            messagebox.showerror("Copy Error", str(e))

    # --- Data access (matches logic in ReportsFrame; read-only) ---
    def get_user_emission_data(self, user_id, date_from, date_to):
        conn = sqlite3.connect("carbon_emission.db")

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

        transport_emissions = df_transport["Emission_Amount"].sum() if not df_transport.empty else 0
        energy_emissions = df_energy["Emission_Amount"].sum() if not df_energy.empty else 0
        waste_emissions = df_waste["Emission_Amount"].sum() if not df_waste.empty else 0
        industrial_emissions = (
            df_industrial["Emission_Produced"].sum() if not df_industrial.empty else 0
        )

        total_emissions = transport_emissions + energy_emissions + waste_emissions + industrial_emissions
        total_offset = df_offset["Offset_Amount"].sum() if not df_offset.empty else 0
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
                "transport_emissions": float(transport_emissions),
                "energy_emissions": float(energy_emissions),
                "waste_emissions": float(waste_emissions),
                "industrial_emissions": float(industrial_emissions),
                "total_emissions": float(total_emissions),
                "total_offset": float(total_offset),
                "net_emissions": float(net_emissions),
            },
        }

    # --- Recommendation logic (presentation only) ---
    def build_action_plan(self, summary, user_string, date_from, date_to, mode=None):
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

        def pct(x):
            return (x / total * 100.0) if total > 0 else 0.0

        lines = []
        lines.append(f"User: {user_string}")
        lines.append(f"Period: {date_from} to {date_to}")
        lines.append("")
        lines.append("Your emissions summary (kg CO2e):")
        lines.append(f"- Transportation: {emissions['Transportation']:.2f} ({pct(emissions['Transportation']):.1f}%)")
        lines.append(f"- Energy: {emissions['Energy']:.2f} ({pct(emissions['Energy']):.1f}%)")
        lines.append(f"- Waste: {emissions['Waste']:.2f} ({pct(emissions['Waste']):.1f}%)")
        lines.append(f"- Industrial: {emissions['Industrial']:.2f} ({pct(emissions['Industrial']):.1f}%)")
        lines.append(f"- Total: {total:.2f}")
        lines.append(f"- Offset: {offset:.2f}")
        lines.append(f"- Net: {net:.2f}")
        lines.append("")

        if mode in ("Individual", "Industry"):
            lines.append(f"Mode: {mode}")
        lines.append(f"Priority focus: {highest} (largest share of your emissions).")
        lines.append("")
        lines.append("Top tasks you can do (start with 2–3 this week):")
        lines.extend(self.category_tasks(highest, mode=mode))
        lines.append("")
        lines.append("Extra quick wins (low effort):")
        lines.extend(self.quick_wins(emissions))
        lines.append("")

        if total > 0 and offset < total * 0.1:
            lines.append("Offset note:")
            lines.append("- Your offset is relatively low compared to your total emissions. Consider adding verified offsets after reducing emissions first.")
            lines.append("")

        return "\n".join(lines)

    def category_tasks(self, category, mode=None):
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
            base.insert(1, "- Implement monitoring: measure emissions per unit output to find efficiency opportunities.")
        return base

    def quick_wins(self, emissions):
        tasks = []
        # Always useful
        tasks.append("- Track emissions monthly (same categories) and aim for a small steady reduction.")
        # Tailor: if any category is non-zero, propose 1 additional quick win
        if emissions.get("Transportation", 0) > 0:
            tasks.append("- Keep tires properly inflated and drive smoothly to reduce fuel use.")
        if emissions.get("Energy", 0) > 0:
            tasks.append("- Wash clothes in cold water and air-dry when possible.")
        if emissions.get("Waste", 0) > 0:
            tasks.append("- Plan meals to cut food waste (a hidden emissions source).")
        return tasks

    def build_program_suggestions(self, summary):
        # Map top categories to program keywords in your Sustainability_Program table.
        emissions = {
            "Transportation": summary["transport_emissions"],
            "Energy": summary["energy_emissions"],
            "Waste": summary["waste_emissions"],
            "Industrial": summary["industrial_emissions"],
        }
        highest = max(emissions, key=emissions.get)

        category_to_program_names = {
            "Transportation": ["Sustainable Transportation"],
            "Energy": ["Green Energy Initiative", "Energy Efficiency Program"],
            "Waste": ["Zero Waste Challenge"],
            "Industrial": ["Carbon Footprint Reduction", "Energy Efficiency Program"],
        }

        wanted = category_to_program_names.get(highest, [])

        try:
            conn = sqlite3.connect("carbon_emission.db")
            df = pd.read_sql_query("SELECT Program_Name, Description FROM Sustainability_Program", conn)
            conn.close()
        except Exception:
            df = pd.DataFrame(columns=["Program_Name", "Description"])

        lines = []
        lines.append(f"Matched to your top category: {highest}")
        lines.append("")

        if df.empty:
            lines.append("No program data found.")
            return "\n".join(lines)

        matches = df[df["Program_Name"].isin(wanted)]
        if matches.empty:
            lines.append("No matching programs found in the database for this category.")
            return "\n".join(lines)

        for _, row in matches.iterrows():
            lines.append(f"- {row['Program_Name']}: {row['Description']}")

        lines.append("")
        lines.append("Tip: You can view all programs in the Advanced (SQL) tab with:")
        lines.append("SELECT * FROM Sustainability_Program;")
        return "\n".join(lines)

