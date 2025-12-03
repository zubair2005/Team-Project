"""Leader dashboard UI with tabbed navigation."""

import tkinter as tk
import os
import json
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
    get_camp,
    normalize_uk_phone_to_formatted,
    update_camper,
)
from ui.components import MessageBoard, Table, ScrollFrame
from ui.theme import get_palette, tint


def build_dashboard(root: tk.Misc, user: Dict[str, str], logout_callback: Callable[[], None]) -> tk.Frame:
    scroll = ScrollFrame(root)
    container = scroll.content

    header = ttk.Frame(container)
    header.pack(fill=tk.X, padx=10, pady=8)

    display_name = str(user.get("username") or "Leader")
    tk.Label(header, text=f"{display_name} Dashboard", font=("Helvetica", 16, "bold")).pack(side=tk.LEFT)
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
    assign_hscroll = ttk.Scrollbar(assign_container, orient="horizontal", command=assignments_table.xview)
    assignments_table.configure(yscrollcommand=assign_scroll.set, xscrollcommand=assign_hscroll.set)
    for col in columns:
        assignments_table.heading(col, text=col)
        assignments_table.column(col, width=140, minwidth=120, stretch=True)
    assignments_table.heading("Camp", anchor=tk.W)
    assignments_table.column("Camp", width=200, minwidth=160, stretch=False, anchor=tk.W)
    assignments_table.heading("Location", anchor=tk.W)
    assignments_table.column("Location", width=160, minwidth=140, stretch=False, anchor=tk.W)
    assignments_table.heading("Area", anchor=tk.CENTER)
    assignments_table.column("Area", width=120, minwidth=100, stretch=False, anchor=tk.CENTER)
    assignments_table.heading("Start", anchor=tk.CENTER)
    assignments_table.column("Start", width=120, minwidth=100, stretch=False, anchor=tk.CENTER)
    assignments_table.heading("End", anchor=tk.CENTER)
    assignments_table.column("End", width=120, minwidth=100, stretch=False, anchor=tk.CENTER)
    assignments_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
    assign_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4)
    assign_hscroll.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 4))

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
    avail_hscroll = ttk.Scrollbar(avail_container, orient="horizontal", command=available_table.xview)
    available_table.configure(yscrollcommand=avail_scroll.set, xscrollcommand=avail_hscroll.set)
    for col in columns:
        available_table.heading(col, text=col)
        available_table.column(col, width=140, minwidth=120, stretch=True)
    available_table.heading("Camp", anchor=tk.W)
    available_table.column("Camp", width=200, minwidth=160, stretch=False, anchor=tk.W)
    available_table.heading("Location", anchor=tk.W)
    available_table.column("Location", width=160, minwidth=140, stretch=False, anchor=tk.W)
    available_table.heading("Area", anchor=tk.CENTER)
    available_table.column("Area", width=120, minwidth=100, stretch=False, anchor=tk.CENTER)
    available_table.heading("Start", anchor=tk.CENTER)
    available_table.column("Start", width=120, minwidth=100, stretch=False, anchor=tk.CENTER)
    available_table.heading("End", anchor=tk.CENTER)
    available_table.column("End", width=120, minwidth=100, stretch=False, anchor=tk.CENTER)
    available_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
    avail_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4)
    avail_hscroll.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 4))

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

    # In-tab camp selector (preferred over relying on 'Camps & Pay' selection)
    selector_row = ttk.Frame(tab_campers)
    selector_row.pack(fill=tk.X, padx=10, pady=(8, 2))
    ttk.Label(selector_row, text="Camp:", style="Muted.TLabel").pack(side=tk.LEFT, padx=(0, 6))
    camp_selector_var = tk.StringVar(value="(None)")
    camp_selector = ttk.Combobox(selector_row, textvariable=camp_selector_var, state="readonly", width=40, style="Filled.TCombobox", exportselection=False)
    camp_selector.pack(side=tk.LEFT, padx=(0, 8))
    # Mapping from display label -> camp_id
    label_to_camp_id = {}
    selected_camp_for_campers: Optional[int] = None  # None means unspecified; -1 means explicit "(None)"

    def refresh_camp_selector() -> None:
        nonlocal label_to_camp_id, selected_camp_for_campers
        rows = list_leader_assignments(leader_id)
        label_to_camp_id = {}
        values = []
        for rec in rows:
            # Make label reasonably unique and informative
            label = f"{rec['name']} — {rec['start_date']} → {rec['end_date']}"
            # If duplicate labels occur, append camp_id
            if label in label_to_camp_id:
                label = f"{label} (#{rec['camp_id']})"
            label_to_camp_id[label] = rec["camp_id"]
            values.append(label)
        if not values:
            camp_selector.configure(values=["(None)"])
            camp_selector_var.set("(None)")
            # Keep unspecified so cross-tab fallback works until user explicitly picks "(None)"
            selected_camp_for_campers = None
        else:
            camp_selector.configure(values=["(None)"] + values)
            # Keep current selection if still available; else reset
            current = camp_selector_var.get()
            if current in label_to_camp_id:
                # Keep same
                selected_camp_for_campers = label_to_camp_id[current]
            else:
                camp_selector_var.set("(None)")
                # Keep unspecified so cross-tab fallback works until user explicitly picks "(None)"
                selected_camp_for_campers = None

    def _on_camp_selected(_evt=None) -> None:
        nonlocal selected_camp_for_campers
        label = camp_selector_var.get()
        if label == "(None)":
            selected_camp_for_campers = -1
        else:
            selected_camp_for_campers = label_to_camp_id.get(label)
        load_campers_for_selection()

    camp_selector.bind("<<ComboboxSelected>>", _on_camp_selected)

    # Helper: refresh selector when switching to this tab
    def _on_tab_changed(_evt=None) -> None:
        try:
            tab_text = notebook.tab(notebook.select(), "text")
            if tab_text == "Campers":
                refresh_camp_selector()
                # If no explicit selection in the in-tab selector, sync to assignment table selection
                if selected_camp_for_campers is None:
                    _sync_selector_to_assignment()
        except Exception:
            pass
    notebook.bind("<<NotebookTabChanged>>", _on_tab_changed)

    # Sort + Search controls
    controls_row = ttk.Frame(tab_campers)
    controls_row.pack(fill=tk.X, padx=10, pady=(2, 6))
    # Sort
    ttk.Label(controls_row, text="Sort:", style="Muted.TLabel").pack(side=tk.LEFT, padx=(0, 6))
    sort_var = tk.StringVar(value="Alphabetical A–Z")
    sort_box = ttk.Combobox(
        controls_row,
        textvariable=sort_var,
        values=["Alphabetical A–Z", "Alphabetical Z–A", "DOB Asc", "DOB Desc"],
        state="readonly",
        width=22,
        style="Filled.TCombobox",
        exportselection=False,
    )
    sort_box.pack(side=tk.LEFT, padx=(0, 12))
    # Search scope
    ttk.Label(controls_row, text="Search by:", style="Muted.TLabel").pack(side=tk.LEFT, padx=(0, 6))
    search_scope_var = tk.StringVar(value="Name")
    search_scope = ttk.Combobox(
        controls_row,
        textvariable=search_scope_var,
        values=["Name", "DOB (YYYY-MM-DD)", "Phone (+44 XXXX XXXXXX)", "Food units/day"],
        state="readonly",
        width=26,
        style="Filled.TCombobox",
        exportselection=False,
    )
    search_scope.pack(side=tk.LEFT, padx=(0, 6))
    # Search input
    search_query_var = tk.StringVar(value="")
    search_entry = ttk.Entry(controls_row, textvariable=search_query_var, width=28)
    search_entry.pack(side=tk.LEFT, padx=(0, 6))
    # Actions
    def run_campers_search() -> None:
        scope = search_scope_var.get()
        raw = search_query_var.get().strip()
        if not raw:
            messagebox.showwarning("Search", "Please enter a search value.")
            try:
                search_entry.focus_set()
            except Exception:
                pass
            return
        # Validate and normalize per scope
        if scope == "DOB (YYYY-MM-DD)":
            import re
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
                messagebox.showerror("Search", "DOB must be in YYYY-MM-DD format.")
                try:
                    search_entry.focus_set()
                    search_entry.selection_range(0, tk.END)
                except Exception:
                    pass
                return
            _set_active_search("DOB (YYYY-MM-DD)", raw)
        elif scope == "Phone (+44 XXXX XXXXXX)":
            # Allow substring search; no strict validation required
            _set_active_search("Phone (+44 XXXX XXXXXX)", raw)
        elif scope == "Food units/day":
            try:
                int(raw)
            except ValueError:
                messagebox.showerror("Search", "Food units/day must be an integer.")
                try:
                    search_entry.focus_set()
                    search_entry.selection_range(0, tk.END)
                except Exception:
                    pass
                return
            _set_active_search("Food units/day", raw)
        else:
            # Name
            _set_active_search("Name", raw)
        # debug removed
        # Apply and report no matches if any
        load_campers_for_selection()
        try:
            count = int(getattr(tab_campers, "_last_gallery_count", 0) or 0)
        except Exception:
            count = 0
        if count == 0:
            messagebox.showinfo("Search", "No matches found.")
            # debug removed
    def clear_campers_search() -> None:
        search_query_var.set("")
        _set_active_search(None, "")
        load_campers_for_selection()
    ttk.Button(controls_row, text="Search", command=run_campers_search).pack(side=tk.LEFT, padx=(0, 6))
    ttk.Button(controls_row, text="Clear", command=clear_campers_search).pack(side=tk.LEFT)
    # React to sort changes immediately
    sort_box.bind("<<ComboboxSelected>>", lambda _evt: load_campers_for_selection())
    # Run search on Enter key
    search_entry.bind("<Return>", lambda _evt: run_campers_search())
    # Keep active search state (None or dict with 'scope' and 'value')
    active_search = {"scope": None, "value": None}
    def _set_active_search(scope: str, value: str) -> None:
        active_search["scope"] = scope
        active_search["value"] = value
    # Clear search when leaving Campers tab
    def _on_tab_changed_clear_search(_evt=None) -> None:
        try:
            tab_text = notebook.tab(notebook.select(), "text")
            if tab_text != "Campers":
                search_query_var.set("")
                _set_active_search(None, "")
        except Exception:
            pass
    notebook.bind("<<NotebookTabChanged>>", _on_tab_changed_clear_search, add="+")

    campers_frame = tk.LabelFrame(tab_campers, text="Campers in selected camp", padx=10, pady=10)
    campers_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    # Gallery container (scrollable)
    gallery_outer = ttk.Frame(campers_frame)
    gallery_outer.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
    gallery_canvas = tk.Canvas(gallery_outer, highlightthickness=0, bd=0)
    gallery_scroll = ttk.Scrollbar(gallery_outer, orient="vertical", command=gallery_canvas.yview)
    gallery_canvas.configure(yscrollcommand=gallery_scroll.set)
    gallery_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    gallery_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    gallery_content = ttk.Frame(gallery_canvas)
    _gallery_window = gallery_canvas.create_window((0, 0), window=gallery_content, anchor="nw")

    def _on_gallery_configure(_evt=None) -> None:
        try:
            gallery_canvas.configure(scrollregion=gallery_canvas.bbox("all"))
        except Exception:
            pass
    def _on_gallery_canvas_resize(_evt=None) -> None:
        try:
            gallery_canvas.itemconfigure(_gallery_window, width=gallery_canvas.winfo_width())
            _layout_gallery_cards()
        except Exception:
            pass
    gallery_content.bind("<Configure>", _on_gallery_configure)
    gallery_canvas.bind("<Configure>", _on_gallery_canvas_resize)

    def _sync_selector_to_assignment() -> None:
        nonlocal selected_camp_for_campers, label_to_camp_id
        selection = assignments_table.selection()
        if not selection:
            return
        assignment_id = int(selection[0])
        record = next((rec for rec in list_leader_assignments(leader_id) if rec["id"] == assignment_id), None)
        if record is None:
            return
        camp_id = record["camp_id"]
        # Ensure selector options are current
        refresh_camp_selector()
        # Find label for camp_id
        label = next((lbl for lbl, cid in label_to_camp_id.items() if cid == camp_id), None)
        if label:
            camp_selector_var.set(label)
            selected_camp_for_campers = camp_id

    # Shared images cache on tab frame
    tab_campers._camper_thumb = None  # type: ignore[attr-defined]
    tab_campers._camper_large = None  # type: ignore[attr-defined]
    gallery_cards = []  # hold card frames for relayout

    def _ensure_camper_images() -> None:
        if getattr(tab_campers, "_camper_thumb", None) is not None:
            return
        # Try preferred path then fallbacks (support user-provided filenames)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(base_dir, "data", "images", "camper.png"),
            os.path.join(base_dir, "data", "camper.png"),
            os.path.join(base_dir, "data", "campa.png"),
        ]
        img_path = next((p for p in candidates if os.path.exists(p)), None)
        try:
            photo = tk.PhotoImage(file=img_path) if img_path else None
            # debug removed
            # Create thumbnail via subsample to approx 96x96
            if photo:
                w = max(1, int(photo.width()))
                h = max(1, int(photo.height()))
                factor = max(1, int(max(w / 96, h / 96)))
                thumb = photo.subsample(factor, factor)
                tab_campers._camper_thumb = thumb  # type: ignore[attr-defined]
                tab_campers._camper_large = photo  # type: ignore[attr-defined]
            else:
                tab_campers._camper_thumb = None  # type: ignore[attr-defined]
                tab_campers._camper_large = None  # type: ignore[attr-defined]
        except Exception:
            tab_campers._camper_thumb = None  # type: ignore[attr-defined]
            tab_campers._camper_large = None  # type: ignore[attr-defined]

    def _make_initials_avatar(master: tk.Misc, first: str, last: str) -> tk.Canvas:
        # Simple circular initials fallback at ~96x96
        palette = get_palette(master)
        canvas = tk.Canvas(master, width=96, height=96, highlightthickness=0, bd=0, bg=palette["surface"])
        # Circle
        canvas.create_oval(2, 2, 94, 94, fill=palette["accent"], outline=palette["accent"])
        initials = ((first[:1] or "?") + (last[:1] or "")).upper()
        canvas.create_text(48, 50, text=initials, fill="#ffffff", font=("Helvetica", 28, "bold"))
        return canvas

    def _calc_age_yrs(dob_str: str) -> str:
        try:
            import datetime as _dt
            dob = _dt.datetime.strptime(dob_str, "%Y-%m-%d").date()
            today = _dt.date.today()
            years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return f"{years} yrs"
        except Exception:
            return "—"

    def _layout_gallery_cards() -> None:
        # Grid cards with auto-fit based on available width
        if not gallery_cards:
            return
        width = max(1, gallery_canvas.winfo_width())
        card_w = 200
        cols = max(1, width // (card_w + 16))
        for idx, card in enumerate(gallery_cards):
            r = idx // cols
            c = idx % cols
            card.grid(row=r, column=c, padx=8, pady=8, sticky="n")
        # Configure grid columns to expand evenly
        for c in range(max(1, cols)):
            gallery_content.grid_columnconfigure(c, weight=1)

    def _render_gallery(campers: list) -> None:
        nonlocal gallery_cards
        # Clear previous
        for child in list(gallery_content.children.values()):
            child.destroy()
        gallery_cards = []
        _ensure_camper_images()
        palette = get_palette(gallery_content)

        def _open_camper_profile(camper: Dict) -> None:
            dialog = tk.Toplevel(gallery_content)
            dialog.title("Camper Profile")
            dialog.geometry("600x680")
            try:
                dialog.minsize(520, 560)
            except Exception:
                pass
            dialog.transient(gallery_content.winfo_toplevel())
            try:
                dialog.grab_set()
            except Exception:
                pass
            # debug removed
            # Track the open profile dialog so we can close it when selection changes
            try:
                prev = getattr(tab_campers, "_profile_dialog", None)
                if prev is not None and prev.winfo_exists():
                    prev.destroy()
            except Exception:
                pass
            try:
                setattr(tab_campers, "_profile_dialog", dialog)
            except Exception:
                pass
            # Scrollable content container
            container = ttk.Frame(dialog)
            container.pack(fill=tk.BOTH, expand=True)
            canvas = tk.Canvas(container, highlightthickness=0, bd=0)
            vscroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=vscroll.set)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            vscroll.pack(side=tk.RIGHT, fill=tk.Y)
            outer = ttk.Frame(canvas, padding=12)
            _win = canvas.create_window((0, 0), window=outer, anchor="nw")
            def _on_outer_configure(_evt=None) -> None:
                try:
                    canvas.configure(scrollregion=canvas.bbox("all"))
                except Exception:
                    pass
            def _on_canvas_configure(_evt=None) -> None:
                try:
                    canvas.itemconfigure(_win, width=canvas.winfo_width())
                except Exception:
                    pass
            outer.bind("<Configure>", _on_outer_configure)
            canvas.bind("<Configure>", _on_canvas_configure)
            # Large avatar
            holder = ttk.Frame(outer, style="Card.TFrame")
            holder.pack(pady=(4, 8))
            img_label = None
            if getattr(tab_campers, "_camper_large", None) is not None:  # type: ignore[attr-defined]
                base = tab_campers._camper_large  # type: ignore[attr-defined]
                try:
                    # Downscale if excessively large to fit within ~320px box
                    w, h = int(base.width()), int(base.height())
                    if w > 320 or h > 320:
                        factor = max(1, int(max(w / 320, h / 320)))
                        display_img = base.subsample(factor, factor)
                    else:
                        display_img = base
                    img_label = tk.Label(holder, image=display_img, bg=palette["surface"])
                    # Prevent garbage collection
                    img_label._keep_ref = display_img  # type: ignore[attr-defined]
                    img_label.pack()
                except Exception:
                    img_label = None
            if img_label is None:
                _make_initials_avatar(holder, camper.get("first_name",""), camper.get("last_name","")).pack()
            # Editable Details
            form = ttk.Frame(outer, style="Card.TFrame", padding=10)
            form.pack(fill=tk.X, pady=(0, 8))
            first_var = tk.StringVar(value=str(camper.get("first_name","")))
            last_var = tk.StringVar(value=str(camper.get("last_name","")))
            dob_var = tk.StringVar(value=str(camper.get("dob","")))
            phone_var = tk.StringVar(value=str(camper.get("emergency_contact","")))
            food_var = tk.StringVar(value=str(camper.get("food_units_per_day",0)))
            original_phone = str(camper.get("emergency_contact",""))
            # Best-effort normalize phone on open (no error if invalid)
            try:
                _maybe_norm = normalize_uk_phone_to_formatted(phone_var.get())
                if _maybe_norm:
                    phone_var.set(_maybe_norm)
            except Exception:
                pass
            # Row 1
            ttk.Label(form, text="First name").grid(row=0, column=0, sticky=tk.W, padx=4, pady=4)
            ttk.Entry(form, textvariable=first_var, width=20).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
            ttk.Label(form, text="Last name").grid(row=0, column=2, sticky=tk.W, padx=4, pady=4)
            ttk.Entry(form, textvariable=last_var, width=20).grid(row=0, column=3, sticky="ew", padx=4, pady=4)
            # Row 2
            ttk.Label(form, text="DOB (YYYY-MM-DD)").grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
            ttk.Entry(form, textvariable=dob_var, width=20).grid(row=1, column=1, sticky="ew", padx=4, pady=4)
            ttk.Label(form, text="Emergency (+44 XXXX XXXXXX)").grid(row=1, column=2, sticky=tk.W, padx=4, pady=4)
            phone_entry = ttk.Entry(form, textvariable=phone_var, width=20)
            phone_entry.grid(row=1, column=3, sticky="ew", padx=4, pady=4)
            # Row 3
            ttk.Label(form, text="Food units/day").grid(row=2, column=0, sticky=tk.W, padx=4, pady=4)
            ttk.Entry(form, textvariable=food_var, width=12).grid(row=2, column=1, sticky="ew", padx=4, pady=4)
            # Make form columns expand
            try:
                form.grid_columnconfigure(1, weight=1)
                form.grid_columnconfigure(3, weight=1)
            except Exception:
                pass
            # Auto-normalize phone on focus-out (silent if invalid)
            def _on_phone_focus_out(_evt=None) -> None:
                try:
                    norm = normalize_uk_phone_to_formatted(phone_var.get())
                    if norm:
                        phone_var.set(norm)
                except Exception:
                    pass
            phone_entry.bind("<FocusOut>", _on_phone_focus_out)
            # Info line shows computed age
            def _update_age_label() -> None:
                ttk.Label(outer, text=f"Age: { _calc_age_yrs(dob_var.get() or '') }", style="Muted.TLabel").pack(anchor=tk.W)
            _update_age_label()
            # Debug toggle: show raw record
            debug_row = ttk.Frame(outer)
            debug_row.pack(fill=tk.X, pady=(6, 2))
            ttk.Label(debug_row, text="Debug:", style="Muted.TLabel").pack(side=tk.LEFT)
            show_raw_var = tk.BooleanVar(value=False)
            debug_frame = ttk.Frame(outer)
            debug_text_widget = None
            def _toggle_debug() -> None:
                nonlocal debug_text_widget
                if show_raw_var.get():
                    if debug_text_widget is None:
                        debug_frame.pack(fill=tk.BOTH, expand=True, pady=(2, 6))
                        txt = tk.Text(debug_frame, height=10, wrap="word")
                        txt.pack(fill=tk.BOTH, expand=True)
                        try:
                            txt.insert(tk.END, json.dumps(camper, indent=2, default=str))
                        except Exception:
                            txt.insert(tk.END, str(camper))
                        txt.config(state="disabled")
                        debug_text_widget = txt
                else:
                    for child in list(debug_frame.children.values()):
                        child.destroy()
                    debug_frame.pack_forget()
                    debug_text_widget = None
            ttk.Checkbutton(debug_row, text="Show raw record", variable=show_raw_var, command=_toggle_debug).pack(side=tk.LEFT, padx=8)

            def _save_edits() -> None:
                # Validate inputs per spec
                f = first_var.get().strip()
                l = last_var.get().strip()
                if not f and not l:
                    messagebox.showerror("Edit camper", "Enter at least a first or last name.")
                    return
                dob_text = dob_var.get().strip()
                import re as _re
                if not _re.fullmatch(r"\d{4}-\d{2}-\d{2}", dob_text):
                    messagebox.showerror("Edit camper", "DOB must be in YYYY-MM-DD format.")
                    return
                # Try actual date parse
                try:
                    import pandas as _pd
                    _pd.to_datetime(dob_text, format="%Y-%m-%d")
                except Exception:
                    messagebox.showerror("Edit camper", "DOB is not a valid date.")
                    return
                # Phone normalization (+44XXXXXXXXX or +44 XXXX XXXXX -> +44 XXXX XXXXX)
                phone_raw = phone_var.get().strip()
                if phone_raw == "":
                    normalized = ""
                else:
                    normalized = normalize_uk_phone_to_formatted(phone_raw)
                    if not normalized:
                        messagebox.showerror("Edit camper", "Phone must be +44 followed by exactly 10 digits (e.g. +441234567890) or +44 XXXX XXXXXX (digits only).")
                        try:
                            phone_entry.focus_set()
                            phone_entry.selection_range(0, tk.END)
                        except Exception:
                            pass
                        return
                phone_var.set(normalized)
                # Food units/day int
                try:
                    food_int = int(food_var.get().strip())
                except Exception:
                    messagebox.showerror("Edit camper", "Food units/day must be an integer.")
                    return
                if food_int < 0:
                    messagebox.showerror("Edit camper", "Food units/day must be non-negative.")
                    return
                # Persist to DB
                camper_id = int(camper.get("camper_id"))
                camp_camper_id = int(camper.get("id"))
                ok = update_camper(camper_id, f, l, dob_text, normalized)
                if not ok:
                    messagebox.showerror("Edit camper", "Failed to update camper details.")
                    return
                try:
                    update_camp_camper_food(camp_camper_id, food_int)
                except Exception as exc:
                    messagebox.showerror("Edit camper", f"Failed to update food units/day: {exc}")
                    return
                # debug removed
                # Refresh view and close
                try:
                    load_campers_for_selection()
                except Exception:
                    pass
                dialog.destroy()

            buttons = ttk.Frame(outer)
            buttons.pack(fill=tk.X, pady=12)
            ttk.Button(buttons, text="Save", command=_save_edits).pack(side=tk.RIGHT, padx=4)
            ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)

        def _bind_card_click(widget: tk.Misc, camper: Dict) -> None:
            def _open(_evt=None) -> None:
                _open_camper_profile(camper)
            # Bind to container and its children
            try:
                widget.bind("<Button-1>", _open)
            except Exception:
                pass
            for child in getattr(widget, "winfo_children", lambda: [])():
                _bind_card_click(child, camper)

        for camper in campers:
            card = ttk.Frame(gallery_content, style="Card.TFrame", padding=8)
            # Image or initials
            holder = ttk.Frame(card, style="Card.TFrame")
            holder.pack()
            if getattr(tab_campers, "_camper_thumb", None) is not None:  # type: ignore[attr-defined]
                lbl = tk.Label(holder, image=tab_campers._camper_thumb, bg=palette["surface"])  # type: ignore[attr-defined]
                lbl.pack()
            else:
                _make_initials_avatar(holder, camper.get("first_name",""), camper.get("last_name","")).pack()
            # Text details
            name = f"{camper.get('first_name','')} {camper.get('last_name','')}".strip()
            ttk.Label(card, text=name, font=("Helvetica", 11, "bold")).pack(pady=(6, 0))
            dob = camper.get("dob") or ""
            ttk.Label(card, text=f"DOB: {dob}  •  { _calc_age_yrs(dob) }", style="Muted.TLabel").pack()
            ttk.Label(card, text=f"Emergency: {camper.get('emergency_contact','')}", style="Muted.TLabel").pack()
            ttk.Label(card, text=f"Food/day: {camper.get('food_units_per_day',0)}", style="Muted.TLabel").pack()
            # Click to open profile
            _bind_card_click(card, camper)
            # Store for layout
            gallery_cards.append(card)
        _layout_gallery_cards()

    campers_empty_label = ttk.Label(campers_frame, text="No campers in the selected camp.", style="Muted.TLabel")
    campers_empty_label.pack_forget()

    def load_campers_for_selection() -> None:
        # Prefer in-tab selector
        target_camp_id: Optional[int] = selected_camp_for_campers
        # If explicitly "(None)" was chosen, clear and return (do not fall back)
        if target_camp_id == -1:
            try:
                for child in list(gallery_content.children.values()):
                    child.destroy()
                setattr(tab_campers, "_last_gallery_count", 0)
            except Exception:
                pass
            try:
                prev = getattr(tab_campers, "_profile_dialog", None)
                if prev is not None and prev.winfo_exists():
                    prev.destroy()
                    setattr(tab_campers, "_profile_dialog", None)
            except Exception:
                pass
            campers_empty_label.pack(pady=(0, 4), anchor=tk.W)
            return
        # Fallback: use selection from 'Camps & Pay' if none chosen in selector
        selection = assignments_table.selection()
        assignment_id = int(selection[0]) if selection else None
        record = next((rec for rec in list_leader_assignments(leader_id) if rec["id"] == assignment_id), None) if assignment_id is not None else None
        if target_camp_id is None and record is not None:
            target_camp_id = record["camp_id"]
        if target_camp_id is None:
            # Nothing selected anywhere; show empty state
            # Clear any existing gallery content
            try:
                for child in list(gallery_content.children.values()):
                    child.destroy()
                setattr(tab_campers, "_last_gallery_count", 0)
            except Exception:
                pass
            # Close any open profile dialog
            try:
                prev = getattr(tab_campers, "_profile_dialog", None)
                if prev is not None and prev.winfo_exists():
                    prev.destroy()
                    setattr(tab_campers, "_profile_dialog", None)
            except Exception:
                pass
            campers_empty_label.pack(pady=(0, 4), anchor=tk.W)
            return
        campers = list_camp_campers(target_camp_id)
        # Apply active search filter if present
        scope = active_search.get("scope")
        query = (active_search.get("value") or "").strip()
        # debug removed
        if scope and query:
            q_lower = query.lower()
            if scope == "Name":
                def _match_name(row) -> bool:
                    first = str(row.get("first_name", "")).lower()
                    last = str(row.get("last_name", "")).lower()
                    full = f"{first} {last}"
                    return (q_lower in first) or (q_lower in last) or (q_lower in full)
                campers = [r for r in campers if _match_name(r)]
            elif scope == "DOB (YYYY-MM-DD)":
                campers = [r for r in campers if str(r.get("dob") or "") == query]
            elif scope == "Phone (+44 XXXX XXXXXX)":
                # Substring match across multiple normalized variants (robust to formatting)
                import re as _re
                q_clean = _re.sub(r"[^\d+]", "", query or "")
                q_digits = _re.sub(r"\D", "", query or "")
                def _match_phone(row) -> bool:
                    s = str(row.get("emergency_contact") or "")
                    s_clean = _re.sub(r"[^\d+]", "", s)          # keep '+' and digits
                    s_digits = _re.sub(r"\D", "", s)              # digits only
                    # Local variant without +44
                    s_local = s_digits
                    if s_digits.startswith("44"):
                        s_local = s_digits[2:]
                    # Any of the query forms contained in any candidate form
                    if q_clean and q_clean in s_clean:
                        return True
                    if q_digits and q_digits in s_digits:
                        return True
                    if q_digits and q_digits in s_local:
                        return True
                    return False
                campers = [r for r in campers if _match_phone(r)]
            elif scope == "Food units/day":
                try:
                    q_int = int(query)
                    campers = [r for r in campers if int(r.get("food_units_per_day") or 0) == q_int]
                except Exception:
                    campers = []
        # debug removed
        # Apply sorting (search/filtering will be added in step 6)
        try:
            mode = sort_var.get() if 'sort_var' in locals() or 'sort_var' in globals() else "Alphabetical A–Z"
        except Exception:
            mode = "Alphabetical A–Z"
        if mode in ("Alphabetical A–Z", "Alphabetical Z–A"):
            campers.sort(key=lambda r: (str(r.get("last_name","")).lower(), str(r.get("first_name","")).lower()))
            if mode.endswith("Z–A"):
                campers.reverse()
        elif mode == "DOB Asc":
            # YYYY-MM-DD sorts lexicographically; missing treated last
            campers.sort(key=lambda r: (str(r.get("dob") or "9999-99-99")))
        elif mode == "DOB Desc":
            campers.sort(key=lambda r: (str(r.get("dob") or "0000-00-00")), reverse=True)
        # Render gallery with current campers list
        try:
            _render_gallery(campers)
        except Exception:
            # Fail-safe: do not crash UI if gallery rendering fails
            pass
        # Track count for 'no results' and empty state
        try:
            setattr(tab_campers, "_last_gallery_count", len(campers))
        except Exception:
            pass
        # Empty state toggle (based on gallery list)
        if not campers:
            # Close any open profile dialog if list is empty
            try:
                prev = getattr(tab_campers, "_profile_dialog", None)
                if prev is not None and prev.winfo_exists():
                    prev.destroy()
                    setattr(tab_campers, "_profile_dialog", None)
            except Exception:
                pass
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

    action_row = ttk.Frame(campers_frame)
    action_row.pack(fill=tk.X, pady=4)
    ttk.Button(action_row, text="Import campers from CSV", command=import_csv).pack(side=tk.LEFT, padx=4)

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
    activities_hscroll = ttk.Scrollbar(activities_container, orient="horizontal", command=activities_table.xview)
    activities_table.configure(yscrollcommand=activities_scroll.set, xscrollcommand=activities_hscroll.set)
    activities_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
    activities_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4)
    activities_hscroll.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 4))

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
                date_dt = pd.to_datetime(date, format="%Y-%m-%d")
            except Exception:
                messagebox.showerror("Activity", "Invalid date format. Use YYYY-MM-DD.")
                return
            # Validate date within camp range
            camp = get_camp(assignment["camp_id"])
            try:
                start_dt = pd.to_datetime(camp["start_date"], format="%Y-%m-%d")
                end_dt = pd.to_datetime(camp["end_date"], format="%Y-%m-%d")
            except Exception:
                messagebox.showerror("Activity", "Could not read camp dates for validation.")
                return
            if date_dt < start_dt or date_dt > end_dt:
                messagebox.showerror(
                    "Activity",
                    f"Date must be within the camp’s dates ({camp['start_date']} to {camp['end_date']}).",
                )
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

        ttk.Label(dialog, text="Select multiple campers (Ctrl/Cmd + click)", style="Muted.TLabel", font=("Helvetica", 10, "italic")).pack(pady=4)

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
                date_dt = pd.to_datetime(date, format="%Y-%m-%d")
            except Exception:
                messagebox.showerror("Activity", "Invalid date format. Use YYYY-MM-DD.")
                return
            # Validate date within camp range
            camp = get_camp(assignment["camp_id"])
            try:
                start_dt = pd.to_datetime(camp["start_date"], format="%Y-%m-%d")
                end_dt = pd.to_datetime(camp["end_date"], format="%Y-%m-%d")
            except Exception:
                messagebox.showerror("Activity", "Could not read camp dates for validation.")
                return
            if date_dt < start_dt or date_dt > end_dt:
                messagebox.showerror(
                    "Activity",
                    f"Date must be within the camp’s dates ({camp['start_date']} to {camp['end_date']}).",
                )
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
        # Keep the in-tab selector in sync with assignment selection unless user picked "(None)"
        if selected_camp_for_campers is None:
            _sync_selector_to_assignment()
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
    reports_hscroll = ttk.Scrollbar(reports_container, orient="horizontal", command=reports_table.xview)
    reports_table.configure(yscrollcommand=reports_scroll.set, xscrollcommand=reports_hscroll.set)
    reports_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
    reports_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4)
    reports_hscroll.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 4))

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
            # Enforce strict format
            try:
                import pandas as pd
                pd.to_datetime(date, format="%Y-%m-%d")
            except Exception:
                messagebox.showerror("Report", "Invalid date format. Use YYYY-MM-DD.")
                return
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
    stats_hscroll = ttk.Scrollbar(stats_table_container, orient="horizontal", command=stats_table.xview)
    stats_table.configure(yscrollcommand=stats_scroll.set, xscrollcommand=stats_hscroll.set)
    stats_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
    stats_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4)
    stats_hscroll.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 4))

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

