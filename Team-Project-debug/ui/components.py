import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from services import list_messages
from typing import Callable, Iterable, List, Sequence, Tuple, Optional
from ui.theme import get_palette, tint


class MessageBoard(tk.Frame):
    def __init__(self, master: tk.Misc, post_callback: Callable[[str], None],
                 fetch_callback: Callable[[], Sequence[str]], current_user: Optional[str] = None,
                 enable_search: bool = True):
        super().__init__(master)
        self.post_callback = post_callback
        self.fetch_callback = fetch_callback
        self.current_user = current_user
        self.enable_search = enable_search

        palette = get_palette(self)
        self.configure(background=palette["bg"])

        tk.Label(self, text="Chat", font=("Helvetica", 12, "bold"), bg=palette["bg"], fg=palette["text"]).pack(
            pady=(0, 4), anchor=tk.W)
        if self.enable_search:
            search_row = ttk.Frame(self)
            search_row.pack(fill=tk.X, pady=(0, 6))
            ttk.Label(search_row, text="Search:", style="Muted.TLabel").pack(side=tk.LEFT, padx=(0, 6))
            self._search_var = tk.StringVar(value="")
            self._search_entry = ttk.Entry(search_row, textvariable=self._search_var, width=36)
            self._search_entry.pack(side=tk.LEFT, padx=4)
            self._scope_var = tk.StringVar(value="Users")
            ttk.Combobox(
                search_row,
                textvariable=self._scope_var,
                values=["Users", "Date (YYYY-MM-DD)", "Message Content"],
                state="readonly",
                width=24,
                style="Filled.TCombobox",
            ).pack(side=tk.LEFT, padx=6)
            ttk.Button(search_row, text="Search", command=self._run_search).pack(side=tk.LEFT, padx=4)

        # Scrollable messages area (Canvas + inner Frame)
        container = tk.Frame(self, bg=palette["bg"])
        container.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(container, bg=palette["bg"], highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.messages_frame = tk.Frame(self.canvas, bg=palette["bg"])
        self.messages_window = self.canvas.create_window((0, 0), window=self.messages_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_frame_configure(_evt=None) -> None:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        def _on_canvas_configure(_evt=None) -> None:
            # Make inner frame match canvas width for wrapping
            self.canvas.itemconfigure(self.messages_window, width=self.canvas.winfo_width())

        self.messages_frame.bind("<Configure>", _on_frame_configure)
        self.canvas.bind("<Configure>", _on_canvas_configure)

        entry_frame = ttk.Frame(self)
        entry_frame.pack(fill=tk.X, pady=6)

        self.entry = ttk.Entry(entry_frame)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(entry_frame, text="Refresh", command=self.refresh).pack(side=tk.RIGHT)
        ttk.Button(entry_frame, text="Send", command=self._send).pack(side=tk.RIGHT, padx=4)

        self.refresh()

    def refresh(self) -> None:
        messages = list(self.fetch_callback())
        # Re-render as chat bubbles
        for child in list(self.messages_frame.children.values()):
            child.destroy()
        for raw in messages:
            created, sender, content = self._parse_line(raw)
            self._add_bubble(sender, content, created)
        # Auto-scroll to bottom
        self.after(10, lambda: self.canvas.yview_moveto(1.0))

    def _run_search(self) -> None:
        keyword = (self._search_var.get() if hasattr(self, "_search_var") else "").strip()
        scope = (self._scope_var.get() if hasattr(self, "_scope_var") else "Users")
        if not keyword:
            messagebox.showwarning("Search", "Please enter a search keyword.")
            return
        rows = list_messages()
        matches: List[str] = []
        key_lower = keyword.lower()
        if scope == "Date (YYYY-MM-DD)":
            import re
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", keyword):
                messagebox.showerror("Search", "Date must be in format YYYY-MM-DD.")
                return
        for row in rows:
            sender = (row.get("sender_username") or "").strip()
            created = str(row.get("created_at") or "").strip()
            content = (row.get("content") or "").strip()
            if scope == "Users":
                if sender.lower() == key_lower:
                    matches.append(f"[{created}] {sender}: {content}")
            elif scope == "Message Content":
                if key_lower in content.lower():
                    matches.append(f"[{created}] {sender}: {content}")
            else:  # Date (YYYY-MM-DD)
                # Compare date-only part robustly
                date_part = created.split(" ")[0].split("T")[0] if created else ""
                if date_part == keyword:
                    matches.append(f"[{created}] {sender}: {content}")
        if not matches:
            if scope == "Users":
                messagebox.showerror("Search", f"No messages found from user '{keyword}'.")
            elif scope == "Message Content":
                messagebox.showerror("Search", f"No messages containing '{keyword}'.")
            else:
                messagebox.showerror("Search", f"No messages found for date '{keyword}'.")
            return
        # Show results dialog (viewer only in this step)
        dialog = tk.Toplevel(self)
        dialog.title(f"Chat results: {scope} = '{keyword}'")
        dialog.geometry("520x420")
        # Container
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        text = tk.Text(frame, state="normal", height=16, wrap="word")
        text.pack(fill=tk.BOTH, expand=True)
        # Oldest first (reverse chronological in DB → reverse here)
        for line in reversed(matches):
            text.insert(tk.END, line + "\n")
        text.config(state="disabled")
        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=8)

        def do_export() -> None:
            path = filedialog.asksaveasfilename(
                title="Export chat results",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")],
                initialfile="chat_export.csv",
            )
            if not path:
                return
            try:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    # Write plain lines; consumer can open in any editor
                    for line in reversed(matches):
                        f.write(line)
                        f.write("\n")
                messagebox.showinfo("Export", f"Saved {len(matches)} line(s) to:\n{path}")
            except OSError as exc:
                messagebox.showerror("Export failed", f"Could not write file:\n{exc}")

        ttk.Button(buttons, text="Export to CSV", command=do_export).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)

    def _send(self) -> None:
        content = self.entry.get().strip()
        if not content:
            return
        self.post_callback(content)
        self.entry.delete(0, tk.END)
        self.refresh()

    def _parse_line(self, line: str) -> Tuple[str, str, str]:
        created = ""
        sender = ""
        content = line
        try:
            if line.startswith("["):
                rb = line.find("]")
                if rb != -1:
                    created = line[1:rb].strip()
                    rest = line[rb + 1:].lstrip()
                else:
                    rest = line
            else:
                rest = line
            colon = rest.find(":")
            if colon != -1:
                sender = rest[:colon].strip()
                content = rest[colon + 1:].strip()
            else:
                sender = ""
                content = rest.strip()
        except Exception:
            created, sender, content = "", "", line
        return created, sender, content

    def _add_bubble(self, sender: str, content: str, created: str) -> None:
        palette = get_palette(self)
        is_me = (self.current_user is not None) and (sender == self.current_user)

        row = tk.Frame(self.messages_frame, bg=palette["bg"])
        row.pack(fill=tk.X, pady=3, padx=8)

        side = tk.RIGHT if is_me else tk.LEFT
        bubble_bg = palette["accent"] if is_me else palette["surface"]
        text_fg = "#ffffff" if is_me else palette["text"]
        meta_fg = "#e5e7eb" if is_me else palette["muted"]

        # Simple rectangular bubble using a Frame and Labels (restores previous behavior)
        bubble = tk.Frame(row, bg=bubble_bg, bd=0, highlightthickness=0)
        bubble.pack(side=side, padx=6, ipady=4)

        # Content label
        lbl = tk.Label(
            bubble,
            text=content,
            bg=bubble_bg,
            fg=text_fg,
            justify=tk.LEFT,
            wraplength=480,
            font=("Helvetica", 11),
        )
        lbl.pack(anchor=tk.W, padx=10, pady=(6, 2))

        # Meta (sender • timestamp)
        meta_text = sender if not is_me else "You"
        if created:
            meta_text += f" • {created}"
        meta = tk.Label(
            bubble,
            text=meta_text,
            bg=bubble_bg,
            fg=meta_fg,
            font=("Helvetica", 9),
        )
        meta.pack(anchor=tk.E if is_me else tk.W, padx=10, pady=(0, 6))


