"""Leader dashboard UI with tabbed navigation."""

import tkinter as tk
import sqlite3
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Callable, Dict, Optional

from services import (
    assign_campers_to_activity,
    assign_leader_to_camp,
    create_activity,
    delete_activity,
    update_activity,
    delete_daily_report,
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
    # NEW: needed for parent/consent info
    list_users,
    list_parent_campers,
    get_consent_form,
)
from ui.components import MessageBoard, Table, ScrollFrame
from ui.theme import get_palette, tint

from ui.components import MessageBoard, Table, ScrollFrame
from ui.theme import get_palette, tint


def build_dashboard(root: tk.Misc, user: Dict[str, str], logout_callback: Callable[[], None]) -> tk.Frame:
    scroll = ScrollFrame(root)
    container = scroll.content

    header = ttk.Frame(container)
    header.pack(fill=tk.X, padx=10, pady=8)

    tk.Label(header, text="Leader Dashboard", font=("Helvetica", 16, "bold")).pack(side=tk.LEFT)
    ttk.Button(header, text="Logout", command=logout_callback).pack(side=tk.RIGHT)

    notebook = ttk.Notebook(container)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    leader_id = user.get("id")

    # ========== Tab 1: Camps & Pay ==========
    tab_camps = tk.Frame(notebook)
    notebook.add(tab_camps, text="Camps & Pay")

    ttk.Label(tab_camps, text="Pay summary", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, padx=10, pady=(6, 2))
    pay_frame = ttk.Frame(tab_camps, style="Card.TFrame", padding=10)
    pay_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

    total_pay_var = tk.StringVar(value="Total: 0.00")
    ttk.Label(pay_frame, textvariable=total_pay_var, font=("Helvetica", 13, "bold")).pack(side=tk.LEFT, padx=6)

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
    assign_container = ttk.Frame(assignments_frame)
    assign_container.pack(fill=tk.BOTH, expand=True)
    assignments_table = ttk.Treeview(assign_container, columns=columns, show="headings", height=6)
    assign_scroll = ttk.Scrollbar(assign_container, orient="vertical", command=assignments_table.yview)
    assignments_table.configure(yscrollcommand=assign_scroll.set)
    for col in columns:
        assignments_table.heading(col, text=col)
        assignments_table.column(col, width=140)
    assignments_table.heading("Camp", anchor=tk.W)
    assignments_table.column("Camp", width=180, anchor=tk.W)
    assignments_table.heading("Location", anchor=tk.W)
    assignments_table.column("Location", anchor=tk.W)
    assignments_table.heading("Area", anchor=tk.CENTER)
    assignments_table.column("Area", anchor=tk.CENTER)
    assignments_table.heading("Start", anchor=tk.CENTER)
    assignments_table.column("Start", anchor=tk.CENTER)
    assignments_table.heading("End", anchor=tk.CENTER)
    assignments_table.column("End", anchor=tk.CENTER)
    assignments_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
    assign_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

    assignments_empty_label = ttk.Label(assignments_frame, text="No assignments yet.", style="Muted.TLabel")
    assignments_empty_label.pack_forget()

    def refresh_assignments() -> None:
        assignments_table.delete(*assignments_table.get_children())
        palette = get_palette(assignments_table)
        assignments_table.tag_configure("even", background=palette["surface"])
        assignments_table.tag_configure("odd", background=tint(palette["surface"], -0.03))
        rows = list_leader_assignments(leader_id)
        if not rows:
            assignments_empty_label.pack(pady=(0, 4), anchor=tk.W)
        else:
            assignments_empty_label.pack_forget()
        for idx, record in enumerate(rows):
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
                tags=("odd",) if (idx % 2 == 1) else ("even",),
            )
        refresh_available_camps()
        refresh_pay_summary()

    tk.Label(assignments_frame, text="Available camps (no conflicts)").pack(pady=(10, 4))
    avail_container = ttk.Frame(assignments_frame)
    avail_container.pack(fill=tk.BOTH, expand=True)
    available_table = ttk.Treeview(avail_container, columns=columns, show="headings", height=5)
    avail_scroll = ttk.Scrollbar(avail_container, orient="vertical", command=available_table.yview)
    available_table.configure(yscrollcommand=avail_scroll.set)
    for col in columns:
        available_table.heading(col, text=col)
        available_table.column(col, width=140)
    available_table.heading("Camp", anchor=tk.W)
    available_table.column("Camp", width=180, anchor=tk.W)
    available_table.heading("Location", anchor=tk.W)
    available_table.column("Location", anchor=tk.W)
    available_table.heading("Area", anchor=tk.CENTER)
    available_table.column("Area", anchor=tk.CENTER)
    available_table.heading("Start", anchor=tk.CENTER)
    available_table.column("Start", anchor=tk.CENTER)
    available_table.heading("End", anchor=tk.CENTER)
    available_table.column("End", anchor=tk.CENTER)
    available_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
    avail_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

    available_empty_label = ttk.Label(assignments_frame, text="No available camps.", style="Muted.TLabel")
    available_empty_label.pack_forget()

    def refresh_available_camps() -> None:
        available_table.delete(*available_table.get_children())
        palette = get_palette(available_table)
        available_table.tag_configure("even", background=palette["surface"])
        available_table.tag_configure("odd", background=tint(palette["surface"], -0.03))
        rows = list_available_camps_for_leader(leader_id)
        if not rows:
            available_empty_label.pack(pady=(0, 4), anchor=tk.W)
        else:
            available_empty_label.pack_forget()
        for idx, camp in enumerate(rows):
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
                tags=("odd",) if (idx % 2 == 1) else ("even",),
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

    action_row = ttk.Frame(assignments_frame)
    action_row.pack(fill=tk.X, pady=4)
    ttk.Button(action_row, text="Assign selected camp", command=assign_selected_camp).pack(side=tk.LEFT, padx=4)
    ttk.Button(action_row, text="Remove selected assignment", command=remove_assignment).pack(side=tk.LEFT, padx=4)

    refresh_assignments()

    # ========== Tab 2: Campers ==========
    tab_campers = tk.Frame(notebook)
    notebook.add(tab_campers, text="Campers")

    ttk.Label(tab_campers, text="Select an assignment from 'Camps & Pay' tab first", style="Muted.TLabel", font=("Helvetica", 10, "italic")).pack(pady=4)

    campers_frame = tk.LabelFrame(tab_campers, text="Campers in selected camp", padx=10, pady=10)
    campers_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    # Campers table with vertical scrollbar
    campers_container = ttk.Frame(campers_frame)
    campers_container.pack(fill=tk.BOTH, expand=True)

    campers_columns = [
        "Name",
        "DOB",
        "Emergency",
        "Food units/day",
        "Parent linked",
        "Parent name(s)",
        "Consent given",
    ]
    campers_table = Table(campers_container, columns=campers_columns)

    campers_scroll = ttk.Scrollbar(campers_container, orient="vertical", command=campers_table.yview)
    campers_table.configure(yscrollcommand=campers_scroll.set)
    campers_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
    campers_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

    campers_empty_label = ttk.Label(campers_frame, text="No campers in the selected camp.", style="Muted.TLabel")
    campers_empty_label.pack_forget()

    def load_campers_for_selection() -> None:
        selection = assignments_table.selection()
        campers_table.load_rows([])
        if not selection:
            return

        assignment_id = int(selection[0])
        record = next((rec for rec in list_leader_assignments(leader_id) if rec["id"] == assignment_id), None)
        if record is None:
            return

        camp_id = record["camp_id"]
        campers = list_camp_campers(camp_id)

        # Build camper → parents map based on existing parent–camper links
        parents = [u for u in list_users() if u["role"] == "parent" and u["enabled"]]
        camper_to_parents: Dict[int, list] = {}
        for parent_user in parents:
            linked_campers = list_parent_campers(parent_user["id"])
            for c in linked_campers:
                camper_to_parents.setdefault(c["id"], []).append(parent_user)

        rows = []
        for camper in campers:
            camper_id = camper["id"]
            parents_for_camper = camper_to_parents.get(camper_id, [])

            has_parent = "Y" if parents_for_camper else "N"
            parent_names = ", ".join(p["username"] for p in parents_for_camper)

            # Consent: Y if any linked parent has given consent for this camp
            consent_col = ""
            if parents_for_camper:
                consent_yes = False
                for p in parents_for_camper:
                    existing = get_consent_form(p["id"], camper_id, camp_id)
                    if existing and existing.get("consent"):
                        consent_yes = True
                        break
                consent_col = "Y" if consent_yes else "N"

            rows.append(
                (
                    f"{camper['first_name']} {camper['last_name']}",
                    camper["dob"],
                    camper["emergency_contact"],
                    camper["food_units_per_day"],
                    has_parent,
                    parent_names,
                    consent_col,
                )
            )

        campers_table.load_rows(rows)

        # Zebra-striping after load
        palette = get_palette(campers_table)
        campers_table.tag_configure("even", background=palette["surface"])
        campers_table.tag_configure("odd", background=tint(palette["surface"], -0.03))
        for idx, item_id in enumerate(campers_table.get_children()):
            campers_table.item(item_id, tags=("odd",) if (idx % 2 == 1) else ("even",))

        # Empty state toggle
        if not rows:
            campers_empty_label.pack(pady=(0, 4), anchor=tk.W)
        else:
            campers_empty_label.pack_forget()

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
    def export_csv() -> None:
        selection = assignments_table.selection()
        if not selection:
            messagebox.showinfo("Export", "Select an assignment from 'Camps & Pay' tab first.")
            return

        assignment_id = int(selection[0])
        assignment = next(
            (rec for rec in list_leader_assignments(leader_id) if rec["id"] == assignment_id),
            None,
        )
        if assignment is None:
            messagebox.showerror("Export", "Assignment not found.")
            return

        camp_id = assignment["camp_id"]
        campers = list_camp_campers(camp_id)
        if not campers:
            messagebox.showinfo("Export", "No campers to export for this camp.")
            return

        # Ask where to save the CSV
        path = filedialog.asksaveasfilename(
            title="Save campers CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"camp_{camp_id}_campers.csv",
        )
        if not path:
            return

        # Build camper → parents map
        parents = [u for u in list_users() if u["role"] == "parent" and u["enabled"]]
        camper_to_parents: Dict[int, list] = {}
        for parent_user in parents:
            linked_campers = list_parent_campers(parent_user["id"])
            for c in linked_campers:
                camper_to_parents.setdefault(c["id"], []).append(parent_user)

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Header row – includes 3 new columns
                writer.writerow(
                    [
                        "First name",
                        "Last name",
                        "DOB",
                        "Emergency contact",
                        "Food units/day",
                        "Parent linked (Y/N)",
                        "Parent name(s)",
                        "Consent given (Y/N)",
                    ]
                )

                for camper in campers:
                    camper_id = camper["id"]
                    parents_for_camper = camper_to_parents.get(camper_id, [])
                    has_parent = "Y" if parents_for_camper else "N"
                    parent_names = ", ".join(p["username"] for p in parents_for_camper)

                    # Aggregate consent: Y if any linked parent has given consent for this camp
                    consent_col = ""
                    if parents_for_camper:
                        consent_yes = False
                        for p in parents_for_camper:
                            existing = get_consent_form(p["id"], camper_id, camp_id)
                            if existing and existing.get("consent"):
                                consent_yes = True
                                break
                        consent_col = "Y" if consent_yes else "N"

                    writer.writerow(
                        [
                            camper["first_name"],
                            camper["last_name"],
                            camper["dob"],
                            camper["emergency_contact"],
                            camper["food_units_per_day"],
                            has_parent,
                            parent_names,
                            consent_col,
                        ]
                    )
        except OSError as exc:
            messagebox.showerror("Export", f"Failed to write CSV:\n{exc}")
            return

        messagebox.showinfo("Export complete", f"Exported {len(campers)} camper(s) to:\n{path}")

    action_row = ttk.Frame(campers_frame)
    action_row.pack(fill=tk.X, pady=4)
    ttk.Button(action_row, text="Import campers from CSV", command=import_csv).pack(side=tk.LEFT, padx=4)
    ttk.Button(action_row, text="Adjust food units", command=adjust_food_units).pack(side=tk.LEFT, padx=4)
    ttk.Button(action_row, text="Export campers to CSV", command=export_csv).pack(side=tk.LEFT, padx=4)

    # ========== Tab 3: Activities ==========
    tab_activities = tk.Frame(notebook)
    notebook.add(tab_activities, text="Activities")

    tk.Label(tab_activities, text="Select an assignment from 'Camps & Pay' tab first", fg="#666666", font=("Helvetica", 10, "italic")).pack(pady=4)

    activities_frame = tk.LabelFrame(tab_activities, text="Activities for selected camp", padx=10, pady=10)
    activities_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    # Activities table with vertical scrollbar
    activities_container = ttk.Frame(activities_frame)
    activities_container.pack(fill=tk.BOTH, expand=True)
    activities_table = Table(activities_container, columns=["Name", "Date", "Participants"])
    activities_scroll = ttk.Scrollbar(activities_container, orient="vertical", command=activities_table.yview)
    activities_table.configure(yscrollcommand=activities_scroll.set)
    activities_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
    activities_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

    activities_empty_label = ttk.Label(activities_frame, text="No activities for the selected camp.", style="Muted.TLabel")
    activities_empty_label.pack_forget()

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
        # Zebra-striping after load
        palette = get_palette(activities_table)
        activities_table.tag_configure("even", background=palette["surface"])
        activities_table.tag_configure("odd", background=tint(palette["surface"], -0.03))
        for idx, item_id in enumerate(activities_table.get_children()):
            activities_table.item(item_id, tags=("odd",) if (idx % 2 == 1) else ("even",))
        # Empty state toggle
        if not rows:
            activities_empty_label.pack(pady=(0, 4), anchor=tk.W)
        else:
            activities_empty_label.pack_forget()

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

        ttk.Label(dialog, text="Activity name").pack(pady=4)
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=30).pack(pady=4)

        ttk.Label(dialog, text="Date (YYYY-MM-DD)").pack(pady=4)
        date_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=date_var, width=20).pack(pady=4)

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

        ttk.Button(dialog, text="Create", command=save).pack(pady=8)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=4)

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

        camp_id = assignment["camp_id"]

        # All campers for this camp
        all_campers = list_camp_campers(camp_id)
        if not all_campers:
            messagebox.showinfo("Activity", "No campers available to assign.")
            return

        # Build camper → parents map from parent–camper links
        parents = [u for u in list_users() if u["role"] == "parent" and u["enabled"]]
        camper_to_parents: Dict[int, list] = {}
        for parent_user in parents:
            linked_campers = list_parent_campers(parent_user["id"])
            for c in linked_campers:
                camper_to_parents.setdefault(c["id"], []).append(parent_user)

        # Split campers into consent-eligible and not
        eligible_campers = []
        ineligible_names = []

        for camper in all_campers:
            camper_id = camper["id"]
            parents_for_camper = camper_to_parents.get(camper_id, [])

            consent_yes = False
            for p in parents_for_camper:
                existing = get_consent_form(p["id"], camper_id, camp_id)
                if existing and existing.get("consent"):
                    consent_yes = True
                    break

            if consent_yes:
                eligible_campers.append(camper)
            else:
                ineligible_names.append(f"{camper['first_name']} {camper['last_name']}")

        if not eligible_campers:
            msg = "No campers with parental consent are available for this camp."
            if ineligible_names:
                msg += "\n\nCampers without consent:\n- " + "\n- ".join(ineligible_names)
            messagebox.showinfo("Activity", msg)
            return

        # If some campers are excluded, warn the leader once
        if ineligible_names:
            messagebox.showwarning(
                "Consent required",
                "The following campers cannot be assigned because no parent consent "
                "has been recorded for this camp:\n\n"
                + "\n".join(f"- {name}" for name in ineligible_names)
            )

        # Now continue as before but only with eligible_campers
        selection_activity = activities_table.selection()
        if not selection_activity:
            messagebox.showinfo("Activity", "Select an activity first.")
            return
        index = activities_table.index(selection_activity[0])
        activities = list_camp_activities(camp_id)
        if index >= len(activities):
            return
        activity = activities[index]

        dialog = tk.Toplevel(container)
        dialog.title("Bulk assign campers to activity")
        dialog.geometry("400x360")

        ttk.Label(
            dialog,
            text="Select campers with consent (Ctrl/Cmd + click)",
            style="Muted.TLabel",
            font=("Helvetica", 10, "italic"),
        ).pack(pady=4)

        listbox = tk.Listbox(dialog, selectmode=tk.MULTIPLE)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Only list campers with consent
        for camper in eligible_campers:
            listbox.insert(tk.END, f"{camper['first_name']} {camper['last_name']}")

        def assign_selected() -> None:
            sel_indices = listbox.curselection()
            if not sel_indices:
                messagebox.showinfo("Assign", "Select at least one camper.")
                return
            camper_ids = [eligible_campers[idx]["id"] for idx in sel_indices]
            try:
                assign_campers_to_activity(activity["id"], camper_ids)
                message = f"Assigned {len(camper_ids)} camper(s) to activity."
            except sqlite3.IntegrityError:
                message = "Some selected campers aren’t in this camp; they were skipped."
            messagebox.showinfo("Assign", message)
            dialog.destroy()
            load_activities()

        ttk.Button(dialog, text="Assign", command=assign_selected).pack(pady=6)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=6)

    activities_actions = ttk.Frame(activities_frame)
    activities_actions.pack(fill=tk.X, pady=4)
    ttk.Button(activities_actions, text="Create activity", command=create_activity_dialog).pack(side=tk.LEFT, padx=4)
    def edit_selected_activity() -> None:
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
            messagebox.showinfo("Activity", "Select an activity to edit.")
            return
        index = activities_table.index(selection_activity[0])
        activities = list_camp_activities(assignment["camp_id"])
        if index >= len(activities):
            return
        activity = activities[index]
        dialog = tk.Toplevel(container)
        dialog.title("Edit activity")
        dialog.geometry("360x220")
        ttk.Label(dialog, text="Activity name").pack(pady=4)
        name_var = tk.StringVar(value=activity["name"])
        ttk.Entry(dialog, textvariable=name_var, width=30).pack(pady=4)
        ttk.Label(dialog, text="Date (YYYY-MM-DD)").pack(pady=4)
        date_var = tk.StringVar(value=activity["date"])
        ttk.Entry(dialog, textvariable=date_var, width=20).pack(pady=4)
        def save_edit() -> None:
            name = name_var.get().strip()
            date = date_var.get().strip()
            if not name or not date:
                messagebox.showwarning("Activity", "Name and date required.")
                return
            try:
                import pandas as pd
                pd.to_datetime(date)
            except Exception:
                messagebox.showerror("Activity", "Invalid date format. Use YYYY-MM-DD.")
                return
            if not update_activity(activity["id"], assignment["camp_id"], name, date):
                messagebox.showerror("Activity", "Failed to update activity.")
                return
            dialog.destroy()
            load_activities()
        ttk.Button(dialog, text="Save", command=save_edit).pack(pady=8)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=4)
    ttk.Button(activities_actions, text="Edit activity", command=edit_selected_activity).pack(side=tk.LEFT, padx=4)
    ttk.Button(activities_actions, text="Delete activity", command=delete_selected_activity).pack(side=tk.LEFT, padx=4)
    ttk.Button(activities_actions, text="Bulk assign campers", command=assign_campers_to_selected_activity).pack(side=tk.LEFT, padx=4)

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

    # Reports table with vertical scrollbar
    reports_container = ttk.Frame(reports_frame)
    reports_container.pack(fill=tk.BOTH, expand=True)
    reports_table = Table(reports_container, columns=["Date", "Notes"])
    reports_scroll = ttk.Scrollbar(reports_container, orient="vertical", command=reports_table.yview)
    reports_table.configure(yscrollcommand=reports_scroll.set)
    reports_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
    reports_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

    reports_empty_label = ttk.Label(reports_frame, text="No reports for the selected camp.", style="Muted.TLabel")
    reports_empty_label.pack_forget()

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
        rows = [(report["date"], report["notes"]) for report in reports]
        reports_table.load_rows(rows)
        # Zebra-striping after load
        palette = get_palette(reports_table)
        reports_table.tag_configure("even", background=palette["surface"])
        reports_table.tag_configure("odd", background=tint(palette["surface"], -0.03))
        for idx, item_id in enumerate(reports_table.get_children()):
            reports_table.item(item_id, tags=("odd",) if (idx % 2 == 1) else ("even",))
        # Empty state toggle
        if not rows:
            reports_empty_label.pack(pady=(0, 4), anchor=tk.W)
        else:
            reports_empty_label.pack_forget()

    def add_report() -> None:
        selection = assignments_table.selection()
        if not selection:
            messagebox.showinfo("Report", "Select an assignment from 'Camps & Pay' tab first.")
            return
        assignment_id = int(selection[0])
        assignment = next((rec for rec in list_leader_assignments(leader_id) if rec["id"] == assignment_id), None)
        if assignment is None:
            return

        dialog = tk.Toplevel(container)
        dialog.title("Add daily report")
        dialog.geometry("480x360")

        ttk.Label(dialog, text="Date (YYYY-MM-DD)").pack(pady=4)
        date_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=date_var, width=20).pack(pady=4)

        ttk.Label(dialog, text="Report / notes").pack(pady=4)
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

        ttk.Button(dialog, text="Save", command=save_report).pack(pady=6)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=4)

    def edit_report() -> None:
        selection = assignments_table.selection()
        if not selection:
            messagebox.showinfo("Report", "Select an assignment from 'Camps & Pay' tab first.")
            return
        assignment_id = int(selection[0])
        assignment = next((rec for rec in list_leader_assignments(leader_id) if rec["id"] == assignment_id), None)
        if assignment is None:
            return
        # Require selecting a report row
        report_sel = reports_table.selection()
        if not report_sel:
            messagebox.showinfo("Report", "Select a report row to edit.")
            return
        idx = reports_table.index(report_sel[0])
        # Fetch current data
        current_rows = reports_table.get_children()
        if idx >= len(current_rows):
            return
        item_id = current_rows[idx]
        values = reports_table.item(item_id, "values")
        original_date = values[0]
        original_notes = values[1]

        dialog = tk.Toplevel(container)
        dialog.title("Edit daily report")
        dialog.geometry("480x380")

        ttk.Label(dialog, text="Date (YYYY-MM-DD)").pack(pady=4)
        date_var = tk.StringVar(value=original_date)
        ttk.Entry(dialog, textvariable=date_var, width=20).pack(pady=4)

        ttk.Label(dialog, text="Report / notes").pack(pady=4)
        text_widget = tk.Text(dialog, height=10, width=50)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        text_widget.insert("1.0", original_notes)

        def save_edit() -> None:
            new_date = date_var.get().strip()
            new_notes = text_widget.get("1.0", tk.END).strip()
            if not new_date:
                messagebox.showwarning("Report", "Date required.")
                return
            if not new_notes:
                messagebox.showwarning("Report", "Notes required (cannot save empty report).")
                return
            # If date changed, delete old row first to avoid duplicate entries
            if new_date != original_date:
                delete_daily_report(leader_id, assignment["camp_id"], original_date)
            save_daily_report(leader_id, assignment["camp_id"], new_date, new_notes)
            dialog.destroy()
            refresh_daily_reports()

        ttk.Button(dialog, text="Save", command=save_edit).pack(pady=6)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=4)

    reports_actions = ttk.Frame(reports_frame)
    reports_actions.pack(fill=tk.X, pady=4)
    ttk.Button(reports_actions, text="Add report", command=add_report).pack(side=tk.LEFT, padx=4)
    ttk.Button(reports_actions, text="Edit report", command=edit_report).pack(side=tk.LEFT, padx=4)

    # ========== Tab 5: Statistics ==========
    tab_stats = tk.Frame(notebook)
    notebook.add(tab_stats, text="Statistics")

    tk.Label(tab_stats, text="Statistics & Trends for All Camps Led", font=("Helvetica", 14, "bold")).pack(pady=8)

    stats_container = ttk.Frame(tab_stats)
    stats_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    # Stats table with vertical scrollbar
    stats_table_columns = ["Camp", "Area", "Days", "Campers", "Attending", "Participation %", "Activities", "Food/Day", "Total Food", "Reports"]
    stats_table_container = ttk.Frame(stats_container)
    stats_table_container.pack(fill=tk.BOTH, expand=True)
    stats_table = Table(stats_table_container, columns=stats_table_columns)
    stats_scroll = ttk.Scrollbar(stats_table_container, orient="vertical", command=stats_table.yview)
    stats_table.configure(yscrollcommand=stats_scroll.set)
    stats_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
    stats_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

    # Align headers/cells
    stats_table.heading("Camp", text="Camp", anchor=tk.W)
    stats_table.column("Camp", anchor=tk.W, width=160)
    stats_table.heading("Area", text="Area", anchor=tk.W)
    stats_table.column("Area", anchor=tk.W, width=120)
    for col in ["Days", "Campers", "Attending", "Participation %", "Activities", "Food/Day", "Total Food", "Reports"]:
        stats_table.heading(col, text=col, anchor=tk.CENTER)
        stats_table.column(col, anchor=tk.CENTER)

    stats_empty_label = ttk.Label(stats_container, text="No statistics to display.", style="Muted.TLabel")
    stats_empty_label.pack_forget()

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
        # Zebra-striping after load
        palette = get_palette(stats_table)
        stats_table.tag_configure("even", background=palette["surface"])
        stats_table.tag_configure("odd", background=tint(palette["surface"], -0.03))
        for idx, item_id in enumerate(stats_table.get_children()):
            stats_table.item(item_id, tags=("odd",) if (idx % 2 == 1) else ("even",))
        # Empty state toggle
        if not rows:
            stats_empty_label.pack(pady=(0, 4), anchor=tk.W)
        else:
            stats_empty_label.pack_forget()

    # Summary panel
    ttk.Label(tab_stats, text="Summary across all camps", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, padx=10, pady=(6, 2))
    summary_frame = ttk.Frame(tab_stats, style="Card.TFrame", padding=10)
    summary_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

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
        current_user=user.get("username"),
    ).pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    return scroll

