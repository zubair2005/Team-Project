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


def _is_under_18(dob_str: str) -> bool:
    """Check if a person is under 18 based on DOB string (YYYY-MM-DD)."""
    try:
        dob = _dt.datetime.strptime(dob_str, "%Y-%m-%d").date()
        today = _dt.date.today()
        years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return years < 18
    except Exception:
        return False


# construct and return parent dashboard widget
def build_dashboard(root: tk.Misc, user: Dict[str, Any], on_logout: Callable[[], None]) -> tk.Widget:
    # Main container that will fill the window - use grid for better resize behavior - ensures full-screen expansion
    root_frame = ttk.Frame(root)
    root_frame.grid_rowconfigure(1, weight=1)  # Content row expands vertically
    root_frame.grid_columnconfigure(0, weight=1)  # Column expands horizontally

    # Fixed header bar (always stays in view and anchored to the right)
    header = ttk.Frame(root_frame)
    header.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
    header.grid_columnconfigure(1, weight=1)  # spacer column expands

    ttk.Label(header, text=f"Parent Dashboard - {user.get('username')}",
              font=("Helvetica", 14, "bold")).grid(row=0, column=0, sticky="w")
    ttk.Frame(header).grid(row=0, column=1, sticky="ew")  # spacer
    ttk.Button(header, text="Logout", command=on_logout).grid(row=0, column=2, sticky="e")

    # Scrollable content below header (with horizontal scroll)
    scroll = ScrollFrame(root_frame, enable_horizontal=True)
    scroll.grid(row=1, column=0, sticky="nsew")
    container = scroll.content

    # Notebook that fills remaining space
    notebook = ttk.Notebook(container)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
    # Ensure notebook expands its tabs to fill available space
    container.pack_propagate(True)

    # Build tabs
    _build_schedules_tab(notebook, user)

    # Only show Consent tab if any linked camper is under 18
    try:
        campers = list_parent_campers(user["id"])
    except Exception:
        campers = []

    if any(_is_under_18(str(c.get("dob") or "")) for c in campers):
        _build_consent_tab(notebook, user)

    _build_leader_reports_tab(notebook, user)

    return root_frame