class ScrollFrame(tk.Frame):
    """A reusable scrollable container with both vertical and horizontal scrollbars.
    Place content into the 'content' frame attribute. The outer frame should be packed/gridded.
    """

    def __init__(self, master: tk.Misc):
        palette = get_palette(master)
        super().__init__(master, bg=palette["bg"])
        self.canvas = tk.Canvas(self, bg=palette["bg"], highlightthickness=0, bd=0)
        self.vscroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.hscroll = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vscroll.set, xscrollcommand=self.hscroll.set)

        # Layout: canvas fills, scrollbars at right and bottom
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vscroll.grid(row=0, column=1, sticky="ns")
        self.hscroll.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Inner content frame
        self.content = tk.Frame(self.canvas, bg=palette["bg"])
        self._window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        # Update scrollregion when content size changes
        def _on_content_configure(_evt=None) -> None:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        self.content.bind("<Configure>", _on_content_configure)

        # Keep left alignment; allow horizontal scroll by not forcing width
        def _on_canvas_resize(_evt=None) -> None:
            # Make content span the visible width; allow vertical overflow for scrolling
            self.canvas.itemconfigure(self._window_id, anchor="nw", width=self.canvas.winfo_width())

        self.canvas.bind("<Configure>", _on_canvas_resize)


class Table(ttk.Treeview):
    def __init__(self, master: tk.Misc, columns: Iterable[str]):
        super().__init__(master, columns=columns, show="headings")
        for col in columns:
            self.heading(col, text=col)
            self.column(col, width=120)

    def load_rows(self, rows: List[Sequence[str]]) -> None:
        self.delete(*self.get_children())
        for row in rows:
            self.insert("", tk.END, values=row)


