import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class ScrollableFrame(ttk.Frame):
    """A vertically scrollable container for long report content."""

    def __init__(self, parent):
        super().__init__(parent)

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.inner = ttk.Frame(self.canvas)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mousewheel scrolling (Windows)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        # Make inner frame match canvas width so labels wrap nicely
        self.canvas.itemconfigure(self._window, width=event.width)

    def _on_mousewheel(self, event):
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass


class ReportsFrame(ttk.Frame):
    def __init__(self, parent, session=None):
        super().__init__(parent)
        self.parent = parent
        self.session = session
        self.create_widgets()
        
    def create_widgets(self):
        # Overall layout
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # User selection section (end-user mode uses logged-in session)
        user_frame = ttk.LabelFrame(self, text="Report Settings")
        user_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        self.user_var = tk.StringVar()

        if self.session is None:
            # Developer / fallback behavior (keeps old functionality if used standalone)
            users = self.get_users()
            user_label = ttk.Label(user_frame, text="Select User:")
            user_label.grid(row=0, column=0, padx=5, pady=5)

            self.user_combo = ttk.Combobox(
                user_frame,
                textvariable=self.user_var,
                values=users,
                state="readonly",
                width=30,
            )
            self.user_combo.grid(row=0, column=1, padx=5, pady=5)

            refresh_btn = ttk.Button(
                user_frame,
                text="Refresh Users",
                command=lambda: self.refresh_users(show_message=True),
            )
            refresh_btn.grid(row=0, column=2, padx=5, pady=5)
        else:
            # End-user behavior (no user switching)
            self.user_var.set(f"{self.session.user_id} - {self.session.full_name}")
            ttk.Label(user_frame, text="User:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            ttk.Label(user_frame, text=f"{self.session.full_name} ({self.session.email})").grid(
                row=0, column=1, padx=5, pady=5, sticky="w"
            )
        
        # Date range
        self.date_from_var = tk.StringVar(value=datetime.now().replace(month=1, day=1).strftime("%Y-%m-%d"))
        self.date_to_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        
        from_label = ttk.Label(user_frame, text="From Date (YYYY-MM-DD):")
        from_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        from_entry = ttk.Entry(user_frame, textvariable=self.date_from_var, width=15)
        from_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        to_label = ttk.Label(user_frame, text="To Date (YYYY-MM-DD):")
        to_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        to_entry = ttk.Entry(user_frame, textvariable=self.date_to_var, width=15)
        to_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        # Generate report button
        generate_btn = ttk.Button(user_frame, text="Generate Report", command=self.generate_report)
        generate_btn.grid(row=3, column=0, columnspan=2, padx=5, pady=10)
        
        # Report display area with tabs
        self.report_notebook = ttk.Notebook(self)
        self.report_notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # Carbon report tab (scrollable)
        self.summary_tab = ttk.Frame(self.report_notebook)
        self.report_notebook.add(self.summary_tab, text="Carbon Report")
        
        # Charts tab
        self.charts_tab = ttk.Frame(self.report_notebook)
        self.report_notebook.add(self.charts_tab, text="Charts")

        # Trends tab (time series)
        self.trends_tab = ttk.Frame(self.report_notebook)
        self.report_notebook.add(self.trends_tab, text="Trends")
        
        # Details tab
        self.details_tab = ttk.Frame(self.report_notebook)
        self.report_notebook.add(self.details_tab, text="Details")
        
        # Default message in summary tab
        self._summary_scroll = ScrollableFrame(self.summary_tab)
        self._summary_scroll.pack(fill=tk.BOTH, expand=True)
        self.summary_label = ttk.Label(
            self._summary_scroll.inner,
            text="Click 'Generate Report' to view your carbon emission summary.",
            font=('Arial', 12)
        )
        self.summary_label.pack(padx=20, pady=30, anchor="w")
    
    def get_users(self):
        """Get list of users for dropdown"""
        try:
            conn = sqlite3.connect('carbon_emission.db')
            cursor = conn.cursor()
            cursor.execute("SELECT User_ID, Full_Name FROM User_Profile")
            users = cursor.fetchall()
            conn.close()
            return [f"{user[0]} - {user[1]}" for user in users]
        except Exception as e:
            messagebox.showerror("Database Error", f"Error fetching users: {str(e)}")
            return []
    
    def extract_user_id(self, user_string):
        """Extract user ID from dropdown selection string"""
        if not user_string:
            return None
        try:
            return int(user_string.split(" - ")[0])
        except:
            return None
    
    def generate_report(self):
        """Generate carbon emission report for selected user"""
        if self.session is not None:
            user_id = self.session.user_id
            user_string = f"{self.session.user_id} - {self.session.full_name}"
        else:
            user_string = self.user_var.get()
            user_id = self.extract_user_id(user_string)
        
        if not user_id:
            messagebox.showwarning("Selection Error", "Please select a user")
            return
        
        # Get date range
        date_from = self.date_from_var.get()
        date_to = self.date_to_var.get()
        
        try:
            # Validate date format
            datetime.strptime(date_from, "%Y-%m-%d")
            datetime.strptime(date_to, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Date Error", "Please enter valid dates in YYYY-MM-DD format")
            return
        
        try:
            # Get user carbon emission data
            data = self.get_user_emission_data(user_id, date_from, date_to)
            
            # Clear existing report content
            self.clear_report_tabs()
            
            # Generate report content
            self.generate_summary_tab(data, user_string)
            self.generate_charts_tab(data)
            self.generate_trends_tab(data)
            self.generate_details_tab(data)
            
            # Switch to summary tab
            self.report_notebook.select(0)
            
        except Exception as e:
            messagebox.showerror("Report Error", f"Error generating report: {str(e)}")
    
    def get_user_emission_data(self, user_id, date_from, date_to):
        """Get carbon emission data for the user"""
        conn = sqlite3.connect('carbon_emission.db')
        
        # Get user profile info
        df_user = pd.read_sql_query(
            "SELECT * FROM User_Profile WHERE User_ID = ?", 
            conn, 
            params=(user_id,)
        )
        
        # Get transportation data
        df_transport = pd.read_sql_query(
            """
            SELECT t.*, ef.Emission_Per_Unit, 
                   (t.Distance_KM * ef.Emission_Per_Unit) as Emission_Amount
            FROM Transportation t
            LEFT JOIN Emission_Factor ef ON t.Vehicle_Type = ef.Source_Type
            WHERE t.User_ID = ? AND t.Date BETWEEN ? AND ?
            """, 
            conn, 
            params=(user_id, date_from, date_to)
        )
        
        # Get energy consumption data
        df_energy = pd.read_sql_query(
            """
            SELECT ec.*, ef.Emission_Per_Unit,
                   (ec.Consumption_KWH * ef.Emission_Per_Unit) as Emission_Amount
            FROM Energy_Consumption ec
            LEFT JOIN Emission_Factor ef ON ec.Energy_Source = ef.Source_Type
            WHERE ec.User_ID = ? AND ec.Date BETWEEN ? AND ?
            """, 
            conn, 
            params=(user_id, date_from, date_to)
        )
        
        # Get waste management data (per waste type)
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
        
        # Get industrial activity data
        df_industrial = pd.read_sql_query(
            """
            SELECT * FROM Industrial_Activity
            WHERE User_ID = ? AND Date BETWEEN ? AND ?
            """, 
            conn, 
            params=(user_id, date_from, date_to)
        )
        
        # Get carbon offset data
        df_offset = pd.read_sql_query(
            """
            SELECT * FROM Carbon_Offset
            WHERE User_ID = ? AND Date BETWEEN ? AND ?
            """, 
            conn, 
            params=(user_id, date_from, date_to)
        )
        
        # Calculate summary totals
        transport_emissions = df_transport['Emission_Amount'].sum() if not df_transport.empty else 0
        energy_emissions = df_energy['Emission_Amount'].sum() if not df_energy.empty else 0
        waste_emissions = df_waste['Emission_Amount'].sum() if not df_waste.empty else 0
        industrial_emissions = df_industrial['Emission_Produced'].sum() if not df_industrial.empty else 0
        total_emissions = transport_emissions + energy_emissions + waste_emissions + industrial_emissions
        total_offset = df_offset['Offset_Amount'].sum() if not df_offset.empty else 0
        net_emissions = total_emissions - total_offset
        
        conn.close()
        
        # Return all data in a dictionary
        return {
            'user': df_user,
            'transport': df_transport,
            'energy': df_energy,
            'waste': df_waste,
            'industrial': df_industrial,
            'offset': df_offset,
            'summary': {
                'transport_emissions': transport_emissions,
                'energy_emissions': energy_emissions,
                'waste_emissions': waste_emissions,
                'industrial_emissions': industrial_emissions,
                'total_emissions': total_emissions,
                'total_offset': total_offset,
                'net_emissions': net_emissions
            }
        }
    
    def clear_report_tabs(self):
        """Clear all content from report tabs"""
        # Clear summary scroll content
        for widget in self._summary_scroll.inner.winfo_children():
            widget.destroy()
            
        for widget in self.charts_tab.winfo_children():
            widget.destroy()
            
        for widget in self.details_tab.winfo_children():
            widget.destroy()
    
    def generate_summary_tab(self, data, user_string):
        """Generate summary tab content"""
        summary = data['summary']
        user_data = data['user']
        
        if user_data.empty:
            ttk.Label(self._summary_scroll.inner, text="No user data found", font=('Arial', 12)).pack(pady=20)
            return
            
        # Create summary frame
        summary_frame = ttk.Frame(self._summary_scroll.inner)
        summary_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # User information
        user_info = ttk.LabelFrame(summary_frame, text="User Information")
        user_info.pack(fill=tk.X, pady=10)
        
        ttk.Label(user_info, text=f"Name: {user_data.iloc[0]['Full_Name']}").pack(anchor='w', padx=10, pady=2)
        ttk.Label(user_info, text=f"Email: {user_data.iloc[0]['Email']}").pack(anchor='w', padx=10, pady=2)
        ttk.Label(user_info, text=f"Location: {user_data.iloc[0]['Location']}").pack(anchor='w', padx=10, pady=2)
        
        # Date range
        date_info = ttk.LabelFrame(summary_frame, text="Report Period")
        date_info.pack(fill=tk.X, pady=10)
        
        ttk.Label(date_info, text=f"From: {self.date_from_var.get()} To: {self.date_to_var.get()}").pack(anchor='w', padx=10, pady=5)
        
        # Emissions summary
        emissions_info = ttk.LabelFrame(summary_frame, text="Carbon Emissions Summary")
        emissions_info.pack(fill=tk.X, pady=10)
        
        # Create a grid for emissions data
        ttk.Label(emissions_info, text="Emission Source", font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=10, pady=5, sticky='w')
        ttk.Label(emissions_info, text="Amount (kg CO2e)", font=('Arial', 10, 'bold')).grid(row=0, column=1, padx=10, pady=5, sticky='e')
        
        ttk.Label(emissions_info, text="Transportation").grid(row=1, column=0, padx=10, pady=2, sticky='w')
        ttk.Label(emissions_info, text=f"{summary['transport_emissions']:.2f}").grid(row=1, column=1, padx=10, pady=2, sticky='e')
        
        ttk.Label(emissions_info, text="Energy Consumption").grid(row=2, column=0, padx=10, pady=2, sticky='w')
        ttk.Label(emissions_info, text=f"{summary['energy_emissions']:.2f}").grid(row=2, column=1, padx=10, pady=2, sticky='e')
        
        ttk.Label(emissions_info, text="Waste Management").grid(row=3, column=0, padx=10, pady=2, sticky='w')
        ttk.Label(emissions_info, text=f"{summary['waste_emissions']:.2f}").grid(row=3, column=1, padx=10, pady=2, sticky='e')
        
        ttk.Label(emissions_info, text="Industrial Activity").grid(row=4, column=0, padx=10, pady=2, sticky='w')
        ttk.Label(emissions_info, text=f"{summary['industrial_emissions']:.2f}").grid(row=4, column=1, padx=10, pady=2, sticky='e')
        
        ttk.Separator(emissions_info, orient='horizontal').grid(row=5, column=0, columnspan=2, sticky='ew', padx=10, pady=5)
        
        ttk.Label(emissions_info, text="Total Emissions", font=('Arial', 10, 'bold')).grid(row=6, column=0, padx=10, pady=2, sticky='w')
        ttk.Label(emissions_info, text=f"{summary['total_emissions']:.2f}", font=('Arial', 10, 'bold')).grid(row=6, column=1, padx=10, pady=2, sticky='e')
        
        ttk.Label(emissions_info, text="Carbon Offset").grid(row=7, column=0, padx=10, pady=2, sticky='w')
        ttk.Label(emissions_info, text=f"{summary['total_offset']:.2f}").grid(row=7, column=1, padx=10, pady=2, sticky='e')
        
        ttk.Separator(emissions_info, orient='horizontal').grid(row=8, column=0, columnspan=2, sticky='ew', padx=10, pady=5)
        
        ttk.Label(emissions_info, text="Net Emissions", font=('Arial', 11, 'bold')).grid(row=9, column=0, padx=10, pady=5, sticky='w')
        ttk.Label(emissions_info, text=f"{summary['net_emissions']:.2f}", font=('Arial', 11, 'bold')).grid(row=9, column=1, padx=10, pady=5, sticky='e')

        # Insights section (plain-language analysis for end users)
        insights = ttk.LabelFrame(summary_frame, text="Key Insights")
        insights.pack(fill=tk.X, pady=10)

        emissions_breakdown = {
            "Transportation": summary["transport_emissions"],
            "Energy Consumption": summary["energy_emissions"],
            "Waste Management": summary["waste_emissions"],
            "Industrial Activity": summary["industrial_emissions"],
        }
        highest_category = max(emissions_breakdown, key=emissions_breakdown.get)
        total = summary["total_emissions"]
        highest_value = emissions_breakdown[highest_category]
        share = (highest_value / total * 100.0) if total > 0 else 0.0

        ttk.Label(
            insights,
            text=f"Most of your emissions come from {highest_category} "
                 f"({highest_value:.1f} kg CO2e, about {share:.1f}% of your total).",
            wraplength=600,
            justify="left",
        ).pack(anchor="w", padx=10, pady=2)

        if summary["net_emissions"] > 0:
            ttk.Label(
                insights,
                text=f"Your net emissions for this period are {summary['net_emissions']:.1f} kg CO2e "
                     f"after accounting for offsets.",
                wraplength=600,
                justify="left",
            ).pack(anchor="w", padx=10, pady=2)
        else:
            ttk.Label(
                insights,
                text="Great job — your offsets are equal to or higher than your total emissions "
                     "for this period.",
                wraplength=600,
                justify="left",
            ).pack(anchor="w", padx=10, pady=2)

        # Recommendations section
        recommendations = ttk.LabelFrame(summary_frame, text="Recommendations")
        recommendations.pack(fill=tk.X, pady=10)

        # Generate recommendations based on emissions
        recommendations_text = self.generate_recommendations(summary)
        recommendation_label = ttk.Label(recommendations, text=recommendations_text, wraplength=750, justify='left')
        recommendation_label.pack(anchor='w', padx=10, pady=10)
    
    def generate_recommendations(self, summary):
        """Generate recommendations based on emissions data"""
        recommendations = []
        
        # Check which category has highest emissions
        emissions = {
            'Transportation': summary['transport_emissions'],
            'Energy Consumption': summary['energy_emissions'],
            'Waste Management': summary['waste_emissions'],
            'Industrial Activity': summary['industrial_emissions']
        }
        
        highest_category = max(emissions, key=emissions.get)
        
        # General recommendation
        recommendations.append(f"Your highest emissions come from {highest_category}. Focus on reducing this area first.")
        
        # Category-specific recommendations
        if highest_category == 'Transportation':
            recommendations.append("Consider using public transportation, carpooling, or switching to electric vehicles.")
            recommendations.append("Reduce unnecessary travel and combine trips when possible.")
            
        elif highest_category == 'Energy Consumption':
            recommendations.append("Switch to energy-efficient appliances and LED lighting.")
            recommendations.append("Consider renewable energy sources like solar panels.")
            recommendations.append("Improve insulation to reduce heating and cooling needs.")
            
        elif highest_category == 'Waste Management':
            recommendations.append("Practice recycling and composting to reduce landfill waste.")
            recommendations.append("Choose products with minimal packaging.")
            recommendations.append("Donate or repurpose items instead of disposing them.")
            
        elif highest_category == 'Industrial Activity':
            recommendations.append("Implement more efficient industrial processes.")
            recommendations.append("Consider cleaner energy sources for industrial operations.")
            recommendations.append("Invest in carbon capture technologies.")
        
        # Carbon offset recommendations
        if summary['total_offset'] < summary['total_emissions'] * 0.1:
            recommendations.append("Consider increasing your carbon offset contributions through tree planting or renewable energy credits.")
        
        return "\n• ".join([""] + recommendations)
    
    def generate_charts_tab(self, data):
        """Generate charts for visual representation"""
        summary = data['summary']

        # Split charts into separate tabs so nothing is cramped
        charts_notebook = ttk.Notebook(self.charts_tab)
        charts_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tab_breakdown = ttk.Frame(charts_notebook)
        tab_offset = ttk.Frame(charts_notebook)
        tab_transport = ttk.Frame(charts_notebook)
        tab_energy = ttk.Frame(charts_notebook)

        charts_notebook.add(tab_breakdown, text="Breakdown")
        charts_notebook.add(tab_offset, text="Offset")
        charts_notebook.add(tab_transport, text="Transport")
        charts_notebook.add(tab_energy, text="Energy")

        # --- Breakdown (Pie) ---
        fig1 = plt.Figure(figsize=(7.5, 5.2), dpi=100)
        ax1 = fig1.add_subplot(111)
        emissions = [
            summary['transport_emissions'],
            summary['energy_emissions'],
            summary['waste_emissions'],
            summary['industrial_emissions']
        ]
        labels = ['Transportation', 'Energy', 'Waste', 'Industrial']

        filtered_emissions = []
        filtered_labels = []
        for e, l in zip(emissions, labels):
            if e > 0:
                filtered_emissions.append(e)
                filtered_labels.append(l)

        if filtered_emissions:
            ax1.pie(filtered_emissions, labels=filtered_labels, autopct='%1.1f%%')
            ax1.set_title('Emissions by Source')
        else:
            ax1.text(0.5, 0.5, 'No emissions data available', ha='center', va='center')
            ax1.set_title('Emissions by Source')
        fig1.tight_layout()
        canvas1 = FigureCanvasTkAgg(fig1, master=tab_breakdown)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- Offset (Bar) ---
        fig2 = plt.Figure(figsize=(7.5, 5.2), dpi=100)
        ax2 = fig2.add_subplot(111)
        categories = ['Total Emissions', 'Carbon Offset', 'Net Emissions']
        values = [summary['total_emissions'], summary['total_offset'], summary['net_emissions']]
        bars = ax2.bar(categories, values, color=['red', 'green', 'blue'])
        ax2.set_title('Emissions vs Offset')
        ax2.tick_params(axis='x', rotation=12)
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height, f'{height:.1f}', ha='center', va='bottom')
        fig2.tight_layout()
        canvas2 = FigureCanvasTkAgg(fig2, master=tab_offset)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- Transport ---
        fig3 = plt.Figure(figsize=(7.5, 5.2), dpi=100)
        ax3 = fig3.add_subplot(111)
        if not data['transport'].empty:
            transport_by_type = data['transport'].groupby('Vehicle_Type')['Distance_KM'].sum().sort_values(ascending=False)
            transport_by_type.plot(kind='bar', ax=ax3)
            ax3.set_title('Transportation by Vehicle Type')
            ax3.set_ylabel('Distance (km)')
            ax3.tick_params(axis='x', rotation=20)
        else:
            ax3.text(0.5, 0.5, 'No transportation data available', ha='center', va='center')
            ax3.set_title('Transportation by Vehicle Type')
        fig3.tight_layout()
        canvas3 = FigureCanvasTkAgg(fig3, master=tab_transport)
        canvas3.draw()
        canvas3.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- Energy ---
        fig4 = plt.Figure(figsize=(7.5, 5.2), dpi=100)
        ax4 = fig4.add_subplot(111)
        if not data['energy'].empty:
            energy_by_source = data['energy'].groupby('Energy_Source')['Consumption_KWH'].sum().sort_values(ascending=False)
            energy_by_source.plot(kind='bar', ax=ax4)
            ax4.set_title('Energy by Source')
            ax4.set_ylabel('Consumption (kWh)')
            ax4.tick_params(axis='x', rotation=20)
        else:
            ax4.text(0.5, 0.5, 'No energy data available', ha='center', va='center')
            ax4.set_title('Energy by Source')
        fig4.tight_layout()
        canvas4 = FigureCanvasTkAgg(fig4, master=tab_energy)
        canvas4.draw()
        canvas4.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def generate_trends_tab(self, data):
        """Generate time-series charts (monthly emissions/net) if dates exist."""
        for widget in self.trends_tab.winfo_children():
            widget.destroy()

        trends_frame = ttk.Frame(self.trends_tab)
        trends_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Build monthly totals by category from available data
        def to_month_series(df, date_col, value_col):
            if df is None or df.empty or date_col not in df.columns or value_col not in df.columns:
                return None
            tmp = df[[date_col, value_col]].copy()
            tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
            tmp = tmp.dropna(subset=[date_col])
            if tmp.empty:
                return None
            tmp["Month"] = tmp[date_col].dt.to_period("M").dt.to_timestamp()
            return tmp.groupby("Month")[value_col].sum().sort_index()

        transport = to_month_series(data.get("transport"), "Date", "Emission_Amount")
        energy = to_month_series(data.get("energy"), "Date", "Emission_Amount")
        waste = to_month_series(data.get("waste"), "Date", "Emission_Amount")
        industrial = to_month_series(data.get("industrial"), "Date", "Emission_Produced")
        offset = to_month_series(data.get("offset"), "Date", "Offset_Amount")

        # Merge months
        series_list = [s for s in [transport, energy, waste, industrial, offset] if s is not None]
        if not series_list:
            ttk.Label(trends_frame, text="No dated data available to build trends.").pack(pady=20)
            return

        all_months = pd.Index([])
        for s in series_list:
            all_months = all_months.union(s.index)
        all_months = all_months.sort_values()

        def reindex(s):
            return s.reindex(all_months, fill_value=0) if s is not None else pd.Series(0, index=all_months)

        t = reindex(transport)
        e = reindex(energy)
        w = reindex(waste)
        i = reindex(industrial)
        o = reindex(offset)

        total = t + e + w + i
        net = total - o

        fig = plt.Figure(figsize=(10, 5), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(all_months, total.values, marker="o", label="Total emissions")
        ax.plot(all_months, net.values, marker="o", label="Net emissions (after offset)")
        ax.set_title("Monthly Emissions Trend")
        ax.set_ylabel("kg CO2e")
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.autofmt_xdate(rotation=30)

        canvas = FigureCanvasTkAgg(fig, master=trends_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def generate_details_tab(self, data):
        """Generate detailed data tables"""
        # Create notebook for data categories
        details_notebook = ttk.Notebook(self.details_tab)
        details_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs for each data category
        transport_tab = ttk.Frame(details_notebook)
        energy_tab = ttk.Frame(details_notebook)
        waste_tab = ttk.Frame(details_notebook)
        industrial_tab = ttk.Frame(details_notebook)
        offset_tab = ttk.Frame(details_notebook)
        
        details_notebook.add(transport_tab, text="Transportation")
        details_notebook.add(energy_tab, text="Energy")
        details_notebook.add(waste_tab, text="Waste")
        details_notebook.add(industrial_tab, text="Industrial")
        details_notebook.add(offset_tab, text="Carbon Offset")
        
        # Add data tables to each tab
        self.create_data_table(transport_tab, data['transport'], ['Transport_ID', 'Vehicle_Type', 'Distance_KM', 'Date', 'Emission_Amount'])
        self.create_data_table(energy_tab, data['energy'], ['Energy_ID', 'Energy_Source', 'Consumption_KWH', 'Date', 'Emission_Amount'])
        self.create_data_table(waste_tab, data['waste'], ['Waste_ID', 'Waste_Type', 'Waste_Weight_KG', 'Date', 'Emission_Amount'])
        self.create_data_table(industrial_tab, data['industrial'], ['Industry_ID', 'Activity_Type', 'Emission_Produced', 'Date'])
        self.create_data_table(offset_tab, data['offset'], ['Offset_ID', 'Offset_Type', 'Offset_Amount', 'Date'])
    
    def create_data_table(self, parent, df, columns):
        """Create a treeview to display dataframe"""
        if df.empty:
            ttk.Label(parent, text="No data available for this category").pack(pady=20)
            return
        
        # Keep only columns we want to display
        display_columns = [col for col in columns if col in df.columns]
        
        # Create frame with scrollbars
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbars
        vsb = ttk.Scrollbar(frame, orient="vertical")
        hsb = ttk.Scrollbar(frame, orient="horizontal")
        
        # Treeview
        tree = ttk.Treeview(frame, columns=display_columns, show='headings',
                           yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Configure scrollbars
        vsb.config(command=tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        hsb.config(command=tree.xview)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        tree.pack(fill=tk.BOTH, expand=True)
        
        # Set column headings and formats
        for col in display_columns:
            tree.heading(col, text=col.replace('_', ' '))
            
            # Adjust column width based on content
            if 'Date' in col:
                tree.column(col, width=100, anchor='center')
            elif 'ID' in col:
                tree.column(col, width=80, anchor='center')
            elif any(x in col for x in ['Amount', 'KWH', 'KM', 'KG']):
                tree.column(col, width=120, anchor='e')
            else:
                tree.column(col, width=150, anchor='w')
        
        # Add data rows
        for i, row in df.iterrows():
            values = []
            for col in display_columns:
                val = row[col] if col in row else ""
                
                # Format numeric values
                if isinstance(val, (int, float)):
                    if col in ['Distance_KM', 'Consumption_KWH', 'Waste_Weight_KG', 'Emission_Amount', 'Emission_Produced', 'Offset_Amount']:
                        val = f"{val:.2f}"
                
                values.append(val)
            
            tree.insert("", tk.END, values=values)
    
    def refresh_users(self, show_message=False):
        """Refresh the user dropdown list"""
        users = self.get_users()
        self.user_combo['values'] = users
        if show_message:
            messagebox.showinfo("Refresh Complete", "User list has been refreshed.")