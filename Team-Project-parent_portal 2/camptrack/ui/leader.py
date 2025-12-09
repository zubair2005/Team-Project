"""Leader dashboard UI with tabbed navigation."""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Callable, Dict, Optional

from services import (
    assign_campers_to_activity,
    assign_leader_to_camp,
    create_activity,
    delete_activity,
    get_leader_statistics,
    import_campers_from_csv,
    list_activity_campers,
    list_available_camps_for_leader,
    list_camp_activities,
    list_camp_campers,
    list_daily_reports,
    list_leader_assignments,
    list_messages_lines,
    get_leader_pay_summary,
    post_message,
    remove_leader_assignment,
    save_daily_report,
    update_camp_camper_food,
)
from ui.components import MessageBoard, Table


def build_dashboard(root: tk.Misc, user: Dict[str, str], logout_callback: Callable[[], None]) -> tk.Frame:
    container = tk.Frame(root)

    header = tk.Frame(container)
    header.pack(fill=tk.X, padx=10, pady=8)

    tk.Label(header, text="Leader Dashboard", font=("Helvetica", 16, "bold")).pack(side=tk.LEFT)
    tk.Button(header, text="Logout", command=logout_callback).pack(side=tk.RIGHT)

    notebook = ttk.Notebook(container)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    leader_id = user.get("id")

    # ========== Tab 1: Camps & Pay ==========
    tab_camps = tk.Frame(notebook)
    notebook.add(tab_camps, text="Camps & Pay")

    pay_frame = tk.LabelFrame(tab_camps, text="Pay summary", padx=10, pady=10)
    pay_frame.pack(fill=tk.X, padx=10, pady=6)

    total_pay_var = tk.StringVar(value="Total: 0.00")
    total_pay_label = tk.Label(pay_frame, textvariable=total_pay_var, font=("Helvetica", 12, "bold"))
    total_pay_label.pack(side=tk.LEFT, padx=6)

    per_camp_text = tk.Text(pay_frame, height=3, width=60, state="disabled")
    per_camp_text.pack(side=tk.LEFT, padx=6)

    def refresh_pay_summary() -> None:
        summary = get_leader_pay_summary(leader_id)
        total_pay_var.set(f"Total: {summary['total_pay']:.2f}")
        per_camp_text.config(state="normal")
        per_camp_text.delete("1.0", tk.END)
        if not summary["per_camp"]:
            per_camp_text.insert(tk.END, "No camps assigned yet.\n")
        else:
            for item in summary["per_camp"]:
                per_camp_text.insert(
                    tk.END,
                    f"{item['camp_name']}: {item['days']} day(s) • {item['pay']:.2f} units\n",
                )
        per_camp_text.config(state="disabled")

    assignments_frame = tk.LabelFrame(tab_camps, text="My camp assignments", padx=10, pady=10)
    assignments_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    columns = ("Camp", "Location", "Area", "Start", "End")
    assignments_table = ttk.Treeview(assignments_frame, columns=columns, show="headings", height=6)
    for col in columns:
        assignments_table.heading(col, text=col)
        assignments_table.column(col, width=140)
    assignments_table.column("Camp", width=180)
    assignments_table.pack(fill=tk.BOTH, expand=True, pady=4)

    def refresh_assignments() -> None:
        assignments_table.delete(*assignments_table.get_children())
        for record in list_leader_assignments(leader_id):
            assignments_table.insert(
                "",
                tk.END,
                iid=record["id"],
                values=(
                    record["name"],
                    record["location"],
                    record.get("area", ""),
                    record["start_date"],
                    record["end_date"],
                ),
            )
        refresh_available_camps()
        refresh_pay_summary()

    tk.Label(assignments_frame, text="Available camps (no conflicts)").pack(pady=(10, 4))
    available_table = ttk.Treeview(assignments_frame, columns=columns, show="headings", height=5)
    for col in columns:
        available_table.heading(col, text=col)
        available_table.column(col, width=140)
    available_table.column("Camp", width=180)
    available_table.pack(fill=tk.BOTH, expand=True, pady=4)

    def refresh_available_camps() -> None:
        available_table.delete(*available_table.get_children())
        for camp in list_available_camps_for_leader(leader_id):
            available_table.insert(
                "",
                tk.END,
                iid=camp["id"],
                values=(
                    camp["name"],
                    camp["location"],
                    camp.get("area", ""),
                    camp["start_date"],
                    camp["end_date"],
                ),
            )

    def assign_selected_camp() -> None:
        selection = available_table.selection()
        if not selection:
            messagebox.showinfo("Assign", "Select a camp from the available list.")
            return
        camp_id = int(selection[0])
        if not assign_leader_to_camp(leader_id, camp_id):
            messagebox.showerror(
                "Assign",
                "Unable to assign camp. It may conflict with existing assignments.",
            )
            return
        refresh_assignments()

    def remove_assignment() -> None:
        selection = assignments_table.selection()
        if not selection:
            messagebox.showinfo("Remove", "Select an assignment first.")
            return
        assignment_id = int(selection[0])
        if not messagebox.askyesno("Remove", "Remove this assignment?"):
            return
        if not remove_leader_assignment(assignment_id, leader_id):
            messagebox.showerror("Remove", "Unable to remove assignment.")
            return
        refresh_assignments()

    action_row = tk.Frame(assignments_frame)
    action_row.pack(fill=tk.X, pady=4)
    tk.Button(action_row, text="Assign selected camp", command=assign_selected_camp).pack(side=tk.LEFT, padx=4)
    tk.Button(action_row, text="Remove selected assignment", command=remove_assignment).pack(side=tk.LEFT, padx=4)

    refresh_assignments()

    # ========== Tab 2: Campers ==========
    tab_campers = tk.Frame(notebook)
    notebook.add(tab_campers, text="Campers")

    tk.Label(tab_campers, text="Select an assignment from 'Camps & Pay' tab first", fg="#666666", font=("Helvetica", 10, "italic")).pack(pady=4)

    campers_frame = tk.LabelFrame(tab_campers, text="Campers in selected camp", padx=10, pady=10)
    campers_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    campers_table = Table(campers_frame, columns=["Name", "DOB", "Emergency", "Food units/day"])
    campers_table.pack(fill=tk.BOTH, expand=True, pady=4)

    def load_campers_for_selection() -> None:
        selection = assignments_table.selection()
        campers_table.load_rows([])
        if not selection:
            return
        assignment_id = int(selection[0])
        record = next((rec for rec in list_leader_assignments(leader_id) if rec["id"] == assignment_id), None)
        if record is None:
            return
        campers = list_camp_campers(record["camp_id"])
        campers_table.load_rows(
            [
                (
                    f"{row['first_name']} {row['last_name']}",
                    row["dob"],
                    row["emergency_contact"],
                    row["food_units_per_day"],
                )
                for row in campers
            ]
        )

    assignments_table.bind("<<TreeviewSelect>>", lambda _evt: load_campers_for_selection())

    def import_csv() -> None:
        selection = assignments_table.selection()
        if not selection:
            messagebox.showinfo("Import", "Select an assignment from 'Camps & Pay' tab first.")
            return
        assignment_id = int(selection[0])
        assignment = next((rec for rec in list_leader_assignments(leader_id) if rec["id"] == assignment_id), None)
        if assignment is None:
            messagebox.showerror("Import", "Assignment not found.")
            return
        file_path = filedialog.askopenfilename(
            title="Select campers CSV",
            filetypes=[("CSV Files", "*.csv")],
        )
        if not file_path:
            return
        try:
            result = import_campers_from_csv(assignment["camp_id"], file_path)
        except Exception as exc:
            messagebox.showerror("Import", f"Failed to import: {exc}")
            return
        messagebox.showinfo(
            "Import complete",
            f"Created: {result['created']}\nLinked: {result['linked']}\nDuplicates skipped: {result['duplicates']}\nErrors: {len(result['errors'])}",
        )
        load_campers_for_selection()

    def adjust_food_units() -> None:
        selection = assignments_table.selection()
        if not selection:
            messagebox.showinfo("Food", "Select an assignment from 'Camps & Pay' tab first.")
            return
        assignment_id = int(selection[0])
        assignment = next((rec for rec in list_leader_assignments(leader_id) if rec["id"] == assignment_id), None)
        if assignment is None:
            return
        campers = list_camp_campers(assignment["camp_id"])
        if not campers:
            messagebox.showinfo("Food", "No campers to adjust.")
            return

        dialog = tk.Toplevel(container)
        dialog.title("Adjust food units per day")
        dialog.geometry("420x360")

        listbox = tk.Listbox(dialog)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for idx, camper in enumerate(campers):
            listbox.insert(
                tk.END,
                f"{camper['first_name']} {camper['last_name']} - {camper['food_units_per_day']} units",
            )

        def update_selected() -> None:
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            camper = campers[idx]
            amount = simpledialog.askinteger(
                "Food units",
                f"Units per day for {camper['first_name']} {camper['last_name']}",
                minvalue=0,
                initialvalue=camper["food_units_per_day"],
                parent=dialog,
            )
            if amount is None:
                return
            update_camp_camper_food(camper["id"], amount)
            campers[idx]["food_units_per_day"] = amount
            listbox.delete(idx)
            listbox.insert(
                idx,
                f"{camper['first_name']} {camper['last_name']} - {amount} units",
            )
            load_campers_for_selection()

        tk.Button(dialog, text="Update", command=update_selected).pack(pady=6)
        tk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=6)

    action_row = tk.Frame(campers_frame)
    action_row.pack(fill=tk.X, pady=4)
    tk.Button(action_row, text="Import campers from CSV", command=import_csv).pack(side=tk.LEFT, padx=4)
    tk.Button(action_row, text="Adjust food units", command=adjust_food_units).pack(side=tk.LEFT, padx=4)

    # ========== Tab 3: Activities ==========
    tab_activities = tk.Frame(notebook)
    notebook.add(tab_activities, text="Activities")

    tk.Label(tab_activities, text="Select an assignment from 'Camps & Pay' tab first", fg="#666666", font=("Helvetica", 10, "italic")).pack(pady=4)

    activities_frame = tk.LabelFrame(tab_activities, text="Activities for selected camp", padx=10, pady=10)
    activities_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    activities_table = Table(activities_frame, columns=["Name", "Date", "Participants"])
    activities_table.pack(fill=tk.BOTH, expand=True, pady=4)

    def load_activities() -> None:
        selection = assignments_table.selection()
        activities_table.load_rows([])
        if not selection:
            return
        assignment_id = int(selection[0])
        assignment = next((rec for rec in list_leader_assignments(leader_id) if rec["id"] == assignment_id), None)
        if assignment is None:
            return
        activities = list_camp_activities(assignment["camp_id"])
        rows = []
        for activity in activities:
            participants = list_activity_campers(activity["id"])
            rows.append((activity["name"], activity["date"], len(participants)))
        activities_table.load_rows(rows)

    def create_activity_dialog() -> None:
        selection = assignments_table.selection()
        if not selection:
            messagebox.showinfo("Activity", "Select an assignment from 'Camps & Pay' tab first.")
            return
        assignment_id = int(selection[0])
        assignment = next((rec for rec in list_leader_assignments(leader_id) if rec["id"] == assignment_id), None)
        if assignment is None:
            return

        dialog = tk.Toplevel(container)
        dialog.title("Create activity")
        dialog.geometry("360x220")

        tk.Label(dialog, text="Activity name").pack(pady=4)
        name_var = tk.StringVar()
        tk.Entry(dialog, textvariable=name_var, width=30).pack(pady=4)

        tk.Label(dialog, text="Date (YYYY-MM-DD)").pack(pady=4)
        date_var = tk.StringVar()
        tk.Entry(dialog, textvariable=date_var, width=20).pack(pady=4)

        def save() -> None:
            name = name_var.get().strip()
            date = date_var.get().strip()
            if not name or not date:
                messagebox.showwarning("Activity", "Name and date required.")
                return
            # Validate date format
            try:
                import pandas as pd
                pd.to_datetime(date)
            except Exception:
                messagebox.showerror("Activity", "Invalid date format. Use YYYY-MM-DD.")
                return
            if not create_activity(assignment["camp_id"], name, date):
                messagebox.showerror("Activity", "Failed to create activity.")
                return
            dialog.destroy()
            load_activities()

        tk.Button(dialog, text="Create", command=save).pack(pady=8)
        tk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=4)

    def delete_selected_activity() -> None:
        selection_assignment = assignments_table.selection()
        if not selection_assignment:
            messagebox.showinfo("Activity", "Select an assignment from 'Camps & Pay' tab first.")
            return
        assignment_id = int(selection_assignment[0])
        assignment = next((rec for rec in list_leader_assignments(leader_id) if rec["id"] == assignment_id), None)
        if assignment is None:
            return

        selection = activities_table.selection()
        if not selection:
            messagebox.showinfo("Activity", "Select an activity to delete.")
            return
        index = activities_table.index(selection[0])
        activities = list_camp_activities(assignment["camp_id"])
        if index >= len(activities):
            return
        activity = activities[index]
        if not messagebox.askyesno("Activity", "Delete this activity?"):
            return
        if not delete_activity(activity["id"], assignment["camp_id"]):
            messagebox.showerror("Activity", "Failed to delete.")
            return
        load_activities()

    def assign_campers_to_selected_activity() -> None:
        selection_assignment = assignments_table.selection()
        if not selection_assignment:
            messagebox.showinfo("Activity", "Select an assignment from 'Camps & Pay' tab first.")
            return
        assignment_id = int(selection_assignment[0])
        assignment = next((rec for rec in list_leader_assignments(leader_id) if rec["id"] == assignment_id), None)
        if assignment is None:
            return

        selection_activity = activities_table.selection()
        if not selection_activity:
            messagebox.showinfo("Activity", "Select an activity first.")
            return
        index = activities_table.index(selection_activity[0])
        activities = list_camp_activities(assignment["camp_id"])
        if index >= len(activities):
            return
        activity = activities[index]

        campers = list_camp_campers(assignment["camp_id"])
        if not campers:
            messagebox.showinfo("Activity", "No campers available to assign.")
            return

        dialog = tk.Toplevel(container)
        dialog.title("Bulk assign campers to activity")
        dialog.geometry("400x360")

        tk.Label(dialog, text="Select multiple campers (Ctrl/Cmd + click)", font=("Helvetica", 10, "italic")).pack(pady=4)

        listbox = tk.Listbox(dialog, selectmode=tk.MULTIPLE)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for camper in campers:
            listbox.insert(tk.END, f"{camper['first_name']} {camper['last_name']}")

        def assign_selected() -> None:
            sel_indices = listbox.curselection()
            if not sel_indices:
                messagebox.showinfo("Assign", "Select at least one camper.")
                return
            camper_ids = [campers[idx]["id"] for idx in sel_indices]
            assign_campers_to_activity(activity["id"], camper_ids)
            messagebox.showinfo("Assign", f"Assigned {len(camper_ids)} camper(s) to activity.")
            dialog.destroy()
            load_activities()

        tk.Button(dialog, text="Assign", command=assign_selected).pack(pady=6)
        tk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=6)

    activities_actions = tk.Frame(activities_frame)
    activities_actions.pack(fill=tk.X, pady=4)
    tk.Button(activities_actions, text="Create activity", command=create_activity_dialog).pack(side=tk.LEFT, padx=4)
    tk.Button(activities_actions, text="Delete activity", command=delete_selected_activity).pack(side=tk.LEFT, padx=4)
    tk.Button(activities_actions, text="Bulk assign campers", command=assign_campers_to_selected_activity).pack(side=tk.LEFT, padx=4)

    def refresh_current_assignment_details() -> None:
        load_campers_for_selection()
        load_activities()
        refresh_daily_reports()

    assignments_table.bind("<<TreeviewSelect>>", lambda _evt: refresh_current_assignment_details())

    # ========== Tab 4: Daily Reports ==========
    tab_reports = tk.Frame(notebook)
    notebook.add(tab_reports, text="Daily Reports")

    tk.Label(tab_reports, text="Select an assignment from 'Camps & Pay' tab first", fg="#666666", font=("Helvetica", 10, "italic")).pack(pady=4)

    reports_frame = tk.LabelFrame(tab_reports, text="Daily reports for selected camp", padx=10, pady=10)
    reports_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    reports_table = Table(reports_frame, columns=["Date", "Notes"])
    reports_table.pack(fill=tk.BOTH, expand=True, pady=4)

    def refresh_daily_reports() -> None:
        reports_table.load_rows([])
        selection = assignments_table.selection()
        if not selection:
            return
        assignment_id = int(selection[0])
        assignment = next((rec for rec in list_leader_assignments(leader_id) if rec["id"] == assignment_id), None)
        if assignment is None:
            return
        reports = list_daily_reports(leader_id, assignment["camp_id"])
        reports_table.load_rows([(report["date"], report["notes"]) for report in reports])

    def create_or_edit_report() -> None:
        selection = assignments_table.selection()
        if not selection:
            messagebox.showinfo("Report", "Select an assignment from 'Camps & Pay' tab first.")
            return
        assignment_id = int(selection[0])
        assignment = next((rec for rec in list_leader_assignments(leader_id) if rec["id"] == assignment_id), None)
        if assignment is None:
            return

        dialog = tk.Toplevel(container)
        dialog.title("Daily report")
        dialog.geometry("480x360")

        tk.Label(dialog, text="Date (YYYY-MM-DD)").pack(pady=4)
        date_var = tk.StringVar()
        tk.Entry(dialog, textvariable=date_var, width=20).pack(pady=4)

        tk.Label(dialog, text="Report / notes").pack(pady=4)
        text_widget = tk.Text(dialog, height=10, width=50)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        def save_report() -> None:
            date = date_var.get().strip()
            notes = text_widget.get("1.0", tk.END).strip()
            if not date:
                messagebox.showwarning("Report", "Date required.")
                return
            if not notes:
                messagebox.showwarning("Report", "Notes required (cannot save empty report).")
                return
            save_daily_report(leader_id, assignment["camp_id"], date, notes)
            dialog.destroy()
            refresh_daily_reports()

        tk.Button(dialog, text="Save", command=save_report).pack(pady=6)
        tk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=4)

    reports_actions = tk.Frame(reports_frame)
    reports_actions.pack(fill=tk.X, pady=4)
    tk.Button(reports_actions, text="Add/Edit report", command=create_or_edit_report).pack(side=tk.LEFT, padx=4)

    # ========== Tab 5: Statistics ==========
    tab_stats = tk.Frame(notebook)
    notebook.add(tab_stats, text="Statistics")

    tk.Label(tab_stats, text="Statistics & Trends for All Camps Led", font=("Helvetica", 14, "bold")).pack(pady=8)

    stats_container = tk.Frame(tab_stats)
    stats_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    stats_table = Table(
        stats_container,
        columns=["Camp", "Area", "Days", "Campers", "Attending", "Participation %", "Activities", "Food/Day", "Total Food", "Reports"]
    )
    stats_table.pack(fill=tk.BOTH, expand=True, pady=4)

    def refresh_statistics() -> None:
        stats = get_leader_statistics(leader_id)
        rows = []
        for stat in stats:
            rows.append((
                stat["camp_name"],
                stat["camp_area"],
                stat["camp_days"],
                stat["total_campers"],
                stat["campers_attending"],
                f"{stat['participation_rate']}%",
                stat["total_activities"],
                stat["food_allocated_per_day"],
                stat["total_food_used"],
                stat["incident_report_count"],
            ))
        stats_table.load_rows(rows)

    # Summary panel
    summary_frame = tk.LabelFrame(tab_stats, text="Summary across all camps", padx=10, pady=10)
    summary_frame.pack(fill=tk.X, padx=10, pady=6)

    summary_text = tk.Text(summary_frame, height=6, state="disabled")
    summary_text.pack(fill=tk.X, pady=4)

    def update_summary() -> None:
        stats = get_leader_statistics(leader_id)
        summary_text.config(state="normal")
        summary_text.delete("1.0", tk.END)
        
        if not stats:
            summary_text.insert(tk.END, "No camps assigned yet.\n")
        else:
            total_camps = len(stats)
            total_campers = sum(s["total_campers"] for s in stats)
            total_activities = sum(s["total_activities"] for s in stats)
            total_food = sum(s["total_food_used"] for s in stats)
            total_reports = sum(s["incident_report_count"] for s in stats)
            avg_participation = sum(s["participation_rate"] for s in stats) / len(stats) if stats else 0
            
            summary_text.insert(tk.END, f"Total camps supervised: {total_camps}\n")
            summary_text.insert(tk.END, f"Total campers across all camps: {total_campers}\n")
            summary_text.insert(tk.END, f"Average participation rate: {avg_participation:.1f}%\n")
            summary_text.insert(tk.END, f"Total activities conducted: {total_activities}\n")
            summary_text.insert(tk.END, f"Total food resources used: {total_food} units\n")
            summary_text.insert(tk.END, f"Incident/daily reports filed: {total_reports}\n")
        
        summary_text.config(state="disabled")

    def refresh_all_stats() -> None:
        refresh_statistics()
        update_summary()

    refresh_all_stats()

    tk.Button(stats_container, text="Refresh Statistics", command=refresh_all_stats).pack(pady=6)

    # ========== Tab 6: Chat ==========
    tab_chat = tk.Frame(notebook)
    notebook.add(tab_chat, text="Chat")

    MessageBoard(
        tab_chat,
        post_callback=lambda content: post_message(leader_id, content),
        fetch_callback=lambda: list_messages_lines(),
    ).pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    return container