class BarChart(tk.Canvas):
    def __init__(self, master: tk.Misc, width: int = 400, height: int = 240):
        super().__init__(master, width=width, height=height, background="white", highlightthickness=1,
                         highlightbackground="#cccccc")
        self.width = width
        self.height = height

    def draw(self, data: List[Tuple[str, int]], title: str = "") -> None:
        self.delete("all")

        # Draw title
        if title:
            self.create_text(self.width // 2, 16, text=title, font=("Helvetica", 11, "bold"), fill="#2c3e50")

        if not data:
            self.create_text(self.width // 2, self.height // 2, text="No data", fill="#95a5a6", font=("Helvetica", 10))
            return

        labels, values = zip(*data)
        max_value = max(values) if values else 0
        if max_value == 0:
            max_value = 1

        margin = 45
        chart_height = self.height - margin * 2
        chart_width = self.width - margin * 2
        bar_width = chart_width / max(len(values), 1)

        # Draw gridlines
        for i in range(5):
            y = self.height - margin - (i * chart_height / 4)
            self.create_line(margin, y, self.width - margin, y, fill="#ecf0f1", width=1)

        # Draw bars with gradient-like effect
        colors = ["#3498db", "#2ecc71", "#9b59b6", "#e74c3c", "#f39c12", "#1abc9c"]

        for idx, value in enumerate(values):
            x0 = margin + idx * bar_width + 8
            x1 = margin + (idx + 1) * bar_width - 8
            bar_height = (value / max_value) * chart_height
            y0 = self.height - margin - bar_height
            y1 = self.height - margin

            color = colors[idx % len(colors)]
            self.create_rectangle(x0, y0, x1, y1, fill=color, outline="", width=0)

            # Value label above bar
            self.create_text((x0 + x1) / 2, y0 - 12, text=str(value), font=("Helvetica", 9, "bold"), fill="#2c3e50")

            # X-axis label (truncate if too long)
            label = str(labels[idx])
            if len(label) > 10:
                label = label[:9] + "…"
            self.create_text((x0 + x1) / 2, self.height - margin + 14, text=label, font=("Helvetica", 8),
                             fill="#34495e")


class DualBarChart(tk.Canvas):
    def __init__(self, master: tk.Misc, width: int = 400, height: int = 240):
        super().__init__(master, width=width, height=height, background="white", highlightthickness=1,
                         highlightbackground="#cccccc")
        self.width = width
        self.height = height

    def draw(self, data: List[Tuple[str, int, int]], labels: Tuple[str, str] = ("A", "B"), title: str = "") -> None:
        self.delete("all")

        # Draw title
        if title:
            self.create_text(self.width // 2, 16, text=title, font=("Helvetica", 11, "bold"), fill="#2c3e50")

        if not data:
            self.create_text(self.width // 2, self.height // 2, text="No data", fill="#95a5a6", font=("Helvetica", 10))
            return

        max_value = max(max(a, b) for _, a, b in data)
        if max_value == 0:
            max_value = 1

        # Use separate top/bottom margins to make space for legend and avoid overlap
        left_right_margin = 45
        top_margin = 70
        bottom_margin = 45

        chart_height = self.height - (top_margin + bottom_margin)
        chart_width = self.width - left_right_margin * 2
        bar_group_width = chart_width / max(len(data), 1)
        bar_width = (bar_group_width - 10) / 2

        # Draw gridlines
        for i in range(5):
            y = self.height - bottom_margin - (i * chart_height / 4)
            self.create_line(left_right_margin, y, self.width - left_right_margin, y, fill="#ecf0f1", width=1)

        # Better colors: blue for first, green for second
        colors = ["#3498db", "#27ae60"]

        for idx, (label, val1, val2) in enumerate(data):
            base_x = left_right_margin + idx * bar_group_width
            for jdx, value in enumerate((val1, val2)):
                x0 = base_x + jdx * bar_width + 4
                x1 = x0 + bar_width - 4
                bar_height = (value / max_value) * chart_height
                y0 = self.height - bottom_margin - bar_height
                y1 = self.height - bottom_margin
                color = colors[jdx]
                self.create_rectangle(x0, y0, x1, y1, fill=color, outline="", width=0)
                self.create_text((x0 + x1) / 2, y0 - 12, text=str(value), font=("Helvetica", 9, "bold"), fill="#2c3e50")

            # X-axis label (truncate if needed)
            label_text = str(label)
            if len(label_text) > 10:
                label_text = label_text[:9] + "…"
            self.create_text(base_x + bar_group_width / 2, self.height - bottom_margin + 14, text=label_text,
                             font=("Helvetica", 8), fill="#34495e")

        # Legend
        legend_y = 36  # below title area, above bars
        self.create_rectangle(left_right_margin, legend_y, left_right_margin + 14, legend_y + 14, fill=colors[0],
                              outline="")
        self.create_text(left_right_margin + 18, legend_y + 7, text=labels[0], anchor=tk.W, font=("Helvetica", 9),
                         fill="#2c3e50")
        self.create_rectangle(left_right_margin + 120, legend_y, left_right_margin + 134, legend_y + 14, fill=colors[1],
                              outline="")
        self.create_text(left_right_margin + 138, legend_y + 7, text=labels[1], anchor=tk.W, font=("Helvetica", 9),
                         fill="#2c3e50")


class PillButton(tk.Canvas):
    def __init__(self, master: tk.Misc, text: str, command: Callable[[], None], variant: str = "default",
                 width: int = 140, height: int = 36):
        super().__init__(master, width=width, height=height, highlightthickness=0, bd=0)
        self._text = text
        self._command = command
        self._variant = variant
        self._width = width
        self._height = height
        self._hover = False
        self._press = False
        self._items = {}
        self._apply_bg()
        self._redraw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        # React to theme changes
        self.bind_all("<<ThemeChanged>>", self._on_theme_changed, add="+")

    def _apply_bg(self) -> None:
        bg = get_palette(self)["bg"]
        self.configure(background=bg, highlightbackground=bg)

    def _colors(self) -> Tuple[str, str]:
        palette = get_palette(self)
        if self._variant == "primary":
            fill = palette["accent"]
            text = "#ffffff"
            if self._hover:
                fill = tint(fill, -0.08)
            if self._press:
                fill = tint(fill, -0.16)
            return fill, text
        else:
            fill = palette["surface"]
            text = palette["text"]
            if self._hover:
                fill = palette["border"]
            if self._press:
                fill = tint(fill, -0.06)
            return fill, text

    def _redraw(self) -> None:
        self.delete("all")
        w, h = self._width, self._height
        r = h // 2
        fill, text_color = self._colors()
        # Ensure canvas bg matches theme each draw (in case of theme toggles)
        self._apply_bg()
        # Base shape (pill): two circles + center rect (fill)
        self.create_oval(0, 0, 2 * r, 2 * r, fill=fill, outline="")
        self.create_oval(w - 2 * r, 0, w, 2 * r, fill=fill, outline="")
        self.create_rectangle(r, 0, w - r, h, fill=fill, outline="")
        # Label
        self.create_text(w // 2, h // 2, text=self._text, fill=text_color, font=("Helvetica", 11, "bold"))

    def _on_enter(self, _evt) -> None:
        self._hover = True
        self._redraw()

    def _on_leave(self, _evt) -> None:
        self._hover = False
        self._press = False
        self._redraw()

    def _on_press(self, _evt) -> None:
        self._press = True
        self._redraw()

    def _on_release(self, _evt) -> None:
        was_press = self._press
        self._press = False
        self._redraw()
        if was_press and callable(self._command):
            self._command()

    def _on_theme_changed(self, _evt=None) -> None:
        # Update canvas background and repaint to remove any rectangular artifacts
        self._apply_bg()
        self._redraw()
