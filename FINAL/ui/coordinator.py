"""Coordinator dashboard UI with tabbed navigation."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict, Optional

from services import (
    add_stock_topup,
    create_camp,
    delete_camp,
    get_coordinator_dashboard_stats,
    get_food_shortage_alerts,
    get_daily_pay_rate,
    list_camps,
    list_messages_lines,
    list_stock_topups,
    post_message,
    set_daily_pay_rate,
    update_camp,
)
from ui.components import BarChart, DualBarChart, MessageBoard, ScrollFrame
from ui.theme import get_palette, tint

UK_CITIES = sorted([
    "London",
    "Birmingham", "Coventry", "Wolverhampton",
    "Manchester", "Salford",
    "Leeds", "Bradford", "Wakefield",
    "Liverpool",
    "Newcastle upon Tyne", "Sunderland",
    "Sheffield",
    "Bristol",
    "Leicester",
    "Nottingham",
    "Hull",
    "Stoke-on-Trent", "Lichfield",
    "Plymouth", "Exeter",
    "Southampton", "Portsmouth", "Winchester",
    "Brighton and Hove",
    "Wells", "Bath",
    "Canterbury",
    "Carlisle",
    "Chelmsford",
    "Chester",
    "Chichester",
    "Durham",
    "Ely", "Peterborough",
    "Gloucester",
    "Hereford",
    "Lancaster", "Preston",
    "Lincoln",
    "Norwich",
    "Oxford",
    "Ripon", "York",
    "Salisbury",
    "St Albans",
    "St Davids",
    "Stirling",
    "Swansea",
    "Truro",
    "Worcester",

    "Edinburgh",
    "Glasgow",
    "Aberdeen",
    "Dundee",
    "Perth",
    "Inverness",

    "Bangor",
    "Belfast", "Lisburn",
    "Derry",
    "Newry",
])

UK_COUNTIES = sorted([
    "Greater London",
    "West Midlands",
    "Greater Manchester",
    "West Yorkshire",
    "Merseyside",
    "Tyne and Wear",
    "South Yorkshire",
    "Bristol",
    "Leicestershire",
    "Nottinghamshire",
    "East Riding of Yorkshire",
    "Staffordshire",
    "Devon",
    "Hampshire",
    "East Sussex",
    "Somerset",
    "Kent",
    "Cumbria",
    "Essex",
    "Cheshire",
    "West Sussex",
    "County Durham",
    "Cambridgeshire",
    "Gloucestershire",
    "Herefordshire",
    "Lancashire",
    "Lincolnshire",
    "Norfolk",
    "Oxfordshire",
    "North Yorkshire",
    "Wiltshire",
    "Hertfordshire",
    "Pembrokeshire",
    "Stirling",
    "West Glamorgan",
    "Cornwall",
    "Worcestershire",

    "Edinburgh",
    "Glasgow",
    "Aberdeen City",
    "Dundee City",
    "Perth and Kinross",
    "Highland",

    "Down",
    "Antrim",
    "Derry and Londonderry",
    "Armagh",
])

UK_COUNTIES_CITIES = {
    "Greater London": ["London"],
    "West Midlands": ["Birmingham", "Coventry", "Wolverhampton"],
    "Greater Manchester": ["Manchester", "Salford"],
    "West Yorkshire": ["Leeds", "Bradford", "Wakefield"],
    "Merseyside": ["Liverpool"],
    "Tyne and Wear": ["Newcastle upon Tyne", "Sunderland"],
    "South Yorkshire": ["Sheffield"],
    "Bristol": ["Bristol"],
    "Leicestershire": ["Leicester"],
    "Nottinghamshire": ["Nottingham"],
    "East Riding of Yorkshire": ["Hull"],
    "Staffordshire": ["Stoke-on-Trent", "Lichfield"],
    "Devon": ["Plymouth", "Exeter"],
    "Hampshire": ["Southampton", "Portsmouth", "Winchester"],
    "East Sussex": ["Brighton and Hove"],
    "Somerset": ["Wells", "Bath"],
    "Kent": ["Canterbury"],
    "Cumbria": ["Carlisle"],
    "Essex": ["Chelmsford"],
    "Cheshire": ["Chester"],
    "West Sussex": ["Chichester"],
    "County Durham": ["Durham"],
    "Cambridgeshire": ["Ely", "Peterborough"],
    "Gloucestershire": ["Gloucester"],
    "Herefordshire": ["Hereford"],
    "Lancashire": ["Lancaster", "Preston"],
    "Lincolnshire": ["Lincoln"],
    "Norfolk": ["Norwich"],
    "Oxfordshire": ["Oxford"],
    "North Yorkshire": ["Ripon", "York"],
    "Wiltshire": ["Salisbury"],
    "Hertfordshire": ["St Albans"],
    "Pembrokeshire": ["St Davids"],
    "Stirling": ["Stirling"],
    "West Glamorgan": ["Swansea"],
    "Cornwall": ["Truro"],
    "Worcestershire": ["Worcester"],

    "Edinburgh": ["Edinburgh"],
    "Glasgow": ["Glasgow"],
    "Aberdeen City": ["Aberdeen"],
    "Dundee City": ["Dundee"],
    "Perth and Kinross": ["Perth"],
    "Highland": ["Inverness"],

    "Down": ["Bangor"],
    "Antrim": ["Belfast", "Lisburn"],
    "Derry and Londonderry": ["Derry"],
    "Armagh": ["Newry"]
}



def build_dashboard(root: tk.Misc, user: Dict[str, str], logout_callback: Callable[[], None]) -> tk.Frame:
    scroll = ScrollFrame(root)
    container = scroll.content

    header = ttk.Frame(container)
    header.pack(fill=tk.X, padx=10, pady=8)

    tk.Label(header, text="Coordinator Dashboard", font=("Helvetica", 16, "bold")).pack(side=tk.LEFT)
    ttk.Button(header, text="Logout", command=logout_callback).pack(side=tk.RIGHT)

    notebook = ttk.Notebook(container)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    # ========== Tab 1: Camps ==========
    tab_camps = tk.Frame(notebook)
    notebook.add(tab_camps, text="Camps")

    pay_frame_title = ttk.Label(tab_camps, text="Daily pay rate per leader (currency units)", font=("Helvetica", 11, "bold"))
    pay_frame_title.pack(anchor=tk.W, padx=10, pady=(6, 2))
    pay_frame = ttk.Frame(tab_camps, style="Card.TFrame", padding=10)
    pay_frame.pack(fill=tk.X, padx=10, pady=(0, 6))
    daily_rate_var = tk.StringVar(value=get_daily_pay_rate())
    daily_rate_entry = ttk.Entry(pay_frame, textvariable=daily_rate_var, width=10)
    daily_rate_entry.pack(side=tk.LEFT, padx=6)

    def save_daily_rate() -> None:
        value = daily_rate_var.get().strip()
        if not value.isdigit():
            messagebox.showerror("Daily pay rate", "Enter a non-negative integer value.")
            return
        set_daily_pay_rate(value)
        messagebox.showinfo("Daily pay rate", "Updated successfully.")

    ttk.Button(pay_frame, text="Save", command=save_daily_rate, style="Primary.TButton").pack(side=tk.LEFT)

    camps_frame = tk.LabelFrame(tab_camps, text="Camp list", padx=10, pady=10)
    camps_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    columns = (
        "Name",
        "County",
        "City",
        "Type",
        "Leaders",
        "Start",
        "End",
        "Daily Food",
        "Default Food/Person",
        "Top-up Δ",
        "Effective Daily",
    )
    # Table container with vertical scrollbar
    table_container = ttk.Frame(camps_frame)
    table_container.pack(fill=tk.BOTH, expand=True)
    camps_table = ttk.Treeview(table_container, columns=columns, show="headings", height=10)
    camps_scroll = ttk.Scrollbar(table_container, orient="vertical", command=camps_table.yview)
    camps_table.configure(yscrollcommand=camps_scroll.set)
    for col in columns:
        camps_table.heading(col, text=col)
        camps_table.column(col, width=100)
    # Header and cell alignment for readability
    camps_table.heading("Name", anchor=tk.W)
    camps_table.column("Name", width=140, anchor=tk.W)
    camps_table.heading("County", anchor=tk.W)
    camps_table.column("County", width=120, anchor=tk.W)
    camps_table.heading("City", anchor=tk.CENTER)
    camps_table.column("City", anchor=tk.CENTER)
    camps_table.heading("Type", anchor=tk.CENTER)
    camps_table.column("Type", anchor=tk.CENTER)
    camps_table.heading("Leaders", anchor=tk.CENTER)
    camps_table.column("Leaders", width=120, anchor=tk.CENTER)
    camps_table.heading("Start", anchor=tk.CENTER)
    camps_table.column("Start", width=90, anchor=tk.CENTER)
    camps_table.heading("End", anchor=tk.CENTER)
    camps_table.column("End", width=90, anchor=tk.CENTER)
    camps_table.heading("Daily Food", anchor=tk.CENTER)
    camps_table.column("Daily Food", anchor=tk.CENTER)
    camps_table.heading("Default Food/Person", anchor=tk.CENTER)
    camps_table.column("Default Food/Person", anchor=tk.CENTER)
    camps_table.heading("Top-up Δ", anchor=tk.CENTER)
    camps_table.column("Top-up Δ", anchor=tk.CENTER)
    camps_table.heading("Effective Daily", anchor=tk.CENTER)
    camps_table.column("Effective Daily", anchor=tk.CENTER)
    camps_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
    camps_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

    # Empty state label (hidden unless no camps)
    camps_empty_label = ttk.Label(camps_frame, text="No camps available. Create one above.", style="Muted.TLabel")
    camps_empty_label.pack_forget()

    ttk.Label(tab_camps, text="Create / Update Camp", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, padx=10, pady=(6, 2))
    form_frame = ttk.Frame(tab_camps, style="Card.TFrame", padding=10)
    form_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

    name_var = tk.StringVar()
    county_var = tk.StringVar()
    city_var = tk.StringVar()
    leaders_var = tk.StringVar(value='n/a')
    type_var = tk.StringVar(value="day")
    start_var = tk.StringVar()
    end_var = tk.StringVar()
    daily_food_var = tk.StringVar(value="0")
    default_food_var = tk.StringVar(value="0")

    # Two-column compact layout
    ttk.Label(form_frame, text="Name").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
    ttk.Entry(form_frame, textvariable=name_var, width=25).grid(row=0, column=1, sticky=tk.W, padx=4, pady=2)


    ttk.Label(form_frame, text="County").grid(row=0, column=2, sticky=tk.W, padx=4, pady=2)
    county_menu = ttk.Combobox(
        form_frame,
        textvariable=county_var,
        values=UK_COUNTIES,
        state="readonly",
        width=22,
        exportselection=False
    )
    county_menu.grid(row=0, column=3, sticky=tk.W, padx=4, pady=2)

    ttk.Label(form_frame, text="City").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
    city_menu = ttk.Combobox(
        form_frame,
        textvariable=city_var,
        values=UK_CITIES,
        state="readonly",
        width=22,
        exportselection=False
    )
    city_menu.grid(row=1, column=1, sticky=tk.W, padx=4, pady=2)

    def pick_city(event): # the cities at the top of the list will be in the selected county
        county = county_var.get()
        city_items = UK_COUNTIES_CITIES.get(county, [])
        new_cities =  [i for i in UK_CITIES if i not in city_items]
        city_menu.config(values=city_items+new_cities)
        if city_items:
            city_var.set(city_items[0])
        else:
            city_var.set("")
            return

    def pick_county(event): # the county selection will change depending on the city selected
        city = city_var.get()
        county = [k for k, v in UK_COUNTIES_CITIES.items() if city in v][0]
        if county:
            county_var.set(county)
        else:
            county_var.set("")
            return

    county_menu.bind("<<ComboboxSelected>>", pick_city)
    city_menu.bind("<<ComboboxSelected>>", pick_county)

    ttk.Label(form_frame, text="Type").grid(row=1, column=2, sticky=tk.W, padx=4, pady=2)
    type_menu = ttk.Combobox(
        form_frame,
        textvariable=type_var,
        values=["day", "overnight", "expedition"],
        state="readonly",
        width=22,
        style="Filled.TCombobox",
        exportselection=False,
    )
    type_menu.grid(row=1, column=3, sticky=tk.W, padx=4, pady=2)
    def _on_type_selected(evt) -> None:
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
            form_frame.focus_set()
        except Exception:
            pass
    type_menu.bind("<<ComboboxSelected>>", _on_type_selected)

    ttk.Label(form_frame, text="Leaders").grid(row=2, column=0, sticky=tk.W, padx=4, pady=2)
    ttk.Entry(form_frame, textvariable=leaders_var, width=25, state="readonly").grid(row=2, column=1, sticky=tk.W, padx=4, pady=2)

    ttk.Label(form_frame, text="Start date").grid(row=3, column=0, sticky=tk.W, padx=4, pady=2)
    ttk.Entry(form_frame, textvariable=start_var, width=25).grid(row=3, column=1, sticky=tk.W, padx=4, pady=2)

    ttk.Label(form_frame, text="End date").grid(row=3, column=2, sticky=tk.W, padx=4, pady=2)
    ttk.Entry(form_frame, textvariable=end_var, width=25).grid(row=3, column=3, sticky=tk.W, padx=4, pady=2)

    ttk.Label(form_frame, text="Daily food units").grid(row=4, column=0, sticky=tk.W, padx=4, pady=2)
    ttk.Entry(form_frame, textvariable=daily_food_var, width=25).grid(row=4, column=1, sticky=tk.W, padx=4, pady=2)

    ttk.Label(form_frame, text="Default food/camper/day").grid(row=4, column=2, sticky=tk.W, padx=4, pady=2)
    ttk.Entry(form_frame, textvariable=default_food_var, width=25).grid(row=4, column=3, sticky=tk.W, padx=4, pady=2)

    selected_camp_id: Optional[int] = None

    def reset_form() -> None:
        nonlocal selected_camp_id
        city_menu.config(value=UK_CITIES) # resets dropdowns
        county_menu.config(value=UK_COUNTIES)
        selected_camp_id = None
        name_var.set("")
        county_var.set("")
        city_var.set("")
        leaders_var.set("n/a")
        type_var.set("day")
        start_var.set("")
        end_var.set("")
        daily_food_var.set("0")
        default_food_var.set("0")
        update_form_buttons()

    def select_camp() -> None:
        nonlocal selected_camp_id
        selection = camps_table.selection()
        if not selection:
            messagebox.showinfo("Select camp", "Choose a camp from the list.")
            return
        selected_camp_id = int(selection[0])
        item = camps_table.item(selection[0])
        values = item["values"]
        # Map by column name to avoid index drift
        vals = dict(zip(columns, values))
        name_var.set(vals.get("Name", ""))
        county_var.set(vals.get("County", ""))
        city_var.set(vals.get("City", ""))
        type_var.set(vals.get("Type", "day"))
        leaders_var.set(vals.get("Leaders", ""))
        start_var.set(vals.get("Start", ""))
        end_var.set(vals.get("End", ""))
        daily_food_var.set(str(vals.get("Daily Food", "0")))
        default_food_var.set(str(vals.get("Default Food/Person", "0")))
        update_form_buttons()

    def validate_int(var: str, label: str) -> Optional[int]:
        if not var.strip().lstrip('-').isdigit():
            messagebox.showerror("Validation", f"{label} must be an integer.")
            return None
        return int(var.strip())

    def validate_dates(start: str, end: str) -> bool:
        import datetime
        import re
        import pandas as pd

        # Allow 1 or 2 digits for month/day
        if not re.fullmatch(r"^\d{4}-\d{1,2}-\d{1,2}$", start) or not re.fullmatch(r"^\d{4}-\d{1,2}-\d{1,2}$", end):
            messagebox.showerror("Validation", "Dates must be in format YYYY-MM-DD.")
            return False

        try:
            start_dt = pd.to_datetime(start)
            end_dt = pd.to_datetime(end)
            duration = (end_dt - start_dt).days

            if type_var.get() == 'day' and start_dt != end_dt:
                messagebox.showerror("Validation", "Start and end date of a day camp must be the same.")
                return False

            elif type_var.get() == 'overnight' and duration != 1:
                messagebox.showerror(
                    "Validation",
                    "End date should be the day after the start date for an overnight camp."
                )
                return False

            elif type_var.get() == 'expedition' and duration < 2:
                messagebox.showerror(
                    "Validation",
                    "End date of an expedition should be at least two days after the start date."
                )
                return False

        except ValueError:
            messagebox.showerror("Validation", "Date values are invalid (nonexistent month/day).")
            return False

        if end_dt < start_dt:
            messagebox.showerror("Validation", "End date must be on or after start date.")
            return False

        return True

    def create_or_updateCamp(update: bool) -> None:
            name = name_var.get().strip()
            county = county_var.get().strip()
            start = start_var.get().strip()
            end = end_var.get().strip()
            update_form_buttons()


            # Basic required fields check
            if not name or not county or not start or not end:
                messagebox.showwarning("Validation", "Name, county, start and end dates are required.")
                return

            # Date validation
            if not validate_dates(start, end):
                return

            # Numeric fields validation
            daily_food = validate_int(daily_food_var.get(), "Daily food units planned")
            if daily_food is None or daily_food < 0:
                messagebox.showerror("Validation", "Daily food units must be non-negative.")
                return

            default_food = validate_int(default_food_var.get(), "Default food per camper")
            if default_food is None or default_food < 0:
                messagebox.showerror("Validation", "Default food per camper must be non-negative.")
                return
            if default_food > daily_food:
                messagebox.showerror("Validation", "The daily food per camper should not exceed the daily food for the camp.")
                return

            # Duplicate camp name check
            def camp_name_exists(name_to_check: str) -> bool:
                """Check if a camp name already exists (case-insensitive)."""
                name_lower = name_to_check.strip().lower()
                for camp in list_camps():
                    if update and selected_camp_id == camp["id"]:
                        continue
                    if camp["name"].strip().lower() == name_lower:
                        return True
                return False

            if camp_name_exists(name):
                messagebox.showerror(
                    "Duplicate Name",
                    "Camp name is already in use. Please choose something else."
                )
                return

            # Arguments to create/update
            args = (
                name,
                county,
                city_var.get().strip(),
                type_var.get(),
                start,
                end,
                daily_food,
                default_food,
            )

            # Update or create
            if update:
                if selected_camp_id is None:
                    messagebox.showinfo("Update", "Select a camp first.")
                    return
                ok = update_camp(selected_camp_id, *args)
                if not ok:
                    messagebox.showerror("Update", "Failed to update camp. Ensure data is valid and unique.")
                    return
            else:
                ok = create_camp(*args)
                if not ok:
                    messagebox.showerror("Create", "Failed to create camp. Ensure data is valid and unique.")
                    return

            # Refresh UI
            load_camps()
            reset_form()


    button_row = ttk.Frame(form_frame)
    button_row.grid(row=5, column=0, columnspan=4, pady=8)

    create_btn = ttk.Button(button_row, text="Create", command=lambda: create_or_updateCamp(False), width=12)
    create_btn.pack(side=tk.LEFT, padx=4)

    update_btn = ttk.Button(button_row, text="Update", command=lambda: create_or_updateCamp(True), width=12)
    update_btn.pack(side=tk.LEFT, padx=4)

    delete_btn = ttk.Button(button_row, text="Delete", command=lambda: delete_selected_camp(), width=12)
    delete_btn.pack(side=tk.LEFT, padx=4)

    # added back the clear button
    clear_btn = ttk.Button(button_row, text="Clear", command=lambda: reset_form(), width=12)
    clear_btn.pack(side=tk.LEFT, padx=4)


    def update_form_buttons() -> None:
        """Enable/disable Create, Update, Delete buttons based on camp selection."""
        if selected_camp_id is None:
            create_btn.config(state="normal")
            update_btn.config(state="disabled")
            delete_btn.config(state="disabled")
        else:
            create_btn.config(state="disabled")
            update_btn.config(state="normal")
            delete_btn.config(state="normal")



    def delete_selected_camp() -> None:
        selection = camps_table.selection()
        if not selection:
            messagebox.showinfo("Delete camp", "Select a camp first.")
            return
        camp_id = int(selection[0])
        if not messagebox.askyesno("Delete camp", "Deleting a camp removes all related data. Continue?"):
            return
        if not delete_camp(camp_id):
            messagebox.showerror("Delete camp", "Unable to delete camp. Ensure no dependent data exists.")
            return
        load_camps()
        reset_form()
        update_form_buttons()

    ttk.Button(camps_frame, text="Select", command=select_camp).pack(side=tk.LEFT, padx=4)
    ttk.Button(camps_frame, text="Delete", command=delete_selected_camp).pack(side=tk.LEFT, padx=4)

    # ========== Tab 2: Stock Management ==========
    tab_stock = tk.Frame(notebook)
    notebook.add(tab_stock, text="Stock Management")

    ttk.Label(tab_stock, text="Top up daily food", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, padx=10, pady=(6, 2))
    topup_frame = ttk.Frame(tab_stock, style="Card.TFrame", padding=10)
    topup_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

    ttk.Label(topup_frame, text="Select a camp from 'Camps' tab, then apply a delta:").pack(pady=4, anchor=tk.W)

    topup_input_frame = ttk.Frame(topup_frame)
    topup_input_frame.pack(fill=tk.X, pady=4)

    topup_var = tk.StringVar(value="0")
    ttk.Label(topup_input_frame, text="Delta units per day (+/-)").pack(side=tk.LEFT, padx=4)
    ttk.Entry(topup_input_frame, textvariable=topup_var, width=10).pack(side=tk.LEFT, padx=4)

    def apply_topup() -> None:
        selection = camps_table.selection()
        if not selection:
            messagebox.showinfo("Top-up", "Select a camp from 'Camps' tab first.")
            return
        if not topup_var.get().strip() or topup_var.get().strip() == "0":
            messagebox.showwarning("Top-up", "Enter a non-zero integer delta.")
            return
        try:
            delta = int(topup_var.get().strip())
        except ValueError:
            messagebox.showerror("Top-up", "Delta must be an integer (can be negative).")
            return
        camp_id = int(selection[0])
        add_stock_topup(camp_id, delta)
        load_camps()
        topup_var.set("0")
        refresh_topup_history()

    ttk.Button(topup_input_frame, text="Apply", command=apply_topup, style="Primary.TButton").pack(side=tk.LEFT, padx=4)

    ttk.Label(tab_stock, text="Top-up history for selected camp", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, padx=10, pady=(6, 2))
    history_frame = ttk.Frame(tab_stock, style="Card.TFrame", padding=10)
    history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

    # Text area with themed scrollbar
    history_scroll = ttk.Scrollbar(history_frame, orient="vertical")
    history = tk.Text(history_frame, height=12, state="disabled", yscrollcommand=history_scroll.set)
    history_scroll.config(command=history.yview)
    history.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
    history_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def refresh_topup_history() -> None:
        selection = camps_table.selection()
        if not selection:
            history.config(state="normal")
            history.delete("1.0", tk.END)
            history.insert(tk.END, "Select a camp from 'Camps' tab to view top-up history.\n")
            history.config(state="disabled")
            return
        camp_id = int(selection[0])
        entries = list_stock_topups(camp_id)
        history.config(state="normal")
        history.delete("1.0", tk.END)
        if not entries:
            history.insert(tk.END, "No top-ups recorded for this camp.\n")
        else:
            for entry in entries:
                history.insert(
                    tk.END,
                    f"{entry['created_at']}: Δ {entry['delta_daily_units']} units\n",
                )
        history.config(state="disabled")

    camps_table.bind("<<TreeviewSelect>>", lambda _evt: refresh_topup_history())

    # ========== Tab 3: Analytics & Alerts ==========
    tab_analytics = tk.Frame(notebook)
    notebook.add(tab_analytics, text="Analytics")

    charts_container = ttk.Frame(tab_analytics)
    charts_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    chart_campers = BarChart(charts_container, width=360, height=220)
    chart_leaders = BarChart(charts_container, width=360, height=220)
    chart_activities = BarChart(charts_container, width=360, height=220)
    chart_area = BarChart(charts_container, width=360, height=220)
    chart_food = DualBarChart(charts_container, width=360, height=220)

    chart_campers.grid(row=0, column=0, padx=6, pady=6)
    chart_leaders.grid(row=0, column=1, padx=6, pady=6)
    chart_activities.grid(row=1, column=0, padx=6, pady=6)
    chart_area.grid(row=1, column=1, padx=6, pady=6)
    chart_food.grid(row=0, column=2, rowspan=2, padx=6, pady=6)

    # Removed muted subtitle to keep the UI clean

    ttk.Label(tab_analytics, text="Food shortage alerts", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, padx=10, pady=(6, 2))
    alerts_frame = ttk.Frame(tab_analytics, style="Card.TFrame", padding=10)
    alerts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

    # Replace Listbox with a styled read-only Text area + scrollbar for nicer formatting
    alerts_scroll = ttk.Scrollbar(alerts_frame, orient="vertical")
    alerts_text = tk.Text(
        alerts_frame,
        height=10,
        wrap="word",
        state="disabled",
        yscrollcommand=alerts_scroll.set,
    )
    alerts_scroll.config(command=alerts_text.yview)
    alerts_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=4)
    alerts_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def refresh_alerts() -> None:
        alerts = get_food_shortage_alerts()
        alerts_text.config(state="normal")
        alerts_text.delete("1.0", tk.END)
        if not alerts:
            alerts_text.insert(tk.END, "No shortages detected.\n")
            alerts_text.config(state="disabled")
            return
        for idx, alert in enumerate(alerts, start=1):
            camp_name = alert["camp_name"]
            days = len(alert["shortages"])
            # Header line for each camp
            alerts_text.insert(tk.END, f"• {camp_name} — {days} shortage day(s)\n")
            # Detail lines (up to 5)
            for day in alert["shortages"][:5]:
                alerts_text.insert(
                    tk.END,
                    f"    – {day['date']}: needs {abs(day['gap'])} unit(s)\n",
                )
            if len(alert["shortages"]) > 5:
                alerts_text.insert(tk.END, "    …\n")
            if idx < len(alerts):
                alerts_text.insert(tk.END, "\n")
        alerts_text.config(state="disabled")

    def refresh_charts() -> None:
        stats = get_coordinator_dashboard_stats()
        chart_campers.draw(stats["campers_per_camp"], title="Campers per camp")
        chart_leaders.draw(stats["leaders_per_camp"], title="Leaders per camp")
        chart_activities.draw(stats["activities_per_camp"], title="Activities per camp")
        chart_area.draw(stats["camps_by_area"], title="Camps by area")
        food_data = [
            (row["label"], row["effective"], row["required"])
            for row in stats["food_comparison"]
        ]
        chart_food.draw(food_data, labels=("Effective", "Required"), title="Daily food planned vs required")

    def load_camps() -> None:
        camps_table.delete(*camps_table.get_children())
        palette = get_palette(camps_table)
        # Configure zebra striping
        camps_table.tag_configure("even", background=palette["surface"])
        camps_table.tag_configure("odd", background=tint(palette["surface"], -0.03))

        camps = list_camps()
        if not camps:
            camps_empty_label.pack(pady=(4, 0), anchor=tk.W)
            return
        else:
            camps_empty_label.pack_forget()

        for idx, camp in enumerate(camps):
            camps_table.insert(
                "",
                tk.END,
                iid=camp["id"],
                values=(
                    camp["name"],
                    camp["location"],
                    camp.get("area", ""),
                    camp["type"],
                    camp.get("leader_names", "-"),
                    camp["start_date"],
                    camp["end_date"],
                    camp["daily_food_units_planned"],
                    camp["default_food_units_per_camper_per_day"],
                    camp["topup_delta"],
                    camp["effective_daily_food"],
                ),
                tags=("odd",) if (idx % 2 == 1) else ("even",),
            )
        refresh_charts()
        refresh_alerts()

    #def export_analytics_report():
        ##ath = filedialog.asksaveasfilename(
             #title="Export Analytics Report",
             #defaultextension=".txt",
             #filetypes=[("Text file", "*.txt"), ("All files", "*.*")],
             #initialfile="analytics_report.txt",
         #)
         #if not path:
    #         return
    #
    #     try:
    #         pass


    load_camps()
    refresh_topup_history()

    # ========== Tab 4: Chat ==========
    tab_chat = tk.Frame(notebook)
    notebook.add(tab_chat, text="Chat")

    MessageBoard(
        tab_chat,
        post_callback=lambda content: post_message(user.get("id"), content),
        fetch_callback=lambda: list_messages_lines(),
        current_user=user.get("username"),
    ).pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    return scroll
