import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import sqlite3
import pandas as pd
from updated_queries import updated_queries
from carbon_emission_db import setup_database, ensure_correct_emission_factors
from data_insertion import DataInsertionFrame
from reports import ReportsFrame
from recommendations import RecommendationsFrame
from login import LoginFrame
from session import AppSession

class CarbonEmissionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Carbon Emission Calculator & Insights")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)

        self.apply_theme()
        self.session: AppSession | None = None
        self.show_dev_tools = False
        
        # Set up the database if it doesn't exist
        try:
            self.check_database()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to set up database: {str(e)}")
        
        # Main container (gives us a nicer, consistent padding)
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.build_menu()
        self.show_login()
        
        # Initialize the query history
        self.query_history = []
        self.history_index = -1
        
    def build_menu(self):
        menubar = tk.Menu(self.root)

        account_menu = tk.Menu(menubar, tearoff=0)
        account_menu.add_command(label="Logout", command=self.logout, state="disabled")
        menubar.add_cascade(label="Account", menu=account_menu)
        self._account_menu = account_menu

        dev_menu = tk.Menu(menubar, tearoff=0)
        dev_menu.add_command(
            label="Show Developer Tools",
            command=self.toggle_dev_tools,
            state="disabled",
        )
        menubar.add_cascade(label="Developer", menu=dev_menu)
        self._dev_menu = dev_menu

        self.root.config(menu=menubar)

    def clear_main(self):
        for w in self.main_frame.winfo_children():
            w.destroy()

    def show_login(self):
        self.session = None
        self.clear_main()
        self._account_menu.entryconfig("Logout", state="disabled")

        login = LoginFrame(self.main_frame, on_login=self.on_login)
        login.pack(fill=tk.BOTH, expand=True)

    def on_login(self, session: AppSession):
        self.session = session
        self._account_menu.entryconfig("Logout", state="normal")
        # Only developer accounts can toggle SQL/dev tools
        if self.session.role == "developer":
            self._dev_menu.entryconfig(0, state="normal")
        else:
            self.show_dev_tools = False
            self._dev_menu.entryconfig(0, state="disabled")
        self.build_app_shell()

    def logout(self):
        if messagebox.askyesno("Logout", "Do you want to logout?"):
            self.show_login()

    def toggle_dev_tools(self):
        if self.session is None or self.session.role != "developer":
            messagebox.showinfo(
                "Developer tools",
                "Developer tools are only available for developer accounts.",
            )
            return
        self.show_dev_tools = not self.show_dev_tools
        label = "Hide Developer Tools" if self.show_dev_tools else "Show Developer Tools"
        self._dev_menu.entryconfig(0, label=label)
        # If logged in, rebuild tabs; if not, just keep login screen.
        if self.session is not None:
            self.build_app_shell()

    def build_app_shell(self):
        """Build the end-user product UI after login."""
        if self.session is None:
            self.show_login()
            return

        self.clear_main()

        # --- Top header ---
        header = ttk.Frame(self.main_frame)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=1)

        self.page_title_var = tk.StringVar(value="Dashboard")
        title = ttk.Label(header, textvariable=self.page_title_var, font=("Arial", 14, "bold"))
        title.grid(row=0, column=0, sticky="w")

        who = ttk.Label(
            header,
            text=f"Signed in as {self.session.full_name} • Mode: {self.session.mode}",
        )
        who.grid(row=0, column=1, sticky="e")

        # --- Sidebar + content ---
        self.main_frame.rowconfigure(1, weight=1)
        self.main_frame.columnconfigure(1, weight=1)

        self.nav_frame = ttk.Frame(self.main_frame)
        self.nav_frame.grid(row=1, column=0, sticky="nsw", padx=(0, 10))

        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.grid(row=1, column=1, sticky="nsew")
        self.content_frame.rowconfigure(0, weight=1)
        self.content_frame.columnconfigure(0, weight=1)

        # Create pages (stacked frames)
        self.pages: dict[str, ttk.Frame] = {}
        self._nav_buttons: dict[str, ttk.Button] = {}

        self.pages["Home"] = ttk.Frame(self.content_frame)
        self.pages["Add Data"] = ttk.Frame(self.content_frame)
        self.pages["Analysis & Charts"] = ttk.Frame(self.content_frame)
        self.pages["Recommendations"] = ttk.Frame(self.content_frame)

        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        self.home_tab = self.pages["Home"]
        self.insertion_tab = self.pages["Add Data"]
        self.reports_tab = self.pages["Analysis & Charts"]
        self.recommendations_tab = self.pages["Recommendations"]

        self.setup_home_tab()
        self.setup_insertion_tab()
        self.setup_reports_tab()
        self.setup_recommendations_tab()

        # Developer tools page (developer accounts only; still toggleable)
        if self.session.role == "developer" and self.show_dev_tools:
            self.pages["Developer (SQL)"] = ttk.Frame(self.content_frame)
            self.pages["Developer (SQL)"].grid(row=0, column=0, sticky="nsew")
            self.query_tab = self.pages["Developer (SQL)"]
            self.setup_query_tab()

        self.build_sidebar()
        self.show_page("Home")

    def build_sidebar(self):
        """Create side navigation buttons."""
        for w in self.nav_frame.winfo_children():
            w.destroy()

        ttk.Label(self.nav_frame, text="Navigation", font=("Arial", 11, "bold")).pack(
            anchor="w", pady=(0, 8)
        )

        def add_btn(label: str):
            btn = ttk.Button(self.nav_frame, text=label, command=lambda: self.show_page(label))
            btn.pack(fill=tk.X, pady=4)
            self._nav_buttons[label] = btn

        add_btn("Home")
        add_btn("Add Data")
        add_btn("Analysis & Charts")
        add_btn("Recommendations")

        if "Developer (SQL)" in self.pages:
            ttk.Separator(self.nav_frame, orient="horizontal").pack(fill=tk.X, pady=10)
            add_btn("Developer (SQL)")

        ttk.Separator(self.nav_frame, orient="horizontal").pack(fill=tk.X, pady=10)
        ttk.Button(self.nav_frame, text="Logout", command=self.logout).pack(fill=tk.X, pady=4)

    def show_page(self, name: str):
        """Raise a page and update header title."""
        page = self.pages.get(name)
        if page is None:
            return
        page.tkraise()
        self.page_title_var.set(name)
        
    def check_database(self):
        """Check if database exists, if not create it, and ensure factors are correct."""
        try:
            conn = sqlite3.connect('carbon_emission.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='User_Profile'")
            exists = cursor.fetchone() is not None
            conn.close()
            if not exists:
                setup_database()
        except Exception:
            setup_database()

        # Ensure emission factors are updated even for existing databases.
        try:
            ensure_correct_emission_factors('carbon_emission.db')
        except Exception:
            # If this fails, continue with whatever factors exist.
            pass

    def apply_theme(self):
        """Apply a friendlier ttk theme + some basic spacing styles."""
        try:
            style = ttk.Style(self.root)
            # 'clam' is widely available and looks much nicer than defaults.
            style.theme_use("clam")

            # Slightly larger padding makes the UI feel less cramped.
            style.configure("TButton", padding=(10, 6))
            style.configure("TNotebook.Tab", padding=(12, 8))
            style.configure("TLabelframe", padding=(10, 8))
        except Exception:
            # If anything goes wrong, keep default appearance.
            pass
    
    def setup_query_tab(self):
        """Set up the query tab components"""
        # Create the main frames
        self.create_query_frames()
        
        # Create the query section
        self.create_query_section()
        
        # Create the results section
        self.create_results_section()
        
        # Create the predefined queries section
        self.create_predefined_queries_section()
    
    def setup_insertion_tab(self):
        """Set up the data insertion tab"""
        # Create the data insertion frame
        self.insertion_frame = DataInsertionFrame(self.insertion_tab, session=self.session)
        self.insertion_frame.pack(fill=tk.BOTH, expand=True)
    
    def setup_reports_tab(self):
        """Set up the reports tab"""
        # Create the reports frame
        self.reports_frame = ReportsFrame(self.reports_tab, session=self.session)
        self.reports_frame.pack(fill=tk.BOTH, expand=True)

    def setup_recommendations_tab(self):
        """Set up the recommendations tab"""
        self.recommendations_frame = RecommendationsFrame(self.recommendations_tab, session=self.session)
        self.recommendations_frame.pack(fill=tk.BOTH, expand=True)

    def setup_home_tab(self):
        """Simple end-user landing page with guided actions."""
        frame = ttk.Frame(self.home_tab, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text="What would you like to do?",
            font=("Arial", 13, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        ttk.Label(
            frame,
            text="1) Add your latest data → 2) Generate your report → 3) Follow recommendations",
        ).pack(anchor="w", pady=(0, 16))

        btns = ttk.Frame(frame)
        btns.pack(anchor="w")

        ttk.Button(btns, text="Add Data", command=lambda: self.show_page("Add Data")).grid(
            row=0, column=0, padx=(0, 10), pady=6, sticky="w"
        )
        ttk.Button(btns, text="Analysis & Charts", command=lambda: self.show_page("Analysis & Charts")).grid(
            row=0, column=1, padx=(0, 10), pady=6, sticky="w"
        )
        ttk.Button(btns, text="Recommendations", command=lambda: self.show_page("Recommendations")).grid(
            row=0, column=2, pady=6, sticky="w"
        )
            
    def create_query_frames(self):
        """Create the main application frames for the query tab"""
        # Top frame for query input
        self.query_frame = ttk.LabelFrame(self.query_tab, text="SQL Query (Advanced)")
        self.query_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)
        
        # Middle frame for query results
        self.results_frame = ttk.LabelFrame(self.query_tab, text="Query Results")
        self.results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Bottom frame for predefined queries
        self.predefined_frame = ttk.LabelFrame(self.query_tab, text="Predefined Queries")
        self.predefined_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)
        
    def create_query_section(self):
        """Create the query input section"""
        help_text = (
            "Tip: Use SELECT queries to explore your data safely.\n"
            "INSERT / UPDATE / DELETE will modify the database."
        )
        ttk.Label(self.query_frame, text=help_text, justify="left").pack(anchor="w", padx=5, pady=(5, 0))

        # Query text area
        self.query_text = scrolledtext.ScrolledText(self.query_frame, height=6)
        self.query_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Buttons frame
        button_frame = ttk.Frame(self.query_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Run query button
        run_button = ttk.Button(button_frame, text="Run Query", command=self.run_custom_query)
        run_button.pack(side=tk.LEFT, padx=5)

        export_button = ttk.Button(button_frame, text="Export Results (CSV)", command=self.export_results_csv)
        export_button.pack(side=tk.LEFT, padx=5)
        
        # Clear button
        clear_button = ttk.Button(button_frame, text="Clear", command=self.clear_query)
        clear_button.pack(side=tk.LEFT, padx=5)
        
        # History navigation buttons
        prev_button = ttk.Button(button_frame, text="Previous Query", command=self.load_previous_query)
        prev_button.pack(side=tk.LEFT, padx=5)
        
        next_button = ttk.Button(button_frame, text="Next Query", command=self.load_next_query)
        next_button.pack(side=tk.LEFT, padx=5)
        
    def create_results_section(self):
        """Create the results display section"""
        # Create a frame for the Treeview
        tree_frame = ttk.Frame(self.results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbars for the Treeview
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Results Treeview
        self.results_tree = ttk.Treeview(tree_frame, yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Configure scrollbars
        vsb.config(command=self.results_tree.yview)
        hsb.config(command=self.results_tree.xview)
        
        # Place the Treeview and scrollbars
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.results_tree.pack(fill=tk.BOTH, expand=True)
        
        # Status bar for showing query info
        self.status_bar = ttk.Label(self.results_frame, text="Ready", anchor=tk.W)
        self.status_bar.pack(fill=tk.X, padx=5, pady=2)
        
    def create_predefined_queries_section(self):
        """Create the predefined queries section with a scrollable list (less clutter)."""
        list_frame = ttk.Frame(self.predefined_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        ttk.Label(
            list_frame,
            text="Pick a predefined analysis query. It will be loaded into the editor above.",
        ).pack(anchor="w", pady=(0, 4))

        search_row = ttk.Frame(list_frame)
        search_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(search_row, text="Search:").pack(side=tk.LEFT)
        self.predefined_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.predefined_search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
        search_entry.bind("<KeyRelease>", self.on_predefined_search)

        inner = ttk.Frame(list_frame)
        inner.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(inner, orient="vertical")
        self.predefined_list = tk.Listbox(
            inner,
            height=12,
            yscrollcommand=scrollbar.set,
            exportselection=False,
        )
        scrollbar.config(command=self.predefined_list.yview)

        self.predefined_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Populate list with query names (sorted for easier scanning)
        self._all_predefined_names = sorted(updated_queries.keys())
        self._render_predefined_list(self._all_predefined_names)

        self.predefined_list.bind("<<ListboxSelect>>", self.on_predefined_select)
        self.predefined_list.bind("<Double-Button-1>", self.on_predefined_double_click)

    def _render_predefined_list(self, names):
        if not hasattr(self, "predefined_list"):
            return
        self.predefined_list.delete(0, tk.END)
        for name in names:
            self.predefined_list.insert(tk.END, name)

    def on_predefined_search(self, event=None):
        if not hasattr(self, "_all_predefined_names"):
            return
        term = (self.predefined_search_var.get() or "").strip().lower()
        if not term:
            self._render_predefined_list(self._all_predefined_names)
            return
        filtered = [n for n in self._all_predefined_names if term in n.lower()]
        self._render_predefined_list(filtered)

    def on_predefined_select(self, event):
        """Handle selection of a predefined query from the listbox."""
        if not hasattr(self, "predefined_list"):
            return
        selection = self.predefined_list.curselection()
        if not selection:
            return
        index = selection[0]
        name = self.predefined_list.get(index)
        query = updated_queries.get(name)
        if query:
            # Only load into editor on single click (keeps user in control).
            self.query_text.delete("1.0", tk.END)
            self.query_text.insert("1.0", query)

    def on_predefined_double_click(self, event):
        """Run the currently selected query on double click."""
        if not hasattr(self, "predefined_list"):
            return
        selection = self.predefined_list.curselection()
        if not selection:
            return
        name = self.predefined_list.get(selection[0])
        query = updated_queries.get(name)
        if query:
            self.run_predefined_query(query, name)
        
    def run_custom_query(self):
        """Run the custom query from the text input"""
        query = self.query_text.get("1.0", tk.END).strip()
        if not query:
            messagebox.showwarning("Empty Query", "Please enter an SQL query to run.")
            return
        
        # Add to history if not already the last query
        if not self.query_history or query != self.query_history[-1]:
            self.query_history.append(query)
            self.history_index = len(self.query_history) - 1
        
        # Run the query
        self.execute_query(query, "Custom Query")
        
    def run_predefined_query(self, query, name):
        """Run a predefined query"""
        # Set the query text in the input area
        self.query_text.delete("1.0", tk.END)
        self.query_text.insert("1.0", query)
        
        # Add to history if not already the last query
        if not self.query_history or query != self.query_history[-1]:
            self.query_history.append(query)
            self.history_index = len(self.query_history) - 1
        
        # Run the query
        self.execute_query(query, name)
        
    def execute_query(self, query, name):
        """Execute the given SQL query and display results"""
        try:
            # Connect to the database
            conn = sqlite3.connect('carbon_emission.db')
            
            # Check if it's a SELECT query
            is_select = query.strip().upper().startswith("SELECT")
            
            if is_select:
                # For SELECT queries, fetch and display results
                df = pd.read_sql_query(query, conn)
                self.display_results(df)
                row_count = len(df)
                col_count = len(df.columns)
                self.status_bar.config(text=f"{name}: {row_count} rows, {col_count} columns")
            else:
                # For other queries (INSERT, UPDATE, DELETE, etc.)
                cursor = conn.cursor()
                cursor.execute(query)
                conn.commit()
                affected_rows = cursor.rowcount
                self.status_bar.config(text=f"{name}: {affected_rows} rows affected")
                self.clear_results()
                messagebox.showinfo("Success", f"Query executed successfully. {affected_rows} rows affected.")
            
            conn.close()
            
        except Exception as e:
            self.status_bar.config(text=f"Error: {str(e)}")
            messagebox.showerror("Query Error", str(e))
            
    def display_results(self, df):
        """Display the results DataFrame in the Treeview"""
        # Clear previous results
        self.clear_results()
        
        # Configure columns
        self.results_tree["columns"] = list(df.columns)
        
        # Format column headings
        self.results_tree.column("#0", width=0, stretch=False)
        for col in df.columns:
            self.results_tree.column(col, anchor=tk.W, width=100)
            self.results_tree.heading(col, text=col, anchor=tk.W)
        
        # Add data rows
        for i, row in df.iterrows():
            values = [row[col] for col in df.columns]
            self.results_tree.insert("", tk.END, text=str(i), values=values)
            
    def clear_results(self):
        """Clear the results Treeview"""
        # Delete all items
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
            
        # Reset columns
        self.results_tree["columns"] = []
        
    def clear_query(self):
        """Clear the query text area"""
        self.query_text.delete("1.0", tk.END)

    def export_results_csv(self):
        """Export current Treeview results to a CSV file (read-only enhancement)."""
        try:
            columns = list(self.results_tree["columns"])
            if not columns:
                messagebox.showwarning("No Results", "There are no query results to export.")
                return

            rows = []
            for item in self.results_tree.get_children():
                rows.append(self.results_tree.item(item).get("values", []))

            df = pd.DataFrame(rows, columns=columns)
            filename = "query_results_export.csv"
            df.to_csv(filename, index=False)
            messagebox.showinfo("Export Complete", f"Saved results to: {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export results: {str(e)}")
        
    def load_previous_query(self):
        """Load the previous query from history"""
        if not self.query_history:
            return
            
        if self.history_index > 0:
            self.history_index -= 1
            query = self.query_history[self.history_index]
            self.query_text.delete("1.0", tk.END)
            self.query_text.insert("1.0", query)
            
    def load_next_query(self):
        """Load the next query from history"""
        if not self.query_history:
            return
            
        if self.history_index < len(self.query_history) - 1:
            self.history_index += 1
            query = self.query_history[self.history_index]
            self.query_text.delete("1.0", tk.END)
            self.query_text.insert("1.0", query)

    # The old tab refresh hook was developer-focused (selecting users). In the end-user
    # flow, the current user is the logged-in session, so we no longer need it.

if __name__ == "__main__":
    # Create main window
    root = tk.Tk()
    app = CarbonEmissionApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        # If the app is interrupted from the terminal (Ctrl+C), exit cleanly.
        try:
            root.destroy()
        except Exception:
            pass