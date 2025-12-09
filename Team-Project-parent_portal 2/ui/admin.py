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
    list_notifications_for_user,
    mark_notifications_read,
    add_parent_camper,
    list_parent_campers,
    list_campers,

)
from ui.components import MessageBoard, ScrollFrame
from ui.theme import get_palette, tint

def _build_parent_camper_tab(container: tk.Widget) -> None:
        """Admin UI to link parent users to campers."""

        # Top row: selectors
        selector_frame = ttk.Frame(container)
        selector_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(selector_frame, text="Parent:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        ttk.Label(selector_frame, text="Camper:").grid(row=0, column=2, sticky="w", padx=(10, 5))

        # Load parents and campers
        parents = [u for u in list_users() if u["role"] == "parent" and u["enabled"]]
        campers = list_campers()

        parent_labels = [f'{p["username"]} (id={p["id"]})' for p in parents]
        camper_labels = [f'{c["first_name"]} {c["last_name"]} (id={c["id"]})' for c in campers]

        parent_label_to_id = {label: p["id"] for label, p in zip(parent_labels, parents)}
        camper_label_to_id = {label: c["id"] for label, c in zip(camper_labels, campers)}

        parent_var = tk.StringVar()
        camper_var = tk.StringVar()

        parent_cb = ttk.Combobox(
            selector_frame,
            textvariable=parent_var,
            values=parent_labels,
            state="readonly",
            width=30,
        )
        parent_cb.grid(row=0, column=1, sticky="w")

        camper_cb = ttk.Combobox(
            selector_frame,
            textvariable=camper_var,
            values=camper_labels,
            state="readonly",
            width=30,
        )
        camper_cb.grid(row=0, column=3, sticky="w")

        # Table of linked campers for the selected parent
        list_frame = ttk.Frame(container)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        ttk.Label(list_frame, text="Linked campers for selected parent:").pack(anchor=tk.W)

        columns = ("camper",)
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        tree.heading("camper", text="Camper")
        tree.column("camper", width=320, anchor=tk.W)
        tree.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        def _refresh_links(*_args) -> None:
            """Reload campers linked to the selected parent."""
            tree.delete(*tree.get_children())
            parent_label = parent_var.get()
            if not parent_label:
                return
            parent_id = parent_label_to_id[parent_label]
            linked = list_parent_campers(parent_id)
            for c in linked:
                camper_name = f'{c["first_name"]} {c["last_name"]} (id={c["id"]})'
                tree.insert("", tk.END, values=(camper_name,))

        def _link_parent_camper() -> None:
            parent_label = parent_var.get()
            camper_label = camper_var.get()
            if not parent_label or not camper_label:
                messagebox.showwarning("Missing selection", "Please select both a parent and a camper.")
                return
            parent_id = parent_label_to_id[parent_label]
            camper_id = camper_label_to_id[camper_label]
            ok = add_parent_camper(parent_id, camper_id)
            if not ok:
                messagebox.showerror("Error", "Failed to link parent and camper.")
                return
            messagebox.showinfo("Linked", "Parent and camper have been linked.")
            _refresh_links()

        link_btn = ttk.Button(selector_frame, text="Link Parent to Camper", command=_link_parent_camper)
        link_btn.grid(row=0, column=4, padx=(10, 0))

        # Refresh table when parent changes
        parent_cb.bind("<<ComboboxSelected>>", _refresh_links)

def build_dashboard(root: tk.Misc, user: Dict[str, str], logout_callback: Callable[[], None]) -> tk.Frame:

    def _open_notifications():
        win = tk.Toplevel()
        win.title("Notifications")

        notifications = list_notifications_for_user(user["id"])
        if not notifications:
            ttk.Label(win, text="No notifications.").pack(padx=10, pady=10)
            return

        for n in notifications:
            ttk.Label(
                win,
                text=f"[{n['created_at']}] {n['message']}",
                wraplength=400,
                justify="left",
            ).pack(anchor=tk.W, padx=10, pady=2)

        ttk.Button(
            win,
            text="Mark all as read",
            command=lambda: (mark_notifications_read(user["id"]), win.destroy()),
        ).pack(pady=10)
    
    scroll = ScrollFrame(root)
    container = scroll.content

    header = ttk.Frame(container)
    header.pack(fill=tk.X, pady=8, padx=10)

    tk.Label(header, text="Administrator Dashboard", font=("Helvetica", 16, "bold")).pack(side=tk.LEFT)

    ttk.Button(header, text="Notifications", command=_open_notifications).pack(side=tk.RIGHT, padx=(0, 5))

    ttk.Button(header, text="Logout", command=logout_callback).pack(side=tk.RIGHT)

    notebook = ttk.Notebook(container)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    # ========== Tab 1: User Management ==========
    tab_users = tk.Frame(notebook)
    notebook.add(tab_users, text="User Management")

    ttk.Label(tab_users, text="User Accounts", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, padx=10, pady=(10, 2))
    manage_frame = ttk.Frame(tab_users, style="Card.TFrame", padding=10)
    manage_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

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
        values=["leader", "coordinator", "parent"],
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
        if record["role"] in {"admin", "coordinator"} and not enabled:
            messagebox.showerror("Disable", f"Cannot disable the sole {record['role']} account.")
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
        if record["role"] in {"admin", "coordinator"}:
            messagebox.showerror(
                "Delete",
                f"Cannot delete the only {record['role']} account. Disable it instead if necessary.",
            )
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

    # ========== Tab 2: Parent-Camper Links ==========

    tab_links = tk.Frame(notebook)
    notebook.add(tab_links, text="Parent–Camper Links")
    _build_parent_camper_tab(tab_links) 
    
    # ========== Tab 3: Chat ==========
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



