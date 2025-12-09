"""Admin dashboard UI with tabbed navigation."""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Callable, Dict, Optional

from services import (
    create_user,
    delete_user,
    list_messages_lines,
    list_users,
    post_message,
    update_user_enabled,
    update_user_username,
    count_roles
)
from ui.components import MessageBoard


def build_dashboard(root: tk.Misc, user: Dict[str, str], logout_callback: Callable[[], None]) -> tk.Frame:
    container = tk.Frame(root)

    header = tk.Frame(container)
    header.pack(fill=tk.X, pady=8, padx=10)

    tk.Label(header, text="Administrator Dashboard", font=("Helvetica", 16, "bold")).pack(side=tk.LEFT)
    tk.Button(header, text="Logout", command=logout_callback).pack(side=tk.RIGHT)

    notebook = ttk.Notebook(container)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    # ========== Tab 1: User Management ==========
    tab_users = tk.Frame(notebook)
    notebook.add(tab_users, text="User Management")

    manage_frame = tk.LabelFrame(tab_users, text="User Accounts", padx=10, pady=10)
    manage_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # adds search feature ==============
    search_frame = tk.Frame(manage_frame)
    search_frame.pack(fill=tk.X, pady=6)

    def search_name():
        keyword = search_entry.get().lower().strip()
        selection = 0
        if not keyword:
            for item in table.selection():
                table.selection_remove(item)
            return
        for child in table.get_children():
            if keyword == table.item(child)["values"][0]:
                selection = child
                break
        if selection:
            table.selection_set(selection)
        else:
            for item in table.selection():
                table.selection_remove(item)
            return

    tk.Label(search_frame, text="Search username").pack(side=tk.LEFT)
    search_entry = tk.Entry(search_frame, width=20)
    search_entry.pack(side=tk.LEFT)
    search_button = tk.Button(search_frame, text="Search", width=5, height=1, command=search_name)
    search_button.pack(side=tk.LEFT)


    table = ttk.Treeview(manage_frame, columns=("Username", "Role", "Enabled"), show="headings", height=12)
    table.heading("Username", text="Username")
    table.heading("Role", text="Role")
    table.heading("Enabled", text="Enabled")
    table.column("Username", width=140)
    table.column("Role", width=120)
    table.column("Enabled", width=80)
    table.pack(fill=tk.BOTH, expand=True, pady=4)

    user_cache: Dict[int, Dict[str, str]] = {}


    def refresh_users() -> None:
        table.delete(*table.get_children())
        user_cache.clear()
        for row in list_users():
            user_cache[row["id"]] = row
            table.insert(
                "",
                tk.END,
                iid=row["id"],
                values=(row["username"], row["role"], "Yes" if row["enabled"] else "No"),
                tags=("disabled",) if not row["enabled"] else (),
            )

    table.tag_configure("disabled", foreground="#888888")

    refresh_users()

    form_frame = tk.Frame(manage_frame)
    form_frame.pack(fill=tk.X, pady=6)

    tk.Label(form_frame, text="Username").grid(row=0, column=0, padx=4, pady=2, sticky=tk.W)
    username_entry = tk.Entry(form_frame, width=20)
    username_entry.grid(row=0, column=1, padx=4, pady=2)

    tk.Label(form_frame, text="Role").grid(row=0, column=2, padx=4, pady=2, sticky=tk.W)
    role_var = tk.StringVar(value="leader")
    role_menu = ttk.Combobox(form_frame, textvariable=role_var, values=["leader", "coordinator"], state="readonly", width=15)
    role_menu.grid(row=0, column=3, padx=4, pady=2)

    def create_user_action() -> None:
        # create a condition where if i want to create a new coordinator account it should ask if you want to disable the existing coordinator account
        # they should only ask you this if you only have one coordinator account PRESENT (use count_roles()) done

        username = username_entry.get().strip()
        role = role_var.get()
        enabled_no = count_roles()[1]

        if not username:
            messagebox.showwarning("Validation", "Username is required.")
            return
        for existing in user_cache.values():
            if username == existing['username']:
                messagebox.showerror(
                    "Create user",
                    "Username already exists. Please try again.",
                )
                return

        if enabled_no["coordinator"] == 1:
            for existing in user_cache.values():
                if existing["role"] == "coordinator" and existing["enabled"]:
                    if messagebox.askyesno("Coordinator already enabled",
                                           "Creating a new coordinator account will mean you have to disable the current active account. Proceed?"):
                        update_user_enabled(existing["id"], False)
                        create_user(username,role)
                        refresh_users()
                        return
                    else:
                        messagebox.showerror(
                            "Create user",
                            f"Exactly one {role} is allowed. Disable the existing account first if you must replace it.")
                        return
        # IDK if this is necessary because there is already something for the coordinator, there isnt even an option to create a new admin on the drop down
        if role in {"admin", "coordinator"}:
            for existing in user_cache.values():
                if existing["role"] == role and existing["enabled"]:
                    messagebox.showerror(
                        "Create user",
                        f"Exactly one {role} is allowed. Disable the existing account first if you must replace it.",
                    )
                    return

        if not create_user(username, role):
            messagebox.showerror("Create user", "Failed to create user. Ensure username is unique and role limits allow it.")
            return
        username_entry.delete(0, tk.END)
        refresh_users()

    tk.Button(form_frame, text="Create User", command=create_user_action).grid(row=0, column=4, padx=4, pady=2)

    selection_frame = tk.Frame(manage_frame)
    selection_frame.pack(fill=tk.X, pady=4)

    tk.Label(selection_frame, text="Select a user row, then:", font=("Helvetica", 10, "bold")).pack(side=tk.LEFT, padx=4)

    def get_selected_user_id() -> Optional[int]:
        selection = table.selection()
        if not selection:
            messagebox.showinfo("Selection", "Click on a user row in the table to select it.")
            return None
        return int(selection[0])

    def get_selected_user() -> Optional[Dict[str, str]]:
        user_id = get_selected_user_id()
        if user_id is None:
            return None
        record = user_cache.get(user_id)
        if record is None:
            messagebox.showwarning("Selection", "User no longer exists; refreshing list.")
            refresh_users()
            return None
        return record

    def edit_username() -> None:
        record = get_selected_user()
        if record is None:
            return
        new_username = simpledialog.askstring(
            "Edit username",
            f"Enter new username for {record['username']}:",
            initialvalue=record["username"],
            parent=container,
        )
        if not new_username or new_username.strip() == "":
            return
        if not update_user_username(record["id"], new_username.strip()):
            messagebox.showerror("Edit", "Failed to update username. Ensure it's unique.")
            return
        refresh_users()

    def set_enabled(enabled: bool) -> None:

        record = get_selected_user()
        enabled_no = count_roles()[1] #adds a counter for the number of admins, leaders and coordinators
        count = count_roles()[0]

        # can't disable something that's already disabled
        if not(record["enabled"]) and not enabled:
            messagebox.showerror("Disable", f"This account is already disabled.")
            return

        # shouldn't be able to delete the sole active leader account
        if enabled_no["leader"] <= 1 and record["role"] == "leader" and not enabled:
            messagebox.showerror("Disable", f"Cannot disable the sole {record['role']} account.")
            return
        # shouldn't be able to disable the sole active coordinator account
        if enabled_no["coordinator"] <= 1 and record["role"] == "coordinator" and not enabled:
            messagebox.showerror("Disable", f"Cannot disable the sole {record['role']} account.")
            return
        # you cant enable more than one coordinator, the only way to change the active coordinator is by creating a new one
        if enabled_no["coordinator"] == 1 and record["role"] == "coordinator":
            if count["coordinator"] != 1:
                messagebox.showerror("Enable", f"Only one {record['role']} can be active.")
            return

        # you can't delete an admin account! not sure if i should keep because it will work the same as the if statement below
        if record["role"] == "admin" and not enabled:
            messagebox.showerror("Disable", f"Cannot disable an {record['role']} account.")
            return

        if record["id"] == user.get("id") and not enabled:
            messagebox.showwarning("Disable", "You cannot disable the account currently logged in.")
            return

        update_user_enabled(record["id"], enabled)
        refresh_users()

    def delete_selected() -> None:
        record = get_selected_user()
        count = count_roles()[0]
        if record is None:
            return

        # shouldn't be able to delete the sole leader account
        if count["leader"] == 1 and record["role"] == "leader":
            messagebox.showerror("Delete", f"Cannot delete the sole {record['role']} account.")
            return
        # shouldn't be able to delete the sole coordinator account
        if count["coordinator"] == 1 and record["role"] == "coordinator" or record["enabled"]:
            messagebox.showerror("Delete", f"Cannot delete the sole {record['role']} account.")
            return

        # you can't delete an admin account!
        if record["role"] == "admin":
            messagebox.showerror("Delete", f"Cannot delete the {record['role']} account.")
            return

        # this would never run
        if record["id"] == user.get("id"):
            messagebox.showwarning("Delete", "You cannot delete the account currently logged in.")
            return

        if not messagebox.askyesno("Delete user", "Are you sure? This is a hard delete."):
            return
        if not delete_user(record["id"]):
            messagebox.showerror("Delete", "Cannot delete user with existing assignments or logs. Disable instead.")
            return
        refresh_users()

    tk.Button(selection_frame, text="Edit name", command=edit_username).pack(side=tk.LEFT, padx=4)
    tk.Button(selection_frame, text="Enable", command=lambda: set_enabled(True)).pack(side=tk.LEFT, padx=4)
    tk.Button(selection_frame, text="Disable", command=lambda: set_enabled(False)).pack(side=tk.LEFT, padx=4)
    tk.Button(selection_frame, text="Delete", command=delete_selected).pack(side=tk.LEFT, padx=4)

    # ========== Tab 2: Chat ==========
    tab_chat = tk.Frame(notebook)
    notebook.add(tab_chat, text="Chat")

    def post_message_wrapper(content: str) -> None:
        post_message(user.get("id"), content)

    MessageBoard(
        tab_chat,
        post_callback=post_message_wrapper,
        fetch_callback=lambda: list_messages_lines(),
    ).pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    return container



