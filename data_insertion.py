import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime

class DataInsertionFrame(ttk.Frame):
    def __init__(self, parent, session=None):
        super().__init__(parent)
        self.parent = parent
        self.session = session
        self.create_widgets()
        
    def create_widgets(self):
        # Category selection
        category_frame = ttk.LabelFrame(self, text="Select Data Category")
        category_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.category_var = tk.StringVar()

        categories = self.get_categories_for_session()
        
        self.category_combo = ttk.Combobox(
            category_frame, 
            textvariable=self.category_var, 
            values=categories,
            state="readonly",
            width=30
        )
        self.category_combo.pack(padx=10, pady=5)
        self.category_combo.bind("<<ComboboxSelected>>", self.on_category_select)
        
        # Form frame (will be populated dynamically)
        self.form_frame = ttk.LabelFrame(self, text="Data Entry Form")
        self.form_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Default message
        self.default_label = ttk.Label(
            self.form_frame, 
            text="Please select a category to enter data", 
            font=('Arial', 12)
        )
        self.default_label.pack(padx=20, pady=30)
        
        # Form elements will be created dynamically based on selected category
        self.form_elements = {}

    def get_categories_for_session(self):
        # End-user: categories depend on the chosen mode at login
        if self.session is None:
            return [
                "User Profile",
                "Transportation",
                "Energy Consumption",
                "Waste Management",
                "Industrial Activity",
                "Carbon Offset",
            ]

        if getattr(self.session, "mode", "Individual") == "Industry":
            return [
                "Industrial Activity",
                "Energy Consumption",
                "Transportation",
                "Carbon Offset",
            ]

        # Individual
        return [
            "Transportation",
            "Energy Consumption",
            "Waste Management",
            "Carbon Offset",
        ]
        
    def on_category_select(self, event=None):
        # Clear the form frame
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        
        # Reset form elements dictionary
        self.form_elements = {}
        
        # Get selected category
        category = self.category_var.get()
        
        # Create appropriate form based on category
        if category == "User Profile":
            self.create_user_form()
        elif category == "Transportation":
            self.create_transportation_form()
        elif category == "Energy Consumption":
            self.create_energy_form()
        elif category == "Waste Management":
            self.create_waste_form()
        elif category == "Industrial Activity":
            self.create_industrial_form()
        elif category == "Carbon Offset":
            self.create_offset_form()
    
    def create_user_form(self):
        # Create form for User Profile
        ttk.Label(self.form_frame, text="Full Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        name_entry = ttk.Entry(self.form_frame, width=30)
        name_entry.grid(row=0, column=1, padx=5, pady=5)
        self.form_elements["Full_Name"] = name_entry
        
        ttk.Label(self.form_frame, text="Email:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        email_entry = ttk.Entry(self.form_frame, width=30)
        email_entry.grid(row=1, column=1, padx=5, pady=5)
        self.form_elements["Email"] = email_entry
        
        ttk.Label(self.form_frame, text="Location:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        location_entry = ttk.Entry(self.form_frame, width=30)
        location_entry.grid(row=2, column=1, padx=5, pady=5)
        self.form_elements["Location"] = location_entry
        
        submit_btn = ttk.Button(self.form_frame, text="Submit", command=self.insert_user_data)
        submit_btn.grid(row=3, column=0, columnspan=2, pady=10)
    
    def create_transportation_form(self):
        row0 = 0
        if self.session is None:
            # Get user IDs for dropdown
            user_ids = self.get_user_ids()

            ttk.Label(self.form_frame, text="User:").grid(row=row0, column=0, padx=5, pady=5, sticky="w")
            user_combo = ttk.Combobox(self.form_frame, values=user_ids, state="readonly", width=28)
            user_combo.grid(row=row0, column=1, padx=5, pady=5)
            self.form_elements["User_ID"] = user_combo
            row0 += 1
        else:
            ttk.Label(self.form_frame, text="User:").grid(row=row0, column=0, padx=5, pady=5, sticky="w")
            ttk.Label(self.form_frame, text=f"{self.session.full_name} ({self.session.email})").grid(
                row=row0, column=1, padx=5, pady=5, sticky="w"
            )
            row0 += 1
        
        ttk.Label(self.form_frame, text="Vehicle Type:").grid(row=row0, column=0, padx=5, pady=5, sticky="w")
        vehicle_types = ["Car", "Bus", "Train", "Airplane", "Bicycle", "Electric Car", "Motorcycle", "Walking"]
        vehicle_combo = ttk.Combobox(self.form_frame, values=vehicle_types, width=28)
        vehicle_combo.grid(row=row0, column=1, padx=5, pady=5)
        self.form_elements["Vehicle_Type"] = vehicle_combo
        
        ttk.Label(self.form_frame, text="Distance (KM):").grid(row=row0 + 1, column=0, padx=5, pady=5, sticky="w")
        distance_entry = ttk.Entry(self.form_frame, width=30)
        distance_entry.grid(row=row0 + 1, column=1, padx=5, pady=5)
        self.form_elements["Distance_KM"] = distance_entry
        
        ttk.Label(self.form_frame, text="Date (YYYY-MM-DD):").grid(row=row0 + 2, column=0, padx=5, pady=5, sticky="w")
        date_entry = ttk.Entry(self.form_frame, width=30)
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_entry.grid(row=row0 + 2, column=1, padx=5, pady=5)
        self.form_elements["Date"] = date_entry
        
        submit_btn = ttk.Button(self.form_frame, text="Submit", command=self.insert_transportation_data)
        submit_btn.grid(row=row0 + 3, column=0, columnspan=2, pady=10)
    
    def create_energy_form(self):
        row0 = 0
        if self.session is None:
            user_ids = self.get_user_ids()

            ttk.Label(self.form_frame, text="User:").grid(row=row0, column=0, padx=5, pady=5, sticky="w")
            user_combo = ttk.Combobox(self.form_frame, values=user_ids, state="readonly", width=28)
            user_combo.grid(row=row0, column=1, padx=5, pady=5)
            self.form_elements["User_ID"] = user_combo
            row0 += 1
        else:
            ttk.Label(self.form_frame, text="User:").grid(row=row0, column=0, padx=5, pady=5, sticky="w")
            ttk.Label(self.form_frame, text=f"{self.session.full_name} ({self.session.email})").grid(
                row=row0, column=1, padx=5, pady=5, sticky="w"
            )
            row0 += 1
        
        ttk.Label(self.form_frame, text="Energy Source:").grid(row=row0, column=0, padx=5, pady=5, sticky="w")
        energy_sources = ["Electricity", "Natural Gas", "Solar", "Wind", "Coal", "Biomass", "Geothermal"]
        energy_combo = ttk.Combobox(self.form_frame, values=energy_sources, width=28)
        energy_combo.grid(row=row0, column=1, padx=5, pady=5)
        self.form_elements["Energy_Source"] = energy_combo
        
        ttk.Label(self.form_frame, text="Consumption (KWH):").grid(row=row0 + 1, column=0, padx=5, pady=5, sticky="w")
        consumption_entry = ttk.Entry(self.form_frame, width=30)
        consumption_entry.grid(row=row0 + 1, column=1, padx=5, pady=5)
        self.form_elements["Consumption_KWH"] = consumption_entry
        
        ttk.Label(self.form_frame, text="Date (YYYY-MM-DD):").grid(row=row0 + 2, column=0, padx=5, pady=5, sticky="w")
        date_entry = ttk.Entry(self.form_frame, width=30)
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_entry.grid(row=row0 + 2, column=1, padx=5, pady=5)
        self.form_elements["Date"] = date_entry
        
        submit_btn = ttk.Button(self.form_frame, text="Submit", command=self.insert_energy_data)
        submit_btn.grid(row=row0 + 3, column=0, columnspan=2, pady=10)
    
    def create_waste_form(self):
        row0 = 0
        if self.session is None:
            user_ids = self.get_user_ids()

            ttk.Label(self.form_frame, text="User:").grid(row=row0, column=0, padx=5, pady=5, sticky="w")
            user_combo = ttk.Combobox(self.form_frame, values=user_ids, state="readonly", width=28)
            user_combo.grid(row=row0, column=1, padx=5, pady=5)
            self.form_elements["User_ID"] = user_combo
            row0 += 1
        else:
            ttk.Label(self.form_frame, text="User:").grid(row=row0, column=0, padx=5, pady=5, sticky="w")
            ttk.Label(self.form_frame, text=f"{self.session.full_name} ({self.session.email})").grid(
                row=row0, column=1, padx=5, pady=5, sticky="w"
            )
            row0 += 1
        
        ttk.Label(self.form_frame, text="Waste Type:").grid(row=row0, column=0, padx=5, pady=5, sticky="w")
        waste_types = ["Plastic", "Paper", "Glass", "Metal", "Organic", "Electronic", "Hazardous"]
        waste_combo = ttk.Combobox(self.form_frame, values=waste_types, width=28)
        waste_combo.grid(row=row0, column=1, padx=5, pady=5)
        self.form_elements["Waste_Type"] = waste_combo
        
        ttk.Label(self.form_frame, text="Weight (KG):").grid(row=row0 + 1, column=0, padx=5, pady=5, sticky="w")
        weight_entry = ttk.Entry(self.form_frame, width=30)
        weight_entry.grid(row=row0 + 1, column=1, padx=5, pady=5)
        self.form_elements["Waste_Weight_KG"] = weight_entry
        
        ttk.Label(self.form_frame, text="Date (YYYY-MM-DD):").grid(row=row0 + 2, column=0, padx=5, pady=5, sticky="w")
        date_entry = ttk.Entry(self.form_frame, width=30)
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_entry.grid(row=row0 + 2, column=1, padx=5, pady=5)
        self.form_elements["Date"] = date_entry
        
        submit_btn = ttk.Button(self.form_frame, text="Submit", command=self.insert_waste_data)
        submit_btn.grid(row=row0 + 3, column=0, columnspan=2, pady=10)
    
    def create_industrial_form(self):
        row0 = 0
        if self.session is None:
            user_ids = self.get_user_ids()

            ttk.Label(self.form_frame, text="User:").grid(row=row0, column=0, padx=5, pady=5, sticky="w")
            user_combo = ttk.Combobox(self.form_frame, values=user_ids, state="readonly", width=28)
            user_combo.grid(row=row0, column=1, padx=5, pady=5)
            self.form_elements["User_ID"] = user_combo
            row0 += 1
        else:
            ttk.Label(self.form_frame, text="User:").grid(row=row0, column=0, padx=5, pady=5, sticky="w")
            ttk.Label(self.form_frame, text=f"{self.session.full_name} ({self.session.email})").grid(
                row=row0, column=1, padx=5, pady=5, sticky="w"
            )
            row0 += 1
        
        ttk.Label(self.form_frame, text="Activity Type:").grid(row=row0, column=0, padx=5, pady=5, sticky="w")
        activity_types = ["Manufacturing", "Construction", "Chemical Processing", "Food Processing", 
                         "Textile Production", "Mining", "Agriculture"]
        activity_combo = ttk.Combobox(self.form_frame, values=activity_types, width=28)
        activity_combo.grid(row=row0, column=1, padx=5, pady=5)
        self.form_elements["Activity_Type"] = activity_combo
        
        ttk.Label(self.form_frame, text="Emission Produced:").grid(row=row0 + 1, column=0, padx=5, pady=5, sticky="w")
        emission_entry = ttk.Entry(self.form_frame, width=30)
        emission_entry.grid(row=row0 + 1, column=1, padx=5, pady=5)
        self.form_elements["Emission_Produced"] = emission_entry
        
        ttk.Label(self.form_frame, text="Date (YYYY-MM-DD):").grid(row=row0 + 2, column=0, padx=5, pady=5, sticky="w")
        date_entry = ttk.Entry(self.form_frame, width=30)
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_entry.grid(row=row0 + 2, column=1, padx=5, pady=5)
        self.form_elements["Date"] = date_entry
        
        submit_btn = ttk.Button(self.form_frame, text="Submit", command=self.insert_industrial_data)
        submit_btn.grid(row=row0 + 3, column=0, columnspan=2, pady=10)
    
    def create_offset_form(self):
        row0 = 0
        if self.session is None:
            user_ids = self.get_user_ids()

            ttk.Label(self.form_frame, text="User:").grid(row=row0, column=0, padx=5, pady=5, sticky="w")
            user_combo = ttk.Combobox(self.form_frame, values=user_ids, state="readonly", width=28)
            user_combo.grid(row=row0, column=1, padx=5, pady=5)
            self.form_elements["User_ID"] = user_combo
            row0 += 1
        else:
            ttk.Label(self.form_frame, text="User:").grid(row=row0, column=0, padx=5, pady=5, sticky="w")
            ttk.Label(self.form_frame, text=f"{self.session.full_name} ({self.session.email})").grid(
                row=row0, column=1, padx=5, pady=5, sticky="w"
            )
            row0 += 1
        
        ttk.Label(self.form_frame, text="Offset Type:").grid(row=row0, column=0, padx=5, pady=5, sticky="w")
        offset_types = ["Tree Planting", "Renewable Energy Credits", "Methane Capture", 
                        "Carbon Sequestration", "Energy Efficiency"]
        offset_combo = ttk.Combobox(self.form_frame, values=offset_types, width=28)
        offset_combo.grid(row=row0, column=1, padx=5, pady=5)
        self.form_elements["Offset_Type"] = offset_combo
        
        ttk.Label(self.form_frame, text="Offset Amount:").grid(row=row0 + 1, column=0, padx=5, pady=5, sticky="w")
        amount_entry = ttk.Entry(self.form_frame, width=30)
        amount_entry.grid(row=row0 + 1, column=1, padx=5, pady=5)
        self.form_elements["Offset_Amount"] = amount_entry
        
        ttk.Label(self.form_frame, text="Date (YYYY-MM-DD):").grid(row=row0 + 2, column=0, padx=5, pady=5, sticky="w")
        date_entry = ttk.Entry(self.form_frame, width=30)
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_entry.grid(row=row0 + 2, column=1, padx=5, pady=5)
        self.form_elements["Date"] = date_entry
        
        submit_btn = ttk.Button(self.form_frame, text="Submit", command=self.insert_offset_data)
        submit_btn.grid(row=row0 + 3, column=0, columnspan=2, pady=10)
    
    def get_user_ids(self):
        """Get user IDs and names for dropdown"""
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
    
    def insert_user_data(self):
        """Insert new user into database"""
        try:
            # Validate form
            full_name = self.form_elements["Full_Name"].get().strip()
            email = self.form_elements["Email"].get().strip()
            location = self.form_elements["Location"].get().strip()
            
            if not full_name or not email or not location:
                messagebox.showwarning("Validation Error", "Please fill in all fields")
                return
            
            # Insert data
            conn = sqlite3.connect('carbon_emission.db')
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO User_Profile (Full_Name, Email, Location) VALUES (?, ?, ?)", 
                (full_name, email, location)
            )
            
            conn.commit()
            conn.close()
            
            # Show success message
            messagebox.showinfo("Success", "User data added successfully")
            
            # Clear form
            for entry in self.form_elements.values():
                entry.delete(0, tk.END)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error inserting data: {str(e)}")
    
    def insert_transportation_data(self):
        """Insert transportation data into database"""
        try:
            # Validate form
            if self.session is not None:
                user_id = self.session.user_id
            else:
                user_string = self.form_elements["User_ID"].get()
                user_id = self.extract_user_id(user_string)
            
            vehicle_type = self.form_elements["Vehicle_Type"].get().strip()
            distance_str = self.form_elements["Distance_KM"].get().strip()
            date = self.form_elements["Date"].get().strip()
            
            if not user_id or not vehicle_type or not distance_str or not date:
                messagebox.showwarning("Validation Error", "Please fill in all fields")
                return
            
            try:
                distance = float(distance_str)
            except ValueError:
                messagebox.showwarning("Validation Error", "Distance must be a number")
                return
            
            # Insert data
            conn = sqlite3.connect('carbon_emission.db')
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO Transportation (User_ID, Vehicle_Type, Distance_KM, Date) VALUES (?, ?, ?, ?)", 
                (user_id, vehicle_type, distance, date)
            )
            
            conn.commit()
            conn.close()
            
            # Show success message
            messagebox.showinfo("Success", "Transportation data added successfully")
            
            # Clear form (except user and date)
            self.form_elements["Vehicle_Type"].delete(0, tk.END)
            self.form_elements["Distance_KM"].delete(0, tk.END)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error inserting data: {str(e)}")
    
    def insert_energy_data(self):
        """Insert energy consumption data into database"""
        try:
            # Validate form
            if self.session is not None:
                user_id = self.session.user_id
            else:
                user_string = self.form_elements["User_ID"].get()
                user_id = self.extract_user_id(user_string)
            
            energy_source = self.form_elements["Energy_Source"].get().strip()
            consumption_str = self.form_elements["Consumption_KWH"].get().strip()
            date = self.form_elements["Date"].get().strip()
            
            if not user_id or not energy_source or not consumption_str or not date:
                messagebox.showwarning("Validation Error", "Please fill in all fields")
                return
            
            try:
                consumption = float(consumption_str)
            except ValueError:
                messagebox.showwarning("Validation Error", "Consumption must be a number")
                return
            
            # Insert data
            conn = sqlite3.connect('carbon_emission.db')
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO Energy_Consumption (User_ID, Energy_Source, Consumption_KWH, Date) VALUES (?, ?, ?, ?)", 
                (user_id, energy_source, consumption, date)
            )
            
            conn.commit()
            conn.close()
            
            # Show success message
            messagebox.showinfo("Success", "Energy consumption data added successfully")
            
            # Clear form (except user and date)
            self.form_elements["Energy_Source"].delete(0, tk.END)
            self.form_elements["Consumption_KWH"].delete(0, tk.END)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error inserting data: {str(e)}")
    
    def insert_waste_data(self):
        """Insert waste management data into database"""
        try:
            # Validate form
            if self.session is not None:
                user_id = self.session.user_id
            else:
                user_string = self.form_elements["User_ID"].get()
                user_id = self.extract_user_id(user_string)
            
            waste_type = self.form_elements["Waste_Type"].get().strip()
            weight_str = self.form_elements["Waste_Weight_KG"].get().strip()
            date = self.form_elements["Date"].get().strip()
            
            if not user_id or not waste_type or not weight_str or not date:
                messagebox.showwarning("Validation Error", "Please fill in all fields")
                return
            
            try:
                weight = float(weight_str)
            except ValueError:
                messagebox.showwarning("Validation Error", "Weight must be a number")
                return
            
            # Insert data
            conn = sqlite3.connect('carbon_emission.db')
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO Waste_Management (User_ID, Waste_Type, Waste_Weight_KG, Date) VALUES (?, ?, ?, ?)", 
                (user_id, waste_type, weight, date)
            )
            
            conn.commit()
            conn.close()
            
            # Show success message
            messagebox.showinfo("Success", "Waste management data added successfully")
            
            # Clear form (except user and date)
            self.form_elements["Waste_Type"].delete(0, tk.END)
            self.form_elements["Waste_Weight_KG"].delete(0, tk.END)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error inserting data: {str(e)}")
    
    def insert_industrial_data(self):
        """Insert industrial activity data into database"""
        try:
            # Validate form
            if self.session is not None:
                user_id = self.session.user_id
            else:
                user_string = self.form_elements["User_ID"].get()
                user_id = self.extract_user_id(user_string)
            
            activity_type = self.form_elements["Activity_Type"].get().strip()
            emission_str = self.form_elements["Emission_Produced"].get().strip()
            date = self.form_elements["Date"].get().strip()
            
            if not user_id or not activity_type or not emission_str or not date:
                messagebox.showwarning("Validation Error", "Please fill in all fields")
                return
            
            try:
                emission = float(emission_str)
            except ValueError:
                messagebox.showwarning("Validation Error", "Emission must be a number")
                return
            
            # Insert data
            conn = sqlite3.connect('carbon_emission.db')
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO Industrial_Activity (User_ID, Activity_Type, Emission_Produced, Date) VALUES (?, ?, ?, ?)", 
                (user_id, activity_type, emission, date)
            )
            
            conn.commit()
            conn.close()
            
            # Show success message
            messagebox.showinfo("Success", "Industrial activity data added successfully")
            
            # Clear form (except user and date)
            self.form_elements["Activity_Type"].delete(0, tk.END)
            self.form_elements["Emission_Produced"].delete(0, tk.END)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error inserting data: {str(e)}")
    
    def insert_offset_data(self):
        """Insert carbon offset data into database"""
        try:
            # Validate form
            if self.session is not None:
                user_id = self.session.user_id
            else:
                user_string = self.form_elements["User_ID"].get()
                user_id = self.extract_user_id(user_string)
            
            offset_type = self.form_elements["Offset_Type"].get().strip()
            amount_str = self.form_elements["Offset_Amount"].get().strip()
            date = self.form_elements["Date"].get().strip()
            
            if not user_id or not offset_type or not amount_str or not date:
                messagebox.showwarning("Validation Error", "Please fill in all fields")
                return
            
            try:
                amount = float(amount_str)
            except ValueError:
                messagebox.showwarning("Validation Error", "Offset amount must be a number")
                return
            
            # Insert data
            conn = sqlite3.connect('carbon_emission.db')
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO Carbon_Offset (User_ID, Offset_Type, Offset_Amount, Date) VALUES (?, ?, ?, ?)", 
                (user_id, offset_type, amount, date)
            )
            
            conn.commit()
            conn.close()
            
            # Show success message
            messagebox.showinfo("Success", "Carbon offset data added successfully")
            
            # Clear form (except user and date)
            self.form_elements["Offset_Type"].delete(0, tk.END)
            self.form_elements["Offset_Amount"].delete(0, tk.END)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error inserting data: {str(e)}") 