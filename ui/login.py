
"""Login UI and session handoff for CampTrack."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict, Optional

from services import authenticate
from ui import admin, coordinator, leader, parent
from ui import theme as app_theme


RoleBuilder = Callable[[tk.Misc, Dict[str, str], Callable[[], None]], tk.Widget]


ROLE_BUILDERS: Dict[str, RoleBuilder] = {
    "admin": admin.build_dashboard,
    "coordinator": coordinator.build_dashboard,
    "leader": leader.build_dashboard,
    "parent": parent.build_dashboard,
}


class CampTrackApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("CampTrack - Login")
        self.root.geometry("420x280")
        self.root.resizable(True, True)
        app_theme.apply_theme(self.root, mode="light")

        self.active_dashboard: Optional[tk.Widget] = None

        self._build_login_frame()

    def _build_login_frame(self) -> None:
        self.login_frame = ttk.Frame(self.root, padding=20)
        self.login_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(self.login_frame, text="Welcome to CampTrack", font=("Helvetica", 18, "bold")).pack(pady=(0, 16))

        form = ttk.Frame(self.login_frame)
        form.pack()

        ttk.Label(form, text="Username").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.username_entry = ttk.Entry(form, width=30)
        self.username_entry.grid(row=0, column=1, pady=4)
        self.username_entry.insert(0, "admin")

        ttk.Label(form, text="Password (blank)").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.password_entry = ttk.Entry(form, show="*", width=30)
        self.password_entry.grid(row=1, column=1, pady=4)

        button_frame = ttk.Frame(self.login_frame)
        button_frame.pack(pady=16)

        self.login_status = tk.StringVar()
        status_label = ttk.Label(self.login_frame, textvariable=self.login_status, style="Error.TLabel")
        status_label.pack()

        ttk.Button(button_frame, text="Login", width=14, style="Primary.TButton", command=self._handle_login).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Quit", width=14, command=self.root.quit).pack(side=tk.LEFT, padx=4)

        self.password_entry.bind("<Return>", lambda _: self._handle_login())
        self.username_entry.focus_set()

    def _handle_login(self) -> None:
        username = self.username_entry.get().strip()
        password = self.password_entry.get() or ""

        user = authenticate(username, password)
        if not user:
            self.login_status.set("Login failed. Check username/password or account status.")
            return

        role = user.get("role")
        builder = ROLE_BUILDERS.get(role)
        if builder is None:
            messagebox.showerror("Unsupported role", f"No dashboard implemented for role '{role}'.")
            return

        self._open_dashboard(builder, user)

    def _open_dashboard(self, builder: RoleBuilder, user: Dict[str, str]) -> None:
        if self.active_dashboard is not None:
            self.active_dashboard.destroy()
            self.active_dashboard = None

        self.login_frame.pack_forget()
        self.root.title(f"CampTrack - {user['role'].title()} Dashboard")

        # Set appropriate window size for role
        role_sizes = {
            "admin": "900x700",
            "coordinator": "1200x800",
            "leader": "1000x750",
            "parent": "1000x750",
        }
        self.root.geometry(role_sizes.get(user["role"], "1000x700"))

        def logout() -> None:
            if messagebox.askyesno("Logout", "Do you really want to logout?"):
                self._perform_logout()

        self.active_dashboard = builder(self.root, user, logout)
        self.active_dashboard.pack(fill=tk.BOTH, expand=True)

    def _perform_logout(self) -> None:
        if self.active_dashboard is not None:
            self.active_dashboard.destroy()
            self.active_dashboard = None

        self.root.title("CampTrack - Login")
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        self.username_entry.focus_set()
        self.password_entry.delete(0, tk.END)
        self.login_status.set("")

    def run(self) -> None:
        self.root.mainloop()


def launch_login() -> None:
    CampTrackApp().run()