# creates schedule tab showing camps for each camper
def _build_schedules_tab(notebook: ttk.Notebook, user: Dict[str, Any]) -> None:
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="Schedules")
    # Configure tab to expand properly
    tab.grid_rowconfigure(0, weight=1)
    tab.grid_columnconfigure(0, weight=1)

    campers = list_parent_campers(user["id"])
    if not campers:
        ttk.Label(tab, text="No campers linked to your account.").grid(row=0, column=0, pady=10)
        return

    camper_names = [f"{c['first_name']} {c['last_name']}" for c in campers]
    selected_camper = tk.StringVar(value=camper_names[0])

    # Main container
    container = ttk.Frame(tab)
    container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    # Configure container to expand
    container.grid_rowconfigure(1, weight=1)  # Table row expands
    container.grid_columnconfigure(0, weight=1)

    # Top frame with combobox
    top = ttk.Frame(container)
    top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    ttk.Label(top, text="Select Camper:").pack(side=tk.LEFT, padx=(0, 10))
    camper_menu = ttk.Combobox(top, textvariable=selected_camper, values=camper_names, state="readonly", width=40)
    camper_menu.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Camps table - page-level scrolling only
    columns = ("Name", "Location", "Start Date", "End Date", "Type")
    camp_tree = ttk.Treeview(container, columns=columns, show="headings")
    camp_tree.grid(row=1, column=0, sticky="nsew")

    for col in columns:
        camp_tree.heading(col, text=col)
        camp_tree.column(col, width=120, minwidth=100, stretch=True)

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
    # Configure tab to expand properly
    tab.grid_rowconfigure(0, weight=1)
    tab.grid_columnconfigure(0, weight=1)

    campers = list_parent_campers(user["id"])
    if not campers:
        ttk.Label(tab, text="No campers linked to your account.").grid(row=0, column=0, pady=10)
        return

    camper_names = [f"{c['first_name']} {c['last_name']}" for c in campers]
    
    # Main container
    container = ttk.Frame(tab)
    container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    # Configure container to expand
    container.grid_rowconfigure(0, weight=0)  # Top row (fixed)
    container.grid_rowconfigure(1, weight=0)  # Description label (fixed)
    container.grid_rowconfigure(2, weight=3)  # Reports table expands (more space)
    container.grid_rowconfigure(3, weight=0)  # Detail label (fixed)
    container.grid_rowconfigure(4, weight=1)  # Detail pane (less space)
    container.grid_columnconfigure(0, weight=1)
    
    # Top row with selector
    top_row = ttk.Frame(container)
    top_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    ttk.Label(top_row, text="Select Camper:").pack(side=tk.LEFT)
    selected_camper = tk.StringVar(value=camper_names[0])
    camper_menu = ttk.Combobox(top_row, textvariable=selected_camper, values=camper_names, state="readonly", width=38)
    camper_menu.pack(side=tk.LEFT, padx=(5, 0))

    # Description label
    ttk.Label(container, text="Daily reports submitted by leaders for your camper's camps:",
              style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 5))

    # Reports table - page-level scrolling only
    reports_tree = ttk.Treeview(container, columns=("Date", "Leader", "Notes"), show="headings")
    reports_tree.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
    
    reports_tree.heading("Date", text="Date")
    reports_tree.heading("Leader", text="Leader")
    reports_tree.heading("Notes", text="Notes (click row to view full message)")
    reports_tree.column("Date", width=100, minwidth=80, stretch=False)
    reports_tree.column("Leader", width=120, minwidth=100, stretch=False)
    reports_tree.column("Notes", width=500, minwidth=300, stretch=True)
    
    # Detail view for full message
    ttk.Label(container, text="Full Message:", font=("Helvetica", 10, "bold")).grid(row=3, column=0, sticky="w", pady=(0, 4))
    detail_frame = ttk.Frame(container, style="Card.TFrame", padding=5)
    detail_frame.grid(row=4, column=0, sticky="nsew")
    
    detail_scroll = ttk.Scrollbar(detail_frame, orient="vertical")
    detail_text = tk.Text(detail_frame, height=4, wrap="word", state="disabled", yscrollcommand=detail_scroll.set)
    detail_scroll.config(command=detail_text.yview)
    detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def refresh_reports(*_args: Any) -> None:
        for row in reports_tree.get_children():
            reports_tree.delete(row)
        # Clear detail view
        detail_text.config(state="normal")
        detail_text.delete("1.0", tk.END)
        detail_text.insert("1.0", "Select a report to view the full message.")
        detail_text.config(state="disabled")
        
        camper_idx = camper_names.index(selected_camper.get())
        camper_id = campers[camper_idx]["id"]
        reports = list_daily_reports_for_camper(camper_id)
        
        # Zebra-striping
        from ui.theme import get_palette, tint
        palette = get_palette(reports_tree)
        reports_tree.tag_configure("even", background=palette["surface"])
        reports_tree.tag_configure("odd", background=tint(palette["surface"], -0.03))
        
        for idx, r in enumerate(reports):
            # Truncate notes for table display
            notes = r.get("notes", "")
            display_notes = (notes[:60] + "...") if len(notes) > 60 else notes
            reports_tree.insert(
                "",
                tk.END,
                values=(r.get("date", ""), r.get("leader", ""), display_notes),
                tags=("odd",) if (idx % 2 == 1) else ("even",)
            )
    
    def show_report_detail(event=None) -> None:
        selection = reports_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        values = reports_tree.item(item_id, "values")
        if len(values) < 3:
            return
        date, leader, display_notes = values[0], values[1], values[2]
        
        # Get full notes from original data
        camper_idx = camper_names.index(selected_camper.get())
        camper_id = campers[camper_idx]["id"]
        reports = list_daily_reports_for_camper(camper_id)
        matching_report = next((r for r in reports if r.get("date") == date and r.get("leader") == leader), None)
        
        if matching_report:
            detail_text.config(state="normal")
            detail_text.delete("1.0", tk.END)
            detail_text.insert("1.0", f"Date: {date}\nLeader: {leader}\n\n{matching_report.get('notes', '')}")
            detail_text.config(state="disabled")
    
    reports_tree.bind("<<TreeviewSelect>>", show_report_detail)
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


