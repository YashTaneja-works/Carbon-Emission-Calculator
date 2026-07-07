import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import hashlib

from session import AppSession


class LoginFrame(ttk.Frame):
    """
    End-user login / signup screen.
    Uses email + password, plus a mode (Individual / Industry).
    Developer accounts unlock the Developer (SQL) tools.
    """

    def __init__(self, parent, on_login):
        super().__init__(parent)
        self.parent = parent
        self.on_login = on_login  # callback(AppSession) -> None
        self._ensure_auth_table()
        self._build()

    def _build(self):
        container = ttk.Frame(self, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(container, text="Carbon Emission Calculator", font=("Arial", 18, "bold"))
        title.pack(anchor="center", pady=(0, 6))

        subtitle = ttk.Label(
            container,
            text="Sign in to add data, analyze your emissions, and get recommendations.",
        )
        subtitle.pack(anchor="center", pady=(0, 16))

        card = ttk.Frame(container, padding=16)
        card.pack(anchor="center")

        notebook = ttk.Notebook(card)
        notebook.pack(fill=tk.BOTH, expand=True)

        self.signin_tab = ttk.Frame(notebook, padding=12)
        self.signup_tab = ttk.Frame(notebook, padding=12)
        notebook.add(self.signin_tab, text="Sign in")
        notebook.add(self.signup_tab, text="Create account")

        self._build_signin(self.signin_tab)
        self._build_signup(self.signup_tab)

    def _build_signin(self, parent):
        ttk.Label(parent, text="Email").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.signin_email = ttk.Entry(parent, width=36)
        self.signin_email.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(parent, text="Password").grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.signin_password = ttk.Entry(parent, width=36, show="*")
        self.signin_password.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(parent, text="Mode").grid(row=4, column=0, sticky="w", pady=(0, 4))
        self.signin_mode = tk.StringVar(value="Individual")
        mode_combo = ttk.Combobox(
            parent,
            textvariable=self.signin_mode,
            values=["Individual", "Industry"],
            state="readonly",
            width=34,
        )
        mode_combo.grid(row=5, column=0, sticky="ew", pady=(0, 12))

        btn = ttk.Button(parent, text="Sign in", command=self._signin)
        btn.grid(row=6, column=0, sticky="ew")

        hint = ttk.Label(
            parent,
            text="Tip: Use the same email you used when creating the account.",
        )
        hint.grid(row=7, column=0, sticky="w", pady=(4, 0))

        parent.columnconfigure(0, weight=1)

    def _build_signup(self, parent):
        ttk.Label(parent, text="Full name").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.signup_name = ttk.Entry(parent, width=36)
        self.signup_name.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(parent, text="Email").grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.signup_email = ttk.Entry(parent, width=36)
        self.signup_email.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(parent, text="Location / City").grid(row=4, column=0, sticky="w", pady=(0, 4))
        self.signup_location = ttk.Entry(parent, width=36)
        self.signup_location.grid(row=5, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(parent, text="Mode").grid(row=6, column=0, sticky="w", pady=(0, 4))
        self.signup_mode = tk.StringVar(value="Individual")
        mode_combo = ttk.Combobox(
            parent,
            textvariable=self.signup_mode,
            values=["Individual", "Industry"],
            state="readonly",
            width=34,
        )
        mode_combo.grid(row=7, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(parent, text="Password").grid(row=8, column=0, sticky="w", pady=(0, 4))
        self.signup_password = ttk.Entry(parent, width=36, show="*")
        self.signup_password.grid(row=9, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(parent, text="Account type").grid(row=10, column=0, sticky="w", pady=(0, 4))
        self.signup_role = tk.StringVar(value="user")
        roles_frame = ttk.Frame(parent)
        roles_frame.grid(row=11, column=0, sticky="w", pady=(0, 10))
        ttk.Radiobutton(roles_frame, text="End user", value="user", variable=self.signup_role).pack(
            side="left", padx=(0, 10)
        )
        ttk.Radiobutton(
            roles_frame, text="Developer (advanced)", value="developer", variable=self.signup_role
        ).pack(side="left")

        btn = ttk.Button(parent, text="Create account", command=self._signup)
        btn.grid(row=12, column=0, sticky="ew")

        parent.columnconfigure(0, weight=1)

    def _signin(self):
        email = self.signin_email.get().strip()
        password = self.signin_password.get().strip()
        mode = self.signin_mode.get().strip() or "Individual"
        if not email or not password:
            messagebox.showwarning("Missing details", "Please enter both email and password.")
            return
        if not self._is_valid_email(email):
            messagebox.showwarning("Invalid email", "Please enter a valid email address (must contain @).")
            return

        try:
            session = self._load_session(email=email, password=password, mode=mode)
        except ValueError as e:
            messagebox.showwarning("Sign in failed", str(e))
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to sign in: {str(e)}")
            return

        self.on_login(session)

    def _signup(self):
        name = self.signup_name.get().strip()
        email = self.signup_email.get().strip()
        location = self.signup_location.get().strip()
        mode = self.signup_mode.get().strip() or "Individual"
        password = self.signup_password.get().strip()
        role = self.signup_role.get().strip() or "user"

        if not name or not email or not location or not password:
            messagebox.showwarning("Missing info", "Please fill in name, email, location and password.")
            return
        if not self._is_valid_email(email):
            messagebox.showwarning("Invalid email", "Please enter a valid email address (must contain @).")
            return
        if not self._is_valid_password(password):
            messagebox.showwarning(
                "Weak password",
                "Password must be at least 6 characters and contain at least one uppercase letter.",
            )
            return

        try:
            self._create_user(name=name, email=email, location=location, password=password, role=role)
            session = self._load_session(email=email, password=password, mode=mode)
        except ValueError as e:
            messagebox.showwarning("Create account failed", str(e))
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create account: {str(e)}")
            return

        messagebox.showinfo("Welcome", "Account created successfully.")
        self.on_login(session)

    def _create_user(self, name: str, email: str, location: str, password: str, role: str):
        conn = sqlite3.connect("carbon_emission.db")
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM User_Profile WHERE lower(Email) = lower(?)", (email,))
        exists = cursor.fetchone()[0] > 0
        if exists:
            conn.close()
            raise ValueError("An account with this email already exists. Please sign in instead.")

        cursor.execute(
            "INSERT INTO User_Profile (Full_Name, Email, Location) VALUES (?, ?, ?)",
            (name, email, location),
        )
        user_id = cursor.lastrowid

        password_hash = self._hash_password(password)
        role_norm = "developer" if role == "developer" else "user"

        cursor.execute(
            """
            INSERT INTO User_Auth (User_ID, Email, Password_Hash, Role)
            VALUES (?, lower(?), ?, ?)
            """,
            (user_id, email, password_hash, role_norm),
        )

        conn.commit()
        conn.close()

    def _load_session(self, email: str, password: str, mode: str) -> AppSession:
        conn = sqlite3.connect("carbon_emission.db")
        cursor = conn.cursor()

        self._ensure_auth_table(conn)

        cursor.execute(
            """
            SELECT ua.User_ID, ua.Password_Hash, ua.Role
            FROM User_Auth ua
            WHERE ua.Email = lower(?)
            """,
            (email,),
        )
        auth_row = cursor.fetchone()
        if not auth_row:
            conn.close()
            raise ValueError("No account found for this email. Please create an account first.")

        user_id, stored_hash, role = auth_row
        if stored_hash != self._hash_password(password):
            conn.close()
            raise ValueError("Incorrect password.")

        cursor.execute(
            "SELECT Full_Name, Email, Location FROM User_Profile WHERE User_ID = ?",
            (user_id,),
        )
        user_row = cursor.fetchone()
        conn.close()

        if not user_row:
            raise ValueError("User profile not found for this account.")

        full_name, email_db, location = user_row
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

    def _ensure_auth_table(self, conn: sqlite3.Connection | None = None):
        """Create User_Auth table if it doesn't exist yet."""
        close_after = False
        if conn is None:
            conn = sqlite3.connect("carbon_emission.db")
            close_after = True
        cursor = conn.cursor()
        cursor.execute(
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

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        return "@" in email and "." in email.split("@")[-1]

    @staticmethod
    def _is_valid_password(password: str) -> bool:
        if len(password) < 6:
            return False
        return any(ch.isupper() for ch in password)


