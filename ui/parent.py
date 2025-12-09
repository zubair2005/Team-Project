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
    submit_feedback,
    list_daily_reports_for_camper,
)

"""
Parents can:

1. View camps their children are enrolled in (Schedules tab).
2. Submit simple yes/no consent forms with optional notes (Consent tab).
3. See daily reports for their campers and submit free‑text feedback (Progress tab).
"""

# construct and return parent dashboard widget
def build_dashboard(root: tk.Misc, user: Dict[str, Any], on_logout: Callable[[], None]) -> tk.Widget:

    frame = ttk.Frame(root, padding=10)

    header = ttk.Frame(frame)
    ttk.Label(header, text=f"Parent Dashboard - {user.get('username')}", font=("Helvetica", 14, "bold")).pack(side=tk.LEFT, padx=(0, 10))
    ttk.Button(header, text="Logout", command=on_logout).pack(side=tk.RIGHT)
    header.pack(fill=tk.X, pady=(0, 10))

    notebook = ttk.Notebook(frame)
    _build_schedules_tab(notebook, user)
    _build_consent_tab(notebook, user)
    _build_progress_tab(notebook, user)
    notebook.pack(fill=tk.BOTH, expand=True)

    return frame

# creates schedule tab showing camps for each camper
def _build_schedules_tab(notebook: ttk.Notebook, user: Dict[str, Any]) -> None:
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="Schedules")

    campers = list_parent_campers(user["id"])
    if not campers:
        ttk.Label(tab, text="No campers linked to your account.").pack(pady=10)
        return

    camper_names = [f"{c['first_name']} {c['last_name']} (ID {c['id']})" for c in campers]
    selected_camper = tk.StringVar(value=camper_names[0])

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

    ttk.Label(tab, text="Select Camper:").pack(anchor=tk.W)
    camper_menu = ttk.OptionMenu(tab, selected_camper, camper_names[0], *camper_names, command=update_camp_list)
    camper_menu.pack(anchor=tk.W, pady=(0, 5))

    columns = ("Name", "Location", "Start Date", "End Date", "Type")
    camp_tree = ttk.Treeview(tab, columns=columns, show="headings", height=8)
    for col in columns:
        camp_tree.heading(col, text=col)
        camp_tree.column(col, width=120)
    camp_tree.pack(fill=tk.BOTH, expand=True)

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

    canvas = tk.Canvas(tab)
    scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)

    scroll_frame.bind(
        "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    entries: List[Dict[str, Any]] = []

    for camper in campers:
        camper_id = camper["id"]
        camper_camps = list_camps_for_camper(camper_id)
        for camp in camper_camps:
            camp_id = camp["id"]
            existing = get_consent_form(user["id"], camper_id, camp_id)
            consent_var = tk.IntVar(value=existing["consent"] if existing else 0)
            notes_var = tk.StringVar(value=existing.get("notes", "") if existing else "")

            row = ttk.Frame(scroll_frame, padding=5)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=f"Camper: {camper['first_name']} {camper['last_name']} ").grid(row=0, column=0, sticky=tk.W)
            ttk.Label(row, text=f"Camp: {camp['name']} ({camp['start_date']} – {camp['end_date']}) ").grid(row=0, column=1, sticky=tk.W)
            ttk.Label(row, text="Consent: ").grid(row=0, column=2, sticky=tk.E)
            ttk.Radiobutton(row, text="Yes", variable=consent_var, value=1).grid(row=0, column=3)
            ttk.Radiobutton(row, text="No", variable=consent_var, value=0).grid(row=0, column=4)
            ttk.Label(row, text="Notes: ").grid(row=1, column=0, sticky=tk.E)
            notes_entry = ttk.Entry(row, textvariable=notes_var, width=40)
            notes_entry.grid(row=1, column=1, columnspan=3, sticky=tk.W)

            entries.append(
                {
                    "camper_id": camper_id,
                    "camp_id": camp_id,
                    "consent_var": consent_var,
                    "notes_var": notes_var,
                }
            )

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

    ttk.Button(tab, text="Save Consent Forms", command=save_all).pack(pady=5)

# creates the progress and feedback tab
def _build_progress_tab(notebook: ttk.Notebook, user: Dict[str, Any]) -> None:
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="Progress & Feedback")

    campers = list_parent_campers(user["id"])
    if not campers:
        ttk.Label(tab, text="No campers linked to your account.").pack(pady=10)
        return

    camper_names = [f"{c['first_name']} {c['last_name']} (ID {c['id']})" for c in campers]
    selected_camper = tk.StringVar(value=camper_names[0])

    top_row = ttk.Frame(tab)
    ttk.Label(top_row, text="Select Camper:").pack(side=tk.LEFT)
    camper_menu = ttk.OptionMenu(top_row, selected_camper, camper_names[0], *camper_names)
    camper_menu.pack(side=tk.LEFT, padx=(5, 0))
    top_row.pack(anchor=tk.W, pady=(0, 5))

    reports_frame = ttk.Frame(tab)
    reports_tree = ttk.Treeview(reports_frame, columns=("Date", "Leader", "Notes"), show="headings", height=10)
    for col, width in [("Date", 100), ("Leader", 120), ("Notes", 400)]:
        reports_tree.heading(col, text=col)
        reports_tree.column(col, width=width)
    reports_tree.pack(fill=tk.BOTH, expand=True)
    reports_frame.pack(fill=tk.BOTH, expand=True)

    feedback_frame = ttk.Frame(tab)
    ttk.Label(feedback_frame, text="Enter Feedback:").pack(anchor=tk.W)
    feedback_text = tk.Text(feedback_frame, height=4)
    feedback_text.pack(fill=tk.BOTH, expand=True)
    ttk.Button(
        feedback_frame,
        text="Submit Feedback",
        command=lambda: _submit_feedback_action(),
    ).pack(pady=(5, 0), anchor=tk.E)
    feedback_frame.pack(fill=tk.BOTH, expand=False, pady=(5, 0))

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

    selected_camper.trace_add("write", lambda *_: refresh_reports())
    refresh_reports()
