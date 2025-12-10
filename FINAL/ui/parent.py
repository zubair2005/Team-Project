"""Parent dashboard UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, Any, List, Optional

from services import (
    list_parent_campers,
    list_camps_for_camper,
    list_camps_for_parent,
    submit_consent_form,
    get_consent_form,
    get_all_consents_for_parent,
    submit_feedback,
    list_daily_reports_for_camper,
)
from ui.components import ScrollFrame
import datetime as _dt


# construct and return parent dashboard widget
def build_dashboard(root: tk.Misc, user: Dict[str, Any], on_logout: Callable[[], None]) -> tk.Widget:
    # Main container that will fill the window - use grid for better resize behavior
    root_frame = ttk.Frame(root)
    root_frame.grid_rowconfigure(1, weight=1)  # Notebook row expands
    root_frame.grid_columnconfigure(0, weight=1)  # Column expands

    # Header (fixed height)
    header = ttk.Frame(root_frame)
    header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

    ttk.Label(header, text=f"Parent Dashboard - {user.get('username')}",
              font=("Helvetica", 14, "bold")).pack(side=tk.LEFT)

    # Spacer to push logout button to right
    ttk.Frame(header).pack(side=tk.LEFT, fill=tk.X, expand=True)

    ttk.Button(header, text="Logout", command=on_logout).pack(side=tk.RIGHT)

    # Notebook that fills remaining space
    notebook = ttk.Notebook(root_frame)
    notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    # Build tabs
    _build_schedules_tab(notebook, user)

    # Only show Consent tab if any linked camper is under 18
    try:
        campers = list_parent_campers(user["id"])
    except Exception:
        campers = []

    def _is_under_18(dob_str: str) -> bool:
        try:
            dob = _dt.datetime.strptime(dob_str, "%Y-%m-%d").date()
            today = _dt.date.today()
            years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return years < 18
        except Exception:
            return False

    if any(_is_under_18(str(c.get("dob") or "")) for c in campers):
        _build_consent_tab(notebook, user)

    _build_leader_reports_tab(notebook, user)
    _build_feedback_tab(notebook, user)

    return root_frame

# creates schedule tab showing camps for each camper
def _build_schedules_tab(notebook: ttk.Notebook, user: Dict[str, Any]) -> None:
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="Schedules")

    campers = list_parent_campers(user["id"])
    if not campers:
        ttk.Label(tab, text="No campers linked to your account.").pack(pady=10)
        return

    camper_names = [f"{c['first_name']} {c['last_name']}" for c in campers]
    selected_camper = tk.StringVar(value=camper_names[0])

    # Main container
    container = ttk.Frame(tab)
    container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Top frame with combobox
    top = ttk.Frame(container)
    top.pack(fill=tk.X, pady=(0, 10))
    ttk.Label(top, text="Select Camper:").pack(side=tk.LEFT, padx=(0, 10))
    camper_menu = ttk.Combobox(top, textvariable=selected_camper, values=camper_names, state="readonly", width=40)
    camper_menu.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Treeview with scrollbars - use grid for proper resizing
    tree_container = ttk.Frame(container)
    tree_container.pack(fill=tk.BOTH, expand=True)
    tree_container.grid_rowconfigure(0, weight=1)
    tree_container.grid_columnconfigure(0, weight=1)

    columns = ("Name", "Location", "Start Date", "End Date", "Type")
    camp_tree = ttk.Treeview(tree_container, columns=columns, show="headings")

    # Scrollbars
    v_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=camp_tree.yview)
    h_scroll = ttk.Scrollbar(tree_container, orient="horizontal", command=camp_tree.xview)
    camp_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

    # Grid layout for proper resizing
    camp_tree.grid(row=0, column=0, sticky="nsew")
    v_scroll.grid(row=0, column=1, sticky="ns")
    h_scroll.grid(row=1, column=0, sticky="ew")

    for col in columns:
        camp_tree.heading(col, text=col)
        camp_tree.column(col, width=120, minwidth=100)

    def update_camp_list(*_args: Any) -> None:
        for row in camp_tree.get_children():
            camp_tree.delete(row)
        idx = camper_names.index(selected_camper.get())
        camper_id = campers[idx]["id"]
        camps = list_camps_for_camper(camper_id)
        for camp in camps:
            camp_tree.insert(
                "",
                tk.END,
                values=(camp["name"], camp["location"], camp["start_date"], camp["end_date"], camp["type"]),
            )

    camper_menu.bind("<<ComboboxSelected>>", lambda _e: update_camp_list())
    update_camp_list()


# creates consent form tab allowing parents to submit yes/no for consent
def _build_consent_tab(notebook: ttk.Notebook, user: Dict[str, Any]) -> None:
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="Consent")

    campers = list_parent_campers(user["id"])
    camps = list_camps_for_parent(user["id"])

    if not campers or not camps:
        ttk.Label(tab, text="No camps or campers associated with your account.").pack(pady=10)
        return

    # Filter out over-18 campers (they don't need consent)
    under_18_campers = [c for c in campers if _is_under_18(str(c.get("dob") or ""))]
    
    if not under_18_campers:
        ttk.Label(tab, text="All linked campers are 18 or older. No consent forms needed.").pack(pady=10)
        return

    # Batch load all consents for performance
    all_consents = get_all_consents_for_parent(user["id"])

    # Create main container
    main_container = ttk.Frame(tab)
    main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Canvas for scrolling
    canvas = tk.Canvas(main_container, highlightthickness=0, bd=0)
    scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    # Configure canvas
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

    def on_canvas_configure(event):
        # Update scroll region and frame width
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(canvas_window, width=event.width)

    canvas.bind("<Configure>", on_canvas_configure)

    # Pack widgets
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.configure(yscrollcommand=scrollbar.set)

    entries: List[Dict[str, Any]] = []
    for camper in under_18_campers:
        camper_id = camper["id"]
        camper_camps = list_camps_for_camper(camper_id)
        for camp in camper_camps:
            camp_id = camp["id"]
            # Use batch-loaded consents instead of individual query
            existing = all_consents.get((camper_id, camp_id))
            consent_var = tk.IntVar(value=existing["consent"] if existing else 0)
            notes_var = tk.StringVar(value=(existing.get("notes", "") if existing else ""))

            # Each consent item in a framed box
            frame = ttk.Frame(scrollable_frame, padding=10, relief="groove", borderwidth=1)
            frame.pack(fill=tk.X, pady=5, padx=5)

            # Camper info
            ttk.Label(frame, text=f"Camper: {camper['first_name']} {camper['last_name']}",
                      font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky=tk.W)
            ttk.Label(frame, text=f"Camp: {camp['name']} ({camp['start_date']} – {camp['end_date']})").grid(row=0,
                                                                                                            column=1,
                                                                                                            sticky=tk.W,
                                                                                                            padx=(20,
                                                                                                                  0))

            # Consent buttons
            ttk.Label(frame, text="Consent:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
            ttk.Radiobutton(frame, text="Yes", variable=consent_var, value=1).grid(row=1, column=1, sticky=tk.W,
                                                                                   padx=(0, 10))
            ttk.Radiobutton(frame, text="No", variable=consent_var, value=0).grid(row=1, column=2, sticky=tk.W)

            # Notes
            ttk.Label(frame, text="Notes:").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
            notes_entry = ttk.Entry(frame, textvariable=notes_var, width=50)
            notes_entry.grid(row=2, column=1, columnspan=2, sticky=tk.W + tk.E, pady=(10, 0), padx=(0, 10))

            # Make columns expand
            frame.grid_columnconfigure(1, weight=1)
            frame.grid_columnconfigure(2, weight=0)

            entries.append({
                "camper_id": camper_id,
                "camp_id": camp_id,
                "consent_var": consent_var,
                "notes_var": notes_var,
            })

    # Save button at bottom (outside scroll)
    button_frame = ttk.Frame(tab)
    button_frame.pack(fill=tk.X, pady=10)

    def save_all() -> None:
        for entry in entries:
            consent = bool(entry["consent_var"].get())
            notes = entry["notes_var"].get().strip()
            submit_consent_form(
                parent_user_id=user["id"],
                camper_id=entry["camper_id"],
                camp_id=entry["camp_id"],
                consent=consent,
                notes=notes,
            )
        messagebox.showinfo("Consent Saved", "Consent forms have been saved successfully.")

    ttk.Button(button_frame, text="Save All Consent Forms", command=save_all).pack(pady=5)


# creates the leader reports tab (read-only view of daily reports)
def _build_leader_reports_tab(notebook: ttk.Notebook, user: Dict[str, Any]) -> None:
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="Leader Reports")

    campers = list_parent_campers(user["id"])
    if not campers:
        ttk.Label(tab, text="No campers linked to your account.").pack(pady=10)
        return

    camper_names = [f"{c['first_name']} {c['last_name']}" for c in campers]
    
    # Main container
    container = ttk.Frame(tab)
    container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Top row with selector
    top_row = ttk.Frame(container)
    top_row.pack(fill=tk.X, pady=(0, 10))
    ttk.Label(top_row, text="Select Camper:").pack(side=tk.LEFT)
    selected_camper = tk.StringVar(value=camper_names[0])
    camper_menu = ttk.Combobox(top_row, textvariable=selected_camper, values=camper_names, state="readonly", width=38)
    camper_menu.pack(side=tk.LEFT, padx=(5, 0))

    # Description label
    ttk.Label(container, text="Daily reports submitted by leaders for your camper's camps:",
              style="Muted.TLabel").pack(anchor=tk.W, pady=(0, 5))

    # Reports treeview with scrollbars - use grid for proper resizing
    tree_container = ttk.Frame(container)
    tree_container.pack(fill=tk.BOTH, expand=True)
    tree_container.grid_rowconfigure(0, weight=1)
    tree_container.grid_columnconfigure(0, weight=1)
    
    reports_tree = ttk.Treeview(tree_container, columns=("Date", "Leader", "Notes"), show="headings")
    v_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=reports_tree.yview)
    h_scroll = ttk.Scrollbar(tree_container, orient="horizontal", command=reports_tree.xview)
    reports_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
    
    for col, width in [("Date", 100), ("Leader", 120), ("Notes", 500)]:
        reports_tree.heading(col, text=col)
        reports_tree.column(col, width=width, minwidth=80)
    
    # Grid layout for proper resizing
    reports_tree.grid(row=0, column=0, sticky="nsew")
    v_scroll.grid(row=0, column=1, sticky="ns")
    h_scroll.grid(row=1, column=0, sticky="ew")

    def refresh_reports(*_args: Any) -> None:
        for row in reports_tree.get_children():
            reports_tree.delete(row)
        camper_idx = camper_names.index(selected_camper.get())
        camper_id = campers[camper_idx]["id"]
        reports = list_daily_reports_for_camper(camper_id)
        for r in reports:
            reports_tree.insert(
                "",
                tk.END,
                values=(r.get("date", ""), r.get("leader", ""), r.get("notes", "")),
            )

    camper_menu.bind("<<ComboboxSelected>>", lambda _e: refresh_reports())
    selected_camper.trace_add("write", lambda *_: refresh_reports())
    refresh_reports()


# creates the feedback tab (parent can submit feedback)
def _build_feedback_tab(notebook: ttk.Notebook, user: Dict[str, Any]) -> None:
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="Submit Feedback")

    campers = list_parent_campers(user["id"])
    if not campers:
        ttk.Label(tab, text="No campers linked to your account.").pack(pady=10)
        return

    camper_names = [f"{c['first_name']} {c['last_name']}" for c in campers]
    
    # Main container
    container = ttk.Frame(tab)
    container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Top row with selector
    top_row = ttk.Frame(container)
    top_row.pack(fill=tk.X, pady=(0, 10))
    ttk.Label(top_row, text="Select Camper:").pack(side=tk.LEFT)
    selected_camper = tk.StringVar(value=camper_names[0])
    camper_menu = ttk.Combobox(top_row, textvariable=selected_camper, values=camper_names, state="readonly", width=38)
    camper_menu.pack(side=tk.LEFT, padx=(5, 0))

    # Feedback entry
    ttk.Label(container, text="Enter your feedback about the camp experience:",
              font=("Helvetica", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
    
    feedback_text = tk.Text(container, height=8, wrap=tk.WORD)
    feedback_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

    def _submit_feedback_action() -> None:
        text = feedback_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("No feedback", "Please enter feedback before submitting.")
            return
        camper_idx = camper_names.index(selected_camper.get())
        camper_id = campers[camper_idx]["id"]
        camps = list_camps_for_camper(camper_id)
        camp_id = camps[-1]["id"] if camps else None
        if camp_id is None:
            messagebox.showerror("No camp", "This camper is not assigned to any camp.")
            return
        submit_feedback(
            parent_user_id=user["id"],
            camper_id=camper_id,
            camp_id=camp_id,
            feedback=text,
        )
        feedback_text.delete("1.0", tk.END)
        messagebox.showinfo("Feedback submitted", "Your feedback has been recorded.")

    ttk.Button(container, text="Submit Feedback", command=_submit_feedback_action).pack(anchor=tk.E)


