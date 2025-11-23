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
    count_roles_total,
    count_roles_enabled,
)
from ui.components import MessageBoard, ScrollFrame
from ui.theme import get_palette, tint


def build_dashboard(root: tk.Misc, user: Dict[str, str], logout_callback: Callable[[], None]) -> tk.Frame:
    scroll = ScrollFrame(root)
    container = scroll.content

    header = ttk.Frame(container)
    header.pack(fill=tk.X, pady=8, padx=10)

    tk.Label(header, text="Administrator Dashboard", font=("Helvetica", 16, "bold")).pack(side=tk.LEFT)
    ttk.Button(header, text="Logout", command=logout_callback).pack(side=tk.RIGHT)

    notebook = ttk.Notebook(container)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    # ========== Tab 1: User Management ==========
    tab_users = tk.Frame(notebook)
    notebook.add(tab_users, text="User Management")

    ttk.Label(tab_users, text="User Accounts", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, padx=10, pady=(10, 2))
    manage_frame = ttk.Frame(tab_users, style="Card.TFrame", padding=10)
    manage_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    # Username search (exact, case-insensitive)
    search_row = ttk.Frame(manage_frame)
    search_row.pack(fill=tk.X, pady=(0, 6))
    ttk.Label(search_row, text="Search username", style="Muted.TLabel").pack(side=tk.LEFT, padx=(0, 6))
    search_var = tk.StringVar(value="")
    search_entry = ttk.Entry(search_row, textvariable=search_var, width=20)
    search_entry.pack(side=tk.LEFT, padx=4)
    def do_search() -> None:
        keyword = search_var.get().strip()
        if not keyword:
            # Clear selection if empty
            sel = table.selection()
            if sel:
                table.selection_remove(*sel)
            return
        target = None
        for item_id in table.get_children():
            row_vals = table.item(item_id).get("values", [])
            if not row_vals:
                continue
            username = str(row_vals[0])
            if username.lower() == keyword.lower():
                target = item_id
                break
        if target:
            table.selection_set(target)
            table.focus(target)
            table.see(target)
        else:
            sel = table.selection()
            if sel:
                table.selection_remove(*sel)
            messagebox.showinfo("Not found", "Not found")
    def clear_search() -> None:
        search_var.set("")
        sel = table.selection()
        if sel:
            table.selection_remove(*sel)
    ttk.Button(search_row, text="Search", command=do_search).pack(side=tk.LEFT, padx=4)
    ttk.Button(search_row, text="Clear", command=clear_search).pack(side=tk.LEFT)

    # Users table container with vertical scrollbar
    table_container = ttk.Frame(manage_frame)
    table_container.pack(fill=tk.BOTH, expand=True)
    table = ttk.Treeview(table_container, columns=("Username", "Role", "Enabled"), show="headings", height=12)
    table_scroll = ttk.Scrollbar(table_container, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=table_scroll.set)
    table.heading("Username", text="Username", anchor=tk.W)
    table.heading("Role", text="Role", anchor=tk.CENTER)
    table.heading("Enabled", text="Enabled", anchor=tk.CENTER)
    table.column("Username", width=140, anchor=tk.W)
    table.column("Role", width=120, anchor=tk.CENTER)
    table.column("Enabled", width=80, anchor=tk.CENTER)
    table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
    table_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

    # Empty state label (hidden unless no users)
    empty_label = ttk.Label(manage_frame, text="No users to display.", style="Muted.TLabel")
    empty_label.pack_forget()

    user_cache: Dict[int, Dict[str, str]] = {}

    def refresh_users() -> None:
        table.delete(*table.get_children())
        user_cache.clear()
        palette = get_palette(table)
        # Zebra striping
        table.tag_configure("even", background=palette["surface"])
        table.tag_configure("odd", background=tint(palette["surface"], -0.03))
        users = list_users()
        if not users:
            empty_label.pack(pady=(4, 0), anchor=tk.W)
            return
        else:
            empty_label.pack_forget()
        for idx, row in enumerate(users):
            user_cache[row["id"]] = row
            tags = []
            if not row["enabled"]:
                tags.append("disabled")
            tags.append("odd" if (idx % 2 == 1) else "even")
            table.insert(
                "",
                tk.END,
                iid=row["id"],
                values=(row["username"], row["role"], "Yes" if row["enabled"] else "No"),
                tags=tuple(tags),
            )

    table.tag_configure("disabled", foreground="#888888")

    refresh_users()

    form_frame = ttk.Frame(manage_frame)
    form_frame.pack(fill=tk.X, pady=6)

    ttk.Label(form_frame, text="Username", font=("Helvetica", 11)).grid(row=0, column=0, padx=4, pady=2, sticky=tk.W)
    username_entry = ttk.Entry(form_frame, width=20)
    username_entry.grid(row=0, column=1, padx=4, pady=2)

    ttk.Label(form_frame, text="Role", font=("Helvetica", 11)).grid(row=0, column=2, padx=4, pady=2, sticky=tk.W)
    role_var = tk.StringVar(value="leader")
    role_menu = ttk.Combobox(
        form_frame,
        textvariable=role_var,
        values=["leader", "coordinator"],
        state="readonly",
        width=15,
        style="Filled.TCombobox",
        exportselection=False,
    )
    role_menu.grid(row=0, column=3, padx=4, pady=2)
    def _on_combo_selected(evt) -> None:
        # Ensure no lingering text selection in readonly state
        w = evt.widget
        try:
            w.selection_clear()
        except Exception:
            try:
                w.selection_clear(0, "end")
            except Exception:
                pass
        try:
            w.selection_range(0, 0)
        except Exception:
            pass
        try:
            w.icursor("end")
        except Exception:
            pass
        # Optionally shift focus away so macOS doesn't draw focus glow
        try:
            form_frame.focus_set()
        except Exception:
            pass
    role_menu.bind("<<ComboboxSelected>>", _on_combo_selected)

    def create_user_action() -> None:
        username = username_entry.get().strip()
        role = role_var.get()
        if not username:
            messagebox.showwarning("Validation", "Username is required.")
            return
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

    ttk.Button(form_frame, text="Create User", command=create_user_action).grid(row=0, column=4, padx=4, pady=2)

    selection_frame = ttk.Frame(manage_frame)
    selection_frame.pack(fill=tk.X, pady=4)

    ttk.Label(selection_frame, text="Select a user row, then:", style="Muted.TLabel", font=("Helvetica", 10)).pack(side=tk.LEFT, padx=4)

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
        if record is None:
            return
        role = record.get("role", "")
        username_display = record.get("username", "User")
        # If the requested state equals current state, inform and return
        if bool(record.get("enabled")) == bool(enabled):
            state_txt = "enabled" if enabled else "disabled"
            messagebox.showinfo("Status unchanged", f"{username_display} is already {state_txt}.")
            return
        # Never allow disabling admin accounts
        if role == "admin" and not enabled:
            messagebox.showerror("Disable", "Cannot disable an admin account.")
            return
        # Prevent disabling the last enabled user of a role
        if not enabled:
            enabled_counts = count_roles_enabled()
            if enabled_counts.get(role, 0) <= 1:
                messagebox.showerror("Disable", f"Cannot disable the sole {role} account.")
                return
        if record["id"] == user.get("id") and not enabled:
            messagebox.showwarning("Disable", "You cannot disable the account currently logged in.")
            return
        update_user_enabled(record["id"], enabled)
        refresh_users()

    def delete_selected() -> None:
        record = get_selected_user()
        if record is None:
            return
        role = record.get("role", "")
        # Block deleting admin accounts entirely
        if role == "admin":
            messagebox.showerror("Delete", "Cannot delete the admin account.")
            return
        # Prevent deleting the last remaining user of a role
        total_counts = count_roles_total()
        if total_counts.get(role, 0) <= 1:
            messagebox.showerror("Delete", f"Cannot delete the sole {role} account.")
            return
        if record["id"] == user.get("id"):
            messagebox.showwarning("Delete", "You cannot delete the account currently logged in.")
            return
        if not messagebox.askyesno("Delete user", "Are you sure? This is a hard delete."):
            return
        if not delete_user(record["id"]):
            messagebox.showerror("Delete", "Cannot delete user with existing assignments or logs. Disable instead.")
            return
        refresh_users()

    ttk.Button(selection_frame, text="Edit name", command=edit_username).pack(side=tk.LEFT, padx=4)
    ttk.Button(selection_frame, text="Enable", command=lambda: set_enabled(True)).pack(side=tk.LEFT, padx=4)
    ttk.Button(selection_frame, text="Disable", command=lambda: set_enabled(False)).pack(side=tk.LEFT, padx=4)
    ttk.Button(selection_frame, text="Delete", command=delete_selected).pack(side=tk.LEFT, padx=4)

    # ========== Tab 2: Chat ==========
    tab_chat = tk.Frame(notebook)
    notebook.add(tab_chat, text="Chat")

    def post_message_wrapper(content: str) -> None:
        post_message(user.get("id"), content)

    MessageBoard(
        tab_chat,
        post_callback=post_message_wrapper,
        fetch_callback=lambda: list_messages_lines(),
        current_user=user.get("username"),
    ).pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    return scroll



